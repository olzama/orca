#!/usr/bin/env python3
"""Which of the tagger's labels does the grammar really reject? (roadmap O113, step 1)

A label that differs from gold is not necessarily rejected: the grammar licenses many
analyses and gold is the one the annotators judged best. A rejection is a replay
failure. For each held-out training sentence whose first guess the grammar rejected
(scripts/rejections.py), this starts from gold, which replays, and puts back the first
guess's labels that differ from gold under the failing node:

  - one at a time: replay fails -> that label is rejected in gold's context ('single');
                   replay succeeds -> licensed there, only not gold ('licensed');
  - if no single label fails but the first guess does: pairs of the remaining labels,
    a failing pair is a rejected combination ('pair');
  - otherwise the failure needs three or more labels together ('larger').

Tree labels encode the bracketing; a put-back that the decoder cannot turn into a tree
counts as rejected too, but is recorded apart ('ill-formed').

    culprits.py run --fold K [--limit N]   -> data/rejections/culprits-fold{K}.jsonl (resumable)
    culprits.py merge                       -> data/rejections/culprits-train-folds.jsonl + culprits-summary.json

One line per sentence: id, status ('done', 'gold fails', 'first accepted now', 'token mismatch',
'error: ...'), and for 'done': diff [[kind, pos, label]], verdicts [{kind, pos, label, verdict}],
pairs [[i, j]] (indices into diff) of rejected combinations, larger (bool).
"""
import argparse
import collections
import itertools
import json
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)
ORCA = os.path.join(HERE, '..')
OUT = os.path.join(ORCA, 'data', 'rejections')
MAX_PAIRS = 45            # at most 10 labels' worth of pairs; beyond that, 'larger' unexamined


class Tester:
    def __init__(self):
        from rejections import Replayer
        self.rp = Replayer()

    def path(self, text):
        from orca.tokens import lattice_path, token_chart
        return lattice_path(token_chart(text, self.rp.ace, self.rp.dat), self.rp.known)

    def accepts(self, sid, path, labels):
        """Replay one label sequence once (no repair). True if the grammar accepts it,
        'ill-formed' if the labels do not decode to a tree, False if replay fails."""
        rp = self.rp
        n = len(path)
        top = {k: [[(labels[k][j], 0.0, 1.0)] for j in range(n)] for k in ('leaf', 'tree')}
        st = {'id': sid, 'forms': [q[0] for q in path], 'leaf': [None] * n, 'tree': [None] * n}
        r = rp.repair
        r._WORK = (rp.fg, [st], [top], {sid: [q[1] for q in path]}, rp.args, rp.lx)
        r.GOLD_MRS.clear()
        rp.spans.clear()
        outcome = r.search(0)[0]
        if outcome.startswith('accepted'):
            return True
        # repair calls failing_tokens only when a decoded tree fails in replay; a label
        # sequence that does not decode to a tree fails before that, leaving no span
        return False if rp.spans else 'ill-formed'

    def examine(self, sid, text, gold, first, span, n):
        path = self.path(text)
        if len(path) != n:
            return {'status': 'token mismatch'}
        if self.accepts(sid, path, gold) is not True:
            return {'status': 'gold fails'}
        if self.accepts(sid, path, first) is True:
            return {'status': 'first accepted now'}
        diff = [('leaf', j, first['leaf'][j]) for j in span if first['leaf'][j] != gold['leaf'][j]]
        diff += [('tree', j, first['tree'][j]) for j in span if j < n - 1 and first['tree'][j] != gold['tree'][j]]

        def with_(items):
            lab = {k: list(gold[k]) for k in ('leaf', 'tree')}
            for kind, j, label in items:
                lab[kind][j] = label
            return lab

        verdicts, ok = [], []
        for i, d in enumerate(diff):
            a = self.accepts(sid, path, with_([d]))
            v = 'licensed' if a is True else ('ill-formed' if a == 'ill-formed' else 'single')
            verdicts.append({'kind': d[0], 'pos': d[1], 'label': d[2], 'verdict': v})
            if a is True:
                ok.append(i)
        pairs, larger = [], False
        if len(ok) == len(diff) and diff:                     # every label fine alone: look for combinations
            cand = list(itertools.combinations(ok, 2))
            if len(cand) <= MAX_PAIRS:
                for i, j in cand:
                    if self.accepts(sid, path, with_([diff[i], diff[j]])) is not True:
                        pairs.append([i, j])
            larger = not pairs
        return {'status': 'done', 'diff': [list(d) for d in diff], 'verdicts': verdicts,
                'pairs': pairs, 'larger': larger}


def run(a):
    import torch
    torch.set_num_threads(1)
    from check_raw_tokens import raw_inputs
    data = os.path.join(ORCA, 'data', f'encoded-2025-bothall-surface-cv{a.fold}')
    fold = json.load(open(os.path.join(data, 'fold.json')))
    split = os.path.join(ORCA, 'data', 'profiles-2025', 'train')
    raw = {}
    for name in fold['profiles']:
        with tempfile.TemporaryDirectory() as d:
            os.symlink(os.path.realpath(os.path.join(split, name)), os.path.join(d, name))
            raw.update(raw_inputs(d))
    rej = {}
    for line in open(os.path.join(OUT, f'fold{a.fold}.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        if r.get('status') == 'rejected':
            rej[r['id']] = r['span']
    path_out = os.path.join(OUT, f'culprits-fold{a.fold}.jsonl')
    done = set()
    if os.path.exists(path_out):
        for line in open(path_out, encoding='utf-8'):
            try:
                done.add(json.loads(line)['id'])
            except Exception:
                pass
    t = Tester()
    out = open(path_out, 'a', encoding='utf-8')
    t0, k = time.time(), 0
    for line in open(os.path.join(ORCA, 'data', 'cv-candidates', f'fold{a.fold}.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        if r['id'] not in rej or r['id'] in done or r['id'] not in raw:
            continue
        if a.limit and k >= a.limit:
            break
        rec = {'id': r['id'], 'n': len(r['forms'])}
        try:
            rec.update(t.examine(r['id'], raw[r['id']], r['gold'], r['first'], rej[r['id']], len(r['forms'])))
        except Exception as e:
            rec['status'] = f'error: {type(e).__name__}: {str(e)[:120]}'
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        out.flush()
        k += 1
        if k % 200 == 0:
            print(f'fold {a.fold}: {k} done, {(time.time() - t0) / k:.3f} s/sentence', flush=True)
    out.close()
    print(f'fold {a.fold}: finished, {k} sentences', flush=True)


def merge(a):
    st, verd = collections.Counter(), collections.Counter()
    with open(os.path.join(OUT, 'culprits-train-folds.jsonl'), 'w', encoding='utf-8') as out:
        for k in range(5):
            p = os.path.join(OUT, f'culprits-fold{k}.jsonl')
            if not os.path.exists(p):
                st['missing folds'] += 1
                continue
            for line in open(p, encoding='utf-8'):
                r = json.loads(line)
                s = r['status'] if not r['status'].startswith('error') else 'error'
                st[s] += 1
                if s != 'done':
                    continue
                for v in r['verdicts']:
                    verd[(v['kind'], v['verdict'])] += 1
                if any(v['verdict'] != 'licensed' for v in r['verdicts']):
                    st['done: at least one single culprit'] += 1
                elif r['pairs']:
                    st['done: only pair culprits'] += 1
                elif r['larger']:
                    st['done: needs three or more labels'] += 1
                out.write(json.dumps(r, ensure_ascii=False) + '\n')
    s = {'sentences': dict(st), 'labels': {f'{k} {v}': c for (k, v), c in sorted(verd.items())}}
    json.dump(s, open(os.path.join(OUT, 'culprits-summary.json'), 'w'), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    r = sub.add_parser('run')
    r.add_argument('--fold', type=int, required=True)
    r.add_argument('--limit', type=int, default=0)
    sub.add_parser('merge')
    a = ap.parse_args()
    {'run': run, 'merge': merge}[a.cmd](a)
