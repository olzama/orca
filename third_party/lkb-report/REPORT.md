Draft, not sent. A report for the LKB-FOS maintainers (where to send it: see the end).

# `do-parse-tty` called twice in a row crashes LKB-FOS in batch use

## Summary

In a non-interactive LKB-FOS session, two consecutive calls to `lkb::do-parse-tty` can crash the
process. The parse summary is built in a separate thread (`show-parse-summary-really`, started
through `acl-compat.mp:process-preset`), and `do-parse-tty` returns before that thread finishes.
The next call starts parsing while the summary thread is still rebuilding full feature
structures, and the two threads interfere: the summary thread fails with a unification error,
and with `--non-interactive` the process quits. If the error is caught instead, later parses in
the same process fail with a variety of internal errors, so the state stays corrupted.

## Environment

- LKB-FOS 5.6, `lkb.linux_x86_64`, banner "Welcome to LKB 5.6 (built with SBCL, 07:15:03 20 Jun 2023)"
- English Resource Grammar 2025 (git tag `2025`, commit f017ef8), loaded with its `lkb/script`
- Ubuntu 24.04, x86-64

## Repro

`repro.lisp` (replace `ERG_DIR` with the path of the ERG checkout):

```lisp
(lkb::read-script-file-aux "ERG_DIR/lkb/script")
(dolist (s '("Where can i find your palmtops?" "Where can i find your palmtops?"))
  (format t "~%=== PARSING: ~a~%" s)
  (lkb::do-parse-tty s)
  (format t "~%=== RESULT: ~a parses~%" (length lkb::*parse-record*)))
```

```
lkb.linux_x86_64 --non-interactive --load repro.lisp
```

Output (full log in `repro-output.txt`):

```
=== PARSING: Where can i find your palmtops?
=== RESULT: 4 parses
=== PARSING: Where can i find your palmtops?
Unhandled SIMPLE-ERROR in thread #<SB-THREAD:THREAD "Anonymous" RUNNING {1006D11373}>: Unification failure (CYCLE (SYNSEM LOCAL))
...
3: (ERROR "~A~%Attempt to reunify ~A into rule ~A at < ~{~A ~^: ~}> failed when constructing full FS" "Unification failure (CYCLE (SYNSEM LOCAL))" #D[v_np_le ...] V_N3S-BSE_ILR (ARGS FIRST))
4: (REAPPLY-RULE #[rule V_N3S-BSE_ILR ] (#:EDGE137) NIL NIL)
5: ((LABELS REBUILD-FULL-FS-1 :IN REBUILD-FULL-FS) #:EDGE316)
...
10: (MAKE-NEW-PARSE-TREE #[Edge # 323: `flr-hd_wh-mc_c' <312 322> (0 c 31) ] 1 NIL)
11: (SHOW-PARSE-SUMMARY-REALLY (#[Edge # 323: ...] ...))
12: ((LAMBDA (&REST ACL-COMPAT.MP::ARGS) :IN ACL-COMPAT.MP:PROCESS-PRESET) ...)
...
unhandled condition in --disable-debugger mode, quitting
```

The same sentence parses without error when it is the first one in the session.

## Evidence that it is a race

- With `(sleep 5)` after each `do-parse-tty` call, the sentence parses three times in a row without error (4 parses each time).
- With `(setf lkb::*show-parse-p* nil)` and no pause, likewise: three times in a row, no error.
- Over a run of the 2,062 Redwoods dev sentences, one sentence after another with the default `*show-parse-p*`, roughly half of the sentences ended in an error once the first one occurred. The errors varied: `Inconsistency - incorrect arguments NULL-WITH-DIFF-LIST and #D[list-with-diff-list ...] to GREATEST-COMMON-SUBTYPE`, `The value STRING is not of type STRING when binding STRING`, `Inconsistency - missing quickcheck representation for type *TOP*`, `hypothesize-edge() failed to build even the 0th tree from a root`. Each of the sentences we rechecked parses without error on its own in a fresh process. With `*show-parse-p*` set to nil, the first 277 sentences of the same run produced no errors.

## Workaround

`(setf lkb::*show-parse-p* nil)` before batch parsing with `do-parse-tty`.

## Suggestion

Either have `do-parse-tty` wait for the summary thread before returning, or skip the summary
display when there is no display to show it on (`--non-interactive`, or no X display).

## Not checked

- Whether a later LKB-FOS release than the 20 June 2023 build already behaves differently.
- Whether this is the intended way to batch-parse; `do-parse-tty` was used because it applies the grammar's REPP preprocessing to raw text. If the [incr tsdb()] route is the recommended one for batch work, the report reduces to a note that `do-parse-tty` is not safe to call repeatedly from a script.

## Where to send

LKB-FOS is maintained by John Carroll. The DELPH-IN Discourse forum has been the usual place for LKB questions (address to verify); a GitHub issue tracker for LKB-FOS, if there is one, was not checked. To confirm with Olga before sending.
