# 0009: Formal foundations: the theory's logic versus what implementations run

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

The canonical formalism of Pollard and Sag (1994) is model-theoretic: total, sort-resolved objects, a description language with negation, disjunction, quantification, and relations, and no unification. Every implementation platform runs the 1987-style logic of partial feature structures with unification (Ch. 3, Sections 1-2, pp. 89-93). Shared AVM notation "contributes to obscuring substantial differences". Analyses in the theoretical literature freely use devices that the DELPH-IN formalism lacks: set-valued features with union, relational constraints such as shuffle and append with unknown split points, and default constraints. Defaults in particular carry central principles while not being "a well-defined part of the formal foundations of theoretical HPSG" (Ch. 17, fn. 23, p. 790).

## Evidence

- All of the RSRL constructs are said to be necessary to render Pollard and Sag (1994) without reformulating it (Ch. 3, pp. 93, 96-98).
- Default principles: the Generalised Head Feature Principle, SLASH Amalgamation, REL propagation (Ch. 1, Section 5.1, pp. 23-24; Ch. 13, Section 4, pp. 549-550; Ch. 14, fn. 25, p. 613). Default inheritance is accepted by some and rejected by others (Ch. 31, Section 3, pp. 1460-1462); Malouf holds defaults are abbreviatory and can be compiled out (Ch. 4, fn. 10, p. 151).
- Set-valued SLASH with several members; which member a rule binds is not fixed by the rule (Ch. 13, pp. 540-543; Ch. 15, pp. 680-681). The ERG limits SLASH to one element (Ch. 25, fn. 9, p. 1109).
- Relational constraints throughout the schemata (Ch. 10, pp. 375-379, 391-398; Ch. 11, pp. 427-456; Ch. 23, pp. 1053-1065).
- Blocking "necessitates a change to the logic" (Ch. 21, Section 3.3, pp. 963-964).
- Four competing model theories; two of them fail their intended one-to-one correspondence between utterances and structures (Ch. 3, Section 6, pp. 117-122).
- Theory is shaped by platforms, and analyses are sometimes chosen for parser efficiency (Ch. 3, pp. 89-91; Ch. 25, pp. 1109-1110). TRALE lets engineers implement a wider range of proposals directly than the LKB (Melnik 2007; Ch. 25, p. 1117).
- The formalism is Turing-complete; tractability is left to the particular grammar (Ch. 25, p. 1108; Ch. 28, p. 1305).
- The gap is old. Carroll (1993, PhD thesis, Section 1.3.1, pp. 5-6) says the declarative theories of the 1980s "tend not to be well suited to practical parsing with large grammars" because they rely on the conceptually simultaneous application of principles, and that wide-coverage projects therefore adopted simpler formalisms with straightforward computational interpretations, partly because a direct implementation of one theory would soon become obsolete (Boguraev et al. 1988). No system had used an unmodified implementation of GPSG, LFG, or ID/LP format (pp. 14-15). Notes in `reading/notes/carroll-1993-ch1-introduction.md`.

## Competing analyses

- Model-theoretic HPSG with RSRL: King 1999; Pollard 1999; Richter 2004, 2007.
- Unification over typed feature structures: Pollard and Sag 1987; Copestake 2002 (DELPH-IN).
- TRALE as a middle position with relations, complex antecedents, and empty elements.
- Type Theory with Records, which replaces unification by merge and predication (Ch. 26, Sections 3-4, pp. 1167-1176).

## Consequence for our parser and grammars

"Licensed by the grammar" in our strict output means licensed under the implementation formalism. A small unification engine is enough for DELPH-IN grammars as Ch. 25 describes them and not enough for grammars taken directly from the theoretical literature, which need compilation (sets to lists, defaults expanded, relations unfolded into rule variants). Each compilation multiplies rule names and labels.

## Proposal and test

Proposal: define an explicit "replayable fragment" of HPSG: typed feature structures, list-valued features, fixed-arity rules, no relations, no defaults at run time. State for each construct outside it the compilation that brings it inside, and the cost in rule names.

Test: for a sample of analyses from Tier 1 of the reading list (for example SLASH Amalgamation, the Argument Realization Principle with list difference, schema (19) with two appends), write the compiled version and count rule variants. Prediction: bounded and small for English; position-indexed variants grow linearly with maximum valence length (four or five in DELPH-IN grammars, Ch. 25, p. 1109).

## Status

open.
