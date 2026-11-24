Draft, not sent. To: Woodley Packard. From: Olga Zamaraeva. Send only after Olga has opened the pull request and filled in its link.

Subject: Small ACE patch: --per-item-disable (pull request on delph-in/ace)

Dear Woodley,

I have opened a small pull request on delph-in/ace: [PR link]

It adds an opt-in flag, --per-item-disable. With it, an input line "#DISABLE <lexemes>" changes the -L list for the sentences that follow, so a caller can restrict lexical lookup differently for each sentence without restarting ACE. We use ACE this way to parse with only the lexical entries a supertagger proposes; starting ACE and mapping the grammar image for every sentence cost about 35 ms per sentence, more than the parsing itself for short sentences.

Without the flag nothing changes: we checked that the output is byte-identical to unpatched main on 300 Redwoods sentences, and that the restricted parses match running ACE once per sentence with -L.

Thank you for ACE, and for looking at this whenever you have a moment.

Best regards,
Olga
