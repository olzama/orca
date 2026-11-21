#!/usr/bin/env python3
"""Replace the word forms of encoded sentences by the text as typed.

The treebank's forms depend on the analysis: a token analyzed with a generic
name entry keeps its case, other tokens are lower-cased by the grammar's
token mapping. From raw text the analysis is not known when the tagger runs,
so training on those forms leaks the answer. Here each token's form becomes
the slice of the original input given by its character span (+FROM, +TO),
which is also what orca.tokens gives for new text.

Usage:
    surface_forms.py --encoded IN.jsonl --out OUT.jsonl --profiles DIR [DIR ...] [--jobs N]
"""
import argparse
import glob
import json
import multiprocessing as mp
import os
import re
import sys

from delphin import derivation, tsdb

SPAN = re.compile(r'\+FROM (?:#\d+=)?\\?"(\d+)\\?".*?\+TO (?:#\d+=)?\\?"(\d+)\\?"')


def spans(der):
    """Character spans of the tokens of a derivation, in order."""
    out = []

    def walk(node):
        kids = node.daughters
        if kids and all(isinstance(d, derivation.UDFTerminal) for d in kids):
            for tok in kids[0].tokens or []:
                m = SPAN.search(tok.tfs or '')
                out.append((int(m.group(1)), int(m.group(2))) if m else None)
            return
        for d in kids:
            walk(d)

    walk(der)
    return out


def profile_forms(prof):
    """{id: [form, ...]} for one profile."""
    res = {}
    try:
        items = {}
        inames = [f.name for f in tsdb.read_schema(prof)['item']]
        with tsdb.open(prof, 'item') as rows:
            for line in rows:
                r = tsdb.split(line)
                items[r[inames.index('i-id')]] = r[inames.index('i-input')]
        pnames = [f.name for f in tsdb.read_schema(prof)['parse']]
        p2i = {}
        with tsdb.open(prof, 'parse') as rows:
            for line in rows:
                r = tsdb.split(line)
                p2i[r[pnames.index('parse-id')]] = r[pnames.index('i-id')]
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        i_der, i_pid = names.index('derivation'), names.index('parse-id')
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                if not r[i_der]:
                    continue
                text = items.get(p2i.get(r[i_pid]))
                if text is None:
                    continue
                try:
                    sp = spans(derivation.from_string(r[i_der]))
                except Exception:
                    continue
                if any(s is None for s in sp):
                    continue
                res[f'{os.path.basename(prof)}/{r[i_pid]}'] = [text[a:b] for a, b in sp]
    except Exception as exc:
        print(f'skip {prof}: {exc}', file=sys.stderr)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--encoded', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--profiles', nargs='+', required=True, help='directories holding profiles')
    ap.add_argument('--jobs', type=int, default=8)
    args = ap.parse_args()
    profs = [p for d in args.profiles for p in sorted(glob.glob(os.path.join(d, '*')))
             if os.path.exists(os.path.join(p, 'relations'))]
    forms = {}
    with mp.Pool(args.jobs) as pool:
        for res in pool.imap_unordered(profile_forms, profs):
            forms.update(res)
    st = {'sentences': 0, 'replaced': 0, 'missing': 0, 'length differs': 0, 'empty form': 0, 'forms changed': 0}
    with open(args.encoded, encoding='utf-8') as f, open(args.out, 'w', encoding='utf-8') as out:
        for line in f:
            r = json.loads(line)
            st['sentences'] += 1
            new = forms.get(r['id'])
            if new is None:
                st['missing'] += 1
            elif len(new) != len(r['tokens']):
                st['length differs'] += 1
            elif any(not x.strip() for x in new):
                st['empty form'] += 1
            else:
                st['replaced'] += 1
                for t, x in zip(r['tokens'], new):
                    st['forms changed'] += t['form'] != x
                    t['form'] = x
            out.write(json.dumps(r, ensure_ascii=False) + '\n')
    print(json.dumps(st, indent=1))


if __name__ == '__main__':
    main()
