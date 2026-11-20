/*
 * Compiled core of the replay engine: typed feature structures in a flat
 * arena, destructive unification with an undo trail, lazy expansion of type
 * constraints and run-time type inference. Mirrors orca/tfs/dag.py.
 *
 * Types and features are small integers assigned on the Python side.
 * Greatest lower bounds and type constraints are asked from Python the
 * first time they are needed and cached here. Stored structures (rules,
 * lexical entries, type constraints, tokens) are registered as flat
 * templates and copied into the arena in one pass.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdint.h>
#include <string.h>

typedef struct { int32_t feat, val; } Arc;
typedef struct {
    int32_t type, fwd, narcs, cap;
    int64_t off;            /* start of this node's arcs in the arc pool */
    int32_t copy_gen, copy_to;
    uint8_t expanded;
} Rec;

typedef struct { int32_t n; int32_t *types; uint8_t *exp; int32_t *start; int32_t *feat; int32_t *target; } Tpl;
typedef struct { int8_t kind; int32_t node; int64_t old; } Trail;

static Rec *nodes; static int64_t nn, ncap;
static Arc *pool; static int64_t np, pcap;
static Trail *trail; static int64_t nt, tcap;
static Tpl *tpls; static int32_t ntpl, tplcap;
static int32_t *cons_tpl; static int32_t ncons;          /* type -> template, -1 none, -2 unknown */
static int64_t *gkey; static int32_t *gval; static int64_t gcap, gfill;   /* glb cache */
static PyObject *glb_cb, *cons_cb;
static int32_t copy_gen = 0;
static int64_t n_unify = 0;

/* failure report */
static int32_t fail_path[4096]; static int fail_len; static int32_t fail_a, fail_b; static int fail_kind;
/* fail_kind: 1 = type clash, 2 = missing feature, 3 = Python error */
static int32_t path[4096]; static int plen;

static int grow(void **p, int64_t *cap, int64_t need, size_t size) {
    if (need <= *cap) return 0;
    int64_t c = *cap ? *cap : 1024;
    while (c < need) c *= 2;
    void *q = realloc(*p, c * size);
    if (!q) { PyErr_NoMemory(); return -1; }
    *p = q; *cap = c; return 0;
}

static inline int32_t deref(int32_t n) { while (nodes[n].fwd >= 0) n = nodes[n].fwd; return n; }

static int32_t new_node(int32_t type, uint8_t exp, int32_t cap) {
    if (grow((void **)&nodes, &ncap, nn + 1, sizeof(Rec)) < 0) return -1;
    if (grow((void **)&pool, &pcap, np + cap, sizeof(Arc)) < 0) return -1;
    Rec *r = &nodes[nn];
    r->type = type; r->fwd = -1; r->narcs = 0; r->cap = cap; r->off = np; r->copy_gen = 0; r->expanded = exp;
    np += cap;
    return (int32_t)nn++;
}

static int push_trail(int8_t kind, int32_t node, int64_t old) {
    if (grow((void **)&trail, &tcap, nt + 1, sizeof(Trail)) < 0) return -1;
    trail[nt].kind = kind; trail[nt].node = node; trail[nt].old = old; nt++;
    return 0;
}

static inline int32_t find(int32_t n, int32_t f) {
    Rec *r = &nodes[n]; Arc *a = pool + r->off;
    for (int32_t i = 0; i < r->narcs; i++) if (a[i].feat == f) return a[i].val;
    return -1;
}

static int add_arc(int32_t n, int32_t f, int32_t v, int trailed) {
    Rec *r = &nodes[n];
    if (r->narcs == r->cap) {
        int32_t c = r->cap ? r->cap * 2 : 4;
        if (grow((void **)&pool, &pcap, np + c, sizeof(Arc)) < 0) return -1;
        r = &nodes[n];
        memcpy(pool + np, pool + r->off, r->narcs * sizeof(Arc));
        r->off = np; r->cap = c; np += c;
    }
    pool[r->off + r->narcs].feat = f; pool[r->off + r->narcs].val = v; r->narcs++;
    if (trailed) return push_trail('a', n, f);
    return 0;
}

/* ---- greatest lower bounds ---- */
static int32_t glb(int32_t a, int32_t b) {
    if (a == b) return a;
    int64_t key = ((int64_t)a << 32) | (uint32_t)b;
    if (gcap) {
        int64_t i = (uint64_t)(key * 0x9E3779B97F4A7C15ULL) & (gcap - 1);
        while (gkey[i] != -1) { if (gkey[i] == key) return gval[i]; i = (i + 1) & (gcap - 1); }
    }
    PyObject *res = PyObject_CallFunction(glb_cb, "ii", a, b);
    if (!res) { fail_kind = 3; return -2; }
    int32_t t = (int32_t)PyLong_AsLong(res); Py_DECREF(res);
    if (gfill * 2 >= gcap) {
        int64_t oc = gcap, c = gcap ? gcap * 2 : 1 << 16;
        int64_t *ok = gkey; int32_t *ov = gval;
        gkey = malloc(c * sizeof(int64_t)); gval = malloc(c * sizeof(int32_t));
        for (int64_t i = 0; i < c; i++) gkey[i] = -1;
        gcap = c; gfill = 0;
        for (int64_t i = 0; i < oc; i++) if (ok[i] != -1) {
            int64_t j = (uint64_t)(ok[i] * 0x9E3779B97F4A7C15ULL) & (gcap - 1);
            while (gkey[j] != -1) j = (j + 1) & (gcap - 1);
            gkey[j] = ok[i]; gval[j] = ov[i]; gfill++;
        }
        free(ok); free(ov);
    }
    int64_t i = (uint64_t)(key * 0x9E3779B97F4A7C15ULL) & (gcap - 1);
    while (gkey[i] != -1) i = (i + 1) & (gcap - 1);
    gkey[i] = key; gval[i] = t; gfill++;
    return t;
}

/* ---- templates ---- */
static int32_t copy_tpl(int32_t id) {
    Tpl *t = &tpls[id];
    int64_t base = nn;
    if (grow((void **)&nodes, &ncap, nn + t->n, sizeof(Rec)) < 0) return -1;
    int64_t narcs = t->start[t->n];
    if (grow((void **)&pool, &pcap, np + narcs, sizeof(Arc)) < 0) return -1;
    for (int32_t i = 0; i < t->n; i++) {
        Rec *r = &nodes[base + i];
        int32_t k = t->start[i + 1] - t->start[i];
        r->type = t->types[i]; r->fwd = -1; r->narcs = k; r->cap = k; r->off = np + t->start[i];
        r->copy_gen = 0; r->expanded = t->exp[i];
    }
    for (int64_t j = 0; j < narcs; j++) { pool[np + j].feat = t->feat[j]; pool[np + j].val = (int32_t)(base + t->target[j]); }
    np += narcs; nn += t->n;
    return (int32_t)base;
}

static int32_t constraint(int32_t type) {
    if (type < ncons && cons_tpl[type] != -2) return cons_tpl[type];
    PyObject *res = PyObject_CallFunction(cons_cb, "i", type);
    if (!res) { fail_kind = 3; return -3; }
    int32_t t = (int32_t)PyLong_AsLong(res); Py_DECREF(res);
    if (type >= ncons) {
        int32_t c = ncons ? ncons : 1024;
        while (c <= type) c *= 2;
        cons_tpl = realloc(cons_tpl, c * sizeof(int32_t));
        for (int32_t i = ncons; i < c; i++) cons_tpl[i] = -2;
        ncons = c;
    }
    cons_tpl[type] = t;
    return t;
}

/* ---- unification ---- */
static int32_t merge(int32_t a, int32_t b);

static void fail(int32_t ta, int32_t tb, int kind) {
    if (fail_kind) return;
    fail_kind = kind; fail_a = ta; fail_b = tb;
    fail_len = plen; memcpy(fail_path, path, plen * sizeof(int32_t));
}

static int32_t expand(int32_t n) {
    n = deref(n);
    if (nodes[n].expanded) return n;
    if (push_trail('e', n, 0) < 0) return -1;
    nodes[n].expanded = 1;
    int32_t c = constraint(nodes[n].type);
    if (c == -3) return -1;
    if (c >= 0) {
        int32_t cp = copy_tpl(c);
        if (cp < 0 || merge(n, cp) < 0) return -1;
    }
    return deref(n);
}

static int32_t merge(int32_t a, int32_t b) {
    a = deref(a); b = deref(b);
    if (a == b) return a;
    n_unify++;
    int32_t t = glb(nodes[a].type, nodes[b].type);
    if (t == -2) return -1;
    if (t < 0) { fail(nodes[a].type, nodes[b].type, 1); return -1; }
    uint8_t ae = nodes[a].expanded, be = nodes[b].expanded;
    if (!ae && !be) {
        if (push_trail('f', b, 0) < 0) return -1;
        nodes[b].fwd = a;
        if (nodes[a].type != t) { if (push_trail('t', a, nodes[a].type) < 0) return -1; nodes[a].type = t; }
        return a;
    }
    if (!ae) { int32_t x = a; a = b; b = x; uint8_t y = ae; ae = be; be = y; }
    int new_type = t != nodes[a].type && !(be && t == nodes[b].type);
    if (push_trail('f', b, 0) < 0) return -1;
    nodes[b].fwd = a;
    if (nodes[a].type != t) { if (push_trail('t', a, nodes[a].type) < 0) return -1; nodes[a].type = t; }
    if (be) {
        int32_t k = nodes[b].narcs;
        for (int32_t i = 0; i < k; i++) {
            Arc arc = pool[nodes[b].off + i];
            int32_t mine = find(a, arc.feat);
            if (mine < 0) {
                if (add_arc(a, arc.feat, arc.val, 1) < 0) return -1;
            } else {
                if (plen >= 4096) { fail(0, 0, 2); return -1; }
                path[plen++] = arc.feat;
                if (merge(mine, arc.val) < 0) { plen--; return -1; }
                plen--;
            }
        }
    }
    if (new_type) {
        int32_t c = constraint(t);
        if (c == -3) return -1;
        if (c >= 0) {
            int32_t cp = copy_tpl(c);
            if (cp < 0 || merge(a, cp) < 0) return -1;
        }
    }
    return deref(a);
}

static void undo_to(int64_t mark) {
    while (nt > mark) {
        Trail *e = &trail[--nt];
        switch (e->kind) {
        case 't': nodes[e->node].type = (int32_t)e->old; break;
        case 'f': nodes[e->node].fwd = -1; break;
        case 'e': nodes[e->node].expanded = 0; break;
        case 'a': nodes[e->node].narcs--; break;
        }
    }
}

/* copy of a live structure (for snapshots) */
static int32_t copy_live(int32_t n) {
    n = deref(n);
    if (nodes[n].copy_gen == copy_gen) return nodes[n].copy_to;
    int32_t k = nodes[n].narcs;
    int32_t m = new_node(nodes[n].type, nodes[n].expanded, k);
    if (m < 0) return -1;
    nodes[n].copy_gen = copy_gen; nodes[n].copy_to = m;
    for (int32_t i = 0; i < k; i++) {
        Arc arc = pool[nodes[n].off + i];
        int32_t v = copy_live(arc.val);
        if (v < 0) return -1;
        pool[nodes[m].off + i].feat = arc.feat; pool[nodes[m].off + i].val = v;
    }
    nodes[m].narcs = k;
    return m;
}

/* ---- Python interface ---- */
static PyObject *failure_or_error(void) {
    if (fail_kind == 3 || PyErr_Occurred()) return NULL;
    PyObject *p = PyList_New(fail_len);
    for (int i = 0; i < fail_len; i++) PyList_SET_ITEM(p, i, PyLong_FromLong(fail_path[i]));
    PyObject *res = Py_BuildValue("(iNii)", fail_kind, p, fail_a, fail_b);
    return res;
}

static int start_path(PyObject *prefix) {
    plen = 0; fail_kind = 0;
    if (!prefix || prefix == Py_None) return 0;
    Py_ssize_t k = PySequence_Size(prefix);
    for (Py_ssize_t i = 0; i < k && plen < 4096; i++) {
        PyObject *x = PySequence_GetItem(prefix, i);
        path[plen++] = (int32_t)PyLong_AsLong(x); Py_DECREF(x);
    }
    return 0;
}

static PyObject *py_init(PyObject *self, PyObject *args) {
    PyObject *g, *c;
    if (!PyArg_ParseTuple(args, "OO", &g, &c)) return NULL;
    Py_XDECREF(glb_cb); Py_XDECREF(cons_cb);
    Py_INCREF(g); Py_INCREF(c); glb_cb = g; cons_cb = c;
    Py_RETURN_NONE;
}

static PyObject *py_add_template(PyObject *self, PyObject *args) {
    PyObject *types, *exp, *start, *feat, *target;
    if (!PyArg_ParseTuple(args, "OOOOO", &types, &exp, &start, &feat, &target)) return NULL;
    if (ntpl == tplcap) { tplcap = tplcap ? tplcap * 2 : 1024; tpls = realloc(tpls, tplcap * sizeof(Tpl)); }
    Tpl *t = &tpls[ntpl];
    Py_ssize_t n = PySequence_Size(types), m = PySequence_Size(feat);
    t->n = (int32_t)n;
    t->types = malloc(n * sizeof(int32_t)); t->exp = malloc(n); t->start = malloc((n + 1) * sizeof(int32_t));
    t->feat = malloc((m ? m : 1) * sizeof(int32_t)); t->target = malloc((m ? m : 1) * sizeof(int32_t));
    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *x = PySequence_GetItem(types, i); t->types[i] = (int32_t)PyLong_AsLong(x); Py_DECREF(x);
        x = PySequence_GetItem(exp, i); t->exp[i] = (uint8_t)PyObject_IsTrue(x); Py_DECREF(x);
    }
    for (Py_ssize_t i = 0; i <= n; i++) { PyObject *x = PySequence_GetItem(start, i); t->start[i] = (int32_t)PyLong_AsLong(x); Py_DECREF(x); }
    for (Py_ssize_t i = 0; i < m; i++) {
        PyObject *x = PySequence_GetItem(feat, i); t->feat[i] = (int32_t)PyLong_AsLong(x); Py_DECREF(x);
        x = PySequence_GetItem(target, i); t->target[i] = (int32_t)PyLong_AsLong(x); Py_DECREF(x);
    }
    if (PyErr_Occurred()) return NULL;
    return PyLong_FromLong(ntpl++);
}

static PyObject *py_copy_template(PyObject *self, PyObject *args) {
    int id; if (!PyArg_ParseTuple(args, "i", &id)) return NULL;
    int32_t r = copy_tpl(id); if (r < 0) return NULL;
    return PyLong_FromLong(r);
}

static PyObject *py_new_node(PyObject *self, PyObject *args) {
    int type, exp = 0; if (!PyArg_ParseTuple(args, "i|p", &type, &exp)) return NULL;
    int32_t r = new_node(type, (uint8_t)exp, 2); if (r < 0) return NULL;
    return PyLong_FromLong(r);
}

static PyObject *py_set_arc(PyObject *self, PyObject *args) {
    int n, f, v; if (!PyArg_ParseTuple(args, "iii", &n, &f, &v)) return NULL;
    if (add_arc(n, f, v, 0) < 0) return NULL;
    Py_RETURN_NONE;
}

static PyObject *py_del_arc(PyObject *self, PyObject *args) {
    int n, f; if (!PyArg_ParseTuple(args, "ii", &n, &f)) return NULL;
    n = deref(n);
    Rec *r = &nodes[n]; Arc *a = pool + r->off;
    for (int32_t i = 0; i < r->narcs; i++) if (a[i].feat == f) {
        memmove(a + i, a + i + 1, (r->narcs - i - 1) * sizeof(Arc)); r->narcs--; break;
    }
    Py_RETURN_NONE;
}

/* unify(a, b, path_prefix) -> node, or a failure tuple (kind, path, type_a, type_b) */
static PyObject *py_unify(PyObject *self, PyObject *args) {
    int a, b; PyObject *prefix = NULL;
    if (!PyArg_ParseTuple(args, "ii|O", &a, &b, &prefix)) return NULL;
    start_path(prefix);
    int32_t r = merge(a, b);
    if (r < 0) return failure_or_error();
    return PyLong_FromLong(r);
}

/* get(node, feats, path_prefix) -> node, or a failure tuple */
static PyObject *py_get(PyObject *self, PyObject *args) {
    int n; PyObject *feats, *prefix = NULL;
    if (!PyArg_ParseTuple(args, "iO|O", &n, &feats, &prefix)) return NULL;
    start_path(prefix);
    Py_ssize_t k = PySequence_Size(feats);
    for (Py_ssize_t i = 0; i < k; i++) {
        PyObject *x = PySequence_GetItem(feats, i); int32_t f = (int32_t)PyLong_AsLong(x); Py_DECREF(x);
        n = deref(n);
        int32_t v = find(n, f);
        if (v < 0) {
            n = expand(n);
            if (n < 0) return failure_or_error();
            v = find(n, f);
            if (v < 0) { fail_kind = 0; path[plen] = f; plen++; fail(nodes[n].type, f, 2); return failure_or_error(); }
        }
        n = v;
    }
    return PyLong_FromLong(deref(n));
}

static PyObject *py_expand(PyObject *self, PyObject *args) {
    int n; if (!PyArg_ParseTuple(args, "i", &n)) return NULL;
    start_path(NULL);
    int32_t r = expand(n);
    if (r < 0) return failure_or_error();
    return PyLong_FromLong(r);
}

static PyObject *py_copy(PyObject *self, PyObject *args) {
    int n; if (!PyArg_ParseTuple(args, "i", &n)) return NULL;
    copy_gen++;
    int32_t r = copy_live(n); if (r < 0) return NULL;
    return PyLong_FromLong(r);
}

static PyObject *py_type(PyObject *self, PyObject *args) {
    int n; if (!PyArg_ParseTuple(args, "i", &n)) return NULL;
    return PyLong_FromLong(nodes[deref(n)].type);
}

static PyObject *py_deref(PyObject *self, PyObject *args) {
    int n; if (!PyArg_ParseTuple(args, "i", &n)) return NULL;
    return PyLong_FromLong(deref(n));
}

static PyObject *py_arcs(PyObject *self, PyObject *args) {
    int n; if (!PyArg_ParseTuple(args, "i", &n)) return NULL;
    n = deref(n);
    PyObject *out = PyList_New(nodes[n].narcs);
    for (int32_t i = 0; i < nodes[n].narcs; i++) {
        Arc a = pool[nodes[n].off + i];
        PyList_SET_ITEM(out, i, Py_BuildValue("(ii)", a.feat, deref(a.val)));
    }
    return out;
}

static PyObject *py_mark(PyObject *self, PyObject *args) { return PyLong_FromLongLong(nt); }
static PyObject *py_undo(PyObject *self, PyObject *args) {
    long long m; if (!PyArg_ParseTuple(args, "L", &m)) return NULL; undo_to(m); Py_RETURN_NONE;
}
static PyObject *py_forget(PyObject *self, PyObject *args) {
    long long m; if (!PyArg_ParseTuple(args, "L", &m)) return NULL; if (m < nt) nt = m; Py_RETURN_NONE;
}
static PyObject *py_reset(PyObject *self, PyObject *args) { nn = 0; np = 0; nt = 0; Py_RETURN_NONE; }
static PyObject *py_stats(PyObject *self, PyObject *args) {
    return Py_BuildValue("{s:L,s:L,s:L,s:i,s:L}", "nodes", (long long)nn, "arcs", (long long)np,
                         "trail", (long long)nt, "templates", ntpl, "unifications", (long long)n_unify);
}

static PyMethodDef methods[] = {
    {"init", py_init, METH_VARARGS, NULL},
    {"add_template", py_add_template, METH_VARARGS, NULL},
    {"copy_template", py_copy_template, METH_VARARGS, NULL},
    {"new_node", py_new_node, METH_VARARGS, NULL},
    {"set_arc", py_set_arc, METH_VARARGS, NULL},
    {"del_arc", py_del_arc, METH_VARARGS, NULL},
    {"unify", py_unify, METH_VARARGS, NULL},
    {"get", py_get, METH_VARARGS, NULL},
    {"expand", py_expand, METH_VARARGS, NULL},
    {"copy", py_copy, METH_VARARGS, NULL},
    {"type", py_type, METH_VARARGS, NULL},
    {"deref", py_deref, METH_VARARGS, NULL},
    {"arcs", py_arcs, METH_VARARGS, NULL},
    {"mark", py_mark, METH_NOARGS, NULL},
    {"undo", py_undo, METH_VARARGS, NULL},
    {"forget", py_forget, METH_VARARGS, NULL},
    {"reset", py_reset, METH_NOARGS, NULL},
    {"stats", py_stats, METH_NOARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module = {PyModuleDef_HEAD_INIT, "_fastdag", NULL, -1, methods};
PyMODINIT_FUNC PyInit__fastdag(void) { return PyModule_Create(&module); }
