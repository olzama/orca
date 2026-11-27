"""Review of two given analyses per sentence, side by side, one verdict per item.

Usage:
    python -m kelp.review --input FILE.jsonl [--grammar ERG_DIR/english.tdl] [--labeled]
                          [--author NAME] [--explain PROVIDER] [--explain-model MODEL] [--explain-ahead]
                          [--port 8768] [--host 127.0.0.1]

Input: one JSON object per line,
    {"id": "profile/i-id", "sentence": "...",
     "group": "g017", "group_label": "...", "group_size": 36,          (optional)
     "example": true,                    (optional: the item that stands for its group)
     "a": {"label": "gold", "derivation": "(root_strict ...)", "mrs": "[ LTOP: ... ]"},
     "b": {"label": "orca", "derivation": "...", "mrs": "..."}}
with the reference analysis in "a". A side without an analysis has null for
derivation and mrs.

Sides are shown blind unless --labeled is given: which of a and b is on the
left depends on the item's group (or on its id, for an item without a group), and the labels appear once a verdict is given.

Explanations from the model are kept in FILE.explanations.json, so each item
is asked about once. With --explain-ahead they are all fetched in the background.

Verdicts are appended to FILE.verdicts.jsonl, one line per decision; the last
line of an id counts:
    {"id", "group", "verdict": "a" | "b" | "both" | "neither" | "", "note",
     "shown": {"left": "a" | "b", "right": ...}, "author", "time"}

Groups. Items with the same "group" form a group; the page lists one example
per group (the first member marked "example", or the first member) and the
other members under it. A verdict on the example holds for every member that
has no verdict of its own. An item can be taken out of its group or put into
another one; each such change is appended to FILE.groups.jsonl
    {"id", "from": the input's group, "to": group or null, "author", "time"}
and FILE.resolved.jsonl is rewritten after every change with one line per item:
    {"id", "group": as it is now, "verdict", "from": "own" | "group" | "", "example"}

With --grammar, rule, type and entry names can be looked up, and the
grammar's notes on them are shown. No parser is loaded.
"""
import argparse
import getpass
import hashlib
import json
import os
import re
import subprocess
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from delphin import derivation, dmrs
from delphin.codecs import simplemrs

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
VERDICTS = ('a', 'b', 'both', 'neither', '')


def _surface(terminals, sentence):
    """The words of a lexical entry as they are in the sentence, from the
    character positions of its tokens; otherwise the forms in the derivation."""
    at = [(int(a), int(b)) for t in terminals for tok in (t.tokens or [])
          for a, b in re.findall(r'\+FROM\s+\\?"(\d+)\\?".*?\+TO\s+\\?"(\d+)\\?"', str(tok.tfs), re.S)]
    if at and sentence and max(b for _, b in at) <= len(sentence):
        return sentence[min(a for a, _ in at):max(b for _, b in at)]
    return ' '.join(t.form for t in terminals)


def tree_json(text, sentence=''):
    """A derivation string as (root condition, tree, words). Unary chains are
    one node, as in Kelp's trees. Spans count the words between spaces, so that
    two trees of one sentence have comparable spans even where one of them has
    a lexical entry of several words."""
    d = derivation.from_string(text)
    term = lambda n: [t for t in n.daughters if isinstance(t, derivation.UDFTerminal)]
    root = None
    if d.is_root():
        root, d = d.entity, d.daughters[0]
    words = []

    def walk(n):
        labels, start = [], len(words)
        while not term(n) and len(n.daughters) == 1:
            labels.append(n.entity)
            n = n.daughters[0]
        if term(n):
            words.extend(_surface(term(n), sentence).split() or ['?'])
            labels.append(n.type or n.entity)
            return {'labels': labels, 'entry': n.entity, 'start': start, 'end': len(words), 'children': []}
        labels.append(n.entity)
        kids = [walk(c) for c in n.daughters]
        return {'labels': labels, 'entry': None, 'start': start, 'end': len(words), 'children': kids}

    return root, walk(d), words


def graph_json(text):
    """A SimpleMRS string as the DMRS dictionary that Kelp's page draws, with
    character positions where the MRS has them."""
    d = dmrs.from_mrs(simplemrs.decode(text))
    return {'top': d.top, 'index': d.index,
            'nodes': [{'id': n.id, 'pred': str(n.predicate), 'carg': n.carg, 'props': dict(n.properties),
                       'from': n.cfrom, 'to': n.cto} for n in d.nodes],
            'links': [{'from': k.start, 'to': k.end, 'role': k.role, 'post': k.post} for k in d.links]}


def side_json(side, sentence=''):
    out = {'label': (side or {}).get('label', ''), 'tree': None, 'root': None, 'words': [], 'dmrs': None, 'error': ''}
    if not side:
        return out
    try:
        if side.get('derivation'):
            out['root'], out['tree'], out['words'] = tree_json(side['derivation'], sentence)
        if side.get('mrs'):
            out['dmrs'] = graph_json(side['mrs'])
    except Exception as e:                  # one bad analysis must not stop the review
        out['error'] = f'{type(e).__name__}: {e}'[:300]
    return out


def _nodes(tree):
    out = [tree] if tree else []
    for c in (tree or {}).get('children', []):
        out += _nodes(c)
    return out


def _tree_notes(side, other, most=10):
    """The widest nodes of one side's tree that the other tree lacks, for the model."""
    key = lambda n: (n['start'], n['end'], tuple(n['labels']), n['entry'])
    theirs = {key(n) for n in _nodes(other['tree'])}
    mine = [n for n in _nodes(side['tree']) if key(n) not in theirs]
    mine.sort(key=lambda n: (n['start'] - n['end'], n['start']))
    return [f'tree: {" > ".join(str(x) for x in n["labels"])}' + (f' (lexical entry {n["entry"]})' if n['entry'] else '')
            + f' over "{" ".join(side["words"][n["start"]:n["end"]])}"' for n in mine[:most]]


class Review:
    def __init__(self, path, labeled=False, author=None, explain=None):
        self.path, self.labeled, self.explain = path, labeled, explain
        self.out = re.sub(r'\.jsonl?$', '', path) + '.verdicts.jsonl'
        self.author = author or getpass.getuser()
        self.lock = threading.Lock()
        self.items, self.verdicts = [], {}
        base = re.sub(r'\.jsonl?$', '', path)
        self.groups_file, self.resolved = base + '.groups.jsonl', base + '.resolved.jsonl'
        self.moves, self.labels = {}, {}        # item id -> the group it was put in (None: none); group -> label
        self.notes = re.sub(r'\.jsonl?$', '', path) + '.explanations.json'     # {id: {difference, a, b}}
        self.explained = {}
        if os.path.exists(self.notes):
            with open(self.notes, encoding='utf-8') as f:
                self.explained = json.load(f)
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    # one placement per group, so that its members can be compared with its example
                    by = rec['group'] if rec.get('group') is not None else rec['id']
                    flip = not labeled and hashlib.sha1(str(by).encode()).digest()[0] % 2 == 1
                    self.items.append({'id': str(rec['id']), 'sentence': rec.get('sentence', ''),
                                       'group': rec.get('group'), 'example': bool(rec.get('example')),
                                       'group_size': rec.get('group_size'),
                                       'left': 'b' if flip else 'a', 'right': 'a' if flip else 'b',
                                       'a': side_json(rec.get('a'), rec.get('sentence', '')),
                                       'b': side_json(rec.get('b'), rec.get('sentence', ''))})
                    if rec.get('group') is not None:
                        self.labels.setdefault(rec['group'], rec.get('group_label') or str(rec['group']))
        self.by_id = {it['id']: it for it in self.items}
        if os.path.exists(self.groups_file):
            with open(self.groups_file, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        m = json.loads(line)
                        if m['id'] in self.by_id:
                            if m['to'] == self.by_id[m['id']]['group']:
                                self.moves.pop(m['id'], None)
                            else:
                                self.moves[m['id']] = m['to']
        if os.path.exists(self.out):
            with open(self.out, encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        v = json.loads(line)
                        self.verdicts[v['id']] = v

    def _group(self, it):
        """The group the item is in now: its own, or where the reviewer put it (None: in no group)."""
        return self.moves[it['id']] if it['id'] in self.moves else it['group']

    def entry(self, it):
        """One item as the page needs it. Labels are held back while the item is blind and has no verdict."""
        v = self.verdicts.get(it['id'], {})
        hide = not self.labeled and not v.get('verdict')
        sides = {}
        for where in ('left', 'right'):
            s = dict(it[it[where]])
            s['label'] = '' if hide else s['label']
            s['is'] = None if hide else it[where]
            sides[where] = s
        return dict(self._status(it), sentence=it['sentence'], group0=it['group'], example=it['example'],
                    group_size=it['group_size'], left=sides['left'], right=sides['right'], explanation=self._shown(it))

    def _status(self, it):
        v = self.verdicts.get(it['id'], {})
        return {'id': it['id'], 'group': self._group(it), 'moved': it['id'] in self.moves,
                'verdict': {'a': it['left'] == 'a' and 'left' or 'right', 'b': it['left'] == 'b' and 'left' or 'right'}
                .get(v.get('verdict'), v.get('verdict', '')), 'note': v.get('note', '')}

    def listing(self):
        return [self.entry(it) for it in self.items]

    def changed(self, ident):
        """What the page needs after a change: the changed item in full, and the status of every item."""
        return {'item': self.entry(self.by_id[ident]), 'status': [self._status(it) for it in self.items]}

    def move(self, ident, to):
        """Put an item into another group, into none (to=None), or back (to='')."""
        with self.lock:
            it = self.by_id[ident]
            if to == '' or to == it['group']:
                self.moves.pop(ident, None)
            elif to is None or to in self.labels:
                self.moves[ident] = to
            else:
                raise ValueError(f'no such group: {to}')
            rec = {'id': ident, 'from': it['group'], 'to': self._group(it), 'author': self.author,
                   'time': time.strftime('%Y-%m-%dT%H:%M:%S')}
            with open(self.groups_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            self._resolve()

    def _resolve(self):
        """Write, for every item, its group as it is now and the verdict that
        holds for it: its own, or else that of its group's example (the first
        member marked as example, or the first member)."""
        members = {}
        for it in self.items:
            g = self._group(it)
            if g is not None:
                members.setdefault(g, []).append(it)
        rep = {g: next((m for m in ms if m['example']), ms[0]) for g, ms in members.items()}
        tmp = self.resolved + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            for it in self.items:
                g = self._group(it)
                own = self.verdicts.get(it['id'], {}).get('verdict', '')
                via = self.verdicts.get(rep[g]['id'], {}).get('verdict', '') if g is not None and not own else ''
                f.write(json.dumps({'id': it['id'], 'group': g, 'verdict': own or via,
                                    'from': 'own' if own else 'group' if via else '',
                                    'example': g is not None and rep[g] is it}, ensure_ascii=False) + '\n')
        os.replace(tmp, self.resolved)

    def judge(self, ident, verdict, note):
        """verdict: left, right, both, neither or ''."""
        with self.lock:
            it = self.by_id[ident]
            v = it[verdict] if verdict in ('left', 'right') else verdict
            if v not in VERDICTS:
                raise ValueError(f'unknown verdict: {verdict}')
            rec = {'id': ident, 'group': it['group'], 'verdict': v, 'note': note or '',
                   'shown': {'left': it['left'], 'right': it['right']}, 'author': self.author,
                   'time': time.strftime('%Y-%m-%dT%H:%M:%S')}
            with open(self.out, 'a', encoding='utf-8') as f:
                f.write(json.dumps(rec, ensure_ascii=False) + '\n')
                f.flush()
                os.fsync(f.fileno())
            self.verdicts[ident] = rec
            self._resolve()

    def _shown(self, it):
        e = self.explained.get(it['id'])
        return e and {'difference': e.get('difference', ''), 'left': e.get(it['left'], ''), 'right': e.get(it['right'], '')}

    def explain_item(self, ident):
        """What the two analyses disagree about, in plain English: asked of the
        model once per item and kept in a file next to the input."""
        from kelp import explain as X
        if self.explain is None:
            raise ValueError('this server has no model for explanations (see --explain)')
        it = self.by_id[ident]
        if ident not in self.explained:
            sides = [it['a'], it['b']]
            if not all(s['tree'] or s['dmrs'] for s in sides):
                raise ValueError('there is nothing to compare')
            facts = X.distinguishing([s['dmrs'] for s in sides]) if all(s['dmrs'] for s in sides) else [[], []]
            text = X.prompt(it['sentence'], [(k + 1, facts[k], _tree_notes(s, sides[1 - k])) for k, s in enumerate(sides)])
            answer = self.explain(text)                 # outside the lock: this takes seconds
            with self.lock:
                self.explained[ident] = {'difference': answer.get('difference', ''), 'a': answer.get('1', ''), 'b': answer.get('2', '')}
                tmp = self.notes + '.tmp'
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(self.explained, f, ensure_ascii=False, indent=1)
                os.replace(tmp, self.notes)
        return self._shown(it)

    def explain_ahead(self):
        """Explain every item that has no explanation yet; meant for a background thread."""
        for it in self.items:
            try:
                self.explain_item(it['id'])
            except Exception as e:                      # one failure must not stop the rest
                print(f'no explanation for {it["id"]}: {e}', flush=True)


def make_handler(review, docs, lookup, explainer):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, kind='application/json'):
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header('Content-Type', kind + '; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path, _, query = self.path.partition('?')
            query = urllib.parse.parse_qs(query)
            if path in ('/', '/index.html'):
                with open(os.path.join(STATIC, 'review.html'), 'rb') as f:
                    self._send(200, f.read(), 'text/html')
            elif path == '/api/review':
                self._send(200, {'file': os.path.basename(review.path), 'labeled': review.labeled,
                                 'explainer': explainer, 'groups': review.labels, 'items': review.listing()})
            elif path == '/api/docs':
                self._send(200, docs)
            elif path == '/api/lookup':
                if lookup is None:
                    self._send(404, {'error': 'the server was started without a grammar'})
                else:
                    self._send(200, lookup.get(query.get('name', [''])[0]))
            else:
                self._send(404, {'error': 'not found'})

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                if self.path == '/api/verdict':
                    review.judge(str(body['id']), body.get('verdict', ''), body.get('note', ''))
                    self._send(200, review.changed(str(body['id'])))
                elif self.path == '/api/move':
                    review.move(str(body['id']), body.get('to'))
                    self._send(200, review.changed(str(body['id'])))
                elif self.path == '/api/explain':
                    self._send(200, review.explain_item(str(body['id'])))
                else:
                    self._send(404, {'error': 'not found'})
            except KeyError:
                self._send(404, {'error': 'no such item'})
            except (ValueError, TypeError, OSError, subprocess.SubprocessError) as e:
                self._send(400, {'error': str(e)})

        def log_message(self, *args):
            pass

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input', required=True)
    ap.add_argument('--grammar', help="the grammar's top TDL file, for lookup and the grammar's notes")
    ap.add_argument('--labeled', action='store_true', help='show which side is which from the start')
    ap.add_argument('--author')
    ap.add_argument('--explain', default='auto', choices=['auto', 'none', 'claude-cli', 'anthropic', 'openai', 'gemini'])
    ap.add_argument('--explain-model')
    ap.add_argument('--explain-ahead', action='store_true',
                    help='ask the model about every item in the background, so that explanations are there when an item is opened')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8768)
    args = ap.parse_args()
    from kelp.explain import PROVIDERS, ask, choose
    provider = choose(args.explain)
    explain = (lambda text: ask(provider, args.explain_model, text)) if provider else None
    review = Review(args.input, args.labeled, args.author, explain)
    docs, lookup = {}, None
    if args.grammar:
        from kelp.docs import Lookup
        lookup = Lookup(os.path.dirname(os.path.abspath(args.grammar)))
        used = set()

        def note(n):
            entry = str(n['entry'] or '').lower()       # a leaf without its lexical type gets it from the grammar
            if entry and n['labels'][-1] == n['entry'] and lookup.info.get(entry, {}).get('type'):
                n['labels'][-1] = lookup.info[entry]['type']
            used.update(str(x).lower() for x in n['labels'] + [n['entry'] or ''])
            for c in n['children']:
                note(c)

        for it in review.items:
            for s in ('a', 'b'):
                if it[s]['tree']:
                    note(it[s]['tree'])
        docs = {name: d for name, d in lookup.info.items() if name in used}
    if args.explain_ahead and explain:
        threading.Thread(target=review.explain_ahead, daemon=True).start()
    bad = sum(bool(it[s]['error']) for it in review.items for s in ('a', 'b'))
    print(f'{len(review.items)} items, {len(review.verdicts)} with a verdict' + (f', {bad} analyses unreadable' if bad else ''), flush=True)
    print(f'Verdicts: {review.out}', flush=True)
    print(f'Kelp review is at http://{args.host}:{args.port}/', flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(review, docs, lookup, provider and PROVIDERS[provider][3])).serve_forever()


if __name__ == '__main__':
    main()
