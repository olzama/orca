#!/usr/bin/env python3
"""Repair by replay: when the grammar rejects the tagger's derivation, try
the tagger's next-best labels inside the part of the tree that failed.

Best-first search over label assignments. The start is the tagger's first
choice for every token. A rejected assignment is expanded by changing one
label (leaf or tree) of a token under the failing node to one of its k best
alternatives. Assignments are tried in order of probability under the
tagger, until one replays or the budget of replays is used up. Each replay
is linear in the sentence; there is no chart.

Usage:
    repair.py --data DATA_DIR --grammar ERG/english.tdl --profiles SPLIT_DIR
              --tagger MODEL_DIR --out FILE [--split dev] [--budget 30] [--limit N]
"""
import argparse
import collections
import heapq
import json
import math
import os
import sys
import time

import torch
from transformers import AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from eval_trees import to_leaves  # noqa: E402
from llm_label import read  # noqa: E402
from orca.encoding import Leaf, decode  # noqa: E402
from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402
from orca.tfs.lexicon import Lexicon, replay_with_entries  # noqa: E402
from replay_predictions import gold_tokens  # noqa: E402
from train_tagger import UNK, Tagger, collate  # noqa: E402

CONT = '<cont>'


def failing_tokens(tree, where, leaf_labels):
    """Token positions under the node that a replay failure names."""
    path = [int(i) for i in where.split()[0].split('.')[1:]]
    node = tree
    start = 0

    def n_leaves(t):
        return 1 if isinstance(t, Leaf) else sum(n_leaves(c) for c in t.children)

    for i in path:
        if isinstance(node, Leaf) or i >= len(node.children):
            break
        for c in node.children[:i]:
            start += n_leaves(c)
        node = node.children[i]
    leaves = set(range(start, start + n_leaves(node)))
    out, li = [], -1
    for j, l in enumerate(leaf_labels):
        if not l.startswith(CONT):
            li += 1
        if li in leaves:
            out.append(j)
    return out


_WORK = None


def search(index):
    """Best-first repair of one sentence. Runs in a worker process."""
    g, sents, tops, tokens, args, lexicon = _WORK
    s, top = sents[index], tops[index]
    forms, n = s['forms'], len(s['forms'])
    toks = tokens[s['id']]
    cache = {} if args.cache else None

    def replay(leaf, tree):
        """None if accepted, else the token positions to reconsider."""
        mark = g.u.mark()
        try:
            t = decode(to_leaves(forms, leaf, tree))
        except Exception:
            return list(range(n))
        try:
            if lexicon is not None:
                replay_with_entries(g, lexicon, t, toks, cache=cache)
            else:
                g.replay_tree(t, toks, cache=cache)
            return None
        except ReplayFailure as e:
            return failing_tokens(t, e.where, leaf) or list(range(n))
        finally:
            del g.u.trail[mark:]

    def assignment(state):
        leaf = [top['leaf'][j][0][0] for j in range(n)]
        tree = [top['tree'][j][0][0] for j in range(n)]
        for kind, j, r in state:
            (leaf if kind == 'leaf' else tree)[j] = top[kind][j][r][0]
        return leaf, tree

    def right(leaf, tree):
        return leaf == s['leaf'] and tree[:-1] == s['tree'][:-1]

    heap, seen, counter, n_replays = [(0.0, 0, ())], {()}, 1, 0
    accepted, first_right = None, None
    while heap and n_replays < args.budget:
        cost, _, state = heapq.heappop(heap)
        leaf, tree = assignment(state)
        if first_right is None:
            first_right = right(leaf, tree)
        n_replays += 1
        span = replay(leaf, tree)
        if span is None:
            accepted = (leaf, tree, state)
            break
        changed = {(kind, j) for kind, j, _ in state}
        cands = []
        for j in span:
            for kind in ('leaf', 'tree'):
                if kind == 'tree' and j == n - 1:
                    continue
                if (kind, j) not in changed and len(top[kind][j]) > 1:
                    cands.append((top[kind][j][0][2], kind, j))
        cands.sort()
        for _, kind, j in cands[:args.fanout]:
            for r in range(1, len(top[kind][j])):
                label, logp, p = top[kind][j][r]
                if p < args.min_prob:
                    break
                new = tuple(sorted(state + ((kind, j, r),)))
                if new not in seen:
                    seen.add(new)
                    heapq.heappush(heap, (cost + top[kind][j][0][1] - logp, counter, new))
                    counter += 1
    if accepted is None:
        outcome = 'rejected, budget used' if n_replays >= args.budget else 'rejected, nothing left to try'
        leaf, tree = assignment(())
        return outcome, leaf, tree, n_replays, first_right, False
    leaf, tree, state = accepted
    ok = right(leaf, tree)
    outcome = ('accepted at first try' if not state else 'accepted after repair') + (', right' if ok else ', wrong')
    return outcome, leaf, tree, n_replays, first_right, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--tagger', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', default='dev')
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--min-prob', type=float, default=0.005)
    ap.add_argument('--budget', type=int, default=30, help='replays per sentence')
    ap.add_argument('--fanout', type=int, default=8, help='least certain decisions expanded per failure')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--entries', action='store_true',
                    help='replay with lexical entries found in the lexicon')
    ap.add_argument('--no-cache', dest='cache', action='store_false',
                    help='rebuild every subtree on every replay')
    ap.add_argument('--pred-out')
    args = ap.parse_args()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    labels = json.load(open(os.path.join(args.tagger, 'labels.json')))
    itos = {'leaf': labels['leaf'], 'tree': labels['tree']}
    stoi = {k: {l: i for i, l in enumerate(v)} for k, v in itos.items()}
    tok = AutoTokenizer.from_pretrained(labels['encoder'])
    model = Tagger(labels['encoder'], len(itos['leaf']), len(itos['tree'])).to(device)
    model.load_state_dict(torch.load(os.path.join(args.tagger, 'model.pt'), map_location=device), strict=False)
    model.eval()

    sents = read(os.path.join(args.data, f'{args.split}.jsonl'))
    if args.limit:
        sents = sents[:args.limit]
    tokens = gold_tokens(args.profiles)
    g = Grammar(args.grammar)
    t0 = time.time()

    # phase 1: tag everything (GPU), keeping the k best labels per token
    tops = []
    for s in sents:
        n = len(s['forms'])
        with torch.no_grad():
            ids, mask, first, _, _, kept = collate([s], tok, stoi['leaf'], stoi['tree'], device)
            with torch.autocast('cuda', dtype=torch.float16, enabled=device.type == 'cuda'):
                logits = dict(zip(('leaf', 'tree'), model(ids, mask, first)))
        top = {}
        for kind in ('leaf', 'tree'):
            p = logits[kind].float().softmax(-1).topk(args.k, -1)
            top[kind] = [[(itos[kind][i], math.log(max(q, 1e-12)), q) for q, i in zip(ps, idx)]
                         for ps, idx in zip(p.values.tolist(), p.indices.tolist())]
            top[kind] += [[(UNK, 0.0, 1.0)]] * (n - kept[0])
        tops.append(top)
    tag_secs = time.time() - t0

    # phase 2: replay and repair (CPU), one sentence per task
    global _WORK
    lexicon = Lexicon(g, os.path.dirname(args.grammar)) if args.entries else None
    _WORK = (g, sents, tops, tokens, args, lexicon)
    t1 = time.time()
    if args.workers > 1:
        import multiprocessing
        with multiprocessing.get_context('fork').Pool(args.workers) as pool:
            results = pool.map(search, range(len(sents)), chunksize=4)
    else:
        results = [search(i) for i in range(len(sents))]
    search_secs = time.time() - t1

    stats = collections.Counter()
    by_len = collections.defaultdict(collections.Counter)
    out_pred = open(args.pred_out, 'w', encoding='utf-8') if args.pred_out else None
    for s, (outcome, leaf, tree, n_replays, first_right, ok) in zip(sents, results):
        band = min(len(s['forms']) // 10 * 10, 60)
        stats['sentences'] += 1
        stats['first choice right'] += first_right
        if outcome.startswith('accepted'):
            stats['accepted'] += 1
            stats['accepted and right'] += ok
        stats[outcome] += 1
        by_len[band][outcome] += 1
        stats['replays'] += n_replays
        if out_pred:
            out_pred.write(json.dumps({'id': s['id'], 'forms': s['forms'], 'leaf': leaf, 'tree': tree,
                                       'outcome': outcome}, ensure_ascii=False) + '\n')
    result = {'args': {k: v for k, v in vars(args).items() if k in ('split', 'k', 'min_prob', 'budget', 'fanout', 'limit', 'cache', 'entries')},
              'stats': dict(stats),
              'right_among_accepted': stats['accepted and right'] / stats['accepted'] if stats['accepted'] else None,
              'by_length': {str(b): dict(by_len[b]) for b in sorted(by_len)},
              'replays_per_sentence': stats['replays'] / stats['sentences'],
              'tagging_seconds': tag_secs, 'repair_seconds': search_secs, 'workers': args.workers,
              'sentences_per_second_repair_stage': stats['sentences'] / search_secs}
    if out_pred:
        out_pred.close()
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
