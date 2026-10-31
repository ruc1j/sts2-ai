"""Act 1-2 dropout funnel and per-encounter loss rates over v23+v24 (fights grouped by act via boss kills)."""
from fullrun_load import *
import statistics as st
from collections import defaultdict
BOSS1={'MONSTER.VANTOM'}; BOSS2={'MONSTER.THE_INSATIABLE'}
tab=defaultdict(lambda:[0,0,[]]); funnel=defaultdict(int)
for tag,seed,p in runs():
    rows=R.read_rows(p); a=0; cur=None; fights=[]
    for r in rows:
        if r['phase']=='combat':
            if cur is None: cur={'ids0':tuple(sorted(e['id'] for e in r.get('enemies') or [])),'hp0':r['player']['hp']}
        elif r['phase']=='combat_end' and cur is not None:
            cur['won']=r.get('won'); fights.append(cur); cur=None
    funnel['runs']+=1
    for fi in fights:
        ids=set(fi['ids0']); t=tab[(a,fi['ids0'])]; t[0]+=1; t[1]+=(not fi['won']); t[2].append(fi['hp0'])
        if a==0 and ids&BOSS1:
            funnel['vantom_fought']+=1
            if fi['won']: a=1; funnel['vantom_won']+=1
        elif a==1 and ids&BOSS2:
            funnel['insatiable_fought']+=1
            if fi['won']: a=2; funnel['insatiable_won']+=1
print(dict(funnel))
for lab in (0,1):
    print('--- Act',lab+1)
    for (l,ids),(n,lost,hp) in sorted(tab.items(),key=lambda kv:-kv[1][1]):
        if l!=lab or (lost==0 and n<5) or lost==0: continue
        print(f"{n:4d} fights {lost:3d} lost {100*lost/n:5.1f}%  entryHP med {st.median(hp):.0f}  {'+'.join(i.replace('MONSTER.','') for i in ids)}")
