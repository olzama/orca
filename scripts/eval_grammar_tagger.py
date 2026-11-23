#!/usr/bin/env python3
"""Evaluate a tagger for any DELPH-IN grammar on a treebank split, from the
treebank's own (gold) tokens: replay the tagger's first guess, repair with its
k-best labels (scripts/repair.py), and compare the chosen derivation's MRS with
the treebank's. Without a ranking model for the grammar, the accepted
derivation with the lowest tagger cost is chosen (the first one repair finds).

Usage:
    eval_grammar_tagger.py --grammar TOP.tdl --tagger MODEL_DIR --profiles DIR
                           --encoded SPLIT.jsonl --out OUT.json [--threads 2]
"""
import argparse
import collections
import glob
import json
import math
import os
import re
import sys
import time
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--tagger', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--encoded', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--kbest', type=int, default=30)
    ap.add_argument('--budget', type=int, default=600)
    ap.add_argument('--threads', type=int, default=2)
    a = ap.parse_args()

    import torch
    from transformers import AutoTokenizer
    from delphin import mrs as M, tsdb
    from delphin.codecs import simplemrs
    import repair
    from check_treebank_mrs import glb_anon
    from compare_mrs import normalized, to_pydelphin
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.fast import FastGrammar, extract
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon, replay_with_entries
    from replay_predictions import gold_tokens
    from train_tagger import UNK, Tagger, collate

    torch.set_num_threads(a.threads)
    labels = json.load(open(os.path.join(a.tagger, 'labels.json')))
    itos = {'leaf': labels['leaf'], 'tree': labels['tree']}
    stoi = {k: {l: i for i, l in enumerate(v)} for k, v in itos.items()}
    tok = AutoTokenizer.from_pretrained(labels['encoder'])
    model = Tagger(labels['encoder'], len(itos['leaf']), len(itos['tree']))
    model.load_state_dict(torch.load(os.path.join(a.tagger, 'model.pt'), map_location='cpu'), strict=False)
    model.eval()
    dev = torch.device('cpu')

    def tag(forms):
        n = len(forms)
        s = {'forms': forms, 'leaf': [UNK] * n, 'tree': [UNK] * n}
        with torch.no_grad():
            ids, mask, first, _, _, kept = collate([s], tok, stoi['leaf'], stoi['tree'], dev)
            logits = dict(zip(('leaf', 'tree'), model(ids, mask, first)))
        top = {}
        for kind in ('leaf', 'tree'):
            p = logits[kind].float().softmax(-1).topk(a.k, -1)
            top[kind] = [[(itos[kind][i], math.log(max(q, 1e-12)), q) for q, i in zip(ps, idx)]
                         for ps, idx in zip(p.values.tolist(), p.indices.tolist())]
            top[kind] += [[(UNK, 0.0, 1.0)]] * (n - kept[0])
        return top

    gold = {}
    for prof in sorted(glob.glob(os.path.join(a.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = rec[names.index('mrs')]
    toks = gold_tokens(a.profiles)

    g = Grammar(a.grammar)
    lx = Lexicon(g, os.path.dirname(a.grammar))
    lx.locate_missing = True
    fg = FastGrammar(g)
    for name, status in g.status.items():
        if status in ('rule', 'lex-rule'):
            fg.instance(name)
    args = SimpleNamespace(cache=True, kbest=a.kbest, budget=a.budget, fanout=8, min_prob=0.005,
                           commit=False, commit_min=0, root_focus=False)

    def mrs_of(forms, leaf, tree, t_toks):
        fg.reset()
        fs, _ = replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), t_toks)
        return glb_anon(to_pydelphin(extract(fg, fs)))

    c, causes, recs = collections.Counter(), collections.Counter(), []
    t0 = time.time()
    for line in open(a.encoded):
        r = json.loads(line)
        forms, gleaf, gtree = labels_of(r['tokens'])
        n = len(forms)
        c['sentences'] += 1
        try:
            ref = glb_anon(simplemrs.decode(re.sub(r'CARG: ([^\s"\]]+)', r'CARG: "\1"', gold[r['id']])))
        except Exception:
            c['treebank MRS unreadable'] += 1
            continue
        c['comparable'] += 1
        top = tag(forms)
        s = {'id': r['id'], 'forms': forms, 'leaf': gleaf, 'tree': gtree}
        repair._WORK = (fg, [s], [top], {r['id']: toks[r['id']]}, args, lx)
        repair.GOLD_MRS.clear()
        outcome, leaf, tree, n_replays, first_right, ok, kbest = repair.search(0)
        rec = {'id': r['id'], 'n': n, 'outcome': outcome, 'replays': n_replays, 'accepted': len(kbest)}
        # where the tagger's k-best cannot reach gold: gold label outside the top k, or never seen in training
        for kind, gl in (('leaf', gleaf), ('tree', gtree)):
            for j in range(n if kind == 'leaf' else n - 1):
                cands = [x[0] for x in top[kind][j]]
                if gl[j] not in cands:
                    rec[f'{kind} gold outside top {a.k}'] = rec.get(f'{kind} gold outside top {a.k}', 0) + 1
                    if gl[j] not in stoi[kind]:
                        rec[f'{kind} gold label unseen in training'] = rec.get(f'{kind} gold label unseen in training', 0) + 1
        if outcome.startswith('accepted at first try'):
            c['first guess accepted'] += 1
        if kbest:
            c['any analysis'] += 1
            best = min(kbest, key=lambda x: x['cost'])
            try:
                ours = mrs_of(forms, best['leaf'], best['tree'], toks[r['id']])
                same = M.is_isomorphic(normalized(ours), normalized(ref), properties=False)
                withp = M.is_isomorphic(normalized(ours), normalized(ref), properties=True)
            except Exception:
                same = withp = False
                c['chosen derivation re-replay failed'] += 1
            c['same MRS'] += bool(same)
            c['same MRS with properties'] += bool(withp)
            rec['same'] = bool(same)
            among = False
            for k in kbest:
                try:
                    if M.is_isomorphic(normalized(mrs_of(forms, k['leaf'], k['tree'], toks[r['id']])), normalized(ref), properties=False):
                        among = True
                        break
                except Exception:
                    pass
            c['gold MRS among accepted'] += among
            rec['gold among accepted'] = among
        else:
            outside = rec.get(f'leaf gold outside top {a.k}', 0) + rec.get(f'tree gold outside top {a.k}', 0)
            unseen = rec.get('leaf gold label unseen in training', 0) + rec.get('tree gold label unseen in training', 0)
            causes['gold label never seen in training' if unseen else
                   f'gold label seen but outside top {a.k}' if outside else
                   'gold reachable, budget or search' if outcome.endswith('budget used') else 'gold reachable, not found'] += 1
        recs.append(rec)
    by_len = collections.defaultdict(collections.Counter)
    for x in recs:
        band = 'under 5' if x['n'] < 5 else '5-9' if x['n'] < 10 else '10-19' if x['n'] < 20 else '20 and over'
        by_len[band]['n'] += 1
        by_len[band]['first'] += x['outcome'].startswith('accepted at first try')
        by_len[band]['any'] += x['accepted'] > 0
        by_len[band]['same'] += bool(x.get('same'))
    out = {'tagger': os.path.basename(os.path.normpath(a.tagger)), 'grammar': a.grammar, 'split': a.encoded,
           'k': a.k, 'kbest': a.kbest, 'budget': a.budget, 'seconds': round(time.time() - t0, 1),
           'counts': dict(c), 'no analysis, by cause': dict(causes), 'by length': {k: dict(v) for k, v in by_len.items()},
           'records': recs}
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'records'}, indent=1))


if __name__ == '__main__':
    main()
