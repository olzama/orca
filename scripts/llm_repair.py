#!/usr/bin/env python3
"""Pilot: an LLM repairs derivations the grammar rejects, by reasoning over
the grammar's own definitions.

For each sentence that the tagger and repair could not analyze, the model is
shown the tagger's derivation with numbered nodes, where and why replay
fails (rule, feature path, clashing types), the TDL definitions of the rule
and the types involved, and the lexical types the lexicon allows for each
word. It answers with replacement subtrees. Each answer is replayed; on
failure the new failure is reported back, up to a fixed number of rounds.
Accepted derivations are compared with the gold MRS.

The model is called through the `claude` command line (print mode), so the
calls use the Claude subscription of the person running it.

Usage:
    llm_repair.py --data DATA --grammar ERG/english.tdl --profiles SPLIT_DIR
                  --failed KBEST.jsonl --out OUT_DIR [--n 60] [--rounds 3]
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
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from delphin import mrs as M, tsdb  # noqa: E402
from delphin.codecs import simplemrs  # noqa: E402

from compare_mrs import normalized, to_pydelphin  # noqa: E402
from eval_trees import to_leaves  # noqa: E402
from llm_label import call, parse, render, rule_docs  # noqa: E402
from orca.encoding import Leaf, Node, decode  # noqa: E402
from orca.tfs.fast import FastGrammar, extract  # noqa: E402
from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402
from orca.tfs.lexicon import Lexicon, replay_with_entries  # noqa: E402
from replay_predictions import gold_tokens  # noqa: E402

DEF = re.compile(r'^([^\s;:]+)\s*:=(.*?)\n\s*\n', re.M | re.S)

SYSTEM = """You are an expert in HPSG and in the English Resource Grammar (ERG). You repair \
derivations that the grammar rejects.

A derivation is a tree. Internal nodes are grammar rules with one or two daughters; lexical rules \
(names ending in lr) are unary nodes directly above a leaf; a leaf is a lexical type with the \
word(s) it covers in double quotes; the top node is a root condition (root_...). The grammar \
replays a derivation bottom-up by unification. When a unification fails, you are told the node, \
the feature path inside that node's rule (ARGS.FIRST is the first daughter, ARGS.REST.FIRST the \
second), and the two types that could not be unified.

Your job: work out from the grammar definitions why the derivation fails and what analysis the \
grammar intends for this sentence, then give a corrected derivation. Rules of the game:
- Each word may only get a lexical type that the lexicon allows for it (listed for every word, with \
the lexical rules that the spelling requires). Words not in the lexicon get unknown-word types.
- Use only rule names that exist (documented in the list below or seen in the derivation).
- Keep the words exactly and in order.
- Change as little as necessary, but change everything that has to change.

Answer format: first reason briefly. Then give one or more lines, each of the form
REPLACE <node id>: <bracketed subtree>
where the subtree covers exactly the same words as the node it replaces, written like the \
derivation: (rule daughter daughter), (lexical_rule daughter), (lexical_type "word"). Replacing \
node 0 replaces the whole derivation. Nothing after the REPLACE lines.

Documentation of the grammar's rules (name: description, with an example):

{docs}"""


def tdl_index(erg):
    out = {}
    for path in glob.glob(os.path.join(erg, '*.tdl')):
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read() + '\n\n'
        for m in DEF.finditer(text):
            out.setdefault(m.group(1).lower(), (m.group(1) + ' :=' + m.group(2)).strip())
    return out


def numbered(t, path='0', depth=0, lines=None):
    """The derivation as indented lines with node ids (paths of child indices)."""
    lines = [] if lines is None else lines
    pad = '  ' * depth
    if isinstance(t, Leaf):
        lines.append(f'{pad}[{path}] {t.entry} "{" ".join(t.forms)}"')
    else:
        lines.append(f'{pad}[{path}] {t.label}')
        for i, c in enumerate(t.children):
            numbered(c, f'{path}.{i}', depth + 1, lines)
    return lines


def node_at(t, path):
    for i in path.split('.')[1:]:
        t = t.children[int(i)]
    return t


def replace_at(t, path, new):
    parts = path.split('.')[1:]
    if not parts:
        return new

    def walk(node, rest):
        if not rest:
            return new
        i = int(rest[0])
        kids = list(node.children)
        kids[i] = walk(kids[i], rest[1:])
        return Node(node.label, tuple(kids))

    return walk(t, parts)


def words(t):
    return list(t.forms) if isinstance(t, Leaf) else [w for c in t.children for w in words(c)]


def labels(t):
    out = {t.entry if isinstance(t, Leaf) else t.label}
    if not isinstance(t, Leaf):
        for c in t.children:
            out |= labels(c)
    return out


def lexicon_options(lx, forms):
    """For each word: lexical types the lexicon allows, with the lexical rules
    needed for the spelling."""
    by_orth = collections.defaultdict(set)
    for (lextype, orth), names in lx.by_type_orth.items():
        by_orth[orth].add(lextype)
    lines = []
    for w in forms:
        opts = set()
        low = w.lower().replace('\\', '')
        for t in by_orth.get(low, ()):
            opts.add(t)
        for rule in lx.undo:
            for stem in lx.stems(low, rule):
                for t in by_orth.get(stem, ()):
                    opts.add(f'{t} + {rule}')
        lines.append(f'  {w}: ' + ('; '.join(sorted(opts)) if opts else
                                   'not in the lexicon (unknown word: use a generic unknown-word type)'))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--failed', required=True, help='repair output with candidates (k-best run)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--seed', type=int, default=1)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    gdir = os.path.dirname(args.grammar)

    g = Grammar(args.grammar)
    fg = FastGrammar(g)
    lx = Lexicon(g, gdir)
    defs = tdl_index(gdir)
    toks = gold_tokens(args.profiles)
    gold_mrs = {}
    for prof in sorted(glob.glob(os.path.join(args.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('derivation')]:
                    gold_mrs[f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}"] = normalized(
                        simplemrs.decode(rec[names.index('mrs')]))
    failed = []
    with open(args.failed, encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            if not r.get('candidates'):
                failed.append(r)
    random.Random(args.seed).shuffle(failed)
    sample = failed[:args.n]
    system = SYSTEM.format(docs='\n'.join(rule_docs(gdir)))
    lock = threading.Lock()           # the engine is not thread-safe; LLM calls run in parallel

    def check(sid, tree):
        """('accepted', same_mrs) or ('rejected', node id, explanation)."""
        with lock:
            fg.reset()
            try:
                fs, _ = replay_with_entries(fg, lx, tree, toks[sid])
                same = M.is_isomorphic(to_pydelphin(extract(fg, fs)), gold_mrs[sid], properties=False)
                return ('accepted', same)
            except ReplayFailure as e:
                node = e.where.split()[0]
                return ('rejected', node, str(e.cause))
            except Exception as e:                      # malformed proposal
                return ('rejected', '0', f'{type(e).__name__}: {e}')

    def grammar_context(tree, node):
        try:
            sub = node_at(tree, node)
        except Exception:
            sub = tree
        names = sorted(labels(sub))[:12]
        parts = []
        for n in names:
            d = defs.get(n.lower())
            if d:
                parts.append(d[:1500])
                sup = re.findall(r'^\s*([\w+*-]+)', d.split(':=', 1)[1])
                for s in sup[:1]:
                    if s.lower() in defs and s.lower() != n.lower():
                        parts.append(defs[s.lower()][:1500])
        return '\n\n'.join(parts)

    def run(r):
        sid, forms = r['id'], r['forms']
        tree = decode(to_leaves(forms, r['leaf'], r['tree']))
        log = {'id': sid, 'forms': forms, 'rounds': []}
        verdict = check(sid, tree)
        history = []
        for rnd in range(args.rounds):
            if verdict[0] == 'accepted':
                break
            _, node, cause = verdict
            prompt = '\n'.join([
                'Sentence: ' + ' '.join(forms),
                '', 'Current derivation (node ids in brackets):', *numbered(tree),
                '', f'Replay fails at node [{node}]: {cause}',
                '', 'Lexical types the lexicon allows for each word:', lexicon_options(lx, forms),
                '', 'Grammar definitions of the rule and types under the failing node:',
                grammar_context(tree, node),
                *(['', 'Earlier attempts in this conversation and why they failed:'] + history if history else []),
            ])
            data = call(args.model, system, prompt, args.out)
            text = data.get('result') or ''
            step = {'round': rnd + 1, 'failing_node': node, 'cause': cause, 'response': text,
                    'usage': data.get('usage'), 'cost': data.get('total_cost_usd'), 'seconds': data.get('seconds')}
            new = tree
            ok = True
            for m in re.finditer(r'^REPLACE\s+\[?([\d.]+)\]?\s*:\s*(\(.*\))\s*$', text, re.M):
                try:
                    sub = parse(m.group(2))
                    old = node_at(new, m.group(1))
                    if words(sub) != words(old):
                        ok = False
                        step['problem'] = f'words of the replacement for [{m.group(1)}] differ'
                        break
                    new = replace_at(new, m.group(1), sub)
                except Exception as e:
                    ok = False
                    step['problem'] = f'unreadable replacement: {e}'
                    break
            if new is tree and ok:
                step['problem'] = 'no REPLACE line'
                ok = False
            if ok:
                tree = new
                verdict = check(sid, tree)
            step['verdict'] = list(verdict)
            log['rounds'].append(step)
            history.append(f"- attempt {rnd + 1}: " + (step.get('problem') or f'replay fails at [{verdict[1]}]: {verdict[2]}'
                                                       if verdict[0] == 'rejected' or not ok else 'accepted'))
        log['final'] = list(verdict)
        log['derivation'] = render(tree)
        return log

    results = []
    with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool, \
            open(os.path.join(args.out, 'log.jsonl'), 'w', encoding='utf-8') as out:
        for log in pool.map(run, sample):
            results.append(log)
            out.write(json.dumps(log, ensure_ascii=False) + '\n')
            out.flush()
            v = log['final']
            print(f"{len(results)}/{len(sample)} {v[0]}{' gold MRS' if v[0] == 'accepted' and v[1] else ''} "
                  f"after {len(log['rounds'])} rounds", flush=True)
    st = collections.Counter()
    for log in results:
        st['sentences'] += 1
        st['accepted'] += log['final'][0] == 'accepted'
        st['accepted with gold MRS'] += log['final'][0] == 'accepted' and bool(log['final'][1])
        st['calls'] += len(log['rounds'])
        for step in log['rounds']:
            st['cost_usd_equivalent'] += step.get('cost') or 0
            st['seconds'] += step.get('seconds') or 0
            st['malformed answers'] += 'problem' in step
        st[f"accepted after {len(log['rounds'])} rounds"] += log['final'][0] == 'accepted'
    summary = {'args': {k: v for k, v in vars(args).items() if k in ('n', 'rounds', 'model', 'seed')}, 'stats': dict(st)}
    with open(os.path.join(args.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
