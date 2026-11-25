#!/bin/bash
# O114: fallback and chart mode timed without --all-mrs, quiet kesha, GPU 1 (replay: dev-retime-o114-plain.json)
cd /mnt/kesha/orca
export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1
L=logs/retime-o114.log; echo "b start $(date) load $(cat /proc/loadavg)" >> $L
for m in fallback chart; do
.venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothsurf-debertav3large --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --mode $m --save-mrs --out analysis/mrs/dev-retime-o114-plain-$m.json >> $L 2>&1
echo "$m plain done $(date) load $(cat /proc/loadavg)" >> $L
done
