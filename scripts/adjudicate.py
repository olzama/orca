#!/usr/bin/env python3
"""An LLM judges sentences where Orca and the reference parse (here ACE's
first-ranked parse, unchecked) give different meanings.

Each disagreement is shown as two readings, in random order, each by the DMRS
predicates and links the other reading lacks (as in llm_rank.py). The model
answers A, B, BOTH (both acceptable readings of the sentence) or NEITHER.
Orca then counts as right when it agrees with the reference, or when the judge
picks Orca's reading or BOTH.

Usage:
    adjudicate.py prepare --eval EVAL.json --profiles PROF_DIR [--sentences SENTS.txt] --out DIR
    adjudicate.py run --out DIR [--batch 5] [--parallel 4] [--model M]
    adjudicate.py score --out DIR [--targets CALLS.jsonl]
"""
import argparse
import collections
import concurrent.futures
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def prepare(args):
    from delphin import tsdb
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    from llm_rank import facts
    ref = {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                if r[names.index('mrs')]:
                    ref[f"{os.path.basename(prof)}/{r[names.index('parse-id')]}"] = r[names.index('mrs')]
    if args.sentences:
        lines = [l.rstrip('\n') for l in open(args.sentences)]
        text = lambda sid: lines[int(sid.split('/')[1]) - 1]
    else:                                   # treebank split: raw input of each item
        from check_raw_tokens import raw_inputs
        raw = raw_inputs(args.profiles)
        text = lambda sid: raw[sid]
    rng = random.Random(7)
    items, st = [], collections.Counter()
    for r in json.load(open(args.eval))['records']:
        st['sentences'] += 1
        if r['same MRS']:
            st['agree'] += 1
            continue
        if not r.get('mrs'):
            st['Orca: no analysis'] += 1
            continue
        try:
            fo = facts(normalized(simplemrs.decode(r['mrs'])))
            fr = facts(normalized(simplemrs.decode(ref[r['id']])))
        except Exception:
            st['unreadable MRS'] += 1
            continue
        o, a = sorted((fo - fr).elements()), sorted((fr - fo).elements())
        if not o and not a:
            st['differ only in scope or properties'] += 1
            continue
        orca_first = rng.random() < 0.5
        items.append({'id': r['id'], 'sentence': text(r['id']),
                      'A': o if orca_first else a, 'B': a if orca_first else o, 'orca': 'A' if orca_first else 'B'})
        st['to judge'] += 1
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, 'items.jsonl'), 'w') as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + '\n')
    json.dump(dict(st), open(os.path.join(args.out, 'prepare.json'), 'w'), indent=1)
    print(json.dumps(dict(st), indent=1))


SYSTEM = """You judge two semantic analyses of the same English sentence, produced by the English Resource Grammar. Each reading is shown only by what it has and the other lacks: predicates (node ...) and links (head -ROLE-> dependent). Predicate names are lemma_partofspeech_sense (n noun, v verb, a adjective or adverb, p preposition, q quantifier, c conjunction); ARG1, ARG2 ... are argument roles; /EQ and /H mark links that share a label or go through a scope relation; compound, appos, implicit_conj, udef_q, generic_entity, unknown and similar are grammar-internal predicates. Decide which reading is a correct analysis of the sentence as a careful human reader understands it. Answer A or B if exactly one is correct, BOTH if both are acceptable readings of this sentence, NEITHER if both are wrong. Answer with one line per sentence, "N: X", where N is the sentence number and X is A, B, BOTH or NEITHER. No other text."""


def prompt(batch):
    parts = []
    for i, it in enumerate(batch, 1):
        parts.append(f'Sentence {i}: {it["sentence"]}')
        for L in 'AB':
            parts.append(f'  Reading {L}: ' + ('; '.join(it[L]) if it[L] else '(nothing beyond what both share)'))
        parts.append('')
    return '\n'.join(parts)


def run(args):
    from llm_label import call
    items = [json.loads(l) for l in open(os.path.join(args.out, 'items.jsonl'))]
    log = os.path.join(args.out, 'calls.jsonl')
    done = set()
    if os.path.exists(log):
        for l in open(log):
            r = json.loads(l)
            if r.get('answers'):
                done.update(r['ids'])
    todo = [it for it in items if it['id'] not in done]
    batches = [todo[i:i + args.batch] for i in range(0, len(todo), args.batch)]

    def go(batch):
        try:
            data = call(args.model, SYSTEM, prompt(batch), args.out)
            text = data.get('result') or ''
        except Exception as e:
            data, text = {'error': str(e)[:300]}, ''
        ans = {}
        for m in re.finditer(r'^\s*(\d+)\s*:\s*(A|B|BOTH|NEITHER)\b', text, re.M):
            k = int(m.group(1)) - 1
            if 0 <= k < len(batch):
                ans[batch[k]['id']] = m.group(2)
        return {'ids': [b['id'] for b in batch], 'answers': ans, 'raw': text[:2000],
                'cost_usd': data.get('total_cost_usd'), 'error': data.get('error')}

    with concurrent.futures.ThreadPoolExecutor(args.parallel) as ex, open(log, 'a') as f:
        for rec in ex.map(go, batches):
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            f.flush()
            print(len(rec['answers']), 'of', len(rec['ids']), flush=True)


def score(args):
    items = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(args.out, 'items.jsonl'))}
    ans, cost, calls = {}, 0.0, 0
    for l in open(os.path.join(args.out, 'calls.jsonl')):
        r = json.loads(l)
        ans.update(r['answers'])
        cost += r.get('cost_usd') or 0
        calls += 1
    verdict = collections.Counter()
    by_id = {}
    for sid, it in items.items():
        a = ans.get(sid)
        v = ('unanswered' if a is None else a.lower() if a in ('BOTH', 'NEITHER')
             else 'orca' if a == it['orca'] else 'reference')
        verdict[v] += 1
        by_id[sid] = v
    res = {'verdicts': dict(verdict), 'calls': calls, 'cost_usd': round(cost, 2), 'by_id': by_id}
    json.dump(res, open(os.path.join(args.out, 'score.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'by_id'}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('prepare', 'run', 'score'))
    ap.add_argument('--eval')
    ap.add_argument('--profiles')
    ap.add_argument('--sentences')
    ap.add_argument('--out', required=True)
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-opus-5-5')
    args = ap.parse_args()
    {'prepare': prepare, 'run': run, 'score': score}[args.cmd](args)


if __name__ == '__main__':
    main()
