#!/usr/bin/env python3
"""Replay ACE's parses with Orca and compare MRSs, counting also the analyses
that differ only in which same-type entry a word uses (lexicon.entry_variants).

For each replayable sentence: Orca's first resolution (lexicon order) is compared
with ACE's first-ranked MRS; then, if it differs, whether ACE's MRS is among the
entry variants Orca also accepts.

Usage:
    check_entry_variants.py --grammar TOP.tdl --profiles DIR --replayable FILE.jsonl [--limit N] [--out OUT.json]
"""
import argparse
import collections
import glob
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..'))
sys.setrecursionlimit(20000)


def main():
    from delphin import mrs as M, tsdb
    from delphin.codecs import simplemrs
    from compare_mrs import to_pydelphin
    from eval_trees import to_leaves
    from llm_label import labels_of
    from orca.encoding import decode
    from orca.tfs.fast import FastGrammar, extract
    from orca.tfs.grammar import Grammar
    from orca.tfs.lexicon import Lexicon, replay_with_entries, entry_variants
    from replay_predictions import gold_tokens

    ap = argparse.ArgumentParser()
    ap.add_argument('--grammar', required=True)
    ap.add_argument('--profiles', required=True)
    ap.add_argument('--replayable', required=True)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--out')
    a = ap.parse_args()

    ace = {}
    for prof in sorted(glob.glob(os.path.join(a.profiles, '*'))):
        if not os.path.exists(os.path.join(prof, 'relations')):
            continue
        names = [f.name for f in tsdb.read_schema(prof)['result']]
        with tsdb.open(prof, 'result') as rows:
            for line in rows:
                rec = tsdb.split(line)
                if rec[names.index('mrs')]:
                    ace.setdefault(f"{os.path.basename(prof)}/{rec[names.index('parse-id')]}", rec[names.index('mrs')])
    toks = gold_tokens(a.profiles)
    g = Grammar(a.grammar)
    fg, lx = FastGrammar(g), Lexicon(g, os.path.dirname(a.grammar))
    c, diffs = collections.Counter(), []
    lines = open(a.replayable).read().splitlines()[:a.limit]
    for line in lines:
        r = json.loads(line)
        if r['id'] not in ace:
            continue
        ref = simplemrs.decode(ace[r['id']])
        forms, leaf, tree = labels_of(r['tokens'])
        t = decode(to_leaves(forms, leaf, tree))
        fg.reset()
        try:
            fs, resolved = replay_with_entries(fg, lx, t, toks[r['id']])
        except Exception:
            c['replay failed'] += 1
            continue
        m = to_pydelphin(extract(fg, fs))
        c['sentences'] += 1
        same = M.is_isomorphic(m, ref, properties=True)
        c['first resolution = ACE'] += same
        alts = entry_variants(fg, lx, t, toks[r['id']], resolved)
        c['with entry variants'] += bool(alts)
        among = same
        if not same:
            for alt in alts:
                fg.reset()
                fs2, _ = fg.replay_tree(alt, toks[r['id']])
                if M.is_isomorphic(to_pydelphin(extract(fg, fs2)), ref, properties=True):
                    among = True
                    break
            diffs.append({'id': r['id'], 'variants': len(alts), 'ace among variants': among})
        c['ACE among first or variants'] += among
    out = {'counts': dict(c), 'differences': diffs}
    print(json.dumps(out['counts'], indent=1))
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
