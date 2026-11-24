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

How we tested it, with ERG 2025 (compiled with this branch's base, main at 31afda8) and 300 sentences drawn at random (fixed seed) from the Redwoods dev profiles:

1. **Two builds from the same commit.** `main` as is ("stock") and `main` with this patch ("patched"), same compiler and flags; both report the same version.
2. **Without the option, nothing changes.** Both builds parse the 300 sentences in one process each, first-best (`-1`) and 20-best (`-n 20`), with the same memory and time limits. We compare the console output item by item: the MRS and the derivation of every result, in rank order (timings excluded). Output is byte-identical.
3. **With the option, the same parses as restarting ACE.** For each sentence we take a restriction list as a real caller would build it: our supertagger's five best lexical types per word (probability at least 0.001) turned into lexical entries, and every other lexeme that could match the sentence's words disabled, about 60 lexemes per sentence on average. Then:
   - reference: stock `main` started once per sentence with `-L <that list>`;
   - patched: one process started with `--per-item-disable`, fed `#DISABLE <that list>` followed by the sentence, for all 300 sentences in turn.
   We compare item by item as in step 2, for `-1` and for `-n 20`.
4. **The restriction really changes between inputs.** In one process: "The dog barked." with `#DISABLE bark_v1`, then a bare `#DISABLE`, then `#DISABLE bark_v1` again. Without `bark_v1` ACE gives only fragment analyses without the verb's predicate; with it, the ordinary parse. Each of the three outputs equals a separate stock run with the corresponding `-L`.
5. **Timing.** Wall-clock time per sentence for step 3's two set-ups, on the same machine in the same session (it was running other jobs, so the absolute numbers are higher than on an idle machine).

| Check | Result |
|---|---|
| Step 2, `-1` and `-n 20` | byte-identical |
| Step 3, `-1` | 300 of 300 identical |
| Step 3, `-n 20` | 300 of 300 identical |
| Step 4 | passes |
| Step 5, time per sentence, one ACE run per sentence → one process | 178 → 138 ms (`-n 20`: 182 → 141 ms) |

The same change on the 0.9.34 release passed the same checks (and a full run over all 2,062 dev sentences with identical results), and is used by our parser and its public demo. The test script is available on request.

## License

Contributed under ACE's existing license.
