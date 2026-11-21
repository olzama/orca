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


def balanced(text):
    """Close unbalanced brackets in a model's subtree (a common slip on long
    subtrees): drop surplus closing brackets at the end, add missing ones."""
    text = text.strip()
    depth, out, quoted, esc = 0, [], False, False
    for ch in text:
        if quoted:
            esc = ch == '\\' and not esc
            quoted = not (ch == '"' and not esc)
        elif ch == '"':
            quoted = True
        elif ch == '(':
            depth += 1
        elif ch == ')':
            if depth == 0:
                continue
            depth -= 1
        out.append(ch)
    return ''.join(out) + ')' * depth


def leaf_paths(t, path='0', rules=(), pos=0, out=None):
    """(path, leaf, lexical rules above it, first token) for every leaf."""
    out = [] if out is None else out
    if isinstance(t, Leaf):
        out.append((path, t, rules, pos))
        return out
    lex = len(t.children) == 1 and t.label.lower().endswith('lr')
    for i, c in enumerate(t.children):
        leaf_paths(c, f'{path}.{i}', rules + (t.label.lower(),) if lex else (), pos, out)
        pos += len(words(c))
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


def limit_hit(text):
    """True for the message the claude command returns instead of an answer
    once the subscription's usage limit is reached."""
    return bool(text) and bool(re.search(r"hit your .*limit", text))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--failed', required=True, help='repair output with candidates (k-best run)')
    ap.add_argument('--out', required=True)
    ap.add_argument('--n', type=int, default=60)
    ap.add_argument('--rounds', type=int, default=3)
    ap.add_argument('--extra-rounds', type=int, default=3, help='more rounds for sentences of 20 words or more')
    ap.add_argument('--max-points', type=int, default=8, help='failure points shown per round')
    ap.add_argument('--max-context', type=int, default=40000, help='characters of grammar definitions')
    ap.add_argument('--parallel', type=int, default=4)
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--reuse', help='log.jsonl of an earlier run with the same settings: its sentences are copied, not rerun')
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
    reused = {}
    if args.reuse:
        with open(args.reuse, encoding='utf-8') as f:
            for line in f:
                r = json.loads(line)
                if not any(limit_hit(s.get('response')) for s in r['rounds']):
                    reused[r['id']] = r
        print(f'reusing {len(reused)} sentences from {args.reuse}', flush=True)
    stop = threading.Event()          # set when the usage limit is reached
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

    def failures(sid, tree):
        """Every failure that can be seen before any is fixed: words the
        lexicon does not license with their type, then unification failures.
        After a failure at node f, the subtrees beside the path from the
        top to f are replayed on their own, recursively."""
        out = []
        for path, leaf, rules, pos in leaf_paths(tree):
            if not leaf.entry.startswith('entry:') and not lx.lookup(leaf.forms, leaf.entry.lower(), rules):
                out.append((path, f'missing lexical entry: the lexicon has no entry of type '
                                  f'{leaf.entry} for "{" ".join(leaf.forms)}" (with the lexical rules above it)'))

        def walk(sub, path, start):
            with lock:
                fg.reset()
                try:
                    replay_with_entries(fg, lx, sub, toks[sid][start:], strict=False)
                    return
                except ReplayFailure as e:
                    where, cause = e.where.split()[0], str(e.cause)
            f = path + where[1:]
            out.append((f, cause))
            node, here, steps = sub, path, f[len(path):].split('.')[1:]
            for k in steps:
                pos = start
                for i, c in enumerate(node.children):
                    if i != int(k):
                        walk(c, f'{here}.{i}', pos)
                    pos += len(words(c))
                start += sum(len(words(c)) for c in node.children[:int(k)])
                node, here = node.children[int(k)], f'{here}.{k}'

        walk(tree, '0', 0)
        seen, uniq = set(), []
        for f, c in out:
            if f not in seen:
                seen.add(f)
                uniq.append((f, c))
        return uniq

    def grammar_context(tree, node, skip=None):
        skip = set() if skip is None else skip
        try:
            sub = node_at(tree, node)
        except Exception:
            sub = tree
        names = [n for n in sorted(labels(sub)) if n.lower() not in skip][:12]
        skip.update(n.lower() for n in names)
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
        rounds = args.rounds + (args.extra_rounds if len(forms) >= 20 else 0)
        for rnd in range(rounds):
            if verdict[0] == 'accepted':
                break
            fails = failures(sid, tree) or [(verdict[1], verdict[2])]
            shown = fails[:args.max_points]
            context, used = [], set()
            for node, _ in shown:
                c = grammar_context(tree, node, skip=used)
                if c:
                    context.append(c)
            report = []
            for node, cause in shown:
                try:
                    span = ' '.join(words(node_at(tree, node)))
                except Exception:
                    span = '?'
                report.append(f'- node [{node}] ("{span}"): {cause}')
            prompt = '\n'.join([
                'Sentence: ' + ' '.join(forms),
                '', 'Current derivation (node ids in brackets):', *numbered(tree),
                '', f'Replay finds {len(fails)} independent failure point(s)' +
                (f' (the first {len(shown)} are shown)' if len(fails) > len(shown) else '') + ':', *report,
                'Subtrees that are not listed replay correctly on their own; keep them unless the analysis '
                'above them must change. Fix all listed points in this answer, preferably by replacing small '
                'subtrees (one REPLACE line per point). Failures higher up in the tree only become visible once '
                'these are fixed.',
                '', 'Lexical types the lexicon allows for each word:', lexicon_options(lx, forms),
                '', 'Grammar definitions of the rules and types under the failing nodes:',
                '\n\n'.join(context)[:args.max_context],
                *(['', 'Earlier attempts in this conversation and why they failed:'] + history if history else []),
            ])
            if stop.is_set():
                return None
            data = call(args.model, system, prompt, args.out)
            text = data.get('result') or ''
            if limit_hit(text):
                stop.set()
                print('usage limit reached: ' + text.strip(), flush=True)
                return None
            step = {'round': rnd + 1, 'failure_points': [list(x) for x in fails], 'response': text,
                    'usage': data.get('usage'), 'cost': data.get('total_cost_usd'), 'seconds': data.get('seconds')}
            new, done, problems = tree, [], []
            for m in re.finditer(r'^REPLACE\s+\[?([\d.]+)\]?\s*:\s*(\(.*)$', text, re.M):
                path = m.group(1).rstrip('.')
                if any(path == d or path.startswith(d + '.') or d.startswith(path + '.') for d in done):
                    problems.append(f'[{path}] overlaps another replacement; ignored')
                    continue
                try:
                    raw = m.group(2).strip()
                    try:
                        sub = parse(raw)
                    except Exception:
                        sub = parse(balanced(raw))
                        step['repaired_brackets'] = step.get('repaired_brackets', 0) + 1
                    old = node_at(new, path)
                    if words(sub) != words(old):
                        problems.append(f'the replacement for [{path}] covers "{" ".join(words(sub))}", '
                                        f'not "{" ".join(words(old))}"; ignored')
                        continue
                    new = replace_at(new, path, sub)
                    done.append(path)
                except Exception as e:
                    problems.append(f'unreadable replacement for [{path}]: {e}; ignored')
            if problems:
                step['problems'] = problems
            if not done:
                problems.append('no usable REPLACE line')
                step['problems'] = problems
            else:
                tree = new
                verdict = check(sid, tree)
            step['verdict'] = list(verdict)
            log['rounds'].append(step)
            note = '; '.join(problems)
            if done:
                note = (note + '; ' if note else '') + f'replaced {", ".join("[" + d + "]" for d in done)}'
                if verdict[0] == 'rejected':
                    note += ' (the derivation above now includes these changes)'
            history.append(f'- attempt {rnd + 1}: {note}')
        log['final'] = list(verdict)
        log['derivation'] = render(tree)
        return log

    results = []
    with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool, \
            open(os.path.join(args.out, 'log.jsonl'), 'w', encoding='utf-8') as out:
        for log in pool.map(lambda r: reused.get(r['id']) or (None if stop.is_set() else run(r)), sample):
            if log is None:           # stopped by the usage limit; rerun later with --reuse
                continue
            results.append(log)
            out.write(json.dumps(log, ensure_ascii=False) + '\n')
            out.flush()
            v = log['final']
            print(f"{len(results)}/{len(sample)} {v[0]}{' gold MRS' if v[0] == 'accepted' and v[1] else ''} "
                  f"after {len(log['rounds'])} rounds", flush=True)
    st = collections.Counter()
    for log in results:
        st['sentences'] += 1
        band = 'under 20 words' if len(log['forms']) < 20 else '20 words or more'
        st[f'sentences {band}'] += 1
        st[f'accepted {band}'] += log['final'][0] == 'accepted'
        st[f'gold MRS {band}'] += log['final'][0] == 'accepted' and bool(log['final'][1])
        st['accepted'] += log['final'][0] == 'accepted'
        st['accepted with gold MRS'] += log['final'][0] == 'accepted' and bool(log['final'][1])
        st['calls'] += len(log['rounds'])
        for step in log['rounds']:
            st['cost_usd_equivalent'] += step.get('cost') or 0
            st['seconds'] += step.get('seconds') or 0
            st['answers with problems'] += 'problems' in step
            st['answers with repaired brackets'] += 'repaired_brackets' in step
        st[f"accepted after {len(log['rounds'])} rounds"] += log['final'][0] == 'accepted'
    summary = {'args': {k: v for k, v in vars(args).items() if k in ('n', 'rounds', 'extra_rounds', 'max_points', 'model', 'seed')}, 'stats': dict(st)}
    if len(results) < len(sample):
        summary['incomplete'] = f'{len(sample) - len(results)} sentences not run (usage limit); rerun with --reuse'
    with open(os.path.join(args.out, 'summary.json'), 'w') as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
