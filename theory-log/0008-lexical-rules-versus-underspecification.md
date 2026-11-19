# 0008: Argument realization: lexical rule, underspecification, or type construction

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

The same alternation (extraction, clitic realization, argument drop, passive) can be a lexical rule, the resolution of an underspecified lexical entry, or an inferred type combination, and the theory offers "no general guideline": "the issue cannot be settled a priori and must be argued on a case by case basis" (Ch. 4, Section 5.3, p. 165; Section 6, p. 166). The formal status of lexical rules themselves "has proven surprisingly difficult" to fix (Ch. 4, Section 5.1, pp. 155-158), and phrase structure rules, lexical rules, and defaults are meta-notation outside the feature logic whose re-interpretation is "sometimes trivial and sometimes nearly impossible" (Ch. 3, Section 1, pp. 89-90). The Argument Realization Principle that connects ARG-ST to valence is admitted to be an idealization whose form the introductory chapter declines to fix (Ch. 1, Section 4.1, p. 17; Ch. 9, Section 2, pp. 318-319).

## Evidence

- The Complement Extraction Lexical Rule applies to any COMPS member; Monachesi's clitic rule uses shuffle (Ch. 4, Section 5.2, pp. 158-159). One rule name, several outputs.
- Meurers's (2001) formalization "does not always work as intended" (Lahm 2016; Ch. 4, p. 156).
- Lexical rules have a direction; causative/inchoative alternations may not (Ch. 4, p. 159; Ch. 9, Section 5.2, p. 344).
- Online type construction derives passive without a rule; Müller, and Müller and Wechsler, are "highly sceptical", since rules feed each other and Turkish causatives apply more than once (Ch. 21, Section 2.3, pp. 952-954, fn. 3).
- Valence was SUBCAT, then SUBJ/SPR/COMPS, then ARG-ST was reintroduced for binding, and the ARG-ST/valence relation "was soon loosened" (Ch. 9, Section 2, pp. 317-319; Ch. 1, p. 17, fn. 23).
- In implemented grammars lexical rules are unary-branching rules: ERG, CoreGram, Grammix (Ch. 4, p. 156); LKB (Ch. 21, pp. 958-959).

## Competing analyses

- Lexical rules as unary structures with the input as daughter: Briscoe and Copestake 1999; Meurers 2001; Riehemann 1998.
- Underspecified argument realization with canonical and non-canonical synsem types: Bouma, Malouf and Sag 2001; Miller and Sag 1997; Ginzburg and Sag 2000.
- Online type construction: Koenig and Jurafsky 1995; Koenig 1999.
- Phrasal argument structure constructions: Goldberg 1995; rejected in Müller and Wechsler 2014 (Ch. 32, Section 2, pp. 1521-1527).
- Information-based Morphology for inflection: a set of realization rules, no chain (Crysmann and Bonami 2016; Ch. 21, Section 4.1, pp. 965-969).

## Consequence for our parser and grammars

Only the unary-rule formulation gives a node in the derivation tree, which the label's rule chain depends on. Under the other formulations the tree is not a complete recipe, and label inventories are not comparable across grammars (Ch. 4 reader). The theory's indifference here is our main reason to state a rule of our own.

## Proposal and test

Proposal: a design principle for our grammars, "one decision, one name": every choice that changes valence, SLASH, or the semantics is a named unary rule that is functional (one input, one output). Relational rules are split into one rule per affected position.

Test: replay determinism on Redwoods. For each derivation, replay from rule names and lexical entry identifiers and compare the result with the stored analysis. Prediction: identity in all cases for the ERG; each mismatch identifies a place where the grammar itself relies on underspecified realization. For label sparsity, measure how many distinct chains the split rules add.

## Status

open.
