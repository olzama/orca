#!/usr/bin/env python3
"""Ask Claude for simple Hausa sentences built from HaG's own lexicon, in plain
spelling (no tone or length marks, as HaG's input expects), to measure how many
of ACE's HaG parses Orca replays.

Usage: hausa_sentences.py --grammar-dir HAG --out DIR [--calls 4] [--per-call 50]
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_label import call  # noqa: E402

SYSTEM = 'You write test sentences for a computational grammar of Hausa. Output only the sentences, one per line.'


def vocabulary(gdir):
    pat = re.compile(r'^([^\s;:]+)\s*:=\s*([^\s&]+)\s*&(.*?)\]\s*\.\s*$', re.M | re.S)
    out = []
    for name in sorted(os.listdir(gdir)):
        if name != 'lexicon.tdl':            # the only lexicon file HaG's build loads
            continue
        text = open(os.path.join(gdir, name), encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'^([^\s;:]+)\s*:=\s*([^\s&]+)\s*&(.*?)\.\s*$', text, re.M | re.S):
            stem = re.search(r'STEM\s*<\s*"([^"]+)"', m.group(3))
            pred = re.search(r'PRED\s*"_[^_"]+_([a-z]+)_([^"]*?)_rel"', m.group(3))
            if stem:
                gloss = pred.group(2) if pred else ''
                out.append(f'{stem.group(1)}\t{m.group(2)}\t{gloss}')
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar-dir', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--calls', type=int, default=4)
    ap.add_argument('--per-call', type=int, default=50)
    ap.add_argument('--model', default='claude-sonnet-5-5')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    vocab = vocabulary(a.grammar_dir)
    focus = ['statements in the completive and continuous aspects, with pronoun subjects and noun subjects',
             'transitive verbs with noun and pronoun objects, possessives (linker -n/-r), adjectives',
             'negation, yes-no questions and wh-questions (wa, me, ina)',
             'future and subjunctive aspects, plural nouns, numbers, prepositional phrases']
    prompt = lambda i: (f'Write {a.per_call} short, natural Hausa sentences (3 to 8 words), each different, focusing on '
                        f'{focus[i % len(focus)]}.\nUse only words from this vocabulary of the grammar (stem, lexical type, '
                        'English gloss), inflected as Hausa requires, plus pronouns and aspect markers.\n'
                        'Write in plain standard spelling WITHOUT tone or vowel-length marks (hooked letters ɓ ɗ ƙ and \' are fine). '
                        'No translations, no numbering.\n\n' + '\n'.join(vocab))
    with concurrent.futures.ThreadPoolExecutor(4) as ex:
        res = list(ex.map(lambda i: call(a.model, SYSTEM, prompt(i), a.out), range(a.calls)))
    sents, seen = [], set()
    with open(os.path.join(a.out, 'calls.jsonl'), 'w') as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
            for line in str(r.get('result', '')).splitlines():
                s = re.sub(r'^\s*(\d+[.)]\s*|[-*]\s*)', '', line).strip()
                if s and s.lower() not in seen and len(s.split()) <= 15:
                    seen.add(s.lower()); sents.append(s)
    open(os.path.join(a.out, 'sentences.txt'), 'w').write('\n'.join(sents) + '\n')
    print(json.dumps({'vocabulary': len(vocab), 'sentences': len(sents)}))


if __name__ == '__main__':
    main()
