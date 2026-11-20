#!/usr/bin/env python3
"""What happens when predicted derivations are replayed: a closer look.

For rejected derivations: how many labels are wrong, how many separate
failure points there are, whether a failure point contains a wrong label,
and how much of the sentence still replays as complete subtrees (replay
continues in the sister subtrees after a failure).

For accepted derivations that differ from gold: what differs (lexical
labels, tree labels, only the root condition), by how much, and which
labels are exchanged most often.

Usage:
    analyze_replay_outcomes.py --grammar ERG/english.tdl --profiles SPLIT_DIR
                               --gold DATA/dev.jsonl --pred MODEL/dev-pred.jsonl --out FILE
"""
import argparse
import collections
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from eval_trees import brackets, to_leaves  # noqa: E402
from llm_label import read  # noqa: E402
from orca.encoding import Leaf, decode  # noqa: E402
from orca.tfs.dag import UnificationFailure, deref  # noqa: E402
from orca.tfs.grammar import ARGS, DELETED_DAUGHTERS, Grammar, ReplayFailure  # noqa: E402
from replay_predictions import gold_tokens  # noqa: E402

CONT = '<cont>'
BANDS = ((0, 10, 'under 10'), (10, 20, '10-19'), (20, 30, '20-29'), (30, 10 ** 6, '30 and over'))


def band(n):
    return next(name for lo, hi, name in BANDS if lo <= n < hi)


def partial_replay(g, tree, tokens):
    """Replay as much as possible. Returns (accepted, ok_spans, failures):
    ok_spans are the token spans of maximal subtrees that replay, failures
    are (start, end, label, cause) of the nodes where replay first fails."""
    u = g.u
    ok_spans, failures = [], []

    def go(t, pos):
        if isinstance(t, Leaf):
            end = pos + len(t.forms)
            try:
                fs, _ = g.replay_tree(t, tokens[pos:end])
                return fs, end
            except ReplayFailure as e:
                failures.append((pos, end, t.entry, str(e.cause)))
                return None, end
        name = t.label.lower()
        kids, cur = [], pos
        for c in t.children:
            fs, nxt = go(c, cur)
            kids.append((fs, cur, nxt))
            cur = nxt

        def give_up(cause=None):
            for fs, a, b in kids:
                if fs is not None:
                    ok_spans.append((a, b))
            if cause is not None:
                failures.append((pos, cur, name, cause))
            return None, cur

        if any(fs is None for fs, _, _ in kids):
            return give_up()
        try:
            if name.startswith('root_'):
                u.unify(u.copy(g.instance(name)), kids[0][0], ['<root>'])
                return kids[0][0], cur
            fs = u.copy(g.instance(name))
            arg = u.get(fs, ARGS)
            for i, (dfs, _, _) in enumerate(kids):
                u.unify(u.get(arg, 'FIRST'), dfs, [ARGS] + ['REST'] * i + ['FIRST'])
                arg = u.get(arg, 'REST')
            if g.h.glb(deref(arg).type, '*null*') is None:
                return give_up('too few daughters')
            fs = deref(fs)
            for f in DELETED_DAUGHTERS:
                fs.arcs.pop(f, None)
            return fs, cur
        except UnificationFailure as e:
            return give_up(str(e))
        except (KeyError, ValueError) as e:
            return give_up(f'label not usable here: {e}')

    mark = u.mark()
    fs, end = go(tree, 0)
    del u.trail[mark:]
    if fs is not None:
        ok_spans.append((0, end))
    return fs is not None, ok_spans, failures


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--gold', required=True)
    ap.add_argument('--pred', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    gold = {s['id']: s for s in read(args.gold)}
    with open(args.pred, encoding='utf-8') as f:
        preds = [json.loads(line) for line in f]
    tokens = gold_tokens(args.profiles)
    g = Grammar(args.grammar)

    rej = collections.defaultdict(lambda: collections.defaultdict(list))
    rej_n = collections.Counter()
    wrong_hist = collections.defaultdict(collections.Counter)
    fail_has_error = collections.Counter()
    acc_diff = collections.Counter()
    acc_diff_n = collections.Counter()
    conf_leaf, conf_tree = collections.Counter(), collections.Counter()
    diff_sizes = []
    match = n_gold = n_pred = 0
    outcome = collections.defaultdict(collections.Counter)

    for p in preds:
        s = gold[p['id']]
        n = len(p['forms'])
        b = band(n)
        leaf_wrong = [j for j in range(n) if p['leaf'][j] != s['leaf'][j]]
        tree_wrong = [j for j in range(n - 1) if p['tree'][j] != s['tree'][j]]
        wrong = sorted(set(leaf_wrong) | set(tree_wrong))
        try:
            tree = decode(to_leaves(p['forms'], p['leaf'], p['tree']))
        except Exception:
            outcome[b]['rejected'] += 1
            rej_n[b] += 1
            rej[b]['wrong labels'].append(len(leaf_wrong) + len(tree_wrong))
            rej[b]['failure points'].append(1)
            rej[b]['share of tokens in replayed subtrees'].append(0.0)
            rej[b]['share of tokens in largest replayed subtree'].append(0.0)
            continue
        accepted, ok_spans, failures = partial_replay(g, tree, tokens[p['id']])
        if accepted:
            if not wrong:
                outcome[b]['accepted, same as gold'] += 1
                continue
            outcome[b]['accepted, differs from gold'] += 1
            acc_diff_n[b] += 1
            root_only = (not leaf_wrong and all(
                p['tree'][j].split('|')[0] == s['tree'][j].split('|')[0]
                and [r for r in p['tree'][j].split('|', 1)[-1].split() if not r.startswith('root_')]
                == [r for r in s['tree'][j].split('|', 1)[-1].split() if not r.startswith('root_')]
                for j in tree_wrong)) or (not tree_wrong and all(
                    [r for r in p['leaf'][j].split() if 'root_' not in r] ==
                    [r for r in s['leaf'][j].split() if 'root_' not in r] for j in leaf_wrong))
            lextype_only = not tree_wrong and all(
                p['leaf'][j].split('|')[1:] == s['leaf'][j].split('|')[1:] for j in leaf_wrong)
            same_shape = all(p['tree'][j].split('|')[0] == s['tree'][j].split('|')[0] for j in tree_wrong)
            if root_only:
                kind = 'only the root condition differs'
            elif lextype_only:
                kind = 'only lexical types differ'
            elif not tree_wrong:
                kind = 'only leaf labels differ (lexical or unary rules)'
            elif same_shape:
                kind = 'same bracketing, different rule names'
            else:
                kind = 'different bracketing'
            acc_diff[kind] += 1
            diff_sizes.append(len(leaf_wrong) + len(tree_wrong))
            for j in leaf_wrong:
                conf_leaf[(s['leaf'][j], p['leaf'][j])] += 1
            for j in tree_wrong:
                conf_tree[(s['tree'][j], p['tree'][j])] += 1
            gb = brackets(decode(to_leaves(s['forms'], s['leaf'], s['tree'])))
            pb = brackets(tree)
            match += sum((gb & pb).values())
            n_gold += sum(gb.values())
            n_pred += sum(pb.values())
            continue
        outcome[b]['rejected'] += 1
        rej_n[b] += 1
        covered = set()
        for a, e in ok_spans:
            if e - a >= 2:
                covered.update(range(a, e))
        largest = max((e - a for a, e in ok_spans), default=0)
        rej[b]['wrong labels'].append(len(leaf_wrong) + len(tree_wrong))
        rej[b]['failure points'].append(len(failures))
        rej[b]['share of tokens in replayed subtrees'].append(len(covered) / n)
        rej[b]['share of tokens in largest replayed subtree'].append(largest / n)
        k = len(leaf_wrong) + len(tree_wrong)
        wrong_hist[b]['1' if k == 1 else '2' if k == 2 else '3-4' if k <= 4 else '5 or more'] += 1
        for a, e, _, _ in failures:
            fail_has_error['failure points'] += 1
            fail_has_error['with a wrong label inside'] += any(a <= j < e for j in wrong)
            fail_has_error['tokens under failure points'] += e - a
            fail_has_error['tokens in those sentences'] += n / len(failures)

    def summarize(values):
        return {'mean': round(statistics.mean(values), 3), 'median': statistics.median(values)} if values else None

    prec, rec = (match / n_pred, match / n_gold) if n_pred else (0, 0)
    result = {
        'outcome_by_length': {b: dict(outcome[b]) for _, _, b in BANDS},
        'rejected': {b: {'sentences': rej_n[b],
                         **{k: summarize(v) for k, v in rej[b].items()},
                         'wrong labels per sentence': dict(wrong_hist[b])} for _, _, b in BANDS},
        'failure_points': dict(fail_has_error),
        'accepted_but_different': {
            'sentences': sum(acc_diff_n.values()), 'by_length': dict(acc_diff_n),
            'kind': dict(acc_diff.most_common()),
            'labels that differ per sentence': summarize(diff_sizes),
            'bracket_f1_against_gold': 2 * prec * rec / (prec + rec) if prec + rec else None,
            'most common leaf differences (gold -> predicted)': [[a, b, c] for (a, b), c in conf_leaf.most_common(15)],
            'most common tree differences (gold -> predicted)': [[a, b, c] for (a, b), c in conf_tree.most_common(15)],
        },
    }
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
