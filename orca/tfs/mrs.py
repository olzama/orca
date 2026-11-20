"""Reading Minimal Recursion Semantics off a replayed feature structure.

After replay, the semantics is in the sign: the hook, the list of
elementary predications and the handle constraints. Variables are nodes;
two arguments are the same variable when they are the same node.
"""
from .dag import deref

SORTS = (('h', 'handle'), ('e', 'event'), ('x', 'ref-ind'), ('i', 'individual'), ('p', 'non_event'))
ROLES_FIRST = ('LBL', 'ARG0', 'ARG1', 'ARG2', 'ARG3', 'ARG4', 'RSTR', 'BODY', 'L-INDEX', 'R-INDEX',
               'L-HNDL', 'R-HNDL', 'CARG')
SKIP = {'PRED', 'CFROM', 'CTO', 'LNK', 'WLINK', 'PARAMS', 'IDIOMP', '--PSV'}


def extract(grammar, fs):
    """Return {'top', 'index', 'rels': [(pred, {role: value})], 'hcons': [(hi, rel, lo)]}."""
    u, h = grammar.u, grammar.h
    names = {}

    def sort(t):
        for letter, name in SORTS:
            if name in h.code and t in h.code and h.subsumes(name, t):
                return letter
        return 'u'

    def var(n):
        n = deref(n)
        if n.type.startswith('"'):
            return n.type
        if id(n) not in names:
            names[id(n)] = f'{sort(n.type)}{len(names) + 1}'
        return names[id(n)]

    def items(lst):
        cur, last = u.get(lst, 'LIST'), u.get(lst, 'LAST')
        while deref(cur) is not deref(last) and 'FIRST' in deref(cur).arcs:
            yield deref(deref(cur).arcs['FIRST'])
            cur = deref(cur).arcs['REST']

    cont = u.get(fs, 'SYNSEM', 'LOCAL', 'CONT')
    out = {'top': var(u.get(cont, 'HOOK', 'LTOP')), 'index': var(u.get(cont, 'HOOK', 'INDEX')),
           'rels': [], 'hcons': []}
    for ep in items(u.get(cont, 'RELS')):
        pred = deref(ep.arcs['PRED']).type if 'PRED' in ep.arcs else ep.type
        pred = pred.strip('"')
        pred = pred[:-4] if pred.endswith('_rel') else pred
        roles = [r for r in ROLES_FIRST if r in ep.arcs] + sorted(
            r for r in ep.arcs if r not in ROLES_FIRST and r not in SKIP)
        out['rels'].append((pred, {r: var(ep.arcs[r]) for r in roles}))
    for q in items(u.get(cont, 'HCONS')):
        out['hcons'].append((var(q.arcs['HARG']), q.type, var(q.arcs['LARG'])))
    return out


def to_text(mrs):
    lines = [f"TOP {mrs['top']}  INDEX {mrs['index']}"]
    for pred, roles in mrs['rels']:
        args = ', '.join(f'{r} {v}' for r, v in roles.items() if r != 'LBL')
        lines.append(f"  {roles.get('LBL', '?')}:{pred}({args})")
    lines.append('  ' + ', '.join(f'{a} {rel} {b}' for a, rel, b in mrs['hcons']))
    return '\n'.join(lines)
