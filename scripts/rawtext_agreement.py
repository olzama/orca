#!/usr/bin/env python3
"""Agreement between Orca's confident raw-text analyses and ACE (roadmap O82, before training).

The raw-text run (scripts/rawtext.py) sent only the least certain third of Orca's analyses to ACE;
the silver data for the rest comes from Orca alone. This draws a random sample (fixed seed) of those
confident, Orca-origin sentences per source, parses them with full ACE first-best (same settings as
the raw-text ACE step), and compares ACE's MRS with Orca's (normalized, isomorphism, properties off,
as the evaluation does). The routed third's agreement, from data/rawtext/silver/report.json, is
repeated for comparison.

Usage:
    rawtext_agreement.py run [--n 1000] [--workers 3] [--chunk 250] [--limit N]   -> data/rawtext/agreement/report.json
"""
import argparse
import glob
import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from rawtext import OUT, ROOT, load_parses, _free_gb  # noqa: E402

ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
DAT = os.path.join(ROOT, 'data/ace/erg-2025.dat')


def confident(source):
    """Sentences not sent to ACE whose silver came from Orca (accepted replay analysis with labels)."""
    d = os.path.join(OUT, source)
    P = load_parses(source)
    sent = {l.strip() for l in open(os.path.join(d, 'to-ace.txt')) if l.strip()}
    return P, sorted(i for i, r in P.items() if i not in sent and r.get('mode used') != 'chart'
                     and int(r.get('accepted') or 0) > 0 and r.get('labels') and r.get('mrs'))


def run(a):
    from delphin import tsdb, mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    base = os.path.join(OUT, 'agreement' + ('-test' if a.limit else ''))
    os.makedirs(base, exist_ok=True)
    R = glob.glob(os.path.join(ROOT, 'data/profiles-2025/dev/*/relations'))[0]
    silver = json.load(open(os.path.join(OUT, 'silver', 'report.json')))
    report = {'what': 'Orca confident (not routed to ACE, Orca-origin silver) vs full ACE first-best, random sample per source, seed 20261124',
              'ace settings': f'-1 --timeout={a.timeout} --max-chart-megabytes={a.mb} --max-unpack-megabytes={a.mb + 2000}'}
    for source in a.sources:
        P, pool = confident(source)
        rng = random.Random(20261124)
        sample = rng.sample(pool, min(a.limit or a.n, len(pool)))
        d = os.path.join(base, source)
        os.makedirs(d, exist_ok=True)
        chunks = [sample[i:i + a.chunk] for i in range(0, len(sample), a.chunk)]
        procs, profs = [], []
        for c, chunk in enumerate(chunks):
            prof = os.path.join(d, f'{source}-{c:03d}')
            profs.append((prof, chunk))
            if os.path.exists(os.path.join(prof, 'parse')) and os.path.getsize(os.path.join(prof, 'parse')) > 0:
                continue
            txt = prof + '.txt'
            with open(txt, 'w') as o:
                for i in chunk:
                    o.write(P[i]['text'] + '\n')
            subprocess.run([os.path.join(ROOT, '.venv/bin/delphin'), 'mkprof', '--input', txt, '--relations', R, prof],
                           check=True, stdout=subprocess.DEVNULL)
            while len([p for p in procs if p.poll() is None]) >= a.workers or _free_gb() < 12:
                time.sleep(5)
            log = open(prof + '.log', 'w')
            procs.append(subprocess.Popen([os.path.join(ROOT, '.venv/bin/delphin'), 'process', '-g', DAT, '--executable', ACE,
                                           f'--options=-1 --timeout={a.timeout} --max-chart-megabytes={a.mb} --max-unpack-megabytes={a.mb + 2000}',
                                           prof], stdout=log, stderr=log))
        for p in procs:
            p.wait()
        n = parsed = same = 0
        for prof, chunk in profs:
            ace = {}
            names = [f.name for f in tsdb.read_schema(prof)['result']]
            with tsdb.open(prof, 'result') as rows:
                for line in rows:
                    rec = tsdb.split(line)
                    if rec[names.index('mrs')]:
                        ace[int(rec[names.index('parse-id')])] = rec[names.index('mrs')]
            for k, sid in enumerate(chunk, 1):
                n += 1
                if k not in ace:
                    continue
                parsed += 1
                try:
                    ok = M.is_isomorphic(normalized(simplemrs.decode(P[sid]['mrs'])), normalized(simplemrs.decode(ace[k])), properties=False)
                except Exception:
                    ok = False
                same += bool(ok)
        s = silver.get(source, {})
        report[source] = {'confident pool (Orca-origin silver, not routed)': len(pool), 'sampled': n, 'ACE parsed': parsed,
                          'same MRS as ACE': same, 'share of both parsed': round(same / parsed, 4) if parsed else None,
                          'for comparison, routed (least certain) third': {'both parsed': s.get('both Orca (replay) and ACE'),
                                                                           'same MRS': s.get('Orca same as ACE')}}
        print(source, report[source], flush=True)
    json.dump(report, open(os.path.join(base, 'report.json'), 'w'), indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('run',))
    ap.add_argument('--sources', nargs='+', default=['gutenberg', 'wikipedia'])
    ap.add_argument('--n', type=int, default=1000)
    ap.add_argument('--limit', type=int, default=0, help='test run: only this many per source, into agreement-test/')
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--chunk', type=int, default=250)
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--mb', type=int, default=12000)
    a = ap.parse_args()
    run(a)


if __name__ == '__main__':
    main()
