"""The unlikelihood term for labels the grammar rejected (train_tagger.py --rejections)."""
import json
import math
import os
import sys
import tempfile

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from train_tagger import attach_rejections, unlikelihood  # noqa: E402


def sents():
    return [{'id': 'a', 'forms': ['x', 'y', 'z'], 'leaf': ['L1', 'L2', 'L1'], 'tree': ['T1', 'T2', '<none>']},
            {'id': 'b', 'forms': ['u', 'v'], 'leaf': ['L2', 'L2'], 'tree': ['T1', '<none>']}]


LEAF = {'<unk>': 0, 'L1': 1, 'L2': 2, 'L3': 3}
TREE = {'<unk>': 0, 'T1': 1, 'T2': 2, '<none>': 3}


def write(recs):
    f = tempfile.NamedTemporaryFile('w', suffix='.jsonl', delete=False)
    for r in recs:
        f.write(json.dumps(r) + '\n')
    f.close()
    return f.name


def test_attach_skips_unknown_gold_and_out_of_range():
    s = sents()
    p = write([{'id': 'a', 'rejected': [['leaf', 1, 'L3'], ['leaf', 0, 'L1'], ['tree', 0, 'T9'], ['leaf', 7, 'L3']]},
               {'id': 'b', 'rejected': [['tree', 0, 'T2']]}])
    n = attach_rejections(s, p, LEAF, TREE)
    assert n == 2
    assert s[0]['rej'] == [('leaf', 1, 3)]          # gold label, unknown label, out of range dropped
    assert s[1]['rej'] == [('tree', 0, 2)]


def test_value_and_alignment():
    s = sents()
    s[0]['rej'] = [('leaf', 1, 3)]
    s[1]['rej'] = [('tree', 0, 2)]
    leaf = torch.zeros(5, 4)                       # 3 + 2 words, flattened in batch order
    tree = torch.zeros(5, 4)
    leaf[1, 3] = 2.0                               # word 1 of sentence a
    tree[3, 2] = -1.0                              # word 0 of sentence b (offset 3)
    pl = math.exp(2) / (math.exp(2) + 3)
    pt = math.exp(-1) / (math.exp(-1) + 3)
    want = (-math.log(1 - pl) - math.log(1 - pt)) / 5
    got = unlikelihood(s, [3, 2], leaf, tree).item()
    assert abs(got - want) < 1e-6


def test_truncated_words_skipped_and_empty_is_zero():
    s = sents()
    s[0]['rej'] = [('leaf', 2, 3)]
    assert unlikelihood(s, [2, 2], torch.zeros(4, 4), torch.zeros(4, 4)).item() == 0.0
    assert unlikelihood(sents(), [3, 2], torch.zeros(5, 4), torch.zeros(5, 4)).item() == 0.0


def test_gradient_lowers_rejected_label():
    s = sents()
    s[0]['rej'] = [('leaf', 1, 3)]
    leaf = torch.zeros(5, 4, requires_grad=True)
    tree = torch.zeros(5, 4)
    unlikelihood(s, [3, 2], leaf, tree).backward()
    with torch.no_grad():
        new = leaf - 1.0 * leaf.grad
    assert new[1].softmax(-1)[3] < leaf[1].softmax(-1)[3]
