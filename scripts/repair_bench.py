#!/usr/bin/env python3
"""Rerun repair (and ranking, MRS) on cached tokens and tagger output, to time
and change repair without re-tagging, and to check that a change keeps every
result identical.

    repair_bench.py prepare --eval data/profiles-2025/dev --gold DEV.jsonl --cache CACHE.pkl [--tagger M]
        tokens (ACE preprocessing) and the tagger's k-best labels for every sentence, once (CPU is fine)
    repair_bench.py run --cache CACHE.pkl --out RUN.json [--limit N] [--profile PROF.out]
        repair + ranking + MRS from the cache; per sentence: outcome, replays, accepted
        derivations (labels, entries), chosen index, MRS text; repair seconds
    repair_bench.py compare A.json B.json
        identical outcomes, accepted derivations, chosen derivation and MRS?
"""
import argparse
import json
import os
import pickle
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def prepare(a):
    import torch
    torch.set_num_threads(4)                      # leave cores for GPU trainings' data loading
    from check_raw_tokens import raw_inputs
    from llm_label import read
    from orca.tokens import lattice_path, token_chart
    from orca_parse import Parser
    p = Parser(tagger=a.tagger, device='cpu')
    raw = raw_inputs(a.eval)
    out = {}
    for i, s in enumerate(read(a.gold)):
        text = raw[s['id']]
        path = lattice_path(token_chart(text, p.ace, p.dat), p.known)
        forms = [text[x:y] for _, _, (x, y) in path] if p.surface else [q[0] for q in path]
        top = p.tag(forms) if forms else None
        out[s['id']] = {'text': text, 'path': path, 'forms': forms, 'top': top}
        if i % 200 == 0:
            print(i, flush=True)
    os.makedirs(os.path.dirname(a.cache) or '.', exist_ok=True)
    with open(a.cache, 'wb') as f:
        pickle.dump({'tagger': p.tagger_name, 'items': out}, f)


def run(a):
    from compare_mrs import to_pydelphin
    from delphin.codecs import simplemrs
    from eval_trees import to_leaves
    from orca.encoding import decode
    from orca.tfs.fast import extract
    from orca_parse import Parser
    from rerank import with_entries
    data = pickle.load(open(a.cache, 'rb'))
    p = Parser(tagger=a.tagger, device='cpu')
    r = p.repair
    items = list(data['items'].items())[:a.limit]
    recs, rep_secs = {}, 0.0
    prof = None
    if a.profile:
        import cProfile
        prof = cProfile.Profile()
    for sid, it in items:
        path, forms, top = it['path'], it['forms'], it['top']
        if not forms:
            recs[sid] = {'outcome': 'no tokens'}
            continue
        rforms = [q[0] for q in path] if p.normalized_lookup else forms
        s = {'id': sid, 'forms': rforms, 'leaf': [None] * len(forms), 'tree': [None] * len(forms)}
        r._WORK = (p.fg, [s], [top], {sid: [q[1] for q in path]}, p.args, p.lx)
        r.GOLD_MRS.clear()
        t = time.perf_counter()
        if prof:
            prof.enable()
        outcome, leaf, tree, n_replays, _, _, kbest = r.search(0)
        if prof:
            prof.disable()
        rep_secs += time.perf_counter() - t
        rec = {'outcome': outcome.replace(', wrong', '').replace(', right', ''), 'replays': n_replays,
               'kbest': [[c['leaf'], c['tree'], c['entries'], c['cost']] for c in kbest]}
        if kbest:
            scored = []
            for c in kbest:
                tr = with_entries(decode(to_leaves(rforms, c['leaf'], c['tree'])), c['entries'])
                scored.append((p.me.score(tr, p.lx.type_of.get, p.generic), tr, c))
            best = max(range(len(scored)), key=lambda i: scored[i][0])
            p.fg.reset()
            fs, _ = p.fg.replay_tree(scored[best][1], [q[1] for q in path])
            rec['chosen'] = best
            rec['mrs'] = simplemrs.encode(to_pydelphin(extract(p.fg, fs)))
        recs[sid] = rec
    res = {'sentences': len(items), 'repair seconds': rep_secs, 'repair seconds per sentence': rep_secs / max(1, len(items)),
           'records': recs}
    json.dump(res, open(a.out, 'w'))
    print(json.dumps({k: v for k, v in res.items() if k != 'records'}))
    if prof:
        prof.dump_stats(a.profile)


def compare(a):
    x, y = (json.load(open(f))['records'] for f in (a.a, a.b))
    diff = {k: 0 for k in ('outcome', 'replays', 'kbest', 'chosen', 'mrs')}
    for sid in x:
        for k in diff:
            diff[k] += x[sid].get(k) != y.get(sid, {}).get(k)
    print(json.dumps({'sentences': len(x), 'differ': diff, 'missing': len(set(x) ^ set(y))}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('prepare', 'run', 'compare'))
    ap.add_argument('a', nargs='?')
    ap.add_argument('b', nargs='?')
    ap.add_argument('--eval', default='data/profiles-2025/dev')
    ap.add_argument('--gold', default='data/encoded-2025-bothall-surface/dev.jsonl')
    ap.add_argument('--tagger', default='data/models/tagger-2025bothsurf-debertav3large')
    ap.add_argument('--cache', default='data/bench/dev-debertav3large-tags.pkl')
    ap.add_argument('--out')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--profile')
    a = ap.parse_args()
    {'prepare': prepare, 'run': run, 'compare': compare}[a.cmd](a)


if __name__ == '__main__':
    main()
