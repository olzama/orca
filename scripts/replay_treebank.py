#!/usr/bin/env python3
"""Replay gold treebank derivations with the engine and report failures.

Every gold derivation should unify; each failure points at a gap in the
engine (or a mismatch between treebank and grammar version).

Usage:
    replay_treebank.py --grammar ERG_DIR/english.tdl --profiles SPLIT_DIR [--limit N] [--out FILE]
"""
import argparse
import collections
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.setrecursionlimit(20000)

from delphin import derivation, tsdb  # noqa: E402

from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--out')
    args = ap.parse_args()
    t0 = time.time()
    g = Grammar(args.grammar)
    print(f'grammar loaded in {time.time() - t0:.1f}s: {len(g.h.authored)} types, '
          f'{g.h.n_glb} added, {len(g.instances)} instances', flush=True)
    ok = fail = 0
    causes, examples = collections.Counter(), {}
    nodes = 0
    t1 = time.time()
    done = False
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if done or not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        i_der, i_pid = names.index('derivation'), names.index('parse-id')
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if not rec[i_der]:
                    continue
                d = derivation.from_string(rec[i_der])
                top = d.daughters[0] if d.entity.startswith('root') and d.daughters else d
                mark = g.u.mark()
                try:
                    g.replay(top)
                    ok += 1
                except ReplayFailure as e:
                    fail += 1
                    rule = e.where.split()[-1]
                    cause = str(e.cause)
                    key = f'{rule} | {cause}' if 'missing' in cause else cause
                    causes[key] += 1
                    examples.setdefault(key, f'{os.path.basename(prof)}/{rec[i_pid]} at {e.where}')
                del g.u.trail[mark:]
                nodes += len(d.internals()) if hasattr(d, 'internals') else 0
                if args.limit and ok + fail >= args.limit:
                    done = True
                    break
    secs = time.time() - t1
    result = {'derivations': ok + fail, 'replayed': ok, 'failed': fail,
              'seconds': secs, 'derivations_per_second': (ok + fail) / secs if secs else 0,
              'node_unifications': g.u.count,
              'failure_causes': [[k, c, examples[k]] for k, c in causes.most_common(40)]}
    print(json.dumps(result, indent=1))
    if args.out:
        with open(args.out, 'w') as f:
            json.dump(result, f, indent=1)


if __name__ == '__main__':
    main()
