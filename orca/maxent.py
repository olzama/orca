"""Scoring derivations with a DELPH-IN maximum entropy ranking model.

The ERG ships the model ACE uses to rank parses (`redwoods.mem`). Its
features are local configurations of the derivation tree: a node, its
daughters, and up to three of its ancestors (`^` marks the top of the
tree). Leaves are lexical types, with the word below them. A derivation's
score is the sum of the weights of its features.
"""
import os
import pickle
import re
from typing import Dict, List, Tuple

from .encoding import Leaf

LINE = re.compile(r'^\(\d+\) \[1 \((\d+)\) (.*)\] (\S+) \{')
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\S+')


class MaxEnt:
    def __init__(self, path, cache=None):
        cache = cache or path + '.pkl'
        if os.path.exists(cache) and os.path.getmtime(cache) > os.path.getmtime(path):
            with open(cache, 'rb') as f:
                self.weights, self.grandparenting = pickle.load(f)
            return
        self.weights: Dict[Tuple, float] = {}
        self.grandparenting = 3
        with open(path, encoding='utf-8') as f:
            for line in f:
                if line.startswith('*feature-grandparenting*'):
                    self.grandparenting = int(line.split(':=')[1].strip(' .\n'))
                m = LINE.match(line)
                if m:
                    labels = tuple(TOKEN.findall(m.group(2)))
                    self.weights[(int(m.group(1)),) + labels] = float(m.group(3))
        with open(cache, 'wb') as f:
            pickle.dump((self.weights, self.grandparenting), f)

    def features(self, tree, lextype, generic=lambda e: False):
        """Feature keys of a tree whose leaves name lexical entries
        (`entry:NAME`) or lexical types. `lextype` maps an entry to its type."""
        out = []

        def label(t):
            if isinstance(t, Leaf):
                e = t.entry[6:] if t.entry.startswith('entry:') else t.entry
                return lextype(e) or e
            return t.label

        def word(t):
            e = t.entry[6:] if t.entry.startswith('entry:') else t.entry
            w = ' '.join(t.forms)
            return '"' + (w if generic(e) else w.lower()) + '"'

        def walk(t, ancestors):
            me = label(t)
            kids = [word(t)] if isinstance(t, Leaf) else [label(c) for c in t.children]
            for g in range(self.grandparenting + 1):
                up = ancestors[-g:] if g else []
                if g > len(ancestors):
                    if g > len(ancestors) + 1:
                        break
                    up = ['^'] + ancestors
                out.append((g, *up, me, *kids))
            if not isinstance(t, Leaf):
                for c in t.children:
                    walk(c, ancestors + [me])

        top = tree
        while not isinstance(top, Leaf) and top.label.lower().startswith('root_'):
            top = top.children[0]
        walk(top, [])
        return out

    def score(self, tree, lextype, generic=lambda e: False):
        w = self.weights
        return sum(w.get(f, 0.0) for f in self.features(tree, lextype, generic))

    def coverage(self, tree, lextype, generic=lambda e: False) -> Tuple[int, int]:
        fs = self.features(tree, lextype, generic)
        return sum(f in self.weights for f in fs), len(fs)
