#!/usr/bin/env python3
"""Experiment: an LLM labels sentences with derivations, from examples only.

For each sampled sentence the prompt holds the most similar training
sentences with their derivations, and for each word the analyses it had in
training. The system prompt holds the grammar's own documentation of its
rules. The model answers with one bracketed derivation per sentence, which
is converted to the tagger's label format so that the same scoring applies.

The model is called through the `claude` command line in print mode.

Usage:
    llm_label.py --data DATA_DIR --erg ERG_DIR --out OUT_DIR [--n 60] [--model M]
"""
import argparse
import collections
import json
import math
import os
import random
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

from eval_trees import to_leaves  # noqa: E402
from orca.encoding import Leaf, Node, decode, encode, relative_depths  # noqa: E402

LEXRULE = re.compile(r'lr$')
CONT, NONE, UNK = '<cont>', '<none>', '<unk>'
TOKEN = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+')
DOC = re.compile(r'^([^\s;:]+)\s*:=[^\n]*\n"""\n(.*?)"""', re.M | re.S)


def labels_of(tokens):
    return ([t['form'] for t in tokens],
            [f"{t['lextype']}|{t['lexrules']}|{t['unaries']}" for t in tokens],
            [NONE if t['node'] is None else f"{t['delta']}|{t['node']}" for t in tokens])


def read(path):
    out = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            forms, leaf, tree = labels_of(r['tokens'])
            out.append({'id': r['id'], 'forms': forms, 'leaf': leaf, 'tree': tree})
    return out


def render(t):
    if isinstance(t, Leaf):
        text = ' '.join(t.forms).replace('\\', '\\\\').replace('"', '\\"')
        return f'({t.entry} "{text}")'
    return f"({t.label} {' '.join(render(c) for c in t.children)})"


def parse(text):
    toks = TOKEN.findall(text)
    pos = 0

    def node():
        nonlocal pos
        if toks[pos] != '(':
            raise ValueError('expected (')
        label = toks[pos + 1]
        pos += 2
        if toks[pos].startswith('"'):
            form = toks[pos][1:-1].replace('\\"', '"').replace('\\\\', '\\')
            pos += 1
            out = Leaf(label, tuple(form.split()))
        else:
            kids = []
            while toks[pos] != ')':
                kids.append(node())
            out = Node(label, tuple(kids))
        if toks[pos] != ')':
            raise ValueError('expected )')
        pos += 1
        return out

    tree = node()
    if pos != len(toks):
        raise ValueError('trailing material')
    return tree


def tree_to_labels(tree):
    """Token-level label strings in the tagger's format."""
    leaves = encode(tree)
    forms, leaf, tr = [], [], []
    for l, delta in zip(leaves, relative_depths(leaves)):
        lex = ' '.join(n for n in l.chain if LEXRULE.search(n))
        phr = ' '.join(n for n in l.chain if not LEXRULE.search(n))
        forms.append(l.forms[0])
        leaf.append(f'{l.entry}|{lex}|{phr}')
        tr.append(NONE if l.node is None else f"{delta}|{' '.join(l.node)}")
        for f in l.forms[1:]:
            forms.append(f)
            leaf.append(f'{CONT}||')
            tr.append(NONE)
    return forms, leaf, tr


def gold_tree(s):
    return decode(to_leaves(s['forms'], s['leaf'], s['tree']))


def rule_docs(erg):
    lines = []
    for name in ('constructions.tdl', 'inflr.tdl', 'lexrinst.tdl'):
        path = os.path.join(erg, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8', errors='replace') as f:
            for m in DOC.finditer(f.read()):
                doc = ' '.join(m.group(2).split())
                lines.append(f'{m.group(1)}: {doc}')
    return lines


class Retriever:
    def __init__(self, train, max_len=40):
        self.train = train
        self.index = collections.defaultdict(set)
        for i, s in enumerate(train):
            if len(s['forms']) <= max_len:
                for w in {f.lower() for f in s['forms']}:
                    self.index[w].add(i)
        n = len(train)
        self.idf = {w: math.log(n / len(ids)) for w, ids in self.index.items()}

    def nearest(self, forms, k):
        words = {f.lower() for f in forms}
        score = collections.Counter()
        for w in words:
            ids = self.index.get(w, ())
            if len(ids) > 20000:      # words in nearly every sentence carry no signal
                continue
            for i in ids:
                score[i] += self.idf[w]
        ranked = sorted(score, key=lambda i: (-score[i] / math.sqrt(len(self.train[i]['forms']) + 5), i))
        out, seen = [], set()
        for i in ranked:
            key = ' '.join(self.train[i]['forms']).lower()
            if key not in seen:
                seen.add(key)
                out.append(self.train[i])
                if len(out) == k:
                    break
        return out


def word_analyses(train):
    table = collections.defaultdict(collections.Counter)
    for s in train:
        i = 0
        while i < len(s['forms']):
            j = i + 1
            while j < len(s['forms']) and s['leaf'][j].startswith(CONT):
                j += 1
            lextype, lex, _ = s['leaf'][i].split('|')
            table[' '.join(s['forms'][i:j]).lower()][(lextype, lex)] += 1
            i = j
    return table


SYSTEM = """You produce syntactic derivations in the style of the English Resource Grammar (ERG), \
an HPSG grammar. A derivation is a tree. Every internal node is the name of a grammar rule and has \
one or two daughters. Every leaf is a lexical type (a name ending in _le) with the word it covers in \
double quotes. Lexical rules (names ending in lr) are unary nodes directly above a leaf. The topmost \
node is a root condition (a name starting with root_).

Format: (rule daughter daughter), (rule daughter), (lexical_type "word"). A leaf may cover several \
words: (lexical_type "New York"). \
Keep the words exactly as given and in the same order.

Documentation of the grammar's rules, from the grammar itself (name: description, with an example):

{docs}

You will be given sentences to analyze. For each one you get similar sentences with their correct \
derivations, and the analyses that each word had in the treebank (lexical type, then the lexical \
rules applied to it, if any; take the order of several rules from the examples). Use only rule and type \
names that occur in the documentation or the examples.

Answer with exactly one line per sentence: the sentence number, a tab, and the derivation on a \
single line. No other text."""


def build_prompt(batch, retriever, analyses, k, max_cands):
    parts = []
    for n, s in enumerate(batch, 1):
        parts.append(f'### Sentence {n}\nWords: ' + ' | '.join(s['forms']))
        parts.append('Analyses of these words in the treebank (most frequent first):')
        seen = set()
        for f in s['forms']:
            if f.lower() in seen:
                continue
            seen.add(f.lower())
            cands = analyses.get(f.lower())
            if cands:
                txt = '; '.join(f"{lt}{' + ' + lr if lr else ''} ({c})" for (lt, lr), c in cands.most_common(max_cands))
            else:
                txt = 'not in the treebank'
            parts.append(f'  {f}: {txt}')
        parts.append('Similar sentences with their derivations:')
        for ex in retriever.nearest(s['forms'], k):
            parts.append('  ' + ' '.join(ex['forms']))
            parts.append('  ' + render(gold_tree(ex)))
        parts.append('')
    parts.append(f'Now give the derivations of sentences 1 to {len(batch)}, one line each.')
    return '\n'.join(parts)


def call(model, system, prompt, cwd):
    cmd = ['claude', '-p', '--model', model, '--system-prompt', system, '--tools', '',
           '--strict-mcp-config', '--disable-slash-commands', '--no-session-persistence',
           '--setting-sources', '', '--output-format', 'json']
    t0 = time.time()
    proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, cwd=cwd, timeout=1800)
    data = json.loads(proc.stdout)
    data['seconds'] = time.time() - t0
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--erg', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--split', default='dev')
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--examples', type=int, default=6)
    ap.add_argument('--candidates', type=int, default=6)
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--dry-run', action='store_true', help='write the first prompt and stop')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    train = read(os.path.join(args.data, 'train.jsonl'))
    pool = read(os.path.join(args.data, f'{args.split}.jsonl'))
    random.Random(args.seed).shuffle(pool)
    sample = sorted(pool[:args.n], key=lambda s: len(s['forms']))
    retriever, analyses = Retriever(train), word_analyses(train)
    system = SYSTEM.format(docs='\n'.join(rule_docs(args.erg)))
    with open(os.path.join(args.out, 'system-prompt.txt'), 'w') as f:
        f.write(system)

    usage = collections.Counter()
    status = collections.Counter()
    with open(os.path.join(args.out, f'{args.split}-pred.jsonl'), 'w', encoding='utf-8') as out, \
            open(os.path.join(args.out, 'raw.jsonl'), 'w', encoding='utf-8') as raw:
        for b in range(0, len(sample), args.batch):
            batch = sample[b:b + args.batch]
            prompt = build_prompt(batch, retriever, analyses, args.examples, args.candidates)
            if args.dry_run:
                with open(os.path.join(args.out, 'first-prompt.txt'), 'w') as f:
                    f.write(prompt)
                print(f'system prompt {len(system)} chars, first prompt {len(prompt)} chars')
                return
            data = call(args.model, system, prompt, args.out)
            raw.write(json.dumps({'ids': [s['id'] for s in batch], 'response': data}) + '\n')
            raw.flush()
            u = data.get('usage', {})
            for key in ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens'):
                usage[key] += u.get(key, 0)
            usage['seconds'] += data['seconds']
            usage['cost_usd_equivalent'] += data.get('total_cost_usd') or 0
            answers = {}
            for line in (data.get('result') or '').splitlines():
                m = re.match(r'\s*(\d+)\s+(\(.*\))\s*$', line)
                if m:
                    answers[int(m.group(1))] = m.group(2)
            for n, s in enumerate(batch, 1):
                forms = s['forms']
                leaf, tree, outcome = [UNK] * len(forms), [UNK] * len(forms), 'ok'
                try:
                    f2, l2, t2 = tree_to_labels(parse(answers[n]))
                    if f2 == forms:
                        leaf, tree = l2, t2
                    else:
                        outcome = 'words changed'
                except KeyError:
                    outcome = 'no answer'
                except Exception:
                    outcome = 'not a binary tree'
                status[outcome] += 1
                out.write(json.dumps({'id': s['id'], 'forms': forms, 'leaf': leaf, 'tree': tree,
                                      'status': outcome}, ensure_ascii=False) + '\n')
            out.flush()
            print(f'batch {b // args.batch + 1}: {dict(status)} {data["seconds"]:.0f}s', flush=True)

    with open(os.path.join(args.out, 'run.json'), 'w') as f:
        json.dump({'args': vars(args), 'status': dict(status), 'usage': dict(usage)}, f, indent=1)
    print(json.dumps({'status': dict(status), 'usage': dict(usage)}, indent=1))


if __name__ == '__main__':
    main()
