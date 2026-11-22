"""Type hierarchy of a TDL grammar, closed under greatest lower bounds.

Each type gets a code: the set of authored types at or below it, as a bit
set. Two types are compatible if their codes intersect, and their greatest
lower bound is the type whose code is that intersection. Grammars leave many
such types implicit; `close()` adds them, as every DELPH-IN processor does
when it loads a grammar.
"""
import os
import re
import time
from typing import Dict, List, Optional

from delphin import tdl

TOP = '*top*'
STRING = 'string'
INCLUDE = re.compile(r'^\s*:include\s+"([^"]+)"', re.M)
SECTION = re.compile(r'^\s*:(begin|end)\s+:(type|instance)(?:\s+:status\s+([\w-]+))?', re.M)


def load_plan(top_file, root=None, outer=(None, None)):
    """Files of a grammar in load order, as (path, section, status).

    Included files that themselves only include others (HaG's hausa-word.tdl)
    are followed recursively; include paths are relative to the grammar root.
    The ERG's top file includes only leaf files, so its plan is unchanged."""
    root = root or os.path.dirname(os.path.abspath(top_file))
    plan, stack = [], [outer]              # sections nest
    with open(top_file, encoding='utf-8') as f:
        for line in f:
            line = line.split(';')[0]
            m = SECTION.match(line)
            if m:
                if m.group(1) == 'begin':
                    stack.append((m.group(2), m.group(3)))
                elif len(stack) > 1:
                    stack.pop()
                continue
            m = INCLUDE.match(line)
            if m:
                name = m.group(1)
                path = os.path.join(root, name if name.endswith('.tdl') else name + '.tdl')
                with open(path, encoding='utf-8') as g:
                    nested = any(INCLUDE.match(l.split(';')[0]) for l in g)
                if nested:
                    plan += load_plan(path, root, stack[-1])
                else:
                    plan.append((path,) + stack[-1])
    return plan


class Hierarchy:
    def __init__(self):
        self.parents: Dict[str, List[str]] = {TOP: []}
        self.definitions = {}            # name -> list of tdl definitions (definition + addenda)
        self.code: Dict[str, int] = {}
        self.by_code: Dict[int, str] = {}
        self.glb_parents: Dict[str, List[str]] = {}   # for added types: authored types just above
        self._glb_cache = {}

    # -- loading ---------------------------------------------------------

    def add_file(self, path):
        for event, obj, _ in tdl.iterparse(path, encoding='utf-8'):
            if event == 'TypeDefinition':
                name = obj.identifier.lower()
                supers = [str(t).lower() for t in obj.supertypes
                          if type(t) is tdl.TypeIdentifier]
                self.parents[name] = supers or [TOP]
                self.definitions[name] = [obj]
            elif event == 'TypeAddendum':
                name = obj.identifier.lower()
                extra = [str(t).lower() for t in obj.supertypes
                         if type(t) is tdl.TypeIdentifier]
                self.parents.setdefault(name, [TOP])
                self.parents[name] += [s for s in extra if s not in self.parents[name]]
                self.definitions.setdefault(name, []).append(obj)

    def finalize(self):
        """Compute codes, then add the missing greatest lower bounds."""
        missing = {s for ps in self.parents.values() for s in ps} - set(self.parents)
        if missing:
            raise ValueError(f'undefined supertypes: {sorted(missing)[:10]}')
        children = {t: [] for t in self.parents}
        for t, ps in self.parents.items():
            for p in ps:
                children[p].append(t)
        self.authored = list(self.parents)
        bit = {t: 1 << i for i, t in enumerate(self.authored)}
        code = {}

        def below(t):                       # iterative post-order
            stack = [(t, iter(children[t]))]
            acc = {t: bit[t]}
            while stack:
                node, it = stack[-1]
                for c in it:
                    if c in code:
                        acc[node] |= code[c]
                    else:
                        acc[c] = bit[c]
                        stack.append((c, iter(children[c])))
                        break
                else:
                    code[node] = acc.pop(node)
                    stack.pop()
                    if stack:
                        acc[stack[-1][0]] |= code[node]

        below(TOP)
        unreachable = set(self.parents) - set(code)
        if unreachable:
            raise ValueError(f'types not under {TOP}: {sorted(unreachable)[:10]}')
        self.code = code
        self.by_code = {c: t for t, c in code.items()}
        if len(self.by_code) != len(code):
            raise ValueError('two types have the same set of subtypes')
        self._close()

    def _close(self):
        """Add a type for every intersection of two codes that has none."""
        start = time.time()
        frontier = list(self.by_code)
        known = list(self.by_code)
        n_new = 0
        while frontier:
            fresh = []
            for a in frontier:
                for b in known:
                    c = a & b
                    if c and c != a and c != b and c not in self.by_code:
                        name = f'glbtype{n_new}'
                        n_new += 1
                        self.by_code[c] = name
                        self.code[name] = c
                        fresh.append(c)
            known += fresh
            frontier = fresh
        self.n_glb = n_new
        self.close_seconds = time.time() - start

    # -- queries ---------------------------------------------------------

    def subsumes(self, general, specific):
        cg, cs = self.code[general], self.code[specific]
        return cg & cs == cs

    def glb(self, a: str, b: str) -> Optional[str]:
        """Most general type that is both a and b, or None if incompatible.
        String literals (written with their quotes) are subtypes of `string`."""
        if a == b:
            return a
        key = (a, b)
        if key in self._glb_cache:
            return self._glb_cache[key]
        qa, qb = a.startswith('"'), b.startswith('"')
        if qa or qb:
            if qa and qb:
                out = None
            else:
                lit, other = (a, b) if qa else (b, a)
                out = lit if self.subsumes(other, STRING) else None
        else:
            out = self.by_code.get(self.code[a] & self.code[b])
        self._glb_cache[key] = out
        return out

    def authored_above(self, name):
        """Authored types that subsume a type (for inheriting constraints)."""
        c = self.code[name]
        return [t for t in self.authored if self.code[t] & c == c]


def load(top_file):
    h = Hierarchy()
    for path, section, _ in load_plan(top_file):
        if section == 'type':
            h.add_file(path)
    h.finalize()
    return h
