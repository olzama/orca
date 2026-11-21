#!/usr/bin/env python3
"""ACE's n best parses of treebank sentences, each labeled by whether its MRS
is the gold one: training data for a ranking model.

Reads the items and gold MRSs of every profile in a split (read only) and
writes one JSON line per sentence: id, input, gold MRS, and the n best
results (derivation, MRS, same_mrs). Resumable: sentences already in the
output are skipped.

Usage:
    ace_nbest.py --profiles SPLIT_DIR --out FILE.jsonl [--n 30] [--workers 4]
"""
import argparse
import glob
import json
import multiprocessing as mp
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
DAT = os.path.join(HERE, '..', 'data/ace/erg-2025.dat')
_P = {}


def items(split_dir):
    from delphin import tsdb
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        sch = tsdb.read_schema(prof)
        inames = [f.name for f in sch['item']]
        text = {}
        with tsdb.open(prof, 'item') as rows:
            for line in rows:
                r = tsdb.split(line)
                text[r[inames.index('i-id')]] = r[inames.index('i-input')]
        pnames = [f.name for f in sch['parse']]
        p2i = {}
        with tsdb.open(prof, 'parse') as rows:
            for line in rows:
                r = tsdb.split(line)
                p2i[r[pnames.index('parse-id')]] = r[pnames.index('i-id')]
        names = [f.name for f in sch['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                pid = r[names.index('parse-id')]
                if r[names.index('mrs')] and p2i.get(pid) in text:
                    yield {'id': f'{os.path.basename(prof)}/{pid}', 'input': text[p2i[pid]], 'gold': r[names.index('mrs')]}


def init(n, slim):
    from delphin import ace
    _P['slim'] = slim
    _P['parser'] = ace.ACEParser(DAT, executable=ACE, cmdargs=[f'-n', str(n), '--timeout=60', '--max-chart-megabytes=4000',
                                                               '--max-unpack-megabytes=5000'], stderr=open(os.devnull, 'w'))


def work(it):
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    try:
        resp = _P['parser'].interact(it['input'])
        res = resp.results()
    except Exception as e:
        return {**it, 'results': [], 'error': str(e)[:200]}
    try:
        g = normalized(simplemrs.decode(it['gold']))
    except Exception as e:               # a few treebank MRSs are not readable by pydelphin
        return {**it, 'results': [], 'error': f'gold MRS unreadable: {str(e)[:150]}'}
    out = []
    for r in res:
        try:
            m = normalized(simplemrs.decode(r['mrs']))
            same = bool(M.is_isomorphic(g, m, properties=False))
        except Exception:
            same = False
        rec = {'derivation': r['derivation'], 'same_mrs': same}
        if not _P['slim']:
            rec['mrs'] = r['mrs']
        out.append(rec)
    return {**it, 'results': out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=30)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--ids', help='file with one sentence id per line: parse only these')
    ap.add_argument('--slim', action='store_true', help='keep derivations and labels only, not the MRSs')
    args = ap.parse_args()
    done = set()
    if os.path.exists(args.out):
        for l in open(args.out):
            done.add(json.loads(l)['id'])
    only = set(open(args.ids).read().split()) if args.ids else None
    todo = [it for it in items(args.profiles) if it['id'] not in done and (only is None or it['id'] in only)]
    print(f'{len(todo):,} sentences to parse ({len(done):,} done)', flush=True)
    with mp.Pool(args.workers, initializer=init, initargs=(args.n, args.slim)) as pool, open(args.out, 'a') as f:
        for i, rec in enumerate(pool.imap_unordered(work, todo, chunksize=4), 1):
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            if i % 2000 == 0:
                f.flush()
                print(i, flush=True)


if __name__ == '__main__':
    main()
