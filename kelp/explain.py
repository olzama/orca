"""Plain-English explanations of the readings of a sentence, on request.

The model gets the sentence and, per reading, only what sets it apart from
the other readings: predicates, links between predicates, and the lexical
entries of the words that are analyzed differently. It says what the sentence
means under each reading and must not say which reading is better.

Explanations are optional. The model can be Claude through the `claude`
command-line program (a subscription, no key), or Claude, GPT or Gemini
through their services, each with a key in the environment. Without any of
these Kelp works as before, with no explanations. Nothing is sent unless
the annotator asks.
"""
import collections
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

SYSTEM = """You explain semantic analyses from the English Resource Grammar to a linguist in plain English. For one sentence you get several readings, numbered, each shown only by what distinguishes it from the other readings: predicates (node ...), links (head -ROLE-> dependent; ARG1, ARG2 ... are argument roles; /EQ means the two share a scope label, /H that the link goes through a scope constraint; names are lemma_partofspeech_sense; udef_q, compound, appos, implicit_conj and similar are grammar-internal predicates), and the lexical entries chosen for some words, with the grammar's own note on the entry's type.
For each reading, write one or two short sentences saying what the sentence means under that reading, focusing on exactly where the readings differ (which word attaches to what, what modifies what, which sense of a word, what is the scope). Be concrete and use the sentence's own words. Do not say which reading is better, more natural or more likely, and do not hint at it.
Some readings also come with the parts of their syntax tree that the others lack (tree: rule names over the words they cover); use these only to understand the difference, and do not recite rule names.
Also say, in one plain sentence, what the readings disagree about.
Answer with JSON only: {"difference": "...", "<reading number>": "...", ...}."""


def facts(graph):
    """The predicates and links of a meaning (as the engine's DMRS dictionary), as a multiset of strings."""
    name = {n['id']: n['pred'] + (f'("{n["carg"]}")' if n.get('carg') else '') for n in graph['nodes']}
    out = collections.Counter(f'node {v}' for v in name.values())
    for k in graph['links']:
        if k['from'] in name and k['to'] in name:
            post = '' if k.get('post') in ('NEQ', '', None) else '/' + k['post']
            out[f"{name[k['from']]} -{k.get('role') or ''}{post}-> {name[k['to']]}"] += 1
    return out


def distinguishing(graphs):
    """Per reading, its facts that not every reading has (equally often)."""
    all_facts = [facts(g) for g in graphs]
    out = []
    for f in all_facts:
        out.append(sorted(x for x in f if any(o[x] != f[x] for o in all_facts)))
    return out


def prompt(sentence, readings):
    """readings: [(number, [distinguishing facts], [notes on words])]"""
    parts = [f'Sentence: {sentence}']
    for number, fs, notes in readings:
        parts.append(f'Reading {number}: ' + ('; '.join(fs) if fs else '(no predicate or link that the others lack)'))
        for note in notes:
            parts.append(f'    {note}')
    return '\n'.join(parts)


def _parse(answer):
    try:
        return {str(k): str(v) for k, v in json.loads(re.search(r'\{.*\}', answer, re.S).group(0)).items()}
    except (ValueError, AttributeError):
        raise ValueError('the model gave no usable answer')


def _post(url, headers, body, timeout):
    req = urllib.request.Request(url, json.dumps(body).encode(), dict(headers, **{'Content-Type': 'application/json'}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise ValueError(f'the model service answered {e.code}: {e.read().decode(errors="replace")[:300]}')


def _claude_cli(model, text, timeout):
    """The `claude` command-line program, with the subscription that is logged in there."""
    cmd = ['claude', '-p', '--model', model, '--system-prompt', SYSTEM, '--tools', '',
           '--strict-mcp-config', '--disable-slash-commands', '--no-session-persistence',
           '--setting-sources', '', '--output-format', 'json']
    proc = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=timeout)
    try:
        return json.loads(proc.stdout).get('result', '')
    except ValueError:
        raise ValueError('the claude program gave no answer' + (': ' + proc.stderr.strip()[:200] if proc.stderr.strip() else ''))


def _anthropic(model, text, timeout):
    d = _post('https://api.anthropic.com/v1/messages',
              {'x-api-key': os.environ['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'},
              {'model': model, 'max_tokens': 2000, 'system': SYSTEM, 'messages': [{'role': 'user', 'content': text}]}, timeout)
    return ''.join(b.get('text', '') for b in d.get('content', []))


def _openai(model, text, timeout):
    d = _post('https://api.openai.com/v1/chat/completions', {'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY']},
              {'model': model, 'messages': [{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': text}]}, timeout)
    return d['choices'][0]['message']['content']


def _gemini(model, text, timeout):
    d = _post(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
              {'x-goog-api-key': os.environ['GEMINI_API_KEY']},
              {'system_instruction': {'parts': [{'text': SYSTEM}]}, 'contents': [{'parts': [{'text': text}]}]}, timeout)
    return ''.join(p.get('text', '') for p in d['candidates'][0]['content']['parts'])


# provider -> (function, default model, the environment variable with its key, how it is named on the page)
PROVIDERS = {
    'claude-cli': (_claude_cli, 'claude-opus-5-5', None, 'Claude'),
    'anthropic': (_anthropic, 'claude-opus-5-5', 'ANTHROPIC_API_KEY', 'Claude'),
    'openai': (_openai, 'gpt-4o-mini', 'OPENAI_API_KEY', 'GPT'),
    'gemini': (_gemini, 'gemini-2.5-flash', 'GEMINI_API_KEY', 'Gemini'),
}


def choose(provider='auto'):
    """The provider to use, or None for no explanations. 'auto': the claude
    program if it is installed, otherwise the first service whose key is set."""
    if provider == 'none':
        return None
    if provider != 'auto':
        key = PROVIDERS[provider][2]
        if key and not os.environ.get(key):
            raise SystemExit(f'--explain {provider} needs the environment variable {key}')
        if provider == 'claude-cli' and not shutil.which('claude'):
            raise SystemExit('--explain claude-cli needs the claude program')
        return provider
    if shutil.which('claude'):
        return 'claude-cli'
    return next((p for p, (_, _, key, _) in PROVIDERS.items() if key and os.environ.get(key)), None)


def ask(provider, model, text, timeout=300):
    """{reading number: explanation}, from one call to the model."""
    fn, default, _, _ = PROVIDERS[provider]
    return _parse(fn(model or default, text, timeout))
