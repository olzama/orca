#!/usr/bin/env python3
"""Orca (replay, chart, fallback) and ACE on Redwoods dev: by sentence length, and precision
on the sentences each system analyzes. Roadmap O76 (the 'Orca and ACE' walkthrough section).

Per system, from its eval file (records with 'mrs' and 'same MRS'):
  - by length band (tokens from data/encoded-2025/dev.jsonl, the bands of make_page.results()):
    sentences, same MRS (exact meaning, properties not compared), with MRS (any analysis);
  - precision, over the sentences the system analyzes: share with the right meaning, and
    predicate and link precision against gold (score_semantics.graph: DMRS predicate and
    link multisets, as score_tables.py computes them for the older systems).

Usage: orca_ace_current.py [--out analysis/orca-ace/dev-current.json]
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

from delphin import tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from compare_mrs import normalized  # noqa: E402
from score_semantics import graph  # noqa: E402

ORCA = os.path.join(HERE, '..')
BANDS = ((0, 10, 'under 10'), (10, 20, '10 to 19'), (20, 30, '20 to 29'), (30, 10 ** 6, '30 and over'))
SYSTEMS = (('replay', 'analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-minprob001.json'),
           ('chart', 'analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-chart-0.001.json'),
           ('fallback', 'analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-fallback-0.001.json'),
           ('ace', 'analysis/mrs/dev-ace-final-as-eval.json'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ORCA, 'analysis/orca-ace/dev-current.json'))
    a = ap.parse_args()
    length = {}
    for l in open(os.path.join(ORCA, 'data/encoded-2025/dev.jsonl')):
        r = json.loads(l)
        length[r['id']] = len(r['tokens'])
    band = {sid: next(n for lo, hi, n in BANDS if lo <= k < hi) for sid, k in length.items()}
    gold = {}
    for prof in sorted(glob.glob(os.path.join(ORCA, 'data/profiles-2025/dev/*'))):
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                if r[names.index('mrs')]:
                    gold[f"{os.path.basename(prof)}/{r[names.index('parse-id')]}"] = graph(normalized(simplemrs.decode(r[names.index('mrs')])))
    out = {'bands': [b for _, _, b in BANDS], 'systems': {}}
    for name, path in SYSTEMS:
        recs = json.load(open(os.path.join(ORCA, path)))['records']
        by = collections.defaultdict(collections.Counter)
        prec = collections.Counter()
        for r in recs:
            sid = r['id']
            has = bool(r.get('mrs'))
            same = str(r.get('same MRS')) == 'True'
            for b in ('all', band[sid]):
                by[b]['sentences'] += 1
                by[b]['with MRS'] += has
                by[b]['same MRS'] += same
            if has and sid in gold:
                try:
                    sp, sl = graph(normalized(simplemrs.decode(r['mrs'])))
                except Exception:
                    prec['unreadable MRS'] += 1
                    continue
                gp, gl = gold[sid]
                prec['analyzed'] += 1
                prec['right meaning'] += same
                prec['sys preds'] += sum(sp.values())
                prec['ok preds'] += sum((sp & gp).values())
                prec['sys links'] += sum(sl.values())
                prec['ok links'] += sum((sl & gl).values())
        out['systems'][name] = {
            'file': path,
            'by band': {b: dict(by[b]) for b in ['all'] + out['bands']},
            'precision': {'analyzed': prec['analyzed'], 'right meaning': prec['right meaning'],
                          'unreadable MRS': prec['unreadable MRS'],
                          'predicate precision': prec['ok preds'] / prec['sys preds'] if prec['sys preds'] else None,
                          'link precision': prec['ok links'] / prec['sys links'] if prec['sys links'] else None}}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    for name, s in out['systems'].items():
        p = s['precision']
        print(name, {b: (v['same MRS'], v['with MRS'], v['sentences']) for b, v in s['by band'].items()},
              p['analyzed'], p['right meaning'], round(100 * p['predicate precision'], 1), round(100 * p['link precision'], 1))


if __name__ == '__main__':
    main()
