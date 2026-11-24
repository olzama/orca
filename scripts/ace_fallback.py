#!/usr/bin/env python3
"""Hybrid Orca + ACE: how much exact meaning and speed if ACE parses the
sentences Orca routes to it.

  time:  ACE wall time per sentence on a set of dev sentences (one process).
  route: cross-validated routing of sentences to ACE from Orca's own signals;
         the curve of sentences sent vs exact meaning vs speed.

Usage:
    ace_fallback.py time --ids no-analysis --out analysis/ace-fallback/time-noanalysis.json
    ace_fallback.py route --cands CANDS.jsonl --out analysis/ace-fallback/route.json
"""
import argparse
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.join(HERE, '..')
RUN = os.path.join(ROOT, 'analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-current.json')
ACE_EVAL = os.path.join(ROOT, 'analysis/mrs/dev-ace-final-as-eval.json')
ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
DAT = os.path.join(ROOT, 'data/ace/erg-2025.dat')


def buckets(path=None):
    run = json.load(open(path or RUN))
    out = {}
    for x in run['records']:
        out[x['id']] = ('right' if x['same MRS'] else 'none' if not x['accepted']
                        else 'found' if x['gold among accepted'] else 'wrong')
    return run, out


def cmd_time(a):
    from check_raw_tokens import raw_inputs
    from delphin import ace as A
    raw = raw_inputs(os.path.join(ROOT, 'data/profiles-2025/dev'))
    run, b = buckets()
    ids = [i for i, k in b.items() if a.ids == 'all' or k == {'no-analysis': 'none'}.get(a.ids, a.ids)]
    done = {}
    if os.path.exists(a.out):
        done = json.load(open(a.out)).get('per_sentence', {})
    args = ['-1', f'--timeout={a.timeout}', f'--max-chart-megabytes={a.mb}', f'--max-unpack-megabytes={a.mb}']
    for n, i in enumerate(ids):
        if i in done:
            continue
        t = time.perf_counter()
        try:
            res = A.parse(DAT, raw[i], executable=ACE, cmdargs=list(args), stderr=open(os.devnull, 'w')).results()
            ok = bool(res)
        except Exception as e:
            ok = False
            print('error', i, repr(e)[:200], flush=True)
        done[i] = {'seconds': time.perf_counter() - t, 'parsed': ok}
        if n % 10 == 0:
            json.dump({'settings': args, 'per_sentence': done}, open(a.out, 'w'))
            print(n, flush=True)
    secs = [v['seconds'] for v in done.values()]
    json.dump({'settings': args, 'sentences': len(done), 'seconds': sum(secs),
               'parsed': sum(v['parsed'] for v in done.values()), 'per_sentence': done}, open(a.out, 'w'), indent=1)
    print(json.dumps({'sentences': len(done), 'seconds': round(sum(secs), 1)}))


def features(rec, c, tags):
    """Orca's own per-sentence signals: tagger confidence, repair effort, candidates."""
    import math
    top = tags['top']
    l1 = [w[0][2] for w in top['leaf']] or [1.0]
    t1 = [w[0][2] for w in top['tree']] or [1.0]
    cands = (c or {}).get('candidates') or []
    costs = sorted(x.get('cost') or 0.0 for x in cands)
    margin = (costs[1] - costs[0]) if len(costs) > 1 else 10.0
    return [math.log(min(l1) + 1e-9), math.log(min(t1) + 1e-9),
            sum(math.log(p + 1e-9) for p in l1) / len(l1), sum(math.log(p + 1e-9) for p in t1) / len(t1),
            math.log1p(rec.get('replays') or 0), 1.0 if rec.get('outcome') == 'accepted at first try' else 0.0,
            math.log1p(int(rec.get('accepted') or 0)), min(margin, 10.0), math.log1p(len(top['leaf'])),
            1.0 if not int(rec.get('accepted') or 0) else 0.0]


def logreg(X, y, Xt, l2=1.0, steps=3000, lr=0.1):
    """L2-regularized logistic regression by gradient descent on standardized features."""
    import numpy as np
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z, Zt = (X - mu) / sd, (Xt - mu) / sd
    w, b0 = np.zeros(Z.shape[1]), 0.0
    for _ in range(steps):
        p = 1 / (1 + np.exp(-(Z @ w + b0)))
        g = p - y
        w -= lr * (Z.T @ g / len(y) + l2 * w / len(y))
        b0 -= lr * g.mean()
    return 1 / (1 + np.exp(-(Zt @ w + b0)))


def auc(y, s):
    import numpy as np
    order = np.argsort(s)
    ranks = np.empty(len(s))
    ranks[order] = np.arange(1, len(s) + 1)
    pos = y == 1
    return (ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * (~pos).sum())


def cmd_route(a):
    import pickle
    import numpy as np
    run, b = buckets(a.run)
    ace = {r['id']: str(r['same MRS']) == 'True' for r in json.load(open(ACE_EVAL))['records']}
    tags = pickle.load(open(os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl'), 'rb'))['items']
    cands = {}
    for l in open(a.cands):
        r = json.loads(l)
        cands[r['id']] = r
    recs = {x['id']: x for x in run['records']}
    ids = [i for i in b if i in tags]
    X = np.array([features(recs[i], cands.get(i), tags[i]) for i in ids])
    orca_ok = np.array([b[i] == 'right' for i in ids])
    ace_ok = np.array([ace.get(i, False) for i in ids])
    # target: send to ACE when Orca is wrong (what we can detect); evaluate gain in exact meaning
    y = (~orca_ok).astype(int)
    random.seed(1)
    order = list(range(len(ids)))
    random.shuffle(order)
    K = 5
    score = np.zeros(len(ids))
    for k in range(K):
        test = order[k::K]
        train = [j for j in order if j not in set(test)]
        score[test] = logreg(X[train], y[train], X[test])
    # always send no-analysis sentences; then by score
    none = np.array([b[i] == 'none' for i in ids])
    run_secs = len(ids) / run['sentences per second']
    t = json.load(open(a.time)) if a.time and os.path.exists(a.time) else None
    ace_none = {k: v['seconds'] for k, v in t['per_sentence'].items()} if t else {}
    ace_mean = (t['seconds'] / t['sentences']) if t else None
    # other sentences: ACE's mean over all of dev in our comparison runs (first pass plus 16 GB and 28 GB retries)
    ACE_DEV_MEAN = (1276.6 + 437.8 + 301.5) / 2062
    rest = sorted([j for j in range(len(ids)) if not none[j]], key=lambda j: -score[j])
    curve, sent = [], {}
    for extra in (0, 50, 100, 200, 300, 400, 600, 800, 1000, len(rest)):
        send = set(np.where(none)[0]) | set(rest[:extra])
        right = sum((ace_ok[j] if j in send else orca_ok[j]) for j in range(len(ids)))
        secs = run_secs + sum(ace_none.get(ids[j], ACE_DEV_MEAN) for j in send)
        curve.append({'sent to ACE': len(send), 'exact': int(right),
                      'sentences per second': round(len(ids) / secs, 2)})
        sent[len(send)] = sorted(ids[j] for j in send)
    out = {'sentences': len(ids), 'orca exact': int(orca_ok.sum()), 'ace exact': int(ace_ok.sum()),
           'cv AUC (Orca wrong)': round(float(auc(y, score)), 3), 'ace seconds per sentence (measured on no-analysis)': ace_mean,
           'curve': curve, 'features': ['min leaf p', 'min tree p', 'mean log leaf p', 'mean log tree p', 'log replays', 'first try',
                                        'log accepted', 'tagger-cost margin of the two best accepted', 'log length', 'no analysis']}
    out['run'] = os.path.relpath(a.run or RUN, ROOT)
    out['ace seconds, sentences without a measured time'] = round(ACE_DEV_MEAN, 3)
    out['no-analysis sentences without a measured ACE time'] = int(sum(1 for j in np.where(none)[0] if ids[j] not in ace_none))
    json.dump(out, open(a.out, 'w'), indent=1)
    if a.sent_out:
        json.dump(sent, open(a.sent_out, 'w'))
    print(json.dumps({k: v for k, v in out.items() if k != 'features'}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('time', 'route'))
    ap.add_argument('--ids', default='no-analysis')
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--mb', type=int, default=16000)
    ap.add_argument('--cands')
    ap.add_argument('--time')
    ap.add_argument('--run', help='Orca eval JSON to route from (default: the run before the repair cutoff change)')
    ap.add_argument('--sent-out', help='write the ids sent to ACE at each curve point')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    {'time': cmd_time, 'route': cmd_route}[a.cmd](a)


if __name__ == '__main__':
    main()
