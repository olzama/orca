# 0003: Order domains: is word order part of constituent structure?

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

The founding word order principle was never stated. The Constituent Order Principle of Pollard and Sag (1987) is "more of a promissory note than an actual principle" (Ch. 2, Section 2.2, pp. 51-52), and its function order-constituents "was never worked out in detail" (Ch. 10, Section 3, p. 377). Two incompatible answers grew in the gap: order as concatenation of daughters' PHON values, tied to the tree, and order read off a separate DOM list (Reape 1994; Kathol 2000) that lets non-sisters interleave. The Handbook's introduction calls the role of domains "an unresolved matter" and declines to say whether HPSG with domains is still monostratal (Ch. 1, Section 7.1, pp. 32-34).

## Evidence

- Against domains for German clause structure: they produce spurious ambiguity and fail on multiple fronting (Ch. 10, Section 6.4, pp. 397-401); pure linearization cannot handle agreement and the remote passive in verbal complexes (Ch. 11, Section 5.1.2, pp. 453-456).
- For domains: Warlpiri split NPs (Donohue and Sag 1999; Ch. 10, Section 6.2, pp. 394-395; Ch. 30, Section 10, pp. 1420-1423); scrambling with Korean control verbs, which fail the tests for argument attraction, so the authors say it "must be due to a different process (that is, domain union ...)" (Ch. 11, Section 5.2.1, p. 464); Udi and Pashto endoclitics (Ch. 4, Section 2.2, pp. 132-134); Welsh superficial agreement (Ch. 6, Section 7.2, pp. 238-239).
- Domains survive in analyses of ellipsis and coordination (Ch. 10, pp. 390-391; Ch. 19, Section 6.3, pp. 876-877), French subject inversion, and a few English constructions (Ch. 14, p. 636; Ch. 16, pp. 736-737).
- In implementation: Babel makes extensive use of discontinuous constituents (Ch. 25, Section 3.3.3, pp. 1119-1120); Müller (2004) preferred linearization for computational reasons and later gave it up for theoretical ones (Ch. 14, fn. 54).
- Hudson calls the claim that there are no discontinuous phrases "clearly false" (Ch. 31, Section 1, p. 1449).

## Competing analyses

- Order domains: Reape 1994; Kathol 1995, 2000; Kathol and Pollard 1995; Donohue and Sag 1999.
- Continuous constituents with argument attraction and head movement: Hinrichs and Nakazawa 1994; Müller 2005, 2021 (Ch. 10, Section 8, pp. 403-404).
- Continuous constituents with non-cancellation of arguments: Bender 2008 on Wambaya (Ch. 10, Section 7, pp. 402-403; Ch. 30, pp. 1423-1424). Both this and domains add a level beyond the tree: a DOM list, or a persistent valence list that acts like an LFG f-structure (Ch. 30, p. 1424).
- Whether phenogrammar and tectogrammar can be cleanly separated at all is disputed (Kubota 2014; Ch. 29, Section 3.3.1, pp. 1356-1357).
- Continuous binary right-branching structures whose runs of same-category nodes are typed as lists, with order stated as list sorts (topological fields as types): Oliva 1992 (COLING, pp. 184-190). Local and continuous, but it orders only within one head's level, so it does not address discontinuity, and it keeps an empty end-of-level element (notes in `reading/notes/oliva-1992-word-order-binary-lists.md`).

## Consequence for our parser and grammars

A tag sequence that decodes to a continuous tree cannot represent a domain analysis, and under shuffle the tree does not fix the string. The design is safe for grammars with a context-free backbone (Ch. 25, pp. 1108-1109) and for English. The Korean control-verb case is the Handbook's clearest claim that some data still need domains.

## Proposal and test

Proposal: commit to continuous derivations and treat discontinuity through valence (attraction, non-cancellation) and nonlocal features. Record every construction for which the literature offers only a domain analysis.

Test: non-projectivity in UD treebanks is a proxy. For each target language, measure the share of non-projective arcs that our continuous grammar (or a Grammar Matrix grammar) can derive by extraction, extraposition, attraction, or non-cancellation. Prediction: the residue is small for English and German and concentrated in a few construction types; a large residue for a language such as Korean or Warlpiri would count against the proposal.

## Status

open.
