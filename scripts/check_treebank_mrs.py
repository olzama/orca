#!/usr/bin/env python3
"""Replay a treebank's gold derivations (encoded, as filter_replayable.py keeps them)
with Orca and compare Orca's MRS with the treebank's, for any DELPH-IN grammar.

Usage: check_treebank_mrs.py --grammar TOP.tdl --profiles DIR --encoded REPLAYABLE.jsonl --out OUT.json
"""
import argparse
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


GLB = re.compile(r'^(glbtype\d+|g\(\d+\))$')


def glb_anon(m):
    """Predicates that are computed GLB types have arbitrary names (Orca glbtype50, LKB g(171)): one name for all."""
    from delphin import mrs as M
    rels = [M.EP('glb' if GLB.match(str(ep.predicate)) else ep.predicate, ep.label, args=dict(ep.args), lnk=ep.lnk)
            for ep in m.rels]
    return M.MRS(m.top, m.index, rels, m.hcons, icons=m.icons, variables=m.variables)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--encoded', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    import glob
    from delphin import mrs as M, tsdb
    from delphin.codecs import simplemrs
    from compare_mrs import normalized, to_pydelphin
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.fast import FastGrammar, extract
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon, replay_with_entries
    from replay_predictions import gold_tokens
    gold = {}
    for prof in sorted(glob.glob(os.path.join(a.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
    toks = gold_tokens(a.profiles)
    g = Grammar(a.grammar)
    fg, lx = FastGrammar(g), Lexicon(g, os.path.dirname(a.grammar))
    c, diffs = collections.Counter(), []
    for line in open(a.encoded):
        r = json.loads(line)
        c['sentences'] += 1
        forms, leaf, tree = labels_of(r['tokens'])
        fg.reset()
        try:
            fs, _ = replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), toks[r['id']])
            ours = to_pydelphin(extract(fg, fs))
        except Exception as e:
            c['replay or extraction failed'] += 1
            continue
        try:
            ref = simplemrs.decode(re.sub(r'CARG: ([^\s"\]]+)', r'CARG: "\1"', gold[r['id']]))   # older exports leave CARG values unquoted
        except Exception:
            c['treebank MRS unreadable'] += 1
            continue
        ours, ref = glb_anon(ours), glb_anon(ref)
        same = M.is_isomorphic(normalized(ours), normalized(ref), properties=False)
        withp = M.is_isomorphic(normalized(ours), normalized(ref), properties=True)
        withi = M.is_isomorphic(normalized(ours, icons=True), normalized(ref, icons=True), properties=True)
        c['same without properties'] += same
        c['same with properties'] += withp
        c['same with properties and ICONS'] += withi
        if not withi and len(diffs) < 40:
            diffs.append({'id': r['id'], 'same': bool(same), 'with properties': bool(withp)})
    out = {'counts': dict(c), 'examples': diffs}
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(out['counts'], indent=1))


if __name__ == '__main__':
    main()
