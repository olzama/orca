#!/usr/bin/env python3
"""Check the grammar changes proposed by the gap diagnosis against the ERG.

For each "missing lexical entry" proposal: does the ERG already have an entry
with that spelling (and, for particle verbs, that particle) of the proposed
type? Does the proposed type exist at all? For each "missing construction"
proposal: is there a rule that looks like it (by name)? Each proposal is
classified as confirmed gap / already in grammar / unclear.

The proposals (word, proposed type) are transcribed from
analysis/diagnosis/gaps1/results.jsonl (the free-text "fix" field).

Usage: check_gap_proposals.py [--erg data/erg/2025] [--out analysis/diagnosis/gaps1/proposals-check.json]
"""
import argparse
import collections
import json
import os
import re

# (item id, kind, spelling or construction, proposed type or rule, particle, note)
PROPOSALS = [
    ('ecpa/2205908', 'entry', 'top of line', 'aj_-_i-att_le', None, ''),
    ('ecpa/2214708', 'entry', 'in', 'n_-_c-meas-abb_le', None, 'inch'),
    ('ecpa/2214810', 'entry', '4', 'p_np_i_le', None, 'texting spelling of "for"'),
    ('ecpa/2219409', 'entry', 'bust', 'aj_-_i_le', None, 'broken'),
    ('ecpa/2237908', 'entry', 'gig', 'n_-_c-meas_le', None, 'gigabyte'),
    ('ecpa/2239508', 'construction', "g-dropped -in'", 'v_prp_olr variant', None, "lookin'"),
    ('ecpa/2239509', 'entry', 'whatta', None, None, 'what do/have'),
    ('ecpa/2242408', 'entry', 'advertize', 'v_np*_le', None, 'spelling variant'),
    ('ecpa/2260208', 'entry', '”', 'n_-_c-meas-abb_le', None, 'inch mark (ACE preprocessing turns " into ”)'),
    ('ecpa/2267708', 'entry', 'might', 'av_-_s-vp_le', None, '"might could"'),
    ('ecpa/2273108', 'entry', '”', 'n_-_c-meas-abb_le', None, 'inch mark'),
    ('ecpa/2287008', 'entry', 'portable', 'n_-_c_le', None, 'noun'),
    ('ecpa/2301608', 'entry', 'megapixel', 'n_-_c-meas_le', None, 'measure'),
    ('ws212/1000007201950', 'construction', 'gapping', 'gap', None, ''),
    ('ws212/1000007202040', 'construction', 'noun ellipsis after adjective', 'elid|ellip', None, ''),
    ('ws212/1000007401840', 'construction', 'gapping', 'gap', None, ''),
    ('ws212/1000007600090', 'construction', 'noun ellipsis in a from-to range', 'elid|ellip', None, ''),
    ('ws212/1000007600740', 'entry', 's.a.', None, None, 'see also'),
    ('gen-pilot1/1077', 'entry', 'knock', 'v_p-np_le', 'out', ''),
    ('gen-pilot1/1249', 'construction', 'gapping', 'gap', None, ''),
    ('gen-pilot1/1304', 'construction', 'unlike-category predicative coordination', 'j-n_crd|jpr-.*_crd|n-j_crd', None, 'AP and NP'),
    ('gen-pilot1/1523', 'entry', 'muslin', 'n_-_mc_le', None, ''),
    ('gen-pilot1/1561', 'entry', 'heads-up', 'n_cp_c-optc_le', None, 'with a that-clause'),
    ('gen-pilot1/1589', 'entry', 'ultrasound', 'n_-_mc_le', None, ''),
    ('gen-pilot1/1683', 'entry', 'line', 'v_p-np_le', 'up', ''),
    ('gen-pilot1/1837', 'entry', 'unprepared', 'n_-_c-pl-def_le', None, '"the unprepared"'),
    ('gen-round2/171', 'entry', 'heads-up', 'n_cp_c-optc_le', None, 'with a that-clause'),
    ('gen-round2/189', 'entry', 'reveler', 'n_-_c_le', None, 'US spelling'),
    ('gen-round2/289', 'entry', 'migrate', 'v_np_le', None, 'transitive'),
    ('gen-round2/409', 'entry', 'loch', 'n_-_c_le', None, ''),
    ('gen-round2/448', 'entry', "builder 's", 'aj_-_i-cmpd_le', None, "builder's tea"),
    ('gen-round2/1501', 'entry', 'vegan', 'aj_-_i_le', None, ''),
    ('gen-round2/1579', 'entry', 'hand', 'v_p-np_le', 'out', ''),
    ('gen-round2/1959', 'entry', 'steel', 'n_-_mc_le', None, 'mass-count'),
    ('gen-round3/597', 'entry', 'consider', 'v_np-prd_sor_le', None, 'raising'),
    ('gen-round3/1667', 'entry', 'pull', 'v_p_le', 'over', ''),
]

FILES = ('lexicon.tdl', 'ple.tdl', 'lexicon-rbst.tdl', 'gle.tdl', 'gle-gen.tdl')


def read_lexicon(erg):
    entries = []          # (name, type, orth tuple, compkey)
    pat = re.compile(r'^([^\s;:]+)\s*:=\s*([^\s&]+)\s*&(.*?)\]\s*\.\s*$', re.M | re.S)
    for f in FILES:
        p = os.path.join(erg, f)
        if not os.path.exists(p):
            continue
        text = open(p, encoding='utf-8').read()
        for m in re.finditer(r'^([^\s;:]+)\s*:=\s*([^\s&]+)\s*&(.*?)(?=^\S[^\n]*:=|\Z)', text, re.M | re.S):
            body = m.group(3)
            o = re.search(r'ORTH\s*<([^>]*)>', body)
            orth = tuple(x.lower() for x in re.findall(r'"((?:[^"\\]|\\.)*)"', o.group(1))) if o else ()
            ck = re.search(r'--COMPKEY\s+(\S+?)[,\s\]]', body)
            entries.append((m.group(1), m.group(2), orth, ck.group(1) if ck else None))
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--erg', default='data/erg/2025')
    ap.add_argument('--out', default='analysis/diagnosis/gaps1/proposals-check.json')
    a = ap.parse_args()
    entries = read_lexicon(a.erg)
    types = set()
    for f in ('letypes.tdl', 'lextypes.tdl'):
        types |= set(re.findall(r'^([^\s;:]+)\s*:=', open(os.path.join(a.erg, f), encoding='utf-8').read(), re.M))
    rules = re.findall(r'^([^\s;:]+)\s*:=', open(os.path.join(a.erg, 'constructions.tdl'), encoding='utf-8').read(), re.M)
    by_orth = collections.defaultdict(list)
    for name, t, orth, ck in entries:
        by_orth[' '.join(orth)].append((name, t, ck))
    out = []
    for iid, kind, what, typ, particle, note in PROPOSALS:
        rec = {'id': iid, 'kind': kind, 'proposal': what, 'type': typ, 'particle': particle, 'note': note}
        if kind == 'entry':
            key = what.replace('-', ' - ') if what == 'heads-up' else what
            have = by_orth.get(what.lower(), []) + (by_orth.get(key, []) if key != what else [])
            if what == 'heads-up':
                have += by_orth.get('heads-up', []) + by_orth.get('heads up', [])
            rec['existing'] = [f'{n} ({t}{", " + ck if ck else ""})' for n, t, ck in have]
            rec['type exists'] = (typ in types) if typ else None
            if particle:
                match = [n for n, t, ck in have if t == typ and ck and f'_{particle}_' in ck]
            else:
                match = [n for n, t, ck in have if t == typ]
            if match:
                rec['verdict'] = 'already in grammar'
                rec['why'] = 'entry exists: ' + ', '.join(match)
            elif typ and typ not in types:
                rec['verdict'] = 'unclear'
                rec['why'] = 'proposed type does not exist'
            elif typ is None:
                rec['verdict'] = 'unclear'
                rec['why'] = 'no type proposed (nonstandard form; a preprocessing or robustness question)'
            else:
                rec['verdict'] = 'confirmed gap'
                rec['why'] = 'no entry of this type for this spelling' + (f' with particle {particle}' if particle else '')
        else:
            like = [r for r in rules if re.search(typ, r)] if typ and '_olr' not in typ else []
            rec['similar rules'] = like
            if what == 'gapping':
                rec['verdict'] = 'confirmed gap'
                rec['why'] = 'no gapping rule (only relative-clause "modgap" rules)'
            elif what.startswith('noun ellipsis'):
                rec['verdict'] = 'confirmed gap'
                rec['why'] = 'no rule for an adjective heading an elliptical noun phrase'
            elif what.startswith('unlike'):
                rec['verdict'] = 'unclear'
                rec['why'] = 'the ERG has adjective-noun coordination rules (j-n_crd, n-j_crd); whether they cover AP and pronoun NP as a predicate needs a test'
            else:
                rec['verdict'] = 'unclear'
                rec['why'] = 'nonstandard spelling: preprocessing rather than grammar'
        out.append(rec)
    c = collections.Counter(r['verdict'] for r in out)
    json.dump({'counts': dict(c), 'proposals': out}, open(a.out, 'w'), indent=1, ensure_ascii=False)
    for r in out:
        print(f"{r['verdict']:20} {r['proposal']:28} {r['type'] or '':20} {r['why'][:90]}")
    print(dict(c))


if __name__ == '__main__':
    main()
