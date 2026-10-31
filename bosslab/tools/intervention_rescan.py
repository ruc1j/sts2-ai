"""Re-tally of the three intervention areas (reward Block adoption, rest choice, potions) over v23+v24 Act 3 entrants."""
from fullrun_load import *
import statistics as st, collections, json
rs=runs()
TM=R.build_type_map([p for _,_,p in rs])
# Block cards: id with vars Block/ExtraBlock seen in hand anywhere
BL=set()
for _,_,p in rs:
    for r in R.read_rows(p):
        for c in r.get('hand') or []:
            if any(v.get('id') in ('Block','ExtraBlock') for v in (c.get('vars') or [])) and c.get('type')=='Skill': BL.add(c['id'])
per={}
for tag,seed,p in rs:
    rows=R.read_rows(p)
    if not R.entered_act3(rows): continue
    qrows,won=R.queen_fight(rows)
    offered=taken=0; other=skip=0
    rest=collections.Counter(); 
    pot_used=0; pot_left_end=0
    for r in rows:
        ph=r['phase']
        if ph=='card_reward' and r.get('type')=='card_reward':
            blk=[c for c in r['cards'] if c['id'] in BL]
            offered+=len(blk)
            chosen=r.get('card_id')
            if chosen in BL and any(c['id']==chosen for c in blk): taken+=1
            # blocks not chosen
            n_not=len(blk)-(1 if chosen in BL else 0)
            if chosen: other+=n_not
            else: skip+=n_not
        elif ph=='card_reward' and r.get('type')=='card_reward_alternative':
            blk=[c for c in r['cards'] if c['id'] in BL]; offered+=len(blk); skip+=len(blk)
        elif ph=='rest': rest[r.get('option_id')]+=1
    # Queen entry
    rec=dict(seed=seed,tag=tag,queen=bool(qrows),won=won,blk_off=offered,blk_taken=taken,blk_other=other,blk_skip=skip,rest=dict(rest))
    if qrows:
        e=qrows[0]; deck=[c for k in ('hand','draw_pile','discard_pile','exhaust_pile') for c in (e.get(k) or [])]
        rec['skills']=sum(1 for c in deck if TM.get(c['id'])=='Skill'); rec['deck']=len(deck)
        rec['blk_in_deck']=sum(1 for c in deck if c['id'] in BL)
        rec['upg']=sum(1 for c in deck if (c.get('upgrade') or 0)>0)
        rec['potions']=len(e.get('potions') or [])
        last=qrows[-1]; rec['potions_left']=len(last.get('potions') or [])
        rec['entry_hp']=e['player']['hp']; rec['max_hp']=e['player']['max_hp']
        rec['shave']=R.A.hp_removed_from_trace(qrows,R.QUEEN_SUFFIX)
    per[seed]=rec
json.dump(per,open('/tmp/rescan.json','w'))
def tally(sub,label):
    off=sum(r['blk_off'] for r in sub); tk=sum(r['blk_taken'] for r in sub)
    print(f"{label:34s} runs={len(sub):3d} Block offered={off:4d} taken={tk:4d} ({100*tk/max(1,off):.1f}%) other={sum(r['blk_other'] for r in sub)} skip={sum(r['blk_skip'] for r in sub)}")
A3=list(per.values()); Q=[r for r in A3 if r['queen']]
for tg in ('astra_ctrl_v23','astra_ctrl_v24'):
    tally([r for r in A3 if r['tag']==tg],'Act3 entrants '+tg[-3:])
tally(A3,'Act3 entrants ALL'); tally(Q,'Queen fights ALL')
med=st.median(r['skills'] for r in Q); print('median Skills at Queen entry',med)
tally([r for r in Q if r['skills']<med],'Queen, Skills < median'); tally([r for r in Q if r['skills']>=med],'Queen, Skills >= median')
# rest decisions
rc=collections.Counter(); 
for r in A3:
    for k,v in r['rest'].items(): rc[k]+=v
print('rest options (Act3 entrants whole run):',dict(rc))
# potions at Queen entry / left at end
print('Queen entry potions mean',round(st.mean(r['potions'] for r in Q),2),'left at end mean',round(st.mean(r['potions_left'] for r in Q),2),
      'fights with potion left>0:',sum(1 for r in Q if r['potions_left']>0),'/',len(Q))
print('entry HP/max med',st.median(r['entry_hp']/r['max_hp'] for r in Q),'upgraded in deck med',st.median(r['upg'] for r in Q),'deck med',st.median(r['deck'] for r in Q))
# shave vs Block count / upgraded count / skills (descriptive)
def split(key,label):
    m=st.median(r[key] for r in Q); lo=[r['shave']/400 for r in Q if r[key]<m]; hi=[r['shave']/400 for r in Q if r[key]>=m]
    print(f"{label}: median {m}  lo n={len(lo)} shave med {st.median(lo):.3f} | hi n={len(hi)} shave med {st.median(hi):.3f}")
split('blk_in_deck','Block cards in deck'); split('upg','upgraded cards'); split('skills','skills'); split('entry_hp','entry HP')
