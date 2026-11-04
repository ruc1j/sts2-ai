#!/usr/bin/env python3
"""Pair the C1 engine-pack panel with its same-seed control (astra_ctrl_v24).

Read-only over data/: the C1 panel is written by the live run, so this only
reads files whose runmeta/manifest exists (a run in flight is skipped).

    python3 bosslab/tools/clear5_pair.py --main /Users/mao/workspace/sts2-ai \
        --cand astra_clear5_c1 --control astra_ctrl_v24 --out /tmp/pair.md

Reports, per EVALUATION.md order: Act 1/2/3 clears, reachpoint improvement /
regression / tie, deaths by enemy, adoption of the four engine cards per offer,
Demon Form played turns, demon_form_early_direct activations, Queen shave and
survival, cards that never got played, and Python-side rollout exceptions.
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics

QUEEN = ".QUEEN"
ENGINE = ("CARD.DEMON_FORM", "CARD.RUPTURE", "CARD.CRIMSON_MANTLE", "CARD.INFLAME")


def read_rows(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def load_runs(data_dir, panel):
    runs = {}
    for path in sorted(glob.glob(os.path.join(data_dir, f"{panel}_*_runmeta.json"))):
        seed = os.path.basename(path)[len(panel) + 1: -len("_runmeta.json")]
        manifest_path = os.path.join(data_dir, f"{panel}_{seed}_manifest.json")
        agent_path = os.path.join(data_dir, f"{panel}_{seed}_agent.jsonl")
        if not (os.path.exists(manifest_path) and os.path.exists(agent_path)):
            continue
        with open(manifest_path, encoding="utf-8") as f:
            manifest = json.load(f)
        runs[seed] = {"manifest": manifest, "rows": read_rows(agent_path)}
    return runs


def reach(manifest):
    depth = (manifest.get("outcome") or {}).get("depth") or [0, 0]
    return tuple(depth[:2])


def last_enemy(rows):
    for row in reversed(rows):
        if row.get("phase") == "combat" and row.get("enemies"):
            ids = [str(e.get("id", "")).replace("MONSTER.", "") for e in row["enemies"]]
            return "+".join(ids)
    return None


def queen_fight(rows):
    for i, row in enumerate(rows):
        if row.get("phase") != "combat":
            continue
        if any(str(e.get("id", "")).endswith(QUEEN) for e in row.get("enemies") or ()):
            fight, end = [], None
            for later in rows[i:]:
                if later.get("phase") == "combat_end":
                    end = later
                    break
                if later.get("phase") == "combat":
                    fight.append(later)
            return fight, end
    return None, None


def run_stats(rows):
    stats = collections.Counter()
    offers = collections.Counter()
    taken = collections.Counter()
    stats_runs_offered = collections.Counter()
    played_turns = 0
    played = set()
    deck = set()
    for row in rows:
        if row.get("phase") == "card_reward":
            ids = {c.get("id") for c in row.get("cards") or ()}
            for card in ENGINE:
                if card in ids:
                    offers[card] += 1
                    stats_runs_offered[card] = 1
            if row.get("card_id") in ENGINE:
                taken[row["card_id"]] += 1
        if row.get("phase") == "combat":
            cid = row.get("card_id")
            if cid:
                played.add(cid)
                if cid == "CARD.DEMON_FORM":
                    played_turns += 1
            for card in list(row.get("hand") or ()) + list(row.get("draw_pile") or ()) + list(row.get("discard_pile") or ()):
                if card.get("id"):
                    deck.add(card["id"])
        if row.get("phase") == "shop" and row.get("action") == "buy_card" and row.get("card_id") in ENGINE:
            stats["engine_shop_" + row["card_id"]] += 1
        source = str(row.get("decision_source") or "")
        if "exception" in source:
            stats[source] += 1
        if source == "demon_form_early_direct":
            stats["demon_form_early_direct"] += 1
    fight, end = queen_fight(rows)
    queen = {}
    if fight:
        first = fight[0]
        queen_hp = next((float(e.get("hp") or 0) for e in first.get("enemies") or ()
                         if str(e.get("id", "")).endswith(QUEEN)), None)
        queen_max = next((float(e.get("max_hp") or 0) for e in first.get("enemies") or ()
                          if str(e.get("id", "")).endswith(QUEEN)), None)
        last = fight[-1]
        final_hp = next((float(e.get("hp") or 0) for e in last.get("enemies") or ()
                         if str(e.get("id", "")).endswith(QUEEN)), 0.0)
        if queen_max:
            queen["shave"] = max(0.0, min(1.0, 1.0 - final_hp / queen_max))
        queen["turns"] = max((r.get("turn") or 0) for r in fight)
        queen["won"] = bool(end and end.get("won"))
    return {
        "offers": offers,
        "runs_offered": stats_runs_offered,
        "taken": taken,
        "demon_form_played_turns": played_turns,
        "demon_early": stats["demon_form_early_direct"],
        "engine_shop": {k[len("engine_shop_"):]: v for k, v in stats.items() if k.startswith("engine_shop_")},
        "exceptions": {k: v for k, v in stats.items() if "exception" in k},
        "queen": queen,
        "never_played": sorted(deck - played),
        "deck_size": len(deck),
    }


def aggregate(runs):
    manifest_clear = collections.Counter()
    reach_counts = []
    deaths = collections.Counter()
    offers = collections.Counter()
    runs_offered = collections.Counter()
    taken = collections.Counter()
    demon_turns = []
    demon_early = 0
    engine_shop = collections.Counter()
    shaves, turns = [], []
    never = collections.Counter()
    exceptions = collections.Counter()
    for seed, data in runs.items():
        outcome = data["manifest"].get("outcome") or {}
        manifest_clear["act_1"] += 1 if outcome.get("act_1_complete") else 0
        manifest_clear["act_2"] += 1 if outcome.get("act_2_complete") else 0
        manifest_clear["act_3"] += 1 if outcome.get("act_3_complete") else 0
        reach_counts.append(reach(data["manifest"]))
        stats = run_stats(data["rows"])
        enemy = last_enemy(data["rows"])
        if enemy:
            deaths[enemy] += 1
        offers.update(stats["offers"])
        runs_offered.update(stats["runs_offered"])
        taken.update(stats["taken"])
        demon_turns.append(stats["demon_form_played_turns"])
        demon_early += stats["demon_early"]
        engine_shop.update(stats["engine_shop"])
        if stats["queen"]:
            shaves.append(stats["queen"].get("shave"))
            turns.append(stats["queen"].get("turns"))
        never.update(stats["never_played"])
        exceptions.update(stats["exceptions"])
    return {
        "n": len(runs),
        "clear": manifest_clear,
        "reach": reach_counts,
        "deaths": deaths,
        "offers": offers,
        "runs_offered": runs_offered,
        "taken": taken,
        "demon_turns": demon_turns,
        "demon_early": demon_early,
        "engine_shop": engine_shop,
        "shaves": [s for s in shaves if s is not None],
        "queen_turns": [t for t in turns if t],
        "never": never,
        "exceptions": exceptions,
    }


def render(cand, control, paired):
    lines = [f"# C1 vs 対照（完了 run {cand['n']} / {control['n']}、同一seed {len(paired)} 組）", ""]
    lines.append("## 突破数")
    lines.append("| | Act 1 | Act 2 | Act 3 |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.append(f"| C1 ({cand['n']}) | {cand['clear']['act_1']} | {cand['clear']['act_2']} | {cand['clear']['act_3']} |")
    lines.append(f"| 対照 ({control['n']}) | {control['clear']['act_1']} | {control['clear']['act_2']} | {control['clear']['act_3']} |")

    improved = worsened = tied = 0
    rows_out = []
    for seed, c_reach, v_reach in paired:
        if c_reach > v_reach:
            improved += 1
        elif c_reach < v_reach:
            worsened += 1
        else:
            tied += 1
        rows_out.append(f"| {seed} | {c_reach[0]}-{c_reach[1]} | {v_reach[0]}-{v_reach[1]} |")
    lines += ["", f"到達点（改善/悪化/同値）: {improved}/{worsened}/{tied}"]
    lines += ["", "| seed | C1 | 対照 |", "| --- | --- | --- |"] + rows_out

    lines += ["", "## 敗北した敵（最終の戦闘）"]
    for enemy, count in cand["deaths"].most_common(10):
        lines.append(f"- C1 {enemy}: {count}")
    for enemy, count in control["deaths"].most_common(10):
        lines.append(f"- 対照 {enemy}: {count}")

    lines += ["", "## 4枚の提示と採用"]
    lines.append("| カード | C1 提示（run/回） | C1 採用 | 対照 提示（run/回） | 対照 採用 |")
    lines.append("| --- | ---: | ---: | ---: | ---: |")
    for card in ENGINE:
        lines.append(f"| {card.replace('CARD.', '')} | {cand['runs_offered'][card]}/{cand['offers'][card]} | "
                     f"{cand['taken'][card]} | {control['runs_offered'][card]}/{control['offers'][card]} | "
                     f"{control['taken'][card]} |")

    lines += ["", "## 部品別の発動数"]
    lines.append("| 部品 | C1 | 対照 |")
    lines.append("| --- | ---: | ---: |")
    lines.append(f"| 報酬でengine採用（行数） | {sum(cand['taken'].values())} | {sum(control['taken'].values())} |")
    lines.append(f"| ショップでengine購入 | {sum(cand['engine_shop'].values())} | {sum(control['engine_shop'].values())} |")
    lines.append(f"| demon_form_early_direct 発動 | {cand['demon_early']} | {control['demon_early']} |")
    lines.append(f"| DEMON_FORM 使用ターン合計 | {sum(cand['demon_turns'])} | {sum(control['demon_turns'])} |")
    lines.append("")
    lines.append("進捗の評価（部品1）は trace から発動数を数えられない（探索の内部で決まる）。"
                 "同じ観測での再生が要る。")

    lines += ["", "## Demon Form と早期出し"]
    lines.append(f"- DEMON_FORM を打ったターン数（run平均）: C1 {statistics.mean(cand['demon_turns']) if cand['demon_turns'] else 0:.2f}、"
                 f"対照 {statistics.mean(control['demon_turns']) if control['demon_turns'] else 0:.2f}")
    lines.append(f"- demon_form_early_direct 発動: C1 {cand['demon_early']}、対照 {control['demon_early']}")

    lines += ["", "## Queen戦（Queen単独）"]
    if cand["shaves"]:
        lines.append(f"- C1: n={len(cand['shaves'])} 削り中央 {statistics.median(cand['shaves']):.3f}、"
                     f"生存中央 {statistics.median(cand['queen_turns']):.0f}ターン")
    if control["shaves"]:
        lines.append(f"- 対照: n={len(control['shaves'])} 削り中央 {statistics.median(control['shaves']):.3f}、"
                     f"生存中央 {statistics.median(control['queen_turns']):.0f}ターン")

    lines += ["", "## 未使用のまま終わった札（C1上位）"]
    for card, count in cand["never"].most_common(8):
        lines.append(f"- {card.replace('CARD.', '')}: {count} run")

    lines += ["", "## Python側の例外"]
    if cand["exceptions"]:
        for key, count in cand["exceptions"].most_common():
            lines.append(f"- C1 {key}: {count}")
    else:
        lines.append("- C1: なし")
    if control["exceptions"]:
        for key, count in control["exceptions"].most_common():
            lines.append(f"- 対照 {key}: {count}")
    else:
        lines.append("- 対照: なし")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--main", default="/Users/mao/workspace/sts2-ai")
    ap.add_argument("--data", default=None)
    ap.add_argument("--cand", default="astra_clear5_c1")
    ap.add_argument("--control", default="astra_ctrl_v24")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    data_dir = args.data or os.path.join(args.main, "data")
    cand = load_runs(data_dir, args.cand)
    # Compare only same-seed controls: the panel's 136 runs would otherwise set the
    # baseline from seeds the candidate never ran, which is not a paired comparison.
    control = {s: v for s, v in load_runs(data_dir, args.control).items() if s in cand}
    paired = []
    for seed in sorted(cand):
        if seed in control:
            paired.append((seed, reach(cand[seed]["manifest"]), reach(control[seed]["manifest"])))
    text = render(aggregate(cand), aggregate(control), paired)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {args.out} (C1 {len(cand)} runs, control {len(control)}, paired {len(paired)})")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
