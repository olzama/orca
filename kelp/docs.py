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
