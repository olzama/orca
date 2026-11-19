# 0002: Verb placement: empty verbal head, order domains, or flat construction

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

With binary branching only sisters can be ordered, so a clause-initial finite verb cannot be placed by local reordering. The majority analysis for German keeps constituents continuous and pays with an empty element: a unary rule on the verb, a head feature DSL passed down the head path, and an empty verbal head with PHON < > (Ch. 10, Section 5.1, pp. 384-386). The same chapter argues against empty-free alternatives, and the framework that criticizes Minimalist empty heads reports that this one is "standard among HPSG grammarians of German" and, given multiple fronting, "unavoidable" (Ch. 28, Section 4.2.1, p. 1288). HPSG has "a minimum" of empty elements with no stated principle for when one is justified (Ch. 28, Section 4.1, p. 1273).

## Evidence

- German apparent multiple fronting: several constituents before the finite verb if they depend on the same verb. Müller analyzes the fronted material as a VP headed by an empty verb; sketch (49) has three empty positions in one clause (Ch. 10, Section 6.4.2, pp. 398-401). He concedes that the earlier empty head "comes as a stipulation" and judges the relational alternative "less principled than positing an empty element".
- Clause-type meanings: German verb-first and verb-second clauses have seven uses; three verb-first examples differ only in intonation (Ch. 10, Section 5.3, pp. 388-390).
- Müller reports assuming order domains for ten years before switching (Ch. 10, fn. 11).
- For verb-initial languages proper (Welsh, Tongan), surface-oriented flat analyses are preferred and the trace analysis has not been seriously applied (Ch. 5, Section 4.1, pp. 196-197).

## Competing analyses

- Head movement with an empty element and DSL: Borsley 1989; Kiss 1995; Meurers 2000; Müller 2005, 2021; Bouma and van Noord 1998 for Dutch (Ch. 10, pp. 383-386).
- Linearization in flat structures or order domains: Reape 1994; Kathol 2001; Müller 1995, 2003; Wetta 2011 (Ch. 10, Section 6, pp. 390-401). Kathol's and Wetta's surface-based clause types are called "doomed to failure" given multiple fronting.
- A flat auxiliary-initial construction: Sag et al. 2020; Fillmore 1999 (Ch. 10, Section 5.2, pp. 386-387; Ch. 12, Section 4.1, p. 524; Ch. 30, Section 5, p. 1407).
- An auxiliary entry with two complements and no subject: Sag, Wasow and Bender 2003 (Ch. 12, fn. 25).
- Empty heads, unary projections, and lexical rules can do the same work (Ch. 28, fn. 27, p. 1284).

## Consequence for our parser and grammars

For German-type grammars the design gets continuity or tracelessness, not both, from the published analyses. A tokenless verb leaf must be folded into a unary rule or a neighboring label. English is affected only if the ERG's inversion analysis uses head movement, which the Handbook does not say.

## Proposal and test

Proposal: replace the verb trace by a unary rule at the clause-final position of the head path (a "verb-missing" projection), so that DSL passing is unchanged and every leaf is a token. For multiple fronting, a second unary rule heads the fronted VP.

Test: take a sample of German verb-second and multiple-fronting sentences with trace-based analyses, convert them, and check that (1) the converted derivations decode from one label per token, (2) replay yields the same semantics as the trace-based derivation. Prediction: the conversion is one-to-one except where two empty positions are adjacent, as in sketch (49); count those.

## Status

open. Depends on choosing a German grammar to test with.
