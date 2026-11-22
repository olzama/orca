#!/usr/bin/env python3
"""Sentences ACE could not parse but Orca analyzes: why ACE failed, and whether
Orca's reading is right.

Candidates are those of diagnose_rejections.py gaps: dev items without a gold
analysis, dev items ACE fails on, and generated sentences ACE could not parse.

  beyond_ace.py collect --out DIR     Orca on each candidate (tagger on CPU); for those Orca
                                      analyzes, ACE again with generous limits
  beyond_ace.py judge --out DIR       Claude Opus: is Orca's reading a correct analysis?
  beyond_ace.py score --out DIR       table by source, ACE outcome and verdict
"""
import argparse
import collections
import concurrent.futures
import glob
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

TAGGER = 'data/models/tagger-2025bothsurf-debertav3large'
ACE_LIMITS = {'timeout': 300, 'chart_mb': 6000, 'unpack_mb': 6000}   # lowered from 12000/12000: GPU training shares the machine's RAM
ACE_OPTS = ['-1', f"--timeout={ACE_LIMITS['timeout']}", f"--max-chart-megabytes={ACE_LIMITS['chart_mb']}", f"--max-unpack-megabytes={ACE_LIMITS['unpack_mb']}"]
MIN_FREE_GB = 12


def candidates():
    from delphin import itsdb
    cands = []
    ace_dev = json.load(open('analysis/mrs/dev-ace-final-as-eval.json'))['records']
    ace_fail = {r['id'] for r in ace_dev if not r.get('mrs')}
    for p in sorted(glob.glob('data/profiles-2025/dev/*/')):
        name = p.rstrip('/').split('/')[-1]
        ts = itsdb.TestSuite(p)
        items = {r['i-id']: r['i-input'] for r in ts['item']}
        nogold = {r['i-id'] for r in ts['parse'] if r['readings'] == 0}
        for iid, text in items.items():
            sid = f'{name}/{iid}'
            if iid in nogold:
                cands.append(('dev, no gold', sid, text))
            elif sid in ace_fail:
                cands.append(('dev, ACE fails', sid, text))
    for rnd in ('pilot1', 'round2', 'round3'):
        for p in glob.glob(f'data/generated/{rnd}/profiles/*/'):
            ts = itsdb.TestSuite(p)
            items = {r['i-id']: r['i-input'] for r in ts['item']}
            for r in ts['parse']:
                if r['readings'] == 0:
                    cands.append(('generated', f'gen-{rnd}/{r["i-id"]}', items[r['i-id']]))
    return cands


def ace_rerun(text):
    """ACE with generous limits: 'parsed', 'time limit', 'memory limit', or 'no parse'."""
    from orca_parse import DEFAULTS
    try:
        p = subprocess.run([DEFAULTS['ace'], '-g', DEFAULTS['dat'], *ACE_OPTS], input=text + '\n',
                           capture_output=True, text=True, timeout=420)
        out, err = p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return {'outcome': 'time limit', 'note': 'killed after 420 s', 'mrs': None}
    mrs = None
    m = re.search(r'^SENT: .*?\n(.+?)\s*;\s*\(', out, re.S | re.M)
    if '[ LTOP:' in out or '[ TOP:' in out:
        s = out[out.find('['):]
        depth, end = 0, None
        for i, ch in enumerate(s):
            depth += ch == '['
            depth -= ch == ']'
            if depth == 0:
                end = i + 1
                break
        mrs = s[:end] if end else None
    low = err.lower()
    if mrs:
        outcome = 'parsed'
    elif 'timed out' in low or 'timeout' in low:
        outcome = 'time limit'
    elif 'ram limit' in low or 'memory' in low or 'too many edges' in low:
        outcome = 'memory limit'
    else:
        outcome = 'no parse'
    return {'outcome': outcome, 'note': err.strip().splitlines()[-1][:200] if err.strip() else '', 'mrs': mrs}


def free_gb():
    for line in open('/proc/meminfo'):
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) / 1024 / 1024
    return 0


def collect(a):
    """Orca first (cached in orca.jsonl), then ACE one sentence at a time (cached in ace.jsonl), each
    started only when at least MIN_FREE_GB of memory is available; items.jsonl joins the two."""
    import time
    from delphin.codecs import simplemrs
    from delphin import mrs as M
    from compare_mrs import normalized
    from llm_rank import facts
    os.makedirs(a.out, exist_ok=True)
    of, af = os.path.join(a.out, 'orca.jsonl'), os.path.join(a.out, 'ace.jsonl')
    if not os.path.exists(of):
        from orca_parse import Parser
        cands = candidates()
        print(len(cands), 'candidates', flush=True)
        P = Parser(tagger=TAGGER, device='cpu')
        with open(of + '.tmp', 'w') as f:
            for kind, sid, text in cands:
                try:
                    out = P.parse(text, sid)
                except Exception:
                    continue
                m = out.pop('_mrs_obj', None)
                out.pop('_fs', None)
                if not out.get('accepted derivations') or m is None:
                    continue
                f.write(json.dumps({'kind': kind, 'id': sid, 'sentence': text, 'mrs': out['mrs'],
                                    'facts': sorted(facts(normalized(m)).elements())}, ensure_ascii=False) + '\n')
                f.flush()
        os.rename(of + '.tmp', of)
    got = [json.loads(l) for l in open(of)]
    print(len(got), 'analyzed by Orca', flush=True)
    done = {}
    if os.path.exists(af):
        done = {r['id']: r for r in map(json.loads, open(af))}
    with open(af, 'a') as f:
        for g in got:
            if g['id'] in done:
                continue
            while free_gb() < MIN_FREE_GB:
                print(f'waiting: {free_gb():.1f} GB available', flush=True)
                time.sleep(60)
            r = ace_rerun(g['sentence'])
            r.update({'id': g['id'], 'limits': dict(ACE_LIMITS)})
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            f.flush()
            done[g['id']] = r
            print(g['id'], r['outcome'], flush=True)
    for g in got:
        r = done[g['id']]
        g['ace'], g['ace_note'], g['ace_mrs'], g['ace_limits'] = r['outcome'], r['note'], r['mrs'], r['limits']
        if r['mrs']:
            try:
                g['same_as_ace'] = bool(M.is_isomorphic(normalized(simplemrs.decode(g['mrs'])),
                                                        normalized(simplemrs.decode(r['mrs'])), properties=False))
            except Exception:
                g['same_as_ace'] = None
    with open(os.path.join(a.out, 'items.jsonl'), 'w') as f:
        for g in got:
            f.write(json.dumps(g, ensure_ascii=False) + '\n')
    print(json.dumps(collections.Counter((g['kind'], g['ace']) for g in got).most_common()), flush=True)


SYSTEM = """You judge one semantic analysis of an English sentence, produced by the English Resource Grammar. The analysis is shown as predicates (node ...) and links (head -ROLE-> dependent). Predicate names are lemma_partofspeech_sense (n noun, v verb, a adjective or adverb, p preposition, q quantifier, c conjunction); ARG1, ARG2 ... are argument roles; /EQ and /H mark links that share a label or go through a scope relation; compound, appos, implicit_conj, udef_q, generic_entity, unknown and similar are grammar-internal predicates. Some sentences are ill-formed (typos, missing words); judge whether the analysis captures what the writer evidently meant. Answer RIGHT if it is a correct analysis, PARTLY if its main predicate-argument structure is right but some part is wrong (a misattached modifier, a wrong word sense, a wrong reading of one phrase), WRONG if the main structure is wrong. Answer with one line per sentence, "N: X | reason", where X is RIGHT, PARTLY or WRONG and the reason is at most 15 words. No other text."""


def prompt(batch):
    parts = []
    for i, it in enumerate(batch, 1):
        parts.append(f'Sentence {i}: {it["sentence"]}')
        parts.append('  Analysis: ' + '; '.join(it['facts']))
        parts.append('')
    return '\n'.join(parts)


def judge(a):
    from llm_label import call
    items = [json.loads(l) for l in open(os.path.join(a.out, 'items.jsonl'))]
    batches = [items[i:i + 5] for i in range(0, len(items), 5)]

    def one(batch):
        r = call(a.model, SYSTEM, prompt(batch), a.out)
        verdict = {}
        for line in str(r.get('result', '')).splitlines():
            m = re.match(r'\s*(\d+)\s*:\s*(RIGHT|PARTLY|WRONG)\s*\|?\s*(.*)', line)
            if m and 1 <= int(m.group(1)) <= len(batch):
                verdict[batch[int(m.group(1)) - 1]['id']] = (m.group(2), m.group(3).strip())
        return verdict, r.get('total_cost_usd', 0) or 0
    out, cost = {}, 0.0
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        for v, c in ex.map(one, batches):
            out.update(v)
            cost += c
    json.dump({'verdicts': out, 'cost_usd': cost, 'calls': len(batches), 'model': a.model},
              open(os.path.join(a.out, 'verdicts.json'), 'w'), indent=1, ensure_ascii=False)
    print(len(out), 'judged', f'${cost:.2f}')


def score(a):
    items = [json.loads(l) for l in open(os.path.join(a.out, 'items.jsonl'))]
    v = json.load(open(os.path.join(a.out, 'verdicts.json')))
    table = collections.defaultdict(collections.Counter)
    for it in items:
        verdict = v['verdicts'].get(it['id'], ['not judged'])[0]
        for key in (it['kind'], 'all'):
            t = table[key]
            t['n'] += 1
            t['ACE ' + it['ace']] += 1
            t[verdict] += 1
            if it.get('same_as_ace') is not None:
                t['ACE parsed, same MRS as Orca'] += bool(it['same_as_ace'])
    out = {'by source': {k: dict(t) for k, t in table.items()}, 'cost_usd': v['cost_usd']}
    json.dump(out, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('collect', 'judge', 'score'))
    ap.add_argument('--out', default='analysis/beyond-ace')
    ap.add_argument('--model', default='claude-opus-5-5')
    a = ap.parse_args()
    {'collect': collect, 'judge': judge, 'score': score}[a.cmd](a)


if __name__ == '__main__':
    main()
