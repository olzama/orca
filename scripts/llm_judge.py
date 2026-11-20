#!/usr/bin/env python3
"""Experiment: an LLM settles the tagger's doubtful decisions.

The tagger labels each sentence. Wherever its best label has a probability
below a threshold, its k best labels become the options of a decision. Each
option is shown in readable form: for a tree label, the rule and the two
stretches of words it would combine; for a leaf label, the lexical type and
rules. The LLM picks one option per decision; all other labels stay as the
tagger had them.

Usage:
    llm_judge.py --data DATA_DIR --erg ERG_DIR --tagger MODEL_DIR --out OUT_DIR
                 [--n 100] [--threshold 0.9] [--k 5] [--model M] [--dry-run]
"""
import argparse
import collections
import json
import os
import random
import re
import sys

import torch
from transformers import AutoTokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

from eval_trees import to_leaves  # noqa: E402
from llm_label import call, read, render, rule_docs  # noqa: E402
from orca.encoding import Leaf, decode  # noqa: E402
from train_tagger import NONE, UNK, Tagger, collate  # noqa: E402

CONT = '<cont>'
LETTERS = 'ABCDEFGH'

SYSTEM = """You help choose the correct syntactic analysis of English sentences in the style of \
the English Resource Grammar (ERG), an HPSG grammar. A derivation is a tree: internal nodes are \
grammar rules with one or two daughters, leaves are lexical types (names ending in _le), and \
lexical rules (names ending in lr) apply directly above a leaf.

Documentation of the grammar's rules, from the grammar itself (name: description, with an example):

{docs}

A statistical tagger has analyzed each sentence. You are shown its analysis as a bracketed tree and \
a list of decisions where it was unsure. Each decision has lettered options with the tagger's own \
probability. Option A is always the tagger's first choice, and it is right more often than any other \
single option, so move away from A only when the sentence gives a reason.

Two kinds of decision:
- Lexical: which lexical type and rules a word has.
- Structural: after a given word, which rule joins which stretch of words on the left with which \
stretch on the right. The stretches shown for each option assume the tagger's first choice for all \
other decisions.

Choose the option that the ERG treebank would have. Answer with exactly one line per decision, in \
the form `3.2: B` (sentence number, decision number, letter). No other text."""


def split_node(tree, leaf_index):
    """The binary node whose left daughter ends at the given leaf, with spans."""
    found = {}

    def walk(t, start):
        if isinstance(t, Leaf):
            return start + 1
        if len(t.children) == 1:
            return walk(t.children[0], start)
        mid = walk(t.children[0], start)
        end = walk(t.children[1], mid)
        if mid - 1 == leaf_index:
            found['span'] = (start, mid, end)
        return end

    walk(tree, 0)
    return found.get('span')


def leaf_texts(forms, leaf_labels):
    """Text of each leaf (continuation tokens merged into the leaf before)."""
    texts = []
    for f, l in zip(forms, leaf_labels):
        if l.startswith(CONT) and texts:
            texts[-1] += ' ' + f
        else:
            texts.append(f)
    return texts


def describe_tree(option, j, forms, base_leaf, base_tree, docs):
    if '|' not in option:
        return None
    labels = list(base_tree)
    labels[j] = option
    try:
        tree = decode(to_leaves(forms, base_leaf, labels))
    except Exception:
        return None
    li = sum(1 for l in base_leaf[:j] if not l.startswith(CONT))
    span = split_node(tree, li)
    if span is None:
        return None
    texts = leaf_texts(forms, base_leaf)
    start, mid, end = span
    rules = option.split('|', 1)[1].split()
    rule, above = rules[-1], rules[:-1]
    out = f"{rule} joins [{' '.join(texts[start:mid])}] + [{' '.join(texts[mid:end])}]"
    if above:
        out += f"; then unary {' , '.join(reversed(above))} on the result"
    if rule in docs:
        out += f'  ({docs[rule]})'
    return out


def describe_leaf(option, type_words):
    if option.startswith(CONT):
        return 'this word continues the previous word as one multi-word lexical entry'
    parts = (option.split('|') + ['', ''])[:3]
    if parts[0] == UNK:
        return None
    out = parts[0]
    if parts[1]:
        out += ' + lexical rules ' + parts[1]
    if parts[2]:
        out += '; then unary rules ' + parts[2]
    words = type_words.get(parts[0])
    if words:
        out += f"  (other words of this type: {', '.join(words)})"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--erg', required=True)
    ap.add_argument('--tagger', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', default='dev')
    ap.add_argument('--n', type=int, default=100)
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--threshold', type=float, default=0.9)
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--min-prob', type=float, default=0.01)
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    labels = json.load(open(os.path.join(args.tagger, 'labels.json')))
    leaf_itos, tree_itos = labels['leaf'], labels['tree']
    leaf_stoi = {l: i for i, l in enumerate(leaf_itos)}
    tree_stoi = {l: i for i, l in enumerate(tree_itos)}
    tok = AutoTokenizer.from_pretrained(labels['encoder'])
    model = Tagger(labels['encoder'], len(leaf_itos), len(tree_itos)).to(device)
    model.load_state_dict(torch.load(os.path.join(args.tagger, 'model.pt'), map_location=device), strict=False)
    model.eval()

    type_words = collections.defaultdict(collections.Counter)
    for s in read(os.path.join(args.data, 'train.jsonl')):
        for f, l in zip(s['forms'], s['leaf']):
            type_words[l.split('|')[0]][f.lower()] += 1
    type_words = {t: [w for w, _ in c.most_common(4)] for t, c in type_words.items()}
    docs = dict(line.split(': ', 1) for line in rule_docs(args.erg) if ': ' in line)
    system = SYSTEM.format(docs='\n'.join(rule_docs(args.erg)))

    pool = read(os.path.join(args.data, f'{args.split}.jsonl'))
    random.Random(args.seed).shuffle(pool)
    sample = sorted(pool[:args.n], key=lambda s: len(s['forms']))

    items = []
    with torch.no_grad():
        for s in sample:
            ids, mask, first, _, _, kept = collate([s], tok, leaf_stoi, tree_stoi, device)
            with torch.autocast('cuda', dtype=torch.float16, enabled=device.type == 'cuda'):
                leaf_logits, tree_logits = model(ids, mask, first)
            n = len(s['forms'])
            lp = leaf_logits.float().softmax(-1).topk(args.k, -1)
            tp = tree_logits.float().softmax(-1).topk(args.k, -1)
            base_leaf = [leaf_itos[i] for i in lp.indices[:, 0].tolist()] + [UNK] * (n - kept[0])
            base_tree = [tree_itos[i] for i in tp.indices[:, 0].tolist()] + [UNK] * (n - kept[0])
            decisions = []
            for j in range(kept[0]):
                for kind, top, itos, base in (('leaf', lp, leaf_itos, base_leaf), ('tree', tp, tree_itos, base_tree)):
                    if kind == 'tree' and (j == n - 1 or base_leaf[j].startswith(CONT)):
                        continue
                    probs = top.values[j].tolist()
                    if probs[0] >= args.threshold:
                        continue
                    options = []
                    for p, i in zip(probs, top.indices[j].tolist()):
                        if p < args.min_prob and options:
                            break
                        text = (describe_leaf(itos[i], type_words) if kind == 'leaf'
                                else describe_tree(itos[i], j, s['forms'], base_leaf, base_tree, docs))
                        if text:
                            options.append({'label': itos[i], 'prob': p, 'text': text})
                    if len(options) > 1 and options[0]['label'] == base[j]:
                        decisions.append({'kind': kind, 'token': j, 'options': options})
            items.append({'sent': s, 'base_leaf': base_leaf, 'base_tree': base_tree, 'decisions': decisions})

    def prompt_for(batch):
        parts = []
        for n, it in enumerate(batch, 1):
            s = it['sent']
            parts.append(f'### Sentence {n}')
            parts.append('Words: ' + ' '.join(f'{i + 1}:{w}' for i, w in enumerate(s['forms'])))
            try:
                parts.append("Tagger's analysis: " + render(decode(to_leaves(s['forms'], it['base_leaf'], it['base_tree']))))
            except Exception:
                pass
            for d_no, d in enumerate(it['decisions'], 1):
                j = d['token']
                if d['kind'] == 'leaf':
                    parts.append(f"Decision {n}.{d_no} (lexical): word {j + 1} \"{s['forms'][j]}\"")
                else:
                    li = sum(1 for l in it['base_leaf'][:j] if not l.startswith(CONT))
                    unit = leaf_texts(s['forms'], it['base_leaf'])[li]
                    parts.append(f"Decision {n}.{d_no} (structural): what joins after \"{unit}\" (starting at word {j + 1})")
                for letter, o in zip(LETTERS, d['options']):
                    parts.append(f"  {letter} (tagger {o['prob']:.0%}): {o['text']}")
            parts.append('')
        parts.append('Give one line per decision.')
        return '\n'.join(parts)

    todo = [it for it in items if it['decisions']]
    n_dec = sum(len(it['decisions']) for it in items)
    print(f'{len(items)} sentences, {len(todo)} with decisions, {n_dec} decisions', flush=True)
    if args.dry_run:
        with open(os.path.join(args.out, 'first-prompt.txt'), 'w') as f:
            f.write(prompt_for(todo[len(todo) // 2:len(todo) // 2 + args.batch]))
        return

    usage = collections.Counter()
    with open(os.path.join(args.out, 'raw.jsonl'), 'w', encoding='utf-8') as raw:
        for b in range(0, len(todo), args.batch):
            batch = todo[b:b + args.batch]
            data = call(args.model, system, prompt_for(batch), args.out)
            raw.write(json.dumps({'ids': [it['sent']['id'] for it in batch], 'response': data}) + '\n')
            raw.flush()
            u = data.get('usage', {})
            for key in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                usage[key] += u.get(key, 0)
            usage['seconds'] += data['seconds']
            usage['cost_usd_equivalent'] += data.get('total_cost_usd') or 0
            for m in re.finditer(r'(\d+)\.(\d+)\s*[:\-]\s*([A-H])\b', data.get('result') or ''):
                n, d_no, letter = int(m.group(1)), int(m.group(2)), LETTERS.index(m.group(3))
                if 1 <= n <= len(batch) and 1 <= d_no <= len(batch[n - 1]['decisions']):
                    d = batch[n - 1]['decisions'][d_no - 1]
                    if letter < len(d['options']):
                        d['choice'] = letter
            print(f'batch {b // args.batch + 1}/{-(-len(todo) // args.batch)} {data["seconds"]:.0f}s', flush=True)

    # apply the choices and score
    stats = collections.Counter()
    files = {name: open(os.path.join(args.out, f'{args.split}-pred-{name}.jsonl'), 'w', encoding='utf-8')
             for name in ('tagger', 'judge', 'oracle')}
    for it in items:
        s = it['sent']
        variants = {name: (list(it['base_leaf']), list(it['base_tree'])) for name in files}
        for d in it['decisions']:
            gold = s[d['kind']][d['token']]
            labels_ = [o['label'] for o in d['options']]
            chosen = d.get('choice', 0)
            stats['decisions'] += 1
            stats['unanswered'] += 'choice' not in d
            stats['gold among options'] += gold in labels_
            stats['tagger right'] += labels_[0] == gold
            stats['judge right'] += labels_[chosen] == gold
            stats['judge kept A'] += chosen == 0
            stats['fixed'] += labels_[0] != gold and labels_[chosen] == gold
            stats['broken'] += labels_[0] == gold and labels_[chosen] != gold
            stats[f"{d['kind']} decisions"] += 1
            stats[f"{d['kind']} tagger right"] += labels_[0] == gold
            stats[f"{d['kind']} judge right"] += labels_[chosen] == gold
            idx = 0 if d['kind'] == 'leaf' else 1
            variants['judge'][idx][d['token']] = labels_[chosen]
            if gold in labels_:
                variants['oracle'][idx][d['token']] = gold
        for name, (leaf, tree) in variants.items():
            files[name].write(json.dumps({'id': s['id'], 'forms': s['forms'], 'leaf': leaf, 'tree': tree},
                                         ensure_ascii=False) + '\n')
            n = len(s['forms'])
            stats[f'{name} tokens'] += n
            stats[f'{name} leaf right'] += sum(a == b for a, b in zip(leaf, s['leaf']))
            stats[f'{name} tree right'] += sum(a == b for a, b in zip(tree, s['tree']))
            stats[f'{name} sentences right'] += leaf == s['leaf'] and tree[:-1] == s['tree'][:-1]
    for f in files.values():
        f.close()
    summary = {'args': vars(args), 'sentences': len(items), 'sentences_with_decisions': len(todo),
               'stats': dict(stats), 'usage': dict(usage)}
    with open(os.path.join(args.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({'stats': dict(stats), 'usage': dict(usage)}, indent=1))


if __name__ == '__main__':
    main()
