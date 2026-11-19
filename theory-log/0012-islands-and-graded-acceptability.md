# 0012: Islands and graded acceptability: what belongs in a categorical grammar

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

HPSG grammars are categorical: an object is well-formed iff it satisfies all constraints, and no constraint is violable (Ch. 1, Section 2, p. 5, fn. 3). Yet for extraction the chapters show that nearly every proposed island constraint has robust counterexamples, that acceptability is graded, and that the remaining filtering is "at least in part probabilistic" (Ch. 15, Sections 3-12; Section 8.2, p. 690). HPSG "remains relatively agnostic about many island types", and "it is unclear how to combine probabilistic information with syntactic, semantic and pragmatic representations" (Ch. 15, Section 14, pp. 700-701). Neither defaults nor probabilities are part of the formal foundations (Ch. 17, fn. 23). The theory therefore has no principled place for the boundary between "ungrammatical" and "dispreferred", and the boundary may differ by language.

## Evidence

- Accepted counterexamples to the Coordinate Structure Constraint (element part), the Complex NP Constraint, Subjacency, the Right Roof Constraint, subject and adjunct islands (Ch. 15, pp. 669-693).
- Only the Conjunct Constraint, the Left Branch Condition, part of Superiority, and tentatively the Complementizer Constraint get grammatical accounts, and the last is called ad hoc (Ch. 15, pp. 668, 693-699).
- The processing explanation is itself disputed (Sprouse et al. 2012 versus Hofmeister and Sag; Ch. 15, Section 4.2, p. 676).
- A preference that is statistical in English is categorical in Lummi (Ch. 24, Section 1, pp. 1082-1084). Sag insisted that grammatical generalizations be categorical (Ch. 24, fn. 4).
- Graded agreement judgments ("??", "?*") inside a hard-unification account (Ch. 6, pp. 220-221, 224-226).
- Violable, weighted ordering constraints for the German Mittelfeld lie outside the standard formalism (Ch. 10, Section 2, pp. 373-374).
- Hand-written rule weights in implemented grammars were brittle; statistical ranking over treebanks replaced them (Ch. 25, fn. 11, pp. 1110-1111).
- Mal-rules license known errors inside the grammar (Ch. 25, Section 4.2.1, pp. 1124-1125).

## Competing analyses

- Islands in the grammar as SLASH or EXTRA constraints: Pollard and Sag 1994; Phillips 2013; Sprouse et al. 2012.
- Islands outside the grammar: Hofmeister and Sag 2010; Sag 2010; Chaves 2012; Chaves and Putnam 2020.
- Hybrid, with language-specific grammaticalization: Wasow (Ch. 24, Section 4.1, pp. 1092-1094).
- Weighted or violable constraints over feature structures: Sorace and Keller 2005; Pullum and Scholz 2001 (Ch. 28, Section 3.1, pp. 1263-1264).
- Probabilities on types or Data-Oriented Parsing with HPSG: Bender 2001; Neumann and Flickinger 2002; Miyao and Tsujii 2008 (Ch. 15, p. 701; Ch. 17, p. 790; Ch. 24, p. 1083).

## Consequence for our parser and grammars

If the grammar hard-codes islands, good sentences fail replay; if it does not, replay succeeds on island violations and "strict" means grammar-licensed, with acceptability left to the tagger. Our tagger-plus-replay split is the second of the two options stated in Ch. 24, and the strict/relaxed boundary is where the theory's unresolved question becomes an engineering parameter.

## Proposal and test

Proposal: keep grammars permissive about extraction, as Ch. 15 argues, and report two separate quantities for every analysis: licensed (replay succeeds) and tagger confidence. In the relaxed path, record which unification failed, so that each relaxed analysis names the violated constraint.

Test: (1) find which SLASH and EXTRA constraints the ERG imposes and count Redwoods-external attested sentences that fail replay only because of them. (2) Check whether tagger confidence on licensed island-violating test items (from the Ch. 15 examples) is lower than on matched controls. Prediction: confidence separates the two sets without any grammatical island constraint; if it does not, the probabilistic account in Ch. 15 loses support.

## Status

open.
