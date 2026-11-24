"""What is sent to the model that explains readings, and when there is no model."""
import pytest

from kelp import explain as X

A = {'nodes': [{'id': 1, 'pred': '_show_v_1', 'carg': None}, {'id': 2, 'pred': 'named', 'carg': 'Browne'}],
     'links': [{'from': 1, 'to': 2, 'role': 'ARG3', 'post': 'NEQ'}]}
B = {'nodes': [{'id': 1, 'pred': '_show_v_1', 'carg': None}, {'id': 2, 'pred': 'named', 'carg': 'Browne'},
               {'id': 3, 'pred': '_to_p', 'carg': None}],
     'links': [{'from': 3, 'to': 2, 'role': 'ARG2', 'post': 'NEQ'}, {'from': 3, 'to': 1, 'role': 'ARG1', 'post': 'EQ'}]}


def test_only_the_differences_are_sent():
    a, b = X.distinguishing([A, B])
    assert a == ['_show_v_1 -ARG3-> named("Browne")']
    assert b == ['_to_p -ARG1/EQ-> _show_v_1', '_to_p -ARG2-> named("Browne")', 'node _to_p']
    text = X.prompt('Abrams showed the office to Browne.', [(1, a, []), (2, b, ['"to": lexical entry to_nmod, type p_np_i-nm-no-tm_le'])])
    assert 'Reading 2: _to_p -ARG1/EQ-> _show_v_1' in text and 'to_nmod' in text and 'node _show_v_1' not in text


def test_no_model(monkeypatch):
    assert X.choose('none') is None
    monkeypatch.setattr(X.shutil, 'which', lambda name: None)
    for _, _, key, _ in X.PROVIDERS.values():
        if key:
            monkeypatch.delenv(key, raising=False)
    assert X.choose('auto') is None
    monkeypatch.setenv('GEMINI_API_KEY', 'x')
    assert X.choose('auto') == 'gemini'
    with pytest.raises(SystemExit):
        X.choose('openai')


def test_answer_parsing():
    assert X._parse('Here: {"1": "a", "2": "b"}') == {'1': 'a', '2': 'b'}
    with pytest.raises(ValueError):
        X._parse('no answer')
