"""Rebuild the body of the Orca walkthrough page from measured data.

Everything between </header> and the page script is regenerated: a short
visible part (headline numbers, pipeline, tagger, label encoding, results,
where the misses are) and one folded section per experiment. The worked
examples (drawn by the page script into #examples) sit in the last fold.

Usage: make_page.py PAGE.html   (rewrites the page in place)
"""
import collections
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
BEST_RUN = f'{BEST_KEY}-minprob001'   # current parser defaults (lookup fixes, MRS read as ACE does, faster repair, repair cutoff 0.001)
BEST = json.load(open(f'{ORCA}/analysis/mrs/dev-2025bothsurf-{BEST_KEY}-rawtext-minprob001.json'))
BEST_PROPS = f'{ORCA}/analysis/mrs/dev-2025bothsurf-{BEST_RUN}-properties.json'
BEST_ICONS = f'{ORCA}/analysis/mrs/dev-2025bothsurf-{BEST_RUN}-icons.json'
BEST_JUDGE = f'{ORCA}/analysis/adjudicate/dev-bothsurf-{BEST_RUN}/score.json'
BERT_NEW = f'{ORCA}/analysis/mrs/dev-2025bothsurf-rawtext-normlocate.json'
# Hausa: Orca's MRS against ACE's on the 357 parses of rounds 1-2 (commit 03fc7ea): same without properties, with properties and ICONS
HAUSA_MRS = (357, 343, 343)
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
    t = [('main', f'{100 * c["same MRS"] / N:.1f}%', 'exactly the gold meaning (predicates, arguments, scope: the usual measure in parsing work), from raw text'),
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
    bn, bp, bbj = load(BERT_NEW), load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-normlocate-rootcheck-properties.json'), load(f'{ORCA}/analysis/adjudicate/dev-bothsurf-normlocate/score.json')
    ace = T['ace']['all']
    grp = lambda text: f'<tr><td colspan="7"><i>{text}</i></td></tr>'
    row = lambda name, n, *cells: (f'<tr><td>{name}</td>' + td(f'{n:,}')
                                   + ''.join(td(c, i in (0, 2)) for i, c in enumerate(cells)) + '</tr>')
    rows = [grp('Redwoods dev (e-mails, Wikipedia), compared with the annotators\' gold'),
            row('&nbsp;&nbsp;Orca (DeBERTa-v3 large), from raw text', N, pct(oc['same MRS'], N),
                pct(props['same with properties'], N) if props else na('running'),
                pct(oc['same MRS'] + jd['verdicts']['orca'] + jd['verdicts']['both'], N) if jd else na('being judged'),
                pct(oc['with MRS'], N), f"{BEST['sentences per second']:.1f}"),
            (row('&nbsp;&nbsp;Orca (BERT-base), from raw text', N, pct(bn['counts']['same MRS'], N),
                 pct(bp['same with properties'], N) if bp else na('running'),
                 pct(bn['counts']['same MRS'] + bbj['verdicts']['orca'] + bbj['verdicts']['both'], N) if bbj else na('being judged'),
                 pct(bn['counts']['with MRS'], N), f"{bn['sentences per second']:.1f}") if bn else
             row('&nbsp;&nbsp;Orca (BERT-base), from raw text', N, na('re-running with the lookup fixes'), na('re-running'), na('re-running'), na('re-running'), na('re-running'))),
            row('&nbsp;&nbsp;ACE, first-ranked parse', N, pct(ace['same MRS'], N),
                pct(load(f'{ORCA}/analysis/mrs/dev-ace-properties.json')['same with properties'], N) if load(f'{ORCA}/analysis/mrs/dev-ace-properties.json') else na('not measured'),
                pct(ace['same MRS'] + aj['verdicts']['orca'] + aj['verdicts']['both'], N) if aj else na('being judged'),
                pct(ace['with MRS'], N), f'{N / (ACE_PASS + ACE_RETRY):.1f}')]
    cnt, verdicts, _, labels = gen_counts()
    if verdicts:
        g = cnt['all']
        gb = gen_counts('')[0]['all']
        lo = g['agree'] + g['reference'] + g['both']
        hi = lo + g['none'] + g['scope']
        rows += [grp(f'Generated sentences on hard phenomena (rounds 1 to {len(labels)}), '
                     'compared with ACE\'s first-ranked parse, which nobody checked'),
                 row('&nbsp;&nbsp;Orca (DeBERTa-v3 large), from raw text', g['n'], pct(g['agree'], g['n']), na('not measured'), pct(g['agree'] + g['orca'] + g['both'], g['n']),
                     pct(g['mrs'], g['n']), na('not measured')),
                 row('&nbsp;&nbsp;Orca (BERT-base), from raw text', gb['n'], na('not re-run with the lookup fixes'), na('not measured'), na('not re-run'), na('not re-run'), na('not measured')),
                 row('&nbsp;&nbsp;ACE, first-ranked parse', g['n'], na('the reference'), na('the reference'),
                     f'{100 * lo / g["n"]:.1f}–{100 * hi / g["n"]:.1f}%', pct(g['n'], g['n']), na('not measured'))]
    t = table([('Text and parser', ''), ('Sentences', 'n'), ('Same meaning as the reference', 'n hl'), ('… with tense, number and information structure too', 'n hl'),
               ('Right according to the LLM judge', 'n hl'), ('Any analysis', 'n'), ('Sentences per second', 'n')], rows)
    c = notes('<b>… with tense, number and information structure too:</b> the variable properties (tense, aspect, mood, sentence force, number, person, gender) and ICONS must match as well; ICONS never break a match for either parser.',
              '<b>Same meaning as the reference:</b> on dev the reference is gold; on generated text it is ACE\'s unchecked first parse.',
              '<b>Run-to-run spread:</b> a second training run of the same tagger, with another random seed, gets about one point less exact meaning on dev (<i>Generated sentences</i>).',
              '<b>Comparing with other work:</b> most semantic parsing evaluation scores predicates and arguments only (SDP\'s DM, AMR\'s Smatch, CCG dependencies, EDM<sub>NA</sub>), as the first column does; full EDM and MRP\'s EDS score count properties too.',
              '<b>Right according to the LLM judge:</b> same meaning, or the judge (Claude Opus) accepts this parser\'s reading where they differ.',
              '<b>ACE on generated text:</b> a range; sentences the judge never saw count as wrong for the low end, right for the high end.',
              'Agreements between Orca and ACE count as right; checking them was inconclusive (<i>Generated sentences</i>).')
    finds = ['<b>Exact match understates Orca:</b> the judge often accepts Orca\'s reading where it differs (<i>Generated sentences</i>).',
             '<b>Losses are in proposing</b>, not ranking, and grow with length (<i>Where the wrong sentences go wrong</i>).',
             '<b>The tagger plus a chart</b> (ACE restricted to the tagger\'s lexical entries) beats replay by about five points, at almost three times ACE\'s speed (<i>The tagger plus a chart</i>).',
             '<b>ACE as a fallback</b> where Orca finds nothing lifts exact meaning by five points, still over twice ACE\'s speed (<i>Orca with ACE as a fallback</i>).',
             '<b>Bigger encoders help</b>, even with all the data (<i>Encoders</i>).',
             '<b>Training on judged generated sentences</b> makes no difference beyond what a second run of the same setup does (<i>Generated sentences</i>).',
             '<b>Other grammars work:</b> Orca replays every Hausa parse ACE finds and nearly all of the Spanish treebank (<i>Another grammar: Hausa</i>, <i>Spanish</i>).',
             '<b>Faster than ACE</b>, but more sentences get no analysis (<i>Orca and ACE</i>).',
             '<b>Where ACE runs out of memory</b>, Orca still gives a right or partly right reading almost every time (<i>Where ACE fails</i>).',
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
    bb = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-bert-current-breakdown.json')
    bv = [0, 0, 0, 0]
    for x in (bb or {}).get('records', []):
        bv[3 if not x['accepted'] else 2 if not x['gold among accepted'] else 0 if x['same MRS'] else 1] += 1
    rows = [mrow('BERT-base tagger', bv) if bb else f'<tr><td>BERT-base tagger</td>' + td(na('re-running with the current parser')) * 5 + '</tr>',
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
    ic = load(BEST_ICONS)
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
                       'The first row is what most parsing work compares (SDP\'s DM, AMR\'s Smatch, CCG dependencies, EDM<sub>NA</sub>); the second is closer to full EDM and MRP\'s EDS score.',
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
    body += exp_ensemble()
    return fold('Encoders', 'DeBERTa and XLM-R large lead, with the treebank alone and with all data.', body)


GEN_ROUNDS = (('pilot1', 'Round 1'), ('round2', 'Round 2'), ('round3', 'Round 3'))


def gen_counts(key=f'{BEST_KEY}-normlocate'):
    """Per round, per phenomenon and overall: sentences, analyses, and how each sentence came out
    (agree with ACE; judge says orca / reference / both / neither; none = Orca no analysis; scope = differ only in scope)."""
    import collections
    cnt = collections.defaultdict(collections.Counter)
    verdicts, info = {}, {}
    for rnd, label in GEN_ROUNDS:
        path = f'{ORCA}/analysis/mrs/gen-{rnd}-bothsurf{"-" + key if key else ""}-rawtext.json'
        if not os.path.exists(path):
            continue
        gdir = f'{ORCA}/data/generated/{rnd}'
        tgt = {}
        for l in open(f'{gdir}/calls.jsonl'):
            c = json.loads(l)
            for s in c['sentences'] or []:
                tgt.setdefault(s.strip(), c['target'])
        sents = [l.rstrip('\n') for l in open(f'{gdir}/sentences.txt')]
        vg = json.load(open(f'{ORCA}/analysis/adjudicate/gen-{rnd}{"-" + key if key else ""}/score.json'))
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
    vd = load(BEST_JUDGE) or load(f'{ORCA}/analysis/adjudicate/dev-bothsurf-{BEST_KEY}-normlocate/score.json')   # the previous run's verdicts while the current one is judged
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
                      f'Kept if ACE parses them and Orca can replay the parse. Orca: {BEST_NAME}, from raw text; reference: ACE\'s unchecked first parse.')
            + t2 + notes(f'Claude Opus sees the two readings in random order, each by what the other lacks (${cost:.2f} in all).',
                         'On generated text ACE\'s first parse is a weak reference, so training uses the judged reading.'))
    m0, m1 = (load(f'{ORCA}/analysis/mrs/{x}') for x in ('dev-2025bothsurf-debertav3large-rawtext.json', 'dev-2025bothsurf-debertav3large-gen12-rawtext.json'))
    if m0 and m1:
        def grow(name, key):
            dv = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-{key}-rawtext.json')['counts']
            dp = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-{key}-properties.json')
            g3 = load(f'{ORCA}/analysis/mrs/gen-round3-bothsurf-{key}-rawtext.json')['counts']
            j3 = load(f'{ORCA}/analysis/adjudicate/gen-round3-{key}/score.json')
            n3 = g3['sentences']
            return (f'<tr><td>{name}</td>' + td(pct(dv['same MRS'], N), True) + td(pct(dp['same with properties'], N) if dp else na('running'))
                    + td(pct(dv['with MRS'], N)) + td(pct(g3['same MRS'], n3)) + td(pct(g3['same MRS'] + j3['verdicts']['orca'] + j3['verdicts'].get('both', 0), n3) if j3 else na('being judged'), True)
                    + td(pct(g3['with MRS'], n3)) + '</tr>')
        t4 = table([('DeBERTa-v3 large, trained on', ''), ('Same meaning as gold', 'n hl'), ('… with tense, number and information structure too', 'n'), ('Any analysis', 'n'),
                    ('Same meaning as ACE', 'n'), ('Right according to the LLM judge', 'n hl'), ('Any analysis', 'n')],
                   [grow('All data', 'debertav3large'), grow('All data and the judged rounds 1 and 2 (four times over)', 'debertav3large-gen12')],
                   group=[('', 1), (f'Redwoods dev ({N:,})', 3), ('Round 3, unseen in training', 3)])
        body += ('    <h3>Training on the judged sentences</h3>\n' + t4
                 + notes('Judged training data: ACE\'s reading unless the judge preferred Orca\'s; sentences judged wrong both ways dropped.',
                         'One training run each, measured before the lookup fixes; the table below compares runs with the current defaults.'))
        body += exp_seeds()
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


def exp_hausa():
    rounds = [r for r in ('round1', 'round2') if os.path.exists(f'{ORCA}/data/hausa/{r}/filter.json')]
    if not rounds:
        return ''
    tot = collections.Counter()
    rows = []
    for i, r in enumerate(rounds, 1):
        f = next(iter(json.load(open(f'{ORCA}/data/hausa/{r}/filter.json')).values()))
        w = sum(1 for _ in open(f'{ORCA}/data/hausa/{r}/sentences.txt'))
        tot.update({'w': w, 'p': f['sentences'], 'r': f['replayed']})
        rows.append(f'<tr><td>&nbsp;&nbsp;Round {i}</td>' + td(f'{w:,}') + td(pct(f['sentences'], w)) + td(pct(f['replayed'], f['sentences']), True) + '</tr>')
    rows.insert(0, '<tr><td><b>All</b></td>' + td(f"{tot['w']:,}") + td(pct(tot['p'], tot['w'])) + td(pct(tot['r'], tot['p']), True) + '</tr>')
    t = table([('Hausa sentences', ''), ('Written', 'n'), ('ACE finds a parse', 'n'), ('Orca replays ACE\'s parse', 'n hl')], rows)
    n, a0, a1 = HAUSA_MRS
    t2 = table([('Orca\'s MRS for ACE\'s Hausa parse equals ACE\'s', ''), ('Parses', 'n'), ('Share', 'n hl')],
               [f'<tr><td>Predicates, arguments, scope</td>' + td(f'{n:,}') + td(pct(a0, n), True) + '</tr>',
                f'<tr><td>&nbsp;&nbsp;… and properties (gender, tense–aspect …) and ICONS</td>' + td(f'{n:,}') + td(pct(a1, n), True) + '</tr>'])
    t = t + t2
    body = t + notes('Grammar: HaG (Crysmann), built on the Grammar Matrix. Claude Sonnet wrote the sentences from HaG\'s lexicon, in plain spelling without tone marks.',
                     'Replay: Orca rebuilds ACE\'s first parse from its labels, finding entries in HaG\'s lexicon from the plain words. Properties use HaG\'s own mapping.',
                     'The MRS differences are one homograph: plain <i>nama</i> is both meat and animal. HaG\'s build has no ranking model, so ACE\'s choice between them is arbitrary; Orca offers both readings.',
                     'Before two fixes, Orca assumed ERG habits: lexical-rule names, spelling rules, and a shorthand in definitions that the ERG uses only for lists.')
    return fold('Another grammar: Hausa', 'Orca replays every Hausa parse ACE finds, after removing assumptions that held only for the ERG.', body)


def exp_edm():
    e = load(f'{ORCA}/analysis/edm/dev.json')
    if not e:
        return ''
    S = e['systems']
    def row(name, key, ind=False):
        o, a = S['orca'][key], S['ace'][key]
        cell = lambda x: f"{100 * x['p']:.1f} / {100 * x['r']:.1f} / <b>{100 * x['f']:.1f}</b>"
        return f'<tr><td>{"&nbsp;&nbsp;" if ind else ""}{name}</td>' + td(cell(o)) + td(cell(a)) + '</tr>'
    rows = [row('EDM: names, arguments, properties, tops', 'EDM' if 'EDM' in S['orca'] else 'all'),
            row('EDM<sub>NA</sub>: names and arguments only', 'EDM_NA'),
            row('Names (predicates)', 'names', True), row('Arguments', 'arguments', True),
            row('Properties (tense, number … and names\' strings)', 'properties', True), row('Tops', 'tops', True)]
    t = table([('Redwoods dev (2,062 sentences)', ''), (f'Orca ({BEST_NAME.split(" tagger")[0]}), from raw text', 'n hl'), ('ACE, first-ranked parse', 'n')], rows)
    body = t + notes('Precision / recall / F1, in %, over elementary dependencies tied to character spans (Dridan and Oepen 2011), micro-averaged; mtool, the MRP scorer, gives the same numbers.',
                     'A sentence without an analysis counts as an empty graph, which lowers recall only.',
                     'Partial credit: a sentence with one wrong argument still scores on the rest, unlike exact match.')
    rx = load(f'{ORCA}/analysis/relaxed/dev.json')
    if rx:
        def prf(x):
            p, r, f = (x.get(k) for k in ('p', 'r', 'f'))
            return f"{100 * p:.1f} / {100 * r:.1f} / <b>{100 * f:.1f}</b>"
        e1, e2 = rx['EDM_NA (names, arguments)']['robust or fragments'], rx['EDM without tops (names, arguments, properties)']['robust or fragments']
        rows = [f'<tr><td>Words covered by some fragment</td>' + td(pct(rx['words covered'], rx['words']), True) + '</tr>',
                f'<tr><td>&nbsp;&nbsp;… by fragments of two or more words</td>' + td(pct(rx['words in multi-word fragments'], rx['words'])) + '</tr>',
                '<tr><td>EDM<sub>NA</sub> of the fragments against gold (P / R / F1)</td>' + td(prf(e1)) + '</tr>',
                '<tr><td>EDM, properties included (P / R / F1)</td>' + td(prf(e2)) + '</tr>']
        body += ('    <h3>Fragments where there is no full analysis</h3>\n' + table([(f'The {rx["sentences"]} dev sentences without a full analysis', ''), ('', 'n')], rows)
                 + notes('The largest pieces of the tagger\'s first guess that the grammar accepts, each with its own MRS; the ERG\'s robust root conditions rescue only one sentence. Without fragments these sentences score zero. Off by default (scripts/relaxed.py).'))
    return fold('EDM, as published parsers report it', 'Orca is as precise as ACE; the gap is in recall, from sentences Orca does not analyze.', body)


def exp_spanish():
    rp, mr = load(f'{ORCA}/analysis/srg/replay-0.3.6.json'), load(f'{ORCA}/analysis/srg/mrs-0.3.6.json')
    if not rp or not mr:
        return ''
    n = sum(v['sentences'] for v in rp.values()); r = sum(v['replayed'] for v in rp.values())
    c = mr['counts']; m = c['sentences'] - c['treebank MRS unreadable']
    rows = [f'<tr><td>Orca replays the gold derivation</td>' + td(f'{n:,}') + td(pct(r, n), True) + '</tr>',
            f'<tr><td>&nbsp;&nbsp;… and its MRS equals the treebank\'s</td>' + td(f'{m:,}') + td(pct(c['same without properties'], m), True) + '</tr>',
            f'<tr><td>&nbsp;&nbsp;… with properties and ICONS too</td>' + td(f'{m:,}') + td(pct(c['same with properties and ICONS'], m), True) + '</tr>']
    t = table([('Spanish Resource Grammar treebank (release 0.3.6)', ''), ('Sentences', 'n'), ('Share', 'n hl')], rows)
    body = t + notes('Gold derivations from 14 treebank profiles, preferred analysis only; grammar SRG 0.3.6 compiled with ACE. Treebank MRSs that PyDelphin cannot read are left out.',
                     'Five more ERG-only assumptions removed on the way, among them inflection rules that match part-of-speech tags (SRG\'s input is tagged lemmas).')
    tg = load(f'{ORCA}/analysis/srg/tagger-dev-0.3.6.json')
    if tg:
        k = tg['counts']; n = k['comparable']
        rows = [f'<tr><td>{name}</td>' + td(pct(k[key], n), hl) + '</tr>' for name, key, hl in
                (('First guess accepted by the grammar', 'first guess accepted', False), ('Any analysis after repair', 'any analysis', False),
                 ('Same MRS as the treebank', 'same MRS', True), ('&nbsp;&nbsp;… with properties too', 'same MRS with properties', True),
                 ('Gold MRS among the accepted analyses (ceiling)', 'gold MRS among accepted', False))]
        body += ('    <h3>A Spanish tagger</h3>\n' + table([(f'SRG treebank dev, {n:,} sentences', ''), ('Share', 'n')], rows)
                 + notes('XLM-R large trained on 2,149 treebank sentences (split by profile); the treebank\'s own tokens, not raw text. No ranking model for SRG: the accepted analysis the tagger likes best is chosen.',
                         'Dev sentences are short (4 words on average, against 10 in training). Most failures are labels never seen in training: more data, not more search.'))
    return fold('Another grammar: Spanish', 'Orca replays the Spanish treebank and rebuilds its meanings; a first Spanish tagger gets half of the dev meanings exactly.', body)


def exp_beyond_ace():
    d = f'{ORCA}/analysis/beyond-ace'
    if not os.path.exists(f'{d}/verdicts.json'):
        return ''
    items = {json.loads(l)['id']: json.loads(l) for l in open(f'{d}/items.jsonl')}
    ace = {json.loads(l)['id']: json.loads(l)['outcome'] for l in open(f'{d}/ace.jsonl')}
    verd = json.load(open(f'{d}/verdicts.json'))
    vs = verd['verdicts']
    c = collections.defaultdict(collections.Counter)
    for i, it in items.items():
        src = 'Generated sentences ACE could not parse' if it['kind'] == 'generated' else 'Dev sentences without a gold analysis'
        for k in (src, (src, ace.get(i)), 'all'):
            c[k]['n'] += 1
            c[k][vs.get(i, ['none'])[0]] += 1
    label = {'parsed': 'ACE parses them on a rerun', 'memory limit': 'ACE runs out of memory (6 GB)', 'no parse': 'ACE finds no analysis'}
    row = lambda name, x: (f'<tr><td>{name}</td>' + td(f"{x['n']:,}") + td(pct(x['RIGHT'], x['n']), True) + td(pct(x['PARTLY'], x['n'])) + td(pct(x['WRONG'], x['n'])) + '</tr>')
    rows = []
    for src in ('Dev sentences without a gold analysis', 'Generated sentences ACE could not parse'):
        rows.append(row(f'<b>{src}</b>', c[src]))
        rows += [row('&nbsp;&nbsp;' + label[o], c[(src, o)]) for o in ('parsed', 'memory limit', 'no parse') if c[(src, o)]['n']]
    t = table([('Sentences Orca analyzes', ''), ('Sentences', 'n'), ('Orca right', 'n hl'), ('Partly right', 'n'), ('Wrong', 'n')], rows,
              group=[('', 2), ('According to the LLM judge', 3)])
    body = t + notes(f'ACE rerun one sentence at a time, 300 s and 6 GB per sentence. Claude Opus judged Orca\'s reading alone from its predicates and links (${verd["cost_usd"]:.2f}).',
                     'Dev items without gold are ones the annotators rejected every reading for; ACE does parse most of them.')
    return fold('Where ACE fails', 'On generated text, ACE mostly fails by running out of memory; Orca\'s reading is then right or partly right almost every time.', body)


def exp_replay_rate():
    c = collections.Counter(r['outcome'] for r in BEST['records'])
    first, after = c['accepted at first try'], c['accepted after repair']
    rows = [f'<tr><td>Orca, ERG (Redwoods dev, raw text): first guess accepted</td>' + td(f'{N:,}') + td(pct(first, N), True) + '</tr>',
            f'<tr><td>&nbsp;&nbsp;… or after repair (up to 600 replays)</td>' + td(f'{N:,}') + td(pct(first + after, N), True) + '</tr>',
            '<tr><td>Matsuzaki et al. 2007, Enju (WSJ dev): first CFG-filtered sequence accepted</td>' + td(na('not stated')) + td('94.9%', True) + '</tr>',
            '<tr><td>&nbsp;&nbsp;… or within 111 sequences</td>' + td(na('not stated')) + td('97.6%', True) + '</tr>']
    t = table([('Proposed derivation accepted by the grammar', ''), ('Sentences', 'n'), ('Share', 'n hl')], rows)
    body = t + notes('Enju is an HPSG derived from the Penn Treebank (12 schemata, lexical templates); its candidates pass a context-free approximation of the grammar before the check, and its supertagger proposes lexical entries only. Orca proposes lexical and rule labels and checks them directly.',
                     'Published rates for this kind of check exist only for treebank-derived grammars; these are the first for a large hand-built HPSG with full semantics.')
    return fold('Replay rate, compared with CFG filtering', 'Orca\'s first guess passes the ERG less often than Enju\'s filtered guess passes Enju; repair closes most of the gap.', body)


def exp_seeds():
    runs = [('DeBERTa-v3 large, all data, run 1', 'dev-2025bothsurf-debertav3large-rawtext-normlocate-rootcheck.json'),
            ('DeBERTa-v3 large, all data, run 2 (another random seed)', 'dev-2025bothsurf-debertav3large-seed2-rawtext.json'),
            ('DeBERTa-v3 large, all data and the judged generated sentences', 'dev-2025bothsurf-debertav3large-gen12-rawtext-normlocate.json')]
    rows = []
    for name, f in runs:
        x = load(f'{ORCA}/analysis/mrs/{f}')
        if not x:
            return ''
        rows.append(f'<tr><td>{name}</td>' + td(pct(x['counts']['same MRS'], N), True) + td(pct(x['counts']['with MRS'], N)) + '</tr>')
    t = table([('Tagger', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n')], rows)
    return ('    <h3>How much two runs differ</h3>\n' + t
            + notes('Redwoods dev, raw text, current parser defaults. The two runs differ only in the random seed; the run with the judged sentences falls between them.'))


def exp_hybrid():
    r = load(f'{ORCA}/analysis/ace-fallback/route.json')
    cb = load(f'{ORCA}/analysis/supertag-ace/combined.json')
    if not r:
        return ''
    full = {c['sent to ACE']: c for c in r['curve']}
    rest = {c['sent']: c for c in (cb or {}).get('curves', {}).get('restricted', [])}
    casc = {c['sent']: c for c in (cb or {}).get('curves', {}).get('cascade', [])}
    ns = sorted(set(full) | set(rest) | set(casc))
    def cells(c, key='exact'):
        return (td(pct(c[key], N), True) + td(f"{c['sentences per second']:.2f}")) if c else td(na('not measured')) + td(na('not measured'))
    base = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-current.json')   # the Orca run the routing was fitted on
    orca = f"{base['sentences per second']:.2f}"
    rows = ['<tr><td>0 (Orca alone)</td>' + (td(pct(r['orca exact'], N), True) + td(orca)) * 3 + '</tr>']
    for n in ns:
        name = f'{n:,}' + (' (where Orca finds no analysis)' if n == 156 else ' (all sentences, after Orca)' if n == N else '')
        rows.append(f'<tr><td>{name}</td>' + cells(full.get(n)) + cells(rest.get(n)) + cells(casc.get(n)) + '</tr>')
    ace_sps = f'{N / (ACE_PASS + ACE_RETRY):.2f}'
    rows.append('<tr><td><b>ACE alone</b>, full lexicon (the baseline)</td>' + (td(pct(r['ace exact'], N), True) + td(ace_sps)) * 3 + '</tr>')
    t = table([('Sentences sent to the fallback', ''), ('Same meaning as gold', 'n hl'), ('Sentences per second', 'n'),
               ('Same meaning as gold', 'n hl'), ('Sentences per second', 'n'), ('Same meaning as gold', 'n hl'), ('Sentences per second', 'n')], rows,
              group=[('', 1), ('Full ACE', 2), ('Restricted ACE (tagger\'s entries, ≥ 0.001)', 2), ('Restricted ACE, then full ACE if it finds nothing', 2)])
    body = t + notes('Redwoods dev, raw text, 2,062 sentences. First the sentences where Orca finds no analysis (156), then Orca\'s least certain ones, by a logistic model on Orca\'s own signals (tagger probabilities, replays, candidates), cross-validated on dev (AUC ' + f'{r["cv AUC (Orca wrong)"]:.2f}' + ' for spotting Orca\'s errors).',
                     'Speed includes Orca\'s whole run. Full ACE time is measured on the no-analysis sentences (3.7 s each) and ACE\'s dev mean elsewhere; restricted ACE time is measured. Orca here is the run before the repair cutoff change (73.0%).',
                     'Sending everything is worse than sending about half: where Orca is confident, its own analysis beats the fallback\'s.',
                     '<b>All sentences, after Orca</b> includes Orca\'s time; <b>ACE alone</b> is ACE without Orca, the baseline.',
                     'Different systems from Orca alone, so they sit beside the headline, not in it.')
    return fold('Orca with a fallback for the hard sentences', 'Routing the hard half of the sentences to ACE reaches 82–85% at one to two sentences per second; sending everything gains nothing more.', body)


def exp_supertag_ace():
    c = load(f'{ORCA}/analysis/supertag-ace/cutoffs.json')
    if not c:
        return ''
    tag_s = (ms('tokens') + ms('tag')) / 1000            # Orca's tokens and tagging, per sentence (GPU)
    rows = [f'<tr><td>Orca (replay of the tagger\'s labels, repair, ranking)</td>' + td(pct(BEST['counts']['same MRS'], N), True) + td(pct(BEST['counts']['with MRS'], N)) + td(f"{BEST['sentences per second']:.1f}") + '</tr>']
    for cut in ('0.01', '0.001', '0.0001'):
        x = c[cut]
        run = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-chart-{cut}.json')
        speed = f"{run['sentences per second']:.1f}" if run else f"{1 / (x['ace seconds per sentence'] + tag_s):.1f} (estimate)"
        rows.append(f'<tr><td>ACE restricted to the tagger\'s lexical entries (top 5, probability ≥ {cut})</td>' + td(pct(x['same MRS'], N), True) + td(pct(x['parsed'], N))
                    + td(speed) + '</tr>')
    fb = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-fallback-0.001.json')
    if fb:
        rows.append(f'<tr><td>Orca, and restricted ACE (≥ 0.001) where Orca finds no analysis</td>' + td(pct(fb['counts']['same MRS'], N), True) + td(pct(fb['counts']['with MRS'], N))
                    + td(f"{fb['sentences per second']:.1f}") + '</tr>')
    rows.append(f'<tr><td>ACE, full lexicon</td>' + td(pct(T['ace']['all']['same MRS'], N), True) + td(pct(T['ace']['all']['with MRS'], N)) + td(f'{N / (ACE_PASS + ACE_RETRY):.1f}') + '</tr>')
    t = table([('Redwoods dev, raw text', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Sentences per second', 'n')], rows)
    body = t + notes('Restricted ACE: the DeBERTa tagger\'s lexical labels become lexical entries (Orca\'s lookup); every other lexeme that could match a word is switched off (ACE -L), so ACE\'s chart and the ERG\'s ranking model work only with the tagger\'s choices. Tree labels are not used.',
                     'Speed measured end to end on one kesha GPU (tagging) and one CPU core (ACE), while other jobs ran; the 0.01 row is an estimate.',
                     'The tagger gets lexical types right far more often than tree labels; the chart finds trees that label-by-label replay misses.')
    return fold('The tagger plus a chart: ACE restricted to the tagger\'s words', 'More accurate than replay (about five points) at less than half Orca\'s speed and almost three times ACE\'s.', body)


def exp_ensemble():
    e = load(f'{ORCA}/analysis/ensemble/summary.json')
    if not e:
        return ''
    rp = e['repair (replay mode, cutoff 0.001)']
    ch = next((v for k, v in e.items() if k.startswith('chart')), {})
    def row(name, k):
        r = rp.get(k, {})
        c = ch.get(k, {}) if isinstance(ch, dict) else {}
        cx = c.get('exact', c.get('same MRS'))
        return (f'<tr><td>{name}</td>' + td(pct(r['exact'], N), True) + td(pct(r['any analysis'], N)) + td(pct(r['gold among accepted'], N))
                + (td(pct(cx, N), True) if cx is not None else td(na('not run'))) + '</tr>')
    rows = [row('One tagger (seed 1)', 's1-top5'), row('Average of two (two seeds)', 'ens2'), row('Average of seven (two seeds, five folds)', 'ens7')]
    t = table([('DeBERTa-v3 large taggers', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Gold among the analyses', 'n'), ('Same meaning as gold', 'n hl')], rows,
              group=[('', 1), ('Replay', 3), ('Chart mode', 1)])
    return ('    <h3>Averaging taggers</h3>\n' + t
            + notes('Label probabilities averaged per word; each extra model adds about 37 ms of tagging per sentence on GPU. One run each on dev; one tagger\'s run-to-run spread is about one point.'))


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
            + exp_training() + exp_encoders() + exp_supertag_ace() + exp_hybrid() + exp_edm() + exp_replay_rate() + exp_generated() + exp_beyond_ace() + exp_agreement() + exp_hausa() + exp_spanish() + exp_rawtext() + exp_properties() + exp_ace() + exp_llm() + exp_llm_rank() + exp_examples() + '  </section>\n\n')
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
        out = rebuild(s)                # build first, so a failure leaves the page untouched
        open(p, 'w').write(out)
        print('rebuilt', p)
