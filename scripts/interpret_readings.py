#!/usr/bin/env python3
"""Plain-English paraphrases of two readings of a sentence, for human review pages.

Each case gives a sentence and, for readings A and B, the semantic facts that set
it apart from the other (predicates and links, as in llm_rank.facts). The model
says what each reading means in a sentence or two, neutrally: it must not say
which reading is better. Used by the judge check for roadmap O90.

Usage:
    interpret_readings.py --cases analysis/judge-check/cases.json --out analysis/judge-check/interpretations.json
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_label import call  # noqa: E402

SYSTEM = """You explain semantic analyses from the English Resource Grammar to a linguist in plain English. For each sentence you get two readings, A and B, each shown only by what distinguishes it from the other: predicates (node ...) and links (head -ROLE-> dependent; ARG1, ARG2 ... are argument roles; /EQ means the two share a scope label, /H that the link goes through a scope constraint; names are lemma_partofspeech_sense; udef_q, compound, appos, implicit_conj and similar are grammar-internal predicates).
For each reading, write one or two short sentences saying what the sentence means under that reading, focusing on exactly where the two differ (which word attaches to what, what modifies what, which sense of a word, what is the scope). Be concrete and use the sentence's own words. Do not say which reading is better, more natural or more likely, and do not hint at it.
Answer with JSON only: {"<case id>": {"A": "...", "B": "..."}, ...}."""


def prompt(batch):
    parts = []
    for c in batch:
        parts.append(f'Case {c["id"]}: {c["sentence"]}')
        for k in ('A', 'B'):
            parts.append(f'  Reading {k}: ' + ('; '.join(c[k]) if c[k] else '(nothing beyond what both readings share)'))
    return '\n'.join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cases', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--batch', type=int, default=5)
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-opus-5-5')
    a = ap.parse_args()
    cases = json.load(open(a.cases))
    for c in cases:     # treebank markup out of the sentence shown to the model
        c['sentence'] = re.sub(r'\s+', ' ', re.sub(r'[⌊⌋•]', '', c['sentence'])).strip()
    batches = [cases[i:i + a.batch] for i in range(0, len(cases), a.batch)]
    out, cost = {}, 0.0

    def go(b):
        d = call(a.model, SYSTEM, prompt(b), os.path.dirname(os.path.abspath(a.out)))
        text = d.get('result', '')
        m = re.search(r'\{.*\}', text, re.S)
        return json.loads(m.group(0)) if m else {}, d.get('total_cost_usd', 0.0)

    with concurrent.futures.ThreadPoolExecutor(a.parallel) as ex:
        for res, c in ex.map(go, batches):
            out.update(res)
            cost += c or 0.0
    json.dump({'model': a.model, 'cost_usd': cost, 'by_id': out}, open(a.out, 'w'), indent=1, ensure_ascii=False)
    print(len(out), 'of', len(cases), f'${cost:.2f}')


if __name__ == '__main__':
    main()
