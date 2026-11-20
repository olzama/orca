# Pollard and Sag (1994), Chapter 9: Reflections and Revisions

*Head-Driven Phrase Structure Grammar*, University of Chicago Press, pp. 344–393. Read from the text layer of the scan (`PollardSag1994.pdf`). Running prose is clean; attribute-value matrices and trees are garbled in the text layer and were reconstructed from the surrounding prose, so details of individual rule statements should be checked against the page images before being quoted. Read 2026-11-20.

Question for this reading: what does the 1994 theory assume that DELPH-IN changed, and is replay deterministic under it?

## Summary

The chapter revises the theory of the first eight chapters, and the authors call it "somewhat speculative" and a "tentative sketch" whose technical details "have not been worked out" (pp. 346, 393). Following Borsley, the single SUBCAT list is split into three valence features, SUBJ, COMPS, and SPR, governed by a Valence Principle (p. 348; restated p. 392). SUBCAT is kept, on words only, as the concatenation of the three, because binding theory needs obliqueness (pp. 375–376). A lexically based X-bar theory follows, with Head-Subject, Head-Specifier, and Head-Complement schemata (p. 362). Specifiers are argued to be non-heads with their own category, distinct from subjects, which select their head sister through the head feature SPEC while the head selects them through SPR (Sections 9.4.1–9.4.4, pp. 359–373). Welsh finite clauses are analyzed as subjectless: the apparent subject is the least oblique complement (Section 9.3, pp. 351–358). Section 9.5 gives a traceless account of extraction by three lexical rules: complement extraction, subject extraction, and adjunct extraction (pp. 376–388). Section 9.6 keeps a Head-Subject-Complement schema for English inversion after rejecting a lexical alternative (pp. 388–390). Section 9.7 classifies headed structures into seven sorts (pp. 391–393).

## Caveats for the parser

### 1. Flat, multi-daughter schemata (high for labels and tree shape; binary-unary assumption)

The Head-Complement Schema combines a lexical head with all of its complements at once (p. 362: the tag "ranges over lists" of complements). The Head-Subject-Complement Schema for inverted clauses has a head, a subject, and complements as sisters (p. 388), and Welsh VSO clauses are flat head-complement phrases (p. 353). The authors record that this schema is "an odd man out" because every other schema licenses one kind of non-head daughter, and that they found "no obvious way to eliminate" it (pp. 388, 390). None of this is binary branching.

### 2. The extraction lexical rules are named steps, but one name covers several outcomes (high; deterministic replay)

The Complement Extraction Lexical Rule removes "one element" from COMPS and places it in SLASH ((62), p. 378). For a verb with two complements the rule has two possible outputs, shown for the second object of a double-object verb in (63), p. 379. A rule name alone would not say which complement was removed.

### 3. Subject and adjunct extraction are registered on the higher verb (high; deterministic replay, bridge)

The Subject Extraction Lexical Rule applies to the verb that takes the clausal complement: it gives that verb an alternant taking a VP complement and puts the missing subject in the verb's own SLASH ((69), pp. 382–384). In *which guests you said are here* the rule applies to *said*, and *are here* is an ordinary VP ((71), p. 383). The Adjunct Extraction Lexical Rule likewise applies to a verb taking an S complement, and the extracted adjunct modifies that complement ((80)–(81), p. 387). The word whose dependent is missing carries no mark. Fronted adjuncts interpreted in the matrix clause are not extraction at all but head-adjunct structures ((75), p. 385), so a string such as *When do you think your husband is planning to leave you?* (77c, p. 386) has two analyses with different rule sets.

### 4. Lexical rules can interact to give spurious ambiguity (medium; deterministic replay)

A lexical rule for inversion that turned the subject into a first complement would, together with complement extraction, give *John must leave* a second, head-filler analysis ((86), p. 389). The authors call this a "spurious structural ambiguity" and reject the lexical inversion rule for this reason and two others (pp. 389–390). The general point for us: with freely interacting lexical rules, one string can have several derivations with the same meaning, and exact-match evaluation against a single gold derivation would then be unfair.

### 5. Empty elements remain after traces are removed (medium; no-empty-elements assumption)

The chapter still refers to the null relativizer of Chapter 5, now selecting a slashed finite S through COMPS (pp. 349–351, fns. 7–8). The traceless revision removes *wh*-traces only. Comparative subdeletion sites are treated by a further non-local feature (p. 369, fn. 25).

### 6. Sets and several non-local features (medium; engine)

SLASH is set-valued and combined by set union in the lexical rules ((62), p. 378); the Nonlocal Feature Principle of Chapter 4 is retained (p. 379). Extraposed *than* and *as* phrases are assumed to be licensed by a rightward non-local feature EXTRA (p. 366, fn. 23).

### 7. "Subject" is not a uniform notion (medium; UD bridge)

In Welsh the post-verbal nominal of a finite clause is a complement, and only nonfinite predicates have a non-empty SUBJ (pp. 352–357). The authors suggest the same for German polar questions, Japanese and Korean, and German verb-second clauses "treated via 'extraction' from a head-initial clause" (pp. 357–358), while Syrian Arabic is said to need the head-subject-complement schema (p. 358). Possessors are specifiers in English and German and subjects in Welsh, Yup'ik, and Hungarian (pp. 374–375). A mapping from valence features to UD relations has to be stated per language.

### 8. Clitics introduced by lexical rule (low for English; leaves and tokens)

Welsh clitic doubling is handled by lexical rules whose output phonology has the clitic prepended to the verb ((28), p. 357), so the clitic and verb are one word for the grammar.

## Support for the design

- **A small universal inventory of headed structures.** Seven sorts, classified by the kind of non-head daughter: head-complement, head-marker, head-specifier, head-filler, head-subject, head-adjunct, and head-subject-complement, with a table giving for each the semantic head, the selector, and the feature involved ((90), (92), pp. 391–392). The authors call it "a universal typology of headed constructions" (p. 393). This is close to the coarse schema layer we planned, and the table already records the semantic head per schema, which the relaxed semantics needs.
- **Locality of valence.** Valence specifications "cannot propagate beyond the largest constituent headed by the word that introduced them" (p. 362), and SUBCAT is to be appropriate for words only so that non-local subcategorization is impossible (p. 376). Local constraints are what replay applies.
- **Traceless extraction with SLASH originating on the head.** "SLASH originates not on traces, but rather from the head that licenses the 'missing' element" (p. 378), motivated by the processing evidence of Pickering and Barry (pp. 377–378). Extraction is a property of a word, so a word-level label can carry it.
- **Lexical rules as the mechanism.** Complement extraction is a lexical rule on the head word. In a derivation this is a unary step in that word's chain, which is the form our label scheme handles.
- **Function words as non-heads.** Complementizers are markers and determiners are specifiers; both are non-heads that select their head sister through SPEC (pp. 363–364, 385, 392). For these two classes the head daughter is the content word, as in UD.

## Theory strains

- **Whether Head-Subject and Head-Filler are one schema.** The authors list four technical obstacles and suggest treating the two as a natural class (pp. 381–382, fn. 40).
- **The inversion schema.** It breaks the pattern of one non-head type per schema; both lexical alternatives fail (pp. 388–390).
- **Specifier as head or non-head.** A reductio is given against specifiers as heads, using recursive degree specification (pp. 363–371); the authors grant that the argument has not been made for German, and note Netter's account with determiners as heads (p. 373, fn. 31). The mutual selection of determiner and noun is offered as the reason for "the general lack of consensus" about the head of a noun phrase (p. 363).
- **Subject or specifier for possessives and gerunds.** Left open for verbal gerunds; language-dependent for possessors (pp. 374–375).
- **Relation between valence lists and SUBCAT.** Extraction outputs violate the canonical relation while passive outputs seem to obey it: "As yet, we have no general theory of such differences" (p. 379, fn. 38). This is the gap that Bouma, Malouf and Sag (2001) later address.
- **Which adjuncts can be extracted.** The restriction of adjunct extraction to modifiers of S complements "should ultimately follow from more general principles" (pp. 387–388); the semantic and pragmatic limits are not characterized.
- **Predicative noun phrases.** Three problems are listed and left open (p. 360, fn. 20).

## Key primary sources

- Borsley 1987, 1989, 1990, and "to appear" (SUBJ versus COMPS; SPR; Welsh).
- Pickering and Barry 1991 (processing evidence against traces).
- Gazdar, Klein, Pullum and Sag 1984; Kaplan and Zaenen 1989; Steedman 1987 (earlier traceless analyses).
- Bresnan 1973 (comparatives and degree specification).
- Abney 1987 (determiners as heads; possessors).
- Pollard and Sag 1987 (the SUBCAT-based theory being revised).
- Kathol (unpublished, cited for German declension); Netter (in press, German noun phrases).

## Not covered here

These are my remarks, not statements from the chapter.

- **What DELPH-IN changed, as far as I can say from our data.** The ERG treebank has only unary and binary rules, so the flat schemata of caveat 1 were replaced by binary ones. Extraction in the ERG is marked by phrasal unary rules (`hd_xcmp_c`, `hd_xsb-fin_c`, `hd_xaj-int-vp_c`) and not by lexical rules on the embedding verb, so caveat 3 may not carry over; the rule names suggest the mark sits on the phrase whose dependent is missing, which I have not verified in the rule definitions. Whether the ERG treats complementizers as heads or as markers is also unverified, and matters for the UD bridge.
- **Caveat 2 applies to any grammar we write.** A named extraction step must identify the dependent it removes, or replay needs a search over the options.
- **Chapters 4 and 5 are needed to judge the remaining empty elements** (traces in the standard theory, the null relativizer). They are in the queue.
- The chapter does not discuss semantics composition beyond one footnote on adjunct scope (p. 387, fn. 45); Chapter 8 covers it.
