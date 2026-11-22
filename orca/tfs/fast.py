"""Replay with the compiled core (`_fastdag`).

`FastGrammar` wraps a loaded `Grammar` and offers the same replay interface
(`replay_tree`, `u.mark()`, `del u.trail[m:]`), so `replay_with_entries` and
the scripts can use either. Feature structures here are integers that name
nodes in the core's arena. Call `reset()` between sentences to free the
arena; nothing made before a reset may be used after it.
"""
from .dag import Node, UnificationFailure, deref
from .grammar import ARGS, CONS, DELETED_DAUGHTERS, NULL, TOKENS_LAST, TOKENS_LIST, ReplayFailure
from . import _fastdag as C


class _Trail:
    """Stands in for the list `Unifier.trail`: `del trail[m:]` keeps the
    changes made since mark m and forgets how to undo them."""

    def __delitem__(self, key):
        C.forget(key.start or 0)


class _Unifier:
    def __init__(self):
        self.trail = _Trail()

    @staticmethod
    def mark():
        return C.mark()

    @staticmethod
    def undo(m):
        C.undo(m)


class FastGrammar:
    def __init__(self, grammar):
        self.g = grammar
        self.h = grammar.h
        self.vpm_path = getattr(grammar, 'vpm_path', None)
        self.u = _Unifier()
        self.type_ids, self.type_names = {}, []
        self.feat_ids, self.feat_names = {}, []
        for t in self.h.code:
            self.tid(t)
        self._instances, self._tokens = {}, {}
        self.leaf_memo = {}
        C.init(self._glb, self._constraint)
        self.null_name = grammar.NULL
        self.NULL, self.CONS = self.tid(grammar.NULL), self.tid(grammar.CONS)
        self.F = {f: self.fid(f) for f in (ARGS, 'FIRST', 'REST') + DELETED_DAUGHTERS}
        self.TL = [self.fid(f) for f in TOKENS_LIST]
        self.TLAST = [self.fid(f) for f in TOKENS_LAST]

    # -- ids ---------------------------------------------------------------

    def tid(self, name):
        i = self.type_ids.get(name)
        if i is None:
            i = self.type_ids[name] = len(self.type_names)
            self.type_names.append(name)
        return i

    def fid(self, name):
        i = self.feat_ids.get(name)
        if i is None:
            i = self.feat_ids[name] = len(self.feat_names)
            self.feat_names.append(name)
        return i

    def _glb(self, a, b):
        t = self.h.glb(self.type_names[a], self.type_names[b])
        return -1 if t is None else self.tid(t)

    def _constraint(self, t):
        c = self.g.constraint(self.type_names[t])
        return -1 if c is None else self.template(c)

    def template(self, root):
        """Register a Python structure (never changed afterwards) as a template."""
        index, order, stack = {}, [], [deref(root)]
        while stack:
            x = deref(stack.pop())
            if id(x) in index:
                continue
            index[id(x)] = len(order)
            order.append(x)
            stack.extend(reversed(list(x.arcs.values())))
        types = [self.tid(x.type) for x in order]
        expanded = [x.expanded for x in order]
        start, feats, targets = [0], [], []
        for x in order:
            for f, v in x.arcs.items():
                feats.append(self.fid(f))
                targets.append(index[id(deref(v))])
            start.append(len(feats))
        return C.add_template(types, expanded, start, feats, targets)

    # -- failures ----------------------------------------------------------

    def _check(self, result):
        if isinstance(result, int):
            return result
        kind, path, a, b = result
        names = [self.feat_names[f] for f in path]
        if kind == 2:
            raise KeyError(names[-1] if names else '?')
        raise UnificationFailure(names, self.type_names[a], self.type_names[b])

    def unify(self, a, b, path=()):
        return self._check(C.unify(a, b, [self.fid(f) for f in path]))

    def get(self, n, *feats):
        return self._check(C.get(n, [self.fid(f) for f in feats]))

    def type(self, n):
        return self.type_names[C.type(n)]

    def arcs(self, n):
        return [(self.feat_names[f], v) for f, v in C.arcs(n)]

    def reset(self):
        C.reset()
        self._tokens.clear()
        self.leaf_memo.clear()

    # -- building blocks ---------------------------------------------------

    def instance(self, name):
        t = self._instances.get(name)
        if t is None:
            t = self._instances[name] = self.template(self.g.instance(name))
        return C.copy_template(t)

    def token(self, text):
        """A token structure, built in the core once per sentence and copied."""
        master = self._tokens.get(text)
        if master is None:
            master = self._tokens[text] = self._build_token(text)
        return C.copy(master)

    def _build_token(self, text):
        from .grammar import DAG_TOKEN
        toks = DAG_TOKEN.findall(text.replace('\\"', '"'))
        pos, tags = 0, {}

        def value():                      # parse into [type, [(feat, child)], node id]
            nonlocal pos
            tok, tag = toks[pos], None
            if tok.startswith('#'):
                tag = tok.rstrip('=')
                pos += 1
                if not tok.endswith('='):
                    return tags[tag]
                tok = toks[pos]
            node = [tok if tok.startswith('"') else tok.lower(), [], None]
            pos += 1
            if tag:
                tags[tag] = node
            if pos < len(toks) and toks[pos] == '[':
                pos += 1
                while toks[pos] != ']':
                    feat = toks[pos].upper()
                    pos += 1
                    node[1].append((feat, value()))
                pos += 1
            return node

        intro, h = self.g.intro, self.h

        def build(node, path):            # children first, then type constraint, as in _wellform
            if node[2] is not None:
                return node[2]
            t = node[0]
            for f, _ in node[1]:
                g = h.glb(t, intro[f])
                if g is None:
                    raise UnificationFailure(path + (f,), t, intro[f])
                t = g
            n = node[2] = C.new_node(self.tid(t))
            for f, child in node[1]:
                C.set_arc(n, self.fid(f), build(child, path + (f,)))
            if node[1]:
                self._check(C.expand(n))
            return n

        return build(value(), ('token',))

    # -- replay ------------------------------------------------------------

    def replay_tree(self, tree, tokens, where='0', cache=None):
        """As `Grammar.replay_tree`, returning (node, remaining tokens)."""
        if cache is None:
            return self._replay(tree, tokens, where, None)
        key = (tree, len(tokens))
        hit = cache.get(key)
        if hit is not None:
            if hit[0] == 'ok':
                return C.copy(hit[1]), tokens[hit[2]:]
            raise ReplayFailure(where + hit[1], hit[2])
        try:
            return self._replay(tree, tokens, where, cache)
        except ReplayFailure as e:
            if key not in cache:
                cache[key] = ('fail', e.where[len(where):], e.cause)
            raise

    def _replay(self, tree, tokens, where, cache):
        from ..encoding import Leaf
        F = self.F
        try:
            if isinstance(tree, Leaf):
                name = tree.entry.lower()
                if name.startswith('entry:'):
                    fs = self.instance(name[6:])
                else:
                    if name not in self.h.code or not name.endswith('_le'):
                        raise KeyError(name)
                    fs = self._check(C.expand(C.new_node(self.tid(name))))
                n = len(tree.forms)
                if any(isinstance(t, tuple) for t in tokens[:n]):
                    return self._leaf_alternatives(tree, tokens[:n], where), tokens[n:]
                mine, tokens = [self.token(t) for t in tokens[:n]], tokens[n:]
                if mine:
                    lst = C.new_node(self.NULL)
                    for tok in reversed(mine):
                        cell = C.new_node(self.CONS, True)
                        C.set_arc(cell, F['FIRST'], tok)
                        C.set_arc(cell, F['REST'], lst)
                        lst = cell
                    self._check(C.unify(self._check(C.get(fs, self.TL)), lst, self.TL))
                    self._check(C.unify(self._check(C.get(fs, self.TLAST)), mine[-1], self.TLAST))
                return fs, tokens
            name = tree.label.lower()
            if name.startswith('root_'):
                fs, tokens = self.replay_tree(tree.children[0], tokens, where + '.0', cache)
                # a root condition is a check, as in ACE: the MRS is read from the structure without it
                # (unified in, it would add e.g. SF prop and make an index an event)
                mark = C.mark()
                try:
                    self._check(C.unify(self.instance(name), fs, [self.fid('<root>')]))
                finally:
                    C.undo(mark)
                return fs, tokens
            built = []
            try:
                for i, d in enumerate(tree.children):
                    before = len(tokens)
                    dfs, tokens = self.replay_tree(d, tokens, f'{where}.{i}', cache)
                    built.append(((d, before), dfs, before - len(tokens)))
                mark = C.mark()
                fs = self.instance(name)
                arg = self._check(C.get(fs, [F[ARGS]]))
                path = [F[ARGS]]
                for i, (_, dfs, _) in enumerate(built):
                    first = self._check(C.get(arg, [F['FIRST']], path))
                    self._check(C.unify(first, dfs, path + [F['FIRST']]))
                    arg = self._check(C.get(arg, [F['REST']], path))
                    path = path + [F['REST']]
                t = C.type(arg)
                if t != self.NULL and self.h.glb(self.type_names[t], self.null_name) is None:
                    raise UnificationFailure([ARGS], 'too few daughters', name)
            except (ReplayFailure, UnificationFailure):
                if cache is not None and built:
                    if len(built) == len(tree.children):
                        C.undo(mark)
                    for key, dfs, used in built:
                        if key not in cache:
                            cache[key] = ('ok', C.copy(dfs), used)
                raise
            for f in DELETED_DAUGHTERS:
                C.del_arc(fs, F[f])
            return C.deref(fs), tokens
        except ReplayFailure:
            raise
        except UnificationFailure as e:
            raise ReplayFailure(f'{where} {name}', e) from None
        except (KeyError, ValueError) as e:
            raise ReplayFailure(f'{where} {name}', f'missing {e}') from None

    def _leaf_alternatives(self, tree, mine, where):
        """A leaf over token positions that each hold alternative tokens (a
        token lattice for raw text): the first combination, in the order
        given, that unifies with the lexical entry."""
        import itertools
        F = self.F
        name = tree.entry.lower()
        last = None
        choices = [t if isinstance(t, tuple) else (t,) for t in mine]
        for alts in choices:              # build masters outside any undo mark, or undo would unbuild them
            for t in alts:
                if t not in self._tokens:
                    self._tokens[t] = self._build_token(t)
        for combo in itertools.product(*choices):
            mark = C.mark()
            try:
                if name.startswith('entry:'):
                    fs = self.instance(name[6:])
                else:
                    if name not in self.h.code or not name.endswith('_le'):
                        raise KeyError(name)
                    fs = self._check(C.expand(C.new_node(self.tid(name))))
                toks = [self.token(t) for t in combo]
                lst = C.new_node(self.NULL)
                for tok in reversed(toks):
                    cell = C.new_node(self.CONS, True)
                    C.set_arc(cell, F['FIRST'], tok)
                    C.set_arc(cell, F['REST'], lst)
                    lst = cell
                self._check(C.unify(self._check(C.get(fs, self.TL)), lst, self.TL))
                self._check(C.unify(self._check(C.get(fs, self.TLAST)), toks[-1], self.TLAST))
                return fs
            except UnificationFailure as e:
                C.undo(mark)
                last = e
        raise last


def extract(fg, fs):
    """MRS of a replayed structure, as `orca.tfs.mrs.extract` returns it."""
    from .mrs import ROLES_FIRST, SKIP, SORTS
    h = fg.h
    names = {}

    def sort(t):
        for letter, name in SORTS:
            if name in h.code and t in h.code and h.subsumes(name, t):
                return letter
        return 'u'

    def var(n):
        n = C.deref(n)
        t = fg.type_names[C.type(n)]
        if t.startswith('"'):
            return t.replace('\\', '')
        if n not in names:
            names[n] = f'{sort(t)}{len(names) + 1}'
        return names[n]

    def items(lst):
        cur, last = fg.get(lst, 'LIST'), fg.get(lst, 'LAST')
        while C.deref(cur) != C.deref(last):
            cell = fg._check(C.expand(cur))
            arcs = dict(fg.arcs(cell))
            if 'FIRST' not in arcs:
                break
            yield fg._check(C.expand(arcs['FIRST']))
            cur = arcs['REST']

    cont = fg.get(fs, 'SYNSEM', 'LOCAL', 'CONT')
    out = {'top': var(fg.get(cont, 'HOOK', 'LTOP')), 'index': var(fg.get(cont, 'HOOK', 'INDEX')),
           'rels': [], 'hcons': []}
    if getattr(fg, 'vpm_path', None):
        out['vpm'] = fg.vpm_path                  # which property mapping applies (compare_mrs.to_pydelphin)
    for ep in items(fg.get(cont, 'RELS')):
        arcs = dict(fg.arcs(ep))
        pred = fg.type(arcs['PRED']) if 'PRED' in arcs else fg.type(ep)
        pred = pred.strip('"').replace('\\', '')
        pred = pred[:-4] if pred.endswith('_rel') else pred
        roles = [r for r in ROLES_FIRST if r in arcs] + sorted(
            r for r in arcs if r not in ROLES_FIRST and r not in SKIP)
        out['rels'].append((pred, {r: var(arcs[r]) for r in roles}))
        span = []                                  # character span, for display (comparisons ignore it)
        for f in ('CFROM', 'CTO'):
            try:
                span.append(int(fg.type(arcs[f]).strip('"').replace('\\', '')))
            except Exception:
                span.append(-1)
        out.setdefault('lnk', []).append(tuple(span))
    for q in items(fg.get(cont, 'HCONS')):
        arcs = dict(fg.arcs(q))
        out['hcons'].append((var(arcs['HARG']), fg.type(q), var(arcs['LARG'])))
    # individual constraints (information structure: topic, focus ...)
    out['icons'] = []
    try:
        for q in items(fg.get(cont, 'ICONS')):
            arcs = dict(fg.arcs(q))
            if 'IARG1' in arcs and 'IARG2' in arcs:
                out['icons'].append((var(arcs['IARG1']), fg.type(q), var(arcs['IARG2'])))
    except Exception:
        pass
    # variable properties (number, person, tense, ...) as grammar feature paths;
    # the grammar's VPM maps them to MRS property names (see compare_mrs.to_pydelphin)
    out['props'] = {}
    sections = _vpm_sections(getattr(fg, 'vpm_path', None))
    paths = {q for feats, _ in sections for q in feats}
    for n, name in list(names.items()):
        if name[0] in 'hu':
            continue
        raw = {}

        def walk(node, path):
            node = fg._check(C.expand(node))
            for f, v in fg.arcs(node):
                p = path + (f,)
                key = '.'.join(p)
                if key in paths:
                    raw[key] = fg.type(C.deref(v))
                elif any(q.startswith(key + '.') for q in paths):
                    walk(v, p)
        try:
            walk(n, ())
        except Exception:       # an unreadable index keeps no properties
            pass
        props = {}
        for feats, rows in sections:
            props.update(_vpm_match(h, feats, rows, raw))
        if props:
            out['props'][name] = props
    return out


# The grammar's variable property mapping (semi.vpm), read for extraction: which
# feature paths under a variable it maps, and the left-hand sides of its forward
# rules (<> and >>) in file order. The ERG's file is the default.
_VPM_SECTIONS = {}


def _vpm_sections(path=None):
    """[(feature paths, [left-hand value tuples])] for each section of the VPM."""
    import os
    path = os.path.normpath(path or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data/erg/2025/semi.vpm'))
    if path not in _VPM_SECTIONS:
        sections = []
        for line in open(path, encoding='utf-8', errors='replace'):
            line = line.split(';')[0].strip()
            if not line:
                continue
            if ' : ' in line:
                feats = tuple(line.split(' : ')[0].split())
                if all(f[0] not in '[' for f in feats):
                    sections.append((feats, []))
            elif sections and ('<>' in line or '>>' in line):
                op = '<>' if '<>' in line else '>>'
                lhs = tuple(line.split(op)[0].split())
                if len(lhs) == len(sections[-1][0]):
                    sections[-1][1].append(lhs)
        _VPM_SECTIONS[path] = sections
    return _VPM_SECTIONS[path]


def _vpm_match(h, feats, rows, raw):
    """The grammar values of one VPM section as the VPM sees them, matching rows by
    subsumption as ACE does: the first row whose every left-hand value equals,
    subsumes, or is a wildcard for the variable's value. Returns {path: value}
    (the row's value, or the variable's own for a wildcard); {} if no row applies."""
    vals = [raw.get(f) for f in feats]
    if all(v is None for v in vals):
        return {}
    for row in rows:
        out, ok = {}, True
        for f, lhs, val in zip(feats, row, vals):
            if lhs == '!':
                ok = val is None
            elif val is None or lhs[0] == '[':
                ok = False
            elif lhs == val or lhs == '*':
                out[f] = val
            elif lhs in h.code and val in h.code and h.subsumes(lhs, val):
                out[f] = lhs
            else:
                ok = False
            if not ok:
                break
        if ok:
            return out
    return {}
