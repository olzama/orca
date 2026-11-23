"""Derivation trees as one label per leaf, and back.

The encoding follows Gómez-Rodríguez and Vilares (2018): each leaf says how
deep its lowest common ancestor with the next leaf is and what that ancestor
is called. A derivation here has only unary and binary nodes, so the sequence
decodes to exactly one tree. Unary chains are folded into the label of the
node below them.

The module knows nothing about any grammar or file format. Trees are built
from `Leaf` and `Node`.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple, Union


@dataclass(frozen=True)
class Leaf:
    entry: str                 # name of the lexical entry
    forms: Tuple[str, ...]     # the tokens the entry spans (one or more)


@dataclass(frozen=True)
class Node:
    label: str                 # rule name (or root condition)
    children: Tuple['Tree', ...]

    def __hash__(self):         # cached: trees are used as dictionary keys during repair
        h = self.__dict__.get('_hash')
        if h is None:
            h = hash((self.label, self.children))
            object.__setattr__(self, '_hash', h)
        return h


Tree = Union[Leaf, Node]


def n_leaves(t) -> int:
    """Number of leaves under a node (cached on the node)."""
    if isinstance(t, Leaf):
        return 1
    n = t.__dict__.get('_n')
    if n is None:
        n = sum(n_leaves(c) for c in t.children)
        object.__setattr__(t, '_n', n)
    return n


@dataclass
class LeafLabel:
    """Everything one leaf contributes to the tree.

    chain: unary nodes above the leaf, top-down.
    depth: number of binary nodes from the root down to, and including, the
           lowest common ancestor of this leaf and the next; None on the
           last leaf.
    node:  unary nodes above that ancestor, top-down, followed by the
           ancestor's own label; None on the last leaf.
    """
    entry: str
    forms: Tuple[str, ...]
    chain: Tuple[str, ...]
    depth: Optional[int] = None
    node: Optional[Tuple[str, ...]] = None


class EncodingError(ValueError):
    pass


def encode(tree: Tree) -> List[LeafLabel]:
    leaves: List[LeafLabel] = []

    def walk(t: Tree, chain: Tuple[str, ...], depth: int) -> None:
        if isinstance(t, Leaf):
            leaves.append(LeafLabel(t.entry, t.forms, chain))
        elif len(t.children) == 1:
            walk(t.children[0], chain + (t.label,), depth)
        elif len(t.children) == 2:
            walk(t.children[0], (), depth + 1)
            last_left = leaves[-1]
            last_left.depth = depth + 1
            last_left.node = chain + (t.label,)
            walk(t.children[1], (), depth + 1)
        else:
            raise EncodingError(f'{t.label}: {len(t.children)} daughters')

    walk(tree, (), 0)
    return leaves


def interner(table: Optional[dict] = None):
    """Constructors for Node and Leaf that return one shared object per distinct
    subtree (hash-consing). With a table kept across many trees (repair replays
    hundreds of near-identical trees per sentence), each subtree's cached hash and
    leaf count are computed once. Equal trees are equal either way; only object
    identity is shared. Without a table: the plain constructors."""
    if table is None:
        return Node, Leaf

    def node(label, children):
        key = ('N', label, children)
        t = table.get(key)
        if t is None:
            t = table[key] = Node(label, children)
        return t

    def leaf(entry, forms):
        key = ('L', entry, forms)
        t = table.get(key)
        if t is None:
            t = table[key] = Leaf(entry, forms)
        return t
    return node, leaf


def decode(leaves: List[LeafLabel], intern: Optional[dict] = None) -> Tree:
    """Rebuild the tree. Any depth sequence decodes: a span is split at its
    shallowest ancestor, the leftmost one if several tie. With `intern` (a dict
    kept by the caller), identical subtrees are shared objects (see interner)."""
    if not leaves:
        raise EncodingError('no leaves')
    mk_node, mk_leaf = interner(intern)

    def wrap(t: Tree, chain: Tuple[str, ...]) -> Tree:
        for label in reversed(chain):
            t = mk_node(label, (t,))
        return t

    def build(lo: int, hi: int) -> Tree:
        if lo == hi:
            leaf = leaves[lo]
            return wrap(mk_leaf(leaf.entry, leaf.forms), leaf.chain)
        split = min(range(lo, hi), key=lambda i: (leaves[i].depth, i))
        node = leaves[split].node
        binary = mk_node(node[-1], (build(lo, split), build(split + 1, hi)))
        return wrap(binary, node[:-1])

    for leaf in leaves[:-1]:
        if leaf.depth is None or not leaf.node:
            raise EncodingError('a non-final leaf lacks depth or node')
    return build(0, len(leaves) - 1)


def relative_depths(leaves: List[LeafLabel]) -> List[Optional[int]]:
    """Depth of each leaf's ancestor relative to the previous leaf's."""
    out, prev = [], 0
    for leaf in leaves:
        if leaf.depth is None:
            out.append(None)
        else:
            out.append(leaf.depth - prev)
            prev = leaf.depth
    return out


def absolute_depths(deltas: List[Optional[int]]) -> List[Optional[int]]:
    out, prev = [], 0
    for d in deltas:
        if d is None:
            out.append(None)
        else:
            prev += d
            out.append(prev)
    return out
