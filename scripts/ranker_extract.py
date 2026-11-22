#!/usr/bin/env python3
"""Shrink ACE's n-best files (redwoods-train-ace30/500.jsonl) to what a ranking
model needs: per sentence, each derivation as a bare tree of rule and entry
names, and whether its MRS is the gold one.

The derivation strings carry each token's feature structure; those quoted
strings are dropped before parsing, keeping only the surface form.

Usage: ranker_extract.py IN.jsonl OUT.jsonl [--workers 6]
"""
import argparse
import json
import multiprocessing as mp
import re

QUOTED = re.compile(r'"(?:[^"\\]|\\.)*"')


def bare(deriv):
    """'(id rule score start end (...))' -> nested [name, children...]; leaves are [entry, form]."""
    first = [True]

    def keep(m):                      # keep the form string, drop the token feature structures
        s = m.group(0)
        return '"tok"' if s.startswith('"token') or len(s) > 60 else s
    s = QUOTED.sub(keep, deriv)
    toks = re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+', s)
    pos = 0

    def node():
        nonlocal pos
        assert toks[pos] == '('
        pos += 1
        items = []
        while toks[pos] != ')':
            if toks[pos] == '(':
                items.append(node())
            else:
                items.append(toks[pos])
                pos += 1
        pos += 1
        return items
    t = node()

    def clean(n):
        # (id name score start end children...) or ("form" id "tok" ...) or (root_name (...))
        heads = [x for x in n if not isinstance(x, list)]
        kids = [clean(x) for x in n if isinstance(x, list)]
        if heads and heads[0].startswith('"'):
            return heads[0].strip('"').lower()
        if len(heads) >= 2 and re.fullmatch(r'-?\d+', heads[0]):
            name = heads[1]
        else:
            name = heads[0]
        if kids and all(isinstance(k, str) for k in kids):
            return [name, ' '.join(kids)]          # lexical entry over its form(s)
        return [name] + kids
    return clean(t)


def work(line):
    r = json.loads(line)
    out = []
    for x in r.get('results', []):
        try:
            out.append([bare(x['derivation']), str(x.get('same_mrs')) == 'True'])
        except Exception:
            pass
    return json.dumps({'id': r['id'], 'n': len(out), 'gold_in': any(g for _, g in out), 'derivs': out}, separators=(',', ':'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    with open(a.inp) as f, open(a.out, 'w') as o, mp.Pool(a.workers) as pool:
        for i, s in enumerate(pool.imap(work, f, chunksize=8)):
            o.write(s + '\n')
            if i % 2000 == 0:
                print(i, flush=True)


if __name__ == '__main__':
    main()
