"""The whole sign of an ACE analysis, rebuilt by Orca's replay.

ACE prints a derivation, not the feature structure. Replaying that derivation
(lexical entries, rules, and the token structures ACE recorded) with Orca's
unifier rebuilds the sign, so ACE's analysis can be shown in the demo's
feature-structure viewer next to Orca's. The root conditions are tried in the
order ACE reports them; the first that holds gives the sign.
"""
from delphin import derivation as D

from orca.encoding import Leaf, Node
from orca.tfs.grammar import ReplayFailure

# `parsing-roots` of the ERG's ACE configuration, in the order ACE reports them (as scripts/kelp_check_forest.py)
ROOTS = ['root_strict', 'root_informal', 'root_inffrag', 'root_frag', 'root_robust_frag',
         'root_robust', 'root_exclam_ques']


def to_replay(deriv):
    """A pydelphin derivation (or its string) as (Orca tree with 'entry:' leaves, token structures)."""
    d = D.from_string(deriv) if isinstance(deriv, str) else deriv
    toks = []

    def walk(n):
        kids = n.daughters or []
        if kids and all(isinstance(k, D.UDFTerminal) for k in kids):
            forms = []
            for term in kids:
                forms.append(term.form)
                toks.extend(tok.tfs for tok in (term.tokens or []))
            return Leaf('entry:' + n.entity, tuple(forms))
        return Node(n.entity, tuple(walk(k) for k in kids if isinstance(k, D.UDFNode)))

    root = d
    if root.entity in ROOTS and len(root.daughters or []) == 1:      # a rooted derivation: keep only the tree
        root = root.daughters[0]
    return walk(root), toks


def replay_sign(fg, deriv):
    """Replay an ACE derivation; returns (sign node, root condition) or (None, reason).
    Resets the grammar's memory: read anything from an earlier sign before calling."""
    try:
        tree, toks = to_replay(deriv)
    except Exception as e:
        return None, f'unreadable derivation: {type(e).__name__}'
    reason = 'no root condition holds'
    for root in ROOTS:
        fg.reset()
        try:
            fs, _ = fg.replay_tree(Node(root, (tree,)), toks)
            return fs, root
        except ReplayFailure as e:
            reason = f'replay failed: {str(e.cause)[:80]}'
            if not e.where.endswith(root):
                break                                    # failed below the root: no root condition helps
    return None, reason
