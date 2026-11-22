#!/usr/bin/env python3
"""A larger ranking model for Orca's accepted derivations.

Trained on ACE's n-best parses of the Redwoods training sentences
(data/ranking/features/train-ace30.jsonl, -ace500.jsonl; see
ranker_extract.py): for each sentence, the candidate derivations as bare
trees and whether each has the gold MRS. The model is log-linear, like the
ERG's own MaxEnt model (redwoods.mem): a derivation's score is the sum of
weights of its features, and training maximizes the probability of the
gold-matching candidates among each sentence's candidates.

Features (hashed into 2^23 weights):
  - the MaxEnt model's own templates: a node, its daughters, and up to three
    ancestors, with lexical types at the leaves and the word below them;
  - the same with lexical entries in place of lexical types;
  - the ERG MaxEnt score itself, as one real-valued feature (so the model
    starts from the existing ranker and learns corrections).

Steps:
  featurize  -> data/ranking/features/shards/*.npz
  train      -> data/models/ranker-<name>/model.pt
  eval       -> rerank Orca's accepted dev derivations (MODEL/dev-strict-k30-b600.jsonl)

Usage:
  train_ranker.py featurize [--workers 5] [--limit N]
  train_ranker.py train --name NAME [--epochs 4] [--l2 1e-7]
  train_ranker.py eval --name NAME --kbest data/models/tagger-.../dev-strict-k30-b600.jsonl --out FILE
"""
import argparse
import collections
import glob
import json
import multiprocessing as mp
import os
import random
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
ORCA = os.path.join(HERE, '..')
FEAT = os.path.join(ORCA, 'data', 'ranking', 'features')
BITS = int(os.environ.get('RANKER_BITS', 23))      # hashed weights: 2^BITS
TEMPLATES = os.environ.get('RANKER_TEMPLATES', 'all')   # 'erg': only the ERG MaxEnt templates (lexical types)
SHARDS = ('shards' if BITS == 23 else f'shards{BITS}') + ('' if TEMPLATES == 'all' else '-' + TEMPLATES)
MASK = (1 << BITS) - 1
GP = 3                                    # grandparenting, as in redwoods.mem
MAX_CANDS = 100                           # per sentence, from the 500-best lists
SEP = '\x1f'

_E2T = None
_ME = None


def init_worker():
    global _E2T, _ME
    from encode_treebank import entry_types
    from orca.maxent import MaxEnt
    _E2T = {k.lower(): v for k, v in entry_types(os.path.join(ORCA, 'data', 'erg', '2025')).items()}
    _ME = MaxEnt(os.path.join(ORCA, 'data', 'erg', '2025', 'redwoods.mem'))


def is_leaf(t):
    return len(t) == 2 and isinstance(t[1], str)


def tree_features(tree):
    """Hashed feature ids and the ERG MaxEnt score of a bare tree."""
    ids, me = [], 0.0
    w = _ME.weights

    def walk(t, anc_t, anc_e):
        if is_leaf(t):
            entry = t[0].lower()
            lt = _E2T.get(entry) or entry
            labs = ((lt, anc_t), (entry, anc_e))
            word = '"' + t[1] + '"'
            kids_t = kids_e = (word,)
        else:
            lt = t[0]
            labs = ((lt, anc_t), (lt, anc_e))
            kids = t[1:]
            kids_t = tuple(_E2T.get(k[0].lower(), k[0].lower()) if is_leaf(k) else k[0] for k in kids)
            kids_e = tuple(k[0].lower() if is_leaf(k) else k[0] for k in kids)
        nonlocal me
        for which, ((name, anc), kids) in enumerate(zip(labs, (kids_t, kids_e))):
            for g in range(GP + 1):
                if g == 0:
                    up = ()
                elif g <= len(anc):
                    up = tuple(anc[-g:])
                elif g == len(anc) + 1:
                    up = ('^',) + tuple(anc)
                else:
                    break
                key = (g,) + up + (name,) + kids
                if which == 0:
                    me += w.get(key, 0.0)
                elif TEMPLATES == 'erg':
                    continue
                ids.append(key_id(which, key))
        if not is_leaf(t):
            for k in t[1:]:
                walk(k, anc_t + [lt], anc_e + [labs[1][0]])

    top = tree
    while not is_leaf(top) and top[0].lower().startswith('root_') and len(top) == 2:
        top = top[1]
    walk(top, [], [])
    return ids, me


def key_id(which, key):
    return zlib.crc32((str(which) + SEP + SEP.join(map(str, key))).encode()) & MASK


def featurize_line(line):
    r = json.loads(line)
    d = r['derivs']
    if not r.get('gold_in') or len(d) < 2 or all(g for _, g in d):
        return None
    if len(d) > MAX_CANDS:                # keep every gold one and a sample of the others
        gold = [x for x in d if x[1]]
        rest = [x for x in d if not x[1]]
        random.Random(r['id']).shuffle(rest)
        d = gold + rest[:MAX_CANDS - len(gold)]
        random.Random(r['id'] + '/order').shuffle(d)    # gold must not sit first: ties pick the first
    feats, lens, gold, mes = [], [], [], []
    for tree, g in d:
        try:
            ids, me = tree_features(tree)
        except Exception:
            continue
        feats.append(np.asarray(ids, dtype=np.int32))
        lens.append(len(ids))
        gold.append(bool(g))
        mes.append(me)
    if len(gold) < 2 or not any(gold) or all(gold):
        return None
    return r['id'], np.concatenate(feats), np.asarray(lens, np.int32), np.asarray(gold), np.asarray(mes, np.float32)


def featurize(a):
    os.makedirs(os.path.join(FEAT, SHARDS), exist_ok=True)
    done500 = set()
    p500 = os.path.join(FEAT, 'train-ace500.jsonl')

    def lines():
        n = 0
        if os.path.exists(p500):          # sentences whose gold is beyond the 30 best
            with open(p500) as f:
                for l in f:
                    if not l.endswith('\n'):
                        break
                    done500.add(json.loads(l[:200].split(',"n"')[0] + '}')['id'])
                    yield l
                    n += 1
                    if a.limit and n >= a.limit:
                        return
        with open(os.path.join(FEAT, 'train-ace30.jsonl')) as f:
            for l in f:
                if json.loads(l[:200].split(',"n"')[0] + '}')['id'] in done500:
                    continue
                yield l
                n += 1
                if a.limit and n >= a.limit:
                    return

    shard, buf, k = 0, [], 0

    def flush():
        nonlocal shard, buf
        if not buf:
            return
        ids, feats, lens, gold, mes = zip(*buf)
        np.savez(os.path.join(FEAT, SHARDS, f'shard{shard:03d}.npz'), ids=np.asarray(ids), feats=np.concatenate(feats),
                 tree_lens=np.concatenate(lens), cand_counts=np.asarray([len(x) for x in gold], np.int32),
                 gold=np.concatenate(gold), me=np.concatenate(mes))
        shard += 1
        buf = []

    with mp.Pool(a.workers, initializer=init_worker) as pool:
        for res in pool.imap(featurize_line, lines(), chunksize=16):
            k += 1
            if res is not None:
                buf.append(res)
            if len(buf) >= 5000:
                flush()
            if k % 5000 == 0:
                print('sentences', k, 'shards', shard, flush=True)
    flush()
    print('done', k, 'sentences read', shard, 'shards')


def load_shards():
    S = [np.load(p) for p in sorted(glob.glob(os.path.join(FEAT, SHARDS, '*.npz')))]
    ids = np.concatenate([s['ids'] for s in S])
    cc = np.concatenate([s['cand_counts'] for s in S])
    tl = np.concatenate([s['tree_lens'] for s in S])
    return ids, np.concatenate([s['feats'] for s in S]), tl, cc, np.concatenate([s['gold'] for s in S]), np.concatenate([s['me'] for s in S])


def model_cls():
    import torch

    class Ranker(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.w = torch.nn.EmbeddingBag(1 << BITS, 1, mode='sum', padding_idx=0)   # id 0: features cut as too rare
            torch.nn.init.zeros_(self.w.weight)
            self.me = torch.nn.Parameter(torch.ones(1))

        def forward(self, feats, offsets, me):
            return self.w(feats, offsets).squeeze(-1) + self.me * me
    return Ranker


def batch_tensors(sel, feats, tree_start, tl, cand_start, cc, gold, me, dev):
    """Tensors for a batch of sentences: flat trees and a padded [B, K] layout."""
    import torch
    trees = np.concatenate([np.arange(cand_start[s], cand_start[s] + cc[s]) for s in sel])
    f = np.concatenate([feats[tree_start[t]:tree_start[t] + tl[t]] for t in trees])
    offs = np.concatenate([[0], np.cumsum(tl[trees])[:-1]])
    K = int(cc[sel].max())
    pos = np.concatenate([np.arange(cc[s]) for s in sel])
    row = np.repeat(np.arange(len(sel)), cc[sel])
    t = lambda x, dt: torch.as_tensor(x, dtype=dt, device=dev)
    return (t(f, torch.long), t(offs, torch.long), t(me[trees], torch.float32), t(row, torch.long), t(pos, torch.long),
            K, t(gold[trees], torch.bool))


def nll(model, bt, n):
    import torch
    f, offs, me, row, pos, K, g = bt
    s = model(f, offs, me)
    full = torch.full((n, K), -1e9, device=s.device)
    full[row, pos] = s
    gm = torch.full((n, K), -1e9, device=s.device)
    gm[row, pos] = torch.where(g, s, torch.full_like(s, -1e9))
    return (torch.logsumexp(full, 1) - torch.logsumexp(gm, 1)).mean(), full, gm


def train(a):
    import torch
    dev = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    ids, feats, tl, cc, gold, me = load_shards()
    print('sentences', len(cc), 'candidates', len(tl), 'feature ids', len(feats), flush=True)
    if a.min_count:                  # features seen fewer times than this (over all candidates) are dropped to id 0
        counts = np.bincount(feats, minlength=1 << BITS)
        keep = counts >= a.min_count
        keep[0] = False
        feats = np.where(keep[feats], feats, 0).astype(np.int32)
        print('features kept', int(keep.sum()), 'of', int((counts > 0).sum()), flush=True)
    tree_start = np.concatenate([[0], np.cumsum(tl.astype(np.int64))[:-1]])
    cand_start = np.concatenate([[0], np.cumsum(cc.astype(np.int64))[:-1]])
    rng = np.random.default_rng(1)
    order = rng.permutation(len(cc))
    nh = max(500, len(cc) // 20)
    held, tr = order[:nh], order[nh:]
    Ranker = model_cls()
    model = Ranker().to(dev)
    if a.init_mem:                   # check: the ERG weights placed in the hashed table should reproduce MaxEnt
        from orca.maxent import MaxEnt
        mem = MaxEnt(os.path.join(ORCA, 'data', 'erg', '2025', 'redwoods.mem'))
        W = torch.zeros(1 << BITS)
        hit = collections.Counter()
        for key, wt in mem.weights.items():
            k = key_id(0, (key[0],) + tuple(key[1:]))
            hit[k] += 1
            W[k] += wt
        print('MaxEnt features', len(mem.weights), 'buckets used', len(hit), 'colliding buckets', sum(1 for v in hit.values() if v > 1), flush=True)
        with torch.no_grad():
            model.w.weight[:, 0] = W.to(dev)
    if a.no_me:                      # from scratch: no ERG MaxEnt score as a feature
        with torch.no_grad():
            model.me.zero_()
        model.me.requires_grad_(False)
    opt = torch.optim.Adagrad([p for p in model.parameters() if p.requires_grad], lr=a.lr, weight_decay=a.l2)
    out = os.path.join(ORCA, 'data', 'models', f'ranker-{a.name}')
    os.makedirs(out, exist_ok=True)

    def held_acc(which=None):
        which = held if which is None else which
        model.eval()
        right = right_me = 0
        with torch.no_grad():
            for i in range(0, len(which), 512):
                sel = which[i:i + 512]
                bt = batch_tensors(sel, feats, tree_start, tl, cand_start, cc, gold, me, dev)
                _, full, gm = nll(model, bt, len(sel))
                best = full.argmax(1)
                right += (gm.gather(1, best[:, None]).squeeze(1) > -1e8).sum().item()
                mfull = torch.full_like(full, -1e9)
                mfull[bt[3], bt[4]] = bt[2]
                right_me += (gm.gather(1, mfull.argmax(1)[:, None]).squeeze(1) > -1e8).sum().item()
        model.train()
        return right / len(which), right_me / len(which)

    D = dict(np.load(a.dev)) if a.dev else None
    if D is not None and a.min_count:
        D['feats'] = np.where(keep[D['feats']], D['feats'], 0).astype(np.int32)
    if D is not None:
        d_ts = np.concatenate([[0], np.cumsum(D['tree_lens'].astype(np.int64))[:-1]])
        d_cs = np.concatenate([[0], np.cumsum(D['cand_counts'].astype(np.int64))[:-1]])

    def dev_picked():
        if D is None:
            return None, None
        model.eval()
        with torch.no_grad():
            sel = np.arange(len(D['cand_counts']))
            bt = batch_tensors(sel, D['feats'], d_ts, D['tree_lens'], d_cs, D['cand_counts'], D['gold'], D['me'], dev)
            _, full, gm = nll(model, bt, len(sel))
            got = (gm.gather(1, full.argmax(1)[:, None]).squeeze(1) > -1e8).sum().item()
            mfull = torch.full_like(full, -1e9)
            mfull[bt[3], bt[4]] = bt[2]
            got_me = (gm.gather(1, mfull.argmax(1)[:, None]).squeeze(1) > -1e8).sum().item()
        model.train()
        return got, got_me

    print('dev picked (model, MaxEnt):', dev_picked(), flush=True)
    acc, acc_me = held_acc()
    print(f'held-out: gold picked {acc:.4f} (MaxEnt alone {acc_me:.4f})', flush=True)
    best, log = -1, []
    for ep in range(a.epochs):
        rng.shuffle(tr)
        tot = 0.0
        for bi, i in enumerate(range(0, len(tr), a.batch)):
            sel = tr[i:i + a.batch]
            bt = batch_tensors(sel, feats, tree_start, tl, cand_start, cc, gold, me, dev)
            loss, _, _ = nll(model, bt, len(sel))
            if a.l2_touched:                 # L2 on the weights this batch uses
                loss = loss + a.l2_touched * model.w.weight[torch.unique(bt[0])].pow(2).sum()
            opt.zero_grad()
            loss.backward()
            opt.step()
            tot += loss.item()
            if bi % 300 == 0:
                print(f'epoch {ep + 1} batch {bi} loss {tot / (bi + 1):.4f} dev {dev_picked()}', flush=True)
        acc, _ = held_acc()
        tracc, trme = held_acc(tr[:3000])
        print(f'train-sample gold picked {tracc:.4f} (MaxEnt {trme:.4f})', flush=True)
        dp, dme = dev_picked()
        log.append({'epoch': ep + 1, 'loss': tot / (bi + 1), 'held_gold_picked': acc, 'held_maxent_alone': acc_me, 'dev_picked': dp, 'dev_maxent': dme})
        print(json.dumps(log[-1]), flush=True)
        crit = dp if dp is not None else acc
        if crit > best:
            best = crit
            torch.save(model.state_dict(), os.path.join(out, 'model.pt'))
        elif ep >= 1:
            break
    json.dump({'args': vars(a), 'sentences': int(len(cc)), 'candidates': int(len(tl)), 'log': log}, open(os.path.join(out, 'metrics.json'), 'w'), indent=1)


def orca_bare(forms, leaf_labels, tree_labels, entries):
    """An Orca candidate (labels and entries) as a bare tree like ranker_extract.py makes."""
    from eval_trees import to_leaves
    from orca.encoding import Leaf, decode
    from rerank import with_entries
    t = with_entries(decode(to_leaves(forms, leaf_labels, tree_labels)), entries)

    def conv(n):
        if isinstance(n, Leaf):
            e = n.entry[6:] if n.entry.startswith('entry:') else n.entry
            return [e, ' '.join(n.forms).lower()]
        return [n.label] + [conv(c) for c in n.children]
    return conv(t)


def devprep(a):
    """Orca's accepted dev derivations as a shard, for scoring during training."""
    init_worker()
    ids, feats, lens, gold, mes, counts = [], [], [], [], [], []
    for line in open(a.kbest, encoding='utf-8'):
        r = json.loads(line)
        cands = r.get('candidates') or []
        if not cands:
            continue
        for c in cands:
            f, me = tree_features(orca_bare(r['forms'], c['leaf'], c['tree'], c['entries']))
            feats.append(np.asarray(f, np.int32)); lens.append(len(f)); mes.append(me); gold.append(bool(c.get('same_mrs')))
        ids.append(r['id']); counts.append(len(cands))
    np.savez(a.out, ids=np.asarray(ids), feats=np.concatenate(feats), tree_lens=np.asarray(lens, np.int32),
             cand_counts=np.asarray(counts, np.int32), gold=np.asarray(gold), me=np.asarray(mes, np.float32))
    print('dev sentences with candidates', len(ids), 'candidates', len(lens))


def evaluate(a):
    import collections
    import torch
    init_worker()
    from rerank import BANDS
    Ranker = model_cls()
    model = Ranker()
    if a.name:
        model.load_state_dict(torch.load(os.path.join(ORCA, 'data', 'models', f'ranker-{a.name}', 'model.pt'), map_location='cpu'))
    model.eval()
    st = collections.Counter()
    by = collections.defaultdict(collections.Counter)
    for line in open(a.kbest, encoding='utf-8'):
        r = json.loads(line)
        st['sentences'] += 1
        band = next(n for lo, hi, n in BANDS if lo <= len(r['forms']) < hi)
        by[band]['sentences'] += 1
        cands = r.get('candidates') or []
        if not cands:
            continue
        st['with candidates'] += 1
        golds, feats, offs, mes = [], [], [], []
        for c in cands:
            ids, me = tree_features(orca_bare(r['forms'], c['leaf'], c['tree'], c['entries']))
            offs.append(sum(len(x) for x in feats))
            feats.append(ids)
            mes.append(me)
            golds.append(bool(c.get('same_mrs')))
        with torch.no_grad():
            s = model(torch.tensor([i for x in feats for i in x], dtype=torch.long), torch.tensor(offs), torch.tensor(mes)).numpy()
        pick = {'first found': 0, 'ERG MaxEnt': int(np.argmax(mes)), 'new model': int(np.argmax(s))}
        st['oracle'] += any(golds)
        by[band]['oracle'] += any(golds)
        for k, i in pick.items():
            st[k] += golds[i]
            by[band][k] += golds[i]
    res = {'kbest': a.kbest, 'model': a.name, 'stats': dict(st), 'by_length': {b: dict(by[b]) for _, _, b in BANDS}}
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['featurize', 'train', 'eval', 'devprep'])
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--name', default='')
    ap.add_argument('--epochs', type=int, default=4)
    ap.add_argument('--batch', type=int, default=64)
    ap.add_argument('--lr', type=float, default=0.05)
    ap.add_argument('--l2', type=float, default=0.0)
    ap.add_argument('--kbest')
    ap.add_argument('--no-me', action='store_true')
    ap.add_argument('--init-mem', action='store_true')
    ap.add_argument('--min-count', type=int, default=0)
    ap.add_argument('--l2-touched', type=float, default=0.0)
    ap.add_argument('--dev', help='dev shard from devprep: early stopping on picked-gold count there')
    ap.add_argument('--out')
    a = ap.parse_args()
    {'featurize': featurize, 'train': train, 'eval': evaluate, 'devprep': devprep}[a.step](a)


if __name__ == '__main__':
    main()
