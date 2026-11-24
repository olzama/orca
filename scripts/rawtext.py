#!/usr/bin/env python3
"""More raw text for training (roadmap task l-rawtext): Gutenberg and Wikipedia.

Steps (outputs under data/rawtext/<source>/):
  pool    split the downloaded parquet text into sentences, filter, dedupe, drop
          Redwoods dev/test sentences (and whole Wikipedia articles that contain
          one), drop sentences already in training; sample N per source.
  parse   Orca in fallback mode on the sample (one process per --shard), saving
          per sentence the outcome, mode, MRS, labels and the routing signals.
  route   fit the "Orca is wrong" router on dev (scripts/ace_fallback.py
          features) and choose the sentences to send to full ACE.
  ace     full ACE (first parse) on the chosen sentences, through a tsdb profile.
  silver  training records: ACE's derivation where ACE ran and parsed, else
          Orca's accepted replay derivation; replay-checked; agreement report;
          assemble data/encoded-2025-bothall-raw1-surface.

The parquet files are untrusted data: they are only read as text.
"""
import argparse
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.setrecursionlimit(20000)

RAW = {'gutenberg': 'data/raw/gutenberg/*.parquet', 'wikipedia': 'data/raw/wikipedia/*.parquet'}
OUT = os.path.join(ROOT, 'data/rawtext')
BASE_TRAIN = os.path.join(ROOT, 'data/encoded-2025-bothall-news25-surface/train.jsonl')
NEW_DIR = os.path.join(ROOT, 'data/encoded-2025-bothall-raw1-surface')

ABBREV = {'mr', 'mrs', 'ms', 'dr', 'st', 'prof', 'sr', 'jr', 'vs', 'etc', 'e.g', 'i.e', 'no', 'vol', 'fig', 'gen',
          'col', 'capt', 'lt', 'sgt', 'rev', 'hon', 'gov', 'sen', 'rep', 'inc', 'ltd', 'co', 'corp', 'jan', 'feb',
          'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec', 'mt', 'ft', 'u.s', 'c', 'ca', 'approx'}
FUNC = {'the', 'of', 'and', 'to', 'a', 'in', 'is', 'was', 'that', 'it', 'he', 'she', 'for', 'with', 'as', 'on', 'his',
        'her', 'i', 'you', 'they', 'be', 'by', 'at', 'had', 'not', 'are', 'but', 'this', 'from', 'which', 'were'}


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def split_sentences(par):
    out, start = [], 0
    for m in re.finditer(r'[.!?]["\'”’)\]]*\s+(?=["\'“‘(]?[A-Z])', par):
        end = m.end()
        prev = par[start:m.start() + 1].rstrip()
        last = re.findall(r'([A-Za-z.]+)\.$', prev)
        if last and (last[0].lower().rstrip('.') in ABBREV or re.fullmatch(r'[A-Z]', last[0])):
            continue
        out.append(par[start:end].strip())
        start = end
    tail = par[start:].strip()
    if tail:
        out.append(tail)
    return out


def good(s):
    w = s.split()
    if not 4 <= len(w) <= 45:
        return False
    if not re.match(r'^["\'“‘(]?[A-Z]', s) or not re.search(r'[.!?]["\'”’)]*$', s):
        return False
    if re.search(r'[|{}=<>\\@#*~^\[\]]|https?:|www\.|\t|_{2,}|\.\.\.\.|--{2,}', s):
        return False
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 0.6 * len(s.replace(' ', '')):
        return False
    if sum(c.isdigit() for c in s) > 0.1 * len(s):
        return False
    if sum(c.isupper() for c in letters) > 0.3 * len(letters):
        return False
    if sum(1 for c in letters if not c.isascii()) > 0.03 * len(letters):
        return False
    if not FUNC & {x.lower().strip('.,;:!?"\'()') for x in w}:
        return False
    if 'gutenberg' in s.lower() or 'ebook' in s.lower():
        return False
    return True


def paragraphs(text, source):
    if source == 'gutenberg':
        a = re.search(r'\*\*\* ?START OF[^\n]*\n', text)
        b = re.search(r'\n[^\n]*\*\*\* ?END OF', text)
        text = text[a.end() if a else 0: b.start() if b else len(text)]
    for par in re.split(r'\n\s*\n', text):
        lines = [l.strip() for l in par.split('\n') if l.strip()]
        if not lines:
            continue
        if source == 'gutenberg' and len(lines) >= 3 and sum(len(l) < 45 for l in lines) > len(lines) / 2:
            continue                                     # verse, tables of contents, indexes
        par = ' '.join(lines).replace('_', '')
        par = re.sub(r'\s+', ' ', par)
        if source == 'wikipedia' and not re.search(r'[.!?]$', par):
            continue                                     # headings, list items
        yield par


def redwoods_eval_texts():
    from delphin import tsdb
    keys = set()
    for split in ('dev', 'test'):
        for prof in glob.glob(os.path.join(ROOT, 'data/profiles-2025', split, '*')):
            if not os.path.exists(os.path.join(prof, 'item')) and not os.path.exists(os.path.join(prof, 'item.gz')):
                continue
            names = [f.name for f in tsdb.read_schema(prof)['item']]
            with tsdb.open(prof, 'item') as rows:
                for line in rows:
                    keys.add(norm(tsdb.split(line)[names.index('i-input')]))
    keys.discard('')
    return keys


def training_texts():
    keys = set()
    for l in open(BASE_TRAIN):
        r = json.loads(l)
        keys.add(norm(''.join(t['form'] for t in r['tokens'])))
    return keys


def cmd_pool(a):
    import pyarrow.parquet as pq
    rw = redwoods_eval_texts()
    tr = training_texts()
    print('redwoods dev/test sentences', len(rw), 'training sentences', len(tr), flush=True)
    for source, pat in RAW.items():
        d = os.path.join(OUT, source)
        os.makedirs(d, exist_ok=True)
        seen, pool, stats = set(), [], {'documents': 0, 'documents dropped (contain a Redwoods dev/test sentence)': 0,
                                        'sentences split': 0, 'kept by filters': 0, 'duplicates': 0, 'in training': 0}
        dropped_titles = []
        for f in sorted(glob.glob(os.path.join(ROOT, pat))):
            pf = pq.ParquetFile(f)
            for batch in pf.iter_batches(batch_size=200):
                for row in batch.to_pylist():
                    stats['documents'] += 1
                    doc = str(row.get('id'))
                    sents = []
                    for par in paragraphs(row.get('text') or '', source):
                        sents += split_sentences(par)
                    stats['sentences split'] += len(sents)
                    keys = [norm(s) for s in sents]
                    if any(k in rw for k in keys if len(k) > 20):
                        stats['documents dropped (contain a Redwoods dev/test sentence)'] += 1
                        dropped_titles.append(row.get('title') or doc)
                        continue
                    for i, (s, k) in enumerate(zip(sents, keys)):
                        if not good(s):
                            continue
                        stats['kept by filters'] += 1
                        if k in seen:
                            stats['duplicates'] += 1
                            continue
                        seen.add(k)
                        if k in tr:
                            stats['in training'] += 1
                            continue
                        if k in rw:
                            continue
                        pool.append({'doc': doc, 'title': row.get('title'), 'n': i, 'text': s})
        stats['pool'] = len(pool)
        random.seed(1)
        sample = random.sample(pool, min(a.n, len(pool)))
        for j, x in enumerate(sample):
            x['id'] = f'{source}/{j + 1}'
        with open(os.path.join(d, 'sample.jsonl'), 'w') as o:
            for x in sample:
                o.write(json.dumps(x, ensure_ascii=False) + '\n')
        stats['sample'] = len(sample)
        stats['dropped documents'] = dropped_titles[:200]
        json.dump(stats, open(os.path.join(d, 'pool.json'), 'w'), indent=1)
        print(source, {k: v for k, v in stats.items() if k != 'dropped documents'}, flush=True)


def cmd_parse(a):
    """Orca fallback mode on one shard of a source's sample."""
    import time
    from orca_parse import Parser
    d = os.path.join(OUT, a.source)
    sample = [json.loads(l) for l in open(os.path.join(d, 'sample.jsonl'))]
    mine = sample[a.shard::a.shards]
    out_path = os.path.join(d, f'parse-{a.shard}.jsonl')
    done = set()
    if os.path.exists(out_path):
        done = {json.loads(l)['id'] for l in open(out_path)}
    p = Parser(tagger=a.tagger, mode='fallback', fragments=False)
    orig_tag = p.tag
    last = {}

    def tag(forms):
        top = orig_tag(forms)
        last['top1'] = {k: [w[0][2] for w in top[k]] for k in ('leaf', 'tree')}
        return top
    p.tag = tag
    with open(out_path, 'a') as o:
        for x in mine:
            if x['id'] in done:
                continue
            last.clear()
            t0 = time.time()
            try:
                r = p.parse(x['text'], x['id'])
            except Exception as e:
                r = {'outcome': f'error: {type(e).__name__}'}
            rec = {'id': x['id'], 'text': x['text'], 'outcome': r.get('outcome'), 'mode used': r.get('mode used') or (r.get('chart') and 'chart') or 'replay',
                   'replays': r.get('replays'), 'accepted': r.get('accepted derivations'),
                   'candidate costs': r.get('candidate costs'), 'chosen': r.get('chosen'),
                   'mrs': r.get('mrs'), 'labels': r.get('labels'), 'chart': r.get('chart'),
                   'top1': last.get('top1'), 'n tokens': len(r.get('tokens') or []), 'seconds': time.time() - t0,
                   'steps': r.get('seconds')}
            o.write(json.dumps(rec, ensure_ascii=False) + '\n')
            o.flush()


def load_parses(source):
    recs = {}
    for f in sorted(glob.glob(os.path.join(OUT, source, 'parse-*.jsonl'))):
        for l in open(f):
            r = json.loads(l)
            recs[r['id']] = r
    return recs


def raw_features(r):
    """The ace_fallback.py features from a parse record (same order)."""
    import math
    top1 = r.get('top1') or {'leaf': [1.0], 'tree': [1.0]}
    l1, t1 = top1['leaf'] or [1.0], top1['tree'] or [1.0]
    costs = sorted(r.get('candidate costs') or [])
    margin = (costs[1] - costs[0]) if len(costs) > 1 else 10.0
    acc = int(r.get('accepted') or 0) if r.get('mode used') != 'chart' else 0
    return [math.log(min(l1) + 1e-9), math.log(min(t1) + 1e-9),
            sum(math.log(q + 1e-9) for q in l1) / len(l1), sum(math.log(q + 1e-9) for q in t1) / len(t1),
            math.log1p(r.get('replays') or 0), 1.0 if r.get('outcome') == 'accepted at first try' else 0.0,
            math.log1p(acc), min(margin, 10.0), math.log1p(len(l1)), 1.0 if not acc else 0.0]


def cmd_route(a):
    """Fit the router on all of dev (features as in ace_fallback.py), score the raw-text parses."""
    import pickle
    import numpy as np
    from ace_fallback import features, logreg
    run = json.load(open(os.path.join(ROOT, 'analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-current.json')))
    tags = pickle.load(open(os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl'), 'rb'))['items']
    cands = {}
    for l in open(os.path.join(ROOT, 'analysis/ace-fallback/dev-cands-current.jsonl')):
        r = json.loads(l)
        cands[r['id']] = r
    recs = [x for x in run['records'] if x['id'] in tags]
    X = np.array([features(x, cands.get(x['id']), tags[x['id']]) for x in recs])
    y = np.array([0 if str(x['same MRS']) == 'True' else 1 for x in recs])
    summary = {}
    for source in a.sources:
        P = load_parses(source)
        ids = sorted(P)
        Xt = np.array([raw_features(P[i]) for i in ids])
        score = logreg(X, y, Xt)
        replay_ok = [P[i].get('mode used') != 'chart' and int(P[i].get('accepted') or 0) > 0 for i in ids]
        rest = sorted([j for j in range(len(ids)) if replay_ok[j]], key=lambda j: -score[j])
        k = int(round(a.share * len(ids)))
        send = {ids[j] for j in range(len(ids)) if not replay_ok[j]} | {ids[j] for j in rest[:k]}
        with open(os.path.join(OUT, source, 'to-ace.txt'), 'w') as o:
            for i in ids:
                if i in send:
                    o.write(i + '\n')
        summary[source] = {'parsed records': len(ids), 'replay analysis': sum(replay_ok),
                           'chart only': sum(1 for i in ids if P[i].get('mode used') == 'chart' and P[i].get('mrs')),
                           'no analysis': sum(1 for i in ids if not P[i].get('mrs')),
                           'sent to ACE': len(send), 'of which least certain with a replay analysis': min(k, len(rest))}
        print(source, summary[source], flush=True)
    json.dump(summary, open(os.path.join(OUT, 'route.json'), 'w'), indent=1)


def cmd_ace(a):
    """Full ACE (first parse) on the routed sentences, as one tsdb profile per source."""
    import subprocess
    R = glob.glob(os.path.join(ROOT, 'data/profiles-2025/dev/*/relations'))[0]
    for source in a.sources:
        d = os.path.join(OUT, source)
        ids = [l.strip() for l in open(os.path.join(d, 'to-ace.txt')) if l.strip()]
        text = {json.loads(l)['id']: json.loads(l)['text'] for l in open(os.path.join(d, 'sample.jsonl'))}
        pdir = os.path.join(d, 'profiles')
        os.makedirs(pdir, exist_ok=True)
        # one profile per chunk, so ACE runs in parallel and a crash loses little
        chunks = [ids[i:i + a.chunk] for i in range(0, len(ids), a.chunk)]
        jobs = []
        for c, chunk in enumerate(chunks):
            prof = os.path.join(pdir, f'{source}-{c:03d}')
            if os.path.exists(os.path.join(prof, 'result')) and os.path.getsize(os.path.join(prof, 'parse')) > 0:
                continue
            txt = os.path.join(d, f'chunk-{c:03d}.txt')
            with open(txt, 'w') as o:
                for i in chunk:
                    o.write(text[i] + '\n')
            with open(os.path.join(d, f'chunk-{c:03d}.ids'), 'w') as o:
                o.write('\n'.join(chunk) + '\n')
            subprocess.run([os.path.join(ROOT, '.venv/bin/delphin'), 'mkprof', '--input', txt, '--relations', R, prof],
                           check=True, stdout=subprocess.DEVNULL)
            jobs.append(prof)
        procs = []
        for prof in jobs:
            while len([p for p in procs if p.poll() is None]) >= a.workers or _free_gb() < 12:
                import time
                time.sleep(5)
            log = open(prof + '.log', 'w')
            procs.append(subprocess.Popen([os.path.join(ROOT, '.venv/bin/delphin'), 'process', '-g', os.path.join(ROOT, 'data/ace/erg-2025.dat'),
                                           '--executable', '/home/olga/delphin/tools/ACE/ace-0.9.34/ace',
                                           f'--options=-1 --timeout={a.timeout} --max-chart-megabytes={a.mb} --max-unpack-megabytes={a.mb + 2000}',
                                           prof], stdout=log, stderr=log))
        for p in procs:
            p.wait()
        print(source, 'ACE profiles', len(chunks), flush=True)


def _free_gb():
    for l in open('/proc/meminfo'):
        if l.startswith('MemAvailable'):
            return int(l.split()[1]) / 1e6
    return 99


def cmd_silver(a):
    """Training records from ACE (routed sentences it parsed) and Orca (the rest with a replay analysis)."""
    import collections
    from delphin import tsdb, mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    from encode_treebank import entry_types, run_split
    from judged_training import orca_tokens
    report = {}
    os.makedirs(os.path.join(OUT, 'silver'), exist_ok=True)
    allrecs = []
    for source in a.sources:
        d = os.path.join(OUT, source)
        P = load_parses(source)
        sent = {l.strip() for l in open(os.path.join(d, 'to-ace.txt')) if l.strip()}
        # map profile items back to sample ids
        id_of = {}
        for idsf in sorted(glob.glob(os.path.join(d, 'chunk-*.ids'))):
            c = os.path.basename(idsf)[6:9]
            for n, i in enumerate(open(idsf).read().split()):
                id_of[(f'{source}-{c}', n + 1)] = i
        # ACE: encode, replay-check, forms as typed
        st, _ = run_split(os.path.join(d, 'profiles'), entry_types(os.path.join(ROOT, 'data/erg/2025')), os.path.join(d, 'ace-encoded.jsonl'))
        import subprocess
        subprocess.run([os.path.join(ROOT, '.venv/bin/python'), os.path.join(HERE, 'filter_replayable.py'), '--grammar', os.path.join(ROOT, 'data/erg/2025/english.tdl'),
                        '--profiles', os.path.join(d, 'profiles'), '--encoded', os.path.join(d, 'ace-encoded.jsonl'),
                        '--out-train', os.path.join(d, 'ace-replayable.jsonl'), '--out-held', os.path.join(d, 'ace-held.jsonl'),
                        '--stats', os.path.join(d, 'ace-filter.json'), '--hold', '0', '--workers', str(a.workers)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([os.path.join(ROOT, '.venv/bin/python'), os.path.join(HERE, 'surface_forms.py'), '--encoded', os.path.join(d, 'ace-replayable.jsonl'),
                        '--out', os.path.join(d, 'ace-train.jsonl'), '--profiles', os.path.join(d, 'profiles')],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ace_train = {}
        for l in open(os.path.join(d, 'ace-train.jsonl')):
            r = json.loads(l)
            prof, pid = r['id'].split('/')
            sid = id_of.get((prof, int(pid)))
            if sid:
                r['id'] = f'raw-{sid}'
                ace_train[sid] = r
        # ACE MRSs for agreement
        ace_mrs = {}
        for prof in glob.glob(os.path.join(d, 'profiles', '*')):
            if not os.path.isdir(prof):
                continue
            names = [f.name for f in tsdb.read_schema(prof)['result']]
            with tsdb.open(prof, 'result') as rows:
                for line in rows:
                    rec = tsdb.split(line)
                    sid = id_of.get((os.path.basename(prof), int(rec[names.index('parse-id')])))
                    if sid and rec[names.index('mrs')]:
                        ace_mrs[sid] = rec[names.index('mrs')]
        c = collections.Counter()
        for sid, r in P.items():
            c['sample'] += 1
            orca_ok = r.get('mode used') != 'chart' and int(r.get('accepted') or 0) > 0 and r.get('labels')
            if sid in sent:
                c['sent to ACE'] += 1
                if sid in ace_mrs:
                    c['ACE parsed'] += 1
                    if orca_ok and r.get('mrs'):
                        c['both Orca (replay) and ACE'] += 1
                        try:
                            same = M.is_isomorphic(normalized(simplemrs.decode(r['mrs'])), normalized(simplemrs.decode(ace_mrs[sid])), properties=False)
                        except Exception:
                            same = False
                        c['Orca same as ACE'] += bool(same)
                    elif r.get('mrs'):
                        c['chart only and ACE'] += 1
                if sid in ace_train:
                    allrecs.append(ace_train[sid])
                    c['silver from ACE'] += 1
                elif orca_ok:
                    allrecs.append({'id': f'raw-{sid}', 'tokens': orca_tokens(r['labels'])})
                    c['silver from Orca (ACE failed or not replayable)'] += 1
                else:
                    c['no silver'] += 1
            elif orca_ok:
                allrecs.append({'id': f'raw-{sid}', 'tokens': orca_tokens(r['labels'])})
                c['silver from Orca'] += 1
            else:
                c['no silver'] += 1
        c.update({f'ACE encode: {k}': v for k, v in st.items() if isinstance(v, int)})
        report[source] = dict(c)
        print(source, dict(c), flush=True)
    with open(os.path.join(OUT, 'silver', 'train.jsonl'), 'w') as o:
        for r in allrecs:
            o.write(json.dumps(r, ensure_ascii=False) + '\n')
    # assemble the new training folder
    os.makedirs(NEW_DIR, exist_ok=True)
    n_base = 0
    with open(os.path.join(NEW_DIR, 'train.jsonl'), 'w') as o:
        for l in open(BASE_TRAIN):
            o.write(l)
            n_base += 1
        for r in allrecs:
            o.write(json.dumps(r, ensure_ascii=False) + '\n')
    for s in ('dev', 'test'):
        t = os.path.join(NEW_DIR, f'{s}.jsonl')
        if not os.path.exists(t):
            os.symlink(f'../encoded-2025-bothall-surface/{s}.jsonl', t)
    report['train'] = {'base (encoded-2025-bothall-news25-surface)': n_base, 'new raw-text silver': len(allrecs), 'total': n_base + len(allrecs)}
    json.dump(report, open(os.path.join(OUT, 'silver', 'report.json'), 'w'), indent=1)
    open(os.path.join(NEW_DIR, 'README'), 'w').write(
        'train = encoded-2025-bothall-news25-surface/train.jsonl + raw-text silver from Gutenberg and Wikipedia '
        '(data/rawtext, scripts/rawtext.py): ACE\'s first parse where Orca was unsure and ACE parsed it, else Orca\'s accepted replay derivation; '
        'Redwoods dev/test sentences and Wikipedia articles containing them excluded.\n' + json.dumps(report, indent=1) + '\n')
    print(json.dumps(report['train']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('pool', 'parse', 'route', 'ace', 'silver'))
    ap.add_argument('--n', type=int, default=50000)
    ap.add_argument('--source', default='gutenberg')
    ap.add_argument('--sources', nargs='+', default=['gutenberg', 'wikipedia'])
    ap.add_argument('--shard', type=int, default=0)
    ap.add_argument('--shards', type=int, default=1)
    ap.add_argument('--tagger', default=os.path.join(ROOT, 'data/models/tagger-2025bothsurf-debertav3large'))
    ap.add_argument('--share', type=float, default=0.3)
    ap.add_argument('--chunk', type=int, default=500)
    ap.add_argument('--workers', type=int, default=6)
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--mb', type=int, default=16000)
    a = ap.parse_args()
    {'pool': cmd_pool, 'parse': cmd_parse, 'route': cmd_route, 'ace': cmd_ace, 'silver': cmd_silver}[a.cmd](a)


if __name__ == '__main__':
    main()
