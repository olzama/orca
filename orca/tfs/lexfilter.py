"""The grammar's lexical filtering, applied to the generic lexical entries Orca proposes.

A chart parser builds every lexical edge of a token span and then applies the
grammar's lexical-filtering rules (status `lexical-filtering-rule`, the ERG's
lfr.tdl): a rule with an +INPUT and a +CONTEXT removes the input edge when an
edge matching the context is in the same chart cell (+POSITION "I1@C1"). The
ERG's main rule removes a generic (unknown-word) edge whenever a native entry
covers the same token, unless the token is a named entity.

Orca builds only the lexical edge the tagger proposes, so it never sees the
competing edges. This module rebuilds, for one proposed generic leaf, the
edges of the same token span that the rules can refer to, and evaluates the
rules by unification:

  input    the generic entry with the lexical rules above it, replayed over
           its tokens;
  context  native edges of the same span: entries spelled like the words,
           bare or through one spelling rule (as lexical lookup finds them),
           replayed over the same tokens; and the other generic entries,
           bare, for rules whose context is itself generic (generic names).

A rule fires when its +INPUT first element unifies with the input edge and
(for a rule with a context) its +CONTEXT first element unifies with one of
the context edges, in the same structure (so reentrancies between the two are
respected). Rules without a context are evaluated on the input alone.
Rules whose values the replay engine cannot match (regular-expression
strings, as in the ERG's punctuation rules) simply never fire: the filter
errs on the side of keeping an entry.

Only single generic leaves are checked; native entries are never filtered
(the ERG's rules only remove unknown-word edges and generic names).
"""
import re
import warnings

from delphin import tdl

from ..encoding import Leaf, Node
from .grammar import ReplayFailure
from .dag import UnificationFailure


def _regexes(term, path, out):
    """(feature path, pattern) for every regular-expression value in a rule's TDL definition."""
    if isinstance(term, tdl.Regex):
        with warnings.catch_warnings():     # the ERG's patterns start with '[[' (a literal bracket): harmless FutureWarning
            warnings.simplefilter('ignore', FutureWarning)
            out.append((tuple(path), re.compile(str(term))))
    elif isinstance(term, (tdl.Conjunction, tdl.TypeDefinition)):
        for t in (term.conjunction.terms if isinstance(term, tdl.TypeDefinition) else term.terms):
            _regexes(t, path, out)
    elif isinstance(term, tdl.ConsList):
        for i, v in enumerate(term.values()):
            _regexes(v, list(path) + ['REST'] * i + ['FIRST'], out)
    elif isinstance(term, tdl.AVM):
        for f, v in term.features():
            _regexes(v, list(path) + f.upper().split('.'), out)
    return out


class LexicalFilter:
    def __init__(self, fg, lexicon):
        self.fg, self.lx = fg, lexicon
        g = fg.g
        self.rules = [n for n, s in g.status.items() if s == 'lexical-filtering-rule']
        # regular-expression values (the ERG's punctuation and italics rules): the replay engine does not match
        # them, so they are checked here, on the string at that path, as a whole-string match (as ACE does)
        self.regex = {n: _regexes(g.instances[n], [], []) for n in self.rules}
        self.generic = {e for es in lexicon.generic.values() for e in es}
        self.n_filtered = 0
        self.memo = {}

    def is_generic(self, entry):
        return entry in self.generic

    # -- edges of a span ------------------------------------------------------

    def _native_trees(self, forms):
        words = [f.lower().replace('\\', '') for f in forms]
        by_orth = self.lx._by_orth()
        trees = [Leaf('entry:' + e, tuple(forms)) for e in by_orth.get(' '.join(words), ())]
        for rule in self.lx.undo:
            for i, w in enumerate(words):
                for stem in self.lx.stems(w, rule):
                    sp = words[:i] + [stem] + words[i + 1:]
                    for e in by_orth.get(' '.join(sp), ()):
                        trees.append(Node(rule, (Leaf('entry:' + e, tuple(forms)),)))
        return trees

    def _generic_trees(self, forms, exclude):
        return [Leaf('entry:' + e, tuple(forms)) for e in sorted(self.generic) if e != exclude]

    # -- the check --------------------------------------------------------------

    def status(self, entry, rules, forms, toks):
        """'filtered' if the grammar's lexical filtering removes this generic entry (with the lexical rules
        above it, given top-down) over these tokens; 'no edge' if the entry does not unify with the tokens
        at all (a chart parser never builds it); otherwise 'kept'. Native entries are always 'kept'."""
        if entry not in self.generic:
            return 'kept'
        key = (entry, tuple(rules), tuple(forms), tuple(toks))
        hit = self.memo.get(key)
        if hit is not None:
            return hit
        out = self._check(entry, rules, forms, toks)
        self.memo[key] = out
        if out == 'filtered':
            self.n_filtered += 1
        if len(self.memo) > 200000:            # the answer depends only on the key, so it is kept across sentences
            self.memo.clear()
        return out

    def filtered(self, entry, rules, forms, toks):
        return self.status(entry, rules, forms, toks) == 'filtered'

    def keeps(self, entry, rules, forms, toks):
        return self.status(entry, rules, forms, toks) == 'kept'

    def _check(self, entry, rules, forms, toks):
        fg = self.fg
        for t in toks:                         # token masters are built outside any undo mark, or undo would unbuild them
            for x in (t if isinstance(t, tuple) else (t,)):
                if x not in fg._tokens:
                    fg._tokens[x] = fg._build_token(x)
        tree = Leaf('entry:' + entry, tuple(forms))
        for r in reversed(rules):              # rules are given top-down
            tree = Node(r, (tree,))
        m0 = fg.u.mark()
        try:
            try:
                inp, _ = fg.replay_tree(tree, list(toks))
            except ReplayFailure:
                try:                            # the bare entry, if its rules do not apply here
                    inp, _ = fg.replay_tree(Leaf('entry:' + entry, tuple(forms)), list(toks))
                except ReplayFailure:
                    return 'no edge'
            if not self.rules:
                return 'kept'
            native = generic = None
            for name in self.rules:
                m1 = fg.u.mark()
                try:
                    R = fg.instance(name)
                    try:
                        fg.unify(fg.get(R, '+INPUT', 'FIRST'), inp)
                    except (UnificationFailure, KeyError):
                        continue
                    if not self._regex_ok(name, '+INPUT', inp):
                        continue
                    try:
                        ctx_first = fg.get(R, '+CONTEXT', 'FIRST')
                    except (UnificationFailure, KeyError):
                        ctx_first = None
                    if ctx_first is None:
                        return 'filtered'          # a rule on the input alone
                    if native is None:
                        native = self._native_trees(forms)
                    cands = native
                    onset = self._onset(ctx_first)
                    if onset == 'unk_onset':       # the context is a generic edge itself (generic names)
                        if generic is None:
                            generic = self._generic_trees(forms, entry)
                        cands = generic
                    for t in cands:
                        m2 = fg.u.mark()
                        try:
                            sign, _ = fg.replay_tree(t, list(toks))
                            fg.unify(fg.get(R, '+CONTEXT', 'FIRST'), sign)
                            if self._regex_ok(name, '+CONTEXT', sign):
                                return 'filtered'
                        except (ReplayFailure, UnificationFailure, KeyError):
                            pass
                        finally:
                            fg.u.undo(m2)
                finally:
                    fg.u.undo(m1)
            return 'kept'
        finally:
            fg.u.undo(m0)

    def _regex_ok(self, name, which, sign):
        """Whether the sign's strings match the rule's regular expressions under +INPUT or +CONTEXT."""
        for path, rx in self.regex.get(name, ()):
            if path[:2] != (which, 'FIRST'):
                continue
            try:
                value = self.fg.type(self.fg.get(sign, *path[2:]))
            except (UnificationFailure, KeyError):
                return False
            if not (value.startswith('"') and value.endswith('"') and rx.fullmatch(value[1:-1])):
                return False            # not a string, or no match: the rule does not apply
        return True

    def _onset(self, node):
        try:
            return self.fg.type(self.fg.get(node, 'SYNSEM', 'PHON', 'ONSET'))
        except (UnificationFailure, KeyError):
            return None
