#!/usr/bin/env python3
"""Pilot: an LLM chooses among the readings of a sentence; compared with MaxEnt.

For each dev sentence, the derivations that repair got accepted (a k-best
file from repair.py) are replayed and grouped by meaning (isomorphic MRS).
Sentences with at least two readings, one of them gold, are kept. Each
reading is shown to the model only by what distinguishes it: the DMRS links
and predicates not shared by all readings (in the spirit of the discriminants
annotators use). The model picks one reading per sentence. MaxEnt's choice is
the reading of its best-scored derivation.

Usage:
    llm_rank.py prepare --grammar ERG/english.tdl --profiles DEV_DIR --kbest FILE.jsonl --out DIR [--n 300]
    llm_rank.py run --out DIR [--batch 5] [--parallel 4] [--model M]
    llm_rank.py score --out DIR
"""
import argparse
import collections
import concurrent.futures
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

LETTERS = 'ABCDEFGHIJ'
MAX_READINGS = 8


def short(pred, carg):
    p = pred.lstrip('_')
    p = re.sub(r'_rel$', '', p)
    return f'{p}("{carg}")' if carg else p


def facts(m):
    """Readable predicates and links of an MRS (via DMRS), as a multiset."""
    from delphin import dmrs
    d = dmrs.from_mrs(m)
    name = {n.id: short(n.predicate, n.carg) for n in d.nodes}
    out = collections.Counter(f'node {v}' for v in name.values())
    for l in d.links:
        post = '' if l.post in ('NEQ', '') else f'/{l.post}'
        out[f'{name[l.start]} -{l.role}{post}-> {name[l.end]}'] += 1
    return out


def prepare(args):
    from delphin import derivation, mrs as M, tsdb
    from compare_mrs import normalized, to_pydelphin
    from eval_trees import to_leaves
    from orca.encoding import decode
    from orca.maxent import MaxEnt
    from orca.tfs.fast import FastGrammar, extract
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    from rerank import with_entries
    import glob
    gdir = os.path.dirname(args.grammar)
    g = Grammar(args.grammar)
    lx = Lexicon(g, gdir)
    me = MaxEnt(os.path.join(gdir, 'redwoods.mem'))
    generic = lambda e: g.status.get(e) == 'generic-lex-entry'
    fg = FastGrammar(g)
    derivs, gold = {}, {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                if r[names.index('derivation')]:
                    sid = f"{os.path.basename(prof)}/{r[names.index('parse-id')]}"
                    derivs[sid] = r[names.index('derivation')]
                    gold[sid] = r[names.index('mrs')]
    from delphin.codecs import simplemrs
    keep = []
    st = collections.Counter()
    for line in open(args.kbest, encoding='utf-8'):
        r = json.loads(line)
        cands = r.get('candidates') or []
        st['sentences'] += 1
        if not cands:
            continue
        st['with candidates'] += 1
        toks = [t.tfs for term in derivation.from_string(derivs[r['id']]).terminals() for t in (term.tokens or [])]
        gm = normalized(simplemrs.decode(gold[r['id']]))
        groups = []          # [mrs, best score, is gold, n derivations]
        for c in cands:
            tr = with_entries(decode(to_leaves(r['forms'], c['leaf'], c['tree'])), c['entries'])
            score = me.score(tr, lx.type_of.get, generic)
            try:
                fg.reset()
                fs, _ = fg.replay_tree(tr, toks)
                m = normalized(to_pydelphin(extract(fg, fs)))
            except Exception:
                continue
            for grp in groups:
                if M.is_isomorphic(grp[0], m, properties=False):
                    grp[1] = max(grp[1], score)
                    grp[3] += 1
                    break
            else:
                groups.append([m, score, bool(M.is_isomorphic(gm, m, properties=False)), 1])
        if len(groups) < 2 or not any(gr[2] for gr in groups):
            continue
        st['two or more readings, gold among them'] += 1
        groups.sort(key=lambda gr: -gr[1])
        groups = groups[:MAX_READINGS]
        fs_ = [facts(gr[0]) for gr in groups]
        common = fs_[0].copy()
        for f in fs_[1:]:
            common &= f
        readings = [{'facts': sorted((f - common).elements()), 'maxent': gr[1], 'gold': gr[2], 'derivations': gr[3]}
                    for gr, f in zip(groups, fs_)]
        keep.append({'id': r['id'], 'sentence': ' '.join(r['forms']), 'readings': readings,
                     'margin': groups[0][1] - groups[1][1]})
    random.Random(1).shuffle(keep)
    st['kept for the pilot'] = min(len(keep), args.n)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, 'items.jsonl'), 'w') as f:
        for k in keep[:args.n]:
            f.write(json.dumps(k, ensure_ascii=False) + '\n')
    print(json.dumps(st, indent=1))


SYSTEM = """You choose the intended reading of English sentences. Each reading is a semantic analysis from the English Resource Grammar, shown only by what distinguishes it from the other readings of the same sentence: predicates (node ...) and links (head -ROLE-> dependent) that not every reading has. Predicate names are lemma_partofspeech_sense; ARG1, ARG2 ... are argument roles; /EQ and /H mark links that share a label or go through a scope relation; compound, appos, implicit_conj, udef_q and similar are grammar-internal predicates. Pick the reading a careful human reader would understand the sentence to mean in ordinary context. Answer with one line per sentence, "N: X", where N is the sentence number and X the letter of the reading. No other text."""


def prompt(batch):
    parts = []
    for i, it in enumerate(batch, 1):
        parts.append(f'Sentence {i}: {it["sentence"]}')
        for L, rd in zip(LETTERS, it['readings']):
            parts.append(f'  Reading {L}: ' + ('; '.join(rd['facts']) if rd['facts'] else '(nothing beyond what all readings share)'))
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
        for m in re.finditer(r'^\s*(\d+)\s*:\s*([A-J])\b', text, re.M):
            k = int(m.group(1)) - 1
            if 0 <= k < len(batch):
                ans[batch[k]['id']] = LETTERS.index(m.group(2))
        return {'ids': [b['id'] for b in batch], 'answers': ans, 'raw': text[:2000], 'seconds': data.get('seconds'),
                'cost_usd': data.get('total_cost_usd'), 'usage': data.get('usage'), 'error': data.get('error')}

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
    bins = ((0, 1, 'margin under 1'), (1, 3, '1 to 3'), (3, 1e9, '3 and over'))
    out = collections.defaultdict(collections.Counter)
    for sid, it in items.items():
        if sid not in ans:
            continue
        b = next(n for lo, hi, n in bins if lo <= it['margin'] < hi)
        for key in ('all', b):
            c = out[key]
            c['sentences'] += 1
            c['maxent right'] += it['readings'][0]['gold']
            c['llm right'] += it['readings'][ans[sid]]['gold']
            c['gold shown'] += any(r['gold'] for r in it['readings'])
            c['readings'] += len(it['readings'])
    res = {'by margin': {k: dict(v) for k, v in out.items()}, 'answered': len(ans), 'items': len(items),
           'calls': calls, 'cost_usd': round(cost, 2)}
    json.dump(res, open(os.path.join(args.out, 'score.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('prepare', 'run', 'score'))
    ap.add_argument('--grammar')
    ap.add_argument('--profiles')
    ap.add_argument('--kbest')
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=300)
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-opus-5-5')
    args = ap.parse_args()
    {'prepare': prepare, 'run': run, 'score': score}[args.cmd](args)


if __name__ == '__main__':
    main()
