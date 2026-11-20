# Li, Zhou, Zhao and Parnow (2022): HPSG-inspired joint neural constituent and dependency parsing in O(n³) time complexity

*IEEE/ACM Transactions on Audio, Speech, and Language Processing* 30: 355–365. Read from the text layer; the result tables (I–IV) and Figures 1–5 are images and were not legible in the text, so no scores are reported here. Read 2026-11-20.

Question for this reading: this is the closest prior neural work. What does it take from HPSG, what does it leave out, and how does it join constituents and dependencies?

## Summary

The paper builds on Zhou and Zhao (2019), who combine a constituent tree and a dependency tree into one "simplified HPSG" structure: a constituent tree in which every span has a head word (Sections I–II, pp. 355–356). A shared self-attention encoder feeds a span scorer (for labeled constituents) and a biaffine scorer (for dependency arcs), trained jointly; decoding finds the best pair of trees at once (Section III, pp. 357–358). Joint decoding in the earlier system costs O(n⁵), because for each split point the head words of the two sub-spans are searched over (p. 358). The contribution is a head scorer: each token gets a score saying how high in the tree it is a head, so the head of a span is read off as the token with the best score, and decoding drops to O(n³) (Section III.E–F, pp. 358–360). The paper also gives an algorithm that turns a dependency tree into a labeled pseudo-constituent tree, so that the joint parser can be trained from Universal Dependencies treebanks alone (Section III.G, p. 360; Section V.B, p. 364).

## What it takes from HPSG

Only the Head Feature Principle: a phrase is a projection of its head daughter, so each constituent has one head word, and that word is the dependent of something outside the span and the governor of the other words inside it (p. 355; p. 358, fn. 1). The authors are explicit about the distance from HPSG: the structure bears "a much closer family resemblance to the head-lexicalized structures" of Collins (2003) (pp. 355–356); there is "no explicit notion of 'type' in this work"; and "the notion of feature structure unification was only weakly utilized ..., e.g. for checking HFP constraint" (p. 360).

## What it leaves out

Everything else that makes an analysis HPSG: lexical types, valence, rule schemata, the type hierarchy, lexical rules, non-local features, and semantics. Labels are Penn Treebank constituent categories and dependency relation names. There is no grammar that licenses or rejects the output, so there is no notion of a strict analysis. The paper does not claim otherwise.

## Caveats for the parser

### 1. "HPSG parsing" in the neural literature can mean this (high for positioning, not for design)

A reader searching for neural HPSG parsing finds this line of work first. What we plan differs in kind: output in a grammar's own rule and type vocabulary, checked by the grammar. The difference has to be stated early in anything we write.

### 2. The dependency-to-constituent conversion is much weaker than the bridge we need (high; UD bridge)

Algorithm 2 (p. 360) makes one phrase out of a head and all of its dependents, and labels the phrase with the dependency relation between its head word and that word's governor. It deliberately uses no relation-specific rules, so that it applies to any annotation scheme (p. 360). The result is flat (binarized only inside the chart with an empty label, p. 357), has no argument or adjunct distinction, no order of saturation, and no functional heads. Non-projective arcs are handled by moving the offending child up to an ancestor until the leaves are back in surface order (p. 360, Fig. 4). This shows that a rule-free conversion from UD is possible and useful for training a parser, and also how little HPSG content such a conversion carries.

### 3. Predicted head scores can be inconsistent (medium; tree encoding)

The head scores must satisfy three properties for decoding to be deterministic (highest in span; same across the spans a word heads; monotone under span inclusion). Gold targets satisfy them; predictions "maybe not follow these properties strictly", which "may cause some errors in the final parse tree" (p. 359). Any per-token encoding of structure has the same exposure: the label sequence the tagger emits may not decode to a well-formed tree. The paper has no repair step.

### 4. Depth is capped (low; tree encoding)

Head level is predicted as a class with a maximum of 32; deeper spans are truncated (p. 361). Our ERG derivations reach depth 45 in the training data, so a level-based label would need a higher cap or a relative encoding.

## Support for the design

- **A per-token label can carry the tree's head structure.** The head scorer assigns each token the level of the highest span it heads, predicted by a feed-forward layer per token, and classification of the level worked better than regression on a score (p. 359). This is a sequence-labeling component inside a chart parser, and it is what removed the O(n²) factor.
- **Long sentences are in reach of neural parsers.** Decoding is timed on Wikipedia sentences in three length bands up to 200–300 words; the O(n³) decoder stays in the same order of magnitude as plain CKY and MST decoding, with stated speedups over the O(n⁵) decoder of 1.41 (up to 100 words), 17.7 (100–200), and 639 (200–300) (p. 362). The authors also note that with a pre-trained encoder the encoder dominates run time for short sentences (p. 361).
- **Constituents and dependencies help each other.** Joint training and decoding beat the separate baselines, and the error analysis shows a case where each structure corrects the other (pp. 361–362). This supports predicting derivation structure and dependencies from one encoder with several heads.
- **Training from UD alone is workable.** With converted pseudo-constituents the joint parser is reported as best on four of six languages in the UD comparison (p. 364; scores not legible).
- **Head rules matter.** Different head rules for converting constituents to dependencies change both constituent and dependency scores (p. 364). For us this is a reason to derive heads from the grammar and not from external head tables.

## Theory strains

None; the paper is not about the theory. Its one theoretical remark is that HPSG "can be treated as a synthesis of multiple grammar theories" (p. 355).

## Key primary sources

- Zhou and Zhao 2019, Head-driven phrase structure grammar parsing on Penn Treebank (ACL): the joint span structure and the O(n⁵) decoder.
- Sagae, Miyao and Tsujii 2007, HPSG parsing with shallow dependency constraints (ACL): cited as constraining the application of wide-coverage HPSG rules with dependency parses (p. 364). This is direct precedent for restricting a grammar-based parser with predicted structure and should be read.
- Mrini et al. 2020 (label attention on the same parser).
- Stern, Andreas and Klein 2017; Kitaev and Klein 2018 (span-based chart parsing); Dozat and Manning 2017 (biaffine scorer).
- Collins 2003 (head-lexicalized structures).
- Xia and Palmer 2001 and later work on converting dependency structures to phrase structures.

## Not covered here

These are my remarks, not statements from the paper.

- The head-level label is close in spirit to the encodings of Gómez-Rodríguez and Vilares (2018) and to hexatagging: each word says how far up it projects. The paper does not cite the sequence-labeling line. A design that keeps their per-token head level and drops the chart is, in effect, where our tagger starts.
- The paper evaluates accuracy against treebank trees only. It has nothing on whether the distribution of predicted labels matches the gold distribution, which is the property the lexical and construction frequency studies need.
- I could not read the tables, so I cannot say how large the accuracy cost of the O(n³) decoder is; the text calls it "a small performance loss" (p. 364).
