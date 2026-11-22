#!/usr/bin/env python3
"""Check generated sentences where Orca and ACE agree: is their shared reading right?

On generated text the reference is ACE's first-ranked parse, which nobody checked,
so a sentence where Orca's MRS matches it is counted as right without evidence.
This samples such sentences, takes ACE's n best parses as the competing readings,
and asks the judge (Claude Opus) to pick the right reading or say none is right.
Readings are shown in random order, each by what distinguishes it from the others.

Steps:
  sample   --evals E1.json E2.json --n 300 --out DIR       -> DIR/<profile-dir-name>.ids, one per round
  (then:   ace_nbest.py --profiles data/generated/ROUND/profiles --ids DIR/ROUND.ids --out DIR/ROUND-ace30.jsonl --n 30)
  prepare  --nbest DIR/*-ace30.jsonl --out DIR             -> DIR/items.jsonl
  run      --out DIR
  score    --out DIR                                       -> DIR/score.json
"""
import argparse
import collections
import concurrent.futures
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_rank import LETTERS, MAX_READINGS, facts  # noqa: E402


def sample(args):
    agree = []
    for e in args.evals:
        agree += [r['id'] for r in json.load(open(e))['records'] if r['same MRS']]
    random.Random(11).shuffle(agree)
    pick = agree[:args.n]
    os.makedirs(args.out, exist_ok=True)
    by = collections.defaultdict(list)
    for sid in pick:
        by[sid.split('/')[0]].append(sid)
    for prof, ids in by.items():
        open(os.path.join(args.out, f'{prof}.ids'), 'w').write('\n'.join(ids) + '\n')
    print(json.dumps({'agreements': len(agree), 'sampled': len(pick), **{k: len(v) for k, v in by.items()}}))


def prepare(args):
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    rng = random.Random(5)
    st, items = collections.Counter(), []
    for path in args.nbest:
        for line in open(path):
            r = json.loads(line)
            st['sentences'] += 1
            groups = []                     # [mrs, shared with Orca (= ACE's first)]
            for x in r['results']:
                try:
                    m = normalized(simplemrs.decode(x['mrs']))
                except Exception:
                    continue
                if not any(M.is_isomorphic(g[0], m, properties=False) for g in groups):
                    groups.append([m, bool(x['same_mrs'])])
            if not any(g[1] for g in groups):
                st['first parse not reproduced'] += 1
                continue
            if len(groups) < 2:
                st['only one reading'] += 1
                continue
            shared = next(g for g in groups if g[1])
            others = [g for g in groups if not g[1]][:MAX_READINGS - 1]
            shown = [shared] + others
            rng.shuffle(shown)
            fs = [facts(g[0]) for g in shown]
            common = fs[0].copy()
            for f in fs[1:]:
                common &= f
            st['judged'] += 1
            items.append({'id': r['id'], 'sentence': r['input'], 'shared': shown.index(shared),
                          'readings': [sorted((f - common).elements()) for f in fs]})
    with open(os.path.join(args.out, 'items.jsonl'), 'w') as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + '\n')
    json.dump(dict(st), open(os.path.join(args.out, 'prepare.json'), 'w'), indent=1)
    print(json.dumps(dict(st), indent=1))


SYSTEM = """You choose the intended reading of English sentences. Each reading is a semantic analysis from the English Resource Grammar, shown only by what distinguishes it from the other readings of the same sentence: predicates (node ...) and links (head -ROLE-> dependent) that not every reading has. Predicate names are lemma_partofspeech_sense; ARG1, ARG2 ... are argument roles; /EQ and /H mark links that share a label or go through a scope relation; compound, appos, implicit_conj, udef_q and similar are grammar-internal predicates. Pick the reading a careful human reader would understand the sentence to mean in ordinary context, or answer NONE if no reading is a correct analysis. Answer with one line per sentence, "N: X", where N is the sentence number and X the letter of the reading or NONE. No other text."""


def prompt(batch):
    parts = []
    for i, it in enumerate(batch, 1):
        parts.append(f'Sentence {i}: {it["sentence"]}')
        for L, rd in zip(LETTERS, it['readings']):
            parts.append(f'  Reading {L}: ' + ('; '.join(rd) if rd else '(nothing beyond what all readings share)'))
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
        for m in re.finditer(r'^\s*(\d+)\s*:\s*([A-J]|NONE)\b', text, re.M):
            k = int(m.group(1)) - 1
            if 0 <= k < len(batch):
                ans[batch[k]['id']] = m.group(2)
        return {'ids': [b['id'] for b in batch], 'answers': ans, 'raw': text[:2000],
                'cost_usd': data.get('total_cost_usd'), 'error': data.get('error')}

    with concurrent.futures.ThreadPoolExecutor(args.parallel) as ex, open(log, 'a') as f:
        for rec in ex.map(go, batches):
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            f.flush()


def score(args):
    items = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(args.out, 'items.jsonl'))}
    ans, cost = {}, 0.0
    for l in open(os.path.join(args.out, 'calls.jsonl')):
        r = json.loads(l)
        ans.update(r['answers'])
        cost += r.get('cost_usd') or 0
    c, by_id = collections.Counter(), {}
    for sid, a in ans.items():
        v = 'none right' if a == 'NONE' else 'shared reading' if LETTERS.index(a) == items[sid]['shared'] else 'another reading'
        c[v] += 1
        by_id[sid] = v
    res = {'prepare': json.load(open(os.path.join(args.out, 'prepare.json'))), 'verdicts': dict(c),
           'answered': len(ans), 'cost_usd': round(cost, 2), 'by_id': by_id}
    json.dump(res, open(os.path.join(args.out, 'score.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'by_id'}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('sample', 'prepare', 'run', 'score'))
    ap.add_argument('--evals', nargs='*')
    ap.add_argument('--nbest', nargs='*')
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=300)
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-opus-5-5')
    args = ap.parse_args()
    {'sample': sample, 'prepare': prepare, 'run': run, 'score': score}[args.cmd](args)


if __name__ == '__main__':
    main()
