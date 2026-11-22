#!/usr/bin/env python3
"""Compare the MRS read off replayed structures with the gold MRS.

With --pred, the predicted derivations (tagger labels, entries from the
lexicon) are replayed; without it, the gold derivations are. An MRS counts
as the same when it is isomorphic to the gold one (same predications,
arguments, and handle constraints up to renaming of variables); variable
properties such as tense and number are not compared yet.

Usage:
    compare_mrs.py --grammar ERG/english.tdl --profiles SPLIT_DIR --out FILE
                   [--gold DATA/dev.jsonl --pred MODEL/pred.jsonl] [--limit N]
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

from delphin import derivation, mrs as dmrs_mrs, predicate, tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from eval_trees import to_leaves  # noqa: E402
from orca.encoding import decode  # noqa: E402
from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402
from orca.tfs.lexicon import Lexicon, replay_with_entries  # noqa: E402
from orca.tfs.mrs import extract  # noqa: E402


from delphin.lnk import Lnk  # noqa: E402


def to_pydelphin(m, vpm_path=None):
    """Our extracted MRS as a PyDelphin MRS, with the top handle that the
    root contributes (a handle related to the local top by qeq). Variable
    properties go through the parsed grammar's VPM (`vpm_path`, else the one
    the extraction names, else the ERG's)."""
    rels = []
    lnks = m.get('lnk') or []
    for i, (pred, roles) in enumerate(m['rels']):
        args = {r: (v.strip('"') if r == 'CARG' else v) for r, v in roles.items() if r != 'LBL'}
        a, b = lnks[i] if i < len(lnks) else (-1, -1)
        lnk = Lnk.charspan(a, b) if a >= 0 and b >= 0 else None
        rels.append(dmrs_mrs.EP(predicate.normalize(pred), roles['LBL'], args=args, lnk=lnk))
    hcons = [dmrs_mrs.HCons('h0', 'qeq', m['top'])]
    hcons += [dmrs_mrs.HCons(a, 'qeq', b) for a, rel, b in m['hcons']]
    mapping = _vpm(vpm_path or m.get('vpm'))
    variables = {v: mapping.apply(v, p)[1] for v, p in m.get('props', {}).items()}
    icons = [dmrs_mrs.ICons(a, rel, b) for a, rel, b in m.get('icons', [])]
    return dmrs_mrs.MRS('h0', m['index'], rels, hcons, icons=icons, variables=variables)


_VPM = {}
ERG_VPM = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data/erg/2025/semi.vpm')


def _vpm(path=None):
    """A grammar's variable property mapping (grammar feature paths to MRS
    properties), loaded once per file; the ERG's by default."""
    path = os.path.normpath(path or ERG_VPM)
    if path not in _VPM:
        from delphin import vpm
        _VPM[path] = vpm.load(path)
    return _VPM[path]


def normalized(m, icons=False):
    """Predicates normalized, variable properties dropped; ICONS (information
    structure) dropped unless icons=True, as in every comparison so far."""
    rels = [dmrs_mrs.EP(predicate.normalize(ep.predicate), ep.label, args=dict(ep.args)) for ep in m.rels]
    return dmrs_mrs.MRS(m.top, m.index, rels, m.hcons, icons=m.icons if icons else None)


def describe(m):
    return sorted(f"{ep.predicate}({','.join(sorted(ep.args))})" for ep in m.rels)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--pred')
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    g = Grammar(args.grammar)
    lexicon = Lexicon(g, os.path.dirname(args.grammar))
    gold = {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = (
                        rec[names.index('derivation')], rec[names.index('mrs')])
    preds = None
    if args.pred:
        with open(args.pred, encoding='utf-8') as f:
            preds = [json.loads(line) for line in f]
    items = preds if preds is not None else [{'id': k} for k in gold]
    if args.limit:
        items = items[:args.limit]

    st = collections.Counter()
    by_outcome = collections.defaultdict(collections.Counter)
    examples = []
    for it in items:
        deriv, gold_text = gold[it['id']]
        st['sentences'] += 1
        mark = g.u.mark()
        try:
            d = derivation.from_string(deriv)
            if preds is None:
                fs = g.replay(d.daughters[0])
            else:
                toks = [t.tfs for term in d.terminals() for t in (term.tokens or [])]
                fs, _ = replay_with_entries(g, lexicon, decode(to_leaves(it['forms'], it['leaf'], it['tree'])), toks)
            ours = to_pydelphin(extract(g, fs))
        except (ReplayFailure, Exception) as e:
            st['no structure'] += 1
            by_outcome[it.get('outcome', 'gold derivation')]['no structure'] += 1
            del g.u.trail[mark:]
            continue
        del g.u.trail[mark:]
        st['structure built'] += 1
        try:
            ref = normalized(simplemrs.decode(gold_text))
            same = dmrs_mrs.is_isomorphic(ours, ref, properties=False)
        except Exception as e:
            st['gold MRS unreadable'] += 1
            continue
        st['same MRS as gold'] += same
        by_outcome[it.get('outcome', 'gold derivation')]['same MRS' if same else 'different MRS'] += 1
        if not same and len(examples) < 8:
            a, b = describe(ours), describe(ref)
            examples.append({'id': it['id'], 'only ours': [x for x in a if x not in b][:6],
                             'only gold': [x for x in b if x not in a][:6],
                             'counts': [len(ours.rels), len(ref.rels), len(ours.hcons), len(ref.hcons)]})
    result = {'stats': dict(st), 'by_outcome': {k: dict(v) for k, v in by_outcome.items()},
              'examples_of_differences': examples}
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
