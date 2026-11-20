# 0011: Valence geometry, the notion of subject, and what is universal

Source: reader notes on the HPSG Handbook (2021), merged in `reading/handbook/SYNTHESIS.md`. Page numbers are Handbook pages. The proposal is ours and is not from the Handbook.

## Strain

The inventory of valence features has changed with almost every stage of the theory and still differs by author and by language: single SUBCAT, SUBJ plus COMPS, SPR in addition to or instead of SUBJ, a single VAL list, SBCG's VALENCE plus XARG. "Obviously, there are some important issues here" (Ch. 1, Section 4.1, p. 17, fn. 23); valence representation across languages remains "a matter of robust debate" (Ch. 2, Section 6, p. 61). As a result HPSG has no cross-linguistic formal correlate of "subject" (Ch. 30, Section 4, pp. 1404-1405): the same argument sits on different lists by language and by author, and only ARG-ST is uniform (Ch. 10, Section 4, pp. 380-383). ARG-ST itself may not be universal.

## Evidence

- English subjects on SPR (Sag, Wasow and Bender 2003; Müller) or SUBJ (Borsley 1987; Ginzburg and Sag 2000); German subjects of finite verbs on COMPS (Pollard 1996; Kiss 1995) (Ch. 10, pp. 380-383, fn. 6-7).
- SUBJ lists with more than one element for Danish (Müller and Ørsnes 2013; Ch. 5, fn. 9) and Korean (Ryu 2013; Ch. 7, pp. 264-265).
- Balinese, Toba Batak, Tagalog: the subject is not the first ARG-ST member; binding follows ARG-ST and control follows SUBJ or the Actor (Ch. 9, Section 3.3, pp. 323-325; Ch. 12, Section 2.4, pp. 510-513; Ch. 20, Section 5, pp. 918-922; Ch. 30, Section 11, pp. 1424-1426).
- Moro symmetrical objects need a partially ordered ARG-ST (Ch. 9, Section 3.4, pp. 325-326).
- Oneida: no syntactic valence; only a list of semantic indices for at most two animate arguments (Koenig and Michelson; Ch. 5, Section 2.2.2, pp. 186-188; Ch. 9, Section 7, pp. 354-355; Ch. 28, Section 5.3, p. 1306).
- The subject must stay visible on saturated phrases for tags, copy raising, and controlled overt subjects, which needs XARG and relaxes locality of selection (Ch. 12, Section 2.5, pp. 513-515).
- "Grammars should be motivated on a language-specific basis" (Ch. 1, pp. 7-8; Ch. 28, p. 1262).

## Competing analyses

- SUBJ, COMPS, and ARG-ST as candidates for near-universality (Ball; Ch. 5, Section 5, p. 202).
- A single VAL list with a binary Head-Valent Schema (Ball 2008; Keenan 2000; Ch. 5, Section 4.3).
- LFG's universal SUBJ function; some HPSG work imports function features (qVAL, Kropp Dakubu et al. 2007; ERG feature, Pollard 1994) (Ch. 30, p. 1405).
- Word Grammar's open taxonomy of labeled functions (Ch. 31, Section 5.3, pp. 1480-1484).
- Bottom-up shared cores: Grammar Matrix and CoreGram, both revisable (Ch. 25, pp. 1115-1121).

## Consequence for our parser and grammars

The UD bridge cannot use a language-independent rule from list position to nsubj or obj, and the "coarse universal schemas" of the relaxed output have no standing in the theory. Head-subject and head-complement schemas would have nothing to apply to in a language like Oneida.

## Proposal and test

Proposal: give every grammar an explicit, declarative function map from (valence list, position, case, voice type) to a UD relation, stored with the grammar and inspectable, in the spirit of the function features cited in Ch. 30. The relaxed schemas are defined over this function layer, not over valence lists.

Test: for English, German, and one voice-system language with a UD treebank, measure labeled attachment of core arguments produced through the function map against gold UD. Prediction: a map with at most a few dozen rows per language reaches the accuracy of hand-written per-rule conversion; if the German map needs case information from the feature structure (Ch. 30, p. 1404), record it as confirmation that tree shape is insufficient.

## Status

open.

## Update 2026-11-20

Pollard and Sag 1994, Chapter 9, already treats "subject" as language-dependent: Welsh finite clauses are subjectless, with the apparent subject as least oblique complement (pp. 351-358); the same is suggested for German polar questions, Japanese and Korean (pp. 357-358); possessors are specifiers in English and German and subjects in Welsh, Yup'ik and Hungarian (pp. 374-375). Notes: `reading/notes/pollard-sag-1994-ch9-reflections-and-revisions.md`.
