# Orca: Omnilingual Rapid Constraint-based Analysis

Fast HPSG-style parsing and inspectable grammars for many languages. An orca is a fast dolphin: the project grows out of the DELPH-IN tradition.

## Why

Precision grammars in the HPSG tradition give analyses that can be inspected and reasoned about: every node in a derivation is licensed by a documented type in a hierarchy, and the semantics is built together with the syntax. Two limitations keep this kind of analysis from being used more widely. Parsing is slow, to the point that long sentences cannot be parsed at all, and broad-coverage grammars exist for very few languages. Orca aims to remove both.

## Goals

1. **Fast parsing.** Parse text of any length into HPSG-style derivations with semantics (Minimal Recursion Semantics), starting with English and the English Resource Grammar.
2. **More grammars.** Expand grammars that already exist, at any size, and create grammars for languages that have none. The Spanish Resource Grammar is the first target for expansion.
3. **Inspectable results.** A parse is more than a labeled tree: it must be possible to explore the type hierarchy behind it and to read what each type and rule involved means.
4. **A better theory, in the long term.** We record where current syntactic theory strains and which alternatives exist. If that record adds up to a revision of the theory, we will publish it.

## Approach

**Draw on all available data.** No single source is enough for most languages, so the project combines them:

- implemented grammars, in HPSG and in other frameworks;
- annotated corpora, Universal Dependencies treebanks in particular;
- the theoretical literature (HPSG first, then other frameworks);
- typological databases;
- descriptive grammars written by field linguists;
- raw text.

**Bridges to existing resources.** Orca is not tied to any existing software, but its grammars and analyses should connect to what exists. At a minimum this means a bridge to DELPH-IN, so that a grammar can be expressed in the DELPH-IN formalism and existing DELPH-IN grammars and treebanks can be used directly. A second bridge runs in both directions between HPSG derivations and Universal Dependencies, so that new grammars can be trained on and tested against the many treebanks that exist in that format.

**Parsing as sequence labeling.** The parser design will probably build on parsing as sequence labeling: a neural tagger assigns each token a label, and the label sequence decodes to a full derivation. The grammar then checks the proposed derivation and builds the semantics, so that the output is licensed by the grammar wherever possible, with a more relaxed analysis as a fallback. This part of the design is still open.

## Status

Early stage. So far the repository contains a survey of the HPSG literature for consequences on the parser design, and statistics over the derivations of the English treebanks.

## Contents

- `reading/`: notes from literature surveys.
- `theory-log/`: observations and proposals about the theory.
- `analysis/`: corpus and treebank statistics.
- `scripts/`: utilities.
