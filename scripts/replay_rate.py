#!/usr/bin/env python3
"""Share of sentences whose first accepted derivation comes within k replays.

For the comparison with Matsuzaki et al. 2007 (Enju: share of sentences whose
k-th CFG-filtered sequence is the first the HPSG accepts). Reads a repair_bench.py
or orca_parse.py run whose per-sentence records carry 'replays to first accepted'
(None when nothing was accepted).

Usage: replay_rate.py RUN.json OUT.json
"""
import json
import sys

KS = (1, 2, 5, 10, 20, 50, 111, 600)


def main():
    run, out = sys.argv[1], sys.argv[2]
    d = json.load(open(run))
    recs = d['records']
    recs = list(recs.values()) if isinstance(recs, dict) else recs
    vals = [r.get('replays to first accepted') for r in recs]
    if any('replays to first accepted' not in r for r in recs):
        sys.exit('run lacks "replays to first accepted": re-run with the current repair.py')
    n = len(vals)
    acc = sorted(v for v in vals if v is not None)
    res = {'run': run, 'sentences': n, 'accepted': len(acc),
           'within k replays': {str(k): sum(1 for v in acc if v <= k) for k in KS},
           'median replays to first accepted, of accepted': acc[len(acc) // 2] if acc else None}
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
