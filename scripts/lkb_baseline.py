#!/usr/bin/env python3
"""LKB baseline on Redwoods dev (roadmap O104): LKB-FOS with ERG 2025, first-ranked analysis
(the ERG's MaxEnt model, redwoods.mem, as ACE uses), from raw text (the grammar's own REPP
preprocessing in LKB), MRS against gold, time per sentence on one core.

    lkb_baseline.py prepare [--shards 3]          -> data/lkb/dev-shard{K}.txt (id TAB sentence)
    lkb_baseline.py run --shard K [--edges N] [--timeout S]   -> data/lkb/dev-shard{K}.out (resumable by shard only)
    lkb_baseline.py score                          -> analysis/mrs/dev-lkb.json (eval format: records id, mrs, same MRS)

Limits: LKB has no memory limit like ACE's; a sentence stops at the edge limit (default 100,000)
or the time limit (default 300 s), and counts as no analysis. The LKB binary is a reference copy
(run only).
"""
import argparse
import re
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
ORCA = os.path.join(HERE, '..')
LKB = '/home/olga/delphin/tools/lkb_fos/lkb.linux_x86_64'
SCRIPT = os.path.join(ORCA, 'data/erg/2025/lkb/script')
OUT = os.path.join(ORCA, 'data/lkb')
DEV = os.path.join(ORCA, 'data/profiles-2025/dev')

LISP = r'''
(lkb::read-script-file-aux "%(script)s")
(setf lkb::*first-only-p* 1)
(setf lkb::*show-parse-p* nil)   ; do-parse-tty otherwise rebuilds the parse summary in a thread that races the next parse
(setf lkb::*maximum-number-of-edges* %(edges)d)
(with-open-file (in "%(inp)s" :external-format :utf-8)
  (with-open-file (out "%(out)s" :direction :output :if-exists :append :if-does-not-exist :create :external-format :utf-8)
    (loop for line = (read-line in nil) while line do
      (let* ((tab (position #\Tab line)) (id (subseq line 0 tab)) (s (subseq line (1+ tab)))
             (t0 (get-internal-real-time)) (status "ok"))
        (setf lkb::*parse-record* nil)
        (handler-case (sb-ext:with-timeout %(timeout)d (lkb::do-parse-tty s))
          (sb-ext:timeout () (setf status "timeout") (setf lkb::*parse-record* nil))
          (storage-condition () (setf status "memory") (setf lkb::*parse-record* nil))
          (error (e) (setf status (substitute #\Space #\Newline (format nil "error: ~a" e))) (setf lkb::*parse-record* nil)))
        (format out "@@ID ~a~%@@STATUS ~a~%@@N ~a~%@@T ~,4f~%@@MRS~%" id status (length lkb::*parse-record*)
                (/ (- (get-internal-real-time) t0) internal-time-units-per-second))
        (when lkb::*parse-record*
          (ignore-errors (mrs::output-mrs1 (mrs::extract-mrs (first lkb::*parse-record*)) 'mrs::simple out)))
        (format out "~%@@END~%")
        (finish-output out)
        (sb-ext:gc :full t)))))
'''


def gold_mrs():
    from delphin import tsdb
    gold = {}
    for prof in sorted(glob.glob(os.path.join(DEV, '*'))):
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        for line in tsdb.open(prof, 'result'):
            r = tsdb.split(line)
            if r[names.index('mrs')]:
                gold[f"{os.path.basename(prof)}/{r[names.index('parse-id')]}"] = r[names.index('mrs')]
    return gold


def items():
    """Dev items with a gold MRS (the 2,062 sentences every dev table uses)."""
    from delphin import tsdb
    out, gold = [], gold_mrs()
    for prof in sorted(glob.glob(os.path.join(DEV, '*'))):
        name = os.path.basename(prof)
        for row in tsdb.open(prof, 'item'):
            r = tsdb.split(row)
            names = [f.name for f in tsdb.read_schema(prof)['item']]
            sid = f"{name}/{r[names.index('i-id')]}"
            if sid in gold:
                out.append((sid, r[names.index('i-input')]))
    return out


def prepare(a):
    os.makedirs(OUT, exist_ok=True)
    its = items()
    for k in range(a.shards):
        with open(os.path.join(OUT, f'dev-shard{k}.txt'), 'w', encoding='utf-8') as f:
            for sid, s in its[k::a.shards]:
                f.write(f"{sid}\t{s.replace(chr(9), ' ').replace(chr(10), ' ')}\n")
    print(len(its), 'items in', a.shards, 'shards')


def run(a):
    """Runs LKB over the shard; when LKB dies on a sentence (an error in a worker thread quits the
    process), that sentence is recorded as 'crash' and LKB restarts after it."""
    inp, out = os.path.join(OUT, f'dev-shard{a.shard}.txt'), os.path.join(OUT, f'dev-shard{a.shard}.out')
    lisp, rest = os.path.join(OUT, f'dev-shard{a.shard}.lisp'), os.path.join(OUT, f'dev-shard{a.shard}.rest')
    text = LISP
    for k, v in {'script': SCRIPT, 'edges': a.edges, 'inp': rest, 'out': out, 'timeout': a.timeout}.items():
        text = text.replace('%%(%s)s' % k, str(v)).replace('%%(%s)d' % k, str(v))
    open(lisp, 'w').write(text)
    lines = open(inp, encoding='utf-8').read().splitlines()
    t0, crashes = time.time(), 0
    while True:
        done = {r['id'] for r in parse_out(out)} if os.path.exists(out) else set()
        todo = [l for l in lines if l.split('\t', 1)[0] not in done]
        if not todo:
            break
        open(rest, 'w', encoding='utf-8').write('\n'.join(todo) + '\n')
        with open(out + '.log', 'a') as log:
            subprocess.run([LKB, '--non-interactive', '--load', lisp], stdout=log, stderr=subprocess.STDOUT)
        done2 = {r['id'] for r in parse_out(out)}
        if len(done2) < len(lines):          # LKB quit before the end: the first sentence not done crashed it
            bad = next(l.split('\t', 1)[0] for l in todo if l.split('\t', 1)[0] not in done2)
            with open(out, 'a', encoding='utf-8') as f:
                f.write(f'@@ID {bad}\n@@STATUS crash\n@@N 0\n@@T 0\n@@MRS\n\n@@END\n')
            crashes += 1
    json.dump({'wall seconds (includes grammar loading after crashes)': time.time() - t0, 'edges': a.edges, 'timeout': a.timeout,
               'crashes': crashes}, open(out + '.json', 'w'))


def parse_out(path):
    recs, cur, mrs = [], None, None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if line.startswith('@@ID '):
            cur, mrs = {'id': line[5:]}, None
        elif line.startswith('@@STATUS '):
            cur['status'] = line[9:]
        elif line.startswith('@@N '):
            cur['parses'] = int(line[4:])
        elif line.startswith('@@T '):
            cur['seconds'] = float(line[4:])
        elif line == '@@MRS':
            mrs = []
        elif line == '@@END':
            cur['mrs'] = '\n'.join(mrs).strip() or None
            recs.append(cur)
            cur, mrs = None, None
        elif mrs is not None:
            mrs.append(line)
    return recs


def score(a):
    import collections
    from delphin import mrs as M, tsdb
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    gold = gold_mrs()
    recs, wall, st = [], 0.0, collections.Counter()
    for p in sorted(glob.glob(os.path.join(OUT, 'dev-shard*.out'))):
        recs += parse_out(p)
    for r in recs:
        st[r['status'] if not r['status'].startswith('error') else 'error'] += 1
        r['same MRS'] = False
        if r['mrs'] and r['id'] in gold:
            try:
                r['same MRS'] = bool(M.is_isomorphic(normalized(simplemrs.decode(re.sub(r'<-?\d+:-?\d+>', '', r['mrs']))),   # LKB glues spans to predicate names
                                                     normalized(simplemrs.decode(gold[r['id']])), properties=False))
            except Exception as e:
                r['mrs error'] = type(e).__name__
    secs = sum(r['seconds'] for r in recs)
    res = {'system': 'LKB-FOS 5.6, ERG 2025, first-ranked (redwoods.mem), raw text',
           'counts': {'sentences': len(recs), 'with MRS': sum(1 for r in recs if r['mrs']), 'same MRS': sum(r['same MRS'] for r in recs)},
           'status': dict(st), 'seconds per sentence (one core)': secs / max(1, len(recs)),
           'sentences per second': len(recs) / secs if secs else None,
           'limits': json.load(open(sorted(glob.glob(os.path.join(OUT, 'dev-shard*.out.json')))[0])) if glob.glob(os.path.join(OUT, 'dev-shard*.out.json')) else None,
           'records': recs}
    json.dump(res, open(os.path.join(ORCA, 'analysis/mrs/dev-lkb.json'), 'w'))
    print(json.dumps({k: v for k, v in res.items() if k != 'records'}, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--shards', type=int, default=3)
    r = sub.add_parser('run')
    r.add_argument('--shard', type=int, required=True)
    r.add_argument('--edges', type=int, default=100000)
    r.add_argument('--timeout', type=int, default=300)
    sub.add_parser('score')
    a = ap.parse_args()
    {'prepare': prepare, 'run': run, 'score': score}[a.cmd](a)
