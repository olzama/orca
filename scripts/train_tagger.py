#!/usr/bin/env python3
"""Tagger v1: one encoder, two classification heads per token.

leaf head: lexical type + lexical rules + unary rules above the leaf
tree head: relative depth + label of the lowest common ancestor with the
           next leaf

Reads the JSON lines written by encode_treebank.py. After every epoch it
evaluates on dev and keeps the best model; at the end it evaluates the best
model on dev and test and writes predictions and metrics.

Usage:
    train_tagger.py --data DATA_DIR --out MODEL_DIR [--encoder NAME] [--epochs N]
"""
import argparse
import collections
import json
import math
import os
import random
import signal
import sys
import time

import torch
from torch import nn
from transformers import AutoModel, AutoTokenizer

NONE, UNK = '<none>', '<unk>'


def leaf_label(t):
    return f"{t['lextype']}|{t['lexrules']}|{t['unaries']}"


def tree_label(t):
    return NONE if t['node'] is None else f"{t['delta']}|{t['node']}"


def read(path, limit=None):
    sents = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            toks = rec['tokens']
            sents.append({'id': rec['id'], 'forms': [t['form'] for t in toks],
                          'leaf': [leaf_label(t) for t in toks],
                          'tree': [tree_label(t) for t in toks]})
            if limit and len(sents) >= limit:
                break
    return sents


def vocab(sents, key):
    counts = collections.Counter(l for s in sents for l in s[key])
    itos = [UNK] + sorted(counts)
    return itos, {l: i for i, l in enumerate(itos)}, counts


class Tagger(nn.Module):
    """Encoder plus two heads. With `lora`, the encoder is frozen in half
    precision and trained through low-rank adapters (for decoder language
    models); with `bilstm`, a bidirectional LSTM sits between encoder and
    heads, so that a left-to-right model also sees the words to the right."""

    def __init__(self, encoder, n_leaf, n_tree, dropout=0.1, lora=0, bilstm=0):
        super().__init__()
        if lora:
            from peft import LoraConfig, get_peft_model
            base = AutoModel.from_pretrained(encoder, torch_dtype=torch.float16)
            self.encoder = get_peft_model(base, LoraConfig(
                r=lora, lora_alpha=2 * lora, lora_dropout=0.05,
                target_modules=['q_proj', 'k_proj', 'v_proj', 'o_proj',
                                'gate_proj', 'up_proj', 'down_proj']))
        else:
            self.encoder = AutoModel.from_pretrained(encoder, torch_dtype=torch.float32)  # some checkpoints (deberta-v3) default to fp16
        h = self.encoder.config.hidden_size
        self.lstm = nn.LSTM(h, bilstm, batch_first=True, bidirectional=True) if bilstm else None
        out = 2 * bilstm if bilstm else h
        self.drop = nn.Dropout(dropout)
        self.leaf = nn.Linear(out, n_leaf)
        self.tree = nn.Linear(out, n_tree)

    def forward(self, input_ids, attention_mask, first):
        hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        if self.lstm is not None:
            with torch.autocast('cuda', enabled=False):
                packed = nn.utils.rnn.pack_padded_sequence(
                    hidden.float(), attention_mask.sum(1).cpu(), batch_first=True, enforce_sorted=False)
                hidden, _ = nn.utils.rnn.pad_packed_sequence(
                    self.lstm(packed)[0], batch_first=True, total_length=input_ids.size(1))
        words = self.drop(hidden[first])          # one vector per word
        return self.leaf(words), self.tree(words)

    def trained_state(self):
        """Everything except frozen encoder weights."""
        frozen = {n for n, p in self.named_parameters() if not p.requires_grad}
        return {k: v for k, v in self.state_dict().items() if k not in frozen}


def batches(sents, size, shuffle):
    order = list(range(len(sents)))
    if shuffle:
        random.shuffle(order)
        # group sentences of similar length inside large shuffled chunks
        chunks = [order[i:i + size * 50] for i in range(0, len(order), size * 50)]
        order = [i for c in chunks for i in sorted(c, key=lambda i: len(sents[i]['forms']))]
        groups = [order[i:i + size] for i in range(0, len(order), size)]
        random.shuffle(groups)
    else:
        order.sort(key=lambda i: len(sents[i]['forms']))
        groups = [order[i:i + size] for i in range(0, len(order), size)]
    for g in groups:
        yield [sents[i] for i in g]


_PIECES = {}


def collate_last(batch, tok, leaf_stoi, tree_stoi, device, max_len=512):
    """For left-to-right models: words are tokenized one by one and each word
    is represented by its last subword, which has seen the whole word."""
    rows, marks, leaf, tree, kept = [], [], [], [], []
    for s in batch:
        ids, last = [], []
        for i, w in enumerate(s['forms']):
            key = (i > 0, w)
            if key not in _PIECES:
                _PIECES[key] = tok.encode((' ' if i else '') + w, add_special_tokens=False) or [tok.pad_token_id]
            if len(ids) + len(_PIECES[key]) > max_len:
                break
            ids.extend(_PIECES[key])
            last.append(len(ids) - 1)
            leaf.append(leaf_stoi.get(s['leaf'][i], 0))
            tree.append(tree_stoi.get(s['tree'][i], 0))
        rows.append(ids)
        marks.append(last)
        kept.append(len(last))
    width = max(len(r) for r in rows)
    input_ids = torch.full((len(rows), width), tok.pad_token_id, dtype=torch.long)
    mask = torch.zeros((len(rows), width), dtype=torch.long)
    first = torch.zeros((len(rows), width), dtype=torch.bool)
    for b, (ids, last) in enumerate(zip(rows, marks)):
        input_ids[b, :len(ids)] = torch.tensor(ids)
        mask[b, :len(ids)] = 1
        first[b, last] = True
    return (input_ids.to(device), mask.to(device), first.to(device),
            torch.tensor(leaf, device=device), torch.tensor(tree, device=device), kept)


def collate(batch, tok, leaf_stoi, tree_stoi, device, max_len=512):
    if getattr(tok, 'orca_last_subword', False):
        return collate_last(batch, tok, leaf_stoi, tree_stoi, device, max_len)
    enc = tok([s['forms'] for s in batch], is_split_into_words=True, truncation=True,
              max_length=max_len, padding=True, return_tensors='pt')
    first = torch.zeros_like(enc['input_ids'], dtype=torch.bool)
    leaf, tree, kept = [], [], []
    for b, s in enumerate(batch):
        seen = set()
        for pos, w in enumerate(enc.word_ids(b)):
            if w is not None and w not in seen:
                seen.add(w)
                first[b, pos] = True
                leaf.append(leaf_stoi.get(s['leaf'][w], 0))
                tree.append(tree_stoi.get(s['tree'][w], 0))
        kept.append(len(seen))    # words that survived truncation
    return (enc['input_ids'].to(device), enc['attention_mask'].to(device), first.to(device),
            torch.tensor(leaf, device=device), torch.tensor(tree, device=device), kept)


def jsd(p, q):
    """Jensen-Shannon divergence (bits) between two count dictionaries."""
    keys = set(p) | set(q)
    n, m = sum(p.values()), sum(q.values())
    out = 0.0
    for k in keys:
        a, b = p.get(k, 0) / n, q.get(k, 0) / m
        mid = (a + b) / 2
        if a:
            out += 0.5 * a * math.log2(a / mid)
        if b:
            out += 0.5 * b * math.log2(b / mid)
    return out


@torch.no_grad()
def evaluate(model, sents, tok, vocabs, device, train_counts, batch_size=64, pred_path=None):
    (leaf_itos, leaf_stoi), (tree_itos, tree_stoi) = vocabs
    model.eval()
    n_tok = ok_leaf = ok_tree = ok_both = 0
    sent_total = collections.Counter()
    sent_ok = collections.Counter()
    truncated = 0
    gold_lt, pred_lt = collections.Counter(), collections.Counter()
    band_total, band_ok = collections.Counter(), collections.Counter()
    out = open(pred_path, 'w', encoding='utf-8') if pred_path else None
    start = time.time()
    for batch in batches(sents, batch_size, shuffle=False):
        ids, mask, first, _, _, kept = collate(batch, tok, leaf_stoi, tree_stoi, device)
        with torch.autocast('cuda', dtype=torch.float16, enabled=device.type == 'cuda'):
            leaf_logits, tree_logits = model(ids, mask, first)
        pl, pt = leaf_logits.argmax(-1).tolist(), tree_logits.argmax(-1).tolist()
        at = 0
        for s, k in zip(batch, kept):
            n = len(s['forms'])
            pred_leaf = [leaf_itos[i] for i in pl[at:at + k]] + [UNK] * (n - k)
            pred_tree = [tree_itos[i] for i in pt[at:at + k]] + [UNK] * (n - k)
            at += k
            truncated += k < n
            all_ok = True
            for gl, gt, a, b in zip(s['leaf'], s['tree'], pred_leaf, pred_tree):
                n_tok += 1
                ok_leaf += gl == a
                ok_tree += gt == b
                ok_both += gl == a and gt == b
                all_ok &= gl == a and gt == b
                g_type, p_type = gl.split('|')[0], a.split('|')[0]
                gold_lt[g_type] += 1
                pred_lt[p_type] += 1
                f = train_counts.get(g_type, 0)
                band = '0' if f == 0 else '1-9' if f < 10 else '10-99' if f < 100 else '100-999' if f < 1000 else '1000+'
                band_total[band] += 1
                band_ok[band] += g_type == p_type
            band = min(n // 10 * 10, 60)
            sent_total[band] += 1
            sent_ok[band] += all_ok
            if out:
                out.write(json.dumps({'id': s['id'], 'forms': s['forms'], 'leaf': pred_leaf,
                                      'tree': pred_tree}, ensure_ascii=False) + '\n')
    if out:
        out.close()
    secs = time.time() - start
    return {
        'tokens': n_tok, 'sentences': sum(sent_total.values()),
        'leaf_acc': ok_leaf / n_tok, 'tree_acc': ok_tree / n_tok, 'both_acc': ok_both / n_tok,
        'exact_match': sum(sent_ok.values()) / sum(sent_total.values()),
        'exact_match_by_length': {str(b): [sent_ok[b], sent_total[b]] for b in sorted(sent_total)},
        'lextype_acc_by_train_frequency': {b: [band_ok[b], band_total[b]] for b in band_total},
        'lextype_types_gold': len(gold_lt), 'lextype_types_predicted': len(pred_lt),
        'lextype_types_gold_never_predicted': len(set(gold_lt) - set(pred_lt)),
        'lextype_jsd_bits': jsd(gold_lt, pred_lt),
        'truncated_sentences': truncated,
        'sentences_per_second': sum(sent_total.values()) / secs,
        'tokens_per_second': n_tok / secs,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--encoder', default='bert-base-cased')
    ap.add_argument('--epochs', type=int, default=6)
    ap.add_argument('--batch', type=int, default=32)
    ap.add_argument('--lr', type=float, default=3e-5)
    ap.add_argument('--head-lr', type=float, default=1e-3)
    ap.add_argument('--limit', type=int, default=None, help='use only this many training sentences')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--lora', type=int, default=0, help='adapter rank; freezes the encoder')
    ap.add_argument('--bilstm', type=int, default=0, help='hidden size of a BiLSTM over the encoder')
    ap.add_argument('--last-subword', action='store_true',
                    help='represent a word by its last subword (left-to-right models)')
    ap.add_argument('--freeze-embeddings', action='store_true',
                    help='do not update the embedding table (saves optimizer memory)')
    ap.add_argument('--grad-checkpointing', action='store_true',
                    help='recompute activations in the backward pass (less memory, about a third slower)')
    ap.add_argument('--checkpoint-every', type=int, default=2000,
                    help='save a resumable checkpoint every this many steps (and on SIGTERM/SIGINT)')
    ap.add_argument('--resume', action='store_true', help='continue from OUT/checkpoint.pt if it exists')
    args = ap.parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    os.makedirs(args.out, exist_ok=True)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    train = read(os.path.join(args.data, 'train.jsonl'), args.limit)
    dev = read(os.path.join(args.data, 'dev.jsonl'))
    test = read(os.path.join(args.data, 'test.jsonl'))
    leaf_itos, leaf_stoi, leaf_counts = vocab(train, 'leaf')
    tree_itos, tree_stoi, _ = vocab(train, 'tree')
    lextype_counts = collections.Counter()
    for l, c in leaf_counts.items():
        lextype_counts[l.split('|')[0]] += c
    vocabs = ((leaf_itos, leaf_stoi), (tree_itos, tree_stoi))
    with open(os.path.join(args.out, 'labels.json'), 'w') as f:
        json.dump({'leaf': leaf_itos, 'tree': tree_itos, 'encoder': args.encoder}, f)
    print(f'train {len(train)} dev {len(dev)} test {len(test)} | leaf labels {len(leaf_itos)} '
          f'tree labels {len(tree_itos)}', flush=True)

    tok = AutoTokenizer.from_pretrained(args.encoder)
    tok.orca_last_subword = args.last_subword
    model = Tagger(args.encoder, len(leaf_itos), len(tree_itos), lora=args.lora, bilstm=args.bilstm).to(device)
    if args.grad_checkpointing:
        model.encoder.gradient_checkpointing_enable()
    heads = list(model.leaf.parameters()) + list(model.tree.parameters())
    if model.lstm is not None:
        heads += list(model.lstm.parameters())
    if args.freeze_embeddings:
        for p in model.encoder.embeddings.parameters():
            p.requires_grad = False
    body = [p for p in model.encoder.parameters() if p.requires_grad]
    opt = torch.optim.AdamW([{'params': body, 'lr': args.lr},
                             {'params': heads, 'lr': args.head_lr}], weight_decay=0.01)
    steps = args.epochs * math.ceil(len(train) / args.batch)
    warm = int(0.05 * steps)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warm if s < warm else max(0.0, (steps - s) / (steps - warm)))
    scaler = torch.amp.GradScaler(enabled=device.type == 'cuda')
    loss_fn = nn.CrossEntropyLoss()

    best, history, step, skipped = -1.0, [], 0, 0
    ckpt_path = os.path.join(args.out, 'checkpoint.pt')
    start_epoch, start_pos, epoch_rng = 1, 0, None
    if args.resume and os.path.exists(ckpt_path):
        ck = torch.load(ckpt_path, map_location=device, weights_only=False)
        model.load_state_dict(ck['model'])
        opt.load_state_dict(ck['opt'])
        sched.load_state_dict(ck['sched'])
        scaler.load_state_dict(ck['scaler'])
        best, history, step, skipped = ck['best'], ck['history'], ck['step'], ck['skipped']
        start_epoch, start_pos, epoch_rng = ck['epoch'], ck['pos'], ck['epoch_rng']
        torch.set_rng_state(ck['torch_rng'].cpu())
        if device.type == 'cuda' and ck.get('cuda_rng') is not None:
            torch.cuda.set_rng_state(ck['cuda_rng'].cpu())
        print(f'resumed at epoch {start_epoch}, batch {start_pos}, step {step}', flush=True)
    stop = {'now': False}

    def on_signal(signum, frame):
        stop['now'] = True
    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    def save_checkpoint(epoch, pos, rng):
        tmp = ckpt_path + '.tmp'
        torch.save({'model': model.state_dict(), 'opt': opt.state_dict(), 'sched': sched.state_dict(),
                    'scaler': scaler.state_dict(), 'best': best, 'history': history, 'step': step,
                    'skipped': skipped, 'epoch': epoch, 'pos': pos, 'epoch_rng': rng,
                    'torch_rng': torch.get_rng_state(),
                    'cuda_rng': torch.cuda.get_rng_state() if device.type == 'cuda' else None}, tmp)
        os.replace(tmp, ckpt_path)

    for epoch in range(start_epoch, args.epochs + 1):
        model.train()
        t0, running = time.time(), 0.0
        if epoch == start_epoch and epoch_rng is not None:
            random.setstate(epoch_rng)
        else:
            epoch_rng = random.getstate()        # the epoch's batch order is rebuilt from this on resume
            start_pos = 0
        epoch_batches = list(batches(train, args.batch, shuffle=True))
        for pos, batch in enumerate(epoch_batches):
            if pos < start_pos:
                continue
            if stop['now']:
                save_checkpoint(epoch, pos, epoch_rng)
                print(f'stopped at epoch {epoch}, batch {pos}, step {step}; checkpoint saved', flush=True)
                sys.exit(75)
            if step and step % args.checkpoint_every == 0 and pos > start_pos:
                save_checkpoint(epoch, pos, epoch_rng)
            ids, mask, first, leaf, tree, _ = collate(batch, tok, leaf_stoi, tree_stoi, device)
            try:
                with torch.autocast('cuda', dtype=torch.float16, enabled=device.type == 'cuda'):
                    leaf_logits, tree_logits = model(ids, mask, first)
                    loss = loss_fn(leaf_logits.float(), leaf) + loss_fn(tree_logits.float(), tree)
                opt.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
            except torch.OutOfMemoryError:      # a batch of very long sentences
                del ids, mask, first, leaf, tree
                opt.zero_grad(set_to_none=True)
                torch.cuda.empty_cache()
                skipped += 1
                sched.step()
                step += 1
                continue
            scaler.unscale_(opt)
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            step += 1
            running += loss.item()
            if step % 500 == 0:
                print(f'  step {step}/{steps} loss {running / 500:.3f}', flush=True)
                running = 0.0
        m = evaluate(model, dev, tok, vocabs, device, lextype_counts, batch_size=args.batch)
        m['epoch'], m['train_minutes'] = epoch, (time.time() - t0) / 60
        m['batches_skipped_for_memory'] = skipped
        history.append(m)
        print(f"epoch {epoch}: leaf {m['leaf_acc']:.4f} tree {m['tree_acc']:.4f} "
              f"exact {m['exact_match']:.4f} ({m['train_minutes']:.1f} min)", flush=True)
        if m['exact_match'] > best:
            best = m['exact_match']
            torch.save(model.trained_state(), os.path.join(args.out, 'model.pt'))
        save_checkpoint(epoch + 1, 0, random.getstate())

    model.load_state_dict(torch.load(os.path.join(args.out, 'model.pt'), map_location=device), strict=False)
    final = {'args': vars(args), 'history': history}
    for name, sents in (('dev', dev), ('test', test)):
        final[name] = evaluate(model, sents, tok, vocabs, device, lextype_counts, batch_size=args.batch,
                               pred_path=os.path.join(args.out, f'{name}-pred.jsonl'))
    with open(os.path.join(args.out, 'metrics.json'), 'w') as f:
        json.dump(final, f, indent=1)
    print(json.dumps({k: final[k] for k in ('dev', 'test')}, indent=1))


if __name__ == '__main__':
    main()
