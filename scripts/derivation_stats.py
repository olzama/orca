#!/usr/bin/env python3
"""Statistics over ERG derivations in [incr tsdb()] profiles.

Answers, with data, the questions that decide the tree encoding for a tagger:
are all nodes unary or binary, how long are unary chains, how many leaves span
several tokens, how large are the label inventories, and how many of the
composite per-leaf labels in held-out data were never seen in training.

Usage:
    derivation_stats.py --profiles ROOT --erg ERG_DIR --out OUT_DIR
ROOT contains train/, dev/, test/, each holding profile directories.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

from delphin import derivation, tsdb

LEXRULE = re.compile(r'(lr|_odlr|_ilr|_olr|_dlr|_plr)$')


def entry_types(erg_dir):
    """Map lexical entry names to lexical types, read from the lexicon files."""
    mapping = {}
    pat = re.compile(r'^([^\s;:]+)\s*:=\s*([^\s&.]+)', re.M)
    for name in ('lexicon.tdl', 'gle.tdl', 'gle-gen.tdl', 'ple.tdl', 'lexicon-rbst.tdl'):
        path = os.path.join(erg_dir, name)
        if os.path.exists(path):
            with open(path, encoding='utf-8', errors='replace') as f:
                for m in pat.finditer(f.read()):
                    mapping.setdefault(m.group(1), m.group(2))
    return mapping


def is_preterminal(node):
    return bool(node.daughters) and all(
        isinstance(d, derivation.UDFTerminal) for d in node.daughters)


def analyze(node, st, e2t, chain, depth):
    """Walk a derivation; `chain` holds the unary nodes directly above."""
    st['max_depth'] = max(st['max_depth'], depth)
    if is_preterminal(node):
        term = node.daughters[0]
        ntok = len(term.tokens) if term.tokens else 1
        st['tokens_per_leaf'][ntok] += 1
        st['form_words_per_leaf'][len(term.form.split())] += 1
        if ntok > 1:
            st['multi_token_forms'][term.form.lower()] += 1
        lextype = e2t.get(node.entity)
        if lextype is None:
            st['unmapped_entries'][node.entity] += 1
            lextype = 'UNMAPPED'
        lex = tuple(n for n in chain if LEXRULE.search(n))
        phr = tuple(n for n in chain if not LEXRULE.search(n))
        # chain is top-down; lexical rules should all sit below phrasal unaries
        if chain and any(LEXRULE.search(a) and not LEXRULE.search(b)
                         for a, b in zip(chain, chain[1:])):
            st['interleaved_chains'] += 1
        st['entry'][node.entity] += 1
        st['lextype'][lextype] += 1
        st['lexrule_chain'][lex] += 1
        st['phrasal_unary_chain_at_leaf'][phr] += 1
        st['lexrule_chain_len'][len(lex)] += 1
        st['unary_chain_len_at_leaf'][len(chain)] += 1
        st['leaf_label:lextype+lexrules'][(lextype, lex)] += 1
        st['leaf_label:lextype+lexrules+phrasal_unaries'][(lextype, lex, phr)] += 1
        return 1
    n = len(node.daughters)
    st['arity'][n] += 1
    if LEXRULE.search(node.entity):
        st['lexrule'][node.entity] += 1
    else:
        st['phrasal_rule'][node.entity] += 1
        st['phrasal_rule_arity'][(node.entity, n)] += 1
    leaves = 0
    for d in node.daughters:
        leaves += analyze(d, st, e2t, chain + [node.entity] if n == 1 else [], depth + 1)
    if n == 1 and not chain and not LEXRULE.search(node.entity):
        pass
    return leaves


def run_split(split_dir, e2t):
    st = collections.defaultdict(collections.Counter)
    st['max_depth'] = 0
    st['interleaved_chains'] = 0
    n_deriv = n_fail = 0
    lengths = collections.Counter()
    roots = collections.Counter()
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        try:
            schema = tsdb.read_schema(prof)
            idx = [f.name for f in schema['result']].index('derivation')
            rows = tsdb.open(prof, 'result')
        except Exception as exc:  # missing or unreadable result file
            print(f'  skip {prof}: {exc}', file=sys.stderr)
            continue
        with rows:
            for line in rows:
                s = tsdb.split(line)[idx]
                if not s:
                    continue
                try:
                    d = derivation.from_string(s)
                except Exception:
                    n_fail += 1
                    continue
                n_deriv += 1
                roots[d.entity] += 1
                top = d.daughters[0] if d.entity.startswith('root') and d.daughters else d
                lengths[min(analyze(top, st, e2t, [], 0) // 10 * 10, 60)] += 1
    st['n_derivations'] = n_deriv
    st['n_unparsed_derivation_strings'] = n_fail
    st['leaves_per_sentence_band'] = lengths
    st['root'] = roots
    return st


def oov(train, other, key):
    tr, ot = train[key], other[key]
    tok = sum(ot.values())
    unseen_types = [k for k in ot if k not in tr]
    unseen_tok = sum(ot[k] for k in unseen_types)
    return {'types_in_split': len(ot), 'unseen_types': len(unseen_types),
            'unseen_token_share': unseen_tok / tok if tok else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--erg', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    e2t = entry_types(args.erg)
    stats = {s: run_split(os.path.join(args.profiles, s), e2t) for s in ('train', 'dev', 'test')}

    summary = {}
    for s, st in stats.items():
        leaves = sum(st['tokens_per_leaf'].values())
        summary[s] = {
            'derivations': st['n_derivations'],
            'unparsed_derivation_strings': st['n_unparsed_derivation_strings'],
            'leaves': leaves,
            'arity': dict(sorted(st['arity'].items())),
            'max_depth': st['max_depth'],
            'tokens_per_leaf': dict(sorted(st['tokens_per_leaf'].items())),
            'form_words_per_leaf': dict(sorted(st['form_words_per_leaf'].items())),
            'unary_chain_len_at_leaf': dict(sorted(st['unary_chain_len_at_leaf'].items())),
            'lexrule_chain_len': dict(sorted(st['lexrule_chain_len'].items())),
            'interleaved_chains': st['interleaved_chains'],
            'unmapped_entry_tokens': sum(st['unmapped_entries'].values()),
            'unmapped_entry_types': len(st['unmapped_entries']),
            'leaves_per_sentence_band': dict(sorted(st['leaves_per_sentence_band'].items())),
            'inventory': {k: len(st[k]) for k in (
                'phrasal_rule', 'lexrule', 'entry', 'lextype', 'lexrule_chain',
                'phrasal_unary_chain_at_leaf', 'leaf_label:lextype+lexrules',
                'leaf_label:lextype+lexrules+phrasal_unaries', 'root')},
        }
        if s != 'train':
            summary[s]['unseen_vs_train'] = {k: oov(stats['train'], st, k) for k in (
                'phrasal_rule', 'lexrule', 'entry', 'lextype', 'lexrule_chain',
                'phrasal_unary_chain_at_leaf', 'leaf_label:lextype+lexrules',
                'leaf_label:lextype+lexrules+phrasal_unaries')}
    with open(os.path.join(args.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)

    tr = stats['train']
    for key in ('phrasal_rule', 'lexrule', 'lextype', 'lexrule_chain',
                'phrasal_unary_chain_at_leaf', 'multi_token_forms', 'unmapped_entries',
                'phrasal_rule_arity', 'root'):
        with open(os.path.join(args.out, f'train-{key}.tsv'), 'w') as f:
            for k, c in tr[key].most_common():
                f.write(f"{c}\t{' '.join(k) if isinstance(k, tuple) and all(isinstance(x, str) for x in k) else k}\n")
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
