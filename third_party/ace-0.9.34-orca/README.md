# ACE 0.9.34 with the Orca per-item restriction patch

ACE is Woodley Packard's parser for DELPH-IN grammars (MIT license, `LICENSE-ACE`;
http://sweaglesw.org/linguistics/ace/). Orca's chart mode runs ACE restricted to the
tagger's lexical entries: every other lexeme that could match a word is disabled with
ACE's `-L` option. `-L` is fixed when ACE starts, so stock ACE has to be started once per
sentence, and start-up (mostly paging in the grammar image) costs about 35 ms of a typical
49 ms chart step (`analysis/ace-startup/summary.json`).

`per-item-disable.patch` (main.c only) adds an opt-in flag, `--per-item-disable`. With it,
an input line

    #DISABLE name1 name2 ...

sets the `-L` string (lexemes to disable, matched by substring exactly as `-L`) for the
following items, and `#DISABLE` alone restores the command-line `-L` value. Directive lines
are not parsed and print nothing. Without the flag, ACE behaves exactly as before (checked:
byte-identical output). Lexical lookup reads the restriction afresh for every token and
ACE keeps no lexical cache between items, so one running process gives the same parses as
one process per sentence (checked on 300 dev sentences, first parse and 20-best).

Build: `tools/build_ace_orca.sh` (downloads and checks ACE 0.9.34, REPP 0.2.2 and Boost
1.71.0; builds Boost.Regex and REPP statically; installs `third_party/ace-orca/ace`;
compares with an official ACE binary). Needs gcc, g++, make, curl, bzip2. Build products
and downloads are not in git.

Orca uses it automatically when `third_party/ace-orca/ace` exists (or `ORCA_ACE_PATCHED`
names another path): `scripts/supertag_ace.py` keeps one patched ACE process per option
set and sends each sentence's restriction as a `#DISABLE` line. `ORCA_ACE_PERSISTENT=0`
returns to one stock ACE run per sentence.
