#!/usr/bin/env python3
"""Checks for the --per-item-disable patch on delph-in/ace main (roadmap O109, step 1).

Builds compared: main without the patch ("stock") and main with it ("patched"), both from
third_party/build/ace-upstream/, with ERG 2025 compiled by the stock main build.
  (a) without the flag: patched and stock produce byte-identical output on 300 dev sentences,
      first-best (-1) and 20-best (-n 20), MRS and derivation of every result in rank order;
  (b) with the flag: one patched process fed "#DISABLE <lexemes>" before each sentence gives,
      item by item, the same output as stock main run once per sentence with -L <lexemes>;
      the restrictions are Orca's chart-mode restrictions from saved tagger output (top 5, >= 0.001);
  (c) the restriction really changes between items.
Usage: python3 check.py OUT.json
"""
import json
import os
import pickle
import random
import subprocess
import sys
import time

ROOT = '/mnt/kesha/orca'
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, ROOT)
B = os.path.join(ROOT, 'third_party/build/ace-upstream')
STOCK, PATCHED = f'{B}/main-stock/ace', f'{B}/main-patched/ace'
DAT = f'{B}/erg-2025-main.dat'
LIM = ['--timeout=60', '--max-chart-megabytes=6000', '--max-unpack-megabytes=7000']
MODES = {'first-best': ['-1'], 'n-best (20)': ['-n', '20']}   # console output: MRS and derivation per result, in rank order, no timings


def items_of(stdout, n):
    """Split ACE's console output into one string per input item (each ends with two empty lines)."""
    blocks, cur = [], []
    lines = stdout.split('\n')
    i = 0
    while i < len(lines):
        cur.append(lines[i])
        if lines[i] == '' and i + 1 < len(lines) and lines[i + 1] == '' and any(x.strip() for x in cur):
            blocks.append('\n'.join(cur).strip())
            cur = []
            i += 1
        i += 1
    if any(x.strip() for x in cur):
        blocks.append('\n'.join(cur).strip())
    return blocks


def run(binary, args, text):
    p = subprocess.run([binary, '-g', DAT] + args, input=text, capture_output=True, text=True)
    return p.stdout


def check_c():
    s = 'The dog barked.'
    steps = [('bark_v1', False), ('', True), ('bark_v1', False)]
    text = ''.join(f'#DISABLE {d}\n{s}\n' if d else f'#DISABLE\n{s}\n' for d, _ in steps)
    pat = items_of(run(PATCHED, ['-1', '--per-item-disable'], text), len(steps))
    rows = []
    for (d, verb), p in zip(steps, pat):
        st = run(STOCK, ['-1'] + (['-L', d] if d else []), s + '\n').strip()
        rows.append({'disabled': d, 'has _bark_v_1': '_bark_v_1' in p, 'expected': verb, 'same as stock with -L': p == st})
    return {'items': rows, 'ok': all(r['has _bark_v_1'] == r['expected'] and r['same as stock with -L'] for r in rows)}


def main():
    import supertag_ace as S
    S._init(None)
    items = pickle.load(open(os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl'), 'rb'))['items']
    ids = sorted(i for i in items if items[i].get('top'))
    random.Random(20261124).shuffle(ids)
    ids = ids[:300]
    sents = [' '.join(items[i]['text'].split()) for i in ids]
    dis = [' '.join(sorted(S.allowed_and_disabled(items[i], 5, 0.001)[1])) for i in ids]
    res = {'sentences': len(ids), 'stock': STOCK, 'patched': PATCHED, 'grammar image': DAT}

    # (a) no flag: byte-identical output
    a = {}
    for m, args in MODES.items():
        text = '\n'.join(sents) + '\n'
        t0 = time.time(); so = run(STOCK, args + LIM, text); ts = time.time() - t0
        t0 = time.time(); po = run(PATCHED, args + LIM, text); tp = time.time() - t0
        a[m] = {'identical': so == po, 'bytes': len(so), 'stock seconds': ts, 'patched seconds': tp}
    res['(a) without the flag'] = a

    # (b) with the flag vs stock with -L per sentence
    b = {}
    for m, args in MODES.items():
        t0 = time.time()
        stock = [run(STOCK, args + LIM + (['-L', d] if d else []), s + '\n').strip() for s, d in zip(sents, dis)]
        ts = time.time() - t0
        text = ''.join(f'#DISABLE {d}\n{s}\n' for s, d in zip(sents, dis))
        t0 = time.time(); po = run(PATCHED, args + LIM + ['--per-item-disable'], text); tp = time.time() - t0
        pat = items_of(po, len(sents))
        diff = [ids[i] for i in range(len(sents)) if i >= len(pat) or pat[i] != stock[i]]
        b[m] = {'items compared': len(sents), 'patched items': len(pat), 'identical': len(sents) - len(diff),
                'differ': diff[:20], 'stock seconds (one run per sentence)': ts, 'patched seconds (one process)': tp,
                'ms per sentence stock': 1000 * ts / len(sents), 'ms per sentence patched': 1000 * tp / len(sents)}
    res['(b) with the flag'] = b

    # (c) the restriction changes between items: the same sentence with and without bark_v1 disabled;
    # each item must equal stock ACE run once with the same -L, and _bark_v_1 must vanish and come back
    res['(c) restriction changes'] = check_c()
    json.dump(res, open(sys.argv[1], 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items()}, indent=1)[:3000])


if __name__ == '__main__':
    main()
