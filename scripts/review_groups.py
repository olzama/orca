#!/usr/bin/env python3
"""Group the items where Orca's first analysis differs from gold by how the derivations differ (roadmap O116).

Each token carries a leaf label (lexical type | lexical rules | unary rules) and a tree label
(attachment height | rule names); a difference is described by the label changes, without positions:
  lex   gold lexical type -> Orca's
  rule  gold rules at a token -> Orca's
  attach  same rules, attached at another height
Items with the same set of changes form a group; groups are also merged by their most frequent single change.

    review_groups.py RUN.json [--gold data/encoded-2025-bothall-surface/dev.jsonl] [--out analysis/review-groups/dev]
"""
import argparse
import ast
import collections
import json
import os
import random


def gold_labels(path):
    out = {}
    for line in open(path):
        d = json.loads(line)
        toks = d['tokens'] if isinstance(d['tokens'], list) else ast.literal_eval(d['tokens'])
        out[d['id']] = {'forms': [t['form'] for t in toks],
                        'leaf': [f"{t['lextype']}|{t['lexrules']}|{t['unaries']}" for t in toks],
                        'tree': [f"{t['delta']}|{t['node']}" if t.get('node') else '<none>' for t in toks]}
    return out


def changes(g, o):
    ch = []
    for i in range(min(len(g['leaf']), len(o['leaf']))):
        gl, ol = g['leaf'][i].split('|'), o['leaf'][i].split('|')
        if gl[0] != ol[0]:
            ch.append(('lex', gl[0], ol[0]))
        elif gl[1:] != ol[1:]:
            ch.append(('lexrule', '|'.join(gl[1:]), '|'.join(ol[1:])))
        gt, ot = g['tree'][i].split('|', 1) if '|' in g['tree'][i] else ('', g['tree'][i]), o['tree'][i].split('|', 1) if '|' in o['tree'][i] else ('', o['tree'][i])
        if gt[1] != ot[1]:
            ch.append(('rule', gt[1], ot[1]))
        elif gt[0] != ot[0]:
            ch.append(('attach', gt[1], f'{gt[0]}->{ot[0]}'))
    if len(g['leaf']) != len(o['leaf']):
        ch.append(('tokens', str(len(g['leaf'])), str(len(o['leaf']))))
    return ch


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run')
    ap.add_argument('--gold', default='data/encoded-2025-bothall-surface/dev.jsonl')
    ap.add_argument('--out', default='analysis/review-groups/dev')
    ap.add_argument('--seed', type=int, default=116)
    a = ap.parse_args()
    gold = gold_labels(a.gold)
    recs = json.load(open(a.run))['records']
    items, nolabels = [], 0
    for r in recs:
        if r.get('same MRS') or not r.get('mrs'):
            continue
        if not r.get('labels') or r['id'] not in gold:
            nolabels += 1
            continue
        ch = changes(gold[r['id']], r['labels'])
        items.append({'id': r['id'], 'sentence': ' '.join(gold[r['id']]['forms']), 'changes': ch})
    exact = collections.defaultdict(list)
    for x in items:
        exact[tuple(sorted(set(map(tuple, x['changes']))))].append(x['id'])
    freq = collections.Counter(c for x in items for c in set(map(tuple, x['changes'])))
    coarse = collections.defaultdict(list)
    for x in items:
        cs = set(map(tuple, x['changes']))
        key = max(cs, key=lambda c: (freq[c], c)) if cs else ('same labels', '', '')
        coarse[key].append(x['id'])
    rng = random.Random(a.seed)
    groups = [{'key': list(k), 'size': len(v), 'example': rng.choice(v), 'items': v} for k, v in sorted(coarse.items(), key=lambda kv: -len(kv[1]))]
    os.makedirs(a.out, exist_ok=True)
    json.dump({'run': a.run, 'differing items with an analysis': len(items), 'without labels': nolabels,
               'exact groups': len(exact), 'exact groups of 2 or more': sum(len(v) > 1 for v in exact.values()),
               'groups (by most frequent change)': len(groups), 'groups': groups, 'items': items},
              open(os.path.join(a.out, 'groups.json'), 'w'), indent=1)
    print(len(items), 'items;', len(exact), 'exact groups,', sum(len(v) > 1 for v in exact.values()), 'of 2 or more;', len(groups), 'coarse groups')
    for g in groups[:15]:
        print(g['size'], g['key'])


if __name__ == '__main__':
    main()
