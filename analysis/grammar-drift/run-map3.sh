#!/bin/bash
# O91 step 3, third pass: word fallback only for lexical types the grammar lacks.
cd /mnt/kesha/orca
M=data/label-map/erg-2025-to-2020.json; G20=data/erg/2020-orca/english.tdl
nice .venv/bin/python scripts/repair_bench.py run --grammar $G20 --label-map $M --map-types --word-fallback-missing-only --out analysis/grammar-drift/dev-2020-maptypes-fallbackmissing.json > analysis/grammar-drift/dev-2020-maptypes-fallbackmissing.log 2>&1
