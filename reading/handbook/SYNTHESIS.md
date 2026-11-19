# HPSG Handbook (2021): synthesis for the parser design

Source: 32 reader notes in `notes/ch01.md` to `notes/ch32.md` and the readers' structured results. This file merges them. It adds no content from outside the notes. Page numbers are Handbook pages as the readers recorded them.

How to read the labels used below:

- **Handbook** marks what the chapters say.
- **Implemented grammars** marks what the chapters say about DELPH-IN or other implemented grammars. Most chapters say nothing; that is recorded as "not discussed".
- **Consequence** is a conclusion for our design. It is the readers' or this synthesis's inference, and the Handbook does not discuss our architecture.
- **Phase** says whether the point matters for the ERG phase, the multilingual phase, or both.
- Priority: P1 = can change the design or must be measured before the design is fixed; P2 = needs a decision or a check; P3 = record and move on.

One fact about the evidence base shapes everything below. Of the 32 chapters, only Chapter 25 (Bender and Emerson) describes implemented grammars in any detail, and Chapters 2, 4, 17, 21, 22, and 23 contain a few sentences each. Chapter 25 itself does not state that DELPH-IN grammars are limited to unary and binary rules, that they have no empty elements, or that a derivation tree determines the feature structure and the MRS. The three assumptions the design leans on most are therefore neither confirmed nor refuted by the Handbook. They have to be verified in the ERG source, Copestake (2002), and the Redwoods treebanks (see Section C).

---

## A. Caveats, grouped by design assumption

Groups are ordered by how much their leading caveat constrains the design. IDs are stable and are used in the theory log.

### A1. Leaves correspond to tokens

**LT-1. Right-Node Raising is analyzed by deletion; leaves without tokens, also below the word level. (P1, both phases)**

- Handbook: Ch. 16, Section 7, pp. 760-763: a syntactic, non-elliptical account is "harder to maintain"; the shared material can be missing from inside islands (78) and can be part of a word ("sole or co-author", (79)); rule (80) (Chaves 2014; Shiraishi et al. 2019) is a unary rule that splits a MORPHO-PHONOLOGY list into five sublists and drops one under PHON and LID identity; it applies outside coordination (83) and to discontinuous cases (84). Ch. 19, Section 6.2, pp. 873-876: Right Node Raising "has consistently attracted HPSG analyses involving silent material", order-domain based (Yatabe 2001, 2012) or deletion-like (Chaves 2014; Abeillé et al. 2016); Backward Periphery Deletion (59) "targets any linearized strings, whether constituents or otherwise". Ch. 29, Section 4.2.4, pp. 1367-1368: the literature agrees that the phenomenon is not unitary and that some of it needs surface ellipsis.
- Implemented grammars: not discussed in any of the three chapters. Chaves (2014) reassigns part of the data to extraposition (EXTRA) and to VP or N' ellipsis, which need no deletion (Ch. 19, p. 875, fn. 31).
- Consequence: this is the one English construction for which the Handbook reports no surface-only HPSG analysis. Before fixing the tree encoding, find out how the ERG derives these sentences in Redwoods (continuous, token-leaved, or not covered) and count them. If the ERG derivation is continuous, the encoding is unaffected and the theory problem moves to the semantics. If such sentences are uncovered, they define part of the workload of the relaxed output. Word-part sharing ("under- and overgenerates") is a tokenization question to settle together with LT-3.

**LT-2. Argument cluster coordination has an elliptical analysis in which the rule name does not fix how much is elided. (P1, both phases)**

- Handbook: Ch. 16, Section 7, pp. 756-757: constraint (71) lets left-edge material of a non-initial coordinand be absent from the mother; example (72) shows that different amounts of elided material give different meanings for one string. Ch. 19, Section 6.3, pp. 876-877: Coordination Schema (63) works on order-domain (DOM) lists; the same schema yields plain coordination, cluster coordination, or both-edge ellipsis. Ch. 29, Section 4.2.1, pp. 1361-1363: both representative analyses (Beavers and Sag 2004; Yatabe 2001, Yatabe and Tam 2021) need a stipulation to get the scope of a shared quantifier right.
- Implemented grammars: not discussed. The surface-true alternative is Mouret (2006): cluster phrases plus a lexical rule on the verb (Ch. 16, pp. 757-760; Ch. 19, p. 876). The cluster phrase is n-ary and non-headed.
- Consequence: under the Mouret analysis the construction fits the design after binarization, with one more lexical rule in the label chain. Under the elliptical analysis it does not fit at all. Check which one the ERG uses. For our own grammars, adopt the cluster analysis.

**LT-3. One lexical entry can span several tokens; real text needs token mapping before tagging. (P1, ERG phase)**

- Handbook: Ch. 25, Section 2.2.2, p. 1112, and Section 3.2, pp. 1117-1118: for multiword expressions such as "by and large" the grammar assigns one lexical entry to several tokens; real text also needs unknown-word handling, markup handling, and external analyzers. Ch. 17, Section 2, p. 779, and Section 4.3, pp. 791-792: fixed idioms are "words with spaces" (Sag et al. 2002); syntactically irregular idioms get phrasal lexical entries with unspecified internal structure.
- Implemented grammars: solved in DELPH-IN by ubertagging (Dridan 2013), which predicts a segmentation jointly with supertags (Ch. 25, p. 1112). The token-mapping machinery itself is not described.
- Consequence: the design statement "leaves correspond to tokens" has to be restated as "leaves correspond to grammar segments, and the tagger predicts the segmentation". The label scheme needs a segmentation component (for example a continuation label for non-initial tokens of a multi-token leaf). This is a design change for the ERG phase, with a direct precedent.

**LT-4. Pronominal clitics and other argument markers are analyzed as affixes; the argument has no leaf. (P2, multilingual phase)**

- Handbook: Ch. 1, Section 4.1, pp. 16-17; Ch. 4, Section 3.2, pp. 136-137, and Section 5.3, pp. 160-161 (Miller and Sag 1997: French "y va" is one entry); Ch. 11, Section 3, pp. 427-430, and Section 4.3, pp. 443-445 (a climbed clitic is realized on a different word from the predicate whose argument it is); Ch. 21, Section 4.4, pp. 982-984 (Romance clusters as verbal inflection); Ch. 18, Section 3, pp. 825-827 (negators as affixes); Ch. 5, Section 2.1, pp. 180-184, Ch. 9, Section 3.1, pp. 320-321, Ch. 7, p. 252.
- Implemented grammars: not discussed.
- Consequence (readers' inference; the chapters do not discuss tokenization or UD): where a treebank splits the clitic off, HPSG leaves and UD words disagree. The per-language bridge needs an explicit token-to-leaf alignment table, and the lexical-rule chain in the label must encode the affixal arguments. Safe to ignore for the ERG, except for the English items in LT-6.

**LT-5. Word-internal discontinuity: endoclitics, word-part ellipsis, signs below the word. (P3, multilingual phase)**

- Handbook: Ch. 4, Section 2.2, pp. 131-134 (Udi and Pashto endoclitics analyzed with discontinuous lexical items and order domains; word-part ellipsis via a structured morphophonology list; lexical sharing left open for Turkish); Ch. 21, p. 949 and p. 958 (word-syntactic and morpheme-based proposals), Section 4.4 (Sorani Kurdish, Portuguese mesoclisis); Ch. 29, p. 1352, fn. 16 (Lexical Integrity is not assumed by all HPSG analyses).
- Implemented grammars: not discussed.
- Consequence: rare; record per language when it comes up.

**LT-6. English possessive 's is a syntactic word in the specifier treatment. (P3, ERG phase)**

- Handbook: Ch. 8, Section 2.1.3, pp. 283-284 and fn. 8 (a determiner heading a DetP); fn. 20, p. 299 (Malouf 2000: a genitive).
- Implemented grammars: not discussed. Contracted "n't" is not discussed anywhere in the Handbook (reader remark, Ch. 18).
- Consequence: read the ERG's choice off the grammar; it fixes the token inventory.

**LT-7. Spoken and multimodal input. (P3, out of scope)**

- Handbook: Ch. 26, Section 1, pp. 1156-1157 (disfluencies, laughter, overlap); Ch. 27, Section 3.2, pp. 1212-1214 (gesture leaves on a second layer, rules conditioned on timing and prosody).
- Consequence: transcribed speech would go to the relaxed output as the normal case. Ignore for now.

### A2. No empty elements

**EE-1. The continuous analysis of verb placement in German and Germanic uses an empty verbal head. (P1, multilingual phase)**

- Handbook: Ch. 10, Section 5.1, pp. 384-386 (unary rule on the verb, head feature DSL, an empty lexical element with PHON < >; the majority analysis for German, also used for Dutch and Danish), and Section 8, pp. 403-404; Section 6.4.2, pp. 398-401 (apparent multiple fronting: sketch (49) has three empty positions in one clause). Ch. 28, Section 4.2.1, p. 1288: the analogue of head movement "is standard among HPSG grammarians of German" and multiple fronting makes it "unavoidable". Ch. 5, Section 4.1, p. 196; Ch. 30, Section 5, pp. 1406-1407 (Borsley 1989); Ch. 23, Section 6, pp. 1068-1069 (analyses of German fronting built on it).
- Implemented grammars: not discussed in Ch. 10. Trace-free alternatives named there: the flat constructional analysis (Sag et al. 2020) and linearization. Ch. 28, fn. 27, p. 1284: empty heads can model the effect of unary projections (pointer to Müller 2016, Sections 19.2 and 19.5). Ch. 32, pp. 1503-1504: any phrase structure grammar with empty elements can be translated into one without (Bar-Hillel, Perles and Shamir 1961).
- Consequence: the mainstream German analyses give continuity or tracelessness, not both (Ch. 10 reader). For the multilingual phase we need a stated policy: compile the verb trace into a unary rule on the clause, or fold it into a neighboring label. The multiple-fronting case, with two adjacent empty positions, is the stress test. No effect on the ERG unless the ERG uses a head-movement analysis of inversion, which has to be checked.

**EE-2. Traces at gap sites remain a live option in the theory. (P2, both phases)**

- Handbook: Ch. 13, Section 2, p. 540, Section 3, pp. 543-549, Section 10, p. 582 (both analyses exist; listed by the authors as unresolved; traces in Pollard and Sag 1994 for complements, Levine and Hukari 2006 throughout, Borsley 2009/2013, Müller 2004). Ch. 1, Section 2, pp. 5-7 ("some debate"); Ch. 2, pp. 59-61 (both analyses appear in Pollard and Sag 1994); Ch. 4, p. 165 and fn. 12 (CoreGram cited among trace-based approaches); Ch. 15, p. 668; Ch. 30, p. 1418; Ch. 32, pp. 1502-1504 (Müller defends empty elements when there is language-internal evidence); Ch. 22, pp. 1007-1009 (Pollard and Yoo's scope theory covers only trace-based extraction); Ch. 23, p. 1047.
- Implemented grammars: no chapter says whether the ERG uses traces. Ch. 13 calls the traceless view "probably the most widely assumed position".
- Consequence: harmless for a traceless grammar. For trace-based grammars (CoreGram, EE-4) a conversion step is needed. Verify in the ERG.

**EE-3. Other empty elements: empty relativizer, null complementizer, empty copula. (P3, both phases)**

- Handbook: Ch. 14, Section 2.2, pp. 607-609, and Section 3.3.2, p. 632: Pollard and Sag (1994, Ch. 5) use an empty relativizer; a purely lexical, non-constructional account of bare relatives without empty elements is impossible. Ch. 13, p. 545 fn. 4, pp. 557-558 (empty copula for AAVE, null complementizer for zero relatives). Ch. 32, p. 1535; Ch. 31, p. 1477 (covert verb as one option for verbless clauses).
- Implemented grammars: not discussed. The dominant analysis (Sag 1997) has no empty elements and uses phrasal unary constructions instead (see TE-3).
- Consequence: the price of tracelessness is unmarked unary constructions that the tagger must predict.

**EE-4. Grammars outside DELPH-IN use empty elements and more. (P2, multilingual phase)**

- Handbook: Ch. 25, Section 3.1, p. 1115, and Section 3.2, p. 1117: CoreGram grammars run on TRALE, which accommodates empty elements, relational constraints, implications with complex antecedents, and cyclic feature structures.
- Consequence: our replay engine targets the DELPH-IN formalism. CoreGram grammars are a source of analyses, and they cannot be loaded as they are.

### A3. Derivations are continuous

**CO-1. Order domains decouple word order from the tree. (P1, multilingual phase)**

- Handbook: Ch. 10, Section 6, pp. 390-397 (DOM lists, shuffle, liberation for Warlpiri, partial compaction; the tree "does not correspond to the linearization of the DOMAIN objects"); Ch. 1, Section 7.1, pp. 32-34 ("an unresolved matter"); Ch. 2, pp. 50-52; Ch. 11, Section 5.2.1, p. 464 (domain union still needed for scrambling with Korean control verbs); Ch. 29, Section 3.3.1, pp. 1355-1357; Ch. 30, Section 10, pp. 1420-1423 (Donohue and Sag 1999); Ch. 31, Section 4.4, pp. 1471-1474; Ch. 5, pp. 196-197; Ch. 28, p. 1258.
- Implemented grammars: Ch. 25, Section 3.3.3, pp. 1119-1120: Babel, a broad-coverage German grammar, makes extensive use of discontinuous constituents (Müller 2004), with worse worst-case complexity and no apparent practical penalty. Ch. 14, fn. 54: Müller (2004) preferred linearization for computational reasons and later abandoned it for theoretical ones. Ch. 10, Section 7: Bender (2008) handles Wambaya with continuous constituents through non-cancellation of arguments. For DELPH-IN: not discussed.
- Consequence: no effect on the ERG. For the multilingual phase, restrict targets to grammars with a context-free backbone, and treat non-cancellation (UD-4) as the continuous route for free-order languages. Readers disagree on severity for English: Ch. 31's reader rates continuity "medium for English", the others "low"; the Handbook gives English order-domain analyses only for the items in CO-3.

**CO-2. Extraposition has four coexisting analyses. (P2, both phases)**

- Handbook: Ch. 13, Section 8, pp. 572-579; Ch. 14, Section 4.1, pp. 637-639 ("little to choose" between them); Ch. 10, Section 6.3, pp. 395-397 and fn. 14; Ch. 15, Sections 5-6, pp. 677-680 (no syntactic bound on EXTRA; no detailed account of extraposition islands in any framework). The analyses: order domains with partial compaction (Kathol and Pollard 1995); a nonlocal EXTRA feature with lexical rules at the source word and an n-ary Head-Extra Schema (Keller 1995; Müller 1999; Bouma 1996); anaphoric ANCHOR percolation, where the clause binds one of several candidate nominals (Kiss 2005); a hybrid (Crysmann 2013).
- Implemented grammars: Crysmann (2005) is cited as a synthesis of Kiss and Keller whose title says "an efficient and portable implementation" (Ch. 13, Ch. 14); the chapters do not describe it. Ch. 13 calls the order-domain analysis "highly questionable" for English.
- Consequence: English has extraposed relatives ("Someone might win who does not deserve it", Ch. 14). Under EXTRA the tree is continuous, the source noun's label carries a lexical rule whose only evidence is distant, and the UD attachment must be read from the feature structure. Under ANCHOR the tree may not fix the antecedent (see SE-3). Check the ERG's choice; read Crysmann (2005).

**CO-3. Residual order-domain analyses of English constructions. (P3, ERG phase)**

- Handbook: Ch. 14, Section 3.4, p. 636 (preposed supplemental relatives, Lee-Goldman 2012; no continuous alternative given); Ch. 16, Section 3.2, pp. 736-737 (floating "either", Hofmeister 2010); Ch. 10, pp. 390-391 (domains "still play a role" in ellipsis and coordination); Ch. 7, p. 263 (ellipsis accounts of unlike coordination stated over domains).
- Consequence: rare constructions; expect relaxed output unless the ERG has continuous analyses.

**CO-4. Constraints stated on linear order: superficial agreement, negator placement. (P3, multilingual phase)**

- Handbook: Ch. 6, Section 7.2, pp. 238-239 (Welsh agreement over DOM, Borsley 2009); Ch. 16, Section 4.3.1, pp. 748-750 (closest conjunct agreement; edge features LAGR/RAGR as a unification-only alternative); Ch. 18, Section 5, pp. 834-835 (topological fields for Italian and Welsh negation; a selectional alternative exists).
- Consequence: prefer the edge-feature or selectional variants in our grammars.

**CO-5. Split NPs and partial fronting. (P3, multilingual phase)**

- Handbook: Ch. 8, Section 3.5, p. 307 (extraction out of nominals, no analysis given); Ch. 23, Section 6, pp. 1063-1067 (German NP-PP split; the chapter does not say how it is derived); Ch. 32, Section 2, p. 1522 (partial VP fronting handled with Categorial-Grammar-like valence, trees kept).
- Consequence: check De Kuthy (2002) before judging.

### A4. Rules are unary or binary

**BU-1. Theoretical HPSG, especially for English and French, assumes flat structures. (P2, both phases)**

- Handbook: Ch. 10, Section 3, pp. 375-377 (researchers on English and French "usually assume a flat structure"), Section 5.2, pp. 386-387 (ternary auxiliary-initial clause, Sag et al. 2020); Ch. 1, Section 5.1, pp. 22-23, Section 5.2, p. 29; Ch. 12, Section 4.1, p. 524 (non-binary initial-aux-ph; fn. 25 gives the two-complement alternative); Ch. 16, Section 3, pp. 729-732 (three coordination structures; the authors hold that no internal structure is motivated); Ch. 5, Section 4.2, pp. 197-200 (Head-All-Valents for VSO); Ch. 11, Sections 4.2-4.3, pp. 436-444 (the Italian flat VP is argued for empirically against the Spanish cluster); Ch. 18, pp. 820-824; Ch. 28, Section 4.2.1, pp. 1284-1288 (flat and binary both "viable"); Ch. 30, p. 1407; Ch. 3, p. 100 (a schema may leave the number of daughters unspecified); Ch. 2, pp. 58-60; Ch. 8, p. 291; Ch. 32, p. 1513.
- Implemented grammars: Ch. 1, fn. 30: binary branching has been assumed in HPSG grammars for a number of languages. Ch. 10, p. 379: binary schema (19) can be parameterized for English. Drellishak and Bender (2005) are listed among binary coordination analyses (Ch. 16, p. 729). Ch. 25 gives the parsing complexity for a general maximum rule arity and does not state that DELPH-IN rules are at most binary.
- Consequence: binary-plus-unary is a property of particular grammars. Comparing ERG derivations with the theoretical literature, and converting any flat-tradition grammar, needs a declared binarization convention. The convention must keep distinctions that the literature encodes by flatness (Italian flat VP versus Spanish verb cluster, readers' inference in Ch. 11).

**BU-2. Variable-arity and headless constructions. (P3, both phases)**

- Handbook: Ch. 32, Section 4.1, pp. 1530-1534 (NPN: an unbounded DTRS list, no head; Müller argues a binary head-driven analysis would need several idiosyncratic lexical items); Ch. 28, pp. 1290-1291; Ch. 31, pp. 1476-1477; Ch. 19, Section 6.1, pp. 870-873 (gapping cluster "XP+"); Ch. 13, pp. 573-574 (n-ary Head-Extra Schema).
- Implemented grammars: not discussed.
- Consequence: rare in text; check ERG treatment of "day after day"; otherwise relaxed.

### A5. The derivation tree is a complete, search-free recipe (deterministic replay)

**DR-1. Non-canonical argument realization may have no rule node. (P1, both phases)**

- Handbook: Ch. 13, Section 2, pp. 540-541, Section 3, pp. 544, 546-547: in the mainstream traceless analysis the gap is only on ARG-ST and the slashed verb has a shorter COMPS list; no rule is named. Ch. 9, Section 3.1, pp. 320-321: exceptions to the Argument Realization Principle are handled by a lexical rule, or by a feature on each ARG-ST item with no rule (Bouma et al. 2001). Ch. 4, Section 5.2, pp. 158-159, Section 5.3, pp. 159-165: the Complement Extraction Lexical Rule and Monachesi's clitic rule are relational (any COMPS member), and the underspecification alternative has no rule at all; "no general guideline" for choosing. Ch. 1, pp. 16-17 (the authors decline to fix the form of the principle); Ch. 5, pp. 185-186; Ch. 13, pp. 560-567 (resumptives: the choice is made on the head).
- Implemented grammars: Ch. 4, p. 156: lexical rules are unary-branching rules in the ERG, CoreGram, and Grammix. No chapter says how the ERG introduces gaps or optional arguments. Named lexical rules are shown for extraposition only (Ch. 13, pp. 573-574).
- Consequence: replay is deterministic only if every such choice is a named unary step or is forced by later unification. For the ERG this is a check: for each of extraction, argument drop, and VP ellipsis, confirm that a rule name records the choice and that the rule identifies which argument is affected. For our own grammars it is a design rule: no free choice inside the word.

**DR-2. A binary head-complement rule may discharge any element of COMPS. (P1, multilingual phase)**

- Handbook: Ch. 10, Section 3, pp. 379-380 (schema (19) splits COMPS with two appends and realizes "an arbitrary element"); Ch. 11, Section 5.1.2, pp. 456-457 (schema (38), "with the relevant one in any position"; finite subjects are on COMPS too).
- Implemented grammars: not discussed. For fixed-order languages the schema is restricted to the first element (Ch. 10, p. 379), so English is unaffected.
- Consequence: for German-type grammars the rule label must carry the position of the discharged complement, or replay needs a bounded search. With case syncretism one tree can otherwise license several feature structures. Design decision for the multilingual phase: index the rule name by position.

**DR-3. The theory's descriptions use sets, relations, and defaults beyond plain unification. (P2, both phases)**

- Handbook: Ch. 3, Section 2, pp. 93, 96-98, Section 3, pp. 101-105: rendering Pollard and Sag (1994) needs negation, disjunction, quantification, relations (append, member, shuffle, set operations), and chains; phrase structure rules, lexical rules, and defaults are meta-notation outside the logic (pp. 89-90, 100). Sets and set union: Ch. 1, pp. 13, 24; Ch. 13, pp. 540-543, 549-551, 567-569; Ch. 14, pp. 609-613. Defaults: Ch. 1, pp. 23-24 (Generalised Head Feature Principle); Ch. 13, pp. 549-550, 556, 560; Ch. 14, fn. 25; Ch. 4, pp. 150-155; Ch. 17, fn. 23 (defaults and probabilities are not a well-defined part of the formal foundations). Relations in schemata: Ch. 10, pp. 375-379, 391, 396, 398; Ch. 11, pp. 427, 441, 444, 456; Ch. 12, pp. 499, 510, 526; Ch. 23, pp. 1053-1054, 1062-1065; Ch. 21, pp. 968-974 (Information-based Morphology).
- Implemented grammars: Ch. 3, p. 93: partial feature structures and unification "are still essential for all current HPSG implementation platforms". Ch. 25, p. 1109 and fn. 9: the boundedness argument for DELPH-IN grammars assumes no relational constraints; SLASH has at most one element in the ERG; no DEPS list. Ch. 23, p. 1047: the Grammar Matrix uses difference lists for RELS, HCONS, and ICONS. Ch. 4, fn. 10: defaults can be compiled away (Malouf 2000). Ch. 21, p. 960: few versions of HPSG support default inheritance.
- Consequence: a small unification engine suffices for DELPH-IN grammars as the Handbook describes them. "Licensed by the grammar" then means licensed by the implementation formalism, which is the 1987-style logic of partial information and not the 1994 model theory (Ch. 3, pp. 90-93). Grammars from the theoretical tradition need compilation first. One limit of the ERG follows from the one-element SLASH: sentences with two simultaneous dependencies (Ch. 13, examples (16), (47); Ch. 15, pp. 680-681) are outside it.

**DR-4. Argument attraction leaves the head's valence open until the complement is known. (P2, multilingual phase)**

- Handbook: Ch. 11, Section 3, pp. 426-428, Section 5.1.2, p. 458 (German attracts from COMPS because of partial VP fronting), Section 4.1, pp. 432-433 (lexical rules whose input condition is met only through inherited arguments); Ch. 12, p. 499 fn. 8, p. 519 fn. 21; Ch. 9, Section 6, pp. 351-353; Ch. 18, Section 4, pp. 828-832 (argument composition in the syntax).
- Implemented grammars: not discussed.
- Consequence: the lexical type of an attracting head cannot encode a fixed frame; replay validates lexical rules late. Not an issue for English (Ch. 11, fn. 26).

**DR-5. Principles that are not attached to any rule application. (P2, both phases)**

- Handbook: structural case resolved by a separate principle (Ch. 7, Section 2, pp. 249-254); binding principles with dominance, recursion over ARG-ST, and list threading (Ch. 20, pp. 897-898, 908-915, 927-932); global well-formedness of total objects (Ch. 3, pp. 107-108, 114); idiom licensing over arbitrary depth (Ch. 17, pp. 788-793); constraints on unembedded signs only (Ch. 23, p. 1061, p. 1072); Paninian blocking, which "necessitates a change to the logic" (Ch. 21, pp. 963-964, 971-974); the Raising Principle as a constraint on the lexicon (Ch. 12, pp. 500-502); focus projection as a disjunctive principle on every phrase (Ch. 23, pp. 1053-1055).
- Implemented grammars: Grammar Matrix case systems are compiled into lexical types (Ch. 7, p. 264). Idioms are checked after parsing from semantic representations (Ch. 17, fn. 21, Flickinger 2015). Whether the ERG enforces any binding principle is not discussed. Blocking: not discussed.
- Consequence: three checks follow. (a) Replay needs an explicit root step. (b) If blocking is not compiled into rule descriptions, a regular rule wrongly tagged on an irregular stem replays successfully; test with deliberately wrong tags. (c) Strict output should make no claim about binding or idiom well-formedness unless the grammar encodes it.

**DR-6. Strict identity requirements reject grammatical input. (P2, both phases)**

- Handbook: filler-gap LOCAL identity fails for "the person who I spoke to" under the nominative analysis and for auxiliary-stranding relatives (Ch. 14, pp. 620-622, 635-636; Ch. 13, Section 9, pp. 580-582; Ch. 30, pp. 1405-1406); CAT identity across coordinands mispredicts for INV, AUX, and SLASH (Ch. 16, Section 4.1, pp. 741-745); coordination of unlike categories (Ch. 16, Section 6, pp. 753-756); case syncretism needs enriched type hierarchies, which grow double exponentially for unlike-case coordination (Ch. 7, Section 3, pp. 256-263; Ch. 14, pp. 643-646; Ch. 29, pp. 1357-1358); the Head-Fragment Schema wrongly rules out attested case mismatch (Ch. 19, p. 868); pied-piping constraints err in both directions (Ch. 14, pp. 601-605).
- Implemented grammars: not discussed. Syncretism reduces to ordinary typed unification over a suitable hierarchy (Ch. 7, p. 258; Ch. 16, Figure 9).
- Consequence: these are predictable places where strict replay fails on good sentences. Log replay failures by rule and feature path; a cluster at filler-gap or coordination identity points here.

**DR-7. Strict means grammar-licensed, which differs from acceptable; and coverage is partial. (P2, ERG phase)**

- Handbook: Ch. 15 throughout (nearly every island constraint has accepted counterexamples; HPSG "remains relatively agnostic about many island types"; Section 14, pp. 700-701); Ch. 24, Section 4.1, pp. 1092-1094; Ch. 29, p. 1359; Ch. 28, p. 1305. Coverage: Ch. 25, Section 4.1.4, p. 1124, Section 4.2.2-4.2.3, pp. 1126-1127 (the grammar does not cover all text; grammar-based treebanks contain only covered items); Ch. 2, pp. 66-70. Mal-rules: Ch. 25, Section 4.2.1, pp. 1124-1125 (a mal-rule is treated like a normal rule in parsing).
- Implemented grammars: robust processing exists for uncovered sentences (Zhang and Krieger 2011; Buys and Blunsom 2017; Chen et al. 2018). Which island constraints the ERG imposes is not discussed.
- Consequence: define "strict" as "replays under grammar version V with rule set R", with mal-rules excluded or flagged. The tagger's training data is biased toward covered sentences; measure tagger behavior on sentences the ERG rejects.

**DR-8. In ID/LP format the rule does not fix daughter order. (P3, multilingual phase)**

- Handbook: Ch. 10, Section 2, pp. 371-375, Section 3, pp. 376-377 (the Constituent Order Principle "was never worked out in detail"); Ch. 18, pp. 815-818; Ch. 5, pp. 197-200; Ch. 3, p. 101.
- Consequence: compile LP rules into ordered rule variants. Bookkeeping, as long as constituents are continuous.

### A6. Semantics (MRS) is a by-product of replay

**SE-1. For fragments, sluices, gapping, and ellipsis the content comes from context. (P1, both phases)**

- Handbook: Ch. 19, Section 4, pp. 860-864: the Head-Fragment Schema (31) is a unary rule whose content is supplied by MAX-QUD and SAL-UTT; all existing HPSG analyses of fragments are based on it. Ch. 15, Section 13, p. 700 (sluicing: a unary construction "that taps into contextual information"). Gapping by direct interpretation: Ch. 16, Section 7, pp. 763-764; Ch. 19, Section 6.1, pp. 870-873; scope anomalies, Ch. 29, Section 4.2.2, pp. 1364-1366. VP ellipsis as a pro argument on ARG-ST with no content: Ch. 12, Section 4.2, pp. 525-526; Ch. 18, Section 2.3, pp. 819-822; Ch. 19, Section 5, pp. 868-870. Dialogue: Ch. 26, Section 2.4, pp. 1165-1166, Section 4, pp. 1176-1181.
- Implemented grammars: not discussed in any of these chapters.
- Consequence: the trees fit the design (unary rule, no empty leaf). The MRS from sentence-level replay is incomplete for these constructions, and that should be the documented contract: strict output may contain unresolved anaphoric predications. Decide what the MRS contains at an ellipsis site (check the ERG) and keep ARG-ST-level information available for a later resolution component (Ch. 19, pp. 854-855, sprouting).

**SE-2. A derivation fixes one underspecified MRS; scope is resolved elsewhere. (P3, both phases)**

- Handbook: Ch. 22, Section 6.1, pp. 1019-1023 (resolution is better left to a separate algorithm outside the grammar, p. 1021); Ch. 26, p. 1171; Ch. 28, pp. 1264-1265; Ch. 29, pp. 1354-1355; Ch. 30, pp. 1426-1428. Under Cooper storage the tree does not determine retrieval: Ch. 22, Section 3.1, pp. 1005-1009; Ch. 13, pp. 569-571; Ch. 8, pp. 282-283; Ch. 3, pp. 97-98. Under Lexical Resource Semantics one syntactic structure admits several semantic values (Ch. 22, Section 6.2, pp. 1026-1034).
- Implemented grammars: MRS composition per rule is list append plus a semantic head fixed per construction type (Ch. 22, rule (39), pp. 1023-1024).
- Consequence: consistent with the design. Readers differ in the severity they give Cooper storage (low in Ch. 22, medium in Ch. 13); it does not apply to MRS-based grammars. The replay engine is tied to MRS-style composition and cannot serve storage- or LRS-based grammars.

**SE-3. Cases where one tree leaves a semantic link open. (P2, both phases)**

- Handbook: the antecedent of a relative clause under Kiss's ANCHOR analysis (Ch. 13, Section 8.3, pp. 575-579; Ch. 14, p. 638); adverb scope inside a German coherence field (Ch. 11, pp. 455-456, 459-460); negative concord versus double negation by quantifier retrieval at the verb (Ch. 18, pp. 837-838), and identity of contributions across words, for which no MRS analysis is given (Ch. 22, pp. 1031-1033); long-distance agreement (Ch. 6, pp. 236-238); summed "pluralic" gaps (Ch. 15, pp. 670-671, 689); sublexical scope of "again" (Ch. 9, pp. 334-337); internally headed relatives (Ch. 14, pp. 641-643); the semantics of coordination, set aside by Ch. 16 (fn. 5, p. 733); binding, which the tree never determines (Ch. 20, pp. 889-899, 927-932).
- Implemented grammars: not discussed, except that Branco's representation is compared with MRS (Ch. 20, p. 927).
- Consequence: for each case the grammar either underspecifies (fits) or makes the choice a rule name (fits, with a tagging cost). Check the English cases in the ERG: extraposed relatives, modifier scope, coordination scope.

**SE-4. Construction and clause-type meaning. (P2, both phases)**

- Handbook: Ch. 10, Sections 5.2-5.3, pp. 386-390 (clause-type meaning from phrasal subtypes, lexical items, or implicational constraints that look at the configuration or at intonation; fn. 12: a clause-level unary rule, Ginzburg and Sag 2000); Ch. 22, Section 5, pp. 1016-1018 ("quite a few" unary constructions whose function is strictly semantic; Müller 2015 as the lexical alternative); Ch. 14, Section 3.4, pp. 633-636 (restrictive versus non-restrictive relatives: same syntax, two modes of combination); Ch. 32, pp. 1499-1500, 1531-1535; Ch. 16, pp. 737-740.
- Implemented grammars: C-CONT is mentioned only for the Grammar Matrix information-structure rules (Ch. 23) and gesture rules (Ch. 27); how ERG rules contribute predications is not described in the Handbook.
- Consequence: semantics is a by-product only where each meaning-bearing construction is a named rule. The tagger then has to choose among rules with identical strings ("Are they crazy?" versus "Are they crazy!"). A wrong choice still replays. This needs a semantic-accuracy metric separate from replay success.

**SE-5. Meaning distinctions whose cue is prosody. (P3, both phases)**

- Handbook: Ch. 23, Section 3, pp. 1049-1058 (focus projection; accent-driven lexical rules in Song 2017), Section 2, pp. 1046-1049 (index-valued information structure cannot single out a modifier); Ch. 15, pp. 694-695 (accented wh-entries); Ch. 12, pp. 522-524 (unstressed "do"); Ch. 10, pp. 388-390; Ch. 24, p. 1086; Ch. 26, pp. 1161-1162.
- Implemented grammars: Song and Bender (2012) and Song (2017), in the Grammar Matrix, leave the ICONS type underspecified: one MRS, one syntactic structure (Ch. 23, pp. 1056-1057).
- Consequence: follow the underspecification route; do not load accent-driven rules when parsing text.

**SE-6. Idioms. (P2, ERG phase)**

- Handbook: Ch. 17, Section 4, pp. 784-794: analyses disagree on where the idiomatic meaning comes from; lexical accounts add homophonous idiomatic entries selected through LID.
- Implemented grammars: fn. 21, p. 790: free occurrence of idiomatic words "is not an issue for parsing"; Flickinger (2015) identifies idioms from bits of semantic representation in parser output. Ch. 32, fn. 10, p. 1508: local selection with LEXICAL IDENTIFIER was part of the CSLI grammar fragment.
- Consequence: strict replay may yield literal predicates with idioms identified afterwards. Decide whether the post-parse idiom check is part of "strict".

**SE-7. Material in MRS with no token; dependency reductions lose information. (P3, ERG phase)**

- Handbook: Ch. 25, Section 2.2.3, pp. 1112-1114 (abstract predicates such as udef_q and compound; EDS, DMRS, and DM each drop something). Arguments with no token: Ch. 6, pp. 222-223; Ch. 9, pp. 320-321, 348-349; Ch. 12, pp. 509-510. Per-constituent contents are not kept in the final structure (Ch. 26, Section 3.1, pp. 1167-1169).
- Consequence: evaluate on MRS-level metrics as well as token-level ones. Recording the semantic contribution of each replay step is cheap and answers the Ch. 26 point (reader's inference).

### A7. Tree encoding and the label inventory

**TE-1. The tagger carries the whole disambiguation burden, and lexical types cover about half of it. (P1, ERG phase)**

- Handbook: Ch. 25, Section 2.2.2, pp. 1110-1112, Section 5.1, pp. 1128-1129: the 2018 ERG gives 21 readings for a five-word sentence and 35,094 for one newspaper sentence; in Redwoods about half the ambiguity is lexical and half syntactic; a supertagger sometimes predicts the wrong entry.
- Implemented grammars: supertagging and ubertagging prune before chart parsing; a separate treebank-trained model ranks the remaining parses (Toutanova et al. 2002, 2005).
- Consequence (reader's inference from these figures): in a search-free design the structure bits and unary chains must carry the syntactic half. Measure exact-derivation accuracy separately for lexical type, unary chain, and structure bits. Keep an n-best or small-beam variant of replay as a fallback to compare against.

**TE-2. Zero-marked lexical rules whose evidence is elsewhere in the sentence. (P2, both phases)**

- Handbook: lexical rules feed each other and carry voice, valence change, and type shifting (Ch. 9, pp. 316, 345-346, 351-358; Ch. 28, fn. 27 and p. 1293; Ch. 32, pp. 1521-1530); extraposition rules on the source noun (Ch. 13, pp. 573-574); extraction-path marking (Ch. 13, pp. 545-546, 550-551); "dont" and subject extraction rules (Ch. 14, pp. 622-626); adverb-complement and ellipsis rules (Ch. 18, pp. 820-821); focus-projection rules (Ch. 23, pp. 1057-1058); passive on a verb with no object of its own (Ch. 11, pp. 432-433, 455-456); case fixed by a verb far up a raising chain (Ch. 7, pp. 247-254).
- Implemented grammars: Goodman and Bender (2010) on stating dependencies between morphological rules (Ch. 21, p. 959).
- Consequence: this confirms the label format and predicts where the label space is sparse. Measure the distribution of unary chains in Redwoods (length, frequency rank, unseen-chain rate on held-out data).

**TE-3. Phrasal unary rules with no surface cue. (P2, both phases)**

- Handbook: bare relatives (Ch. 14, Section 3.3.2, pp. 629-632: a unary node above a whole clause); zero relatives (Ch. 13, p. 558); semantic type-shifting constructions (Ch. 22, pp. 1016-1018; Ch. 28, fn. 27); clause-type rules (Ch. 10, fn. 12); metonymy (Ch. 6, pp. 233-234); fragments (Ch. 19); sluicing (Ch. 15, p. 700); LIGHT-changing head-only phrase (Ch. 11, fn. 13).
- Consequence: the encoding must place unary chains at phrasal nodes of any height, and the tagger must predict them from context. Replay detects a missing node and cannot repair it (Ch. 14 reader). Measure phrasal-unary recall separately.

**TE-4. One string, several derivations with the same or nearly the same meaning. (P2, both phases)**

- Handbook: "could not approve" (modifier versus complement "not", Ch. 18, pp. 816-821); restructuring verbs with two descriptions and "no evident semantic distinction" (Ch. 11, pp. 422-423, 431-436); spurious ambiguity from relaxed schemata and from Kathol's grammar (Ch. 10, p. 382 fn. 7, pp. 397-398); string-vacuous extraposition (Ch. 13, fn. 39); lexical coordination versus Right-Node Raising (Ch. 16, pp. 750-753); raising and control share one tree and differ only in lexical type (Ch. 12, pp. 497-505); fragment clause types (Ch. 19, pp. 860-861).
- Implemented grammars: treebanking exposes spurious ambiguity in the grammar (Ch. 25, p. 1124).
- Consequence: the treebank's canonical choice is what the tagger learns. A wrong lexical type for raising versus control often still unifies and gives wrong roles. Report semantic accuracy conditional on replay success.

**TE-5. The inventories are open in the theory. (P3, multilingual phase)**

- Handbook: derivation is unbounded and derivational rules are recursive (Ch. 21, pp. 949, 954, 961); recursive unary rules are possible in the formalism (Ch. 25, pp. 1108-1109); online type construction means lexical types need not be declared (Ch. 4, pp. 161-164; Ch. 21, pp. 952-954); Information-based Morphology has no rule chain (Ch. 21, Section 4.1, pp. 965-969); the ERG has over 60 types for raising and control predicates (Ch. 25, p. 1129); many construction-specific phrase types (Ch. 28, pp. 1257, 1267, 1276-1280).
- Implemented grammars: grammar implementation "typically follows" the Item-and-Process line, with LKB character unification attached to unary lexical rules (Ch. 21, pp. 958-959).
- Consequence: for DELPH-IN grammars the chain model holds. A grammar written in Information-based Morphology would need a different label (a set of rules or a property set).

**TE-6. Derivations are tied to a grammar version. (P3, ERG phase)**

- Handbook: Ch. 25, p. 1112, p. 1124 (treebanks are updated with each release by replaying stored annotator decisions).
- Consequence: version the label vocabulary with the grammar; retrain per release.

### A8. Conversion between derivations and UD

**UD-1. Headedness is analysis-dependent, and some phrases have no head. (P1, both phases)**

- Handbook: coordination is non-headed (Ch. 16, Section 2, pp. 726-729; Ch. 28, pp. 1288-1290; Ch. 1, fn. 9); the head of a nominal differs across the specifier, DP, and functor treatments, as do bracketings of "so good a bargain" and "a hundred pages" (Ch. 8, Sections 2-3, pp. 278-306); determiners and complementizers: "no consensus" (Ch. 1, pp. 31-32); relative "that" as marker, pronoun, or complementizer (Ch. 14, pp. 620-622); free relatives have no consistent head (Ch. 14, pp. 643-646; Ch. 13, pp. 559-560); headless schemata (Ch. 20, pp. 900, 912; Ch. 31, pp. 1474-1478; Ch. 32, pp. 1530-1534); syntactic versus semantic head in head-adjunct structures (Ch. 22, pp. 1009-1012); weak heads (Ch. 8, pp. 304-306); negator as head of a verb complex (Ch. 18, pp. 828-834). Dependency theories themselves differ on heads (Ch. 31, p. 1458).
- Implemented grammars: not discussed.
- Consequence: the bridge needs a head table per grammar and per rule, with explicit conventions for headless rules. It cannot be derived from "head daughter" alone.

**UD-2. HPSG has no uniform formal notion of subject; ARG-ST order and grammatical function come apart. (P2, multilingual phase)**

- Handbook: Ch. 30, Section 4, pp. 1404-1405; Ch. 9, Section 3.3, pp. 323-325 (Balinese and other voice systems); Ch. 12, pp. 510-513; Ch. 20, pp. 918-922; Ch. 10, Section 4, pp. 380-383 (German subjects of finite verbs on COMPS; SPR versus SUBJ for English); Ch. 5, pp. 200-202; Ch. 7, pp. 264-265; Ch. 31, pp. 1480-1484.
- Consequence: read relations from valence saturation plus case, per grammar. No language-independent rule such as "first ARG-ST element = nsubj".

**UD-3. The dependency information in an HPSG analysis is a graph. (P2, both phases)**

- Handbook: one filler with several gaps (Ch. 13, pp. 543, 549-552; Ch. 15, pp. 666, 670-671; Ch. 28, pp. 1296-1298; Ch. 29, pp. 1340-1343); shared dependents in lexical coordination (Ch. 9, pp. 357-358; Ch. 16, pp. 750-753); multiple and mutual dependencies (Ch. 31, pp. 1478-1480); dependencies that end in a lexical entry with no filler (Ch. 13, pp. 555-558); filler-gap mismatches (Ch. 13, pp. 580-582).
- Consequence: basic UD loses information. Decide whether the bridge targets enhanced dependencies; in the UD-to-HPSG direction the sharing has to be recovered.

**UD-4. The argument/adjunct line and the attachment site move with the analysis. (P2, both phases)**

- Handbook: adjuncts as complements or on DEPS (Ch. 1, p. 30, "unresolved"; Ch. 7, pp. 254-256; Ch. 9, pp. 351-353; Ch. 13, pp. 548-549; Ch. 10, pp. 378-379; Ch. 20, pp. 910-912); the passive by-phrase with three statuses (Ch. 9, pp. 348-350); argument attraction puts the lower verb's dependents on the higher verb (Ch. 11); non-cancellation attaches the parts of a split NP to the verbal projection (Ch. 10, Section 7, pp. 402-403; Ch. 30, pp. 1423-1424); EXTRA (Ch. 15, pp. 677-680).
- Implemented grammars: DELPH-IN does not adopt DEPS (Ch. 25, fn. 9).
- Consequence: the bridge must read some relations from the replayed feature structure, not from tree shape or rule names.

**UD-5. Precedent for the bridge is thin. (P2, ERG phase)**

- Handbook: Ch. 25, Section 3.3.1, pp. 1118-1119, Section 4.1.4, p. 1123: the only HPSG-to-UD mapping mentioned is for Alpino (Bouma and van Noord 2017), starting from dependency graphs built in the feature structures. The nearest case for the other direction is Enju (Penn Treebank conversion with construction-specific rewriting). Ch. 30, p. 1428: Glue Semantics has been paired with UD (Gotham and Haug 2018).
- Consequence: no published ERG-derivation-to-UD conversion is cited in the Handbook (reader remark). Budget for construction-specific rules.

### A9. Relaxed output and coarse universal schemas

**RX-1. The theory does not provide universal schemas. (P2, multilingual phase)**

- Handbook: "grammars should be motivated on a language-specific basis" (Ch. 1, pp. 7-8; Ch. 28, pp. 1262, 1305-1306); Oneida may lack syntactic valence and ARG-ST (Ch. 5, pp. 186-188; Ch. 9, pp. 354-355; Ch. 28, p. 1306); early HPSG's few schemata were judged too simple (Ch. 28, pp. 1267, 1276-1280).
- Implemented grammars: the Grammar Matrix core and libraries, CoreGram's shared constraint sets, and Enju's small set of hand-written schemata are existing coarse inventories; both projects treat the core as revisable (Ch. 25, pp. 1115-1121).
- Consequence: present the relaxed schemas as an engineering approximation. Start from the Grammar Matrix core.

**RX-2. Coarse schemas do not determine semantic composition. (P2, both phases)**

- Handbook: Ch. 22, Section 1, pp. 1001-1002, and Section 6.1.2, pp. 1023-1024: every Semantics Principle is a list of cases; the semantic head is fixed per construction type (intersective versus scopal). Ch. 32, pp. 1499-1500: constructions add meaning of their own.
- Implemented grammars: Robust MRS can be used with shallow analyses (Ch. 22, fn. 5, p. 1020).
- Consequence: the relaxed output needs at least an intersective/scopal bit per modifier. RMRS is the natural target format.

**RX-3. Relaxed output is outside the theory's notion of well-formedness. (P3, both phases)**

- Handbook: Ch. 1, p. 5 and fn. 3 (no violable constraints in most HPSG work); Ch. 10, pp. 373-374; Ch. 28, pp. 1263-1264 (weighted and violable constraints are possible in principle); Ch. 24, pp. 1082-1084 (categorical grammar plus a separate probabilistic component as one stated option).
- Implemented grammars: mal-rules (Ch. 25, pp. 1124-1125) and the PCFG approximation of Zhang and Krieger (2011) are existing forms of relaxation.
- Consequence: keep strict and relaxed outputs formally separate and labeled. A relaxed path that records which unification failed fits the view in Ch. 28 (reader's inference).

---

## B. Support for the design in the Handbook

Statements below are from the chapters unless marked.

1. **One surface structure, no movement.** HPSG is monostratal with a single, relatively simple constituent structure (Ch. 1, p. 5; Ch. 22, pp. 1001, 1004; Ch. 24, pp. 1089-1090; Ch. 28, pp. 1273, 1299). Passive, raising, control, and scrambling are analyzed without movement (Ch. 12, p. 497; Ch. 28, pp. 1273-1274, 1291-1296).
2. **Local licensing.** "All constraints are purely local and never affect anything larger than the immediate tree consisting of an expression and its daughters" (Ch. 28, p. 1299). An HPSG grammar "largely consists of constraints on local sub-trees" (Ch. 30, p. 1397). Constructional Localism (Ch. 2, pp. 69-70). The principle of surface combinatorics (Ch. 4, p. 129). Unbounded dependencies are a series of local feature-passing steps (Ch. 13, pp. 540-542; Ch. 30, pp. 1418-1420).
3. **Context-free backbone and bounded structures in DELPH-IN grammars.** The standard chart algorithm applies where every analysis is a phrase-structure tree plus constraints between mother and daughters; DELPH-IN grammars have short valence lists, no relational constraints, a one-element SLASH in the ERG, and no DEPS (Ch. 25, pp. 1108-1109, fn. 9).
4. **Lexical rules are unary rules in implemented grammars.** Stated for the ERG, CoreGram, and Grammix (Ch. 4, pp. 130, 156, 165); for the LKB (Ch. 21, pp. 958-959); as the description-level consensus (Ch. 21, p. 990; Ch. 1, p. 10; Ch. 9, p. 345; Ch. 30, p. 1418; Ch. 32, fn. 26).
5. **Lexicalism makes the per-token label informative.** Most combinatorial information is in the lexical entry and schemata are few (Ch. 4, p. 140; Ch. 24, pp. 1091-1092; Ch. 8, pp. 295-296; Ch. 32, p. 1521). Argument structure alternations are lexical (Ch. 9, pp. 316, 355-358).
6. **Supertagging precedent.** Supertagging is established for HPSG (Matsuzaki et al. 2007); ubertagging gave a fourfold speedup with better accuracy (Ch. 25, pp. 1111-1112). Neural systems trained on grammar output gain from using the derivation trees (Chen et al. 2018; Ch. 25, p. 1127).
7. **Traceless analyses are the majority position for extraction and relatives.** Ch. 13, pp. 540, 544; Ch. 14, pp. 596, 609; Ch. 15, p. 668; Ch. 2, p. 61. No empty elements are used for pro-drop, affixal arguments, raising, control, or VP ellipsis (Ch. 6, p. 222; Ch. 9, p. 321; Ch. 12, pp. 497, 509, 526; Ch. 18, pp. 815-816, 821-822; Ch. 19, pp. 849, 868-870, 877). No zero morphemes (Ch. 21, pp. 957-958).
8. **Semantics is built at every node, in tandem with syntax.** Ch. 1, pp. 26-27; Ch. 8, p. 281; Ch. 6, p. 232; Ch. 22, p. 1004. MRS composition is list append plus a semantic head "determined uniquely for each construction type" (Ch. 22, pp. 1023-1024). Scope ambiguity is not derivational ambiguity (Ch. 22, pp. 1007, 1020-1021; Ch. 29, p. 1355).
9. **Agreement, case, and linking need no extra pass.** Agreement is a side effect of valence saturation, modification, and binding (Ch. 6, pp. 220, 223-224). English nominative is assigned in the lexical entry of the finite verb (Ch. 7, p. 246). Grammar Matrix case systems are constraints on lexical types (Ch. 7, p. 264). Linking is declarative and lexical (Ch. 9, p. 332).
10. **Continuity is defended for hard cases.** Ch. 10, Sections 7-8, pp. 402-404: even very free order can be analyzed without discontinuous constituents (Bender 2008). Ch. 11, pp. 453-456, 462-464: argument attraction is preferred over domain union for German coherent constructions and Korean auxiliaries. Ch. 13, p. 575: the order-domain analysis of extraposition is "highly questionable" for English. English order is the easy case (Ch. 10, pp. 369, 377).
11. **Binary branching is an accepted option.** Ch. 1, fn. 30; Ch. 10, pp. 377-379; Ch. 28, p. 1286; Ch. 11, pp. 443, 456-457; Ch. 16, p. 730; Ch. 18, pp. 829-834.
12. **Binding does not constrain tree shape.** Ch. 20, pp. 900, 932-933; binding and grammatical relations are read from ARG-ST (Ch. 4, pp. 138-140; Ch. 5, pp. 199, 202).
13. **Island constraints need not be in the grammar.** Ch. 15, pp. 671-672, 680, 700-701; Ch. 29, p. 1359. A permissive grammar plus a probabilistic component is the division of labor the chapters point to (Ch. 15, pp. 676, 690; Ch. 24, p. 1083).
14. **Per-word decomposition of a phrase-structure analysis.** Hudson's "neo-HPSG" sketch assigns each phrasal node of a headed analysis to one word, as a chain of sub-tokens (Ch. 31, Section 6, pp. 1484-1486). The reader notes that this is the observation the tree encoding rests on.
15. **Resources and ecosystem.** Standardized formalism processed by several engines (LKB, PET, ACE, Agree); Redwoods stores the selected full analyses; WikiWoods has 55 million parsed sentences (Ch. 25, pp. 1117, 1124). The Grammar Matrix and CoreGram support the multilingual aim (Ch. 2, pp. 65-66; Ch. 5, fn. 32; Ch. 25, pp. 1115-1122). Bouma and van Noord (2017) built a UD treebank from Alpino output (Ch. 25, pp. 1119, 1123).
16. **Robust targets exist.** RMRS for shallow analyses (Ch. 22, fn. 5); PCFG approximation of an HPSG (Ch. 25, p. 1117); mal-rules (Ch. 25, pp. 1124-1125).
17. **Implementation is valued by the theory.** Ch. 1, p. 7; Ch. 28, p. 1256.

---

## C. Open questions the Handbook does not settle

### C1. To check in the ERG, Copestake (2002), and Redwoods

These come from the readers' "Not covered here" sections. They are reader remarks, not Handbook content.

1. Are all ERG rules unary or binary? Are there any lexical entries or rules with empty phonology? (Ch. 25 does not say; raised by readers of Ch. 1, 2, 10, 13, 25, 28.)
2. Does a derivation tree (rule names plus lexical entry identifiers) determine the feature structure and the MRS with no residual choice? Which rules contribute predications (C-CONT)? (Ch. 22, 25, 32.)
3. How are gaps introduced: lexical rule, unary phrasal extraction rule, or underspecification? Does the rule name identify the extracted argument? Are sets recoded as lists or difference lists, and are defaults compiled out? (Ch. 4, 9, 13, 14, 15.)
4. Subject-auxiliary inversion: which analysis, and how is it binarized? (Ch. 5, 10, 12, 30.)
5. Coordination, Right-Node Raising, argument clusters, gapping, fragments, VP ellipsis: are the treebanked derivations continuous and token-leaved, and what does the MRS contain at an ellipsis site? How frequent is each in Redwoods? (Ch. 16, 19, 29.)
6. Relative clauses: bare relatives, "that", free relatives, extraposed relatives; which of the competing options, and at what height do phrasal unary rules sit? (Ch. 14.)
7. "not", contracted "n't", possessive "'s", do-support: analyses and tokenization. (Ch. 8, 18, 21.)
8. Which island constraints does the ERG impose on SLASH in coordination, adjuncts, and subjects? (Ch. 15.)
9. Does the ERG implement any binding principle, any information structure (ICONS), or the INDEX/CONCORD split? (Ch. 6, 20, 23.)
10. Idioms and multiword entries: how many, and is the idiom check post-parse? (Ch. 17.)
11. How are lexical-rule chains restricted (ordering, cycles, spelling-changing versus other rules), and how are regular forms of irregular stems blocked? (Ch. 4, 21.)
12. Token mapping, punctuation, and unknown words: what must the per-token label encode? (Ch. 1, 4, 25.)
13. NPN, comparative correlatives, "let alone", the "way" construction: does the ERG have binary rules for them? (Ch. 32.)

### C2. Left open by the theory, as the chapters themselves state

1. Whether gaps are empty categories, and whether SLASH passing is head-driven (Ch. 13, p. 582).
2. How much role order domains should play, and whether HPSG with domains is still monostratal (Ch. 1, pp. 32-34).
3. Flat versus binary branching: both declared viable, with no criterion (Ch. 28, pp. 1284-1288).
4. The form of the Argument Realization Principle, and when to use a lexical rule and when underspecification (Ch. 1, p. 17; Ch. 4, pp. 165-166).
5. The correct analysis of non-constituent coordination and the scope of shared quantifiers (Ch. 16, p. 765; Ch. 29, pp. 1361-1363).
6. Which CAT features coordinands share (Ch. 16, pp. 741-744).
7. The passive and its by-phrase (Ch. 9, pp. 344-351).
8. Adjuncts as complements (Ch. 1, p. 30; Ch. 20, pp. 910-915).
9. How to combine probabilistic information with HPSG representations (Ch. 15, p. 701; Ch. 24, pp. 1082-1084).
10. What is universal: SUBJ, COMPS, and ARG-ST as candidates, with Oneida as the challenge (Ch. 5, p. 202; Ch. 9, pp. 354-355; Ch. 28, pp. 1305-1306).
11. No MRS account of negative concord or polyadic quantification is given (Ch. 22, pp. 1031-1033); the semantics of coordination is set aside (Ch. 16, fn. 5).
12. No explicit HPSG account of islands, of extraposition islands, of it-clefts with relative-phrase fillers, of sprouting, or of the interaction of VP ellipsis with extraction (Ch. 15, pp. 678-680, 700-701; Ch. 14, pp. 640-641; Ch. 19, pp. 854-855; Ch. 29, pp. 1366-1367).

### C3. Flags on the notes themselves

1. **Bibliography letters differ by chapter.** "Müller 2021b" is the German clause structure book in Ch. 10 and Ch. 11 and the constituent-order Handbook chapter in Ch. 5 and Ch. 31; "Müller 2021c" is Germanic syntax in Ch. 10 and German clause structure in Ch. 28; "Müller 1999a/1999b" likewise vary. Titles are used below.
2. **Crysmann citations.** Ch. 16 cites "Crysmann 2004" for elliptical argument cluster coordination, and Ch. 19 cites Crysmann 2008 for the same point; the Ch. 16 reader doubts the 2004 reference (it is listed as a paper on modifier attachment). Ch. 14 cites Crysmann 2004 for the Kiss-style analysis, which matches that title.
3. **Chaves on gapping.** Ch. 16 cites Chaves 2006 for the elliptical account; Ch. 19 and Ch. 29 cite Chaves 2009.
4. **Pollard and Sag 1994 page for the flat VP.** Ch. 1 and Ch. 20 give p. 40 (Ch. 1 for ternary inversion); Ch. 28 gives p. 36 for the ternary VP; Ch. 10 gives pp. 39-40 and 362. Check in the book.
5. **Severity disagreements.** Cooper storage (low in Ch. 22, medium in Ch. 13); continuity for English (medium in Ch. 31, low elsewhere).
6. **Many consequences are inferences.** The readers of Ch. 4, 6, 7, 11, 13-16, 18-23, 28-31 mark their UD and replay consequences as their own. None of these chapters mentions UD except Ch. 25, Ch. 30 (one citation), and Ch. 31 (as a treebank collection).
7. **Author perspective.** The four Müller chapters (10, 20, 28, 32) argue for binary branching and tolerate empty elements; Ch. 13 and Ch. 14 report the traceless view as the majority. Ch. 21's claim of a consensus model for inflection is made by a co-developer of that model (reader's flag).
8. **Unverified reader statement.** The Ch. 10 reader believes Bender (2008) is tied to an implemented Wambaya grammar; the chapter does not say so.

---

## D. Second-wave reading list

Chapter numbers in parentheses show which Handbook chapters rely on the work, according to the readers' lists. Works are grouped by priority tier.

### Tier 1: works the project owner named

**Pollard and Sag**

1. **Pollard and Sag 1994, *Head-Driven Phrase Structure Grammar*.** Listed as a key source by the readers of all chapters except 18, 19, and 27. The parts the chapters lean on: schemata and the flat VP (pp. 36-40; Ch. 1, 5, 10, 20, 28); agreement (Ch. 2, Section 2.5.1; Ch. 6); raising, control, and the Raising Principle (Ch. 3; Ch. 12); unbounded dependencies with traces, Section 4.3 on "easy" adjectives, Section 4.6 on multiple gaps (Ch. 13, 24, 28); relative clauses with the empty relativizer and REL (Ch. 5; Ch. 13, 14, 29, 32); Binding Theory (Ch. 6; Ch. 20, 29); coordination (pp. 200-205; Ch. 16); Cooper storage (pp. 322-328; Ch. 22); case (p. 30; Ch. 7); and Chapter 9, the valence revision and traceless extraction by lexical rules (Ch. 2, 4, 7, 9). Chapter 9 is the first thing to read: it is where the standard theory becomes compatible with our assumptions.
2. **Pollard and Sag 1987, *Information-based syntax and semantics*.** The unification-based foundations that implementations still use (Ch. 3), the Constituent Order Principle (Ch. 10), SUBCAT (Ch. 1, 2, 9, 32), the first Semantics Principle (Ch. 22).
3. **Pollard and Sag 1992, "Anaphors in English and the scope of Binding Theory".** Binding on ARG-ST (Ch. 4, 6, 20, 28, 29).

**Sag's later work**

4. **Bouma, Malouf and Sag 2001, "Satisfying constraints on extraction and adjunction".** The most widely cited paper in the Handbook after Pollard and Sag 1994 (Ch. 1, 4, 7, 9-13, 15, 19, 20, 25, 30-32). Traceless extraction by underspecified argument realization, SLASH amalgamation, adjuncts as dependents (DEPS). Decides DR-1; DELPH-IN does not adopt DEPS (Ch. 25).
5. **Sag 1997, "English relative clause constructions".** The constructional, empty-element-free analysis with phrasal unary rules (Ch. 1, 2, 4, 8, 10, 12-14, 17, 20, 22, 24, 28, 29, 32). Source of TE-3.
6. **Ginzburg and Sag 2000, *Interrogative investigations*.** Constructional HPSG: clause-type hierarchy, Argument Realization Principle, fragments (Head-Fragment Schema, MAX-QUD, SAL-UTT), wh in situ (Ch. 1, 2, 4, 5, 8, 10, 11, 13-15, 19, 22, 26, 28-30).
7. **Sag 2010, "English filler-gap constructions".** The family of filler-gap constructions; islands kept out of the grammar (Ch. 1, 13-16, 20, 28, 29, 32).
8. **Sag 2012, "Sign-Based Construction Grammar: An informal synopsis"**, with Sag, Boas and Kay 2012. Constructs with MOTHER and DTRS, close to derivation-tree nodes; criticized by Müller in Ch. 32 (Ch. 1-3, 5, 8, 10-13, 15, 20, 28, 32).
9. **Sag et al. 2020, "Lessons from the English auxiliary system".** Inversion as a ternary construction, the AUX feature (Ch. 10, 12, 14, 16, 30).
10. **Sag, Wasow and Bender 2003, *Syntactic theory*.** The textbook version: gapless extraction (Ch. 14 of the book), auxiliaries with two complements (Ch. 1, 6, 8-10, 12, 16, 24, 26, 30, 32).
11. **Beavers and Sag 2004, "Coordinate ellipsis and apparent non-constituent coordination".** The elliptical analysis behind LT-1 and LT-2 (Ch. 7, 15, 16, 19, 29).
12. **Sag 2003, "Coordination and underspecification".** Unlike categories, syncretism without sort resolution (Ch. 7, 16, 28).
13. **Sag and Fodor 1995, "Extraction without traces".** (Ch. 1, 15, 30.)
14. **Miller and Sag 1997, "French clitic movement without clitics or movement".** Source of LT-4 (Ch. 1, 4, 5, 7, 9, 11, 21).
15. **Kim and Sag 2002, "Negation without head-movement".** (Ch. 9, 12, 18, 31.)
16. **Sag 2007, "Remarks on locality".** XARG, LID (Ch. 11, 12, 32).
17. **Kay, Sag and Flickinger 2015, "A lexical theory of phrasal idioms"** (manuscript); **Nunberg, Sag and Wasow 1994, "Idioms"**; **Sag, Baldwin, Bond, Copestake and Flickinger 2002, "Multiword expressions"**. (Ch. 17, 32.)
18. **Manning and Sag 1998, "Argument structure, valence, and binding"; Manning and Sag 1999, "Dissociations between argument structure and grammatical relations"; Manning, Sag and Iida 1999, "The lexical integrity of Japanese causatives".** (Ch. 1, 5, 9, 12, 20, 29.)
19. **Donohue and Sag 1999, "Domains in Warlpiri".** The order-domain analysis of free order (Ch. 1, 10, 30).
20. **Hofmeister and Sag 2010; Levine and Sag 2003; Sag and Wasow 2011; de Swart and Sag 2002; Sag and Nykiel 2011.** Islands as processing effects, extraction data, performance-compatible grammar, negative concord, sluicing (Ch. 2, 15, 18, 19, 24, 28).

**Bouma**

21. **Bouma and van Noord 1998, "Word order constraints on verb clusters in German and Dutch".** Verb clusters and cross-serial dependencies, head movement for Dutch (Ch. 10, 11, 12, 25, 28).
22. **Bouma 1996, "Extraposition as a nonlocal dependency".** The EXTRA analysis (Ch. 14, 15).
23. **Bouma and van Noord 2017, "The automatic construction of a Universal Dependency treebank for Dutch".** The only HPSG-to-UD precedent in the Handbook (Ch. 25).
24. **Bouma, van Noord and Malouf 2001, "Alpino".** (Ch. 2, 25.) **van Noord and Bouma 1994, "The scope of adjuncts and the processing of lexical rules"** (Ch. 10); **van Noord and Bouma 1997, "Dutch verb clustering without verb clusters"** (Ch. 20); Bouma 1988 (Ch. 8, footnote only).

**Müller**

25. **Müller 2004, "Continuous or discontinuous constituents? A comparison between syntactic analyses for constituent order and their processing systems".** The direct comparison of the two architectures in implemented grammars (Ch. 14, 25). Highest priority among the Müller papers for our design.
26. **Müller 2005, "Zur Analyse der deutschen Satzstruktur" and "Zur Analyse der scheinbar mehrfachen Vorfeldbesetzung"; Müller 2021, *German clause structure*; Müller 2003, "Mehrfache Vorfeldbesetzung".** The empty verbal head and multiple fronting, EE-1 (Ch. 10, 11, 23, 28).
27. **Müller 2021, *Germanic syntax*.** Binary branching with a parameterized schema (Ch. 10, 28).
28. **Müller 2016/2018/2020, *Grammatical theory*.** Sections 19.2 and 19.5 on empty elements, unary projections, and lexical rules; Chapter 17 on restrictiveness (Ch. 2, 28, 31, 32).
29. **Müller 2004, "Elliptical constructions, multiple frontings, and surface-based syntax".** The case for empty elements (Ch. 1, 13, 32).
30. **Müller 2015, "The CoreGram project".** Language-specific motivation, shared constraint sets, trace-based grammars (Ch. 1, 4, 5, 9, 25, 28, 30).
31. **Müller and Wechsler 2014, "Lexical approaches to argument structure"; Müller 2018, "A lexicalist account of argument structure"; Müller 2006, "Phrasal or lexical constructions?".** Why valence change belongs in the lexical-rule chain (Ch. 2, 4, 9, 14, 21, 24, 29, 30, 32).
32. **Müller 1999, *Deutsche Syntax deklarativ*.** Babel grammar: extraposition, unary relative phrase, binding problems (Ch. 6, 13-15, 20, 25). **Müller 1996, the Babel system and partial VP fronting** (Ch. 1, 11, 31, 32).
33. **Müller 2002, *Complex predicates*.** (Ch. 9, 11, 12, 14, 32.)
34. **Müller 2015, "Satztypen: Lexikalisch oder/und phrasal".** Clause-type semantics without a clause-type hierarchy (Ch. 10, 22).
35. **Müller 2009, "On predication"; Müller 2003, German passive; Müller and Ørsnes 2013, passive in Danish, English, and German; Müller 1999, free relatives in German; Müller 2010, Persian complex predicates; Müller 2008, depictives; Müller 2013, *HPSG: Eine Einführung*; Müller 2004, "Complex NPs, subjacency, and extraposition"; Müller and Kasper 2000.** (Ch. 1, 4, 7-9, 11-15, 17, 28, 30, 31.)

### Tier 2: implementation and DELPH-IN sources that settle Section C1

36. **Copestake, Flickinger, Pollard and Sag 2005, "Minimal Recursion Semantics".** Listed for 16 chapters; needed to verify that MRS falls out of replay.
37. **Copestake 2002, *Implementing typed feature structure grammars*.** The formalism the engine targets (Ch. 1, 2, 4, 21, 25).
38. **Copestake, Lascarides and Flickinger 2001, "An algebra for semantic construction".** (Ch. 9, 22.) **Copestake 2007 (RMRS) and 2009 ("Slacker semantics", DMRS).** (Ch. 22, 25-27.)
39. **Dridan 2013, "Ubertagging".** Segmentation plus supertags, LT-3 (Ch. 25). **Matsuzaki, Miyao and Tsujii 2007** on supertagging (Ch. 25).
40. **Flickinger 2000, "On building a more efficient grammar by exploiting types"; Flickinger 2011.** ERG design choices (Ch. 2, 25).
41. **Oepen, Flickinger, Toutanova and Manning 2004, "LinGO Redwoods"; Toutanova et al. 2002, 2005.** (Ch. 1, 2, 25.)
42. **Briscoe and Copestake 1999; Meurers 2001; Lascarides and Copestake 1999; Flickinger 1987.** Lexical rules as unary structures; defaults (Ch. 1, 2, 4, 9, 21, 28, 31, 32).
43. **Bender 2008, "Radical non-configurationality without shuffle operators".** The continuous route for free order (Ch. 5, 10, 30, 31).
44. **Bender, Flickinger and Oepen 2002; Bender et al. 2010; Drellishak and Bender 2005; Drellishak 2008, 2009; Goodman and Bender 2010; Song 2017; Song and Bender 2012; Crowgey 2012.** Grammar Matrix core and libraries (Ch. 1, 2, 5, 7, 16, 18, 21, 23, 25).
45. **Crysmann 2005, "Relative clause extraposition in German: An efficient and portable implementation"; Crysmann 2003, "On the treatment of word order in a computational grammar of German".** (Ch. 13, 14, 19.)
46. **Chen, Sun and Wan 2018; Buys and Blunsom 2017; Zhang and Krieger 2011; Ivanova et al. 2012; Miyao, Ninomiya and Tsujii 2005; Miyao and Tsujii 2008.** Neural and robust parsing with DELPH-IN and Enju resources (Ch. 24, 25).
47. **Melnik 2007; Fokkens 2014.** Theory versus implementation; analysis-order effects (Ch. 25).
48. **Bender and Flickinger 1999 (XARG, tag questions); Flickinger 2008 ("Transparent heads"); Flickinger 2015 (idioms); Villavicencio and Copestake 2002.** (Ch. 12, 17, 28, 32.)

### Tier 3: word order, empty elements, extraposition

49. **Reape 1994, "Domain union and word order variation in German".** Listed for 16 chapters; the source of order domains.
50. **Kathol 2000, *Linear syntax*; Kathol and Pollard 1995, "Extraposition via complex domain formation".** (Ch. 1, 2, 4, 6, 7, 10, 11, 13, 14, 18, 29, 31.)
51. **Hinrichs and Nakazawa 1994, "Linearizing AUXs in German verbal complexes".** Argument attraction (Ch. 9-12).
52. **Borsley 1989, "Phrase-Structure Grammar and the Barriers conception of clause structure".** Head movement in HPSG; the empty relativizer idea (Ch. 10, 14, 30). **Kiss 1995, *Infinite Komplementation*** (Ch. 10, 11).
53. **Levine and Hukari 2006, *The unity of unbounded dependency constructions*.** The case for traces (Ch. 1, 4, 13, 15, 29).
54. **Keller 1995; Kiss 2005; Crysmann 2013.** The three remaining extraposition analyses (Ch. 1, 10, 13-15).
55. **De Kuthy 2002, *Discontinuous NPs in German*; De Kuthy and Meurers 2001.** (Ch. 8, 11, 23.)

### Tier 4: coordination and ellipsis

56. **Chaves 2014, "On the disunity of right-node raising phenomena"; Chaves 2012, "On the grammar of extraction and coordination".** (Ch. 13, 15, 16, 19, 24, 29.)
57. **Mouret 2006, "A phrase structure approach to argument cluster coordination".** The surface-true alternative (Ch. 16, 19).
58. **Abeillé, Bîlbîie and Mouret 2014 (gapping); Abeillé 2006 (lexical coordination); Park 2019 and Park, Koenig and Chaves 2019 (gapping scope).** (Ch. 16, 19, 28, 29.)
59. **Yatabe 2001; Yatabe and Tam 2021; Kubota and Levine 2015; Levine 2011; Crysmann 2008.** The dispute over ellipsis-based coordination (Ch. 7, 16, 19, 29, 31).
60. **Levine, Hukari and Calcagno 2001; Daniels 2002; Levy and Pollard 2002.** Syncretism and neutralization in type hierarchies (Ch. 7, 16, 29).
61. **Ginzburg and Miller 2018; Ginzburg 2012; Kim 2015; Arnold and Borsley 2008, 2010.** Ellipsis, dialogue context, auxiliary-stranding relatives (Ch. 12-14, 19, 26).

### Tier 5: lexicon, morphology, semantics, multilingual

62. **Koenig 1999, *Lexical relations*; Riehemann 1998, 2001; Koenig and Jurafsky 1995.** (Ch. 4, 17, 20, 21, 32.)
63. **Crysmann and Bonami 2016, "Variable morphotactics in Information-based Morphology".** (Ch. 4, 21.)
64. **Davis and Koenig 2000; Davis 2001; Koenig and Davis 2006.** Linking (Ch. 4, 5, 9, 30).
65. **Pollard and Yoo 1998; Przepiórkowski 1998; Kasper 1997; Richter and Sailer 2004.** Scope and adjunct semantics before and beside MRS (Ch. 3, 22, 26, 29, 30).
66. **Przepiórkowski 1999 (case); Meurers 1999; Heinz and Matiasek 1994; Malouf 2000.** (Ch. 4, 7, 8.)
67. **Wechsler and Zlatić 2003; Wechsler and Arka 1998; Wechsler 1999.** Agreement; Balinese voice and binding (Ch. 4, 6, 9, 12, 16, 20, 30).
68. **Koenig and Michelson 2012, 2014, 2015.** Oneida (Ch. 5, 9, 28, 31).
69. **Abeillé and Godard 2002, 2000, 1997; Monachesi 1998.** Romance auxiliaries, weight, clitics (Ch. 9-12, 18).
70. **Van Eynde 2006, 2018; Abeillé, Bonami, Godard and Tseng 2004.** Nominal structure (Ch. 8, 15, 32).
71. **Branco 2002; Hukari and Levine 1995; Walker 2011.** Binding (Ch. 20, 29).
72. **Richter 2004 (RSRL); King 1999; Pollard 1999.** Formal foundations (Ch. 3, 26, 28).
73. **Borsley 2006, 2009, 2013; Crysmann 2012, 2016.** Welsh clause structure and agreement; resumption (Ch. 5, 6, 13, 16, 28).
74. **Bargmann 2015; Jackendoff 2008.** NPN (Ch. 28, 31, 32).

---

## E. Theory strains recorded in the theory log

Twelve entries were written to `theory-log/` (0001 to 0012). Strains reported by the readers and not logged, for a later pass: the passive and its by-phrase (Ch. 9); adjuncts as complements (Ch. 1, 7, 9, 13, 20); the four successive mechanisms for quantifier scope (Ch. 22); the Binding Theory's mixed configurational and argument-structure basis, Principle C, and coordination (Ch. 20, 29); NP versus DP and the specifier/functor dispute (Ch. 8); lexical versus phrasal idiom analyses (Ch. 17); the location and value type of information-structure features (Ch. 23); the model for inflection (Ch. 21); the four model theories for HPSG (Ch. 3); the status of HPSG's semantic objects (Ch. 26).
