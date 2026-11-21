#!/usr/bin/env python3
"""Every measure for every system on one split, overall and by sentence length.

Per sentence: does the system give an MRS, is it the gold MRS (isomorphic,
variable properties not compared), how many of its predicates and links are
in gold, and is its derivation tree the gold tree (the root condition is not
compared, since ACE's output carries none). Counts are summed over the set,
so a sentence without an analysis lowers recall but not precision.

Systems:
  --ace FILE.jsonl               ACE output from run_ace.py (MRS and derivation)
  --labels NAME=FILE.jsonl       Orca labels (id, forms, leaf, tree), replayed with entries
  --llm NAME=BASE:LOG.jsonl      system BASE, with the derivations an LLM repair
                                 run got accepted for the sentences BASE leaves out

Usage:
    score_tables.py --grammar ERG/english.tdl --profiles SPLIT_DIR --gold DATA/dev.jsonl
                    --out FILE [--ace ...] [--labels ...] [--llm ...]
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from delphin import derivation, mrs as M, tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from compare_mrs import normalized, to_pydelphin  # noqa: E402
from encode_treebank import entry_types, to_tree  # noqa: E402
from eval_trees import to_leaves  # noqa: E402
from llm_label import parse, read, tree_to_labels  # noqa: E402
from orca.encoding import Leaf, Node, decode  # noqa: E402
from orca.tfs.fast import FastGrammar, extract  # noqa: E402
from orca.tfs.grammar import Grammar  # noqa: E402
from orca.tfs.lexicon import Lexicon, replay_with_entries  # noqa: E402
from replay_predictions import gold_tokens  # noqa: E402
from score_semantics import BANDS, graph  # noqa: E402

ROOT = re.compile(r'^root_')


def unrooted(t):
    """Drop root-condition nodes (root_strict, root_informal, ...)."""
    while isinstance(t, Node) and ROOT.match(t.label) and len(t.children) == 1:
        t = t.children[0]
    if isinstance(t, Leaf):
        return t
    return Node(t.label, tuple(unrooted(c) for c in t.children))


def tree_key(t):
    forms, leaf, tree = tree_to_labels(unrooted(t))
    return tuple(leaf), tuple(tree)


def lextyped(t, e2t):
    """ACE leaves carry lexical entries; the tagger's carry lexical types."""
    if isinstance(t, Leaf):
        return Leaf(e2t.get(t.entry, t.entry), t.forms)
    return Node(t.label, tuple(lextyped(c, e2t) for c in t.children))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--gold', required=True, help='encoded split (gold labels)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--ace')
    ap.add_argument('--labels', action='append', default=[])
    ap.add_argument('--llm', action='append', default=[])
    args = ap.parse_args()
    gdir = os.path.dirname(args.grammar)

    gold_mrs = {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold_mrs[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = normalized(
                        simplemrs.decode(rec[names.index('mrs')]))
    gold = {s['id']: s for s in read(args.gold)}
    gold_key = {sid: tree_key(decode(to_leaves(s['forms'], s['leaf'], s['tree']))) for sid, s in gold.items()}
    length = {sid: len(s['forms']) for sid, s in gold.items()}
    gold_graph = {sid: graph(m) for sid, m in gold_mrs.items()}

    g = Grammar(args.grammar)
    fg, lx = FastGrammar(g), Lexicon(g, gdir)
    toks = gold_tokens(args.profiles)

    def replay(sid, tree):
        fg.reset()
        try:
            fs, _ = replay_with_entries(fg, lx, tree, toks[sid])
            return to_pydelphin(extract(fg, fs))
        except Exception:
            return None

    def judge(sid, m, key):
        """Per-sentence record for an analysis (m None = no analysis)."""
        r = {'mrs': m is not None, 'same_mrs': False, 'same_tree': False}
        if m is None:
            return r
        try:
            r['same_mrs'] = bool(M.is_isomorphic(m, gold_mrs[sid], properties=False))
            sp, sl = graph(m)
        except Exception:
            r['mrs'] = False
            return r
        gp, gl = gold_graph[sid]
        r.update({'sys preds': sum(sp.values()), 'ok preds': sum((sp & gp).values()),
                  'sys links': sum(sl.values()), 'ok links': sum((sl & gl).values())})
        r['same_tree'] = key == gold_key[sid]
        return r

    systems = {}
    if args.ace:
        e2t = entry_types(gdir)
        recs = {}
        for line in open(args.ace, encoding='utf-8'):
            a = json.loads(line)
            m = key = None
            if a.get('mrs'):
                try:
                    m = normalized(simplemrs.decode(a['mrs']))
                except Exception:
                    m = None
            if a.get('derivation'):
                try:
                    key = tree_key(lextyped(to_tree(derivation.from_string(a['derivation'])), e2t))
                except Exception:
                    key = None
            recs[a['id']] = judge(a['id'], m, key)
        systems['ace'] = recs
    for spec in args.labels:
        name, path = spec.split('=', 1)
        recs = {}
        for line in open(path, encoding='utf-8'):
            p = json.loads(line)
            try:
                t = decode(to_leaves(p['forms'], p['leaf'], p['tree']))
            except Exception:
                continue
            recs[p['id']] = judge(p['id'], replay(p['id'], t), tree_key(t))
        systems[name] = recs
        print(f'{name}: {len(recs)} sentences scored', file=sys.stderr)
    for spec in args.llm:
        name, rest = spec.split('=', 1)
        base, path = rest.split(':', 1)
        recs = {k: v for k, v in systems[base].items() if v['mrs']}
        for line in open(path, encoding='utf-8'):
            r = json.loads(line)
            if r['final'][0] != 'accepted' or recs.get(r['id'], {}).get('mrs'):
                continue
            t = parse(r['derivation'])
            recs[r['id']] = judge(r['id'], replay(r['id'], t), tree_key(t))
        systems[name] = recs

    gold_tot = collections.Counter()
    for sid in gold:
        band = next(n for lo, hi, n in BANDS if lo <= length[sid] < hi)
        gp, gl = gold_graph[sid]
        for b in ('all', band):
            gold_tot[(b, 'preds')] += sum(gp.values())
            gold_tot[(b, 'links')] += sum(gl.values())
            gold_tot[(b, 'sentences')] += 1

    out = {}
    for name, recs in systems.items():
        by = collections.defaultdict(collections.Counter)
        for sid in gold:
            band = next(n for lo, hi, n in BANDS if lo <= length[sid] < hi)
            r = recs.get(sid, {'mrs': False})
            for b in ('all', band):
                c = by[b]
                c['with MRS'] += r['mrs']
                c['same MRS'] += r.get('same_mrs', False)
                c['same tree'] += r.get('same_tree', False)
                for k in ('sys preds', 'ok preds', 'sys links', 'ok links'):
                    c[k] += r.get(k, 0)
        res = {}
        for b, c in by.items():
            n = gold_tot[(b, 'sentences')]
            d = {'sentences': n, 'with MRS': c['with MRS'], 'same MRS': c['same MRS'], 'same tree': c['same tree']}
            for kind in ('preds', 'links'):
                p = c[f'ok {kind}'] / c[f'sys {kind}'] if c[f'sys {kind}'] else 0.0
                rc = c[f'ok {kind}'] / gold_tot[(b, kind)] if gold_tot[(b, kind)] else 0.0
                d[kind] = {'precision': p, 'recall': rc, 'f1': 2 * p * rc / (p + rc) if p + rc else 0.0}
            res[b] = d
        out[name] = res
    with open(args.out, 'w') as f:
        json.dump(out, f, indent=1)
    for name, res in out.items():
        a = res['all']
        print(f"{name:24} MRS {a['with MRS']:5} same {a['same MRS']:5} tree {a['same tree']:5} "
              f"P/R/F preds {a['preds']['precision']:.3f}/{a['preds']['recall']:.3f}/{a['preds']['f1']:.3f} "
              f"links {a['links']['precision']:.3f}/{a['links']['recall']:.3f}/{a['links']['f1']:.3f}")


if __name__ == '__main__':
    main()
