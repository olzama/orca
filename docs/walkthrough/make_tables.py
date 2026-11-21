"""Rebuild the accuracy and speed tables of the walkthrough from measured data.

Input: analysis/mrs/dev-2025-tables.json (scripts/score_tables.py) and the
timings recorded in analysis/replay/*.json and data/ace/*.jsonl (copied below).
Usage: make_tables.py PAGE.html [PAGE.html ...]   (rewrites the pages in place)
"""
import json
import sys

ORCA = '/mnt/kesha/orca'
T = json.load(open(f'{ORCA}/analysis/mrs/dev-2025-tables.json'))
N = T['ace']['all']['sentences']
BANDS = [('under 10', 'Under 10'), ('10-19', '10 to 19'), ('20-29', '20 to 29'), ('30 and over', '30 and over')]

# Timings, in seconds for the 2,062 dev sentences
ACE_PASS, ACE_RETRY, ACE_MEDIAN = 1276.6, 437.8 + 301.5, 0.046   # dev-ace-1best, -retry16, -retry28
TAG, REPAIR1_K30, REPAIR6_K30, REPAIR6_K1, RANK = 17.46, 144.26, 28.87, 7.49, 2.0
LLM_SECS, LLM_SENTS, STREAMS = 26136.2, 390, 4

SYSTEMS = [
    ('first_proposal', "Orca, tagger's first guess"),
    ('first_accepted', 'Orca, repaired'),
    ('best', 'Orca, repaired and ranked'),
    ('best_llm', 'Orca, repaired and ranked, plus LLM repair'),
    ('ace', 'ACE (baseline)'),
]


def pct(k, n):
    return f'{100 * k / n:.1f}% <span class="cnt">({k:,})</span>'


def p1(x):
    return f'{100 * x:.1f}'


def sps(x):
    return f'{x:.3f}' if x < 0.1 else f'{x:,.2f}' if x < 1 else f'{x:,.1f}' if x < 100 else f'{x:,.0f}'


def td(x, hl=False):
    return f'<td class="n{" hl" if hl else ""}">{x}</td>'


def table(head, rows, group=None):
    g = ''
    if group:
        g = '<tr>' + ''.join(f'<th{" colspan=" + chr(34) + str(n) + chr(34) if n > 1 else ""} class="g">{t}</th>'
                             for t, n in group) + '</tr>'
    h = '<tr>' + ''.join(f'<th{" class=" + chr(34) + c + chr(34) if c else ""}>{t}</th>' for t, c in head) + '</tr>'
    body = '\n'.join('          ' + r for r in rows)
    return f'''    <div class="scroll">
      <table class="results">
        <thead>{g}{h}</thead>
        <tbody>
{body}
        </tbody>
      </table>
    </div>
'''


def accuracy():
    rows = []
    for key, name in SYSTEMS:
        a = T[key]['all']
        rows.append(f'<tr><td>{name}</td>' + td(pct(a['same MRS'], N), True) + td(pct(a['with MRS'], N))
                    + td(p1(a['preds']['f1'])) + td(p1(a['links']['f1'])) + td(pct(a['same tree'], N)) + '</tr>')
    t1 = table([('System', ''), ('Exact meaning (same MRS as gold)', 'n hl'), ('Any analysis', 'n'),
                ('Predicates right (F1)', 'n'), ('Links right (F1)', 'n'), ('Exact tree', 'n')], rows)
    rows = []
    for key, name in SYSTEMS[2:]:
        a = T[key]['all']
        rows.append(f'<tr><td>{name}</td>' + td(f"{a['with MRS']:,}") + td(pct(a['same MRS'], a['with MRS']), True)
                    + td(p1(a['preds']['precision'])) + td(p1(a['links']['precision'])) + '</tr>')
    t2 = table([('System', ''), ('Sentences with an analysis', 'n'), ('Exact meaning', 'n hl'),
                ('Predicates that are in gold (%)', 'n'), ('Links that are in gold (%)', 'n')], rows)
    return (t1 + '''    <p class="caption">All 2,062 sentences; counts in parentheses. <b>Orca, repaired</b>: if the grammar rejects the tagger's guess, the tagger's next-best labels are tried under the failing node until a derivation is accepted. <b>Ranked</b>: repair collects up to 30 accepted derivations and the grammar's own ranking model (the one ACE uses) picks one. <b>Plus LLM repair</b>: for the sentences still without an analysis, the step described further down. <b>Any analysis</b>: the grammar accepts a complete derivation. <b>Predicates right, links right</b>: the share of gold predicates and of gold semantic links that the analysis also has, balanced against how many it adds that gold lacks; a sentence without an analysis scores zero. <b>Exact tree</b>: same rules and lexical types throughout (the root condition is not compared, since ACE's output does not record it). As a check of the engine, replaying the annotators' own derivations gives exactly the gold meaning for every sentence, so all losses come from the proposed derivations.</p>
    <h3>When a system does give an analysis</h3>
''' + t2 + '''    <p class="caption">The same runs, restricted to the sentences each system analyzes. Orca's analyses are as precise as ACE's; the gap in the first table is almost entirely the sentences Orca cannot analyze.</p>
  </section>
''')


def side_by_side():
    rows = []
    for b, label in BANDS:
        n = T['ace'][b]['sentences']
        rows.append(f'<tr><td>{label}</td>' + td(f'{n:,}')
                    + ''.join(td(pct(T[s][b]['same MRS'], n), True) for s in ('ace', 'best', 'best_llm'))
                    + ''.join(td(pct(T[s][b]['with MRS'], n)) for s in ('ace', 'best', 'best_llm')) + '</tr>')
    by_len = table([('Words', ''), ('Sentences', 'n'), ('ACE', 'n hl'), ('Orca', 'n hl'), ('Orca + LLM', 'n hl'),
                    ('ACE', 'n'), ('Orca', 'n'), ('Orca + LLM', 'n')], rows,
                   group=[('', 2), ('Exact meaning', 3), ('Any analysis', 3)])
    full1 = TAG + REPAIR1_K30 + RANK
    full6 = TAG + REPAIR6_K30 + RANK
    miss = lambda k: f"{N - T[k]['all']['with MRS']:,}"
    rows = [
        f'<tr><td>ACE</td>{td(sps(N / (ACE_PASS + ACE_RETRY)), True)}{td("one CPU core")}{td("up to 28 GB")}{td(miss("ace"))}</tr>',
        f'<tr><td>Orca, repaired and ranked</td>{td(sps(N / full1), True)}{td("one GPU, one CPU core")}{td("megabytes")}{td(miss("best"))}</tr>',
        f'<tr><td>Orca, repaired and ranked</td>{td(sps(N / full6), True)}{td("one GPU, six CPU cores")}{td("megabytes")}{td(miss("best"))}</tr>',
        f'<tr><td>Orca, repaired and ranked, plus LLM repair</td>{td(sps(N / (full1 + LLM_SECS / STREAMS)), True)}{td(f"as above, {STREAMS} model calls at a time")}{td("megabytes locally")}{td(miss("best_llm"))}</tr>',
    ]
    speed = table([('System', ''), ('Sentences per second', 'n hl'), ('Hardware', 'n'), ('Memory', 'n'),
                   ('Left without an analysis', 'n')], rows)
    rows = [
        f'<tr><td>Tagging</td>{td(sps(N / TAG), True)}{td("one GPU (RTX 2080 Ti)")}</tr>',
        f'<tr><td>Replaying one given derivation</td>{td("about 670", True)}{td("one CPU core")}</tr>',
        f'<tr><td>Repair, stopping at the first accepted derivation</td>{td(sps(N / REPAIR6_K1), True)}{td("six CPU cores")}</tr>',
        f'<tr><td>Repair, collecting up to 30 accepted derivations</td>{td(sps(N / REPAIR1_K30), True)}{td("one CPU core")}</tr>',
        f'<tr><td>Ranking the accepted derivations</td>{td("about 1,000", True)}{td("one CPU core")}</tr>',
        f'<tr><td>LLM repair, per sentence it is given</td>{td(sps(LLM_SENTS / LLM_SECS), True)}{td("one model call at a time")}</tr>',
    ]
    stages = table([('Stage of Orca', ''), ('Sentences per second', 'n hl'), ('Hardware', 'n')], rows)
    return ('''  <section class="stack">
    <h2>Orca and the ACE chart parser, side by side</h2>
    <p>ACE is the parser the treebank was built with. It searches a chart of all possible analyses and then ranks them with a statistical model. Orca proposes one derivation per sentence with the tagger and lets the grammar check it, so it never builds the chart.</p>
    <h3>By sentence length</h3>
''' + by_len + '''    <p class="caption">Orca here is "repaired and ranked". Word counts are treebank tokens. Both systems lose accuracy with length; Orca loses it much faster, mostly because for long sentences it more often finds no analysis at all. The LLM step supplies about half of the missing analyses in every length band, but for long sentences they are rarely exact.</p>
    <h3>Speed</h3>
''' + speed + '''    <p class="caption">Sentences per second is the number of sentences divided by the total time. ACE's time includes retrying its 14 hardest sentences with more memory; the hardest ran out of memory after building up to 230,000 chart edges, while most sentences take a fraction of a second. These are short sentences (about 12 words on average); the comparison on long sentences, where ACE often fails, is still to be made. The LLM step is counted as the time of its model calls. Loading the grammar (about 17 seconds for Orca, 1 for ACE) is not included.</p>
    <h3>Where Orca's time goes</h3>
''' + stages + '''    <p class="caption">Collecting up to 30 accepted derivations costs much more than stopping at the first, and buys the gain from ranking. The LLM step is three orders of magnitude slower than the rest, which is why it is used only for the sentences the fast path cannot analyze.</p>
  </section>

''')


def training_data():
    reps = {'best': 246.0, 'lithuman_best': 211.7, 'lit_best': 188.8}    # analysis/replay/dev-*-strict-k30-b600.json
    sizes = {'best': 86278, 'lithuman_best': 107652, 'lit_best': 189281}
    names = {'best': 'Redwoods treebank only (current tagger)',
             'lithuman_best': 'plus literary corpus: human excerpts',
             'lit_best': 'plus literary corpus: human and LLM-written excerpts'}
    rows = []
    for k in ('best', 'lithuman_best', 'lit_best'):
        a = T[k]['all']
        rows.append(f'<tr><td>{names[k]}</td>' + td(f'{sizes[k]:,}') + td(pct(a['same MRS'], N), True) + td(pct(a['with MRS'], N))
                    + td(p1(a['preds']['f1'])) + td(p1(a['links']['f1'])) + td(pct(a['same tree'], N)) + td(f'{reps[k]:.0f}') + '</tr>')
    t = table([('Tagger trained on', ''), ('Training sentences', 'n'), ('Exact meaning', 'n hl'), ('Any analysis', 'n'),
               ('Predicates right (F1)', 'n'), ('Links right (F1)', 'n'), ('Exact tree', 'n'), ('Replays per sentence in repair', 'n')], rows)
    return ('  <section class="stack">\n    <h2>More training data: grammar parses of literary text</h2>\n'
            '    <p>The treebank is small. A literary corpus (excerpts from novels of 1838 to 1921, and four sets of LLM-written excerpts matched to them) had already been parsed with the same grammar by ACE, keeping its first-ranked analysis. These analyses are not checked by an annotator, but every one replays in Orca\'s engine to the same meaning, so they are analyses the grammar licenses. Thirty excerpts are kept out of training in all five sets, for later tests on this corpus. The tagger is retrained with the same settings, and the full pipeline (repair, ranking) is measured on the same 2,062 development sentences.</p>\n'
            + t +
            '    <p class="caption">"Repaired and ranked" in every row. Both additions help on every measure, and the tagger needs fewer replays to find an accepted derivation. Adding the LLM-written excerpts to the human ones adds analyses but not exact meanings. Each row is one training run; how much a rerun with another random seed would differ has not been measured, so differences of a few dozen sentences between the last two rows may be chance. The pipeline rows elsewhere on this page still use the treebank-only tagger.</p>\n'
            '  </section>\n\n')


def fallback():
    rows = [
        '<tr><td>LLM repair (Claude Opus)</td>' + td('188') + td('89', True) + td(sps(LLM_SENTS / LLM_SECS) + ' per model call stream') + td('about $0.35 per sentence (API-equivalent)') + '</tr>',
        '<tr><td>ACE</td>' + td('388') + td('270', True) + td(sps(390 / 1315.0) + ' on one CPU core') + td('none') + '</tr>',
    ]
    t = table([('Fallback, on the 390 sentences', ''), ('Analyses', 'n'), ('Exact meaning', 'n hl'), ('Sentences per second', 'n'), ('Cost', 'n')], rows)
    return ('<!-- fallback -->\n    <h3>Compared with ACE as the fallback</h3>\n' + t +
            '    <p class="caption">The same 390 sentences that repair leaves without an analysis, given instead to ACE (its time includes retries with more memory). For English, where a chart parser and its ranking model exist, ACE is the better fallback on both speed and accuracy. ACE also spends most of its total time on exactly these sentences, so with an ACE fallback Orca would be only modestly faster than ACE alone; the speed advantage depends on Orca itself failing less often. The LLM step is more useful offline: on sentences of training or silver data that Orca cannot analyze, where its accepted repairs can become repair patterns or training examples; on sentences too long for ACE\'s memory; and as a diagnosis of why the grammar rejects an analysis.</p>\n'
            '<!-- /fallback -->\n')


CSS = '.results th.g { text-align: center; border-bottom: 0; color: var(--fg); }\n.results .cnt { color: var(--muted); font-weight: 400; }\n'


def rebuild(s):
    start = s.index('    <div class="scroll">\n      <table class="results">\n        <thead>', s.index('How good is it right now?'))
    end = s.index('  <section class="stack">\n    <h2>Tested:')
    s = s[:start] + accuracy() + '\n' + training_data() + side_by_side() + s[end:]
    if '<!-- fallback -->' in s:
        s = s[:s.index('<!-- fallback -->')] + s[s.index('<!-- /fallback -->\n') + len('<!-- /fallback -->\n'):]
    i = s.index('  <section class="stack">\n    <h2>The steps</h2>')
    j = s.rindex('  </section>', 0, i)
    s = s[:j] + fallback() + s[j:]
    if '.results th.g' not in s:
        anchor = '.results th.n { text-align: right; }\n'
        s = s.replace(anchor, anchor + CSS)
    b = T['best']['all']
    i = s.index('      <div class="tile main">')
    old_tiles = s[i:s.index('    </div>', i)]
    tiles = (f'      <div class="tile main"><b>{100 * b["same MRS"] / N:.1f}%</b><span>of sentences get <strong>exactly the gold meaning</strong> (the same MRS)</span></div>\n'
             f'      <div class="tile"><b>{100 * b["with MRS"] / N:.1f}%</b><span>get a complete analysis that the grammar accepts, with full structure and semantics</span></div>\n'
             f'      <div class="tile"><b>{100 * b["same tree"] / N:.1f}%</b><span>get exactly the gold tree</span></div>\n')
    return s.replace(old_tiles, tiles)


for p in sys.argv[1:]:
    s = open(p).read()
    open(p, 'w').write(rebuild(s))
    print('rebuilt', p)
