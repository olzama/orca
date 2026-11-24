#!/usr/bin/env python3
"""Several readings in chart mode (O97), measured on Redwoods dev: ACE restricted to the tagger's lexical
entries (as supertag_ace.py / orca_parse --mode chart) asked for its n best parses; parses with the same MRS
form one reading, scored by its best parse; reports gold among the top 1, 2, 3, 5 distinct readings and the
set size and gold-in-set for the demo's margin rule. Uses the saved tagger output, no GPU.

Usage:
    chart_readings_eval.py --out analysis/readings/dev-chart.json [--n 20] [--workers 2] [--margin 1.25]
"""
import argparse
import json
import math
import os
import pickle
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
ROOT = os.path.join(HERE, '..')

import supertag_ace as S  # noqa: E402


def one(args):
    sid, item, k, min_prob, n, timeout = args
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    import readings_eval as RE
    allowed, disabled, _ = S.allowed_and_disabled(item, k, min_prob)
    t0 = time.time()
    try:
        parses = S.run_restricted_nbest(item['text'], disabled, n, timeout)
    except Exception:
        parses = []
    secs = time.time() - t0
    items = []
    for sc, mrs_s, _ in parses:
        try:
            items.append((sc, normalized(simplemrs.decode(mrs_s)), None))
        except Exception:
            pass
    same = lambda x, y: bool(M.is_isomorphic(x, y, properties=False))
    rds = RE.group_readings(items, same)
    probs = RE.softmax_mass(rds)
    g = S._GOLD.get(sid)
    gold = [bool(g is not None and same(rd['mrs'], g)) for rd in rds]
    return sid, {'parses': len(parses), 'scores': [rd['score'] for rd in rds], 'probs': probs, 'gold': gold, 'seconds': secs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl'))
    ap.add_argument('--gold', default=os.path.join(ROOT, 'data/profiles-2025/dev'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--min-prob', type=float, default=0.001)
    ap.add_argument('--n', type=int, default=20)
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--margin', type=float, default=1.25)
    ap.add_argument('--readings', type=int, default=5)
    a = ap.parse_args()
    import readings_eval as RE
    items = pickle.load(open(a.cache, 'rb'))['items']
    jobs = [(i, items[i], a.k, a.min_prob, a.n, a.timeout) for i in items if items[i].get('top')]
    res = {}
    t0 = time.time()
    with ProcessPoolExecutor(a.workers, initializer=S._init, initargs=(a.gold,)) as ex:
        for sid, r in ex.map(one, jobs, chunksize=4):
            res[sid] = r
    N = len(items)
    topk = {str(k): sum(1 for r in res.values() if any(r['gold'][:k])) for k in (1, 2, 3, 5)}
    sel = [RE.select(r['scores'], k=a.readings, margin=a.margin) for r in res.values()]
    in_set = sum(1 for r, s in zip(res.values(), sel) if any(r['gold'][i] for i in s))
    sizes = [len(s) for s in sel if s]
    summary = {'sentences': N, 'parsed': sum(1 for r in res.values() if r['parses']), 'n best asked': a.n,
               'distinct readings per parsed sentence': sum(len(r['scores']) for r in res.values() if r['scores']) / max(1, sum(1 for r in res.values() if r['scores'])),
               'gold among top k distinct readings': topk,
               f'margin {a.margin}, at most {a.readings}': {'gold in set': in_set, 'mean set size': sum(sizes) / max(1, len(sizes)),
                                                          'more than one': sum(1 for x in sizes if x > 1)},
               'ace seconds per sentence': sum(r['seconds'] for r in res.values()) / max(1, len(res)), 'wall seconds': time.time() - t0}
    json.dump({'summary': summary, 'records': res}, open(a.out, 'w'))
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
