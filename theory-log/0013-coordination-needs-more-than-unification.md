# 0013: Coordination in the theory needs a relation that unification does not provide

Source: reading notes on Sag (2003), "Coordination and Underspecification" (`reading/notes/sag-coordination-and-underspecification.md`), and on Drellishak and Bender (2005), "A Coordination Module for a Crosslinguistic Grammar Resource" (`reading/notes/drellishak-bender-coordination-module.md`). Page numbers are those of the papers. The proposal is ours.

## Strain

Unification computes the most general common subtype of two descriptions. Sag's coordination rule states the opposite relation: the category of the mother must be a supertype of the category of each conjunct, and lexical entries place upper bounds on feature values (Sag 2003, pp. 274-277). A grammar that follows this analysis cannot be checked by a unifier alone. Implemented grammars state coordination with binary rules and ordinary unification, and they leave the category of the mother partly stipulated per phrase type (Drellishak and Bender 2005, pp. 114, 117-118).

## Evidence

- Coordination of unlikes: *wealthy and a Republican* has a head value that is a supertype of noun and adjective; *grew and remained* requires an adjective because valence is identified (Sag 2003, pp. 274-276).
- Syncretism: a form that satisfies an accusative and a dative requirement at once gets a type below both; this covers case in German and Polish and verb forms in English (Sag 2003, pp. 278-279, 284-287).
- The analysis uses upper bounds, values fixed at non-maximal types, one negated bound, and a root condition that compares feature structures (Sag 2003, pp. 278, 280-281).
- Spurious ambiguity is admitted: *findet Frauen* has four case values, and neither proposed remedy is adopted (Sag 2003, pp. 279-280).
- Right-node raising is left unanalyzed (Sag 2003, p. 283).
- The theory's rules are flat; the implemented ones are binary, with nodes that are not constituents and, where there is no conjunction word, unary nodes with no surface evidence (Sag 2003, pp. 275-281; Drellishak and Bender 2005, pp. 115-119, 125-126).
- The implemented analysis licenses two groupings for the same string under most strategies, which its authors flag as possibly wrong (Drellishak and Bender 2005, p. 126).

## Competing analyses

- Feature intersection (Sag, Gazdar, Wasow and Weisler 1985), refuted by Jacobson's example (Sag 2003, p. 269).
- Fully resolved types with large hierarchies of combined values (Levy 2001; Levy and Pollard 2001; Daniels 2001), rejected on the size of the hierarchy (Sag 2003, pp. 270-272).
- Underspecified, non-resolved feature structures with subsumption constraints (Sag 2003).
- Binary rule chains with stipulated mother categories (the ERG; Drellishak and Bender 2005).

## Consequence for our parser and grammars

Replay stays within unification only if coordination is stated the way implemented grammars state it. Each kind of unlike coordination then needs its own supertype or its own rule (Sag 2003, fn. 9, p. 276), and the tagger has to choose among many coordination rules; these are among the rules it confuses most. Exact-match scoring is unfair where the grammar licenses several derivations with one meaning.

## Proposal and test

Keep unification as the only operation of the engine. In our grammar core, define a coordination node label as a tuple (role in the chain, marking pattern, phrase type) and derive rule names from it. Test 1: count how many coordination rules of the ERG exist only to cover unlike or syncretic conjuncts, and how often each occurs in the treebank. Test 2: check whether collapsing equivalent coordination derivations (same MRS) changes tagger scores.

## Status

Open. Recorded 2026-11-20.
