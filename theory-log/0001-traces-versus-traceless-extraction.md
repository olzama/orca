# 0001: Traces versus traceless extraction

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

HPSG has never settled whether the bottom of an unbounded dependency is an empty category. Pollard and Sag (1994) contains both analyses: traces in Chapter 4 and three extraction lexical rules without traces in Chapter 9 (Ch. 2, Sections 5-6, pp. 59-61). The Handbook chapter on unbounded dependencies lists the question as unresolved (Ch. 13, Section 10, p. 582), and the introductory chapter notes "some debate" (Ch. 1, Section 2, p. 6). Each side pays a price. Traces force a stipulation that conjuncts cannot be empty (Ch. 15, Section 3, p. 668). Traceless extraction forces case, agreement, and linking constraints to hold of lexemes instead of words (Ch. 13, Section 3, pp. 546-547), and the Pollard and Yoo scope theory, which repairs narrow scope for extracted quantifiers, covers trace-based extraction only (Ch. 22, Section 3.1, pp. 1007-1009).

## Evidence

- For tracelessness: a gap cannot be a conjunct; Hausa and Mauritian verb morphology treats extraction like valence reduction (Ch. 13, pp. 545-546); the Conjunct Constraint follows with no stipulation (Ch. 15, p. 668).
- For traces: Archi agreement needs constituent-structure constraints (Borsley 2016; Ch. 13, fn. 10, pp. 546-547); linear position in weak crossover, called controversial (Ch. 30, Section 9, p. 1418); adjunct and subject gaps are handled uniformly (Levine and Hukari 2006; Ch. 13, pp. 547-549).
- Binding is indifferent: ARG-ST is the same under both analyses (Ch. 20, Section 2.2, pp. 901-903).
- Information-structure features were moved out of LOCAL to stay neutral between the two (Ch. 23, Section 2, p. 1047).

## Competing analyses

- Traces: Pollard and Sag 1994 (complement position); Levine and Hukari 2006 (all gaps); Borsley 2009, 2013; Müller 2004 (Ch. 13, pp. 543-549; Ch. 4, p. 165, fn. 12, which also cites CoreGram among trace-based approaches).
- Traceless, lexical rule: Complement Extraction Lexical Rule (Pollard and Sag 1994, Ch. 9; Ch. 4, Section 5.2, p. 158).
- Traceless, underspecified argument realization: Sag 1997; Bouma, Malouf and Sag 2001; Ginzburg and Sag 2000; Sag 2010. "Probably the most widely assumed position" (Ch. 13, p. 544).
- A third option, gaps on valence lists and absent from the tree, "has rarely been considered" (Ch. 13, p. 540).
- Müller argues for a weak ban on empty elements: allowed when there is language-internal evidence (Ch. 32, Section 1.2.1, pp. 1503-1504).

## Consequence for our parser and grammars

A trace is a leaf with no token, which a one-label-per-token encoding cannot carry directly. The underspecification variant has the opposite problem: no rule node records which argument is the gap, so the derivation tree is not a complete recipe (SYNTHESIS, DR-1). The lexical-rule variant is the one that fits: a named unary step in the label chain. No Handbook chapter says which variant the ERG uses.

## Proposal and test

Proposal: in our grammars every gap is introduced by a named unary rule that identifies the affected argument. Treat trace-based source grammars by compiling each trace into such a rule (Ch. 32, pp. 1503-1504, reports that grammars with empty elements can be translated into grammars without).

Test: (1) in the ERG, confirm that each extraction in Redwoods derivations is marked by a rule name, and that replay from rule names alone reproduces the stored SLASH values. Prediction: zero derivations in which two different gap choices replay under the same rule names. (2) Check whether the lexeme-level consequences claimed for traceless grammars (Ch. 13, pp. 546-547) show up as ERG design decisions.

## Status

open. Not yet checked against the ERG.

## Update 2026-11-20

Bouma, Malouf and Sag (2001) is the underspecification variant in full (notes: `reading/notes/bouma-malouf-sag-2001-extraction-adjunction.md`). It confirms that under that variant no node records the gap, that a lexical entry is satisfied by many feature structures (pp. 14-15), and that the constraints need list and set relations with delayed evaluation (p. 16). It adds a case the Handbook notes did not single out: for an extracted adjunct the tree does not record which verb the adjunct depends on (pp. 46-47).

First part of the test: the ERG treebank marks extraction with named unary rules (`hd_xcmp_c`, `hd_xsb-fin_c`, `hd_xaj-int-vp_c`; counts in `analysis/derivation-stats/`). So the ERG follows the named-step variant, as the proposal requires. Still to check in the rule definitions: whether `hd_xcmp_c` identifies the complement when there are several.

Pollard and Sag 1994, Chapter 9 (notes: `reading/notes/pollard-sag-1994-ch9-reflections-and-revisions.md`) is the source of the lexical-rule variant. Two properties of it weaken the "named step" reading: the complement extraction rule removes any one complement under a single rule (p. 378), and subject and adjunct extraction are registered on the embedding verb, not on the word whose dependent is missing (pp. 382-387). The proposal above therefore needs the stronger wording: the named step must sit on the word or phrase that loses the dependent, and must identify which dependent.

## Update 2026-11-22

Pollard and Sag 1994, Chapters 4 and 5 (notes: `reading/notes/pollard-sag-1994-ch4-unbounded-dependencies.md`, `...-ch5-relative-clauses.md`) are the traced baseline. They add three inputs. (1) The Trace Principle is parametrized: universally a trace must be subcategorized by a substantive head, and English adds strict subcategorization (non-subject), which gives *that*-trace effects; Icelandic and Norwegian lack them (Section 4.4). So the subject/non-subject asymmetry belongs in grammar-particular rules, which matches the ERG's separate `hd_xsb-fin_c` and `hd_xcmp_c`. (2) Adverbial extraction from embedded clauses can't be reduced to matrix "annotation" (*When their parents are in town next week, I doubt that the twins will attend*), and the 1994 trace analysis has no place for it; this is what Chapter 9 revises (Section 4.4, end). (3) The 1994 theory also needs null relativizers for relative clauses (Ch. 5); the ERG replaces both traces and null relativizers with unary rules, so the move away from empty elements is general, not specific to extraction.

Hausa (Crysmann 2010; `reading/notes/crysmann-2010-hausa-resumption-islands.md`): null and overt resumptive pronouns introduce SLASH via lexical rules on the pronoun or on the verb (valence reduction), with island sensitivity checked at filler-head nodes. This supports the "named step on the word that loses the dependent" wording above: in HaG, the step is a lexical rule on the head whose argument is resumed or dropped.
