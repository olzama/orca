#!/bin/bash
# Evaluate a tagger on generated rounds (ACE's first parse as reference), then let the LLM judge rule on its disagreements.
# Usage: GPU=0 scripts/gen_eval_tagger.sh MODEL_DIR KEY ROUND...
set -e
cd /mnt/kesha/orca
M=$1; K=$2; shift 2
export HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=${GPU:-0}
for NAME in "$@"; do
  G=data/generated/$NAME; E=analysis/mrs/gen-$NAME-bothsurf-$K-rawtext.json; A=analysis/adjudicate/gen-$NAME-$K
  [ -s $E ] || .venv/bin/python scripts/orca_parse.py --tagger $M --eval $G/profiles --gold $G/train.jsonl --save-mrs --out $E 2>&1 | grep -A4 '"counts"'
  .venv/bin/python scripts/adjudicate.py prepare --eval $E --profiles $G/profiles --sentences $G/sentences.txt --out $A 2>&1 | grep -v -i "warn\|links = \|top = "
  .venv/bin/python scripts/adjudicate.py run --out $A > $A.run.log 2>&1
  .venv/bin/python scripts/adjudicate.py score --out $A | grep -v by_id
  echo "DONE $NAME"
done
