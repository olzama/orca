"""Labels the grammar does not define fail soft: replay reports a ReplayFailure (a rejection
that repair can move past), never another exception. Matters when the tagger and the grammar
come from different versions (roadmap O91). Uses ERG 2025 and the cached dev tagger output."""
import os
import pickle
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, ROOT)
sys.setrecursionlimit(20000)
GRAMMAR = os.path.join(ROOT, 'data/erg/2025/english.tdl')
CACHE = os.path.join(ROOT, 'data/bench/dev-debertav3large-tags.pkl')
pytestmark = pytest.mark.skipif(not (os.path.exists(GRAMMAR) and os.path.exists(CACHE)), reason='needs ERG 2025 and the dev tag cache')


@pytest.fixture(scope='module')
def setup():
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    g = Grammar(GRAMMAR)
    lx = Lexicon(g, os.path.dirname(GRAMMAR))
    lx.locate_missing = True
    fg = FastGrammar(g)
    items = pickle.load(open(CACHE, 'rb'))['items']
    return fg, lx, items


def replay(fg, lx, it, leaf, tree):
    from eval_trees import to_leaves
    from orca.encoding import decode
    from orca.tfs.lexicon import replay_with_entries
    forms = [q[0] for q in it['path']]
    fg.reset()
    return replay_with_entries(fg, lx, decode(to_leaves(forms, leaf, tree)), [q[1] for q in it['path']])


def first_guess(it):
    top = it['top']
    return [c[0][0] for c in top['leaf']], [c[0][0] for c in top['tree']]


def accepted_item(fg, lx, items):
    for sid in ('ecpa/2200108', *list(items)[:50]):
        it = items.get(sid)
        if not it or not it['top'] or len(it['forms']) < 3:
            continue
        leaf, tree = first_guess(it)
        try:
            replay(fg, lx, it, leaf, tree)
            return it, leaf, tree
        except Exception:
            continue
    pytest.skip('no accepted first guess found')


def test_unknown_lexical_type_is_a_rejection(setup):
    from orca.tfs.grammar import ReplayFailure
    fg, lx, items = setup
    it, leaf, tree = accepted_item(fg, lx, items)
    bad = list(leaf)
    bad[0] = 'zz_no-such-type_le' + bad[0][bad[0].index('|'):]
    with pytest.raises(ReplayFailure):
        replay(fg, lx, it, bad, tree)


def test_unknown_lexical_rule_is_a_rejection(setup):
    from orca.tfs.grammar import ReplayFailure
    fg, lx, items = setup
    it, leaf, tree = accepted_item(fg, lx, items)
    parts = leaf[0].split('|')
    parts[1] = (parts[1] + ' zz_no-such_lr').strip()
    bad = list(leaf)
    bad[0] = '|'.join(parts)
    with pytest.raises(ReplayFailure):
        replay(fg, lx, it, bad, tree)


def test_unknown_phrasal_rule_is_a_rejection(setup):
    from orca.tfs.grammar import ReplayFailure
    fg, lx, items = setup
    it, leaf, tree = accepted_item(fg, lx, items)
    j = next(i for i, t in enumerate(tree[:-1]) if '|' in t and t.split('|', 1)[1].split()[-1] != '<none>')
    depth, body = tree[j].split('|', 1)
    xs = body.split()
    xs[-1] = 'zz-no-such_c'
    bad = list(tree)
    bad[j] = depth + '|' + ' '.join(xs)
    with pytest.raises(ReplayFailure):
        replay(fg, lx, it, leaf, bad)
