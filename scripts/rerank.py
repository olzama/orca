#!/usr/bin/env python3
"""Rerank the k best accepted derivations of each sentence with the ERG's
ranking model, alone or combined with the tagger's cost, and report how
often the chosen derivation has the gold MRS.

Usage:
    rerank.py --grammar ERG/english.tdl --kbest MODEL/dev-kbest10.jsonl --out FILE
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from eval_trees import to_leaves  # noqa: E402
from orca.encoding import Leaf, Node, decode  # noqa: E402
from orca.maxent import MaxEnt  # noqa: E402
from orca.tfs.grammar import Grammar  # noqa: E402
from orca.tfs.lexicon import Lexicon  # noqa: E402

BANDS = ((0, 10, 'under 10'), (10, 20, '10-19'), (20, 30, '20-29'), (30, 10 ** 6, '30 and over'))


def with_entries(tree, entries):
    it = iter(entries)

    def walk(t):
        if isinstance(t, Leaf):
            return Leaf(next(it), t.forms)
        return Node(t.label, tuple(walk(c) for c in t.children))

    return walk(tree)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--kbest', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--weights', default='0,0.5,1,2', help='weights of the tagger cost to report')
    ap.add_argument('--pred-out', help='write the derivation chosen with the first weight')
    args = ap.parse_args()
    gdir = os.path.dirname(args.grammar)
    me = MaxEnt(os.path.join(gdir, 'redwoods.mem'))
    g = Grammar(args.grammar)
    lx = Lexicon(g, gdir)
    generic = lambda e: g.status.get(e) == 'generic-lex-entry'
    lams = [float(x) for x in args.weights.split(',')]
    st = collections.Counter()
    by = {lam: collections.Counter() for lam in lams}
    n_by = collections.Counter()
    out = open(args.pred_out, 'w', encoding='utf-8') if args.pred_out else None
    with open(args.kbest, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            st['sentences'] += 1
            band = next(n for lo, hi, n in BANDS if lo <= len(r['forms']) < hi)
            n_by[band] += 1
            cands = r.get('candidates') or []
            if not cands:
                continue
            st['with candidates'] += 1
            st['first candidate has gold MRS'] += bool(cands[0].get('same_mrs'))
            st['oracle'] += any(c.get('same_mrs') for c in cands)
            scored = []
            for c in cands:
                tree = with_entries(decode(to_leaves(r['forms'], c['leaf'], c['tree'])), c['entries'])
                scored.append((me.score(tree, lx.type_of.get, generic), c['cost'], bool(c.get('same_mrs'))))
            if out:
                i = max(range(len(scored)), key=lambda j: scored[j][0] - lams[0] * scored[j][1])
                c = cands[i]
                out.write(json.dumps({'id': r['id'], 'forms': r['forms'], 'leaf': c['leaf'], 'tree': c['tree'],
                                      'entries': c['entries'], 'rank_in_kbest': i,
                                      'same_mrs': bool(c.get('same_mrs'))}, ensure_ascii=False) + '\n')
            for lam in lams:
                best = max(scored, key=lambda x: x[0] - lam * x[1])
                st[f'reranked, cost weight {lam}'] += best[2]
                by[lam][band] += best[2]
    n = st['sentences']
    result = {'stats': dict(st),
              'share_of_all_sentences': {k: round(v / n, 4) for k, v in st.items() if k != 'sentences'},
              'by_length': {f'cost weight {lam}': {b: [by[lam][b], n_by[b]] for _, _, b in BANDS} for lam in lams}}
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
