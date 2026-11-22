#!/usr/bin/env python3
"""Exact MRS with and without variable properties.

Usage: check_properties.py EVAL.json PROFILES_DIR [OUT.json]
(EVAL from orca_parse --save-mrs)."""
import json, glob, os, sys, collections
from delphin import tsdb, predicate
from delphin.codecs import simplemrs
from delphin import mrs as M
evalf, profdir = sys.argv[1], sys.argv[2]
gold = {}
for prof in sorted(glob.glob(os.path.join(profdir, '*'))):
    if not os.path.exists(os.path.join(prof, 'relations')): continue
    names = [f.name for f in tsdb.read_schema(prof)['result']]
    with tsdb.open(prof, 'result') as rows:
        for line in rows:
            rec = tsdb.split(line)
            if rec[names.index('derivation')]:
                gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
SHARED = None
def norm(m, keep=None):
    vs = {v: {k: x for k, x in p.items() if keep is None or k in keep} for v, p in m.variables.items()}
    rels = [M.EP(predicate.normalize(ep.predicate), ep.label, args=dict(ep.args)) for ep in m.rels]
    return M.MRS(m.top, m.index, rels, m.hcons, variables=vs)
d = json.load(open(evalf))
propnames_a = collections.Counter(); propnames_g = collections.Counter()
same = 0; keep = 0; diffs = collections.Counter(); examples = []
for r in d['records']:
    if str(r.get('same MRS')) != 'True' or not r.get('mrs'): continue
    same += 1
    a0 = simplemrs.decode(r['mrs']); g0 = simplemrs.decode(gold[r['id']])
    ka = {k for p in a0.variables.values() for k in p}; kg = {k for p in g0.variables.values() for k in p}
    propnames_a.update(ka); propnames_g.update(kg)
    a = norm(a0, ka & kg); g = norm(g0, ka & kg)
    if M.is_isomorphic(a, g, properties=True):
        keep += 1; continue
    # find differing properties: map via predicate+role of ARG0
    def props(m):
        out = collections.Counter()
        for ep in m.rels:
            v = ep.args.get('ARG0')
            if v and v in m.variables:
                for k, val in m.variables[v].items():
                    out[(ep.predicate, k, val.lower())] += 1
        idx = m.variables.get(m.index, {})
        for k, val in idx.items(): out[('INDEX', k, val.lower())] += 1
        return out
    pa, pg = props(a), props(g)
    for key in (pa - pg): diffs[(key[1], key[0] if key[0]=='INDEX' else '', 'orca='+key[2])] += 1
    if len(examples) < 12: examples.append((r['id'], sorted((pa - pg).items())[:3], sorted((pg - pa).items())[:3]))
print('orca props', propnames_a); print('gold props', propnames_g)
print('same MRS (no properties):', same, ' also same with properties:', keep)
for k, v in diffs.most_common(25): print(v, k)
for e in examples: print(e)

# per-sentence summary: which property names differ, for the walkthrough page
by_sent = collections.Counter()
for r in d['records']:
    if str(r.get('same MRS')) != 'True' or not r.get('mrs'):
        continue
    a0 = simplemrs.decode(r['mrs']); g0 = simplemrs.decode(gold[r['id']])
    if M.is_isomorphic(norm(a0), norm(g0), properties=True):
        continue
    names = set()
    va = {ep.predicate: a0.variables.get(ep.args.get('ARG0'), {}) for ep in a0.rels}
    vg = {ep.predicate: g0.variables.get(ep.args.get('ARG0'), {}) for ep in g0.rels}
    for p in set(va) | set(vg):
        x, y = va.get(p, {}), vg.get(p, {})
        names |= {k for k in set(x) | set(y) if x.get(k, '').lower() != y.get(k, '').lower()}
    kind = 'sentence force' if 'SF' in names else 'tense or aspect' if names & {'TENSE', 'MOOD', 'PROG', 'PERF'} else 'number, person or gender' if names & {'NUM', 'PERS', 'GEND'} else 'other'
    by_sent[kind] += 1
out = {'sentences': len(d['records']), 'same without properties': same, 'same with properties': keep, 'differ by kind': dict(by_sent)}
print(out)
if len(sys.argv) > 3:
    json.dump(out, open(sys.argv[3], 'w'), indent=1)
