"""token_chart: a tokenizer timeout is retried, then fails soft (no tokens) instead of raising."""
import os
import stat
import sys
import tempfile
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from orca.tokens import token_chart  # noqa: E402


def _script(body):
    fd, path = tempfile.mkstemp(suffix='.sh')
    with os.fdopen(fd, 'w') as f:
        f.write('#!/bin/sh\n' + body + '\n')
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


def test_timeout_fails_soft():
    slow = _script('sleep 5')
    try:
        t = time.time()
        assert token_chart('x', slow, 'g', timeout=0.3, retry_timeout=0.6) == []
        assert time.time() - t < 3            # both attempts, not the full sleep
    finally:
        os.remove(slow)


def test_retry_succeeds():
    # first call is slow, second fast: a marker file tells the script which call it is
    marker = tempfile.mktemp()
    s = _script(f'if [ -e {marker} ]; then exit 0; else touch {marker}; sleep 5; fi')
    try:
        assert token_chart('x', s, 'g', timeout=0.3, retry_timeout=2) == []   # no token lines, but no exception
        assert os.path.exists(marker)
    finally:
        os.remove(s)
        if os.path.exists(marker):
            os.remove(marker)
