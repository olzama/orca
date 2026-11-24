"""token_chart with one ACE process kept running gives the same token chart as one ACE run per sentence."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from orca.tokens import token_chart  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..')
ACE = '/home/olga/delphin/tools/ACE/ace-0.9.34/ace'
DAT = os.path.join(ROOT, 'data/ace/erg-2025.dat')
pytestmark = pytest.mark.skipif(not (os.path.exists(ACE) and os.path.exists(DAT)), reason='ACE or the ERG image not available')


@pytest.mark.parametrize('sentence', ['I saw the man with the telescope.', 'Yes.', '', 'Do you have it and how much does it cost?'])
def test_same_as_per_call(sentence):
    assert token_chart(sentence, ACE, DAT) == token_chart(sentence, ACE, DAT, per_call=True)


def test_survives_fork():
    ref = token_chart('I saw it.', ACE, DAT, per_call=True)
    assert token_chart('I saw it.', ACE, DAT) == ref
    pid = os.fork()
    if pid == 0:
        os._exit(0 if token_chart('I saw it.', ACE, DAT) == ref else 1)
    _, status = os.waitpid(pid, 0)
    assert status == 0
    assert token_chart('I saw it.', ACE, DAT) == ref
