"""An annotation session over one full-forest profile.

Holds, per item, the decisions made so far and the item's status. Every
change is appended to a journal file at once, and the journal is read back
at startup, so nothing is lost when the server stops.

The journal is Kelp's own record. Writing the standard profile relations
(`tree`, `decision`, `preference`, `result`) is a separate step.
"""
import json
import os
import threading
import time

from delphin import itsdb

from kelp.discriminants import Chains, Constraint
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
        self.words = self._words(forest)

    def _words(self, forest):
        """The text between each pair of neighboring chart vertices."""
        n = max(t.end for t in forest.tokens.values())
        words = ['?'] * n
        for t in forest.tokens.values():
            if t.end == t.start + 1 and words[t.start] == '?':
                words[t.start] = self.text[t.cfrom:t.cto] if t.cfrom >= 0 else t.form
        return words


class Session:
    def __init__(self, profile, journal=None):
        self.profile = profile
        self.journal = journal or os.path.join(profile, 'kelp-journal.jsonl')
        self.lock = threading.Lock()
        ts = itsdb.TestSuite(profile)
        parse = {r['parse-id']: r['i-id'] for r in ts['parse']}
        text = {r['i-id']: r['i-input'] for r in ts['item']}
        self.items = {pid: Item(pid, parse[pid], text[parse[pid]], forest)
                      for pid, forest in sorted(load_forests(profile).items())}
        self._replay_journal()

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
                    item.constraints, item.remaining, item.status = constraints, remaining, rec['status']

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

    def state(self, pid):
        with self.lock:
            return self._state(self.items[pid])

    def _state(self, item):
        counts = item.chains.count(item.constraints)
        found = item.chains.discriminants(item.constraints, counts)

        def node(pair):
            n, kids = pair
            return {'labels': list(n.labels), 'start': n.start, 'end': n.end,
                    'settled': counts.using[n.id] == counts.total,
                    'children': [node(k) for k in kids]}

        picked = item.chains.pick(counts)
        return {'id': item.pid, 'i-id': item.iid, 'input': item.text, 'words': item.words,
                'total': item.total, 'remaining': counts.total, 'status': item.status,
                'decisions': [_to_json(c) for c in item.constraints],
                'discriminants': [dict(_to_json(c), count=k) for c, k in found.items()],
                'tree': node(picked) if picked else None}

    def act(self, pid, action, constraint=None):
        """Apply one action to an item and return its new state.
        Actions: decide (with a constraint), undo, reset, accept, reject, reopen."""
        with self.lock:
            item = self.items[pid]
            if action == 'decide':
                c = _from_json(constraint)
                left = item.chains.count(item.constraints + [c]).total
                if not left:
                    raise ValueError('no tree satisfies this decision together with the earlier ones')
                item.constraints.append(c)
                item.remaining, item.status = left, OPEN
            elif action == 'undo':
                if item.constraints:
                    item.constraints.pop()
                    item.remaining = item.chains.count(item.constraints).total
                item.status = OPEN
            elif action == 'reset':
                item.constraints, item.remaining, item.status = [], item.total, OPEN
            elif action == 'accept':
                item.status = ACCEPTED
            elif action == 'reject':
                item.status = REJECTED
            elif action == 'reopen':
                item.status = OPEN
            else:
                raise ValueError(f'unknown action: {action}')
            self._log(item)
            return self._state(item)
