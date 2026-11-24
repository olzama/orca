#!/usr/bin/env python3
"""Chart parsing restricted to the tagger's lexical choices (supertagging, as in
Ninomiya et al. 2006 and Matsuzaki et al. 2007), using ACE itself.

For each sentence, the tagger's top lexical labels per token (lextype|lexrules|unaries,
from the cached tagger output of repair_bench.py) are turned into lexical entries with
Orca's lexicon lookup. Every other lexical entry that could match a word of the sentence
(native or generic) is disabled with ACE's -L option (a substring match on lexeme names,
so entries whose names contain an allowed name stay enabled), so ACE builds its chart, and ranks
with the ERG's MaxEnt model, only over the entries the tagger proposed.

ACE starts in about 0.04 s, so it is run once per sentence.

Usage:
    supertag_ace.py --ids FILE|all --out OUT.json [--k 5] [--min-prob 0.001] [--workers 3]
"""
import argparse
import json
import os
import pickle
import re
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
sys.path.insert(0, ROOT)
sys.setrecursionlimit(20000)
ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
DAT = os.path.join(ROOT, 'data/ace/erg-2025.dat')
ERG = os.path.join(ROOT, 'data/erg/2025')

_LX = _ORTH = _ALLGEN = _GOLD = None


def chart_index(lx):
    """For a Lexicon: orth word -> [(entry, all orth words)], and the set of generic entries."""
    import collections
    orth = collections.defaultdict(list)
    for (lt, o), names in lx.by_type_orth.items():
        ws = tuple(o.split())
        for w in set(ws):
            for n in names:
                orth[w].append((n, ws))
    return orth, {n for ns in lx.generic.values() for n in ns}


def _init(gold_dir):
    global _LX, _ORTH, _ALLGEN, _GOLD
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    from repair_bench import load_gold
    g = Grammar(os.path.join(ERG, 'english.tdl'))
    _LX = Lexicon(g, ERG)
    _ORTH, _ALLGEN = chart_index(_LX)
    _GOLD = load_gold(gold_dir) if gold_dir else {}


def allowed_and_disabled(item, k, min_prob, lx=None, orth=None, allgen=None):
    """Entries the tagger proposes (top k labels per token, probability >= min_prob after
    the first) and the entries to disable with ACE's -L. item: {'path', 'top'} as in
    orca_parse (path: the token lattice path; top: the tagger's k-best labels)."""
    _LX, _ORTH, _ALLGEN = (lx, orth, allgen) if lx is not None else (globals()['_LX'], globals()['_ORTH'], globals()['_ALLGEN'])
    words = [p[0].lower() for p in item['path']]
    allowed, unresolved = set(), 0
    for i, labels in enumerate(item['top']['leaf']):
        for j, (lab, _lp, prob) in enumerate(labels[:k]):
            if j > 0 and prob < min_prob:
                break
            lextype, rules, _ = (lab.split('|') + ['', ''])[:3]
            if lextype in ('<cont>', '<none>', ''):
                continue
            found = _LX.lookup([item['path'][i][0]], lextype.lower(), rules.split())
            if not found:
                unresolved += 1
            allowed.update(found)
    # every native entry that could surface over the sentence's words (or their stems)
    vocab = set(words)
    for w in words:
        for rule in _LX.undo:
            vocab.update(_LX.stems(w, rule))
        for (iw, rule), stems in _LX.irregular.items():
            if iw == w:
                vocab.update(stems)
    cand = set()
    for w in vocab:
        for name, ws in _ORTH.get(w, ()):
            if all(x in vocab for x in ws):
                cand.add(name)
    disabled = (cand | _ALLGEN) - allowed
    # ACE's -L disables every lexeme whose name occurs anywhere in the option string
    # (substring match), so a disabled name that contains an allowed one would also
    # disable the allowed one: keep such entries enabled.
    disabled = {d for d in disabled if not any(a in d for a in allowed)}
    return allowed, disabled, unresolved


LAST = {}       # timing of the latest restricted run: 'wall seconds' (the whole ACE process) and 'parse seconds' (ACE's own figure)


def _timed(p, wall):
    """Record how the latest ACE run's time splits: ACE reports its own parsing time on stderr
    ("NOTE: parsed 1 / 1 sentences, avg ..., time 0.00660s"); the rest is starting up and loading the grammar."""
    m = re.search(r'NOTE: parsed .*?time ([0-9.]+)s', p.stderr or '')
    LAST.clear()
    LAST.update({'wall seconds': wall, 'parse seconds': float(m.group(1)) if m else None})


def run_restricted(text, disabled, timeout=60, ace=ACE, dat=DAT, trees=False):
    """ACE's first-ranked analysis with the given lexemes disabled: (mrs, derivation, seconds);
    mrs and derivation are strings (derivation only with trees=True), None when ACE finds nothing."""
    cmd = [ace, '-g', dat, '-1', f'--timeout={timeout}', '--max-chart-megabytes=6000', '--max-unpack-megabytes=7000']
    if not trees:
        cmd.append('-T')
    if disabled:
        cmd += ['-L', ' '.join(sorted(disabled))]
    t1 = time.time()
    p = subprocess.run(cmd, input=text + '\n', capture_output=True, text=True, timeout=timeout + 30)
    secs = time.time() - t1
    _timed(p, secs)
    line = next((l for l in p.stdout.splitlines() if l.startswith('[')), None)
    if line is None:
        return None, None, secs
    if trees:
        i = line.find('] ; ')
        if i >= 0:
            return line[:i + 1].strip(), line[i + 4:].strip() or None, secs
    return line, None, secs


def run_restricted_nbest(text, disabled, n, timeout=60, ace=ACE, dat=DAT):
    """ACE's n best analyses with the given lexemes disabled, best first: [(maxent score, mrs, derivation), ...]
    (strings; empty when ACE finds nothing). The score is ACE's MaxEnt score of the parse (:ascore), read from
    ACE's [incr tsdb()] output; called directly, like run_restricted, so the long -L list stays one argument."""
    import re
    cmd = [ace, '-g', dat, '-n', str(max(1, n)), '--tsdb-stdout', f'--timeout={timeout}',
           '--max-chart-megabytes=6000', '--max-unpack-megabytes=7000']
    if disabled:
        cmd += ['-L', ' '.join(sorted(disabled))]
    t1 = time.time()
    p = subprocess.run(cmd, input=text + '\n', capture_output=True, text=True, timeout=timeout + 30)
    _timed(p, time.time() - t1)
    field = re.compile(r'\(:([a-z-]+) \. ?("(?:[^"\\]|\\.)*"|[^()"]*)\)')
    unq = lambda v: re.sub(r'\\(.)', r'\1', v[1:-1]) if v.startswith('"') else v.strip()
    out = []
    for block in re.split(r'(?=\(:result-id \. )', p.stdout)[1:]:
        f = {k: unq(v) for k, v in field.findall(block)}
        if f.get('mrs') and f.get('ascore'):
            try:
                out.append((float(f['ascore']), f['mrs'].strip(), (f.get('derivation') or '').strip() or None))
            except ValueError:
                continue
    return out


def parse_one(args):
    sid, item, k, min_prob, timeout = args
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    from compare_mrs import normalized
    t0 = time.time()
    allowed, disabled, unresolved = allowed_and_disabled(item, k, min_prob)
    prep = time.time() - t0
    mrs_line, _, ace_s = run_restricted(item['text'], disabled, timeout)
    same = None
    if mrs_line and sid in _GOLD:
        try:
            same = bool(M.is_isomorphic(normalized(simplemrs.decode(mrs_line)), _GOLD[sid], properties=False))
        except Exception:
            same = False
    return sid, {'parsed': bool(mrs_line), 'same MRS': same, 'allowed': len(allowed), 'disabled': len(disabled),
                 'unresolved labels': unresolved, 'prep seconds': prep, 'ace seconds': ace_s, 'mrs': mrs_line}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl'))
    ap.add_argument('--gold', default=os.path.join(ROOT, 'data/profiles-2025/dev'))
    ap.add_argument('--ids', default='all', help='file with one sentence id per line, or "all"')
    ap.add_argument('--out', required=True)
    ap.add_argument('--k', type=int, default=5)
    ap.add_argument('--min-prob', type=float, default=0.001)
    ap.add_argument('--timeout', type=int, default=60)
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    items = pickle.load(open(a.cache, 'rb'))['items']
    ids = list(items) if a.ids == 'all' else [l.strip() for l in open(a.ids) if l.strip()]
    jobs = [(i, items[i], a.k, a.min_prob, a.timeout) for i in ids if items.get(i) and items[i].get('top')]
    out, t0 = {}, time.time()
    with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(a.gold,)) as ex:
        for n, (sid, r) in enumerate(ex.map(parse_one, jobs, chunksize=4)):
            out[sid] = r
            if n % 100 == 0:
                print(n, round(time.time() - t0), flush=True)
    s = {'sentences': len(out), 'parsed': sum(r['parsed'] for r in out.values()),
         'same MRS': sum(bool(r['same MRS']) for r in out.values()),
         'ace seconds per sentence': sum(r['ace seconds'] for r in out.values()) / max(1, len(out)),
         'prep seconds per sentence': sum(r['prep seconds'] for r in out.values()) / max(1, len(out)),
         'k': a.k, 'min_prob': a.min_prob, 'wall seconds': time.time() - t0}
    json.dump({'summary': s, 'records': out}, open(a.out, 'w'))
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    main()
