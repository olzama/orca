#!/bin/bash
# O76: peak memory (max RSS) of one Orca process, replay and chart mode, on the first 200 dev sentences, kesha GPU 1.
cd /mnt/kesha/orca
for M in replay chart; do
  CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 /usr/bin/time -v .venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothsurf-debertav3large \
    --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --mode $M --limit 200 \
    --out /tmp/claude-1001/o76-mem-$M.json > /tmp/claude-1001/o76-mem-$M.log 2>&1
  echo "$M $(grep -E 'Maximum resident|Elapsed' /tmp/claude-1001/o76-mem-$M.log | tr '\n' ' ')"
done
