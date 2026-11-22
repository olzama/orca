#!/usr/bin/env python3
"""Encode treebank derivations as one label per token and test the round trip.

For every derivation in train/, dev/ and test/: build the tree, encode it,
decode it, and compare with the original. Writes the encoded sentences as
JSON lines (one file per split) and a summary of round-trip results and
label inventories.

Usage:
    encode_treebank.py --profiles ROOT --erg ERG_DIR --data DATA_DIR --out OUT_DIR
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from delphin import derivation, tsdb  # noqa: E402

from orca.encoding import (Leaf, Node, decode, encode,  # noqa: E402
                           relative_depths)

LEXRULE = re.compile(r'lr$')
FORM = re.compile(r'\+FORM \\?"(.*?)\\?" \+FROM')
CONT = '<cont>'   # label of the second and later tokens of a multi-token leaf
LEXICON_FILES = ('lexicon.tdl', 'gle.tdl', 'gle-gen.tdl', 'ple.tdl', 'lexicon-rbst.tdl')


def entry_types(erg_dir):
    mapping = {}
    pat = re.compile(r'^([^\s;:]+)\s*:=\s*([^\s&.]+)', re.M)
    for name in LEXICON_FILES:
        path = os.path.join(erg_dir, name)
        if os.path.exists(path):
            with open(path, encoding='utf-8', errors='replace') as f:
                for m in pat.finditer(f.read()):
                    mapping.setdefault(m.group(1), m.group(2))
    return mapping


def to_tree(node):
    kids = node.daughters
    if kids and all(isinstance(d, derivation.UDFTerminal) for d in kids):
        term = kids[0]
        forms = []
        for tok in term.tokens or []:
            m = FORM.search(tok.tfs or '')
            if m:
                forms.append(m.group(1))
        if not forms:
            forms = term.form.split() or [term.form]
        return Leaf(node.entity, tuple(forms))
    return Node(node.entity, tuple(to_tree(d) for d in kids))


def lexrule_names(top_file):
    """Names of the grammar's lexical rules (status lex-rule), for grammars whose
    rule names don't follow the ERG's convention of ending in 'lr' (HaG's _ir rules)."""
    import sys
    from delphin import tdl
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from orca.tfs.hierarchy import load_plan
    names = set()
    for path, section, status in load_plan(top_file):
        if section == 'instance' and status == 'lex-rule':
            for event, obj, _ in tdl.iterparse(path, encoding='utf-8'):
                if event in ('TypeDefinition', 'LexicalRuleDefinition'):
                    names.add(obj.identifier.lower())
    return names


def token_rows(leaves, e2t, lexrules=None):
    """One row per token: form plus the factored label. Lexical rules are told
    apart by name (ERG) or, given the grammar's set of lexical rules, by status."""
    is_lex = (lambda n: n.lower() in lexrules) if lexrules else (lambda n: bool(LEXRULE.search(n)))
    rows = []
    for leaf, delta in zip(leaves, relative_depths(leaves)):
        lex = [n for n in leaf.chain if is_lex(n)]
        phr = [n for n in leaf.chain if not is_lex(n)]
        rows.append({
            'form': leaf.forms[0],
            'entry': leaf.entry,
            'lextype': e2t.get(leaf.entry, 'entry:' + leaf.entry),
            'lexrules': ' '.join(lex),
            'unaries': ' '.join(phr),
            'delta': delta,
            'depth': leaf.depth,
            'node': ' '.join(leaf.node) if leaf.node else None,
        })
        for form in leaf.forms[1:]:
            rows.append({'form': form, 'entry': CONT, 'lextype': CONT, 'lexrules': '',
                         'unaries': '', 'delta': None, 'depth': None, 'node': None})
    return rows


VIEWS = {
    'lextype': lambda r: r['lextype'],
    'leaf: lextype+lexrules+unaries': lambda r: (r['lextype'], r['lexrules'], r['unaries']),
    'node (unaries+binary rule)': lambda r: r['node'],
    'delta': lambda r: r['delta'],
    'tree: delta+node': lambda r: (r['delta'], r['node']),
    'tree, absolute depth: depth+node': lambda r: (r['depth'], r['node']),
    'full label': lambda r: (r['lextype'], r['lexrules'], r['unaries'], r['delta'], r['node']),
}


def run_split(split_dir, e2t, out_path, lexrules=None):
    st = {
        'derivations': 0, 'unreadable': 0, 'not_binary': 0, 'round_trip_ok': 0,
        'round_trip_fail': 0, 'tokens': 0, 'leaves': 0, 'interleaved_chains': 0,
        'max_depth': 0, 'failures': [],
    }
    counts = {k: collections.Counter() for k in VIEWS}
    entries_by_form_type = collections.defaultdict(collections.Counter)
    with open(out_path, 'w', encoding='utf-8') as out:
        for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
            if not os.path.exists(os.path.join(prof, 'relations')):
                continue
            try:
                names = [f.name for f in tsdb.read_schema(prof)['result']]
                i_der, i_pid = names.index('derivation'), names.index('parse-id')
                rows = tsdb.open(prof, 'result')
            except Exception as exc:
                print(f'  skip {prof}: {exc}', file=sys.stderr)
                continue
            with rows:
                for line in rows:
                    rec = tsdb.split(line)
                    if not rec[i_der]:
                        continue
                    sid = f'{os.path.basename(prof)}/{rec[i_pid]}'
                    try:
                        tree = to_tree(derivation.from_string(rec[i_der]))
                    except Exception:
                        st['unreadable'] += 1
                        continue
                    st['derivations'] += 1
                    try:
                        leaves = encode(tree)
                    except ValueError:
                        st['not_binary'] += 1
                        continue
                    if decode(leaves) == tree:
                        st['round_trip_ok'] += 1
                    else:
                        st['round_trip_fail'] += 1
                        if len(st['failures']) < 20:
                            st['failures'].append(sid)
                    for leaf in leaves:
                        kinds = [bool(LEXRULE.search(n)) for n in leaf.chain]
                        if any(a and not b for a, b in zip(kinds, kinds[1:])):
                            st['interleaved_chains'] += 1
                        key = (' '.join(leaf.forms).lower(), e2t.get(leaf.entry, leaf.entry),
                               tuple(n for n in leaf.chain if LEXRULE.search(n)))
                        entries_by_form_type[key][leaf.entry] += 1
                    toks = token_rows(leaves, e2t, lexrules)
                    st['leaves'] += len(leaves)
                    st['tokens'] += len(toks)
                    st['max_depth'] = max([st['max_depth']] + [l.depth or 0 for l in leaves])
                    for r in toks:
                        if r['entry'] != CONT:
                            for k, view in VIEWS.items():
                                counts[k][view(r)] += 1
                    out.write(json.dumps({'id': sid, 'tokens': toks}, ensure_ascii=False) + '\n')
    amb = {k: v for k, v in entries_by_form_type.items() if len(v) > 1}
    st['form+lextype+lexrules keys'] = len(entries_by_form_type)
    st['keys with several entries'] = len(amb)
    st['leaves under such keys'] = sum(sum(v.values()) for v in amb.values())
    return st, counts


def unseen(train, other):
    total = sum(other.values())
    new = [k for k in other if k not in train]
    return {'types': len(other), 'unseen_types': len(new),
            'unseen_leaf_share': sum(other[k] for k in new) / total if total else 0.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--erg', required=True)
    ap.add_argument('--data', required=True, help='directory for encoded JSON lines')
    ap.add_argument('--out', required=True, help='directory for the summary')
    args = ap.parse_args()
    os.makedirs(args.data, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    e2t = entry_types(args.erg)

    summary, counts = {}, {}
    for split in ('train', 'dev', 'test'):
        st, counts[split] = run_split(os.path.join(args.profiles, split), e2t,
                                      os.path.join(args.data, f'{split}.jsonl'))
        st['inventory'] = {k: len(c) for k, c in counts[split].items()}
        if split != 'train':
            st['unseen_vs_train'] = {k: unseen(counts['train'][k], c)
                                     for k, c in counts[split].items()}
        summary[split] = st
    with open(os.path.join(args.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    for k in ('delta', 'node (unaries+binary rule)', 'tree: delta+node'):
        name = re.sub(r'\W+', '_', k).strip('_')
        with open(os.path.join(args.out, f'train-{name}.tsv'), 'w') as f:
            for key, c in counts['train'][k].most_common():
                f.write(f'{c}\t{key}\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
