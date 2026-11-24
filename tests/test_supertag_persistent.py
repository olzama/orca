"""O106: chart mode's restricted ACE kept running (patched ACE, --per-item-disable) gives the
same output as one stock ACE run per sentence, and falls back cleanly when switched off."""
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
sys.path.insert(0, ROOT)

import supertag_ace as sa  # noqa: E402

needs_patched = pytest.mark.skipif(not os.access(sa.ACE_PATCHED, os.X_OK) or not os.access(sa.ACE, os.X_OK)
                                   or not os.path.exists(sa.DAT), reason='patched or stock ACE, or grammar image, missing')

SENTS = ['The dog barked.', 'I saw the man with the telescope.', 'the the the of of.']
# disable the ordinary entries of "dog" and "saw", as -L would
DISABLED = {'dog_n1', 'saw_v1', 'see_v1'}


def _both(fn, *args, **kw):
    out = {}
    for mode in ('0', '1'):
        os.environ['ORCA_ACE_PERSISTENT'] = mode
        out[mode] = [fn(s, *args, **kw) for s in SENTS]
        if mode == '1':
            assert sa.LAST.get('persistent') is True
    os.environ.pop('ORCA_ACE_PERSISTENT', None)
    return out


@needs_patched
def test_first_best_identical():
    out = _both(lambda s: sa.run_restricted(s, DISABLED, 60, trees=True)[:2])
    assert out['0'] == out['1']


@needs_patched
def test_nbest_identical():
    out = _both(lambda s: sa.run_restricted_nbest(s, DISABLED, 5, 60))
    assert out['0'] == out['1']


@needs_patched
def test_restriction_changes_between_items():
    os.environ['ORCA_ACE_PERSISTENT'] = '1'
    try:
        a = sa.run_restricted('The dog barked.', set(), 60)[0]
        b = sa.run_restricted('The dog barked.', {'dog_n1'}, 60)[0]
        c = sa.run_restricted('The dog barked.', set(), 60)[0]
    finally:
        os.environ.pop('ORCA_ACE_PERSISTENT', None)
    assert a == c and a != b


@needs_patched
def test_timing_fields():
    os.environ['ORCA_ACE_PERSISTENT'] = '1'
    try:
        sa.run_restricted_nbest('The dog barked.', set(), 3, 60)
    finally:
        os.environ.pop('ORCA_ACE_PERSISTENT', None)
    assert sa.LAST['wall seconds'] is not None and sa.LAST['parse seconds'] is not None


def test_switched_off_uses_stock():
    os.environ['ORCA_ACE_PERSISTENT'] = '0'
    try:
        assert sa._persistent(['-1'], sa.DAT) is None
    finally:
        os.environ.pop('ORCA_ACE_PERSISTENT', None)
