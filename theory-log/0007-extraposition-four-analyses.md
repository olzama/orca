# 0007: Extraposition: four coexisting analyses

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

Extraposition of relative clauses, PPs, and complement clauses has four live analyses in HPSG, each using different machinery, and the chapters find "little to choose between these alternatives" in theoretical cost (Ch. 14, Section 4.1, pp. 637-639). One analysis gives up continuity, one adds a second nonlocal feature with zero-marked lexical rules and spurious ambiguity, and one gives up a tree-determined antecedent. On top of that, corpus data show that extraposition is not bounded by NP, PP, or the clause, and "a detailed account of extraposition island phenomena does not exist in any framework" (Ch. 15, Section 6, pp. 678-680).

## Evidence

- "Someone might win who does not deserve it" (Ch. 14, example (67)).
- Extraposed relatives and PPs whose host is embedded under several NP and PP nodes; extraposition from subjects and out of embedded clauses (Ch. 15, Sections 5-6, pp. 677-680).
- Split antecedents and hydras ("the boy and the girl who dated each other") (Ch. 13, Section 8.3, pp. 575-579; Ch. 14, fn. 22, p. 611).
- String-vacuous extraposition yields spurious ambiguity under EXTRA; a PERIPHERY feature was added to control it (Ch. 13, fn. 39).
- Crysmann (2013) says the unified EXTRA analysis "severely overgenerates" (Ch. 13, p. 579).

## Competing analyses

- Order domains with partial compaction: Kathol and Pollard 1995; Nerbonne 1994. Called "highly questionable" for English (Ch. 13, Section 8.2, p. 575).
- Nonlocal EXTRA with lexical rules at the source word and an n-ary Head-Extra Schema: Keller 1995; Bouma 1996; Müller 1999 (Ch. 13, Section 8.1, pp. 573-574).
- Anaphoric ANCHOR percolation, relying on MRS or LRS: Kiss 2005; Crysmann 2004; Walker 2017 (Ch. 13, Figure 12; Ch. 14, p. 638).
- Hybrid: ANCHOR for adjuncts, extraction-like for complements: Crysmann 2013. Crysmann 2005 is cited as a synthesis of Kiss and Keller with an efficient implementation; the chapters do not describe it.

## Consequence for our parser and grammars

EXTRA keeps the tree continuous, at the cost of a lexical rule on the source noun whose only evidence is a distant clause, and of reading the UD attachment from the feature structure. ANCHOR keeps the tree simplest, and the same rule application is compatible with several antecedents, so the tree may not determine the MRS (the Ch. 14 reader marks this as an inference to verify in Kiss 2005 and Crysmann 2004). Domains are outside the design.

## Proposal and test

Proposal: use the ANCHOR-style analysis with the antecedent left underspecified in the MRS when more than one nominal is available, and resolve attachment in the UD bridge with a ranking model.

Test: on extraposed relatives in an English UD treebank (non-projective acl:relcl), measure how often the set of ANCHOR candidates has more than one member and how often the nearest candidate is the gold antecedent. Prediction: the candidate set is a singleton or nearest-wins in the large majority of cases; if so, the underspecification costs little. Read Crysmann 2005 before implementing.

## Status

open.
