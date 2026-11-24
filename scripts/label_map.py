#!/usr/bin/env python3
"""Map a tagger's grammar names onto another version of the grammar (roadmap O91, step 3:
keep Orca working when the grammar changes, without retraining).

Built offline from two grammar versions: `old`, the one the tagger was trained for, and
`new`, the one Orca now runs with.

  lexical types   a type `new` lacks is mapped through its lexical entries: the types those
                  same entries have in `new` (one type = a rename or merge; several = a split,
                  all offered, replay decides), most entries first.
  rules           a rule, lexical rule or root condition `new` lacks is mapped only when the
                  mapping is unambiguous by name family: exactly one rule of `new` that `old`
                  lacks has the same first name segment and the same suffix (sb-hd_x_c ->
                  sb-hd_y_c). No other guessing; constructions are never invented.

The parser uses the map (orca/tfs/lexicon.py Lexicon.type_map / rule_map, FastGrammar.rule_map)
when an option turns it on; see repair_bench.py --label-map / --word-fallback.

Usage:
    label_map.py --old data/erg/2025/english.tdl --new data/erg/2020-orca/english.tdl --out data/label-map/erg-2025-to-2020.json
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

RULE_STATUSES = ('rule', 'lex-rule')


def family(name):
    """First name segment and suffix: 'sb-hd_mc_c' -> ('sb-hd', 'c'); 'root_strict' -> ('root', None)."""
    parts = name.split('_')
    return parts[0], (parts[-1] if len(parts) > 2 else None)


def build(old_tdl, new_tdl):
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    g0, g1 = Grammar(old_tdl), Grammar(new_tdl)
    lx0, lx1 = Lexicon(g0, os.path.dirname(old_tdl)), Lexicon(g1, os.path.dirname(new_tdl))
    by_type0 = collections.defaultdict(list)
    for e, t in lx0.type_of.items():
        by_type0[t].append(e)
    types, stats = {}, collections.Counter()
    for t in sorted(by_type0):
        if t in g1.h.parents:
            continue
        stats['lexical types missing'] += 1
        there = collections.Counter(lx1.type_of.get(e) for e in by_type0[t])
        there.pop(None, None)
        if not there:
            stats['… no entry of it in the new lexicon'] += 1
            continue
        types[t] = [x for x, _ in there.most_common()]
        stats['… one type there (rename or merge)' if len(there) == 1 else '… several types there (split)'] += 1
    rules = {}
    names0 = {n for n, s in g0.status.items() if s in RULE_STATUSES}
    names1 = {n for n, s in g1.status.items() if s in RULE_STATUSES}
    # root conditions are instances too (status None in some load plans): include names starting with root_
    names0 |= {n for n in g0.instances if n.startswith('root_')}
    names1 |= {n for n in g1.instances if n.startswith('root_')}
    only1 = collections.defaultdict(list)
    for n in names1 - names0:
        only1[family(n)].append(n)
    for n in sorted(names0 - names1):
        stats['rules missing'] += 1
        cands = only1.get(family(n), [])
        if len(cands) == 1:
            rules[n] = cands[0]
            stats['… mapped by name family'] += 1
        else:
            stats['… not mapped (no or several candidates)'] += 1
    return {'old': old_tdl, 'new': new_tdl, 'types': types, 'rules': rules, 'stats': dict(stats)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--old', default='data/erg/2025/english.tdl')
    ap.add_argument('--new', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    m = build(a.old, a.new)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(m, open(a.out, 'w'), indent=1)
    print(json.dumps(m['stats'], indent=1))
    print(json.dumps(m['rules'], indent=1))


if __name__ == '__main__':
    main()
