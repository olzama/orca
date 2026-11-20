#!/usr/bin/env python3
"""Decode predicted label sequences to trees and compare them with gold trees.

Reports labeled bracket precision, recall and F1 over all nodes (phrasal
rules, lexical rules and lexical types, each with its token span), and the
share of sentences whose whole tree is right, by sentence length.

Usage:
    eval_trees.py --gold DATA_DIR/test.jsonl --pred MODEL_DIR/test-pred.jsonl [--out FILE]
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from orca.encoding import Leaf, LeafLabel, Node, absolute_depths, decode  # noqa: E402

CONT = '<cont>'


def to_leaves(forms, leaf_labels, tree_labels):
    """Token-level label strings to leaf labels; continuation tokens are merged."""
    leaves, deltas = [], []
    for form, ll, tl in zip(forms, leaf_labels, tree_labels):
        parts = (ll.split('|') + ['', ''])[:3]
        if parts[0] == CONT and leaves:
            last = leaves[-1]
            leaves[-1] = LeafLabel(last.entry, last.forms + (form,), last.chain, node=last.node)
            continue
        chain = tuple(parts[2].split()) + tuple(parts[1].split())
        delta, _, node = tl.partition('|')
        try:
            delta = int(delta)
        except ValueError:          # <none> or <unk> where a tree label is needed
            delta, node = 0, '<unk>'
        leaves.append(LeafLabel(parts[0], (form,), chain, node=tuple(node.split()) or ('<unk>',)))
        deltas.append(delta)
    deltas[-1] = None
    leaves[-1].node = None
    for leaf, depth in zip(leaves, absolute_depths(deltas)):
        leaf.depth = depth
    return leaves


def brackets(tree):
    out = collections.Counter()

    def walk(t, start):
        if isinstance(t, Leaf):
            end = start + len(t.forms)
            out[(t.entry, start, end)] += 1
            return end
        end = start
        for c in t.children:
            end = walk(c, end)
        out[(t.label, start, end)] += 1
        return end

    walk(tree, 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gold', required=True)
    ap.add_argument('--pred', required=True)
    ap.add_argument('--out')
    args = ap.parse_args()

    gold = {}
    with open(args.gold, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            t = r['tokens']
            gold[r['id']] = ([x['form'] for x in t],
                             [f"{x['lextype']}|{x['lexrules']}|{x['unaries']}" for x in t],
                             ['<none>' if x['node'] is None else f"{x['delta']}|{x['node']}" for x in t])
    match = n_gold = n_pred = 0
    total, exact = collections.Counter(), collections.Counter()
    with open(args.pred, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            g = decode(to_leaves(*gold[r['id']]))
            p = decode(to_leaves(r['forms'], r['leaf'], r['tree']))
            gb, pb = brackets(g), brackets(p)
            match += sum((gb & pb).values())
            n_gold += sum(gb.values())
            n_pred += sum(pb.values())
            band = min(len(r['forms']) // 10 * 10, 60)
            total[band] += 1
            exact[band] += g == p
    prec, rec = match / n_pred, match / n_gold
    result = {
        'sentences': sum(total.values()),
        'bracket_precision': prec, 'bracket_recall': rec,
        'bracket_f1': 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        'exact_tree': sum(exact.values()) / sum(total.values()),
        'exact_tree_by_length': {str(b): [exact[b], total[b]] for b in sorted(total)},
    }
    print(json.dumps(result, indent=1))
    if args.out:
        with open(args.out, 'w') as f:
            json.dump(result, f, indent=1)


if __name__ == '__main__':
    main()
