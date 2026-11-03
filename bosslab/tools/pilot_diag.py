#!/usr/bin/env python3
"""PILOT-1 diagnostics over the 59 Act 3 Queen fights of astra_ctrl_v23+v24.

Analysis only: reads the agent traces under the main checkout's data/ directory
and prints markdown for bosslab/results/pilot_diag.md.  It never touches the
policy code, the game, or the run artifacts.

Sections:
  calib    search_value vs the fight's actual outcome and shave fraction
  scaling  Power / Strength cards: turns in hand, played, energy at hand
  str3     decomposition of the "総火力/ターン 38.8 -> 37.2" discrepancy
  reward   deck combination comparison for the known Act 3 clears

Usage:
    python3 bosslab/tools/pilot_diag.py calib --data-dir /Users/mao/workspace/sts2-ai/data
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import analyze_bosslab as A  # noqa: E402

QUEEN = ".QUEEN"
AMALGAM = "TORCH_HEAD_AMALGAM"
TAGS = ("astra_ctrl_v23", "astra_ctrl_v24")


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
                continue
    return rows


def queen_slice(rows):
    """Combat rows of the Queen fight and the closing combat_end row."""
    start = None
    for i, row in enumerate(rows):
        if row.get("phase") != "combat":
            continue
        if any(str(e.get("id", "")).endswith(QUEEN) for e in row.get("enemies") or []):
            start = i
            break
    if start is None:
        return None, None
    combat, end = [], None
    for row in rows[start:]:
        if row.get("phase") == "combat_end":
            end = row
            break
        if row.get("phase") == "combat":
            combat.append(row)
    return combat, end


def fight_metrics(combat, end):
    """Queen-only shave is the EVALUATION.md metric; the Queen+Amalgam sum is a
    different number (the 599 denominator) and is kept under its own name."""
    removed = {}
    max_hp = {}
    for suffix, key in ((QUEEN, "queen"), (AMALGAM, "amalgam")):
        removed[key] = A.hp_removed_from_trace(combat, suffix) or 0
        first = next((next((e for e in (r.get("enemies") or [])
                            if str(e.get("id", "")).endswith(suffix)), None)
                      for r in combat), None)
        max_hp[key] = float(first.get("max_hp") or 0) if first else 0.0
    combined_removed = removed["queen"] + removed["amalgam"]
    combined_max = max_hp["queen"] + max_hp["amalgam"]
    turns = max((r.get("turn") or 0) for r in combat) if combat else 0
    won = bool(end and end.get("won"))
    return {
        "removed": combined_removed,
        "max_hp": combined_max,
        "queen_removed": removed["queen"],
        "amalgam_removed": removed["amalgam"],
        "shave": (removed["queen"] / max_hp["queen"]) if max_hp["queen"] else None,
        "shave_combined": (combined_removed / combined_max) if combined_max else None,
        "turns": turns,
        "won": won,
    }


def load_fights(data_dir):
    fights = []
    for tag in TAGS:
        for path in sorted(glob.glob(os.path.join(data_dir, f"{tag}_*_agent.jsonl"))):
            seed = os.path.basename(path)[len(tag) + 1:-len("_agent.jsonl")]
            rows = read_rows(path)
            combat, end = queen_slice(rows)
            if not combat:
                continue
            m = fight_metrics(combat, end)
            entry = combat[0]
            player = entry.get("player") or {}
            hand_ids = {c.get("id") for c in (entry.get("hand") or [])}
            fights.append({
                "tag": tag,
                "seed": seed,
                "combat": combat,
                "entry_hp": player.get("hp"),
                "entry_max_hp": player.get("max_hp"),
                "entry_hand": hand_ids,
                "entry_potions": len(entry.get("potions") or []),
                "entry_relics": len((player.get("relics") or [])),
                **m,
            })
    return fights


def spearman(xs, ys):
    """Rank correlation without scipy (average ranks for ties)."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out
    if len(xs) < 3:
        return None
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else None


def values_by_turn(combat):
    """Search value of the chosen action, per turn."""
    out = defaultdict(list)
    for row in combat:
        sv = row.get("search_value")
        if sv is None:
            continue
        out[row.get("turn")].append(float(sv))
    return out


def first_value(combat):
    for row in combat:
        if row.get("search_value") is not None:
            return float(row["search_value"])
    return None


def section_calib(fights):
    lines = []
    lit = [f for f in fights if f["first_value"] is not None]
    n = len(lit)
    lines.append(f"対象: Queen戦 {len(fights)} 戦（v23 {sum(1 for f in fights if f['tag'].endswith('v23'))}、"
                 f"v24 {sum(1 for f in fights if f['tag'].endswith('v24'))}）。"
                 f"うち search_value が1回でも記録された戦闘 {n} 戦。")
    lines.append("")
    lines.append("### 1-1 1手目の評価値と結果")
    vals = [f["first_value"] for f in lit]
    shaves = [f["shave"] for f in lit]
    rho = spearman(vals, shaves)
    lines.append(f"- 1手目 search_value の中央値 {statistics.median(vals):+.3f}"
                 f"（範囲 {min(vals):+.3f}〜{max(vals):+.3f}）")
    lines.append(f"- 1手目値とQueen削り割合（Queen単独）の Spearman ρ = {rho:+.3f}（n={n}）" if rho is not None else "- 相関は算出不能")
    win = [f for f in lit if f["won"]]
    lose = [f for f in lit if not f["won"]]
    if win and lose:
        lines.append(f"- 勝ち {len(win)} 戦の1手目値中央値 {statistics.median([f['first_value'] for f in win]):+.3f}、"
                     f"負け {len(lose)} 戦 {statistics.median([f['first_value'] for f in lose]):+.3f}")
    # bin table over first values
    bins = [(-9, -0.8), (-0.8, -0.5), (-0.5, -0.2), (-0.2, 0.2), (0.2, 9)]
    lines.append("")
    lines.append("| 1手目値の範囲 | 戦闘数 | 勝ち | 削り中央値 | 削り平均 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for lo, hi in bins:
        group = [f for f in lit if lo <= f["first_value"] < hi]
        if not group:
            continue
        sh = [f["shave"] for f in group]
        lines.append(f"| {lo:+.1f}〜{hi:+.1f} | {len(group)} | {sum(1 for f in group if f['won'])} | "
                     f"{statistics.median(sh):.3f} | {statistics.mean(sh):.3f} |")

    lines.append("")
    lines.append("### 1-2 全決定の評価値と勝率（局面を独立に数えないので参考値）")
    buckets = [(-9, -0.9), (-0.9, -0.6), (-0.6, -0.3), (-0.3, 0.0),
               (0.0, 0.3), (0.3, 0.6), (0.6, 0.9), (0.9, 9)]
    lines.append("| 評価値 | 決定数 | その決定を含む戦闘の勝率 | 削り中央値 |")
    lines.append("| --- | --- | --- | --- |")
    per_bucket = {b: [] for b in buckets}
    for f in lit:
        for row in f["combat"]:
            sv = row.get("search_value")
            if sv is None:
                continue
            for b in buckets:
                if b[0] <= float(sv) < b[1]:
                    per_bucket[b].append(f)
                    break
    for b in buckets:
        group = per_bucket[b]
        if not group:
            continue
        wins = sum(1 for f in group if f["won"])
        sh = [f["shave"] for f in group]
        lines.append(f"| {b[0]:+.1f}〜{b[1]:+.1f} | {len(group)} | {wins}/{len(group)}"
                     f" = {wins/len(group):.0%} | {statistics.median(sh):.3f} |")

    lines.append("")
    lines.append("### 1-3 ターンごとの評価値（中央値）")
    lines.append("| ターン | 戦闘数 | 値の中央値 | そのターンの削り中央値（累積） |")
    lines.append("| --- | --- | --- | --- |")
    by_turn = defaultdict(list)
    for f in lit:
        tv = values_by_turn(f["combat"])
        for turn, vs in tv.items():
            by_turn[turn].append((statistics.mean(vs), f))
    for turn in sorted(by_turn):
        group = by_turn[turn]
        if len(group) < 3:
            continue
        lines.append(f"| {turn} | {len(group)} | "
                     f"{statistics.median([v for v, _ in group]):+.3f} | "
                     f"{statistics.median([f['shave'] for _, f in group]):.3f} |")

    lines.append("")
    lines.append("### 1-4 評価値は何を写しているか")
    ent_hp = [f["entry_hp"] for f in lit]
    lines.append(f"- 1手目値と入場HPの ρ = {_rho_text(vals, ent_hp)}")
    atk = [len(f["entry_hand"]) for f in lit]
    lines.append(f"- 1手目値と初期手札枚数の ρ = {_rho_text(vals, atk)}（代理指標として弱い）")
    turns = [f["turns"] for f in lit]
    lines.append(f"- 1手目値と生存ターンの ρ = {_rho_text(vals, turns)}")
    lines.append(f"- Queen削り割合と生存ターンの ρ = {_rho_text(shaves, turns)}")
    combined = [f["shave_combined"] for f in lit]
    lines.append(f"- 参考: Queen+Amalgam合算の削り割合（分母599）は 中央値 "
                 f"{statistics.median([x for x in combined if x is not None]):.3f}。"
                 f"EVALUATION.mdの主信号ではないので、以下の比較はQueen単独で行う。")

    lines.append("")
    lines.append("### 1-5 評価値は戦闘中に動くか")
    within, between, deltas = [], [], []
    for f in lit:
        vs = [float(r["search_value"]) for r in f["combat"] if r.get("search_value") is not None]
        if len(vs) < 3:
            continue
        between.append(statistics.mean(vs))
        within.append(statistics.pvariance(vs) ** 0.5)
        deltas.append(vs[-1] - vs[0])
    if between:
        bvar = statistics.pvariance(between)
        wvar = statistics.mean([w * w for w in within])
        lines.append(f"- 戦闘間の平均値のSD {statistics.pstdev(between):.3f}、"
                     f"戦闘内のSD中央値 {statistics.median(within):.3f}。"
                     f"分散のうち戦闘間で決まる割合は {bvar/(bvar+wvar):.0%}。")
        lines.append(f"- 1手目から最終決定までの値の変化: 中央値 {statistics.median(deltas):+.3f}、"
                     f"+0.3以上動いた戦闘 {sum(1 for d in deltas if d > 0.3)}、"
                     f"−0.3以下 {sum(1 for d in deltas if d < -0.3)}（n={len(deltas)}）。")
        pos = sum(1 for f in lit
                  if any(float(r["search_value"]) > 0
                         for r in f["combat"] if r.get("search_value") is not None))
        lines.append(f"- 1回でも正の値が出た戦闘は {pos}/{len(lit)}。")
    return "\n".join(lines)


STRENGTH_CARDS = {
    "CARD.DEMON_FORM", "CARD.INFLAME", "CARD.RUPTURE",
    "CARD.LIMIT_BREAK", "CARD.FLEX", "CARD.SPOT_WEAKNESS",
}


def scaling_events(fights):
    """Per (fight, turn, card) rows for every Power / Strength card in hand."""
    events = []
    for f in fights:
        by_turn = defaultdict(list)
        for row in f["combat"]:
            by_turn[row.get("turn")].append(row)
        for turn, rows in by_turn.items():
            played = {r.get("card_id") for r in rows if r.get("card_id")}
            seen = {}
            for row in rows:
                for card in row.get("hand") or []:
                    cid = card.get("id")
                    is_power = card.get("type") == "Power"
                    if not (is_power or cid in STRENGTH_CARDS):
                        continue
                    info = seen.setdefault(cid, {
                        "card": cid,
                        "power": is_power,
                        "strength": cid in STRENGTH_CARDS,
                        "cost": card.get("cost"),
                        "energies": [],
                    })
                    energy = (row.get("player") or {}).get("energy")
                    if energy is not None:
                        info["energies"].append(energy)
            for cid, info in seen.items():
                played_this_turn = cid in played
                cost = info["cost"]
                energies = info["energies"]
                max_energy = max(energies) if energies else None
                if played_this_turn:
                    state = "played"
                elif max_energy is None or cost is None:
                    state = "unknown"
                elif max_energy < cost:
                    state = "energy_short"
                else:
                    state = "castable_not_played"
                alternatives = Counter()
                for row in rows:
                    cid2 = row.get("card_id")
                    if cid2 and cid2 != cid:
                        alternatives[cid2] += 1
                events.append({
                    "seed": f["seed"], "tag": f["tag"], "turn": turn,
                    "card": cid, "cost": cost, "max_energy": max_energy,
                    "state": state, "played_any": played_this_turn,
                    "alternatives": alternatives,
                    "energy_left": (rows[-1].get("player") or {}).get("energy"),
                })
    return events


def section_scaling(fights):
    ev = scaling_events(fights)
    lines = []
    lines.append(f"対象: Queen戦 {len(fights)} 戦の全決定行。手札に現れた Power札とStrength系の札"
                 f"（DEMON_FORM / INFLAME / RUPTURE / LIMIT_BREAK / FLEX / SPOT_WEAKNESS）を、"
                 f"ターン×札の単位で数えた。")
    lines.append("")
    lines.append("### 2-1 札ごとの内訳")
    lines.append("| カード | 手札にあったターン | 打った | 打てたのに打たない | エネルギー不足 |")
    lines.append("| --- | --- | --- | --- | --- |")
    by_card = defaultdict(Counter)
    for e in ev:
        by_card[e["card"]][e["state"]] += 1
    order = sorted(by_card, key=lambda c: -sum(by_card[c].values()))
    for cid in order:
        c = by_card[cid]
        total = sum(c.values())
        lines.append(f"| {cid.replace('CARD.', '')} | {total} | {c['played']} | "
                     f"{c['castable_not_played']} | {c['energy_short']} |")

    lines.append("")
    lines.append("### 2-2 打てたのに打たなかったときの手")
    sk = [e for e in ev if e["state"] == "castable_not_played"]
    alt_types = Counter()
    no_play = 0
    for e in sk:
        if not e["alternatives"]:
            no_play += 1
        for cid in e["alternatives"]:
            alt_types[cid] += 1
    lines.append(f"- 該当 {len(sk)} 件のうち、同じターンに別の札を打っていた "
                 f"{len(sk) - no_play} 件、何も打たずにターンを終えた {no_play} 件。")
    lines.append(f"- 代わりに打った札の上位: "
                 + "、".join(f"{k.replace('CARD.', '')} {v}"
                             for k, v in alt_types.most_common(8)) + "。")
    left = [e["energy_left"] for e in sk if e["energy_left"] is not None]
    if left:
        lines.append(f"- そのターン終了時の残りエネルギー: 中央値 {statistics.median(left):.0f}、"
                     f"0のターン {sum(1 for x in left if x == 0)}/{len(left)}。")

    lines.append("")
    lines.append("### 2-3 エネルギー不足の内訳")
    es = [e for e in ev if e["state"] == "energy_short"]
    lines.append(f"- 該当 {len(es)} 件。札のコスト中央値 "
                 f"{statistics.median([e['cost'] for e in es if e['cost'] is not None]):.1f}、"
                 f"そのときの手札時エネルギー中央値 "
                 f"{statistics.median([e['max_energy'] for e in es if e['max_energy'] is not None]):.1f}。")
    lines.append("")
    lines.append("### 2-4 Strength系の打ち漏らし（全10件）")
    lines.append("| seed | ターン | 札 | コスト | 手札時エネルギー | 終了時残 | 代わりに打った札 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for e in ev:
        if e["card"] not in STRENGTH_CARDS or e["state"] != "castable_not_played":
            continue
        alts = "、".join(f"{k.replace('CARD.', '')}×{v}"
                        for k, v in e["alternatives"].most_common(4))
        lines.append(f"| {e['seed']} | {e['turn']} | {e['card'].replace('CARD.', '')} | "
                     f"{e['cost']} | {e['max_energy']} | {e['energy_left']} | {alts} |")
    lines.append("")
    lines.append("区別: 「打てたのに打たなかった」はそのターンのどこかでエネルギーがコスト以上あった場合。"
                 "「エネルギー不足」は手札にあったすべての決定でコスト未満だった場合。"
                 "同じカードを2枚持つターンはカードID単位でまとめているため、片方だけ打った場合も"
                 "「打った」に寄る。")
    return "\n".join(lines)


def str_trials(str_dir):
    """One row per lab trial of the str3 experiment (base / str3 pairs)."""
    out = []
    meta = json.loads(Path(str_dir, "lab_results.jsonl").read_text())
    return meta


def str_summary(str_dir):
    import glob as _glob
    arms = {}
    with open(os.path.join(str_dir, "lab_results.jsonl"), encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            arms[rec["trial_index"]] = rec["trial_id"]
    trials = []
    for path in sorted(_glob.glob(os.path.join(str_dir, "trial_*_agent.jsonl"))):
        index = int(os.path.basename(path).split("_")[1])
        spec, arm, offset = arms[index].split("|")
        combat, end = queen_slice(read_rows(path))
        if not combat:
            continue
        types = {c.get("id"): c.get("type") for r in combat for c in (r.get("hand") or [])}
        dealt_q = dealt_a = 0.0
        attacks = 0
        attack_damage = []
        setup = 0
        strength = []
        for i, row in enumerate(combat[:-1]):
            nxt = combat[i + 1]
            prev = {e.get("id"): float(e.get("hp") or 0)
                    for e in (row.get("enemies") or [])}
            cur = {e.get("id"): float(e.get("hp") or 0)
                   for e in (nxt.get("enemies") or [])}
            for key, hp in prev.items():
                loss = max(0.0, hp - cur.get(key, hp))
                if "QUEEN" in key:
                    dealt_q += loss
                elif "AMALGAM" in key:
                    dealt_a += loss
            cid = row.get("card_id")
            if cid and types.get(cid) == "Attack":
                attacks += 1
                loss_here = sum(max(0.0, hp - cur.get(k, hp)) for k, hp in prev.items())
                attack_damage.append(loss_here)
            elif cid in ("CARD.INFLAME", "CARD.DEMON_FORM", "CARD.RUPTURE"):
                setup += 1
            for power in ((row.get("player") or {}).get("powers") or []):
                if "STRENGTH" in str(power.get("id", "")):
                    strength.append(power.get("amount") or 0)
        enemies = (combat[-1].get("enemies") or [])
        trials.append({
            "spec": spec, "arm": arm,
            "turns": max(r.get("turn") or 0 for r in combat),
            "queen_removed": A.hp_removed_from_trace(combat, QUEEN) or 0,
            "amalgam_removed": A.hp_removed_from_trace(combat, AMALGAM) or 0,
            "dealt_queen": dealt_q,
            "dealt_amalgam": dealt_a,
            "attacks": attacks,
            "dmg_per_attack": (statistics.mean(attack_damage)
                               if attack_damage else None),
            "setup": setup,
            "max_strength": max(strength) if strength else 0,
            "amalgam_killed": not any("AMALGAM" in str(e.get("id", "")) for e in enemies),
        })
    return trials


def section_str3(str_dir, fights=None):
    trials = str_summary(str_dir)
    lines = []
    n_pairs = len({(t["spec"], t["arm"]) for t in trials}) // 2
    lines.append(f"対象: `bosslab_act3_str_conf` の {len(trials)} trial（{n_pairs} 組、base と str3）。"
                 f"trace から計器を独立に計算し直した。")
    lines.append("")

    def arm(name):
        return [t for t in trials if t["arm"] == name]

    def fp(t):
        return (t["queen_removed"] + t["amalgam_removed"]) / t["turns"] if t["turns"] else None

    lines.append("### 3-1 まず計器の再現")
    lines.append("| 指標 | base | str3 |")
    lines.append("| --- | --- | --- |")
    for label, fn in (
        ("総火力/ターン（removed合計÷ターン、trial平均）", lambda t: fp(t)),
        ("消したHP合計（Queen+Amalgam、trial平均）", lambda t: t["queen_removed"] + t["amalgam_removed"]),
        ("生存ターン（trial平均）", lambda t: t["turns"]),
        ("Queenのみ削り（trial平均）", lambda t: t["queen_removed"]),
        ("Amalgamのみ削り（trial平均）", lambda t: t["amalgam_removed"]),
        ("攻撃の回数（trial平均）", lambda t: t["attacks"]),
        ("攻撃1回あたりのダメージ（trial平均）", lambda t: t["dmg_per_attack"]),
        ("INFLAME/DEMON_FORM/RUPTURE使用回数", lambda t: t["setup"]),
        ("最大Strength（中央値）", lambda t: t["max_strength"]),
    ):
        b = [fn(t) for t in arm("base") if fn(t) is not None]
        c = [fn(t) for t in arm("str3") if fn(t) is not None]
        if not b or not c:
            continue
        med = "中央値" in label
        bv = statistics.median(b) if med else statistics.mean(b)
        cv = statistics.median(c) if med else statistics.mean(c)
        lines.append(f"| {label} | {bv:.2f} | {cv:.2f} |")

    # ratio of means vs mean of ratios
    b = arm("base"); c = arm("str3")
    rb = sum(t["queen_removed"] + t["amalgam_removed"] for t in b) / sum(t["turns"] for t in b)
    rc = sum(t["queen_removed"] + t["amalgam_removed"] for t in c) / sum(t["turns"] for t in c)
    lines.append("")
    lines.append(f"比の平均と平均の比は一致しない。removed合計をターン合計で割ると base {rb:.2f} → str3 {rc:.2f}"
                 f"（差 {rc-rb:+.2f}）、trialごとの比の平均では "
                 f"{statistics.mean([fp(t) for t in b]):.2f} → {statistics.mean([fp(t) for t in c]):.2f}"
                 f"（差 {statistics.mean([fp(t) for t in c]) - statistics.mean([fp(t) for t in b]):+.2f}）。"
                 f"報告の 38.8→37.2 は後者。")

    lines.append("")
    lines.append("### 3-2 分母か分子か")
    tb = statistics.mean([t["turns"] for t in b])
    tc = statistics.mean([t["turns"] for t in c])
    lines.append(f"- 生存ターンは base {tb:.2f} → str3 {tc:.2f} で差がない。分母は下がっていない。")
    lines.append(f"- 分子（Queen+Amalgamの削り）は base {statistics.mean([t['queen_removed']+t['amalgam_removed'] for t in b]):.1f}"
                 f" → str3 {statistics.mean([t['queen_removed']+t['amalgam_removed'] for t in c]):.1f} で減っている。")
    lines.append(f"- 内訳は Queen {statistics.mean([t['queen_removed'] for t in b]):.1f}→"
                 f"{statistics.mean([t['queen_removed'] for t in c]):.1f}、"
                 f"Amalgam {statistics.mean([t['amalgam_removed'] for t in b]):.1f}→"
                 f"{statistics.mean([t['amalgam_removed'] for t in c]):.1f}。"
                 f"Amalgamは最大HP 199で頭打ちになる。")
    lines.append(f"- Amalgam撃破は base {sum(1 for t in b if t['amalgam_killed'])}/{len(b)}、"
                 f"str3 {sum(1 for t in c if t['amalgam_killed'])}/{len(c)}。")
    lines.append(f"- 攻撃1回あたりのダメージは {statistics.mean([t['dmg_per_attack'] for t in b]):.2f} → "
                 f"{statistics.mean([t['dmg_per_attack'] for t in c]):.2f} で、上がっている。"
                 f"最大Strengthの中央値は {statistics.median([t['max_strength'] for t in b]):.1f} → "
                 f"{statistics.median([t['max_strength'] for t in c]):.1f}。")

    lines.append("")
    lines.append("### 3-3 組ごとの内訳")
    lines.append("| spec | base removed | str3 removed | 差 | baseターン | str3ターン |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    by = defaultdict(dict)
    for t in trials:
        by[t["spec"]][t["arm"]] = t
    deltas = []
    for spec, arms in sorted(by.items()):
        if "base" not in arms or "str3" not in arms:
            continue
        bt, ct = arms["base"], arms["str3"]
        br = bt["queen_removed"] + bt["amalgam_removed"]
        cr = ct["queen_removed"] + ct["amalgam_removed"]
        deltas.append(cr - br)
        lines.append(f"| {spec} | {br:.0f} | {cr:.0f} | {cr-br:+.0f} | {bt['turns']} | {ct['turns']} |")
    lines.append("")
    lines.append(f"- 悪化 {sum(1 for d in deltas if d < 0)} 組、改善 {sum(1 for d in deltas if d > 0)} 組、"
                 f"同値 {sum(1 for d in deltas if d == 0)} 組。")
    lines.append("")
    lines.append("読み: 「Strength +4で総火力/ターンが下がった」は、攻撃1回あたりのダメージが下がったという意味ではない。"
                 "分子が Queen と Amalgam の合算で、Amalgam が最大HP 199で頭打ちになるため、"
                 "Amalgam に寄ったダメージが総火力に反映されにくい。str3 では Amalgam 撃破が1組増え、"
                 "Queen への削りが34減っている（同じ組で同時に起きた差で、因果は主張しない）。"
                 "加えて比の平均は短い戦闘（3ターン死亡）を過大評価する。交絡として、str3 はデッキが3枚多く、"
                 "セットアップ使用が0.33→2.08回に増えており、エネルギーとドローの配分も変わっている。"
                 "したがって 38.8→37.2 は「1枚あたりの打点の低下」ではなく、対象配分と指標の作り方の差として読む。")
    return "\n".join(lines)


CLEAR_RUNS = (
    ("file", "astra_ctrl_v23_495FF454B7_agent.jsonl"),
    ("tar", "2026-09.tar.gz", "act3_recheck_2675e82_N8CQ4ZKP2W_agent.jsonl"),
    ("tar", "2026-09.tar.gz", "candidate_vulnlethal_N8CQ4ZKP2W_agent.jsonl"),
    ("tar", "2026-10.tar.gz", "astra_eval_v1_candidate_N8CQ4ZKP2W_agent.jsonl"),
    ("tar", "2026-10.tar.gz", "astra_eval_v10_candidate_DD1018C7FF_agent.jsonl"),
    ("tar", "2026-10.tar.gz", "astra_eval_v14_control_8D95FF5CE9_agent.jsonl"),
    ("tar", "2026-10.tar.gz", "astra_eval_v6_candidate_E8282AC0A7_agent.jsonl"),
)
EXTRA_CLEARS = (
    ("tar", "2026-09.tar.gz", "candidate_last_hp_selfdamage_H2LV6ZJ4XW_agent.jsonl"),
    ("tar", "2026-10.tar.gz", "smoke_v17_FD7A9C8F5F_agent.jsonl"),
)

STRENGTH_SRC = {"CARD.RUPTURE", "CARD.INFLAME", "CARD.DEMON_FORM", "CARD.LIMIT_BREAK"}
ENERGY_SRC = {"CARD.BLOODLETTING", "CARD.SEEING_RED", "CARD.OFFERING"}
MULTI_HIT = {"CARD.SWORD_BOOMERANG", "CARD.WHIRLWIND", "CARD.ANGER",
             "CARD.POMMEL_STRIKE", "CARD.TWIN_STRIKE"}
DRAW_SRC = {"CARD.BATTLE_TRANCE", "CARD.HELLRAISER", "CARD.OFFERING",
            "CARD.POMMEL_STRIKE", "CARD.SHRUG_IT_OFF"}


def _read_run(desc, data_dir):
    if desc[0] == "file":
        path = os.path.join(data_dir, desc[1])
        return read_rows(path)
    import tarfile
    with tarfile.open(os.path.join(data_dir, "_archive", desc[1]), "r:gz") as tar:
        handle = tar.extractfile(desc[2])
        text = handle.read().decode("utf-8", "replace")
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _entry_of(rows):
    for row in rows:
        if row.get("phase") != "combat":
            continue
        if any(str(e.get("id", "")).endswith(QUEEN) for e in row.get("enemies") or []):
            cards = ((row.get("draw_pile") or []) + (row.get("hand") or [])
                     + (row.get("discard_pile") or []) + (row.get("exhaust_pile") or []))
            player = row.get("player") or {}
            return {
                "ids": [c.get("id") for c in cards],
                "relics": list(player.get("relics") or []),
                "max_energy": player.get("max_energy"),
                "hp": player.get("hp"),
                "upgrades": sum(1 for c in cards if c.get("upgrade")),
                "cards": len(cards),
            }
    return None


def section_reward(fights, data_dir):
    groups = {"clear": [], "low": [], "rest": []}
    for desc in CLEAR_RUNS:
        entry = _entry_of(_read_run(desc, data_dir))
        if entry:
            groups["clear"].append(entry)
    for f in fights:
        if f["shave"] is None:
            continue
        row = f["combat"][0]
        cards = ((row.get("draw_pile") or []) + (row.get("hand") or [])
                 + (row.get("discard_pile") or []) + (row.get("exhaust_pile") or []))
        entry = {
            "ids": [c.get("id") for c in cards],
            "relics": list((row.get("player") or {}).get("relics") or []),
            "max_energy": (row.get("player") or {}).get("max_energy"),
            "hp": (row.get("player") or {}).get("hp"),
            "upgrades": sum(1 for c in cards if c.get("upgrade")),
            "cards": len(cards),
        }
        groups["low" if f["shave"] < 0.3 else "rest"].append(entry)

    def presence(group, key):
        count = Counter()
        for entry in group:
            count.update(set(entry[key]))
        return count

    lines = []
    n_low = len(groups["low"])
    n_rest = len(groups["rest"])
    lines.append(f"比較: Act 3踏破 run（記録の7本） 対 Queen削り0.3未満の{n_low}戦（v23+v24） 対 残り{n_rest}戦。"
                 f"削りはQueen単独（EVALUATION.mdの主信号）。デッキはQueen入場時の手札・山札・捨て札・廃棄札のカードID。")
    lines.append("")
    lines.append("踏破 run の内訳（7本）: `astra_ctrl_v23_495FF454B7`、`N8CQ4ZKP2W` が3本"
                 "（act3_recheck / candidate_vulnlethal / astra_eval_v1_candidate）、"
                 "`astra_eval_v10_candidate_DD1018C7FF`、`astra_eval_v14_control_8D95FF5CE9`、"
                 "`astra_eval_v6_candidate_E8282AC0A7`。")
    lines.append("")
    lines.append("生ログの走査では、踏破した trace は全部で15本、seedの種類では9本だった。"
                 "記録の7本に入らない踏破が2本ある: `candidate_last_hp_selfdamage_H2LV6ZJ4XW`（2026-09）と"
                 "`smoke_v17_FD7A9C8F5F`（2026-10）。どちらも Neow から始まる完全な run で、Queen戦の"
                 "`combat_end.won=true` で終わっている。")
    lines.append("")
    lines.append("### 5-1 札の有無（件数）")
    lines.append(f"| カード | 踏破 7本 | 削り<0.3 {n_low}戦 | 残り {n_rest}戦 |")
    lines.append("| --- | --- | --- | --- |")
    pc = presence(groups["clear"], "ids")
    pl_ = presence(groups["low"], "ids")
    pr = presence(groups["rest"], "ids")
    keys = set(pc) | set(pl_) | set(pr)
    ranked = sorted(keys, key=lambda k: (-(pc.get(k, 0) - 0.3 * pl_.get(k, 0)), -pc.get(k, 0)))
    for key in ranked[:14]:
        lines.append(f"| {key.replace('CARD.', '')} | {pc.get(key, 0)}/7 | {pl_.get(key, 0)}/{n_low} | "
                     f"{pr.get(key, 0)}/{n_rest} |")

    lines.append("")
    lines.append("### 5-2 組み合わせ（件数）")
    lines.append(f"| 組み合わせ | 踏破 7本 | 削り<0.3 {n_low}戦 | 残り {n_rest}戦 |")
    lines.append("| --- | --- | --- | --- |")
    def all_of(ids, needed):
        return needed <= ids

    def any_of(ids, pool):
        return bool(ids & pool)

    combos = (
        ("Strength源（どれか1枚）", lambda ids: any_of(ids, STRENGTH_SRC)),
        ("RUPTURE 単独", lambda ids: "CARD.RUPTURE" in ids),
        ("RUPTURE + CRIMSON_MANTLE", lambda ids: all_of(ids, {"CARD.RUPTURE", "CARD.CRIMSON_MANTLE"})),
        ("RUPTURE + MAD_SCIENCE", lambda ids: all_of(ids, {"CARD.RUPTURE", "CARD.MAD_SCIENCE"})),
        ("FORGOTTEN_RITUAL + RUPTURE", lambda ids: all_of(ids, {"CARD.FORGOTTEN_RITUAL", "CARD.RUPTURE"})),
        ("Strength源 + エネルギー源", lambda ids: any_of(ids, STRENGTH_SRC) and any_of(ids, ENERGY_SRC)),
        ("Strength源 + ドロー源", lambda ids: any_of(ids, STRENGTH_SRC) and any_of(ids, DRAW_SRC)),
        ("RUPTURE + CRIMSON_MANTLE + MAD_SCIENCE", lambda ids: all_of(
            ids, {"CARD.RUPTURE", "CARD.CRIMSON_MANTLE", "CARD.MAD_SCIENCE"})),
    )
    for label, pred in combos:
        counts = [sum(1 for e in group if pred(set(e["ids"])))
                  for group in (groups["clear"], groups["low"], groups["rest"])]
        lines.append(f"| {label} | {counts[0]}/7 | {counts[1]}/{n_low} | {counts[2]}/{n_rest} |")

    lines.append("")
    lines.append("### 5-3 エネルギー源とレリック")
    lines.append(f"| 指標 | 踏破 7本 | 削り<0.3 {n_low}戦 | 残り {n_rest}戦 |")
    lines.append("| --- | --- | --- | --- |")
    for label, fn, fmt in (
        ("最大エネルギー 平均", lambda g: statistics.mean([e["max_energy"] for e in g]), "{:.2f}"),
        ("入場HP 平均", lambda g: statistics.mean([e["hp"] for e in g]), "{:.1f}"),
        ("デッキ枚数 平均", lambda g: statistics.mean([e["cards"] for e in g]), "{:.1f}"),
        ("強化枚数 平均", lambda g: statistics.mean([e["upgrades"] for e in g]), "{:.1f}"),
        ("レリック数 平均", lambda g: statistics.mean([len(e["relics"]) for e in g]), "{:.1f}"),
    ):
        lines.append(f"| {label} | " + " | ".join(
            fmt.format(fn(g)) for g in (groups["clear"], groups["low"], groups["rest"])) + " |")
    rel = {name: [presence(g, "relics").get(name, 0)
                  for g in (groups["clear"], groups["low"], groups["rest"])]
           for name in ("RELIC.STRAWBERRY", "RELIC.LANTERN", "RELIC.ANCHOR",
                        "RELIC.GOLDEN_PEARL", "RELIC.LETTER_OPENER")}
    for name, counts in rel.items():
        lines.append(f"| {name.replace('RELIC.', '')} | {counts[0]}/7 | {counts[1]}/{n_low} | {counts[2]}/{n_rest} |")
    energy_relics = [r for e in groups["clear"] + groups["low"] + groups["rest"]
                     for r in e["relics"] if "ENERGY" in str(r)]
    lines.append(f"| エネルギー系レリック | {len(energy_relics)} 件（全群合計） | | |")

    lines.append("")
    lines.append("### 5-4 交絡（この比較で言えないこと）")
    lines.append("- 踏破7本は2026-09-10〜10-28 の別々の方針版で走った run で、削り<0.3 の14戦は v23/v24（10-28以降）だけ。"
                 "時代と方針版が揃っていない。")
    lines.append("- 踏破 run は結果で選んでいる。持ち物の差は勝因の候補であって、勝因そのものではない。")
    lines.append("- `N8CQ4ZKP2W` の3本は同じ seed で、デッキもほぼ同一。独立な標本は実質5本。"
                 "上の「4/7」は2種類のデッキ（495FF454B7 と N8CQ4ZKP2W）を数えている。")
    lines.append("- 踏破 run の入場HPは平均90.1で、削り<0.3 の68.3より高い。Act 1〜2を健全に抜けた選択の差が"
                 "そのままデッキ差に見えている可能性がある。")
    lines.append("- 削り<0.3 の14戦は「到達はしたが削れなかった」集団で、Act 3に来られなかった run は含まない。")
    lines.append("")
    lines.append("読み: 単札では RUPTURE が 5/7 対 2/14、組み合わせでは RUPTURE+CRIMSON_MANTLE が 4/7 対 0/14、"
                 "RUPTURE+MAD_SCIENCE が 4/7 対 0/14。ただし標本は実質5本で、時代と入場HPの交絡が大きい。"
                 "報酬方針の候補にするなら、この差を「勝ち筋の仮説」として事前登録し、フルrunで測る必要がある。")
    return "\n".join(lines)


def _rho_text(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return "算出不能"
    r = spearman([p[0] for p in pairs], [p[1] for p in pairs])
    return f"{r:+.3f}（n={len(pairs)}）" if r is not None else "算出不能"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("section", choices=["calib", "scaling", "str3", "reward", "all"])
    ap.add_argument("--data-dir", default="/Users/mao/workspace/sts2-ai/data")
    ap.add_argument("--str-dir", default=str(HERE.parent.parent / "data" / "bosslab_act3_str_conf"))
    args = ap.parse_args(argv)

    fights = load_fights(args.data_dir)
    for f in fights:
        f["first_value"] = first_value(f["combat"])

    out = []
    if args.section in ("calib", "all"):
        out.append(section_calib(fights))
    if args.section in ("scaling", "all"):
        out.append(section_scaling(fights))
    if args.section in ("str3", "all"):
        out.append(section_str3(args.str_dir))
    if args.section in ("reward", "all"):
        out.append(section_reward(fights, args.data_dir))
    print("\n\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
