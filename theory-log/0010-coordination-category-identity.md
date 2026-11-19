# 0010: Coordination: headedness, category identity, and neutralization

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

Coordination is the main exception to head-driven structure (Ch. 16, Section 2, pp. 726-729), and the standard constraint that coordinands share their whole CAT value is too strong in several directions. The authors conclude that only "some of the features in CAT" should be shared, "despite the fact that one of the prime motivations for CAT was coordination phenomena", and do not say which (Ch. 16, Section 4.1, pp. 741-744). Coordination of unlike categories shows that the mother's features are not the intersection of the daughters'. The type-hierarchy repair for syncretism and unlike cases grows double exponentially with the number of cases and is "widely perceived as very complex and inelegant" (Ch. 7, Section 3, pp. 259-263). There is no consensus on the coordinator's status or on branching (Ch. 16, p. 765).

## Evidence

- CAT identity mispredicts for INV (coordination of inverted and non-inverted clauses), AUX, and SLASH (asymmetric extraction) (Ch. 16, examples (35), (36), (42)).
- "a Republican and proud of it"; "alone and without money" (Ch. 16, Section 6, pp. 753-756; Ch. 28, pp. 1288-1290).
- Syncretic forms satisfy two case requirements at once in coordination, free relatives, and parasitic gaps (Ch. 7, pp. 256-258; Ch. 14, pp. 643-646). With three cases the Daniels hierarchy has 35 types (Ch. 7, Section 3, pp. 259-263).
- When an NP with case is coordinated with a sentence, "it is not clear what categories should be borne by the coordinate structure as a whole" (Ch. 7, p. 263).
- Agreement resolution needs purpose-built structures: a person hierarchy or list-valued features (Ch. 16, Sections 4.2-4.3, pp. 745-750).
- Lexical coordination yields "an apparent paradox", a phrase that behaves as a word (Ch. 16, Section 5, pp. 750-753).
- The Coordinate Structure Constraint, once a flagship result of SLASH identity, "does not receive a unitary account in modern HPSG" (Ch. 15, Section 3, pp. 669-672).

## Competing analyses

- Unlike categories: disjunctive categories (Daniels 2002; Yatabe 2004); type underspecification, giving up sort resolution (Sag 2003); gradient categories (Chaves 2013); left-periphery ellipsis (Beavers and Sag 2004; Chaves 2006), attacked by Levine (2011). The authors find underspecification "more promising".
- Syncretism: enriched hierarchies with pure types (Levine, Hukari and Calcagno 2001; Daniels 2002); lattices outside the hierarchy (Levy and Pollard 2002); Crysmann 2005.
- Structure: binary, flat, or totally flat; coordinator as marker or weak head (Ch. 16, Section 3, pp. 729-736).
- Headed ConjP: Kayne 1994; Johannessen 1998; rejected by Borsley 2005.

## Consequence for our parser and grammars

A grammar that follows full CAT identity fails strict replay on attested sentences. The underspecification route needs a mother that is more general than each daughter, which is a generalization (join) step, not unification; it can be precomputed in the type hierarchy at the cost of hierarchy size. For the UD bridge, coordination has no head daughter, so the head is a convention.

## Proposal and test

Proposal: coordination shares only a declared short list of features (to be determined empirically), and the mother's HEAD value is the precomputed join of the daughters' types, looked up from a table built at grammar compile time.

Test: collect coordinations from Redwoods and UD treebanks, record for each pair of conjunct categories and each CAT feature whether the values agree. Prediction: a small set of features is shared in nearly all attested coordinations; the join table for English HEAD types is small. A large table, or no stable shared set, would favor the ellipsis analyses.

## Status

open.
