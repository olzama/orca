"""Kelp's server: one annotator, one profile.

Usage:
    python -m kelp.server --profile FOREST_PROFILE [--port 8765] [--host 127.0.0.1]

Then open http://localhost:8765/ in a browser. From another machine, forward
the port first:  ssh -L 8765:localhost:8765 USER@THIS_MACHINE
"""
import argparse
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from kelp.session import Session

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
_ITEM = re.compile(r'^/api/item/(\d+)$')


def make_handler(session):
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
            path = self.path.split('?')[0]
            m = _ITEM.match(path)
            try:
                if path in ('/', '/index.html'):
                    with open(os.path.join(STATIC, 'index.html'), 'rb') as f:
                        self._send(200, f.read(), 'text/html')
                elif path == '/api/items':
                    self._send(200, {'profile': os.path.basename(os.path.normpath(session.profile)),
                                     'items': session.summary()})
                elif m:
                    self._send(200, session.state(int(m.group(1))))
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
                self._send(200, session.act(int(m.group(1)), body.get('action'), body.get('constraint')))
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
    args = ap.parse_args()
    print(f'Loading {args.profile} ...', flush=True)
    session = Session(args.profile)
    print(f'{len(session.items)} items. Journal: {session.journal}', flush=True)
    print(f'Kelp is at http://{args.host}:{args.port}/', flush=True)
    ThreadingHTTPServer((args.host, args.port), make_handler(session)).serve_forever()


if __name__ == '__main__':
    main()
