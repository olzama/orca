# 0006: Ellipsis and fragments: content that the derivation does not supply

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

For fragments, sluices, gapping, and VP ellipsis, HPSG's direct-interpretation analyses keep the syntax surface-true and move the missing content into contextual features (MAX-QUD, SAL-UTT) or leave it as an unresolved pro argument. The grammar then licenses a sign whose semantics is not composed from its daughters, which strains the framework's own claim that syntax and semantics are built in tandem. The authors concede "there is evidence to support both" silent structure and direct interpretation, and that HPSG has no uniform account of ellipsis (Ch. 19, Introduction, p. 848; Section 3, pp. 851-860).

## Evidence

- The Head-Fragment Schema (31) is a unary rule whose content comes from the dialogue context; all existing HPSG analyses of fragments are based on it (Ch. 19, Section 4, pp. 860-864). It wrongly rules out attested case mismatch in Hungarian, and its [IC +] stipulation fails for speakers who accept "Lee says eggs" (Ch. 19, p. 861, fn. 15; p. 868 and fn. 22).
- Sluicing: a unary construction "that taps into contextual information"; the antecedent need not be overt (Ch. 15, Section 13, p. 700).
- VP ellipsis: a pro VP on the auxiliary's ARG-ST; resolution "is not based on syntactic reconstruction" (Ch. 19, Section 5, pp. 868-870; Ch. 12, Section 4.2, pp. 525-526; Ch. 18, Section 2.3, pp. 819-822). Its island behavior is "at best inconsistent" (Ch. 19, Section 3.2, pp. 855-857).
- Gapping: the gapped conjunct is a fragment over a cluster of remnants, and its meaning comes from the first conjunct (Ch. 16, Section 7, pp. 763-764; Ch. 19, Section 6.1, pp. 870-873). Modals and negation in the first conjunct can scope over the coordination; the one HPSG account is stated in Lexical Resource Semantics, with determiner gapping left open (Ch. 29, Section 4.2.2, pp. 1364-1366).
- Case matching between fragment and antecedent is cross-linguistically robust and favors silent structure (Ch. 19, Section 3.1, pp. 851-853).
- Clarification requests need the content of sub-constituents, which neither unification nor constraint accumulation keeps (Ch. 26, Section 3.1, pp. 1167-1169).

## Competing analyses

- PF deletion with movement of the remnant: Merchant 2001, 2005.
- Direct interpretation: Ginzburg and Sag 2000; Culicover and Jackendoff 2005; Abeillé, Bîlbîie and Mouret 2014; Park 2019.
- Deletion-like gapping within HPSG: Chaves (2006 in Ch. 16; 2009 in Ch. 19 and Ch. 29; the notes disagree on the year).
- Dialogue-level frameworks that embed the grammar in an update semantics: Ginzburg 2012 (Ch. 26, Section 2.4, pp. 1164-1166).

## Consequence for our parser and grammars

The trees fit the design: unary rule, no empty leaf. The MRS obtained by replaying one sentence is incomplete for these constructions, and the same tree gets different contents in different contexts. "Semantics as a by-product" needs the qualifier "up to context-dependent resolution". Gapping inside one sentence is the hard case, because the context is the first conjunct and a sentence-level parser could resolve it.

## Proposal and test

Proposal: strict output for an elliptical construction contains an explicit unresolved predication with pointers to the remnants; a separate, optional resolution step fills it. For sentence-internal gapping, resolution copies the predicate of the first conjunct and aligns remnants with correlates by category and role, not by position (Ch. 19, examples (50)-(54)).

Test: on gapping sentences from Redwoods or UD (orphan relation), compare the MRS after resolution with a gold MRS of the paraphrase with the verb repeated. Prediction: alignment by category and role succeeds on most cases; failures cluster in the scope-anomaly type of Ch. 29.

## Status

open.
