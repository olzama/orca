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
BEST_KEY, BEST_NAME = 'debertav3large', 'DeBERTa-v3 large tagger, all data'
BEST = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothsurf-{BEST_KEY}-rawtext.json'))      # best tagger from raw text
BEST_PROPS = f'{ORCA}/analysis/mrs/dev-2025bothsurf-{BEST_KEY}-properties.json'
BEST_JUDGE = f'{ORCA}/analysis/adjudicate/dev-bothsurf-{BEST_KEY}/score.json'
ACE_JUDGE = f'{ORCA}/analysis/adjudicate/dev-ace/score.json'
RAW_HALF = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothhalfsurf-rawtext.json'))
OLD_ORACLE = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothall-rawtext-oracle.json'))
METRICS = json.load(open(f'{ORCA}/data/models/tagger-2025bothsurf-debertav3large/metrics.json'))   # the best tagger
LABELS = json.load(open(f'{ORCA}/data/models/tagger-2025bothsurf-debertav3large/labels.json'))
# From treebank tokens: rerank.py on data/models/tagger-2025bothall-bert/dev-strict-k30-b600.jsonl
TREEBANK_SPLIT = (1511, 80, 237, 234)
# analysis/raw-tokens-dev.json (scripts/check_raw_tokens.py)
RAW_CHECK = (('Gold derivation replays over raw-text tokens', 2056), ('… with the gold MRS', 2056),
             ('Word forms as in the treebank', 1838), ('… ignoring case', 2003))


def ms(step, run=None):
    run = run or BEST
    return 1000 * run['seconds by step'][step] / run['counts']['sentences']


def fold(title, takeaway, body, open_=False):
    return (f'  <details class="fold"{" open" if open_ else ""}>\n'
            f'    <summary><span class="ft">{title}</span><span class="fs">{takeaway}</span></summary>\n'
            f'    <div class="fb stack">\n{body}    </div>\n  </details>\n')


def cap(text):
    return f'    <p class="caption">{text}</p>\n'


def notes(*items):
    """Short notes under a table, one point each."""
    return '    <ul class="notes">\n' + ''.join(f'      <li>{x}</li>\n' for x in items) + '    </ul>\n'


def load(path):
    return json.load(open(path)) if os.path.exists(path) else None


def tiles():
    c = BEST['counts']
    ace_sps = N / (ACE_PASS + ACE_RETRY)
    jd = load(BEST_JUDGE)
    pr = load(BEST_PROPS)
    t = [('main', f'{100 * c["same MRS"] / N:.1f}%', 'exactly the gold meaning (predicates, arguments, scope), from raw text'),
         ('', f'{100 * pr["same with properties"] / N:.1f}%' if pr else '…', 'the same, with tense, number and information structure too'),
         ('', f'{100 * (c["same MRS"] + jd["verdicts"]["orca"] + jd["verdicts"]["both"]) / N:.1f}%' if jd else '…',
          'right according to the LLM judge' + ('' if jd else ' (being judged)')),
         ('', f'{100 * c["with MRS"] / N:.1f}%', 'get a full analysis the grammar accepts'),
         ('', f'{BEST["sentences per second"]:.1f}', f'sentences per second (ACE: {ace_sps:.1f})')]
    return ('  <section class="stack">\n    <div class="tiles">\n'
            + ''.join(f'      <div class="tile {k}"><b>{v}</b><span>{d}</span></div>\n' for k, v, d in t)
            + '    </div>\n'
            + cap(f'English Resource Grammar (2025), Redwoods dev: {N:,} unseen sentences. {BEST_NAME}. '
                  f'ACE, the grammar\'s chart parser: {100 * T["ace"]["all"]["same MRS"] / N:.1f}% exact.')
            + '  </section>\n')


def na(text):
    """A cell with no number yet: say why (queued, running, not measured, ...)."""
    return f'<span class="na">{text}</span>'


def summary():
    """One table across the evaluations, then the main findings in words (numbers stay in the table)."""
    oc = BEST['counts']
    jd, props, aj = load(BEST_JUDGE), load(BEST_PROPS), load(ACE_JUDGE)
    bj = load(f'{ORCA}/analysis/adjudicate/dev-bothsurf/score.json')
    ace = T['ace']['all']
    grp = lambda text: f'<tr><td colspan="7"><i>{text}</i></td></tr>'
    row = lambda name, n, *cells: (f'<tr><td>{name}</td>' + td(f'{n:,}')
                                   + ''.join(td(c, i in (0, 2)) for i, c in enumerate(cells)) + '</tr>')
    rows = [grp('Redwoods dev (e-mails, Wikipedia), compared with the annotators\' gold'),
            row('&nbsp;&nbsp;Orca (DeBERTa-v3 large), from raw text', N, pct(oc['same MRS'], N),
                pct(props['same with properties'], N) if props else na('running'),
                pct(oc['same MRS'] + jd['verdicts']['orca'] + jd['verdicts']['both'], N) if jd else na('being judged'),
                pct(oc['with MRS'], N), f"{BEST['sentences per second']:.1f}"),
            row('&nbsp;&nbsp;Orca (BERT-base), from raw text', N, pct(ORACLE['counts']['same MRS'], N),
                pct(load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-properties.json')['same with properties'], N),
                pct(ORACLE['counts']['same MRS'] + bj['verdicts']['orca'] + bj['verdicts']['both'], N),
                pct(ORACLE['counts']['with MRS'], N), f"{ORACLE['sentences per second']:.1f}"),
            row('&nbsp;&nbsp;ACE, first-ranked parse', N, pct(ace['same MRS'], N),
                pct(load(f'{ORCA}/analysis/mrs/dev-ace-properties.json')['same with properties'], N) if load(f'{ORCA}/analysis/mrs/dev-ace-properties.json') else na('not measured'),
                pct(ace['same MRS'] + aj['verdicts']['orca'] + aj['verdicts']['both'], N) if aj else na('being judged'),
                pct(ace['with MRS'], N), f'{N / (ACE_PASS + ACE_RETRY):.1f}')]
    cnt, verdicts, _, labels = gen_counts()
    if verdicts:
        g = cnt['all']
        lo = g['agree'] + g['reference'] + g['both']
        hi = lo + g['none'] + g['scope']
        rows += [grp(f'Generated sentences on hard phenomena (rounds 1 to {len(labels)}), '
                     'compared with ACE\'s first-ranked parse, which nobody checked'),
                 row('&nbsp;&nbsp;Orca (BERT-base), from raw text', g['n'], pct(g['agree'], g['n']), na('not measured'), pct(g['agree'] + g['orca'] + g['both'], g['n']),
                     pct(g['mrs'], g['n']), na('not measured')),
                 row('&nbsp;&nbsp;ACE, first-ranked parse', g['n'], na('the reference'), na('the reference'),
                     f'{100 * lo / g["n"]:.1f}–{100 * hi / g["n"]:.1f}%', pct(g['n'], g['n']), na('not measured'))]
    t = table([('Text and parser', ''), ('Sentences', 'n'), ('Same meaning as the reference', 'n hl'), ('… with tense, number and information structure too', 'n hl'),
               ('Right according to the LLM judge', 'n hl'), ('Any analysis', 'n'), ('Sentences per second', 'n')], rows)
    c = notes('<b>… with tense, number and information structure too:</b> the variable properties (tense, aspect, mood, sentence force, number, person, gender) and ICONS must match as well; ICONS never break a match for either parser.',
              '<b>Same meaning as the reference:</b> on dev the reference is gold; on generated text it is ACE\'s unchecked first parse.',
              '<b>Right according to the LLM judge:</b> same meaning, or the judge (Claude Opus) accepts this parser\'s reading where they differ.',
              '<b>ACE on generated text:</b> a range; sentences the judge never saw count as wrong for the low end, right for the high end.',
              'Agreements between Orca and ACE count as right; checking them was inconclusive (<i>Generated sentences</i>).')
    finds = ['<b>Exact match understates Orca:</b> the judge often accepts Orca\'s reading where it differs (<i>Generated sentences</i>).',
             '<b>Losses are in proposing</b>, not ranking, and grow with length (<i>Where the wrong sentences go wrong</i>).',
             '<b>Bigger encoders help</b>, even with all the data (<i>Encoders</i>).',
             '<b>Faster than ACE</b>, but more sentences get no analysis (<i>Orca and ACE</i>).',
             '<b>Wrong agreement is turned down</b>; ACE finds strained readings instead (<i>Agreement after distracting material</i>).',
             '<b>LLMs help offline</b> (repair, judging), <b>not online</b> (<i>LLM repair</i>, <i>LLM choosing among readings</i>).']
    return ('  <section class="stack">\n    <h2>Where Orca stands</h2>\n' + t + c
            + '    <ul class="finds">\n' + ''.join(f'      <li>{x}</li>\n' for x in finds) + '    </ul>\n  </section>\n')


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
    svg.append('<text class="bt" x="450" y="90" text-anchor="middle">DeBERTa-v3 large encoder, fine-tuned</text>')
    svg.append('<text class="bs" x="450" y="108" text-anchor="middle">SentencePiece subwords · 24 layers · 1,024 dimensions · 435M parameters</text>')
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
        ('Training data', '590,721 sentences: Redwoods treebank (86,278) and ACE parses of literary and news text, checked by replay; word forms as typed'),
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
            + cap('No chart: the tagger proposes a complete derivation; the grammar checks it by unification. Times: average per dev sentence, from raw text.')
            + '    <h3>The tagger</h3>\n'
            f'    <div class="scroll pad">{tagger_svg()}</div>\n'
            f'    <div class="kv specs">{kv}</div>\n'
            + '    <h3>A derivation as two labels per word</h3>\n' + enc_t
            + cap('Tree labels fix one binary tree: depth change and rule of the node joining each word to the next (after Gómez-Rodríguez and Vilares 2018).')
            + '  </section>\n')


def split(run):
    out = [0, 0, 0, 0]
    for x in run['records']:
        out[3 if not x['accepted'] else 2 if not x['gold among accepted'] else 0 if x['same MRS'] else 1] += 1
    return out


def results():
    bert, best = ORACLE['counts'], BEST['counts']
    ace = T['ace']['all']
    rows = [f'<tr><td>ACE (chart parser)</td>' + td(pct(ace['same MRS'], N), True) + td(pct(ace['with MRS'], N))
            + td(f'{N / (ACE_PASS + ACE_RETRY):.1f}') + td(na('no tagger')) + '</tr>',
            f'<tr><td>Orca, BERT-base tagger</td>' + td(pct(bert['same MRS'], N), True) + td(pct(bert['with MRS'], N))
            + td(f"{ORACLE['sentences per second']:.1f}") + td(f'{ms("tag", ORACLE):.0f}') + '</tr>',
            f'<tr><td><b>Orca, DeBERTa-v3 large tagger</b></td>' + td(pct(best['same MRS'], N), True) + td(pct(best['with MRS'], N))
            + td(f"{BEST['sentences per second']:.1f}") + td(f'{ms("tag"):.0f}') + '</tr>']
    t1 = table([('Parser', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Sentences per second', 'n'),
                ('Tagger ms per sentence', 'n')], rows)
    # where each sentence ends up
    n_by = {}
    for l in open(f'{ORCA}/data/encoded-2025/dev.jsonl'):
        r = json.loads(l)
        n_by[r['id']] = len(r['tokens'])
    bands = ((0, 10, 'under 10'), (10, 20, '10 to 19'), (20, 30, '20 to 29'), (30, 10 ** 6, '30 and over'))
    cnt = {b: [0, 0, 0, 0, 0] for _, _, b in bands}
    for x in BEST['records']:
        b = next(nm for lo, hi, nm in bands if lo <= n_by[x['id']] < hi)
        k = 3 if not x['accepted'] else 2 if not x['gold among accepted'] else 0 if x['same MRS'] else 1
        cnt[b][k] += 1
        cnt[b][4] += 1
    tot = [sum(cnt[b][i] for b in cnt) for i in range(4)]

    def mrow(name, v):
        n = sum(v[:4])
        return f'<tr><td>{name}</td>' + td(f'{n:,}') + ''.join(td(pct(x, n), i == 0) for i, x in enumerate(v[:4])) + '</tr>'
    rows = [mrow('BERT-base tagger', split(ORACLE)),
            mrow('<b>DeBERTa-v3 large tagger</b>', tot)]
    say = {'under 10': 'under 10 words', '10 to 19': '10 to 19 words', '20 to 29': '20 to 29 words', '30 and over': '30 words or more'}
    rows += [mrow(f'&nbsp;&nbsp;… of which sentences of {say[b]}', cnt[b]) for _, _, b in bands]
    t2 = table([('Tagger', ''), ('Sentences', 'n'), ('Right meaning chosen', 'n hl'), ('Right meaning found, another chosen', 'n'),
                ('Analyses found, none right', 'n'), ('No analysis', 'n')], rows,
               group=[('', 2), ('Right meaning', 2), ('Wrong or missing', 2)])
    return ('  <section class="stack">\n    <h2>Where the wrong sentences go wrong</h2>\n' + t2
            + notes(f'All {N:,} dev sentences, from raw text; each row adds up to 100%. Gold derivations always replay to the gold MRS, so all loss is in the proposals.',
                    '<b>Found, another chosen:</b> a ranking error. <b>None right:</b> a proposing error. <b>No analysis:</b> the grammar rejected everything proposed.',
                    'Most of the loss is in proposing, and it grows with length.')
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
                    + td(pct(rc['gold MRS among accepted'], N)) + '</tr>')
    t2 = table([('Forms as typed, from raw text; tagger trained on', ''), ('Right meaning chosen', 'n hl'), ('Any analysis', 'n'),
                ('Right meaning among the analyses found', 'n')], rows)
    t = t + cap('BERT-base, treebank tokens.') + t2 + cap('BERT-base. Half the silver data, chosen at random, costs little.')
    body = t + notes('Silver data: ACE\'s first parses of novels (1838 to 1921) and news (NYT 2023, 2025), with LLM-written counterparts, kept if they replay.',
                     'One run each; seed variation not measured.')
    return fold('Training data', 'More grammar-licensed text helped up to now; halving it costs little.', body)


def exp_rawtext():
    rows = [f'<tr><td>{k}</td>{td(pct(v, N), True)}</tr>' for k, v in RAW_CHECK]
    t1 = table([(f'Check on all {N:,} dev sentences', ''), ('Share of sentences', 'n hl')], rows)
    steps = [('Tokens (ACE preprocessing, separate process)', 'tokens'), ('Tagger (GPU)', 'tag'),
             ('Replay and repair (one core)', 'repair'), ('Ranking', 'rank'), ('MRS', 'mrs')]
    rows = [f'<tr><td>{n}</td>{td(format(ms(k), ".1f"))}</tr>' for n, k in steps]
    rows.append(f'<tr><td><b>End to end</b></td>{td(format(1000 / BEST["sentences per second"], ".1f"), True)}</tr>')
    t2 = table([('DeBERTa-v3 large, from raw text', ''), ('ms per sentence', 'n hl')], rows)
    tb = T['bothall_best']['all']
    rows = [f'<tr><td>Treebank tokens and word forms (idealized: the annotators\' tokenization)</td>' + td(pct(tb['same MRS'], N), True) + td(pct(tb['with MRS'], N)) + '</tr>',
            f'<tr><td>Raw text, tagger trained on treebank word forms</td>' + td(pct(RAW['counts']['same MRS'], N), True) + td(pct(RAW['counts']['with MRS'], N)) + '</tr>',
            f'<tr><td>Raw text, tagger trained on forms as typed (used everywhere else)</td>' + td(pct(ORACLE['counts']['same MRS'], N), True) + td(pct(ORACLE['counts']['with MRS'], N)) + '</tr>']
    t0 = table([('BERT-base tagger, all data; input', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n')], rows)
    body = (t0 + cap('Treebank tokens are not available for new text; every other number on this page is from raw text.') + t1 + t2 + notes('Tokens come from ACE\'s preprocessing, without parsing; replay picks the token the lexical entry accepts.',
                            'Treebank word forms leak the analysis through capitalization; training on forms as typed removes the leak.'))
    return fold('From raw text', 'The grammar\'s tokens work; the tagger loses a little on capitalization.', body)


def exp_properties():
    p = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothsurf-properties.json'))
    n = p['sentences']
    pd = load(BEST_PROPS)
    ic = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-{BEST_KEY}-icons.json')
    rows = [f'<tr><td>Predicates, arguments and scope only</td>{td(pct(p["same without properties"], n), True)}'
            + td(pct(pd['same without properties'], n) if pd else na('running'), True) + '</tr>',
            f'<tr><td>… and also tense, aspect, mood, sentence force, number, person, gender</td>{td(pct(p["same with properties"], n), True)}'
            + td(pct(pd['same with properties'], n) if pd else na('running'), True) + '</tr>',
            f'<tr><td>… or instead ICONS (information structure: topic, focus)</td>{td(na("not measured"))}'
            + td(pct(ic['same with ICONS'], n) if ic else na('running'), True) + '</tr>']
    t1 = table([('What must match gold', ''), ('BERT-base', 'n hl'), ('DeBERTa-v3 large', 'n hl')], rows,
               group=[('', 1), ('Exact meaning, raw text, all data', 2)])
    lost = p['same without properties'] - p['same with properties']
    rows = [f'<tr><td>{k}</td>{td(pct(v, lost))}</tr>' for k, v in sorted(p['differ by kind'].items(), key=lambda kv: -kv[1])]
    t2 = table([(f'Sentences that stop matching ({lost})', ''), ('Share', 'n')], rows)
    body = (t1 + notes('Properties: features on MRS variables (TENSE, SF, NUM …), mapped as ACE does.',
                       f'ICONS: about one gold analysis in six has them ({ic["gold with ICONS"] if ic else "…"} of {n:,}). Requiring them loses no exact match: they follow from the derivation.' if ic else 'ICONS: being measured.')
            + t2 + cap('BERT-base. Each sentence counted once, under the first kind that differs. Sentence force: statement against question.'))
    return fold('Tense, number, information structure', 'Orca now outputs them; requiring them to match changes the headline little.', body)


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
    miss = lambda k: pct(N - T[k]['all']['with MRS'], N)
    rows = [f'<tr><td>ACE</td>{td(sps(N / (ACE_PASS + ACE_RETRY)), True)}{td("1 CPU core")}{td("up to 28 GB")}{td(miss("ace"))}</tr>',
            f'<tr><td>Orca</td>{td(sps(N / full1), True)}{td("1 GPU, 1 core")}{td("about 2 GB")}{td(miss("best"))}</tr>',
            f'<tr><td>Orca</td>{td(sps(N / full6), True)}{td("1 GPU, 6 cores")}{td("about 2 GB")}{td(miss("best"))}</tr>',
            f'<tr><td>Orca (DeBERTa-v3 large), from raw text</td>{td(format(BEST["sentences per second"], ".1f"), True)}{td("1 GPU, 1 core")}{td("about 3 GB")}{td(pct(N - BEST["counts"]["with MRS"], N))}</tr>',
            f'<tr><td>Orca + LLM repair</td>{td(sps(N / (full1 + LLM_SECS / STREAMS)), True)}{td(f"+ {STREAMS} model calls at a time")}{td("about 2 GB, plus the API")}{td(miss("best_llm"))}</tr>']
    speed = table([('System', ''), ('Sentences per second', 'n hl'), ('Hardware', 'n'), ('Memory', 'n'), ('Sentences with no analysis', 'n')], rows)
    rows = []
    for key, name in SYSTEMS[2:]:
        a = T[key]['all']
        rows.append(f'<tr><td>{name}</td>' + td(f"{a['with MRS']:,}") + td(pct(a['same MRS'], a['with MRS']), True)
                    + td(p1(a['preds']['precision'])) + td(p1(a['links']['precision'])) + '</tr>')
    prec = table([('System', ''), ('Sentences it analyzes', 'n'), ('Right meaning, of those', 'n hl'),
                  ('Its predicates that are in gold (%)', 'n'), ('Its links that are in gold (%)', 'n')], rows)
    body = (by_len + cap('BERT-base, treebank only, treebank tokens.')
            + speed + cap('Dev sentences average about 12 words. ACE\'s time includes retries with more memory.')
            + prec + cap('Only the sentences each system analyzes.'))
    return fold('Orca and ACE', 'Faster at every setting; behind on long sentences.', body)


def exp_llm():
    llm = open(os.path.join(HERE, 'llm-table.html')).read()
    rows = ['<tr><td>LLM repair (Claude Opus)</td>' + td(pct(188, 390)) + td(pct(89, 390), True) + td(sps(LLM_SENTS / LLM_SECS)) + td('about $0.35 per sentence') + '</tr>',
            '<tr><td>ACE</td>' + td(pct(388, 390)) + td(pct(270, 390), True) + td(sps(390 / 1315.0)) + td('none') + '</tr>']
    fb = table([('Fallback on the 390 sentences repair leaves', ''), ('Any analysis', 'n'), ('Right meaning', 'n hl'),
                ('Sentences per second', 'n'), ('Cost', 'n')], rows)
    body = (llm + cap('Claude Opus sees the failure points and the grammar\'s definitions; the grammar replays every answer. Costs are API-equivalent.')
            + fb + cap('ACE is the better fallback for English.'))
    return fold('LLM repair', 'Accepted analyses for about half the leftovers; slow; used offline only.', body)


def exp_llm_rank():
    path = f'{ORCA}/analysis/llm-rank/pilot1/score.json'
    if not os.path.exists(path):
        return ''
    r = json.load(open(path))
    rows = []
    for key, name in (('all', 'All'), ('margin under 1', '&nbsp;&nbsp;… of which the ranking model is unsure (score margin under 1)'), ('1 to 3', '&nbsp;&nbsp;… margin 1 to 3'), ('3 and over', '&nbsp;&nbsp;… margin 3 or more (the ranking model is sure)')):
        c = r['by margin'][key]
        rows.append(f'<tr><td>{name}</td>' + td(f"{c['sentences']:,}") + td(f"{c['readings'] / c['sentences']:.1f}")
                    + td(pct(c['maxent right'], c['sentences']), True) + td(pct(c['llm right'], c['sentences']), True) + '</tr>')
    t = table([('Dev sentences with two or more readings, the right one among them', ''), ('Sentences', 'n'), ('Readings per sentence', 'n'),
               ('Ranking model picks the right one', 'n hl'), ('LLM picks the right one', 'n hl')], rows)
    body = t + cap(f'A random 300 of 622. Readings shown by what sets them apart; Claude Opus picks one (${r["cost_usd"]:.2f}). Many misses are treebank conventions.')
    return fold('LLM choosing among readings', 'Below the grammar\'s ranking model at every margin.', body)


ENCODERS = (('bertbase', 'BERT-base (cased)', '110M'), ('robertalarge', 'RoBERTa-large', '355M'),
            ('xlmrlarge', 'XLM-R large', '560M'), ('debertav3large', 'DeBERTa-v3 large', '435M'))


def exp_encoders():
    rows = []
    for data, model, run, title in (('surf', '2025surf-{}', 'dev-2025surf-{}-rawtext.json', 'Redwoods treebank only (86,278 sentences)'),
                                    ('all', '2025bothsurf-{}', 'dev-2025bothsurf-{}-rawtext.json', 'All data (590,721 sentences)')):
        rows.append(f'<tr><td colspan="8"><i>{title}</i></td></tr>')
        for key, name, size in ENCODERS:
            k = 'bert' if (data == 'all' and key == 'bertbase') else key
            mp = f'{ORCA}/data/models/tagger-{model.format(k)}/metrics.json'
            rp = f'{ORCA}/analysis/mrs/' + ('dev-2025bothsurf-rawtext.json' if k == 'bert' else run.format(k))
            if os.path.exists(mp):
                d = json.load(open(mp))['dev']
                tag = td(p1(d['leaf_acc'])) + td(p1(d['tree_acc'])) + td(p1(d['exact_match']))
            else:
                tag = td(na('training')) + td('') + td('')
            if os.path.exists(rp):
                rc = json.load(open(rp))['counts']
                among = pct(rc['gold MRS among accepted'], N) if 'gold MRS among accepted' in rc else na('not measured')
                raw = td(pct(rc['same MRS'], N), True) + td(pct(rc['with MRS'], N)) + td(among)
            else:
                raw = td(na('evaluation queued')) + td(na('queued')) + td(na('queued'))
            rows.append(f'<tr><td>&nbsp;&nbsp;{name}</td>' + td(size) + tag + raw + '</tr>')
    t = table([('Encoder', ''), ('Parameters', 'n'), ('Leaf labels right (%)', 'n'), ('Tree labels right (%)', 'n'),
               ('Every label of the sentence right (%)', 'n'), ('Right meaning chosen', 'n hl'), ('Any analysis', 'n'), ('Right meaning among the analyses found', 'n')],
              rows, group=[('', 2), ('Tagging, dev', 3), ('Full pipeline from raw text, dev', 3)])
    body = t + cap('Same recipe for all: forms as typed, 6 epochs, batch 32, learning rate 3e-5 (BERT-base) or 2e-5. One run each.')
    return fold('Encoders', 'DeBERTa and XLM-R large lead, with the treebank alone and with all data.', body)


GEN_ROUNDS = (('pilot1', 'Round 1'), ('round2', 'Round 2'), ('round3', 'Round 3'))


def gen_counts():
    """Per round, per phenomenon and overall: sentences, analyses, and how each sentence came out
    (agree with ACE; judge says orca / reference / both / neither; none = Orca no analysis; scope = differ only in scope)."""
    import collections
    cnt = collections.defaultdict(collections.Counter)
    verdicts, info = {}, {}
    for rnd, label in GEN_ROUNDS:
        path = f'{ORCA}/analysis/mrs/gen-{rnd}-bothsurf-rawtext.json'
        if not os.path.exists(path):
            continue
        gdir = f'{ORCA}/data/generated/{rnd}'
        tgt = {}
        for l in open(f'{gdir}/calls.jsonl'):
            c = json.loads(l)
            for s in c['sentences'] or []:
                tgt.setdefault(s.strip(), c['target'])
        sents = [l.rstrip('\n') for l in open(f'{gdir}/sentences.txt')]
        vg = json.load(open(f'{ORCA}/analysis/adjudicate/gen-{rnd}/score.json'))
        verdicts[label] = vg
        recs = json.load(open(path))['records']
        info[label] = (len(sents), len(recs))
        for r in recs:
            t = tgt[sents[int(r['id'].split('/')[1]) - 1].strip()]
            x = 'agree' if str(r['same MRS']) == 'True' else vg['by_id'].get(r['id'], 'none' if not int(r['accepted'] or 0) else 'scope')
            for k in (t, label, 'all'):
                cnt[k]['n'] += 1
                cnt[k]['mrs'] += bool(int(r['accepted'] or 0))
                cnt[k][x] += 1
    return cnt, verdicts, info, [l for _, l in GEN_ROUNDS if l in verdicts]


def exp_generated():
    import collections
    cnt, verdicts, info, labels = gen_counts()
    if not verdicts:
        return ''
    right = lambda d: d['agree'] + d['orca'] + d['both']
    order = sorted((k for k in cnt if k not in labels and k != 'all'), key=lambda k: cnt[k]['agree'] / cnt[k]['n'])
    row = lambda name, d: (f'<tr><td>{name}</td>' + td(f"{d['n']:,}") + td(pct(d['agree'], d['n']))
                           + td(pct(right(d), d['n']), True) + td(pct(d['mrs'], d['n'])) + '</tr>')
    rows = ([row(f'<b>{l}</b>', cnt[l]) for l in labels] + [row('<b>All rounds</b>', cnt['all'])]
            + ['<tr><td colspan="5"><i>All rounds, by phenomenon targeted</i></td></tr>']
            + [row('&nbsp;&nbsp;' + k.replace('-', ' ').capitalize().replace('Pp ', 'PP '), cnt[k]) for k in order])
    t = table([('Generated sentences', ''), ('Sentences', 'n'), ('Same meaning as ACE\'s parse', 'n'), ('Right according to the LLM judge', 'n hl'),
               ('Any analysis', 'n')], rows)
    vd = json.load(open(f'{ORCA}/analysis/adjudicate/dev-bothsurf/score.json'))
    def jrow(name, v):
        n = sum(v.values())
        return (f'<tr><td>{name}</td>' + td(f'{n:,}') + td(pct(v['orca'], n), True) + td(pct(v['reference'], n), True)
                + td(pct(v.get('both', 0), n)) + td(pct(v.get('neither', 0), n)) + '</tr>')
    rows = [jrow(f'{l}: generated; the reference is ACE\'s first-ranked parse', verdicts[l]['verdicts']) for l in labels]
    rows.append(jrow('Dev sentences; the reference is the annotators\' gold', vd['verdicts']))
    t2 = table([('Sentences where Orca and the reference mean different things', ''), ('Sentences', 'n'), ('Orca\'s reading is right', 'n hl'),
                ('The reference is right', 'n hl'), ('Both are acceptable', 'n'), ('Neither is right', 'n')], rows,
               group=[('', 2), ('The judge says', 4)])
    cost = sum(v['cost_usd'] for v in verdicts.values()) + vd['cost_usd']
    sizes = '; '.join(f'{l}: {a:,} written, {b:,} parsed by ACE and replayable' for l, (a, b) in info.items())
    body = (t + notes('Claude Sonnet wrote the sentences. Round 1: ten phenomena; round 2: the seven hardest; round 3: agreement, control against raising, four of the hardest.',
                      'Kept if ACE parses them and Orca can replay the parse. Orca: BERT-base, from raw text; reference: ACE\'s unchecked first parse.')
            + t2 + notes(f'Claude Opus sees the two readings in random order, each by what the other lacks (${cost:.2f} in all).',
                         'On generated text ACE\'s first parse is a weak reference, so training uses the judged reading.'))
    ap = f'{ORCA}/analysis/agreements/gen-r12/score.json'
    if os.path.exists(ap):
        a = json.load(open(ap))
        its = [json.loads(l) for l in open(f'{ORCA}/analysis/agreements/gen-r12/items.jsonl')]
        bins = {'2 to 4': collections.Counter(), '5 to 8': collections.Counter()}
        for it in its:
            c = bins['2 to 4' if len(it['readings']) <= 4 else '5 to 8']
            c['n'] += 1
            c[a['by_id'].get(it['id'])] += 1
        al = collections.Counter()
        for c in bins.values():
            al.update(c)
        arow = lambda name, c: (f'<tr><td>{name}</td>' + td(f"{c['n']:,}") + td(pct(c['shared reading'], c['n']), True)
                                + td(pct(c['another reading'], c['n'])) + td(pct(c['none right'], c['n'])) + '</tr>')
        lr = json.load(open(f'{ORCA}/analysis/llm-rank/pilot1/score.json'))['by margin']['all']
        rows = ([arow('<b>All</b>', al)] + [arow(f'&nbsp;&nbsp;… {k} readings shown', c) for k, c in bins.items()]
                + [f'<tr><td>For comparison: dev, about {lr["readings"] / lr["sentences"]:.0f} readings shown, gold among them</td>' + td(f"{lr['sentences']:,}")
                   + td(pct(lr['llm right'], lr['sentences']), True) + td(pct(lr['sentences'] - lr['llm right'], lr['sentences'])) + td(na('not offered')) + '</tr>'])
        t3 = table([('Generated sentences where Orca and ACE agree, a random sample', ''), ('Sentences', 'n'),
                    ('Judge picks the shared reading', 'n hl'), ('Judge picks another reading', 'n'), ('Judge says none is right', 'n')], rows)
        body += ('    <h3>Checking the agreements</h3>\n' + t3
                 + notes(f'Rounds 1 and 2. Readings: up to eight distinct meanings from ACE\'s 30 best parses, in random order (${a["cost_usd"]:.2f}).',
                         'Inconclusive: the judge is unreliable when choosing among many readings, as the dev row shows.'))
    return fold('Generated sentences', 'Harder than dev; ACE\'s own parses of them are often wrong.', body)


def exp_agreement():
    path = f'{ORCA}/analysis/agreement-attractors/score.json'
    if not os.path.exists(path):
        return ''
    s = json.load(open(path))
    def row(name, e, key):
        g, u = s[f'e{e}|grammatical|{key}'], s[f'e{e}|ungrammatical|{key}']
        n, m = g['n'], u['n']
        return (f'<tr><td>{name}</td>' + td(f'{n:,}') + td(pct(g.get('accepted at first try', 0), n))
                + td(pct(g['orca analysis'], n)) + td(pct(g['same as ace'], n), True)
                + td(pct(m - u['orca analysis'], m), True) + td(pct(m - u['ace analysis'], m)) + '</tr>')
    grp = lambda t: f'<tr><td colspan="7"><i>{t}</i></td></tr>'
    ind = '&nbsp;&nbsp;'
    rows = ([grp('Experiment 1: subject, then verb; sometimes after a long clause with a noun of its own'), row('<b>All</b>', 1, 'all'),
             row(ind + 'No clause before the subject', 1, 'no top clause'),
             row(ind + 'A clause before it, whose noun has the subject\'s number', 1, 'top clause, attractor matches'),
             row(ind + 'A clause before it, whose noun has the other number', 1, 'top clause, attractor mismatches'),
             grp('Experiment 2: clefted subject, separated from its verb by embedded clauses'), row('<b>All</b>', 2, 'all')]
            + [row(ind + f'{k} embedded clause{"s" if k > 1 else ""}', 2, f'level {k}') for k in (1, 2, 3, 4)])
    t = table([('Stimuli', ''), ('Sentences of each kind', 'n'), ('Orca\'s first guess accepted', 'n'), ('Orca finds an analysis', 'n'),
               ('Same meaning as ACE', 'n hl'), ('Orca finds no analysis', 'n hl'), ('ACE finds no analysis', 'n')], rows,
              group=[('', 2), ('Verb agrees with the subject', 3), ('Verb does not agree', 2)])
    body = t + notes('Chaves and Richter (2021) stimuli, each filled with the agreeing and the non-agreeing verb. Orca: BERT-base, raw text.',
                     'ACE\'s readings make the verb agree with something else: <i>A scientist … said I thought the boys is lost</i> (the scientist is lost).',
                     'A clause before the subject makes first guesses fail more often; the number of its noun does not matter.')
    return fold('Agreement after distracting material', 'Wrong agreement is turned down; ACE finds strained readings that Orca does not.', body)


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
ul.finds { margin: 0; padding-left: 1.2em; display: flex; flex-direction: column; gap: 6px; }
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
    body = ('\n' + tiles() + '\n' + summary() + '\n' + how() + '\n' + results() + '\n  <section class="stack">\n    <h2>Experiments</h2>\n'
            + exp_training() + exp_encoders() + exp_generated() + exp_agreement() + exp_rawtext() + exp_properties() + exp_ace() + exp_llm() + exp_llm_rank() + exp_examples() + '  </section>\n\n')
    s = s[:start] + body + s[end:]
    if 'details.fold' not in s:
        s = s.replace('</style>', CSS + '</style>', 1)
    if 'ul.finds' not in s:
        s = s.replace('</style>', 'ul.finds { margin: 0; padding-left: 1.2em; display: flex; flex-direction: column; gap: 6px; }\n</style>', 1)
    if 'ul.notes' not in s:
        s = s.replace('</style>', 'ul.notes { margin: 0; padding-left: 1.1em; font-size: 0.85rem; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }\n</style>', 1)
    if 'span.na' not in s:
        s = s.replace('</style>', 'span.na { color: var(--muted); font-style: italic; font-size: 0.85em; }\n</style>', 1)
    return s


if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = open(p).read()
        open(p, 'w').write(rebuild(s))
        print('rebuilt', p)
