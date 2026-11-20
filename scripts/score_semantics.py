#!/usr/bin/env python3
"""Semantic accuracy of a parser's output against gold MRS.

Systems: ACE's first-ranked MRS (--ace FILE.jsonl from run_ace.py) and/or
the Orca pipeline (--pred FILE.jsonl of labels, replayed with entries).
Measures: share of sentences with an MRS, share whose MRS is isomorphic to
gold (variable properties not compared), and two graded scores over the
DMRS graph: F1 of predicates and F1 of links (head predicate, role, scope
relation, dependent predicate), counted as multisets over the whole set.

Usage:
    score_semantics.py --grammar ERG/english.tdl --profiles SPLIT_DIR --out FILE
                       [--ace ACE.jsonl] [--pred PRED.jsonl]
"""
import argparse
import collections
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from delphin import derivation, dmrs, mrs as M, tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from compare_mrs import normalized, to_pydelphin  # noqa: E402
from eval_trees import to_leaves  # noqa: E402
from orca.encoding import decode  # noqa: E402

BANDS = ((0, 10, 'under 10'), (10, 20, '10-19'), (20, 30, '20-29'), (30, 10 ** 6, '30 and over'))


def graph(m):
    """Multisets of predicates and of links of an MRS, via its DMRS."""
    d = dmrs.from_mrs(m)
    name = {n.id: n.predicate + (f'("{n.carg}")' if n.carg else '') for n in d.nodes}
    preds = collections.Counter(name.values())
    links = collections.Counter((name[l.start], l.role, l.post, name[l.end]) for l in d.links)
    return preds, links


def score(system, gold, lengths):
    st = collections.Counter()
    by = collections.defaultdict(collections.Counter)
    tp = collections.Counter()
    for sid, ref in gold.items():
        band = next(n for lo, hi, n in BANDS if lo <= lengths[sid] < hi)
        st['sentences'] += 1
        by[band]['sentences'] += 1
        gp, gl = graph(ref)
        tp['gold preds'] += sum(gp.values())
        tp['gold links'] += sum(gl.values())
        m = system.get(sid)
        if m is None:
            continue
        st['with MRS'] += 1
        by[band]['with MRS'] += 1
        try:
            same = M.is_isomorphic(m, ref, properties=False)
            sp, sl = graph(m)
        except Exception:
            st['unusable MRS'] += 1
            continue
        st['same MRS'] += same
        by[band]['same MRS'] += same
        tp['sys preds'] += sum(sp.values())
        tp['sys links'] += sum(sl.values())
        tp['ok preds'] += sum((sp & gp).values())
        tp['ok links'] += sum((sl & gl).values())

    def f1(kind):
        p = tp[f'ok {kind}'] / tp[f'sys {kind}'] if tp[f'sys {kind}'] else 0.0
        r = tp[f'ok {kind}'] / tp[f'gold {kind}'] if tp[f'gold {kind}'] else 0.0
        return {'precision': p, 'recall': r, 'f1': 2 * p * r / (p + r) if p + r else 0.0}

    n = st['sentences']
    return {'sentences': n, 'with_mrs': st['with MRS'], 'same_mrs': st['same MRS'],
            'same_mrs_share': st['same MRS'] / n, 'coverage': st['with MRS'] / n,
            'predicates': f1('preds'), 'links': f1('links'),
            'by_length': {b: dict(by[b]) for _, _, b in BANDS}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--ace')
    ap.add_argument('--pred')
    args = ap.parse_args()
    gold, derivs, lengths = {}, {}, {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    sid = f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"
                    gold[sid] = normalized(simplemrs.decode(rec[names.index('mrs')]))
                    derivs[sid] = rec[names.index('derivation')]
                    d = derivation.from_string(derivs[sid])
                    lengths[sid] = sum(len(t.tokens or [1]) for t in d.terminals())
    result = {}
    if args.ace:
        system, secs = {}, []
        with open(args.ace, encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                secs.append(r.get('seconds', 0))
                if r.get('mrs'):
                    try:
                        system[r['id']] = normalized(simplemrs.decode(r['mrs']))
                    except Exception:
                        pass
        result['ace'] = score(system, gold, lengths)
        result['ace']['seconds_total'] = sum(secs)
        result['ace']['seconds_max'] = max(secs) if secs else None
    if args.pred:
        from orca.tfs.grammar import Grammar
        from orca.tfs.lexicon import Lexicon, replay_with_entries
        from orca.tfs.mrs import extract
        g = Grammar(args.grammar)
        lexicon = Lexicon(g, os.path.dirname(args.grammar))
        system = {}
        with open(args.pred, encoding='utf-8') as f:
            for line in f:
                p = json.loads(line)
                d = derivation.from_string(derivs[p['id']])
                toks = [t.tfs for term in d.terminals() for t in (term.tokens or [])]
                mark = g.u.mark()
                try:
                    fs, _ = replay_with_entries(g, lexicon, decode(to_leaves(p['forms'], p['leaf'], p['tree'])), toks)
                    system[p['id']] = to_pydelphin(extract(g, fs))
                except Exception:
                    pass
                del g.u.trail[mark:]
        result['orca'] = score(system, gold, lengths)
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
