#!/usr/bin/env python3
"""Local demo: type a sentence, see Orca's analysis (and ACE's, to compare).

Serves docs/demo/index.html and a JSON endpoint, POST /api/parse with
{"sentence": "...", "ace": true|false}. The models stay loaded; one
sentence is parsed at a time.

Usage:
    demo_server.py [--port 8017] [--host 127.0.0.1] [--tagger MODEL_DIR]

From another computer, forward the port first:
    ssh -L 8017:localhost:8017 HOST     then open http://localhost:8017
"""
import argparse
import http.server
import json
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

from orca_parse import DEFAULTS, Parser, ace_parse, dmrs_json  # noqa: E402
from ace_sign import replay_sign  # noqa: E402

PAGE = os.path.join(HERE, '..', 'docs', 'demo', 'index.html')
LOCK = threading.Lock()
PARSER = None
MAX_CHARS = 1000
MAX_WORDS = 60           # longer sentences are refused
PER_MINUTE = 30          # requests per visitor per minute
MAX_WAITING = 4          # requests waiting for the parser; more get "busy"
ACE_TIMEOUT = 10         # seconds for the ACE comparison
RECENT = defaultdict(deque)
WAITING = 0
COUNT_LOCK = threading.Lock()


def measured_note():
    """One line on how this pipeline does from raw text on the dev set, if measured."""
    path = os.path.join(HERE, '..', 'analysis', 'mrs', f'dev-{PARSER.tagger_name.replace("tagger-", "").replace("-bert", "")}-rawtext.json')
    if not os.path.exists(path):
        return ''
    r = json.load(open(path))
    c, n = r['counts'], r['counts']['sentences']
    return (f"Measured from raw text on the {n:,} development sentences of the 2025 treebank: "
            f"{100 * c['same MRS'] / n:.1f}% get exactly the gold meaning, {100 * c['with MRS'] / n:.1f}% get an analysis, "
            f"{r['sentences per second']:.1f} sentences per second.")


from fragments import mrs_view  # noqa: E402  (shared with orca_parse's fragment output)


def fs_view(fg, root, limit=150000):
    """The whole feature structure as a node table for the page to unfold:
    {root, nodes: {id: [type, [[feature, id], ...]]}}; shared nodes appear once."""
    from orca.tfs import _fastdag as C
    nodes, todo = {}, [root]
    while todo and len(nodes) < limit:
        n = C.deref(todo.pop())
        if n in nodes:
            continue
        try:
            n2 = fg._check(C.expand(n))
        except Exception:
            n2 = n
        arcs = [(f, C.deref(v)) for f, v in fg.arcs(n2)]
        nodes[n] = [fg.type(n2), [[f, v] for f, v in arcs]]
        todo.extend(v for _, v in arcs)
    return {'root': C.deref(root), 'nodes': nodes, 'truncated': bool(todo)}


# How the sentence is analyzed; the request's "method" picks one. Chart is the most accurate on dev and the default.
METHODS = {'chart': ('chart', None),        # the tagger's candidate lexical entries, then a chart parser (ACE) limited to them
           'fallback': ('fallback', None),  # label, replay, repair; the limited chart parser only where that finds nothing
           'replay': ('replay', None),      # label, replay, repair: Orca's own method
           'first': ('replay', 1)}          # label and replay only: the tagger's first derivation, no repair
BUDGET = None                               # the parser's own repair budget, remembered at start
READINGS, MARGIN = 5, 1.25   # several readings (O97): at most 5, within 1.25 (MaxEnt, log space) of the best


def reading_options(req):
    """readings and margin from the request: readings 1-10 (default 5), margin >= 0 or null for none (default 1.25)."""
    try:
        k = min(10, max(1, int(req.get('readings', READINGS))))
    except (TypeError, ValueError):
        k = READINGS
    mg = req.get('margin', MARGIN)
    try:
        mg = None if mg is None else max(0.0, float(mg))
    except (TypeError, ValueError):
        mg = MARGIN
    return k, mg


def reading_tree(rd):
    """The derivation tree of a reading, in the page's tree format."""
    try:
        if rd.get('_tree') is not None:
            return PARSER.tree_json(rd['_tree'])
        if rd.get('_ace_derivation'):
            from delphin import derivation as D
            from encode_treebank import to_tree
            return PARSER.tree_json(to_tree(D.from_string(rd['_ace_derivation'])))
    except Exception:
        return None
    return None


def reading_fs(rd, path):
    """The whole sign of a reading: replayed from its derivation (Orca's) or rebuilt from ACE's derivation."""
    if rd.get('_tree') is not None:
        try:
            PARSER.fg.reset()
            fs, _ = PARSER.fg.replay_tree(rd['_tree'], path)
            return fs_view(PARSER.fg, fs), None
        except Exception as e:
            return None, f'could not rebuild this reading\'s sign ({type(e).__name__})'
    if rd.get('_ace_derivation'):
        sign, how = replay_sign(PARSER.fg, rd['_ace_derivation'])
        return (fs_view(PARSER.fg, sign), None) if sign is not None else (None, how)
    return None, 'no derivation'


def reading_views(r):
    """The readings list for the page: the first is the top-level analysis; the others carry their own
    MRS view, DMRS and tree. Their feature structures are fetched on demand (they can be large)."""
    out = []
    for i, rd in enumerate(r.get('readings') or []):
        v = {'probability': rd.get('probability'), 'maxent score': rd.get('maxent score')}
        if i > 0:
            m = rd.get('_mrs_obj')
            v['mrs'] = rd.get('mrs')
            v['mrs_view'] = mrs_view(m)
            try:
                v['dmrs'] = dmrs_json(m) if m is not None else None
            except Exception:
                v['dmrs'] = None
            v['derivation'] = reading_tree(rd)
        out.append(v)
    return out


def same_mrs(a, b):
    from delphin import mrs as M
    from compare_mrs import normalized
    try:
        return bool(M.is_isomorphic(normalized(a), normalized(b), properties=False))
    except Exception:
        return None


TYPES = None             # the grammar's definitions for the page's type lookup (built in main)
LOOKUPS_PER_MINUTE = 240
RECENT_LOOKUPS = defaultdict(deque)
_SUPERS = re.compile(r':[=+<]\s*((?:[^\s&\[\]"<>,.#]+\s*&\s*)*[^\s&\[\]"<>,.#]+)')
_KIND_BY_FILE = {'constructions.tdl': 'syntactic rule', 'inflr.tdl': 'lexical rule', 'lexrinst.tdl': 'lexical rule',
                 'lexrinst-tok.tdl': 'lexical rule', 'lexicon.tdl': 'lexical entry', 'lexicon-rbst.tdl': 'lexical entry',
                 'gle.tdl': 'generic lexical entry', 'roots.tdl': 'root condition'}


def build_types(grammar_file, hierarchy):
    """What the page's type lookup needs: the grammar's definitions as written (kelp.docs.Lookup), the
    authored type hierarchy in both directions, and for each type the instances (rules, entries) defined from it."""
    from kelp.docs import Lookup
    lk = Lookup(os.path.dirname(os.path.abspath(grammar_file)))
    parents = {t: list(ps) for t, ps in hierarchy.parents.items()}
    children = defaultdict(list)
    for t, ps in parents.items():
        for q in ps:
            children[q].append(t)
    instances = defaultdict(list)
    for name, d in lk.info.items():
        if name not in parents and d['type'] in parents:
            instances[d['type']].append(name)
    return {'lookup': lk, 'parents': parents, 'children': children, 'instances': instances}


def type_view(query, limit=300):
    """One name in the grammar: what it is, its documentation, the types above and below it, and its definition."""
    lk, parents = TYPES['lookup'], TYPES['parents']
    q = query.strip().lower()[:200]
    got = lk.get(q)
    defs = got['definitions']
    info = lk.info.get(q) or {}
    is_type = q in parents
    if is_type:
        supers = parents[q]
    else:                                  # an instance (rule, lexical entry): the types its definition names
        m = _SUPERS.search(re.sub(r'%(?:prefix|suffix)[^\n]*\n|""".*?"""', '', defs[0]['text'], flags=re.S)) if defs else None
        supers = [t.strip().lower() for t in m.group(1).split('&')] if m else []
        supers = [t for t in supers if t in parents]
    kind = ('type' if is_type else _KIND_BY_FILE.get(defs[0]['file'], 'instance') if defs else None)
    if is_type and q.endswith('_le'):
        kind = 'lexical type'
    subs, inst = sorted(TYPES['children'].get(q, [])), sorted(TYPES['instances'].get(q, []))
    return {'name': q, 'found': bool(defs) or is_type, 'kind': kind, 'doc': info.get('doc', ''), 'ex': info.get('ex', []),
            'supertypes': supers, 'subtypes': subs[:limit], 'subtypes total': len(subs),
            'instances': inst[:limit], 'instances total': len(inst), 'definitions': defs}


class Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            with open(PAGE, encoding='utf-8') as f:
                self._send(200, f.read(), 'text/html; charset=utf-8')
        elif self.path == '/api/info':
            self._send(200, json.dumps({'tagger': PARSER.tagger_name, 'note': measured_note()}), 'application/json')
        elif self.path == '/api/loaded':
            # the project files this process has loaded: deploy_demo.sh restarts only when one of them changed
            root = os.path.realpath(os.path.join(HERE, '..')) + os.sep
            files = {os.path.realpath(f) for f in (getattr(m, '__file__', None) for m in list(sys.modules.values())) if f}
            self._send(200, json.dumps(sorted(f[len(root):] for f in files if f.startswith(root) and '.venv' not in f)), 'application/json')
        elif self.path.startswith('/api/type?'):
            from urllib.parse import parse_qs, urlsplit
            name = (parse_qs(urlsplit(self.path).query).get('name') or [''])[0]
            if self.limited(RECENT_LOOKUPS, LOOKUPS_PER_MINUTE):
                self._send(429, json.dumps({'error': 'Too many lookups. Please wait a little.'}), 'application/json')
            elif not name.strip() or TYPES is None:
                self._send(400, json.dumps({'error': 'no name given'}), 'application/json')
            else:
                self._send(200, json.dumps(type_view(name), ensure_ascii=False), 'application/json')
        else:
            self._send(404, 'not found', 'text/plain')

    def visitor(self):
        # behind a tunnel or a reverse proxy every request comes from 127.0.0.1; the proxy passes the real address on
        if self.client_address[0] in ('127.0.0.1', '::1'):
            return self.headers.get('CF-Connecting-IP') or self.headers.get('X-Real-IP') or self.client_address[0]
        return self.client_address[0]

    def limited(self, recent=RECENT, per_minute=None):
        now, q = time.time(), recent[self.visitor()]
        with COUNT_LOCK:
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= (per_minute or PER_MINUTE):
                return True
            q.append(now)
        return False

    def do_POST(self):
        global WAITING
        if self.path != '/api/parse':
            self._send(404, 'not found', 'text/plain')
            return
        if self.limited():
            self._send(429, json.dumps({'error': f'Too many requests: at most {PER_MINUTE} a minute. Please wait a little.'}), 'application/json')
            return
        with COUNT_LOCK:
            busy = WAITING >= MAX_WAITING
            if not busy:
                WAITING += 1
        if busy:
            self._send(503, json.dumps({'error': 'The parser is busy. Please try again in a moment.'}), 'application/json')
            return
        try:
            n = int(self.headers.get('Content-Length', 0))
            req = json.loads(self.rfile.read(min(n, 100_000)) or b'{}')
            text = ' '.join(str(req.get('sentence', '')).split())[:MAX_CHARS]
            if not text:
                self._send(400, json.dumps({'error': 'empty sentence'}), 'application/json')
                return
            if len(text.split()) > MAX_WORDS:
                self._send(400, json.dumps({'error': f'Please enter at most {MAX_WORDS} words.'}), 'application/json')
                return
            with LOCK:
                PARSER.readings, PARSER.margin = reading_options(req)
                method = req.get('method') if req.get('method') in METHODS else 'chart'
                PARSER.mode, budget = METHODS[method]
                PARSER.args.budget = budget or BUDGET
                r = PARSER.parse(text)
                fs_for = req.get('fs_for')
                if fs_for is not None:                    # the sign of one further reading, fetched when its tab opens
                    rds = r.get('readings') or []
                    try:
                        i = int(fs_for)
                    except (TypeError, ValueError):
                        i = -1
                    if not 0 <= i < len(rds):
                        self._send(400, json.dumps({'error': 'no such reading'}), 'application/json')
                        return
                    fsv, note = reading_fs(rds[i], r.get('_tokens'))
                    self._send(200, json.dumps({'reading': i, 'fs': fsv, 'fs_note': note}, ensure_ascii=False), 'application/json')
                    return
                m = r.pop('_mrs_obj', None)
                r['mrs_view'] = mrs_view(m)
                fs = r.pop('_fs', None)
                ad = r.pop('_ace_derivation', None)
                if fs is not None:
                    r['fs'] = fs_view(PARSER.fg, fs)
                elif ad:                                  # chart mode: the sign of ACE's restricted parse, rebuilt by replay
                    sign, how = replay_sign(PARSER.fg, ad)
                    r['fs'] = fs_view(PARSER.fg, sign) if sign is not None else None
                    r['fs_note'] = None if sign is not None else how
                else:
                    r['fs'] = None
                if r.get('readings'):
                    r['readings'] = reading_views(r)
                r.pop('_tokens', None)
                if req.get('ace'):
                    a = ace_parse(text, timeout=ACE_TIMEOUT)
                    am = a.pop('_mrs_obj', None)
                    a['mrs_view'] = mrs_view(am)
                    der = a.pop('_derivation', None)       # ACE prints no feature structure: rebuild it by replaying its derivation
                    if der:
                        try:                               # the same tree view as Orca's derivation
                            from delphin import derivation as D
                            from encode_treebank import to_tree
                            a['derivation'] = PARSER.tree_json(to_tree(D.from_string(der)))
                        except Exception:
                            a['derivation'] = None
                        t0 = time.perf_counter()           # not ACE's time: Orca rebuilding the sign for display
                        sign, how = replay_sign(PARSER.fg, der)
                        a['sign seconds'] = time.perf_counter() - t0
                        a['fs'] = fs_view(PARSER.fg, sign) if sign is not None else None
                        a['fs_note'] = None if sign is not None else how
                    a['same as orca'] = same_mrs(m, am) if m is not None and am is not None else None
                    r['ace'] = a
            self._send(200, json.dumps(r, ensure_ascii=False), 'application/json')
        except Exception as e:
            self._send(500, json.dumps({'error': f'{type(e).__name__}: {e}'[:500]}), 'application/json')
        finally:
            with COUNT_LOCK:
                WAITING -= 1

    def log_message(self, fmt, *args):
        # request line and status only; what visitors type is not logged
        sys.stderr.write('%s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), fmt % args))


def main():
    global PARSER
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8017)
    ap.add_argument('--tagger', default=DEFAULTS['tagger'])
    args = ap.parse_args()
    PARSER = Parser(tagger=args.tagger, fragments=True, mode='chart')   # the demo shows one sentence at a time: the most accurate mode
    PARSER.parse('The dog barked.')
    global TYPES, BUDGET
    BUDGET = PARSER.args.budget
    TYPES = build_types(DEFAULTS['grammar'], PARSER.fg.h)
    srv = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Orca demo ready: http://{args.host}:{args.port}', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
