# Hand-off notes (2026-11-20)

State of the Orca project at the end of the first working session, for whoever continues. Read the README first for the goals. Project memory (decisions, Olga's preferences, a dated log) is in the Claude memory folder of the `delphin` project; the files `universal-hpsg-open-questions.md`, `universal-hpsg-project-vision.md` and `semantic-accuracy-first.md` matter most.

## What exists and works

Pipeline for English with the ERG 2025 release:

1. **Tagger** (`scripts/train_tagger.py`): encoder with two heads per token. Leaf label = lexical type + lexical rules + unary rules; tree label = relative depth + rule of the lowest common ancestor with the next token (`orca/encoding.py`, lossless round trip on all treebank derivations).
2. **Lexicon lookup** (`orca/tfs/lexicon.py`): lexical entry from words + lexical type + lexical rules, by undoing spelling rules; ambiguity resolved by replay.
3. **Replay engine** (`orca/tfs/`): type hierarchy with greatest lower bounds (`hierarchy.py`), destructive unifier with undo trail and lazy type-constraint expansion (`dag.py`), grammar loading and replay with a subtree cache (`grammar.py`), MRS extraction (`mrs.py`).
4. **Repair** (`scripts/repair.py`): best-first search over the tagger's k best labels under the failing node; parallel workers.
5. **Evaluation**: `scripts/compare_mrs.py` (isomorphism with gold MRS via PyDelphin), `scripts/analyze_replay_outcomes.py`, `scripts/eval_trees.py`, `scripts/score_semantics.py` (written, not yet run; see below).

Checks that hold: every gold derivation of dev (2,062) and test (8,004) replays; gold derivations give the gold MRS for 2,062 of 2,062 dev sentences; gold labels with looked-up entries replay for 2,057 of 2,062.

## Current accuracy (dev, 2,062 sentences, tagger `tagger-2025b-bert`, repair budget 200, lexical entries)

| Measure | Result |
|---|---|
| Complete analysis accepted by the grammar | 89.0% (1,836) |
| Same MRS as gold | 56.9% (1,174) |
| Same tree as gold | 51.5% (1,061) |

Olga's reporting rule: an accepted analysis counts as a success; semantic accuracy (exact and partial) is the headline; tree accuracy is secondary. She considers the current accuracy poor.

## Data and environment (none of this is in git)

- Python: `/mnt/kesha/orca/.venv` (conda prefix, Python 3.11; PyDelphin, PyTorch, Transformers, peft, xlrd). Run tests with `.venv/bin/python -m pytest tests`.
- Grammar and gold profiles: `data/erg/2025` (tag `2025` of github.com/delph-in/erg). Split by profile name in `data/profiles-2025/{train,dev,test}` (symlinks; the split is the one in the release's `etc/redwoods.xls`; `sh-spband-r`, `ntucle`, `omw`, `wlb03`, `wnb03` and the aggregate profiles are excluded).
- Encoded data: `data/encoded-2025/*.jsonl` (from `scripts/encode_treebank.py`).
- Models: `data/models/` (`tagger-2025b-bert` is current; `bert-base-cased`). Encoders are in the Hugging Face cache; run with `HF_HUB_OFFLINE=1`.
- ACE: `/home/olga/delphin/tools/ACE/ace-0.9.34/ace`; compiled grammar `data/ace/erg-2025.dat`.
- GPUs: two RTX 2080 Ti (11 GB). Other machines (`mortimer`, `flash`, `mafalda`) belong to shared or other work; ask before using them.
- Everything under `/home/olga/delphin` and `/mnt/kesha/lenka-fork` is reference only: do not modify.

## In progress when this was written

1. **ACE baseline on dev.** `scripts/run_ace.py` was writing `data/ace/dev-ace-1best.jsonl` (1,787 of 2,062 done). When complete: retry sentences without an MRS at 16 GB / 120 s, then 28 GB / 300 s (same value for chart and unpack; flags `-1 --rooted-derivation --udx --max-words=1000`), and report resource failures separately from "no analysis". Then run `scripts/score_semantics.py --ace ... --pred data/models/tagger-2025b-bert/dev-repair-b200-entries.jsonl` to get, for ACE and for Orca, coverage, same MRS, and partial scores (F1 of predicates and of DMRS links). The script is untested. Caveats to state with the result: gold comes from ACE's own forest, so the baseline measures ACE's ranking model, which may have been trained on the dev profiles (not checked); ACE tokenizes raw text while Orca uses gold tokens.
2. **Replay speed.** Olga asked to optimize replay. Measured: about 47 sentences per second on one core (gold dev, entries), about 4,850 node unifications and 11,500 node copies per sentence; `copy` is about 58% of the time and `_merge` most of the rest (profile script idea: cProfile over `replay_with_entries` after a warm-up). Unfilling stored structures (`Grammar._unfill`, kept because it is harmless) did not reduce copying. Not yet tried, in suggested order: (a) run the replay stage under PyPy (no PyTorch needed in the workers); (b) copy less: copy only the part of the rule that the daughters touch, and write the rest when the mother is built (Slayden 2012, notes in `reading/notes/`), or find out which copies dominate (rules, type constraints during unification, lexical entries); (c) a compiled engine with flat arrays and a fixed feature order per type. Full pipeline today: 44 to 87 sentences per second on six cores; ACE on dev: about 8.6 sentences per second on one core (dev sentences are short).

## Next steps agreed or proposed

1. Finish the ACE baseline and the partial semantic score; add both to the walkthrough page.
2. Choose better among valid readings (the largest loss: 32% of dev sentences get a complete analysis with a different meaning): return several accepted analyses and rank them (the ERG's own ranking model, a ranker over the semantics, or an LLM choosing between grammar-licensed meanings).
3. Better tagger from more data: silver derivations from ACE on raw text, then fine-tuning on gold.
4. Long sentences (the original motivation): join the stretches that already replay; build a test set of sentences ACE cannot parse (the other parsing project records failures by length: almost none under 20 words, about two thirds parsed at 46 to 60 words, nothing above about 65).
5. Still missing: tokenization from raw text, variable properties in the MRS, root conditions and orthography of inflectional rules in gold replay, a check against cyclic structures.
6. Long-term reminders from Olga: high accuracy in the end; an LLM that learns from the grammar itself and not only from examples; expanding the grammar, other grammars (the Spanish Resource Grammar next), other theories.

## Experiments done (results in `analysis/`)

- Larger encoder (`xlm-roberta-large`): about two points better; needs `--freeze-embeddings --batch 16` on 11 GB.
- Decoder LM as encoder (Qwen2.5-1.5B + LoRA + BiLSTM): below `bert-base`.
- LLM labels sentences from retrieved examples (`scripts/llm_label.py`): as good as the tagger where its brackets balance; bracket counting fails on long sentences.
- LLM judges the tagger's doubtful decisions (`scripts/llm_judge.py`): no clear gain, with or without reasoning.

## Working rules (Olga's)

- American English everywhere. In papers, numbers go in tables and prose does not repeat them. Avoid "X rather than Y" and "not X but Y" unless the contrast is the point.
- End every status message with a short "Loose ends" list, limited to what matters for the immediate next step.
- State agent count and rough cost before multi-agent runs. Reading from `reading/QUEUE.md` happens in idle time, one document per agent, notes in `reading/notes/` in the existing format.
- Record strains in the theory in `theory-log/`.
- Retrain when the training data is corrected. Commit and push code once it has run and produced the expected result; commit messages end with the attribution lines used in the history.
- The walkthrough page (https://claude.ai/artifact/Vw5SDykPm9VX9zk8VptTLL, shared by link) is built from `docs/walkthrough/`; its built HTML lived in a session scratch folder and has to be regenerated from the template with the two helper scripts there.

## Known rough edges

- `scripts/repair.py` and `scripts/replay_predictions.py` take tokens from the gold profiles.
- Five gold-label dev sentences fail with looked-up entries (two ambiguous words; the choice procedure changes one at a time).
- The failure report of `replay_treebank.py` keeps one example per cause.
- Reading queue items 1c to 1g are papers not on disk, with citations from memory that must be verified.
- A nightly reading job was scheduled inside the first session only; it does not survive that session.
