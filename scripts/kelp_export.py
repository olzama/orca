#!/usr/bin/env python3
"""Write a Kelp review set (roadmap O116): one example per group of review_groups.py, gold in "a", Orca in "b".

    kelp_export.py [--groups analysis/review-groups/dev/groups.json] [--out analysis/review-groups/dev/kelp-review.jsonl] [--min-size 1]

Gold derivation and MRS come from the Redwoods dev profiles; Orca's derivation is not in the saved run, so each
example is parsed again with the same tagger and defaults, and kept only if its MRS is the saved run's.
Kelp's format: id, sentence, group, group_label, group_size, a/b = {label, derivation (UDF), mrs (SimpleMRS)}.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
ORCA = os.path.join(HERE, '..')
DEV = os.path.join(ORCA, 'data/profiles-2025/dev')


def gold():
    from delphin import tsdb
    out = {}
    for prof in sorted(glob.glob(os.path.join(DEV, '*'))):
        name = os.path.basename(prof)
        items = {}
        inames = [f.name for f in tsdb.read_schema(prof)['item']]
        for row in tsdb.open(prof, 'item'):
            r = tsdb.split(row)
            items[r[inames.index('i-id')]] = r[inames.index('i-input')]
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        for line in tsdb.open(prof, 'result'):
            r = tsdb.split(line)
            pid = r[names.index('parse-id')]
            if r[names.index('mrs')]:
                out[f'{name}/{pid}'] = {'sentence': items.get(pid), 'derivation': r[names.index('derivation')], 'mrs': r[names.index('mrs')]}
    return out


def udf(t, span=None):
    """Orca's tree (tree_json form) as a UDF derivation string; node ids numbered in order."""
    n = [0]
    def walk(x, lo):
        n[0] += 1
        i = n[0]
        if 'entry' in x:
            form = ' '.join(x['forms']).replace('\\', '\\\\').replace('"', '\\"')
            forms = f'"{form}"'   # one terminal per lexical node, a multiword entry's forms joined by spaces (as in the profiles)
            k = len(x['forms'])
            return f'({i} {x["entry"]} 0 {lo} {lo + k} ({forms}))', lo + k
        parts, hi = [], lo
        for c in x['children']:
            s, hi = walk(c, hi)
            parts.append(s)
        return f'({i} {x["label"]} 0 {lo} {hi} {" ".join(parts)})', hi
    if 'label' in t and t['label'].startswith('root_') and len(t['children']) == 1:
        s, _ = walk(t['children'][0], 0)
        return f'({t["label"]} {s})'
    return walk(t, 0)[0]


LABELS = {'attach': lambda k: f'{k[1]} attached at another height ({k[2]})', 'rule': lambda k: f'rule {k[1]} -> {k[2]}',
          'lex': lambda k: f'lexical type {k[1]} -> {k[2]}', 'lexrule': lambda k: f'lexical/unary rules {k[1] or "none"} -> {k[2] or "none"}',
          'tokens': lambda k: f'{k[1]} tokens -> {k[2]}'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--groups', default=os.path.join(ORCA, 'analysis/review-groups/dev/groups.json'))
    ap.add_argument('--out', default=os.path.join(ORCA, 'analysis/review-groups/dev/kelp-review.jsonl'))
    ap.add_argument('--min-size', type=int, default=1)
    ap.add_argument('--all', action='store_true', help='every member of every group, its example first (Kelp checks the groups)')
    a = ap.parse_args()
    from orca_parse import Parser
    from compare_mrs import normalized
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    G = json.load(open(a.groups))
    run = {r['id']: r for r in json.load(open(os.path.join(ORCA, G['run']) if not os.path.isabs(G['run']) else G['run']))['records']}
    gd = gold()
    p = Parser()
    kept, dropped = 0, []
    with open(a.out, 'w') as f:
        for k, g in enumerate(G['groups']):
            if g['size'] < a.min_size:
                continue
            members = [g['example']] + ([i for i in g['items'] if i != g['example']] if a.all else [])
            for sid in members:
              x = gd[sid]
              r = p.parse(x['sentence'], sid)
              m = r.get('_mrs_obj')
              saved = run[sid].get('mrs')
              same = m is not None and saved and M.is_isomorphic(normalized(m), normalized(simplemrs.decode(saved)), properties=True)
              if not same:
                  dropped.append(sid)
                  continue
              f.write(json.dumps({'id': sid, 'sentence': x['sentence'], 'group': f'g{k:03d}', 'group_label': LABELS.get(g['key'][0], str)(g['key']),
                                  'group_size': g['size'], 'example': sid == g['example'],
                                  'a': {'label': 'gold', 'derivation': x['derivation'], 'mrs': x['mrs']},
                                  'b': {'label': 'orca', 'derivation': udf(r['derivation']), 'mrs': r['mrs']}}, ensure_ascii=False) + '\n')
              kept += 1
    print('written', kept, 'dropped (parse differs from the saved run)', len(dropped), dropped[:5])


if __name__ == '__main__':
    main()
