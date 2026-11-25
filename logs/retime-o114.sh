#!/bin/bash
# O114: why the quiet re-timing (5.4 sentences/s) is slower than the 23 Nov headline (6.8): replay with and without --all-mrs, quiet kesha, GPU 1
cd /mnt/kesha/orca
export CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1
L=logs/retime-o114.log; echo "start $(date) load $(cat /proc/loadavg)" >> $L
.venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothsurf-debertav3large --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --mode replay --save-mrs --out analysis/mrs/dev-retime-o114-plain.json >> $L 2>&1
echo "plain done $(date) load $(cat /proc/loadavg)" >> $L
.venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothsurf-debertav3large --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --mode replay --save-mrs --all-mrs --out analysis/mrs/dev-retime-o114-allmrs.json >> $L 2>&1
echo "allmrs done $(date) load $(cat /proc/loadavg)" >> $L
