"""Lexicon lookup across grammar versions (roadmap O91 step 3): a lexical type the grammar
lacks is found through the type map, and the word-level fallback offers the word's entries of
other types with the same part of speech. Both are off unless set. Uses ERG 2025."""
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, ROOT)
sys.setrecursionlimit(20000)
GRAMMAR = os.path.join(ROOT, 'data/erg/2025/english.tdl')
pytestmark = pytest.mark.skipif(not os.path.exists(GRAMMAR), reason='needs ERG 2025')


@pytest.fixture(scope='module')
def lx():
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon
    return Lexicon(Grammar(GRAMMAR), os.path.dirname(GRAMMAR))


def test_off_by_default(lx):
    assert lx.lookup(['dog'], 'no_such_type_le', ()) == []


def test_type_map(lx):
    real = lx.lookup(['dog'], 'n_-_c_le', ())
    assert real
    lx.type_map = {'old_dog_type_le': ['n_-_c_le']}
    try:
        assert lx.lookup(['dog'], 'old_dog_type_le', ()) == real
    finally:
        del lx.type_map


def test_word_fallback_same_part_of_speech(lx):
    lx.word_fallback = True
    try:
        found = lx.lookup(['dog'], 'n_-_no-such-variant_le', ())
        assert found and all(lx.type_of[e].startswith('n_') for e in found)
        assert not any(lx.type_of[e].startswith('v_') for e in lx.lookup(['dog'], 'n_-_no-such-variant_le', ()))
    finally:
        lx.word_fallback = False


def test_exact_entries_win(lx):
    lx.word_fallback = True
    try:
        assert lx.lookup(['dog'], 'n_-_c_le', ()) == [e for e in lx.lookup(['dog'], 'n_-_c_le', ())]
        assert all(lx.type_of[e] == 'n_-_c_le' for e in lx.lookup(['dog'], 'n_-_c_le', ()))
    finally:
        lx.word_fallback = False


def test_word_fallback_missing_type_only(lx):
    lx.word_fallback = 'missing-type'
    try:
        # type exists in the grammar, word lacks an entry of it: no fallback (repair handles the tagger's error)
        assert 'n_-_mc_le' in lx._types() and lx.lookup(['dog'], 'n_-_mc_le', ()) == []
        # type unknown to this grammar: fallback to the word's entries of the same part of speech
        assert lx.lookup(['dog'], 'n_-_no-such-variant_le', ())
    finally:
        lx.word_fallback = False
