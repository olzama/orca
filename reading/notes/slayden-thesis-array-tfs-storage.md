# Slayden (2012): Array TFS storage for unification grammars

Glenn C. Slayden, *Array TFS storage for unification grammars*, thesis for the degree of Master of Science, University of Washington, 2012, program Linguistics – Computational Linguistics, committee Emily M. Bender and Stephan Oepen (title page). Read from `Slayden-MS-thesis.pdf`: 126 PDF pages, namely title page, abstract, contents (i–iii), acknowledgements (iv), dedication (v), body pp. 1–114, references pp. 115–119. Page numbers below are the thesis's own (PDF page = thesis page + 7). Read in full from the text layer `txt/Slayden-MS-thesis.txt`. The text layer garbles the formulas, the tables, and every figure, so the following were checked against the PDF page images: Table 1 (p. 45), formula 3.21 and Table 2 (p. 49), Tables 3 and 4 (p. 57), Figures 13 and 14 (pp. 72, 74), Table 6 (p. 102), Figures 22 to 25 and Table 7 (pp. 108–111). The array tables in Figures 9, 11, 17, 19, 20 and 21 are legible in the text layer and were read there. Figures 1 to 7, 10, 12, 15, 16, 18 and 26 were read from captions and prose only. Read 2026-11-20.

Question for this reading: what does the thesis offer for a much faster replay engine (one given derivation, checked bottom-up, no chart, no search)? Specifically: (1) the array representation and how unification, copying and sharing work on it; (2) type hierarchy encoding and greatest lower bounds; (3) well-formedness and the time at which type constraints are applied; (4) copying, allocation and concurrency; (5) which techniques serve chart search only; (6) measured numbers; (7) lexical rules, orthographic rules, tokens, MRS extraction.

## Summary

The thesis describes the feature structure storage and the unifier of *agree*, a DELPH-IN-compatible chart parser and generator written in C# for the .NET runtime (pp. 2, 38, 103). It answers questions 1, 3 and 4 in detail, gives little on question 2, and almost nothing on question 7. It contains no profile of time by component and no unification rate; all timings are end-to-end parse times.

**Storage (Sections 2.3 and 3.2, pp. 21–49).** A feature structure is one root pair plus one contiguous, read-only array with one row per arc:

- Root: `(type, mark)`, stored outside the array. The root mark is 1, or 0 when the root type has no appropriate features and the array is empty (pp. 43–44).
- Row: `(f, m_F, t, m_T)`, four 32-bit integers, 16 bytes (p. 44). `f` is the feature, `m_F` the "in-mark" of the node the arc leaves, `t` the type of the node the arc reaches, `m_T` the "out-mark" of that node. The features of a node with mark `m` are the rows whose `m_F` equals `m` (formulas 2.36–2.37, p. 28).
- Marks are integers local to one structure. A node whose type has no appropriate features has out-mark 0, and 0 never occurs as an in-mark; a node reached by exactly one arc has a positive mark; a node reached by more than one arc (a reentrancy) has a negative mark, and its `(t, m_T)` pair is repeated by value in every row that reaches it (pp. 28, 46–47; Figure 9, p. 51; Figure 11, p. 53). The number of rows equals the number of arcs of the graph (p. 51).
- Access is a hash lookup on `(f, m_F)`, which returns `(t, m_T)` and, on request, the row index. A failed lookup returns `(⊤, 0)`, so an unconstrained feature costs no row; the evaluated system never stores a non-coreferenced `⊤` node (pp. 36–37, 46–47). There is no index from a mark to its type: the caller carries `(type, mark)` down the recursion and enumerates the features appropriate to the type (pp. 31–32, 36).
- Hash index: a table of 256 initial entries per structure plus a separate `next` array of the same length as the row array; the hash is `(f + m_F) & 255` (formula 3.21, p. 49; pp. 48–49). A separate `next` array beat a 20-byte five-field row, which the author attributes to alignment (p. 48).
- Type identifier: low 27 bits name a type or a string, high 5 bits are flags: coreferenced, leaf type, has appropriate features, string, string value, Skolem constant (Table 1, p. 45). Identifiers follow a topological order, so a subtype has a greater identifier than its supertypes, and `⊤` is 0 (p. 45).
- A rule structure caches the marks and row indexes of its daughter positions, so no traversal is needed to find them (p. 94). Each structure records how many coreferences it contains (pp. 80, 97).

**Unifier (Section 4.4, pp. 75–100).** Two passes over detached scratch slots; the inputs are never modified.

- One operation takes any number of "participants": one outer structure and others unified at its root or at positions inside it. Participants can be added while the operation runs (pp. 93–94).
- Each participant is assigned a contiguous range of slots in one scratch array: one slot for its root and one per row, addressed by row index. Global slot 0 is reserved so that 0 can mean "not forwarded" (pp. 83, 95–96). A slot holds a forwarding index, the current type, the out-mark, a field for the mark assigned in the writing pass, and a node-counting field (formula 4.9, p. 82; p. 89 says six scalars in total).
- Scratch slots sit on arcs, so a coreferenced node has several slots. In the evaluated system a negative mark indexes a dedicated slot region of its participant (pp. 80, 83–84). In the later design, which the worked example shows, an array `pp_corefs` holds one slot pointer per negative mark of each participant; the first slot visited for a class claims it, and later ones are forwarded to it (pp. 80, 93, 97–99).
- Pass 1 is union-find with dereference-before-forward (pp. 62, 83). For a mother-daughter unification it starts at the daughter's root slot and the slot of the daughter position inside the mother, and visits only what the daughter reaches; the rest of the mother is untouched (p. 94; Figures 17 and 19, pp. 95, 97). At a pair of slots: dereference both, compute the greatest lower bound of the types, fail if there is none. If the result type differs from both input types and has appropriate features, the expanded structure of that type is added as a participant and unified in first (pp. 60, 87, 97 fn. 69). The representative is the slot whose own structure stores rows for more of the needed features; the other slot is forwarded to it after returning from the recursion (p. 87, fn. 61). The pass does not descend into substructure that only one input constrains, except where node counting requires it (p. 90 fn. 63, p. 91).
- Pass 2 runs only after success. It allocates a row array of the counted size, then walks from the outer root slot: for each feature appropriate to the node's final type, it looks up `(f, mark)` in the structure that owns the governing slot, follows forwarding to the representative, and emits a row. New marks come from two counters: coreferenced nodes from −1 downward, others from 2 upward, and 0 for featureless types (pp. 92–93). Slots of the untouched mother portion are initialized on first visit during this pass (pp. 98–100). Figure 21 (p. 99) shows the written result.
- The claimed contribution over Tomabechi is that no per-node list of extra arcs (COMP-ARC-LIST) is needed, because the result is described by forwarding among the row layouts of the inputs (pp. 76–78, 114).

**Type hierarchy.** The partial order is completed with anonymous greatest-lower-bound types "using the technique described in Aït-Kaci (1984)", and the transitive reduction is maintained during that computation (p. 6). The thesis gives no bit-code representation, no table layout and no count of added types. Run-time type unification is mentioned only through the leaf flag "used to optimize type unification" (Table 1, p. 45) and a footnote that names "a (duplex) GLB cache" and bit-array operations after Aït-Kaci et al. 1989 as an alternative for many types at once (fn. 49, p. 72).

**Evaluation (Chapter 5, pp. 101–113).** agree is compared with the LKB and PET on exhaustive parsing and unpacking of the 'hike' corpus with ERG revision 10342. Single-threaded, PET is fastest in total and agree scales best with sentence length; with eight cores agree is fastest (Table 6, p. 102; Table 7, p. 110).

## Caveats for the parser

### 1. The design is write-once and non-destructive, the reverse of ours (high; data representation)

Arrays are read-only once written (pp. 24, 41 fn. 31, 55), every successful unification writes a complete new structure, and the author states that destructive unification "has limited utility in linguistic application" because the arguments are grammar structures or memoized chart results (p. 63). That argument is about chart parsing. Our scheme (fresh copy of the rule, destructive unification of each daughter, undo trail) is closest to D-PATR as the thesis describes it: modify in place, log each change, reverse on failure (p. 64). The thesis does not measure a destructive unifier, so it gives no evidence for or against ours. What it does show is the cost structure of the alternative: pass 1 touches only the daughter-reachable part of the rule, and the rule's remaining rows are copied once, during the writing pass, into an array of the exact final size (pp. 94, 98). Our fresh copy of the whole rule before unification corresponds to "early copying" in the thesis's terms (p. 61).

### 2. Run-time constraint application, with three details (high; correctness of the check)

The trigger is that "the type unification between two nodes results in a type which is not identical to either of the input node types"; the unifier then fetches the expanded constraint of that type and unifies it at the node, and failure there fails the whole unification (p. 60). Details: (a) when the new type has no appropriate features, agree only changes the slot's type and introduces no constraint structure (fn. 69, p. 97); (b) the constraint is unified in before the two argument nodes are joined (p. 87); (c) the same constraint structure can enter at several points of one result, most often with difference-list subtypes in the ERG, and its internal coreferences must stay distinct per instance (fn. 18 and 19, p. 22; p. 61). Detail (c) is automatic when each instance is a fresh copy and is a hazard for any scheme that shares the constraint structure.

### 3. The thesis has no lazy expansion and no unfilling, and its one storage omission caused most of its complications (high; architecture)

Every structure is kept well-formed at all times: the grammar is expanded at load, and internal nodes are unified with the expanded structure of their type (pp. 13–14, 60). The only thing left out of storage is the non-coreferenced `⊤` node (p. 36). That omission produced the "disjoint feature coverage" problem (pp. 86–88), the fallback-fetch mechanism with forwarding loops (pp. 88–89), and two node-counting errors, one of them fatal if unhandled (pp. 90–91). The author later removed the prohibition and required every type's expanded structure to store a row for each feature appropriate to its root type, after which fallback fetch "became unnecessary" (fn. 37, p. 46; p. 88). The author also judges the space saved by the omission to be small for expanded structures (pp. 36–37). Our lazy copying of type constraints leaves far more unstored than this design did; the thesis offers no model for it and its experience counsels caution about partially materialized nodes in a tabular layout.

### 4. Node counting exists because .NET arrays cannot be resized (medium; data representation)

Pass 1 must predict the number of rows of the result so that the array can be allocated before writing; this is "a challenging aspect", worsens the unifier's complexity by forcing descent into substructure that only one input constrains, and can overcount by a row or two (pp. 90–91). The requirement comes from the target platform (p. 82 fn. 58, p. 91). An engine that writes into a growable arena does not need it; that remark is mine.

### 5. Marks are local, so nothing is shared between structures (medium; memory)

A mark has no meaning outside its array, which "summarily interdicts the sharing of substructure" between two structures (p. 52). agree shares only whole grammar structures that are identical after restriction or apart from their root type (p. 18). The LKB, PET and Ace use the structure sharing of Malouf et al. (p. 101). Each result therefore holds a full copy of everything it keeps from its daughters. The thesis sketches remedies (a structure reference paired with a mark, or mark sequences per sentence) and leaves them to future work (pp. 52–53).

### 6. One hash lookup per feature per node is the inner loop (medium; speed)

Storage access is "the most performance-critical aspect of agree" (p. 47). With 256 buckets and structures of 400 to 1200 nodes, a query can traverse up to five chain links (p. 49). The author's own planned replacement sorts rows by in-mark and then feature, so that a node's rows are adjacent and the unifier walks them, "eliminating n − 1 array storage queries for each node with n feature-value pairs" (p. 54). A second proposal drops the feature column and places each node's values at `mark + (f mod u)` for a modulus `u` fixed per feature configuration (formula 3.25, p. 56). Neither was implemented or measured (pp. 57–58).

### 7. Cycle detection is not described for the array unifier (medium; correctness of the check)

The storage layer does not detect cycles (p. 47), the forwarding order is chosen on the assumption that the formalism prohibits cyclic structures (fn. 61, p. 87), and only the abandoned n-way unifier is said to detect mutually cyclic coreferences, as non-zero reentrancy counts at the end of traversal (p. 73). A checker has to reject cyclic results; the thesis does not say where agree does so.

### 8. End-to-end timings do not isolate the unifier (medium; evaluation)

The author says so directly: the LKB and PET share an algorithm and differ widely (pp. 101–102), and agree's single-threaded runs still pay for atomic instructions and task closures (pp. 108, 111). No number in the thesis is a unification rate or a time share.

### 9. Morphology and tokens are again where systems differ (low; lexical processing)

agree did not accept sentences with numeric digits (fn. 71, p. 101; p. 106), did not put stand-off positions into feature structures, so token-mapping paths were filtered out before comparing results with PET (p. 106), and twelve tokenization differences accounted for 1,668 of the differing derivations (fn. 77, p. 106).

### 10. The evaluated system is older than the described one (low; reading the thesis)

Chapter 5 measures a system with stack-allocated scratch slots, a dedicated coreference slot region, fallback fetch, and unstored `⊤` nodes. The text also describes a later design with a generation counter per thread, `pp_corefs`, and root coverage, which was not evaluated (fn. 37, p. 46; p. 80 fn. 56; pp. 81–82, 88, 93, 95).

## Support for the design

- **Replay is the thesis's "unpacking", and all daughters should go in one operation.** Validating the derivations of a packed forest with all of a rule's daughters unified in a single unifier operation was 13% faster in total than one operation per daughter (39.67 s against 45.57 s; Figure 13, p. 72; p. 73). The author notes that this helps unpacking and not parsing, because a parser must keep the intermediate active edges (fn. 51, p. 73). For replay it means one result written per tree node, with no intermediate structure after the first daughter.
- **Constraint structures as participants of the same operation.** Well-formedness structures are added to the running operation "without the expense of starting an entirely new operation" (pp. 93–94).
- **Flat arrays of small integers, one allocation per structure.** The stated gains are trivial discarding and fewer allocations (pp. 23, 114). Structure traversal just to find and free nodes was observed to be slower than a sequential scan of up to 40% more memory (p. 16). Field widths: 16 bits suffice for features and marks with the ERG, and a type needs at least 20 bits (pp. 44–46).
- **Topologically ordered type identifiers with flag bits.** The order lets the unifier know in advance which argument can be the more specific one; the has-features flag is "used in every graph traversal" (p. 45).
- **Few feature configurations.** The ERG's 206 features occur in 120 distinct sets of co-occurring features, of sizes zero to fourteen (p. 19). Fixed per-type layouts are therefore feasible (pp. 54–55).
- **Detached scratch space, one unifier per thread, generation counter.** Each thread owns a unifier object with a reusable slot array and a private generation counter; nothing is contended and nothing is zeroed between operations (pp. 81–82). A shared pool and shared counter, as in van Lohuizen's parser, invite contention (p. 80).
- **Sentence-level parallelism is nearly as good as finer-grained parallelism.** With eight cores, throughput per core fell to 57% for one sentence per thread and 51% for tasks within a sentence (p. 112; Figure 25, p. 111). The author attributes the shared loss to memory bandwidth (p. 112). Unification inside one operation is not parallelized, following van Lohuizen's judgment that it is premature (p. 70, pp. 75–76).
- **Expansion at load can skip nodes.** agree marks only the root of each unexpanded definition as not well-formed and lets unification with well-formed structures settle the rest, and it unifies all parent constraints in one call (fn. 11, p. 14). The transitive reduction of the hierarchy matters only for minimizing these unifications (fn. 5, p. 6).
- **Daughters are deleted from the mother.** "Daughter ARG deletion" is a standard optimization (Table 5, p. 101), and the author sees "little reason to disable" it; without it a structure grows toward 60,000 rows at about 60 words (pp. 44–45).
- **Two passes are less well motivated once success is likely.** The author argues that pre-filters now do the work of the failure-detecting first pass and that this makes single-pass unifiers relevant again (pp. 68, 75). In replay of gold derivations nearly every unification succeeds, so a single-pass or destructive unifier is consistent with this argument; the application to replay is my inference.
- **Search-only techniques.** Table 5 (p. 101) lists daughter ARG deletion, key-driven active edges, span-only rules, quick check, chart dependency filter, ambiguity packing, and rule filter. The thesis does not separate them by purpose. My classification: quick check, rule filter, key-driven edges, chart dependency filter and packing decide which combinations to try or how to store alternatives, and replay needs none of them; ARG deletion keeps structures small and still matters; the span-only condition is part of what the grammar licenses, so a checker has to enforce it as a test on the node's span. The feature restriction of the diagnostic feature RNAME (p. 18) is a size reduction that applies to replay unchanged.

## Theory strains

- **Carpenter's functional definition versus the graph view.** The author argues that implementations follow the graph view while the HPSG literature adopted Carpenter's, and that the array design returns to Carpenter in one respect, the distinguished root (pp. 9–14, 21–23).
- **Dependence on feature appropriateness.** The storage cannot enumerate a node's features without the grammar's appropriateness table, and each feature must be introduced by exactly one type (pp. 7, 35–37). Formalisms without this condition are outside the design (p. 35).
- **Types the grammar writer did not write.** The added greatest-lower-bound types are "not included in the grammar as authored" and are inserted as a convenience (p. 6; Figure 2 shows `glbtype1` between `0-1-list` and `olist`).
- **Features with no linguistic content.** RNAME "is used for diagnostic purposes but does not contribute to linguistic analysis" (p. 18).
- **Cycles.** Prohibited in the DELPH-IN formalism, permitted in other variants, and central to Carpenter's argument for his formalism (p. 13).

## Key primary sources

- Tomabechi 1991, 1992: quasi-destructive unification; the baseline that the LKB, PET and Ace implement (pp. 67–68).
- Wroblewski 1987: incremental non-destructive unification; generation counter; the terms early copying and over copying (pp. 61, 64–65).
- van Lohuizen 2000, 2001 (ACL papers and Delft thesis): thread-safe unification with detached scratch buffers; parallel versus concurrent unification (pp. 69–70, 78, 80).
- Callmeier 2000, 2001: PET; fixed feature layouts and coercion (pp. 19, 54).
- Malouf, Carroll and Copestake 2000: structure sharing and its restrictions; quick check (pp. 17, 67).
- Aït-Kaci 1984; Aït-Kaci, Boyer, Lincoln and Nasr 1989: completion of the type hierarchy; bit-array lattice operations (pp. 6, 72).
- Kiefer, Krieger, Carroll and Malouf 1999: rule filter and quick check (p. 68).
- Karttunen 1986 (D-PATR): destructive unification with a change log (p. 64).
- Pereira 1985: structure sharing with environments (p. 63).
- Oepen and Carroll 2000b: proactive and retroactive packing, which agree adapts to a lock-free chart (p. 103). Hyper-active parsing is cited as Oepen et al. on pp. 61 and 81.

## Measured numbers

All from ERG SVN trunk revision 10342 of November 29, 2011 (fn. 14, p. 18; p. 105). Timings from one machine with two Xeon X5460 processors (8 cores) and 32 GB of memory, running Windows for agree and Linux for the LKB and PET; grammar start-up excluded; exhaustive unpacking of every derivation (p. 105).

| Quantity | Value | Page |
|---|---|---|
| Features in the ERG | 206 | 19, 44 |
| Distinct feature configurations; sizes | 120; 0 to 14 | 19 |
| Non-string types (Table 1, "ERG count") | 8,019 | 45 |
| Leaf types | 3,003 | 45 |
| Types with appropriate features | 5,915 | 45 |
| Strings in the grammar's string table | 46,832 | 45 |
| "Array storage relations" for the ERG type hierarchy; shared at least once | 8,450; 653 | 18 |
| Substructure nodes over all expanded type definitions | 53,412 | 57 |
| Features per node, averaged over configurations; weighted | 5.65; 6.47 | 57 |
| Row size | 16 bytes (10 would suffice) | 44, 46 |
| "Typical TFS" | about 600 nodes, about 10,000 bytes | 44 |
| Structures produced in parsing | about 400 to 1200 nodes | 49 |
| Average rule structure | about 500 nodes | 44 |
| 'hike' corpus | 330 sentences, 11.67 words on average, 277,946 derivations compared | 105, 106 |
| Top-level unifications for the 'hike' task | about 20 million | 105 |
| Top-level unifications for the 24-word sentence 5.4 (195,605 analyses) | about 500 in morphology, 100,000 in the parse, 900,000 in unpacking | 109 |

Single-threaded batch run, 287 sentences of 'hike' (Table 6, p. 102, checked against the page image):

| System | t min (s) | t max (s) | Total (m:ss) | Scaling b, agree = 1.00 |
|---|---|---|---|---|
| LKB | .080 | 1070.0 | 67:14 | 2.08 |
| PET | .007 | 8.4 | 1:47 | 1.18 |
| agree | .008 | 7.7 | 3:04 | 1.00 |

The LKB row excludes 11 further sentences (fn. 71, pp. 101–102). With 8-way concurrency agree parses the corpus in 42 seconds (p. 109; Figure 23, p. 108).

Sentence 5.4 (Table 7, p. 110):

| System | Parse time (s) |
|---|---|
| LKB | did not finish in 7200 |
| PET | 39.47 |
| agree, task limit 1 | 126.13 |
| agree, task limit 8 | 28.19 |
| agree, task limit above 8 (average) | 29.84 |

Unifier variants inside agree, parsing and exhaustive unpacking of a subset of 'hike' (Figure 14, p. 74, read from the image): Wroblewski-style incremental 96.50 s (multi-threaded) and 102.11 s (single-threaded, eight pipelines); n-way 39.67 s and 41.46 s; the array unifier 35.4 s per the caption.

Hash function trials, total parse time in seconds for the 287 sentences (Table 2, p. 49): the best is 38.2 for `(f + m_F) & 255`; the other fifteen cells range from 38.6 to 44.8.

## Not covered here

These are my remarks, not statements from the thesis.

- **No unification rate and no time profile.** Dividing the stated unification counts by the stated times gives about 109,000 top-level unifications per second for agree and 187,000 for PET on the batch run, if the 20 million figure refers to the 287-sentence run (the thesis attaches it to the 'hike' task without saying which subset), and about 7,900 (agree, one task) and 25,300 (PET) per second on sentence 5.4. The two estimates differ by a factor of seven or more, and the thesis does not define "top-level unification" relative to quick-check filtering, so I would not use either as a target.
- **Question 2 is mostly unanswered.** No encoding of the hierarchy, no description of the GLB cache, no algorithm beyond the citation of Aït-Kaci 1984, and no count of added types. Table 1 gives 8,019 non-string types without saying whether added types are included, and p. 18 gives 8,450 "array storage relations" for the type hierarchy without explaining the difference. Our counts (about 7,500 authored plus 4,700 added) are for a much later ERG and cannot be checked against these.
- **Question 7 is mostly unanswered.** Lexical rules and orthographic rules appear only as "morphological analysis" with about 500 unifications for one sentence (p. 109) and in the definition of the chart dependency filter (Table 5, p. 101). Token structures appear only as something agree did not build (p. 106). MRS extraction is named as a component added for generation, together with trigger rules, skolemization and surface read-back, and is not described (p. 103). The only implementation facts are that string values and Skolem constants are encoded in the type identifier with flag bits (Table 1, p. 45).
- **What I would take for the next engine.** (a) Flat integer arrays and integer type identifiers in topological order with flag bits. (b) Rows of a node stored adjacently in a fixed per-type order, which is the author's own untested successor to the hash (p. 54) and removes the lookup that he names as the hot spot. (c) One operation per tree node with all daughters and all triggered constraints as participants. (d) Visit only what the daughters reach; copy the remainder of the rule once, when the mother is written. (e) One unifier with private scratch per thread, parallelism across sentences. I would not take node counting, the unstored-`⊤` convention, or fallback fetch.
- **Open comparison with our destructive design.** The thesis's design writes each mother once and reads daughters in place; ours copies the rule first and mutates it. Which is faster for replay depends on how much of the rule a daughter touches and on whether the daughter's own substructure has to be copied into the mother at all. With no sharing between arrays, this design always copies it; a pointer-based mutable design can adopt the daughter's nodes because each daughter is consumed exactly once. The thesis gives no data on this.
- **Small inconsistencies in the thesis.** The introduction assigns the formalism review to "Chapter 3" (p. 2) though it is Chapter 2; Chapter 5 has no Section 5.1 or 5.4.1; the scratch field for the written mark is `m_copy` in formula 4.9 (p. 82) and `m_src` on p. 93; formula 4.9 shows four fields, p. 82 adds a fifth, p. 89 says six; "Copestake 2002a" and "2002b" in the text appear swapped relative to the reference list (pp. 2–3, 115); fn. 66 cites "footnote 52 on page 61", which is on p. 73. None affects the content above.
- **Not read from images:** Figures 1 to 7, 10, 12, 15, 16, 18 and 26. Nothing in these notes depends on values read from them.
