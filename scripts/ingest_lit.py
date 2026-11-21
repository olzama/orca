#!/usr/bin/env python3
"""Add new parses of the literary corpus to the training data.

The corpus session rebuilds profiles/merged-sofar from all its parsing runs
and then writes profiles/merged-sofar.COMPLETE with a timestamp. Item ids
and profile names stay the same between rebuilds; sentences that failed
before (memory, time) may now have a parse. This script:

  1. does nothing if COMPLETE is missing or its timestamp was already ingested;
  2. encodes the train profiles (data/profiles-lit/train, symlinks into
     merged-sofar; dev and test excerpts are never read);
  3. keeps the sentences not yet in the training data (the base set, plus
     earlier ingests);
  4. keeps those that the grammar replays (filter_replayable.py, nothing held out);
  5. replaces their forms by the text as typed (surface_forms.py);
  6. appends them to OUT_DIR/train.jsonl and records the timestamp.

If COMPLETE changes while reading, the run stops without writing; run it again.

Usage:
    ingest_lit.py [--base data/encoded-2025-bothall-surface/train.jsonl] [--out data/encoded-lit-new]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)

CORPUS = '/mnt/kesha/Human-LLM-Matched-Excerpts-Corpus/profiles'
COMPLETE = os.path.join(CORPUS, 'merged-sofar.COMPLETE')
PY = os.path.join(ROOT, '.venv/bin/python')


def stamp():
    try:
        return open(COMPLETE).read().strip()
    except OSError:
        return None


def ids(path):
    out = set()
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            for line in f:
                out.add(json.loads(line)['id'])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=os.path.join(ROOT, 'data/encoded-2025-bothall-surface/train.jsonl'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'data/encoded-lit-new'))
    ap.add_argument('--profiles', default=os.path.join(ROOT, 'data/profiles-lit/train'))
    ap.add_argument('--erg', default=os.path.join(ROOT, 'data/erg/2025'))
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    state_path = os.path.join(args.out, 'state.json')
    state = json.load(open(state_path)) if os.path.exists(state_path) else {'ingested': []}
    ts = stamp()
    if ts is None:
        print('no merged-sofar.COMPLETE: a rebuild may be under way; try later')
        return
    if any(r['complete'] == ts for r in state['ingested']):
        print(f'already ingested the rebuild of {ts}')
        return
    from encode_treebank import entry_types, run_split
    train_out = os.path.join(args.out, 'train.jsonl')
    with tempfile.TemporaryDirectory(dir=args.out) as tmp:
        enc = os.path.join(tmp, 'encoded.jsonl')
        run_split(args.profiles, entry_types(args.erg), enc)
        if stamp() != ts:
            print('merged-sofar was rebuilt while reading; nothing written, run again')
            return
        have = ids(args.base) | ids(train_out)
        new = os.path.join(tmp, 'new.jsonl')
        n_enc = n_new = 0
        with open(enc, encoding='utf-8') as f, open(new, 'w', encoding='utf-8') as out:
            for line in f:
                n_enc += 1
                if json.loads(line)['id'] not in have:
                    out.write(line)
                    n_new += 1
        stats = {'complete': ts, 'when': time.strftime('%Y-%m-%dT%H:%M:%S'), 'encoded': n_enc, 'new': n_new}
        if n_new:
            ok, held = os.path.join(tmp, 'ok.jsonl'), os.path.join(tmp, 'held.jsonl')
            subprocess.run([PY, os.path.join(HERE, 'filter_replayable.py'), '--grammar', os.path.join(args.erg, 'english.tdl'),
                            '--profiles', args.profiles, '--encoded', new, '--out-train', ok, '--out-held', held,
                            '--stats', os.path.join(tmp, 'filter.json'), '--hold', '0', '--workers', str(args.workers)],
                           check=True)
            surf = os.path.join(tmp, 'surface.jsonl')
            subprocess.run([PY, os.path.join(HERE, 'surface_forms.py'), '--encoded', ok, '--out', surf,
                            '--profiles', args.profiles], check=True, stdout=subprocess.DEVNULL)
            if stamp() != ts:
                print('merged-sofar was rebuilt while reading; nothing written, run again')
                return
            stats['replayable'] = len(ids(surf))
            with open(surf, encoding='utf-8') as f, open(train_out, 'a', encoding='utf-8') as out:
                for line in f:
                    out.write(line)
        state['ingested'].append(stats)
        json.dump(state, open(state_path, 'w'), indent=1)
        print(json.dumps(stats))


if __name__ == '__main__':
    main()
