#!/bin/bash
# O91 step 3: label mapping and word-level fallback, same cached DeBERTa-v3 large dev tags (CPU).
cd /mnt/kesha/orca
M=data/label-map/erg-2025-to-2020.json; G20=data/erg/2020-orca/english.tdl
nice .venv/bin/python scripts/repair_bench.py run --grammar $G20 --label-map $M --map-types --out analysis/grammar-drift/dev-2020-maptypes.json > analysis/grammar-drift/dev-2020-maptypes.log 2>&1 &
nice .venv/bin/python scripts/repair_bench.py run --grammar $G20 --label-map $M --map-types --word-fallback --out analysis/grammar-drift/dev-2020-maptypes-fallback.json > analysis/grammar-drift/dev-2020-maptypes-fallback.log 2>&1 &
nice .venv/bin/python scripts/repair_bench.py run --gold-mrs data/profiles-2025/dev --word-fallback --out analysis/grammar-drift/dev-2025-fallback.json > analysis/grammar-drift/dev-2025-fallback.log 2>&1 &
wait
