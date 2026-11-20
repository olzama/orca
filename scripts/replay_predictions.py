#!/usr/bin/env python3
"""Replay predicted derivations with the grammar.

Reads label sequences in the tagger's prediction format, decodes each to a
tree, and replays it. Reports how many predicted derivations the grammar
accepts and how acceptance relates to being right. With --gold-as-pred the
gold labels are replayed instead, which tests the pipeline itself.

Leaves are replayed at the level of the lexical type, not the lexical entry,
and tokens come from the gold profiles (tokenization is not predicted yet).

Usage:
    replay_predictions.py --grammar ERG/english.tdl --profiles SPLIT_DIR
                          --gold DATA/dev.jsonl [--pred MODEL/dev-pred.jsonl] --out FILE
"""
import argparse
import collections
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from delphin import derivation, tsdb  # noqa: E402

from eval_trees import to_leaves  # noqa: E402
from llm_label import read  # noqa: E402
from orca.encoding import decode  # noqa: E402
from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402


def gold_tokens(split_dir):
    out = {}
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        i_der, i_pid = names.index('derivation'), names.index('parse-id')
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[i_der]:
                    d = derivation.from_string(rec[i_der])
                    out[f'{os.path.basename(prof)}/{rec[i_pid]}'] = [
                        tok.tfs for term in d.terminals() for tok in (term.tokens or [])]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--gold', required=True)
    ap.add_argument('--pred')
    ap.add_argument('--out', required=True)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    gold = {s['id']: s for s in read(args.gold)}
    if args.pred:
        with open(args.pred, encoding='utf-8') as f:
            preds = [json.loads(line) for line in f]
    else:
        preds = list(gold.values())
    if args.limit:
        preds = preds[:args.limit]
    tokens = gold_tokens(args.profiles)
    g = Grammar(args.grammar)

    table = collections.Counter()          # (accepted, correct) -> sentences
    by_len = collections.defaultdict(collections.Counter)
    causes, examples = collections.Counter(), {}
    t0 = time.time()
    for p in preds:
        s = gold[p['id']]
        correct = p['leaf'] == s['leaf'] and p['tree'][:-1] == s['tree'][:-1]
        mark = g.u.mark()
        try:
            tree = decode(to_leaves(p['forms'], p['leaf'], p['tree']))
            g.replay_tree(tree, tokens[p['id']])
            accepted = True
        except ReplayFailure as e:
            accepted = False
            key = str(e.cause)
            if 'missing' in key:
                key = 'label not usable here: ' + key
            causes[key] += 1
            examples.setdefault(key, f"{p['id']} at {e.where}")
        del g.u.trail[mark:]
        table[(accepted, correct)] += 1
        band = min(len(p['forms']) // 10 * 10, 60)
        by_len[band][(accepted, correct)] += 1
    secs = time.time() - t0
    n = len(preds)
    acc = table[(True, True)] + table[(True, False)]
    rej = n - acc

    def cells(c):
        return {'accepted and right': c[(True, True)], 'accepted and wrong': c[(True, False)],
                'rejected and right': c[(False, True)], 'rejected and wrong': c[(False, False)]}

    result = {
        'sentences': n, 'accepted': acc, 'rejected': rej, **cells(table),
        'right_among_accepted': table[(True, True)] / acc if acc else None,
        'right_among_rejected': table[(False, True)] / rej if rej else None,
        'by_length': {str(b): cells(by_len[b]) for b in sorted(by_len)},
        'sentences_per_second': n / secs,
        'failure_causes': [[k, c, examples[k]] for k, c in causes.most_common(30)],
    }
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
