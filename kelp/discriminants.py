"""Counting, discriminants and constraints on a packed forest.

The method is that of the Full Forest Treebanker (Packard 2015, chapter 3).

Unary chains. Every chain of unary rules over one span is collapsed into a
single node, labeled with the whole chain from the top rule down to the
binary rule or lexical entry at its bottom. In a tree of collapsed nodes no
two nodes have the same span, so a statement about a span concerns exactly
one node of the tree, and can be tested on each node by itself.

Constraints. A constraint names a span and says one of three things:
    CHAIN    the tree has a node over the span with exactly this chain
    PRESENT  the tree has a node over the span with this label in its chain
    SPAN     the tree has a node over the span
and each has an opposite, which holds in exactly the other trees:
    ABSENT     no node over the span has this label in its chain
    NOT_CHAIN  no node over the span has exactly this chain
    NOT_SPAN   the tree has no node over the span
FFTB has the first four; of these it cannot save SPAN.
A node is ruled out when it is over the span and fails the test. For the
three positive kinds a node is also ruled out when its span crosses the span,
or when it contains the span and none of its daughters does: every tree of
the remaining nodes then has a node over the span.

A constraint of kind SEM or NOT_SEM is about the meaning of a tree (one
dependency between two predicates is there, or is not). It cannot be tested
on the forest: every node allows it, and the session applies it to the
trees whose meaning it has.

Counting. The number of remaining trees below each node is computed
bottom-up, and the number of remaining trees that use each node top-down.
Both passes visit each node once.

Discriminants. A property of the node over some span (its chain, a label in
its chain, or that there is such a node) that holds in some remaining trees
and not in all.

Lexical entries appear in chain labels under the name that `lexlabel` gives
them. FFTB uses the lexical type; the default here is the entry's own name.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple

from kelp.forest import LEXEME, Forest, Tree

CHAIN, PRESENT, SPAN, ABSENT = 'chain', 'present', 'span', 'absent'
NOT_CHAIN, NOT_SPAN = 'not-chain', 'not-span'
SEM, NOT_SEM = 'sem', 'not-sem'     # about the meaning: see below
_OPPOSITE = {CHAIN: NOT_CHAIN, PRESENT: ABSENT, SPAN: NOT_SPAN, SEM: NOT_SEM}
_OPPOSITE.update({v: k for k, v in list(_OPPOSITE.items())})
_NEGATIVE = (ABSENT, NOT_CHAIN, NOT_SPAN)


@dataclass(frozen=True)
class Constraint:
    kind: str                   # CHAIN, PRESENT, SPAN, or one of their opposites
    start: int
    end: int
    value: Tuple[str, ...] = ()  # a chain, one label, or nothing, by kind

    def negated(self):
        """The constraint that holds in exactly the trees where this one fails."""
        return Constraint(_OPPOSITE[self.kind], self.start, self.end, self.value)


@dataclass(eq=False)
class Node:
    """A unary chain over one span, with the daughters of its bottom edge."""
    id: int
    chain: Tuple[str, ...]      # top to bottom, in forest labels
    labels: Tuple[str, ...]     # the same, with the lexical entry under its `lexlabel` name
    start: int
    end: int
    slots: List[List['Node']] = field(default_factory=list)   # per daughter: the nodes that can fill it
    tokens: tuple = ()          # for a chain that ends in a lexical entry

    def allows(self, c):
        """Whether a tree with this node can satisfy the constraint, as far as
        this node alone shows."""
        if c.kind in (SEM, NOT_SEM):
            return True
        if (self.start, self.end) == (c.start, c.end):
            if c.kind == CHAIN:
                return self.labels == c.value
            if c.kind == PRESENT:
                return c.value[0] in self.labels
            if c.kind == ABSENT:
                return c.value[0] not in self.labels
            if c.kind == NOT_CHAIN:
                return self.labels != c.value
            return c.kind == SPAN
        if c.kind in _NEGATIVE or self.end <= c.start or c.end <= self.start:
            return True
        if c.start <= self.start and self.end <= c.end:
            return True                                     # inside the span
        if not (self.start <= c.start and c.end <= self.end):
            return False                                    # crosses the span
        return any(s[0].start <= c.start and c.end <= s[0].end for s in self.slots)

    def tree(self, kids):
        """The forest tree for this node over the given daughter trees."""
        if self.slots:
            t = Tree(self.chain[-1], self.start, self.end, tuple(kids))
        else:
            t = Tree(self.chain[-1], self.start, self.end, (), self.tokens)
        for label in reversed(self.chain[:-1]):
            t = Tree(label, self.start, self.end, (t,))
        return t


@dataclass
class Counts:
    total: int                  # remaining trees
    below: Dict[int, int]       # node id -> remaining trees of the node's own span
    using: Dict[int, int]       # node id -> remaining trees of the sentence that have the node


class Chains:
    """A forest with its unary chains collapsed."""

    def __init__(self, forest: Forest, lexlabel: Callable[[str], str] = lambda name: name):
        self.nodes: List[Node] = []         # daughters before mothers
        self._slots = {}
        self._made = {}
        self._lexlabel = lexlabel
        seen, self.roots = set(), []
        for _, e in forest.roots:           # one root record per root condition: keep each edge once
            if e.id not in seen:
                seen.add(e.id)
                self.roots.extend(self._slot(e))
        self.roots = list({n.id: n for n in self.roots}.values())

    def _slot(self, host):
        """The nodes that can stand where `host` is named as a daughter."""
        nodes = self._slots.get(host.id)
        if nodes is None:
            found = {}
            for e in host.packed():
                for chain, bottom in self._chains(e):
                    found.setdefault((chain, bottom.id), bottom)
            nodes = []
            for key, bottom in found.items():
                if key not in self._made:
                    self._made[key] = self._node(key[0], bottom)
                nodes.append(self._made[key])
            self._slots[host.id] = nodes
        return nodes

    def _chains(self, e):
        """Every (labels, bottom edge) of a unary chain that starts at `e`."""
        if e.kind == LEXEME or len(e.daughters) != 1:
            return [((e.label,), e)]
        return [((e.label,) + chain, bottom)
                for x in e.daughters[0].packed() for chain, bottom in self._chains(x)]

    def _node(self, chain, bottom):
        slots = [self._slot(d) for d in bottom.daughters]
        labels = chain
        if bottom.kind == LEXEME:
            labels = chain[:-1] + (self._lexlabel(chain[-1]),)
        node = Node(len(self.nodes), chain, labels, bottom.start, bottom.end, slots,
                    tuple(bottom.tokens))
        self.nodes.append(node)             # after its daughters
        return node

    def count(self, constraints=()) -> Counts:
        """The trees that satisfy every constraint."""
        below, using = {}, {}
        for n in self.nodes:
            t = 0
            if all(n.allows(c) for c in constraints):
                t = 1
                for slot in n.slots:
                    t *= sum(below[x.id] for x in slot)
            below[n.id] = t
            using[n.id] = 0
        outside = dict.fromkeys(below, 0)   # trees of the rest of the sentence around the node
        for n in self.roots:
            outside[n.id] = 1
        for n in reversed(self.nodes):      # mothers before daughters
            o = outside[n.id]
            using[n.id] = o * below[n.id]
            if not using[n.id]:
                continue
            sums = [sum(below[x.id] for x in slot) for slot in n.slots]
            for i, slot in enumerate(n.slots):
                rest = o
                for j, s in enumerate(sums):
                    if j != i:
                        rest *= s
                for x in slot:
                    outside[x.id] += rest
        return Counts(sum(below[n.id] for n in self.roots), below, using)

    def discriminants(self, constraints=(), counts=None) -> Dict[Constraint, int]:
        """Each CHAIN, PRESENT and SPAN constraint that some remaining trees
        satisfy and others do not, with the number of trees that satisfy it."""
        counts = counts or self.count(constraints)
        found = {}
        for n in self.nodes:
            k = counts.using[n.id]
            if not k:
                continue
            props = [Constraint(SPAN, n.start, n.end), Constraint(CHAIN, n.start, n.end, n.labels)]
            props += [Constraint(PRESENT, n.start, n.end, (label,)) for label in set(n.labels)]
            for p in props:
                found[p] = found.get(p, 0) + k
        return {p: k for p, k in found.items() if k < counts.total}

    def pick(self, counts):
        """One remaining tree, as nested (node, daughters) pairs: wherever
        nodes compete, the one that most remaining trees use. None when no
        tree remains."""
        if not counts.total:
            return None

        def most(nodes):
            return max(nodes, key=lambda x: counts.using[x.id])

        def walk(n):
            return (n, [walk(most(slot)) for slot in n.slots])

        return walk(most(self.roots))

    def trees(self, constraints=(), limit=None):
        """The remaining trees, as forest trees. Raises ValueError when there
        are more than `limit`."""
        counts = self.count(constraints)
        if limit is not None and counts.total > limit:
            raise ValueError(f'{counts.total} trees remain, more than {limit}')
        memo = {}

        def unpack(n):
            ts = memo.get(n.id)
            if ts is None:
                ts = []
                if counts.below[n.id]:
                    combos = [()]
                    for slot in n.slots:
                        combos = [c + (t,) for c in combos for x in slot for t in unpack(x)]
                    ts = [n.tree(kids) for kids in combos]
                memo[n.id] = ts
            return ts

        return [t for n in self.roots for t in unpack(n)]


def spans(tree, lexlabel=lambda name: name):
    """The collapsed nodes of one tree, as {(start, end): chain labels}."""
    out = {}

    def walk(t):
        labels, top = [], t
        while len(t.children) == 1:
            labels.append(t.label)
            t = t.children[0]
        labels.append(lexlabel(t.label) if t.lexical else t.label)
        out[top.start, top.end] = tuple(labels)
        for c in t.children:
            walk(c)

    walk(tree)
    return out


def satisfies(tree_spans, c):
    """Whether a tree, given as the result of `spans`, satisfies a constraint."""
    if c.kind in (SEM, NOT_SEM):
        return True
    labels = tree_spans.get((c.start, c.end))
    if c.kind in _NEGATIVE:
        return labels is None or (c.kind == ABSENT and c.value[0] not in labels) \
            or (c.kind == NOT_CHAIN and labels != c.value)
    if labels is None:
        return False
    if c.kind == CHAIN:
        return labels == c.value
    if c.kind == PRESENT:
        return c.value[0] in labels
    return True
