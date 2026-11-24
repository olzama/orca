"""O97: distinct readings (scripts/orca_parse.py Parser.distinct_readings, scripts/readings_eval.py)."""
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'scripts'))
sys.path.insert(0, os.path.join(HERE, '..'))

from delphin.codecs import simplemrs  # noqa: E402

import readings_eval as RE  # noqa: E402

DOG = simplemrs.decode('[ TOP: h0 INDEX: e2 RELS: < [ _bark_v_1<4:10> LBL: h1 ARG0: e2 ARG1: x3 ] [ _dog_n_1<0:3> LBL: h4 ARG0: x3 ] > HCONS: < h0 qeq h1 > ]')
CAT = simplemrs.decode('[ TOP: h0 INDEX: e2 RELS: < [ _bark_v_1<4:10> LBL: h1 ARG0: e2 ARG1: x3 ] [ _cat_n_1<0:3> LBL: h4 ARG0: x3 ] > HCONS: < h0 qeq h1 > ]')
FOX = simplemrs.decode('[ TOP: h0 INDEX: e2 RELS: < [ _bark_v_1<4:10> LBL: h1 ARG0: e2 ARG1: x3 ] [ _fox_n_1<0:3> LBL: h4 ARG0: x3 ] > HCONS: < h0 qeq h1 > ]')


def test_select_k_and_margin():
    sc = [5.0, 4.6, 3.0, 2.9]
    assert RE.select(sc) == [0]
    assert RE.select(sc, k=3) == [0, 1, 2]
    assert RE.select(sc, margin=0.5) == [0, 1]
    assert RE.select(sc, k=1, margin=10) == [0]
    assert RE.select([], k=3) == []


def test_group_and_mass():
    from delphin import mrs as M
    same = lambda x, y: bool(M.is_isomorphic(x, y, properties=False))
    rds = RE.group_readings([(1.0, DOG, 'a'), (3.0, CAT, 'b'), (2.0, DOG, 'c')], same)
    assert [rd['score'] for rd in rds] == [3.0, 2.0]          # CAT first, DOG keeps its best score
    assert len(rds[1]['members']) == 2
    probs = RE.softmax_mass(rds)
    z = math.exp(1) + math.exp(3) + math.exp(2)
    assert abs(probs[0] - math.exp(3) / z) < 1e-9 and abs(sum(probs) - 1) < 1e-9


def _stub_parser(readings, margin, mrs_by_tree):
    """A Parser-like object for distinct_readings: replay returns a token; extract maps it to an MRS."""
    import orca_parse
    fake_fast = types.ModuleType('orca.tfs.fast')
    fake_fast.extract = lambda fg, fs: fs
    fake_cmp = types.ModuleType('compare_mrs')
    import compare_mrs as real_cmp
    fake_cmp.normalized = real_cmp.normalized
    fake_cmp.to_pydelphin = lambda x: mrs_by_tree[x]
    obj = types.SimpleNamespace(readings=readings, margin=margin,
                                fg=types.SimpleNamespace(reset=lambda: None, replay_tree=lambda tr, toks: (tr, None)))
    return obj, orca_parse.Parser.distinct_readings, fake_fast, fake_cmp


def _run(readings, margin):
    mrs_by_tree = {'t1': DOG, 't2': DOG, 't3': CAT, 't4': FOX}
    scored = [(5.0, 't1', {}), (4.8, 't2', {}), (4.5, 't3', {}), (1.0, 't4', {})]
    obj, fn, fake_fast, fake_cmp = _stub_parser(readings, margin, mrs_by_tree)
    saved = {k: sys.modules.get(k) for k in ('orca.tfs.fast', 'compare_mrs')}
    sys.modules['orca.tfs.fast'], sys.modules['compare_mrs'] = fake_fast, fake_cmp
    try:
        return fn(obj, scored, [], DOG)
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def test_distinct_readings_k():
    out = _run(readings=3, margin=None)
    assert len(out) == 3                                       # DOG (t1+t2), CAT, FOX
    assert out[0]['maxent score'] == 5.0 and out[1]['maxent score'] == 4.5
    z = sum(math.exp(s - 5.0) for s in (5.0, 4.8, 4.5, 1.0))
    assert abs(out[0]['probability'] - (1 + math.exp(-0.2)) / z) < 1e-9   # both DOG derivations summed


def test_distinct_readings_margin():
    out = _run(readings=5, margin=1.0)
    assert len(out) == 2                                       # FOX is 4.0 below the best
    out = _run(readings=1, margin=1.0)
    assert len(out) == 1


def test_chart_readings_group_select_and_mass():
    """Chart mode (O97): ACE's n best parses grouped by MRS, scored by the best parse, softmax mass summed per reading."""
    import orca_parse
    enc = lambda m: simplemrs.encode(m)
    parses = [(5.0, enc(DOG), 'd1'), (4.8, enc(DOG), 'd2'), (4.5, enc(CAT), 'd3'), (1.0, enc(FOX), 'd4')]
    obj = types.SimpleNamespace(readings=3, margin=None)
    out = orca_parse.Parser.chart_readings(obj, parses)
    assert [r['maxent score'] for r in out] == [5.0, 4.5, 1.0]
    assert out[0]['_ace_derivation'] == 'd1'                    # the reading's best parse
    z = sum(math.exp(s - 5.0) for s in (5.0, 4.8, 4.5, 1.0))
    assert abs(out[0]['probability'] - (1 + math.exp(-0.2)) / z) < 1e-9
    obj = types.SimpleNamespace(readings=5, margin=1.0)
    assert len(orca_parse.Parser.chart_readings(obj, parses)) == 2   # FOX is 4.0 below the best
    obj = types.SimpleNamespace(readings=1, margin=None)
    assert len(orca_parse.Parser.chart_readings(obj, parses)) == 1


def test_strip_private():
    import orca_parse
    r = {'mrs': 'x', '_tokens': [1], 'readings': [{'probability': 0.5, '_tree': object(), '_mrs_obj': object(), '_ace_derivation': 'd'}]}
    orca_parse.strip_private(r)
    assert '_tokens' not in r and r['readings'] == [{'probability': 0.5}]
