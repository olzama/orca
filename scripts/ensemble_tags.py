#!/usr/bin/env python3
"""Ensemble of taggers: average their label probabilities per word.

Steps:
  tag      tag the dev sentences of a cached tagger run (repair_bench.py cache: same
           tokens for every model) with one tagger, keeping its top-K labels per word
  combine  average the probabilities of several taggers' top-K lists (labels a model
           did not list count as 0), renormalize over the union, keep the top 5, and
           write a cache in repair_bench.py's format, so repair runs on it unchanged
  accuracy per-word and whole-sentence accuracy of each tagger and of combined caches

Usage:
  ensemble_tags.py tag --tagger MODEL_DIR --out data/bench/ens/NAME.pkl [--k 10]
  ensemble_tags.py combine --out CACHE.pkl NAME.pkl ...
  ensemble_tags.py accuracy FILE.pkl ...
"""
import argparse
import json
import math
import os
import pickle
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

BASE = 'data/bench/dev-debertav3large-tags.pkl'      # tokens and forms per dev sentence


def tag(a):
    import torch
    from transformers import AutoTokenizer
    from train_tagger import UNK, Tagger, collate
    torch.set_num_threads(4)
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    labels = json.load(open(os.path.join(a.tagger, 'labels.json')))
    assert labels.get('forms') == 'surface', 'expects a tagger trained on text as typed'
    itos = {'leaf': labels['leaf'], 'tree': labels['tree']}
    stoi = {k: {l: i for i, l in enumerate(v)} for k, v in itos.items()}
    tok = AutoTokenizer.from_pretrained(labels['encoder'])
    model = Tagger(labels['encoder'], len(itos['leaf']), len(itos['tree'])).to(dev)
    model.load_state_dict(torch.load(os.path.join(a.tagger, 'model.pt'), map_location=dev), strict=False)
    model.eval()
    items = pickle.load(open(a.base, 'rb'))['items']
    out = {}
    for sid, it in items.items():
        forms = it['forms']
        if not forms:
            out[sid] = None
            continue
        n = len(forms)
        s = {'forms': forms, 'leaf': [UNK] * n, 'tree': [UNK] * n}
        with torch.no_grad():
            ids, mask, first, _, _, kept = collate([s], tok, stoi['leaf'], stoi['tree'], dev)
            with torch.autocast('cuda', dtype=torch.float16, enabled=dev.type == 'cuda'):
                logits = dict(zip(('leaf', 'tree'), model(ids, mask, first)))
        top = {}
        for kind in ('leaf', 'tree'):
            p = logits[kind].float().softmax(-1).topk(a.k, -1)
            top[kind] = [[(itos[kind][i], q) for q, i in zip(ps, idx)] for ps, idx in zip(p.values.tolist(), p.indices.tolist())]
            top[kind] += [[(UNK, 1.0)]] * (n - kept[0])
        out[sid] = top
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    pickle.dump({'tagger': os.path.basename(os.path.normpath(a.tagger)), 'k': a.k, 'top': out}, open(a.out, 'wb'))
    print('tagged', len(out), 'sentences with', a.tagger)


def combine_tops(tops, keep=5):
    """tops: list of {'leaf': [[(label, p), ...] per word], 'tree': ...} for one sentence."""
    out = {}
    for kind in ('leaf', 'tree'):
        n = len(tops[0][kind])
        words = []
        for i in range(n):
            acc = {}
            for t in tops:
                for lab, p in t[kind][i]:
                    acc[lab] = acc.get(lab, 0.0) + p / len(tops)
            z = sum(acc.values()) or 1.0
            best = sorted(acc.items(), key=lambda kv: -kv[1])[:keep]
            words.append([(lab, math.log(max(p / z, 1e-12)), p / z) for lab, p in best])
        out[kind] = words
    return out


def combine(a):
    runs = [pickle.load(open(f, 'rb')) for f in a.files]
    base = pickle.load(open(a.base, 'rb'))
    items = {}
    for sid, it in base['items'].items():
        tops = [r['top'][sid] for r in runs]
        new = dict(it)
        new['top'] = None if any(t is None for t in tops) else combine_tops(tops)
        items[sid] = new
    names = [r['tagger'] for r in runs]
    pickle.dump({'tagger': base['tagger'], 'ensemble': names, 'items': items}, open(a.out, 'wb'))
    print('combined', names, '->', a.out)


def accuracy(a):
    from llm_label import labels_of
    gold = {}
    for l in open(a.gold):
        r = json.loads(l)
        _, lf, tr = labels_of(r['tokens'])
        gold[r['id']] = (lf, tr)
    print('file\twords\tleaf\ttree\tboth\tsentences all right')
    for f in a.files:
        d = pickle.load(open(f, 'rb'))
        tops = d['top'] if 'top' in d else {k: (v['top'] if v else None) for k, v in d['items'].items()}
        w = l1 = t1 = b1 = sents = sall = 0
        for sid, (lf, tr) in gold.items():
            t = tops.get(sid)
            if not t or len(t['leaf']) != len(lf):
                continue
            sents += 1
            ok_all = True
            for i in range(len(lf)):
                pl, pt = t['leaf'][i][0][0], t['tree'][i][0][0]
                w += 1
                l1 += pl == lf[i]
                t1 += pt == tr[i]
                b = pl == lf[i] and pt == tr[i]
                b1 += b
                ok_all &= b
            sall += ok_all
        print(f'{os.path.basename(f)}\t{w}\t{100 * l1 / w:.2f}\t{100 * t1 / w:.2f}\t{100 * b1 / w:.2f}\t{100 * sall / sents:.2f} ({sall}/{sents})')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('tag', 'combine', 'accuracy'))
    ap.add_argument('files', nargs='*')
    ap.add_argument('--tagger')
    ap.add_argument('--out')
    ap.add_argument('--k', type=int, default=10)
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--gold', default='data/encoded-2025-bothall-surface/dev.jsonl')
    a = ap.parse_intermixed_args()
    {'tag': tag, 'combine': combine, 'accuracy': accuracy}[a.cmd](a)


if __name__ == '__main__':
    main()
