#!/usr/bin/env python3
"""Meaning of the derivations an LLM repair run got accepted: replay each
one, compare its MRS with gold (exact, and predicate/link precision and
recall), by sentence length.

Usage: score_llm_repair.py --grammar ERG/english.tdl --profiles SPLIT_DIR LOG.jsonl [LOG.jsonl ...]
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
sys.setrecursionlimit(20000)

from delphin import mrs as M, tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from compare_mrs import normalized, to_pydelphin  # noqa: E402
from llm_label import parse  # noqa: E402
from orca.tfs.fast import FastGrammar, extract  # noqa: E402
from orca.tfs.grammar import Grammar  # noqa: E402
from orca.tfs.lexicon import Lexicon, replay_with_entries  # noqa: E402
from replay_predictions import gold_tokens  # noqa: E402
from score_semantics import graph  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('logs', nargs='+')
    args = ap.parse_args()
    g = Grammar(args.grammar)
    fg, lx = FastGrammar(g), Lexicon(g, os.path.dirname(args.grammar))
    toks = gold_tokens(args.profiles)
    gold = {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = normalized(
                        simplemrs.decode(rec[names.index('mrs')]))
    out = {}
    for path in args.logs:
        by = collections.defaultdict(collections.Counter)
        for line in open(path, encoding='utf-8'):
            r = json.loads(line)
            band = 'under 20 words' if len(r['forms']) < 20 else '20 words or more'
            for b in (band, 'all'):
                by[b]['sentences'] += 1
            if r['final'][0] != 'accepted':
                continue
            fg.reset()
            fs, _ = replay_with_entries(fg, lx, parse(r['derivation']), toks[r['id']])
            m, ref = to_pydelphin(extract(fg, fs)), gold[r['id']]
            sp, sl = graph(m)
            gp, gl = graph(ref)
            for b in (band, 'all'):
                c = by[b]
                c['accepted'] += 1
                c['same MRS'] += M.is_isomorphic(m, ref, properties=False)
                c['sys preds'] += sum(sp.values()); c['gold preds'] += sum(gp.values())
                c['ok preds'] += sum((sp & gp).values())
                c['sys links'] += sum(sl.values()); c['gold links'] += sum(gl.values())
                c['ok links'] += sum((sl & gl).values())
        res = {}
        for b, c in by.items():
            d = {k: c[k] for k in ('sentences', 'accepted', 'same MRS')}
            for kind in ('preds', 'links'):
                p = c[f'ok {kind}'] / c[f'sys {kind}'] if c[f'sys {kind}'] else 0
                rc = c[f'ok {kind}'] / c[f'gold {kind}'] if c[f'gold {kind}'] else 0
                d[kind] = {'precision': round(p, 3), 'recall': round(rc, 3),
                           'f1': round(2 * p * rc / (p + rc), 3) if p + rc else 0}
            res[b] = d
        out[path] = res
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
