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
import re
import subprocess

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


def token_chart(sentence, ace, grammar_dat, timeout=10):
    """The final token chart of one sentence: [(start, end, cfrom, cto, tdl)]."""
    p = subprocess.run([ace, '-g', grammar_dat, '-vv', '--max-chart-megabytes=1'],
                       input=sentence.replace('\n', ' ') + '\n', capture_output=True,
                       text=True, timeout=timeout)
    text = p.stdout + p.stderr
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
