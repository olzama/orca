#!/usr/bin/env python3
"""Orca with a fallback to ACE restricted to the tagger's lexical choices
(supertag_ace.py), optionally cascading to full ACE when the restricted parse
finds nothing. Same routing as ace_fallback.py: sentences without an Orca
analysis always go to the fallback; the rest by a cross-validated score of how
likely Orca is wrong.

Usage:
    supertag_combine.py --restricted analysis/supertag-ace/dev-all.json --out OUT.json
"""
import argparse
import json
import os
import pickle
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from ace_fallback import ACE_EVAL, buckets, features, logreg  # noqa: E402

ACE_DEV_MEAN = (1276.6 + 437.8 + 301.5) / 2062     # full ACE, our comparison runs (as in ace_fallback.py)


def main():
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument('--restricted', default=os.path.join(ROOT, 'analysis/supertag-ace/dev-all.json'))
    ap.add_argument('--cands', default=os.path.join(ROOT, 'analysis/ace-fallback/dev-cands-current.jsonl'))
    ap.add_argument('--time', default=os.path.join(ROOT, 'analysis/ace-fallback/time-noanalysis.json'))
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    run, b = buckets()
    rs = json.load(open(a.restricted))['records']
    ace = {r['id']: str(r['same MRS']) == 'True' for r in json.load(open(ACE_EVAL))['records']}
    tags = pickle.load(open(os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl'), 'rb'))['items']
    cands = {json.loads(l)['id']: json.loads(l) for l in open(a.cands)}
    t = json.load(open(a.time))
    ace_none = {k: v['seconds'] for k, v in t['per_sentence'].items()}
    recs = {x['id']: x for x in run['records']}
    ids = [i for i in b if i in tags and i in rs]
    X = np.array([features(recs[i], cands.get(i), tags[i]) for i in ids])
    orca_ok = np.array([b[i] == 'right' for i in ids])
    y = (~orca_ok).astype(int)
    random.seed(1)
    order = list(range(len(ids)))
    random.shuffle(order)
    score = np.zeros(len(ids))
    for k in range(5):
        test = order[k::5]
        ts = set(test)
        train = [j for j in order if j not in ts]
        score[test] = logreg(X[train], y[train], X[test])
    none = [b[i] == 'none' for i in ids]
    run_secs = len(ids) / run['sentences per second']
    rest = sorted([j for j in range(len(ids)) if not none[j]], key=lambda j: -score[j])

    def outcome(j, mode):
        """(right, seconds) for a routed sentence."""
        r = rs[ids[j]]
        right, secs = bool(r['same MRS']), r['ace seconds'] + r['prep seconds']
        if mode == 'cascade' and not r['parsed']:
            right = ace.get(ids[j], False)
            secs += ace_none.get(ids[j], ACE_DEV_MEAN)
        return right, secs

    curves = {}
    for mode in ('restricted', 'cascade'):
        curve = []
        for extra in (0, 100, 200, 300, 400, 600, 800, 1000, len(rest)):
            send = {j for j in range(len(ids)) if none[j]} | set(rest[:extra])
            right, secs = 0, run_secs
            for j in range(len(ids)):
                if j in send:
                    ok, s = outcome(j, mode)
                    right += ok
                    secs += s
                else:
                    right += orca_ok[j]
            curve.append({'sent': len(send), 'exact': int(right), 'sentences per second': round(len(ids) / secs, 2)})
        curves[mode] = curve
    alone = {'exact': sum(bool(rs[i]['same MRS']) for i in ids), 'parsed': sum(rs[i]['parsed'] for i in ids),
             'sentences per second': round(len(ids) / sum(rs[i]['ace seconds'] + rs[i]['prep seconds'] for i in ids), 2)}
    out = {'sentences': len(ids), 'orca exact': int(orca_ok.sum()), 'full ACE exact': sum(ace.get(i, False) for i in ids),
           'restricted ACE alone (one process)': alone, 'curves': curves,
           'note': 'restricted ACE times measured per sentence; full ACE in the cascade: measured on no-analysis sentences, dev mean elsewhere'}
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
