import sys,json
sys.path.insert(0,'scripts'); sys.path.insert(0,'.'); sys.setrecursionlimit(20000)
from delphin import dmrs, mrs as M
from orca.tfs.grammar import Grammar
from orca.tfs.lexicon import Lexicon, replay_with_entries
from orca.tfs.mrs import extract, to_text
from orca.tfs.dag import deref
from orca.encoding import decode, Leaf
from eval_trees import to_leaves
from replay_predictions import gold_tokens
from compare_mrs import to_pydelphin
S=sys.argv[1]
g=Grammar('data/erg/2025/english.tdl'); lx=Lexicon(g,'data/erg/2025'); toks=gold_tokens('data/profiles-2025/dev')
ex=json.load(open(S+'/examples.json'))
SKIP={'RELS','HCONS','ICONS','CTXT','ARG-S','--SLASHED','MINORS','POSS','NEGPOL','HC-LEX','HS-LEX','NORM','RSUBJHD','LSYNSEM','LPRED','--MIN','--SIND','PT','SORT','COG-ST','SPECI','--TPC','--WH','--BARE','DIV','IND','PRONTYPE','CASE','CARDINAL','PRD','AUX','INV','--ADDIN','--MALCASE','--MALCM','--HID','LPERIPH','RPERIPH','MODIFD','PHON','PUNCT','LKEYS','--COMPHD','CNTRCTD','VAL','--MALPASCASE','ALTMIN','SPCMPS','KCMP','SPEC','MOD','AGR','CONJ'}
def nodes(n,seen):
    n=deref(n)
    if id(n) in seen: return
    seen.add(id(n)); [nodes(v,seen) for v in n.arcs.values()]
def avm(root,depth):
    count={}
    def scan(n,d):
        n=deref(n); count[id(n)]=count.get(id(n),0)+1
        if count[id(n)]>1 or d==0: return
        for f,v in n.arcs.items():
            if f not in SKIP: scan(v,d-1)
    scan(root,depth); tags={}; done=set()
    def out(n,d):
        n=deref(n); o={'t':n.type}
        if count.get(id(n),0)>1 and (n.arcs or True):
            if id(n) not in tags: tags[id(n)]=len(tags)+1
            o['g']=tags[id(n)]
            if id(n) in done: return {'g':tags[id(n)]}
            done.add(id(n))
        if d>0:
            fs=[(f,out(v,d-1)) for f,v in sorted(n.arcs.items()) if f not in SKIP]
            if fs: o['f']=fs
        elif n.arcs: o['more']=1
        return o
    return out(root,depth)
def lst(n):
    out=[]; n=deref(n)
    while 'FIRST' in n.arcs: out.append(deref(n.arcs['FIRST']).type); n=deref(n.arcs['REST'])
    return out,n.type
def build(forms,lab,key):
    fs,res=replay_with_entries(g,lx,decode(to_leaves(forms,lab['leaf'],lab['tree'])),toks[key])
    seen=set(); nodes(fs,seen)
    m=extract(g,fs); pm=to_pydelphin(m); d=dmrs.from_mrs(pm)
    ids={n.id:i for i,n in enumerate(d.nodes)}
    u=g.u; cat=u.get(fs,'SYNSEM','LOCAL','CAT'); val=u.get(cat,'VAL')
    entries=[]
    def lv(t):
        if isinstance(t,Leaf): entries.append([' '.join(t.forms),t.entry.replace('entry:','')])
        else: [lv(c) for c in t.children]
    lv(res)
    return {'n_nodes':len(seen),'entries':entries,
        'val':{f:lst(u.get(val,f)) for f in ('SUBJ','SPR','COMPS')},
        'avm':{'HEAD':avm(u.get(cat,'HEAD'),3),'HOOK':avm(u.get(fs,'SYNSEM','LOCAL','CONT','HOOK'),3),'NONLOC':avm(u.get(fs,'SYNSEM','NONLOC'),2)},
        'mrs':to_text(m).split('\n'),
        'dmrs':{'nodes':[[n.predicate,n.carg] for n in d.nodes],'links':[[ids[l.start],ids[l.end],l.role,l.post] for l in d.links],'top':ids.get(d.top)}}
out={}
out['A']=build(ex['A']['forms'],ex['A']['first'],ex['A']['id'])
out['B']=build(ex['B']['forms'],ex['B']['final'],ex['B']['id'])
out['C']=build(ex['C']['forms'],ex['C']['first'],ex['C']['id'])
out['Cgold']=build(ex['C']['forms'],ex['C']['gold'],ex['C']['id'])
json.dump(out,open(S+'/struct.json','w'),ensure_ascii=False)
a=out['A']; print(a['n_nodes'],a['val'],len(json.dumps(out)),len(json.dumps(a['avm'])))
print(json.dumps(a['avm']['HEAD'])[:700]); print(json.dumps(a['avm']['HOOK'])[:900]); print(a['dmrs'])
print(out['C']['mrs']==out['Cgold']['mrs'])
