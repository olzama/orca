"""Rebuild the body of the Orca walkthrough page from measured data.

Everything between </header> and the page script is regenerated: a short
visible part (headline numbers, pipeline, tagger, label encoding, results,
where the misses are) and one folded section per experiment. The worked
examples (drawn by the page script into #examples) sit in the last fold.

Usage: make_page.py PAGE.html   (rewrites the page in place)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_tables import (BANDS, LLM_SECS, LLM_SENTS, N, ORCA, RANK, REPAIR1_K30, STREAMS, SYSTEMS, T, TAG,  # noqa: E402
                         ACE_PASS, ACE_RETRY, REPAIR6_K1, REPAIR6_K30, p1, pct, sps, table, td)

RAW = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothall-rawtext.json'))
SPS = RAW['sentences per second']
RAW_WITH = RAW['counts']['with MRS']
ORACLE = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothsurf-rawtext.json'))     # best tagger from raw text (forms as typed)
RAW_HALF = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothhalfsurf-rawtext.json'))
OLD_ORACLE = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothall-rawtext-oracle.json'))
METRICS = json.load(open(f'{ORCA}/data/models/tagger-2025bothall-bert/metrics.json'))
LABELS = json.load(open(f'{ORCA}/data/models/tagger-2025bothall-bert/labels.json'))
# From treebank tokens: rerank.py on data/models/tagger-2025bothall-bert/dev-strict-k30-b600.jsonl
TREEBANK_SPLIT = (1511, 80, 237, 234)
# analysis/raw-tokens-dev.json (scripts/check_raw_tokens.py)
RAW_CHECK = (('Gold derivation replays over raw-text tokens', 2056), ('… with the gold MRS', 2056),
             ('Word forms as in the treebank', 1838), ('… ignoring case', 2003))


def ms(step):
    return 1000 * RAW['seconds by step'][step] / RAW['counts']['sentences']


def fold(title, takeaway, body, open_=False):
    return (f'  <details class="fold"{" open" if open_ else ""}>\n'
            f'    <summary><span class="ft">{title}</span><span class="fs">{takeaway}</span></summary>\n'
            f'    <div class="fb stack">\n{body}    </div>\n  </details>\n')


def cap(text):
    return f'    <p class="caption">{text}</p>\n'


def tiles():
    b = T['bothall_best']['all']
    c = RAW['counts']
    ace_sps = N / (ACE_PASS + ACE_RETRY)
    t = [('main', f'{100 * b["same MRS"] / N:.1f}%', 'exactly the gold meaning (same MRS)'),
         ('', f'{100 * ORACLE["counts"]["same MRS"] / N:.1f}%', 'the same, from raw text (tagger trained on forms as typed)'),
         ('', f'{100 * b["with MRS"] / N:.1f}%', 'get a full analysis the grammar accepts'),
         ('', f'{RAW["sentences per second"]:.1f}', f'sentences per second from raw text (ACE: {ace_sps:.1f})')]
    return ('  <section class="stack">\n    <div class="tiles">\n'
            + ''.join(f'      <div class="tile {k}"><b>{v}</b><span>{d}</span></div>\n' for k, v, d in t)
            + '    </div>\n'
            + cap(f'English Resource Grammar (2025), Redwoods development set: {N:,} sentences never seen in training '
                  '(customer e-mails, Wikipedia). Gold is the annotators\' analysis. ACE, the grammar\'s chart parser, gets '
                  f'{100 * T["ace"]["all"]["same MRS"] / N:.1f}% exact.')
            + '  </section>\n')


def box(x, y, w, h, title, sub, cls='', ms_=None):
    out = f'<rect class="bx {cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>'
    out += f'<text class="bt" x="{x + w / 2}" y="{y + 24}" text-anchor="middle">{title}</text>'
    for i, line in enumerate(sub):
        out += f'<text class="bs" x="{x + w / 2}" y="{y + 42 + 14 * i}" text-anchor="middle">{line}</text>'
    if ms_ is not None:
        out += f'<text class="bm" x="{x + w / 2}" y="{y + h + 18}" text-anchor="middle">{ms_}</text>'
    return out


def pipeline():
    W, H, w, h, y, gap = 1000, 190, 122, 84, 30, 24
    names = [('Raw text', ['a sentence'], 'io', None),
             ('Tokens', ['grammar\'s own', 'preprocessing'], '', f'{ms("tokens"):.0f} ms'),
             ('Tagger', ['2 labels', 'per word'], 'nn', f'{ms("tag"):.0f} ms'),
             ('Decode', ['labels → one', 'derivation'], '', None),
             ('Replay', ['unification', 'in C'], 'gr', None),
             ('Rank', ['grammar\'s', 'MaxEnt model'], 'gr', f'{ms("rank"):.0f} ms'),
             ('MRS', ['full sign,', 'semantics'], 'io', f'{ms("mrs"):.0f} ms')]
    x0 = (W - (len(names) * w + (len(names) - 1) * gap)) / 2
    svg = []
    for i, (t, sub, cls, m) in enumerate(names):
        x = x0 + i * (w + gap)
        svg.append(box(x, y, w, h, t, sub, cls, m))
        if i:
            svg.append(f'<line class="ar" x1="{x - gap + 2}" y1="{y + h / 2}" x2="{x - 4}" y2="{y + h / 2}" marker-end="url(#ah)"/>')
    xd, xr = x0 + 3 * (w + gap) + w / 2, x0 + 4 * (w + gap) + w / 2
    svg.append(f'<path class="ar lp" d="M {xr} {y + h} C {xr} {y + h + 52}, {xd} {y + h + 52}, {xd} {y + h + 6}" marker-end="url(#ah)"/>')
    svg.append(f'<text class="bs lt" x="{(xd + xr) / 2}" y="{y + h + 50}" text-anchor="middle">repair: next-best labels under the failing node, until 30 derivations are accepted · {ms("repair"):.0f} ms</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="diag" role="img" aria-label="Orca pipeline">'
            '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0,0 L10,5 L0,10 z" class="ah"/></marker></defs>' + ''.join(svg) + '</svg>')


def tagger_svg():
    W, H = 1080, 250
    words = ['I', 'am', 'interested', 'in', '…']
    svg, xs = [], [150 + 150 * i for i in range(len(words))]
    for x, wd in zip(xs, words):
        svg.append(f'<text class="bt" x="{x}" y="28" text-anchor="middle">{wd}</text>')
        svg.append(f'<line class="ar" x1="{x}" y1="36" x2="{x}" y2="62" marker-end="url(#ah2)"/>')
    svg.append('<rect class="bx nn" x="70" y="66" width="760" height="56" rx="8"/>')
    svg.append('<text class="bt" x="450" y="90" text-anchor="middle">BERT-base-cased encoder, fine-tuned</text>')
    svg.append('<text class="bs" x="450" y="108" text-anchor="middle">WordPiece subwords · 12 layers · 768 dimensions · 110M parameters</text>')
    for x in xs:
        svg.append(f'<line class="ar" x1="{x}" y1="124" x2="{x}" y2="146" marker-end="url(#ah2)"/>')
        svg.append(f'<circle class="dot" cx="{x}" cy="152" r="5"/>')
        svg.append(f'<line class="ar" x1="{x - 8}" y1="160" x2="{x - 40}" y2="188" marker-end="url(#ah2)"/>')
        svg.append(f'<line class="ar" x1="{x + 8}" y1="160" x2="{x + 40}" y2="188" marker-end="url(#ah2)"/>')
        svg.append(f'<rect class="bx lf" x="{x - 70}" y="192" width="62" height="26" rx="5"/><text class="bs" x="{x - 39}" y="209" text-anchor="middle">leaf</text>')
        svg.append(f'<rect class="bx tr" x="{x + 8}" y="192" width="62" height="26" rx="5"/><text class="bs" x="{x + 39}" y="209" text-anchor="middle">tree</text>')
    svg.append('<text class="bs lt" x="860" y="156">first subword of each word</text>')
    svg.append(f'<text class="bs lt" x="860" y="200">2 linear heads, softmax</text>')
    svg.append(f'<text class="bs lt" x="860" y="216">{len(LABELS["leaf"]):,} / {len(LABELS["tree"]):,} labels</text>')
    return (f'<svg viewBox="0 0 {W} {H}" class="diag" role="img" aria-label="Tagger architecture">'
            '<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            '<path d="M0,0 L10,5 L0,10 z" class="ah"/></marker></defs>' + ''.join(svg) + '</svg>')


def how():
    a = METRICS['args']
    h = METRICS['history'][-1]
    specs = [
        ('Encoder', f'{a["encoder"]}, all weights fine-tuned'),
        ('Word vector', 'first subword of each word; dropout 0.1'),
        ('Outputs', f'leaf label ({len(LABELS["leaf"]):,} classes) and tree label ({len(LABELS["tree"]):,} classes) per word'),
        ('Loss', 'sum of the two cross-entropies'),
        ('Training data', '590,721 sentences: Redwoods treebank (86,278) and ACE parses of literary and news text, checked by replay'),
        ('Optimizer', f'AdamW, learning rate {a["lr"]:g} (encoder) and {a["head_lr"]:g} (heads), 5% warm-up, linear decay, '
                      f'{a["epochs"]} epochs, batch {a["batch"]}, mixed precision'),
        ('Per-word accuracy (dev)', f'leaf {100 * h["leaf_acc"]:.1f}%, tree {100 * h["tree_acc"]:.1f}%, both {100 * h["both_acc"]:.1f}%; '
                                    f'every label of the sentence right: {100 * h["exact_match"]:.1f}%'),
        ('Into repair', '5 best labels per word and head; at most 600 replays and 30 accepted derivations per sentence'),
        ('Ranking', 'the MaxEnt model that ships with the ERG (redwoods.mem), the one ACE uses'),
    ]
    kv = ''.join(f'<span>{k}</span><span>{v}</span>' for k, v in specs)
    enc = [('I', 'n_-_pr-i_le||hdn_bnp-qnt_c', '1|root_strict sb-hd_mc_c'), ('am', 'v_prd_am_le||', '1|hd-cmp_u_c'),
           ('interested', 'aj_pp_i-obl_le||', '1|hd-cmp_u_c'), ('in', 'p_np_ptcl_le||', '1|hd-cmp_u_c'),
           ('a', 'd_-_sg-nmd_le||', '1|sp-hd_n_c'), ('lap', 'n_-_c_le||', '1|n-hdn_cpd_c'),
           ('top', 'n_-_c_le|n_sg_ilr|', '1|hd-pct_c'), ('.', 'pt_-_period_le||', '<none>')]
    rows = [f'<tr><td><b>{w}</b></td><td class="m">{l}</td><td class="m">{t.replace("<", "&lt;").replace(">", "&gt;")}</td></tr>' for w, l, t in enc]
    enc_t = table([('Word', ''), ('Leaf: lexical type | lexical rules | unary rules', ''),
                   ('Tree: depth change | rule joining this word to the next', '')], rows)
    return ('  <section class="stack">\n    <h2>How it works</h2>\n'
            f'    <div class="scroll pad">{pipeline()}</div>\n'
            + cap('Time per sentence from raw text, one sentence at a time. No chart is built: the tagger proposes a complete '
                  'derivation and the grammar checks it by unification.')
            + '    <h3>The tagger</h3>\n'
            f'    <div class="scroll pad">{tagger_svg()}</div>\n'
            f'    <div class="kv specs">{kv}</div>\n'
            + '    <h3>A derivation as two labels per word</h3>\n' + enc_t
            + cap('The tree labels fix exactly one binary tree: each says how deep the node joining the word to the next one '
                  'sits, relative to the previous such node, and which rule it is (after Gómez-Rodríguez and Vilares 2018). '
                  'The lexical entry is looked up from the word and its type.')
            + '  </section>\n')


def split(run):
    out = [0, 0, 0, 0]
    for x in run['records']:
        out[3 if not x['accepted'] else 2 if not x['gold among accepted'] else 0 if x['same MRS'] else 1] += 1
    return out


def results():
    rows = []
    for key, name in SYSTEMS:
        a = T[key]['all']
        rows.append(f'<tr><td>{name}</td>' + td(pct(a['same MRS'], N), True) + td(pct(a['with MRS'], N))
                    + td(p1(a['preds']['f1'])) + td(p1(a['links']['f1'])) + td(pct(a['same tree'], N)) + '</tr>')
    c = RAW['counts']
    oc = ORACLE['counts']
    rows.insert(-1, '<tr><td>… the same, from raw text</td>' + td(pct(c['same MRS'], N), True) + td(pct(c['with MRS'], N))
                + td('') + td('') + td('') + '</tr>')
    rows.insert(-1, '<tr><td>… tagger trained on forms as typed, from raw text</td>' + td(pct(oc['same MRS'], N), True)
                + td(pct(oc['with MRS'], N)) + td('') + td('') + td('') + '</tr>')
    t1 = table([('System', ''), ('Exact meaning', 'n hl'), ('Any analysis', 'n'),
                ('Predicates (F1)', 'n'), ('Links (F1)', 'n'), ('Exact tree', 'n')], rows)
    # where each sentence ends up
    n_by = {}
    for l in open(f'{ORCA}/data/encoded-2025/dev.jsonl'):
        r = json.loads(l)
        n_by[r['id']] = len(r['tokens'])
    bands = ((0, 10, 'under 10'), (10, 20, '10 to 19'), (20, 30, '20 to 29'), (30, 10 ** 6, '30 and over'))
    cnt = {b: [0, 0, 0, 0, 0] for _, _, b in bands}
    for x in ORACLE['records']:
        b = next(nm for lo, hi, nm in bands if lo <= n_by[x['id']] < hi)
        k = 3 if not x['accepted'] else 2 if not x['gold among accepted'] else 0 if x['same MRS'] else 1
        cnt[b][k] += 1
        cnt[b][4] += 1
    tot = [sum(cnt[b][i] for b in cnt) for i in range(4)]
    rows = [f'<tr><td>Treebank forms, from treebank tokens, all</td>' + ''.join(td(f'{v:,}', i == 0) for i, v in enumerate(TREEBANK_SPLIT)) + '</tr>',
            '<tr><td>Treebank forms, from raw text, all</td>' + ''.join(td(f'{v:,}', i == 0) for i, v in enumerate(split(OLD_ORACLE))) + '</tr>',
            f'<tr><td>Forms as typed, from raw text, all</td>' + ''.join(td(f'{v:,}', i == 0) for i, v in enumerate(tot)) + '</tr>']
    rows += [f'<tr><td>Forms as typed, from raw text, {b} words ({cnt[b][4]:,})</td>' + ''.join(td(f'{v:,}', i == 0) for i, v in enumerate(cnt[b][:4])) + '</tr>'
             for _, _, b in bands]
    t2 = table([('Sentences', ''), ('Exact meaning', 'n hl'), ('Gold accepted, ranking picks another', 'n'),
                ('Gold never accepted', 'n'), ('No analysis', 'n')], rows)
    return ('  <section class="stack">\n    <h2>Results</h2>\n' + t1
            + cap(f'All {N:,} development sentences, counts in parentheses. Exact meaning: the whole MRS matches gold. '
                  'F1: share of gold predicates and semantic links found, balanced against extra ones. '
                  'Replaying the annotators\' own derivations gives the gold MRS for every sentence, so every loss comes from the proposed derivations.')
            + '    <h3>Where the misses are (best tagger)</h3>\n' + t2
            + cap('Best BERT-base tagger of each kind. Ranking loses few sentences. Most of the gap is in proposing: the gold analysis is never among the accepted '
                  'derivations, or nothing is accepted. Long sentences lose most.')
            + '  </section>\n')


def exp_training():
    runs = [('best', '2025b', 86278, 'Redwoods treebank only'),
            ('lithuman_best', '2025lithuman', 107652, '+ literary, human'),
            ('lit_best', '2025lit', 189281, '+ literary, human and LLM'),
            ('nythuman_best', '2025nythuman', 128468, '+ news, human'),
            ('nytall_best', '2025nytall', 487718, '+ news, human and 11 LLM sets'),
            ('bothhuman_best', '2025bothhuman', 149842, '+ both, human'),
            ('bothall_best', '2025bothall', 590721, '+ both, human and LLM')]
    rows = []
    for k, tag, size, name in runs:
        if k not in T:
            continue
        rps = json.load(open(f'{ORCA}/analysis/replay/dev-{tag}-strict-k30-b600.json'))['replays_per_sentence']
        a = T[k]['all']
        rows.append(f'<tr><td>{name}</td>' + td(f'{size:,}') + td(pct(a['same MRS'], N), True) + td(pct(a['with MRS'], N))
                    + td(p1(a['preds']['f1'])) + td(p1(a['links']['f1'])) + td(f'{rps:.0f}') + '</tr>')
    t = table([('Tagger trained on', ''), ('Sentences', 'n'), ('Exact meaning', 'n hl'), ('Any analysis', 'n'),
               ('Predicates (F1)', 'n'), ('Links (F1)', 'n'), ('Replays per sentence', 'n')], rows)
    rows = []
    for name, r in (('all silver (590,721 sentences)', ORACLE), ('half of the silver (338,269)', RAW_HALF)):
        rc = r['counts']
        rows.append(f'<tr><td>{name}</td>' + td(pct(rc['same MRS'], N), True) + td(pct(rc['with MRS'], N))
                    + td(f"{rc['gold MRS among accepted']:,}") + '</tr>')
    t2 = table([('Forms as typed, from raw text', ''), ('Exact meaning', 'n hl'), ('Any analysis', 'n'), ('Gold among accepted', 'n')], rows)
    t = t + cap('Treebank forms, from treebank tokens.') + t2 + cap('All of the treebank in both; half of the silver sentences chosen at random. Halving the silver data costs little, so more text of the same kind is unlikely to help much.')
    body = t + cap('Silver data: ACE\'s first-ranked parses of a literary corpus (novels 1838 to 1921, with LLM-written matched '
                   'excerpts) and a news corpus (NYT 2023 and 2025, with 11 LLM-written sets), kept only if they replay. '
                   'One run each; seed variation not yet measured.')
    return fold('Training data', 'More grammar-licensed text helped up to now; halving it costs little.', body)


def exp_rawtext():
    rows = [f'<tr><td>{k}</td>{td(format(v, ","), True)}</tr>' for k, v in RAW_CHECK]
    t1 = table([(f'Check on {N:,} dev sentences', ''), ('Sentences', 'n hl')], rows)
    steps = [('Tokens (ACE preprocessing, separate process)', 'tokens'), ('Tagger (GPU)', 'tag'),
             ('Replay and repair (one core)', 'repair'), ('Ranking', 'rank'), ('MRS', 'mrs')]
    rows = [f'<tr><td>{n}</td>{td(format(ms(k), ".1f"))}</tr>' for n, k in steps]
    rows.append(f'<tr><td><b>End to end</b></td>{td(format(1000 / SPS, ".1f"), True)}</tr>')
    t2 = table([('From raw text', ''), ('ms per sentence', 'n hl')], rows)
    body = (t1 + t2 + cap('The grammar\'s preprocessing (tokenization, POS tags, token mapping) runs in ACE without parsing; all '
                          'tokens it proposes for a word are kept, and replay picks the one the lexical entry accepts. '
                          'The loss against treebank tokens comes from word forms: in the treebank, case depends on the analysis '
                          '(name entries keep capitals). Training the tagger on forms as typed removes the leak: more exact meanings from raw text, somewhat fewer analyses.'))
    return fold('From raw text', 'The grammar\'s tokens work; the tagger loses a little on capitalization.', body)


def exp_ace():
    rows = []
    for b, label in BANDS:
        n = T['ace'][b]['sentences']
        rows.append(f'<tr><td>{label}</td>' + td(f'{n:,}')
                    + ''.join(td(pct(T[s][b]['same MRS'], n), True) for s in ('ace', 'best', 'best_llm'))
                    + ''.join(td(pct(T[s][b]['with MRS'], n)) for s in ('ace', 'best', 'best_llm')) + '</tr>')
    by_len = table([('Words', ''), ('Sentences', 'n'), ('ACE', 'n hl'), ('Orca', 'n hl'), ('Orca + LLM', 'n hl'),
                    ('ACE', 'n'), ('Orca', 'n'), ('Orca + LLM', 'n')], rows,
                   group=[('', 2), ('Exact meaning', 3), ('Any analysis', 3)])
    full1, full6 = TAG + REPAIR1_K30 + RANK, TAG + REPAIR6_K30 + RANK
    miss = lambda k: f"{N - T[k]['all']['with MRS']:,}"
    rows = [f'<tr><td>ACE</td>{td(sps(N / (ACE_PASS + ACE_RETRY)), True)}{td("1 CPU core")}{td("up to 28 GB")}{td(miss("ace"))}</tr>',
            f'<tr><td>Orca</td>{td(sps(N / full1), True)}{td("1 GPU, 1 core")}{td("about 2 GB")}{td(miss("best"))}</tr>',
            f'<tr><td>Orca</td>{td(sps(N / full6), True)}{td("1 GPU, 6 cores")}{td("about 2 GB")}{td(miss("best"))}</tr>',
            f'<tr><td>Orca, from raw text</td>{td(format(SPS, ".1f"), True)}{td("1 GPU, 1 core")}{td("about 2 GB")}{td(format(N - RAW_WITH, ","))}</tr>',
            f'<tr><td>Orca + LLM repair</td>{td(sps(N / (full1 + LLM_SECS / STREAMS)), True)}{td(f"+ {STREAMS} model calls at a time")}{td("")}{td(miss("best_llm"))}</tr>']
    speed = table([('System', ''), ('Sentences per second', 'n hl'), ('Hardware', 'n'), ('Memory', 'n'), ('No analysis', 'n')], rows)
    rows = []
    for key, name in SYSTEMS[2:]:
        a = T[key]['all']
        rows.append(f'<tr><td>{name}</td>' + td(f"{a['with MRS']:,}") + td(pct(a['same MRS'], a['with MRS']), True)
                    + td(p1(a['preds']['precision'])) + td(p1(a['links']['precision'])) + '</tr>')
    prec = table([('System', ''), ('With an analysis', 'n'), ('Exact meaning', 'n hl'),
                  ('Predicates in gold (%)', 'n'), ('Links in gold (%)', 'n')], rows)
    body = (by_len + cap('Treebank tokens, treebank-only tagger. Orca loses accuracy with length faster than ACE, mostly by finding no analysis.')
            + speed + cap('Dev sentences average about 12 words. ACE\'s time includes retries of its 14 hardest sentences with more memory.')
            + prec + cap('Restricted to the sentences each system analyzes: Orca\'s analyses are as precise as ACE\'s.'))
    return fold('Orca and ACE', 'Faster at every setting; behind on long sentences.', body)


def exp_llm():
    llm = open(os.path.join(HERE, 'llm-table.html')).read()
    rows = ['<tr><td>LLM repair (Claude Opus)</td>' + td('188') + td('89', True) + td(sps(LLM_SENTS / LLM_SECS)) + td('about $0.35 per sentence') + '</tr>',
            '<tr><td>ACE</td>' + td('388') + td('270', True) + td(sps(390 / 1315.0)) + td('none') + '</tr>']
    fb = table([('Fallback on the 390 sentences repair leaves', ''), ('Analyses', 'n'), ('Exact meaning', 'n hl'),
                ('Sentences per second', 'n'), ('Cost', 'n')], rows)
    body = (llm + cap('Claude Opus sees the rejected derivation, every failure point (feature path, clashing types), the grammar\'s '
                      'definitions of the rules and types involved, and the lexicon\'s options per word; the grammar replays every answer. '
                      'Usage is API-equivalent; calls went through a subscription.')
            + fb + cap('For English, ACE is the better fallback. The LLM step is kept for offline work: training data, grammar expansion, diagnosis.'))
    return fold('LLM repair', 'Accepted analyses for about half the leftovers; slow; used offline only.', body)


def exp_llm_rank():
    path = f'{ORCA}/analysis/llm-rank/pilot1/score.json'
    if not os.path.exists(path):
        return ''
    r = json.load(open(path))
    rows = []
    for key, name in (('all', 'All'), ('margin under 1', 'MaxEnt margin under 1'), ('1 to 3', 'Margin 1 to 3'), ('3 and over', 'Margin 3 and over')):
        c = r['by margin'][key]
        rows.append(f'<tr><td>{name}</td>' + td(f"{c['sentences']:,}") + td(f"{c['readings'] / c['sentences']:.1f}")
                    + td(pct(c['maxent right'], c['sentences']), True) + td(pct(c['llm right'], c['sentences']), True) + '</tr>')
    t = table([('Dev sentences with 2+ readings, gold among them', ''), ('Sentences', 'n'), ('Readings shown', 'n'),
               ('MaxEnt picks gold', 'n hl'), ('LLM picks gold', 'n hl')], rows)
    body = t + cap(f'A random 300 of the 622 such sentences. Each reading is shown only by the DMRS predicates and links that not '
                   f'every reading has; Claude Opus picks one ({r["calls"]} calls, ${r["cost_usd"]:.2f} API-equivalent). '
                   'Many of its misses are the grammar\'s conventions (which predicate or rule the treebank uses), not misreadings.')
    return fold('LLM choosing among readings', 'Below the grammar\'s ranking model at every margin.', body)


ENCODERS = (('bertbase', 'BERT-base (cased)', '110M'), ('robertalarge', 'RoBERTa-large', '355M'),
            ('xlmrlarge', 'XLM-R large', '560M'), ('debertav3large', 'DeBERTa-v3 large', '435M'))


def exp_encoders():
    rows = []
    for key, name, size in ENCODERS:
        mp = f'{ORCA}/data/models/tagger-2025surf-{key}/metrics.json'
        if not os.path.exists(mp):
            continue
        d = json.load(open(mp))['dev']
        rp = f'{ORCA}/analysis/mrs/dev-2025surf-{key}-rawtext.json'
        if os.path.exists(rp):
            rc = json.load(open(rp))['counts']
            raw = td(pct(rc['same MRS'], N), True) + td(pct(rc['with MRS'], N)) + td(f"{rc['gold MRS among accepted']:,}")
        else:
            raw = td('running') + td('') + td('')
        rows.append(f'<tr><td>{name}</td>' + td(size) + td(p1(100 * d['leaf_acc'])) + td(p1(100 * d['tree_acc']))
                    + td(p1(100 * d['exact_match'])) + raw + '</tr>')
    if not rows:
        return ''
    t = table([('Encoder', ''), ('Parameters', 'n'), ('Leaf labels right (%)', 'n'), ('Tree labels right (%)', 'n'),
               ('All labels of the sentence right (%)', 'n'), ('Exact meaning', 'n hl'), ('Any analysis', 'n'), ('Gold among accepted', 'n')],
              rows, group=[('', 2), ('Tagging, dev', 3), ('Full pipeline from raw text, dev', 3)])
    body = t + cap('Same recipe for every encoder: Redwoods treebank only (86,278 sentences), forms as typed, 6 epochs, batch 32; '
                   'learning rate 3e-5 for BERT-base, 2e-5 for the large encoders. One run each. The best encoder will then be trained on all the data.')
    return fold('Encoders', 'Large encoders tag better; whether that carries to exact meaning is being measured.', body)


def exp_generated():
    path = f'{ORCA}/analysis/mrs/gen-pilot1-bothsurf-rawtext.json'
    if not os.path.exists(path):
        return ''
    import collections
    gdir = f'{ORCA}/data/generated/pilot1'
    tgt = {}
    for l in open(f'{gdir}/calls.jsonl'):
        c = json.loads(l)
        for s in c['sentences'] or []:
            tgt.setdefault(s.strip(), c['target'])
    sents = [l.rstrip('\n') for l in open(f'{gdir}/sentences.txt')]
    cnt = collections.defaultdict(collections.Counter)
    for r in json.load(open(path))['records']:
        t = tgt[sents[int(r['id'].split('/')[1]) - 1].strip()]
        for k in (t, 'all'):
            cnt[k]['n'] += 1
            cnt[k]['mrs'] += bool(r['accepted'])
            cnt[k]['same'] += bool(r['same MRS'])
    order = sorted((k for k in cnt if k != 'all'), key=lambda k: cnt[k]['same'] / cnt[k]['n'])
    rows = [f'<tr><td>{k.replace("-", " ").capitalize()}</td>' + td(f"{cnt[k]['n']:,}") + td(pct(cnt[k]['same'], cnt[k]['n']), True)
            + td(pct(cnt[k]['mrs'], cnt[k]['n'])) + '</tr>' for k in order]
    rows.append('<tr><td><b>All generated</b></td>' + td(f"{cnt['all']['n']:,}") + td(pct(cnt['all']['same'], cnt['all']['n']), True)
                + td(pct(cnt['all']['mrs'], cnt['all']['n'])) + '</tr>')
    rows.append('<tr><td>Dev, for comparison (gold: annotators)</td>' + td(f'{N:,}') + td(pct(ORACLE['counts']['same MRS'], N), True)
                + td(pct(ORACLE['counts']['with MRS'], N)) + '</tr>')
    t = table([('Phenomenon targeted', ''), ('Sentences', 'n'), ('Same MRS as ACE', 'n hl'), ('Any analysis', 'n')], rows)
    body = t + cap('Claude Sonnet wrote sentences for ten phenomena where Orca misses (20 calls, $1.71 API-equivalent, 1,982 sentences); '
                   'ACE parsed 1,940 and 1,932 replay. Orca (forms as typed, from raw text) is compared with ACE\'s first-ranked parse, '
                   'which nobody has checked. In a hand-checked sample of unknown-word misses, ACE itself is often wrong '
                   '(a food noun analyzed as an adverb, a plural noun as a verb), so these parses need filtering before they are used for training.')
    return fold('Generated sentences', 'Targeted sentences are harder than dev; unknown words most of all.', body)


def exp_examples():
    steps = open(os.path.join(HERE, 'steps-legend.html')).read()
    body = steps + '    <div id="examples" class="stack" style="gap:28px"></div>\n'
    return fold('Four worked examples', 'Labels, tree, feature structure, MRS and DMRS for real dev sentences.', body)


CSS = '''
/* folds and diagrams */
details.fold { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }
details.fold > summary { cursor: pointer; list-style: none; padding: 14px 18px; display: flex; flex-wrap: wrap; gap: 4px 14px; align-items: baseline; }
details.fold > summary::-webkit-details-marker { display: none; }
details.fold > summary::before { content: "▸"; color: var(--accent); width: 1em; }
details.fold[open] > summary::before { content: "▾"; }
details.fold .ft { font-family: var(--display); font-weight: 600; font-size: 1.1rem; }
details.fold .fs { color: var(--muted); font-size: 0.92rem; }
details.fold .fb { padding: 0 18px 18px; }
svg.diag { width: 100%; min-width: 760px; height: auto; display: block; }
svg.diag .bx { fill: var(--surface); stroke: var(--line); stroke-width: 1.2; }
svg.diag .bx.nn { fill: var(--lex-soft); stroke: var(--lex); }
svg.diag .bx.gr { fill: var(--accent-soft); stroke: var(--accent); }
svg.diag .bx.io { fill: var(--well); }
svg.diag .bx.lf { fill: var(--lex-soft); stroke: transparent; }
svg.diag .bx.tr { fill: var(--accent-soft); stroke: transparent; }
svg.diag .bt { font-family: var(--display); font-size: 15px; font-weight: 600; fill: var(--fg); }
svg.diag .bs { font-family: var(--body); font-size: 11.5px; fill: var(--muted); }
svg.diag .bm { font-family: var(--mono); font-size: 11.5px; fill: var(--accent); }
svg.diag .lt { fill: var(--fg); }
svg.diag .ar { stroke: var(--muted); stroke-width: 1.4; fill: none; }
svg.diag .ah { fill: var(--muted); }
svg.diag .dot { fill: var(--lex); }
.specs { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; font-size: 0.9rem; }
.specs > span:nth-child(odd) { font-family: var(--body); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }
'''


def rebuild(s):
    s = s.replace('<h1>How a sentence gets its analysis, on four real examples</h1>', '<h1>Fast HPSG parsing by proposing and checking derivations</h1>')
    i = s.index('<p class="lede">')
    j = s.index('</p>', i) + 4
    s = s[:i] + ('<p class="lede">A neural tagger proposes a complete derivation of the English Resource Grammar; the grammar '
                 'replays it by unification and accepts it or says where it breaks. Accepted derivations give the full '
                 'feature structure and the MRS.</p>') + s[j:]
    start = s.index('</header>') + len('</header>\n')
    end = s.index('</div>\n\n<script>')
    body = ('\n' + tiles() + '\n' + how() + '\n' + results() + '\n  <section class="stack">\n    <h2>Experiments</h2>\n'
            + exp_training() + exp_encoders() + exp_generated() + exp_rawtext() + exp_ace() + exp_llm() + exp_llm_rank() + exp_examples() + '  </section>\n\n')
    s = s[:start] + body + s[end:]
    if 'details.fold' not in s:
        s = s.replace('</style>', CSS + '</style>', 1)
    return s


if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = open(p).read()
        open(p, 'w').write(rebuild(s))
        print('rebuilt', p)
