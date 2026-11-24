#!/usr/bin/env python3
"""Roadmap O96: does the LLM judge get closer to a person with neutral paraphrases
and ERG documentation of the predicates that differ?

Gold: 60 Redwoods dev sentences where ACE's first parse differs from gold, judged
blind by a person (analysis/judge-check/ and analysis/judge-check2/: cases.json,
key.json, olga-verdicts.json; paraphrases in interpretations.json). Readings are
given in the same A/B order the person saw; the model is told nothing about who
produced which.

Variants (same system prompt as scripts/adjudicate.py, extended per variant):
  1  facts only (the original judge's input)
  2  facts + the two neutral paraphrases
  3  facts + paraphrases + ERG documentation for every predicate found in only one
     reading: lexical types of its entries (lexicon.tdl) with the type's docstring
     and examples (letypes.tdl); a one-line gloss for grammar-internal predicates
  4  variant 3 run three times (run 1 is variant 3; runs 2-3 in shuffled case order),
     majority vote (ties broken by run 1)

Usage:
    judge_variants.py run   [--parallel 3]   -> analysis/judge-variants/calls-*.jsonl
    judge_variants.py score                  -> analysis/judge-variants/score.json
"""
import argparse
import collections
import concurrent.futures
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCA = os.path.dirname(HERE)
sys.path.insert(0, HERE)
OUT = os.path.join(ORCA, 'analysis', 'judge-variants')
SETS = (('set1', 'analysis/judge-check'), ('set2', 'analysis/judge-check2'))
ERG = os.path.join(ORCA, 'data', 'erg', '2025')

SYSTEM = """You judge two semantic analyses of the same English sentence, produced by the English Resource Grammar. Each reading is shown only by what it has and the other lacks: predicates (node ...) and links (head -ROLE-> dependent). Predicate names are lemma_partofspeech_sense (n noun, v verb, a adjective or adverb, p preposition, q quantifier, c conjunction); ARG1, ARG2 ... are argument roles; /EQ and /H mark links that share a label or go through a scope relation; compound, appos, implicit_conj, udef_q, generic_entity, unknown and similar are grammar-internal predicates. Decide which reading is a correct analysis of the sentence as a careful human reader understands it. Answer A or B if exactly one is correct, BOTH if both are acceptable readings of this sentence, NEITHER if both are wrong. Answer with one line per sentence, "N: X", where N is the sentence number and X is A, B, BOTH or NEITHER. No other text."""

EXTRA = {
    2: "\nEach reading also comes with a plain-English paraphrase written by an assistant from the same facts; it can be wrong, so check it against the facts.",
    3: "\nEach reading also comes with a plain-English paraphrase written by an assistant from the same facts (it can be wrong, so check it against the facts), and with the grammar's own documentation of the predicates that occur in only one reading: the lexical types of the words that carry them, with the grammar writer's description and example sentences, or a short gloss for grammar-internal predicates.",
}

# One-line glosses for grammar-internal (non-lexical) predicates.
GLOSS = {
    'udef_q': 'implicit quantifier of a bare noun phrase (no determiner)', 'proper_q': 'quantifier of a proper name',
    'pronoun_q': 'quantifier of a pronoun', 'def_explicit_q': 'definite quantifier from a possessive', 'def_implicit_q': 'implicit definite quantifier',
    'number_q': 'quantifier of a number used as a noun phrase', 'idiom_q_i': 'quantifier inside an idiom', 'free_relative_q': 'quantifier of a free relative (what/whatever ...)',
    'which_q': 'quantifier of a wh-phrase', 'every_q': 'quantifier "every"',
    'compound': 'noun-noun compound: ARG1 the head noun, ARG2 the modifier noun', 'appos': 'apposition: ARG1 and ARG2 refer to the same thing',
    'implicit_conj': 'coordination without a conjunction word (list or comma)', 'generic_entity': 'an unexpressed or generic thing (e.g. the head of "the rich", "half")',
    'unknown': 'a fragment that is not a full sentence; ARG is its content', 'loc_nonsp': 'unspecified location or time relation (bare temporal or locative)',
    'part_of': 'partitive: ARG1 is part of the group ARG2 (e.g. "some of the X")', 'much-many_a': 'the quantity sense of much/many/more/less',
    'more_comp': 'comparative "more/-er": ARG1 is compared', 'neg': 'negation', 'subord': 'subordinate clause linking (ARG1 main, ARG2 subordinate)',
    'nominalization': 'a verb phrase used as a noun (gerund)', 'eventuality': 'an unexpressed event (e.g. in an infinitival relative)',
    'with_p': 'implicit "with" relation (instrument or accompaniment)', 'pron': 'pronoun', 'named': 'a proper name', 'card': 'cardinal number',
    'ord': 'ordinal number', 'time_n': 'implicit time noun', 'place_n': 'implicit place noun', 'person': 'implicit person noun', 'thing': 'implicit thing noun',
    'poss': 'possession (ARG1 possessed, ARG2 possessor)', 'measure': 'measure phrase', 'times': 'multiplication', 'plus': 'addition',
    'comp': 'comparison', 'superl': 'superlative', 'abstr_deg': 'abstract degree', 'id': 'identity', 'be_v_id': 'copula of identity: ARG1 is (the same as) ARG2', 'be_v_nv': 'copula with a non-verbal predicate', 'be_v_there': 'existential there-be', 'parenthetical': 'a parenthetical attached to ARG1', 'named_n': 'a name used as a common noun', 'un-_a_neg': 'the prefix un- (not)', 'colon_p_namely': 'a colon read as "namely": ARG2 specifies ARG1', 'colon_v_id': 'a colon read as identity: ARG1 is ARG2', 'parg_d': 'passive argument link',
    'focus_d': 'focus marking', 'temp_loc_x': 'temporal location', 'unspec_manner': 'unspecified manner', 'elliptical_n': 'elided noun',
    'ellipsis_ref': 'reference to an elided verb phrase', 'interval': 'interval', 'interval_p_start': 'start of an interval', 'interval_p_end': 'end of an interval',
    'mofy': 'month of the year', 'dofw': 'day of the week', 'yofc': 'year', 'numbered_hour': 'clock hour', 'fraction': 'fraction',
    'plus-minus': 'plus or minus', 'manner': 'manner', 'reason': 'reason', 'property': 'property', 'cop_id': 'identity copula',
    'relative_mod': 'relative modifier', 'v_event': 'unspecified verb event', 'unspec_adj': 'unspecified adjective', 'minute': 'minute',
}


def load_lexicon():
    """PRED name (without _rel) -> [(entry, type)], and type -> docstring."""
    by_pred = collections.defaultdict(list)
    text = open(os.path.join(ERG, 'lexicon.tdl'), encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'^(\S+) := (\S+)\s*&(.*?)\]\s*\.\s*$', text, re.M | re.S):
        p = re.search(r'KEYREL\.PRED\s+"?([^",\s\]]+)"?', m.group(3))
        if p:
            by_pred[p.group(1).lower().removesuffix('_rel').lstrip('_')].append((m.group(1), m.group(2)))
    docs = {}
    for f in ('letypes.tdl', 'lextypes.tdl'):
        lt = open(os.path.join(ERG, f), encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'^(\S+) := [^\n]*\n\s*"""(.*?)"""', lt, re.M | re.S):
            docs.setdefault(m.group(1), ' '.join(m.group(2).split()))
    return by_pred, docs


def preds_of(facts):
    out = []
    for f in facts:
        for tok in re.split(r'\s+-\S+->\s+|\s+', f):
            tok = tok.strip()
            if not tok or tok == 'node' or tok.startswith('-'):
                continue
            tok = tok.split('/')[0] if '/' in tok and not tok.startswith('"') else tok
            out.append(tok)
    return out


def documentation(case, by_pred, docs):
    """Lines documenting predicates that occur in one reading only."""
    seen, lines = set(), []
    for r in 'AB':
        for p in [f[5:] for f in case[r] if f.startswith('node ')]:      # predicates found in this reading only
            p = re.sub(r'\(".*"\)$', '', p).split('/')[0]
            if p in seen:
                continue
            seen.add(p)
            if p in GLOSS:
                lines.append(f'    {p}: {GLOSS[p]}')
                continue
            if p.endswith('_p_state'):
                lines.append(f'    {p}: the preposition "{p.split("_")[0]}" in its state sense: ARG1 is in that state or relation to ARG2 (e.g. "in use", "by hand")')
                continue
            ents = by_pred.get(p, [])
            if not ents:
                lines.append(f'    {p}: (no lexical entry; grammar-internal or unknown word)')
                continue
            types = []
            for _, t in ents:
                if t not in types:
                    types.append(t)
            words = sorted({re.sub(r'_[a-z0-9]+$', '', e) for e, _ in ents})[:3]
            for t in types[:3]:
                lines.append(f'    {p} ({", ".join(words)}; type {t}): {docs.get(t, "(no description)")}')
    return lines


def load_cases():
    by_pred, docs = load_lexicon()
    cases = []
    for name, d in SETS:
        cs = {c['id']: c for c in json.load(open(os.path.join(ORCA, d, 'cases.json')))}
        interp = json.load(open(os.path.join(ORCA, d, 'interpretations.json')))['by_id']
        key = json.load(open(os.path.join(ORCA, d, 'key.json')))
        for row in json.load(open(os.path.join(ORCA, d, 'olga-verdicts.json')))['by_case']:
            cid, verdict = row[0], row[2]
            by = row[3] if len(row) > 4 else 'olga'
            c = cs[cid]
            target = {'ACE': key[cid]['ace'], 'gold': key[cid]['gold'], 'both': 'BOTH', 'neither': 'NEITHER'}.get(verdict, verdict.upper())
            cases.append({'id': cid, 'set': name, 'by': by, 'person': target, 'person verdict': verdict,
                          'sentence': c['sentence'], 'A': c['A'], 'B': c['B'], 'interp': interp.get(cid, {}),
                          'doc': documentation(c, by_pred, docs)})
    return cases


def prompt(batch, variant):
    parts = []
    for i, c in enumerate(batch, 1):
        parts.append(f'Sentence {i}: {c["sentence"]}')
        for L in 'AB':
            parts.append(f'  Reading {L}: ' + ('; '.join(c[L]) if c[L] else '(nothing beyond what both share)'))
            if variant >= 2 and c['interp'].get(L):
                parts.append(f'    Paraphrase of {L}: {c["interp"][L]}')
        if variant >= 3 and c['doc']:
            parts.append('  Grammar documentation of predicates found in only one reading:')
            parts += c['doc']
        parts.append('')
    return '\n'.join(parts)


def run(a):
    from llm_label import call
    cases = load_cases()
    os.makedirs(OUT, exist_ok=True)
    json.dump(cases, open(os.path.join(OUT, 'cases.json'), 'w'), indent=1, ensure_ascii=False)
    jobs = []
    for name, variant, seed in (('v1', 1, None), ('v2', 2, None), ('v3', 3, None), ('v3-run2', 3, 2), ('v3-run3', 3, 3)):
        order = list(cases)
        if seed:
            random.Random(seed).shuffle(order)
        for i in range(0, len(order), a.batch):
            jobs.append((name, variant, order[i:i + a.batch]))

    def go(job):
        name, variant, batch = job
        try:
            data = call(a.model, SYSTEM + EXTRA.get(variant, ''), prompt(batch, variant), OUT)
            text = data.get('result') or ''
        except Exception as e:
            data, text = {'error': str(e)[:300]}, ''
        ans = {}
        for m in re.finditer(r'^\s*(\d+)\s*:\s*(A|B|BOTH|NEITHER)\b', text, re.M):
            k = int(m.group(1)) - 1
            if 0 <= k < len(batch):
                ans[batch[k]['id']] = m.group(2)
        return name, {'ids': [c['id'] for c in batch], 'answers': ans, 'raw': text[:2000], 'cost_usd': data.get('total_cost_usd'), 'error': data.get('error')}

    with concurrent.futures.ThreadPoolExecutor(a.parallel) as ex:
        for name, rec in ex.map(go, jobs):
            with open(os.path.join(OUT, f'calls-{name}.jsonl'), 'a') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            print(name, len(rec['answers']), 'of', len(rec['ids']), flush=True)


def score(a):
    cases = json.load(open(os.path.join(OUT, 'cases.json')))
    ans, cost = {}, collections.Counter()
    for name in ('v1', 'v2', 'v3', 'v3-run2', 'v3-run3'):
        ans[name] = {}
        for l in open(os.path.join(OUT, f'calls-{name}.jsonl')):
            r = json.loads(l)
            ans[name].update(r['answers'])
            cost[name] += r.get('cost_usd') or 0.0
    ans['v4'] = {}
    for c in cases:
        votes = [ans[n].get(c['id']) for n in ('v3', 'v3-run2', 'v3-run3') if ans[n].get(c['id'])]
        if votes:
            top = collections.Counter(votes).most_common()
            ans['v4'][c['id']] = top[0][0] if len(top) == 1 or top[0][1] > top[1][1] else votes[0]

    def agree(j, p, lenient):
        if j is None:
            return False
        if j == p:
            return True
        return lenient and ((j == 'BOTH' and p in 'AB') or (p == 'BOTH' and j in 'AB'))

    res = {}
    for v in ('v1', 'v2', 'v3', 'v4'):
        res[v] = {}
        for subset, keep in (('all 60', lambda c: True), ('set 1 (judge had preferred ACE)', lambda c: c['set'] == 'set1'),
                             ('set 2 (judge had preferred gold)', lambda c: c['set'] == 'set2'), ('without the 3 decided by Claude', lambda c: c['by'] != 'claude')):
            cs = [c for c in cases if keep(c)]
            res[v][subset] = {'cases': len(cs), 'answered': sum(1 for c in cs if c['id'] in ans[v]),
                              'exact': sum(agree(ans[v].get(c['id']), c['person'], False) for c in cs),
                              'lenient': sum(agree(ans[v].get(c['id']), c['person'], True) for c in cs)}
        res[v]['answers'] = dict(collections.Counter(ans[v].values()))
    disagree = [{'id': c['id'], 'set': c['set'], 'sentence': c['sentence'], 'person': c['person'],
                 **{v: ans[v].get(c['id']) for v in ('v1', 'v2', 'v3', 'v4')}}
                for c in cases if len({ans[v].get(c['id']) for v in ('v1', 'v2', 'v3', 'v4')}) > 1]
    out = {'variants': {'v1': 'facts only (original judge)', 'v2': '+ paraphrases', 'v3': '+ paraphrases + ERG documentation',
                        'v4': 'v3 three times, majority'},
           'results': res, 'cost_usd': dict(cost), 'cost_usd total': round(sum(cost.values()), 2), 'variants disagree': disagree,
           'note': '60 cases: a difference of about 12 points or less between variants is not evidence.'}
    json.dump(out, open(os.path.join(OUT, 'score.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({v: res[v] for v in res}, indent=1))
    print('cost', out['cost_usd total'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('run', 'score', 'show'))
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--parallel', type=int, default=3)
    ap.add_argument('--model', default='claude-opus-5-5')
    a = ap.parse_args()
    if a.cmd == 'show':
        cs = load_cases()
        print(prompt(cs[:2], 3))
        return
    {'run': run, 'score': score}[a.cmd](a)


if __name__ == '__main__':
    main()
