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
import sys
import threading
import time
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

from orca_parse import DEFAULTS, Parser, ace_parse  # noqa: E402
from ace_sign import replay_sign  # noqa: E402

PAGE = os.path.join(HERE, '..', 'docs', 'demo', 'index.html')
LOCK = threading.Lock()
PARSER = None
MAX_CHARS = 1000
MAX_WORDS = 60           # longer sentences are refused
PER_MINUTE = 10          # requests per visitor per minute
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


def same_mrs(a, b):
    from delphin import mrs as M
    from compare_mrs import normalized
    try:
        return bool(M.is_isomorphic(normalized(a), normalized(b), properties=False))
    except Exception:
        return None


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
        else:
            self._send(404, 'not found', 'text/plain')

    def visitor(self):
        # behind a tunnel every request comes from 127.0.0.1; the tunnel passes the real address on
        return self.headers.get('CF-Connecting-IP') or self.client_address[0]

    def limited(self):
        now, q = time.time(), RECENT[self.visitor()]
        with COUNT_LOCK:
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= PER_MINUTE:
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
                r = PARSER.parse(text)
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
                if req.get('ace'):
                    a = ace_parse(text, timeout=ACE_TIMEOUT)
                    am = a.pop('_mrs_obj', None)
                    a['mrs_view'] = mrs_view(am)
                    der = a.pop('_derivation', None)       # ACE prints no feature structure: rebuild it by replaying its derivation
                    if der:
                        sign, how = replay_sign(PARSER.fg, der)
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
    srv = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Orca demo ready: http://{args.host}:{args.port}', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
