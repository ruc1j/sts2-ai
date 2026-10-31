"""Shared loader for the offline Act 1-3 full-run analyses (act12_dropout / queen_budget / intervention_rescan).

Panels: astra_ctrl_v23 + astra_ctrl_v24 under the main repo data dir; the one hung v24 seed is excluded."""
import json,sys,glob,os
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import act3_fullrun_report as R
D=Path('/Users/mao/workspace/sts2-ai/data')
HUNG={'963F7C2E44'}
def runs():
    out=[]
    for prefix in ('astra_ctrl_v23','astra_ctrl_v24'):
        for p in sorted(D.glob(f'{prefix}_*_agent.jsonl')):
            seed=p.name[len(prefix)+1:-len('_agent.jsonl')]
            if seed in HUNG: continue
            if not R._is_complete(D,prefix,seed): continue
            out.append((prefix,seed,p))
    return out
