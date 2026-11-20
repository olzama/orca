# Copestake (2007): Semantic composition with (Robust) Minimal Recursion Semantics

Ann Copestake, "Semantic composition with (Robust) Minimal Recursion Semantics", *Proceedings of the ACL 2007 Workshop on Deep Linguistic Processing*, Prague, Czech Republic, June 2007, pp. 73–80, Association for Computational Linguistics. Identity taken from the title block and the footer of the first page of the file (p. 73); the page numbers 73–80 are printed on the pages. Read from `Copestake_MRS_algebra_2007.pdf` (8 PDF pages; PDF page = printed page − 72). Read in full from the text layer (`txt/Copestake_MRS_algebra_2007.txt`), and all eight pages were also read as page images. The text layer is good for the prose. It drops the underscores in predicate names (`_sit_v_1` appears as `sit v 1`), flattens subscripts (slot labels, `=q`, `e_past`, operation names), turns ≠ into `6=`, and interleaves the two columns around Figures 2 to 6. Every structure and formula quoted below was checked against the page images. Page numbers below are the printed ones. Read 2026-11-20.

Question for this reading: what is RMRS and what may it leave underspecified; how is it composed from shallow analyses and what does composition need per rule and per word; how does the paper treat what the 2001 algebra (Copestake, Lascarides and Flickinger, "CLF") left out; how does a shallow RMRS relate to the deep MRS of the same sentence; and which formal properties and limitations are stated?

## Summary

The paper is short and programmatic. It restates the CLF algebra in a slightly different vocabulary, repairs two gaps in it, shows that the same algebra composes RMRS, and then moves the slots and the argument relations from the lexical entries into the rules so that composition works with no subcategorization lexicon. The practical outcome is a semantic component for the RASP parser whose output is meant to be compatible with the ERG's (pp. 73, 80). There are no theorems and no evaluation figures.

**RMRS as defined here (Section 2, p. 74; Section 4, p. 77).** RMRS "uses the same approach to scope" as MRS, with labels on EPs and qeq constraints, and "adopts a variant of a neo-Davidsonian representation, where arguments (ARGs) are represented as distinct elements" (p. 74). An RMRS EP has a handle (its label), an anchor, a relation, and "up to one argument of the relation" (p. 77). The MRS EP `l1:chase(e,x,y)` becomes `l1:a1:chase(e), l1:a1:ARG1(x), l1:a1:ARG2(y)` (p. 77); for a quantifier, `RSTR` and `BODY` are split off in the same way (Figure 1, p. 74). What may be left underspecified:

- *Arguments.* An ARG may be absent altogether; "separating out ARGs from the EPs and allowing them to be omitted permits a straightforward notion of a specificity hierarchy in terms of information content" (p. 74).
- *Argument labels.* "ARGn indicates that there is some argument relationship, but it is unknown whether it is an ARG1, ARG2 or ARG3" (p. 74).
- *Predicates.* Relation names follow a convention that "allows them to be constructed without access to a lexicon": `_sit_v` carries only the coarse sense distinction available from the part of speech, a deep grammar gives `_sit_v_1`, "and there is an implicit hierarchy such that `_sit_v_1` is taken as being more specific than `_sit_v`" (p. 74).
- *Conjunction and scope constraints.* The RMRS from a POS tagger alone has no label equalities ("the conjunction information is not available from a POS tagger alone") and, in Figure 1, no qeqs and no variable equalities (p. 74).
- *Variable features.* Both MRS and RMRS "assume an inventory of features on variables which are used to represent tense etc, but these will not be discussed in this paper" (p. 74).

Figure 1 (p. 74) gives three structures for *the fat cat sat on a mat*: the MRS, the RMRS equivalent to it, and the tagger-only RMRS, which is seven EPs with distinct labels, anchors and variables: `l0:a0:_the_q(x0), l1:a1:_fat_j(x1), l2:a2:_cat_n(x2), l3:a3:_sit_v(e3), l4:a4:_on_p(e4), l5:a5:_a_q(x5), l6:a6:_mat_n(x6)`.

**Anchors (pp. 74, 77, 78).** "An EP and its associated ARGs share a unique anchor" (p. 74). The anchor is new in this paper; the 2003 RMRS design used an explicit binary conjunction symbol, the in-group or in-g (p. 77). The reasons given for dropping it: with binary in-g "the order of combination of intersective modifiers affects the semantic representation, though it has no effect on denotation"; an n-ary conjunction cannot be built compositionally with binary branching; redundant per-element conjunction relations give a spurious in-g when there is no modifier and do "not allow for incremental specialisation" (p. 77; the demonstration is omitted). With anchors, conjunction is label equality exactly as in MRS, and the anchor keeps each ARG attached to its own EP after labels have been equated (p. 74). A stated consequence: "RMRS and MRS TFS grammars can be essentially identical apart from lexical types" (p. 77). Current DELPH-IN grammars build MRSs, "which may be converted into RMRSs" (fn. 2, p. 77).

**The algebra restated (Section 2.1, pp. 74–75).** CLF's "holes" are called "slots". A SEMENT is `[l, i]{slots}[eps][hcons]{eqs}`; the hook has a label, an index and an external argument (omitted in the paper), and the slot labels are CLF's SUBJ, SPR, SPEC, COMP1, COMP2, COMP3 and MOD (pp. 74–75). Six principles (p. 75): a syntactically specified slot in the semantic head is filled by the other daughter's hook by adding equalities; the phrase's hook is the semantic head's hook; eps, eqs and hcons are appended; "the slots of the phrase are the unfilled slots of the daughters (although see below)". The assumption about syntax is minimal: "the syntax selects the appropriate op and its arguments for each application" (p. 75). Figure 2 (p. 76) composes *a cat* with op_spec; the determiner is "the semantic head (though not the syntactic head in the ERG)" (p. 75).

**Two repairs to CLF (Section 2.2, pp. 75–76).** "Unfortunately, CLF are imprecise about the algebra in several respects" (p. 75); two are treated.

1. *Slot propagation.* CLF's rule that every unfilled slot reappears on the mother under the same label "is inadequate for real grammars": the passive rule coindexes a COMP of the lexical sign with the SUBJ of the passive (pp. 75–76). Choosing op_subj or op_comp1 at the subject-head rule depending on whether the verb was passivized "would require non-local information" and would rule out an algebra checker (p. 76). The adopted solution is slot renaming: a unary operation op_comp1-subj with slot_subj(op_comp1-subj(a)) = slot_comp1(a) and all other slots unchanged. The inventory of operations grows, and "the choice of operation is then locally determinable from the rule" (p. 76).
2. *Optional complements.* An optional complement that is not realized is discharged by a construction: op_comp1(a1, a2), where a1 is the head, "the only daughter appearing in the TFS for the construction", and a2 "is stipulated by the rule to be `[l, d]{}[][]{}`, where d is the discourse-bound referent" (p. 76).

**Construction semantics (p. 75).** "The MRS approach requires that this can always be treated as equivalent to having an additional daughter in the rule. Thus construction semantics need not be considered separately in the formal algebra, although it does result in some syntactically binary rules being semantically ternary (and so on)." The example named is compound nouns.

**Non-lexicalist syntax with lexical slots (Section 3, pp. 76–77).** With a syntax-semantics interface that names the operations and their arguments per rule, the algebra implements composition for a context-free grammar. Figure 3 (p. 77): `VP -> Vditrans NP1 NP2` with `op_obj(op_iobj(Vditrans, NP1), NP2)`. This "still relies on the assumption that all slots are known for every lexical item: semantically the grammar is lexicalist even though it is not syntactically" (p. 76).

**RMRS with a deep grammar (Section 4, p. 77).** Hooks become triples `[l, a, i]`; the rels hold EPs and ARGs; "formally ARGs are EPs according to the definition above, so this requires no amendment of the algebra". Figure 4 (p. 78) is the RMRS version of *a cat*.

**RMRS with no lexicon (Section 5, pp. 77–78).** The target is RASP: tokenizer, POS tagger, lemmatizer, tag sequence grammar, statistical disambiguator (p. 77).

- *Words.* A "lexicon" of POS tags defines the EPs: `AT lexrel_q(x)`, `AT1 lexrel_q(x)`, `JJ lexrel_j(x)`, `NN1 lexrel_n(x)`, `VVD lexrel_v(e_past)`, `II lexrel_p(e)`, where `lexrel` is replaced by the lemma with a leading underscore. "Producing the semantics from the tagger output and this lexicon is a simple matter of substitution. All EPs are labelled with unique labels and all variables are different unless repeated in the same lexical entry" (p. 78).
- *Tagger only.* "The semantic composition rules would apply trivially. There are no slots, the hooks are irrelevant and there are no equalities", and the result is the accumulated rels (p. 78).
- *With a parse.* Open-class words have no slots, so "both the ARGs and the slots are specified at a phrasal level"; "the central idea in the application of the algebra to RASP is to make use of construction semantics in all rules" (p. 78). The ARG1 of *chase* comes from the application of `S/np_vp`, the ARG2 from `V1/v_np` (p. 78).
- *Figure 5 (p. 79), `VP -> V NP`, `op_arg2(op_r(rule, V), NP)`.* The rule's own sement is `[l2, a2, e2]{[l2, a2, e2]r, [l4, a4, x2]arg2}[l2:a2:ARG2(x2)]`. Its R slot is filled by the verb's hook, which identifies the rule's label, anchor and event with the verb's, so the rule's ARG2 lands on the verb's EP; its ARG2 slot is then filled by the noun phrase's hook. "In effect, the rule adds a slot to the verb" (p. 78). The composition is "semantically ternary because of the rule semantics" (p. 78). In both operations the rule sement is the functor, and the mother's hook is the rule's hook.
- *Why the hook needs an anchor.* "It is necessary for the anchor of the argument-taking structure to be visible at all points where arguments may be attached", and with a scopal modifier that anchor is not the semantic head's: in *a cat did not chase a rat* the ARG1 must attach to *chase* (p. 78). Figure 6 (p. 79): *not* is `[l1, a2, e2]{[l2, a3, e2]mod}[l1:a1:not(e2), l1:a1:ARG1(h4)]` with `h4 =q l2`, so the hook of *not sleep* has the label of *not* and the anchor of *sleep*. *not* can carry a slot and an ARG1 lexically "because *not* is associated with a unique tag in RASP" (p. 78). Hence "the hook would have to include an anchor even if explicit conjunction were used instead of equating labels" (p. 78).

**Implementation (Section 6, p. 79).** The RASP grammar "is formally equivalent to a CFG", and semantic rules are associated with rule names. Composition runs bottom-up over the output tree, whose nodes carry rule names and whose leaves carry word, position and tag (`|Every:1_AT1|`). The transitive closure of the equalities "is computed on the final structure, since nothing requires that it be available earlier". The notation is a shorthand that avoids naming slots and operations:

```
rule V1/v_np
daughters V NP
semhead V
hook [l,a,e] rels {l:a:ARG2(x)}
eqs {x=NP.index,l=V.label,
     a=V.anchor}
```

"If no semantic rule is specified corresponding to a rule used in a tree, the rels are simply appended. Semantic composition is thus robust to omissions in the semantic component of the grammar." Semantic rules "can be constructed semi-automatically", with no details given (p. 79).

**Relation between shallow RMRS and deep MRS (pp. 73, 74, 79, 80).** "MRSs can be converted into RMRSs: RMRS output from shallower systems is less fully specified than the output from deeper systems, but in principle fully compatible. In our work, the semantics produced by a deep grammar is taken as normative" (p. 73). The ordering is the "specificity hierarchy in terms of information content" obtained by omitting ARGs, using ARGn, and using less specific predicate names (p. 74). The paper gives no formal definition of the ordering, no comparison procedure, and no agreement figures. It names a class of real incompatibility: for *it rains* the ERG has an expletive subject, RASP "lacks the lexical information and thus the sentence has extraneous relations for the pronoun and an incorrect ARG1 for *rain*. This is an inevitable consequence of the lack of lexical information" (p. 79). The claim tested is narrower: whether the algebra's restrictions ever make it impossible to build compositionally a RASP-RMRS that matches the ERG-RMRS; "no such cases have been found" (p. 79). The conclusion claims "phrasal-level compatibility of RMRS (to the extent that this is syntactically possible)" and compatibility with the ERG "without compromising RASP speed or robustness" (p. 80).

**Formal properties stated.** ARGs are EPs, so the algebra carries over to RMRS unamended (p. 77). The algebra "enforces a strong monotonicity constraint" and "contributes to limiting the possibilities for specification of scope", which generation and scope resolution can exploit (p. 75); these properties "are thus guaranteed for a range of grammars" (p. 80, with a pointer to Fuchss et al. 2004). The algebra's constraints "cannot be fully implemented in a TFS", so "an additional automatic checker is needed", and the checker needs a specified syntax-semantics interface to extract slots and operations from the TFSs (p. 75). The algebra does not model "the way that the features (representing tense and so on) are instantiated on variables" (p. 75).

## Caveats for the parser

### 1. Without lexical slots, argument labels come from the rule name, and a universal schema name does not carry them (high; relaxed-level composition)

In RASP-RMRS the label ARG1 or ARG2 is a property of the specific rule (`S/np_vp`, `V1/v_np`; p. 78), and each semantic rule is written for one rule name (p. 79). A schema such as "head-complement" does not say whether the complement is the ARG2 or the ARG3, or the ARG1 of a preposition. The paper supplies the fallback, ARGn (p. 74), and never uses it in a composition example. A relaxed level that knows only a universal schema and the semantic head can therefore produce the anchor, the label equalities and an ARGn link; a numbered ARG needs either a finer rule name or lexical information. The application to universal schemas is my inference; the paper discusses only RASP's rule set.

### 2. The semantic head and the anchor-bearing daughter can differ, and telling them apart needs a lexical cue (high; relaxed-level composition)

The hook's anchor must be that of the argument-taking EP, and under a scopal modifier that EP belongs to the modified daughter while the label belongs to the modifier (p. 78, Figure 6 p. 79). RASP gets this right for *not* only because the word has its own tag and can be given a slot and a qeq lexically (p. 78). The paper says nothing about scopal adverbs that share a tag with intersective ones. This is the same bit of information that the CLF notes flagged for op_mod, now with a second consequence: a wrong choice misattaches later arguments.

### 3. Shallow output can contradict deep output, so comparison is not pure subsumption (high; evaluation of relaxed against strict)

"Less fully specified ... but in principle fully compatible" (p. 73) is the design goal. The *it rains* case (p. 79) shows a shallow RMRS with an extra EP and a wrong ARG1, which the deep MRS does not specialize. A relaxed-versus-strict evaluation needs at least three outcomes per element: present in both and compatible, absent from the relaxed analysis (underspecified), and present in the relaxed analysis and contradicted. The paper defines no matching procedure and reports no numbers; the three-way scheme is my suggestion.

### 4. The semantic rule notation is a shorthand, and the paper does not define its expansion (medium; implementation)

The `V1/v_np` rule (p. 79) gives `semhead`, a hook, rels, and equalities over `V.label`, `V.anchor` and `NP.index`. It is called "a convenient shorthand for the full algebra" with no statement of the mapping. As printed, the rule's `e` is not equated with anything, whereas Figure 5 has `e2 = e1`; presumably `semhead V` supplies the remaining hook equalities. The minimal per-rule content can still be read off: which daughter is the semantic head, zero or more ARG relations contributed by the rule, and for each a daughter whose index fills it.

### 5. Missing semantic rules degrade silently (medium; diagnostics)

With no semantic rule for a rule name the rels are appended and nothing else happens (p. 79). The paper presents this as robustness. For Orca the same default makes an incomplete rule table indistinguishable from a sentence that has little relational structure, unless the composer records which nodes fell back; the recording is my suggestion.

### 6. The figures contain inconsistencies (medium; reading the paper, and anyone implementing from the figures)

All checked against the page images.

- Figure 1 (p. 74), "RMRS equivalent": `_on_p(e4, e41, x4)` keeps three arguments although its ARG1 and ARG2 are also listed separately; the ARG1 of `_sit_v_1` is `x31`, a variable that appears nowhere in the equalities (the MRS has `x3`).
- Figure 4 (p. 78): the hook of *a* is `[l4, a2, x2]` and the hook of *a cat* is `[l4, a4, x2]`; `rstr` and `body` both take `h2` (Figure 2 has `h2, h3`).
- Figure 5 (p. 79): the ARG2 is `l2:a2:` on the rule, `l2:a1:` after op_r, and `l2:a2:` again in *chase it*; the eqs list `l1 = l2, e2 = e1` and no anchor equality, although the text requires the rule's ARG to share the verb's anchor; the ARG2 slot is `[l4, a4, x2]` and then `[l4, x2]`.
- Figure 6 (p. 79): the hcons is `h4 =q l2` for *not* and `h4 =q l3` for *not sleep*; the eqs of *not sleep* are empty although a slot was filled; the slot of *not* has anchor `a3` and *sleep* has `a2`. The text says "the anchor of the result is equated with the label of *sleep*" (p. 78), while the figure shows the anchor of *sleep*.
- Figure 3 (p. 77): `l1` labels both `give` and `cat`, and `l4` is both the hook label of *a cat* and the label of `rat`, so the equality `l1 = l4` is ambiguous as printed.

### 7. Rule sements as functors change which daughter "has the slot" (medium; relaxed-level composition)

Principle 1 (p. 75) puts the slot on the semantic head. In the lexicon-free setting the slots are on the rule's sement, and the semantic head is itself an argument (of slot R) whose hook the rule copies (Figure 5, p. 79). An implementation that serves both the strict-derived and the relaxed case can treat every schema as a sement with one slot per daughter; lexical slots are then the special case in which the rule passes a daughter's slot through. That unification is my reading; the paper presents the two settings separately.

### 8. Intermediate analyzers are harder to align than shallow ones (medium; cross-grammar design)

"The RMRS approach can only be fully successful to the extent that it abstracts away from the differences in syntactic analyses assumed by different systems, so intermediate processors are more difficult to deal with than shallow ones" (p. 78). A coarse grammar for another language sits in this intermediate zone.

### 9. Closure of equalities is deferred to the end (low; data representation)

The implementation computes the transitive closure once, on the final structure (p. 79). A relaxed composer needs no per-node resolution unless it wants per-node comparison with the strict level.

## Support for the design

- **A relaxed level with graded information is the paper's subject.** One representation covers tagger-only output (a bag of EPs), parser output with construction-supplied ARGs, and deep-grammar output, ordered by information content (pp. 73–74, 78). The mapping onto Orca's levels is mine.
- **The tagger-only level needs one table.** A map from POS tag to an EP template with a variable sort and optionally a tense feature, plus the lemma (p. 78). Predicate naming by lemma and coarse part of speech is designed to sit above the deep grammar's names in a hierarchy (p. 74).
- **Per-rule semantic records are small.** Rule name, daughters, semantic head, contributed ARGs, equalities to daughters' hook components (p. 79). The hook exposes label, anchor and index (p. 77), plus the external argument in a full grammar (p. 74).
- **Composition is robust by construction.** Unknown rules fall back to appending rels (p. 79), and every step is monotonic accumulation (p. 75).
- **Slot renaming gives lexical and unary rules a place in the algebra.** A unary operation that relabels a slot is "locally determinable from the rule" (p. 76); this fits a tagger that names unary steps explicitly. The fit is my remark.
- **The deep grammar is the norm.** "The semantics produced by a deep grammar is taken as normative when developing semantic representations from shallower processing" (p. 73), which is the direction of Orca's strict-to-relaxed comparison.
- **A checker over the strict level is called for again.** The algebra's constraints cannot be enforced in the TFS, so a checker that extracts slots and operations from the feature structures is needed (p. 75); the same extraction yields the sements against which a relaxed composition can be compared. The comparison is my proposal, as in the CLF notes.
- **Phrasal-level compatibility is claimed** as a result, "to the extent that this is syntactically possible" (p. 80; also p. 73), which is what node-by-node comparison would need.

## Theory strains

- **CLF's own imprecision.** "Unfortunately, CLF are imprecise about the algebra in several respects"; only slot propagation and optionality are repaired here (pp. 75–76). The other respects are not listed.
- **Passive against fixed slot labels.** Keeping the algebra unchanged would make the choice of operation depend on non-local information; the price of the repair is a larger inventory of operations (p. 76).
- **Conjunction in RMRS.** The 2003 in-g design is abandoned because syntactic bracketing leaked into the semantics; the argument that the alternative with redundant conjunction relations blocks incremental specialization is asserted without demonstration (p. 77).
- **Lexicalist semantics against lexicon-free parsing.** Lambda calculus and the CFG version of the algebra both assume lexical semantic properties (p. 76); RASP forces ARGs and slots into the rules (p. 78), and lexical facts such as expletives are then unrecoverable (p. 79).
- **Pure lexicalism against construction semantics.** Because CCG is purely lexicalist, compound nouns and larger numbers "have to be dealt with in a post-parsing phase" in Bos et al.'s system (p. 80).
- **Semantic head against syntactic head.** The determiner is the semantic head of *a cat* and "not the syntactic head in the ERG" (p. 75).
- **Reviewer objections unanswered.** The acknowledgements say the reviewers' comments had to be ignored for lack of time and space (p. 80).

## Key primary sources

- Copestake, Lascarides and Flickinger 2001, An Algebra for Semantic Construction in Constraint-based Grammars (ACL): the starting point (p. 73). Queue item 3, read.
- Copestake 2003, Report on the design of RMRS (DeepThought project deliverable): the original RMRS with in-groups (pp. 73, 74, 77). The fuller definition of RMRS is there.
- Copestake, Flickinger, Sag and Pollard 2005, Minimal Recursion Semantics: An introduction, *Research in Language and Computation* 3(2–3), 281–332 (journal name as printed in the paper's reference list, p. 80): MRS, and the argument against binary conjunction (pp. 73, 77).
- Briscoe and Carroll 2002, Robust accurate statistical annotation of general text (LREC): RASP (p. 73).
- Fuchss, Koller, Niehren and Thater 2004, Minimal Recursion Semantics as Dominance Constraints (ACL): the scope properties referred to in the conclusion (p. 80).
- Spreyer and Frank 2005, Projecting RMRS from TIGER Dependencies (HPSG 2005): RMRS from dependencies, with no attempt to match a deep parser (p. 80).
- Bos, Clark, Steedman, Curran and Hockenmaier 2004; Bos 2005: wide-coverage semantics from CCG with lexical arity (p. 80).
- Haugereid 2004, Linking in Constructions (HPSG 2004): more extensive lexical underspecification with RMRS in a deep grammar (fn. 2, p. 77).
- Flickinger 2000 (the ERG); Gazdar, Klein, Pullum and Sag 1985 (GPSG) (pp. 73, 76).

## Not covered here

These are my remarks, not statements from the paper.

- **Long-distance dependencies, head-filler structures and coordination are absent.** The paper does not mention extraction, gaps, relative clauses, questions or coordination. The gap that the CLF notes sent to this paper remains open. What the paper adds for CLF's omissions is limited to slot renaming for the passive, optional complements, and a restated assumption about construction semantics; lexical rules other than the passive, inflection and unary rules in general are not discussed (a unary `V1/v` and `N1/n` appear in the example tree on p. 79 with no comment).
- **Answer to the relaxed-level question.** With only a universal schema name and the semantic head, the method gives: the bag of EPs, the mother's hook (label, anchor, index), label equalities for intersective combination if the schema implies them, and ARGn links between the anchor-bearing daughter and the other daughter's index. It does not give numbered ARG labels, scopal versus intersective modification, qeqs for anything without a closed-class lexical template, quantifier RSTR links unless the determiner tag carries a slot (as *not* does), or expletives. Each of these needs a finer rule name, a tag-level template, or a lexicon. Figure 4 covers a determiner with a lexical slot only in the deep-grammar setting; the paper does not show how RASP-RMRS composes a determiner with its noun.
- **No comparison metric.** The paper defines neither subsumption between RMRSs nor a matching score. My recollection is that RMRSs from different analyzers are aligned through character positions of the EPs and that later work defines such metrics (for example Dridan and Oepen's Elementary Dependency Match); neither is in this paper and I did not verify either. The example tree shows token positions only (p. 79).
- **Anchors in current tools.** My recollection is that later DELPH-IN representations (Dependency MRS, and RMRS as implemented in the LKB and in PyDelphin) keep anchors or node identifiers in the role described here; not checked.
- **Chunkers and dependency parsers.** The introduction names POS tagging, noun phrase chunking and stochastic parsers as suitable sources (p. 73), but only the tagger and the RASP phrase-structure parser are worked through. Dependency input appears only as a citation of Spreyer and Frank (p. 80).
- **No evaluation.** Coverage of the semantic rule set, agreement with the ERG, and speed are asserted or left out; "no such cases have been found" (p. 79) is the only empirical statement, with no description of how cases were sought.
- **ARG0.** The paper writes the characteristic variable as the single argument inside the EP (`chase(e)`) and does not name it; "up to one argument" (p. 77) covers both this variable in a main EP and the value of an ARG element.
- **Nothing was unreadable.** All eight pages were legible as images; no figure was skipped.
