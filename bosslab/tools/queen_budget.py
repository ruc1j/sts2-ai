"""Queen fight damage budget (per-turn Queen/Amalgam HP, player HP) over the v23+v24 Queen fights."""
from fullrun_load import *
import statistics as st, json
def q(v):
    v=sorted(v); 
    if not v: return None
    return (round(st.median(v),1), round(v[len(v)//4],1), round(v[(3*len(v))//4],1))
recs=[]
for tag,seed,p in runs():
    rows=R.read_rows(p)
    qrows,won=R.queen_fight(rows)
    if not qrows: continue
    turns={}
    for r in qrows:
        turns.setdefault(r.get('turn',0),r)
    seq=[]
    for t in sorted(turns):
        r=turns[t]; en={e['id']:e for e in r['enemies']}
        qq=next((e for i,e in en.items() if i.endswith('.QUEEN')),None)
        a=next((e for i,e in en.items() if 'AMALGAM' in i),None)
        seq.append(dict(t=t,hp=r['player']['hp'],q=qq['hp'] if qq else 0,a=a['hp'] if a else None,blk=r['player'].get('block',0)))
    recs.append(dict(seed=seed,won=won,seq=seq))
out={}
killed=[r for r in recs if r['seq'][-1]['a'] is None]
notk=[r for r in recs if r['seq'][-1]['a'] is not None]
print('killed',len(killed),'not',len(notk))
# Amalgam kill turn = first seq entry with a None
pre_rate=[];post_rate=[];tk=[];hpk=[];qk=[];post_turns=[];post_hploss=[];need=[];life=[];pre_q=[]
for r in killed:
    s=r['seq']; i=next(j for j,x in enumerate(s) if x['a'] is None)
    if i==0: continue
    tk.append(s[i]['t']); hpk.append(s[i]['hp']); qk.append(s[i]['q'])
    # amalgam dmg rate before kill (amalgam max 199)
    pre_rate.append(199/ s[i]['t'] if s[i]['t'] else 0)
    npost=len(s)-1-i
    post_turns.append(npost)
    if npost>=1:
        dq=s[i]['q']-s[-1]['q']; post_rate.append(dq/npost)
        dh=s[i]['hp']-s[-1]['hp']; post_hploss.append(dh/npost)
for lab,v in [('Amalgam killed at turn',tk),('player HP at that point',hpk),('Queen HP at that point',qk),('post-kill turns survived',post_turns),('post-kill Queen dmg/turn (≥1 turn)',post_rate),('post-kill HP loss/turn',post_hploss)]:
    print(lab,len(v),q(v))
# required rate for killing Queen in the post-kill survival window, using the median fight
need=[ (qk[j]) for j in range(len(qk)) ]
# per-fight required dmg/turn to finish Queen before death, if post-kill turns survived n:
req=[]
for r in killed:
    s=r['seq']; i=next(j for j,x in enumerate(s) if x['a'] is None)
    if i==0: continue
    n=max(1,len(s)-1-i+1)  # turns incl. last
    req.append(s[i]['q']/n)
print('required Queen dmg/turn to have killed within observed window',q(req))
# not-killed: Amalgam hp remaining and turns
print('not-killed: turns',q([len(r['seq']) for r in notk]),'amalgam hp at end',q([r['seq'][-1]['a'] for r in notk]),'queen hp at end',q([r['seq'][-1]['q'] for r in notk]))
# total damage dealt per turn across both bosses (Amalgam+Queen), overall
tot=[]
for r in recs:
    s=r['seq']; n=len(s)
    dealt=(199-(s[-1]['a'] or 0))+(s[0]['q']-s[-1]['q'])
    tot.append(dealt/max(1,n))
print('total dmg/turn (avg over turns observed)',q(tot))
# early vs late: Queen HP lost per turn index
import collections
byturn=collections.defaultdict(list)
for r in recs:
    s=r['seq']
    for a,b in zip(s,s[1:]):
        byturn[a['t']].append((a['q']-b['q'])+((a['a'] or 0)-(b['a'] or 0)))
print({t:(len(v),round(st.mean(v),1)) for t,v in sorted(byturn.items()) if len(v)>=10})
json.dump(recs,open('/tmp/queen_recs.json','w'))
