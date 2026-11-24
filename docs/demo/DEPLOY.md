# Demo: several readings (24 November 2026)

## What changed
- When a sentence has more than one reading that the grammar accepts and the ranking model finds close, the page shows a row of tabs above the analysis panels, one per reading with its probability (for example "Reading 1 · 58%"). The number of readings and the percentages depend on the tagger: with BERT-base "I saw the man with the telescope." showed two readings, with DeBERTa-v3 large (the demo's tagger since 24 November) three. A tab redraws the meaning (DMRS and MRS), the derivation and the feature structure for that reading. In readings after the first, orange in the DMRS marks what reading 1 does not have. With one reading the page looks as before.
- Reading 1 is always the analysis shown before this change, so the ACE comparison and everything else are unchanged.
- The demo runs chart mode. For several readings it asks restricted ACE for its 20 best parses (`-n 20` instead of `-1`) and groups those with the same meaning; each reading is scored by its best parse's MaxEnt score, and its percentage is a softmax over the returned parses, summed per reading.

## Server API
- `POST /api/parse` takes two new optional fields:
  - `readings`: at most this many readings, 1 to 10 (default 5);
  - `margin`: only readings whose MaxEnt score is within this of the best, log space (default 1.25; `null` for no margin).
  `{"readings": 1}` gives exactly the old behavior.
- The response is backwards compatible: the top-level fields are reading 1 as before; a new `readings` list carries `probability` and `maxent score` for each reading, and for readings after the first also `mrs`, `mrs_view`, `dmrs` and `derivation`.
- Feature structures of readings after the first are fetched when their tab opens: `POST /api/parse` with `{"sentence": ..., "fs_for": i}` returns `{"reading": i, "fs": ..., "fs_note": ...}` (it parses the sentence again, about 0.1–0.3 s).

## Files
- `scripts/demo_server.py`: options, reading views, `fs_for`.
- `scripts/orca_parse.py`: `Parser.chart_readings` (chart mode), the replay-mode readings now carry what the demo needs, and the best reading's sign is restored after collecting readings; `strip_private()` keeps saved output free of in-memory fields.
- `scripts/supertag_ace.py`: `run_restricted_nbest` (ACE `-n K --tsdb-stdout`, reads each parse's MaxEnt score).
- `docs/demo/index.html`: the reading tabs.
- No new dependencies. Restart the server to pick up the change (deploy_demo.sh does this when loaded files change).

## Reading controls on the page (24 November 2026, later)

Below the Parse button there are now three controls: "At most N readings" (1 to 10, default 5; 1 shows only the top reading, the old behavior), "within M of the best" (the margin, default 1.25, in steps of 0.25) and "no margin". A "?" next to them explains them in plain English. The page sends them with every parse request and with the request for a further reading's feature structure, and remembers them in the viewer's browser. No server change: the server already accepted `readings` and `margin`. Only `docs/demo/index.html` changed; a page reload is enough, no restart.
