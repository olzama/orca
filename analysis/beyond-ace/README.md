# Sentences ACE could not parse that Orca analyzes

Candidates as in `diagnose_rejections.py gaps`: dev items without a gold analysis, dev items ACE fails on, generated sentences ACE could not parse (original ACE runs: 60 s, 4,000/5,000 MB). Orca (DeBERTa tagger, on CPU) analyzed 138 of them (`orca.jsonl`).

ACE rerun one sentence at a time with `-1 --timeout=300 --max-chart-megabytes=6000 --max-unpack-megabytes=6000` (lowered from 12,000 because GPU training shared the RAM; started only with at least 12 GB available). Limits recorded per sentence in `ace.jsonl`. "memory limit" = ACE stopped at the 6,000 MB cap.

Claude Opus judged Orca's reading alone (predicates and links): RIGHT, PARTLY, WRONG (`verdicts.json`, $1.80). `summary.json` has counts. Built by `scripts/beyond_ace.py collect|judge|score`.
