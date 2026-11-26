#!/bin/bash
# Raw-text tagger vs news25 tagger on the 1,000 unseen news sentences (replay mode, agreement with ACE); headline tagger is run-replay.json
cd /mnt/kesha/orca; export HF_HUB_OFFLINE=1; O=analysis/corpus-modes-unseen
CUDA_VISIBLE_DEVICES=1 .venv/bin/python scripts/corpus_modes.py run --out $O --mode replay --tagger data/models/tagger-2025bothraw1selsurf-debertav3large --suffix=-raw1sel > logs/raw1sel-unseen.log 2>&1 &
CUDA_VISIBLE_DEVICES=0 .venv/bin/python scripts/corpus_modes.py run --out $O --mode replay --tagger data/models/tagger-2025bothnews25surf-debertav3large --suffix=-news25 > logs/news25-unseen.log 2>&1 &
wait
for s in -raw1sel -news25; do .venv/bin/python scripts/corpus_modes.py score --out $O --suffix=$s >> logs/raw1sel-unseen.log 2>&1; done
echo "raw1sel-unseen done $(date)" >> logs/raw1sel-unseen.log
