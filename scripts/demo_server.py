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

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))

from orca_parse import DEFAULTS, Parser, ace_parse  # noqa: E402

PAGE = os.path.join(HERE, '..', 'docs', 'demo', 'index.html')
LOCK = threading.Lock()
PARSER = None
MAX_CHARS = 1000


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

    def do_POST(self):
        if self.path != '/api/parse':
            self._send(404, 'not found', 'text/plain')
            return
        try:
            n = int(self.headers.get('Content-Length', 0))
            req = json.loads(self.rfile.read(min(n, 100_000)) or b'{}')
            text = ' '.join(str(req.get('sentence', '')).split())[:MAX_CHARS]
            if not text:
                self._send(400, json.dumps({'error': 'empty sentence'}), 'application/json')
                return
            with LOCK:
                r = PARSER.parse(text)
                m = r.pop('_mrs_obj', None)
                if req.get('ace'):
                    a = ace_parse(text)
                    am = a.pop('_mrs_obj', None)
                    a['same as orca'] = same_mrs(m, am) if m is not None and am is not None else None
                    r['ace'] = a
            self._send(200, json.dumps(r, ensure_ascii=False), 'application/json')
        except Exception as e:
            self._send(500, json.dumps({'error': f'{type(e).__name__}: {e}'[:500]}), 'application/json')

    def log_message(self, fmt, *args):
        sys.stderr.write('%s %s\n' % (self.address_string(), fmt % args))


def main():
    global PARSER
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=8017)
    ap.add_argument('--tagger', default=DEFAULTS['tagger'])
    args = ap.parse_args()
    PARSER = Parser(tagger=args.tagger)
    PARSER.parse('The dog barked.')
    srv = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    print(f'Orca demo ready: http://{args.host}:{args.port}', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
