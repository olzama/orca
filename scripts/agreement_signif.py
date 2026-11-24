#!/usr/bin/env python3
"""Is the attractor-number effect in the agreement test real?

Experiment 1 of Chaves and Richter (2021), grammatical items with a clause before the subject:
the clause's noun has the subject's number ('attractor matches') or the other number
('attractor mismatches'). For each measure (first guess accepted, Orca finds an analysis,
same MRS as ACE) this compares the two conditions with Fisher's exact test (two-sided) and a
two-proportion z-test, from the counts in agreement_test.py's score.json files.

Usage: agreement_signif.py LABEL=SCORE.json [LABEL=SCORE.json ...] --out OUT.json
"""
import argparse
import json
import math

A, B = 'e1|grammatical|top clause, attractor matches', 'e1|grammatical|top clause, attractor mismatches'
MEASURES = (('first guess accepted', 'accepted at first try'), ('Orca finds an analysis', 'orca analysis'),
            ('same MRS as ACE', 'same as ace'))


def lchoose(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_two_sided(a, b, c, d):
    """2x2 table [[a, b], [c, d]]; two-sided p as the sum of tables no more likely than the observed one."""
    r1, r2, c1, n = a + b, c + d, a + c, a + b + c + d
    def p(x):
        return math.exp(lchoose(r1, x) + lchoose(r2, c1 - x) - lchoose(n, c1))
    obs = p(a)
    lo, hi = max(0, c1 - r2), min(r1, c1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def z_test(k1, n1, k2, n2):
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    z = (k1 / n1 - k2 / n2) / se if se else 0.0
    return z, math.erfc(abs(z) / math.sqrt(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('scores', nargs='+')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    res = {}
    for spec in a.scores:
        label, path = spec.split('=', 1)
        s = json.load(open(path))
        ma, mb = s[A], s[B]
        out = {}
        for name, key in MEASURES:
            k1, n1, k2, n2 = ma.get(key, 0), ma['n'], mb.get(key, 0), mb['n']
            if not (k1 or k2):
                continue
            z, pz = z_test(k1, n1, k2, n2)
            out[name] = {'attractor matches': [k1, n1], 'attractor mismatches': [k2, n2],
                         'difference (points)': round(100 * (k2 / n2 - k1 / n1), 1),
                         'fisher p (two-sided)': fisher_two_sided(k1, n1 - k1, k2, n2 - k2), 'z': round(z, 2), 'z-test p': pz}
        res[label] = out
    json.dump(res, open(a.out, 'w'), indent=1)
    for label, out in res.items():
        for name, v in out.items():
            print(f"{label:22s} {name:24s} {v['attractor matches']} vs {v['attractor mismatches']}  diff {v['difference (points)']:+5.1f}  Fisher p={v['fisher p (two-sided)']:.2g}")


if __name__ == '__main__':
    main()
