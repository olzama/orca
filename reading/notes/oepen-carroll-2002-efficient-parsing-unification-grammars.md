# Oepen and Carroll (2002): Efficient parsing for unification-based grammars

Chapter 9 of Stephan Oepen, Daniel Flickinger, Jun-Ichi Tsujii and Hans Uszkoreit (eds.), *Efficiency in Unification-Based Processing* (the title on the PDF's title page), CSLI, dated 10/1/2002 on the title page. Read from `oepen-carroll-2002.pdf` (33 PDF pages: title page, contents, chapter pp. 1–28, references pp. 29–31). The file is an author's typeset copy containing only this chapter, paginated from 1; the page numbers of the printed book are not in the file. Page numbers below are the chapter's own (PDF page = chapter page + 2). The chapter says of itself that it is "a combined and revised version" of Oepen and Carroll 2000b (*Natural Language Engineering* 6(1): 81–97) and Oepen and Carroll 2000a (NAACL 2000, pp. 162–169) (fn. 1, p. 1). Read in full from the text layer; the text layer loses the relation symbols in Tables 2, 4 and 6, the formula on p. 25, and Figures 1, 2, 3 and 5, so Tables 2, 3, 4 and 6 and the formula were checked against the PDF page images. Figures 3 and 5 were read from their captions and the surrounding prose only. Read 2026-11-20.

Question for this reading: what do the known efficiency techniques for unification-based processing imply for the design of a replay engine (one given derivation, checked bottom-up, no chart, no search)?

## Summary

The chapter is about parser control and about measurement. It does not describe a unifier, a type hierarchy encoding, or lexical processing; for those it points to other chapters of the same volume (Malouf, Carroll and Copestake for the unifier, quick check, copying and subsumption; Callmeier for PET; Makino et al. and Ciortuz for abstract machines; p. 2, p. 7). It has three parts.

**Profiling (Section 9.2, pp. 3–6).** Overall time and memory do not characterize a system; the authors define a "competence & performance profile" stored by [incr tsdb()], with a common set of counters across systems (Table 1, p. 5): rule-daughter instantiation attempts that were filtered before unification (*ftasks*), attempts executed (*etasks*), attempts that succeeded (*stasks*), passive edges, top-level unifier calls, top-level copies "made in order to save the results of successful unifications", CPU time, and allocated memory. They report sources of noise: about ten percent difference between two machines with identical hardware, load and memory effects, and garbage collection in the Lisp systems (p. 6).

**Parsing strategies (Section 9.3, pp. 6–15).** Both the LKB and PAGE parsers use Tomabechi's (1991) quasi-destructive unification with the structure-sharing copy of Malouf et al., are bottom-up, and apply the same two filters before any unification: a static rule compatibility table and the quick check (pp. 6–7). The LKB passive parser makes all daughter unifications of a rule succeed before it copies the mother, and stores no active edges (p. 7). The PAGE active parser stores active edges and must copy after each successful unification (p. 7). The measured outcome is that the passive parser "trades unifications for copies" and the two reach similar speed (Table 2, p. 8; p. 9). For the active parser, the daughter to instantiate first should be the "key" daughter, the best discriminator, which is often a different daughter from the linguistic head (pp. 10–11, Figure 1). Hyper-active parsing combines the two: keep the active parser's control, store an active edge without copying its feature structure, recompute the intermediate structure from the rule and the daughter edges when the active edge is extended, and copy only complete passive edges (pp. 12–13). It gives the copy count of the passive parser with a unification count near the active parser's, and lowers both time and memory (Tables 3 and 4, pp. 12, 14).

**Ambiguity packing (Section 9.4, pp. 15–27).** With the linear-time bidirectional subsumption test of Malouf et al., a new edge is packed into an existing more general edge (proactive), or an existing edge is packed into a new more general one (retroactive), with "frosting" and "freezing" to block superseded edges and their derivatives (pp. 17–22, Figure 4). Packing requires a restrictor: the daughters are removed from every passive edge, and the constraints that only build semantic structure are removed from lexical entries and rules for the first phase, then restored in a second, unpacking phase in which each analysis taken from the forest is checked against the unrestricted grammar (p. 24). The best restrictor removes compositional semantics and keeps the attributes used in selection and agreement (Table 6, p. 25).

## Caveats for the parser

### 1. Copying costs more than unifying, and replay needs one copy per node at most (high; data representation)

The chapter never reports the share of time spent in unification or in copying. The closest evidence is Table 3 (p. 12), which holds the control strategy fixed and varies only whether active edges are copied:

| Test set | Parser | Unifications per item | Copies per item | Time (s) | Space (kb) |
|---|---|---|---|---|---|
| csli | active | 288 | 180 | 0.31 | 2432 |
| csli | hyper-active | 354 | 114 | 0.27 | 1686 |
| aged | active | 718 | 452 | 0.87 | 5449 |
| aged | hyper-active | 928 | 293 | 0.71 | 3830 |

Redoing a unification that is known to succeed is cheaper than keeping a copy of its result; this reading of the table is mine, and the authors' statement is that additional unifications "are traded for the copies that were avoided" with a net gain (p. 13). The passive regime shows the pattern replay should follow: all daughter unifications of a rule are done in one pass and the mother is copied once, only after all have succeeded (p. 7). A replay engine does exactly the unifications the passive parser would do for the edges of one tree, so it needs at most one copy per tree node, and none for a node whose unification fails.

### 2. Run-time type inference changes the set of analyses (high; correctness of the check)

Footnote 6 (p. 8) says that PAGE "generates a few additional passive edges" because it does not perform run-time type inference, "i.e. the application of constraints associated with a greatest lower bound that is computed at run-time", as the LKB does. An engine that skips this step accepts structures the grammar rejects. A replay engine is a checker, so it has to apply the constraint of a type whenever unification produces a greatest lower bound that is more specific than both inputs. The chapter gives no algorithm and no cost for this step.

### 3. The restricted first phase overgenerates; the second phase is a replay (high; architecture)

With semantics restricted, the authors "allow overgeneration in the first phase and rely on any semantically invalid analyses being filtered out during unpacking" (p. 24). Two consequences. First, the constraints that build semantics can make a unification fail, so a replay that is meant to certify a derivation must unify the full, unrestricted rules and entries; a syntax-only check is weaker than the grammar. Second, the unpacking phase of a packing parser is the same operation as our replay: take one tree from a source that may overgenerate, and validate it against the unrestricted constraint set.

### 4. The daughters must not be carried in the mother (medium; data representation)

"Parse tree construction must not be duplicated in the feature structures (by means of the HPSG DTRS feature) but be left to the parser"; this is done by restriction applied to all passive edges (p. 24, citing Shieber 1985 and Kiefer et al. 1999). The chapter states this as a precondition for packing. For replay the same restriction keeps the structure at each node from growing with the size of the subtree below it; that consequence is my inference.

### 5. Morphology is where engines disagree (medium; lexical processing)

The only statement about lexical processing in the chapter is that "minor system idiosyncracies—mostly in the treatment of inflectional morphology and irregular spellings" make the LKB and PAGE accept slightly different sets of items (fn. 6, p. 8). The chapter says nothing else about lexical rules, orthographic rules, or token feature structures.

### 6. Parsers and grammars become tuned to each other (low; generality)

Following Carroll (1994), the authors say that parallel development of a parser and a grammar can leave rule storage, the treatment of traces, and the expected input length fitted to one grammar and one test corpus, and that this has probably happened between the LinGO grammar and the LKB parser (p. 2). An engine built against the ERG alone is exposed to the same effect. Their evidence that small test sets mislead: the gain from hyper-active parsing differs between the csli and aged test sets (p. 13).

### 7. Timing measurements are noisy in specific ways (low; evaluation)

Identical machines differed by about ten percent; CPU load and available memory affect CPU time; garbage collection adds noise and appears to slow the non-collection time that follows it (p. 6). The reported CPU times exclude garbage collection, and the authors estimate that counting it would raise the gain of hyper-active parsing from around forty percent to "close to a factor of two" (p. 14).

## Support for the design

- **Search-only techniques.** The rule compatibility table and the quick check exist to avoid unifications that would fail: between 94 and 96 percent of rule-daughter instantiation attempts are filtered out (Tables 2 and 3, pp. 8, 12; the filter rate is defined on p. 5, and fn. 4 notes that Kiefer et al. 1999 define it differently). Key-daughter selection, active and hyper-active edges, agenda ordering, best-first search, subsumption, and packing all concern which combinations to try and how to store alternatives (Sections 9.3 and 9.4). In replay the combinations are given by the derivation, so none of these is needed for correctness. That conclusion is mine; the chapter does not discuss checking a given derivation, apart from the unpacking phase (p. 24).
- **Small, fixed rule arity.** Rules in the LinGO grammar "are at most binary branching" (p. 9); the July 1999 grammar has twenty-four binary rules, seventeen of which have a linguistic head daughter (p. 11). Feature structures are "large, typically containing hundreds of nodes" (p. 17).
- **Quasi-destructive unification with scratch slots.** Both reference parsers use it (pp. 6–7), the subsumption test reuses the same scratch slots (p. 17), and unification by itself allocates little memory, mainly temporary arcs (fn. 8, p. 9; p. 14).
- **Pooled node allocation.** The LKB adopted from PET "a statically allocated pool of dag objects that can be recycled cheaply after a parse has completed"; with it, memory use reflects only temporary arcs and edges (p. 14). The LKB pool has a fixed size and falls back to regular allocation when exhausted (fn. 13, p. 14). Per-sentence arena allocation fits replay directly.
- **A common set of counters.** Table 1 (p. 5) gives the measures that made six parsers comparable. Unifications, copies, CPU time and space per item apply to replay unchanged; *etasks* and *stasks* become attempted and successful rule-daughter unifications, and their difference is the count of derivation failures.
- **Replaying known-successful unifications is named as an open problem.** Future work includes techniques "that reduce the cost of replaying unifications that are known to succeed", with Pereira's (1985) environments, which record only the changes made to the original structures, as a candidate (p. 27).
- **Unary rules are unpredictable.** The authors note "a general non-predictability of categories derived for any token substring (in particular with respect to unary rule applications)" (p. 26). This supports having the tagger name unary steps explicitly.

## Theory strains

- **Restrictive versus constructive constraints.** Packing works well only if constraints that select are separated from constraints that build semantics; the best restrictor has to keep the parts of CONT that take part in selection and agreement (pp. 24–25). The authors report that LinGO development was moving toward a stricter separation in the grammar and in the underlying semantic theory, "partly for linguistic reasons" (fn. 18, p. 25).
- **Linguistic head versus processing key.** In only six of the seventeen headed binary rules is the key daughter the linguistic head (p. 11); "linguistic headedness is not a good indicator for rule instantiation" (p. 11). Keys are stipulated by the grammar writer as annotations on rules (p. 11).
- **Ambiguity in the grammar versus in the parser.** One way to avoid exponential numbers of analyses is to remove sources such as prepositional phrase attachment from the grammar and underspecify the semantics; packing is offered as the orthogonal, computational approach (p. 15).

## Key primary sources

- Malouf, Carroll and Copestake (same volume): quasi-destructive unification with structure-sharing copy, quick check, linear-time bidirectional subsumption. The chapter defers to it for every unifier-level question.
- Callmeier (same volume): PET; the dag recycling pool.
- Tomabechi 1991, Quasi-destructive graph unification (ACL).
- Kiefer, Krieger, Carroll and Malouf 1999, A bag of useful techniques for efficient and robust parsing (ACL): rule filter, quick check, restriction of passive edges.
- Pereira 1985, A structure-sharing representation for unification-based grammar formalisms (ACL): environments.
- Shieber 1985, Using restriction to extend parsing algorithms for complex feature-based formalisms (ACL).
- Moore and Alshawi 1992; van Noord 1997: deferring semantic constraints to the unpacking phase.
- Oepen and Flickinger 1998, Towards systematic grammar profiling; Carroll 1994, Relating complexity to practical performance.
- Makino, Miyao, Torisawa and Tsujii; Ciortuz (same volume): compilation of feature structure operations into abstract machine instructions.

## Not covered here

These are my remarks, not statements from the chapter.

- **The chapter is silent on most of the question.** It contains nothing on the encoding of the type hierarchy or the computation of greatest lower bounds, nothing on well-formedness or the time at which type constraints are expanded beyond fn. 6, nothing on unfilling, nothing on how the quick-check paths are chosen, nothing on lexical rules, orthographic rules or token feature structures beyond fn. 6, and no MRS extraction. It gives no profile of time by component. The chapter by Malouf, Carroll and Copestake in the same volume is the one to read for the unifier; no file in `reading/` has a name matching it (checked 2026-11-20 by file name only).
- **The filters may still earn a place as diagnostics.** A quick-check vector compares the types at a fixed set of paths that most often cause failure. If the tagger proposes a wrong rule, a quick-check mismatch gives a cheap and readable first report of where the daughter and the rule disagree. This is a use the chapter does not consider, and whether it helps depends on how often proposed derivations fail.
- **Destructive unification is a candidate that the chapter does not test.** In replay each intermediate structure is consumed exactly once, by its mother. A design that instantiates a fresh copy of the rule and unifies the daughters into it destructively replaces the copy of the result with a copy of the rule. Which copy is smaller is an empirical question about ERG rules versus restricted mothers; Table 3 says only that copies dominate.
- **The numbers are from Lisp systems on a 300 MHz UltraSparc with the July 1999 grammar** (fn. 7, p. 9; p. 11). The ratios between strategies are informative; the absolute times and the rule counts are historical. The current ERG is several times larger.
- **Bibliographic identity.** The PDF's title page gives the volume title as *Efficiency in Unification-Based Processing*. My recollection is that the book was published by CSLI Publications in 2002 as *Collaborative Language Engineering: A Case Study in Efficient Grammar-based Processing* with the same editors; I did not verify this, and the file contains no printed-book page numbers.
- **Not read from images:** Figures 1, 2, 3 and 5. Nothing in these notes depends on values read from a figure.
