"""A session keeps decisions in its journal and restores them."""
import os

import pytest

from kelp.session import Session

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, '..', 'data', 'kelp', 'mrs-forest')
pytestmark = pytest.mark.skipif(not os.path.isdir(PROFILE), reason='needs the MRS test suite forest profile')


def test_decide_undo_accept_and_restore(tmp_path):
    journal = str(tmp_path / 'journal.jsonl')
    s = Session(PROFILE, journal)
    pid = max(s.items, key=lambda p: s.items[p].total)
    st = s.state(pid)
    assert st['remaining'] == st['total'] > 1 and st['tree'] and not st['tree']['settled']
    d = st['discriminants'][0]
    yes = s.act(pid, 'decide', d)
    assert yes['remaining'] == d['count']
    assert s.act(pid, 'undo')['remaining'] == st['total']
    no = s.act(pid, 'decide', dict(d, kind={'chain': 'not-chain', 'present': 'absent', 'span': 'not-span'}[d['kind']]))
    assert no['remaining'] == st['total'] - d['count']
    with pytest.raises(ValueError):
        s.act(pid, 'decide', d)                     # contradicts the "no"
    while s.state(pid)['discriminants']:            # say yes until nothing is left to decide
        s.act(pid, 'decide', s.state(pid)['discriminants'][0])
    done = s.act(pid, 'accept')
    assert done['remaining'] == 1 and done['status'] == 'accepted' and done['tree']['settled']

    again = Session(PROFILE, journal).state(pid)
    assert again['decisions'] == done['decisions'] and again['status'] == 'accepted'
