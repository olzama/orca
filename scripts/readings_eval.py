#!/usr/bin/env python3
"""Several readings per sentence (roadmap O97): how often the gold meaning is among
Orca's top distinct readings, and a rule for when to return more than one.

extract: for each dev sentence, the accepted derivations (a candidate file written by
    repair_bench.py --gold-mrs --cands-out, with per-derivation gold flags) are scored by
    the MaxEnt ranking model, replayed to MRS, and grouped into distinct readings
    (normalized MRS, isomorphism without properties, as the dev evaluation compares).
    A reading's score is its best derivation's MaxEnt score; its probability is the sum,
    over its derivations, of a softmax of the MaxEnt scores of all accepted derivations.
report: distinct readings per sentence, gold among the top 1/2/3/5/all readings (also by
    sentence length), and the margin rule: return every reading whose score is within M
    (log space) of the best, at most K; M fitted by 5-fold cross-validation.

Usage:
    readings_eval.py extract --cache data/bench/dev-debertav3large-tags.pkl \
        --cands analysis/ace-fallback/dev-cands-minprob001.jsonl --out analysis/readings/dev-readings.jsonl
    readings_eval.py report --readings analysis/readings/dev-readings.jsonl --out analysis/readings/dev-summary.json
"""
import argparse
import collections
import json
import math
import os
import pickle
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

BANDS = ((0, 10, 'under 10'), (10, 20, '10 to 19'), (20, 30, '20 to 29'), (30, 10 ** 6, '30 and over'))


def group_readings(items, same):
    """items: list of (score, mrs or None, payload); same(m1, m2) -> bool.
    Returns readings (best first): dicts with score, members (payloads), mrs."""
    readings = []
    for score, m, payload in sorted(items, key=lambda x: -x[0]):
        for rd in readings:
            if m is not None and rd['mrs'] is not None and same(m, rd['mrs']):
                rd['members'].append((score, payload))
                break
        else:
            readings.append({'score': score, 'mrs': m, 'members': [(score, payload)]})
    return readings


def softmax_mass(readings):
    """Probability of each reading: softmax over all member scores, summed per reading."""
    allsc = [s for rd in readings for s, _ in rd['members']]
    if not allsc:
        return []
    mx = max(allsc)
    z = sum(math.exp(s - mx) for s in allsc)
    return [sum(math.exp(s - mx) for s, _ in rd['members']) / z for rd in readings]


def select(scores, k=None, margin=None):
    """Indices of the readings to return: best first, at most k, within margin (log space) of the best."""
    if not scores:
        return []
    out = [0]
    for i in range(1, len(scores)):
        if k is not None and len(out) >= k:
            break
        if margin is not None and scores[0] - scores[i] > margin:
            break
        if margin is None and k is None:
            break
        out.append(i)
    return out


def extract(a):
    from compare_mrs import normalized, to_pydelphin
    from delphin import mrs as M
    from eval_trees import to_leaves
    from orca.encoding import decode
    from orca.tfs.fast import extract as fs_extract
    from orca_parse import Parser
    from rerank import with_entries
    data = pickle.load(open(a.cache, 'rb'))['items']
    p = Parser(tagger=a.tagger, device='cpu') if a.tagger else Parser(device='cpu')
    same = lambda x, y: bool(M.is_isomorphic(x, y, properties=False))
    with open(a.out, 'w') as out:
        for line in open(a.cands):
            r = json.loads(line)
            sid, cands = r['id'], r['candidates']
            rec = {'id': sid, 'n_tokens': len(r['forms']), 'derivations': len(cands), 'readings': []}
            if cands:
                path = data[sid]['path']
                items = []
                for c in cands:
                    tr = with_entries(decode(to_leaves(r['forms'], c['leaf'], c['tree'])), c['entries'])
                    score = p.me.score(tr, p.lx.type_of.get, p.generic)
                    try:
                        p.fg.reset()
                        fs, _ = p.fg.replay_tree(tr, [q[1] for q in path])
                        m = normalized(to_pydelphin(fs_extract(p.fg, fs)))
                    except Exception:
                        m = None
                    items.append((score, m, bool(c['same_mrs'])))
                rds = group_readings(items, same)
                probs = softmax_mass(rds)
                rec['readings'] = [{'score': rd['score'], 'prob': pr, 'derivations': len(rd['members']),
                                    'gold': any(g for _, g in rd['members']),
                                    'gold mixed': len({g for _, g in rd['members']}) > 1}
                                   for rd, pr in zip(rds, probs)]
            out.write(json.dumps(rec) + '\n')


def report(a):
    recs = [json.loads(l) for l in open(a.readings)]
    N = len(recs)
    band = lambda n: next(nm for lo, hi, nm in BANDS if lo <= n < hi)
    res = {'sentences': N}
    # distribution of distinct readings
    dist = collections.Counter(len(r['readings']) for r in recs)
    res['distinct readings per sentence'] = {str(k): dist[k] for k in sorted(dist)}
    res['derivations per sentence (with an analysis)'] = sum(r['derivations'] for r in recs if r['readings']) / max(1, sum(1 for r in recs if r['readings']))
    res['readings per sentence (with an analysis)'] = sum(len(r['readings']) for r in recs if r['readings']) / max(1, sum(1 for r in recs if r['readings']))
    res['gold mixed in a reading'] = sum(rd['gold mixed'] for r in recs for rd in r['readings'])
    # gold among top k, overall and by band
    ks = (1, 2, 3, 5, 10 ** 6)
    kname = lambda k: 'all' if k == 10 ** 6 else str(k)
    def topk(rs, k):
        return sum(any(rd['gold'] for rd in r['readings'][:k]) for r in rs)
    res['gold among top k'] = {kname(k): topk(recs, k) for k in ks}
    by = collections.defaultdict(list)
    for r in recs:
        by[band(r['n_tokens'])].append(r)
    res['by length'] = {b: {'sentences': len(by[b]), **{kname(k): topk(by[b], k) for k in ks},
                            'mean distinct readings': sum(len(r['readings']) for r in by[b]) / max(1, len(by[b]))}
                        for _, _, b in BANDS}

    # margin rule: curve on all of dev, then 5-fold CV for one operating point
    def evaluate(rs, margin, kmax):
        hit = size = multi = credit = 0
        for r in rs:
            sel = select([rd['score'] for rd in r['readings']], k=kmax, margin=margin)
            if not sel:
                continue
            g = any(r['readings'][i]['gold'] for i in sel)
            hit += g
            size += len(sel)
            multi += len(sel) > 1
            credit += (1 / len(sel)) if g else 0
        n_an = sum(1 for r in rs if r['readings'])
        return {'gold in set': hit, 'mean set size': size / max(1, n_an), 'more than one': multi, 'set credit': credit}
    margins = [0, 0.25, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6]
    res['curve (all dev, at most 5 readings)'] = {str(m): evaluate(recs, m, 5) for m in margins}
    # CV: choose the largest margin whose mean set size on the training folds stays <= target
    rng = random.Random(1)
    idx = list(range(N))
    rng.shuffle(idx)
    folds = [idx[i::5] for i in range(5)]
    cv = {}
    for target in (1.2, 1.3, 1.5):
        agg = collections.Counter()
        chosen = []
        for f in range(5):
            test = [recs[i] for i in folds[f]]
            train = [recs[i] for j in range(5) if j != f for i in folds[j]]
            fine = [m / 20 for m in range(0, 121)]
            ok = [m for m in fine if evaluate(train, m, 5)['mean set size'] <= target]
            m = max(ok) if ok else 0
            chosen.append(m)
            e = evaluate(test, m, 5)
            agg['gold in set'] += e['gold in set']
            agg['more than one'] += e['more than one']
            agg['set credit'] += e['set credit']
            agg['size sum'] += e['mean set size'] * sum(1 for r in test if r['readings'])
        n_an = sum(1 for r in recs if r['readings'])
        cv[str(target)] = {'margins chosen per fold': chosen, 'gold in set': agg['gold in set'],
                           'mean set size': agg['size sum'] / n_an, 'more than one': agg['more than one'],
                           'set credit': round(agg['set credit'], 1)}
    res['cross-validated margin (target mean set size)'] = cv
    res['top 1 only'] = evaluate(recs, 0, 1)
    res['definitions'] = {
        'gold in set': 'sentences whose returned readings include the gold meaning (exact MRS, without properties)',
        'mean set size': 'readings returned per sentence with an analysis',
        'set credit': 'sum over sentences of 1/size when gold is in the returned set, else 0; equals exact match when one reading is returned',
        'margin': 'return every distinct reading whose best derivation\'s MaxEnt score is within M of the top reading\'s (log space), at most 5'}
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'definitions'}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('extract', 'report'))
    ap.add_argument('--cache')
    ap.add_argument('--cands')
    ap.add_argument('--tagger')
    ap.add_argument('--readings')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    extract(a) if a.cmd == 'extract' else report(a)


if __name__ == '__main__':
    main()
