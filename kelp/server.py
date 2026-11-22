"""Kelp's server: one annotator, one profile.

Usage:
    python -m kelp.server --profile FOREST_PROFILE [--grammar ERG_DIR/english.tdl]
                          [--limit 150] [--port 8765] [--host 127.0.0.1]

With --grammar, Orca checks the trees of an item once at most --limit remain,
and the page shows the grammar's documentation and each tree's meaning.

Then open http://localhost:8765/ in a browser. From another machine, forward
the port first:  ssh -L 8765:localhost:8765 USER@THIS_MACHINE
"""
import argparse
import json
import os
import re
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kelp.docs import load_docs
from kelp.session import Session

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
_ITEM = re.compile(r'^/api/item/(\d+)$')


def make_handler(session, docs):
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
            m = _ITEM.match(path)
            try:
                if path in ('/', '/index.html'):
                    with open(os.path.join(STATIC, 'index.html'), 'rb') as f:
                        self._send(200, f.read(), 'text/html')
                elif path == '/api/items':
                    self._send(200, {'profile': os.path.basename(os.path.normpath(session.profile)),
                                     'items': session.summary()})
                elif m:
                    self._send(200, session.state(int(m.group(1)), int(query.get('show', ['0'])[0])))
                elif path == '/api/docs':
                    self._send(200, docs)
                else:
                    self._send(404, {'error': 'not found'})
            except KeyError:
                self._send(404, {'error': 'no such item'})

        def do_POST(self):
            m = _ITEM.match(self.path)
            if not m:
                return self._send(404, {'error': 'not found'})
            try:
                body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                self._send(200, session.act(int(m.group(1)), body.get('action'), body.get('constraint'),
                                            int(body.get('show', 0))))
            except KeyError:
                self._send(404, {'error': 'no such item'})
            except (ValueError, TypeError) as e:
                self._send(400, {'error': str(e)})

        def log_message(self, *args):
            pass

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--profile', required=True)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--grammar', help="the grammar's top TDL file; without it, no checks and no meanings")
    ap.add_argument('--author', help='the annotator name written to the profile (default: the login name)')
    ap.add_argument('--limit', type=int, default=150, help='list and check the trees of an item once at most this many remain')
    args = ap.parse_args()
    engine, docs, lextypes = None, {}, None
    if args.grammar:
        print(f'Loading the grammar {args.grammar} ...', flush=True)
        from kelp.engine import Engine
        engine = Engine(args.grammar)
        docs = load_docs(os.path.dirname(os.path.abspath(args.grammar)))
        lextypes = {name: d['type'] for name, d in docs.items() if d['type'].endswith('_le')}
    print(f'Loading {args.profile} ...', flush=True)
    session = Session(args.profile, engine=engine, limit=args.limit, lextypes=lextypes, author=args.author)
    used = {label.lower() for it in session.items.values() for n in it.chains.nodes for label in n.chain + n.labels}
    docs = {name: d for name, d in docs.items() if name in used}
    if engine:
        threading.Thread(target=session.check_ahead, daemon=True).start()
    print(f'{len(session.items)} items. Journal: {session.journal}', flush=True)
    print(f'Kelp is at http://{args.host}:{args.port}/', flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(session, docs)).serve_forever()


if __name__ == '__main__':
    main()
