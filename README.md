# Orca: Omnilingual Rapid Constraint-based Analysis

Fast HPSG-style parsing and inspectable grammars for many languages. An orca is a fast dolphin: the project grows out of the DELPH-IN tradition and aims to be much faster.

Working repository. Goals, in order of priority:

1. Fast HPSG-style parsing (derivations plus MRS), starting with English and the ERG.
2. Expanding existing grammars (the SRG next) and creating grammars for more languages,
   drawing on computational grammars, treebanks (UD in particular), typology, and
   descriptive grammars.
3. Long term: record where the theory strains and, if warranted, revise it.

Existing DELPH-IN software, grammars and treebanks in `/home/olga/delphin` are reference material
only; this project does not depend on them at run time. The motivating downstream experiment is
`/mnt/kesha/lenka-fork`.

- `reading/`: notes from literature surveys (sources are fetched by `scripts/`).
- `theory-log/`: theory-level observations and proposals.
- `scripts/`: utilities.
