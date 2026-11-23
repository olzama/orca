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
from orca.encoding import Leaf, decode, n_leaves  # noqa: E402
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


def head_index(label):
    """Head daughter of an ERG-style binary rule, read off its name (sb-hd_mc_c: 1)."""
    parts = label.lower().split('_')[0].split('-')
    for i, x in enumerate(parts):
        if x.startswith('hd'):
            return min(i, 1)
    return 0


def top_tokens(tree, leaf_labels, levels=2):
    """Token positions that shape the top of the tree: the split points of the
    binary nodes in its top `levels` levels and all along the head path, and the
    head word itself. Used when the whole sentence fails at the root, where
    failing_tokens gives no locality."""
    picked = set()

    def walk(node, start, lvl, on_head):
        if isinstance(node, Leaf):
            if on_head:
                picked.add(start)
            return
        kids = node.children
        if len(kids) == 1:
            walk(kids[0], start, lvl, on_head)
            return
        left = n_leaves(kids[0])
        if lvl <= levels or on_head:
            picked.add(start + left - 1)            # the token whose tree label makes this node
        h = head_index(node.label)
        walk(kids[0], start, lvl + 1, on_head and h == 0)
        walk(kids[1], start + left, lvl + 1, on_head and h == 1)

    walk(tree, 0, 0, True)
    out, li = [], -1
    for j, l in enumerate(leaf_labels):
        if not l.startswith(CONT):
            li += 1
        if li in picked:
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
    _CURRENT[0] = s['id']
    if hasattr(g, 'reset'):
        g.reset()                       # compiled core: new arena per sentence
    intern = {}                         # one shared object per distinct subtree, for this sentence's replays
    g.node_intern = intern

    def replay(leaf, tree):
        """None if accepted, else the token positions to reconsider."""
        mark = g.u.mark()
        try:
            t = decode(to_leaves(forms, leaf, tree), intern)
        except Exception:
            return list(range(n))
        try:
            if lexicon is not None:
                fs, resolved = replay_with_entries(g, lexicon, t, toks, cache=cache)
            else:
                fs, _ = g.replay_tree(t, toks, cache=cache)
                resolved = t
            if args.kbest > 1:
                accepted_info.append((fs, resolved))
            return None
        except ReplayFailure as e:
            span = failing_tokens(t, e.where, leaf) or list(range(n))
            if root_focus and len(span) == n:
                span = top_tokens(t, leaf) or span
            return span
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

    # Each entry carries the failing span of the state it was expanded from. With
    # args.commit (long sentences): when a change makes the failure move to tokens
    # disjoint from that span, the change fixed its region and another error is now
    # visible. The search then keeps that state as its new base and looks only for
    # fixes of the new region, instead of crossing every fix of the first region with
    # every fix of the second; the earlier frontier is kept on a stack to fall back to.
    commit = getattr(args, 'commit', False) and n >= getattr(args, 'commit_min', 0)
    root_focus = getattr(args, 'root_focus', False) and n >= getattr(args, 'commit_min', 0)
    heap, seen, counter, n_replays = [(0.0, 0, (), None)], {()}, 1, 0
    stack, commits = [], 0
    accepted, first_right = None, None
    accepted_info, kbest = [], []
    # mode 'local' (default): the search above; 'global': whole label sequences in order of total tagger
    # cost; 'hybrid': local first, then global for the remaining budget. distinct: count readings (MRSs).
    mode = getattr(args, 'search', 'local') or 'local'
    distinct = getattr(args, 'distinct', False)
    tried, readings = set(), {}

    def keep(fs, resolved, leaf, tree, cost):
        """Add an accepted derivation to kbest; with `distinct`, only if its reading is new."""
        if distinct and not new_reading(mrs_key(fs), readings):
            return
        kbest.append(candidate(fs, resolved, leaf, tree, cost))

    while mode != 'global' and n_replays < args.budget:
        if not heap:
            if not stack:
                break
            heap = stack.pop()
            continue
        cost, _, state, parent_span = heapq.heappop(heap)
        leaf, tree = assignment(state)
        if first_right is None:
            first_right = right(leaf, tree)
        n_replays += 1
        tried.add(state)
        span = replay(leaf, tree)
        if getattr(args, 'trace', None) is not None:
            args.trace.append((len(state), None if span is None else (min(span), max(span), len(span)), round(cost, 2)))
        if (commit and span is not None and accepted is None and parent_span is not None
                and not parent_span.intersection(span)):
            stack.append(heap)
            heap = []
            commits += 1
        if span is None:
            if accepted is None:
                accepted = (leaf, tree, state)
            if args.kbest <= 1:
                break
            fs, resolved = accepted_info.pop()
            if distinct:
                keep(fs, resolved, leaf, tree, cost)
            else:
                kbest.append(candidate(fs, resolved, leaf, tree, cost))
            if len(kbest) >= args.kbest:
                break
            span = list(range(n))           # look for other readings anywhere
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
                    heapq.heappush(heap, (cost + top[kind][j][0][1] - logp, counter, new, frozenset(span)))
                    counter += 1
    if mode in ('global', 'hybrid') and n_replays < args.budget and (
            accepted is None or (args.kbest > 1 and len(kbest) < args.kbest)):
        # Lazy enumeration of whole assignments in order of total cost (the product of the per-token
        # sorted label lists, as in k-best enumeration over a CFG's fringes): each assignment has one
        # parent, the assignment with its last changed position one rank lower, so the order is exact.
        gmin = getattr(args, 'global_min_prob', 0.0)
        pos = [(kind, j) for j in range(n) for kind in ('leaf', 'tree') if not (kind == 'tree' and j == n - 1)]
        avail = [1 + sum(1 for q in top[kind][j][1:] if q[2] >= gmin) for kind, j in pos]
        delta = lambda i, r: top[pos[i][0]][pos[i][1]][0][1] - top[pos[i][0]][pos[i][1]][r][1]
        heap2, cnt = [(0.0, 0, ())], 1
        while heap2 and n_replays < args.budget:
            cost, _, vec = heapq.heappop(heap2)
            last = vec[-1][0] if vec else -1
            if vec and vec[-1][1] + 1 < avail[last]:
                i, r = vec[-1]
                heapq.heappush(heap2, (cost - delta(i, r) + delta(i, r + 1), cnt, vec[:-1] + ((i, r + 1),)))
                cnt += 1
            for q in range(last + 1, len(pos)):
                if avail[q] > 1:
                    heapq.heappush(heap2, (cost + delta(q, 1), cnt, vec + ((q, 1),)))
                    cnt += 1
            state = tuple(sorted((pos[i][0], pos[i][1], r) for i, r in vec))
            if state in tried:
                continue
            tried.add(state)
            leaf, tree = assignment(state)
            if first_right is None:
                first_right = right(leaf, tree)
            n_replays += 1
            if replay(leaf, tree) is None:
                if accepted is None:
                    accepted = (leaf, tree, state)
                if args.kbest <= 1:
                    break
                fs, resolved = accepted_info.pop()
                keep(fs, resolved, leaf, tree, cost)
                if len(kbest) >= args.kbest:
                    break
    if accepted is None:
        outcome = 'rejected, budget used' if n_replays >= args.budget else 'rejected, nothing left to try'
        leaf, tree = assignment(())
        return outcome, leaf, tree, n_replays, first_right, False, kbest
    leaf, tree, state = accepted
    ok = right(leaf, tree)
    outcome = ('accepted at first try' if not state else 'accepted after repair') + (', right' if ok else ', wrong')
    return outcome, leaf, tree, n_replays, first_right, ok, kbest


def mrs_key(fs):
    """The MRS of an accepted derivation, normalized as comparisons do, for telling readings apart."""
    g = _WORK[0]
    from orca.tfs.fast import extract as fast_extract
    from compare_mrs import normalized, to_pydelphin
    try:
        return normalized(to_pydelphin(fast_extract(g, fs) if hasattr(g, 'reset') else extract_py(g, fs)))
    except Exception:
        return None


def new_reading(m, readings):
    """True (and remember m) if m is not isomorphic to an MRS seen before for this sentence."""
    if m is None:
        return True
    from delphin import mrs as M
    sig = tuple(sorted(str(ep.predicate) for ep in m.rels))
    for other in readings.get(sig, ()):
        if M.is_isomorphic(m, other, properties=False):
            return False
    readings.setdefault(sig, []).append(m)
    return True


def candidate(fs, resolved, leaf, tree, cost):
    """An accepted derivation, with its MRS compared to gold if gold is known."""
    g, sents, tops, tokens, args, lexicon = _WORK
    out = {'cost': round(cost, 4), 'leaf': leaf, 'tree': tree,
           'entries': [l.entry for l in leaves_of(resolved)]}
    if GOLD_MRS:
        from delphin import mrs as M
        from orca.tfs.fast import extract as fast_extract
        from compare_mrs import normalized, to_pydelphin
        try:
            # normalized like the gold (GOLD_MRS holds normalized MRSs): without it, ICONS on our side never match
            m = normalized(to_pydelphin(fast_extract(g, fs) if hasattr(g, 'reset') else extract_py(g, fs)))
            out['same_mrs'] = M.is_isomorphic(m, GOLD_MRS[_CURRENT[0]], properties=False)
        except Exception:
            out['same_mrs'] = False
    return out


def extract_py(g, fs):
    from orca.tfs.mrs import extract
    return extract(g, fs)


def leaves_of(t):
    if isinstance(t, Leaf):
        return [t]
    return [x for c in t.children for x in leaves_of(c)]


GOLD_MRS = {}
_CURRENT = [None]


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
    ap.add_argument('--kbest', type=int, default=1, help='collect up to this many accepted derivations')
    ap.add_argument('--gold-mrs', action='store_true', help='compare each candidate MRS with gold')
    ap.add_argument('--fast', action='store_true', help='replay with the compiled core')
    ap.add_argument('--warmup', type=int, default=300, help='sentences repaired once before timing (with --fast)')
    ap.add_argument('--entries', action='store_true',
                    help='replay with lexical entries found in the lexicon')
    ap.add_argument('--no-cache', dest='cache', action='store_false',
                    help='rebuild every subtree on every replay')
    ap.add_argument('--root-focus', action='store_true', help='a failure at the root: search the top of the tree and the head path first')
    ap.add_argument('--commit', action='store_true', help='long sentences: keep a fix once the failure moves elsewhere')
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
    if args.fast:
        from orca.tfs.fast import FastGrammar
        g = FastGrammar(g)
    _WORK = (g, sents, tops, tokens, args, lexicon)
    t1 = time.time()
    if args.gold_mrs:
        import glob as _glob
        from delphin import tsdb as _tsdb
        from delphin.codecs import simplemrs as _smrs
        from compare_mrs import normalized as _norm
        for prof in sorted(_glob.glob(os.path.join(args.profiles, '*'))):
            if not os.path.exists(os.path.join(prof, 'relations')):
                continue
            names = [f.name for f in _tsdb.read_schema(prof)['result']]
            with _tsdb.open(prof, 'result') as rows:
                for line in rows:
                    rec = _tsdb.split(line)
                    if rec[names.index('derivation')]:
                        GOLD_MRS[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = _norm(
                            _smrs.decode(rec[names.index('mrs')]))
    if args.fast:                         # build templates once, before the workers fork
        for name, status in g.g.status.items():
            if status in ('rule', 'lex-rule'):
                g.instance(name)
        for i in range(min(len(sents), args.warmup)):
            search(i)
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
    for s, (outcome, leaf, tree, n_replays, first_right, ok, kbest) in zip(sents, results):
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
            rec = {'id': s['id'], 'forms': s['forms'], 'leaf': leaf, 'tree': tree, 'outcome': outcome}
            if args.kbest > 1:
                rec['candidates'] = kbest
            out_pred.write(json.dumps(rec, ensure_ascii=False) + '\n')
        if args.kbest > 1 and GOLD_MRS:
            stats['candidates'] += len(kbest)
            stats['gold MRS among k best'] += any(c.get('same_mrs') for c in kbest)
            stats['gold MRS first among k best'] += bool(kbest) and bool(kbest[0].get('same_mrs'))
    result = {'args': {k: v for k, v in vars(args).items() if k in ('split', 'k', 'min_prob', 'budget', 'fanout', 'limit', 'cache', 'entries', 'fast', 'kbest')},
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
