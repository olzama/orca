#!/usr/bin/env python3
"""Where the grammar rejects the tagger's first guess, on held-out training sentences.

The five cross-validation fold taggers (scripts/cv_candidates.py) tagged the Redwoods
training sentences they did not see. For each sentence whose first guess the grammar
rejected, this replays that first guess once (no repair, no tagger needed), takes the
node where replay fails, and records the labels under it that differ from gold:
the labels the grammar's rejection points at. scripts/train_tagger.py --rejections
uses them as negative evidence (an unlikelihood term).

    rejections.py run --fold K            -> data/rejections/fold{K}.jsonl (resumable)
    rejections.py merge                   -> data/rejections/train-folds.jsonl + summary.json

One line per rejected sentence: id, n (tokens), span (token positions under the failing
node; all of them when the failure is at the root), root (failure at the root),
rejected [[kind, position, label], ...] (first-guess labels in the span that differ
from gold; tree labels only before the last token, as in repair).
Only sentences whose raw-text tokens match the treebank's (gold_forms_match) are used,
so positions line up with the training data.
"""
import argparse
import collections
import json
import os
import sys
import tempfile
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)
ORCA = os.path.join(HERE, '..')
OUT = os.path.join(ORCA, 'data', 'rejections')
REJECTED = ('accepted after repair', 'rejected, budget used', 'rejected, nothing left to try')   # first guess rejected


class Replayer:
    """The grammar side of orca_parse.Parser, without the tagger."""

    def __init__(self):
        import repair
        from orca.tfs.fast import FastGrammar
        from orca.tfs.grammar import Grammar
        from orca.tfs.lexicon import Lexicon
        from orca.tokens import known_words
        from orca_parse import DEFAULTS
        self.repair = repair
        self.ace, self.dat = DEFAULTS['ace'], DEFAULTS['dat']
        g = Grammar(DEFAULTS['grammar'])
        self.lx = Lexicon(g, os.path.dirname(DEFAULTS['grammar']))
        self.lx.locate_missing = True
        self.known = known_words(self.lx)
        self.fg = FastGrammar(g)
        for name, status in g.status.items():
            if status in ('rule', 'lex-rule'):
                self.fg.instance(name)
        self.args = SimpleNamespace(cache=True, kbest=1, budget=1, fanout=8, min_prob=0.001,
                                    commit=False, commit_min=0, root_focus=False)
        self.spans = []
        orig = repair.failing_tokens

        def record(*a, **k):                      # the failing node's tokens, as repair computes them
            out = orig(*a, **k)
            self.spans.append(out)
            return out
        repair.failing_tokens = record

    def first_failure(self, sid, text, first):
        """Replay the first guess once. Returns (span, root) or None if it is accepted."""
        from orca.tokens import lattice_path, token_chart
        path = lattice_path(token_chart(text, self.ace, self.dat), self.known)
        rforms = [q[0] for q in path]
        n = len(rforms)
        if n != len(first['leaf']):
            return 'token mismatch'
        top = {k: [[(first[k][j], 0.0, 1.0)] for j in range(n)] for k in ('leaf', 'tree')}
        st = {'id': sid, 'forms': rforms, 'leaf': [None] * n, 'tree': [None] * n}
        r = self.repair
        r._WORK = (self.fg, [st], [top], {sid: [q[1] for q in path]}, self.args, self.lx)
        r.GOLD_MRS.clear()
        self.spans.clear()
        outcome = r.search(0)[0]
        if outcome.startswith('accepted'):
            return None
        span = self.spans[0] if self.spans and self.spans[0] else list(range(n))
        return sorted(span), len(span) == n


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
    os.makedirs(OUT, exist_ok=True)
    path_out = os.path.join(OUT, f'fold{a.fold}.jsonl')
    done = set()
    if os.path.exists(path_out):
        for line in open(path_out, encoding='utf-8'):
            try:
                done.add(json.loads(line)['id'])
            except Exception:
                pass
    rp = Replayer()
    out = open(path_out, 'a', encoding='utf-8')
    t0, k = time.time(), 0
    for line in open(os.path.join(ORCA, 'data', 'cv-candidates', f'fold{a.fold}.jsonl'), encoding='utf-8'):
        r = json.loads(line)
        if r['outcome'] not in REJECTED or not r.get('gold_forms_match') or r['id'] in done or r['id'] not in raw:
            continue
        if a.limit and k >= a.limit:
            break
        rec = {'id': r['id'], 'n': len(r['forms'])}
        try:
            res = rp.first_failure(r['id'], raw[r['id']], r['first'])
        except Exception as e:
            res = f'error: {type(e).__name__}'
        if res is None:
            rec['status'] = 'accepted now'
        elif isinstance(res, str):
            rec['status'] = res
        else:
            span, root = res
            n, g, f = rec['n'], r['gold'], r['first']
            rej = [['leaf', j, f['leaf'][j]] for j in span if f['leaf'][j] != g['leaf'][j]]
            rej += [['tree', j, f['tree'][j]] for j in span if j < n - 1 and f['tree'][j] != g['tree'][j]]
            rec.update(status='rejected', span=span, root=root, rejected=rej)
        out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        out.flush()
        k += 1
        if k % 500 == 0:
            print(f'fold {a.fold}: {k} done, {(time.time() - t0) / k:.3f} s/sentence', flush=True)
    out.close()
    print(f'fold {a.fold}: finished, {k} sentences', flush=True)


def merge(a):
    st = collections.Counter()
    labels = collections.Counter()
    with open(os.path.join(OUT, 'train-folds.jsonl'), 'w', encoding='utf-8') as out:
        for k in range(5):
            p = os.path.join(OUT, f'fold{k}.jsonl')
            if not os.path.exists(p):
                st['missing folds'] += 1
                continue
            for line in open(p, encoding='utf-8'):
                r = json.loads(line)
                st[r['status']] += 1
                if r['status'] != 'rejected':
                    continue
                st['root failures'] += r['root']
                if not r['rejected']:
                    st['rejected, no label in the span differs from gold'] += 1
                    continue
                st['sentences with rejected labels'] += 1
                for kind, _, _ in r['rejected']:
                    labels[kind] += 1
                out.write(json.dumps({'id': r['id'], 'rejected': r['rejected']}, ensure_ascii=False) + '\n')
    s = {'sentences': dict(st), 'rejected labels': dict(labels)}
    json.dump(s, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1)
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
