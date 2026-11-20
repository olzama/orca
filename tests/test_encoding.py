from orca.encoding import (Leaf, Node, absolute_depths, decode, encode,
                           relative_depths)


def L(entry, *forms):
    return Leaf(entry, forms or (entry,))


def test_single_leaf_with_chain():
    t = Node('root', (Node('u2', (Node('u1', (L('a'),)),)),))
    enc = encode(t)
    assert enc[0].chain == ('root', 'u2', 'u1') and enc[0].depth is None
    assert decode(enc) == t


def test_left_and_right_branching():
    left = Node('r2', (Node('r1', (L('a'), L('b'))), L('c')))
    right = Node('r2', (L('a'), Node('r1', (L('b'), L('c')))))
    assert [x.depth for x in encode(left)] == [2, 1, None]
    assert [x.depth for x in encode(right)] == [1, 2, None]
    assert decode(encode(left)) == left
    assert decode(encode(right)) == right


def test_unaries_above_binary_and_leaf_and_multi_token_leaf():
    t = Node('root', (Node('u', (Node('bin', (
        Node('lr', (L('new_york', 'New', 'York'),)),
        Node('u3', (Node('bin2', (L('b'), Node('lr2', (L('c'),)))),)))),)),))
    enc = encode(t)
    assert enc[0].node == ('root', 'u', 'bin')
    assert enc[1].node == ('u3', 'bin2')
    assert decode(enc) == t


def test_relative_depths_round_trip():
    t = Node('r3', (Node('r2', (Node('r1', (L('a'), L('b'))), L('c'))), L('d')))
    enc = encode(t)
    rel = relative_depths(enc)
    assert rel == [3, -1, -1, None]
    assert absolute_depths(rel) == [x.depth for x in enc]
