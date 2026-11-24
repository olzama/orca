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
BERT_CUR = f'{ORCA}/analysis/mrs/dev-2025bothsurf-bert-rawtext-minprob001.json'   # BERT-base with the current defaults
BERT_NEW = BERT_CUR if os.path.exists(BERT_CUR) else f'{ORCA}/analysis/mrs/dev-2025bothsurf-rawtext-normlocate.json'
BERT_PROPS = (f'{ORCA}/analysis/mrs/dev-2025bothsurf-bert-minprob001-properties.json' if BERT_NEW == BERT_CUR
              else f'{ORCA}/analysis/mrs/dev-2025bothsurf-normlocate-rootcheck-properties.json')
BERT_JUDGE = (f'{ORCA}/analysis/adjudicate/dev-bothsurf-bert-minprob001/score.json' if BERT_NEW == BERT_CUR
              else f'{ORCA}/analysis/adjudicate/dev-bothsurf-normlocate/score.json')
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


def fold(title, takeaway, body, open_=False, id_=None):
    return (f'  <details class="fold"{f" id={chr(34)}{id_}{chr(34)}" if id_ else ""}{" open" if open_ else ""}>\n'
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


NOT_YET = '<b>Not measured yet:</b> '


def link(anchor, text):
    return f'<a href="#{anchor}">{text}</a>'


def question(id_, title, answer, shown, folds):
    """A top-level section: the question, a one-sentence answer, the table that answers it, supporting folds."""
    return (f'  <section class="stack" id="{id_}">\n    <h2>{title}</h2>\n    <p class="answer">{answer}</p>\n'
            + shown + folds + '  </section>\n\n')


def modes():
    """Replay, chart, fallback and ACE on dev in one table: the current Orca run, speeds measured together."""
    r = load(f'{ORCA}/analysis/ace-fallback/route-current.json')
    sp = load(f'{ORCA}/analysis/mrs/dev-modes-speed-loaded.json')
    e = load(f'{ORCA}/analysis/edm/dev-current.json')
    if not (r and sp and e):
        return ''
    S, E = sp['runs'], e['systems']
    full = {c['sent to ACE']: c for c in r['curve']}
    none_n = N - BEST['counts']['with MRS']
    half = min((k for k in full if k > none_n and k >= 0.4 * N), key=lambda k: abs(k - 0.45 * N), default=None)
    step_sps = BEST['sentences per second']
    def loaded(c):            # Orca under today's load, plus ACE's measured per-sentence time
        ace_s = N / c['sentences per second'] - N / step_sps
        return N / (N / S['replay']['sentences per second'] + ace_s)
    f1 = lambda k: f"{100 * E[k]['EDM_NA']['f']:.1f}" if k in E else na('not scored')
    ace = T['ace']['all']
    row = lambda name, ex, an, edm, spd: f'<tr><td>{name}</td>' + td(ex, True) + td(an) + td(edm) + td(spd) + '</tr>'
    rows = [row('Orca (replay): the headline', pct(S['replay']['same MRS'], N), pct(S['replay']['with MRS'], N), f1('orca'), f"{S['replay']['sentences per second']:.1f}"),
            row('Orca, then restricted ACE where it finds nothing (fallback mode)', pct(S['fallback']['same MRS'], N), pct(S['fallback']['with MRS'], N), f1('fallback'), f"{S['fallback']['sentences per second']:.1f}"),
            row('Chart mode: ACE restricted to the tagger\'s entries', pct(S['chart']['same MRS'], N), pct(S['chart']['with MRS'], N), f1('chart'), f"{S['chart']['sentences per second']:.1f}")]
    if none_n in full:
        rows.append(row(f'Orca, then full ACE where it finds nothing ({none_n:,} sentences)', pct(full[none_n]['exact'], N), na('not recorded'), f1('ace-none'), f"{loaded(full[none_n]):.1f}"))
    if half:
        rows.append(row(f'Orca, then full ACE for the least certain {half:,}', pct(full[half]['exact'], N), na('not recorded'), f1('ace-half'), f"{loaded(full[half]):.1f}"))
    rows.append(row('ACE alone, full lexicon', pct(ace['same MRS'], N), pct(ace['with MRS'], N), f1('ace'), f'{N / (ACE_PASS + ACE_RETRY):.1f}'))
    t = table([('Redwoods dev, raw text', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('EDM<sub>NA</sub> F1', 'n'), ('Sentences per second', 'n')], rows)
    return (t
            + notes('Replay is Orca\'s own method and the headline; the other rows are different systems built on it. Fallback mode is the default for parsing corpora, chart mode where accuracy matters most.',
                    'Restricted ACE: ACE with only the tagger\'s five best lexical entries per word (probability 0.001 or more). Details in ' + link('chart', 'The tagger plus a chart') + ' and ' + link('fallback', 'Orca with a fallback') + '.',
                    'Full ACE rows: sentences picked first where Orca finds nothing, then where it is least certain (a cross-validated model on Orca\'s own signals).',
                    '<b>Speeds:</b> the three Orca modes measured back to back on 24 November, one GPU and one core, while kesha was busy with other jobs, so all run slower than on a quiet machine (the headline tile, from a quiet run, says ' + f'{step_sps:.1f}' + '). Full-ACE rows: Orca\'s speed under the same load plus ACE\'s measured time for each sentence sent. ACE alone: one core, measured earlier.',
                    '<b>EDM<sub>NA</sub> F1:</b> predicates and arguments with partial credit (' + link('edm', 'EDM') + '); all and properties in that section.',
                    'On novels and news the modes come in the same order, with a wider gap between replay and chart mode (' + link('corpus', 'Novels and news') + ').'))


def runs():
    """Run-to-run spread, and the parser versions behind the tables."""
    seeds = exp_seeds()
    vers = [('Before the lookup fixes', 'dev-2025bothsurf-debertav3large-rawtext.json', 'Encoders; training on the judged sentences. BERT-base in From raw text, Training data, and Tense, number, information structure'),
            ('With the lookup fixes', 'dev-2025bothsurf-debertav3large-rawtext-normlocate-rootcheck.json', 'Nothing on this page now; kept for reference'),
            ('<b>With the repair cutoff at 0.001 (current)</b>', None, 'The headline, the summary table, the error breakdown, the seeds above, the modes and fallback tables, EDM and fragments, encoders (all data), averaging')]
    rows = []
    for name, f, used in vers:
        x = BEST if f is None else load(f'{ORCA}/analysis/mrs/{f}')
        if x:
            rows.append(f'<tr><td>{name}</td>' + td(pct(x['counts']['same MRS'], N), True) + td(pct(x['counts']['with MRS'], N)) + f'<td>{used}</td></tr>')
    t = table([('Parser version (DeBERTa-v3 large, dev, raw text)', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Tables measured with it', '')], rows)
    body = (seeds + t + cap('The same tagger under three versions of the parser. A table on an older version is comparable within itself, not with the headline.'))
    return fold('How much two runs differ, and which parser version each table uses', 'Just under a point between seeds with the current parser; three parser versions behind the tables.', body, id_='runs')


def summary():
    """One table across the evaluations, then the main findings in words (numbers stay in the table)."""
    oc = BEST['counts']
    jd, props, aj = load(BEST_JUDGE), load(BEST_PROPS), load(ACE_JUDGE)
    bj = load(f'{ORCA}/analysis/adjudicate/dev-bothsurf/score.json')
    bn, bp, bbj = load(BERT_NEW), load(BERT_PROPS), load(BERT_JUDGE)
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
                 pct(bn['counts']['with MRS'], N), na('not comparable: measured while kesha was fully loaded') if BERT_NEW == BERT_CUR else f"{bn['sentences per second']:.1f}") if bn else
             row('&nbsp;&nbsp;Orca (BERT-base), from raw text', N, na('re-running with the lookup fixes'), na('re-running'), na('re-running'), na('re-running'), na('re-running'))),
            row('&nbsp;&nbsp;ACE, first-ranked parse', N, pct(ace['same MRS'], N),
                pct(load(f'{ORCA}/analysis/mrs/dev-ace-properties.json')['same with properties'], N) if load(f'{ORCA}/analysis/mrs/dev-ace-properties.json') else na('not measured'),
                pct(ace['same MRS'] + aj['verdicts']['orca'] + aj['verdicts']['both'], N) if aj else na('being judged'),
                pct(ace['with MRS'], N), f'{N / (ACE_PASS + ACE_RETRY):.1f}')]
    cnt, verdicts, _, labels = gen_counts()
    if verdicts:
        g = cnt['all']
        gb = gen_counts('bert-current')[0].get('all')
        gc = gen_counts(f'{BEST_KEY}-chart')[0].get('all')
        lo = g['agree'] + g['reference'] + g['both']
        hi = lo + g['none'] + g['scope']
        GP = (load(f'{ORCA}/analysis/mrs/gen-properties-summary.json') or {}).get('by system', {})
        GS = (load(f'{ORCA}/analysis/mrs/gen-modes-speed-loaded.json') or {}).get('runs', {})
        gprop = lambda k, n: pct(GP[k]['same with properties'], n) if k in GP else na('not measured')
        gspd = lambda m: na('measured under load: see ' + link('generated', 'Generated sentences')) if m in GS else na('not measured')
        rows += [grp(f'Generated sentences on hard phenomena (rounds 1 to {len(labels)}), '
                     'compared with ACE\'s first-ranked parse, which nobody checked'),
                 row('&nbsp;&nbsp;Orca (DeBERTa-v3 large), from raw text', g['n'], pct(g['agree'], g['n']), gprop('debertav3large-current', g['n']), pct(g['agree'] + g['orca'] + g['both'], g['n']),
                     pct(g['mrs'], g['n']), gspd('replay')),
                 (row('&nbsp;&nbsp;Orca (BERT-base), from raw text', gb['n'], pct(gb['agree'], gb['n']), gprop('bert-current', gb['n']), pct(gb['agree'] + gb['orca'] + gb['both'], gb['n']),
                      pct(gb['mrs'], gb['n']), na('not timed')) if gb else ''),
                 (row('&nbsp;&nbsp;Orca chart mode (DeBERTa-v3 large; ACE restricted to the tagger\'s entries)', gc['n'], pct(gc['agree'], gc['n']), gprop('debertav3large-chart', gc['n']), pct(gc['agree'] + gc['orca'] + gc['both'], gc['n']),
                      pct(gc['mrs'], gc['n']), gspd('chart')) if gc else ''),
                 row('&nbsp;&nbsp;ACE, first-ranked parse', g['n'], na('the reference'), na('the reference'),
                     f'{100 * lo / g["n"]:.1f}–{100 * hi / g["n"]:.1f}%', pct(g['n'], g['n']), na('not timed on these'))]
    t = table([('Text and parser', ''), ('Sentences', 'n'), ('Same meaning as the reference', 'n hl'), ('… with tense, number and information structure too', 'n hl'),
               ('Right according to the LLM judge', 'n hl'), ('Any analysis', 'n'), ('Sentences per second', 'n')], rows)
    c = notes('<b>… with tense, number and information structure too:</b> the variable properties (tense, aspect, mood, sentence force, number, person, gender) and ICONS must match as well; on dev ICONS never break a match, on generated text they break two of BERT-base\'s.',
              '<b>Scope-only differences:</b> a few sentences differ from the reference only in quantifier scope; the judge is shown no difference there, so they count as wrong.',
              '<b>Same meaning as the reference:</b> on dev the reference is gold; on generated text it is ACE\'s unchecked first parse.',
              '<b>Run-to-run spread:</b> a second training run of the same tagger, with another random seed, gets about one point less exact meaning on dev (' + link('runs', 'How much two runs differ') + ').',
              '<b>Comparing with other work:</b> most semantic parsing evaluation scores predicates and arguments only (SDP\'s DM, AMR\'s Smatch, CCG dependencies, EDM<sub>NA</sub>), as the first column does; full EDM and MRP\'s EDS score count properties too.',
              '<b>Right according to the LLM judge:</b> same meaning, or the judge (Claude Opus) accepts this parser\'s reading where they differ.',
              '<b>ACE on generated text:</b> a range; sentences the judge never saw count as wrong for the low end, right for the high end.',
              '<b>Chart mode on generated text:</b> it uses ACE\'s chart and ranking model, so agreeing with ACE\'s parse is partly built in; the judge column is the fairer comparison.',
              'Agreements between Orca and ACE count as right; checking them was inconclusive (' + link('generated', 'Generated sentences') + ').',
              NOT_YET + 'speed, and the measure with tense and number, on generated sentences; a few disagreements there have no verdict and count as wrong.')
    return t + c


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
    h = METRICS['dev']   # the saved checkpoint is the best epoch on dev, as in the Encoders table
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
    c = collections.Counter(r['outcome'] for r in BEST['records'])
    shown = (f'    <div class="scroll pad">{pipeline()}</div>\n'
             + cap('No chart: the tagger proposes a complete derivation; the grammar checks it by unification. Times: average per dev sentence, from raw text.')
             + notes('<b>Accepted:</b> every rule in the derivation unifies, and the result meets the grammar\'s root conditions (a complete sentence). Otherwise replay reports the node where it failed.',
                     '<b>Repair:</b> the tagger\'s next-best labels for the words under the failing node are tried, most probable first: up to 5 per word, each with probability 0.001 or more.',
                     f'<b>No analysis:</b> no proposed derivation is accepted, either because the 600 replays are used up ({c["rejected, budget used"]:,} dev sentences) or because every allowed alternative failed ({c["rejected, nothing left to try"]:,}). Replay mode stops there; fallback mode hands such sentences to the chart. Fragments (accepted pieces of the first guess) are reported separately and never counted as analyses.'))
    return shown, fold('The tagger and its labels', 'Architecture, training, and how a derivation becomes two labels per word.', (
            '    <h3>The tagger</h3>\n'
            f'    <div class="scroll pad">{tagger_svg()}</div>\n'
            f'    <div class="kv specs">{kv}</div>\n'
            + '    <h3>A derivation as two labels per word</h3>\n' + enc_t
            + cap('Tree labels fix one binary tree: depth change and rule of the node joining each word to the next (after Gómez-Rodríguez and Vilares 2018).')), id_='tagger')


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
    bb = load(BERT_CUR) or load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-bert-current-breakdown.json')   # same run as the summary row
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
    return (t2
            + notes(f'All {N:,} dev sentences, from raw text; each row adds up to 100%. Gold derivations always replay to the gold MRS, so all loss is in the proposals.',
                    '<b>Found, another chosen:</b> a ranking error. <b>None right:</b> a proposing error. <b>No analysis:</b> the grammar rejected everything proposed.',
                    'Most of the loss is in proposing, and it grows with length.'))


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
    nw = load(f'{ORCA}/analysis/mrs/dev-2025bothnews25surf-debertav3large-rawtext.json')
    if nw:
        drow = lambda name, r: (f'<tr><td>{name}</td>' + td(pct(r['counts']['same MRS'], N), True) + td(pct(r['counts']['with MRS'], N))
                                + td(pct(r['counts']['gold MRS among accepted'], N)) + '</tr>')
        t += (table([('DeBERTa-v3 large, current parser defaults; tagger trained on', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Gold among the analyses found', 'n')],
                    [drow('All data (590,721 sentences)', BEST), drow('All data and more 2025 news (663,219 sentences)', nw)])
              + cap('Redwoods dev, from raw text. The added news (72,092 sentences of ACE\'s first parses, kept if they replay) is a different kind of text from Redwoods, so no gain is expected here; the test that matters is unseen news, which needs a fresh sample (roadmap O71).'))
    body = t + notes('Silver data: ACE\'s first parses of novels (1838 to 1921) and news (NYT 2023, 2025), with LLM-written counterparts, kept if they replay.',
                     'One run each; the run-to-run spread is about one point (' + link('runs', 'How much two runs differ') + ').')
    return fold('Training data', 'More grammar-licensed text helped up to now; halving it costs little.', body, id_='training-data')


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
    body = (t0 + cap('Treebank tokens are not available for new text. The headline, the summary table and every table not marked otherwise are from raw text; the tables that use treebank tokens say so (training data, Orca and ACE, LLM repair, Spanish). BERT-base here is the run before the lookup fixes (' + link('runs', 'parser versions') + ').') + t1 + t2 + notes('Tokens come from ACE\'s preprocessing, without parsing; replay picks the token the lexical entry accepts.',
                            'Treebank word forms leak the analysis through capitalization; training on forms as typed removes the leak.'))
    return fold('From raw text', 'The grammar\'s tokens work; the tagger loses a little on capitalization.', body, id_='raw-text')


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
                       'The BERT-base column and the breakdown below are from the run before the lookup fixes; the current BERT-base run is in the summary table.',
                       'The first row is what most parsing work compares (SDP\'s DM, AMR\'s Smatch, CCG dependencies, EDM<sub>NA</sub>); the second is closer to full EDM and MRP\'s EDS score.',
                       f'ICONS: about one gold analysis in six has them ({ic["gold with ICONS"] if ic else "…"} of {n:,}). Requiring them loses no exact match: they follow from the derivation.' if ic else 'ICONS: being measured.')
            + t2 + cap('BERT-base. Each sentence counted once, under the first kind that differs. Sentence force: statement against question.'))
    return fold('Tense, number, information structure', 'Orca now outputs them; requiring them to match changes the headline little.', body, id_='properties')


def exp_ace_current():
    d = load(f'{ORCA}/analysis/orca-ace/dev-current.json')
    if not d:
        return ''
    S = d['systems']; sy = [('replay', 'Replay'), ('chart', 'Chart'), ('fallback', 'Fallback'), ('ace', 'ACE')]
    say = {'all': 'All', 'under 10': 'Under 10 words', '10 to 19': '10 to 19 words', '20 to 29': '20 to 29 words', '30 and over': '30 words or more'}
    rows = []
    for b in ['all'] + d['bands']:
        n = S['replay']['by band'][b]['sentences']
        rows.append(f'<tr><td>{"&nbsp;&nbsp;" if b != "all" else ""}{say[b]}</td>' + td(f'{n:,}')
                    + ''.join(td(pct(S[k]['by band'][b]['same MRS'], n), True) for k, _ in sy)
                    + ''.join(td(pct(S[k]['by band'][b]['with MRS'], n)) for k, _ in sy) + '</tr>')
    t = table([('Redwoods dev, raw text', ''), ('Sentences', 'n')] + [(nm, 'n hl') for _, nm in sy] + [(nm, 'n') for _, nm in sy], rows,
              group=[('', 2), ('Same meaning as gold', 4), ('Any analysis', 4)])
    prow = lambda k, nm: (f'<tr><td>{nm}</td>' + td(f"{S[k]['precision']['analyzed']:,}") + td(pct(S[k]['precision']['right meaning'], S[k]['precision']['analyzed']), True)
                          + td(p1(S[k]['precision']['predicate precision'])) + td(p1(S[k]['precision']['link precision'])) + '</tr>')
    t2 = table([('Current system', ''), ('Sentences it analyzes', 'n'), ('Right meaning, of those', 'n hl'), ('Its predicates that are in gold (%)', 'n'), ('Its links that are in gold (%)', 'n')],
               [prow(k, nm) for k, nm in sy])
    return ('    <h3>The current system</h3>\n' + t + cap('DeBERTa-v3 large tagger from raw text, current parser defaults; chart and fallback as in the mode table.')
            + t2 + cap('Only the sentences each system analyzes.')
            + notes('<b>Memory limits for ACE on this page:</b> ACE alone on dev gets 6 GB per sentence and retries failures at 16 GB, then 28 GB; chart and fallback modes give restricted ACE 6 GB for the chart and 7 GB for unpacking; Where ACE fails uses 6 GB and 300 s per sentence. One Orca process uses about 3.4 GB.',
                    NOT_YET + 'the current system on several cores (the machine was busy).')
            + '    <h3>The first pipeline</h3>\n')


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
    body = (exp_ace_current() + by_len + cap('BERT-base, treebank only, treebank tokens: the first pipeline, kept for its speed comparison on several cores.')
            + speed + cap('Dev sentences average about 12 words. ACE\'s time includes retries with more memory.')
            + prec + cap('Only the sentences each system analyzes.'))
    return fold('Orca and ACE', 'Faster at every setting and about as precise; behind on long sentences, where chart and fallback modes close part of the gap.', body, id_='orca-ace')


def exp_llm():
    llm = open(os.path.join(HERE, 'llm-table.html')).read()
    rows = ['<tr><td>LLM repair (Claude Opus)</td>' + td(pct(188, 390)) + td(pct(89, 390), True) + td(sps(LLM_SENTS / LLM_SECS)) + td('about $0.35 per sentence') + '</tr>',
            '<tr><td>ACE</td>' + td(pct(388, 390)) + td(pct(270, 390), True) + td(sps(390 / 1315.0)) + td('none') + '</tr>']
    fb = table([('Fallback on the 390 sentences repair leaves', ''), ('Any analysis', 'n'), ('Right meaning', 'n hl'),
                ('Sentences per second', 'n'), ('Cost', 'n')], rows)
    body = (llm + cap('Claude Opus sees the failure points and the grammar\'s definitions; the grammar replays every answer. Costs are API-equivalent.')
            + fb + cap('ACE is the better fallback for English.'))
    return fold('LLM repair', 'Accepted analyses for about half the leftovers; slow; used offline only.', body, id_='llm-repair')


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
    return fold('LLM choosing among readings', 'Below the grammar\'s ranking model at every margin.', body, id_='llm-choice')


ENCODERS = (('bertbase', 'BERT-base (cased)', '110M'), ('robertalarge', 'RoBERTa-large', '355M'),
            ('xlmrlarge', 'XLM-R large', '560M'), ('debertav3large', 'DeBERTa-v3 large', '435M'))


def exp_encoders(open_=False):
    rows = []
    for data, model, run, title in (('surf', '2025surf-{}', 'dev-2025surf-{}-rawtext.json', 'Redwoods treebank only (86,278 sentences)'),
                                    ('all', '2025bothsurf-{}', 'dev-2025bothsurf-{}-rawtext.json', 'All data (590,721 sentences)')):
        rows.append(f'<tr><td colspan="8"><i>{title}</i></td></tr>')
        for key, name, size in ENCODERS:
            k = 'bert' if (data == 'all' and key == 'bertbase') else key
            mp = f'{ORCA}/data/models/tagger-{model.format(k)}/metrics.json'
            rp = f'{ORCA}/analysis/mrs/' + ('dev-2025bothsurf-rawtext.json' if k == 'bert' else run.format(k))
            if data == 'all':   # current parser defaults where re-run
                cur = {'bert': BERT_CUR, 'debertav3large': f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-minprob001.json'}.get(k, f'{ORCA}/analysis/mrs/dev-2025bothsurf-{k}-rawtext-current.json')
                rp = cur if os.path.exists(cur) else rp
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
    body = t + cap('Same recipe for all: forms as typed, 6 epochs, batch 32, learning rate 3e-5 (BERT-base) or 2e-5. One run each. All-data rows: current parser defaults. Treebank-only rows: measured before the lookup fixes (' + link('runs', 'parser versions') + '), so compare them only with each other.')
    body += exp_ensemble()
    return fold('Encoders', 'DeBERTa and XLM-R large lead, with the treebank alone and with all data.', body, open_=open_, id_='encoders')


GEN_ROUNDS = (('pilot1', 'Round 1'), ('round2', 'Round 2'), ('round3', 'Round 3'))


def gen_counts(key=f'{BEST_KEY}-current'):
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
                         'One training run each, measured before the lookup fixes; ' + link('runs', 'How much two runs differ') + ' compares runs after them.'))
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
    gs = load(f'{ORCA}/analysis/mrs/gen-modes-speed-loaded.json')
    ds = load(f'{ORCA}/analysis/mrs/dev-modes-speed-loaded.json')
    if gs and ds:
        srow = lambda name, m: (f'<tr><td>{name}</td>' + td(f"{ds['runs'][m]['sentences per second']:.1f}") + td(f"{gs['runs'][m]['sentences per second']:.1f}", True) + '</tr>')
        body += ('    <h3>Speed</h3>\n' + table([('Sentences per second, measured under the same load', ''), (f'Redwoods dev ({N:,})', 'n'), (f'Generated round 3 ({gs["runs"]["replay"]["sentences"]:,})', 'n hl')],
                                               [srow('Orca (replay)', 'replay'), srow('Chart mode', 'chart')])
                 + notes('Both measured on 24 November on one kesha GPU and one core while other jobs ran, so slower than on a quiet machine. Generated sentences are longer and harder than dev.'))
    return fold('Generated sentences', 'Harder than dev; ACE\'s own parses of them are often wrong.', body, id_='generated')


def exp_hausa(open_=False):
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
                     'Before the fixes, Orca assumed ERG habits: lexical-rule names, spelling rules, and a shorthand in definitions that the ERG uses only for lists.')
    return fold('Another grammar: Hausa', 'Orca replays every Hausa parse ACE finds, after removing assumptions that held only for the ERG.', body, open_=open_, id_='hausa')


def exp_edm():
    e = load(f'{ORCA}/analysis/edm/dev-current.json') or load(f'{ORCA}/analysis/edm/dev.json')
    if not e:
        return ''
    S = e['systems']
    cell = lambda x: f"{100 * x['p']:.1f} / {100 * x['r']:.1f} / <b>{100 * x['f']:.1f}</b>"
    names = [('orca', f'Orca ({BEST_NAME.split(" tagger")[0]}), replay'), ('fallback', '&nbsp;&nbsp;… then restricted ACE where it finds nothing'),
             ('chart', 'Chart mode'), ('ace-none', 'Orca, then full ACE where it finds nothing'), ('ace-half', 'Orca, then full ACE for the least certain'),
             ('ace', 'ACE alone, first-ranked parse')]
    rows = [f'<tr><td>{nm}</td>' + td(cell(S[k]['EDM_NA'])) + td(cell(S[k]['EDM'] if 'EDM' in S[k] else S[k]['all'])) + '</tr>' for k, nm in names if k in S]
    t = table([('Redwoods dev (2,062 sentences)', ''), ('EDM<sub>NA</sub>: names and arguments', 'n hl'), ('EDM: also properties and tops', 'n')], rows)
    o, a = S['orca'], S['ace']
    rows2 = [f'<tr><td>{nm}</td>' + td(cell(o[k])) + td(cell(a[k])) + '</tr>' for k, nm in
             (('names', 'Names (predicates)'), ('arguments', 'Arguments'), ('properties', 'Properties (tense, number … and names\' strings)'), ('tops', 'Tops'))]
    t2 = table([('By part, replay against ACE', ''), ('Orca, replay', 'n hl'), ('ACE', 'n')], rows2)
    body = t + notes('Precision / recall / F1, in %, over elementary dependencies tied to character spans (Dridan and Oepen 2011), micro-averaged; mtool, the MRP scorer, gives the same numbers.',
                     'A sentence without an analysis counts as an empty graph, which lowers recall only. Current parser defaults for every Orca row.',
                     'Partial credit: a sentence with one wrong argument still scores on the rest, unlike exact match.') + t2
    rx = load(f'{ORCA}/analysis/relaxed/dev-current.json') or load(f'{ORCA}/analysis/relaxed/dev.json')
    if rx:
        def prf(x):
            return f"{100 * x['p']:.1f} / {100 * x['r']:.1f} / <b>{100 * x['f']:.1f}</b>"
        e1, e2 = rx['EDM_NA (names, arguments)']['robust or fragments'], rx['EDM without tops (names, arguments, properties)']['robust or fragments']
        rows = [f'<tr><td>Words covered by some fragment</td>' + td(pct(rx['words covered'], rx['words']), True) + '</tr>',
                f'<tr><td>&nbsp;&nbsp;… by fragments of two or more words</td>' + td(pct(rx['words in multi-word fragments'], rx['words'])) + '</tr>',
                '<tr><td>EDM<sub>NA</sub> of the fragments against gold (P / R / F1)</td>' + td(prf(e1)) + '</tr>',
                '<tr><td>EDM, properties included (P / R / F1)</td>' + td(prf(e2)) + '</tr>']
        body += ('    <h3>Fragments where there is no full analysis</h3>\n' + table([(f'The {rx["sentences"]} dev sentences without a full analysis', ''), ('', 'n')], rows)
                 + notes('The largest pieces of the tagger\'s first guess that the grammar accepts, each with its own MRS; the ERG\'s robust root conditions rescue one sentence. Without fragments these sentences score zero. The parser returns fragments as a labeled fallback on the command line and in the demo, never counted as full analyses.'))
    return fold('EDM, as published parsers report it', 'What Orca outputs is about as precise as ACE\'s; the gap is recall, from sentences without an analysis, and the fallbacks close most of it.', body, id_='edm')

def exp_spanish():
    rp, mr = load(f'{ORCA}/analysis/srg/replay-0.3.6.json'), load(f'{ORCA}/analysis/srg/mrs-0.3.6.json')
    if not rp or not mr:
        return ''
    n = sum(v['sentences'] for v in rp.values()); r = sum(v['replayed'] for v in rp.values())
    c = mr['counts']; m = c['sentences'] - c['treebank MRS unreadable']
    rows = [f'<tr><td>Orca replays the gold derivation</td>' + td(f'{n:,}') + td(f'{100 * r / n:.2f}% <span class="cnt">({r:,})</span>' if r != n else pct(r, n), True) + '</tr>',
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
    return fold('Another grammar: Spanish', 'Orca replays the Spanish treebank and rebuilds its meanings; a first Spanish tagger gets half of the dev meanings exactly.', body, id_='spanish')


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
    return fold('Where ACE fails', 'On generated text, ACE mostly fails by running out of memory; Orca\'s reading is then right or partly right almost every time.', body, id_='ace-fails')


def exp_replay_rate():
    c = collections.Counter(r['outcome'] for r in BEST['records'])
    first, after = c['accepted at first try'], c['accepted after repair']
    rr = load(f'{ORCA}/analysis/replay-rate/dev-current.json')
    if rr:
        first = rr['within k replays']['1']   # same run as the rows below (saved tagger output)
    rows = [f'<tr><td>Orca, ERG (Redwoods dev, raw text): first guess accepted</td>' + td(f'{N:,}') + td(pct(first, N), True) + '</tr>']
    if rr:
        rows += [f'<tr><td>&nbsp;&nbsp;… or within {k} replays</td>' + td(f'{N:,}') + td(pct(rr['within k replays'][k], N), k == '111') + '</tr>' for k in ('10', '111', '600')]
    else:
        rows.append(f'<tr><td>&nbsp;&nbsp;… or after repair (up to 600 replays)</td>' + td(f'{N:,}') + td(pct(first + after, N), True) + '</tr>')
    rows += [
            '<tr><td>Matsuzaki et al. 2007, Enju (WSJ dev): first CFG-filtered sequence accepted</td>' + td(na('not stated')) + td('94.9%', True) + '</tr>',
            '<tr><td>&nbsp;&nbsp;… or within 111 sequences</td>' + td(na('not stated')) + td('97.6%', True) + '</tr>']
    t = table([('Proposed derivation accepted by the grammar', ''), ('Sentences', 'n'), ('Share', 'n hl')], rows)
    body = t + notes('Enju is an HPSG derived from the Penn Treebank (12 schemata, lexical templates); its candidates pass a context-free approximation of the grammar before the check, and its supertagger proposes lexical entries only. Orca proposes lexical and rule labels and checks them directly.',
                     'Published rates for this kind of check exist only for treebank-derived grammars; these are the first for a large hand-built HPSG with full semantics.',
                     'Orca rows: one run of repair on the saved tagger output with current defaults, counting replays until the first derivation the grammar accepts; 111 is the bound Matsuzaki et al. report.',
                     NOT_YET + 'the share accepted within k replays (Orca logs only the total).')
    return fold('Replay rate, compared with CFG filtering', 'Orca\'s first guess passes the ERG less often than Enju\'s filtered guess passes Enju; repair closes most of the gap.', body, id_='replay-rate')


def exp_seeds():
    s2 = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-seed2-rawtext-minprob001.json')
    s3 = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-seed3-rawtext-minprob001.json')
    if not s2:
        return ''
    row = lambda name, x: (f'<tr><td>{name}</td>' + td(pct(x['counts']['same MRS'], N), True) + td(pct(x['counts']['with MRS'], N))
                           + td(pct(x['counts']['gold MRS among accepted'], N)) + '</tr>')
    rows = [row('DeBERTa-v3 large, all data, seed 1 (the headline)', BEST), row('DeBERTa-v3 large, all data, seed 2', s2),
            row('DeBERTa-v3 large, all data, seed 3', s3) if s3 else '<tr><td>DeBERTa-v3 large, all data, seed 3</td>' + td(na('training')) * 3 + '</tr>']
    t = table([('Tagger', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Gold among the analyses found', 'n')], rows)
    return (t + notes('Redwoods dev, raw text, current parser defaults. The runs differ only in the random seed of training; everything else, data and recipe included, is the same.'))


def exp_hybrid():
    rc = load(f'{ORCA}/analysis/ace-fallback/route-current.json')
    sp = load(f'{ORCA}/analysis/mrs/dev-modes-speed-loaded.json')
    if rc and sp:
        rep = sp['runs']['replay']['sentences per second']; step = BEST['sentences per second']
        loaded = lambda c: N / (N / rep + N / c['sentences per second'] - N / step)
        none_n = N - BEST['counts']['with MRS']
        rows = ['<tr><td>0 (Orca alone)</td>' + td(pct(rc['orca exact'], N), True) + td(f'{rep:.1f}') + '</tr>']
        for c in rc['curve']:
            n = c['sent to ACE']
            name = f'{n:,}' + (' (where Orca finds no analysis)' if n == none_n else ' (all sentences, after Orca)' if n == N else '')
            rows.append(f'<tr><td>{name}</td>' + td(pct(c['exact'], N), True) + td(f'{loaded(c):.1f}') + '</tr>')
        rows.append('<tr><td><b>ACE alone</b>, full lexicon (the baseline)</td>' + td(pct(rc['ace exact'], N), True) + td(f'{N / (ACE_PASS + ACE_RETRY):.1f}') + '</tr>')
        t = table([('Sentences sent to full ACE', ''), ('Same meaning as gold', 'n hl'), ('Sentences per second', 'n')], rows)
        body = t + notes(f'Redwoods dev, raw text, current parser defaults. First the {none_n} sentences where Orca finds no analysis, then Orca\'s least certain ones, by a logistic model on Orca\'s own signals (tagger probabilities, replays, candidates), cross-validated on dev (AUC {rc["cv AUC (Orca wrong)"]:.2f} for spotting Orca\'s errors).',
                         'Speed: Orca measured on 24 November while kesha was busy with other jobs, plus ACE\'s measured time for each sentence sent (one core). ACE alone: measured earlier.',
                         'Sending everything equals ACE alone in accuracy at a lower speed; the gain per sentence sent falls off quickly after the uncertain half.',
                         'Different systems from Orca alone, so they sit beside the headline, not in it.',
                         NOT_YET + 'the same curve with restricted ACE as the fallback, and restricted then full ACE, on the current run (measured on the earlier run only).')
        return fold('Orca with a fallback for the hard sentences', 'Routing the least certain half of the sentences to ACE comes close to ACE alone at a little more than its speed.', body, id_='fallback')
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
                     'Speed includes Orca\'s whole run. Full ACE time is measured on the no-analysis sentences (3.7 s each) and ACE\'s dev mean elsewhere; restricted ACE time is measured. Orca here is the run of 23 November with the lookup fixes, before the repair cutoff change; it has one exact match more than the run of 22 November in ' + link('runs', 'How much two runs differ') + ', with the same settings.',
                     'With restricted ACE, sending everything is worse than sending about half: where Orca is confident, its own analysis beats the fallback\'s. With full ACE, sending everything equals ACE alone at a lower speed.',
                     '<b>All sentences, after Orca</b> includes Orca\'s time; <b>ACE alone</b> is ACE without Orca, the baseline.',
                     'Different systems from Orca alone, so they sit beside the headline, not in it.')
    return fold('Orca with a fallback for the hard sentences', 'Routing the hard half of the sentences to ACE reaches 82–85% at one to two sentences per second; sending everything adds half a point at most.', body, id_='fallback')


def exp_supertag_ace():
    c = load(f'{ORCA}/analysis/supertag-ace/cutoffs.json')
    if not c:
        return ''
    tag_s = (ms('tokens') + ms('tag')) / 1000            # Orca's tokens and tagging, per sentence (GPU)
    SP = (load(f'{ORCA}/analysis/mrs/dev-modes-speed-loaded.json') or {}).get('runs', {})
    rows = [f'<tr><td>Orca (replay of the tagger\'s labels, repair, ranking)</td>' + td(pct(BEST['counts']['same MRS'], N), True) + td(pct(BEST['counts']['with MRS'], N))
            + td(f"{SP['replay']['sentences per second']:.1f}" if SP else f"{BEST['sentences per second']:.1f}") + '</tr>']
    for cut in ('0.01', '0.001', '0.0001'):
        x = c[cut]
        run = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-chart-{cut}.json')
        speed = (f"{SP['chart']['sentences per second']:.1f}" if SP and cut == '0.001' else na('not measured with the others') if SP
                 else f"{run['sentences per second']:.1f}" if run else f"{1 / (x['ace seconds per sentence'] + tag_s):.1f} (estimate)")
        rows.append(f'<tr><td>ACE restricted to the tagger\'s lexical entries (top 5, probability ≥ {cut})</td>' + td(pct(x['same MRS'], N), True) + td(pct(x['parsed'], N))
                    + td(speed) + '</tr>')
    fb = load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav3large-rawtext-fallback-0.001.json')
    if fb:
        rows.append(f'<tr><td>Orca, and restricted ACE (≥ 0.001) where Orca finds no analysis</td>' + td(pct(fb['counts']['same MRS'], N), True) + td(pct(fb['counts']['with MRS'], N))
                    + td(f"{SP['fallback']['sentences per second']:.1f}" if SP else f"{fb['sentences per second']:.1f}") + '</tr>')
    rows.append(f'<tr><td>ACE, full lexicon</td>' + td(pct(T['ace']['all']['same MRS'], N), True) + td(pct(T['ace']['all']['with MRS'], N)) + td(f'{N / (ACE_PASS + ACE_RETRY):.1f}') + '</tr>')
    t = table([('Redwoods dev, raw text', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Sentences per second', 'n')], rows)
    body = t + notes('Restricted ACE: the DeBERTa tagger\'s lexical labels become lexical entries (Orca\'s lookup); every other lexeme that could match a word is switched off (ACE -L), so ACE\'s chart and the ERG\'s ranking model work only with the tagger\'s choices. Tree labels are not used.',
                     'Speed measured end to end on one kesha GPU (tagging) and one CPU core (ACE); replay, the 0.001 row and the fallback row back to back on 24 November, while other jobs ran, so all slower than on a quiet machine. ACE alone: measured earlier.',
                     'The tagger gets lexical types right far more often than tree labels; the chart finds trees that label-by-label replay misses.')
    return fold('The tagger plus a chart: ACE restricted to the tagger\'s words', 'More accurate than replay (about five points) at less than half Orca\'s speed and almost three times ACE\'s.', body, id_='chart')


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
    xr, xc = (load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav2xlarge-rawtext-minprob001.json') or load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav2xlarge-rawtext.json')), load(f'{ORCA}/analysis/mrs/dev-2025bothsurf-debertav2xlarge-rawtext-chart-0.001.json')
    if xr:
        rows.append('<tr><td>One larger tagger: DeBERTa-v2 xlarge (about 900M parameters)</td>' + td(pct(xr['counts']['same MRS'], N), True) + td(pct(xr['counts']['with MRS'], N))
                    + (td(pct(xr['counts']['gold MRS among accepted'], N)) if 'gold MRS among accepted' in xr['counts'] else td(na('not recorded'))) + (td(pct(xc['counts']['same MRS'], N), True) if xc else td(na('running'))) + '</tr>')
    t = table([('DeBERTa-v3 large taggers', ''), ('Same meaning as gold', 'n hl'), ('Any analysis', 'n'), ('Gold among the analyses', 'n'), ('Same meaning as gold', 'n hl')], rows,
              group=[('', 1), ('Replay', 3), ('Chart mode', 1)])
    return ('    <h3>Averaging taggers, and a larger one</h3>\n' + t
            + notes('Label probabilities averaged per word; each extra model adds about 37 ms of tagging per sentence on GPU. The xlarge tagger tags better word by word, but its exact meaning is within one run-to-run spread (about one point) of DeBERTa-v3 large. One run each on dev.', NOT_YET + 'end-to-end speed with several taggers.'))


def exp_corpus_modes(open_=False):
    d = load(f'{ORCA}/analysis/corpus-modes/summary.json')
    if not d:
        return ''
    M = d['modes']
    groups = [('All', 'all'), ('Novels (held-out excerpts)', 'novels'), ('&nbsp;&nbsp;… human', 'novels/human'), ('&nbsp;&nbsp;… LLM', 'novels/LLM'),
              ('News, 2025', 'news'), ('&nbsp;&nbsp;… human (NYT)', 'news/human'), ('&nbsp;&nbsp;… LLM', 'news/LLM'),
              ('Under 10 words', 'band under 10'), ('10 to 19 words', 'band 10-19'), ('20 to 29 words', 'band 20-29'), ('30 words or more', 'band 30 and over')]
    rows = []
    for name, k in groups:
        c0 = M['replay']['counts'].get(k)
        if not c0:
            continue
        cells = td(f"{c0['ACE parsed']:,}")
        for m in ('replay', 'fallback', 'chart'):
            c = M[m]['counts'][k]
            cells += td(pct(c['same as ACE'], c['ACE parsed']), True) + td(pct(c['analysis'], c['n']))
        rows.append(f'<tr><td>{name}</td>' + cells + '</tr>')
    ns = load(f'{ORCA}/analysis/corpus-modes/news-split.json')
    if ns:
        for name, k in (('News not in Orca\'s training', 'news, not in training'), ('&nbsp;&nbsp;… human', 'news, not in training/human'), ('&nbsp;&nbsp;… LLM', 'news, not in training/LLM'),
                        ('News in Orca\'s training', 'news, in training')):
            c0 = ns['modes']['replay'].get(k)
            if not c0:
                continue
            cells = td(f"{c0['ACE parsed']:,}")
            for m in ('replay', 'fallback', 'chart'):
                c = ns['modes'][m][k]
                cells += td(pct(c['same as ACE'], c['ACE parsed']), True) + td(pct(c['analysis'], c['n']))
            rows.append(f'<tr><td>{name}</td>' + cells + '</tr>')
    t = table([('Corpus sample (2,000 sentences)', ''), ('ACE parsed', 'n'), ('Same as ACE', 'n hl'), ('Any analysis', 'n'), ('Same as ACE', 'n hl'), ('Any analysis', 'n'),
               ('Same as ACE', 'n hl'), ('Any analysis', 'n')], rows, group=[('', 2), ('Replay', 2), ('Fallback', 2), ('Chart', 2)])
    j = load(f'{ORCA}/analysis/corpus-modes/judge-fallback/score.json')
    body = t + notes('500 sentences each from held-out novel excerpts (human, LLM) and 2025 news (NYT, LLM). Reference: ACE\'s first parse, unchecked silver; Orca\'s grammar replays 1,917 of ACE\'s 1,927 derivations, so the grammar versions barely differ.',
                     '<b>Same as ACE</b> is a share of the sentences ACE parsed; <b>Any analysis</b> is a share of all sampled sentences.',
                     'Chart mode shares ACE\'s ranking model, so part of its agreement with ACE is built in.',
                     '<b>Correction:</b> 815 of the 1,000 news sentences were already in Orca\'s training data (found on 24 November); the last rows split them. On unseen news, replay agrees with ACE about ten points less, chart mode barely changes. The novels were all unseen.',
                     'Speeds are not shown: the machine was loaded by other jobs during these runs.')
    pairs = [('Fallback', 'ACE', 'judge-fallback'), ('Chart', 'replay', 'judge-chart-replay'), ('Chart', 'ACE', 'judge-chart-ace')]
    jrows, cost = [], 0
    for first, second, f in pairs:
        jj = load(f'{ORCA}/analysis/corpus-modes/{f}/score.json')
        if not jj:
            continue
        cost += jj.get('cost_usd', 0)
        by = jj.get('by_id', {})
        for gname, pre in (('all', ''), ('novels', 'novels-'), ('news', 'news-')):
            v = collections.Counter(x for i2, x in by.items() if i2.startswith(pre)) if by else collections.Counter(jj['verdicts'])
            n = sum(v.values())
            if not n:
                continue
            label = f'<b>{first} against {second}</b>' if gname == 'all' else f'&nbsp;&nbsp;… {gname}'
            jrows.append(f'<tr><td>{label}</td>' + td(f'{n:,}') + td(pct(v.get('orca', 0), n), True) + td(pct(v.get('reference', 0), n), True)
                         + td(pct(v.get('both', 0), n)) + td(pct(v.get('neither', 0), n)) + '</tr>')
    if jrows:
        body += (table([('Where two systems disagree, a random sample', ''), ('Judged', 'n'), ('First right', 'n hl'), ('Second right', 'n hl'), ('Both', 'n'), ('Neither', 'n')], jrows)
                 + notes(f'Claude Opus, readings shown in random order (${cost:.2f} in all). Only sentences where both systems have an analysis.',
                         'Head to head, chart and replay are about even: chart is preferred on news, replay on novels. Where chart and ACE differ, ACE is preferred about two to one.'))
    return fold('The modes on real text: novels and news', 'Replay agrees with ACE far less on corpus text than on dev; fallback analyzes almost everything; chart mode agrees with ACE most.', body, open_=open_, id_='corpus')


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
                     'A clause before the subject makes first guesses fail more often, whichever number its noun has; whether the difference between the two numbers is real has not been tested.',
                     NOT_YET + 'the DeBERTa tagger, and chart mode, which shares ACE\'s chart and may accept the strained readings.')
    return fold('Agreement after distracting material', 'Wrong agreement is turned down; ACE finds strained readings that Orca does not.', body, id_='agreement')


def exp_label_filter():
    d = load(f'{ORCA}/analysis/label-filter/summary.json')
    if not d:
        return ''
    R = d['runs']
    def row(name, k):
        r = R[k]
        return (f'<tr><td>{name}</td>' + td(pct(r['exact'], N), True) + td(pct(r['with properties and ICONS'], N)) + td(pct(r['any analysis'], N))
                + td(pct(r['gold among accepted'], N)) + td(f"{r['replays'] / N:.0f}") + '</tr>')
    t = table([('Repair, DeBERTa-v3 large tags', ''), ('Same meaning as gold', 'n hl'), ('… with tense, number and information structure too', 'n'), ('Any analysis', 'n'),
               ('Gold among the analyses found', 'n'), ('Replays per sentence', 'n')],
              [row('Current defaults (labels down to probability 0.001)', 'base-0.001'), row('&nbsp;&nbsp;… and the label filter', 'filter-0.001'),
               row('Labels down to probability 0.0001', 'base-0.0001'), row('&nbsp;&nbsp;… and the label filter', 'filter-0.0001')])
    body = t + notes('The filter skips, without a replay, label combinations the grammar can never accept: a leaf whose lexical type cannot take its rules, or a binary rule that cannot take the single-word daughters its tree label gives it. Checked with the most general sign of each label, so it never rules out anything the grammar would accept; on all Redwoods train and dev gold labels it rejects only sentences whose lexical type no longer has an entry in ERG 2025.',
                     'Redwoods dev from raw text; all four runs use the same saved tagger output, so differences come from the search alone. Repair time did not improve: checking every candidate costs about what the skipped replays saved.',
                     'Gains are within the run-to-run spread of about one point, so the filter stays off (repair.py --label-filter).')
    return fold('Ruling out label pairs the grammar can never combine', 'Sound, and it skips a quarter of the replays, but almost none of the skipped candidates would have been right.', body, id_='label-filter')


def exp_grammar_drift():
    d = load(f'{ORCA}/analysis/grammar-drift/compare-2025-2020.json')
    if not d:
        return ''
    c = d['counts']
    rows = [f'<tr><td>ERG 2025 (the grammar the tagger was trained for)</td>' + td(pct(c['A: first guess accepted'], N)) + td(pct(c['A: any analysis'], N), True)
            + td(f"{c['A: replays'] / N:.0f}") + td(na('the reference run')) + '</tr>',
            f'<tr><td>ERG 2020, same tagger output</td>' + td(pct(c['B: first guess accepted'], N)) + td(pct(c['B: any analysis'], N), True)
            + td(f"{c['B: replays'] / N:.0f}") + td(pct(c['both analyzed: same MRS'], c['both analyzed'])) + '</tr>']
    m = load(f'{ORCA}/analysis/grammar-drift/summary-map.json')
    if m:
        R = m['runs']
        mrow = lambda name, k: (f'<tr><td>{name}</td>' + td(pct(R[k]['first guess accepted'], N)) + td(pct(R[k]['any analysis'], N), True)
                                + td(f"{R[k]['replays per sentence']:.0f}") + td(pct(R[k]['same MRS as the reference'], R[k]['both analyzed'])) + '</tr>')
        rows = rows[:1] + [mrow('&nbsp;&nbsp;… with the word-level fallback', 'ERG 2025, word fallback after generic entries')] + rows[1:]
        for name, k in (('&nbsp;&nbsp;… with labels mapped to ERG 2020', 'ERG 2020, type map'), ('&nbsp;&nbsp;… and the word-level fallback', 'ERG 2020, type map, word fallback after generic')):
            if k in R:
                rows.append(mrow(name, k))
    t = table([('Redwoods dev, DeBERTa-v3 large tags from raw text', ''), ('First guess accepted', 'n'), ('Any analysis', 'n hl'), ('Replays per sentence', 'n'),
               ('Same MRS as under ERG 2025, where both have one', 'n')], rows)
    w = d['A analyzed, B not: why']
    lost = sum(w.values())
    names = {'unification failure in B': 'A rule or type with the same name has a changed definition', 'chosen derivation uses a name B lacks': 'A lexical type or rule that ERG 2020 does not have',
             'missing name or entry in B': 'The word has no entry of that type in ERG 2020'}
    t2 = table([(f'Sentences analyzed under ERG 2025 but not under ERG 2020 ({lost:,})', ''), ('Share', 'n')],
               [f'<tr><td>{names.get(k, k)}</td>' + td(pct(v, lost)) + '</tr>' for k, v in sorted(w.items(), key=lambda kv: -kv[1])])
    body = (t + notes('The tagger and the MaxEnt ranking model are each used with their own grammar version (redwoods.mem of 2020 for the 2020 run); tokens are ERG 2025 preprocessing in both runs. Exact match against gold is not shown for 2020: the gold analyses are made with ERG 2025.',
                      'A label the grammar does not have counts as a rejected guess and repair moves on; no sentence fails with an error.')
            + t2 + notes('Each lost sentence counted once, by why the derivation chosen under ERG 2025 fails under ERG 2020. Most changed definitions are one constraint in one rule (flr-hd_rel-fin_c).',
                         'Labels mapped to ERG 2020: a lexical type the grammar lacks is replaced by the type its lexical entries have there (40 of 108 missing types map this way; the rest are new words). Word-level fallback: where a word has no entry of the proposed type, its other entries of the same part of speech are tried after the grammar\'s generic entries, and replay decides. Neither needs retraining; both are options, off by default (orca_parse.py --label-map, --word-fallback).',
                         'The missing rules are new constructions, not renames, so none map. Changed definitions need retraining on data replayed under the new grammar.')
            + cap('The installed trunk and latest GitHub copies of the ERG are the same as ERG 2025, so 2020 is the only different version tested.'))
    return fold('When the grammar changes: the tagger against ERG 2020', 'Trained for ERG 2025, the tagger finds an analysis for clearly fewer sentences under ERG 2020; mapping labels and trying other entries of the same word win back about half, without retraining.', body, id_='grammar-drift')


def exp_judge_check():
    d1 = load(f'{ORCA}/analysis/judge-check/olga-verdicts.json')
    d2 = load(f'{ORCA}/analysis/judge-check2/olga-verdicts.json')
    if not d1:
        return ''
    def row(name, c, total):
        n = sum(c.values())
        return (f'<tr><td>{name}</td>' + td(f'{n:,} of {total}') + td(pct(c.get('ACE', 0), n), True) + td(pct(c.get('both', 0), n)) + td(pct(c.get('gold', 0), n), True)
                + td(pct(c.get('neither', 0) + c.get('unsure', 0), n)) + '</tr>')
    rows = [row('The judge preferred ACE\'s first parse', d1['counts'], 111)]
    if d2:
        rows.append(row('The judge preferred gold', d2['counts'], 154))
    t = table([('Dev sentences where ACE\'s first parse differs from gold (288), a random sample per judge verdict', ''), ('Reviewed', 'n'),
               ('ACE\'s reading is right', 'n hl'), ('Both acceptable', 'n'), ('Gold is right', 'n hl'), ('Neither, or can\'t tell', 'n')], rows,
              group=[('', 2), ('The person\'s verdict', 4)])
    body = t + notes('Olga Zamaraeva, 24 November 2026, blind: the two readings as DMRS graphs in random order, with a neutral paraphrase of each. In the second set, three cases she marked unsure were decided by Claude at her request, with the reasons recorded (all three for gold).',
                     'When the judge sides with gold it is almost always right; when it sides with ACE, it is right more often than not, and otherwise the gold is right. So where the two readings differ, Redwoods gold is often the debatable one, and exact match against gold understates both ACE and Orca.',
                     'One reviewer and 30 cases per row: each share is uncertain by about twenty points either way.')
    jv = load(f'{ORCA}/analysis/judge-variants/score.json')
    if jv:
        R = jv['results']
        vrow = lambda k: (f'<tr><td>{jv["variants"][k][0].upper() + jv["variants"][k][1:]}</td>' + td(pct(R[k]['all 60']['exact'], 60), True) + td(pct(R[k]['all 60']['lenient'], 60))
                          + td(pct(R[k]['without the 3 decided by Claude']['exact'], 57)) + '</tr>')
        body += ('    <h3>Can the judge do better?</h3>\n'
                 + table([('Judge variant, on the 60 reviewed cases', ''), ('Agrees with the person', 'n hl'), ('… counting \'both acceptable\' as compatible', 'n'), ('Agrees, without the three cases decided by Claude', 'n')],
                         [vrow(k) for k in ('v1', 'v2', 'v3', 'v4')])
                 + notes('Paraphrases: a plain-English statement of what each reading means, written by Claude from the differences alone and told not to say which is better. Documentation: the lexical types of differing predicates, with their descriptions and example sentences from the ERG.',
                         f'Claude Opus on the subscription (${jv["cost_usd total"]:.2f}). The cases were chosen by the original judge\'s verdict, so compare the variants with each other, not the absolute rates with dev as a whole; 60 cases leave about twelve points of uncertainty.',
                         'The judge with paraphrases is used from 24 November on.'))
    return fold('Checking the judge against a person', 'The judge agrees with a person in most cases, nearly always when it sides with gold; where it sides with ACE, the gold is often the debatable reading.', body, id_='judge-check')

def exp_examples():
    steps = open(os.path.join(HERE, 'steps-legend.html')).read()
    body = steps + '    <div id="examples" class="stack" style="gap:28px"></div>\n'
    return fold('Four worked examples', 'Labels, tree, feature structure, MRS and DMRS for real dev sentences.', body, id_='worked-examples')


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


SHORT_CSS = '''
ol.short, ul.short { margin: 0; padding-left: 1.3em; display: flex; flex-direction: column; gap: 9px; max-width: 80ch; }
ol.short a, ul.notes a, .caption a { color: var(--accent); white-space: nowrap; }
p.answer { font-size: 1.08rem; max-width: 76ch; }
section[id], details[id] { scroll-margin-top: 12px; }
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
    how_shown, tagger_fold = how()
    body = ('\n' + tiles() + '\n'
            + question('what', 'What Orca is', 'A tagger proposes a whole derivation of the grammar, and the grammar checks it by unification; there is no chart.', how_shown, tagger_fold)
            + question('good', 'How good is it?', 'Replay is several times faster than ACE and clearly less accurate; adding a chart, or sending the hard sentences to ACE, buys back most of the gap at some of the speed.',
                       summary() + '    <h3>The modes side by side</h3>\n' + modes(), exp_supertag_ace() + exp_hybrid() + exp_ace() + exp_judge_check())
            + question('wrong', 'Where does it go wrong?', 'Mostly in proposing: for most wrong sentences the right meaning is never among the analyses found, and failures grow with length. What Orca does output is about as precise as ACE\'s.',
                       results(), exp_edm() + exp_replay_rate())
            + question('beyond', 'Does it hold beyond the treebank?', 'Partly: on novels and news replay agrees with ACE less than on the treebank and chart mode much more; on generated sentences, and where ACE fails, the judge often sides with Orca.',
                       '', exp_corpus_modes(open_=True) + exp_generated() + exp_beyond_ace() + exp_agreement())
            + question('better', 'What makes it better?', 'A stronger encoder and more silver data each add a few points; differences of about one point are within run-to-run spread; LLMs help offline only.',
                       '', exp_encoders(open_=True) + runs() + exp_training() + exp_label_filter() + exp_rawtext() + exp_llm() + exp_llm_rank())
            + question('grammars', 'Does it work with other grammars?', 'So far, yes: Orca replays the Hausa and Spanish grammars\' own parses once ERG-specific assumptions are removed, and a first Spanish tagger works.',
                       '', exp_hausa(open_=True) + exp_spanish() + exp_grammar_drift())
            + question('reference', 'Reference', 'Further measures and worked examples.', '', exp_properties() + exp_examples()) + '\n')
    s = s[:start] + body + s[end:]
    if 'details.fold' not in s:
        s = s.replace('</style>', CSS + '</style>', 1)
    if 'ul.finds' not in s:
        s = s.replace('</style>', 'ul.finds { margin: 0; padding-left: 1.2em; display: flex; flex-direction: column; gap: 6px; }\n</style>', 1)
    if 'ul.notes' not in s:
        s = s.replace('</style>', 'ul.notes { margin: 0; padding-left: 1.1em; font-size: 0.85rem; color: var(--muted); display: flex; flex-direction: column; gap: 2px; }\n</style>', 1)
    if 'p.answer' not in s:
        s = s.replace('</style>', SHORT_CSS + '</style>', 1)
    if 'span.na' not in s:
        s = s.replace('</style>', 'span.na { color: var(--muted); font-style: italic; font-size: 0.85em; }\n</style>', 1)
    return s


if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = open(p).read()
        out = rebuild(s)                # build first, so a failure leaves the page untouched
        open(p, 'w').write(out)
        print('rebuilt', p)
