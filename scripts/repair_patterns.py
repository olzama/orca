#!/usr/bin/env python3
"""Learned repair patterns: label substitutions the tagger tends to need.

Mining (`mine`): tag sentences the tagger never saw in training, but for which
grammar-checked labels exist (the generated rounds, labeled by ACE's parse;
never dev or test), and count where the tagger's first choice differs from the
reference label. Patterns are kept at two levels:

- whole labels: tagger label A -> reference label B (per kind, leaf or tree);
- label parts, so that a pattern carries over to labels seen rarely:
  leaf `lextype|lexrules|unaries` with one part swapped (the rest as the
  tagger had it), tree `delta|node` with the node or the attachment height
  swapped.

Differences in the root condition (root_strict ...) are skipped: ACE's labels of
the generated sentences carry none, so they say nothing about repair.

Using (`augment`): before repair, each token's list of alternatives gets the
pattern labels for its first-choice label, with a pseudo-probability
(1 - p_first) * P(B | A, the tagger was wrong), merged into the tagger's own
list in order of probability. Repair (scripts/repair.py) then tries them
like any other alternative: early if the pattern is strong and the tagger
unsure.

Mining from cross-validation candidates (`mine-cv`): the tagger's first choice
and the treebank's gold labels are already stored per sentence by
cv_candidates.py (held-out folds of the Redwoods training data, each tagged by a
tagger that never saw it), so no tagging is needed. Only sentences whose tokens
match the treebank's are used. Root conditions are kept: here the gold labels
carry them.

Usage:
    repair_patterns.py mine --tagger MODEL --data A.jsonl [B.jsonl ...] --out PATTERNS.json
    repair_patterns.py mine-cv --data data/cv-candidates/fold0.jsonl [...] --out PATTERNS.json
"""
import argparse
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

CONT = '<cont>'


def parts_subs(kind, a, b):
    """Part-level substitutions turning label a into label b, as (part, from, to)."""
    pa, pb = a.split('|'), b.split('|')
    if len(pa) != len(pb):
        return []
    diff = [i for i in range(len(pa)) if pa[i] != pb[i]]
    if len(diff) != 1:
        return []
    i = diff[0]
    names = ('lextype', 'lexrules', 'unaries') if kind == 'leaf' else ('delta', 'node')
    if i >= len(names):
        return []
    return [(names[i], pa[i], pb[i])]


def mine(args):
    from llm_label import read
    import orca_parse
    p = orca_parse.Parser(tagger=args.tagger, k=args.k)
    whole = {k: collections.defaultdict(collections.Counter) for k in ('leaf', 'tree')}
    part = {k: collections.defaultdict(collections.Counter) for k in ('leaf', 'tree')}
    wrong_of = {k: collections.Counter() for k in ('leaf', 'tree')}
    seen = {k: collections.Counter() for k in ('leaf', 'tree')}
    in_topk = collections.Counter()
    n = 0
    for path in args.data:
        for s in read(path):
            top = p.tag(s['forms'])
            n += 1
            for kind in ('leaf', 'tree'):
                for j, gold in enumerate(s[kind]):
                    if kind == 'tree' and j == len(s['forms']) - 1:
                        continue
                    a = top[kind][j][0][0]
                    if a.startswith(CONT) or gold.startswith(CONT):
                        continue
                    seen[kind][a] += 1
                    if a == gold:
                        continue
                    if kind == 'tree' and ('root_' in a) != ('root_' in gold):
                        continue        # the generated data's labels carry no root condition: not a repair
                    wrong_of[kind][a] += 1
                    whole[kind][a][gold] += 1
                    in_topk[(kind, any(x[0] == gold for x in top[kind][j]))] += 1
                    for name, x, y in parts_subs(kind, a, gold):
                        part[kind][(name, x)][y] += 1
    out = {'source': [os.path.relpath(x) for x in args.data], 'tagger': os.path.basename(args.tagger.rstrip('/')), 'sentences': n,
           'errors': {k: sum(wrong_of[k].values()) for k in wrong_of},
           'errors with the reference label in the top k': {f'{k}': in_topk[(k, True)] for k in ('leaf', 'tree')},
           'whole': {}, 'part': {}}
    for kind in ('leaf', 'tree'):
        out['whole'][kind] = {a: [[b, c] for b, c in cs.most_common(args.per_label) if c >= args.min_count]
                              for a, cs in whole[kind].items()}
        out['whole'][kind] = {a: v for a, v in out['whole'][kind].items() if v}
        out['part'][kind] = {f'{name}={x}': [[y, c, sum(cs.values())] for y, c in cs.most_common(args.per_label) if c >= args.min_count]
                             for (name, x), cs in part[kind].items()}
        out['part'][kind] = {a: v for a, v in out['part'][kind].items() if v}
    out['counts'] = {k: {'whole': sum(len(v) for v in out['whole'][k].values()),
                         'part': sum(len(v) for v in out['part'][k].values())} for k in ('leaf', 'tree')}
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ('whole', 'part')}, indent=1))


def mine_cv(args):
    whole = {k: collections.defaultdict(collections.Counter) for k in ('leaf', 'tree')}
    part = {k: collections.defaultdict(collections.Counter) for k in ('leaf', 'tree')}
    wrong = collections.Counter()
    n = used = 0
    for path in args.data:
        for line in open(path, encoding='utf-8'):
            r = json.loads(line)
            n += 1
            if not r.get('gold_forms_match') or 'first' not in r:
                continue
            used += 1
            for kind in ('leaf', 'tree'):
                fl, gl = r['first'][kind], r['gold'][kind]
                if len(fl) != len(gl):
                    continue
                for j, (a, gold) in enumerate(zip(fl, gl)):
                    if kind == 'tree' and j == len(fl) - 1:
                        continue
                    if a == gold or a.startswith(CONT) or gold.startswith(CONT):
                        continue
                    wrong[kind] += 1
                    whole[kind][a][gold] += 1
                    for name, x, y in parts_subs(kind, a, gold):
                        part[kind][(name, x)][y] += 1
    out = {'source': [os.path.relpath(x) for x in args.data], 'tagger': 'cross-validation folds (first choice of each fold\'s tagger)',
           'sentences': n, 'sentences used': used, 'errors': dict(wrong), 'whole': {}, 'part': {}}
    for kind in ('leaf', 'tree'):
        out['whole'][kind] = {a: [[b, c] for b, c in cs.most_common(args.per_label) if c >= args.min_count]
                              for a, cs in whole[kind].items()}
        out['whole'][kind] = {a: v for a, v in out['whole'][kind].items() if v}
        out['part'][kind] = {f'{name}={x}': [[y, c, sum(cs.values())] for y, c in cs.most_common(args.per_label) if c >= args.min_count]
                             for (name, x), cs in part[kind].items()}
        out['part'][kind] = {a: v for a, v in out['part'][kind].items() if v}
    out['counts'] = {k: {'whole': sum(len(v) for v in out['whole'][k].values()),
                         'part': sum(len(v) for v in out['part'][k].values())} for k in ('leaf', 'tree')}
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ('whole', 'part')}, indent=1))


class Patterns:
    def __init__(self, path, weight=1.0, max_new=3, only_new=False):
        d = json.load(open(path))
        self.whole, self.part, self.weight, self.max_new = d['whole'], d['part'], weight, max_new
        self.only_new = only_new       # only add labels the tagger did not list; never reorder its own

    def proposals(self, kind, a):
        """Labels B for first-choice label a, with P(B | a, wrong)."""
        out = collections.Counter()
        cs = self.whole[kind].get(a)
        if cs:
            tot = sum(c for _, c in cs)
            for b, c in cs:
                out[b] = max(out[b], c / tot)
        pa = a.split('|')
        names = ('lextype', 'lexrules', 'unaries') if kind == 'leaf' else ('delta', 'node')
        for i, name in enumerate(names):
            if i >= len(pa):
                break
            for y, c, tot in self.part[kind].get(f'{name}={pa[i]}', []):
                b = '|'.join(pa[:i] + [y] + pa[i + 1:])
                out[b] = max(out[b], 0.5 * c / tot)        # part patterns: weaker evidence than whole labels
        return out.most_common(self.max_new)

    def augment(self, top):
        """Merge pattern labels into the tagger's alternatives (in place)."""
        for kind in ('leaf', 'tree'):
            for j, alts in enumerate(top[kind]):
                if not alts or alts[0][0].startswith(CONT):
                    continue
                a, p1 = alts[0][0], alts[0][2]
                have = {x[0]: i for i, x in enumerate(alts)}
                extra = list(alts[1:])
                for b, q in self.proposals(kind, a):
                    pb = self.weight * (1 - p1) * q
                    if pb <= 0:
                        continue
                    if b in have and have[b] > 0 and not self.only_new:
                        i = have[b] - 1
                        if pb > extra[i][2]:
                            extra[i] = (b, math.log(pb), pb)
                    elif b not in have:
                        extra.append((b, math.log(pb), pb))
                extra.sort(key=lambda x: -x[2])
                top[kind][j] = [alts[0]] + extra
        return top


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('mine')
    m.add_argument('--tagger', required=True)
    m.add_argument('--data', nargs='+', required=True)
    m.add_argument('--out', required=True)
    m.add_argument('--k', type=int, default=5)
    m.add_argument('--min-count', type=int, default=2)
    m.add_argument('--per-label', type=int, default=5)
    c = sub.add_parser('mine-cv')
    c.add_argument('--data', nargs='+', required=True)
    c.add_argument('--out', required=True)
    c.add_argument('--min-count', type=int, default=2)
    c.add_argument('--per-label', type=int, default=5)
    a = ap.parse_args()
    if a.cmd == 'mine':
        mine(a)
    elif a.cmd == 'mine-cv':
        mine_cv(a)


if __name__ == '__main__':
    main()
