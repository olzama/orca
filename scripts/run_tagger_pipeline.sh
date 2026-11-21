#!/bin/bash
# Train a tagger (DATA, MODEL, TAG env vars), then the best pipeline (repair k30 b600, rerank)
# and semantic scoring on 2025 dev.
set -e
cd /mnt/kesha/orca
M=data/models/${MODEL:-tagger-2025lit-bert}
export HF_HUB_OFFLINE=1
mkdir -p $M
.venv/bin/python scripts/train_tagger.py --data data/${DATA:-encoded-2025-lit} --out $M --epochs 6 > $M/train.log 2>&1
.venv/bin/python scripts/repair.py --data data/encoded-2025 --grammar data/erg/2025/english.tdl --profiles data/profiles-2025/dev --tagger $M --out analysis/replay/dev-${TAG:-2025lit}-strict-k30-b600.json --pred-out $M/dev-strict-k30-b600.jsonl --budget 600 --entries --fast --workers 6 --kbest 30 --gold-mrs > $M/repair.log 2>&1
.venv/bin/python scripts/rerank.py --grammar data/erg/2025/english.tdl --kbest $M/dev-strict-k30-b600.jsonl --out analysis/replay/dev-${TAG:-2025lit}-strict-rerank-k30.json --pred-out $M/dev-strict-rerank-k30.jsonl > $M/rerank.log 2>&1
.venv/bin/python -c "
import json
with open('$M/dev-strict-rerank-k30-labels.jsonl','w') as f:
    for l in open('$M/dev-strict-rerank-k30.jsonl'):
        c=json.loads(l); f.write(json.dumps({k:c[k] for k in ('id','forms','leaf','tree')})+'\n')"
.venv/bin/python scripts/score_semantics.py --grammar data/erg/2025/english.tdl --profiles data/profiles-2025/dev --pred $M/dev-strict-rerank-k30-labels.jsonl --out analysis/mrs/dev-${TAG:-2025lit}-strict-rerank-k30-labels-scores.json > $M/score.log 2>&1
echo PIPELINE DONE
