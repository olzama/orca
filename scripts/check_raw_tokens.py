#!/usr/bin/env python3
"""How well do tokens from raw text (orca.tokens, via ACE's preprocessing)
stand in for the treebank's own tokens?

For each sentence of a split: run the raw input through the grammar's
preprocessing, compare the forms with the gold forms, and replay the gold
derivation over the raw-text tokens; is the MRS the gold MRS?

Usage:
    check_raw_tokens.py --grammar ERG/english.tdl --profiles SPLIT_DIR --gold DATA/dev.jsonl
                        --ace ACE --dat ERG.dat --out FILE.json [--workers 6] [--limit N]
"""
import argparse
import collections
import concurrent.futures
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

_W = {}


def raw_inputs(split_dir):
    """id (profile/parse-id) -> raw sentence."""
    from delphin import tsdb
    out = {}
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        items = {}
        names = [f.name for f in tsdb.read_schema(prof)['item']]
        with tsdb.open(prof, 'item') as rows:
            for line in rows:
                rec = tsdb.split(line)
                items[rec[names.index('i-id')]] = rec[names.index('i-input')]
        names = [f.name for f in tsdb.read_schema(prof)['parse']]
        with tsdb.open(prof, 'parse') as rows:
            for line in rows:
                rec = tsdb.split(line)
                out[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = items[rec[names.index('i-id')]]
    return out


def init(args):
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    g = Grammar(args.grammar)
    _W['fg'], _W['lx'], _W['args'] = FastGrammar(g), Lexicon(g, os.path.dirname(args.grammar)), args
    from orca.tokens import known_words
    _W['known'] = known_words(_W['lx'])


def check(item):
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized, to_pydelphin
    from eval_trees import to_leaves
    from orca.encoding import decode
    from orca.tfs.fast import extract
    from orca.tfs.lexicon import replay_with_entries
    from orca.tokens import lattice_path, token_chart
    sid, text, forms, leaf, tree, gold_mrs = item
    fg, lx, args = _W['fg'], _W['lx'], _W['args']
    r = {'id': sid}
    try:
        path = lattice_path(token_chart(text, args.ace, args.dat), _W['known'])
    except Exception as e:
        r['error'] = f'tokens: {type(e).__name__}'
        return r
    got = [p[0] for p in path]
    r['same length'] = len(got) == len(forms)
    r['same forms'] = got == [f.replace('\\/', '/') for f in forms]
    r['same forms ignoring case'] = [f.lower() for f in got] == [f.lower() for f in forms]
    if not r['same length']:
        r['forms'] = [got, forms]
        return r
    if not r['same forms']:
        r['diff'] = [(a, b) for a, b in zip(got, forms) if a != b][:5]
    fg.reset()
    try:
        fs, _ = replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), [p[1] for p in path])
        r['replays'] = True
        m = to_pydelphin(extract(fg, fs))
        r['same MRS'] = bool(M.is_isomorphic(m, normalized(simplemrs.decode(gold_mrs)), properties=False))
    except Exception as e:
        r['replays'] = False
        r['error'] = str(e)[:200]
    return r


def main():
    ap = argparse.ArgumentParser()
    for a in ('--grammar', '--profiles', '--gold', '--ace', '--dat', '--out'):
        ap.add_argument(a, required=True)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    from delphin import tsdb
    from llm_label import read
    raw = raw_inputs(args.profiles)
    gold_mrs = {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold_mrs[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
    sents = read(args.gold)[:args.limit]
    items = [(s['id'], raw[s['id']], s['forms'], s['leaf'], s['tree'], gold_mrs[s['id']]) for s in sents]
    with concurrent.futures.ProcessPoolExecutor(args.workers, initializer=init, initargs=(args,)) as pool:
        recs = list(pool.map(check, items, chunksize=8))
    c = collections.Counter()
    for r in recs:
        c['sentences'] += 1
        for k in ('same length', 'same forms', 'same forms ignoring case', 'replays', 'same MRS'):
            c[k] += bool(r.get(k))
    out = {'counts': dict(c), 'records': recs}
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(dict(c), indent=1))


if __name__ == '__main__':
    main()
