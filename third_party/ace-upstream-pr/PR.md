Draft, not submitted. Pull request to https://github.com/delph-in/ace from a fork under olzama, branch per-item-disable (one commit on top of main 31afda8; the patch file 0001-Add-per-item-disable-change-the-disabled-lexemes-L-b.patch in this folder). Open only with Olga's approval.

# Add --per-item-disable: change the disabled lexemes (-L) between inputs

## What it does

A new, opt-in command-line option for parsing mode. With `--per-item-disable`:

- an input line `#DISABLE <lexemes>` sets the lexemes disabled for the inputs that follow it, in the same format and with the same substring matching as `-L`;
- a bare `#DISABLE` line restores the `-L` value given on the command line;
- such lines are not parsed and produce no output.

Without the option nothing changes. The change is confined to `main.c` (the option, and one branch in the input loop next to the LUI `:` commands) plus one line in `doc/options.wiki`.

## Why

`-L` can only be set once, when ACE starts. A caller that wants a different restriction for every sentence (for example, parsing with only the lexical entries a supertagger proposes for that sentence) has to start ACE once per sentence. Starting ACE and touching the mapped grammar image costs about 30 to 35 ms per sentence with the ERG on our machine, more than the parsing itself for most short sentences. With this option one ACE process serves all sentences.

## Usage

```
$ ace -g erg.dat -1 --per-item-disable
#DISABLE bark_v1
The dog barked.          <- parsed without bark_v1
#DISABLE
The dog barked.          <- parsed with the command-line -L (here: none)
```

## Testing

All on ERG 2025 compiled with this branch's main, 300 random Redwoods dev sentences:

| Check | Result |
|---|---|
| Without the option: output of patched and unpatched main, `-1` and `-n 20` (MRS and derivation of every result, in order) | byte-identical |
| With the option: one patched process with a `#DISABLE` line before each sentence, against unpatched main run once per sentence with the same `-L`, `-1` | 300 of 300 identical |
| Same, `-n 20` | 300 of 300 identical |
| The restriction really changes between inputs ("The dog barked." with `bark_v1` disabled, enabled, disabled again; each equal to a separate `-L` run) | passes |

Time per sentence in the second and third checks (restrictions of 60 lexemes on average, single process, machine otherwise loaded): 178 ms with one ACE run per sentence, 138 ms with one process and `#DISABLE` lines (`-n 20`: 182 and 141 ms).

The same change on the 0.9.34 release passed the same checks and is used by our parser and its public demo.

## License

Contributed under ACE's existing license.
