#!/usr/bin/env python3
"""Break down the errors of a trained tagger on one split.

Tree head: is the depth wrong, the rule wrong, or both; which rules; how
errors spread over sentences. Both heads: how often the gold label is among
the k best (the ceiling for any method that lets the grammar choose among
the k best labels per token).

Usage:
    analyze_tagger_errors.py --data DATA_DIR --model MODEL_DIR --split test --out FILE
"""
import argparse
import collections
import json
import os
import sys

import torch
from transformers import AutoTokenizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_tagger import NONE, Tagger, batches, collate, read  # noqa: E402

KS = (1, 2, 3, 5, 10)


def split_tree(label):
    delta, _, node = label.partition('|')
    rules = node.split()
    return delta, ' '.join(rules[:-1]), rules[-1] if rules else ''


@torch.no_grad()
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--model', required=True)
    ap.add_argument('--split', default='test')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    labels = json.load(open(os.path.join(args.model, 'labels.json')))
    leaf_itos, tree_itos = labels['leaf'], labels['tree']
    leaf_stoi = {l: i for i, l in enumerate(leaf_itos)}
    tree_stoi = {l: i for i, l in enumerate(tree_itos)}
    tok = AutoTokenizer.from_pretrained(labels['encoder'])
    model = Tagger(labels['encoder'], len(leaf_itos), len(tree_itos)).to(device)
    model.load_state_dict(torch.load(os.path.join(args.model, 'model.pt'), map_location=device))
    model.eval()
    sents = read(os.path.join(args.data, f'{args.split}.jsonl'))

    n = 0
    topk = {'leaf': collections.Counter(), 'tree': collections.Counter()}
    sent_topk = {k: 0 for k in KS}            # sentences with every gold label in the k best
    kinds = collections.Counter()             # what is wrong in a tree label
    delta_off = collections.Counter()         # predicted depth minus gold depth
    rule_conf = collections.Counter()         # gold binary rule -> predicted
    rule_total, rule_wrong = collections.Counter(), collections.Counter()
    by_delta_total, by_delta_wrong = collections.Counter(), collections.Counter()
    errs_per_sent = collections.Counter()
    tree_with_leaf = collections.Counter()
    gold_prob_when_wrong = []

    for batch in batches(sents, 64, shuffle=False):
        ids, mask, first, leaf_gold, tree_gold, kept = collate(batch, tok, leaf_stoi, tree_stoi, device)
        with torch.autocast('cuda', dtype=torch.float16, enabled=device.type == 'cuda'):
            leaf_logits, tree_logits = model(ids, mask, first)
        leaf_top = leaf_logits.topk(max(KS), -1).indices
        tree_top = tree_logits.topk(max(KS), -1).indices
        tree_prob = tree_logits.float().softmax(-1)
        leaf_hit = leaf_top == leaf_gold[:, None]
        tree_hit = tree_top == tree_gold[:, None]
        at = 0
        for s, k in zip(batch, kept):
            sl = slice(at, at + k)
            n += k
            for kk in KS:
                lh = leaf_hit[sl, :kk].any(-1)
                th = tree_hit[sl, :kk].any(-1)
                topk['leaf'][kk] += int(lh.sum())
                topk['tree'][kk] += int(th.sum())
                sent_topk[kk] += bool(lh.all() and th.all())
            n_err = 0
            for j in range(k):
                gold = s['tree'][j]
                pred = tree_itos[int(tree_top[at + j, 0])]
                leaf_ok = bool(leaf_hit[at + j, 0])
                if gold == NONE:
                    continue
                gd, gu, gr = split_tree(gold)
                rule_total[gr] += 1
                by_delta_total[gd] += 1
                if pred == gold:
                    tree_with_leaf[('tree right', 'leaf right' if leaf_ok else 'leaf wrong')] += 1
                    continue
                tree_with_leaf[('tree wrong', 'leaf right' if leaf_ok else 'leaf wrong')] += 1
                n_err += 1
                rule_wrong[gr] += 1
                by_delta_wrong[gd] += 1
                if tree_gold[at + j] > 0:
                    gold_prob_when_wrong.append(float(tree_prob[at + j, tree_gold[at + j]]))
                if pred == NONE or '|' not in pred:
                    kinds['predicted no ancestor'] += 1
                    continue
                pd, pu, pr = split_tree(pred)
                wrong = [name for name, a, b in (('depth', gd, pd), ('unaries', gu, pu), ('rule', gr, pr)) if a != b]
                kinds[' + '.join(wrong)] += 1
                if gd != pd:
                    delta_off[max(-4, min(4, int(pd) - int(gd)))] += 1
                if gr != pr:
                    rule_conf[(gr, pr)] += 1
            errs_per_sent[min(n_err, 5)] += 1
            at += k

    gold_prob_when_wrong.sort()
    q = lambda p: gold_prob_when_wrong[int(p * (len(gold_prob_when_wrong) - 1))]
    total_err = sum(kinds.values())
    result = {
        'split': args.split, 'tokens': n, 'sentences': len(sents),
        'gold_in_k_best': {h: {str(k): topk[h][k] / n for k in KS} for h in topk},
        'sentences_with_all_gold_in_k_best': {str(k): sent_topk[k] / len(sents) for k in KS},
        'tree_errors': total_err,
        'tree_error_kinds': dict(kinds.most_common()),
        'depth_error_predicted_minus_gold': {str(k): delta_off[k] for k in sorted(delta_off)},
        'tree_error_rate_by_gold_delta': {d: [by_delta_wrong[d], by_delta_total[d]]
                                          for d in sorted(by_delta_total, key=int)},
        'tree_errors_per_sentence': {str(k): errs_per_sent[k] for k in sorted(errs_per_sent)},
        'tree_and_leaf': {' / '.join(k): v for k, v in tree_with_leaf.items()},
        'gold_probability_when_tree_wrong_quartiles': [q(0.25), q(0.5), q(0.75)],
        'rules_with_most_errors': [[r, rule_wrong[r], rule_total[r]]
                                   for r, _ in rule_wrong.most_common(25)],
        'most_common_rule_confusions': [[g, p, c] for (g, p), c in rule_conf.most_common(25)],
    }
    with open(args.out, 'w') as f:
        json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))


if __name__ == '__main__':
    main()
