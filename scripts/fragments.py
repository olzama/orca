"""Partial analyses for a sentence that gets no full analysis.

From the tagger's first guess (one lexical and one tree label per word):

  1. robust roots: the same derivation under each of the ERG's other root
     conditions (informal, fragment and robust roots, in ACE's order); the first
     that the grammar accepts gives an analysis of the whole sentence;
  2. maximal fragments: otherwise, the largest subtrees of the first guess that
     replay, left to right (a node that fails is replaced by its daughters'
     fragments), each with its own MRS.

Used by scripts/relaxed.py (measurement) and scripts/orca_parse.py (a labeled
fallback in the parser's output). Fragments are never counted as analyses.
"""
import re

# The ERG's parsing roots in ACE's order (scripts/kelp_check_forest.py).
ROOTS = ['root_strict', 'root_informal', 'root_inffrag', 'root_frag', 'root_robust_frag',
         'root_robust', 'root_exclam_ques']
ROOT_RE = re.compile(r'root_[a-z_]+')


def strip_roots(t):
    from orca.encoding import Node
    while isinstance(t, Node) and t.label.startswith('root_') and len(t.children) == 1:
        t = t.children[0]
    return t


def partial_analysis(fg, lx, rforms, leaf, tree, toks):
    """Returns {'result': 'robust root' | 'fragments' | 'nothing' | 'undecodable first guess',
    'root guessed': str|None, 'root': str (robust root only),
    'pieces': [(start, end, label, MRS)]} with PyDelphin MRS objects; a robust-root
    analysis is one piece covering the sentence, labeled with its root."""
    from compare_mrs import to_pydelphin
    from eval_trees import to_leaves
    from orca.encoding import Leaf, decode, n_leaves
    from orca.tfs.fast import extract
    from orca.tfs.lexicon import replay_with_entries

    def try_replay(t, tk):
        fg.reset()
        try:
            fs, _ = replay_with_entries(fg, lx, t, tk)
            return to_pydelphin(extract(fg, fs))
        except Exception:
            return None

    def fragments(t, start, out):
        n = n_leaves(t)
        m = try_replay(t, toks[start:start + n])
        if m is not None:
            out.append((start, start + n, t.entry if isinstance(t, Leaf) else t.label, m))
            return
        if isinstance(t, Leaf):
            return                          # a word with no usable entry: uncovered
        pos = start
        for c in t.children:
            fragments(c, pos, out)
            pos += n_leaves(c)

    res = {'pieces': []}
    try:
        t = decode(to_leaves(rforms, leaf, tree))
    except Exception:
        res['result'] = 'undecodable first guess'
        return res
    guessed = ROOT_RE.search(' '.join(tree))
    res['root guessed'] = guessed.group(0) if guessed else None
    for root in ROOTS:
        if guessed and root == guessed.group(0):
            continue                        # repair already tried the guessed root
        tr2 = [ROOT_RE.sub(root, x) for x in tree]
        if tr2 == tree:
            continue
        try:
            t2 = decode(to_leaves(rforms, leaf, tr2))
        except Exception:
            continue
        m = try_replay(t2, toks)
        if m is not None:
            res['result'], res['root'] = 'robust root', root
            res['pieces'] = [(0, len(rforms), root, m)]
            return res
    fragments(strip_roots(t), 0, res['pieces'])
    res['result'] = 'fragments' if res['pieces'] else 'nothing'
    return res


def mrs_view(m):
    """The MRS as plain JSON for the page's interactive view."""
    if m is None:
        return None
    eps = []
    for ep in m.rels:
        eps.append({'label': ep.label, 'pred': str(ep.predicate), 'from': ep.cfrom, 'to': ep.cto, 'carg': ep.carg,
                    'args': [[r, str(x)] for r, x in ep.args.items() if r != 'CARG']})
    return {'top': m.top, 'index': m.index, 'eps': eps,
            'hcons': [[h.hi, h.relation, h.lo] for h in m.hcons],
            'icons': [[i.left, i.relation, i.right] for i in (m.icons or [])],
            'vars': {v: {k.upper(): str(x) for k, x in props.items()} for v, props in m.variables.items()}}
