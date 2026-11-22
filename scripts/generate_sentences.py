#!/usr/bin/env python3
"""Generate English sentences rich in the constructions the tagger gets wrong.

The targets come from the error profile of the dev set (gold labels the
tagger misses in sentences whose gold meaning is never among the accepted
derivations). Each call asks for N sentences focused on one target, in
varied genres and lengths. The sentences are then parsed by ACE and kept
only if the grammar replays the parse (see make_profile / run_ace.py /
filter_replayable.py), like other silver data.

The model is called through the `claude` command line (print mode), as in
llm_label.py.

Usage:
    generate_sentences.py --out DIR [--per-call 100] [--rounds 2] [--parallel 4] [--model M]
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_label import call  # noqa: E402

TARGETS = {
    'reduced-relatives': 'noun phrases modified by reduced relative clauses: participial ("the report written last year", "a man standing by the door") and adjectival ("a box full of letters")',
    'pp-attachment': 'prepositional phrases and adverbials whose attachment is a real choice: to the verb, to the noun, or to a higher clause ("She saw the house on the hill with a telescope")',
    'complements-vs-adjuncts': 'verbs, nouns and adjectives with prepositional or clausal complements next to similar-looking adjuncts ("rely on", "interested in", "the fact that ...", "the idea of ...")',
    'relative-clauses': 'full relative clauses with who, which, that, whose, where, and zero relatives, including relatives inside relatives and object extraction',
    'noun-compounds': 'long noun compounds and compounds with plural or possessive parts ("customer service phone line", "the city council budget meeting", "a two-year warranty extension")',
    'name-compounds': 'proper names inside compounds and appositions: titles, organizations, places, products, dates ("the Bank of England governor", "Professor Ada Lin of Oslo", "the Model X battery")',
    'coordination': 'coordination of noun phrases, adjectives, verb phrases and clauses, including lists with and without commas, "both ... and", "either ... or", and coordination inside compounds',
    'unknown-words': 'rare, technical, invented or foreign words used as nouns, adjectives and verbs in otherwise ordinary sentences (brand names, scientific terms, regional words)',
    'mass-count': 'nouns that can be mass or count ("coffee", "paper", "experience", "light") used both ways, with and without determiners',
    'do-be': 'the do-be construction: a subject headed by what, all, thing, best, least, most or worst with a relative clause containing the verb do, then a form of be and a verb phrase ("What you have to do is get ready", "All the government does is send out checks", "The least we could do was write a paper", "The first thing he did was call his lawyer"); vary the form of do and of the final verb',
    'optional-complements': 'nouns, verbs and adjectives that take optional complements, used both with and without them ("He resigned", "He resigned from the board", "a picture", "a picture of her mother")',
    # after Chaves and Richter 2021: agreement that BERT-family models get wrong after distracting material
    'agreement-attractors': 'subject-verb agreement across distracting nouns of the other number: a long subject with a plural or singular noun inside it, or a clause with such nouns before the subject, or a clefted subject separated from its verb by embedded clauses ("The engineers handling the removal from our building said the lawyer seems upset", "The key to the cabinets was lost", "It was the cousins who I think you said were upset"); use many different verbs, not only be',
    # after Pollard and Sag 1994, chapters 3 and 7: equi against raising frames of the same verb
    'control-raising': 'verbs and adjectives with infinitival complements that are either control or raising, especially verbs that have both kinds of frames ("expect", "promise", "believe", "want", "ask", "persuade", "seem", "appear", "tend", "likely", "eager", "easy"), including expletive subjects and objects ("There seems to be a problem", "We expect it to rain")',
}

SYSTEM = ('You write natural English sentences for a linguistics dataset. Output only the sentences, '
          'one per line, no numbering, no quotation marks around them, no commentary.')


def prompt(target, n, seed):
    lengths = 'about a third short (under 12 words), a third medium (12 to 25 words), a third long (26 to 50 words)'
    return (f'Write {n} different English sentences that each contain {TARGETS[target]}.\n'
            f'Lengths: {lengths}.\n'
            'Vary the genre: fiction, news, emails, product reviews, encyclopedia text, instructions, dialogue. '
            'Vary tense, voice, and sentence type (statements, questions, imperatives). '
            'Use ordinary, grammatical, natural English; real-sounding names are fine. '
            f'Each sentence must be self-contained. (Batch {seed}: do not repeat common textbook examples.)')


def clean(text):
    out = []
    for line in text.splitlines():
        line = re.sub(r'^\s*(\d+[.)]|[-*•])\s+', '', line).strip().strip('"“”')
        if 3 <= len(line.split()) <= 60 and not line.endswith(':'):
            out.append(line)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--per-call', type=int, default=100)
    ap.add_argument('--rounds', type=int, default=2, help='calls per target')
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-sonnet-5-5')
    ap.add_argument('--targets', help='comma-separated target:calls pairs (default: every target, --rounds calls each)')
    ap.add_argument('--first-batch', type=int, default=1, help='batch number of the first call (vary across rounds)')
    ap.add_argument('--exclude', nargs='*', default=[], help='sentences.txt files of earlier rounds; their sentences are dropped')
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    log = os.path.join(args.out, 'calls.jsonl')
    done = set()
    if os.path.exists(log):
        for l in open(log):
            r = json.loads(l)
            if r.get('sentences'):
                done.add((r['target'], r['round']))
    plan = ({t: int(k) for t, k in (x.split(':') for x in args.targets.split(','))} if args.targets
            else {t: args.rounds for t in TARGETS})
    jobs = [(t, r) for t, k in plan.items() for r in range(k) if (t, r) not in done]

    def run(job):
        t, r = job
        try:
            data = call(args.model, SYSTEM, prompt(t, args.per_call, r + args.first_batch), args.out)
            text = data.get('result') or ''
        except Exception as e:
            data, text = {'error': str(e)[:300]}, ''
        return {'target': t, 'round': r, 'sentences': clean(text), 'seconds': data.get('seconds'),
                'usage': data.get('usage'), 'cost_usd': data.get('total_cost_usd'), 'error': data.get('error'),
                'raw_if_empty': text[:500] if not clean(text) else None}

    with concurrent.futures.ThreadPoolExecutor(args.parallel) as ex, open(log, 'a') as f:
        for rec in ex.map(run, jobs):
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
            f.flush()
            print(rec['target'], rec['round'], len(rec['sentences']), flush=True)
    seen, n = set(), 0
    for f in args.exclude:
        seen.update(l.rstrip('\n') for l in open(f))
    with open(os.path.join(args.out, 'sentences.txt'), 'w') as out:
        for l in open(log):
            r = json.loads(l)
            for s in r['sentences']:
                if s not in seen:
                    seen.add(s)
                    out.write(s + '\n')
                    n += 1
    print('unique sentences', n)


if __name__ == '__main__':
    main()
