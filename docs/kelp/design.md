# Kelp: design draft

Kelp (Keyboard-driven, Efficient, LLM-assisted Parse selection) is Orca's treebanking tool: a successor to the Full Forest Treebanker (FFTB; Packard 2015) for DELPH-IN grammars.

Status: draft for review, 2026-11-22. Nothing here is built except the forest reader (`kelp/forest.py`) and the check in section 4.

## 1. Priorities

In order:

1. A fast, keyboard-driven interface. The annotator's time is the cost to minimize.
2. Proposals from Orca, from ACE's ranking model and from an LLM, so that the usual action is to confirm or correct an analysis. LLM latency does not matter: the annotator is reading the sentence meanwhile.
3. Semantic discriminants next to the syntactic ones.
4. Robust update after grammar changes.
5. Proper saving, in profiles that existing DELPH-IN tools read.
6. More than one correct tree per item, where the annotator wants that.

Out of scope for now: several annotators on one profile, adjudication.

## 2. Architecture

Three parts.

**Offline: ACE builds the forests.** Unchanged from FFTB practice: `mkprof`, then `art -f` with ACE, which stores every analysis of every item, packed, in the `edge` relation. Orca cannot do this step, because it has no exhaustive parser. Kelp only reads the profile, so it does not depend on the ACE version or on ACE's libraries.

**Server: Python, with Orca as the engine.** One process per annotator, started on a profile. It holds the grammar, the forests and the session state, and does four things:

- forest operations: counting, discriminants, applying decisions (section 3);
- rebuilding trees with Orca's replay, which checks them against the grammar and gives the MRS (section 4);
- proposals (section 6);
- reading and writing the profile (section 8).

**Browser: the interface.** A single page served by the server. No build step and no framework are needed for a page of this size; plain JavaScript with SVG for trees.

## 3. Forest operations

These follow Packard (2015, chapter 3) and FFTB's source, rewritten in Python.

- **Unary chains.** Every chain of unary rules over the same span is collapsed into one node. After that, a tree has at most one node per span, and a constraint on a span can be tested on single edges.
- **Counting.** The number of trees consistent with the decisions so far is computed bottom-up over the edges, and the number of remaining trees that use each edge top-down. Both are linear in the size of the forest.
- **Discriminants.** A property of an edge (its full chain, or one rule or lexical type in it) that holds in some remaining trees and not in all is a discriminant.
- **Constraints.** As in FFTB: this chain exactly; this rule or lexical type present; absent; and "this span is a constituent", which FFTB offers but cannot save.

New in Kelp:

- **Early validity check.** FFTB checks a subtree only when it has become unique. Kelp can replay candidate subtrees in the background and remove the ones the grammar rejects before the annotator sees them.
- **Enumeration below a threshold.** When few trees remain (some hundreds), Kelp unpacks them all, replays them, and from then on works with the exact set. This is what makes semantic discriminants possible (section 7).

## 4. Does Orca agree with ACE on forest trees?

FFTB rebuilds trees with ACE's own code. Kelp will use Orca's replay, so Orca must accept exactly the trees ACE accepts and give the same meaning. The check (`scripts/kelp_check_forest.py`) unpacks every tree of every forest, replays it with Orca, and compares with the readings ACE lists when it unpacks the same sentence exhaustively.

| | MRS test suite | CSLI test suite |
|---|---|---|
| Items checked | 107 | 1,187 |
| Distinct trees in the forests | 828 | 24,428 |
| Trees ACE lists | 668 | 23,534 |
| In both ACE's and Orca's sets | 668 | 23,528 |
| Accepted by Orca only | 0 | 0 |
| Listed by ACE only | 0 | 6 |
| Same root condition | 668 | 23,528 |
| Same MRS, without ICONS and variable properties | 668 | 23,528 |
| Same MRS, without ICONS | 667 | 23,368 |
| Same MRS, with ICONS | 667 | 23,368 |

Four CSLI items with more than 2,000 trees each were left out. Per-item results are in `analysis/kelp/`.

Orca accepts the same trees as ACE, so Kelp does not need ACE at annotation time. These points came out of the check and matter for the design:

- **Root conditions.** A root record in the forest only says that the packed edge met a root condition. The particular tree may meet a different one. Kelp must test the grammar's root conditions on the rebuilt tree, in the order in which they are defined in the grammar, which is the order ACE uses.
- **Idioms.** ACE drops readings that contain part of an idiom without the rest. Orca has no idiom rules yet. The check uses the grammar's non-idiom root condition instead, which also rejects a complete idiom: the trees that only ACE lists are all readings of "in order to". Orca needs the idiom rules before Kelp is used on real text.
- **Information structure.** ACE's MRS has ICONS. Orca extracts them as well, and including them in the comparison changes nothing: every difference that remains is in a variable property.
- **Variable properties.** The structure of the meaning is the same for every shared tree. For a small share of trees a property of some variable differs (tense, mood and the like); the cause is not yet known.

## 5. Interface

One screen per item, three areas.

- **Sentence**, on top, large. Words whose analysis is settled are marked.
- **Analysis**, in the middle: the proposed tree with short node labels (S, NP, VP), and next to it the meaning as a dependency view of the MRS (DMRS), from the start and not only at the end. Nodes where the proposers disagree, or where the model is unsure, are marked: these are where the annotator should look.
- **Choices**, on the side: for the node or span in focus, the alternatives, each with its rule name, the grammar's own documentation line and example, the number of trees it keeps, and its probability.

Everything is reachable from the keyboard:

- arrow keys move the focus over tree nodes; `Tab` jumps to the next doubtful node;
- number keys choose among the alternatives at the focus; `x` rejects one;
- `[` and `]` shrink and grow a span selection over the words;
- `Enter` accepts the item when one tree remains (or the marked set, see below); `r` rejects the item; `u` undoes the last decision, without limit; `n` and `p` move between items; `/` opens a comment.

The mouse still works for everything.

Other points:

- **Items without a correct analysis.** Rejection asks for a reason from a short list (no parse; no correct parse; ill-formed input; tokenization), stored in the comment field, since FFTB users maintain such lists by hand.
- **Several correct trees.** `Enter` on a set of remaining trees asks for confirmation and saves all of them as active. The profile format supports this (`t-active` is the number of active trees).
- **List view.** Per item: status, number of trees, number of decisions, whether the proposers agree. Sortable, so easy items can be confirmed in a run.

## 6. Proposals

For each item, before the annotator opens it, Kelp prepares:

1. **Orca's analysis** from the tagger, mapped onto the forest. If the tree is in the forest, it is a full proposal; if only parts are, those parts are proposed.
2. **ACE's best tree**, from the ranking model (one more ACE run per profile, offline).
3. **An LLM judgment** where 1 and 2 differ, and at the discriminants with the most weight. The LLM gets the sentence, its context (the neighboring items), and the alternatives described by their meaning and by the grammar's documentation of the rules involved. It answers with a choice and a one-line reason, shown to the annotator.

Every proposal is expressed as decisions on the forest and checked by the grammar, so a proposal can be wrong but never ill-formed. Proposed decisions are stored with their source and are kept apart from the annotator's own in the profile (section 8).

What to measure before trusting this: on gold profiles, how often each proposer's tree is the gold tree, and how many decisions the annotator would still have to make. The earlier experiment with an LLM judging the tagger's doubtful labels showed no gain, so the LLM step must earn its place in this measurement.

## 7. Semantic discriminants

Packard (2015, chapter 5) notes that semantic discriminants cannot be computed on a packed forest, because they are not local to one edge, and leaves them as future work. The LKB tool has them, over an enumerated list of at most 500 trees: each is one dependency of the meaning, such as "the chasing was done by the dog".

Kelp's plan:

- When the remaining trees are few enough to enumerate (section 3), compute the meaning of each, break it into dependencies, and offer as discriminants the dependencies that hold in some trees and not in all.
- Before that point, offer semantic discriminants for the proposed tree only: "this analysis says X; is that right?". A "no" removes every tree in which the same words are related that way, as far as that can be decided on single edges; the rest is left to the syntactic discriminants.
- Show them in plain words, generated from the predicate names and roles, with the grammar's notation available on demand.

This part needs an experiment of its own: how large the enumeration threshold can be while the interface stays responsive.

## 8. Saving and compatibility

Kelp writes the same relations as FFTB, so that [incr tsdb()], PyDelphin, FFTB and the grammar's release scripts read its profiles:

- `tree`: status of the item (`t-active`: 1 or more accepted, 0 rejected, -1 unannotated), author, start and end time, comment.
- `decision`: one row per decision, with the existing codes for kind and state (manual or inferred; FFTB's type 7 for full chains).
- `preference` and `result`: the chosen tree or trees, with derivation and MRS.

Differences from FFTB:

- **Every decision is saved when it is made**, to a journal file next to the profile, so that a crash or a closed tab loses nothing. The relations are written on accept or reject.
- **Writes are atomic**: to a temporary file, then renamed.
- **History is kept.** Each save adds a new `t-version` and leaves earlier ones in place, as the format intends. Annotation times are not overwritten by updates.
- **Sources of decisions.** The standard `decision` relation has no field for "proposed by Orca, confirmed by the annotator". This goes into the journal and into a Kelp-specific extra relation that other tools ignore.
- **The yield** of each decision's span is written to `d-value`, which FFTB leaves empty.

## 9. Update after a grammar change

FFTB applies the old decisions to the new forest and succeeds when exactly one tree remains and it equals the old gold tree. Decisions are matched by label and token position, so renamed rules and changed tokenization break them. Kelp adds:

- **Character positions.** Decisions are anchored to characters of the input, and mapped to the tokens of the new forest.
- **A rename table**, given by the grammar writer or guessed from the two grammar versions, applied to old decisions and old trees.
- **The old tree and the old meaning as evidence.** When the decisions leave several trees or none, Kelp ranks the new trees by similarity to the old tree and to the old MRS, and proposes the closest, marked for review, with the differences shown.
- **A report per item**, in the nine FFTB categories, plus what changed.

## 10. Order of work

1. Forest operations with tests against brute-force enumeration (unary chains, counting, discriminants, constraints).
2. Profile reading and writing, with a round trip test: load a gold profile, save, compare.
3. Server and a first interface: sentence, discriminants, tree, accept and reject. At this point Kelp does what FFTB does.
4. Meaning display and keyboard operation.
5. Proposals from ACE and Orca; measurement on gold profiles.
6. LLM judgments; measurement.
7. Semantic discriminants.
8. Update.

In Orca itself: idiom rules, node labels from `parse-nodes.tdl`.

## 11. Questions

1. Is the order in section 10 right, or should update (step 8) come earlier because of a pending grammar release?
2. Which grammar and corpus will be treebanked first with Kelp: the ERG, the Spanish grammar, another?
3. Rejection reasons (section 5): is a fixed short list acceptable, and which reasons?
4. Several correct trees: one mark for all cases, or separate marks for "truly ambiguous in context" and "the grammar draws a distinction I cannot judge"?
5. Where does the code live: `kelp/` inside the Orca repository (as now), or its own repository that depends on Orca?

## References

- Packard, Woodley. 2015. *Full forest treebanking*. MA thesis, University of Washington. https://digital.lib.washington.edu/researchworks/handle/1773/33194
