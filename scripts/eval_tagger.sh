#!/bin/bash
# Evaluate a trained as-typed tagger on 2025 dev: raw text (the headline), then
# treebank tokens (repair k30 b600, rerank, semantic scores).
# Usage: GPU=1 scripts/eval_tagger.sh MODEL_NAME TAG
set -e
cd /mnt/kesha/orca
M=data/models/$1; TAG=$2
export HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=${GPU:-1}
.venv/bin/python - <<P
import json; p='$M/labels.json'; d=json.load(open(p)); d['forms']='surface'; json.dump(d,open(p,'w'))
P
.venv/bin/python scripts/orca_parse.py --tagger $M --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl \
    --all-mrs --out analysis/mrs/dev-$TAG-rawtext.json > $M/rawtext.log 2>&1
.venv/bin/python scripts/repair.py --data data/encoded-2025-bothall-surface --grammar data/erg/2025/english.tdl --profiles data/profiles-2025/dev \
    --tagger $M --out analysis/replay/dev-$TAG-strict-k30-b600.json --pred-out $M/dev-strict-k30-b600.jsonl --budget 600 --entries --fast \
    --workers ${WORKERS:-3} --kbest 30 --gold-mrs > $M/repair.log 2>&1
.venv/bin/python scripts/rerank.py --grammar data/erg/2025/english.tdl --kbest $M/dev-strict-k30-b600.jsonl \
    --out analysis/replay/dev-$TAG-strict-rerank-k30.json --pred-out $M/dev-strict-rerank-k30.jsonl > $M/rerank.log 2>&1
.venv/bin/python -c "
import json
with open('$M/dev-strict-rerank-k30-labels.jsonl','w') as f:
    for l in open('$M/dev-strict-rerank-k30.jsonl'):
        c=json.loads(l); f.write(json.dumps({k:c[k] for k in ('id','forms','leaf','tree')})+'\n')"
.venv/bin/python scripts/score_semantics.py --grammar data/erg/2025/english.tdl --profiles data/profiles-2025/dev \
    --pred $M/dev-strict-rerank-k30-labels.jsonl --out analysis/mrs/dev-$TAG-strict-rerank-k30-labels-scores.json > $M/score.log 2>&1
echo "EVAL DONE $1"
