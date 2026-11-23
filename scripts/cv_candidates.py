#!/usr/bin/env python3
"""Orca's candidates on a held-out cross-validation fold of the Redwoods training
data, for training a ranking model and mining repair patterns on data that looks
like what Orca proposes on new text.

For each held-out sentence (raw text, current parser defaults, on CPU):
  forms, outcome, replays,
  candidates: every accepted derivation (leaf, tree, entries, tagger cost,
              ERG MaxEnt score 'me', same_mrs = gold MRS without properties),
  first: the tagger's first-choice leaf and tree labels,
  gold:  the treebank's leaf and tree labels (with 'gold_forms_match': same tokens).
The candidates format is what train_ranker.py devprep/eval read.

    cv_candidates.py run --fold K [--threads 3] [--limit N]
    cv_candidates.py summary --fold K
Writes data/cv-candidates/fold{K}.jsonl (resumable) and fold{K}-summary.json.
"""
import argparse
import collections
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)
ORCA = os.path.join(HERE, '..')
OUT = os.path.join(ORCA, 'data', 'cv-candidates')


def gold_mrs(profiles, split_dir):
    from delphin import tsdb
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    gold = {}
    for name in profiles:
        prof = os.path.join(split_dir, name)
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold[f"{name}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
    return gold, normalized, simplemrs


def run(a):
    import torch
    torch.set_num_threads(a.threads)
    from check_raw_tokens import raw_inputs
    from compare_mrs import normalized
    from delphin.codecs import simplemrs
    from eval_trees import to_leaves
    from llm_label import read
    from orca.encoding import decode
    from orca.tokens import lattice_path, token_chart
    from orca_parse import Parser
    from rerank import with_entries
    data = os.path.join(ORCA, 'data', f'encoded-2025-bothall-surface-cv{a.fold}')
    fold = json.load(open(os.path.join(data, 'fold.json')))
    split = os.path.join(ORCA, 'data', 'profiles-2025', 'train')
    tagger = os.path.join(ORCA, 'data', 'models', f'tagger-2025bothsurf-debertav3large-cv{a.fold}')
    sents = read(os.path.join(data, 'heldout.jsonl'))[:a.limit]
    os.makedirs(OUT, exist_ok=True)
    path_out = os.path.join(OUT, f'fold{a.fold}.jsonl')
    done = set()
    if os.path.exists(path_out):
        for line in open(path_out, encoding='utf-8'):
            try:
                done.add(json.loads(line)['id'])
            except Exception:
                pass
    raw = {}
    for name in fold['profiles']:                          # raw_inputs reads a directory of profiles
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            os.symlink(os.path.realpath(os.path.join(split, name)), os.path.join(d, name))
            raw.update(raw_inputs(d))
    gold, _, _ = gold_mrs(fold['profiles'], split)
    p = Parser(tagger=tagger, device='cpu')
    r = p.repair
    out = open(path_out, 'a', encoding='utf-8')
    t0, n = time.time(), 0
    for s in sents:
        sid = s['id']
        if sid in done or sid not in raw or sid not in gold:
            continue
        text = raw[sid]
        path = lattice_path(token_chart(text, p.ace, p.dat), p.known)
        forms = [text[x:y] for _, _, (x, y) in path] if p.surface else [q[0] for q in path]
        rec = {'id': sid, 'forms': forms, 'gold': {'leaf': s['leaf'], 'tree': s['tree']},
               'gold_forms_match': [f.lower() for f in forms] == [f.lower().replace('\\/', '/') for f in s['forms']]}
        if not forms:
            rec['outcome'] = 'no tokens'
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            continue
        top = p.tag(forms)
        rec['first'] = {k: [top[k][j][0][0] for j in range(len(forms))] for k in ('leaf', 'tree')}
        rforms = [q[0] for q in path] if p.normalized_lookup else forms
        rec['forms'] = rforms
        st = {'id': sid, 'forms': rforms, 'leaf': [None] * len(forms), 'tree': [None] * len(forms)}
        r._WORK = (p.fg, [st], [top], {sid: [q[1] for q in path]}, p.args, p.lx)
        r.GOLD_MRS.clear()
        try:
            r.GOLD_MRS[sid] = normalized(simplemrs.decode(gold[sid]))
        except Exception:
            pass
        outcome, leaf, tree, n_replays, _, _, kbest = r.search(0)
        rec['outcome'] = outcome.replace(', wrong', '').replace(', right', '')
        rec['replays'] = n_replays
        cands = []
        for c in kbest:
            try:
                tr = with_entries(decode(to_leaves(rforms, c['leaf'], c['tree'])), c['entries'])
                me = p.me.score(tr, p.lx.type_of.get, p.generic)
            except Exception:
                me = None
            cands.append({'leaf': c['leaf'], 'tree': c['tree'], 'entries': c['entries'], 'cost': c['cost'],
                          'me': me, 'same_mrs': bool(c.get('same_mrs'))})
        rec['candidates'] = cands
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        out.flush()
        n += 1
        if n % 200 == 0:
            print(f'{n} done, {(time.time() - t0) / n:.2f} s/sentence', flush=True)
    out.close()
    summary(a)


def summary(a):
    st = collections.Counter()
    for line in open(os.path.join(OUT, f'fold{a.fold}.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        st['sentences'] += 1
        st[r.get('outcome', '?')] += 1
        st['tokens match gold'] += bool(r.get('gold_forms_match'))
        c = r.get('candidates') or []
        if c:
            st['with candidates'] += 1
            st['candidates'] += len(c)
            st['gold among candidates'] += any(x['same_mrs'] for x in c)
            st['first found is gold'] += c[0]['same_mrs']
            mes = [x['me'] if x['me'] is not None else float('-inf') for x in c]
            st['ERG MaxEnt pick is gold'] += c[max(range(len(c)), key=lambda i: mes[i])]['same_mrs']
    json.dump(dict(st), open(os.path.join(OUT, f'fold{a.fold}-summary.json'), 'w'), indent=1)
    print(json.dumps(dict(st), indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('run', 'summary'))
    ap.add_argument('--fold', type=int, required=True)
    ap.add_argument('--threads', type=int, default=3)
    ap.add_argument('--limit', type=int)
    a = ap.parse_args()
    {'run': run, 'summary': summary}[a.cmd](a)


if __name__ == '__main__':
    main()
