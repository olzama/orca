# Bouma, Malouf and Sag (2001): Satisfying constraints on extraction and adjunction

*Natural Language and Linguistic Theory* 19: 1–65. Read from `Bouma-Malouf-Sag-SatisfyingConstraintsOnExtract.pdf` (the published version, 66 pages). `SatisfyingConstraintsOnExtractionAndAdjunction.pdf` (62 pages) is a preprint with the same abstract and different page layout; it was not compared line by line. Page numbers below are those of the published version. Read 2026-11-20.

Question for this reading: is traceless extraction deterministic under replay, and what do DEPS and SLASH amalgamation require of the engine?

## Summary

The paper gives one account of complement, adjunct, and subject extraction with no traces and no lexical rules. Three lists are distinguished on words: ARG-ST (selected arguments, where binding applies), DEPS (ARG-ST plus an open list of adverbials), and the valence lists SUBJ and COMPS (Section 2, pp. 6–12). Two constraints on words relate them. Argument Structure Extension lets a verb's DEPS be its ARG-ST followed by any number of adverbials ((10), p. 12; revised as (65), p. 42). Argument Realization says that DEPS is SUBJ followed by COMPS, except that elements of type *gap-ss* may be missing from COMPS ((11), p. 12; (27), p. 23). A gap is therefore a dependent that is never put on a valence list; nothing is removed by rule. SLASH is collected lexically: a word's SLASH is the union of the SLASH values of its dependents minus what it binds ((20), p. 20), and a phrase takes its SLASH from its head daughter only ((22), p. 20). Post-verbal adjuncts are complements of the verb; pre-verbal adverbs remain modifiers in modifier-head structures (Section 4, pp. 38–44). Subject extraction is the case where the first dependent is a gap, and matrix *Who left?* is a head-filler phrase (Section 6, pp. 51–57).

## Caveats for the parser

### 1. Under this analysis no node in the tree records the gap (high; deterministic replay)

Extraction is located "on the interface between the lexicon and the syntax" (p. 23). There is no unary rule and no lexical rule at the extraction site: the verb *hates* with an extracted object is the same lexical entry as the verb with a realized object, satisfying Argument Realization in a different way ((29)–(30), p. 24). The paper states the consequence directly: a lexical description is "satisfied by many distinct feature structures" (p. 14), and with Argument Structure Extension a single entry is satisfied by an infinite number of feature structures differing in the number of elements on DEPS (p. 15). A derivation tree whose nodes are rule names therefore does not say which dependent is the gap, or how many adverbials a verb has taken as dependents. Replay has to recover both by constraint solving.

### 2. Adjunct extraction leaves the attachment site unmarked (high; deterministic replay, semantics)

An extracted adverbial is a *gap-ss* on the DEPS list of the verb it modifies ((76)–(77), pp. 46–47). In *On Tuesday, I think it's likely that Sandy visits Leslie* (72b, p. 45) the tree has a head-filler node at the top and ordinary nodes below. Nothing in the tree distinguishes the reading in which the adverbial is a dependent of *visits* from one in which it is a dependent of a higher verb. The two readings have different semantics. The paper does not discuss this as ambiguity of a derivation, because it has no notion of derivation; the consequence for replay is my inference from (65), (76) and (77).

### 3. The engine would need more than unification (high; deterministic replay)

The constraints use list append, list subtraction (said in footnote 6, p. 10, to be interdefinable with Reape's domain union), set union for SLASH, and disjoint set union in the head-filler constraint ((23), p. 21, fn. 11). Argument Structure Extension leaves a list of unbounded length underspecified. The paper notes that the resulting infinity is like that of recursive lexical rules and that evaluation "can be delayed to a point where only a finite number of solutions remain (typically, after some syntactic processing has taken place)" (p. 16, citing van Noord and Bouma 1994). An engine for this analysis as written needs relational constraints with delayed evaluation.

### 4. Post-verbal adjuncts as complements change tree shape (medium; rule inventory, UD bridge)

*finds a solution today* is one head-complement phrase with the adverb as a complement daughter ((67), p. 43). Pre-verbal adverbs are modifiers in a binary modifier-head structure ((59), p. 39). The head-complement structure is flat, with all complements as sisters. A grammar that follows the paper has two structurally different treatments of adverbials depending on position, and the adjunct or argument status of a post-verbal dependent is not visible in the rule name; it is visible only in whether the dependent is on ARG-ST (p. 44).

### 5. Matrix subject questions are head-filler phrases (low; label inventory)

*Who left?* is analyzed as extraction, with a gap subject and a head-filler phrase, and no longer as a head-subject phrase (p. 54, following Ginzburg and Sag). Embedded *think visits Alcatraz* has a VP-like complement with an unrealized gap subject ((94), p. 55). Labels for the same string differ between grammars that follow this analysis and grammars that keep the subject–VP analysis.

### 6. SLASH can be bound from below (low; UD bridge)

In *an easy man to please* and in French *en*-cliticization the binder of the dependency is lower in the tree than the phrase containing the gap (Sections 3.3–3.4, pp. 29–35). Conversions that recover long-distance dependencies by looking for a filler above the gap would miss these.

## Support for the design

- **No empty leaves.** Gaps "play no independent role in the phrase structure, linear order, or phonology of phrasal signs" (p. 23). Every leaf is a word.
- **Extraction information is local to the head word.** A word's SLASH is computed from its own dependents ((20), p. 20). The cross-linguistic evidence in Sections 1 and 3.2 (Irish complementizer particles, Chamorro verb morphology, pp. 4–5, 26–29) is that languages mark extraction on the words along the path. A per-token label is the natural place for this information.
- **Processing evidence favors association at the head.** The filler is associated with its role when the selecting head is encountered, not at a later trace position (Section 3.5.3, pp. 37–38).
- **Semantics is compositional by append.** The paper adopts Minimal Recursion Semantics: the RELS of a headed phrase is the append of the daughters' RELS, and KEY comes from the head ((18), p. 18).
- **Uniformity.** One mechanism covers complement, adjunct, and subject extraction, so a design that marks extraction once (however it is marked) covers all three.

## Theory strains

- **Lexical rules versus constraints for extraction.** The Complement Extraction Lexical Rule is called "awkward" because lexical rules are meant for morphological processes with lexical exceptions, and complement extraction has none (p. 22); its formal status "has itself been the matter of some debate" (p. 23). The paper replaces three unrelated lexical rules of Pollard and Sag 1994 with one constraint (pp. 2–4, 60–61).
- **Adjuncts as dependents versus adjuncts as modifiers.** Evidence from scope in Dutch and Japanese complex predicates, case in Finnish, and extraction marking in Chamorro is given for selection of adverbials by the verb (pp. 39–41, 50–51). The authors keep the modifier analysis for pre-verbal adverbs (p. 43).
- **Configurational versus head-driven SLASH passing.** The Nonlocal Feature Principle is replaced by lexical amalgamation, motivated by lexical binders such as *easy* and by subbinding (pp. 19–20, 29–35).
- **Islands.** The paper suggests that many island effects may be due to processing (fn. 27, p. 49) and that weak-island behavior of adverbials can be stated as a restriction on SLASH values (p. 49).
- **Subject Condition.** The acceptability of the data it is meant to exclude is described as unclear (p. 59).

## Key primary sources

- Pollard and Sag 1994, Chapters 4 and 9 (the analyses being replaced).
- Sag 1997, English relative clause constructions (traceless analysis with a lexical rule; *gap-ss*).
- Sag and Fodor 1994, Extraction without traces.
- van Noord and Bouma 1994, Adjuncts and the processing of lexical rules (delayed evaluation).
- Manning and Sag 1998; Manning, Sag and Iida 1999 (ARG-ST versus valence).
- Hukari and Levine 1995, 1996 (uniform registration of extraction; critique of Pollard and Sag 1994).
- Ginzburg and Sag (2000), Interrogative investigations.
- Miller and Sag 1997 (French clitics).
- Przepiórkowski 1999 (adjuncts as complements; case).

## Not covered here

These are my remarks, not statements from the paper.

- **The ERG does not implement this analysis as written.** In the Redwoods training derivations, extraction is marked by named unary rules: `hd_xcmp_c` (11,065 occurrences), `hd_xsb-fin_c` (9,388), and `hd_xaj-int-vp_c` (14,668), with `flr-hd_*` rules at the top of the dependency (counts from `analysis/derivation-stats/train-phrasal_rule.tsv`). The rule names suggest extracted complement, extracted subject, and extracted adjunct. If each of these fixes the affected dependent, caveats 1 to 3 do not apply to the ERG, and the adjunct attachment site of caveat 2 is recorded by where the unary rule sits in the tree. Verified 2026-11-20 for complements: `extracted_comp_phrase` (ERG `syntax.tdl`) is a unary phrase whose head daughter has a gap as the first element of COMPS and passes the rest up, so the rule always removes the first remaining complement, and its position among the head-complement steps says which one. The subject and adjunct extraction rules have not been read.
- **Design consequence.** For our own grammars the paper is an argument for what the information is (extraction is a property of the head word's dependents) and the ERG is the model for how to record it (a named unary step in that word's label chain). This is the "one decision, one name" policy of theory log entry 0001.
- The paper does not address computational complexity beyond the remark on delayed evaluation, and says nothing about implementations other than acknowledging the LinGO project.
