#!/usr/bin/env python3
"""Baseline: parse the sentences of treebank profiles with ACE and keep its
first-ranked MRS and derivation, with timing.

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
    cmd = ['-1', f'--timeout={args.timeout}', '--max-chart-megabytes=6000', '--max-unpack-megabytes=7000']
    with ace.ACEParser(args.grammar, cmdargs=cmd, executable=args.ace) as parser, \
            open(args.out, 'w', encoding='utf-8') as out:
        for sid, sentence in items:
            t0 = time.time()
            try:
                response = parser.interact(sentence)
                res = response.result(0) if response['results'] else None
                rec = {'id': sid, 'mrs': res['mrs'] if res else None,
                       'derivation': res['derivation'] if res else None}
            except Exception as e:
                rec = {'id': sid, 'mrs': None, 'derivation': None, 'error': str(e)[:200]}
            rec['seconds'] = time.time() - t0
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()


if __name__ == '__main__':
    main()
