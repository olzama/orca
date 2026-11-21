#!/usr/bin/env python3
"""Keep the silver derivations that Orca's grammar can replay, and hold out
part of each profile.

Silver data parsed with another version of the grammar may contain lexical
entries or rules that this version lacks or has changed. Every encoded
sentence is replayed (labels, entries from the lexicon, the profile's token
feature structures); sentences that fail are dropped. A different MRS is
not a reason to drop: the tree is still licensed by this grammar.

The last --hold share of each profile's sentences (by parse id, so that
neighboring sentences of one text stay together) goes to the held-out file.

Usage:
    filter_replayable.py --grammar ERG/english.tdl --profiles DIR --encoded IN.jsonl
                         --out-train OUT.jsonl --out-held HELD.jsonl --stats FILE.json
                         [--hold 0.1] [--workers 4]
"""
import argparse
import collections
import concurrent.futures
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def check_profile(args, name, sents):
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon, replay_with_entries
    from replay_predictions import gold_tokens
    import tempfile
    g = Grammar(args.grammar)
    fg, lx = FastGrammar(g), Lexicon(g, os.path.dirname(args.grammar))
    with tempfile.TemporaryDirectory() as d:          # gold_tokens reads a directory of profiles
        os.symlink(os.path.realpath(os.path.join(args.profiles, name)), os.path.join(d, name))
        toks = gold_tokens(d)
    ok, failed = [], collections.Counter()
    for line in sents:
        r = json.loads(line)
        forms, leaf, tree = labels_of(r['tokens'])
        fg.reset()
        try:
            replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), toks[r['id']])
            ok.append(line)
        except Exception as e:
            failed[type(e).__name__] += 1
    return name, ok, failed, len(sents)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--encoded', required=True)
    ap.add_argument('--out-train', required=True)
    ap.add_argument('--out-held', required=True)
    ap.add_argument('--stats', required=True)
    ap.add_argument('--hold', type=float, default=0.1)
    ap.add_argument('--workers', type=int, default=4)
    args = ap.parse_args()
    by = collections.defaultdict(list)
    with open(args.encoded, encoding='utf-8') as f:
        for line in f:
            by[line[8:line.index('/', 8)]].append(line)   # {"id": "PROFILE/...
    stats = {}
    # one profile per process: a second Grammar loaded in the same process breaks replay
    with concurrent.futures.ProcessPoolExecutor(args.workers, max_tasks_per_child=1) as pool, \
            open(args.out_train, 'w', encoding='utf-8') as tr, open(args.out_held, 'w', encoding='utf-8') as he:
        jobs = [pool.submit(check_profile, args, n, s) for n, s in by.items()]
        for job in concurrent.futures.as_completed(jobs):
            name, ok, failed, total = job.result()
            ok.sort(key=lambda l: int(json.loads(l)['id'].split('/')[1]))
            cut = int(len(ok) * (1 - args.hold))
            tr.writelines(ok[:cut])
            he.writelines(ok[cut:])
            stats[name] = {'sentences': total, 'replayed': len(ok), 'failed': dict(failed),
                           'train': cut, 'held out': len(ok) - cut}
            print(name, stats[name], flush=True)
    with open(args.stats, 'w') as f:
        json.dump(stats, f, indent=1, sort_keys=True)


if __name__ == '__main__':
    main()
