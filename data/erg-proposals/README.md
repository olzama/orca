Proposed ERG changes from the gap diagnosis (analysis/diagnosis/gaps1), tested on a copy of the ERG
(scripts/test_erg_proposals.py; build in /mnt/kesha/grammars/erg-proposals-build). The ERG is not modified.

Checks (analysis/diagnosis/gaps1/proposals-check.json, proposals-test.json):
- scripts/check_gap_proposals.py: each proposed entry against the ERG lexicon. 5 of 36 proposals already
  exist (knock_out_v1, line_up_v1, hand_out_v1, pull_over_v2, portable_n1): those were tagging errors.
- test: motivating sentences, and 300 random dev sentences (ACE first-ranked MRS, original vs. copy).

Outcome per draft:
- keep (motivating sentence parses with it, no dev change against gold seen): gig_n2, vegan_a1, reveler_n1,
  advertize_v1, migrate_v2, consider_v9, unprepared_n1, bust_a1, top_of_line_a1; retype muslin_n1,
  ultrasound_n1, steel_n1 to n_-_mc_le.
- reject (breaks a dev sentence whose original first parse was gold): inch_abb_n1 ("in": "Canon 131313 in
  stock"), megapixel_n2 ("3.3 megapixels").
- not needed: inch_abb_n2 (”): the original grammar already parses those sentences.
- still fails: heads-up_n1 (tokenization of the hyphen, not the entry), loch_n1 (another cause).
- not drafted: gapping, noun ellipsis (constructions; need a grammarian), "4"/"whatta"/"lookin'"
  (nonstandard spelling: preprocessing), "might could" (dialect), "builder's tea".
New entries have no weights in the ranking model, so they can change which parse ranks first.
