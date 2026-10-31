#!/usr/bin/env python3
"""Pool report for Act 2 boss specs (v23+v24). Usage: act2_pool_report.py TRACE_DIR SPECS_JSONL OUT_MD"""
import collections, glob, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import relic_entry_effects as R

tr, specs_path, out = sys.argv[1:4]
specs = [json.loads(l) for l in open(specs_path)]
block_ids, type_of = set(), {}
for f in glob.glob(tr + "/*_agent.jsonl"):
    for line in open(f, encoding="utf-8-sig", errors="replace"):
        if '"hand"' not in line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        for c in r.get("hand") or ():
            if isinstance(c, dict) and c.get("id"):
                type_of[c["id"]] = c.get("type")
                if any(isinstance(v, dict) and v.get("id") == "Block" for v in c.get("vars") or ()):
                    block_ids.add(c["id"])
HAZ = sorted(set(R.ENTRY_EFFECTS) | {"RELIC.FORGOTTEN_SOUL", "RELIC.BLESSED_ANTLER", "RELIC.BELLOWS", "RELIC.CROSSBOW"})
CLEAN_OK = {"RELIC.STONE_CRACKER", "RELIC.FORGOTTEN_SOUL"}
rows = []
for s in specs:
    deck = [c for p in s["piles"].values() for c in p]
    shrug = [c for c in deck if c["id"] == "CARD.SHRUG_IT_OFF"]
    up = sum(1 for c in shrug if c["upgrade"])
    haz = sorted(set(s["player"]["relics"]) & set(HAZ))
    src = s["sources"][0]["tag"]
    ver = "v24" if "v24" in src else "v23"
    rows.append(dict(id=s["spec_id"], seed=s["run_seed"], ver=ver, enc=s["encounter_hint"].replace("MONSTER.", ""),
        hp=f'{s["player"]["hp"]}/{s["player"]["max_hp"]}', deck=s["deck_size"], sh=len(shrug), up=up, un=len(shrug) - up,
        blk=sum(1 for c in deck if c["id"] in block_ids), nrel=len(s["player"]["relics"]),
        rc="有" if s["relic_counters_observed"] else "無", haz=haz, unres=s["unresolved"],
        won=s["recorded_outcome"]["won"], relics=s["player"]["relics"]))
    rows[-1]["clean"] = not s["unresolved"] and set(haz) <= CLEAN_OK
rows.sort(key=lambda r: (r["enc"], r["ver"], r["seed"]))
L = ["# Act 2 BOSS spec プール（v23 + v24 新形式パネル）", "",
 "抽出: `bosslab/tools/extract_act2_boss_pool.py`（`.dsh/extract_act3_specs.py` の Act 2 版。ボス敵 id は絞らず全て拾う）を v23/v24 の agent trace + mod log"
 "（seed 963F7C2E44 と attempt1 を除く、tmp へ symlink）に実行。出力 `bosslab/specs_act2_boss_v23v24.jsonl`。Block 持ちは全 trace の hand 観測で Block var を持つ card id から導出。"
 "表のレリックは別列に長く出るため末尾の付録に分ける。", "",
 "hazard 定義: " + ", ".join(HAZ), "",
 "clean = unresolved 無し かつ hazard が {STONE_CRACKER, FORGOTTEN_SOUL} のみ（無し含む）。", "",
 "## 件数", ""]
encs = collections.Counter(r["enc"] for r in rows)
L += ["| encounter | spec総数 | clean | clean かつ Shrug>=1 | clean かつ 未強化Shrug>=1 |", "|---|---|---|---|---|"]
for e in sorted(encs):
    g = [r for r in rows if r["enc"] == e]; c = [r for r in g if r["clean"]]
    L.append(f'| {e} | {len(g)} | {len(c)} | {sum(1 for r in c if r["sh"]>=1)} | {sum(1 for r in c if r["un"]>=1)} |')
L += ["", "## spec 一覧", "",
 "| spec_id | seed | 版 | encounter | HP/max | デッキ | Shrug(強/未) | Block持ち | relic数 | relic_counters | hazard | unresolved | 実走勝 | clean |",
 "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    L.append(f'| {r["id"]} | {r["seed"]} | {r["ver"]} | {r["enc"]} | {r["hp"]} | {r["deck"]} | {r["sh"]}({r["up"]}/{r["un"]}) | {r["blk"]} | {r["nrel"]} | {r["rc"]} | '
             f'{",".join(h[6:] for h in r["haz"]) or "-"} | {",".join(r["unres"]) or "-"} | {r["won"]} | {"○" if r["clean"] else "-"} |')
L += ["", "## 付録: レリック一覧", ""]
for r in rows:
    L.append(f'- {r["id"]} ({r["seed"]}): {", ".join(x[6:] for x in r["relics"])}')
Path(out).write_text("\n".join(L) + "\n", encoding="utf-8")
print(collections.Counter(r["ver"] for r in rows), len(rows), sum(r["clean"] for r in rows))
for e in sorted(encs):
    g=[r for r in rows if r["enc"]==e]; c=[r for r in g if r["clean"]]
    print(e,len(g),len(c),sum(r["sh"]>=1 for r in c),sum(r["un"]>=1 for r in c), "won",sum(1 for r in g if r["won"]))
