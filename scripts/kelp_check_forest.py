#!/usr/bin/env python3
"""Check that Orca's replay agrees with ACE on the trees of ACE's packed forests.

A packed forest holds trees that fail when their unifications are redone.
For every item of a full-forest profile this script unpacks every tree,
replays it with Orca, and compares the trees that replay with the readings
ACE itself lists when it unpacks the same sentence exhaustively. It also
compares, for each shared tree, the root condition and the MRS (with and
without ICONS, and without variable properties).

ACE drops readings that contain parts of idioms without the whole idiom.
Orca has no idiom rules yet; a tree counts here as having unlicensed idiom
parts when it fails the grammar's non-idiom root condition. That test would
also reject a complete idiom.

Usage:
    kelp_check_forest.py --grammar ERG_DIR/english.tdl --profile FOREST_PROFILE [--max-trees N] [--out FILE]
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
sys.setrecursionlimit(20000)

from delphin import ace, itsdb, mrs as dmrs  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from compare_mrs import to_pydelphin  # noqa: E402
from kelp.forest import load_forests  # noqa: E402
from orca.encoding import Leaf, Node  # noqa: E402
from orca.tfs.fast import FastGrammar, extract  # noqa: E402
from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402

ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
DAT = os.path.join(HERE, '..', 'data/ace/erg-2025.dat')
# `parsing-roots` and `non-idiom-root` of the ERG's ACE configuration (ace/config.tdl).
# ACE reports the first root condition that holds in the order of definition
# in roots.tdl (informal fragments before formal ones), which is the order here.
ROOTS = ['root_strict', 'root_informal', 'root_inffrag', 'root_frag', 'root_robust_frag',
         'root_robust', 'root_exclam_ques']
NON_IDIOM = 'root_non_idiom'


def to_orca(tree):
    """A forest tree as Orca's replay input: (tree, token structures)."""
    toks = []

    def walk(t):
        if t.lexical:
            toks.extend(tok.avm for tok in t.tokens)
            return Leaf('entry:' + t.label, tuple(tok.form for tok in t.tokens))
        return Node(t.label, tuple(walk(c) for c in t.children))

    return walk(tree), toks


def ace_key(d):
    """An ACE derivation in the form of `kelp.forest.Tree.key()`."""
    kids = [c for c in (d.daughters or []) if hasattr(c, 'entity')]
    return (d.entity, d.start, d.end, tuple(ace_key(c) for c in kids))


def without_icons(m):
    """The MRS without ICONS and without variables that only ICONS mention."""
    used = {m.top, m.index} | {v for ep in m.rels for v in [ep.label, *ep.args.values()]} \
        | {v for hc in m.hcons for v in (hc.hi, hc.lo)}
    return dmrs.MRS(m.top, m.index, m.rels, m.hcons,
                    variables={v: p for v, p in m.variables.items() if v in used})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profile', required=True)
    ap.add_argument('--max-trees', type=int, default=5000)
    ap.add_argument('--out')
    args = ap.parse_args()

    forests = load_forests(args.profile)
    ts = itsdb.TestSuite(args.profile)
    parse = {r['parse-id']: r['i-id'] for r in ts['parse']}
    items = {r['i-id']: r['i-input'] for r in ts['item']}
    fg = FastGrammar(Grammar(args.grammar))
    parser = ace.ACEParser(DAT, executable=ACE,
                           cmdargs=['--disable-generalization', '--rooted-derivations', '--udx',
                                    '--timeout=120', '--max-chart-megabytes=8000',
                                    '--max-unpack-megabytes=8000'])
    tot = collections.Counter()
    report = []
    for pid in sorted(forests):
        forest, text = forests[pid], items[parse[pid]]
        n = forest.count()
        tot['items'] += 1
        if n > args.max_trees:
            tot['skipped: too many trees'] += 1
            continue
        trees = {}
        for _, tree in forest.trees():      # one root record per root condition: keep each tree once
            trees.setdefault(tree.key(), tree)
        valid, idiomatic, causes = {}, set(), collections.Counter()
        for key, tree in trees.items():
            orca_tree, toks = to_orca(tree)
            for root in ROOTS:              # the first root condition that holds, as ACE reports it
                fg.reset()
                try:
                    fs, _ = fg.replay_tree(Node(root, (orca_tree,)), toks)
                except ReplayFailure as e:
                    cause = str(e.cause)[:80]
                    if not e.where.endswith(root):
                        break               # failed below the root: no root condition will help
                    continue
                valid[key] = (root, to_pydelphin(extract(fg, fs)))
                fg.reset()
                try:                        # no idiom parts: nothing more to check
                    fg.replay_tree(Node(NON_IDIOM, (Node(root, (orca_tree,)),)), toks)
                except ReplayFailure:
                    idiomatic.add(key)
                break
            else:
                cause = 'no root condition holds'
            if key not in valid:
                causes[cause] += 1
        theirs = {}
        for res in parser.interact(text).results():
            d = res.derivation()
            theirs[ace_key(d.daughters[0])] = (d.entity, res.get('mrs'))
        plain = set(valid) - idiomatic
        both = plain & set(theirs)
        same_root = sum(valid[k][0] == theirs[k][0] for k in both)
        same_mrs = same_sem = same_all = 0
        for k in both:
            ours, full = valid[k][1], simplemrs.decode(theirs[k][1])
            ref = without_icons(full)
            same_all += bool(dmrs.is_isomorphic(ours, full, properties=True))
            same_mrs += bool(dmrs.is_isomorphic(without_icons(ours), ref, properties=True))
            same_sem += bool(dmrs.is_isomorphic(without_icons(ours), ref, properties=False))
        row = {'parse-id': pid, 'input': text, 'forest_records': n, 'forest_trees': len(trees),
               'orca': len(valid), 'orca_idiom_parts': len(idiomatic), 'ace': len(theirs),
               'both': len(both), 'orca_only': len(plain - set(theirs)),
               'ace_only': len(set(theirs) - plain),
               'ace_only_with_idiom_parts': len(set(theirs) & idiomatic),
               'same_root': same_root, 'same_mrs_with_icons': same_all, 'same_mrs': same_mrs, 'same_mrs_without_properties': same_sem,
               'failure_causes': causes.most_common(5)}
        report.append(row)
        tot['distinct trees in the forests'] += len(trees)
        tot['replayed by Orca'] += len(valid)
        tot['of these, with unlicensed idiom parts by Orca\'s test'] += len(idiomatic)
        tot['listed by ACE'] += len(theirs)
        tot['in both'] += len(both)
        tot['Orca only'] += row['orca_only']
        tot['ACE only'] += row['ace_only']
        tot['ACE only, rejected by Orca\'s idiom test'] += row['ace_only_with_idiom_parts']
        tot['same root condition (of both)'] += same_root
        tot['same MRS with ICONS (of both)'] += same_all
        tot['same MRS without ICONS (of both)'] += same_mrs
        tot['same MRS without ICONS and variable properties (of both)'] += same_sem
        equal = plain == set(theirs)
        tot['items where the two sets are equal'] += equal
        if not equal:
            print(f'DIFF {pid} {text!r}: trees {len(trees)}, Orca {len(plain)}, ACE {len(theirs)}, '
                  f'Orca only {row["orca_only"]}, ACE only {row["ace_only"]}', flush=True)
    parser.close()
    print(json.dumps(tot, indent=1))
    if args.out:
        with open(args.out, 'w') as f:
            json.dump({'totals': tot, 'items': report}, f, indent=1)


if __name__ == '__main__':
    main()
