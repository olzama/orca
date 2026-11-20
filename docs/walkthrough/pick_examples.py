import json,sys,collections
sys.path.insert(0,'scripts'); sys.path.insert(0,'.'); sys.setrecursionlimit(20000)
from llm_label import read
from eval_trees import to_leaves
from orca.encoding import decode, Leaf
from orca.tfs.grammar import Grammar
from replay_predictions import gold_tokens
from analyze_replay_outcomes import partial_replay
gold={s['id']:s for s in read('data/encoded-2025/dev.jsonl')}
first={json.loads(l)['id']:json.loads(l) for l in open('data/models/tagger-2025-bert/dev-pred.jsonl')}
rep=[json.loads(l) for l in open('data/models/tagger-2025-bert/dev-repair-b30.jsonl')]
toks=gold_tokens('data/profiles-2025/dev')
g=Grammar('data/erg/2025/english.tdl')
def nest(t):
    if isinstance(t,Leaf): return {'l':t.entry,'w':' '.join(t.forms)}
    return {'l':t.label,'c':[nest(c) for c in t.children]}
def tree(forms,leaf,tr): return decode(to_leaves(forms,leaf,tr))
def diff(a,b): return [j for j in range(len(a)) if a[j]!=b[j]]
out=collections.defaultdict(list)
for r in rep:
    s=gold[r['id']]; f=first[r['id']]; n=len(r['forms']); o=r['outcome']
    if any('’' in w or '⌊' in w for w in r['forms']): continue
    rec={'id':r['id'],'forms':r['forms'],'gold':{'leaf':s['leaf'],'tree':s['tree']},'first':{'leaf':f['leaf'],'tree':f['tree']},'final':{'leaf':r['leaf'],'tree':r['tree']},'outcome':o}
    key=None
    if o=='accepted at first try, right' and 6<=n<=8 and any('sb-hd' in x for x in s['tree']) and any('hd-cmp' in x for x in s['tree']) and r['id'].startswith('ws'): key='A'
    elif o=='accepted after repair, right' and 6<=n<=10 and len(diff(f['leaf'],r['leaf']))+len(diff(f['tree'][:-1],r['tree'][:-1]))==1: key='B'
    elif o=='accepted at first try, wrong' and 7<=n<=10 and not diff(f['leaf'],s['leaf']) and 1<=len(diff(f['tree'][:-1],s['tree'][:-1]))<=2 and any(f['tree'][j].split('|')[0]!=s['tree'][j].split('|')[0] for j in diff(f['tree'][:-1],s['tree'][:-1])): key='C'
    elif o.startswith('rejected, budget') and 22<=n<=28: key='D'
    if key and len(out[key])<6:
        try:
            rec['gold_tree']=nest(tree(r['forms'],s['leaf'],s['tree'])); t1=tree(r['forms'],f['leaf'],f['tree']); rec['first_tree']=nest(t1)
            rec['final_tree']=nest(tree(r['forms'],r['leaf'],r['tree']))
            acc,ok,fails=partial_replay(g,t1,toks[r['id']]); rec['first_accepted']=acc; rec['ok_spans']=ok; rec['failures']=fails
        except Exception as e: continue
        out[key].append(rec)
json.dump(out,open(sys.argv[1],'w'))
for k in sorted(out):
    for i,r in enumerate(out[k]): print(k,i,len(r['forms']),' '.join(r['forms']),'|',[(a,b,c,d[:70]) for a,b,c,d in r['failures']][:2])
