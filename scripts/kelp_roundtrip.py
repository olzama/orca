#!/usr/bin/env python3
"""Round trip: annotate a forest profile from a gold profile, write it, read it back.

For every item of the gold profile that has one accepted tree, the same tree
is chosen in the forest profile through Kelp's session (as decisions on full
chains), accepted, and written to the profile's relations. The profile is
then read back with PyDelphin and each stored derivation and MRS is compared
with the gold one. A second session is opened on the written profile to
check that it restores every item.

The forest profile is changed: run this on a copy.

Usage:
    kelp_roundtrip.py --grammar ERG_DIR/english.tdl --gold GOLD_PROFILE --profile FOREST_PROFILE_COPY
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))

from delphin import derivation, itsdb, mrs as dmrs  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from kelp.discriminants import spans  # noqa: E402
from kelp.docs import load_docs  # noqa: E402
from kelp.engine import Engine  # noqa: E402
from kelp.forest import Tree  # noqa: E402
from kelp.session import Session  # noqa: E402


def as_tree(d):
    kids = tuple(as_tree(c) for c in (d.daughters or []) if hasattr(c, 'entity'))
    return Tree(d.entity, d.start, d.end, kids)


def without_icons(m):
    used = {m.top, m.index} | {v for ep in m.rels for v in [ep.label, *ep.args.values()]} \
        | {v for hc in m.hcons for v in (hc.hi, hc.lo)}
    return dmrs.MRS(m.top, m.index, m.rels, m.hcons,
                    variables={v: p for v, p in m.variables.items() if v in used})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--gold', required=True)
    ap.add_argument('--profile', required=True)
    ap.add_argument('--out')
    args = ap.parse_args()

    docs = load_docs(os.path.dirname(os.path.abspath(args.grammar)))
    lextypes = {name: d['type'] for name, d in docs.items() if d['type'].endswith('_le')}
    engine = Engine(args.grammar)
    # limit=1: the grammar checks a tree only once it is the only one left
    session = Session(args.profile, engine=engine, limit=1, lextypes=lextypes, author='roundtrip')
    by_iid = {it.iid: it for it in session.items.values()}

    gold_ts = itsdb.TestSuite(args.gold)
    gold_pid = {r['parse-id']: r['i-id'] for r in gold_ts['parse']}
    active = {r['parse-id'] for r in gold_ts['tree'] if r['t-active'] == 1}
    gold = {}
    for r in gold_ts['result']:
        if r['parse-id'] in active:
            gold[gold_pid[r['parse-id']]] = r

    tot, problems = collections.Counter(), []
    for iid, rec in sorted(gold.items()):
        tot['gold items with one accepted tree'] += 1
        item = by_iid.get(iid)
        if item is None:
            tot['no forest for the item'] += 1
            continue
        d = derivation.from_string(rec['derivation'])
        target = spans(as_tree(d.daughters[0]), session.lexlabel)
        try:
            state = session.choose(item.pid, target)
            if state['remaining'] == 1 and state['checked']:
                session.act(item.pid, 'accept')
                tot['accepted'] += 1
            else:
                tot['not narrowed down to one licensed tree'] += 1
                problems.append((iid, f"remaining {state['remaining']}, checked {state['checked']}"))
        except ValueError as e:
            tot['gold tree not in the forest'] += 1
            problems.append((iid, str(e)))

    # read back with PyDelphin
    ts = itsdb.TestSuite(args.profile)
    iid_of = {r['parse-id']: r['i-id'] for r in ts['parse']}
    trees = {iid_of[r['parse-id']]: r for r in ts['tree']}
    prefs = collections.Counter(iid_of[r['parse-id']] for r in ts['preference'])
    for r in ts['result']:
        iid = iid_of[r['parse-id']]
        g = gold[iid]
        tot['results read back'] += 1
        ours, theirs = derivation.from_string(r['derivation']), derivation.from_string(g['derivation'])
        same = ours.entity == theirs.entity and as_tree(ours.daughters[0]).key() == as_tree(theirs.daughters[0]).key()
        tot['same derivation and root as gold'] += same
        a, b = without_icons(simplemrs.decode(r['mrs'])), without_icons(simplemrs.decode(g['mrs']))
        tot['same MRS as gold, without variable properties'] += bool(dmrs.is_isomorphic(a, b, properties=False))
        tot['same MRS as gold, with variable properties'] += bool(dmrs.is_isomorphic(a, b, properties=True))
        tot['tree row says one active tree'] += trees[iid]['t-active'] == 1 and prefs[iid] == 1
        if not same:
            problems.append((iid, 'derivation differs'))
    tot['decision rows'] = len(ts['decision'])

    # a new session on the written profile (no journal) restores the items
    journal = os.path.join(args.profile, 'kelp-journal.jsonl')
    again = Session(args.profile, journal=journal + '.none', engine=engine, limit=1, lextypes=lextypes)
    for it in again.items.values():
        before = session.items[it.pid]
        if before.status:
            tot['items restored from the relations'] += (it.status == before.status
                                                         and it.constraints == before.constraints)
    print(json.dumps(tot, indent=1))
    for p in problems[:20]:
        print('PROBLEM', *p)
    if args.out:
        with open(args.out, 'w') as f:
            json.dump({'totals': tot, 'problems': problems}, f, indent=1)


if __name__ == '__main__':
    main()
