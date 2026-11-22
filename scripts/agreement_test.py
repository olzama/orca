#!/usr/bin/env python3
"""Orca on Chaves and Richter's (2021) agreement stimuli: does the grammar check catch
what a BERT-family encoder gets wrong after distracting material?

The stimuli (data/raw/chaves-richter-2021, from https://osf.io/ad62v/) have a [MASK]
where the verb goes. Each is filled twice, with the form that agrees with the subject
and with the one that doesn't:
  Experiment 1 (subject, possibly after a long top clause with a noun of the other number):
      is / are and seems / seem
  Experiment 2 (clefted subject, separated from its verb by 1 to 4 embedded clauses):
      was / were
Steps:
  make  --out DIR                    -> DIR/items.jsonl
  orca  --out DIR [--tagger T]       -> DIR/orca.jsonl   (outcome, MRS)
  ace   --out DIR                    -> DIR/ace.jsonl    (ACE's first-ranked MRS, or none)
  score --out DIR                    -> DIR/score.json
"""
import argparse
import collections
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SRC = os.path.join(HERE, '..', 'data/raw/chaves-richter-2021')
PAIRS = {1: (('is', 'are'), ('seems', 'seem')), 2: (('was', 'were'),)}


def make(args):
    items = []
    for exp, fn in ((1, 'exp1-subj_verb.csv'), (2, 'exp2-master.csv')):
        for i, row in enumerate(csv.reader(open(os.path.join(SRC, fn)))):
            text, num, level, cond = row[0], row[1], int(row[2]), row[3]
            subj = 'sg' if num == 'N-sg' else 'pl'
            for sg, pl in PAIRS[exp]:
                for form, n in ((sg, 'sg'), (pl, 'pl')):
                    s = text.replace('[MASK]', form)
                    s = s[0].upper() + s[1:] + '.'
                    items.append({'id': f'e{exp}-{i}-{form}', 'exp': exp, 'sentence': s, 'verb': form,
                                  'grammatical': n == subj, 'level': level,
                                  # experiment 1: number of the noun in the top clause (the attractor); experiment 2: subordination
                                  'condition': ('attractor matches' if cond == subj else 'attractor mismatches') if exp == 1 else cond})
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, 'items.jsonl'), 'w') as f:
        for it in items:
            f.write(json.dumps(it) + '\n')
    print(len(items), 'sentences')


def done_ids(path):
    return {json.loads(l)['id'] for l in open(path)} if os.path.exists(path) else set()


def orca(args):
    from orca_parse import Parser
    items = [json.loads(l) for l in open(os.path.join(args.out, 'items.jsonl'))]
    path = os.path.join(args.out, 'orca.jsonl')
    done = done_ids(path)
    p = Parser(tagger=args.tagger)
    with open(path, 'a') as f:
        for it in items:
            if it['id'] in done:
                continue
            r = p.parse(it['sentence'], it['id'])
            f.write(json.dumps({'id': it['id'], 'outcome': r.get('outcome'), 'mrs': r.get('mrs')}) + '\n')
            f.flush()


def ace(args):
    from delphin import ace as A
    from orca_parse import DEFAULTS
    items = [json.loads(l) for l in open(os.path.join(args.out, 'items.jsonl'))]
    path = os.path.join(args.out, 'ace.jsonl')
    done = done_ids(path)
    with A.ACEParser(DEFAULTS['dat'], executable=DEFAULTS['ace'], cmdargs=['-1', '--timeout=60', '--max-chart-megabytes=3000'],
                     stderr=open(os.devnull, 'w')) as parser, open(path, 'a') as f:
        for it in items:
            if it['id'] in done:
                continue
            try:
                res = parser.interact(it['sentence']).results()
                m = res[0]['mrs'] if res else None
            except Exception:
                m = None
            f.write(json.dumps({'id': it['id'], 'mrs': m}) + '\n')
            f.flush()


def score(args):
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    items = [json.loads(l) for l in open(os.path.join(args.out, 'items.jsonl'))]
    orc = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(args.out, 'orca.jsonl'))}
    ac = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(args.out, 'ace.jsonl'))} \
        if os.path.exists(os.path.join(args.out, 'ace.jsonl')) else {}
    out = collections.defaultdict(collections.Counter)
    for it in items:
        o = orc.get(it['id'])
        if not o:
            continue
        a = ac.get(it['id'])
        same = None
        if o['mrs'] and a and a['mrs']:
            try:
                same = bool(M.is_isomorphic(normalized(simplemrs.decode(o['mrs'])), normalized(simplemrs.decode(a['mrs'])), properties=False))
            except Exception:
                same = False
        g = 'grammatical' if it['grammatical'] else 'ungrammatical'
        keys = [f"e{it['exp']}|{g}|all", f"e{it['exp']}|{g}|level {it['level']}", f"e{it['exp']}|{g}|{it['condition']}"]
        if it['exp'] == 1:                  # the attractor manipulation only exists with a top clause
            keys.append(f"e1|{g}|" + ('no top clause' if it['level'] == 0 else f"top clause, {it['condition']}"))
        for k in keys:
            c = out[k]
            c['n'] += 1
            c[o['outcome'] or 'none'] += 1
            c['orca analysis'] += bool(o['mrs'])
            if a is not None:
                c['ace judged'] += 1
                c['ace analysis'] += bool(a['mrs'])
            c['same as ace'] += bool(same)
    res = {k: dict(v) for k, v in sorted(out.items())}
    json.dump(res, open(os.path.join(args.out, 'score.json'), 'w'), indent=1)
    for k, v in res.items():
        print(k, v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('make', 'orca', 'ace', 'score'))
    ap.add_argument('--out', required=True)
    ap.add_argument('--tagger', default=os.path.join(HERE, '..', 'data/models/tagger-2025bothsurf-bert'))
    args = ap.parse_args()
    {'make': make, 'orca': orca, 'ace': ace, 'score': score}[args.cmd](args)


if __name__ == '__main__':
    main()
