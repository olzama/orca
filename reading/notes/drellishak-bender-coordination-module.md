# Drellishak and Bender (2005): A coordination module for a crosslinguistic grammar resource

Scott Drellishak and Emily M. Bender (University of Washington). In Stefan Müller (ed.), *Proceedings of the 12th International Conference on Head-Driven Phrase Structure Grammar*, Department of Informatics, University of Lisbon, pp. 108–128. Stanford, CA: CSLI Publications, 2005. Read from `coordination.pdf` through its text layer `txt/coordination.txt` (all 21 pages). The text layer is clean for prose, rule schemata, and the TDL in (40); it is garbled for the feature structures (17), (29), (31)–(35), (37), (43), for the trees, and for the diacritics in examples (2) and (3). PDF pages 117–125 were checked as page images, and everything reconstructed below from a feature structure or tree comes from those images. Pages 108–116 and 126–128 were read from the text layer only. Page numbers are those of the proceedings. Read 2026-11-20.

Question for this reading: what does a cross-linguistic coordination module parameterize, what does it fix, and what do its rules look like in a derivation tree with only unary and binary nodes?

## Summary

The paper adds coordination to the Grammar Matrix, which until then was "completely silent on the topic" (p. 109). It covers *and* coordination of constituents of the same or similar category, for two or more coordinands (p. 110). A coordination strategy is described along four dimensions: kind of marking, pattern of marking, position of the mark, and phrase types covered (p. 113). The analysis follows the English Resource Grammar: every coordinate structure is a right-branching chain of one binary "top" rule, zero or more binary "mid" rules, and one "bottom" rule that is binary when it attaches a conjunction word and unary otherwise (pp. 115–116). A boolean feature COORD keeps top phrases usable as ordinary constituents and keeps mid and bottom phrases inside the coordination (p. 116). The Matrix supplies two families of types: syntactic types per marking pattern and semantic types per phrase type. Each rule of a language-specific strategy inherits from one type of each family, and the customization software writes three short type definitions per strategy (pp. 123–124). The semantics is the same for all strategies: a right-branching chain of two-place coordination relations (pp. 120–122). The paper contains no evaluation.

### The parameters as stated (Question 1)

The four dimensions, verbatim from p. 113:

1. Kind of Marking: lexical, morphological, none.
2. Pattern of Marking: a-, mono-, poly-, or omnisyndeton.
3. Position of Marking: before or after the coordinand.
4. Phrase types covered: NP, NOM, VP, AP, etc.

The five questions of the Web form, asked once per coordination strategy, verbatim from p. 113:

1. What phrase types are covered by the strategy?
2. Which of the marking patterns does it use?
3. Is it marked by a word or an affix?
4. What is the orthography of that word or affix?
5. Does the mark come before or after the coordinand?

Definitions of the patterns (pp. 111–112): monosyndeton is one mark for any number of coordinands ("A B conj C"); asyndeton is no mark, equivalent to juxtaposition; polysyndeton is reserved for n − 1 marks for n coordinands ("A conj B conj C"); omnisyndeton is n marks for n coordinands ("conj A conj B conj C"). The authors introduce the poly/omni split because it "turned out to be important" for the module (p. 112). Position applies to every pattern except asyndeton, for a word, prefix, or suffix; English *and* precedes the final coordinand and Latin *-que* follows it (p. 112). A language may have several strategies with different phrase-type coverage, as in Fijian *kei* for NPs and *ka* for the other categories (p. 112).

Left out, as stated:

- Comitative ("WITH") coordination, taken to be a separate phenomenon with adjunct syntax (fn. 2, p. 110).
- Non-constituent coordination and the interaction of syncretism with coordination (fn. 1, p. 110).
- Adversative ("but") coordination, correlative conjunctions ("both ... and"), gapping (p. 127).
- Phonological marking as a separate kind: vowel lengthening as in Telugu is treated as a spelling-changing morphological rule, and intonation is ignored because orthographies do not show it (p. 111).
- Agreement resolution on coordinated NPs. It is discussed as motivation (pp. 114–115) and no implementation is described.
- The form covers less than the type library: infixes, reduplication, other complex morphology, and variant marking patterns can be written by hand on top of the Matrix types and cannot be selected in the form (p. 113).
- Coordination of unlike categories: the Web interface "only outputs strategies that cover single phrase types", although the types do not require this (p. 117).

### The analysis (Question 2)

**Rule types.** `coord-phrase` is a subtype of `binary-phrase` and is headless; it has daughters LCOORD-DTR and RCOORD-DTR. `topormid-coord-phrase` is below it, with subtypes `top-coord-rule` ([COORD −]) and `mid-coord-rule` ([COORD +]). `bottom-coord-phrase` is a separate subtype of `phrase` with daughters CONJ-DTR and NONCONJ-DTR and subtypes `unary-bottom-coord-rule` and `binary-bottom-coord-rule` ((17)–(20), p. 117; (33), p. 121; (36), p. 122). All lexical items and ordinary phrase structure and lexical rules are [COORD −] (p. 116).

**Rule schemata per pattern**, with the COORD value in parentheses:

| Pattern | Rules | Source |
|---|---|---|
| Monosyndeton | T(−) → XP(−) XP(+); M(+) → XP(−) XP(+); B(+) → conj XP(−) | (21), p. 118 |
| Polysyndeton | T(−) → XP(−) XP(+); B(+) → conj XP(−) | (23), p. 118 |
| Asyndeton | T(−) → XP(−) XP(+); B(+) → XP(−) | (24), p. 118 |
| Omnisyndeton (final version) | T(−) → L(−) XP(+); M(+) → L(−) XP(+); B(+) → conj XP(−) | (38), p. 123 |

Polysyndeton and asyndeton have no mid rule, so top and bottom alternate, which forces the right number of marks ((25), (26), pp. 118–119). The omnisyndeton schema (27) on p. 119, with bottom phrases as left daughters, is a first version that the semantics section replaces: the left daughters become "left" phrases, a new kind of bottom phrase with the usual semantics, and the rightmost bottom phrase takes a homophonous, semantically empty conjunction or morpheme (pp. 122–123). The paper gives no schema for the left phrase itself; tree (39) shows it as conj XP(−) with COORD − on the mother (p. 123).

**Binary by engineering argument.** The paper declines to review the theoretical debate and gives two reasons (pp. 114–115): the LKB has no rules with an underspecified number of daughters, so a flat analysis needs one rule per arity; and feature "promotion" (French gender, person resolution) multiplies rules, which is cheaper when there are few rules to begin with, and only top and mid rules need duplicating.

**Rules per strategy and phrase type.** Rules are category-specific by design (Section 3.1, pp. 113–114). One strategy for one phrase type gets three rules under monosyndeton (top, mid, bottom) and two under polysyndeton or asyndeton (top, bottom) (pp. 116, 118, 123–124). For omnisyndeton the paper names top, mid, bottom, and left phrases, which I count as four rule types; the paper does not give the count or the output for this case.

**Category of the coordinate phrase.** The mother's MOD and VAL are identified with those of both daughters ((17), p. 117). HEAD values are deliberately left unidentified, between the daughters and between daughter and mother: features such as AUX and AGR sit in HEAD and differ across coordinands, and languages coordinate unlike categories. The phrase-specific rules "stipulate matching HEAD values" (p. 114; pp. 117–118). A string-valued COORD-STRAT feature keeps the rules of one strategy from combining with those of another strategy for the same phrase type (fn. 8, p. 123).

**Semantics.** A coordination relation has LBL, C-ARG, L-HNDL, L-INDEX, R-HNDL, R-INDEX ((29), p. 120). A new feature COORD-REL on `local-min` holds the relation a phrase contributes (p. 120). The bottom phrase supplies the relation and leaves its arguments open: the binary bottom rule takes it from the KEYREL of the conjunction (`conj-lex`) and has empty C-CONT RELS; the unary bottom rule introduces it in its own C-CONT RELS; in both the bottom phrase's INDEX is that of the coordinand ((34), (35), p. 121). The top or mid rule above fills the arguments: its C-CONT LTOP and INDEX are the LBL and C-ARG of the right daughter's COORD-REL, and L-INDEX and R-INDEX are the indices of the left and right daughters ((31), p. 121). A mid phrase has an `implicit-coord-rel` as its own COORD-REL ((32), p. 121), so n coordinands yield a right-branching chain of n − 1 relations ((30), p. 120). The coordinate phrase gets a new index; since nominal indices must be bound, NP coordination rules introduce a quantifier, and NOM coordination rules introduce quantifiers for each coordinand (p. 114). Handles are left unconstrained in the generic types because an NP's handle is that of its quantifier; non-NP types identify them through `event-coord-phrase`, which is not shown (fn. 7, p. 120).

**Number of coordinands.** It is unbounded through recursion: the mid rule iterates under monosyndeton and omnisyndeton, and the top–bottom pair recurses under polysyndeton and asyndeton ((16), p. 116; (25), (26), pp. 118–119).

### From answers to grammar code (Question 3)

Software on the web server checks the answers for consistency (for a lexical strategy the orthography must be given) and produces a starter grammar (p. 113). For each strategy it emits rule types that each inherit from one syntactic Matrix type (marking pattern) and one semantic Matrix type (phrase type), plus a COORD-STRAT value. The English-like monosyndeton NP strategy in (40), p. 124, is three definitions of three lines each: `np1-top-coord-rule := basic-np-top-coord-rule & monopoly-top-coord-rule & [ SYNSEM.LOCAL.COORD-STRAT "1" ]`, the parallel mid rule, and `np1-bottom-coord-rule := conj-first-bottom-coord-rule & np-bottom-coord-phrase & [ SYNSEM.LOCAL.COORD-STRAT "1" ]`.

What this shows about the design:

- **Parameterized:** which of a small closed set of pattern types a rule inherits from, which phrase-type type, the position of the mark (visible in the supertype name `conj-first-bottom-coord-rule`), the spelling of the mark, and a strategy identifier.
- **Fixed in the core library:** the top/mid/bottom architecture, right branching, headlessness, the COORD and COORD-REL features, the semantic composition, and the phrase-type-specific semantic types such as `basic-np-top-coord-rule`. The syntactic pattern types listed are `monopoly-top-coord-rule`, `monopoly-mid-coord-rule`, `apoly-top-coord-rule`, `omni-top-coord-rule`, `omni-mid-coord-rule`, `unary-bottom-coord-rule`, `binary-bottom-coord-rule` (p. 123).
- **Interaction with the rest of the core:** the module adds features to a core type (`local-min`) and adds constraints to "types high in the hierarchy" so that everything outside coordination is [COORD −] (p. 116). The module is therefore an extension of the shared type hierarchy and cannot be a self-contained file of rules.
- **Hand extension is the intended escape route.** The Ono VP strategy (Section 5, pp. 124–125) is outside the form: non-final verbs carry a "medial" inflection and the last is unmarked. It is built from the asyndeton types (top rule and unary bottom rule) plus an assumed boolean head feature MEDIAL, + on the left daughter and − on the right daughter of the top rule, with VFORM and TAM shared among mother and daughters ((43), p. 125).

### Testing (Question 4)

No evaluation is reported: no test suites, no coverage or overgeneration figures. The only statements are the acknowledgment that students in Linguistics 567, Spring 2005, tested the module in their grammars (footnote on p. 109, no languages or results given) and the sketch of Ono NP and VP coordination, which is described as an analysis and for which no run is reported (pp. 124–125). Testing coverage "in implemented grammars for a diverse range of languages" is listed as a next step (p. 127). The examples from Abelam, Kanuri, Telugu, Latin, and Fijian illustrate the typology and are not test data (pp. 111–112).

### Limitations, predictions, future work (Question 5)

- A language that marks only the first coordinand ("conj A B C") is not naturally accommodated; the pattern is reported as unattested (Stassen 2000), and left-branching versions of the rules would cover it (pp. 125–126, fn. 9).
- Some nodes "do not necessarily correspond to constituents", and the omnisyndeton rules select a daughter by phrase type, which the authors call unusual for HPSG (p. 126).
- Monosyndeton types also license polysyndeton (`monopoly-`, p. 123), matching the observation that monosyndeton languages seem always to allow it (p. 126).
- Mono-, poly-, and asyndeton strategies get multiple structures, [[A conj B] conj C] and [A conj [B conj C]]; omnisyndeton does not, and whether "conjunction stacking" occurs is left open (p. 126).
- Possibly wrong prediction: flat, left-branching, and right-branching readings of "A and B and C" may all exist, and the analysis cannot distinguish flat from right-branching (p. 126).
- The set-based treatment of feature resolution is unavailable in the LKB (fn. 5, p. 115; the citation in the footnote has lost its authors in the source, and the reference list suggests Dalrymple and Kaplan 2000).
- Future work: testing on diverse languages, a better user interface, and the phenomena listed under "Left out" above (p. 127).

## Caveats for the parser

### 1. The label inventory for coordination multiplies by strategy, phrase type, and position in the chain (high; tagger label inventory, grammar core)

Rule names in a customized grammar have the shape `np1-top-coord-rule` (p. 124): phrase type, strategy number, and top/mid/bottom. A language with two strategies over five phrase types has on the order of thirty coordination rule names (my arithmetic from pp. 118 and 123). The names are also grammar-internal: "np1" in one grammar and "np1" in another need not be the same strategy. A tagger that names the rule at each node needs either this full product per language or a factored label (role in the chain, pattern, phrase type) that our own core could define once. The paper's two-parent inheritance (one syntactic type, one semantic type, p. 123) is already that factoring at the type level.

### 2. Asyndeton puts unary nodes with no surface evidence into the tree (high; deterministic replay, tagger)

Under asyndeton every non-initial coordinand, or the remaining coordination, sits under a unary bottom rule, and top and bottom alternate, so a three-way coordination contains a unary node directly above a top node ((26), p. 119; the Ono tree (44), p. 125). No token signals these unary steps. The tagger must predict a coordination-specific unary rule on a constituent whose words look like any other XP. The paper does not discuss the ambiguity this adds for juxtaposed phrases in general.

### 3. The same string has several derivations with different semantics, and the flat reading is not separate (high; treebank policy, tagger targets)

For mono-, poly-, and asyndeton the grammar licenses both groupings in (45) (p. 126). Under polysyndeton the chain in (25) (p. 119) is at once the n-way structure and the right-nested structure, which is the conflation the authors flag in (47) (p. 126). Training derivations therefore need a stated convention for which structure is the default. The paper says the right-branching structure is treated as unmarked (p. 126) and gives no disambiguation policy.

### 4. Mid and bottom nodes are not constituents (medium; UD bridge, evaluation)

"conj XP" and "XP [conj XP]" are nodes in every tree, and the authors say such nodes need not correspond to constituents (p. 126). Bracket-based comparison with other treebanks, and conversion to dependencies, must treat the chain as one n-ary coordination. The conjunction is a sister of the last coordinand inside the bottom phrase, which matches the attachment of `cc` in UD for mark-before languages; this comparison is mine.

### 5. Rule counts per coordination vary with the pattern (medium; tagger)

For n coordinands, monosyndeton yields one top, n − 2 mid, and one bottom node; polysyndeton and asyndeton yield n − 1 top and n − 1 bottom nodes; omnisyndeton yields one top, n − 2 mid, n − 1 left, and one bottom node (my counts from (16), (25), (26), (39), pp. 116, 119, 123). A label scheme that attaches chain labels to tokens has to carry a variable number of labels on the coordinands.

### 6. Omnisyndeton needs two homophonous conjunction entries (medium; lexical tagging)

The rightmost mark is a semantically empty item with the same spelling as the contentful one (p. 122). A lexical tagger must choose between two entries for the same form by position in the coordination.

### 7. With a morphological mark, the tree does not show the mark at the coordination rules (medium; replay)

When the mark is an affix the bottom rule is unary (p. 116), and in the Ono case the constraint is a head feature required of the top rule's left daughter (p. 125). The evidence for coordination is then inside a word's lexical rule chain, and the phrasal rules above it look like asyndeton. The paper does not show the lexical rule or how the Web form output connects an affix to the unary bottom rule.

### 8. The module changes core types (medium; design of our grammar core)

COORD and COORD-REL are added to `local-min`, and [COORD −] is added high in the hierarchy for all lexical items and ordinary rules (pp. 116, 120). In a typed specification of our own, a module must be able to declare such additions to shared types explicitly, so that the effect of switching a module on is inspectable and testable.

## Support for the design

- **Unary and binary rules suffice.** Unbounded coordination is expressed with binary top and mid rules and a unary or binary bottom rule; no rule has more than two daughters (pp. 115–116). The argument for this is an engineering one that applies to any system with fixed-arity rules (pp. 114–115).
- **Every leaf is a word.** No empty conjunction is posited for asyndeton; the unary rule introduces the relation in C-CONT ((34), p. 121).
- **Semantics is independent of the marking strategy.** All strategies produce the same chain of relations, which also allows generation with a different strategy from the one parsed (p. 122). An underspecified semantic level can treat coordination uniformly across languages.
- **A small closed parameter space with a hand-written escape.** Five questions per strategy select among a few library types (p. 113), and the same types support unlisted strategies by hand (Ono, pp. 124–125). This is the pattern of a typed choice plus an extension point.
- **Factoring by inheritance.** Marking pattern and phrase type are independent supertypes combined per rule (p. 123). The generated code is nine lines for a strategy ((40), p. 124), so the exported TDL can stay readable.
- **Coordination was prioritized for coverage reasons.** Coordinated phrases have "relatively high text frequency" (p. 109).

## Theory strains

- **Flat versus binary coordination.** Acknowledged as a matter of "much theoretical debate" and decided on engineering grounds (p. 114).
- **Headedness.** The rules are headless to avoid "an unwarranted typological generalization", with Borsley 2005 cited against headed analyses (p. 117 and fn. 6).
- **Like-category coordination as stipulation.** Identity of HEAD is given up because HEAD holds AUX and AGR; matching is stipulated per phrase type (pp. 113–114, 117–118). The generalization that like categories coordinate is thus restated once per category.
- **Selection by phrase type.** The omnisyndeton rules require a particular daughter type, "certainly not 'head-driven'" (p. 126).
- **Feature resolution.** Agreement promotion requires duplicated rule subtypes in the absence of a set-based mechanism (p. 115 and fn. 5).
- **Flat versus right-branching meaning.** The authors suspect a missing reading (p. 126).

## Key primary sources

- Flickinger 2000 and the English Resource Grammar (version of 10/04), the source of the top/mid/bottom analysis (pp. 109, 115).
- Bender, Flickinger and Oepen 2002, The Grammar Matrix.
- Bender and Flickinger 2005, Rapid prototyping of scalable grammars (the notion of a Matrix module).
- Drellishak 2004, A survey of coordination strategies in the world's languages (MA thesis; phrase-type coverage).
- Stassen 2000, AND-languages and WITH-languages.
- Payne 1985, Complex phrases and complex sentences.
- Abeillé 2003; Borsley 2005 (structure and headedness of coordination).
- Beavers and Sag 2004; Dalrymple and Kaplan 2000 (non-constituent coordination; feature resolution).
- Phinnemore 1988, Coordination in Ono.
- Copestake et al. 2003, Minimal Recursion Semantics.

## Not covered here

These are my remarks, not statements from the paper.

- **Gaps in what the paper shows.** It does not show where the mid phrase's `implicit-coord-rel` enters RELS, where the predicate of the relation comes from under asyndeton or affixal marking, the definition of the left phrase, the phrase-type semantic types (`basic-np-top-coord-rule` and the quantifier it introduces), `event-coord-phrase`, the definition of `conj-lex`, or the output of the Web form for affixal, mark-after, and omnisyndeton strategies. The list of types on p. 123 names `np-bottom-coord-rule`, while (40) on p. 124 inherits from `np-bottom-coord-phrase` and `conj-first-bottom-coord-rule`; the paper does not reconcile the names.
- **An inconsistency in (37).** As printed on p. 122, the first `_and_coord_rel` pairs L-HNDL with the left conjunct's LBL and L-INDEX with its ARG0, and the second pairs L-INDEX with an LBL tag and L-HNDL with an ARG0 tag. Both relations are also printed as `_and_coord_rel`, where the text on p. 120 would give `implicit-coord-rel` for the upper one in a strategy with a mid rule. The paper introduces (37) as "something like" the representation. I read the second relation's labels as a typesetting slip; this is unverified.
- **This is the 2005 design.** Later versions of the Matrix customization system may differ in rule names, in the omnisyndeton treatment, and in agreement handling. Nothing here was checked against current Matrix code, by project decision.
- **Comparison with the ERG derivations is still to do.** The ERG's coordination rule names in the Redwoods derivations were not compared with the top/mid/bottom scheme in this reading. That comparison would say whether one factored label set can serve both the ERG and grammars generated from our own core.
- **Design consequence for our core.** Coordination is a case for defining the node label as a tuple (chain role, marking pattern, phrase type) in the grammar specification and deriving the TDL rule name from it, so that the tagger's label space is shared across languages. This is an inference from caveat 1, and it needs a decision record before it is adopted.
- **Tests.** The paper has none, so it gives no model for the tested modules we want. The four patterns times word/affix times before/after give a small grid from which per-strategy positive and negative test items could be generated (for example, the wrong number of marks under polysyndeton); the grid is mine.
