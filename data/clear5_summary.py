#!/usr/bin/env python3
"""One-line outcome for a finished run, plus panel totals. Exit 2 applies the 68-run stop rule."""
import collections
import glob
import json
import os
import sys

tag, seed, seeds_file = sys.argv[1:4]
m = json.load(open(f"data/{tag}_{seed}_manifest.json"))
o = m["outcome"]
last_enemies, deck_power = [], collections.Counter()
for line in open(f"data/{tag}_{seed}_agent.jsonl", encoding="utf-8", errors="replace"):
    try:
        r = json.loads(line)
    except ValueError:
        continue
    if r.get("phase") == "combat" and r.get("enemies_summary"):
        last_enemies = r["enemies_summary"]
    if r.get("decision_source"):
        deck_power[r["decision_source"]] += r["decision_source"] == "demon_form_early_direct"
err = f"data/{tag}_{seed}_agent.err"
err_size = os.path.getsize(err) if os.path.exists(err) else 0
seeds = [s.strip() for s in open(seeds_file) if s.strip()]
done = [json.load(open(p))["outcome"] for p in glob.glob(f"data/{tag}_*_manifest.json")]
n = len(done)
a1 = sum(bool(x["act_1_complete"]) for x in done)
a2 = sum(bool(x["act_2_complete"]) for x in done)
a3 = sum(bool(x["act_3_complete"]) for x in done)
print(
    f"RUN {n}/{len(seeds)} {seed} {o['status']} act3={o['act_3_complete']} depth={o['depth']} "
    f"wins={o['combat_wins']} err={err_size} demonfirst={deck_power['demon_form_early_direct']} "
    f"TOTAL a1={a1} a2={a2} a3={a3}/{n}"
)
if o["act_3_complete"]:
    print(f"CLEAR {seed} a3={a3}/{n}")
if n == 68 and a3 == 0:
    print("GATE 68 runs with zero clears")
    sys.exit(2)
