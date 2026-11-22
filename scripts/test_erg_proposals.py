#!/usr/bin/env python3
"""Test proposed ERG changes (data/erg-proposals) on a copy of the ERG.

1. build: copy data/erg/2025 (without treebanks) to BUILD/src, append
   additions.tdl to its lexicon, apply retype.json, compile with ACE.
2. parse: the motivating sentences and a fixed random sample of dev
   sentences, with the original grammar and with the copy; per sentence the
   number of readings and the first-ranked MRS.
3. report: which motivating sentences now parse, and which dev sentences
   changed (readings or first MRS).

The ERG itself is never modified.

Usage: test_erg_proposals.py build|parse|report [--build DIR] [--n 300] [--workers 3]
"""
import argparse
import concurrent.futures
import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCA = os.path.join(HERE, '..')
ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
ERG = os.path.join(ORCA, 'data/erg/2025')
BASE_DAT = os.path.join(ORCA, 'data/ace/erg-2025.dat')
PROP = os.path.join(ORCA, 'data/erg-proposals')

MOTIVATING = [
    ('ecpa/2214708', "i'd love a laptop with a 17 in screen."),
    ('ecpa/2260208', 'I want to get a 17" monitor, probably a ViewSonic.'),
    ('ecpa/2273108', 'Have any notebooks with a 12 " screen for under $700.00?'),
    ('ecpa/2224708', 'I\'m looking for a Toshiba 12345 laptop with DVD drive, 17" monitor, and 20 gig or bigger disk drive.'),
    ('ecpa/2237908', 'I need a laptop with a couple gigs of storage and space for 512K of memory.'),
    ('ecpa/2301608', 'I would appreciate if you could inform me as soon as the new Nikon digital camera with 5 megapixel is available.'),
    ('gen-pilot1/1561', 'Hi team, just a quick heads-up that the Salesforce migration has been postponed until Monday.'),
    ('gen-round2/1501', 'Is the sauce vegan or merely vegetarian?'),
    ('gen-round2/409', 'He sat by the loch, sipping a dram of Laphroaig and watching the gloaming settle.'),
    ('gen-round2/189', 'Revelers douse one another with colored powder.'),
    ('ecpa/2242408', 'You advertize computers on your website.'),
    ('gen-round2/289', 'This quarter, our team will migrate the legacy monolith to microservices.'),
    ('gen-round3/597', 'Analysts now consider it likely that the two companies will merge.'),
    ('gen-pilot1/1837', 'Anyone who has lived in Chicago in January knows that the wind off the lake is cruel to the unprepared.'),
    ('ecpa/2219409', 'This got bust, so I got a Panasonic model instead.'),
    ('ecpa/2205908', 'What is the top of line digital camera that you sell?'),
    ('gen-pilot1/1523', 'He swaddled the baby in a soft muslin.'),
    ('gen-pilot1/1589', 'She ordered an ultrasound and a full bloodwork panel.'),
    ('gen-round2/1959', 'By 1960 the mill was producing specialty steels for bridges.'),
]


def build(a):
    src = os.path.join(a.build, 'src')
    if os.path.exists(src):
        shutil.rmtree(src)
    shutil.copytree(ERG, src, symlinks=True, ignore=shutil.ignore_patterns('tsdb', '*.dat', '.git', '*.grm'))
    with open(os.path.join(src, 'lexicon.tdl'), 'a', encoding='utf-8') as f:
        f.write('\n\n' + open(os.path.join(PROP, 'additions.tdl'), encoding='utf-8').read())
    retype = {k: v for k, v in json.load(open(os.path.join(PROP, 'retype.json'))).items() if not k.startswith('_')}
    lex = os.path.join(src, 'lexicon.tdl')
    text = open(lex, encoding='utf-8').read()
    for name, (old, new, _) in retype.items():
        text, n = re.subn(rf'^{re.escape(name)} := {re.escape(old)} &', f'{name} := {new} &', text, flags=re.M)
        assert n == 1, name
    open(lex, 'w', encoding='utf-8').write(text)
    dat = os.path.join(a.build, 'erg-proposals.dat')
    r = subprocess.run([ACE, '-g', os.path.join(src, 'ace/config.tdl'), '-G', dat], capture_output=True, text=True)
    open(os.path.join(a.build, 'compile.log'), 'w').write(r.stdout + r.stderr)
    print('compiled' if r.returncode == 0 and os.path.exists(dat) else 'COMPILE FAILED', dat)


def parse_one(args):
    dat, sent = args
    from delphin import ace
    try:
        with ace.ACEParser(dat, executable=ACE, cmdargs=['-1', '--timeout=60', '--max-chart-megabytes=4000',
                                                         '--max-unpack-megabytes=5000'], stderr=subprocess.DEVNULL) as p:
            res = p.interact(sent)
            rs = res.results()
            return {'readings': res.get('readings'), 'mrs': rs[0].get('mrs') if rs else None,
                    'derivation': rs[0].get('derivation') if rs else None, 'error': res.get('error') or None}
    except Exception as e:
        return {'readings': None, 'mrs': None, 'derivation': None, 'error': f'{type(e).__name__}: {e}'[:200]}


def dev_sample(n, seed=7):
    from delphin import itsdb
    items = []
    for prof in sorted(glob.glob(os.path.join(ORCA, 'data/profiles-2025/dev/*'))):
        if os.path.exists(os.path.join(prof, 'relations')):
            ts = itsdb.TestSuite(prof)
            items += [(f"{os.path.basename(prof)}/{r['i-id']}", r['i-input']) for r in ts['item']]
    random.Random(seed).shuffle(items)
    return items[:n]


def parse(a):
    dat = os.path.join(a.build, 'erg-proposals.dat')
    sents = [('motivating', i, s) for i, s in MOTIVATING] + [('dev', i, s) for i, s in dev_sample(a.n)]
    jobs = [(g, d, kind, i, s) for kind, i, s in sents for g, d in (('base', BASE_DAT), ('new', dat))]
    out = {}
    with concurrent.futures.ProcessPoolExecutor(a.workers) as ex:
        for (g, d, kind, i, s), r in zip(jobs, ex.map(parse_one, [(d, s) for g, d, kind, i, s in jobs], chunksize=4)):
            out.setdefault(f'{kind}|{i}', {'kind': kind, 'id': i, 'sentence': s})[g] = r
    json.dump(out, open(os.path.join(a.build, 'parses.json'), 'w'), indent=1, ensure_ascii=False)
    print('parsed', len(out))


def report(a):
    from delphin import mrs as M
    from delphin.codecs import simplemrs
    out = json.load(open(os.path.join(a.build, 'parses.json')))

    def same(x, y):
        if not x or not y:
            return x == y
        try:
            return M.is_isomorphic(simplemrs.decode(x), simplemrs.decode(y), properties=True)
        except Exception:
            return x == y
    mot, dev = [], {'n': 0, 'same readings and first MRS': 0, 'changed': []}
    for k, r in out.items():
        b, n = r['base'], r['new']
        if r['kind'] == 'motivating':
            mot.append({'id': r['id'], 'sentence': r['sentence'], 'readings before': b['readings'], 'readings after': n['readings'],
                        'uses a proposal': bool(n['derivation'] and re.search(
                            r'inch_abb_n|gig_n2|megapixel_n2|heads-up_n1|vegan_a1|loch_n1|reveler_n1|advertize_v1|migrate_v2|consider_v9|'
                            r'unprepared_n1|bust_a1|top_of_line_a1|muslin_n1|ultrasound_n1|steel_n1', n['derivation']))})
        else:
            dev['n'] += 1
            if b['readings'] == n['readings'] and same(b['mrs'], n['mrs']):
                dev['same readings and first MRS'] += 1
            else:
                dev['changed'].append({'id': r['id'], 'sentence': r['sentence'], 'readings': [b['readings'], n['readings']],
                                       'first MRS same': same(b['mrs'], n['mrs']), 'errors': [b['error'], n['error']]})
    res = {'motivating': mot, 'dev regression': dev}
    json.dump(res, open(os.path.join(ORCA, 'analysis/diagnosis/gaps1/proposals-test.json'), 'w'), indent=1, ensure_ascii=False)
    for m in mot:
        print(f"{m['id']:18} {str(m['readings before']):>5} -> {str(m['readings after']):>5}  {'uses proposal' if m['uses a proposal'] else ''}")
    print('dev', dev['n'], 'unchanged', dev['same readings and first MRS'])
    for c in dev['changed'][:20]:
        print('  changed', c['id'], c['readings'], c['first MRS same'], c['sentence'][:70])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('build', 'parse', 'report'))
    ap.add_argument('--build', default='/mnt/kesha/grammars/erg-proposals-build')
    ap.add_argument('--n', type=int, default=300)
    ap.add_argument('--workers', type=int, default=3)
    a = ap.parse_args()
    os.makedirs(a.build, exist_ok=True)
    {'build': build, 'parse': parse, 'report': report}[a.cmd](a)


if __name__ == '__main__':
    main()
