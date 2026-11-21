#!/bin/bash
# ACE 30-best on Redwoods train, then 500-best for the sentences whose full
# 30-best list lacks the gold reading.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
$PY scripts/ace_nbest.py --profiles data/profiles-2025/train --out data/ranking/redwoods-train-ace30.jsonl --n 30 --workers 4
$PY - <<'P'
import json
with open('data/ranking/gold-beyond-30.ids', 'w') as f:
    for l in open('data/ranking/redwoods-train-ace30.jsonl'):
        r = json.loads(l)
        if len(r['results']) == 30 and not any(x['same_mrs'] for x in r['results']):
            f.write(r['id'] + '\n')
P
wc -l data/ranking/gold-beyond-30.ids
$PY scripts/ace_nbest.py --profiles data/profiles-2025/train --ids data/ranking/gold-beyond-30.ids \
    --out data/ranking/redwoods-train-ace500.jsonl --n 500 --workers 4 --slim
