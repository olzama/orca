# 0005: Non-constituent coordination: deletion in a surface-oriented theory

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

HPSG presents itself as surface-oriented and "what you see is what you get", yet for Right-Node Raising all existing analyses posit silent material (Ch. 19, Section 6.2, p. 874), and for argument cluster coordination the best-known analysis is left-periphery ellipsis (Ch. 16, Section 7, pp. 756-757). The deletion rules operate on phonological or order-domain lists and are relational: one rule name covers many amounts of deleted material. Scope of a shared quantifier comes out right only by stipulation (Ch. 29, Section 4.2.1, pp. 1361-1363). The authors of the coordination chapter state that there is no consensus on whether non-constituent coordination involves deletion (Ch. 16, Conclusion, p. 765).

## Evidence

- Right-Node Raising: shared material can be missing inside islands, can be part of a word ("sole or co-author"), can be discontinuous, and occurs outside coordination (Ch. 16, pp. 760-763, examples (78)-(84)); it tolerates syntactic mismatch in French (Abeillé et al. 2016; Shiraishi et al. 2019; Ch. 19, pp. 874-876; Ch. 29, pp. 1367-1368). Cumulative cases ("a total of $10,000 between them") are not the conjunction of two clausal meanings (Ch. 16, fn. 34).
- Argument clusters: different amounts of elided material give different meanings for one string (Ch. 16, example (72)), which supports ellipsis; "as well as", correlative placement in French, and constituent negation support surface clusters (Ch. 16, pp. 757-760).
- Optional Quantifier Merger "does not follow from any general principle and is merely stipulated"; Yatabe's version moves semantic composition from tree nodes to domain objects and needs a stipulated disjunctive constraint (Ch. 29, pp. 1361-1363).
- The ellipsis argument for clusters rests on the assumption that only like categories coordinate, which the same literature concedes is false (Ch. 19, fn. 33).

## Competing analyses

- Ellipsis or deletion: Beavers and Sag 2004; Yatabe 2001, 2004; Crysmann 2008; Chaves 2014 (who splits Right-Node Raising into extraposition, VP or N' ellipsis, and true Right-Node Raising).
- Surface clusters plus a lexical rule on the verb: Mouret 2006.
- Categorial Grammar: the strings are ordinary constituents with compositional meaning (Steedman; Dowty; Kubota and Levine 2015), with HPSG rebuttals (Yatabe and Tam 2021) and criticism of ellipsis (Levine 2011).

## Consequence for our parser and grammars

Deletion analyses give leaves without tokens and a rule whose effect is not fixed by its name; both break the tree encoding and deterministic replay. This is the main point in the Handbook where English data, not only other languages, press on the design. No chapter says what the ERG does.

## Proposal and test

Proposal: adopt cluster constituents (Mouret) for argument clusters. For Right-Node Raising, treat the shared material as attached once, at the right edge, to a coordination of unsaturated constituents, with valence sharing as in lexical coordination (Ch. 16, Section 5, pp. 750-753); send word-part and mismatch cases to the relaxed output.

Test: extract candidate sentences from Redwoods and from an English UD treebank (conj with shared right dependents; orphan relations). Measure (1) how many the ERG covers and with what derivation shape, (2) how many the proposed surface analysis covers with a correct MRS for shared quantifiers. Prediction: the surface analysis covers most corpus instances; the residue is dominated by the mismatch and sub-word types that Ch. 16 and Ch. 19 use as arguments for deletion.

## Status

open. Frequencies unknown; the Handbook gives none.
