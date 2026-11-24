"""The grammar's lexical filtering of generic (unknown-word) entries (roadmap O105, orca/tfs/lexfilter.py).

A chart parser drops a generic edge where a native entry covers the same token (the ERG's
generic_non_ne+native_lfr); Orca, building only the edge the tagger proposes, must do the same.
Uses ERG 2025 and the cached dev tagger output (raw-text tokens)."""
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

SPEEDER = 'ecpa/2252108'      # Which radar detector is the best for the occasional speeder?
TYPO = 'ecpa/2200708'         # My husband's birthdya is next week.


@pytest.fixture(scope='module')
def setup():
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexfilter import LexicalFilter
    from orca.tfs.lexicon import Lexicon
    g = Grammar(GRAMMAR)
    lx = Lexicon(g, os.path.dirname(GRAMMAR))
    lx.locate_missing = True
    fg = FastGrammar(g)
    lf = LexicalFilter(fg, lx)
    items = pickle.load(open(CACHE, 'rb'))['items']
    return fg, lx, lf, items


def token(items, sid, word):
    path = items[sid]['path']
    i = [q[0].lower() for q in path].index(word)
    return path[i][0], path[i][1]


def test_rules_are_loaded(setup):
    _, _, lf, _ = setup
    assert 'generic_non_ne+native_lfr' in lf.rules
    assert lf.is_generic('generic_mass_count_noun') and not lf.is_generic('speeder_n1')


def test_generic_with_a_native_entry_is_filtered(setup):
    fg, _, lf, items = setup
    form, tok = token(items, SPEEDER, 'speeder')
    fg.reset()
    assert lf.filtered('generic_mass_count_noun', ('n_ms-cnt_ilr',), [form], [tok])


def test_generic_without_a_native_entry_is_kept(setup):
    fg, _, lf, items = setup
    form, tok = token(items, TYPO, 'birthdya')
    fg.reset()
    assert not lf.filtered('generic_mass_count_noun', ('n_ms-cnt_ilr',), [form], [tok])


def test_regex_rules_do_not_fire_on_plain_words(setup):
    """The ERG's italics rules constrain ORTH.FORM by a regular expression the replay engine cannot
    match; without the regex check every generic word would be filtered."""
    fg, _, lf, items = setup
    assert any(lf.regex[n] for n in lf.rules)
    form, tok = token(items, TYPO, 'birthdya')
    fg.reset()
    assert not lf.filtered('generic_adj', (), [form], [tok])


def test_leaf_candidates_drop_filtered_generics(setup):
    from orca.encoding import Leaf, Node
    from orca.tfs.grammar import ReplayFailure
    from orca.tfs.lexicon import _leaf_candidates
    fg, lx, lf, items = setup
    form, tok = token(items, SPEEDER, 'speeder')
    generic_type = lx.type_of['generic_mass_count_noun']
    tree = Node('n_ms-cnt_ilr', (Leaf(generic_type, (form,)),))
    lx.lexical_filter = None
    fg.reset()
    _, usable = _leaf_candidates(fg, lx, tree, [tok], strict=False)
    assert 'generic_mass_count_noun' in usable[0]
    lx.lexical_filter = lf
    lx.word_fallback = False
    fg.reset()
    _, usable = _leaf_candidates(fg, lx, tree, [tok], strict=False)
    assert usable[0] == []                      # the fitting generic is filtered; the others do not fit the token
    with pytest.raises(ReplayFailure):
        fg.reset()
        _leaf_candidates(fg, lx, tree, [tok], strict=True)
    lx.word_fallback = True                     # O91's fallback offers the native noun instead
    fg.reset()
    _, usable = _leaf_candidates(fg, lx, tree, [tok], strict=False)
    assert 'speeder_n1' in usable[0]
    lx.word_fallback = False
    lx.lexical_filter = None
