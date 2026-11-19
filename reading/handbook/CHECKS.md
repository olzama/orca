# Spot-check of the top caveats

Each of the 15 top caveats in `SYNTHESIS.md` was checked by an independent reader against the chapter text. The check covers only the claim about what the Handbook says, not the design consequence. Where the verdict is not "supported", the corrected statement below takes precedence over the wording in `SYNTHESIS.md`.

## LT-1: Right-Node Raising is analyzed by deletion, including below the word level

**Verdict:** supported

**Claim checked:** Ch. 16 (Section 7, pp. 760-763) says a syntactic, non-elliptical account of Right-Node Raising is 'harder to maintain', gives examples where the shared material is part of a word ('sole or co-author', (79)), and states rule (80), a unary rule that splits a MORPHO-PHONOLOGY list into five sublists and drops one under PHON and LID identity. Ch. 19 (Section 6.2, pp. 873-876) says Right Node Raising 'has consistently attracted HPSG analyses involving silent material' and that Backward Periphery Deletion (59) 'targets any linearized strings, whether constituents or otherwise'. Neither chapter says what any implemented grammar does.

**Explanation:** Every specific statement in the claim checks out against the chapter text.

**Ch. 16, Section 7 (reading/handbook/txt/ch16.txt, lines 1697-1810, pp. 760-762):**
- p. 760 says: "A syntactic and non-elliptical account of Right-Node Raising is harder to maintain given that this phenomenon does not seem to be sensitive to syntactic structure".
- It then says RNR "can involve lexical structure" and gives (79a) "the SOLE or CO-[author]", along with "UN- nor OVERLY [patriotic]" and "EX- or CURRENT [smokers]".
- Rule (80), right-peripheral-ellipsis-phrase (p. 761), is attributed to Chaves (2014: 874) and Shiraishi et al. (2019) "in simplified format". The mother's MP is L1 + R1 + R2 + R3; the single daughter's MP is L1 + L2 + R1 + R2 + R3, where L2 and R2 share PHON and LID values. So five sublists with one dropped under PHON and LID identity is an accurate reading.
- The text calls it "a unary-branching rule" that "can in principle apply to any phrasal node, including non-coordinate cases".
- "Five sublists" is the claim's own paraphrase of the AVM; the chapter does not use that wording.

**Ch. 19, Section 6.2 (reading/handbook/txt/ch19.txt, lines 1284-1390, pp. 873-876):**
- Verbatim: "Right Node Raising has consistently attracted HPSG analyses involving silent material", and "All existing analyses ... agree on this point".
- (56c,d) show RNR below the word level: "hard- but ... soft-[cover edition]", "under- and ... over[generates]".
- The phrase "targets any linearized strings, whether constituents or otherwise" describes Chaves's optional surface-based deletion mechanism, whose licensing constraint is (59), the Backward Periphery Deletion Construction.

**Ch. 29, Section 4.2.4 (reading/handbook/txt/ch29.txt, lines 1755-1785, pp. 1367-1368):** consistent with the claim. It says RNR is not unitary and "at least some type of RNR should be treated via a mechanism of surface ellipsis".

**Implemented grammars:** none of the three passages mentions one, so the last sentence of the claim holds.

**Caveats that do not change the verdict:**
- The headline "RNR is analyzed by deletion" is slightly broader than the text. Ch. 19 says Chaves (2014) treats RNR as nonuniform (extraposition, VP/N'-ellipsis, and "true" RNR) and that only true RNR gets the deletion rule.
- Ch. 19 also distinguishes a linearization-based strand (Yatabe 2001; 2012) from the "deletion-like" strand (Chaves 2014; Abeillé et al. 2016; Shiraishi et al. 2019).
- Abeillé et al. and Shiraishi et al. argue that strict morphophonological identity is too strong a condition.

## LT-2: Argument cluster coordination as ellipsis: the rule name does not fix how much is elided

**Verdict:** partly-supported

**Claim checked:** Ch. 16 (Section 7, pp. 756-757) presents left-periphery ellipsis constraint (71), under which left-edge material of a non-initial coordinand may be absent from the mother, and example (72), where different amounts of elided material give different meanings for the same string. Ch. 19 (Section 6.3, pp. 876-877) gives Coordination Schema (63), stated over DOM lists, which yields plain coordination, cluster coordination or both-edge ellipsis. Ch. 16 (pp. 757-760) also presents Mouret's (2006) non-elliptical cluster analysis with a lexical rule on the verb.

**Explanation:** Checked against reading/handbook/txt/ch16.txt, ch19.txt and ch29.txt. Almost everything holds; one detail about example (72) is overstated.

Supported:
- Ch. 16, Section 7 "Non-constituent coordination", p. 756: constraint (71) on coord-phrase lets left-periphery phonological material of the non-initial coordinand, identical to that of the initial coordinand, be absent from the mother. On p. 757 the text adds that if the shared list is empty no ellipsis occurs, which backs the "rule does not fix how much is elided" reading. (71) is stated over PHON; the chapter notes that Yatabe, Crysmann, Beavers and Sag, and Chaves operate on linearization domains instead.
- Ch. 19, Section 6.3, pp. 876-877: Coordination Schema (63), adapted from Beavers and Sag (2004: 27), is stated over DOM lists. With A empty it licenses "Kim and Pat"; with A non-empty, argument cluster coordination; with both A and D non-empty, examples like (62), i.e. ellipsis at both edges.
- Ch. 16, pp. 757-760: Mouret's (2006) non-elliptical analysis, with argument-cluster-phrase (73), a CLUSTER head feature, and lexical rule (74) letting a verb take a coordination of clusters as complement, followed by the supporting arguments (as well as/ainsi que, correlative placement, negation).

Overstated:
- (72) on p. 757 is not one string with two meanings. It is a pair of different sentences: (72a) with the one-time predicate "cut down", where the ellipsis must include the subject, and (72b) with "photographed", where the ellipsis can involve just the verb. The chapter does say the approach is "motivated by the existence of ambiguity in sentences like (72)", but it never spells out two readings of a single string.

Ch. 29, Section 4.2.1, pp. 1361-1363, is listed in the cited location but the claim asserts nothing about it. That passage discusses Beavers and Sag's surface-deletion analysis and Yatabe's alternative, mainly on quantifier scope, and is consistent with the ellipsis view.

**Corrected statement:** Ch. 16 (Section 7, pp. 756-757) presents left-periphery ellipsis constraint (71), stated over PHON, under which left-edge material of a non-initial coordinand that is identical to left-edge material of the initial coordinand may be absent from the mother; if the shared list is empty, no ellipsis occurs. The approach is motivated by ambiguity in sentences like (72): the pair (72a)/(72b) shows that the amount of elided material varies. With the one-time predicate "cut down" the ellipsis must include the subject, while with "photographed" it can involve just the verb. Ch. 19 (Section 6.3, pp. 876-877) gives Coordination Schema (63), adapted from Beavers and Sag (2004) and stated over DOM lists, which licenses plain coordination (A empty), argument cluster coordination (A non-empty) or ellipsis at both edges (A and D non-empty). Ch. 16 (pp. 757-760) also presents Mouret's (2006) non-elliptical cluster analysis, with argument-cluster-phrase (73) and a lexical rule (74) on the verb.

## LT-3: One lexical entry can span several tokens; segmentation must be predicted

**Verdict:** supported

**Claim checked:** Ch. 25 (Section 2.2.2, p. 1112) says that for multiword expressions such as 'by and large' the grammar assigns a single lexical entry to multiple tokens, and that ubertagging (Dridan 2013) jointly predicts a segmentation and supertags, with a fourfold speedup and better accuracy. Ch. 17 (Section 2, p. 779) says completely fixed idioms are often called 'words with spaces' (Sag et al. 2002).

**Explanation:** Both quoted statements are in the chapter text at the cited places.

Ch. 25 (Bender & Emerson), Section 2.2.2 "Parse ranking", p. 1112 (reading/handbook/txt/ch25.txt, lines 320-324): "To allow multiword expressions (such as by and large), where the grammar assigns a single lexical entry to multiple tokens, Dridan (2013) proposes an extension of supertagging, called ubertagging, which jointly predicts both a segmentation of the input and supertags for those segments. Dridan manages to increase parsing speed by a factor of four, while also improving parsing accuracy." This matches the claim on every point: single entry over multiple tokens, joint segmentation and supertags, fourfold speedup, better accuracy.

Ch. 17 (Sailer), Section 2 "Empirical domain", p. 779 (reading/handbook/txt/ch17.txt, lines 101-103): "Sag et al. (2002) distinguish three levels of fixedness: fixed, semi-fixed, and flexible. Completely fixed idioms include of course, ad hoc and are often called words with spaces." This matches the claim.

The secondary locations are also relevant. Ch. 25 Section 3.2, pp. 1117-1118, mentions supertagging and ubertagging again as performance innovations for processing large quantities of text. Ch. 17 Section 4.3, pp. 791-792, describes non-decomposable, non-flexible idioms receiving a "phrasal lexical entry".

Two small caveats that do not change the verdict:
- The headline wording "segmentation must be predicted" is slightly stronger than the text. Ch. 25 presents ubertagging as an optional pre-parsing technique for restricting the parser's search, proposed by Dridan; it does not say segmentation has to be predicted.
- The two chapters use different examples. Ch. 25 uses "by and large" for the multi-token lexical entry. Ch. 17 gives "of course" and "ad hoc" as the fixed "words with spaces", and mentions "by and large" separately on the same page as an example of syntactic idiomaticity (after Baldwin & Kim 2010). The claim does not conflate them.

## LT-4: Pronominal clitics analyzed as affixes: arguments with no leaf

**Verdict:** supported

**Claim checked:** Ch. 4 (Section 3.2, pp. 136-137) reports that, following Miller and Sag (1997), French non-subject clitics are prefixes and 'y va' is one lexical entry with empty COMPS and an affixal ARG-ST member. Ch. 11 (Section 3, pp. 427-430; Section 4.3, pp. 443-445) shows climbed clitics realized on the auxiliary or restructuring verb, with leaves such as 'l'a' and 'lo-vuole'. Ch. 21 (Section 4.4, pp. 982-984) treats Romance clitic clusters as inflection of the verb.

**Explanation:** All three chapter attributions check out against the text.

Ch. 4, Section 3.2 (reading/handbook/txt/ch04.txt, lines 497-610; pp. 136-137): "We follow Miller & Sag (1997) and assume here that French non-subject clitics are prefixes." Entry (10) for "y va" has FORM y-va, COMPS <>, and ARG-ST <NP, PP[p-aff, loc]>. The text says "the entry for y va does not subcategorize for a locative PP, since the affix y satisfies the relevant argument structure requirement". Strictly, the chapter presents two entries for aller (va vs. y va); "y va" is one of them, as the claim says.

Ch. 11, Section 3 (ch11.txt, lines 436-500; pp. 428-429, inside the cited 427-430 range): "Romance clitics ... are analyzed as affixes (aff) on verbs, which correspond to arguments of the verb (Miller & Sag 1997)". The affix is on the auxiliary's ARG-ST but not its COMPS, and Figure 3 "Clitic climbing in French" has the leaves "l'a" and "lu". Section 4.3 (lines 1151-1268; pp. 444-445): the affixal element is attracted to the restructuring verb, which becomes a reduced verb targeted by "a morphological rule of cliticization"; Figure 7 has the leaf "lo-vuole" (and Spanish "lo-quiere").

Ch. 21, Section 4.4 Morphotactics (ch21.txt, lines 1842-1865; p. 982): Crysmann and Bonami (2016) on "placement of pronominal affix clusters in Italian" (me-lo-da-te / da-te-me-lo), handled by inflectional realization rules with a stem position index.

Two minor imprecisions that do not change the verdict: Ch. 21 Section 4.4 discusses Italian specifically (European Portuguese mesoclisis appears only in a footnote, and Miller and Sag's French affix cluster is mentioned in Section 3.2, p. 955 or so), so "Romance" is a mild generalization; and the Italian passage sits on p. 982, with the associated rule hierarchies on the following page. I did not check the other cited locations (Ch. 4 Section 5.3, Ch. 1 Section 4.1, chapters 5, 7, 9, 18) beyond confirming that Ch. 4 Section 5.3 does discuss the Monachesi clitic lexical rule and the Miller and Sag constraints, since the claim text makes no specific assertion about them.

## EE-1: The continuous analysis of German verb placement uses an empty verbal head

**Verdict:** supported

**Claim checked:** Ch. 10 (Section 5.1, pp. 384-386) describes the majority analysis of German verb-initial and verb-second clauses as a unary rule on the verb, a head feature DSL, and an empty lexical element with PHON < >; Section 6.4.2 (pp. 398-401) analyzes apparent multiple fronting with an empty verbal head, and sketch (49) has three empty positions in one clause. Ch. 28 (Section 4.2.1, p. 1288) says the analogue of head movement 'is standard among HPSG grammarians of German' and that multiple fronting makes it 'unavoidable'.

**Explanation:** The cited passages in reading/handbook/txt/ch10.txt and ch28.txt say what the claim reports. I checked only Ch. 10 Sections 5.1 and 6.4.2 and Ch. 28 Section 4.2.1; the other listed locations (Ch. 10 Section 8, Ch. 28 fn. 27, Ch. 5, Ch. 30, Ch. 23) were not checked, and the claim text does not depend on them.

Ch. 10, Section 5.1 (pp. 384-386):
- A "special variant of the auxiliary is licensed by a unary rule".
- "DSL is a head feature and hence available everywhere along a projection path".
- (29) "Empty element for head movement" is a word with empty PHON and LOC identified with its HEAD|DSL value ("I am a verb that is missing itself").
- "Such head-movement analyses are assumed by most researchers working on German" (Kiss & Wesche 1991, Oliva 1992, Netter 1992, Frank 1994, Kiss 1995, Feldhaus 1997, Meurers 2000, Müller 2005a, 2021b), which supports "majority analysis".

Ch. 10, Section 6.4.2 (pp. 398-401):
- Müller (2002b) used "an empty verbal head" for apparent multiple fronting within a linearization grammar.
- Müller (2005b; 2021b) drops linearization for head movement: "The empty head that is used for accounting for the verb position in German can also be used to account for apparent multiple frontings."
- Sketch (49a) has three empty positions: _V inside the fronted VP, plus the traces _i and _j.
- P. 402 sums these up as "head-movement approaches with binary branching and continuous constituents", which supports the label "continuous analysis".

Ch. 28, Section 4.2.1 (p. 1288): "The analogue to head-movement analyses is standard among HPSG grammarians of German and there is data from apparent multiple frontings that makes an analysis which is the HPSG analogue of head-movement unavoidable (Müller 2003a; 2005b)."

Two small imprecisions, neither changing the verdict:
- Section 5.1 presents the unary rule, DSL and Figure 5 using English auxiliary inversion (Borsley 1989), then says most researchers on German assume such analyses. It is not a German-specific exposition.
- The Ch. 28 wording is "analogue to head-movement analyses", not "analogue of head movement".

## EE-2: Traces at gap sites remain a live option in the theory

**Verdict:** supported

**Claim checked:** Ch. 13 (Section 2, p. 540; Section 3, pp. 543-549; Section 10, p. 582) says both trace-based and traceless analyses of gaps exist in HPSG, lists the question among the unresolved ones, and calls the traceless view 'probably the most widely assumed position'. Ch. 1 (Section 2, p. 6) notes 'some debate'. Ch. 4 (Section 5.3, p. 165, fn. 12) lists trace-based approaches including Levine and Hukari (2006) and Müller (2015, CoreGram). No chapter says whether the ERG uses traces.

**Explanation:** All cited passages exist and say what the claim reports.

- **Ch. 13, Section 2, p. 540:** "Both positions have been developed within HPSG, but probably the view that there is nothing at all in constituent structure is the more widely assumed position."
- **Ch. 13, Section 3, pp. 543-549:** p. 543 says "some HPSG work assumes that they are empty categories, often called traces". The quoted phrase is on p. 544: "Probably the most widely assumed position is that gaps are only represented in ARG-ST lists". The section also covers trace-based work: early HPSG, Levine & Hukari (2006) with an empty category for both subject and complement gaps, and fn. 10 on Archi favoring a trace-based perspective.
- **Ch. 13, Section 10, p. 582:** "there are some unresolved issues ... In particular, there is disagreement about whether or not gaps are empty categories".
- **Ch. 1, Section 2, p. 6:** much HPSG work assumes no phonologically empty elements in unbounded dependencies; "There is, however, some debate here (Sag & Fodor 1995; Müller 2004; Borsley & Crysmann 2021: Section 3)".
- **Ch. 4, Section 5.3, p. 165, fn. 12:** "But see Levine & Hukari (2006), Müller (2015), Müller & Machicao y Priemer (2019: Section 4.9) and Müller (2021c) for trace-based approaches." The Ch. 4 bibliography confirms Müller 2015 is the CoreGram paper.
- **ERG:** a grep across all chapters for ERG / English Resource Grammar near trace, empty-element, gap or slash terms found no statement on whether the ERG uses traces. The only nearby mention is a Ch. 25 footnote saying the ERG's SLASH list cannot have more than one element. This negative rests on keyword search, not a full read.

Two small precision points that do not change the verdict: the quoted wording is on p. 544 in Section 3 (Section 2, p. 540 says "the more widely assumed position"), and fn. 12 lists four works, of which the claim names two (it says "including"). I did not check the Ch. 32 page range (pp. 1502-1504); Ch. 32 Section 1.2.1 does discuss HPSG versions with and without empty elements.

## CO-1: Order domains decouple word order from the derivation tree

**Verdict:** supported

**Claim checked:** Ch. 10 (Section 6, pp. 390-397) describes constituent order domains in which the mother's DOM is the shuffle of the daughters' contributions and the tree 'does not correspond to the linearization of the DOMAIN objects'. Ch. 11 (Section 5.2.1, p. 464) says scrambling with Korean control verbs 'must be due to a different process (that is, domain union ...)'. Ch. 1 (Section 7.1, pp. 32-34) calls the role of domains 'an unresolved matter'. Ch. 25 (Section 3.3.3, pp. 1119-1120) says Babel, a broad-coverage German grammar, makes extensive use of discontinuous constituents.

**Explanation:** All four attributed passages are in the chapter texts at the cited places.

- Ch. 10 (Müller), Section 6 "Constituent order domains and linearization" starts on p. 390. Constraint (34) on p. 391 computes the mother's DOM as the shuffle of the head daughter's DOM with the list of non-head daughters. Section 6.2 (p. 394) gives the variant where "the DOM values of the daughters are shuffled into the domain of the mothers". The Figure 9 caption (p. 393) reads: "The tree shows the order of combination, which does not correspond to the linearization of the DOMAIN objects." The text adds that the shuffle formulation "allows for discontinuous constituents".
- Ch. 11 (Godard), Section 5.2.1, p. 464: "They take VP complements, and scrambling in (53) must be due to a different process (that is, domain union, as in Lee 2001; see Reape 1994)." This is about Korean control verbs, as claimed.
- Ch. 1 (Abeillé and Borsley), Section 7.1 "Order domains", pp. 32-33: observed order is "a reflection not of the constituent structure of an expression but of a separate system of order domains", and "exactly how much of a role they should play in syntax is an unresolved matter."
- Ch. 25 (Bender and Emerson), Section 3.3.3, p. 1119: "Babel is a broad-coverage grammar of German (Müller 1996; 1999). One interesting feature of this grammar is that it makes extensive use of discontinuous constituents (Müller 2004a)."

Three small imprecisions do not change the verdict:
- In (34) the non-head daughters are inserted as whole objects; only the Section 6.2 variant shuffles the daughters' own DOM values.
- Section 6 runs past p. 397, since Section 6.4 "Problems with order domains" starts there.
- The Ch. 1 quote is specifically about how much of a role domains should play in syntax.

I did not check the Ch. 30 and Ch. 31 locations in the citation list, because the claim text attributes nothing to them.

Files: reading/handbook/txt/ch10.txt, ch11.txt, ch01.txt, ch25.txt in the same directory.

## BU-1: Theoretical HPSG for English and French assumes flat, n-ary structures

**Verdict:** partly-supported

**Claim checked:** Ch. 10 (Section 3, pp. 375-377) says researchers working on English and French 'usually assume a flat structure', and Section 5.2 (pp. 386-387) presents the Sag et al. (2020) analysis of auxiliary-initial clauses as one ternary local tree. Ch. 28 (Section 4.2.1, pp. 1284-1288) presents flat and binary structures as both viable. Ch. 16 (Section 3, pp. 729-732) formalizes coordination with an unbounded DTRS list. Ch. 25 does not state that DELPH-IN rules are at most binary.

**Explanation:** The detailed sub-statements all check out against the text, but the quoted headline ("assumes flat, n-ary structures") is stronger than what the chapters say.

Verified:
- Ch. 10, Section 3 (p. 377; reading/handbook/txt/ch10.txt lines 396-401): "Researchers working on English and French usually assume a flat structure (Pollard & Sag 1994: 39-40, 362; Sag 1997: 479; Ginzburg & Sag 2000: 34; Abeillé & Godard 2000) but assuming binary branching structures would be possible as well ... For languages like German it is usually assumed that structures are binary branching (but see Reape 1994: 156 and Bouma & van Noord 1998: 51)."
- Ch. 10, Section 5.2 (pp. 386-387, Figure 6 "based on Sag et al. (2020: 117)"): the auxiliary-initial clause "Did Kim get the job?" is one local tree S -> V NP VP, licensed by "a schema combining a head with its subject and its VP complement in one go". The word "ternary" is not used there, but the tree is ternary.
- Ch. 28, Section 4.2.1 (pp. 1284-1288): "both flat structures and binary branching structures with different branching directions as in Figure 13 are a viable option in HPSG"; a flat structure is preferred for Welsh, while the head-movement analogue is "standard among HPSG grammarians of German".
- Ch. 16, Section 3 (pp. 729-732): constraint (11) coord-phrase has DTRS as a non-empty list appended to a non-empty list (no upper bound), with subtypes in (12).
- Ch. 25: the only occurrence of "binary" is about Miyao et al. converting Penn Treebank trees to binary-branching ones (Enju); nothing says DELPH-IN rules are at most binary.
- Ch. 1, Section 5.1 (pp. 22-23): "There is no assumption in HPSG that all branching is binary", with footnote 30 noting binary branching is assumed in HPSG grammars for a number of languages.

Overstatements / gaps:
- The headline drops the hedge "usually" and the explicit caveat that binary branching would be possible as well for English and French. The Handbook does not use the term "n-ary".
- Ch. 16 presents the DTRS-list formalization as one of three options (the "flat branching" one, rule 8b). It states that the binary branching analysis of coordination is used in much HPSG work, including Pollard & Sag (1994: 200-205), Beavers & Sag (2004), Drellishak & Bender (2005), and Chaves (2007; 2012b), and that the totally flat analysis is used "much less frequently" (Sag et al. 2003; Sag 2003). So Ch. 16 does not support a blanket flat-structure claim for coordination.
- The blanket citation of chapters 2, 3, 5, 8, 11, 18, 30 was not checked passage by passage; Ch. 12 and Ch. 32 contain only passing mentions (Ch. 12 fn. on Romance flat structure; Ch. 32 fn. 18 "The schema in (8) licenses flat structures").

**Corrected statement:** The Handbook says that HPSG does not require binary branching (Ch. 1, Section 5.1, pp. 22-23) and that researchers working on English and French "usually assume a flat structure" for head-complement phrases (Pollard & Sag 1994; Sag 1997; Ginzburg & Sag 2000; Abeillé & Godard 2000), while noting that binary branching would be possible as well and is the usual assumption for German (Ch. 10, Section 3, p. 377). Ch. 10, Section 5.2 (pp. 386-387, Figure 6) presents the Sag et al. (2020) analysis of English auxiliary-initial clauses as a single flat local tree with three daughters (V, NP, VP). Ch. 28, Section 4.2.1 (pp. 1284-1288) says both flat and binary branching structures are viable options in HPSG. Ch. 16, Section 3 (pp. 729-732) formalizes the flat-branching analysis of coordination with a DTRS list of unbounded length (constraints 11-12), but reports that the binary branching analysis of coordination is also widely used in HPSG, including by Pollard & Sag (1994: 200-205). Ch. 25 makes no statement about the maximum arity of DELPH-IN rules.

## DR-1: Non-canonical argument realization may have no rule node in the tree

**Verdict:** supported

**Claim checked:** Ch. 13 (Section 2, pp. 540-541; Section 3, pp. 544, 546-547) presents the mainstream traceless analysis in which the gap is only on ARG-ST and the slashed verb has a shorter COMPS list, with no rule named. Ch. 9 (Section 3.1, pp. 320-321) says exceptions to the Argument Realization Principle are handled by a lexical rule or by a feature on each ARG-ST item (Bouma et al. 2001). Ch. 4 (Section 5.2, pp. 158-159) shows the Complement Extraction Lexical Rule applying to any complement in COMPS, and (Section 5.3, p. 165) says there is 'no general guideline' for choosing between lexical rules and underspecification.

**Explanation:** All cited passages exist at the stated pages and say what the claim reports.

Ch. 13 (reading/handbook/txt/ch13.txt):
- Section 3, p. 544: "Probably the most widely assumed position is that gaps are only represented in ARG-ST lists" (citing Sag 1997, Bouma, Malouf & Sag 2001, Ginzburg & Sag 2000, Sag 2010).
- Example (18), "Representation of a slashed verb (traceless)", p. 544, shows put with ARG-ST <NP, NP[gap], PP> but COMPS containing only the PP. No lexical rule is named.
- pp. 546-547: "nonlocal realisation corresponds to lexical valence reduction"; "gaps will not be present on the valence lists of word-level signs"; "a traceless, lexical approach to unbounded dependencies".
- Section 2, pp. 540-541, gives the gap representation and the head-driven SLASH percolation, with no trace in Figures 1-2.

Ch. 9, Section 3.1, pp. 320-321: non-canonical signs that violate the ARP "have been approached in two ways". One is a lexical rule that removes items from the valence lists and places an item on SLASH or adds an affix. The other is "a feature of each ARG-ST list item" that specifies whether the item is subject to the ARP.

Ch. 4:
- Section 5.2, p. 158: the CELR (35), adapted from Pollard & Sag 1994: 378, takes any lexeme with a syntactic argument on COMPS and outputs an entry with that argument off COMPS and its LOCAL value in SLASH.
- Section 5.3, pp. 159-160: the Bouma et al. (2001) alternative uses gap-ss and a constraint on word, so "there is no need for the lexical rule in (35)".
- p. 165: on underspecification versus unary-branching (lexical) rules, "Unfortunately, there is no general guideline; it depends on the nature of the data".

Two minor imprecisions, neither changing the verdict:
1. Ch. 9 does not itself attribute the per-item-feature approach to Bouma et al. (2001). It cites them only for the term "canonical signs". The attribution of the non-lexical-rule alternative to Bouma et al. is explicit in Ch. 4, Section 5.3, pp. 159-160, where it is stated as synsem subtypes (canon-ss / gap-ss), not as a feature.
2. Ch. 13 says of (18) "We ignore the COMPS feature", so the shorter COMPS list is shown in the AVM and confirmed in prose only on p. 546.

Ch. 1 and Ch. 5 are in the cited location list, but the claim text attributes nothing to them, so I did not check them.

## DR-2: A binary head-complement rule may discharge an arbitrary COMPS element

**Verdict:** supported

**Claim checked:** Ch. 10 (Section 3, pp. 379-380) gives binary Head-Complement Schema (19), which splits the head daughter's COMPS with two appends and realizes 'an arbitrary element' as the non-head daughter; for fixed-order head-initial languages such as English it is restricted to the first element. Ch. 11 (Section 5.1.2, pp. 456-457) uses the German schema (38) with the discharged element 'in any position' and finite subjects on COMPS.

**Explanation:** Both cited passages say what the claim reports, and the locations are right.

Ch. 10 (reading/handbook/txt/ch10.txt, lines 473-501; Section 3 "Flat and binary branching structures", p. 379, Figure 3 on p. 380):
- Schema (19), "Head-Complement Schema (binary branching)", gives the mother COMPS as 1 ⊕ 2 and the head daughter COMPS as 1 ⊕ <3> ⊕ 2, with 3 identified with the non-head daughter's SYNSEM. That is two appends.
- The text says the schema "works for languages that allow for scrambling, since it allows an arbitrary element to be taken out of the COMPS list of the head daughter and realize it in a local tree."
- It then says the schema can be "parameterized" for fixed order: "for head-initial languages with fixed order (e.g., English), 1 would be the empty list (= combination with the first element in the list)". The claim omits the parallel case, where head-final fixed-order languages have 2 empty (last element).

Ch. 11 (reading/handbook/txt/ch11.txt, lines 1753-1772; Section 5.1.2 "Coherent constructions in HPSG", p. 456, Figure 11 "Clause structure in German" on p. 457):
- Schema (38), "head-complement-phrase (German)", has the same 1 ⊕ <3> ⊕ 2 split, plus LIGHT − on the mother.
- The text says: "the head combines with one complement at a time, noted as 3. The presentation of the list as composed of three parts, with the relevant one in any position, allows for a free order."
- On subjects it says: "the subject of finite verbs is considered as a complement, and is introduced by the same rule" (citing Pollard 1996).

One wording nuance: the "arbitrary element" freedom is stated for scrambling languages, which the claim's "may" already covers. The quoted phrase in Ch. 11 is "the relevant one in any position".

## DR-3: Theoretical analyses use sets, relations and defaults beyond plain unification

**Verdict:** partly-supported

**Claim checked:** Ch. 3 (Section 2, pp. 93, 96-98) says negation, disjunction, quantification, relations and chains are all necessary to render the Pollard and Sag (1994) grammar, and (p. 93) that partial-information algebras and unification 'are still essential for all current HPSG implementation platforms'. Ch. 13 (Section 4, pp. 549-550) says SLASH Amalgamation is a default constraint and SLASH is a set combined by union. Ch. 25 (Section 2.2.1, p. 1109, fn. 9) says the boundedness argument for DELPH-IN grammars assumes no relational constraints, that SLASH has at most one element in the ERG, and that DELPH-IN does not adopt DEPS.

**Explanation:** The substance holds, but the Ch. 3 necessity statement is cited to the wrong place and is worded more specifically than the text.

Ch. 3 (reading/handbook/txt/ch03.txt):
- The p. 93 quote is accurate: the ideas and algebras of feature logics of partial information "are still essential for all current HPSG implementation platforms". The subject is those ideas and algebras; unification is named in the preceding sentence.
- The necessity statement is not in Section 2, pp. 96-98. It is at the end of Section 4, p. 113: "all syntactic constructs of the logical languages above are necessary to achieve that goal without reformulating the grammar" (the goal being a logical rendering of the Pollard and Sag 1994 grammar, per Appendix C of Richter 2004).
- That sentence does not list negation, disjunction, quantification, relations and chains. The list is an inference from the RSRL constructs defined in Sections 3-4 (chains pp. 103-104; quantification, negation and connectives p. 105).
- Section 2, pp. 96-98 only illustrates some of these informally: implication and disjunction in the Word Principle (3b), relations in (3c), and chains in fn. 5 on p. 98.

Ch. 13 (ch13.txt), Section 4, pp. 549-551: supported. SLASH Amalgamation (28) is given on p. 549, and p. 550 says "This is a default constraint, as indicated by the '/'" and that by default the SLASH value of a word is the union of its arguments' SLASH values. Page 551 shows set-valued SLASH and the Nonlocal Feature Principle "using set union".

Ch. 25 (ch25.txt), Section 2.2.1, p. 1109: supported, with small wording differences.
- Body text: for DELPH-IN grammars the number of feature structures is bounded, "Assuming a system without relational constraints".
- Fn. 9: "DELPH-IN does not adopt proposals like the DEPS list of Bouma, Malouf & Sag (2001)", and "in many DELPH-IN grammars, including the English Resource Grammar (ERG), the SLASH list cannot have more than one element".
- The no-relational-constraints assumption is in the body text, not the footnote, and Ch. 25 calls SLASH a list.

I did not check the other chapters in the cited list (1, 4, 9, 10, 11, 14, 17, 21, 23), since the claim text makes no specific assertion about them.

**Corrected statement:** Ch. 3 (Section 2, p. 93) says the ideas and algebras of feature logics of partial information, on which unification is defined, "are still essential for all current HPSG implementation platforms", and that the descriptions of Pollard and Sag (1994) can no longer be arranged in such an algebra. Section 2 (pp. 96-98) informally illustrates implication, disjunction, relations and (fn. 5, p. 98) chains. Ch. 3 Section 4, p. 113 states that "all syntactic constructs of the logical languages above are necessary" to render the Pollard and Sag (1994) grammar without reformulating it; those constructs, defined in Sections 3-4 (pp. 103-105), include negation, the classical connectives, quantification, relations and chains. Ch. 13 (Section 4, pp. 549-551) says SLASH Amalgamation is a default constraint under which a word's SLASH value is the union of its arguments' SLASH values, and that the Nonlocal Feature Principle combines daughters' SLASH values by set union. Ch. 25 (Section 2.2.1, p. 1109) says the boundedness of feature structures in DELPH-IN grammars assumes a system without relational constraints; fn. 9 adds that DELPH-IN does not adopt proposals like the DEPS list of Bouma, Malouf and Sag (2001) and that in many DELPH-IN grammars, including the ERG, the SLASH list cannot have more than one element.

## SE-1: For fragments, gapping and ellipsis the content comes from context

**Verdict:** supported

**Claim checked:** Ch. 19 (Section 4, pp. 860-864) gives the Head-Fragment Schema (31), a unary rule mapping a non-verbal XP to an S whose propositional content is supplied by MAX-QUD, and says all existing HPSG analyses of fragments are based on it; Section 5 (pp. 868-870) treats the elided VP as a noncanonical pro on ARG-ST resolved from 'structured discourse information'. Ch. 16 (Section 7, pp. 763-764, Figure 14) presents direct-interpretation gapping in which the Question Under Discussion of the first clause supplies the verbal semantics.

**Explanation:** Checked against reading/handbook/txt/ch19.txt and ch16.txt; every element of the claim is in the text at (or within) the cited pages.

Ch. 19, Section 4 ("Analyses of nonsentential utterances", starts p. 860): the Head-Fragment Schema (31) is on p. 862, a single-daughter constraint with mother CAT S and a head daughter [HEAD nonverbal] matched to SAL-UTT. The text says it "allows any non-verbal phrasal category (NP, AP, VP, PP, AdvP) to be mapped onto a sentential utterance as long as it corresponds to a Salient Utterance". P. 863: "MAX-QUD provides the propositional semantics for a nonsentential utterance" and its content "can be supplied by either linguistic or nonlinguistic context". P. 864: "in fact all existing analyses of nonsentential utterances (Sag & Nykiel 2011; Ginzburg 2012; Abeille et al. 2014; Kim 2015; Abeille & Hassamal 2019; Kim & Abeille 2019) are based on the Head-Fragment Schema in (31)".

Ch. 19, Section 5 ("Analyses of predicate/argument ellipsis", starts p. 868; relevant text on pp. 869-870): the Argument Realization Principle "allows an argument to be a noncanonical synsem such as pro which need not be mapped onto COMPS"; lexical entry (48) for can has ARG-ST <NP, VP[pro]> with empty COMPS; "ellipsis resolution is not based on syntactic reconstruction in HPSG analyses, but rather on structured discourse information (see Ginzburg & Sag 2000: 295)", with the antecedent information provided by the Dialog Game Board via MAX-QUD.

Ch. 16, Section 7 ("Non-constituent coordination"), p. 763 and Figure 14 on p. 764: "direct-interpretation accounts where the missing material is recovered from the preceding linguistic context (Mouret 2006; Abeille et al. 2014; Park 2019)... illustrated in Figure 14... the Question Under Discussion (QUD, Roberts 1996) of the first clause is λy.λx.∃e(like(x,y)) which is information that is shared across the clausal daughters... This allows the second coordinand to combine the two NPs with the verbal semantics, and recover the propositional meaning."

Minor precision points, none of which change the verdict:
- "Unary rule" is the claim's wording; the chapter calls (31) a "constructional constraint" (the schema does have one daughter).
- The "all existing analyses" statement is about nonsentential utterances (fragments and sluices), which is how the claim uses it.
- The chapter's "non-verbal" list oddly includes VP; that is the Handbook's own wording.
- Ch. 16 also notes that elliptical (non-direct-interpretation) accounts of gapping exist (Chaves 2006), so the QUD analysis is presented as one of two families; the claim's wording ("presents direct-interpretation gapping") is consistent with that.
- I did not check the other cited locations (Ch. 19 Section 6.1, Ch. 15 Section 13, Ch. 26 Section 4, chapters 12, 18, 29), because the claim's specific assertions rest only on Ch. 19 Sections 4-5 and Ch. 16 Section 7.

## TE-1: The tagger carries all disambiguation, and lexical types cover about half of it

**Verdict:** partly-supported

**Claim checked:** Ch. 25 (Section 2.2.2, pp. 1110-1112; Section 5.1, pp. 1128-1129) reports that the 2018 ERG gives 21 readings for a five-word sentence and 35,094 for one newspaper sentence, that ranking is done by a separate statistical model trained on treebanks, and that in Redwoods about half the ambiguity is lexical and half syntactic.

**Explanation:** The reported details all check out, and the page references are right. Ch. 25 Section 2.2.2 (pp. 1110-1112) says the 2018 ERG gives 21 readings for example (2), "My favorite town criers speak clearly" (five words), and 35,094 readings for example (3), the first line of a newspaper article. It says parse ranking "is not usually determined by the grammar itself"; typically a statistical system is trained on a treebank of gold parses to pick the gold parse out of the parse forest. Section 5.1 (pp. 1128-1129) says Toutanova et al. (2002; 2005) found that in the Redwoods treebank (3rd Growth) "roughly half of the ambiguity was lexical, and half syntactic". Ch. 2 Section 9 (pp. 66-67) confirms that the ERG and other DELPH-IN grammars use a treebank-trained statistical model applied at run time for parse selection.

The headline, however, is not what the chapter says, in two respects.

1. "The tagger carries all disambiguation" misattributes the mechanism. The chapter assigns disambiguation to a statistical parse-ranking model that scores whole parses in the forest, using features such as construction likelihood, valence frames, collocations and semantic relations. Supertagging and ubertagging appear only as an optional pruning step before parsing: they choose lexical entries to shrink the search space and can improve speed and accuracy. The chapter never says a tagger carries all disambiguation.

2. "Lexical types cover about half of it" is an inference the chapter does not make. The Redwoods finding describes the source of ambiguity (half lexical, half syntactic). The chapter does not say that lexical types or a supertagger resolve that half; it adds that combining sources of information, such as semantic and syntactic, is important for resolving ambiguity.

Files checked: reading/handbook/txt/ch25.txt (lines 233-330, 1098-1118) and reading/handbook/txt/ch02.txt (lines 889-902).

**Corrected statement:** Disambiguation is carried by a separate statistical parse-ranking model, not by the grammar, and about half of the ambiguity it must resolve is lexical. Ch. 25 (Section 2.2.2, pp. 1110-1112) reports that the 2018 ERG gives 21 readings for a five-word sentence and 35,094 for one newspaper sentence, and that ranking is typically done by a statistical model trained on a treebank of gold parses chosen from the parse forest (also Ch. 2 Section 9, pp. 66-67). Supertagging/ubertagging is described only as an optional pruning step that selects lexical entries before parsing to reduce the search space, improving speed and often accuracy. Section 5.1 (pp. 1128-1129) reports that in the Redwoods treebank (3rd Growth) roughly half of the ambiguity is lexical and half syntactic (Toutanova et al. 2002; 2005), and that combining sources of information is important for resolving it. The Handbook does not say that a tagger carries all disambiguation or that lexical types resolve half of it.

## UD-1: Headedness is analysis-dependent and some phrases have no head

**Verdict:** partly-supported

**Claim checked:** Ch. 16 (Section 2, pp. 726-729) treats coordination as non-headed. Ch. 8 (Sections 2.1-2.3, pp. 278-295) shows the noun as head of a nominal in the specifier and functor treatments and the determiner as head in the DP treatment. Ch. 1 (Section 6.2, pp. 31-32) says of determiners and complementizers 'There is no consensus here'. Ch. 14 (Section 4.2.3, pp. 643-646) says no analysis taking material inside a free relative as head covers the data. Ch. 32 (Section 4.1, pp. 1530-1534) analyzes NPN as a headless construction.

**Explanation:** Four of the five sub-claims check out against the text; the Ch. 1 one is overstated.

- **Ch. 16, Section 2 (pp. 726-729): supported.** The text says "HPSG adopts a rather traditional non-headed analysis of coordination" (p. 728) and argues that category and distribution are determined collectively by the coordinands.
- **Ch. 8, Sections 2.1-2.3 (pp. 278-295): supported.** The specifier and functor treatments are both NP approaches with the noun as head. In the DP treatment "the determiner ... selects the nominal as its complement" and the result is a DP with HEAD det (Figure 6, p. 284). Section 2.4 adds that the NP treatments fit a monostratal surface-oriented framework better than the DP treatment.
- **Ch. 1, Section 6.2: overstated.** "There is no consensus here" (p. 31) closes a passage about complementizers only: a marker analysis was originally proposed, but they have also been analyzed as heads (Sag 1997; Ginzburg & Sag 2000). For determiners, Ch. 1 contrasts specifier and marker analyses, and in both the determiner is a non-head and the noun is the head (Figures 11-12). Ch. 1 therefore reports no dispute about headedness for determiners. The section runs pp. 30-31, not 31-32.
- **Ch. 14, Section 4.2.3 (pp. 643-646): supported, with a caveat.** The sentence "No account assuming any of the material in the relative clause to be the head can account for the data" is in footnote 66 (p. 646). It concerns German mismatching free relatives (Müller 1999a). The main text only presents the dilemma between wh-phrase as head and clause as head.
- **Ch. 32, Section 4.1 (pp. 1530-1533): supported.** The abstract says some areas "seem to require headless phrasal constructions (e.g., the NPN construction ...)". The section gives Bargmann's (2015) phrasal formalization and argues that head-based approaches cannot capture it. The section ends on p. 1533, not 1534.

Ch. 31, Section 5.1 is in the cited locations but argues the opposite, from Word Grammar: "there are no headless phrases" and "it seems reasonable to hypothesise that all phrases have heads". It is on pp. 1474-1477, not 1475-1478. It shows the question is contested in the Handbook but does not support "some phrases have no head".

I did not check the other chapters in the location list (13, 20, 22, 28) beyond a keyword search, which found non-headed coordination mentioned in Ch. 13 and Ch. 28 and an NPN section in Ch. 28 (4.2.3).

**Corrected statement:** Headedness is analysis-dependent and, in HPSG, some phrases have no head. Ch. 16 (Section 2, pp. 726-729) says HPSG adopts a non-headed analysis of coordination. Ch. 8 (Sections 2.1-2.3, pp. 278-295) shows the noun as head of a nominal in the specifier and functor treatments and the determiner as head in the DP treatment (Figure 6, p. 284). Ch. 1 (Section 6.2, pp. 30-31) says "There is no consensus here" about whether complementizers are markers or heads; for determiners it contrasts specifier and marker analyses, both of which keep the noun as head. Ch. 14 (Section 4.2.3, footnote 66, p. 646) says that, for German mismatching free relatives, "No account assuming any of the material in the relative clause to be the head can account for the data". Ch. 32 (abstract and Section 4.1, pp. 1530-1533) treats NPN as requiring a headless phrasal construction. Ch. 31 (Section 5.1, pp. 1474-1477) gives the opposing Word Grammar position that all phrases have heads.

## UD-2: No uniform formal notion of subject; ARG-ST order and grammatical function come apart

**Verdict:** supported

**Claim checked:** Ch. 30 (Section 4, pp. 1404-1405) says HPSG identifies the subject, 'if at all', as a language-specific element of ARG-ST, and that for German it must be defined through case. Ch. 10 (Section 4, pp. 380-383) says German subjects of finite verbs are standardly on COMPS. Ch. 9 (Section 3.3, pp. 323-325) reports that in Balinese Objective Voice the subject is a term other than the ARG-ST-initial one.

**Explanation:** All three cited passages exist at the cited places and say what the claim reports. I checked Ch. 30, Ch. 10 and Ch. 9 only; the other listed chapters (5, 7, 12, 20, 31) are not needed for the three statements in the claim and were not checked.

- **Ch. 30, Section 4 "Grammatical functions and valence", pp. 1404-1405** (reading/handbook/txt/ch30.txt, lines 440-472): "while LFG identifies subjects in every language with the attribute SUBJ, ... HPSG identifies the subject, if at all, as a specific element of the ARG-ST list, but which element it is can vary with the language. An English subject is usually assumed to be the first element in the list, or ARG-ST|FIRST, while the definition of a German subject necessarily involves the CASE feature (Reis 1982)." It adds that German subjects cannot be ARG-ST|FIRST because in subjectless sentences the first ARG-ST item is a non-subject. On p. 1405, HPSG practitioners who do not adopt an LFG-style SUBJ feature "lack a formal correlate of the notion 'subject'". This supports the headline.
- **Ch. 10, Section 4 "SVO vs. SOV", p. 382** (reading/handbook/txt/ch10.txt, lines 631-633): "For German, it is standardly assumed that the subjects of finite verbs are treated like complements (Pollard 1996: 295-296, Kiss 1995: Section 3.1.1) and hence are represented on the COMPS list."
- **Ch. 9, Section 3.3 "Syntactic ergativity", p. 323** (reading/handbook/txt/ch09.txt, lines 380-395): for Balinese as analyzed by Wechsler & Arka (1998), "In the morphologically unmarked, and most common voice, called Objective Voice (OV), the subject is any term except the ARG-ST-initial one."

Two small nuances, neither of which changes the verdict:
- Ch. 30 hedges the variation claim with "many variants of the HPSG framework allow the representation to vary from language to language", and notes that some HPSG work does adopt LFG-style grammatical function features (the qVAL feature of Kropp Dakubu et al. 2007, the ERG feature of Pollard 1994).
- Ch. 30 says the definition of a German subject "necessarily involves" CASE, which is slightly weaker than "must be defined through case".
