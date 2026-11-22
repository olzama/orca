"""The packed parse forest that ACE stores in the `edge` relation of a profile.

A forest is a set of edges. An edge is a lexical entry over one or more
tokens, or a rule applied to daughter edges. Edges that the parser found
interchangeable are packed: one of them (the host) is the one that other
edges name as their daughter, and the others are listed as its alternates.
Wherever the host appears as a daughter, any alternate may stand in its
place. A root record names an edge that spans the sentence and meets a root
condition (Packard 2015, section 3.1).

Some trees in a packed forest are not licensed by the grammar: packing
discards information, so a tree can fail when its unifications are redone.
The number of trees counted here is therefore an upper bound.

Fields of the `edge` relation as ACE writes them:
    e-type    0 token, 1 lexical entry, 2 lexical rule, 3 phrasal rule, 4 root
    e-status  bit 1: the edge is part of some complete analysis
"""
import itertools
import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from delphin import tsdb

TOKEN, LEXEME, LEXRULE, RULE, ROOT = 0, 1, 2, 3, 4
_FROM_TO = re.compile(r'\+FROM "(\d+)" \+TO "(\d+)"')
_FORM = re.compile(r'\+FORM "((?:\\.|[^"\\])*)"')


@dataclass
class Token:
    id: int
    start: int                  # chart vertices
    end: int
    avm: str                    # the token feature structure, as text
    form: str = ''
    cfrom: int = -1             # character positions in the input
    cto: int = -1


@dataclass(eq=False)
class Edge:
    id: int
    label: str                  # rule name or lexical entry name
    kind: int                   # LEXEME, LEXRULE or RULE
    start: int
    end: int
    daughters: List['Edge'] = field(default_factory=list)
    alternates: List['Edge'] = field(default_factory=list)
    tokens: List[Token] = field(default_factory=list)      # lexical entries only

    def packed(self):
        """This edge and every edge that may stand in its place."""
        out, stack = [], [self]
        while stack:
            e = stack.pop()
            out.append(e)
            stack.extend(reversed(e.alternates))
        return out


@dataclass(frozen=True)
class Tree:
    """One derivation unpacked from the forest."""
    label: str
    start: int
    end: int
    children: Tuple['Tree', ...] = ()
    tokens: Tuple[Token, ...] = ()     # lexical entries only

    @property
    def lexical(self):
        return not self.children

    def key(self):
        """Labels and spans only: equal for equal derivations."""
        return (self.label, self.start, self.end, tuple(c.key() for c in self.children))


@dataclass
class Forest:
    tokens: Dict[int, Token]
    edges: Dict[int, Edge]
    roots: List[Tuple[str, Edge]]      # (root condition, edge)

    def count(self):
        """Number of trees in the forest, one per (root condition, tree)."""
        memo = {}

        def packed(e):                  # trees for e or any of its alternates
            return sum(own(x) for x in e.packed())

        def own(e):
            n = memo.get(e.id)
            if n is None:
                n = 1
                for d in e.daughters:
                    n *= packed(d)
                memo[e.id] = n
            return n

        return sum(packed(e) for _, e in self.roots)

    def trees(self):
        """Every (root condition, tree) in the forest. Exponential in general:
        check `count()` first."""
        memo = {}

        def packed(e):
            return [t for x in e.packed() for t in own(x)]

        def own(e):
            ts = memo.get(e.id)
            if ts is None:
                if e.kind == LEXEME:
                    ts = [Tree(e.label, e.start, e.end, (), tuple(e.tokens))]
                else:
                    ts = [Tree(e.label, e.start, e.end, kids)
                          for kids in itertools.product(*(packed(d) for d in e.daughters))]
                memo[e.id] = ts
            return ts

        for root, e in self.roots:
            for t in packed(e):
                yield root, t


def _ids(text):
    return [int(x) for x in text.strip('()').split()] if text else []


def load_forests(profile):
    """All forests of a profile, as {parse-id: Forest}. Items without a
    usable forest are absent."""
    names = [f.name for f in tsdb.read_schema(profile)['edge']]
    col = {n: names.index(n) for n in names}
    rows = {}
    with tsdb.open(profile, 'edge') as lines:
        for line in lines:
            rec = tsdb.split(line)
            rows.setdefault(int(rec[col['parse-id']]), []).append(rec)
    out = {}
    for pid, recs in rows.items():
        forest = _build(recs, col)
        if forest.roots:
            out[pid] = forest
    return out


def _build(recs, col):
    tokens, edges, roots, links = {}, {}, [], []
    for rec in recs:
        eid, kind = int(rec[col['e-id']]), int(rec[col['e-type']])
        label = rec[col['e-label']]
        start, end = int(rec[col['e-start']]), int(rec[col['e-end']])
        if kind == TOKEN:
            tok = Token(eid, start, end, label)
            m = _FROM_TO.search(label)
            if m:
                tok.cfrom, tok.cto = int(m.group(1)), int(m.group(2))
            m = _FORM.search(label)
            if m:
                tok.form = m.group(1)
            tokens[eid] = tok
            continue
        if not int(rec[col['e-status']]) & 1:
            continue                    # not part of any complete analysis
        dtrs = _ids(rec[col['e-daughters']])
        if kind == ROOT:
            roots.append((label, dtrs[0]))
            continue
        edges[eid] = Edge(eid, label, kind, start, end)
        links.append((eid, kind, dtrs, _ids(rec[col['e-alternates']])))
    for eid, kind, dtrs, alts in links:
        e = edges[eid]
        if kind == LEXEME:
            e.tokens = [tokens[d] for d in dtrs]
        else:
            e.daughters = [edges[d] for d in dtrs]
        e.alternates = [edges[a] for a in alts]
    return Forest(tokens, edges, [(label, edges[d]) for label, d in roots])
