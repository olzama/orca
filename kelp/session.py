"""An annotation session over one full-forest profile.

Holds, per item, the decisions made so far and the item's status. Every
change is appended to a journal file at once, and the journal is read back
at startup, so nothing is lost when the server stops.

The journal is Kelp's own record. Writing the standard profile relations
(`tree`, `decision`, `preference`, `result`) is a separate step.

With a grammar, the session works in two modes. While an item has more
remaining trees than `limit`, it counts on the packed forest, which also
holds trees that the grammar does not license. At or below the limit it
unpacks the remaining trees, has Orca check each one, and from then on works
with the licensed trees only, each with its meaning.
"""
import json
import os
import threading
import time

from delphin import itsdb

from kelp.discriminants import CHAIN, PRESENT, SPAN, Chains, Constraint, satisfies, spans
from kelp.forest import load_forests

ACCEPTED, REJECTED, OPEN = 'accepted', 'rejected', ''


def _to_json(c):
    return {'kind': c.kind, 'start': c.start, 'end': c.end, 'value': list(c.value)}


def _from_json(d):
    return Constraint(d['kind'], int(d['start']), int(d['end']), tuple(d.get('value', ())))


class Item:
    def __init__(self, pid, iid, text, forest):
        self.pid, self.iid, self.text = pid, iid, text
        self.chains = Chains(forest)
        self.total = self.chains.count().total
        self.remaining = self.total
        self.constraints = []
        self.status = OPEN
        self.checked = {}           # tree key -> the engine's result (None: not licensed)
        self.words = self._words(forest)

    def _words(self, forest):
        """The text between each pair of neighboring chart vertices."""
        n = max(t.end for t in forest.tokens.values())
        words = ['?'] * n
        for t in forest.tokens.values():
            if t.end == t.start + 1 and words[t.start] == '?':
                words[t.start] = self.text[t.cfrom:t.cto] if t.cfrom >= 0 else t.form
        return words


def _props(tree_spans):
    """The properties of one tree that can be discriminants."""
    for (i, j), labels in tree_spans.items():
        yield Constraint(SPAN, i, j)
        yield Constraint(CHAIN, i, j, labels)
        for label in set(labels):
            yield Constraint(PRESENT, i, j, (label,))


def _tree_json(t, settled):
    labels, top = [], t
    while len(t.children) == 1:
        labels.append(t.label)
        t = t.children[0]
    labels.append(t.label)
    return {'labels': labels, 'start': top.start, 'end': top.end,
            'settled': settled(Constraint(CHAIN, top.start, top.end, tuple(labels))),
            'children': [_tree_json(c, settled) for c in t.children]}


class Session:
    def __init__(self, profile, journal=None, engine=None, limit=50):
        self.profile = profile
        self.journal = journal or os.path.join(profile, 'kelp-journal.jsonl')
        self.engine, self.limit = engine, limit
        self.lock = threading.Lock()
        ts = itsdb.TestSuite(profile)
        parse = {r['parse-id']: r['i-id'] for r in ts['parse']}
        text = {r['i-id']: r['i-input'] for r in ts['item']}
        self.items = {pid: Item(pid, parse[pid], text[parse[pid]], forest)
                      for pid, forest in sorted(load_forests(profile).items())}
        self._replay_journal()

    def check_ahead(self):
        """Check the trees of every small enough item, one tree at a time, so
        that a request never waits long. Meant for a background thread."""
        for item in list(self.items.values()):
            if item.chains.count(item.constraints).total > self.limit:
                continue
            for t in item.chains.trees(item.constraints):
                with self.lock:
                    if t.key() not in item.checked:
                        item.checked[t.key()] = self.engine.check(t)
            with self.lock:
                _, exact = self._view(item, item.constraints)
                item.remaining = len(exact)

    def _view(self, item, constraints):
        """The forest counts and, when few enough trees remain and there is an
        engine, the licensed remaining trees as (tree, spans, engine result)."""
        counts = item.chains.count(constraints)
        if self.engine is None or counts.total > self.limit:
            return counts, None
        exact = []
        for t in item.chains.trees(constraints):
            key = t.key()
            if key not in item.checked:
                item.checked[key] = self.engine.check(t)
            if item.checked[key] is not None:
                exact.append((t, spans(t), item.checked[key]))
        return counts, exact

    def _replay_journal(self):
        if not os.path.exists(self.journal):
            return
        with open(self.journal) as f:
            for line in f:
                rec = json.loads(line)
                item = self.items.get(rec['parse-id'])
                if item is None:
                    continue
                constraints = [_from_json(d) for d in rec['decisions']]
                remaining = item.chains.count(constraints).total
                if remaining:               # a record that no longer fits the forest is skipped
                    item.constraints, item.status = constraints, rec['status']
                    item.remaining = min(remaining, rec.get('remaining', remaining))

    def _log(self, item):
        rec = {'parse-id': item.pid, 'i-id': item.iid, 'time': time.strftime('%Y-%m-%dT%H:%M:%S'),
               'status': item.status, 'remaining': item.remaining,
               'decisions': [_to_json(c) for c in item.constraints]}
        with open(self.journal, 'a') as f:
            f.write(json.dumps(rec) + '\n')
            f.flush()
            os.fsync(f.fileno())

    def summary(self):
        with self.lock:
            return [{'id': it.pid, 'i-id': it.iid, 'input': it.text, 'total': it.total,
                     'remaining': it.remaining, 'decisions': len(it.constraints),
                     'status': it.status} for it in self.items.values()]

    def state(self, pid, show=0):
        with self.lock:
            return self._state(self.items[pid], show)

    def _state(self, item, show=0):
        counts, exact = self._view(item, item.constraints)
        out = {'id': item.pid, 'i-id': item.iid, 'input': item.text, 'words': item.words,
               'total': item.total, 'status': item.status,
               'decisions': [_to_json(c) for c in item.constraints],
               'checked': exact is not None, 'forest': counts.total,
               'tree': None, 'show': 0, 'root': None, 'dmrs': None}
        if exact is None:
            found = item.chains.discriminants(item.constraints, counts)

            def node(pair):
                n, kids = pair
                return {'labels': list(n.labels), 'start': n.start, 'end': n.end,
                        'settled': counts.using[n.id] == counts.total,
                        'children': [node(k) for k in kids]}

            picked = item.chains.pick(counts)
            out.update(remaining=counts.total, tree=node(picked) if picked else None)
        else:
            seen = {}
            for _, sp, _ in exact:
                for p in _props(sp):
                    seen[p] = seen.get(p, 0) + 1
            found = {p: k for p, k in seen.items() if k < len(exact)}
            out['remaining'] = len(exact)
            if exact:
                show = min(max(show, 0), len(exact) - 1)
                tree, _, result = exact[show]
                out.update(show=show, root=result['root'], dmrs=result['dmrs'],
                           tree=_tree_json(tree, lambda p: seen[p] == len(exact)))
        item.remaining = out['remaining']
        out['discriminants'] = [dict(_to_json(c), count=k) for c, k in found.items()]
        return out

    def _remaining(self, item, constraints):
        counts, exact = self._view(item, constraints)
        return counts.total if exact is None else len(exact)

    def _only(self, item, show):
        """Decisions that leave only the tree shown: its chains at the widest
        spans where the remaining trees still differ."""
        _, exact = self._view(item, item.constraints)
        if exact is None or not 0 <= show < len(exact):
            raise ValueError('a single tree can be chosen only among trees the grammar has checked')
        target = exact[show][1]
        left = [sp for _, sp, _ in exact]
        while len(left) > 1:
            for (i, j), labels in sorted(target.items(), key=lambda kv: (kv[0][0] - kv[0][1], kv[0])):
                c = Constraint(CHAIN, i, j, labels)
                kept = [sp for sp in left if satisfies(sp, c)]
                if len(kept) < len(left):
                    item.constraints.append(c)
                    left = kept
                    break

    def act(self, pid, action, constraint=None, show=0):
        """Apply one action to an item and return its new state.
        Actions: decide (with a constraint), only (keep the tree shown), undo,
        reset, accept, reject, reopen."""
        with self.lock:
            item = self.items[pid]
            if action == 'decide':
                c = _from_json(constraint)
                if not self._remaining(item, item.constraints + [c]):
                    raise ValueError('no tree satisfies this decision together with the earlier ones')
                item.constraints.append(c)
                item.status, show = OPEN, 0
            elif action == 'only':
                self._only(item, show)
                item.status, show = OPEN, 0
            elif action == 'undo':
                if item.constraints:
                    item.constraints.pop()
                item.status, show = OPEN, 0
            elif action == 'reset':
                item.constraints, item.status, show = [], OPEN, 0
            elif action == 'accept':
                item.status = ACCEPTED
            elif action == 'reject':
                item.status = REJECTED
            elif action == 'reopen':
                item.status = OPEN
            else:
                raise ValueError(f'unknown action: {action}')
            state = self._state(item, show)
            self._log(item)
            return state
