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


Tree = Union[Leaf, Node]


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


def decode(leaves: List[LeafLabel]) -> Tree:
    """Rebuild the tree. Any depth sequence decodes: a span is split at its
    shallowest ancestor, the leftmost one if several tie."""
    if not leaves:
        raise EncodingError('no leaves')

    def wrap(t: Tree, chain: Tuple[str, ...]) -> Tree:
        for label in reversed(chain):
            t = Node(label, (t,))
        return t

    def build(lo: int, hi: int) -> Tree:
        if lo == hi:
            leaf = leaves[lo]
            return wrap(Leaf(leaf.entry, leaf.forms), leaf.chain)
        split = min(range(lo, hi), key=lambda i: (leaves[i].depth, i))
        node = leaves[split].node
        binary = Node(node[-1], (build(lo, split), build(split + 1, hi)))
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
