# Copestake, Flickinger, Pollard and Sag (2005): Minimal Recursion Semantics: An Introduction

**Identity of the file.** The queue lists this item as the 1999 version. The file is the published journal article: Ann Copestake, Dan Flickinger, Carl Pollard and Ivan A. Sag, "Minimal Recursion Semantics: An Introduction", *Research on Language and Computation* (2005) 3:281–332, © Springer 2006, DOI 10.1007/s11168-006-6327-9 (running head and first page, p. 281). Read from `MRS_intro_1999.pdf` (52 PDF pages; journal pp. 281–332; PDF page = journal page − 280; text pp. 281–326, acknowledgements pp. 326–327, endnotes pp. 327–328, references pp. 329–332). The article says of itself that it "is closely based on a 1999 draft distributed via the authors' web pages" and that later developments are not fully covered (n. 1, p. 327); attribute and type names are those of the ERG "as of July 2003" (n. 17, p. 328). The 1999 draft itself is not in this file. The notes file keeps the slug assigned in the queue. Page numbers below are journal page numbers.

**How it was read.** In full from the text layer `txt/MRS_intro_1999.txt`. The text layer is garbled for every feature structure and tree: examples (30)–(34), (36), (40), (43), (44) and Figures 3–9. It also drops the angle brackets of MRS tuples and the primes in the definitions of §4.1. Examples (31), (33), (34), (36), (40), (43), (44) and Figures 3, 4, 5, 6, 7, 8 and 9 were read from the PDF page images (PDF pp. 22, 26–31, 35–37, 40–43). Figures 1 and 2 (p. 298, dotted-line drawings of qeq relationships) were read from captions and prose only. Read 2026-11-20.

Question for this reading: once every rule and lexical entry of a derivation has been unified, is the MRS fully determined by the feature structure, and what must an engine implement to read it off? Secondary: which well-formedness conditions give a cheap check, and which node of a derivation contributes which part of the semantics.

## Summary

**Motivation (§§1–2, pp. 281–287).** Four criteria for computational semantics: expressive adequacy, grammatical compatibility, computational tractability, underspecifiability (pp. 281–282). Conventional logical forms encode syntactic bracketing that is irrelevant to truth conditions, which hurts transfer and generation; fully flat representations lose scope (pp. 284–286). MRS is described as "a meta-level language for describing semantic structures in some underlying object language", here predicate calculus with generalized quantifiers (pp. 282–283).

**The representation (§3 and §4.1–4.2, pp. 287–299).** The unit is the elementary predication (EP): a label handle, a relation, a list of ordinary variable arguments, and a list of handles for scopal arguments ("holes") (Definition 1, p. 292). EPs with the same label are conjoined (Definition 2, p. 292). An MRS structure is a top handle, a bag of EPs, and a bag of handle constraints, with the condition that no handle outscopes the top (Definition 3, p. 293). A scope-resolved MRS is a tree of EP conjunctions in which the top handle and every hole are identified with an EP label and all constraints hold (Definition 4, p. 293). An MRS is well-formed if it link-subsumes at least one scope-resolved MRS, where linking means adding equalities between handles (Definition 5, pp. 294–295). The one kind of handle constraint used is qeq ("equality modulo quantifiers"): a hole h is qeq to a label l if h = l or a chain of quantifier EPs sits between them, each attached through its body argument (Definition 6, p. 297). EPs are of three classes: non-scopal (cat), fixed scopal (probably), and floating scopal (quantifiers) (p. 299).

**Composition, stated abstractly (§4.3, pp. 299–304).** Each MRS gets a local top (LTOP), "the topmost label in an MRS which is not the label of a floating EP" (p. 299). Lexical items have a key EP; LTOP equals the key's label unless the key is a quantifier or the EP bag is empty, in which case LTOP is unbound (pp. 299–300). Phrases append the daughters' EP bags and handle constraints and share the global top. In intersective combination the daughters' LTOPs are equated with each other and with the mother's. In scopal combination the mother takes the LTOP of the daughter with the scopal EP, and a qeq is added from that EP's hole to the other daughter's LTOP. A root condition adds a qeq from the global top to the root's LTOP (pp. 300–301). A construction may add EPs and qeqs "in exactly the same way as a daughter in a normal rule" (p. 301).

**Feature structure encoding (§5, pp. 304–311).** Type `mrs` with features HOOK, RELS, HCONS; HOOK holds GTOP, LTOP, INDEX; RELS and HCONS are lists; a qeq is a structure of type `qeq` with HARG and LARG (pp. 305–306). An EP is a feature structure whose type is the relation, with LBL and one feature per argument (p. 305). Variable and handle identity is coindexation (p. 305). Figure 4 (p. 308) gives the composition as types: a `phrase` type that identifies the mother's HOOK with DTR1's, equates GTOPs, and appends RELS and HCONS, with subtypes `intersective-phrase` (the two daughters' LTOPs are identical) and `scopal-phrase` (a qeq in DTR1's HCONS has as HARG the ARG1 of a `scopal-reln` whose LBL is DTR1's LTOP, and as LARG the LTOP of DTR2). Scope resolution is done by external modules, outside the grammar (pp. 309–311).

**MRS in the ERG (§6, pp. 311–323).** Indices carry substructure for agreement, tense and mood (pp. 311–312). Verbs introduce event variables, which are not bound by any explicit quantifier (p. 312). Message relations (`prpstn_m_rel`, `int_m_rel`) mark clause type and make GTOP redundant (p. 313). Four general principles of composition are given (pp. 313–314; see caveat 4). Phrases contribute semantics through C-CONT (p. 314, pp. 319–321). The section then covers intersective and scopal modifiers (pp. 314–316), clausal complements, raising and scope, with a comparison to Cooper storage (pp. 315–318), control and XARG (p. 319), and coordination (pp. 322–323).

## Caveats for the parser

### 1. The MRS is determined by unification; two things sit outside it (high; architecture)

The paper presents composition as constraints on types that are satisfied by unification: "since we are now talking about feature structures and unification, we have illustrated how the coindexation propagates through the structure" (p. 309), and the conclusion says an HPSG with MRS allows "lexical and construction-specific constraints on partial semantic interpretations to be characterized in a fully declarative manner" (p. 326). No step in §5.2 or §6 involves a choice. For a given derivation, the feature structure at the root contains the whole MRS.

The two things outside unification:

- **The root condition.** In the abstract formulation the global top is qeq to the root's LTOP, and this qeq is not contributed by any word or phrase (p. 301). Figure 5 represents it "as an extra level in the tree; this is not essential, but provides a locus for the constraint" (p. 309; the top node of Figure 5, p. 310, adds a qeq with HARG = GTOP and LARG = LTOP). For the July 2003 ERG the root condition is different: the global top is equal to the label of the outermost message relation, GTOP is redundant, and "the LTOP of a root structure is also the global top" (p. 313). An engine must know which convention its grammar version uses for the top handle; the paper does not show where the ERG states the root condition.
- **Scope resolution.** Enumerating scoped readings is done by "external modules for extra-grammatical processing" (p. 309). This is not needed to produce the MRS. It is needed only for the full well-formedness test (caveat 6).

### 2. Reading the object off the feature structure is a conversion with its own rules (high; MRS extraction)

The paper gives the correspondence in (31) (p. 306) and its conventions:

- **Relation.** The EP's relation is the type of the EP feature structure; types for lexeme relations have a leading underscore and all relation types end in `_rel` (p. 305). The alternative of a RELN feature is mentioned as a choice not taken (p. 306).
- **Handles and variables are identities of nodes.** "Coindexation is used to represent variable identity; we take a similar approach with handles" (p. 305). A handle or variable name in the MRS object corresponds to one node in the feature structure. A node that is not coindexed with anything still needs a name: the BODY of `_every_rel` in (31) has no tag in the feature structure and is h5 in the tuple (p. 306). The extractor therefore assigns one fresh name per distinct node, and distinct variables must get distinct names (pp. 295–296).
- **Label versus hole.** "There is no type distinction between handles in label position and argument handles" (p. 305). Which handles are labels and which are holes is determined by the feature they are the value of (LBL versus RSTR, BODY, ARG1 of a scopal relation, MARG, L-HNDL, R-HNDL).
- **Sort of a variable and its properties.** The sort comes from the type of the node (`handle`, `ref-ind`, `event` in (31) and (34), pp. 306, 311). Variable properties are the features of the index node: PN and GEN on a `ref-ind`, TENSE and MOOD on an `event` in (34) (p. 311). Tense and mood are "values on the event variable of the verb" that "record the information derived from the morphology of a verb (or an auxiliary)" (p. 312). The paper says "the details of the encoding are not relevant to the MRS representation" (p. 311), so it gives no inventory of properties.
- **Argument features.** A "relatively small set of features" is used across relations; the ERG uses ARG0, ARG1, ARG2 and so on, plus RSTR and BODY for quantifiers (p. 305), MARG for messages (p. 313), L-HNDL and R-HNDL for conjunctions (p. 322).
- **Bags as lists.** RELS and HCONS are bags "implemented as a list" (pp. 305–306). The order is semantically irrelevant and repeated elements are allowed (p. 289; n. 5, p. 327).
- **HCONS.** Each element has type `qeq` with HARG (the hole) and LARG (the label) (p. 306).

### 3. RELS and HCONS are accumulated by append, and append is the engine's business (high; data representation)

"The appending of the accumulator attributes RELS and HCONS can be implemented by difference lists in those variants of feature structure formalisms which do not support an append operator directly" (p. 308). The paper writes the append as `+` in Figure 4, Figures 8–9 and (43) and never shows the difference-list encoding. Reading the final RELS list out of a difference list (from the list's start up to the node shared with its end pointer) is a step the paper leaves to the implementation.

### 4. What each node contributes, according to §6.2 (high; MRS extraction and the relaxed level)

The four principles (pp. 313–314):

1. RELS of a phrase is the append of the daughters' RELS.
2. HCONS of a phrase is the append of the daughters' HCONS.
3. HOOK of a phrase is the HOOK of the semantic head daughter, "which is determined uniquely for each construction type".
4. One slot of the semantic head daughter is identified with the HOOK of the other daughter. Scopal: this yields a qeq between a scopal argument and the other daughter's LTOP. Intersective: an argument of an EP is identified with the other daughter's INDEX, and the two LTOPs are identified.

Then the amendment: a phrase may introduce content through C-CONT, whose value "behaves for purposes of composition just like the semantics of an additional daughter", and "it is possible for the C-CONT to be the semantic head of a phrase" (p. 314). The RELS of a phrase is "always the sum of the RELS list of its daughters (together with its C-CONT)" (p. 318). "Most constructions in the LinGO grammar actually have an empty C-CONT" (p. 320).

Consequences for attribution:

- **The semantic head is often a different daughter from the syntactic head.** In a head-modifier rule "the semantic head daughter is the modifier" (p. 313). In Figure 5 (p. 310) the sentence's HOOK is the HOOK of *probably sleeps*, which is the HOOK of *probably*; the HOOK of *every dog* is the HOOK of *every*.
- **Qeqs mostly originate in lexical entries.** The qeq of a quantifier (HARG = RSTR) and of a scopal adverb (HARG = ARG1) is on the HCONS list of the lexical entry with LARG unfilled; the rule that combines the word with its sister fills LARG by coindexation with the sister's LTOP (p. 307, (33); p. 309). A verb taking a clause has the qeq from its ARG2 to the complement's LTOP in its own entry, reached through ARG-ST ((36), p. 315). A control verb likewise: in Figure 7 (p. 320) *tried* has a qeq from ARG2 to the LTOP of the VP complement and identifies its ARG1 with the complement's XARG.
- **Intersective LTOP identity comes from the rule.** There are two modification rules; "the intersective modifier rule equates the LTOP values of the two daughters, while the scopal version does not", which "removes the need for coindexation of ltops in the lexical entries of intersective adjectives" (p. 315). In Figure 6 (p. 316) the phrase *allegedly difficult* has LTOP = the label of `_allegedly_rel` and INDEX = the index of *difficult*'s argument; the intersective rule then equates that LTOP with the label of `_problem_rel`, and `_difficult_rel` keeps its own label below the qeq.
- **Head-complement rules may leave the mode open.** Rules for combining a lexical head with its complements "might well inherit from the more general (underspecified) type, leaving the lexical head to determine the form of composition" (p. 308). The same rule name in a derivation can therefore be scopal in one instance and intersective in another, decided by the lexical entry.
- **Quantifier BODY is never constrained by composition** (p. 301).
- **Constructions with their own EPs.** The bare-NP rule (Figures 8 and 9, p. 321): C-CONT has RELS with one `udef_rel` (ARG0 = the head daughter's INDEX, RSTR a hole) and HCONS with one qeq from RSTR to the head daughter's LTOP; the mother's HOOK is the C-CONT's HOOK, so C-CONT is the semantic head; the mother's RELS is C-CONT's RELS + the head daughter's. The imperative rule (unary) and the compound noun rule (recursive binary) are named as other cases, without detail (p. 320).
- **Lexical rules.** The only statement: "The same principles also apply for the semantic contribution of lexical rules" (p. 320).
- **Lexical entries with several EPs.** They must satisfy the same principles as phrases, and "we may also need an additional type of handle constraint for simple equality" (p. 309; the example is *non-recursive*). Partially specified handle constraints may be present in lexical entries (n. 12, p. 328).

### 5. Coordination uses direct handle identity and a constructional conjunction (medium; MRS extraction)

Conjunctions are binary relations with L-HNDL and R-HNDL (p. 322). In the coordination rule (43) (p. 322) the mother's HOOK (INDEX and LTOP) is the right daughter's; the right daughter's RELS contains the `conj_rel` whose LBL is that LTOP and whose L-HNDL is identified with the left daughter's LTOP; RELS and HCONS are appended left then right. R-HNDL is filled when the conjunction combines with its right sister "via a head-marker rule not shown here" (p. 322). For three or more conjuncts, a variant of the rule introduces a new conjunction relation in C-CONT (p. 322): in (44) (p. 323), *slip, slide, and slither* has `_and_rel` and a second relation of the general type `conj_rel`, and HCONS is empty. The identity of conjunct LTOPs with the holes is direct, with no qeq, to avoid spurious scope ambiguity (p. 323). So a hole can be filled by structure sharing with no HCONS entry, and a check that expects one qeq per hole is wrong. The presentation "simplifies the implemented ERG coordination analysis in non-essential respects" (n. 20, p. 328). The prose on p. 322 refers to the rule as "(1)"; the rule is numbered (43).

### 6. Well-formedness: what the paper defines, and what is cheap (medium; checking tagger output)

Defined in the paper:

- No handle outscopes the top (Definition 3, p. 293).
- A scope-resolved MRS is a tree of EP conjunctions: connected, single root, no node with two parents; the top and every hole are identified with a label; all constraints hold (Definition 4, p. 293). Every EP label is identified with a hole, except the top's (p. 294).
- Two conditions from the object language: no argument is left unsatisfied, and "an EP may fill at most one argument position" (p. 291). Two holes may not be equated (p. 295).
- Well-formed = link-subsumes at least one scope-resolved MRS (Definition 5, p. 295).
- Variable binding, for complete sentences: a variable is unbound if it is not the bound variable of any quantifier, or if it occurs outside the restriction and body of its quantifier; "no two quantifiers may share bound variables" (p. 295). Event variables are exempt: they "are not explicitly bound" and are assumed to have an implicit wide-scope quantifier (p. 312).
- "A qeq constraint always relates a hole to a label" (p. 297).
- Structural properties that follow from the composition rules: a backbone of fixed scopal EPs ending in non-scopal EPs; every quantifier has a similar backbone under its restriction and a fully unconstrained body; every non-scopal EP is in a qeq relationship with a quantifier's restriction or with an argument of a fixed scopal EP (pp. 302–303).
- Each quantificational determiner contributes exactly one quantifier EP, and no EP is ever duplicated or dropped by composition (p. 318).

On cost: n quantifiers with no other scopal elements give n! scopes, a naive resolver is "problematic", and non-factorial algorithms exist for deciding whether an MRS expressed with dominance constraints has at least one scope (pp. 309–311, citing Niehren and Thater 2003).

On the status of the test: "If an MRS produced by a grammar for a complete sentence does not correspond to any object language structures, we assume there is an error in the grammar"; using semantic ill-formedness to rule out analyses on purpose "requires a rather unlikely degree of perfection on the part of the grammar developer" (n. 6, p. 327). And implemented grammars "sometimes do not completely meet the constraints described" (n. 11, p. 328). So a failed well-formedness check on a licensed derivation points first at the grammar or at the extractor, and the paper gives no ground for treating it as evidence against the tagger's derivation.

### 7. Event variables, tense, and messages are ERG decisions layered on MRS (medium; MRS extraction)

The INDEX of a clause is the verb's event variable (p. 312, (34) p. 311). In (34) the root has an extra EP `prpstn_m_rel` with LBL = the root LTOP, MARG a hole, and a qeq from MARG to the label of `_prbly_rel` (p. 311). A message that is the argument of a scopal EP is equal to that argument position, with no qeq (p. 313). The paper does not say which lexical entry or construction contributes the message relation.

### 8. XARG is a third hook feature (low; MRS extraction)

HOOK contains "the semantic properties that a given phrase 'makes visible' to the outside"; besides LTOP and INDEX the ERG has XARG, the index of the subject argument, used for control (p. 319, Figure 7 p. 320). In the ERG the same index is reachable through the SUBJ list; XARG is motivated by languages in which the controlled element is a pronoun inside the complement (p. 319).

## Support for the design

- **No search and no choice in semantic construction.** Composition is append plus identities stated on rule types and lexical entries (Figure 4, p. 308; pp. 313–314). Replay of a derivation yields the MRS as a by-product of the unifications it already performs.
- **Scope is left underspecified by design, and the grammar yields one MRS per analysis.** "Each analysis of a sentence produced by a grammar corresponds to a single MRS structure" (p. 291). There is no ambiguity in the relative scope of two non-quantifiers "unless there is lexical or syntactic ambiguity" (p. 304); for the ambiguous coordination example "there is only one resolved MRS for each syntactic analysis" (p. 323). The derivation chosen by the tagger fixes everything except quantifier scope.
- **No quantifier store.** The comparison with Cooper storage and with Pollard and Yoo (1998) shows what the engine does not need: no store, no retrieval sites, no amalgamation relations (pp. 317–318).
- **HOOK as the only interface between daughters.** A semantic functor sees only the other daughter's LTOP, INDEX and XARG (pp. 305, 313, 319). This is a small, fixed interface on which a relaxed semantic level could be defined: when unification of the full signs fails, the hook-to-slot identifications and the two appends are still well defined. That use is my inference; the paper does not discuss derivations the grammar rejects.
- **Slots are stated independently of the feature geometry.** Slots "enable us to describe semantic composition without having to discuss the feature structure architecture and which can be implemented in non-feature structure formalisms" (p. 313).
- **Flat EPs with handles can be read with scope ignored.** "To derive a flat representation something like Trujillo's ... we just ignore the handles" (p. 289). A degraded output with EPs and variable identities and no HCONS is a meaningful object in the paper's own terms.
- **RMRS is named as the route to more extreme underspecification**, designed so that shallow systems produce a representation "compatible with the output of deep grammars, such as the ERG" (p. 326).

## Theory strains

- **Qeq versus plain outscopes.** Earlier versions of MRS used other constraint types (n. 9, p. 328). The authors hypothesize that in a grammar that perfectly obeyed the composition constraints qeq would be equivalent to outscopes; this is unproven, and actual grammars deviate, so qeq is kept (n. 11, p. 328).
- **Relaxing the no-ambiguity-between-non-quantifiers property.** It holds for *Kim could not sleep*, "but there are other phenomena that may require these conditions to be relaxed" (p. 304).
- **Relation as type versus relation as feature value.** The RELN alternative would allow complex relations such as very(big)(x) and reduce the number of types; it is set aside for presentation reasons (p. 306). Predicate modifiers are excluded from the object language "for the purposes of the current discussion" (p. 289).
- **Handle identity versus coindexation with whole EPs.** Possible only with an explicit conjunction relation (p. 306).
- **Equality as a handle constraint.** May be needed for semantically complex lexical entries (p. 309).
- **Event variables and scope.** The implicit wide-scope quantifier for events "is not entirely adequate" (p. 312).
- **Role of GTOP.** Redundant in the ERG, but a global top "may however play an important role in DRT-style semantic representations" (n. 18, p. 328).
- **Bare NPs.** `udef_rel` is syntactically a generalized quantifier and the authors "say nothing about what it means" (p. 320; n. 19, p. 328).
- **Quantifier duplication in coordination.** No account of *We needed and craved more protein* (n. 21, p. 328).
- **Predicate names.** Names reflect July 2003; "further normalisation of predicate names" was introduced afterwards (n. 17, p. 328). Older feature names: HANDEL or HNDL for GTOP and for LBL, LISZT or LZT for RELS (n. 14, p. 328).
- **Non-monotonic MRS.** Definable, not considered (n. 8, p. 328).
- **Coverage.** "There are many areas in which our analyses are currently inadequate" (p. 326).

## Key primary sources

- Copestake, Lascarides and Flickinger 2001, An algebra for semantic construction in constraint-based grammars (ACL): the formal statement of hooks and slots that §5.2 and §6.2 rely on. Queue item 3.
- Copestake, Flickinger, Malouf, Riehemann and Sag 1995, Translation using Minimal Recursion Semantics (TMI-95): the earlier partial description.
- Bos 1995, Predicate logic unplugged: holes and labels; the formalization "owes a lot to his work" (p. 324).
- Niehren and Thater 2003; Koller, Niehren and Thater 2003; Fuchss, Koller, Niehren and Thater 2004: MRS as dominance constraints, satisfiability, and an evaluation on a grammar (cited for the qeq question, n. 11).
- Reyle 1993 (UDRT); Nerbonne 1993 (feature-based underspecified semantics); Alshawi and Crouch 1992.
- Kasper 1996, Semantics of recursive modification (unpublished): the problem that the two modifier rules solve.
- Pollard and Yoo 1998; Pollard and Sag 1994: the Cooper storage analyses that MRS replaces.
- Ginzburg and Sag 2000: message relations.
- Flickinger, Copestake and Sag 2000: the ERG.
- Bender, Flickinger and Oepen 2002; Bender and Flickinger 2003: the Matrix.

## Not covered here

These are my remarks, not statements from the article.

- **The file is the 2005 article, so question 5 of the reading (what the 1999 draft marks as provisional) cannot be answered from it.** What the article itself signals as changed since 1999 or as dated is collected under "Theory strains" (n. 1, n. 9, n. 11, n. 14, n. 17).
- **The current ERG differs from the July 2003 grammar described here.** From my recollection, unverified against the grammar files: current ERG releases have no message relations (clause type is a property SF on the event variable); the predicate is the value of a feature PRED on a generic relation type; a third list, ICONS, holds individual constraints; and the top handle is related to the root LTOP by a qeq. Each of these changes the extraction procedure of caveats 1, 2 and 7. The procedure has to be taken from the grammar we replay (its type files and the variable property mapping used by existing extractors), with this article as the conceptual frame.
- **The article gives no extraction algorithm.** It gives a worked correspondence, (31), and conventions. Nothing on the mapping from grammar-internal types and features to the published variable properties, nothing on character spans linking EPs to tokens, nothing on which paths in the sign hold the MRS beyond the paths drawn in Figures 8–9 and (43) (SYNSEM|LOCAL|CONT, C-CONT).
- **Candidate cheap checks on an extracted MRS,** assembled by me from the conditions in caveat 6, in increasing cost: (a) every HARG of a qeq is a hole of some EP or the top, and every LARG is the label of some EP; (b) no handle appears as a hole twice; (c) every `ref-ind` variable is the ARG0 of exactly one quantifier EP, in a complete sentence; (d) every quantifier has a qeq on RSTR and none on BODY; (e) every label that is not a quantifier's is reachable from the top through holes, direct identities and qeqs; (f) at least one scope exists. Checks (a)–(e) are linear. Whether they pass on gold ERG output without exceptions is an empirical question (n. 11 warns that implemented grammars deviate).
- **A count invariant for the tagger.** Since RELS is pure append (p. 318), the number of EPs in the MRS equals the sum over the leaves' lexical entries, the lexical rules and the C-CONTs of the constructions in the derivation. This is checkable from the derivation alone, before any unification. The remark is mine.
- **Lexical rules get one sentence** (p. 320). Which ERG lexical rules add EPs, and how inflectional rules set variable properties, has to be read from the grammar.
- **Not read from images:** Figures 1 and 2 (p. 298). Nothing in these notes depends on them.
