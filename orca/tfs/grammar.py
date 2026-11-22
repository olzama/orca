"""A TDL grammar as feature structures, and replay of a derivation.

Replay takes one derivation (rule names over lexical entries, with the token
feature structures of the leaves) and applies the grammar to it bottom-up:
one copy of the rule per node, one unification per daughter. No search.
"""
import re
from typing import Dict, Optional

from delphin import derivation as dlv
from delphin import tdl

from .dag import Node, UnificationFailure, Unifier, deref
from .hierarchy import TOP, Hierarchy, load_plan

LIST, CONS, NULL, DIFF_LIST = '*list*', '*cons*', '*null*', '*diff-list*'
ARGS = 'ARGS'
DELETED_DAUGHTERS = ('ARGS', 'HD-DTR', 'NH-DTR', 'LCONJ-DTR', 'RCONJ-DTR', 'DTR',
                     'DTR1', 'DTR2', 'DTRA', 'DTRB')
TOKENS_LIST, TOKENS_LAST = ('TOKENS', '+LIST'), ('TOKENS', '+LAST')
DAG_TOKEN = re.compile(r'\[|\]|"(?:\\.|[^"\\])*"|#\d+=?|[^\s\[\]"]+')


class ReplayFailure(Exception):
    def __init__(self, where, cause):
        super().__init__(f'{where}: {cause}')
        self.where, self.cause = where, cause


class Grammar:
    def __init__(self, top_file):
        self.h = Hierarchy()
        self.instances: Dict[str, object] = {}       # name -> tdl definition
        self.status: Dict[str, Optional[str]] = {}
        for path, section, status in load_plan(top_file):
            if section == 'type':
                self.h.add_file(path)
            elif section == 'instance' and status in (
                    'rule', 'lex-rule', 'lex-entry', 'generic-lex-entry', None):
                for event, obj, _ in tdl.iterparse(path, encoding='utf-8'):
                    if event in ('TypeDefinition', 'LexicalRuleDefinition'):
                        name = obj.identifier.lower()
                        self.instances[name] = obj
                        self.status[name] = status
        self.h.finalize()
        # list types: the ERG's *list* *cons* *null* *diff-list*, or the Matrix's plain names (HaG)
        plain = '*cons*' not in self.h.parents and 'cons' in self.h.parents
        self.LIST, self.CONS, self.NULL, self.DIFF_LIST = ('list', 'cons', 'null', 'diff-list') if plain else (LIST, CONS, NULL, DIFF_LIST)
        self._constraints: Dict[str, Optional[Node]] = {}
        self._building = set()
        self._fs: Dict[str, Node] = {}
        self._tokens: Dict[str, Node] = {}
        self.u = Unifier(self.h.glb, self.constraint)
        self._find_introducers()

    # -- from TDL to nodes -----------------------------------------------

    def _find_introducers(self):
        """The most general type that mentions each feature."""
        local = {}
        for name, defs in self.h.definitions.items():
            feats = set()
            for d in defs:
                for term in d.conjunction.terms:
                    if isinstance(term, tdl.AVM):
                        feats.update(path.split('.')[0].upper() for path, _ in term.features())
            local[name] = feats
        self.intro: Dict[str, str] = {}
        for name, feats in local.items():
            for f in feats:
                cur = self.intro.get(f)
                if cur is None or self.h.subsumes(name, cur):
                    self.intro[f] = name
        self.local_features = local

    def _raw(self, term, corefs) -> Node:
        """A TDL term as nodes, with no type constraints applied yet."""
        if term is None:
            return Node(self.NULL)
        if isinstance(term, tdl.Conjunction):
            node = None
            for t in term.terms:
                node = self._raw_into(node, t, corefs)
            return node if node is not None else Node(TOP)
        return self._raw_into(None, term, corefs)

    def _raw_into(self, node, term, corefs):
        if isinstance(term, tdl.Coreference):
            key = str(term)
            shared = corefs.get(key)
            if shared is None:
                shared = corefs[key] = node if node is not None else Node(TOP)
                return shared
            if node is None:
                return shared
            return self._raw_merge(shared, node)
        if isinstance(term, tdl.String):
            new = Node('"' + str(term).strip('"') + '"')
        elif isinstance(term, tdl.Regex):
            new = Node('string')
        elif isinstance(term, tdl.TypeIdentifier):
            new = Node(str(term).lower())
        elif isinstance(term, tdl.AVM):
            new = self._raw_avm(term, corefs)
        elif isinstance(term, tdl.Conjunction):
            new = self._raw(term, corefs)
        else:
            raise TypeError(f'unexpected TDL term {type(term).__name__}')
        return new if node is None else self._raw_merge(node, new)

    def _raw_avm(self, avm, corefs):
        if isinstance(avm, tdl.DiffList):
            node, last = Node(self.DIFF_LIST), Node(TOP)
            cur = node
            feat = 'LIST'
            for value in avm.values():
                cell = Node(self.CONS)
                cell.arcs['FIRST'] = self._raw(value, corefs)
                cur.arcs[feat] = cell
                cur, feat = cell, 'REST'
            cur.arcs[feat] = last
            node.arcs['LAST'] = last
            return node
        feats = list(avm.features())
        if isinstance(avm, tdl.ConsList):
            node = Node(self.CONS if feats else (self.NULL if avm.terminated else self.LIST))
        elif type(avm).__name__ == '_ImplicitAVM':
            node = Node(self.CONS if feats else self.LIST)
        else:
            node = Node(TOP)
        for path, value in feats:
            cur = node
            parts = path.upper().split('.')
            for f in parts[:-1]:
                cur = deref(cur)
                cur = cur.arcs.setdefault(f, Node(TOP))
            cur = deref(cur)
            child = self._raw(value, corefs)
            if parts[-1] in cur.arcs:
                self._raw_merge(cur.arcs[parts[-1]], child)
            else:
                cur.arcs[parts[-1]] = child
        return node

    def _raw_merge(self, a, b):
        """Merge two raw nodes (types are only combined, not yet constrained)."""
        a, b = deref(a), deref(b)
        if a is b:
            return a
        t = self.h.glb(a.type, b.type)
        if t is None:
            raise UnificationFailure((), a.type, b.type)
        a.type = t
        b.fwd = a
        for f, v in b.arcs.items():
            if f in a.arcs:
                self._raw_merge(a.arcs[f], v)
            else:
                a.arcs[f] = v
        return a

    def _wellform(self, node, seen, top=True, path=()):
        """Apply type constraints to a raw structure, daughters first."""
        node = deref(node)
        if id(node) in seen or not node.arcs:
            return node
        seen.add(id(node))
        for f in list(node.arcs):
            self._wellform(node.arcs[f], seen, True, path + (f,))
        if not top:
            return node
        node = deref(node)
        t = node.type
        for f in node.arcs:
            intro = self.intro.get(f)
            if intro is None:
                raise ValueError(f'feature {f} is not introduced by any type')
            g = self.h.glb(t, intro)
            if g is None:
                raise UnificationFailure(path + (f,), t, intro)
            t = g
        node.type = t
        node.expanded = True
        c = self.constraint(t)
        if c is not None:
            self.u.unify(node, self.u.copy(c), path)
        return deref(node)

    # -- types -----------------------------------------------------------

    def constraint(self, t) -> Optional[Node]:
        """The expanded constraint of a type; None if it has no features."""
        if t in self._constraints:
            return self._constraints[t]
        if t.startswith('"'):
            return None
        if t in self._building:
            raise ValueError(f'type constraint of {t} depends on itself')
        self._building.add(t)
        mark = self.u.mark()
        node = Node(t, expanded=True)
        h = self.h
        if t in h.parents:
            parents, defs = h.parents[t], h.definitions.get(t, [])
        else:                               # an added greatest lower bound
            above = h.authored_above(t)
            parents = [a for a in above if not any(b != a and h.subsumes(a, b) for b in above)]
            defs = []
        for p in parents:
            c = self.constraint(p)
            if c is not None:
                self.u.unify(node, self.u.copy(c), [t])
        for d in defs:
            corefs = {}
            for term in d.conjunction.terms:
                if isinstance(term, tdl.AVM):
                    raw = self._raw_avm(term, corefs)
                    raw.type = t
                    self._wellform(raw, set(), top=False, path=(t,))
                    raw = deref(raw)
                    raw.expanded = True
                    self.u.unify(node, raw, [t])
        self._building.discard(t)
        node = deref(node)
        self._constraints[t] = self.u.freeze(self._unfill(node)) if node.arcs else None
        del self.u.trail[mark:]          # changes to fresh nodes only
        return self._constraints[t]

    def _unfill(self, root):
        """Shrink a structure: a substructure that says nothing beyond the
        constraint of its type is replaced by a placeholder of that type,
        which unification expands again only if it is needed."""
        indeg = {}

        def scan(n):
            n = deref(n)
            indeg[id(n)] = indeg.get(id(n), 0) + 1
            if indeg[id(n)] == 1:
                for v in n.arcs.values():
                    scan(v)

        scan(root)
        done = set()

        def plain(n):
            return not n.arcs and indeg.get(id(n), 1) == 1

        def walk(n, is_root):
            n = deref(n)
            if id(n) in done or not n.arcs:
                return
            done.add(id(n))
            for v in n.arcs.values():
                walk(v, False)
            if is_root or indeg[id(n)] != 1 or n.type.startswith('"'):
                return
            c = self._constraints.get(n.type) if n.type not in self._building else None
            if c is None or len(c.arcs) != len(n.arcs):
                return
            seen = set()
            for f, v in n.arcs.items():
                cv = c.arcs.get(f)
                if cv is None:
                    return
                v, cv = deref(v), deref(cv)
                if cv.arcs or id(cv) in seen or not plain(v) or v.type != cv.type:
                    return
                seen.add(id(cv))
            n.arcs = {}
            n.expanded = False

        walk(root, True)
        return root

    # -- instances -------------------------------------------------------

    def instance(self, name) -> Node:
        """The feature structure of a rule, lexical rule or lexical entry."""
        fs = self._fs.get(name)
        if fs is None:
            d = self.instances[name]
            mark = self.u.mark()
            raw = self._raw(d.conjunction, {})
            if not raw.arcs:                 # no local features: make it expandable
                raw = deref(raw)
            fs = self._wellform(raw, set(), path=(name,))
            if not fs.expanded:
                fs = self.u.expand(fs)
            fs = self.u.freeze(self._unfill(fs))
            self._fs[name] = fs
            del self.u.trail[mark:]
        return fs

    # -- replay ----------------------------------------------------------

    def token_node(self, text) -> Node:
        """A token feature structure as stored in a derivation."""
        cached = self._tokens.get(text)
        if cached is not None:
            return self.u.copy(cached)
        if len(self._tokens) > 20000:
            self._tokens.clear()
        toks = DAG_TOKEN.findall(text.replace('\\"', '"'))
        pos = 0
        tags = {}

        def value():
            nonlocal pos
            tok = toks[pos]
            tag = None
            if tok.startswith('#'):
                tag = tok.rstrip('=')
                pos += 1
                if not tok.endswith('='):
                    return tags[tag]
                tok = toks[pos]
            node = Node(tok if tok.startswith('"') else tok.lower())
            pos += 1
            if tag:
                tags[tag] = node
            if pos < len(toks) and toks[pos] == '[':
                pos += 1
                while toks[pos] != ']':
                    feat = toks[pos].upper()
                    pos += 1
                    node.arcs[feat] = value()
                pos += 1
            return node

        node = self._wellform(value(), set(), path=('token',))
        self._tokens[text] = node
        return self.u.copy(node)

    def replay(self, node, where='0') -> Node:
        """Feature structure of a derivation node (a PyDelphin UDF node)."""
        u = self.u
        kids = node.daughters
        name = node.entity.lower()
        try:
            if kids and all(isinstance(d, dlv.UDFTerminal) for d in kids):
                fs = u.copy(self.instance(name))
                tokens = [self.token_node(t.tfs) for t in (kids[0].tokens or [])]
                if tokens:
                    lst = Node(self.NULL)
                    for tok in reversed(tokens):
                        cell = Node(self.CONS, expanded=True)
                        cell.arcs['FIRST'], cell.arcs['REST'] = tok, lst
                        lst = cell
                    u.unify(u.get(fs, *TOKENS_LIST), lst, list(TOKENS_LIST))
                    u.unify(u.get(fs, *TOKENS_LAST), tokens[-1], list(TOKENS_LAST))
                return fs
            fs = u.copy(self.instance(name))
            arg = u.get(fs, ARGS)
            for i, d in enumerate(kids):
                dfs = self.replay(d, f'{where}.{i}')
                u.unify(u.get(arg, 'FIRST'), dfs, [ARGS] + ['REST'] * i + ['FIRST'])
                arg = u.get(arg, 'REST')
            fs = deref(fs)
            for f in DELETED_DAUGHTERS:
                fs.arcs.pop(f, None)
            return fs
        except UnificationFailure as e:
            raise ReplayFailure(f'{where} {name}', e) from None
        except KeyError as e:
            raise ReplayFailure(f'{where} {name}', f'missing {e}') from None
        except ValueError as e:              # e.g. a token feature the grammar lacks
            raise ReplayFailure(f'{where} {name}', f'missing {e}') from None

    def replay_tree(self, tree, tokens, where='0', cache=None):
        """Replay a tree of `orca.encoding` nodes, as decoded from tagger
        labels. Leaves name a lexical type (or `entry:NAME`); `tokens` is the
        list of token structures of the sentence, consumed left to right.
        A node whose label starts with `root_` is checked as a root condition.
        Returns the feature structure and the remaining tokens.

        `cache` (a dict) makes repeated replays of similar trees cheap: a
        subtree that failed before fails at once, and subtrees that were
        complete when a failure occurred above or beside them are copied
        from a snapshot instead of being rebuilt."""
        if cache is None:
            return self._replay_tree(tree, tokens, where, None)
        key = (tree, len(tokens))
        hit = cache.get(key)
        if hit is not None:
            if hit[0] == 'ok':
                return self.u.copy(hit[1]), tokens[hit[2]:]
            raise ReplayFailure(where + hit[1], hit[2])
        try:
            return self._replay_tree(tree, tokens, where, cache)
        except ReplayFailure as e:
            if key not in cache:
                cache[key] = ('fail', e.where[len(where):], e.cause)
            raise

    def _replay_tree(self, tree, tokens, where, cache):
        from ..encoding import Leaf
        u = self.u
        try:
            if isinstance(tree, Leaf):
                name = tree.entry.lower()
                if name.startswith('entry:'):
                    fs = u.copy(self.instance(name[6:]))
                else:
                    if name not in self.h.code or not name.endswith('_le'):
                        raise KeyError(name)
                    fs = u.expand(Node(name))
                n = len(tree.forms)
                mine, tokens = [self.token_node(t) for t in tokens[:n]], tokens[n:]
                if mine:
                    lst = Node(self.NULL)
                    for tok in reversed(mine):
                        cell = Node(self.CONS, expanded=True)
                        cell.arcs['FIRST'], cell.arcs['REST'] = tok, lst
                        lst = cell
                    u.unify(u.get(fs, *TOKENS_LIST), lst, list(TOKENS_LIST))
                    u.unify(u.get(fs, *TOKENS_LAST), mine[-1], list(TOKENS_LAST))
                return fs, tokens
            name = tree.label.lower()
            if name.startswith('root_'):
                fs, tokens = self.replay_tree(tree.children[0], tokens, where + '.0', cache)
                u.unify(u.copy(self.instance(name)), fs, ['<root>'])
                return fs, tokens
            built = []                       # complete daughters: (key, fs, tokens used)
            try:
                for i, d in enumerate(tree.children):
                    before = len(tokens)
                    dfs, tokens = self.replay_tree(d, tokens, f'{where}.{i}', cache)
                    built.append(((d, before), dfs, before - len(tokens)))
                mark = u.mark()
                fs = u.copy(self.instance(name))
                arg = u.get(fs, ARGS)
                for i, (_, dfs, _) in enumerate(built):
                    u.unify(u.get(arg, 'FIRST'), dfs, [ARGS] + ['REST'] * i + ['FIRST'])
                    arg = u.get(arg, 'REST')
                if deref(arg).type != self.NULL and self.h.glb(deref(arg).type, self.NULL) is None:
                    raise UnificationFailure([ARGS], 'too few daughters', name)
            except (ReplayFailure, UnificationFailure):
                if cache is not None and built:
                    if len(built) == len(tree.children):
                        u.undo(mark)         # give the daughters back as they were
                    for key, dfs, used in built:
                        if key not in cache:
                            cache[key] = ('ok', u.copy(dfs), used)
                raise
            fs = deref(fs)
            for f in DELETED_DAUGHTERS:
                fs.arcs.pop(f, None)
            return fs, tokens
        except ReplayFailure:
            raise
        except UnificationFailure as e:
            raise ReplayFailure(f'{where} {name}', e) from None
        except (KeyError, ValueError) as e:
            raise ReplayFailure(f'{where} {name}', f'missing {e}') from None

