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

    run options for evaluation (they add fields, never change search):
        --gold-mrs PROFILES   mark accepted derivations with the gold MRS (same_mrs) and count exact matches
        --patterns P.json [--pattern-weight W] [--pattern-only-new]   learned repair patterns (these do change search)
        --cands-out C.jsonl   accepted derivations per sentence, in the format train_ranker.py devprep/eval read
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


GOLDFLAGS = []


def run(a):
    from compare_mrs import to_pydelphin
    from delphin.codecs import simplemrs
    from eval_trees import to_leaves
    from orca.encoding import decode
    from orca.tfs.fast import extract
    from orca_parse import Parser
    from rerank import with_entries
    data = pickle.load(open(a.cache, 'rb'))
    p = Parser(tagger=a.tagger, device='cpu', **({'grammar': a.grammar} if a.grammar else {}))
    r = p.repair
    if a.label_map:                      # O91: names the grammar lacks, mapped (scripts/label_map.py)
        lm = json.load(open(a.label_map))
        if a.map_types:
            p.lx.type_map = lm['types']
        if a.map_rules:
            p.lx.rule_map = p.fg.rule_map = lm['rules']
    p.lx.word_fallback = 'missing-type' if a.word_fallback_missing_only else a.word_fallback
    gold = load_gold(a.gold_mrs) if a.gold_mrs else {}
    pats = None
    if a.patterns:
        from repair_patterns import Patterns
        pats = Patterns(a.patterns, weight=a.pattern_weight, only_new=a.pattern_only_new)
    cands_out = open(a.cands_out, 'w', encoding='utf-8') if a.cands_out else None
    import copy as _copy
    args = _copy.copy(p.args)            # search settings: the parser's, with these overrides
    for k in ('budget', 'kbest', 'min_prob', 'fanout'):
        if getattr(a, k, None) is not None:
            setattr(args, k, getattr(a, k))
    args.search, args.distinct, args.global_min_prob = a.search, a.distinct, a.global_min_prob
    args.label_filter = a.label_filter
    n_exact = n_any = 0
    items = list(data['items'].items())
    if a.ids:
        keep_ids = set(open(a.ids).read().split())
        items = [x for x in items if x[0] in keep_ids]
    items = items[:a.limit]
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
        if pats is not None:
            import copy
            top = pats.augment(copy.deepcopy(top))
        r._WORK = (p.fg, [s], [top], {sid: [q[1] for q in path]}, args, p.lx)
        r.GOLD_MRS.clear()
        if sid in gold:
            r.GOLD_MRS[sid] = gold[sid]
        t = time.perf_counter()
        if prof:
            prof.enable()
        outcome, leaf, tree, n_replays, _, _, kbest = r.search(0)
        if prof:
            prof.disable()
        rep_secs += time.perf_counter() - t
        GOLDFLAGS.append(kbest)
        rec = {'outcome': outcome.replace(', wrong', '').replace(', right', ''), 'replays': n_replays,
               'replays to first accepted': r.LAST['replays to first accepted'],
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
            n_any += 1
            if gold:
                rec['exact'] = bool(kbest[best].get('same_mrs'))
                n_exact += rec['exact']
        if cands_out is not None:
            cands = [{'leaf': c['leaf'], 'tree': c['tree'], 'entries': c['entries'], 'cost': c['cost'],
                      'same_mrs': bool(c.get('same_mrs'))} for c in kbest]
            cands_out.write(json.dumps({'id': sid, 'forms': rforms, 'outcome': rec['outcome'], 'candidates': cands}, ensure_ascii=False) + '\n')
        recs[sid] = rec
    if a.label_filter and a.label_filter_save and getattr(args, '_label_filter_obj', None) is not None:
        args._label_filter_obj.save(a.label_filter_save)
    res = {'search': {'mode': a.search, 'distinct': a.distinct, 'global_min_prob': a.global_min_prob,
                      'budget': args.budget, 'kbest': args.kbest, 'min_prob': args.min_prob, 'fanout': args.fanout},
           'gold among accepted': sum(any(c.get('same_mrs') for c in kb) for kb in GOLDFLAGS) if gold else None,
           'replays': sum(r.get('replays', 0) for r in recs.values()),
           'sentences': len(items), 'repair seconds': rep_secs, 'repair seconds per sentence': rep_secs / max(1, len(items)),
           'any analysis': n_any, 'label filter': a.label_filter, 'skipped by the label filter': getattr(args, '_n_filtered', None), 'patterns': a.patterns, 'pattern_weight': a.pattern_weight if a.patterns else None,
           'pattern_only_new': a.pattern_only_new if a.patterns else None, 'records': recs}
    if gold:
        res['exact'] = n_exact
    if cands_out is not None:
        cands_out.close()
    json.dump(res, open(a.out, 'w'))
    print(json.dumps({k: v for k, v in res.items() if k != 'records'}))
    if prof:
        prof.dump_stats(a.profile)


def load_gold(split_dir):
    """Gold MRS per sentence id (normalized, as compare_mrs compares them) from a split's profiles."""
    import glob
    from delphin import tsdb
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    gold = {}
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    try:
                        gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = normalized(simplemrs.decode(rec[names.index('mrs')]))
                    except Exception:
                        pass
    return gold


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
    ap.add_argument('--grammar', help='english.tdl of another grammar version (default: the parser\'s, ERG 2025); tokens stay the cached ones')
    ap.add_argument('--out')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--profile')
    ap.add_argument('--gold-mrs', help='profiles of the split, to mark accepted derivations with the gold MRS')
    ap.add_argument('--patterns')
    ap.add_argument('--pattern-weight', type=float, default=1.0)
    ap.add_argument('--pattern-only-new', action='store_true')
    ap.add_argument('--cands-out')
    ap.add_argument('--search', default='local', choices=('local', 'global', 'hybrid'),
                    help='repair search (scripts/repair.py): local (default), global order, or local then global')
    ap.add_argument('--distinct', action='store_true', help='count accepted readings (distinct MRSs), not derivations')
    ap.add_argument('--global-min-prob', type=float, default=0.0, help='labels below this probability are not tried by the global search')
    ap.add_argument('--budget', type=int)
    ap.add_argument('--kbest', type=int)
    ap.add_argument('--min-prob', type=float)
    ap.add_argument('--fanout', type=int)
    ap.add_argument('--ids', help='file with sentence ids to run (one per line)')
    ap.add_argument('--label-filter-save', help='write the label filter table (with the keys computed in this run) here')
    ap.add_argument('--label-filter', help='label filter table (scripts/label_filter.py), or "on" to compute on demand; changes search')
    ap.add_argument('--label-map', help='scripts/label_map.py output: names of the tagger\'s grammar mapped onto this one (O91)')
    ap.add_argument('--map-types', action='store_true', help='with --label-map: map lexical types this grammar lacks')
    ap.add_argument('--map-rules', action='store_true', help='with --label-map: map rules this grammar lacks (unambiguous renames only)')
    ap.add_argument('--word-fallback', action='store_true', help='a word without an entry of the proposed type: offer its entries of other types with the same part of speech')
    ap.add_argument('--word-fallback-missing-only', action='store_true', help='the word fallback only for lexical types this grammar does not have at all')
    a = ap.parse_args()
    {'prepare': prepare, 'run': run, 'compare': compare}[a.cmd](a)


if __name__ == '__main__':
    main()
