"""Forest operations against brute-force enumeration of the trees."""
import os
import random

import pytest

from kelp.discriminants import (ABSENT, CHAIN, NOT_CHAIN, NOT_SPAN, PRESENT, SPAN, Chains,
                                Constraint, satisfies, spans)
from kelp.forest import LEXEME, LEXRULE, RULE, Edge, Forest, Token, load_forests

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, '..', 'data', 'kelp', 'mrs-forest')


def small_forest():
    """Three words; two bracketings, packed; lexical and unary ambiguity; a
    ternary rule; a two-word lexical entry."""
    toks = {i: Token(i, i, i + 1, '', 'abc'[i]) for i in range(3)}
    n = [100]

    def edge(label, kind, start, end, *dtrs):
        n[0] += 1
        e = Edge(n[0], label, kind, start, end)
        if kind == LEXEME:
            e.tokens = list(dtrs)
        else:
            e.daughters = list(dtrs)
        return e

    a = edge('a1', LEXEME, 0, 1, toks[0])
    a.alternates = [edge('a2', LEXEME, 0, 1, toks[0])]
    b = edge('b1', LEXEME, 1, 2, toks[1])
    b.alternates = [edge('lr', LEXRULE, 1, 2, edge('b2', LEXEME, 1, 2, toks[1]))]
    c = edge('c1', LEXEME, 2, 3, toks[2])
    c.alternates = [edge('u1', RULE, 2, 3, edge('u2', RULE, 2, 3, edge('c2', LEXEME, 2, 3, toks[2])))]
    bc_word = edge('bc', LEXEME, 1, 3, toks[1], toks[2])
    ab = edge('x', RULE, 0, 2, a, b)
    bc = edge('y', RULE, 1, 3, b, c)
    bc.alternates = [edge('z', RULE, 1, 3, b, c), bc_word]
    top = edge('s1', RULE, 0, 3, ab, c)
    top.alternates = [edge('s2', RULE, 0, 3, a, bc), edge('s3', RULE, 0, 3, a, b, c),
                      edge('u1', RULE, 0, 3, edge('s2', RULE, 0, 3, a, bc))]
    edges = {}

    def collect(e):
        for x in e.packed():
            if x.id not in edges:
                edges[x.id] = x
                for d in x.daughters:
                    collect(d)

    collect(top)
    return Forest(toks, edges, [('root_a', top), ('root_b', top)])


def brute(forest):
    """Every distinct tree, with its collapsed nodes."""
    trees = {}
    for _, t in forest.trees():
        trees.setdefault(t.key(), t)
    return {k: spans(t) for k, t in trees.items()}


def check(forest, rng, rounds=5):
    chains, every = Chains(forest), brute(forest)
    for _ in range(rounds):
        constraints, left = [], dict(every)
        while True:
            counts = chains.count(constraints)
            assert counts.total == len(left)
            assert {t.key() for t in chains.trees(constraints)} == set(left)
            node, _ = chains.pick(counts)
            assert counts.using[node.id] > 0
            want = {}
            for sp in left.values():
                for (i, j), labels in sp.items():
                    props = [Constraint(SPAN, i, j), Constraint(CHAIN, i, j, labels)]
                    props += [Constraint(PRESENT, i, j, (x,)) for x in set(labels)]
                    for p in props:
                        want[p] = want.get(p, 0) + 1
            want = {p: k for p, k in want.items() if k < len(left)}
            found = chains.discriminants(constraints, counts)
            assert found == want
            if not found:
                break
            c = rng.choice(sorted(found, key=repr))
            if rng.random() < 0.5:
                c = c.negated()
            constraints.append(c)
            left = {k: sp for k, sp in left.items() if satisfies(sp, c)}
        assert len(left) >= 1


def test_small_forest_counts():
    forest = small_forest()
    chains = Chains(forest)
    # s1: 2*2*2; s2 (alone and under u1): 2 * (2*2 + 2*2 + 1) each; s3: 2*2*2
    assert chains.count().total == len(brute(forest)) == 8 + 18 + 18 + 8


def test_small_forest_constraints():
    chains = Chains(small_forest())
    assert chains.count([Constraint(SPAN, 0, 2)]).total == 8                 # s1 only
    assert chains.count([Constraint(SPAN, 1, 3)]).total == 36                # s2, with and without u1
    assert chains.count([Constraint(CHAIN, 0, 3, ('u1', 's2'))]).total == 18
    assert chains.count([Constraint(PRESENT, 0, 3, ('s2',))]).total == 36
    assert chains.count([Constraint(ABSENT, 0, 3, ('s2',))]).total == 16
    assert chains.count([Constraint(CHAIN, 1, 3, ('bc',))]).total == 4
    assert chains.count([Constraint(SPAN, 0, 2), Constraint(SPAN, 1, 3)]).total == 0
    assert chains.count([Constraint(NOT_SPAN, 0, 2), Constraint(NOT_SPAN, 1, 3)]).total == 8    # s3 only
    assert chains.count([Constraint(NOT_CHAIN, 0, 3, ('u1', 's2'))]).total == 34
    assert chains.count([Constraint(ABSENT, 1, 2, ('lr',)), Constraint(SPAN, 0, 2)]).total == 4


def test_small_forest_against_enumeration():
    check(small_forest(), random.Random(0), rounds=50)


def test_lexical_labels():
    chains = Chains(small_forest(), lexlabel=lambda name: name[0].upper())
    found = chains.discriminants()
    assert Constraint(CHAIN, 1, 2, ('lr', 'B')) in found
    assert Constraint(PRESENT, 0, 1, ('A',)) not in found       # a1 and a2 share the label: in every tree
    assert all(t.lexical or t.children for t in chains.trees())


@pytest.mark.skipif(not os.path.isdir(PROFILE), reason='needs the MRS test suite forest profile')
def test_mrs_suite_against_enumeration():
    rng = random.Random(1)
    for pid, forest in sorted(load_forests(PROFILE).items()):
        if forest.count() <= 2000:
            check(forest, rng, rounds=3)
