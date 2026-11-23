#!/usr/bin/env python3
"""Compare Orca's parsing modes (replay, chart, fallback) on real corpus text,
against ACE's first parse in the corpus profiles (unchecked silver).

Steps:
  sample   draw sentences from held-out novel excerpts and the 2025 news, stratified
           human vs LLM; link their profiles into OUT/profiles; write OUT/sample.json
  replay   check which ACE derivations Orca's grammar replays (ACE parsed with ERG
           13b615a, Orca uses f017ef8): OUT/replayable.json
  run      parse every sampled sentence in each mode (GPU tagging), OUT/run-<mode>.json
  score    tables by source, text kind and length band: OUT/summary.json
  judgeeval  write OUT/eval-<mode>.json in orca_parse's eval format, for adjudicate.py

Usage:
  corpus_modes.py sample --out analysis/corpus-modes [--novels 1000 --news 1000]
  corpus_modes.py replay --out analysis/corpus-modes
  corpus_modes.py run --out analysis/corpus-modes --mode replay|chart|fallback
  corpus_modes.py score --out analysis/corpus-modes
"""
import argparse
import collections
import glob
import json
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)
ROOT = os.path.join(HERE, '..')

NOVEL_DEV = os.path.join(ROOT, 'data/profiles-lit/dev')
NEWS = '/mnt/kesha/llm-syntax-data/tsdb/2025-tiered/results/news-short-16g'
BANDS = ((0, 10, 'under 10'), (10, 20, '10-19'), (20, 30, '20-29'), (30, 10 ** 6, '30 and over'))


def read_profile(prof):
    """parse-id -> (input, first ACE MRS or None, first derivation or None)."""
    from delphin import tsdb
    items = {}
    names = [f.name for f in tsdb.read_schema(prof)['item']]
    with tsdb.open(prof, 'item') as rows:
        for line in rows:
            r = tsdb.split(line)
            items[r[names.index('i-id')]] = r[names.index('i-input')]
    pid2item = {}
    names = [f.name for f in tsdb.read_schema(prof)['parse']]
    with tsdb.open(prof, 'parse') as rows:
        for line in rows:
            r = tsdb.split(line)
            pid2item[r[names.index('parse-id')]] = r[names.index('i-id')]
    res = {}
    names = [f.name for f in tsdb.read_schema(prof)['result']]
    try:
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                r = tsdb.split(line)
                pid = r[names.index('parse-id')]
                if pid not in res or str(r[names.index('result-id')]) == '0':
                    res[pid] = (r[names.index('mrs')], r[names.index('derivation')])
    except Exception:
        pass
    return {pid: (items[iid],) + res.get(pid, (None, None)) for pid, iid in pid2item.items()}


def profiles_under(d):
    return sorted(p for p in glob.glob(os.path.join(d, '**'), recursive=True) if os.path.exists(os.path.join(p, 'relations')))


def cmd_sample(a):
    rng = random.Random(11)
    out = a.out
    os.makedirs(os.path.join(out, 'profiles'), exist_ok=True)
    pool = collections.defaultdict(list)      # stratum -> [(profile path, pid)]
    for prof in profiles_under(NOVEL_DEV):
        kind = 'human' if os.path.basename(prof).startswith('human__') else 'LLM'
        for pid, (text, _, _) in read_profile(os.path.realpath(prof)).items():
            if text.strip():
                pool[('novels', kind)].append((os.path.realpath(prof), pid))
    news_profs = profiles_under(NEWS)
    for prof in news_profs:
        src = os.path.relpath(prof, NEWS).split(os.sep)[0]
        kind = 'human' if src.endswith('-human') else 'LLM'
        for pid, (text, _, _) in read_profile(prof).items():
            if text.strip():
                pool[('news', kind)].append((prof, pid))
    want = {('novels', 'human'): a.novels // 2, ('novels', 'LLM'): a.novels - a.novels // 2,
            ('news', 'human'): a.news // 2, ('news', 'LLM'): a.news - a.news // 2}
    sample, used = [], set()
    for (corpus, kind), n in want.items():
        picks = rng.sample(pool[(corpus, kind)], min(n, len(pool[(corpus, kind)])))
        for prof, pid in picks:
            name = (corpus + '-' + os.path.relpath(prof, NEWS if corpus == 'news' else os.path.realpath(NOVEL_DEV)).replace(os.sep, '__'))
            if name not in used:
                link = os.path.join(out, 'profiles', name)
                if not os.path.exists(link):
                    os.symlink(prof, link)
                used.add(name)
            sample.append({'id': f'{name}/{pid}', 'corpus': corpus, 'kind': kind})
    json.dump({'pool sizes': {f'{c}/{k}': len(v) for (c, k), v in pool.items()}, 'sample': sample}, open(os.path.join(out, 'sample.json'), 'w'), indent=1)
    print({f'{c}/{k}': len(v) for (c, k), v in pool.items()}, len(sample), 'profiles', len(used))


def load_sample(out):
    s = json.load(open(os.path.join(out, 'sample.json')))['sample']
    texts = {}
    profs = sorted({x['id'].split('/')[0] for x in s})
    for name in profs:
        for pid, v in read_profile(os.path.join(out, 'profiles', name)).items():
            texts[f'{name}/{pid}'] = v
    return s, texts


def cmd_replay(a):
    """Encode ACE's derivations of the sampled sentences and replay them with Orca's grammar."""
    from encode_treebank import entry_types
    s, _ = load_sample(a.out)
    want = {x['id'] for x in s}
    erg = os.path.join(ROOT, 'data/erg/2025')
    from delphin import derivation
    from encode_treebank import to_tree, token_rows
    from orca.encoding import encode
    e2t = entry_types(erg)
    _, texts = load_sample(a.out)
    keep = os.path.join(a.out, 'encoded.jsonl')
    n = 0
    with open(keep, 'w') as o:                  # only the sampled sentences (encoding whole profiles is slow)
        for sid in sorted(want):
            der = texts[sid][2]
            if not der:
                continue
            try:
                leaves = encode(to_tree(derivation.from_string(der)))
            except Exception:
                continue
            o.write(json.dumps({'id': sid, 'tokens': token_rows(leaves, e2t)}, ensure_ascii=False) + '\n'); n += 1
    # replay in this process: one grammar load, tokens from the sampled derivations only
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon, replay_with_entries
    g = Grammar(os.path.join(erg, 'english.tdl'))
    fg, lx = FastGrammar(g), Lexicon(g, erg)
    ok = []
    for line in open(keep):
        r = json.loads(line)
        d = derivation.from_string(texts[r['id']][2])
        toks = [tok.tfs for term in d.terminals() for tok in (term.tokens or [])]
        forms, leaf, tree = labels_of(r['tokens'])
        fg.reset()
        try:
            replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), toks)
            ok.append(r['id'])
        except Exception:
            pass
    json.dump({'encoded': n, 'replayable': sorted(ok)}, open(os.path.join(a.out, 'replayable.json'), 'w'))
    print('encoded', n, 'replayable', len(ok))


def cmd_run(a):
    from compare_mrs import normalized
    from delphin.codecs import simplemrs
    from delphin import mrs as M
    from orca_parse import Parser
    s, texts = load_sample(a.out)
    p = Parser(mode=a.mode, chart_min_prob=a.chart_min_prob)
    p.parse('The dog barked.')
    recs, t0 = [], time.time()
    for x in s:
        text, ref, _ = texts[x['id']]
        r = p.parse(text, x['id'])
        m = r.pop('_mrs_obj', None)
        r.pop('_fs', None)
        same = None
        if m is not None and ref:
            try:
                same = bool(M.is_isomorphic(normalized(m), normalized(simplemrs.decode(ref)), properties=False))
            except Exception:
                same = None
        recs.append({'id': x['id'], 'analysis': m is not None, 'same as ACE': same, 'ACE parsed': bool(ref),
                     'outcome': r.get('outcome'), 'seconds': r.get('seconds'), 'mrs': r.get('mrs')})
    wall = time.time() - t0
    json.dump({'mode': a.mode, 'chart_min_prob': a.chart_min_prob, 'wall seconds': wall, 'sentences per second': len(recs) / wall, 'records': recs},
              open(os.path.join(a.out, f'run-{a.mode}.json'), 'w'))
    print(a.mode, len(recs), round(len(recs) / wall, 2))


def cmd_score(a):
    s, texts = load_sample(a.out)
    meta = {x['id']: x for x in s}
    rp = set(json.load(open(os.path.join(a.out, 'replayable.json')))['replayable'])
    band = lambda sid: next(nm for lo, hi, nm in BANDS if lo <= len(texts[sid][0].split()) < hi)
    out = {'sentences': len(s), 'ACE parsed': sum(bool(texts[x['id']][1]) for x in s), 'ACE derivation replayable': len(rp), 'modes': {}}
    for mode in ('replay', 'fallback', 'chart'):
        f = os.path.join(a.out, f'run-{mode}.json')
        if not os.path.exists(f):
            continue
        run = json.load(open(f))
        c = collections.defaultdict(collections.Counter)
        for r in run['records']:
            m = meta[r['id']]
            for key in ('all', m['corpus'], f"{m['corpus']}/{m['kind']}", f"band {band(r['id'])}"):
                c[key]['n'] += 1
                c[key]['analysis'] += r['analysis']
                c[key]['ACE parsed'] += r['ACE parsed']
                c[key]['same as ACE'] += bool(r['same as ACE'])
                if r['id'] in rp:
                    c[key]['n replayable'] += 1
                    c[key]['same as ACE, replayable'] += bool(r['same as ACE'])
        out['modes'][mode] = {'sentences per second': run['sentences per second'], 'counts': {k: dict(v) for k, v in c.items()}}
    json.dump(out, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    print(json.dumps({m: {k: v for k, v in d['counts']['all'].items()} | {'sps': round(d['sentences per second'], 2)} for m, d in out['modes'].items()}, indent=1))


def cmd_judgeeval(a):
    run = json.load(open(os.path.join(a.out, f'run-{a.mode}.json')))
    recs = [{'id': r['id'], 'same MRS': bool(r['same as ACE']), 'mrs': r['mrs']} for r in run['records'] if r['ACE parsed']]
    json.dump({'records': recs}, open(os.path.join(a.out, f'eval-{a.mode}.json'), 'w'))
    print(len(recs))


def cmd_judgeitems(a):
    """Judge items for a pair of systems where both have an analysis and differ:
    --pair chart-replay or chart-ace. The first system is the 'orca' side of adjudicate.py."""
    from compare_mrs import normalized
    from delphin.codecs import simplemrs
    from llm_rank import facts
    s, texts = load_sample(a.out)
    first, second = a.pair.split('-')
    runs = {m: {r['id']: r for r in json.load(open(os.path.join(a.out, f'run-{m}.json')))['records']} for m in {first, second} - {'ace'}}
    def mrs_of(sys_, sid):
        if sys_ == 'ace':
            return texts[sid][1]
        return runs[sys_][sid]['mrs']
    rng = random.Random(23)
    cand = []
    for x in s:
        sid = x['id']
        m1, m2 = mrs_of(first, sid), mrs_of(second, sid)
        if not m1 or not m2:
            continue
        try:
            f1, f2 = facts(normalized(simplemrs.decode(m1))), facts(normalized(simplemrs.decode(m2)))
        except Exception:
            continue
        o, b = sorted((f1 - f2).elements()), sorted((f2 - f1).elements())
        if o or b:
            cand.append((sid, o, b))
    rng.shuffle(cand)
    d = os.path.join(a.out, f'judge-{a.pair}')
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, 'items.jsonl'), 'w') as f:
        for sid, o, b in cand[:a.max]:
            first_a = rng.random() < 0.5
            f.write(json.dumps({'id': sid, 'sentence': texts[sid][0], 'A': o if first_a else b, 'B': b if first_a else o,
                                'orca': 'A' if first_a else 'B'}, ensure_ascii=False) + '\n')
    json.dump({'pair': a.pair, 'orca side': first, 'reference side': second, 'disagreements': len(cand), 'judged': min(a.max, len(cand))},
              open(os.path.join(d, 'prepare.json'), 'w'), indent=1)
    print(a.pair, 'disagreements', len(cand), 'to judge', min(a.max, len(cand)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('sample', 'replay', 'run', 'score', 'judgeeval', 'judgeitems'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'analysis/corpus-modes'))
    ap.add_argument('--novels', type=int, default=1000)
    ap.add_argument('--news', type=int, default=1000)
    ap.add_argument('--mode', default='replay')
    ap.add_argument('--chart-min-prob', type=float, default=0.001)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--pair', default='chart-replay')
    ap.add_argument('--max', type=int, default=150)
    a = ap.parse_args()
    {'sample': cmd_sample, 'replay': cmd_replay, 'run': cmd_run, 'score': cmd_score, 'judgeeval': cmd_judgeeval, 'judgeitems': cmd_judgeitems}[a.cmd](a)


if __name__ == '__main__':
    main()
