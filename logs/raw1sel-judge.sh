#!/bin/bash
# O82: is the news gain real? On the unseen-news sentences where the raw1sel tagger now agrees with ACE and the headline tagger gave another analysis, the judge picks between the headline's reading ('orca' side) and ACE's (= raw1sel's).
cd /mnt/kesha/orca; D=analysis/corpus-modes-unseen/judge-replay-ace-raw1sel-gained
.venv/bin/python scripts/adjudicate.py run --out $D > $D.run.log 2>&1
.venv/bin/python scripts/adjudicate.py score --out $D >> $D.run.log 2>&1
echo "done $(date)" >> $D.run.log
