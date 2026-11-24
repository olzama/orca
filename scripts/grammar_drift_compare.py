#!/usr/bin/env python3
"""Compare two repair_bench runs of the same cached tagger output against two grammar
versions (roadmap O91), and find out why sentences analyzed under one version fail
under the other.

For every sentence analyzed under the reference grammar (A) but not under the other (B),
the derivation A chose is replayed under B and the first failure is recorded:
  missing name   the derivation uses a type, rule or root condition B lacks
  no entry       B's lexicon has no entry of that type for the word
  unification    a rule or root condition fails to unify (path and types given)
MRS agreement between the two runs (where both have an analysis) is reported too;
gold is not used for B, since the gold MRSs are made with A's grammar.

Usage:
    grammar_drift_compare.py --a analysis/grammar-drift/dev-2025.json --b analysis/grammar-drift/dev-2020.json \
        --b-grammar data/erg/2020-orca/english.tdl --labels analysis/grammar-drift/labels-2020.json \
        --out analysis/grammar-drift/compare-2025-2020.json
"""
import argparse
import collections
import json
import os
import pickle
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--b-grammar', required=True)
    ap.add_argument('--labels', required=True, help='grammar_drift.py output for B (names B lacks)')
    ap.add_argument('--cache', default='data/bench/dev-debertav3large-tags.pkl')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    from eval_trees import to_leaves
    from grammar_drift import names_of
    from orca.encoding import decode
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar, ReplayFailure
    from orca.tfs.lexicon import Lexicon, replay_with_entries
    A, B = (json.load(open(f))['records'] for f in (a.a, a.b))
    missing = {k.split(':', 1)[1] for k in json.load(open(a.labels))['counterparts']}
    items = pickle.load(open(a.cache, 'rb'))['items']
    g = Grammar(a.b_grammar)
    lx = Lexicon(g, os.path.dirname(a.b_grammar))
    lx.locate_missing = True
    fg = FastGrammar(g)
    for name, st in g.status.items():
        if st in ('rule', 'lex-rule'):
            fg.instance(name)

    def acc(r):
        return bool(r.get('kbest'))

    out = collections.Counter()
    for sid in A:
        ra, rb = A[sid], B.get(sid, {})
        out['sentences'] += 1
        out['A: first guess accepted'] += ra.get('outcome', '').startswith('accepted at first')
        out['B: first guess accepted'] += rb.get('outcome', '').startswith('accepted at first')
        out['A: any analysis'] += acc(ra)
        out['B: any analysis'] += acc(rb)
        out['A: replays'] += ra.get('replays', 0)
        out['B: replays'] += rb.get('replays', 0)
        if acc(ra) and acc(rb):
            out['both analyzed'] += 1
            try:
                same = M.is_isomorphic(normalized(simplemrs.decode(ra['mrs'])), normalized(simplemrs.decode(rb['mrs'])), properties=False)
            except Exception:
                same = False
            out['both analyzed: same MRS'] += same
        elif acc(rb) and not acc(ra):
            out['B only'] += 1

    causes, examples = collections.Counter(), collections.defaultdict(list)
    for sid, ra in A.items():
        if not acc(ra) or acc(B.get(sid, {})):
            continue
        leaf, tree = ra['kbest'][ra['chosen']][0], ra['kbest'][ra['chosen']][1]
        used = {nm for kind, labs in (('leaf', leaf), ('tree', tree)) for lab in labs for _, nm in names_of(kind, lab)}
        gone = sorted(used & missing)
        if gone:
            cause = 'chosen derivation uses a name B lacks'
            detail = ' '.join(gone[:3])
        else:
            it = items[sid]
            forms = [q[0] for q in it['path']]
            fg.reset()
            try:
                replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), [q[1] for q in it['path']])
                cause, detail = 'replays under B (repair did not find it)', ''
            except ReplayFailure as e:
                c = str(e.cause)
                if 'missing' in c:
                    cause = 'missing name or entry in B'
                elif 'no entry' in c or 'lexical entry' in c:
                    cause = 'no lexical entry in B'
                else:
                    cause = 'unification failure in B'
                where = str(e.where).split()
                detail = (where[-1] if where else '') + ': ' + re.sub(r'\s+', ' ', c)[:120]
            except Exception as e:
                cause, detail = 'other error', repr(e)[:120]
        causes[cause] += 1
        examples[cause].append([sid, detail])
    tally = {c: collections.Counter(re.sub(r'"[^"]*"', '"…"', d) if c != 'chosen derivation uses a name B lacks' else d for _, d in ex).most_common(12)
             for c, ex in examples.items()}
    res = {'counts': dict(out), 'A analyzed, B not: why': dict(causes), 'most frequent details': tally, 'examples': {c: ex[:8] for c, ex in examples.items()},
           'all': examples}
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('counts', 'A analyzed, B not: why', 'most frequent details')}, indent=1))


if __name__ == '__main__':
    main()
