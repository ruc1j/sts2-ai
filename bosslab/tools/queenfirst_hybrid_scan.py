#!/usr/bin/env python3
"""Scan base vs queenfirst boss traces for the Amalgam-kill crossover.

Amalgam (MONSTER.TORCH_HEAD_AMALGAM, slot "amalgam") is a secondary minion: it is the only enemy
dealing damage while the Queen buffs, and it auto-dies when the Queen (primary) dies, so killing it
never ends the fight on its own. The base agent concentrates single-target attacks on it
(official_agent.py queen_minion_direct); the queenfirst copy redirects them to the Queen. This script
replays each trial trace and reports, at the start of every player turn, the Amalgam effective HP,
the maximum damage the opening hand could put on it for the available energy, and whether that was a
lethal amount, so a hybrid that attacks Amalgam only when it is killable this turn (and otherwise
goes to the Queen) can be specified and measured.

Damage per card comes from the bridge's own hand preview (card `Damage` var), so player Strength is
already folded in; Vulnerable on Amalgam multiplies by 1.5. Buffs played earlier in the same turn
(HELLRAISER / INFLAME raising Strength) are NOT folded in, so a turn that plays a Strength buff before
its attacks is underestimated. Potion damage is ignored. Amalgam block is subtracted first.

Usage: python3 bosslab/tools/queenfirst_hybrid_scan.py [--out bosslab/results/...]
"""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # bosslab/tools/ -> repo root

RUNS = [
    ("dev2 base", "bosslab_act3_dev2"),
    ("dev2 queenfirst", "bosslab_act3_dev2_queenfirst"),
    ("confirm2 base", "bosslab_act3_confirm2"),
    ("confirm2 queenfirst", "bosslab_act3_confirm2_queenfirst"),
    ("confirm3 base", "bosslab_act3_confirm3"),
    ("confirm3 queenfirst", "bosslab_act3_confirm3_queenfirst"),
]


def rows_of(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if isinstance(r, dict) and r.get("phase") == "combat":
            out.append(r)
    return out


def enemy_by_slot(row: dict, slot: str) -> dict | None:
    for e in row.get("enemies") or ():
        if e.get("slot") == slot:
            return e
    return None


def has_power(enemy: dict | None, pid: str) -> bool:
    return any((p.get("id") == pid for p in ((enemy or {}).get("powers") or ())))


def card_damage(card: dict) -> int | None:
    for v in card.get("vars") or ():
        if v.get("id") == "Damage":
            try:
                return int(float(v.get("value")))
            except (TypeError, ValueError):
                return None
    return None


def max_damage_to_amalgam(hand: list[dict], energy: int, amalgam: dict) -> int:
    """Energy-budgeted (0/1 by copy count) knapsack of attack damage the hand can put on Amalgam.

    Cards with no computed Damage value (unpreviewed skills) and self-damage cards are dropped.
    Vulnerable on Amalgam applies the x1.5 multiplier the real hit will deal.
    """
    items = []
    for card in hand:
        dmg = card_damage(card)
        if not dmg or dmg <= 0:
            continue
        try:
            cost = int(float(card.get("cost") or 0))
        except (TypeError, ValueError):
            continue
        if has_power(amalgam, "POWER.VULNERABLE_POWER"):
            dmg = int(dmg * 1.5)
        items.append((max(0, cost), dmg))
    best = [0] * (energy + 1)
    for cost, dmg in items:
        for e in range(energy, cost - 1, -1):
            cand = best[e - cost] + dmg
            if cand > best[e]:
                best[e] = cand
    return best[energy]


def scan_trace(path: Path, won: bool) -> dict | None:
    rows = rows_of(path)
    if not rows:
        return None
    first, last = rows[0], rows[-1]
    amax = enemy_by_slot(first, "amalgam")
    if amax is None:
        return None

    per_turn: dict[int, dict] = {}
    for row in rows:
        t = int(row.get("turn") or 0)
        if t not in per_turn:
            per_turn[t] = {"start": row}
        per_turn[t]["last"] = row  # keep the last observation seen this turn

    # Observations are taken before each decision, so the state right after a killing blow is only
    # visible on the next observation. Amalgam is killed standalone if it vanishes from the enemy
    # list while the Queen is still present with hp > 0; if the Queen vanishes too, Amalgam co-died
    # as a minion (that is the win, not an Amalgam-focused kill).
    amalgam_dead_turn = None
    amalgam_killed_standalone = False
    for row in rows:
        a_present = enemy_by_slot(row, "amalgam") is not None
        q = enemy_by_slot(row, "queen")
        if not a_present and q is not None and int(q.get("hp") or 0) > 0:
            amalgam_dead_turn = int(row.get("turn") or 0)
            amalgam_killed_standalone = True
            break

    turns = []
    for t in sorted(per_turn):
        start = per_turn[t]["start"]
        last = per_turn[t]["last"]
        a0 = enemy_by_slot(start, "amalgam")
        a_last = enemy_by_slot(last, "amalgam")
        q0 = enemy_by_slot(start, "queen")
        if a0 is None or q0 is None:
            continue
        amax_hp = int(a0.get("hp") or 0) + int(a0.get("block") or 0)
        q_max_hp = int(q0.get("max_hp") or 0)
        try:
            energy = int(float(start["player"].get("energy") or 0))
        except (KeyError, TypeError, ValueError):
            energy = 0
        maxdmg = max_damage_to_amalgam(start.get("hand") or [], energy, a0)
        killable = amax_hp > 0 and maxdmg >= amax_hp
        turns.append({
            "turn": t,
            "amalgam_effhp": amax_hp,
            "maxdmg": maxdmg,
            "killable": killable,
            "queen_hp": int(q0.get("hp") or 0),
            "queen_max_hp": q_max_hp,
            "amalgam_alive_end": (a_last is not None and int(a_last.get("hp") or 0) > 0),
        })

    queen_start_hp = int(enemy_by_slot(first, "queen").get("hp") or 0) if enemy_by_slot(first, "queen") else 0
    queen_final_hp = int((enemy_by_slot(last, "queen") or {}).get("hp") or 0)
    first_kill = next((t["turn"] for t in turns if t["killable"]), None)
    return {
        "trial": path.name,
        "turns": turns,
        "amalgam_start_effhp": turns[0]["amalgam_effhp"] if turns else 0,
        "first_killable_turn": first_kill,
        "amalgam_dead_turn": amalgam_dead_turn,
        "amalgam_killed_standalone": amalgam_killed_standalone,
        "queen_start_hp": queen_start_hp,
        "queen_final_hp": queen_final_hp,
        "queen_pct_lost": (100.0 * (queen_start_hp - queen_final_hp) / queen_start_hp) if queen_start_hp else 0.0,
        "won": won,
        "turns_played": len(turns),
    }


def won_map(run_dir: str) -> dict[int, bool]:
    path = REPO / "data" / run_dir / "lab_results.jsonl"
    out: dict[int, bool] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        idx = rec.get("trial_index")
        res = rec.get("result") or {}
        if idx is not None and "won" in res:
            out[int(idx)] = bool(res["won"])
    return out


def scan_run(label: str, run_dir: str) -> list[dict]:
    wins = won_map(run_dir)
    out = []
    for path in sorted(REPO.glob(f"data/{run_dir}/trial_*_agent.jsonl")):
        idx = int(path.name.split("_")[1])
        rec = scan_trace(path, wins.get(idx, False))
        if rec:
            out.append(rec)
    return out


def fmt_run(trials: list[dict]) -> list[str]:
    lines = []
    n = len(trials)
    wins = sum(1 for t in trials if t["won"])
    standalone = sum(1 for t in trials if t["amalgam_killed_standalone"])
    killable_trials = [t for t in trials if t["first_killable_turn"] is not None]
    avg_fk = (sum(t["first_killable_turn"] for t in killable_trials) / len(killable_trials)) if killable_trials else float("nan")
    lines.append(f"- trials {n}  勝ち {wins}/{n}  Amalgam単独撃破 {standalone}  "
                 f"単ターンのみで击杀可能だった trial {len(killable_trials)}/{n}"
                 + (f"  (初回可能turn 平均 {avg_fk:.1f})" if killable_trials else ""))
    lines.append("")
    lines.append("| trial | 入場AmalgamHP | 初回击杀可能turn | Amalgam単独死亡turn | 初回可能Tの最大Damage | Queen削り% | 結果 | 手数 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in trials:
        fk = t["first_killable_turn"]
        fk_turn = next((c for c in t["turns"] if c["killable"]), None)
        fk_max = fk_turn["maxdmg"] if fk_turn else ""
        lines.append(
            f"| {t['trial'].replace('_agent.jsonl','').replace('trial_','')} | {t['amalgam_start_effhp']} "
            f"| {fk if fk is not None else '—'} | {t['amalgam_dead_turn'] if t['amalgam_dead_turn'] is not None else '—'} "
            f"| {fk_max} | {t['queen_pct_lost']:.0f} | {'勝' if t['won'] else '負'} | {t['turns_played']} |"
        )
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "bosslab/results/act3_queenfirst_hybrid_scan.md"))
    args = ap.parse_args()

    sections = ["# Act3 boss: Amalgam 击杀 crossover 扫描 (item2 解析)", "",
                "Amalgam は二次ミニオン（QUEEN死亡で道連れに消える）。単体処理では勝てないため、",
                "『そのターン击杀できる時だけ Amalgam、できなければ Queen』という切替条件の分かれ目を見る。",
                "maxDamage は手札 preview の Damage 値の energy 最適化（VULN x1.5 反映、同ターン内の",
                "Strength バフ先行・ポーションは未考慮＝楽観/悲観入り混じる近似）。", ""]
    for label, run_dir in RUNS:
        trials = scan_run(label, run_dir)
        sections.append(f"## {label}  ({run_dir})")
        sections += fmt_run(trials)
        sections.append("")
    Path(args.out).write_text("\n".join(sections) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
