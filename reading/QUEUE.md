# Reading queue

Items are read in order during idle time (overnight), a few per night. Each reading
writes `reading/notes/<slug>.md` with the sections used for the Handbook notes (Summary;
Caveats for the parser; Support for the design; Theory strains; Key primary sources;
Not covered here) and updates the theory log when warranted. Mark an item `done` with
the date when its notes exist. Long items are read one chapter per entry.

| # | Status | File | Item | Question to answer |
|---|---|---|---|---|
| 1 | done 2026-11-20 | Bouma-Malouf-Sag-SatisfyingConstraintsOnExtract.pdf (66 pages; the 62-page SatisfyingConstraintsOnExtractionAndAdjunction.pdf is another version: note the differences briefly) | Bouma, Malouf and Sag: Satisfying constraints on extraction and adjunction | Is traceless extraction deterministic under replay? What do DEPS and SLASH amalgamation require of the engine? |
| 1a | done 2026-11-20 | PollardSag1994.pdf (460 pages; scanned, check the text layer and read page images where it is poor) | Pollard and Sag 1994, Chapter 9 (valence revision, traceless extraction) | What the 1994 theory assumes that DELPH-IN changed; determinism of replay |
| 1b | done 2026-11-20 | HPSG-Inspired_Joint_Neural_Constituent_and_Dependency_Parsing_in_On3_Time_Complexity.pdf | HPSG-inspired joint neural constituent and dependency parsing (IEEE/ACM TASLP 2022) | Closest prior neural work: what it takes from HPSG, what it leaves out, how it joins constituents and dependencies |
| 1c | done 2026-11-21 | Sagae-Miyao-Tsujii-2007-shallow-dependency-constraints.pdf (ACL P07-1079) | Sagae, Miyao and Tsujii 2007: HPSG parsing with shallow dependency constraints (ACL; open access, fetch from the ACL Anthology) | Precedent for constraining a grammar-based parser with predicted dependencies: how, and what speed and accuracy it gave |
| 1d | done 2026-11-22 | Ninomiya-et-al-2009-shift-reduce-default-unification.pdf (EACL E09-1069) | Ninomiya, Matsuzaki, Shimizu and Nakagawa 2009: Deterministic shift-reduce parsing for unification-based grammars by using default unification (EACL) | A classifier chooses rule applications and the grammar executes them: what happens when unification fails, and what default unification buys |
| 1e | done 2026-11-22 | Zhang-Krieger-2011-PCFG-approximation-HPSG.pdf (IWPT W11-2923) | Zhang and Krieger 2011: Large-scale corpus-driven PCFG approximation of an HPSG (IWPT) | Derivations proposed by a model trained on ERG treebanks, then rebuilt with the grammar: how often they are licensed |
| 1f | held | (not found in the ACL Anthology under this citation; needs the correct reference) | Packard and Flickinger 2017: Evaluating hybrid approaches to robust parsing (IWPT) | Robust unification over derivations the grammar does not license: a model for our relaxed level |
| 1g | done 2026-11-22 | Zhang-Oepen-Carroll-2007-nbest-unification.pdf (IWPT W07-2207) | Zhang, Oepen and Carroll 2007: Efficiency in unification-based n-best parsing (IWPT) | Selective unpacking replays unifications for chosen trees: failure rates and cost |
| 1h | todo | (fetch from the ACL Anthology, COLING 2002, C02-1075 or nearby; ask before downloading) | Kiefer, Krieger and Prescher 2002: A novel disambiguation method for unification-based grammars using probabilistic context-free approximations (COLING) | Closest precedent for Orca: a PCFG predicts derivations, unification replays them. How often did replay succeed, and what did it cost? |
| 2 | done 2026-11-20 | MRS_intro_1999.pdf | Copestake, Flickinger, Pollard and Sag 2005: Minimal Recursion Semantics: An introduction (Research on Language and Computation 3:281-332; the file name says 1999, but the file is the published article, which is based on a 1999 draft) | Does MRS fall out of replay with no extra choices? What must the engine implement for composition? |
| 3 | done 2026-11-20 | MRS_algebra.pdf | Copestake, Lascarides and Flickinger: An algebra for semantic construction | Composition rules per schema; basis for the relaxed level |
| 4 | done 2026-11-20 | Copestake_MRS_algebra_2007.pdf | Copestake 2007: Semantic composition with (Robust) MRS | What a relaxed, underspecified semantic level can look like |
| 5 | done 2026-11-20 | sag-coordination.pdf | Sag: Coordination and underspecification | Coordination of unlikes and syncretism: effect on labels and replay |
| 6 | done 2026-11-20 | coordination.pdf | Drellishak and Bender: A coordination module for a crosslinguistic grammar resource | Cross-linguistic coordination in an implemented core; lessons for our core |
| 7 | done 2026-11-21 | Word Order in HPSG.pdf | Oliva 1992 (COLING): The proper treatment of word order in HPSG | Order domains versus a continuous backbone |
| 8 | done 2026-11-21 | FrenchCliticsSag.pdf | Miller and Sag: French clitic movement without clitics or movement | Arguments without leaves; token-to-leaf alignment |
| 9 | done 2026-11-20 | oepen-carroll-2002.pdf | Oepen and Carroll: Efficient parsing for unification-based grammars (Chapter 9 of Efficiency in unification-based processing, Oepen, Flickinger, Tsujii and Uszkoreit, eds.; the file contains only this chapter) | Replay engine design |
| 10 | done 2026-11-20 | Slayden-MS-thesis.pdf | Slayden: Array TFS storage for unification grammars (split by chapter) | Replay engine design |
| 11 | done 2026-11-22 (one row per chapter below) | Carroll-Dissertation.pdf | Carroll 1993 dissertation: Practical unification-based parsing of natural language (split by chapter) | Unification-based parsing in practice |
| 11a | done 2026-11-21 | Carroll-Dissertation.pdf | Chapter 1: Introduction (pp. 1-18) | Unification-based parsing in practice |
| 11b | done 2026-11-22 | Carroll-Dissertation.pdf | Chapter 2: The ANLT grammar formalism and unification algorithm (pp. 19-42) | Unification-based parsing in practice |
| 11c | done 2026-11-22 | Carroll-Dissertation.pdf | Chapter 3: The ANLT chart parser (pp. 43-70) | Unification-based parsing in practice |
| 11d | done 2026-11-22 | Carroll-Dissertation.pdf | Chapter 4: LR parsing in a unification-based grammar framework (pp. 71-90) | Unification-based parsing in practice |
| 11e | done 2026-11-22 | Carroll-Dissertation.pdf | Chapter 5: Non-deterministic LR parsing with unification grammars (pp. 91-116) | Unification-based parsing in practice |
| 11f | done 2026-11-22 | Carroll-Dissertation.pdf | Chapter 6: Probabilistic LR parsing (pp. 117-143) | Unification-based parsing in practice |
| 11g | done 2026-11-22 | Carroll-Dissertation.pdf | Chapter 7: Conclusions (throughput, parse selection, undergeneration; pp. 144-153) | Unification-based parsing in practice |
| 12 | done 2026-11-22 (one row per chapter below) | antske-fokkens-phd.pdf | Fokkens dissertation (split by chapter) | Design of the Matrix successor; alternative analyses side by side |
| 12a | done 2026-11-22 | antske-fokkens-phd.pdf (text in txt/) | Chapter 1: Introduction (pp. 1-25) | Design of the Matrix successor; alternative analyses side by side |
| 12b | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 2: Background: HPSG, DELPH-IN, the Grammar Matrix (pp. 26-66) | Design of the Matrix successor |
| 12c | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 3: The CLIMB methodology (pp. 67-121) | Alternative analyses side by side |
| 12d | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 4: CLIMB for Germanic languages (pp. 122-) | Alternative analyses: auxiliaries, word order |
| 12e | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 5: Evaluation of GCLIMB | Efficiency of alternative analyses |
| 12f | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 6: Multilingual aspects of CLIMB (pp. 214-298) | Matrix core in other grammars |
| 12g | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 7: Related work (pp. 299-342) | Metagrammars across frameworks |
| 12h | done 2026-11-22 | antske-fokkens-phd.pdf | Chapter 8: Conclusion and future work (pp. 343-) | |
| 13 | done 2026-11-22 (rows below) | malouf1997gerunds.pdf, then Malouf-dissertation.pdf (by chapter) | Malouf on gerunds and mixed categories | Mixed categories and the type hierarchy |
| 13a | done 2026-11-22 | malouf1997gerunds.pdf | Malouf: Mixed categories in HPSG (verbal gerunds) | Mixed categories and the type hierarchy |
| 13b | done 2026-11-22 | Malouf-dissertation.pdf (text lines 354-1366) | Malouf 1998 dissertation, Chapter 1: Introduction (HPSG preliminaries, universals) | Mixed categories and the type hierarchy |
| 13c | done 2026-11-22 | Malouf-dissertation.pdf (lines 1367-4322) | Chapter 2: English verbal gerunds | |
| 13d | done 2026-11-22 | Malouf-dissertation.pdf (lines 4323-6598) | Chapter 3: Coherent nominalizations | |
| 13e | done 2026-11-22 | Malouf-dissertation.pdf (lines 6599-7775) | Chapter 4 | |
| 13f | done 2026-11-22 | Malouf-dissertation.pdf (lines 7776-8432) | Chapter 5 | |
| 14 | done 2026-11-22 | Haspelmath-Frameworkfree.pdf | Haspelmath: Framework-free grammatical theory | Theory log: what a framework-neutral core would need |
| 15 | done 2026-11-22 | Crysmann-2015-JoLM.pdf | Crysmann: Representing morphological tone in a computational grammar of Hausa | Morphology beyond segmental strings |
| 16 | done 2026-11-22 | FlickingerWasow.pdf | Flickinger and Wasow: A corpus-driven analysis of the do-be construction | ERG analysis practice |
| 17 | done 2026-11-22 (body skimmed) | Ginzburg1995_Article_ResolvingQuestionsI.pdf | Ginzburg: Resolving questions, I | Question semantics |
| 18 | done 2026-11-22 (4.3, 4.5, 4.6 skimmed) | PollardSag1994.pdf | Pollard and Sag 1994, Chapter 4 (unbounded dependencies, traces) | Traces versus traceless; theory log 0001 |
| 19 | done 2026-11-22 (5.3, 5.4 skimmed) | PollardSag1994.pdf | Pollard and Sag 1994, Chapter 5 (relative clauses, empty relativizer) | Empty elements |
| 20 | done 2026-11-22 (1.1-1.4, 1.6-1.9 skimmed) | PollardSag1994.pdf | Pollard and Sag 1994, Chapter 1 (introduction; includes flat structures, pp. 36-40) | Foundations; flat versus binary branching |
| 21 | done 2026-11-22 (Ch2, 3, 6, 7, 8; parts skimmed) | PollardSag1994.pdf | Pollard and Sag 1994, remaining chapters, one per entry (2, 3, 6, 7, 8; add rows when reached) | Foundations |
| 22 | done 2026-11-22 (two sittings) | Sign_based_construction_grammar.pdf | Sag 2012: Sign-Based Construction Grammar, an informal synopsis (142 pages; two sittings) | Constructs, locality; what a construction-based core would look like |
| 23 | done 2026-11-22 | Sag-Wasow-Processing.pdf | Sag and Wasow: Performance-compatible competence grammar | Incremental, surface-oriented processing claims that bear on tagging |
| 24 | done 2026-11-22 | ChavesRichter2021.pdf | Chaves and Richter 2021 (Society for Computation in Linguistics) | Check topic on reading; relevance to neural models and islands |
| 25 | done 2026-11-22 (read early, with item 14) | haspelmath-comp-concepts.pdf | Haspelmath: Comparative concepts and descriptive categories | Theory log: status of cross-linguistic categories in a shared core |
| 26 | done 2026-11-22 | crysmann-hausa-resumptive-islands.pdf | Crysmann: Resumption and islandhood in Hausa | Extraction beyond English; resumptives under replay |
| - | hold | CrysmannRelational.pdf | Whole MWE 2011 proceedings; waiting for Olga to say which paper | |
| - | hold | HPSG.zip | HPSG conference proceedings 2000-2019; consult on demand | |
