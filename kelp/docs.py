"""The grammar's own documentation of rules, lexical rules and lexical types.

The ERG documents many definitions with a string of this form:

    sb-hd_mc_c := subjh_mc_rule &
    \"\"\"
    Head+subject, main clause
    <ex>C arrived.
    \"\"\"

A lexical entry has no documentation of its own; it gets that of its type.
"""
import glob
import os
import re

_DOC = re.compile(r'^([^\s;:"]+)[ \t]*:=((?:(?!^[^\s;:"]+[ \t]*:=)[^"])*?)"""(.*?)"""', re.M | re.S)
_DEF = re.compile(r'^([^\s;:"]+)[ \t]*:=[ \t]*([^\s&.\[]+)', re.M)
_EX = re.compile(r'<(ex|nex)>(.*)')


def load_docs(grammar_dir):
    """{name: {'type': first supertype, 'doc': description, 'ex': [examples]}}
    for every definition in the grammar's TDL files."""
    docs, parents = {}, {}
    for path in sorted(glob.glob(os.path.join(grammar_dir, '*.tdl'))):
        with open(path, encoding='utf-8', errors='replace') as f:
            text = f.read()
        for m in _DEF.finditer(text):
            parents.setdefault(m.group(1).lower(), m.group(2).lower())
        for m in _DOC.finditer(text):
            lines, ex = [], []
            for line in m.group(3).splitlines():
                line = line.strip()
                e = _EX.match(line)
                if e:
                    ex.append(('*' if e.group(1) == 'nex' else '') + e.group(2).strip())
                elif line and not line.startswith('<'):
                    lines.append(line)
            docs.setdefault(m.group(1).lower(), (' '.join(lines), ex))
    out = {}
    for name in set(parents) | set(docs):
        parent = parents.get(name, '')
        doc, ex = docs.get(name) or docs.get(parent) or ('', [])
        out[name] = {'type': parent, 'doc': doc, 'ex': ex}
    return out


_START = re.compile(r'^([^\s;:"]+)[ \t]*:[=+<]', re.M)
_PRED = re.compile(r'PRED\s+"?(_[^\s",\]]+?)(?:_rel)?"?[\s,\]]')
_ORTH = re.compile(r'ORTH\s*<([^>]*)>')
_WORD = re.compile(r'[A-Za-z_*][\w\-+*./]*')


class Lookup:
    """The grammar's definitions by name, and its lexical entries by predicate."""

    def __init__(self, grammar_dir):
        self.defs = {}              # name -> [(file, line number, text)]
        self.entries = {}           # predicate -> [names of the lexical entries that have it]
        self.info = load_docs(grammar_dir)
        self.spelled = {}           # spelling -> [names of the lexical entries spelled so]
        self.of = {}                # lexical entry -> (spelling, predicate)
        for path in sorted(glob.glob(os.path.join(grammar_dir, '*.tdl'))):
            with open(path, encoding='utf-8', errors='replace') as f:
                text = f.read()
            starts = [m for m in _START.finditer(text)]
            line, at = 1, 0
            for m, nxt in zip(starts, starts[1:] + [None]):
                body = text[m.start():nxt.start() if nxt else len(text)]
                body = re.sub(r'(\n[ \t]*(;[^\n]*)?)+$', '', body)      # comments that lead to the next definition
                line += text.count('\n', at, m.start())
                at = m.start()
                name = m.group(1).lower()
                self.defs.setdefault(name, []).append((os.path.basename(path), line, body))
                preds = [p.group(1).lower() for p in _PRED.finditer(body)]
                for pred in preds:
                    names = self.entries.setdefault(pred, [])
                    if name not in names:
                        names.append(name)
                o = _ORTH.search(body)
                if o and name not in self.of:
                    spelling = ' '.join(re.findall(r'"([^"]*)"', o.group(1))).lower()
                    self.of[name] = (spelling, preds[0] if preds else '')
                    self.spelled.setdefault(spelling, []).append(name)

    def get(self, query):
        """What the grammar has under a name: its definitions (each with the
        names in it that can be looked up in turn) and, for a predicate, the
        lexical entries that introduce it."""
        q = query.strip().lower()
        if q.endswith('_rel'):
            q = q[:-4]
        pred = q if q in self.entries else '_' + q if '_' + q in self.entries else None
        mine = self.entries.get(pred, []) if pred else [q] if q in self.of else []
        spellings = sorted({self.of[e][0] for e in mine if e in self.of})
        # every lexical entry with the same spelling: what the entries asked about must be told apart from
        same = [{'name': e, 'spelling': sp, 'predicate': self.of[e][1], 'asked': e in mine,
                 'type': self.info.get(e, {}).get('type', ''), 'doc': self.info.get(e, {}).get('doc', ''),
                 'ex': self.info.get(e, {}).get('ex', [])}
                for sp in spellings for e in self.spelled[sp]]
        out = {'query': query, 'definitions': [], 'predicate': pred, 'same_spelling': same}
        for fname, line, text in self.defs.get(q, []):
            shown = text if len(text) <= 6000 else text[:6000] + '\n...'
            code = re.sub(r'""".*?"""|"[^"\n]*"|;[^\n]*', ' ', shown, flags=re.S)    # no documentation, strings, comments
            names = sorted({w.lower() for w in _WORD.findall(code)
                            if w.lower() in self.defs and w.lower() != q})
            out['definitions'].append({'name': q, 'file': fname, 'line': line, 'text': shown, 'names': names})
        return out
