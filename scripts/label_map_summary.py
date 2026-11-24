#!/usr/bin/env python3
"""Summary table for O91 step 3: repair_bench runs of the same cached tagger output under
grammar versions with and without label mapping / word fallback. Per run: first guess
accepted, any analysis, replays per sentence, and MRS agreement with a reference run
(ERG 2025, the tagger's own grammar) where both have an analysis (as grammar_drift_compare.py:
isomorphic without properties).

Usage:
    label_map_summary.py --ref analysis/grammar-drift/dev-2025.json NAME=RUN.json ... --out SUMMARY.json
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True)
    ap.add_argument('runs', nargs='+')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    ref = json.load(open(a.ref))['records']
    out = {}
    for spec in a.runs:
        name, path = spec.split('=', 1)
        run = json.load(open(path))
        recs = run['records']
        first = sum(1 for r in recs.values() if r.get('outcome') == 'accepted at first try')
        anyan = sum(1 for r in recs.values() if r.get('mrs'))
        both = same = 0
        for sid, r in recs.items():
            q = ref.get(sid, {})
            if r.get('mrs') and q.get('mrs'):
                both += 1
                try:
                    same += M.is_isomorphic(normalized(simplemrs.decode(r['mrs'])), normalized(simplemrs.decode(q['mrs'])), properties=False)
                except Exception:
                    pass
        out[name] = {'file': path, 'sentences': len(recs), 'first guess accepted': first, 'any analysis': anyan,
                     'replays': run.get('replays'), 'replays per sentence': run.get('replays', 0) / max(1, len(recs)),
                     'both analyzed': both, 'same MRS as the reference': same, 'exact (gold)': run.get('exact'),
                     'repair seconds': run.get('repair seconds')}
    json.dump({'reference': a.ref, 'runs': out}, open(a.out, 'w'), indent=1)
    for k, v in out.items():
        print(k, {x: (round(y, 1) if isinstance(y, float) else y) for x, y in v.items() if x != 'file'})


if __name__ == '__main__':
    main()
