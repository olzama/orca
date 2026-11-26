#!/bin/bash
# Re-time replay, fallback and chart on Redwoods dev together on a quiet kesha, now with the lexical filtering in restricted ACE (O115), for the walkthrough's modes table.
cd /mnt/kesha/orca
until [ "$(awk '{print int($1)}' /proc/loadavg)" -lt 2 ]; do sleep 60; done
export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1
L=logs/retime-quiet3.log; echo "start $(date) load $(cat /proc/loadavg)" >> $L
for m in replay fallback chart; do
  .venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothsurf-debertav3large --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --mode $m --save-mrs --all-mrs --out analysis/mrs/dev-modes-speed-quiet3-$m.json >> $L 2>&1
  echo "$m done $(date) load $(cat /proc/loadavg)" >> $L
done
echo "all done $(date)" >> $L
