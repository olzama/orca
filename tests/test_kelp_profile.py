"""Annotations are written to the profile's relations and read back."""
import os
import shutil

import pytest
from delphin import derivation, itsdb

from kelp.session import Session

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, '..', 'data', 'kelp', 'mrs-forest')
pytestmark = pytest.mark.skipif(not os.path.isdir(PROFILE), reason='needs the MRS test suite forest profile')


class FakeEngine:
    """Licenses every tree; stands in for Orca, which takes long to load."""
    def check(self, tree):
        return {'root': 'root_strict', 'dmrs': None, 'mrs': '[ TOP: h0 RELS: < > HCONS: < > ]'}


def rows(profile, relation, pid):
    return [r for r in itsdb.TestSuite(profile)[relation] if r['parse-id'] == pid]


def test_write_and_restore(tmp_path):
    profile = str(tmp_path / 'p')
    shutil.copytree(PROFILE, profile)
    for name in ('kelp-journal.jsonl',):
        if os.path.exists(os.path.join(profile, name)):
            os.remove(os.path.join(profile, name))
    lextypes = {'dog_n1': 'n_-_c_le'}
    s = Session(profile, engine=FakeEngine(), lextypes=lextypes, author='tester')
    pid = max(s.items, key=lambda p: s.items[p].total if s.items[p].total <= 50 else 0)
    other = next(p for p in s.items if p != pid and s.items[p].total > 1)

    st = s.state(pid)
    d = st['discriminants'][0]
    s.act(pid, 'decide', dict(d, kind={'chain': 'not-chain', 'present': 'absent', 'span': 'not-span'}[d['kind']]))
    assert rows(profile, 'tree', pid)[0]['t-active'] == -1          # saved at once, still open
    assert len(rows(profile, 'decision', pid)) == 1 and not rows(profile, 'result', pid)
    while s.state(pid)['remaining'] > 2:
        s.act(pid, 'decide', s.state(pid)['discriminants'][0])
    kept = s.state(pid)['remaining']
    done = s.act(pid, 'accept')                                     # one or two trees, all accepted
    s.act(other, 'reject')

    tree = rows(profile, 'tree', pid)[0]
    assert tree['t-active'] == kept and tree['t-author'] == 'tester'
    assert [r['result-id'] for r in rows(profile, 'preference', pid)] == list(range(kept))
    results = rows(profile, 'result', pid)
    assert len(results) == kept
    for r in results:
        d = derivation.from_string(r['derivation'])
        assert d.entity == 'root_strict' and d.daughters[0].start == 0
    for r in rows(profile, 'decision', pid):
        assert r['d-state'] in (1, 2) and r['d-type'] in (2, 3, 7, 8, 9) and r['d-value']
    assert rows(profile, 'tree', other)[0]['t-active'] == 0

    os.remove(os.path.join(profile, 'kelp-journal.jsonl'))          # restore from the relations alone
    again = Session(profile, engine=FakeEngine(), lextypes=lextypes)
    assert again.items[pid].status == 'accepted' and again.items[other].status == 'rejected'
    assert again.state(pid)['decisions'] == done['decisions']

    again.act(pid, 'undo')                                          # reopening removes the accepted trees
    assert rows(profile, 'tree', pid)[0]['t-active'] == -1 and not rows(profile, 'result', pid)
