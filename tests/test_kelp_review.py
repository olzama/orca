"""The review of two given analyses: reading the input, blind sides, verdicts in terms of a and b."""
import json
import os
import shutil

from kelp.review import Review

SAMPLE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'kelp-review-sample.jsonl')


def test_blind_review_and_verdicts(tmp_path):
    path = str(tmp_path / 'set.jsonl')
    shutil.copy(SAMPLE, path)
    r = Review(path, author='tester')
    first, lost = r.listing()
    assert first['left']['label'] == '' and first['left']['is'] is None          # blind until judged
    assert first['left']['words'] == ['Abrams', 'showed', 'the', 'office', 'to', 'Browne', '.']
    assert first['left']['tree'] and first['left']['dmrs']['nodes'][0]['from'] >= 0
    assert [s['tree'] for s in (lost['left'], lost['right'])].count(None) == 1    # one side has no analysis
    r.judge(first['id'], 'left', 'a note')
    shown = r.by_id[first['id']]['left']
    rec = json.loads(open(str(tmp_path / 'set.verdicts.jsonl')).read().splitlines()[-1])
    assert rec['verdict'] == shown and rec['note'] == 'a note' and rec['shown']['left'] == shown
    again = Review(path).listing()[0]
    assert again['verdict'] == 'left' and again['left']['is'] == shown and again['left']['label']
    labeled = Review(path, labeled=True).listing()[0]
    assert labeled['left']['is'] == 'a' and labeled['verdict'] == ('left' if shown == 'a' else 'right')


def test_groups_and_resolved_verdicts(tmp_path):
    path = str(tmp_path / 'set.jsonl')
    recs = [json.loads(line) for line in open(SAMPLE)]
    recs[1]['group'] = recs[0]['group']                      # both items in one group; the second is its example
    recs[1]['example'] = True
    with open(path, 'w') as f:
        f.write(''.join(json.dumps(r) + '\n' for r in recs))
    r = Review(path, author='tester')
    first, second = (it['id'] for it in r.items)
    r.judge(second, 'neither', '')
    resolved = lambda: {d['id']: d for d in map(json.loads, open(str(tmp_path / 'set.resolved.jsonl')))}
    assert resolved()[first] == {'id': first, 'group': recs[0]['group'], 'verdict': 'neither', 'from': 'group', 'example': False}
    r.move(first, None)                                      # taken out: the group's verdict no longer holds for it
    assert resolved()[first]['verdict'] == '' and resolved()[first]['group'] is None
    assert Review(path).entry(Review(path).by_id[first])['moved']
    r.move(first, '')                                        # put back
    assert resolved()[first]['from'] == 'group' and not r.moves
