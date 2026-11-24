#!/bin/bash
# O91 step 1: the same cached DeBERTa-v3 large dev tags, replay+repair against ERG 2020 and ERG 2025 (current defaults).
cd /mnt/kesha/orca
.venv/bin/python scripts/repair_bench.py run --grammar data/erg/2020-orca/english.tdl --out analysis/grammar-drift/dev-2020.json > analysis/grammar-drift/dev-2020.log 2>&1 &
.venv/bin/python scripts/repair_bench.py run --gold-mrs data/profiles-2025/dev --out analysis/grammar-drift/dev-2025.json > analysis/grammar-drift/dev-2025.log 2>&1 &
wait
