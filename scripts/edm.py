#!/usr/bin/env python3
"""Elementary Dependency Match (Dridan and Oepen 2011) on Redwoods dev, the way
mtool (the MRP 2019/2020 scorer, score/edm.py) computes it.

Each MRS is converted to EDS (pydelphin). Per sentence, as sets:
  names       (span, predicate)
  arguments   (span of source, span of target, role)
  properties  (span, property, value): CARG and the variable properties
              (tense, number, ...) of each node
  tops        (span of the top node)
and precision, recall and F1 are micro-averaged over the corpus. Reported:
  EDM_N names, EDM_A arguments, EDM_P properties, EDM_NA names + arguments
  (predicate-argument structure only), EDM all four together (as mtool's "all").
A sentence without an analysis scores as an empty graph (recall loses, precision
does not), as mtool does with a missing system graph.

Usage:
    edm.py --profiles data/profiles-2025/dev --system NAME=EVAL.json [...] --out analysis/edm/dev.json
    edm.py ... --eds-dir DIR      also write native EDS files for cross-checking with mtool
"""
import argparse
import glob
import json
import os
import sys

from delphin import eds, tsdb
from delphin import predicate as P
from delphin.codecs import simplemrs, eds as edscodec


def gold_mrs(split_dir):
    out = {}
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    out[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
    return out


def to_eds(mrs_string):
    return eds.from_mrs(simplemrs.decode(mrs_string))


def tuples(e):
    if e is None:
        return set(), set(), set(), set()
    span = {n.id: (n.cfrom, n.cto) for n in e.nodes}
    names, args, props, tops = set(), set(), set(), set()
    for n in e.nodes:
        names.add((span[n.id], P.normalize(n.predicate)))
        if n.carg is not None:
            props.add((span[n.id], 'CARG', n.carg.strip('"')))
        for k, v in (n.properties or {}).items():
            props.add((span[n.id], k.upper(), str(v).lower()))
        for role, tgt in n.edges.items():
            if tgt in span:
                args.add((span[n.id], span[tgt], role.upper()))
    if e.top in span:
        tops.add(span[e.top])
    return names, args, props, tops


def prf(g, s, c):
    p = c / s if s else 0.0
    r = c / g if g else 0.0
    return {'g': g, 's': s, 'c': c, 'p': p, 'r': r, 'f': 2 * p * r / (p + r) if p + r else 0.0}


def score(gold, system):
    tot = {k: [0, 0, 0] for k in ('names', 'arguments', 'properties', 'tops')}
    n_missing = 0
    for sid, gm in gold.items():
        g = tuples(to_eds(gm))
        sm = system.get(sid)
        try:
            s = tuples(to_eds(sm)) if sm else tuples(None)
        except Exception:
            s = tuples(None)
        if not sm:
            n_missing += 1
        for k, gg, ss in zip(tot, g, s):
            tot[k][0] += len(gg)
            tot[k][1] += len(ss)
            tot[k][2] += len(gg & ss)
    res = {k: prf(*v) for k, v in tot.items()}
    na = [tot['names'][i] + tot['arguments'][i] for i in range(3)]
    al = [sum(tot[k][i] for k in tot) for i in range(3)]
    res['EDM_NA'] = prf(*na)
    res['EDM'] = prf(*al)
    res['sentences'] = len(gold)
    res['no analysis'] = n_missing
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--system', action='append', required=True, help='NAME=EVAL.json (records with id and mrs)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--eds-dir')
    a = ap.parse_args()
    gold = gold_mrs(a.profiles)
    out = {'gold sentences': len(gold), 'systems': {}}
    for spec in a.system:
        name, path = spec.split('=', 1)
        recs = json.load(open(path))['records']
        system = {r['id']: r['mrs'] for r in recs if r.get('mrs')}
        out['systems'][name] = score(gold, system)
        out['systems'][name]['file'] = path
        if a.eds_dir:
            os.makedirs(a.eds_dir, exist_ok=True)
            for tag, src in (('gold', gold), (name, system)):
                with open(os.path.join(a.eds_dir, f'{tag}.eds'), 'w') as f:
                    for i, sid in enumerate(sorted(gold)):
                        if sid in src:
                            try:
                                f.write(f'#{i + 1}\n' + edscodec.encode(to_eds(src[sid]), properties=True, lnk=True, indent=True) + '\n')
                            except Exception:
                                pass
        s = out['systems'][name]
        print(name, {k: round(100 * s[k]['f'], 2) for k in ('names', 'arguments', 'properties', 'tops', 'EDM_NA', 'EDM')}, file=sys.stderr)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
