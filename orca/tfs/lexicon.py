"""Finding lexical entries for tagged words.

The tagger gives a word its lexical type and lexical rules. The entry itself
is looked up in the grammar's lexicon: an entry of that type whose spelling,
after undoing the spelling changes of the inflectional rules, is the word.
"""
import collections
import os
import re
from typing import Dict, List

from delphin import tdl


def _orth(definition) -> List[str]:
    for term in definition.conjunction.terms:
        if isinstance(term, tdl.AVM):
            for path, value in term.features():
                if path.upper() == 'ORTH':
                    terms = value.terms if isinstance(value, tdl.Conjunction) else [value]
                    for t in terms:
                        if isinstance(t, tdl.ConsList):
                            return [str(v).strip('"').lower() for v in t.values()]
    return []


class Lexicon:
    def __init__(self, grammar, grammar_dir):
        self.by_type_orth: Dict[tuple, List[str]] = collections.defaultdict(list)
        self.generic: Dict[str, List[str]] = collections.defaultdict(list)
        self.type_of: Dict[str, str] = {}
        for name, d in grammar.instances.items():
            status = grammar.status.get(name)
            if status not in ('lex-entry', 'generic-lex-entry'):
                continue
            supers = [str(t).lower() for t in d.supertypes if type(t) is tdl.TypeIdentifier]
            if not supers:
                continue
            self.type_of[name] = supers[0]
            if status == 'generic-lex-entry':
                self.generic[supers[0]].append(name)
            else:
                self.by_type_orth[(supers[0], ' '.join(_orth(d)))].append(name)
        self.undo: Dict[str, list] = {}          # rule -> [(regex on the word, stem ending)]
        letter_sets = {}
        for name in ('inflr.tdl', 'lexrinst.tdl', 'lexrinst-tok.tdl'):
            path = os.path.join(grammar_dir, name)
            if not os.path.exists(path):
                continue
            for event, obj, _ in tdl.iterparse(path, encoding='utf-8'):
                if event == 'LetterSet':
                    letter_sets[obj.var] = obj.characters
                elif event == 'LexicalRuleDefinition' and obj.patterns:
                    self.undo[obj.identifier.lower()] = [
                        self._invert(m, r, letter_sets, obj.affix_type == 'prefix')
                        for m, r in obj.patterns]
        self.irregular: Dict[tuple, List[str]] = collections.defaultdict(list)
        irregs = os.path.join(grammar_dir, 'irregs.tab')
        if os.path.exists(irregs):
            with open(irregs, encoding='utf-8') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) == 3 and not line.startswith(';'):
                        self.irregular[(parts[0].lower(), parts[1].lower())].append(parts[2].lower())

    @staticmethod
    def _invert(match, repl, letter_sets, prefix=False):
        """A spelling pattern (stem ending -> word ending) read backwards."""
        def elements(s):
            out, i = [], 0
            while i < len(s):
                if s[i] == '!' and i + 1 < len(s):
                    out.append(('var', s[i:i + 2]))
                    i += 2
                elif s[i] == '\\' and i + 1 < len(s):
                    out.append(('lit', s[i + 1]))
                    i += 2
                elif s[i] == '*':
                    i += 1
                else:
                    out.append(('lit', s[i]))
                    i += 1
            return out

        groups, regex = {}, ''
        for kind, x in elements(repl):
            if kind == 'lit':
                regex += re.escape(x)
            elif x in groups:
                regex += f'\\{groups[x]}'
            else:
                groups[x] = len(groups) + 1
                regex += '([' + re.escape(letter_sets.get(x, '')) + '])'
        stem = [(kind, groups.get(x) if kind == 'var' else x) for kind, x in elements(match)]
        return re.compile('^' + regex if prefix else regex + '$'), stem, prefix

    def stems(self, word, rule) -> set:
        """Spellings from which the rule could have produced the word."""
        out = set(self.irregular.get((word, rule), ()))
        for regex, stem, prefix in self.undo.get(rule, ()):
            m = regex.search(word)
            if m and all(kind == 'lit' or g is not None for kind, g in stem):
                part = ''.join(x if kind == 'lit' else m.group(x) for kind, x in stem)
                out.add(part + word[m.end():] if prefix else word[:m.start()] + part)
        return out

    def lookup(self, forms, lextype, lexrules) -> List[str]:
        """Entries of the type that can surface as these words under these
        lexical rules (given top-down, as in the tagger's label)."""
        words = [f.lower().replace('\\', '') for f in forms]
        spellings = {tuple(words)}
        for rule in lexrules:
            if rule in self.undo:
                new = set()
                for sp in spellings:
                    for i, w in enumerate(sp):
                        for stem in self.stems(w, rule):
                            new.add(sp[:i] + (stem,) + sp[i + 1:])
                spellings = new
        found = []
        for sp in spellings:
            found += self.by_type_orth.get((lextype, ' '.join(sp)), [])
        return found or list(self.generic.get(lextype, ()))


def resolve(tree, lexicon, pick=None):
    """Replace lexical types at the leaves by lexical entries.

    Returns the new tree and, per leaf, the list of candidate entries.
    `pick` maps a leaf index to the candidate to use (default: the first).
    A leaf with no candidate keeps its lexical type."""
    from ..encoding import Leaf, Node
    pick = pick or {}
    candidates = []

    def walk(t, rules):
        if isinstance(t, Leaf):
            if t.entry.startswith('entry:') or t.entry.startswith('<'):
                candidates.append([])
                return t
            found = lexicon.lookup(t.forms, t.entry.lower(), rules)
            i = len(candidates)
            candidates.append(found)
            if not found:
                return t
            return Leaf('entry:' + found[min(pick.get(i, 0), len(found) - 1)], t.forms)
        unary_lex = len(t.children) == 1 and t.label.lower().endswith('lr')
        below = rules + (t.label.lower(),) if unary_lex else ()
        return Node(t.label, tuple(walk(c, below) for c in t.children))

    return walk(tree, ()), candidates


def _leaf_range(tree, where):
    """Indices of the leaves under the node that a replay failure names."""
    from ..encoding import Leaf

    def n_leaves(t):
        return 1 if isinstance(t, Leaf) else sum(n_leaves(c) for c in t.children)

    node, start = tree, 0
    for i in (int(x) for x in where.split()[0].split('.')[1:]):
        if isinstance(node, Leaf) or i >= len(node.children):
            break
        for c in node.children[:i]:
            start += n_leaves(c)
        node = node.children[i]
    return range(start, start + n_leaves(node))


def replay_with_entries(grammar, lexicon, tree, tokens, cache=None, max_tries=12):
    """Replay a tree whose leaves name lexical types, using lexical entries.

    Where several entries fit a word, those that do not unify with the
    word's own token are dropped first. If replay then fails at a node above
    such a word, its other entries are tried (for example the entries of a
    verb that differ in the preposition they select). Returns the feature
    structure and the tree with the entries that were used."""
    from ..encoding import Leaf
    from .grammar import ReplayFailure
    _, candidates = resolve(tree, lexicon)
    leaves = []

    def collect(t):
        if isinstance(t, Leaf):
            leaves.append(t)
        else:
            for c in t.children:
                collect(c)

    collect(tree)
    pos, usable = 0, []
    for leaf, cands in zip(leaves, candidates):
        toks = tokens[pos:pos + len(leaf.forms)]
        pos += len(leaf.forms)
        if len(cands) > 1:
            keep = []
            for c in cands:
                mark = grammar.u.mark()
                try:
                    grammar.replay_tree(Leaf('entry:' + c, leaf.forms), toks)
                    keep.append(c)
                except ReplayFailure:
                    pass
                del grammar.u.trail[mark:]
            cands = keep or cands
        usable.append(cands)

    def build(pick):
        it = iter(range(len(leaves)))

        def walk(t):
            if isinstance(t, Leaf):
                i = next(it)
                if usable[i]:
                    return Leaf('entry:' + usable[i][pick.get(i, 0)], t.forms)
                return t
            return type(t)(t.label, tuple(walk(c) for c in t.children))

        return walk(tree)

    pick, tries, last = {}, 0, None
    queue = None
    while True:
        resolved = build(pick)
        try:
            fs, _ = grammar.replay_tree(resolved, tokens, cache=cache)
            return fs, resolved
        except ReplayFailure as e:
            last = last or e
            if queue is None:           # alternatives to try, nearest the failure first
                span = _leaf_range(resolved, e.where)
                queue = [(i, r) for i in span for r in range(1, len(usable[i]))]
            tries += 1
            if not queue or tries >= max_tries:
                raise last from None
            i, r = queue.pop(0)
            pick = {i: r}
