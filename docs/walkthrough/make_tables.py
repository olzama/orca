"""Rebuild the accuracy and speed tables of the walkthrough from measured data."""
import json
import sys

ORCA = '/mnt/kesha/orca'
T = json.load(open(f'{ORCA}/analysis/mrs/dev-2025-tables.json'))
N = T['ace']['all']['sentences']
BANDS = [('under 10', 'Under 10'), ('10-19', '10 to 19'), ('20-29', '20 to 29'), ('30 and over', '30 and over')]


def pct(k, n):
    return f'{100 * k / n:.1f}% ({k:,})'


def prf(d):
    return f"{100 * d['precision']:.1f} / {100 * d['recall']:.1f} / {100 * d['f1']:.1f}"


def td(x, hl=False):
    return f'<td class="n{" hl" if hl else ""}">{x}</td>'


ROWS = [
    ('first_proposal', "Orca: tagger's first proposal, replayed by the grammar"),
    ('first_accepted', 'Orca: after repair, first accepted derivation'),
    ('best', "Orca: after repair, best of up to 30 accepted derivations by the ERG's ranking model"),
    ('best_llm', 'Orca: as above, plus LLM repair for the 390 sentences left without an analysis'),
    ('ace', 'ACE chart parser, its first-ranked analysis (baseline)'),
]


def main_table():
    body = []
    for key, name in ROWS:
        a = T[key]['all']
        body.append('          <tr><td>' + name + '</td>' + td(pct(a['same MRS'], N), True) + td(pct(a['with MRS'], N))
                    + td(prf(a['preds'])) + td(prf(a['links'])) + td(pct(a['same tree'], N)) + '</tr>')
    body.append('          <tr><td>Check of the engine: gold derivations, replayed</td>' + td(pct(N, N), True)
                + td(pct(N, N)) + td('100 / 100 / 100') + td('100 / 100 / 100') + td(pct(N, N)) + '</tr>')
    return f'''    <div class="scroll">
      <table class="results">
        <thead><tr><th>System</th><th class="n hl">Same meaning as gold (MRS)</th><th class="n">Complete analysis built</th><th class="n">Predicates in gold: precision / recall / F1</th><th class="n">Links in gold: precision / recall / F1</th><th class="n">Same tree as gold</th></tr></thead>
        <tbody>
{chr(10).join(body)}
        </tbody>
      </table>
    </div>
    <p class="caption">Sentence counts are in parentheses. The predicate and link columns count the predicates and the semantic links of each analysis that also occur in the gold analysis, summed over the whole set: precision is over what the system produced, recall over what gold contains, so a sentence without an analysis lowers recall but not precision. "Same tree" compares the whole derivation tree, rules and lexical types included, but not the root condition, which ACE's output does not record. Where Orca gives an analysis, its precision is as high as ACE's; the gap is in recall, that is, in the sentences it leaves without an analysis. Every Orca row requires each word to have an entry of the proposed type in the lexicon (or an unknown-word entry), as the parser does. The ranking model is the one ACE uses, shipped with the grammar; it scores Orca's derivations exactly as ACE scores its own. ACE is the parser the treebank was made with: its analyses for these sentences include the gold one, and its ranking model chose the first-ranked one. The four sentences it could not analyze ran out of memory at 28 GB. The last row shows that when the engine is given the annotators' derivations it reproduces their semantics for every sentence, so the losses in the rows above come from the tagger's proposals. Not yet compared: word segmentation (taken from the treebank) and tense and number on variables.</p>
  </section>
'''


def band_table(title, col):
    rows = []
    for b, label in BANDS:
        n = T['ace'][b]['sentences']
        rows.append(f'          <tr><td>{label}</td>' + td(f'{n:,}') + ''.join(td(col(T[s][b], n), True) for s in ('ace', 'best', 'best_llm')) + '</tr>')
    return f'''    <h3>{title}</h3>
    <div class="scroll">
      <table class="results">
        <thead><tr><th>Words in the sentence</th><th class="n">Sentences</th><th class="n hl">ACE</th><th class="n hl">Orca</th><th class="n hl">Orca plus LLM repair</th></tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
    </div>
'''


def side_by_side():
    ace_pass, ace_retry = 1276.6, 437.8 + 301.5          # data/ace/dev-ace-1best, -retry16, -retry28
    tag, rep1, rep6, k1_6, rank = 17.46, 144.26, 28.87, 7.49, 2.0
    llm_secs, llm_sents, streams = 26136.2, 390, 4
    full = tag + rep1 + rank
    r = lambda x: f'{x:,.1f}' if x < 100 else f'{x:,.0f}'
    rows = [
        ('ACE, first-ranked analysis, all sentences, retries with more memory included', r(N / (ace_pass + ace_retry)), 'one CPU core', 'up to 28 GB, and more for the 4 it could not finish', '4'),
        ('ACE, first pass only, without the retries', r(N / ace_pass), 'one CPU core', 'up to 6 GB for the chart and 6 GB for unpacking', '14'),
        ('ACE, median sentence', r(1 / 0.046), 'one CPU core', '', ''),
        ('Orca: tagging', r(N / tag), 'one GPU (RTX 2080 Ti)', 'not measured', ''),
        ('Orca: replay of one given derivation', 'about 670', 'one CPU core', 'megabytes per sentence', ''),
        ('Orca: repair, stopping at the first accepted derivation', r(N / k1_6), 'six CPU cores', 'megabytes per sentence', f"{N - T['first_accepted']['all']['with MRS']:,}"),
        ('Orca: repair, collecting up to 30 accepted derivations', r(N / rep1), 'one CPU core', 'megabytes per sentence', f"{N - T['best']['all']['with MRS']:,}"),
        ('Orca: the same repair', r(N / rep6), 'six CPU cores', 'megabytes per sentence', f"{N - T['best']['all']['with MRS']:,}"),
        ('Orca: ranking the accepted derivations', 'about 1,000', 'one CPU core', 'megabytes per sentence', ''),
        ('Orca, full pipeline: tagging, repair collecting up to 30, ranking', r(N / full), 'one GPU and one CPU core', 'megabytes per sentence', f"{N - T['best']['all']['with MRS']:,}"),
        ('LLM repair step, for the sentences the pipeline leaves without an analysis', f'{llm_sents / llm_secs:.3f} per model stream; {streams * llm_sents / llm_secs:.2f} with {streams} streams in parallel', 'remote model (Claude Opus)', 'megabytes per sentence locally', f"{N - T['best_llm']['all']['with MRS']:,}"),
        ('Orca, full pipeline plus LLM repair, over all sentences', f'{N / (full + llm_secs / streams):.2f}', f'as above, {streams} model streams', '', f"{N - T['best_llm']['all']['with MRS']:,}"),
    ]
    body = '\n'.join('          <tr><td>' + a + '</td>' + ''.join(td(x or '—') for x in rest) + '</tr>' for a, *rest in rows)
    return ('''  <section class="stack">
    <h2>Orca and the ACE chart parser, side by side</h2>
    <p>ACE is the parser the treebank was built with. It searches a chart of all possible analyses and then ranks them with a statistical model. Orca proposes one derivation per sentence with the tagger and lets the grammar check it, so it never builds the chart.</p>
''' + band_table('Same meaning as gold, by sentence length', lambda d, n: pct(d['same MRS'], n))
        + band_table('Complete analysis built, by sentence length', lambda d, n: pct(d['with MRS'], n))
        + band_table('Links in gold (F1), by sentence length', lambda d, n: f"{100 * d['links']['f1']:.1f}")
        + '''    <p class="caption">Word counts are treebank tokens. Both systems lose accuracy with length; Orca loses it much faster, mostly because for long sentences it more often finds no accepted derivation at all. The LLM step recovers about half of the missing analyses in every length band, but for long sentences the analyses it finds are rarely exact.</p>
    <h3>Speed and memory on the same 2,062 sentences</h3>
    <div class="scroll">
      <table class="results">
        <thead><tr><th>System or stage</th><th class="n">Sentences per second</th><th class="n">Hardware</th><th class="n">Memory needed</th><th class="n">Sentences left without an analysis</th></tr></thead>
        <tbody>
''' + body + '''
        </tbody>
      </table>
    </div>
    <p class="caption">Sentences per second is the number of sentences divided by the total time of that stage. ACE's average is dominated by its longest sentences: the hardest ran out of memory after building up to 230,000 chart edges, while most sentences take a fraction of a second. Orca's time grows roughly in proportion to sentence length. The LLM step is measured as model time, the sum over all calls of the time each took; a call takes about 20 seconds. Loading the grammar (about 17 seconds for Orca, 1 for ACE) is not included. These are short sentences (about 12 words on average); the comparison on long sentences, where ACE often fails, is still to be made.</p>
  </section>

''')


def rebuild(s):
    start = s.index('    <div class="scroll">\n      <table class="results">\n        <thead><tr><th>System</th><th class="n hl">Same meaning')
    end = s.index('  <section class="stack">\n    <h2>Tested:')
    s = s[:start] + main_table() + '\n' + side_by_side() + s[end:]
    b = T['best']['all']
    old_tiles = s[s.index('      <div class="tile main">'):s.index('    </div>', s.index('      <div class="tile main">'))]
    tiles = (f'      <div class="tile main"><b>{100 * b["same MRS"] / N:.1f}%</b><span>of sentences get <strong>exactly the gold meaning</strong> (the same MRS)</span></div>\n'
             f'      <div class="tile"><b>{100 * b["with MRS"] / N:.1f}%</b><span>get a complete analysis that the grammar accepts, with full structure and semantics</span></div>\n'
             f'      <div class="tile"><b>{100 * b["same tree"] / N:.1f}%</b><span>get exactly the gold tree</span></div>\n')
    return s.replace(old_tiles, tiles)


for p in sys.argv[1:]:
    s = open(p).read()
    open(p, 'w').write(rebuild(s))
    print('rebuilt', p)
