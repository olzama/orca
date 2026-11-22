#!/bin/bash
# Hausa replay rate: Claude writes sentences from HaG's lexicon -> ACE (HaG) -> encode -> Orca replays?
# Usage: scripts/hausa_round.sh NAME [CALLS]
set -e
cd /mnt/kesha/orca
NAME=$1; CALLS=${2:-4}
H=/mnt/kesha/grammars/hag; W=data/hausa/$NAME; P=$W/profiles/hag-$NAME
mkdir -p $W
[ -s $W/sentences.txt ] || .venv/bin/python scripts/hausa_sentences.py --grammar-dir $H --out $W --calls $CALLS | tail -1
rm -rf $W/profiles; mkdir -p $W/profiles
R=$(ls -d data/profiles-2025/dev/*/ | head -1)relations
.venv/bin/delphin mkprof --input $W/sentences.txt --relations $R $P > /dev/null
.venv/bin/delphin process -g /mnt/kesha/grammars/hag-build/hag.dat --executable /home/olga/delphin/tools/ACE/ace-0.9.34/ace \
    --options="-1 --timeout=60 --max-chart-megabytes=4000 --max-unpack-megabytes=5000" $P > $W/ace.log 2>&1
.venv/bin/python - <<P 2>&1 | grep -v -i warn
import sys; sys.path.insert(0, 'scripts'); sys.setrecursionlimit(20000)
from encode_treebank import entry_types, run_split, lexrule_names
st, _ = run_split('$W/profiles', entry_types('$H'), '$W/encoded.jsonl', lexrule_names('$H/hausa.tdl'))
print({k: v for k, v in st.items() if k in ('derivations', 'round_trip_ok', 'round_trip_fail')})
P
.venv/bin/python scripts/filter_replayable.py --grammar $H/hausa.tdl --profiles $W/profiles --encoded $W/encoded.jsonl \
    --out-train $W/replayable.jsonl --out-held $W/held.jsonl --stats $W/filter.json --hold 0 --workers 2 2>&1 | grep -v -i warn | tail -1
echo "HAUSA DONE $NAME $(wc -l < $W/sentences.txt) sentences"
