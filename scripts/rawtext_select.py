"""Training folder from the raw-text silver, chosen per source by the agreement check (data/rawtext/agreement):
Gutenberg keeps Orca's confident analyses (82% agreement with ACE), Wikipedia keeps only ACE's analyses (75%).
Writes data/encoded-2025-bothall-raw1sel-surface."""
import glob, json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data/rawtext')
BASE = os.path.join(ROOT, 'data/encoded-2025-bothall-news25-surface/train.jsonl')
OUT = os.path.join(ROOT, 'data/encoded-2025-bothall-raw1sel-surface')
ACE_ONLY = {'wikipedia'}

def ace_ids(source):
    d = os.path.join(RAW, source); id_of = {}
    for f in sorted(glob.glob(os.path.join(d, 'chunk-*.ids'))):
        c = os.path.basename(f)[6:9]
        for n, i in enumerate(open(f).read().split()):
            id_of[(f'{source}-{c}', n + 1)] = i
    out = set()
    for l in open(os.path.join(d, 'ace-train.jsonl')):
        prof, pid = json.loads(l)['id'].split('/')
        if (prof, int(pid)) in id_of:
            out.add(f'raw-{id_of[(prof, int(pid))]}')
    return out

keep = {s: ace_ids(s) for s in ACE_ONLY}
os.makedirs(OUT, exist_ok=True)
n = {'base': 0}
with open(os.path.join(OUT, 'train.jsonl'), 'w') as o:
    for l in open(BASE):
        o.write(l); n['base'] += 1
    for l in open(os.path.join(RAW, 'silver/train.jsonl')):
        rid = json.loads(l)['id']; src = rid[4:].split('/')[0]
        if src in ACE_ONLY and rid not in keep[src]:
            n[f'{src} dropped (Orca origin)'] = n.get(f'{src} dropped (Orca origin)', 0) + 1; continue
        o.write(l); n[src] = n.get(src, 0) + 1
for s in ('dev', 'test'):
    t = os.path.join(OUT, f'{s}.jsonl')
    if not os.path.exists(t):
        os.symlink(f'../encoded-2025-bothall-surface/{s}.jsonl', t)
open(os.path.join(OUT, 'README'), 'w').write(__doc__ + '\n' + json.dumps(n, indent=1) + '\n')
print(n)
