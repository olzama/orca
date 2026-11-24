"""Input tokens for raw text, from the grammar's own preprocessing in ACE.

Orca replays derivations over token feature structures: the tokens after
REPP tokenization, POS tagging and the grammar's token mapping rules. For
treebank sentences these come with the gold derivation. For new text, ACE
is run with its chart limited to almost nothing, so that it stops after
token mapping, and with -vv, so that it prints the final token chart. No
parsing is done.

The token chart is a lattice. Each span usually has several tokens: one for
words the lexicon knows (+UW -) and others for generic entries (unknown
words, names, numbers). They are kept as alternatives; replay picks the
first one that unifies with the lexical entry (see FastGrammar._replay).
"""
import atexit
import os
import re
import select
import subprocess
import threading
import time

TOKEN_LINE = re.compile(r"^token #(\d+) le \S+ vtx \[(\d+)-(\d+)\] char \[(\d+)-(\d+)\] string '(.*?)' dag (#D\[.*)$")
DEBUG = re.compile(r'#D\[|\]|"(?:\\.|[^"\\])*"|<\d+>=?|[^\s\[\]"]+')


def to_tdl(dag):
    """ACE's debug print of a DAG, as the bracketed form that FastGrammar
    reads: `#D[type F: v ...]` becomes `type [ F v ... ]`, `<1>=` becomes
    `#1=`, and an atom `#D["x"]` becomes `"x"`."""
    toks = DEBUG.findall(dag)
    out, pos = [], 0

    def value():
        nonlocal pos
        t = toks[pos]
        if t.startswith('<'):
            pos += 1
            if t.endswith('='):
                out.append(f'#{t[1:-2]}=')
                return value()
            out.append(f'#{t[1:-1]}')
            return
        assert t == '#D[', (t, pos)
        pos += 1
        out.append(toks[pos])           # type or string
        pos += 1
        feats = []
        while toks[pos] != ']':
            feats.append(toks[pos].rstrip(':'))
            pos += 1
            feats.append(None)
            mark = len(out)
            value()
            feats[-1] = out[mark:]
            del out[mark:]
        pos += 1
        if feats:
            out.append('[')
            for i in range(0, len(feats), 2):
                out.append(feats[i])
                out.extend(feats[i + 1])
            out.append(']')

    value()
    return ' '.join(out)


def _uw(tdl):
    m = re.search(r'\+UW (?:#\d+=? )?([+-])', tdl)
    return m.group(1) if m else '?'


def _cls(tdl):
    m = re.search(r'\+CLASS (?:#\d+=? )?(\S+)', tdl)
    return m.group(1) if m else ''


def _form(tdl):
    m = re.search(r'\+FORM (?:#\d+=? )?("(?:\\.|[^"\\])*")', tdl)
    return m.group(1)[1:-1] if m else ''


class AceTokenizer:
    """One ACE process kept running for token mapping, fed one sentence at a time.

    Starting ACE for every sentence costs more than the token mapping itself
    (the grammar image is loaded each time), so the process is kept and each
    sentence is written to its stdin. ACE flushes its output after every item,
    and the output of an item ends with a `SKIP:` or `SENT:` line followed by
    two empty lines; reading stops there. stderr is discarded: the token chart
    (-vv) is printed on stdout.

    The process is restarted after a timeout (it is then still busy with the
    old sentence), when it dies, after `max_items` sentences, and in a forked
    child (a pipe must not be shared between processes)."""

    END_LINE = ('SKIP: ', 'SENT: ')

    def __init__(self, ace, grammar_dat, max_items=2000):
        self.cmd = [ace, '-g', grammar_dat, '-vv', '--max-chart-megabytes=1']
        self.max_items = max_items
        self.proc, self.pid, self.items = None, None, 0
        self.lock = threading.Lock()

    def _start(self):
        self.close()
        self.proc = subprocess.Popen(self.cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
        self.pid, self.items = os.getpid(), 0

    def close(self):
        p, self.proc = self.proc, None
        if p is not None and self.pid == os.getpid():
            try:
                p.kill()
                p.wait(timeout=5)
            except Exception:
                pass

    def _read_item(self, timeout):
        """stdout of the current item and how reading ended: 'done', 'timeout' or 'eof'."""
        fd, buf, end = self.proc.stdout.fileno(), b'', time.monotonic() + timeout
        while True:
            left = end - time.monotonic()
            if left <= 0:
                return buf.decode(errors='replace'), 'timeout'
            ready, _, _ = select.select([fd], [], [], left)
            if not ready:
                continue
            chunk = os.read(fd, 1 << 16)
            if not chunk:
                return buf.decode(errors='replace'), 'eof'
            buf += chunk
            if buf.endswith(b'\n\n\n'):
                text = buf.decode(errors='replace')
                last = [l for l in text.splitlines() if l]
                if last and any(l.startswith(self.END_LINE) for l in last[-12:]):
                    return text, 'done'

    def chart_text(self, sentence, timeout=10, retry_timeout=60):
        """ACE's stdout for one sentence, or None (same semantics as one ACE run per sentence:
        a timeout is retried once with `retry_timeout`; after a timeout, what was printed is
        used if token mapping finished)."""
        inp = (sentence.replace('\n', ' ') + '\n').encode()
        with self.lock:
            for t in (timeout, retry_timeout):
                if self.proc is None or self.pid != os.getpid() or self.proc.poll() is not None \
                        or self.items >= self.max_items:
                    self._start()
                try:
                    self.proc.stdin.write(inp)
                    self.proc.stdin.flush()
                except (BrokenPipeError, OSError):
                    self._start()
                    self.proc.stdin.write(inp)
                    self.proc.stdin.flush()
                self.items += 1
                text, how = self._read_item(t)
                if how == 'done':
                    return text
                self.close()                    # still busy with this sentence, or gone: start afresh next time
                if how == 'eof' or 'finished token mapping' in text:
                    return text                 # as one ACE run per sentence: what it printed before exiting
            return None


_TOKENIZERS = {}
_TOKENIZERS_LOCK = threading.Lock()


def _tokenizer(ace, grammar_dat):
    with _TOKENIZERS_LOCK:
        tk = _TOKENIZERS.get((ace, grammar_dat))
        if tk is None:
            tk = _TOKENIZERS[(ace, grammar_dat)] = AceTokenizer(ace, grammar_dat)
        return tk


@atexit.register
def _close_tokenizers():
    for tk in list(_TOKENIZERS.values()):
        tk.close()


def _chart_text_per_call(sentence, ace, grammar_dat, timeout, retry_timeout):
    """The old way: one ACE run per sentence (ORCA_TOKENS_PER_CALL=1)."""
    cmd = [ace, '-g', grammar_dat, '-vv', '--max-chart-megabytes=1']
    inp = sentence.replace('\n', ' ') + '\n'
    for t in (timeout, retry_timeout):
        try:
            p = subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=t)
            return p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            part = ''.join(x.decode(errors='replace') if isinstance(x, bytes) else (x or '') for x in (e.stdout, e.stderr))
            if 'finished token mapping' in part:
                return part
    return None


def token_chart(sentence, ace, grammar_dat, timeout=10, retry_timeout=60, per_call=None):
    """The final token chart of one sentence: [(start, end, cfrom, cto, tdl)].

    ACE is only asked for its token mapping, by default in one ACE process kept
    running (AceTokenizer); `per_call=True` or the environment variable
    ORCA_TOKENS_PER_CALL=1 runs ACE once per sentence instead. On a busy machine
    ACE can take longer than `timeout`, so a timeout is retried once with
    `retry_timeout`. If that also times out, whatever ACE printed is used if
    token mapping finished, else the sentence gets no tokens (the caller reports
    'no tokens') instead of the whole run failing."""
    if per_call is None:
        per_call = os.environ.get('ORCA_TOKENS_PER_CALL', '') not in ('', '0')
    if per_call:
        text = _chart_text_per_call(sentence, ace, grammar_dat, timeout, retry_timeout)
    else:
        text = _tokenizer(ace, grammar_dat).chart_text(sentence, timeout, retry_timeout)
    if text is None:
        return []
    out = []
    for line in text.splitlines():
        if line.startswith('finished token mapping'):
            break
        m = TOKEN_LINE.match(line)
        if m:
            out.append((int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)),
                        to_tdl(m.group(7))))
    return out


def known_words(lexicon):
    """Lower-cased words in the orthographies of the lexicon's entries."""
    return {w.lower() for _, orth in lexicon.by_type_orth for w in orth.split()}


def lattice_path(chart, known=None):
    """One path through the lattice, finest spans first, with the tokens of
    each span as alternatives: [(form, (tdl, ...), (cfrom, cto))].

    The form shown to the tagger imitates the treebank's derivations, where
    a word analyzed with a generic name entry keeps its case and other words
    are lower-cased. Which entry the parse will use is not known yet, so a
    word keeps its case when the grammar proposes a name token for it and
    the lexicon (`known`, from known_words) does not have the word. On the
    2025 dev set this gives the treebank's forms for 1,838 of 2,061
    sentences; the rest are mostly words such as "Palm" or "East" that the
    lexicon has but the treebank analyzes as names."""
    by_start = {}
    for s, e, cf, ct, tdl in chart:
        by_start.setdefault(s, {}).setdefault(e, []).append((cf, ct, tdl))
    if not by_start:
        return []
    end_vertex = max(e for s, e, *_ in chart)
    path, v = [], min(by_start)
    while v < end_vertex and v in by_start:
        e = min(by_start[v])
        toks = by_start[v][e]
        forms = sorted({_form(t[2]) for t in toks}, key=lambda f: (f != f.lower(), f))
        lower = forms[0].lower()
        cased = next((f for f in forms if f != f.lower()), lower)
        name = any(_cls(t[2]) == 'proper_ne' for t in toks)
        form = cased if name and known is not None and lower not in known else lower
        native = [t for t in toks if _uw(t[2]) == '-']
        order = native + [t for t in toks if t not in native]
        path.append((form, tuple(t[2] for t in order), (toks[0][0], toks[0][1])))
        v = e
    return path
