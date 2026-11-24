#!/usr/bin/env python3
"""How much of a tagger's label inventory an older (or newer) grammar version lacks,
and which missing names have an obvious counterpart (roadmap O91, robustness to
grammar changes).

A label is split into the grammar names it refers to:
  leaf  'lextype|lexrule lexrule|unary unary'   -> lexical type, lexical rules, unary rules
  tree  'depth|[root ]rule'                      -> phrasal rule (and a root condition at the top)
Each name is looked up in the other grammar: types in its hierarchy, rules and root
conditions among its instances. Counts are over the tagger's cached dev output
(repair_bench.py's cache): first guesses, and every label repair may try (top 5 per
word, probability >= min_prob).

Counterparts for a missing lexical type: the types the other grammar gives to the
lexical entries of the missing type (one type: a rename or a merge; several: a split).
For a missing rule: a rule of the other grammar with the same immediate supertypes.

Usage:
    grammar_drift.py --tagger-grammar data/erg/2025/english.tdl --other data/erg/2020-orca/english.tdl \
        --cache data/bench/dev-debertav3large-tags.pkl --out analysis/grammar-drift/labels-2020.json
"""
import argparse
import collections
import json
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def names_of(kind, label):
    """[(kind of name, name)] a label refers to."""
    if label.startswith('<'):
        return []
    if kind == 'leaf':
        parts = label.split('|')
        out = [('lexical type', parts[0])]
        if len(parts) > 1:
            out += [('lexical rule', x) for x in parts[1].split()]
        if len(parts) > 2:
            out += [('unary rule', x) for x in parts[2].split()]
        return out
    body = label.split('|', 1)[1] if '|' in label else label
    xs = body.split()
    out = [('root condition', x) for x in xs[:-1]]
    if xs and xs[-1] != '<none>':
        out.append(('phrasal rule', xs[-1]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tagger-grammar', default='data/erg/2025/english.tdl')
    ap.add_argument('--other', required=True)
    ap.add_argument('--cache', default='data/bench/dev-debertav3large-tags.pkl')
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--min-prob', type=float, default=0.001)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    g0, g1 = Grammar(a.tagger_grammar), Grammar(a.other)
    lx0, lx1 = Lexicon(g0, os.path.dirname(a.tagger_grammar)), Lexicon(g1, os.path.dirname(a.other))

    def exists(g, kind, name):
        if kind == 'lexical type':
            return name in g.h.parents
        return name in g.status

    data = pickle.load(open(a.cache, 'rb'))['items']
    first = collections.Counter()      # (kind, name) -> first-guess tokens using it
    tried = collections.Counter()      # (kind, name) -> labels repair may try, tokens
    sent_first, sent_tried = collections.Counter(), collections.Counter()
    n_tok = n_sent = 0
    for sid, it in data.items():
        top = it['top']
        if not top:
            continue
        n_sent += 1
        n_tok += len(top['leaf'])
        f_missing, t_missing = set(), set()
        for kind in ('leaf', 'tree'):
            for j, cands in enumerate(top[kind]):
                for r, (label, _, p) in enumerate(cands[:a.k]):
                    if r and p < a.min_prob:
                        break
                    for nm in names_of(kind, label):
                        if exists(g1, *nm):
                            continue
                        tried[nm] += 1
                        t_missing.add(nm)
                        if r == 0:
                            first[nm] += 1
                            f_missing.add(nm)
        for nm in f_missing:
            sent_first[nm] += 1
        if f_missing:
            sent_first['__any__'] += 1
        if t_missing:
            sent_tried['__any__'] += 1

    # inventory: every name the tagger can output
    labels = json.load(open(os.path.join(os.path.dirname(a.cache), '..', 'models', 'tagger-2025bothsurf-debertav3large', 'labels.json')))
    inv = collections.Counter()
    inv_missing = collections.defaultdict(set)
    for kind in ('leaf', 'tree'):
        for label in labels[kind]:
            for nm in names_of(kind, label):
                inv[nm[0]] += 0
                if not exists(g0, *nm):
                    continue
                if not exists(g1, *nm):
                    inv_missing[nm[0]].add(nm[1])
    known = collections.defaultdict(set)
    for kind in ('leaf', 'tree'):
        for label in labels[kind]:
            for nm in names_of(kind, label):
                if exists(g0, *nm):
                    known[nm[0]].add(nm[1])

    # counterparts
    by_type0 = collections.defaultdict(list)
    for e, t in lx0.type_of.items():
        by_type0[t].append(e)
    parents1 = collections.defaultdict(list)
    for nm, st in g1.status.items():
        if st in ('rule', 'lex-rule'):
            parents1[tuple(sorted(g1.h.parents.get(nm, [])))].append(nm)
    counterparts = {}
    for kind, names in inv_missing.items():
        for nm in sorted(names):
            if kind == 'lexical type':
                ents = by_type0.get(nm, [])
                other = collections.Counter(lx1.type_of.get(e) for e in ents)
                kept = {t: c for t, c in other.items() if t}
                counterparts[f'{kind}:{nm}'] = {'entries': len(ents), 'entries in other grammar': sum(kept.values()),
                                               'their types there': dict(sorted(kept.items(), key=lambda kv: -kv[1])[:5]),
                                               'same supertypes there': [t for t in kept if g1.h.parents.get(t) == g0.h.parents.get(nm)][:5]}
            else:
                key = tuple(sorted(g0.h.parents.get(nm, [])))
                counterparts[f'{kind}:{nm}'] = {'same supertypes there': parents1.get(key, [])[:5]}

    def kinds(counter):
        out = collections.defaultdict(lambda: {'names': 0, 'tokens': 0})
        for (k, nm), c in counter.items():
            out[k]['names'] += 1
            out[k]['tokens'] += c
        return dict(out)

    res = {'tagger grammar': a.tagger_grammar, 'other grammar': a.other, 'sentences': n_sent, 'tokens': n_tok,
           'inventory: names the tagger knows, by kind': {k: len(v) for k, v in known.items()},
           'inventory: of those, missing in the other grammar': {k: len(v) for k, v in inv_missing.items()},
           'first guess: missing names by kind (distinct names, label uses)': kinds(first),
           'first guess: sentences with a missing name': sent_first['__any__'],
           'labels repair may try: missing names by kind': kinds(tried),
           'labels repair may try: sentences with a missing name': sent_tried['__any__'],
           'most used missing names (first guess)': [[k, nm, c, sent_first[(k, nm)]] for (k, nm), c in first.most_common(25)],
           'counterparts': counterparts}
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('counterparts',)}, indent=1))


if __name__ == '__main__':
    main()
