# Sag (2003): Coordination and underspecification

Ivan A. Sag, "Coordination and Underspecification", chapter 14 in *The Proceedings of the 9th International Conference on HPSG*, edited by Jong-Bok Kim and Stephen Wechsler, © 2003 Stanford University, pp. 267–291 (title page footer, p. 267; references end on p. 291). Read from `reading/txt/sag-coordination.txt` (text layer of `reading/sag-coordination.pdf`, 25 pages, produced May 2003). The running prose in the text layer is clean. Trees, type hierarchies, and rule boxes are garbled there (tags such as boxed 0, 1, n lose their boxes; hierarchies lose their lines; Polish diacritics break), so examples (7), (9), (10), (11), (12), (16), (20), (21), (30), (31), (32), (36), (39), (44), (47), and (51)–(54) were checked against the PDF page images (PDF pages 1–22, which are printed pages 267–288). Everything quoted or reconstructed below was checked on the page image. Printed page numbers are used throughout. Read 2026-11-20.

Question for this reading: what analysis of coordination of unlikes and of syncretism does the paper propose, and can a plain unifier replay it? What does it imply for labels and for a derivation tree with unary and binary rules?

## Summary

The paper addresses one problem: what feature structure the mother of a coordinate structure has when the conjuncts differ in category, AUX value, selected case, or the case or verb form of a shared gap (examples (1)–(6), pp. 267–268). Its proposal is a change to the foundations of HPSG and a set of constraint schemas that exploit it. Feature structures keep the requirement of being totally well-typed and drop the requirement of being sort-resolved, so the value of a feature may be a nonmaximal type (p. 274). Selectors impose a lower bound on the type of some feature of an argument; the arguments fix the value or impose an upper bound (p. 274). Bounds are written with ≤, where "is less than" means "is a supertype of" (p. 275).

Two formulations of the general coordination rule are given, both flat, with the conjunction as a sister of the conjuncts before the last one. In the ≤-based rule (16) the mother's HEAD value is ≤ the HEAD value of every conjunct, and VAL is identical on the mother and all conjuncts (p. 275). In the =-based rule (20) both HEAD and VAL are identical on mother and conjuncts, and the lexical entries carry upper bounds instead of fixed values (p. 277). A separate NP coordination rule (31) makes the mother plural, identifies CAT across mother and conjuncts, and requires each conjunct's PER value to be ≤ the mother's in the hierarchy *3rd* above *2nd* above *1st* (p. 281).

The type hierarchy carries the work. Disjunctive (nonmaximal) types such as *nominal* over *noun* and *adj* are the possible categories of coordinations of unlikes (12, p. 274). Conjunctive types such as *a&d* below *acc* and *dat* are the values that syncretic forms can take (21, p. 278). Both kinds are posited only where a language motivates them (pp. 274, 278). The paper applies the scheme to unlike-category coordination and Jacobson's puzzle (pp. 274–277), German case syncretism (pp. 278–283), English AUX (p. 284), English right node raising with a syncretic verb form (pp. 284–285), and Polish case (pp. 285–288). It reviews and argues against the complexity of Levy (2001), Levy and Pollard (2001), and Daniels (2001) (pp. 270–272). The author presents the whole as an exploration ("I want to consider what may be a simpler way", p. 273) and flags several points as unresolved.

### The constraints, stated precisely

- **Bounding notation** (p. 275). `[HEAD = [1], nominal ≤ [1]]` says the value is *nominal* or one of its subtypes. `[HEAD = nominal]` fixes the value as the nonmaximal type *nominal* itself. `[1] ≤ adj` says the value is *adj* or one of its supertypes.
- **General Coordination Rule, ≤-based** (16, p. 275): `[HEAD = [0], VAL = [V]] → [HEAD = [1], VAL = [V]] ... [HEAD = [n−1], VAL = [V]] CNJ [HEAD = [n], VAL = [V]]`, where `[0] ≤ [1]`, ..., `[0] ≤ [n]`. Described as a "simplified rule" for constituent coordination other than NP coordination, blending Shieber (1992) and Daniels (2001).
- **General Coordination Rule, =-based** (20, p. 277): the same shape with HEAD = [0] and VAL = [1] on the mother and on every conjunct. Footnote 11 (p. 278) adds that this version might be simplified further by identifying the whole CATEGORY, LOCAL, or SYNTAX value, which the ≤-based version does not allow.
- **NP Coordination Rule** (31, p. 281): mother `NP[NUM = pl, PER = [0], CAT = [C]]`; conjuncts `NP[PER = [i], CAT = [C]]` with CNJ before the last; `[i] ≤ [0]` for every conjunct. With hierarchy (32) the mother's person is the most specific person among the conjuncts (p. 282). CAT identity forces all NP conjuncts to have the same CASE value (p. 282).
- **Root condition** (30, p. 280): a feature structure F is a stand-alone utterance if it satisfies all constraints of the grammar and a root description (finite, empty SUBJ, COMPS, SLASH), "and there is no F′ more general than F that also satisfies 1 and 2".

### How each phenomenon comes out

- **Unlike categories.** *become*, *remain*: `COMPS ⟨[HEAD = [1], nominal ≤ [1]]⟩`; *wealthy* is *adj*, *a Republican* is *noun*; the coordination has `HEAD = nominal` (17, p. 276). Jacobson's puzzle: *grew* requires *adj*; since VAL is identified in coordination, *grew and remained* requires *adj*, and *wealthy and a Republican*, being *nominal*, is excluded (18, p. 276). Three variants (fixed lexical values with the ≤ rule; upper-bounded lexical values with the ≤ rule; upper-bounded lexical values with the = rule) are said to be empirically indistinguishable for English (p. 277).
- **German case syncretism.** With the =-based rule: *findet* requires `acc ≤ [1]`, *hilft* requires `dat ≤ [1]` (22–23, p. 278). *findet und hilft* therefore requires an object whose case is *a&d* (27, p. 279). *Frauen* has no case restriction and can resolve to *a&d*. *Männer* carries `¬(dat ≤ [1])` and *Kindern* carries `[1] ≤ dat` (24, p. 278), so neither fits. Unambiguous words carry an upper bound (26, p. 279). Case identity inside the NP (36, p. 283) excludes *die/den Frauen* after *findet und hilft* (37c, p. 283).
- **AUX.** *likes*: `[1] ≤ −`; *is*: `[1] ≤ +`; the coordinate VP has `AUX = bool` (42, p. 284). Other HEAD features such as VFORM must still agree (p. 284).
- **Person resolution.** Handled by the ≤ condition of rule (31) over hierarchy (32); the author notes that < here corresponds to the subset relation of Dalrymple and Kaplan (2000) (fn. 15, p. 282).
- **Polish.** Hierarchy (47) has disjunctive types *n∨a*, *a∨g*, *g∨d* above the four cases and conjunctive types *n&a*, *a&g*, *g&d* below them (p. 286). *kogo* is `[1] ≤ a&g`, *co* is `[1] ≤ n&a` (49, p. 286). Coordinated clauses with gaps bounded by *acc* and *gen* yield `SLASH = {[CASE = a&g]}` on the coordinate clause, so only *kogo* can be the filler (50, p. 286). Unlike-case NP coordination *wina i całą świnię* gets `CASE = a∨g` because *dajcie* bounds its object by *a∨g* (52, p. 287).

## Caveats for the parser

### 1. The analysis uses constraints that a plain unifier does not have (high; deterministic replay)

The lower bound a selector imposes (`nominal ≤ [1]`) is what unifying with the type *nominal* already does in an engine that allows nonmaximal types. The other devices are different in kind. An upper bound (`[1] ≤ adj`, (19), p. 277; (24b), (26), pp. 278–279) requires the value to stay at or above a type, which unification cannot enforce, since unification only moves a value down the hierarchy. Fixing a value at a nonmaximal type (`[HEAD = nominal]`, p. 275) is the same kind of constraint. The ≤-based rule (16) relates the mother's HEAD to each conjunct's HEAD by subsumption, with no token identity (p. 275). The entry for *Männer* uses a negated bound, `¬(dat ≤ [1])` (24a, p. 278). The root condition (30) quantifies over other feature structures ("there is no F′ more general than F", p. 280), and the author himself raises the objection that this leaves model-theoretic grammar (p. 281). The paper uses no set-valued category features, no explicit generalization operation, no disjunction in the grammar, and no defaults in the main analysis; the membership statements in (28)–(29) (pp. 279–280) describe the space of solutions and are not constraints of the grammar. A default *nom* is mentioned once as an alternative for a Polish problem (fn. 10, p. 277). The statement that the unifier lacks these devices is my reading of the constraints against our engine; the paper does not discuss implementation.

### 2. The intended value is found by minimization over solutions (high; deterministic replay)

Without the root condition, *findet Frauen* has four case values and *findet Männer* three (28–29, pp. 279–280). The paper offers two remedies and chooses neither firmly: treat feature structures that differ only in contiguous types as one equivalence class (Ken Shan's suggestion), or keep only most general satisfiers at the root (30) (p. 280). Footnote 13 (p. 281) adds that a most general satisfier need not be unique unless any two compatible types have a unique ≤ bound, and that there are "further issues here having to do with set-valued features" left outside the paper. A replay engine built on this analysis would return a region of the hierarchy for some values, and a further step would pick the representative.

### 3. The coordination rules are flat and n-ary (high; rule inventory, tree shape)

Rules (16), (20), and (31) have any number of conjunct daughters, with CNJ as a daughter of the coordinate mother placed before the last conjunct (pp. 275, 277, 281). The conjunction does not form a constituent with a conjunct. The GPSG tree (7) has the same ternary shape, NP CNJ AP (p. 269). The paper says nothing about binary alternatives, about conjunctions that appear before every conjunct, or about asyndetic coordination. A derivation tree limited to unary and binary rules needs a binarization of this rule, and the paper gives no guidance on where the bounds or identities would be checked in intermediate nodes.

### 4. The category of a coordination of unlikes depends on its context (medium; labels)

Under the ≤-based rule the conjuncts alone only bound the mother's HEAD from one side: for *wealthy and a Republican* the mother is ≤ *adj* and ≤ *noun*, and it is the selector *become* that requires *nominal* ≤ the value, giving *nominal* (17, p. 276). The uniqueness claim on p. 276 ("at most one feature structure model") is made for whole examples. The inference that the phrase in isolation is not fixed (it could be *nominal* or *pos*) is mine. For a tagger this means a label for the coordinate node cannot be read off the conjunct categories alone under this analysis.

### 5. Every kind of unlike coordination needs its own supertype (medium; type hierarchy, coverage)

Footnote 9 (p. 276) says each different kind of unlike-category coordination "would motivate positing a new supertype", and that the data have not all been considered. Conjunctive types are likewise posited per attested syncretism (p. 278). A grammar built this way has a hierarchy whose shape records which coordinations and syncretisms occur in the language, and a missing type makes an attested coordination unparsable.

### 6. Syncretic and unambiguous words have different kinds of lexical constraint (medium; lexical types)

Under the =-based rule an unambiguous form carries an upper bound and a fully syncretic form such as *Frauen* carries no case constraint (p. 279). A partly syncretic form carries a bound by a conjunctive type (*set*: `[1] ≤ pfp&bse`, (45a), p. 285; *kogo*, (49), p. 286) or a negated bound (*Männer*, p. 278). Lexical types that a tagger predicts would have to encode which of these a form has.

### 7. Identity of VAL is the strong condition (low; useful constraint)

Both rule versions identify VAL across all conjuncts and the mother (pp. 275, 277), so conjuncts must have the same remaining valence, and coordinated selectors pool their requirements on the shared argument (18, p. 276; 27, p. 279). The rules as written mention only HEAD and VAL; the SLASH sharing used for across-the-board extraction in (50) (p. 286) is assumed and not written into a rule.

## Support for the design

- **One description, one structure.** The author's premise is that the grammars people actually write give, for each reading of a string, one intended feature structure, with ambiguity always showing up as distinct descriptions (pp. 273–274). This is the property replay depends on. The paper names quantifier storage as the one exception in Pollard and Sag 1994 and points to MRS as its removal (p. 273).
- **Nonmaximal types as values.** The foundational change (p. 274) is how DELPH-IN-style engines already behave: values are types anywhere in the hierarchy. The second half of this sentence is my remark.
- **Coordination needs no empty elements and no extra structure in this account.** Every example is handled with one coordinate node over the conjuncts and the conjunction (pp. 275–287).
- **Selection is local and lexical.** The selector's bound on one feature of its argument does the work in all five case studies (p. 274), so the information a label has to carry sits on the selecting word and on the form of the selected word.
- **Agreement inside the conjunct is ordinary identity.** Case concord within each NP conjunct is plain structure sharing (36, p. 283), and it is what rules out (37c) and (54) (pp. 283, 287–288).

## Theory strains

- **≤-based versus =-based coordination.** Three variants are declared indistinguishable on English evidence (p. 277). The =-based rule is chosen for German "because it allows for a simpler formulation of relevant constraints" (p. 278).
- **Spurious ambiguity.** Two remedies, neither adopted outright; the author is "not sure what undesirable consequences (if any)" the equivalence-class remedy has (p. 280), and defends the most-general-satisfier remedy against the model-theoretic objection (p. 281).
- **Person hierarchy conflict, flagged as unresolved.** The right node raising example *weil wir das Haus und die Müllers den Garten kaufen* seems to need a type neutral between first and third person, hierarchy (39), which is "inconsistent with the one in (32)"; "At present, I can only flag this as an unresolved issue" (pp. 283–284).
- **Right node raising has no analysis here.** "I'm really not sure how to analyze right node raising examples like this" (p. 283); "there is uncertainty about how to analyze the right node raising construction" (p. 285). The VFORM account of *set* is conditional on an analysis in which one feature value must satisfy both governing verbs and the raised VP's head (p. 285).
- **Case across unlike categories.** A Polish example coordinating a CP with a nominative NP may require case to be visible on CPs, or *nom* as a default; the author is "not at all sure that case has to be transmitted across unlike category coordination" (fn. 10, p. 277).
- **Case in English pronoun conjuncts.** Judgments on *Him and me left*, *They invited Kim and I* are from "only a cursory exploration" of the dialects (p. 282).
- **Number of coordinate NPs.** Plural is stipulated; NPs coordinated with *or* are set aside (fn. 14, p. 281).
- **How far to relax the foundations.** Dropping total well-typedness as well is left open (p. 288).
- **Coordination of unlikes as ellipsis.** Footnote 16 (p. 288) records Jim Blevins's suggestion that examples like (1) are VP coordination in which only the first conjunct's lexical head is pronounced, a discontinuous-dependency analysis that would remove the unlike-category problem.
- **Apparent slips in the text.** P. 281 says "we have abandoned only the condition that feature structures must be totally well-typed", while p. 274 and p. 288 say the abandoned condition is sort-resolution. (46b) (p. 285) uses *psp* where (44) and (45) use *pfp*. Example (1) is *wealthy and a Republican* while the GPSG tree (7) shows *a Republican and proud of it* (pp. 267, 269). These identifications are mine.

## Key primary sources

- Sag, Gazdar, Wasow and Weisler 1985, Coordination and how to distinguish categories (the GPSG intersection analysis; person resolution).
- Jacobson 1987, review of Gazdar et al. 1985 (the *grew and remained* puzzle).
- Bayer 1996, The coordination of unlike categories; Bayer and Johnson 1995, Features and agreement (Type Logical analysis with conjunctive and disjunctive categories).
- Ingria 1990, The limits of unification; Zaenen and Karttunen 1984; Pullum and Zwicky 1986 (the neutralization data).
- Dalrymple and Kaplan 2000, Feature indeterminacy and feature resolution (set-valued features in LFG).
- Levy 2001; Levy and Pollard 2001; Daniels 2001 (HPSG analyses with sort-resolved structures).
- Levine, Hukari and Calcagno 2001 (the hierarchy the HPSG proposals build on).
- Shieber 1992, Constraint-Based Grammar Formalisms (source of the ≤-based rule's approach).
- Dyła 1984; Przepiórkowski 1999 (Polish data).

## What it argues against, and the evidence

- **GPSG intersection of feature specifications** (Sag et al. 1985; Gazdar et al. 1985). Jacobson's contrasts (8) decide: intersection predicts that *grew and remained* imposes only the weaker requirement of *remained*, so *\*grew and remained a Republican* and *\*grew and remained wealthy and a Republican* would be accepted (p. 269).
- **Levy 2001, Levy and Pollard 2001, Daniels 2001.** The argument is about complexity; no data are claimed to decide. Levy and Pollard need a second lattice, with 18 maximal types for three pure cases (10, pp. 270–271). Daniels keeps one hierarchy with pure and non-pure types (11, p. 272). The paper quotes Levy and Pollard on the underlying hierarchy having 127 nodes for three cases and 32,767 for four (p. 272). The author keeps their insights (lower bounds from selectors, conjunctive types for syncretism, one hierarchy as in Daniels) and drops sort-resolution (pp. 274–275).
- **Bayer and Johnson's Type Logical analysis** is treated as the source of the insight; the paper declines only its fully expanded Boolean category space (p. 274).
- **The foundational assumption of sort-resolved models** (King 1989, 1994; Pollard and Sag 1994) is the main target (pp. 273–274, 288).

## Not covered here

These are my remarks, not statements from the paper.

- **The paper is about the category of the mother, not about structure.** It gives no argument for flat over binary coordinate structure, says nothing about the semantics of coordination, and does not treat gapping, argument-cluster coordination, or ellipsis. Right node raising appears only as data whose analysis is declared uncertain (pp. 283, 285, 287), and across-the-board extraction only through shared SLASH (p. 286). Ellipsis appears only in footnote 16.
- **The ERG does not use this structure.** In the Redwoods training derivations (`analysis/derivation-stats/train-phrasal_rule.tsv`) coordination is binary: `mrk-nh_*` rules (for example `mrk-nh_nom_c`, 15,654; `mrk-nh_evnt_c`, 11,189; `mrk-nh_cl_c`, 9,483) and category-pair rules with suffixes `-t`, `-m`, `-im` (for example `np-np_crd-t_c`, 15,715; `cl-cl_crd-t_c`, 5,678; `vp-vp_crd-fin-t_c`, 4,017; `np-np_crd-m_c`, 2,341). The names suggest that the conjunction first combines with the conjunct to its right and that the result then combines with the conjuncts to its left, one at a time. I have not read these rules in the ERG's TDL, so this reading of the names is unverified.
- **The ERG appears to handle unlikes by rule inventory.** There are rules whose names pair different categories (`j-n_crd-t_c`, 166; `n-j_crd-t_c`, 164; `jpr-vpr_crd-t_c`, 81) and rules for predicative phrases of any category (`vppr-vppr_crd-t_c`, 1,007; `ppr-ppr_crd-t_c`, 76). If the names mean what they suggest, the choice that Sag's analysis leaves to the type hierarchy is a choice among rule names for our tagger, which fits the observation that coordination rules are often confused. Unverified in the TDL.
- **What a plain unifier can keep from this paper.** Conjunctive types as greatest lower bounds are ordinary: unifying *acc* and *dat* gives *a&d* if the hierarchy has it. The upper bounds and the negated bound could be approximated by adding types (for example a supertype covering every case value compatible with a form), at the cost of a larger hierarchy, which is the cost the paper tries to avoid. This is a design conjecture and has not been tested.
- **Design consequence.** Under "one decision, one name", the decision "these conjuncts differ in category and the mother is neutral" needs a name in the derivation, since a plain unifier cannot compute the neutral value as this paper's ≤ rule does.
- The 2002 conference date and place are not stated in the document; the title page gives only the proceedings title, editors, and the 2003 copyright.
