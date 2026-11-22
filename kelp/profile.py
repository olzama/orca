"""Annotations in the relations of an [incr tsdb()] profile, as FFTB writes them.

    tree        one row per item: t-active is the number of accepted trees,
                0 for a rejected item, -1 for an item not yet annotated
    decision    one row per decision
    preference  one row per accepted tree, pointing to its `result` row
    result      the accepted trees: derivation and MRS

Decision rows:
    d-state  1 yes, 2 no (3 and 4, inferred, are not written and are skipped on reading)
    d-type   2 a lexical type, 3 a rule: present or absent in the chain over the span
             7 the whole chain over the span, labels joined with "@" (FFTB's "twig")
             8 Kelp only: the whole chain, refused (FFTB reads every type 7 row as yes)
             9 Kelp only: the span is a constituent, or is not
             10 Kelp only: a statement about the meaning ('head|ROLE|dependent') holds, or does not
FFTB skips the types it does not know, so it reads a Kelp profile without
the decisions of types 8, 9 and 10.

Only the rows of the item being saved change; all other rows are kept as
they are. Files are replaced atomically.
"""
import os
import tempfile
import time

from delphin import tsdb

from kelp.discriminants import (ABSENT, CHAIN, NOT_CHAIN, NOT_SEM, NOT_SPAN, PRESENT, SEM, SPAN,
                                Constraint)

RELATIONS = ('tree', 'decision', 'preference', 'result')
_DATE = '%d-%m-%Y %H:%M:%S'


def now():
    return time.strftime(_DATE)


def derivation(root, tree):
    """The tree as a derivation string in ACE's --udx form, under its root condition."""
    def quote(text):
        return '"' + text.replace('\\', '\\\\').replace('"', '\\"') + '"'

    def walk(t):
        head = f'(0 {t.label} 0.000000 {t.start} {t.end} '
        if t.lexical:
            form = ' '.join(tok.form for tok in t.tokens)
            toks = ' '.join(f'{tok.id} {quote(tok.avm)}' for tok in t.tokens)
            return head + f'("{form}" {toks}))'
        return head + ' '.join(walk(c) for c in t.children) + ')'

    return f'({root} {walk(tree)})'


def decision_fields(c, lexical):
    """(d-state, d-type, d-key) for a constraint; `lexical` is the set of
    labels that are lexical types."""
    if c.kind in (CHAIN, NOT_CHAIN):
        return (1, 7, '@'.join(c.value)) if c.kind == CHAIN else (2, 8, '@'.join(c.value))
    if c.kind in (SEM, NOT_SEM):
        return (1 if c.kind == SEM else 2, 10, c.value[0])
    if c.kind in (SPAN, NOT_SPAN):
        return (1 if c.kind == SPAN else 2, 9, '')
    return (1 if c.kind == PRESENT else 2, 2 if c.value[0] in lexical else 3, c.value[0])


def constraint_from(state, kind, key, start, end):
    """The constraint of a decision row, or None for a row Kelp does not use."""
    if state not in (1, 2):
        return None
    if kind == 10:
        return Constraint(SEM if state == 1 else NOT_SEM, start, end, (key,))
    key = key.lower()
    if kind == 7:
        return Constraint(CHAIN, start, end, tuple(key.split('@')))
    if kind == 8:
        return Constraint(NOT_CHAIN, start, end, tuple(key.split('@')))
    if kind == 9:
        return Constraint(SPAN if state == 1 else NOT_SPAN, start, end)
    if kind in (2, 3):
        return Constraint(PRESENT if state == 1 else ABSENT, start, end, (key,))
    return None


class Annotations:
    """The four annotation relations of one profile."""

    def __init__(self, profile):
        self.profile = profile
        self.schema = tsdb.read_schema(profile)
        self.lines = {}                 # relation -> {parse-id: [text lines]}
        for rel in RELATIONS:
            col = [f.name for f in self.schema[rel]].index('parse-id')
            by_item = self.lines[rel] = {}
            try:
                with tsdb.open(profile, rel) as f:
                    for line in f:
                        line = line.rstrip('\n')
                        by_item.setdefault(int(tsdb.split(line)[col]), []).append(line)
            except tsdb.TSDBError:
                pass                    # no file yet

    def _records(self, rel, pid):
        names = [f.name for f in self.schema[rel]]
        return [dict(zip(names, tsdb.split(line))) for line in self.lines[rel].get(pid, [])]

    def read(self, pid):
        """(t-active or None, constraints) as stored for one item."""
        active = None
        for rec in self._records('tree', pid):
            active = int(rec['t-active'])
        constraints = []
        for rec in self._records('decision', pid):
            c = constraint_from(int(rec['d-state']), int(rec['d-type']), rec['d-key'] or '',
                                int(rec['d-start']), int(rec['d-end']))
            if c is not None:
                constraints.append(c)
        return active, constraints

    def _line(self, rel, values):
        fields = self.schema[rel]
        return tsdb.join(tsdb.make_record(values, fields), fields)

    def save(self, pid, active, author, start, end, decisions, results):
        """Replace the rows of one item.
        decisions: (d-state, d-type, d-key, d-value, d-start, d-end) each;
        results: (derivation, mrs) of each accepted tree."""
        stamp = now()
        self.lines['tree'][pid] = [self._line('tree', {
            'parse-id': pid, 't-version': 1, 't-active': active, 't-confidence': -1,
            't-author': author, 't-start': start, 't-end': end, 't-comment': ''})]
        self.lines['decision'][pid] = [self._line('decision', {
            'parse-id': pid, 'd-state': s, 'd-type': t, 'd-key': key, 'd-value': value,
            'd-start': i, 'd-end': j, 'd-date': stamp}) for s, t, key, value, i, j in decisions]
        self.lines['preference'][pid] = [self._line('preference', {
            'parse-id': pid, 't-version': 1, 'result-id': k}) for k in range(len(results))]
        self.lines['result'][pid] = [self._line('result', {
            'parse-id': pid, 'result-id': k, 'derivation': d, 'mrs': m}) for k, (d, m) in enumerate(results)]
        for rel in RELATIONS:
            self._write(rel)

    def _write(self, rel):
        path = os.path.join(self.profile, rel)
        fd, tmp = tempfile.mkstemp(prefix=rel + '.', suffix='.tmp', dir=self.profile)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            for pid in sorted(self.lines[rel]):
                for line in self.lines[rel][pid]:
                    f.write(line + '\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        if os.path.exists(path + '.gz'):
            os.remove(path + '.gz')     # the plain file now holds the relation
