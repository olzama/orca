"""Typed feature structures and unification.

A structure is a graph of nodes. Unification is destructive: it merges the
second node into the first. Every change is recorded on a trail, so a failed
or unwanted unification can be undone.

A node without arcs whose `expanded` flag is off stands for "anything of
this type": the constraint of its type has not been copied in yet. This
keeps structures small. The constraint is copied in only when the node meets
real content, or when unification makes its type more specific than what
either side had (run-time type inference).
"""
from typing import Callable, Dict, List, Optional


class Node:
    __slots__ = ('type', 'arcs', 'fwd', 'expanded')

    def __init__(self, type_, expanded=False):
        self.type = type_
        self.arcs: Dict[str, 'Node'] = {}
        self.fwd: Optional['Node'] = None
        self.expanded = expanded


def deref(n: Node) -> Node:
    while n.fwd is not None:
        n = n.fwd
    return n


class UnificationFailure(Exception):
    def __init__(self, path, left, right):
        super().__init__(f"{'.'.join(path) or '<top>'}: {left} & {right}")
        self.path, self.left, self.right = tuple(path), left, right


class Unifier:
    def __init__(self, glb: Callable[[str, str], Optional[str]],
                 constraint: Callable[[str], Optional[Node]]):
        self.glb = glb
        self.constraint = constraint     # type -> its expanded constraint, or None if it has no arcs
        self.trail: List[tuple] = []
        self.count = 0                   # node unifications, for profiling

    # -- trail -----------------------------------------------------------

    def mark(self):
        return len(self.trail)

    def undo(self, mark):
        trail = self.trail
        while len(trail) > mark:
            kind, node, old = trail.pop()
            if kind == 't':
                node.type = old
            elif kind == 'f':
                node.fwd = None
            elif kind == 'e':
                node.expanded = False
            else:
                del node.arcs[old]

    def _set_type(self, n, t):
        if n.type != t:
            self.trail.append(('t', n, n.type))
            n.type = t

    def _forward(self, src, dst):
        self.trail.append(('f', src, None))
        src.fwd = dst

    # -- operations ------------------------------------------------------

    def copy(self, n: Node, memo=None) -> Node:
        memo = {} if memo is None else memo
        n = deref(n)
        new = memo.get(id(n))
        if new is None:
            new = memo[id(n)] = Node(n.type, n.expanded)
            for f, v in n.arcs.items():
                new.arcs[f] = self.copy(v, memo)
        return new

    def expand(self, n: Node, path=()):
        """Copy the constraint of the node's type into the node."""
        n = deref(n)
        if n.expanded:
            return n
        self.trail.append(('e', n, None))
        n.expanded = True
        c = self.constraint(n.type)
        if c is not None:
            self._merge(n, self.copy(c), list(path))
        return n

    def get(self, n: Node, *feats) -> Node:
        for f in feats:
            n = deref(n)
            if f not in n.arcs:
                self.expand(n)
            n = deref(n).arcs[f]
        return deref(n)

    def unify(self, a: Node, b: Node, path=None) -> Node:
        return self._merge(a, b, [] if path is None else list(path))

    def _merge(self, a, b, path):
        a, b = deref(a), deref(b)
        if a is b:
            return a
        self.count += 1
        t = self.glb(a.type, b.type)
        if t is None:
            raise UnificationFailure(path, a.type, b.type)
        a_exp, b_exp = a.expanded, b.expanded
        if not a_exp and not b_exp:                 # two placeholders
            self._forward(b, a)
            self._set_type(a, t)
            return a
        if not a_exp:                               # keep the node with content
            a, b, a_exp, b_exp = b, a, b_exp, a_exp
        new_type = t != a.type and not (b_exp and t == b.type)
        self._forward(b, a)
        self._set_type(a, t)
        if b_exp:
            arcs = a.arcs
            for f, v in b.arcs.items():
                mine = arcs.get(f)
                if mine is None:
                    self.trail.append(('a', a, f))
                    arcs[f] = v
                else:
                    path.append(f)
                    self._merge(mine, v, path)
                    path.pop()
        if new_type:                                # run-time type inference
            c = self.constraint(t)
            if c is not None:
                self._merge(a, self.copy(c), path)
        return deref(a)


def show(n: Node, indent=0, seen=None, depth=6) -> str:
    """Readable dump, for debugging."""
    seen = {} if seen is None else seen
    n = deref(n)
    if id(n) in seen:
        return f'#{seen[id(n)]}'
    if not n.arcs:
        return n.type
    seen[id(n)] = len(seen)
    if depth == 0:
        return f'#{seen[id(n)]}={n.type}[...]'
    pad = ' ' * (indent + 2)
    body = '\n'.join(f'{pad}{f} {show(v, indent + 2, seen, depth - 1)}' for f, v in sorted(n.arcs.items()))
    return f'#{seen[id(n)]}={n.type} [\n{body} ]'
