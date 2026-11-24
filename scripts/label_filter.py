#!/usr/bin/env python3
"""A grammar-derived filter on label sequences: rule out, without a replay,
derivations the grammar can never accept (roadmap O86).

The idea is that of CFG filtering for HPSG (Torisawa et al. 2000; Yoshinaga
et al. 2003; Matsuzaki et al. 2007): check local configurations against the
grammar once, and skip candidates that contain one that cannot unify. Here the
local configurations come straight from Orca's labels:

  leaf   the leaf label alone: the lexical type's most general sign with the
         label's lexical rules and unary rules applied, bottom-up;
  node   each binary node named by a tree label, with every daughter that is a
         single leaf filled in with that leaf's sign (as in the leaf check),
         and the unary rules above the node (the rest of the tree label)
         applied to the mother. A daughter that spans more than one leaf is
         left unconstrained.

Whether a daughter is a single leaf follows from the depths alone (decode
splits a span at its shallowest node, the leftmost on ties): leaf i is the
whole left daughter of node i if i is the first leaf or depth(i-1) <= depth(i);
leaf i+1 is the whole right daughter if it is the last leaf or
depth(i+1) < depth(i).

Why the filter is sound (it never rejects a derivation the grammar accepts):
replay builds each leaf from a lexical entry of the labeled type, unified with
its tokens; the entry's structure is subsumed by the type's expanded structure,
so the real leaf is at least as specific as the sign checked here. Rule
application is unification with the rule's daughter slots, which is monotone:
if it fails for a more general daughter it fails for every more specific one.
Deleting the daughters' features from a mother removes the same paths in both,
so subsumption is kept; a root condition is a unification check, also
monotone. Leaving a daughter unconstrained drops information, which can only
let more through. So a failure here implies the same failure in every replay
of every derivation that has these labels. The gold labels of Redwoods train
and dev must all pass (`verify`).

Results are memoized per key (the leaf label; the node label with its leaf
daughters' labels) and can be saved to and loaded from a table
(data/label-filter/*.json); keys not in the table are computed on demand.

    label_filter.py verify --data data/encoded-2025 --splits train,dev --out data/label-filter/erg-2025.json
        check every gold label sequence (must all pass) and save the table
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)

from eval_trees import to_leaves  # noqa: E402
from orca.encoding import Leaf, Node  # noqa: E402
from orca.tfs.dag import UnificationFailure  # noqa: E402
from orca.tfs.grammar import ARGS, DELETED_DAUGHTERS, ReplayFailure  # noqa: E402

CONT = '<cont>'


class LabelFilter:
    def __init__(self, fg, table=None):
        self.fg = fg                       # orca.tfs.fast.FastGrammar
        self.memo = {}                     # key -> True (can unify) / False (never)
        if table:
            for k, v in json.load(open(table)).items():
                self.memo[_tuple(json.loads(k))] = v
        self.loaded = len(self.memo)
        self.computed = 0

    # -- the two checks ---------------------------------------------------

    def _leaf_sign(self, entry, chain):
        """The most general sign of a leaf label (raises on failure)."""
        t = Leaf(entry, ('x',))
        for label in reversed(chain):
            t = Node(label, (t,))
        fs, _ = self.fg.replay_tree(t, [])
        return fs

    def leaf_ok(self, entry, chain):
        key = ('L', entry, chain)
        v = self.memo.get(key)
        if v is None:
            from orca.tfs import _fastdag as C
            mark = C.mark()
            try:
                self._leaf_sign(entry, chain)
                v = True
            except ReplayFailure as e:
                v = not _hard(e)
            finally:
                C.undo(mark)
            self.memo[key] = v
            self.computed += 1
        return v

    def node_ok(self, node, left, right):
        """node: the tree label's labels (unary rules above, then the binary rule);
        left/right: (entry, chain) of a daughter that is a single leaf, else None."""
        key = ('N', node, left, right)
        v = self.memo.get(key)
        if v is None:
            v = self._node(node, left, right)
            self.memo[key] = v
            self.computed += 1
        return v

    def _node(self, node, left, right):
        from orca.tfs import _fastdag as C
        fg = self.fg
        F = fg.F
        mark = C.mark()
        try:
            dtrs = []
            for d in (left, right):
                dtrs.append(self._leaf_sign(*d) if d is not None else None)
            fs = self._apply(node[-1], dtrs)
            for label in reversed(node[:-1]):
                fs = self._apply(label, [fs])
            return True
        except ReplayFailure as e:
            return not _hard(e)
        except UnificationFailure:
            return False
        except KeyError:
            return True                    # an unknown rule name: leave it to replay
        finally:
            C.undo(mark)

    def _apply(self, label, dtrs):
        """Mother of rule `label` over daughters (None = unconstrained), as replay builds it."""
        from orca.tfs import _fastdag as C
        fg = self.fg
        F = fg.F
        name = label.lower()
        if name.startswith('root_'):
            fs = dtrs[0]
            if fs is not None:
                fg._check(C.unify(fg.instance(name), fs, [fg.fid('<root>')]))
            return fs
        if name == '<unk>':
            raise KeyError(name)
        fs = fg.instance(name)
        arg = fg._check(C.get(fs, [F[ARGS]]))
        path = [F[ARGS]]
        for d in dtrs:
            first = fg._check(C.get(arg, [F['FIRST']], path))
            if d is not None:
                fg._check(C.unify(first, d, path + [F['FIRST']]))
            arg = fg._check(C.get(arg, [F['REST']], path))
            path = path + [F['REST']]
        t = C.type(arg)
        if t != fg.NULL and fg.h.glb(fg.type_names[t], fg.null_name) is None:
            raise UnificationFailure([ARGS], 'too few daughters', name)
        for f in DELETED_DAUGHTERS:
            C.del_arc(fs, F[f])
        return C.deref(fs)

    # -- a whole label sequence ------------------------------------------

    def check(self, forms, leaf_labels, tree_labels):
        """None if no local configuration is ruled out, else the token positions to reconsider
        (the tokens of the offending leaf, or of the two leaves around the offending node)."""
        try:
            leaves = to_leaves(forms, leaf_labels, tree_labels)
        except Exception:
            return None
        # token positions of each merged leaf
        toks, li = [], -1
        for j, l in enumerate(leaf_labels):
            if not l.startswith(CONT) or li < 0:
                li += 1
                toks.append([])
            toks[li].append(j)
        n = len(leaves)
        if len(toks) != n:
            return None
        lab = [(x.entry, x.chain) for x in leaves]
        for i, (e, ch) in enumerate(lab):
            if e.startswith('<'):
                continue
            if not self.leaf_ok(e, ch):
                return toks[i]
        depth = [x.depth for x in leaves]
        for i in range(n - 1):
            node = leaves[i].node
            if not node or node == ('<unk>',):
                continue
            left_alone = i == 0 or depth[i - 1] <= depth[i]
            right_alone = i + 1 == n - 1 or depth[i + 1] < depth[i]
            left = lab[i] if left_alone and not lab[i][0].startswith('<') else None
            right = lab[i + 1] if right_alone and not lab[i + 1][0].startswith('<') else None
            if not self.node_ok(tuple(node), left, right):
                return toks[i] + toks[i + 1]
        return None

    def save(self, path):
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        json.dump({json.dumps(k): v for k, v in self.memo.items()}, open(path, 'w'))


def _tuple(x):
    """JSON lists back to the nested tuples the memo keys are made of."""
    return tuple(_tuple(y) for y in x) if isinstance(x, list) else x


def _hard(e):
    """A replay failure that is a real unification failure (not a missing type or rule name,
    which replay reports as 'missing ...' and which we leave to replay)."""
    return not (isinstance(e.cause, str) and e.cause.startswith('missing'))


def load_grammar():
    from orca.tfs.fast import FastGrammar
    from orca.tfs.grammar import Grammar
    return FastGrammar(Grammar(os.path.join(HERE, '..', 'data/erg/2025/english.tdl')))


def verify(a):
    from train_tagger import read
    fg = load_grammar()
    lf = LabelFilter(fg, a.table if a.table and os.path.exists(a.table) else None)
    bad, n, t0 = [], 0, time.time()
    for split in a.splits.split(','):
        for s in read(os.path.join(a.data, f'{split}.jsonl'), a.limit):
            n += 1
            r = lf.check(s['forms'], s['leaf'], s['tree'])
            if r is not None:
                bad.append({'id': s['id'], 'tokens': r, 'labels': [(s['leaf'][j], s['tree'][j]) for j in r]})
            if n % 2000 == 0:
                fg.reset()
                print(f'{n} sentences, {len(bad)} rejected, {len(lf.memo)} keys, {time.time() - t0:.0f} s', flush=True)
    fails = sum(1 for v in lf.memo.values() if not v)
    print(json.dumps({'sentences': n, 'gold rejected': len(bad), 'keys': len(lf.memo), 'keys that fail': fails,
                      'seconds': round(time.time() - t0)}, indent=1))
    for b in bad[:20]:
        print(json.dumps(b))
    if a.out:
        lf.save(a.out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=('verify',))
    ap.add_argument('--data', default='data/encoded-2025')
    ap.add_argument('--splits', default='train,dev')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--table', help='start from this table')
    ap.add_argument('--out')
    a = ap.parse_args()
    verify(a)


if __name__ == '__main__':
    main()
