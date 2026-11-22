#!/usr/bin/env python3
"""Ask an LLM why the grammar rejects the closest analysis of a sentence.

First step of grammar expansion: for a sentence Orca cannot analyze, take the
tagger's best derivation, replay it, and give the model what the grammar
reports at the failure point (the node, its rule, the feature path and the two
types that do not unify), the TDL definitions involved, the sentence and the
derivation. The model classifies the cause and proposes the smallest change.

Two kinds of items:
  dev        Redwoods dev sentences Orca rejects. The treebank has a gold
             analysis for each, so the grammar licenses them: the right
             diagnosis is a tagging error. These check the diagnoser.
  generated  generated sentences ACE could not parse either: candidates for
             real gaps in the grammar.
The model is not told which kind an item is.

Usage:
  diagnose_rejections.py prepare --out DIR [--dev 30] [--generated 10] [--seed 1]
  diagnose_rejections.py run --out DIR [--model claude-opus-5-5] [--parallel 4]
  diagnose_rejections.py score --out DIR
"""
import argparse
import collections
import concurrent.futures
import glob
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

ERG = os.path.join(HERE, '..', 'data', 'erg', '2025')
TAGGER = 'data/models/tagger-2025bothsurf-debertav3large'
DEV_EVAL = 'analysis/mrs/dev-2025bothsurf-debertav3large-rawtext.json'
DEV_GOLD = 'data/encoded-2025-bothall-surface/dev.jsonl'
CAUSES = ['wrong tag only', 'missing lexical entry', 'missing construction', 'tokenization', 'punctuation',
          'ungrammatical or robust input', 'other']

GENERIC_NOTE = (
    'How words find lexical entries: the tagger proposes a lexical type (plus lexical rules) for each word, and Orca '
    'looks up an entry of that type with that spelling (after undoing the inflection). If the lexicon has none, Orca '
    'uses the ERG\'s generic entry of that type, if there is one (gle.tdl: generic entries for unknown words, such as '
    'generic_mass_count_noun n_-_mc-unk_le, generic_pl_noun n_-_c-pl-unk_le, generic_adj aj_-_i-unk_le, '
    'generic_trans_verb_* v_np*_le, generic_quoted n_-_gq_le, generic_proper_ne n_-_pn-gen_le; each is licensed by the '
    'token\'s part-of-speech tag, checked as +TNT.+TAGS). Otherwise replay fails with "missing lexical entry". So that '
    'failure means the proposed TYPE has no entry for the word: if the word has entries of other types, or the word is '
    'unknown but the tagger chose a non-generic type (or a generic type whose POS tag does not match), it is a tagging '
    'error, not a gap in the grammar.')
MARKUP_NOTE = (
    'Wikipedia text (the WeScience part of Redwoods) carries GML markup: ⌊/ … /⌋ italics, ⌊> … >⌋ links, ⌊λ … λ⌋ IPA, '
    '⌊( … )⌋ grouping, ⌊∗ … ∗⌋ emphasis. The ERG handles it: italics marks attach to words through punctuation-like '
    'lexical rules (w_italleft_plr, w_italright_plr; w_drop-ileft_plr and w_drop-iright_plr ignore them); italicized '
    'cited or foreign material is usually a generic quoted noun (n_-_gq_le); link marks are mostly removed in '
    'preprocessing (gml.rpp), so "model>⌋s" is model_n2 with n_pl_olr. A failure on a token with markup is almost '
    'always a labeling error, not a gap in the grammar (see ErgGml on the DELPH-IN wiki).')

SYSTEM = ('You are an expert in HPSG and in the English Resource Grammar (ERG). You diagnose why the grammar '
          'rejects a proposed derivation. Answer with one JSON object only.')


def tdl_index():
    """name -> its TDL definition text, from every .tdl file of the ERG."""
    idx = {}
    start = re.compile(r'^([^\s;:%"]+)\s*:[=+<]', re.M)
    for path in sorted(glob.glob(os.path.join(ERG, '*.tdl'))):
        text = open(path, encoding='utf-8', errors='replace').read()
        for block in re.split(r'\n\s*\n', text):
            block = '\n'.join(l for l in block.split('\n') if not l.lstrip().startswith(';')).strip()
            m = start.match(block)
            if m:
                idx.setdefault(m.group(1).lower(), f';; {os.path.basename(path)}\n{block}')
    return idx


def show_tree(t, addr='0', depth=0):
    from orca.encoding import Leaf
    pad = '  ' * depth
    if isinstance(t, Leaf):
        return [f'{pad}{addr} {t.entry} "{" ".join(t.forms)}"']
    out = [f'{pad}{addr} {t.label}']
    for i, c in enumerate(t.children):
        out += show_tree(c, f'{addr}.{i}', depth + 1)
    return out


def node_at(t, addr):
    from orca.encoding import Leaf
    for i in [int(x) for x in addr.split('.')[1:]]:
        if isinstance(t, Leaf) or i >= len(t.children):
            break
        t = t.children[i]
    return t


def labels_under(t):
    from orca.encoding import Leaf
    if isinstance(t, Leaf):
        return [t.entry]
    out = [t.label]
    for c in t.children:
        out += labels_under(c)
    return out


def defs_for(names, idx, limit=40, max_defs=8):
    out, seen = [], set()
    for n in names:
        n = n.lower().replace('entry:', '')
        if n in seen or n not in idx:
            continue
        seen.add(n)
        lines = idx[n].split('\n')
        out.append('\n'.join(lines[:limit]) + ('\n  ...' if len(lines) > limit else ''))
        if len(out) >= max_defs:
            break
    return out


def prepare(a):
    from delphin import itsdb
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.grammar import ReplayFailure
    from orca.tfs.lexicon import replay_with_entries
    from orca.tokens import lattice_path, token_chart
    from orca_parse import Parser

    rng = random.Random(a.seed)
    cands = []
    texts = {}
    for p in glob.glob('data/profiles-2025/dev/*/'):
        for row in itsdb.TestSuite(p)['item']:
            texts[f"{p.rstrip('/').split('/')[-1]}/{row['i-id']}"] = row['i-input']
    gold = {}
    for l in open(DEV_GOLD):
        r = json.loads(l)
        gold[r['id']] = labels_of(r['tokens'])
    rej = [r['id'] for r in json.load(open(DEV_EVAL))['records'] if r['outcome'].startswith('rejected')]
    rng.shuffle(rej)
    cands += [('dev', i, texts[i]) for i in rej if i in texts]
    gen = []
    for rnd in ('pilot1', 'round2', 'round3'):
        for p in glob.glob(f'data/generated/{rnd}/profiles/*/'):
            ts = itsdb.TestSuite(p)
            items = {r['i-id']: r['i-input'] for r in ts['item']}
            for r in ts['parse']:
                if r['readings'] == 0:
                    gen.append(('generated', f'gen-{rnd}/{r["i-id"]}', items[r['i-id']]))
    rng.shuffle(gen)
    from orca.tfs.lexicon import _leaf_range
    P = Parser(tagger=TAGGER, device=a.device)
    idx = tdl_index()
    by_orth = collections.defaultdict(set)
    for (lt, orth), _ in P.lx.by_type_orth.items():
        by_orth[orth].add(lt)
    want = {'dev': a.dev, 'generated': a.generated}
    got = collections.Counter()
    with open(os.path.join(a.out, 'items.jsonl'), 'w') as f:
        for kind, sid, text in cands + gen:
            if got[kind] >= want[kind]:
                continue
            try:
                path = lattice_path(token_chart(text, P.ace, P.dat), P.known)
            except Exception:
                continue
            forms = [text[x:y] for _, _, (x, y) in path] if P.surface else [p[0] for p in path]
            if not forms or len(forms) > 40:
                continue
            top = P.tag(forms)
            leaf = [top['leaf'][j][0][0] for j in range(len(forms))]
            tree = [top['tree'][j][0][0] for j in range(len(forms))]
            t = decode(to_leaves(forms, leaf, tree))
            P.fg.reset()
            try:
                replay_with_entries(P.fg, P.lx, t, [p[1] for p in path])
                continue                       # the best guess replays: nothing to diagnose
            except ReplayFailure as e:
                where, cause = e.where, str(e.cause)
            except Exception as e:
                where, cause = '0', f'{type(e).__name__}: {e}'
            addr = where.split()[0]
            node = node_at(t, addr)
            clash = re.findall(r'[\w*+-]+', cause.split(':', 1)[1]) if ':' in cause else []
            names = [where.split()[1] if len(where.split()) > 1 else ''] + labels_under(node)[:12] + clash
            # the words at and around the failure point
            m = re.search(r'missing lexical entry for "(.*)"', cause)
            if m:
                js = [j for j, f0 in enumerate(forms) if f0 == m.group(1)] or [0]
                lo, hi = js[0], js[0] + 1
            else:
                try:
                    rg = _leaf_range(t, addr)
                    lo, hi = rg.start, rg.stop
                except Exception:
                    lo, hi = 0, len(forms)
            window = range(max(0, lo - 2), min(len(forms), hi + 2))
            alts = []
            for j in window:
                low = forms[j].lower().replace('\\', '')
                alts.append({'word': forms[j], 'at failure': lo <= j < hi,
                             'leaf': [[x[0], round(x[2], 3)] for x in top['leaf'][j][:3]],
                             'tree': [[x[0], round(x[2], 3)] for x in top['tree'][j][:3]],
                             'lexicon types for this spelling': sorted(by_orth.get(low, ()))[:12],
                             'generic entry for the proposed type': sorted(P.lx.generic.get(leaf[j].split('|')[0].lower(), ()))})
            item = {'kind': kind, 'id': sid, 'sentence': text, 'forms': forms, 'where': where, 'cause': cause, 'window': alts,
                    'derivation': '\n'.join(show_tree(t)), 'definitions': defs_for(names, idx),
                    'guess': {'leaf': leaf, 'tree': tree}}
            if kind == 'dev' and sid in gold:
                gf, gl, gt = gold[sid]
                if len(gf) == len(forms):
                    item['wrong labels'] = [{'word': forms[j], 'guess': [leaf[j], tree[j]], 'gold': [gl[j], gt[j]]}
                                            for j in range(len(forms)) if (leaf[j], tree[j]) != (gl[j], gt[j])]
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            got[kind] += 1
            print(kind, sid, where, '|', cause[:80], flush=True)
    print(dict(got))


def prompt_for(it, rich=False):
    defs = '\n\n'.join(it['definitions']) or '(none found)'
    extra = ''
    if rich and it.get('window'):
        rows = []
        for w in it['window']:
            rows.append(f"- {w['word']}{' (at the failure point)' if w['at failure'] else ''}: "
                        f"tagger's top lexical labels {w['leaf']}; top tree labels {w['tree']}; "
                        f"the lexicon has this spelling with types {w['lexicon types for this spelling'] or 'none'}; "
                        f"generic entry for the proposed type: {w['generic entry for the proposed type'] or 'none'}")
        extra = ('\nThe tagger\'s three best labels (with probabilities) for the words at and around the failure point, '
                 'and what the lexicon has for them (lexical label = type|lexical rules|unary rules; tree label = '
                 'attachment|rules above):\n' + '\n'.join(rows) + '\n\n' + GENERIC_NOTE + '\n\n' + MARKUP_NOTE + '\n')
    return f"""A fast parser for the English Resource Grammar proposes one complete derivation per sentence (from a
neural tagger's labels: lexical type plus lexical rules per word, and the rules above it) and the grammar
checks it by unification. For this sentence the proposed derivation was rejected, and no repair found an
accepted one.

Sentence: {it['sentence']}
Tokens (the grammar's own preprocessing): {' | '.join(it['forms'])}

Proposed derivation (node addresses first; leaves are lexical types with their word):
{it['derivation']}

The grammar rejected it at node {it['where']}
Unification failure: {it['cause']}
(the feature path is relative to the rule at that node; the two types do not unify)

Relevant TDL definitions from the ERG:
{defs}
{extra}
Why is the sentence rejected? The proposed labels may be wrong even when the grammar has a correct analysis.
Choose one cause:
- "wrong tag only": the grammar can analyze the sentence; some proposed labels are wrong (say which words, and what they should be)
- "missing lexical entry": a word lacks the entry it needs
- "missing construction": the grammar lacks a rule or construction the sentence needs
- "tokenization": the tokens are wrong
- "punctuation": punctuation the grammar does not handle
- "ungrammatical or robust input": the sentence is ill-formed or fragmentary
- "other"

Answer with JSON only:
{{"cause": "...", "explanation": "two or three sentences, naming the constraint that fails and why",
 "fix": "the smallest change: which labels to change (for a tagging error), or which entry, type or rule to add or change in the grammar",
 "confidence": 0.0}}"""


def run(a):
    from llm_label import call
    items = [json.loads(l) for l in open(os.path.join(a.out, 'items.jsonl'))]
    outp = os.path.join(a.out, 'results.jsonl')
    done = {json.loads(l)['id'] for l in open(outp)} if os.path.exists(outp) else set()
    todo = [it for it in items if it['id'] not in done]

    def one(it):
        try:
            r = call(a.model, SYSTEM, prompt_for(it, a.rich), a.out)
            txt = str(r.get('result', ''))
            m = re.search(r'\{.*\}', txt, re.S)
            ans = json.loads(m.group(0)) if m else {'cause': 'unparsed', 'raw': txt[:2000]}
            return {'id': it['id'], 'kind': it['kind'], 'answer': ans, 'cost_usd': r.get('total_cost_usd', 0), 'seconds': r.get('seconds')}
        except Exception as e:
            return {'id': it['id'], 'kind': it['kind'], 'answer': {'cause': 'error', 'raw': str(e)[:500]}, 'cost_usd': 0}
    with open(outp, 'a') as f, concurrent.futures.ThreadPoolExecutor(a.parallel) as ex:
        for res in ex.map(one, todo):
            f.write(json.dumps(res, ensure_ascii=False) + '\n')
            f.flush()
            print(res['kind'], res['id'], res['answer'].get('cause'), flush=True)


def score(a):
    items = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(a.out, 'items.jsonl'))}
    res = [json.loads(l) for l in open(os.path.join(a.out, 'results.jsonl'))]
    by = collections.defaultdict(collections.Counter)
    right_words = collections.Counter()
    for r in res:
        c = r['answer'].get('cause', 'unparsed')
        by[r['kind']][c] += 1
        it = items[r['id']]
        if r['kind'] == 'dev' and c == 'wrong tag only' and it.get('wrong labels'):
            fix = (r['answer'].get('fix', '') + ' ' + r['answer'].get('explanation', '')).lower()
            right_words['wrong tag, names a word that is wrong'] += any(w['word'].lower() in fix for w in it['wrong labels'])
            right_words['wrong tag'] += 1
    dev = by['dev']
    s = {'items': len(res), 'by kind and cause': {k: dict(v) for k, v in by.items()},
         'dev: diagnosed as tagging error (correct, gold exists)': dev['wrong tag only'], 'dev: items': sum(dev.values()),
         'dev: tagging diagnoses naming a truly wrong word': right_words['wrong tag, names a word that is wrong'],
         'cost_usd': round(sum(r.get('cost_usd') or 0 for r in res), 2)}
    if a.compare:
        old = {json.loads(l)['id']: json.loads(l) for l in open(os.path.join(a.compare, 'results.jsonl'))}
        shared = [r for r in res if r['id'] in old]
        for kind in ('dev', 'generated'):
            sh = [r for r in shared if r['kind'] == kind]
            before = collections.Counter(old[r['id']]['answer'].get('cause') for r in sh)
            after = collections.Counter(r['answer'].get('cause') for r in sh)
            pairs = collections.Counter(f"{old[r['id']]['answer'].get('cause')} -> {r['answer'].get('cause')}" for r in sh)
            s[f'{kind}, same items as {os.path.basename(a.compare)}'] = {'items': len(sh), 'before': dict(before), 'after': dict(after),
                                                                         'changes': dict(pairs.most_common())}
        new_dev = [r for r in res if r['kind'] == 'dev' and r['id'] not in old]
        s['dev, new items'] = {'items': len(new_dev), 'causes': dict(collections.Counter(r['answer'].get('cause') for r in new_dev))}
    json.dump(s, open(os.path.join(a.out, 'summary.json'), 'w'), indent=1)
    print(json.dumps(s, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('step', choices=['prepare', 'run', 'score'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--dev', type=int, default=30)
    ap.add_argument('--generated', type=int, default=10)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--rich', action='store_true', help='round 2: add tagger alternatives, lexicon facts, notes on generic entries and markup')
    ap.add_argument('--compare', help='score: an earlier round\'s directory, to count causes before and after on the shared items')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    {'prepare': prepare, 'run': run, 'score': score}[a.step](a)


if __name__ == '__main__':
    main()
