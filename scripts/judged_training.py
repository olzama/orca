#!/usr/bin/env python3
"""Training records from a generated round, using the LLM judge's verdicts.

Per sentence (only sentences ACE parsed and the grammar replays):
  same MRS as ACE                -> ACE's labels
  judge: ACE's reading or both   -> ACE's labels
  judge: Orca's reading          -> Orca's labels (from an eval run with --save-mrs, which keeps them)
  judge: neither                 -> dropped
  not judged (Orca had no analysis, or the readings differ only in scope or properties) -> ACE's labels,
      unless --drop-unjudged

Usage: judged_training.py --round-dir data/generated/round2 --eval EVAL.json --score analysis/adjudicate/gen-round2/score.json
                          --out OUT.jsonl [--drop-unjudged]
"""
import argparse
import collections
import json
import os

CONT = '<cont>'


def orca_tokens(lab):
    """Orca's chosen candidate (forms, leaf and tree label strings, entries per leaf) as encoded token dicts."""
    toks, entries = [], iter(lab['entries'])
    for form, leaf, tree in zip(lab['forms'], lab['leaf'], lab['tree']):
        lextype, lexrules, unaries = (leaf.split('|') + ['', ''])[:3]
        if lextype == CONT:
            toks.append({'form': form, 'entry': CONT, 'lextype': CONT, 'lexrules': '', 'unaries': '',
                         'delta': None, 'depth': None, 'node': None})
            continue
        entry = next(entries)
        entry = entry[6:] if entry.startswith('entry:') else entry
        delta, _, node = tree.partition('|')
        toks.append({'form': form, 'entry': entry, 'lextype': lextype, 'lexrules': lexrules, 'unaries': unaries,
                     'delta': int(delta) if node else None, 'depth': None, 'node': node or None})
    return toks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round-dir', required=True)
    ap.add_argument('--eval', required=True)
    ap.add_argument('--score', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--drop-unjudged', action='store_true')
    args = ap.parse_args()
    ace = {}
    for l in open(os.path.join(args.round_dir, 'train.jsonl')):
        r = json.loads(l)
        ace[r['id']] = r
    recs = {r['id']: r for r in json.load(open(args.eval))['records']}
    verdict = json.load(open(args.score))['by_id']
    c = collections.Counter()
    with open(args.out, 'w') as f:
        for sid, a in ace.items():
            r, v = recs.get(sid), verdict.get(sid)
            if r and r['same MRS']:
                kind, out = 'same as ACE', a
            elif v in ('reference', 'both'):
                kind, out = f'judge: {v}', a
            elif v == 'orca':
                lab = r.get('labels')
                if not lab or [t['form'] for t in a['tokens']] != lab['forms']:
                    c['judge: orca, labels missing or forms differ'] += 1
                    continue
                kind, out = 'judge: orca', {'id': sid, 'tokens': orca_tokens(lab)}
            elif v == 'neither':
                c['judge: neither (dropped)'] += 1
                continue
            elif args.drop_unjudged:
                c['not judged (dropped)'] += 1
                continue
            else:
                kind, out = 'not judged', a
            c[kind] += 1
            f.write(json.dumps(out, ensure_ascii=False) + '\n')
    print(json.dumps(dict(c), indent=1))


if __name__ == '__main__':
    main()
