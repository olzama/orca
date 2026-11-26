#!/bin/bash
# Raw-text tagger (news25 base + Gutenberg + Wikipedia silver, chosen by agreement) vs the news25 tagger, same current defaults, Redwoods dev from raw text.
cd /mnt/kesha/orca
CUDA_VISIBLE_DEVICES=1 HF_HUB_OFFLINE=1 .venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothraw1selsurf-debertav3large --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --save-mrs --out analysis/mrs/dev-2025bothraw1selsurf-debertav3large-rawtext-current.json > logs/eval-raw1sel.log 2>&1 &
CUDA_VISIBLE_DEVICES=0 HF_HUB_OFFLINE=1 .venv/bin/python scripts/orca_parse.py --tagger data/models/tagger-2025bothnews25surf-debertav3large --eval data/profiles-2025/dev --gold data/encoded-2025-bothall-surface/dev.jsonl --save-mrs --out analysis/mrs/dev-2025bothnews25surf-debertav3large-rawtext-current.json > logs/eval-news25-current.log 2>&1 &
wait
echo "eval-raw1sel exit $(date)" >> logs/eval-raw1sel.log
