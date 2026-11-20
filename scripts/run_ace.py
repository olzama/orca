#!/usr/bin/env python3
"""Baseline: parse the sentences of treebank profiles with ACE and keep its
first-ranked MRS and derivation, with timing.

PyDelphin does not pass on ACE's own notes (for example "hit RAM limit while
unpacking"), so a sentence without a result is recorded as "no analysis"
here; run ACE directly on such sentences to find the actual reason.

Usage:
    run_ace.py --ace ACE_BINARY --grammar GRAMMAR.dat --profiles SPLIT_DIR --out FILE.jsonl
"""
import argparse
import glob
import json
import os
import time

from delphin import ace, itsdb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ace', required=True)
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--memory', type=int, default=6000, help='megabytes for chart and for unpacking')
    ap.add_argument('--only', help='JSON lines file; parse only items that have no MRS there')
    args = ap.parse_args()
    items = []
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        ts = itsdb.TestSuite(prof)
        text = {r['i-id']: r['i-input'] for r in ts['item']}
        iid = {r['parse-id']: r['i-id'] for r in ts['parse']}
        for r in ts['result']:
            if r['derivation']:
                items.append((f"{os.path.basename(prof)}/{r['parse-id']}", text[iid[r['parse-id']]]))
    if args.only:
        with open(args.only, encoding='utf-8') as f:
            todo = {r['id'] for r in map(json.loads, f) if not r.get('mrs')}
        items = [it for it in items if it[0] in todo]
    cmd = ['-1', '--rooted-derivation', '--udx', '--max-words=1000', f'--timeout={args.timeout}',
           f'--max-chart-megabytes={args.memory}', f'--max-unpack-megabytes={args.memory}']
    with ace.ACEParser(args.grammar, cmdargs=cmd, executable=args.ace) as parser, \
            open(args.out, 'w', encoding='utf-8') as out:
        for sid, sentence in items:
            t0 = time.time()
            try:
                response = parser.interact(sentence)
                res = response.result(0) if response['results'] else None
                rec = {'id': sid, 'mrs': res['mrs'] if res else None,
                       'derivation': res['derivation'] if res else None,
                       'errors': response.get('errors') or [], 'notes': response.get('notes') or []}
                if not res:
                    text = ' '.join(rec['errors'] + rec['notes']).lower()
                    rec['failure'] = ('out of memory' if 'memory' in text or 'ram' in text
                                      else 'timeout' if 'timeout' in text or 'timed out' in text
                                      else 'no analysis' if not rec['errors'] else 'error')
            except Exception as e:
                rec = {'id': sid, 'mrs': None, 'derivation': None, 'error': str(e)[:200]}
            rec['seconds'] = time.time() - t0
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()


if __name__ == '__main__':
    main()
