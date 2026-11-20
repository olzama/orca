# Orca: Omnilingual Replayable Constraint-based Analysis

<img src="assets/orca-logo.svg" alt="Orca logo: an orca inside a replay arrow" width="140">

Fast HPSG-style parsing and inspectable grammars for many languages. An orca is a fast dolphin: the project grows out of the DELPH-IN tradition.

## Why

Precision grammars in the HPSG tradition (Pollard and Sag 1994; Müller et al. 2021) give analyses that can be inspected and reasoned about: every node in a derivation is licensed by a documented type in a hierarchy, and the semantics is built together with the syntax. Two limitations keep this kind of analysis from being used more widely. Parsing is slow, to the point that long sentences cannot be parsed at all, and broad-coverage grammars exist for very few languages. Orca aims to remove both.

The point of doing so is to link fast parsing to linguistic hypothesis testing. An implemented grammar is a set of explicit hypotheses about a language, and parsing text with it tests them (Bender 2008). When the parser is fast and covers long sentences, those hypotheses can be tested on corpora of any size and in many languages, and every result can be traced back to the analysis that produced it.

## Goals

1. **Fast parsing.** Parse text of any length into HPSG-style derivations with semantics (Minimal Recursion Semantics; Copestake et al. 2005), starting with English and the English Resource Grammar (Flickinger 2000).
2. **More grammars.** Expand grammars that already exist, at any size, and create grammars for languages that have none. The Spanish Resource Grammar (Marimon 2010) is the first target for expansion.
3. **Inspectable results.** A parse is more than a labeled tree: it must be possible to explore the type hierarchy behind it and to read what each type and rule involved means.
4. **A better theory, in the long term.** We record where current syntactic theory strains and which alternatives exist. If that record adds up to a revision of the theory, we will publish it.

## Approach

**Draw on all available data.** No single source is enough for most languages, so the project combines them:

- implemented grammars, in HPSG and in other frameworks;
- annotated corpora, Universal Dependencies treebanks (de Marneffe et al. 2021) in particular;
- the theoretical literature (HPSG first, then other frameworks);
- typological databases;
- descriptive grammars written by field linguists;
- raw text.

**Bridges between parsing and grammar.** A fast parser alone gives labels; a grammar alone gives hypotheses that are too slow to test at scale. The bridge between them is what makes hypothesis testing possible: the parser's output is stated in the grammar's own types and rules and is checked by the grammar, so a change to an analysis shows up directly in what parses and how. For this reason Orca is not tied to any existing software, but its grammars and analyses should connect to what exists. At a minimum this means a bridge to [DELPH-IN](https://delph-in.github.io/docs/), so that a grammar can be expressed in the DELPH-IN formalism and existing DELPH-IN grammars and treebanks can be used directly. A second bridge runs in both directions between HPSG derivations and Universal Dependencies, so that new grammars can be trained on and tested against the many treebanks that exist in that format.

**Parsing as sequence labeling.** The parser design will probably build on parsing as sequence labeling (Gómez-Rodríguez and Vilares 2018; Strzyz et al. 2019; Kitaev and Klein 2020; Amini et al. 2023), which extends the supertagging that already speeds up HPSG parsing (Dridan 2013; Zamaraeva and Gómez-Rodríguez 2024): a neural tagger assigns each token a label, and the label sequence decodes to a full derivation. The grammar then *replays* the proposed derivation: it applies the named rules and lexical entries bottom-up by unification, with no search. A derivation that replays is licensed by the grammar and comes with its semantics; one that fails is reported with the place and cause of the failure, and a more relaxed analysis serves as a fallback. Every analysis Orca outputs can be replayed in this way, which is what the R in the name stands for.

## Status

Early stage. So far the repository contains a survey of the HPSG literature for consequences on the parser design, and statistics over the derivations of the English treebanks.

## Contents

- `reading/`: notes from literature surveys.
- `theory-log/`: observations and proposals about the theory.
- `analysis/`: corpus and treebank statistics.
- `scripts/`: utilities.

## References

- Amini, Afra, Tianyu Liu, and Ryan Cotterell. 2023. Hexatagging: Projective dependency parsing as tagging. In *Proceedings of ACL 2023*.
- Bender, Emily M. 2008. Grammar engineering for linguistic hypothesis testing. In *Proceedings of the Texas Linguistics Society X Conference: Computational Linguistics for Less-Studied Languages*, 16–36. Stanford: CSLI Publications.
- Copestake, Ann, Dan Flickinger, Carl Pollard, and Ivan A. Sag. 2005. Minimal Recursion Semantics: An introduction. *Research on Language and Computation* 3(2–3), 281–332.
- de Marneffe, Marie-Catherine, Christopher D. Manning, Joakim Nivre, and Daniel Zeman. 2021. Universal Dependencies. *Computational Linguistics* 47(2), 255–308.
- DELPH-IN: Deep Linguistic Processing with HPSG Initiative. https://delph-in.github.io/docs/
- Dridan, Rebecca. 2013. Ubertagging: Joint segmentation and supertagging for English. In *Proceedings of EMNLP 2013*.
- Flickinger, Dan. 2000. On building a more efficient grammar by exploiting types. *Natural Language Engineering* 6(1), 15–28.
- Gómez-Rodríguez, Carlos, and David Vilares. 2018. Constituent parsing as sequence labeling. In *Proceedings of EMNLP 2018*.
- Kitaev, Nikita, and Dan Klein. 2020. Tetra-tagging: Word-synchronous parsing with linear-time inference. In *Proceedings of ACL 2020*.
- Marimon, Montserrat. 2010. The Spanish Resource Grammar. In *Proceedings of LREC 2010*.
- Müller, Stefan, Anne Abeillé, Robert D. Borsley, and Jean-Pierre Koenig (eds.). 2021. *Head-Driven Phrase Structure Grammar: The handbook*. Berlin: Language Science Press. https://doi.org/10.5281/zenodo.5543318
- Pollard, Carl, and Ivan A. Sag. 1994. *Head-Driven Phrase Structure Grammar*. Chicago: University of Chicago Press.
- Strzyz, Michalina, David Vilares, and Carlos Gómez-Rodríguez. 2019. Viable dependency parsing as sequence labeling. In *Proceedings of NAACL 2019*.
- Zamaraeva, Olga, and Carlos Gómez-Rodríguez. 2024. Revisiting supertagging for faster HPSG parsing. In *Proceedings of EMNLP 2024*.
