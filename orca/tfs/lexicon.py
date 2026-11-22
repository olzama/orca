"""Finding lexical entries for tagged words.

The tagger gives a word its lexical type and lexical rules. The entry itself
is looked up in the grammar's lexicon: an entry of that type whose spelling,
after undoing the spelling changes of the inflectional rules, is the word.
"""
import collections
import itertools
import os
import re
from typing import Dict, List

from delphin import tdl


def _unquote(s):
    """A spelling as written in TDL: drop enclosing quotes, undo backslash escapes (\\" is a quotation mark)."""
    if len(s) >= 2 and s[0] == s[-1] == '"':
        s = s[1:-1]
    return re.sub(r'\\(.)', r'\1', s)


def _orth(definition) -> List[str]:
    for term in definition.conjunction.terms:
        if isinstance(term, tdl.AVM):
            for path, value in term.features():
                if path.upper().split('.')[-1] in ('ORTH', 'STEM'):     # STEM: Matrix grammars such as HaG
                    terms = value.terms if isinstance(value, tdl.Conjunction) else [value]
                    for t in terms:
                        if isinstance(t, tdl.ConsList):
                            return [_unquote(str(v)).lower() for v in t.values()]
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
        # lexical rules by status, for grammars whose rule names don't end in 'lr' (HaG's _ir rules)
        self.lexrules = {n.lower() for n, s in grammar.status.items() if s == 'lex-rule'}
        self.undo: Dict[str, list] = {}          # rule -> [(regex on the word, stem ending)]
        letter_sets, wild_cards = {}, {}
        identity = {}
        affix_files = [n for n in ('inflr.tdl', 'lexrinst.tdl', 'lexrinst-tok.tdl') if os.path.exists(os.path.join(grammar_dir, n))]
        if not affix_files:                      # other grammars: any file that defines spelling changes
            for n in sorted(os.listdir(grammar_dir)):
                if n.endswith('.tdl'):
                    with open(os.path.join(grammar_dir, n), encoding='utf-8', errors='replace') as f:
                        if re.search(r'%(suffix|prefix)', f.read()):
                            affix_files.append(n)
        for name in affix_files:
            path = os.path.join(grammar_dir, name)
            for event, obj, _ in tdl.iterparse(path, encoding='utf-8'):
                if event == 'LetterSet':
                    letter_sets[obj.var] = obj.characters
                elif event == 'WildCard':
                    wild_cards[obj.var] = obj.characters
                elif event == 'LexicalRuleDefinition' and obj.patterns:
                    target = self.undo
                    if all(m == r and '!' not in m and '?' not in m for m, r in obj.patterns):
                        target = identity   # spells nothing: the ERG's irregular-only rules (xxirreg), SRG's tag rules (da0ms0)
                    target[obj.identifier.lower()] = [
                        self._invert(m, r, letter_sets, obj.affix_type == 'prefix', wild_cards)
                        for m, r in obj.patterns]
        # grammars whose spelling rules rewrite tags rather than words (the SRG with FreeLing input):
        # most patterns are identities on letter strings that never occur at the end of a lemma
        self.tag_rules = len(identity) > len(self.undo)
        if not self.tag_rules:
            self.undo.update(identity)      # the ERG: irregular forms (irregs.tab) are found through these rules
        self.irregular: Dict[tuple, List[str]] = collections.defaultdict(list)
        irregs = os.path.join(grammar_dir, 'irregs.tab')
        if os.path.exists(irregs):
            with open(irregs, encoding='utf-8') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) == 3 and not line.startswith(';'):
                        self.irregular[(parts[0].lower(), parts[1].lower())].append(parts[2].lower())

    @staticmethod
    def _invert(match, repl, letter_sets, prefix=False, wild_cards=None):
        """A spelling pattern (stem ending -> word ending) read backwards. A wild
        card (?v) matches any of its letters without binding them, so on the stem
        side it stands for each of its letters in turn."""
        wild_cards = wild_cards or {}
        def elements(s):
            out, i = [], 0
            while i < len(s):
                if s[i] == '!' and i + 1 < len(s):
                    out.append(('var', s[i:i + 2]))
                    i += 2
                elif s[i] == '?' and i + 1 < len(s) and s[i:i + 2] in wild_cards:
                    out.append(('wild', s[i:i + 2]))
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
            elif kind == 'wild':
                regex += '[' + re.escape(wild_cards[x]) + ']'
            elif x in groups:
                regex += f'\\{groups[x]}'
            else:
                groups[x] = len(groups) + 1
                regex += '([' + re.escape(letter_sets.get(x, '')) + '])'
        stem = [(kind, groups.get(x) if kind == 'var' else wild_cards[x] if kind == 'wild' else x) for kind, x in elements(match)]
        return re.compile('^' + regex if prefix else regex + '$'), stem, prefix

    def stems(self, word, rule) -> set:
        """Spellings from which the rule could have produced the word."""
        out = set(self.irregular.get((word, rule), ()))
        for regex, stem, prefix in self.undo.get(rule, ()):
            m = regex.search(word)
            if m and all(kind != 'var' or g is not None for kind, g in stem):
                options = [[x] if kind == 'lit' else list(x) if kind == 'wild' else [m.group(x)] for kind, x in stem]
                for part in itertools.product(*options):
                    part = ''.join(part)
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
                if new or not self.tag_rules:
                    spellings = new
                # else: SRG-style rules match the POS tag (%suffix (vmm03p vmm03p0)), not the word, which is
                # already the lemma: a pattern that cannot apply leaves the spelling as it is
        found = []
        for sp in spellings:
            found += self.by_type_orth.get((lextype, ' '.join(sp)), [])
        return found or list(self.generic.get(lextype, ()))


def is_lexrule(lexicon, label):
    name = label.lower()
    return name.endswith('lr') or name in getattr(lexicon, 'lexrules', ())


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
        unary_lex = len(t.children) == 1 and is_lexrule(lexicon, t.label)
        below = rules + (t.label.lower(),) if unary_lex else ()
        return Node(t.label, tuple(walk(c, below) for c in t.children))

    return walk(tree, ()), candidates


def _leaf_range(tree, where):
    """Indices of the leaves under the node that a replay failure names."""
    from ..encoding import Leaf

    from ..encoding import n_leaves

    node, start = tree, 0
    for i in (int(x) for x in where.split()[0].split('.')[1:]):
        if isinstance(node, Leaf) or i >= len(node.children):
            break
        for c in node.children[:i]:
            start += n_leaves(c)
        node = node.children[i]
    return range(start, start + n_leaves(node))


def _leaf_candidates(grammar, lexicon, tree, tokens, strict=True):
    """The leaves of a tree and, per leaf, the lexical entries that fit it (see replay_with_entries)."""
    from ..encoding import Leaf, Node
    from .grammar import ReplayFailure
    memo = getattr(grammar, 'leaf_memo', None)
    leaves = []                       # (leaf, lexical rules above it, first token)
    paths = []                        # each leaf's node path, as replay failures name nodes ('0.1.0')
    position = [0]

    def collect(t, rules, path):
        if isinstance(t, Leaf):
            leaves.append((t, rules, position[0]))
            paths.append(path)
            position[0] += len(t.forms)
        else:
            lex = len(t.children) == 1 and is_lexrule(lexicon, t.label)
            for i, c in enumerate(t.children):
                collect(c, rules + (t.label.lower(),) if lex else (), f'{path}.{i}')

    collect(tree, (), '0')
    usable = []
    for (leaf, rules, pos), leaf_path in zip(leaves, paths):
        key = (leaf, rules, pos)
        cands = memo.get(key) if memo is not None else None
        if cands is None:
            if leaf.entry.startswith('entry:') or leaf.entry.startswith('<'):
                cands = []
            else:
                cands = lexicon.lookup(leaf.forms, leaf.entry.lower(), rules)
            if len(cands) > 1:
                toks = tokens[pos:pos + len(leaf.forms)]
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
            if memo is not None:
                memo[key] = cands
        if not cands and strict and not leaf.entry.startswith('entry:'):
            # a word the lexicon does not license with this type: name the leaf, so that
            # repair reconsiders that word (with locate_missing), or the whole tree
            where = leaf_path if getattr(lexicon, 'locate_missing', False) else '0'
            raise ReplayFailure(f'{where} {leaf.entry}', f'missing lexical entry for "{" ".join(leaf.forms)}"')
        usable.append(cands)

    return leaves, usable


def replay_with_entries(grammar, lexicon, tree, tokens, cache=None, max_tries=12, strict=True):
    """Replay a tree whose leaves name lexical types, using lexical entries.

    Where several entries fit a word, those that do not unify with the
    word's own token are dropped first. If replay then fails at a node above
    such a word, its other entries are tried (for example the entries of a
    verb that differ in the preposition they select). Returns the feature
    structure and the tree with the entries that were used.

    If the grammar object has a `leaf_memo` dict (cleared per sentence), the
    candidate entries of each leaf are worked out once per sentence. With
    `strict`, a leaf for which the lexicon has no entry (and the type no
    generic entry) makes the derivation fail, as it would in the parser."""
    from ..encoding import Leaf, Node
    from .grammar import ReplayFailure
    leaves, usable = _leaf_candidates(grammar, lexicon, tree, tokens, strict)

    def build(pick):
        it = iter(range(len(leaves)))

        def walk(t):
            if isinstance(t, Leaf):
                i = next(it)
                if usable[i]:
                    return Leaf('entry:' + usable[i][pick.get(i, 0)], t.forms)
                return t
            return Node(t.label, tuple(walk(c) for c in t.children))

        return walk(tree)

    pick, tries, last, queue = {}, 0, None, None
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


def entry_variants(grammar, lexicon, tree, tokens, resolved, limit=16):
    """Other analyses of an accepted tree that differ only in which of a word's
    lexical entries is used, where several entries of the same type fit the
    same spelling (Hausa plain "nama": naamàa_n 'meat' and naamàa_n_animal).
    Replay cannot tell them apart; a ranking model, the tagger or the reader must.

    `resolved` is the tree replay_with_entries returned. Returns the other
    resolved trees that the grammar accepts, one word changed at a time
    (at most `limit`); each must be replayed again to get its structure."""
    from ..encoding import Leaf, Node
    from .grammar import ReplayFailure
    leaves, usable = _leaf_candidates(grammar, lexicon, tree, tokens, strict=False)
    chosen = []

    def walk(t):
        if isinstance(t, Leaf):
            chosen.append(t.entry[len('entry:'):] if t.entry.startswith('entry:') else None)
        else:
            for c in t.children:
                walk(c)
    walk(resolved)
    out = []
    for i, cands in enumerate(usable):
        for c in cands:
            if c == chosen[i] or len(out) >= limit:
                continue
            it = iter(range(len(leaves)))

            def swap(t):
                if isinstance(t, Leaf):
                    j = next(it)
                    return Leaf('entry:' + c, t.forms) if j == i else t
                return Node(t.label, tuple(swap(k) for k in t.children))
            alt = swap(resolved)
            grammar.reset()
            try:
                grammar.replay_tree(alt, tokens)
                out.append(alt)
            except ReplayFailure:
                pass
    return out
