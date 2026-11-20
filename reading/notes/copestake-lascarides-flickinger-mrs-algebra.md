# Copestake, Lascarides and Flickinger (2001): An algebra for semantic construction in constraint-based grammars

Ann Copestake, Alex Lascarides and Dan Flickinger, "An Algebra for Semantic Construction in Constraint-based Grammars". Read from `MRS_algebra.pdf` (8 PDF pages: text pp. 1–8, with the references and acknowledgements on p. 8). The file is an authors' copy (pdfTeX, created 9 May 2001) with no venue, no date and no printed page numbers on any page. The venue comes from the ACL Anthology record P01-1019, checked 2026-11-20: *Proceedings of the 39th Annual Meeting of the Association for Computational Linguistics*, Toulouse, July 2001, pp. 140–147. I did not compare the Anthology PDF with this file. Page numbers below are PDF pages of the file (proceedings page = PDF page + 139, if the two versions are paginated alike). Read in full from the text layer (`txt/MRS_algebra.txt`), and all eight pages were also read as page images. The text layer is good for the prose. It garbles Figure 1 (the feature structures, p. 2), it turns every prime into a zero (h′ appears as `h0`, x′e as `x0e`), and it flattens subscripts and the denotation brackets in Section 3. Every formula and every example structure quoted below was checked against the page images. Read 2026-11-20.

Question for this reading: what are the objects and operations of the algebra; can the operations be stated per schema, so that the relaxed level composes semantics from the schema name and the identity of the semantic head; what does the algebra forbid; how does it relate to the feature structures of implemented grammars; and which formal properties are stated?

## Summary

The paper formalizes what MRS-based grammars do when they build semantics by unification. It starts from the observation that the operations in such grammars are specified only in the feature-structure logic, that nothing prevents composition from "accessing arbitrary pieces of structure", and that nothing guarantees monotonicity, defined as: "in each rule application the semantic content of each daughter subsumes some portion of the semantic content of the mother (i.e., no semantic information is dropped during composition)" (p. 1). MRS already enforces accumulation of elementary predications (EPs) by append, but "does not fully specify compositional principles and does not formalize composition" (pp. 1–2). The work began as a "rational reconstruction of semantic composition" in the LinGO ERG (p. 2). The algebra is built in four steps.

**Step 1: the simple algebra (Section 2, pp. 2–3).** A simple semantic entity (SSEMENT) is either the absurdity symbol ⊥ or a four-tuple (Definition 2, p. 3):

- a hook, one index: "a record of the value in the semantic entity that can be used to fill a hole in another entity" (p. 2);
- a hole, empty or one index: holes "record gaps in the semantic form which occur because it represents a syntactically unsaturated structure" (p. 2);
- the lzt, a bag of simple EPs, each a relation symbol with a list of index arguments (Definition 1, p. 3); a bag so that repeated EPs, as in *big big car*, need no check (fn. 2, p. 2);
- the eqs, a set of equalities between variables.

Indices have two subtypes, events and individuals, and an equality is well formed only between variables of compatible sorts; "sort compatibility corresponds to unifiability in the TFS logic" (p. 3). The single operation is op(a1, a2), in which a2 is "the equivalent of a semantic functor and a1 its argument" (p. 3). Definition 3 (p. 3): if a1 = ⊥, or a2 = ⊥, or hole(a2) = ∅, then the result is ⊥. Otherwise:

1. hook(op(a1, a2)) = hook(a2)
2. hole(op(a1, a2)) = hole(a1)
3. lzt(op(a1, a2)) = lzt(a1) ⊕ lzt(a2)
4. eq(op(a1, a2)) = Tr(eq(a1) ∪ eq(a2) ∪ {hook(a1) = hole(a2)}), with Tr the transitive closure

In words (p. 2): a hole in the semantic head is filled with the hook of the other daughter by equating the variables, and the lzts are appended. The mother's hook is the functor's hook; in the one-hole version the functor's hole is used up and the argument's hole is passed up. The example (p. 2): *Kim* `[x2]{[]subj, []comp}[r_name(x2, Kim)]{}` and *sleeps* `[e1]{[x1]subj, []comp}[sleep(e1, x1)]{}` give *Kim sleeps* `[e1]{[]subj, []comp}[sleep(e1, x1), r_name(x2, Kim)]{x1 = x2}`.

Three assumptions accompany the definition (p. 3). Composition is always binary; ternary rules are sequences of binary operations. A grammar rule may contribute semantic information of its own, and that information "obeys all the same constraints as the semantics for a sign", so such a rule is equivalent to a null element in the grammar. The mapping from argument order to linear order "is specified by syntax". Each instance of a lexical sign has variables distinct from those of every other instance; repetition of a variable inside one lexical entity plays the role of lexical coindexation, and coindexation that arises in composition is always an added equality (p. 3; the formal statement is omitted there as "a little long-winded").

**Step 2: labelled holes (Section 4, pp. 4–5).** Real grammars need several holes, each with a label from "a fixed inventory of labels for any grammar framework". For the ERG the inventory is SUBJ, SPR, SPEC, COMP1, COMP2, COMP3 and MOD (pp. 4–5). There is one operation per label. Definition 6 (p. 5) gives op_subj(a1, a2): the result is ⊥ if either argument is ⊥ or if hole_subj(a2) is empty; it is also ⊥ if for some other label l the two daughters together have more than one hole, |hole_l(a1) ∪ hole_l(a2)| > 1. Otherwise the hook is that of a2, the lzts are appended, the eqs gain hook(a1) = hole_subj(a2), and for every label l other than subj the mother's hole is hole_l(a1) ∪ hole_l(a2). "There will be similar operations op_comp1, op_comp2 etc for each labelled hole" (p. 5).

**Step 3: scope (Section 5, pp. 5–6).** EPs get the four MRS components: a handle that labels the EP, a relation, a list of index arguments, and a list of handle arguments for scopal positions (Definition 7, p. 5). A fifth component is added to the entity, a bag of handle constraints (hcons), "accumulated by append" (p. 5). The algebra is neutral about the kind of constraint: `rel_h` stands for qeq as in MRS or for the ≤ of UDRT (p. 5). Hooks and holes become pairs of a handle and an index, and "the handle in the hook corresponds to the LTOP feature in MRS" (p. 5). A SEMENT is ⊥ or a five-tuple of hook, holes, bag of EPs, bag of hcons, and set of equalities (Definition 8, p. 6), written `[h1, i1]{holes}[eps][hcons]{eqs}`. Composition is unchanged except that hcons are appended and filling a hole adds two equalities, one between the handles and one between the indices (p. 6).

**Step 4: external arguments (Section 6, p. 7).** For control, hooks and holes get a third member, the external argument ("the external argument of a verb always corresponds to its subject position"). The authors "believe that the handle, index, external argument triple constitutes all the semantic information that a sign should make accessible to a functor" (p. 7).

**The paper's treatment of each construction type.**

| Construction | Operation | Functor (gives the hook) | What the paper shows | Page |
|---|---|---|---|---|
| Subject | op_subj | the verb | *Kim sleeps*; the noun phrase's hook is equated with the verb's SUBJ hole | pp. 2, 5 |
| Complements | op_comp1, op_comp2, op_comp3 | the selecting head | stated as "similar operations", with no worked composition; the two entries for *expect* show COMP1 holes | pp. 5, 7 |
| Specifier (quantifier) | op_spec | the determiner | *every dog*; only the determiner's SPEC hole is used | p. 6 |
| Intersective modification | op_mod | the modifier | *white dog* | p. 6 |
| Scopal modification | op_mod | the modifier | *probably walks* | p. 6 |
| Control | op_comp1 with triple hooks | the control verb | two lexical entries for *expect*, no composed result shown | p. 7 |
| Coordination | not defined | not stated | one paragraph: an extension for "simple constituent coordination" | p. 5 |

Details of the worked examples, all on p. 6:

- *every* is `[hf, x]{[]subj, []comp1, [h′, x]spec, ...}[he: every(x, hr, hs)][hr =q h′]{}` and *dog* is `[hd, y]{...}[hd: dog(y)][]{}`. op_spec adds `{h′ = hd, x = y}`; the mother keeps the hook `[hf, x]` and the single hcons `hr =q h′`. The qeq between the restriction and the noun's label is in the determiner's lexical entity; the operation adds nothing beyond the two equalities. The determiner is also selected syntactically by the N′ through SPR, but "from the standpoint of the compositional semantics, the determiner is the semantic head, and it is only its SPEC hole which is involved: the N′ must be treated as having an empty SPR hole".
- Intersective and scopal modification use the same operation. "In the ERG, the distinction between intersective and scopal modification arises because of distinctions in representation at the lexical level. The repetition of variables in the SEMENT of a lexical sign ... and the choice of type on those variables determines the type of modification."
- *white* is `[hw, x]{..., [hw, x]mod}[hw: white(x)][]{}`: its MOD hole repeats its own hook handle and its own argument. op_mod with *dog* adds `{hw = hd, x = y}`, so the two EPs share a label and an argument. The mother's hook is `[hw, x]`, the modifier's.
- *probably* is `[hp, e]{..., [h, e]mod}[hp: probably(hs)][hs =q h]{}`: its MOD hole has a handle different from its hook handle, and its entity carries a qeq to that handle. op_mod with *walks* `[hw, e′]{[h′, x]subj, ...}[hw: walks(e′, x)][]{}` adds `{hw = h, e = e′}`. The mother's hook is `[hp, e]`: the adverb's label with the verb's event. The verb's unfilled SUBJ hole `[h′, x]` is in the mother's holes.
- Control (p. 7): *expect* as in *Kim expected to sleep* is `[he, ee, x′e]{[hs, x′e, x′s]subj, [hc, ec, x′e]comp1, ...}[he: expect(ee, x′e, h′e)][h′e =q hc]{}`. The variable x′e is the external argument of *expect*, the index of its subject, and the external argument in the COMP1 hole. In the entry for *Kim expected that Sandy would sleep* the COMP1 hole has an unrelated external argument x′c. The predicate is the same in both entries, and the control reading "arises as a consequence of the restrictions on variable assignments imposed by the equalities".

**Interpretation (Section 3, pp. 4, 6).** The EPs and eqs of the simple algebra are interpreted in a first-order model with events, individuals and an interpretation function; an entity denotes a triple of its hook, its hole and the set of variable assignments that satisfy its EPs and eqs (Definition 4, p. 4). The hook and hole have to be part of the denotation because the meaning of the mother "cannot be constructed purely as a function of" the two sets of assignments (p. 4). For the scopal version the model gains a set of labels with a well-founded partial order, and the denotation has one handle-index pair for the hook and one per hole (p. 6). The language is first order, with no λ-abstraction over higher-order elements; *every* is a predicate in a language whose expressions are "partial descriptions of logical forms in a base language" (p. 6, fn. 5).

**Formal properties stated.**

- op is a function and its range is within Σ, so ⟨Σ, op⟩ is an algebra (Theorem 1, p. 3).
- The denotation mapping is a homomorphism from ⟨Σ, op⟩ to the algebra of denotations, so semantic construction is compositional (Theorem 2, p. 4). The proof is one sentence: it "follows from the definitions".
- For labelled holes, the operations "can be proved to form an algebra"; closure needs the extra observation that the result is ⊥ or has at most one hole per label, which is "straightforward to see" (p. 5). For the version with handles, the revised operations "still form an algebra" (p. 6). Neither proof is given.
- The paper states no associativity, commutativity or confluence result, and no theorem about monotonicity. Monotonicity is defined (p. 1) and is a visible consequence of clauses 3 and 4 and of the append on hcons: every EP, hcons and equality of a daughter is in the mother. That last sentence is my reading of the definitions.

**Relation to implemented grammars (pp. 2, 7, 8).** "The essential features of the algebra can be encoded in the hierarchy of lexical and constructional type constraints" (p. 2), and there is "a straightforward relationship" between the algebra and the feature structures of Figure 1, although other feature architectures share the same encoding (p. 2). Semantics and the syntax-semantics interface "have accounted for approximately nine-tenths of the development time" of the ERG (p. 2). Some of the algebra cannot be encoded in implemented formalisms, because the conditions are negative: "we could not write TFS constraints that absolutely prevent a grammar writer sneaking in a disallowed coindexation by specifying a path into the lzt" (p. 8). The authors propose to treat these as "metalevel conditions on the description of the grammar, which can anyway easily be checked by code which converts the TFS into the algebraic representation"; the constraints "need not be checked at runtime" (p. 8). On the ERG: "we have not yet fully completed the exercise of retrospectively implementing the constraints throughout", the work done so far "revealed many bugs in the grammar", and the grammar has been modified to be monotonic, which the chart generator of Carroll et al. (1999) needs (p. 8). One deviation is named: the KEY feature used for semantic selection "violates these accessibility conditions", and can be replaced by KEYPRED, "which points to the predicate alone" (fn. 7, p. 7). The Grammar Matrix is not mentioned anywhere in the paper.

## Caveats for the parser

### 1. The semantic head is the functor, and it is often a different daughter from the syntactic head (high; relaxed-level composition)

The mother's hook is always the hook of a2, the daughter whose hole is filled (Definitions 3 and 6, pp. 3, 5). In *white dog* and *probably walks* that daughter is the modifier, and in *every dog* it is the determiner (p. 6). A relaxed level that knows the schema name and the syntactic head has to derive the functor from the schema: the head in head-subject and head-complement, the non-head in head-specifier and head-adjunct. The paper gives this mapping only through its examples; the schema names are mine, since the paper speaks of hole labels and never of schemas.

### 2. The operation is selected by a hole label, and the schema name does not always fix the label (high; relaxed-level composition)

The label is determined for subjects (SUBJ), specifiers (SPEC, on the determiner) and modifiers (MOD). For complements the operations are op_comp1, op_comp2 and op_comp3 (p. 5), so a derivation that says only "head-complement" leaves open which complement hole is filled. The paper's remark that HPSG keeps complements on a list, with a fixed upper limit that permits numbered labels (p. 4), does not say how a rule picks the number. A relaxed level needs either a convention (fill the first non-empty COMP hole) or a label from the tagger. The convention is my suggestion.

### 3. Scopal and intersective modification are distinguished in the lexical entity, with one operation for both (high; relaxed-level composition)

op_mod is the same in both cases; the difference is whether the modifier's MOD hole repeats the hook handle (*white*) or carries a separate handle under a qeq (*probably*) (p. 6). A relaxed level with no lexical semantic entities cannot tell the two apart from the schema. It needs one bit per modifier, from a lexical type, from the tagger, or from the rule name if the grammar splits the adjunct rule. The paper never says that the rule carries this information.

### 4. The specifier construction uses SPEC and ignores SPR (medium; relaxed-level composition)

The N′ selects the determiner through SPR, but for composition "the N′ must be treated as having an empty SPR hole" (p. 6). The paper calls this "a slight complication" and does not say how the SPR hole of the N′ comes to be empty, or whether an SPR hole is ever filled by an operation. The inventory on p. 5 lists SPR as a label, and no example uses it.

### 5. Definition 6 does not say what happens to the filled hole or to the argument's hole of the same label (medium; exactness of the definition)

Clause 2 of Definition 6 (p. 5) covers only labels other than subj. The mother's subj hole is shown as empty in *Kim sleeps* (p. 2) and the SPEC hole as empty in *every dog* (p. 6), so the intended reading is that the filled hole disappears. The definition does not state it, and it does not say what happens if the argument a1 also has a non-empty subj hole (in the one-hole version, clause 2 of Definition 3 passes the argument's hole up). An implementation has to choose; treating the filled label as empty in the mother, and a non-empty hole with that label on the argument as an error, matches every example in the paper. That choice is mine.

### 6. Holes of the non-functor daughter survive, and two daughters may not both hold a hole with the same label (medium; invariant)

For every label other than the one being filled, the mother's hole is the union of the daughters' holes, and the result is ⊥ if the union has more than one member (Definition 6, p. 5). In *probably walks* the verb's SUBJ hole passes through the adverb (p. 6). This gives a checkable condition on a derivation: at each binary node, apart from the filled label, at most one daughter has a non-empty hole for any given label. Coordination is the stated exception (caveat 7).

### 7. Coordination is one paragraph with no definition (medium; coverage)

The operations "can be extended in a straightforward way to handle simple constituent coordination of the kind that is currently dealt with in the ERG (e.g., *Kim sleeps and talks* and *Kim and Sandy sleep*); such cases involve daughters with non-empty holes of the same label, and the semantic operation equates these holes in the mother SEMENT" (p. 5). Nothing is said about the hook of the coordinate structure, about the EP for the conjunction, or about which daughter is the functor. Under Definition 6 as written, two daughters with non-empty holes of the same label give ⊥, so coordination needs an operation of a different shape.

### 8. Construction-contributed semantics is covered by an assumption only (medium; coverage)

Rules that add their own EPs are treated as if a null element with an ordinary semantic entity were present (p. 3). The paper gives no example, and it does not say how such a rule's entity is composed with two daughters (two binary operations in some order, presumably). The ERG has many such rules; for the relaxed level each needs its own small entity and an order of application.

### 9. Variable identity is carried by an equality set that must be closed and resolved (low; data representation)

Composition never renames variables: it adds equalities and takes the transitive closure (pp. 3, 6). The result of *every dog* is said to be "semantically equivalent" to the entity with the equalities applied (p. 6). A relaxed-level implementation can use union-find over variables and apply sort compatibility when two classes merge; an incompatible merge (an event with an individual) is ill formed (p. 3). The paper does not say whether an ill-formed equality makes the result ⊥.

### 10. Small inconsistencies in the examples (low; reading the paper)

In the second entry for *expect* the EP's label is written `h` where the hook has `he` (p. 7). In clause 4 of Definition 3 an opening brace is missing (p. 3). In Section 5 the examples use pairs, and the SUBJ hole of *walks* is `[h′, x]` with a handle that plays no further role (p. 6). The hook handle of *every* is `hf`, a handle that labels no EP, and the paper does not comment on it (p. 6).

## Support for the design

- **A relaxed level that composes without full unification is what the algebra describes.** The semantic content is "largely independent of the feature structure architecture of the syntactic representation" (p. 8), and the algebra "abstracts away from the specific feature architecture used in individual grammars" (p. 2). One composition step is: choose the functor and a hole label, add two or three equalities, append two bags. The application to Orca's relaxed level is my conclusion.
- **The rule itself adds almost nothing.** In all the worked examples the operation contributes only equalities between a hook and a hole; EPs, qeqs and the scopal or intersective distinction come from lexical entities (p. 6). This is what makes a small schema inventory plausible, provided the lexical entities are available.
- **The authors propose a converter from feature structures to the algebra as a checker.** The conditions are "metalevel conditions on the description of the grammar", checkable "by code which converts the TFS into the algebraic representation" (p. 8). The same converter applied to the output of strict replay gives the entity that the relaxed level should reproduce, so the two levels can be compared node by node. The comparison is my proposal.
- **Candidate invariants, all from the definitions.** (a) Every EP and hcons of a daughter is in the mother, with nothing dropped (p. 1; clause 3, p. 3; hcons append, p. 5). (b) The mother's hook is the hook of exactly one daughter (clause 1, pp. 3, 5). (c) A functor sees only the hook of its argument: handle, index, external argument (p. 7). (d) At most one hole per label on any entity (Definition 2, p. 3; closure remark, p. 5). (e) Hole labels come from a fixed inventory (pp. 4–5, 7). (f) Equalities respect sorts (p. 3). (g) No coindexation by a path into the lzt (p. 8). (h) Distinct lexical instances share no variables before composition (p. 3).
- **Accessibility has linguistic content.** Because only the hook is visible, "it is impossible to define a verb that controls the object of its complement" (p. 7). A tagger output that requires such a link violates the algebra.
- **Binary composition.** Ternary rules reduce to sequences of binary operations (p. 3).
- **Monotonicity serves generation.** The chart generator of Carroll et al. (1999) determines lexical entries from the input logical form and works only if nonmonotonicity can be identified in advance; the ERG was made monotonic for it (p. 8).

## Theory strains

- **Syntactic selection versus semantic functor in the specifier construction.** The noun selects the determiner through SPR and the determiner is the semantic head through SPEC; the paper calls it "a slight complication" and stipulates that the SPR hole is empty (p. 6).
- **KEY violates accessibility.** The feature used for semantic selection in MRS grammars reaches past the hook; the proposed repair is KEYPRED (fn. 7, p. 7).
- **The algebra cannot be enforced inside the formalism.** Negative conditions are outside implemented TFS logics; a more general logic "would require very considerable research to develop reasonable tractability" (p. 8).
- **The ERG had not been brought fully into line.** "We have not yet fully completed the exercise of retrospectively implementing the constraints throughout" (p. 8).
- **Size of the inventory.** The authors "think it unlikely that we will need to increase the inventory further", while granting that changes to the valence features would change the hole labels (p. 7). Variants of HPSG already differ: Sag and Wasow (1999) have no SPR and SUBJ distinction (fn. 3, p. 4).
- **Monotonic versus nonmonotonic composition.** "Nerbonne (1995) explicitly advocates nonmonotonicity" (p. 7).
- **Relation to λ-calculus left open.** The relation between the entities of non-sentential constituents and "a more 'standard' formal language such as λ-calculus will be explored in future work" (fn. 4, p. 5); λ-abstraction might still serve as a representation device for adjectives such as *former* (fn. 6, p. 6).
- **Underspecified scope and models.** The link from underspecified forms to models of fully scoped forms through supervaluation is asserted, with details omitted "for reasons of space" (fn. 4, p. 5).

## Key primary sources

- Copestake, Flickinger, Sag and Pollard 1999, Minimal Recursion Semantics: An Introduction (manuscript): EPs, handles, qeq conditions and their principles (pp. 1, 5, 7). Item 2 of the queue.
- Pollard and Sag 1994, *Head-Driven Phrase Structure Grammar*: the Semantics Principle, the valence labels, SPR selection (pp. 1, 5, 6).
- Sag and Wasow 1999, *Syntactic Theory: An Introduction*: the simple grammar that the labelled-hole algebra without scope is sufficient for (pp. 1, 5).
- Carroll, Copestake, Flickinger and Poznanski 1999, An efficient chart generator for lexicalist grammars: the consumer of monotonicity (p. 8).
- Zeevat 1989, A compositional approach to Discourse Representation Theory: source of the idea of putting hooks and holes into the denotation (p. 4). Zeevat, Klein and Calder 1987, Unification Categorial Grammar: the closest formalization strategy (p. 7).
- Reyle 1993, Dealing with ambiguities by underspecification (UDRT): ≤ constraints, supervaluation (p. 5). Fernando 1997: the partial order on labels (p. 6).
- Moore 1989, Unification-based semantic interpretation; Alshawi 1992, *The Core Language Engine*: earlier formalizations of practice in unification grammars (p. 7).
- Egg 1998, Wh-questions in Underspecified Minimal Recursion Semantics (p. 1). Nerbonne 1995 (p. 7). Shieber 1986 (p. 1).

## Not covered here

These are my remarks, not statements from the paper.

- **Long-distance dependencies are absent.** The hole inventory has no label for SLASH or a gap, and the paper never mentions extraction, fillers, relative clauses or questions. Head-filler composition has to come from elsewhere; item 4 of the queue (Copestake 2007) is the next place to look, and I have not read it.
- **Also absent:** head-marker structures, lexical rules and inflection, unary rules in general, the global top handle, the scoping of quantifier bodies, the well-formedness conditions on qeqs (deferred to the 1999 manuscript, p. 7), apposition, and any non-constituent or unlike coordination.
- **Answer to the per-schema question.** The operations can be stated per schema for head-subject, head-specifier and head-adjunct given a table from schema to (functor daughter, hole label). Head-complement needs the complement number in addition. Head-adjunct needs lexical information to choose between the scopal and the intersective outcome, because the algebra puts that difference in the modifier's entity. In every case the relaxed level needs lexical entities with holes: the schema plus the head is sufficient for the rule's contribution and insufficient for the whole semantics. Coordination, head-filler and head-marker have no treatment to copy.
- **The ERG's adjunct rules.** My recollection is that the current ERG has separate head-adjunct rules for intersective and scopal modifiers, which would give the tagger's rule label the bit that caveat 3 asks for. I did not check this against the grammar files.
- **The 2001 ERG is the one described.** The inventory of seven labels, the status of KEY, and the claim that the retrofit was incomplete all date from 2001. Whether the current ERG and the Matrix satisfy the algebra is an empirical question that the converter proposed on p. 8 would answer.
- **External argument.** The third hook member is introduced through two lexical entries with no composed example (p. 7). My recollection is that it corresponds to XARG in the HOOK of current grammars; the paper names only LTOP (p. 5) and does not name a feature for the index or the external argument.
- **No associativity result.** For the relaxed level it would be convenient to know that composing the two complements of a ditransitive in either order gives the same entity up to the order of the bags. The definitions suggest it does, and the paper does not state or prove it.
- **Bibliographic identity.** Venue, year and page range are from the ACL Anthology record, not from the file. The file's contents match the record's title and authors.
