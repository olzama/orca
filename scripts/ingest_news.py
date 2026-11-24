#!/usr/bin/env python3
"""Add the corpus session's 2025 news parses to the training data, as a delta.

The news profiles live in tiers under llm-syntax-data/tsdb/2025-tiered/results
(news-short-16g, news-long-46-60-28g, news-long-61-65-120g, and later retries),
one profile per 500-sentence chunk: TIER/SOURCE/SOURCE-NNN. Item ids (i-id =
parse-id) are numbered per SOURCE across chunks, and they match the ids of the
news sentences already in training ("SOURCE/i-id"); the source spelled
Quen14B-2025-llm here is Qwen14B-2025-llm in the training data.

  run       for each tier: sentences ACE parsed that are not yet in training, not
            ingested before, and not in the held-out sample are encoded, replayed
            with Orca's grammar (one grammar per worker process, loaded once),
            given the forms as typed, renamed SOURCE/i-id, and appended to
            OUT/train.jsonl; OUT/state.json records what was ingested, so a later
            retry tier adds only its own new sentences.
  assemble  writes a training folder: the base training files plus OUT/train.jsonl,
            with dev and test linked from the base folder.

Usage:
    ingest_news.py run [--tiers T ...] [--out data/encoded-news25] [--workers 6]
    ingest_news.py assemble --into data/encoded-2025-bothall-news25-surface
"""
import argparse
import collections
import concurrent.futures
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.setrecursionlimit(20000)
PY = sys.executable
RESULTS = '/mnt/kesha/llm-syntax-data/tsdb/2025-tiered/results'
TIERS = ['news-short-16g', 'news-long-46-60-28g', 'news-long-61-65-120g']
ALIAS = {'Quen14B-2025-llm': 'Qwen14B-2025-llm'}
BASE = [os.path.join(ROOT, 'data/encoded-2025-bothall-surface/train.jsonl'),
        os.path.join(ROOT, 'data/encoded-lit-new/train.jsonl')]
HOLD = os.path.join(ROOT, 'analysis/corpus-modes/sample.json')
ID = re.compile(r'^\{"id": "([^"/]+)/(\d+)"')


def canon(src):
    return ALIAS.get(src, src)


def known_keys(paths):
    """(source, i-id) of every news sentence already in these training files."""
    keys = set()
    for p in paths:
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                for line in f:
                    m = ID.match(line)
                    if m and '-20' in m.group(1):
                        keys.add((canon(m.group(1)), int(m.group(2))))
    return keys


def held_out_keys(path):
    """The news sentences of the corpus-modes evaluation sample: never trained on."""
    keys = set()
    if os.path.exists(path):
        for x in json.load(open(path))['sample']:
            if x.get('corpus') == 'news':
                prof, iid = x['id'].split('__', 1)[1].rsplit('/', 1)
                keys.add((canon(prof.rsplit('-', 1)[0]), int(iid)))
    return keys


def parsed_ids(chunk):
    """i-ids of a chunk profile with an ACE derivation (first result)."""
    out = set()
    p = os.path.join(chunk, 'result.gz')
    if not os.path.exists(p):
        p = os.path.join(chunk, 'result')
        if not os.path.exists(p):
            return out
    op = gzip.open if p.endswith('.gz') else open
    with op(p, 'rt', encoding='utf-8', errors='replace') as f:
        for line in f:
            a = line.split('@', 11)
            if len(a) > 10 and a[1] == '0' and a[10][:1] == '(':
                out.add(int(a[0]))
    return out


# -- replay filter, one grammar per worker process --------------------------
_W = {}


def _init(grammar):
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    g = Grammar(grammar)
    _W['fg'], _W['lx'] = FastGrammar(g), Lexicon(g, os.path.dirname(grammar))


def _check(prof_path, lines):
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.lexicon import replay_with_entries
    from replay_predictions import gold_tokens
    name = os.path.basename(prof_path)
    with tempfile.TemporaryDirectory() as d:
        os.symlink(os.path.realpath(prof_path), os.path.join(d, name))
        toks = gold_tokens(d)
    fg, lx = _W['fg'], _W['lx']
    ok, failed = [], collections.Counter()
    for line in lines:
        r = json.loads(line)
        forms, leaf, tree = labels_of(r['tokens'])
        fg.reset()
        try:
            replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), toks[r['id']])
            ok.append(line)
        except Exception as e:
            failed[type(e).__name__] += 1
    return name, ok, failed


def _encode(split_dir, e2t_dir, out):
    from encode_treebank import entry_types, run_split
    st, _ = run_split(split_dir, entry_types(e2t_dir), out)
    return {k: st[k] for k in ('derivations', 'round_trip_ok', 'round_trip_fail', 'not_binary', 'unreadable') if k in st}


def run(args):
    os.makedirs(args.out, exist_ok=True)
    state_path = os.path.join(args.out, 'state.json')
    state = json.load(open(state_path)) if os.path.exists(state_path) else {'ingested': []}
    done = {(s, i) for t in state['ingested'] for s, ids in t.get('ids', {}).items() for i in ids}
    have = known_keys(BASE) | done
    hold = held_out_keys(HOLD)
    grammar = os.path.join(args.erg, 'english.tdl')
    for tier in args.tiers:
        tdir = os.path.join(RESULTS, tier)
        if not os.path.isdir(tdir):
            print(f'{tier}: not there yet')
            continue
        if any(t['tier'] == tier for t in state['ingested']):
            print(f'{tier}: already ingested')
            continue
        stats = collections.Counter()
        want = {}                                       # link name -> set of new i-ids
        links = os.path.join(args.out, 'profiles', tier)
        os.makedirs(links, exist_ok=True)
        for src in sorted(os.listdir(tdir)):
            for ch in sorted(os.listdir(os.path.join(tdir, src))):
                chunk = os.path.join(tdir, src, ch)
                ids = parsed_ids(chunk)
                stats['parsed'] += len(ids)
                new = set()
                for i in ids:
                    k = (canon(src), i)
                    if k in hold:
                        stats['held out (evaluation sample)'] += 1
                    elif k in have:
                        stats['already in training'] += 1
                    else:
                        new.add(i)
                stats['new'] += len(new)
                if new:
                    link = os.path.join(links, ch)
                    if not os.path.exists(link):
                        os.symlink(chunk, link)
                    want[ch] = new
        print(tier, dict(stats), flush=True)
        if not want:
            state['ingested'].append({'tier': tier, 'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'stats': dict(stats), 'ids': {}})
            json.dump(state, open(state_path, 'w'), indent=1)
            continue
        with tempfile.TemporaryDirectory(dir=args.out) as tmp:
            # encode, the chunks split over the workers
            names = sorted(want)
            parts = [names[k::args.workers] for k in range(args.workers)]
            encs = []
            with concurrent.futures.ProcessPoolExecutor(args.workers) as pool:
                jobs = []
                for k, part in enumerate(parts):
                    if not part:
                        continue
                    sd = os.path.join(tmp, f'split{k}')
                    os.makedirs(sd)
                    for n in part:
                        os.symlink(os.path.join(links, n), os.path.join(sd, n))
                    encs.append(os.path.join(tmp, f'enc{k}.jsonl'))
                    jobs.append(pool.submit(_encode, sd, args.erg, encs[-1]))
                for j in jobs:
                    for key, v in j.result().items():
                        stats[f'encode: {key}'] += v
            by = collections.defaultdict(list)
            for e in encs:
                with open(e, encoding='utf-8') as f:
                    for line in f:
                        m = ID.match(line)
                        if m and int(m.group(2)) in want.get(m.group(1), ()):
                            by[m.group(1)].append(line)
            stats['encoded'] = sum(len(v) for v in by.values())
            # replay with Orca's grammar: one grammar per worker, loaded once
            ok_path = os.path.join(tmp, 'ok.jsonl')
            fails = collections.Counter()
            with concurrent.futures.ProcessPoolExecutor(args.workers, initializer=_init, initargs=(grammar,)) as pool, \
                    open(ok_path, 'w', encoding='utf-8') as okf:
                jobs = [pool.submit(_check, os.path.join(links, n), lines) for n, lines in by.items()]
                for j in concurrent.futures.as_completed(jobs):
                    name, ok, failed = j.result()
                    okf.writelines(ok)
                    stats['replayed'] += len(ok)
                    fails.update(failed)
            stats.update({f'rejected: {k}': v for k, v in fails.items()})
            # forms as typed
            surf = os.path.join(tmp, 'surface.jsonl')
            subprocess.run([PY, os.path.join(HERE, 'surface_forms.py'), '--encoded', ok_path, '--out', surf,
                            '--profiles', links, '--jobs', str(args.workers)], check=True, stdout=subprocess.DEVNULL)
            # rename CHUNK/pid -> SOURCE/i-id (parse-id = i-id in these profiles) and append
            ids = collections.defaultdict(list)
            n_out = 0
            with open(surf, encoding='utf-8') as f, open(os.path.join(args.out, 'train.jsonl'), 'a', encoding='utf-8') as out:
                for line in f:
                    r = json.loads(line)
                    ch, pid = r['id'].rsplit('/', 1)
                    src = canon(ch.rsplit('-', 1)[0])
                    r['id'] = f'{src}/{pid}'
                    ids[src].append(int(pid))
                    out.write(json.dumps(r, ensure_ascii=False) + '\n')
                    n_out += 1
            stats['added'] = n_out
        state['ingested'].append({'tier': tier, 'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'stats': dict(stats), 'ids': ids})
        json.dump(state, open(state_path, 'w'), indent=1)
        print(tier, json.dumps(dict(stats)), flush=True)


def assemble(args):
    base_dir = os.path.dirname(BASE[0])
    os.makedirs(args.into, exist_ok=True)
    counts = {}
    with open(os.path.join(args.into, 'train.jsonl'), 'w', encoding='utf-8') as out:
        for p in BASE + [os.path.join(args.out, 'train.jsonl')]:
            n = 0
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f:
                    for line in f:
                        out.write(line)
                        n += 1
            counts[os.path.relpath(p, ROOT)] = n
    for s in ('dev', 'test'):
        t = os.path.join(args.into, f'{s}.jsonl')
        if not os.path.exists(t):
            os.symlink(os.path.relpath(os.path.join(base_dir, f'{s}.jsonl'), args.into), t)
    state = json.load(open(os.path.join(args.out, 'state.json')))
    with open(os.path.join(args.into, 'README'), 'w') as f:
        f.write('Training data = the files below, concatenated; dev and test linked from encoded-2025-bothall-surface.\n')
        for p, n in counts.items():
            f.write(f'  {p}: {n:,} sentences\n')
        f.write(f'  total: {sum(counts.values()):,}\n')
        f.write('News 2025 (corpus session, ERG 13b615a, replayed with Orca\'s grammar), per tier:\n')
        for t in state['ingested']:
            f.write(f"  {t['tier']} ({t['when']}): {json.dumps(t['stats'])}\n")
        f.write('The news sentences of the corpus-modes evaluation sample (analysis/corpus-modes/sample.json) are never added.\n')
    print(json.dumps(counts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('run', 'assemble'))
    ap.add_argument('--tiers', nargs='+', default=TIERS)
    ap.add_argument('--out', default=os.path.join(ROOT, 'data/encoded-news25'))
    ap.add_argument('--into', default=os.path.join(ROOT, 'data/encoded-2025-bothall-news25-surface'))
    ap.add_argument('--erg', default=os.path.join(ROOT, 'data/erg/2025'))
    ap.add_argument('--workers', type=int, default=6)
    args = ap.parse_args()
    run(args) if args.cmd == 'run' else assemble(args)


if __name__ == '__main__':
    main()
