#!/usr/bin/env python3
"""Parse raw sentences with the full Orca pipeline, one sentence at a time.

Steps, each timed:
  1. tokens:  the grammar's own preprocessing (REPP, POS tags, token
              mapping), from ACE without parsing (orca.tokens)
  2. tag:     the tagger's k best labels per token
  3. repair:  best-first replay over the labels until up to --kbest
              derivations are accepted (scripts/repair.py)
  4. rank:    the ERG's MaxEnt model picks one of them (scripts/rerank.py)
  5. MRS:     the chosen derivation is replayed and its MRS read off

Usage:
    orca_parse.py [--tagger MODEL_DIR] "Sentence one." ["Sentence two." ...]
    orca_parse.py --eval SPLIT_DIR --gold DATA/dev.jsonl --out FILE.json   (raw-text run on a split)
"""
import argparse
import json
import math
import os
import sys
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.setrecursionlimit(20000)

DEFAULTS = {
    'grammar': os.path.join(ROOT, 'data/erg/2025/english.tdl'),
    'tagger': os.path.join(ROOT, 'data/models/tagger-2025bothall-bert'),
    'ace': '/home/olga/delphin/tools/ACE/ace-0.9.34/ace',
    'dat': os.path.join(ROOT, 'data/ace/erg-2025.dat'),
}


def dmrs_json(m):
    """The DMRS of an MRS in the form the walkthrough's drawing code takes:
    nodes [pred, carg], links [from, to, role, post], top (node index)."""
    from delphin import dmrs
    d = dmrs.from_mrs(m)
    idx = {n.id: i for i, n in enumerate(d.nodes)}
    return {'nodes': [[n.predicate, n.carg] for n in d.nodes],
            'links': [[idx[l.start], idx[l.end], l.role, l.post] for l in d.links if l.start in idx and l.end in idx],
            'top': idx.get(d.top)}


class Parser:
    def __init__(self, grammar=DEFAULTS['grammar'], tagger=DEFAULTS['tagger'], ace=DEFAULTS['ace'],
                 dat=DEFAULTS['dat'], k=5, kbest=30, budget=600, fanout=8, min_prob=0.005, device=None,
                 all_mrs=False, commit=False, commit_min=0, root_focus=False):
        import torch
        from transformers import AutoTokenizer
        import repair
        from orca.maxent import MaxEnt
        from orca.tfs.fast import FastGrammar
        from orca.tfs.grammar import Grammar
        from orca.tfs.lexicon import Lexicon
        from orca.tokens import known_words
        from train_tagger import Tagger
        self.torch, self.repair = torch, repair
        self.ace, self.dat, self.k = ace, dat, k
        self.all_mrs = all_mrs                          # also read off the MRS of every accepted derivation
        self.args = SimpleNamespace(cache=True, kbest=kbest, budget=budget, fanout=fanout, min_prob=min_prob,
                                    commit=commit, commit_min=commit_min, root_focus=root_focus)
        self.device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
        labels = json.load(open(os.path.join(tagger, 'labels.json')))
        self.itos = {'leaf': labels['leaf'], 'tree': labels['tree']}
        self.surface = labels.get('forms') == 'surface'   # trained on the text as typed (scripts/surface_forms.py)
        self.stoi = {k: {l: i for i, l in enumerate(v)} for k, v in self.itos.items()}
        self.tok = AutoTokenizer.from_pretrained(labels['encoder'])
        self.model = Tagger(labels['encoder'], len(self.itos['leaf']), len(self.itos['tree'])).to(self.device)
        self.model.load_state_dict(torch.load(os.path.join(tagger, 'model.pt'), map_location=self.device), strict=False)
        self.model.eval()
        gdir = os.path.dirname(grammar)
        g = Grammar(grammar)
        self.lx = Lexicon(g, gdir)
        self.known = known_words(self.lx)
        self.me = MaxEnt(os.path.join(gdir, 'redwoods.mem'))
        self.generic = lambda e: g.status.get(e) == 'generic-lex-entry'
        self.fg = FastGrammar(g)
        for name, status in g.status.items():           # rule templates, built once
            if status in ('rule', 'lex-rule'):
                self.fg.instance(name)
        self.tagger_name = os.path.basename(os.path.normpath(tagger))

    def tag(self, forms):
        from train_tagger import UNK, collate
        torch, n = self.torch, len(forms)
        s = {'forms': forms, 'leaf': [UNK] * n, 'tree': [UNK] * n}
        with torch.no_grad():
            ids, mask, first, _, _, kept = collate([s], self.tok, self.stoi['leaf'], self.stoi['tree'], self.device)
            with torch.autocast('cuda', dtype=torch.float16, enabled=self.device.type == 'cuda'):
                logits = dict(zip(('leaf', 'tree'), self.model(ids, mask, first)))
        top = {}
        for kind in ('leaf', 'tree'):
            p = logits[kind].float().softmax(-1).topk(self.k, -1)
            top[kind] = [[(self.itos[kind][i], math.log(max(q, 1e-12)), q) for q, i in zip(ps, idx)]
                         for ps, idx in zip(p.values.tolist(), p.indices.tolist())]
            top[kind] += [[(UNK, 0.0, 1.0)]] * (n - kept[0])
        return top

    def parse(self, text, sid='input'):
        from compare_mrs import to_pydelphin
        from delphin.codecs import simplemrs
        from eval_trees import to_leaves
        from orca.encoding import decode
        from orca.tfs.fast import extract
        from orca.tokens import lattice_path, token_chart
        from rerank import with_entries
        out, t = {'input': text, 'tagger': self.tagger_name, 'seconds': {}}, time.perf_counter()

        def lap(name):
            nonlocal t
            now = time.perf_counter()
            out['seconds'][name] = now - t
            t = now

        path = lattice_path(token_chart(text, self.ace, self.dat), self.known)
        lap('tokens')
        forms = [text[a:b] for _, _, (a, b) in path] if self.surface else [p[0] for p in path]
        out['tokens'] = [{'form': f, 'from': span[0], 'to': span[1], 'alternatives': len(alts)}
                         for f, (_, alts, span) in zip(forms, path)]
        if not forms:
            out['outcome'] = 'no tokens'
            return out
        top = self.tag(forms)
        lap('tag')
        out['first guess'] = {'leaf': [top['leaf'][j][0][0] for j in range(len(forms))],
                              'tree': [top['tree'][j][0][0] for j in range(len(forms))]}
        r = self.repair
        s = {'id': sid, 'forms': forms, 'leaf': [None] * len(forms), 'tree': [None] * len(forms)}
        r._WORK = (self.fg, [s], [top], {sid: [p[1] for p in path]}, self.args, self.lx)
        r.GOLD_MRS.clear()
        outcome, leaf, tree, n_replays, _, _, kbest = r.search(0)
        lap('repair')
        out['outcome'] = outcome.replace(', wrong', '').replace(', right', '')
        out['replays'] = n_replays
        out['accepted derivations'] = len(kbest)
        if not kbest:
            return out
        scored = []
        for c in kbest:
            tr = with_entries(decode(to_leaves(forms, c['leaf'], c['tree'])), c['entries'])
            scored.append((self.me.score(tr, self.lx.type_of.get, self.generic), tr, c))
        best = max(range(len(scored)), key=lambda i: scored[i][0])
        score, tr, c = scored[best]
        out['chosen'] = {'rank among accepted': best, 'maxent score': score, 'tagger cost': c['cost']}
        lap('rank')
        self.fg.reset()
        fs, _ = self.fg.replay_tree(tr, [p[1] for p in path])
        m = to_pydelphin(extract(self.fg, fs))
        lap('mrs')
        out['mrs'] = simplemrs.encode(m, indent=True)
        out['eps'] = [{'pred': ep.predicate, 'label': ep.label,
                       'args': {k: v for k, v in ep.args.items()}, 'carg': ep.carg} for ep in m.rels]
        out['hcons'] = [[h.hi, h.relation, h.lo] for h in m.hcons]
        out['top'], out['index'] = m.top, m.index
        out['derivation'] = self.tree_json(tr)
        out['labels'] = {'forms': forms, 'leaf': list(c['leaf']), 'tree': list(c['tree']), 'entries': list(c['entries'])}
        try:
            out['dmrs'] = dmrs_json(m)
        except Exception:
            out['dmrs'] = None
        out['_mrs_obj'] = m
        out['_fs'] = fs                    # the whole sign; valid until the next parse resets the grammar's memory
        if self.all_mrs:
            out['_all_mrs'] = []
            for _, t2, _ in scored:
                try:
                    self.fg.reset()
                    f2, _ = self.fg.replay_tree(t2, [p[1] for p in path])
                    out['_all_mrs'].append(to_pydelphin(extract(self.fg, f2)))
                except Exception:
                    out['_all_mrs'].append(None)
        return out

    def tree_json(self, t):
        from orca.encoding import Leaf
        if isinstance(t, Leaf):
            entry = t.entry[6:] if t.entry.startswith('entry:') else t.entry
            return {'entry': entry, 'type': self.lx.type_of.get(entry, ''), 'forms': list(t.forms)}
        return {'label': t.label, 'children': [self.tree_json(c) for c in t.children]}


def ace_parse(text, ace=DEFAULTS['ace'], dat=DEFAULTS['dat'], timeout=30):
    """ACE's first-ranked analysis, for comparison."""
    from delphin import ace as A
    from delphin.codecs import simplemrs
    t = time.perf_counter()
    try:
        resp = A.parse(dat, text, executable=ace, cmdargs=['-1', f'--timeout={timeout}'], stderr=open(os.devnull, 'w'))
        res = resp.results()
        secs = time.perf_counter() - t
        if not res:
            return {'seconds': secs, 'mrs': None}
        m = simplemrs.decode(res[0]['mrs'])
        try:
            d = dmrs_json(m)
        except Exception:
            d = None
        return {'seconds': secs, 'mrs': simplemrs.encode(m, indent=True), 'dmrs': d, '_mrs_obj': m}
    except Exception as e:
        return {'seconds': time.perf_counter() - t, 'mrs': None, 'error': str(e)[:200]}


def evaluate(parser, split_dir, gold_path, out_path, limit=None, save_mrs=False, min_tokens=0):
    """Raw-text run over a split, scored by exact MRS against the treebank."""
    import collections
    import glob
    from delphin import mrs as M, tsdb
    from delphin.codecs import simplemrs
    from check_raw_tokens import raw_inputs
    from compare_mrs import normalized
    from llm_label import read
    raw = raw_inputs(split_dir)
    gold = {}
    for prof in sorted(glob.glob(os.path.join(split_dir, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
    sents = [s for s in read(gold_path) if len(s['forms']) >= min_tokens][:limit]
    parser.parse('The dog barked.')                     # warm up GPU and caches
    c, secs = collections.Counter(), collections.Counter()
    recs = []
    t0 = time.perf_counter()
    for s in sents:
        r = parser.parse(raw[s['id']], s['id'])
        m = r.pop('_mrs_obj', None)
        r.pop('_fs', None)
        g = normalized(simplemrs.decode(gold[s['id']]))

        def is_gold(x):
            try:
                return bool(M.is_isomorphic(normalized(x), g, properties=False))
            except Exception:
                return False
        same = m is not None and is_gold(m)
        if parser.all_mrs and m is not None:
            among = any(x is not None and is_gold(x) for x in r.pop('_all_mrs', []))
            c['gold MRS among accepted'] += among
        c['sentences'] += 1
        c['with MRS'] += m is not None
        c['same MRS'] += same
        c['same forms as treebank'] += [t['form'] for t in r['tokens']] == [f.replace('\\/', '/') for f in s['forms']]
        for k, v in r['seconds'].items():
            secs[k] += v
        recs.append({'id': s['id'], 'outcome': r.get('outcome'), 'same MRS': same, 'replays': r.get('replays'),
                     'accepted': r.get('accepted derivations', 0),
                     'gold among accepted': among if parser.all_mrs and m is not None else None,
                     **({'mrs': r.get('mrs'), 'labels': r.get('labels')} if save_mrs else {})})
    wall = time.perf_counter() - t0
    res = {'tagger': parser.tagger_name, 'k': parser.k, 'kbest': parser.args.kbest, 'budget': parser.args.budget,
           'commit': parser.args.commit, 'commit_min': parser.args.commit_min, 'root_focus': parser.args.root_focus, 'min_tokens': min_tokens, 'counts': dict(c), 'seconds by step': dict(secs), 'wall seconds': wall,
           'sentences per second': c['sentences'] / wall, 'records': recs}
    with open(out_path, 'w') as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'records'}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sentences', nargs='*')
    ap.add_argument('--tagger', default=DEFAULTS['tagger'])
    ap.add_argument('--eval')
    ap.add_argument('--gold')
    ap.add_argument('--out')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--all-mrs', action='store_true', help='with --eval: also check whether the gold MRS is among the accepted derivations')
    ap.add_argument('--save-mrs', action='store_true', help='with --eval: keep each sentence\'s chosen MRS in the output')
    ap.add_argument('--k', type=int, default=5, help='tagger labels per word')
    ap.add_argument('--kbest', type=int, default=30, help='stop after this many accepted derivations')
    ap.add_argument('--budget', type=int, default=600, help='at most this many replays per sentence')
    ap.add_argument('--commit', action='store_true', help='repair: keep a fix once the failure moves to another part of the tree (scripts/repair.py)')
    ap.add_argument('--root-focus', action='store_true', help='repair: on a failure at the root, search the top of the tree and the head path first (scripts/repair.py)')
    ap.add_argument('--commit-min', type=int, default=0, help='with --commit: only for sentences of at least this many tokens')
    ap.add_argument('--min-tokens', type=int, default=0, help='with --eval: only sentences of at least this many tokens')
    args = ap.parse_args()
    p = Parser(tagger=args.tagger, all_mrs=args.all_mrs, k=args.k, kbest=args.kbest, budget=args.budget,
               commit=args.commit, commit_min=args.commit_min, root_focus=args.root_focus)
    if args.eval:
        evaluate(p, args.eval, args.gold, args.out, args.limit, args.save_mrs, args.min_tokens)
        return
    for text in args.sentences:
        r = p.parse(text)
        r.pop('_mrs_obj', None)
        r.pop('_fs', None)
        print(json.dumps(r, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
