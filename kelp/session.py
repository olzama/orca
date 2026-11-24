"""An annotation session over one full-forest profile.

Holds, per item, the decisions made so far and the item's status. Every
change is appended to a journal file at once, and the journal is read back
at startup, so nothing is lost when the server stops.

The journal is Kelp's own record and works without a grammar. With a
grammar, every change is also written to the profile's own relations
(`tree`, `decision`, `preference`, `result`; see kelp.profile), and what
those relations hold is read at startup.

With a grammar, the session works in two modes. While an item has more
remaining trees than `limit`, it counts on the packed forest, which also
holds trees that the grammar does not license. At or below the limit it
unpacks the remaining trees, has Orca check each one, and from then on works
with the licensed trees only, each with its meaning.
"""
import collections
import getpass
import json
import os
import threading
import time

from delphin import itsdb

from kelp.discriminants import CHAIN, NOT_SEM, PRESENT, SEM, SPAN, Chains, Constraint, spans
from kelp.forest import load_forests
from kelp.profile import Annotations, decision_fields, derivation, now

ACCEPTED, REJECTED, OPEN = 'accepted', 'rejected', ''


def _to_json(c):
    return {'kind': c.kind, 'start': c.start, 'end': c.end, 'value': list(c.value)}


def _from_json(d):
    return Constraint(d['kind'], int(d['start']), int(d['end']), tuple(d.get('value', ())))


class Item:
    def __init__(self, pid, iid, text, forest, lexlabel):
        self.pid, self.iid, self.text = pid, iid, text
        self.chains = Chains(forest, lexlabel)
        self.lexical = {n.labels[-1] for n in self.chains.nodes if n.tokens}   # labels of lexical entries
        self.started = None         # when the annotator first changed the item
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


def _leaves(tree):
    if tree.lexical:
        yield tree
    for c in tree.children:
        yield from _leaves(c)


def _props(tree_spans):
    """The properties of one tree that can be discriminants."""
    for (i, j), labels in tree_spans.items():
        yield Constraint(SPAN, i, j)
        yield Constraint(CHAIN, i, j, labels)
        for label in set(labels):
            yield Constraint(PRESENT, i, j, (label,))


def _tree_json(t, settled, lexlabel):
    labels, top = [], t
    while len(t.children) == 1:
        labels.append(t.label)
        t = t.children[0]
    labels.append(lexlabel(t.label) if t.lexical else t.label)
    return {'labels': labels, 'start': top.start, 'end': top.end,
            'entry': t.label if t.lexical else None,
            'settled': settled(Constraint(CHAIN, top.start, top.end, tuple(labels))),
            'children': [_tree_json(c, settled, lexlabel) for c in t.children]}


class Session:
    def __init__(self, profile, journal=None, engine=None, limit=150, lextypes=None, author=None,
                 pred_entries=None, explain=None):
        """lextypes: {lexical entry name: lexical type}. With it, entries appear
        in chains under their type, as in FFTB's decisions.
        pred_entries: {predicate: [names of the lexical entries that have it]},
        to show which entry of a tree a predicate comes from.
        explain: a function from a prompt to {reading number: explanation}."""
        self.pred_entries = pred_entries or {}
        self.explain, self.explained = explain, {}
        self.profile = profile
        self.journal = journal or os.path.join(profile, 'kelp-journal.jsonl')
        self.engine, self.limit = engine, limit
        self.budget = 0.5           # seconds of grammar checking inside one request
        self.current = None         # the item last opened
        self.author = author or getpass.getuser()
        lextypes = lextypes or {}
        self.lexlabel = lambda name: lextypes.get(name.lower(), name)
        self.typedocs = {}          # lexical type -> the grammar's note on it
        self.store = Annotations(profile) if engine else None
        self.lock = threading.Lock()
        ts = itsdb.TestSuite(profile)
        parse = {r['parse-id']: r['i-id'] for r in ts['parse']}
        text = {r['i-id']: r['i-input'] for r in ts['item']}
        self.items = {pid: Item(pid, parse[pid], text[parse[pid]], forest, self.lexlabel)
                      for pid, forest in sorted(load_forests(profile).items())}
        if self.store:
            self._read_profile()
        self._replay_journal()

    def _read_profile(self):
        for item in self.items.values():
            active, constraints = self.store.read(item.pid)
            if active is None:
                continue
            remaining = item.chains.count(constraints).total
            if remaining:                   # decisions that no longer fit the forest are skipped
                item.constraints, item.remaining = constraints, remaining
                item.status = ACCEPTED if active > 0 else REJECTED if active == 0 else OPEN

    def _save(self, item, exact):
        """Write the item to the profile's relations."""
        words = lambda c: ' '.join(item.words[c.start:c.end])
        decisions = [decision_fields(c, item.lexical) + (words(c), c.start, c.end) for c in item.constraints]
        results = []
        if item.status == ACCEPTED:
            results = [(derivation(r['root'], t), r['mrs']) for t, _, r in exact]
        active = len(results) if item.status == ACCEPTED else 0 if item.status == REJECTED else -1
        self.store.save(item.pid, active, self.author, item.started or now(), now(), decisions, results)

    def check_ahead(self):
        """Check trees with the grammar, one at a time, so that a request never
        waits long: first those of the item last opened, then those of every
        other item that is small enough. Runs for good; meant for a background thread."""
        order, ahead = iter(list(self.items.values())), None
        while True:
            with self.lock:
                item = self.items.get(self.current)
                busy = item is not None and self._check_one(item)
                while not busy:
                    if ahead is None:
                        ahead = next(order, None)
                    if ahead is None:
                        break
                    busy = self._check_one(ahead)
                    if not busy:
                        ahead = None
            if not busy:
                time.sleep(0.5)

    def _check_one(self, item):
        """Check one unchecked remaining tree of the item; False when there is none."""
        if item.chains.count(item.constraints).total > self.limit:
            return False
        licensed = 0
        for t in item.chains.trees(item.constraints):
            key = t.key()
            if key not in item.checked:
                item.checked[key] = self.engine.check(t)
                return True
            licensed += item.checked[key] is not None
        item.remaining = licensed
        return False

    def _view(self, item, constraints, wait=False):
        """The forest counts and, when few enough trees remain and there is an
        engine, the remaining trees as (tree, spans, engine result). Trees the
        grammar does not license are left out. A tree it has not checked yet
        has None as its result: only `budget` seconds are spent on checking
        here, unless `wait` is set."""
        counts = item.chains.count(constraints)
        if self.engine is None or counts.total > self.limit:
            return counts, None
        exact, start, first = [], time.time(), True
        sem = [c for c in constraints if c.kind in (SEM, NOT_SEM)]
        for t in item.chains.trees(constraints):
            key = t.key()
            if key not in item.checked and (wait or first or time.time() - start < self.budget):
                item.checked[key] = self.engine.check(t)
                first = False
            if key not in item.checked:
                exact.append((t, spans(t, self.lexlabel), None))
            elif item.checked[key] is not None:
                deps = item.checked[key].get('deps', ())
                if all((c.value[0] in deps) == (c.kind == SEM) for c in sem):
                    exact.append((t, spans(t, self.lexlabel), item.checked[key]))
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
            self.current = pid
            return self._state(self.items[pid], show)

    def _state(self, item, show=0):
        counts, exact = self._view(item, item.constraints)
        out = {'id': item.pid, 'i-id': item.iid, 'input': item.text, 'words': item.words,
               'total': item.total, 'status': item.status,
               'decisions': [_to_json(c) for c in item.constraints],
               'checked': exact is not None, 'forest': counts.total,
               'tree': None, 'show': 0, 'root': None, 'dmrs': None, 'trees': [], 'pending': 0,
               'limit': self.limit}
        if exact is None:
            found = item.chains.discriminants(item.constraints, counts)

            def node(pair):
                n, kids = pair
                return {'labels': list(n.labels), 'start': n.start, 'end': n.end,
                        'entry': n.chain[-1] if n.tokens else None,
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
            out['pending'] = sum(r is None for _, _, r in exact)
            if exact:
                show = min(max(show, 0), len(exact) - 1)
                out['trees'] = [{'tree': _tree_json(t, lambda p: seen[p] == len(exact), self.lexlabel),
                                 'root': r and r['root'], 'dmrs': r and r['dmrs'], 'unchecked': r is None,
                                 'deps': r.get('deps', []) if r else [],
                                 'entries': self._entries(t, r)} for t, _, r in exact]
                out.update(out['trees'][show], show=show)
        item.remaining = out['remaining']
        out['discriminants'] = [dict(_to_json(c), count=k) for c, k in found.items()]
        if exact:                           # statements about the meaning that some checked trees make
            known = [r for _, _, r in exact if r]
            said = collections.Counter(d for r in known for d in set(r.get('deps', ())))
            out['discriminants'] += [{'kind': SEM, 'start': 0, 'end': 0, 'value': [d], 'count': k}
                                     for d, k in said.items() if k < len(known)]
        return out

    def _entries(self, tree, result):
        """{predicate: [the lexical entries of this tree that have it]}"""
        if not result or not result.get('dmrs'):
            return {}
        mine, out = {leaf.label.lower() for leaf in _leaves(tree)}, {}
        for n in result['dmrs']['nodes']:
            names = [e for e in self.pred_entries.get(n['pred'].lower(), ()) if e in mine]
            if names:
                out[n['pred']] = names
        return out

    def _reading(self, item, show):
        """Decisions about the meaning that leave the trees with the meaning of
        the tree shown: first what it says and other trees do not, then what
        others say and it does not, each only while it removes trees."""
        _, exact = self._view(item, item.constraints)
        if exact is None or not 0 <= show < len(exact) or exact[show][2] is None:
            raise ValueError('a reading can be chosen only once the grammar has checked its tree')
        known = [set(r.get('deps', ())) for _, _, r in exact if r]
        mine = set(exact[show][2].get('deps', ()))
        every = set().union(*known)
        left = [k for k in known]
        for kind, pool in ((SEM, sorted(mine)), (NOT_SEM, sorted(every - mine))):
            for d in pool:
                kept = [k for k in left if (d in k) == (kind == SEM)]
                if len(kept) < len(left):
                    item.constraints.append(Constraint(kind, 0, 0, (d,)))
                    left = kept

    def explain_readings(self, pid, shows):
        """Plain-English explanations for the trees with the given numbers, each
        standing for one reading: {tree number: text}. Asks the model once
        per set of readings."""
        from kelp import explain as X
        if self.explain is None:
            raise ValueError('this server has no model for explanations (see --explain)')
        with self.lock:
            item = self.items[pid]
            _, exact = self._view(item, item.constraints)
            if exact is None:
                raise ValueError('readings can be explained only once the trees are listed')
            picked = [(i, exact[i]) for i in shows if 0 <= i < len(exact) and exact[i][2] and exact[i][2].get('dmrs')]
            if len(picked) < 2:
                raise ValueError('there is nothing to compare')
            if len(picked) > 8:
                raise ValueError('at most 8 readings can be explained at once: narrow the item down first')
            words = {}
            for i, (t, _, _) in picked:
                for leaf in _leaves(t):
                    words.setdefault((leaf.start, leaf.end), {})[i] = leaf.label
            differ = {sp for sp, by in words.items() if len(by) < len(picked) or len(set(by.values())) > 1}
            readings = []
            for (i, (t, _, r)), fs in zip(picked, X.distinguishing([r['dmrs'] for _, (_, _, r) in picked])):
                notes = []
                for leaf in _leaves(t):
                    if (leaf.start, leaf.end) in differ:
                        ltype = self.lexlabel(leaf.label)
                        notes.append(f'"{" ".join(item.words[leaf.start:leaf.end])}": lexical entry {leaf.label}, type {ltype}'
                                     + (f' ({self.typedocs[ltype.lower()]})' if self.typedocs.get(ltype.lower()) else ''))
                readings.append((i + 1, fs, notes))
            text = X.prompt(item.text, readings)
        if text not in self.explained:              # the model is asked outside the lock
            answer = self.explain(text)
            self.explained[text] = {int(k) - 1: v for k, v in answer.items() if str(k).isdigit()}
        return {'explanations': self.explained[text]}

    def _remaining(self, item, constraints):
        counts, exact = self._view(item, constraints)
        return counts.total if exact is None else len(exact)

    def _only(self, item, show):
        """Decisions that leave only the tree shown."""
        _, exact = self._view(item, item.constraints)
        if exact is None or not 0 <= show < len(exact):
            raise ValueError('a single tree can be chosen only once the trees are listed')
        self._choose(item, exact[show][1])

    def _choose(self, item, target):
        """Decisions that leave the trees with the chains of `target`
        ({span: chain}): its chains at the widest spans where the remaining
        trees still differ. More than one tree is left when trees differ only
        in lexical entries of one type."""
        left = self._remaining(item, item.constraints)
        for (i, j), labels in sorted(target.items(), key=lambda kv: (kv[0][0] - kv[0][1], kv[0])):
            if left <= 1:
                break
            c = Constraint(CHAIN, i, j, tuple(labels))
            kept = self._remaining(item, item.constraints + [c])
            if not kept:
                raise ValueError('the forest has no such tree')
            if kept < left:
                item.constraints.append(c)
                left = kept

    def choose(self, pid, target):
        """Narrow an item down to the tree with the given chains, and return its new state."""
        with self.lock:
            item = self.items[pid]
            item.started = item.started or now()
            self._choose(item, target)
            item.status = OPEN
            return self._finish(item, 0)

    def _finish(self, item, show):
        state = self._state(item, show)
        self._log(item)
        if self.store:
            _, exact = self._view(item, item.constraints, wait=item.status == ACCEPTED)
            self._save(item, exact)
        return state

    def act(self, pid, action, constraint=None, show=0):
        """Apply one action to an item and return its new state.
        Actions: decide (with a constraint), only (keep the tree shown),
        reading (keep the trees that mean what the tree shown means), undo,
        reset, accept, reject, reopen."""
        with self.lock:
            item = self.items[pid]
            item.started = item.started or now()
            if action == 'decide':
                c = _from_json(constraint)
                if not self._remaining(item, item.constraints + [c]):
                    raise ValueError('no tree satisfies this decision together with the earlier ones')
                item.constraints.append(c)
                item.status, show = OPEN, 0
            elif action == 'only':
                self._only(item, show)
                item.status, show = OPEN, 0
            elif action == 'reading':
                self._reading(item, show)
                item.status, show = OPEN, 0
            elif action == 'undo':
                if item.constraints:
                    item.constraints.pop()
                item.status, show = OPEN, 0
            elif action == 'reset':
                item.constraints, item.status, show = [], OPEN, 0
            elif action == 'accept':
                if self.engine:
                    _, exact = self._view(item, item.constraints)
                    if exact is None:
                        raise ValueError(f'too many trees remain to accept: decide until at most {self.limit} are left')
                    if sum(r is None for _, _, r in exact) > 20:
                        raise ValueError('the grammar is still checking the remaining trees: try again in a moment')
                    _, exact = self._view(item, item.constraints, wait=True)
                    if not exact:
                        raise ValueError('the grammar licenses none of the remaining trees: reject the item instead')
                item.status = ACCEPTED
            elif action == 'reject':
                item.status = REJECTED
            elif action == 'reopen':
                item.status = OPEN
            else:
                raise ValueError(f'unknown action: {action}')
            return self._finish(item, show)
