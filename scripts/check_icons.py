#!/usr/bin/env python3
"""How many exact meanings survive when ICONS (information structure) must match too.

Usage: check_icons.py EVAL.json PROFILES_DIR [OUT.json]
EVAL.json is an orca_parse.py --eval run with --save-mrs, made after ICONS extraction was added.
"""
import collections
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from delphin import mrs as M, tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402
from compare_mrs import normalized  # noqa: E402


def gold_mrs(split_dir):
    gold = {}
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                if r[names.index('derivation')]:
                    gold[f"{os.path.basename(prof)}/{r[names.index('parse-id')]}"] = r[names.index('mrs')]
    return gold


def main():
    ev, split = sys.argv[1], sys.argv[2]
    gold = gold_mrs(split)
    c, kinds = collections.Counter(), collections.Counter()
    for r in json.load(open(ev))['records']:
        c['sentences'] += 1
        g = simplemrs.decode(gold[r['id']])
        c['gold with ICONS'] += bool(g.icons)
        if not r.get('mrs'):
            continue
        o = simplemrs.decode(r['mrs'])
        c['Orca with ICONS'] += bool(o.icons)
        if not M.is_isomorphic(normalized(o), normalized(g), properties=False):
            continue
        c['same without ICONS'] += 1
        if M.is_isomorphic(normalized(o, True), normalized(g, True), properties=False):
            c['same with ICONS'] += 1
        else:
            kinds['Orca has none, gold has some' if not o.icons and g.icons else
                  'gold has none, Orca has some' if o.icons and not g.icons else 'both have ICONS, different'] += 1
    res = {**c, 'differ by kind': dict(kinds)}
    print(json.dumps(res, indent=1))
    if len(sys.argv) > 3:
        json.dump(res, open(sys.argv[3], 'w'), indent=1)


if __name__ == '__main__':
    main()
