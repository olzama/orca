# 0004: Flat versus binary branching

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

HPSG has no theory of branching. Work on English and French "usually assume[s] a flat structure" and work on German assumes binary branching (Ch. 10, Section 3, pp. 375-380). Borsley and Müller, writing together, declare both "viable" and give no criterion (Ch. 28, Section 4.2.1, pp. 1284-1288). The formalism allows a schema to leave the number of daughters unspecified (Ch. 3, Section 3, p. 100). Since binding and grammatical relations are read from ARG-ST and not from the tree (Ch. 20, Section 2.1, p. 900), little inside the theory can decide the question, and tree shape becomes a free parameter of each grammar.

## Evidence

- Flat: the ternary VP and inverted clause of Pollard and Sag (1994: 36-40) (Ch. 1, Section 5.1, pp. 22-23; Ch. 28, p. 1286); auxiliary-initial clauses as one ternary local tree (Sag et al. 2020; Ch. 10, pp. 386-387); Head-All-Valents for VSO languages, where morphology that belongs to the next constituent is easier to state among sisters (Ch. 5, Section 4.2, pp. 197-200); the Italian flat VP, argued for empirically against the Spanish verb cluster (Ch. 11, Sections 4.2-4.3, pp. 436-444); coordination with any number of daughters (Ch. 16, Section 3, pp. 729-732).
- Binary: free adjunct placement and unbounded adjunct recursion come for free; flat structures need relational constraints over daughter lists, adjuncts as valents, or an infinite lexicon (Ch. 10, pp. 377-379). The binary Head-Valent analysis of VSO makes verb and subject a constituent (Ch. 5, Section 4.3, pp. 200-202).
- The binary analysis of coordination needs two rules and a special feature against coordinator recursion (Ch. 16, pp. 729-731).
- Open questions listed for VSO: why flat structures are licensed there and not elsewhere, and why binary combination goes from least to most oblique (Ch. 5, p. 202).

## Competing analyses

- Flat head-complement structures: Pollard and Sag 1994; Sag 1997; Ginzburg and Sag 2000; Abeillé and Godard 2000.
- Binary with a parameterized Head-Complement Schema: Müller 2015, 2021 (Ch. 10, schema (19), p. 379).
- Head of a head-complement phrase as a word versus a LEX+ or LIGHT phrase (Ch. 1, fn. 29-30; Ch. 11, Section 4.3, p. 442).
- Minimalism: binary only, which the chapter calls dubious (Ch. 28, p. 1271).

## Consequence for our parser and grammars

The tree encoding assumes unary and binary rules. That is a property of some grammars, and the Handbook does not state it for DELPH-IN (Ch. 25 gives complexity for a general maximum arity). Flat analyses must be binarized, and where flatness itself carries a contrast (Italian versus Spanish), the binarization must keep it. Attachment order inside a binarized VP is a grammar-internal choice the UD bridge has to undo.

## Proposal and test

Proposal: treat binary branching as an encoding convention with a fixed, documented order of saturation (least oblique complement first for head-initial languages, as in schema (19)), and record the flat-versus-cluster contrast in a feature such as LIGHT, as Ch. 11 does.

Test: (1) confirm the maximum rule arity in the ERG. (2) For a set of constructions analyzed flat in the literature (inversion, ditransitives, coordination of three conjuncts), check that binarized derivations map to the same UD tree and the same MRS under either order of saturation. Prediction: MRS is invariant; where it is not (adverb scope), the theory has a real branching fact to state.

## Status

open.
