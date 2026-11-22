"""Orca as Kelp's grammar engine: is a forest tree licensed, and what does it mean?

A tree is rebuilt with Orca's replay under the first root condition that
holds, in the order in which ACE tests them. A tree with idiom parts is
dropped by the grammar's non-idiom root condition; Orca has no idiom rules
yet, so this also drops a complete idiom.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
sys.setrecursionlimit(20000)

from delphin import dmrs  # noqa: E402

from compare_mrs import to_pydelphin  # noqa: E402
from orca.encoding import Leaf, Node  # noqa: E402
from orca.tfs.fast import FastGrammar, extract  # noqa: E402
from orca.tfs.grammar import Grammar, ReplayFailure  # noqa: E402

# The ERG's parsing roots, in the order of their definition in roots.tdl.
ROOTS = ['root_strict', 'root_informal', 'root_inffrag', 'root_frag', 'root_robust_frag',
         'root_robust', 'root_exclam_ques']
NON_IDIOM = 'root_non_idiom'


def to_orca(tree):
    """A forest tree as Orca's replay input: (tree, token structures)."""
    toks = []

    def walk(t):
        if t.lexical:
            toks.extend(tok.avm for tok in t.tokens)
            return Leaf('entry:' + t.label, tuple(tok.form for tok in t.tokens))
        return Node(t.label, tuple(walk(c) for c in t.children))

    return walk(tree), toks


def _dmrs(m):
    d = dmrs.from_mrs(m)
    return {'top': d.top, 'index': d.index,
            'nodes': [{'id': n.id, 'pred': str(n.predicate), 'carg': n.carg, 'props': dict(n.properties)}
                      for n in d.nodes],
            'links': [{'from': k.start, 'to': k.end, 'role': k.role, 'post': k.post} for k in d.links]}


class Engine:
    def __init__(self, grammar_file):
        self.fg = FastGrammar(Grammar(grammar_file))

    def check(self, tree):
        """None when the grammar does not license the tree; otherwise the root
        condition it meets and its meaning as a DMRS."""
        fg = self.fg
        orca_tree, toks = to_orca(tree)
        for root in ROOTS:
            fg.reset()
            try:
                fs, _ = fg.replay_tree(Node(root, (orca_tree,)), toks)
            except ReplayFailure as e:
                if not e.where.endswith(root):
                    return None             # failed below the root: no root condition will help
                continue
            meaning = extract(fg, fs)
            fg.reset()
            try:
                fg.replay_tree(Node(NON_IDIOM, (Node(root, (orca_tree,)),)), toks)
            except ReplayFailure:
                return None
            try:
                graph = _dmrs(to_pydelphin(meaning))
            except Exception:               # a meaning that has no DMRS form
                graph = None
            return {'root': root, 'dmrs': graph}
        return None
