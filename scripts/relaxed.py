#!/usr/bin/env python3
"""Partial analyses for sentences that get no full analysis (prototype).

For each sentence whose repair ends with no accepted derivation, from the cached
tagger output (repair_bench.py prepare), take the tagger's first guess and try:

  1. robust roots: the same derivation under each of the ERG's root conditions
     (informal, fragment and robust roots, in ACE's order); the first that the
     grammar accepts gives a full analysis;
  2. maximal fragments: otherwise, the largest subtrees of the first guess that
     replay, left to right (a node that fails is replaced by its daughters'
     fragments), each with its own MRS.

Nothing here changes the parser: it only reads the cache and a finished run, so
full analyses are untouched (the "flag" is running this script at all).

Partial credit against gold is EDM-style (scripts/edm.py): names, arguments and
properties over character spans, micro-averaged; a fragment analysis contributes
the union of its fragments' tuples; tops are left out (fragments have no single
top).

Usage:
    relaxed.py --cache data/bench/dev-debertav3large-tags.pkl \\
               --run analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-current.json \\
               --profiles data/profiles-2025/dev --out analysis/relaxed/dev.json
"""
import argparse
import collections
import json
import os
import pickle
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from fragments import ROOTS, ROOT_RE  # noqa: E402,F401  (the logic lives in fragments.py)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', required=True)
    ap.add_argument('--run', required=True, help='a finished orca_parse --eval run (which sentences got no analysis)')
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--tagger', default='data/models/tagger-2025bothsurf-debertav3large')
    ap.add_argument('--out', required=True)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()

    import torch
    torch.set_num_threads(a.threads)
    from delphin.codecs import simplemrs
    from edm import gold_mrs, prf, to_eds, tuples
    from fragments import partial_analysis
    from orca_parse import Parser

    data = pickle.load(open(a.cache, 'rb'))['items']
    run = json.load(open(a.run))
    failed = [r['id'] for r in run['records'] if str(r['outcome']).startswith('rejected') or r['outcome'] == 'no tokens']
    failed = failed[:a.limit]
    gold = gold_mrs(a.profiles)
    p = Parser(tagger=a.tagger, device='cpu')
    fg, lx = p.fg, p.lx

    recs, c = {}, collections.Counter()
    tot = {'robust or fragments': [0, 0, 0], 'nothing': [0, 0, 0]}
    tot_all = {'robust or fragments': [0, 0, 0], 'nothing': [0, 0, 0]}
    words_total = words_covered = words_multi = 0
    t0 = time.time()
    for sid in failed:
        it = data[sid]
        path, forms, top = it['path'], it['forms'], it['top']
        rec = {'text': it['text']}
        if not forms:
            rec['result'] = 'no tokens'
            recs[sid] = rec
            c['no tokens'] += 1
            continue
        rforms = [q[0] for q in path] if p.normalized_lookup else forms
        toks = [q[1] for q in path]
        n = len(forms)
        leaf = [top['leaf'][j][0][0] for j in range(n)]
        tree = [top['tree'][j][0][0] for j in range(n)]
        pa = partial_analysis(fg, lx, rforms, leaf, tree, toks)
        if pa['result'] == 'undecodable first guess':
            rec['result'] = pa['result']
            recs[sid] = rec
            c[pa['result']] += 1
            continue
        rec['root guessed'] = pa['root guessed']
        frags = [(s, e, simplemrs.encode(m)) for s, e, _, m in pa['pieces']]
        if pa['result'] == 'robust root':
            rec['result'] = 'robust root'
            rec['root'] = pa['root']
            rec['mrs'] = [frags[0][2]]
            covered = multi = n
            c['robust root'] += 1
        else:
            rec['result'] = pa['result']
            rec['fragments'] = [{'from': s, 'to': e, 'words': ' '.join(forms[s:e]), 'mrs': m} for s, e, m in frags]
            rec['mrs'] = [m for _, _, m in frags]
            covered = sum(e - s for s, e, _ in frags)
            multi = sum(e - s for s, e, _ in frags if e - s > 1)
            c['fragments' if frags else 'nothing'] += 1
            c['fragments, count'] += len(frags)
        words_total += n
        words_covered += covered
        words_multi += multi
        rec['words'], rec['covered'], rec['in multi-word fragments'] = n, covered, multi
        # partial credit against gold
        if sid in gold:
            g = tuples(to_eds(gold[sid]))
            s = [set(), set(), set()]
            for m in rec['mrs']:
                try:
                    tt = tuples(to_eds(m))
                except Exception:
                    continue
                for i in range(3):
                    s[i] |= tt[i]
            na_g, na_s = g[0] | g[1], s[0] | s[1]
            all_g, all_s = g[0] | g[1] | g[2], s[0] | s[1] | s[2]
            for d, gg, ss in ((tot, na_g, na_s), (tot_all, all_g, all_s)):
                d['robust or fragments'][0] += len(gg)
                d['robust or fragments'][1] += len(ss)
                d['robust or fragments'][2] += len(gg & ss)
                d['nothing'][0] += len(gg)
            c['with gold'] += 1
        recs[sid] = rec
    res = {'sentences': len(failed), 'counts': dict(c), 'seconds': round(time.time() - t0, 1),
           'words': words_total, 'words covered': words_covered, 'words in multi-word fragments': words_multi,
           'EDM_NA (names, arguments)': {k: prf(*v) for k, v in tot.items()},
           'EDM without tops (names, arguments, properties)': {k: prf(*v) for k, v in tot_all.items()},
           'records': recs}
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in res.items() if k != 'records'}, indent=1))


if __name__ == '__main__':
    main()
