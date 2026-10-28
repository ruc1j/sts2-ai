#!/usr/bin/env python3
"""Turn-by-turn comparison of a BossLab trial fight vs the real fight on the same entry state.

Analysis only. For each trial of one arm (default base) this reads the lab trial trace
(data/bosslab_pass1/trial_NNNN_agent.jsonl) and the original run trace recorded in the spec's
sources, parses both trace streams (each record = one observation + the decision made on it,
written by CombatBridge in both cases), and aligns them turn by turn. The goal is to find the
first difference that RNG variance cannot explain — the candidates from the leader:

- boss scaling: per executed move, the intent damage numbers and the boss's own Strength gains
  (Salivate +2 vs +3 is an ascension difference), versus the real fight's numbers;
- boss move/intent sequence: the Insatiable cycles LIQUIFY -> THRASH -> BITE -> SALIVATE -> ...
  deterministically, so a different executed sequence means the fight state diverged (Sandpit
  escapes, kills, respawns) rather than RNG;
- player start-of-combat powers and relic effects: entry powers, relic counters at end, and the
  per-turn power timeline (e.g. Paels' Blood Strength gains after the first attack);
- damage economy: per turn, cards played, energy used, damage dealt, damage taken, block — the
  systematic question is whether the lab agent converts the same resources into less damage;
- agent config: the simulations field on every decision record (100 vs the real run's value) and
  decision_source mix.

Differences that are inherent RNG (opening hand order, Sand card placement, reshuffle order) are
reported but flagged as such: what matters is a difference that repeats in the same direction
across all six specs.

Usage (from the worktree root):
  python3 .dsh/bosslab_turn_diff.py --arm base --out .dsh/bosslab_turn_diff.md
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MAIN_TREE = Path("/Users/mao/workspace/sts2-ai")
BOSS_SUFFIX = "THE_INSATIABLE"


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
        if isinstance(r, dict):
            out.append(r)
    return out


def boss_combat_blocks(rows: list[dict]) -> list[list[dict]]:
    """Group the decision records of each Insatiable fight into blocks."""
    blocks: list[list[dict]] = []
    cur: list[dict] = []
    for r in rows:
        if r.get("phase") == "combat":
            cur.append(r)
        elif r.get("phase") == "combat_end":
            if cur and any((e.get("id") or "").endswith(BOSS_SUFFIX) for e in cur[0].get("enemies") or []):
                blocks.append(cur)
            cur = []
    if cur and any((e.get("id") or "").endswith(BOSS_SUFFIX) for e in cur[0].get("enemies") or []):
        blocks.append(cur)
    return blocks


def card_ids(obs: dict, key: str) -> list[str]:
    return [c.get("id", "?") + ("+" if (c.get("upgrade") or 0) else "")
            for c in (obs.get(key) or []) if isinstance(c, dict)]


def intent_sig(enemies: list[dict]) -> str:
    parts = []
    for e in enemies:
        for it in e.get("intents") or []:
            dmg = it.get("damage") or 0
            rep = it.get("repeats") or 1
            parts.append(f"{it.get('type','?')}:{dmg:g}x{rep}")
        parts[-1:-1] = [f"[{e.get('slot', '?')}]"]
    return " ".join(parts)


def powers_str(lst) -> str:
    return ",".join(f"{(p.get('id') or '').replace('POWER.','')}={p.get('amount')}"
                    for p in (lst or []) if isinstance(p, dict)) or "-"


def turns_of(block: list[dict]) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = collections.defaultdict(list)
    for r in block:
        out[int(r.get("turn") or 0)].append(r)
    return out


def per_turn_table(blocks: list[list[dict]], label: str) -> tuple[list[str], dict]:
    """One markdown line per decision plus a per-turn summary dict for systematic stats."""
    block = blocks[0]
    lines = ["", f"### {label}", "",
             "| T | seq | play | tgt | dmg→enemy | dmg←enemy | block | energy L→R | hand | P-powers | E-hp | E-move | intents | src/sims |",
             "| - | - | - | - | - | - | - | - | - | - | - | - | - | - |"]
    summary: dict = {"turns": 0, "dmg_dealt": 0, "dmg_taken": 0, "energy_used": 0,
                     "played": collections.Counter(), "move_seq": [], "move_dmg": collections.Counter(),
                     "salivate_str": [], "srcs": collections.Counter(), "sims": set(),
                     "entry_powers": powers_str((block[0].get("player") or {}).get("powers")),
                     "entry_hand": card_ids(block[0], "hand"), "end_relic_counters": {}}
    prev_enemy_hp = None
    prev_player = None
    prev_history: list[str] = []
    for r in block:
        turn = int(r.get("turn") or 0)
        enemies = r.get("enemies") or []
        e0 = enemies[0] if enemies else {}
        player = r.get("player") or {}
        hp = int(player.get("hp") or 0)
        block_amt = int(player.get("block") or 0)
        energy = int(player.get("energy") or 0)
        e_hp = int(e0.get("hp") or 0)
        dealt = taken = 0
        if prev_enemy_hp is not None:
            dealt = max(0, prev_enemy_hp - e_hp)
        if prev_player is not None:
            taken = max(0, int(prev_player.get("hp") or 0) - hp)
            # damage taken between obs rows also happens on the enemy phase; block delta at
            # the row after an end_turn marks what the enemy hit.
        # enemy moves actually executed since previous observation (history grows append-only)
        hist = list(e0.get("history") or [])
        new_moves = hist[len(prev_history):] if hist[:len(prev_history)] == prev_history else hist
        if new_moves:
            summary["move_seq"].append("|".join(m.replace("_MOVE", "") for m in new_moves))
            if taken:
                for m in new_moves:
                    summary["move_dmg"][m.replace("_MOVE", "")] += taken
        prev_history = hist
        if e0.get("powers"):
            sal = [p for p in e0["powers"] if "STRENGTH" in (p.get("id") or "")]
            if new_moves and any("SALIVATE" in m for m in new_moves) and sal:
                summary["salivate_str"].append(int(sal[0].get("amount") or 0))
        play = r.get("card_id") or {"end_turn": "END", "skip": "SKIP"}.get(r.get("type"), r.get("type"))
        if r.get("card_id"):
            summary["played"][play + ("+" if (r.get("upgrade_hand_index") is not None) else "")] += 1
        summary["dmg_dealt"] += dealt
        summary["dmg_taken"] += taken
        summary["srcs"][str(r.get("decision_source"))] += 1
        if r.get("simulations") is not None:
            summary["sims"].add(int(r["simulations"]))
        lines.append(
            f"| {turn} | {r.get('seq')} | {play} | {r.get('target_id') or '-'} | {dealt or ''} | {taken or ''} | "
            f"{block_amt} | {energy} | {len(card_ids(r, 'hand'))} | {powers_str(player.get('powers'))} | "
            f"{e_hp} | {e0.get('move', '')} | {intent_sig(enemies)} | {r.get('decision_source')}/{r.get('simulations')} |")
        prev_enemy_hp, prev_player = e_hp, player
    summary["turns"] = max(turns_of(block)) if block else 0
    end = block[-1] if block else {}
    summary["end_relic_counters"] = (end.get("player") or {}).get("relic_counters") or {}
    summary["final_enemy_hp"] = prev_enemy_hp
    summary["won"] = any("combat_end" in json.dumps(x) for x in [block[-1:]])  # not exact; caller fills
    return lines, summary


def summarize_systematic(a: dict, b: dict, label_a: str, label_b: dict) -> list[str]:
    """Rows comparing the two summaries for direction-consistent (systematic) differences."""
    rows = []
    if a["entry_powers"] != b["entry_powers"]:
        rows.append(f"entry player powers differ: {a['entry_powers']} vs {b['entry_powers']}")
    sa, sb = a["salivate_str"], b["salivate_str"]
    if sa and sb and collections.Counter(sa) != collections.Counter(sb):
        rows.append(f"boss salivate Strength differs: {label_a}={collections.Counter(sa)} vs lab={collections.Counter(sb)}")
    for key in ("dmg_dealt", "dmg_taken"):
        if a["turns"] and b["turns"]:
            pass
    la, lb = max(a["turns"], 1), max(b["turns"], 1)
    rows.append(f"dmg dealt/turn: {label_a} {a['dmg_dealt'] / la:.0f} vs lab {b['dmg_dealt'] / lb:.0f}"
                f" ({a['dmg_dealt']}/{a['turns']} vs {b['dmg_dealt']}/{b['turns']} turns)")
    rows.append(f"dmg taken/turn: {label_a} {a['dmg_taken'] / la:.0f} vs lab {b['dmg_taken'] / lb:.0f}")
    e_a = sum(1 for _ in a["srcs"].elements() if True)
    sims_a = a["sims"] or {None}
    sims_b = b["sims"] or {None}
    if sims_a != sims_b:
        rows.append(f"agent simulations differ: real={sorted(x for x in sims_a if x is not None)} vs lab={sorted(x for x in sims_b if x is not None)}")
    else:
        rows.append(f"simulations match: {sorted(x for x in sims_a if x is not None)}")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", default=str(HERE / "bosslab_plan.json"))
    ap.add_argument("--pass-dir", dest="pass_dir", default=str(REPO / "data/bosslab_pass1"))
    ap.add_argument("--specs", default=str(HERE / "boss_specs.jsonl"))
    ap.add_argument("--traces-dir", dest="traces_dir", default=str(MAIN_TREE / "data"))
    ap.add_argument("--arm", default="base")
    ap.add_argument("--out", default=str(HERE / "bosslab_turn_diff.md"))
    ap.add_argument("--offsets", default="0", help="comma list of offsets to compare (default 0)")
    args = ap.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    specs = {json.loads(l)["spec_id"]: json.loads(l)
             for l in Path(args.specs).read_text(encoding="utf-8").splitlines() if l.strip()}
    offsets = {int(x) for x in args.offsets.split(",")}
    traces_dir = Path(args.traces_dir)

    trials = [t for t in plan["trials"] if t["arm"] == args.arm and t["rng_offset"] in offsets]
    out = ["# BossLab ターン別突合 (T6a)", "",
           f"arm={args.arm} offsets={sorted(offsets)} pass={Path(args.pass_dir).name}",
           "各行は trace の 1 観測=1 判定。dmg→enemy は直前行からの敵 HP 減、dmg←enemy は直前行からの",
           "player HP 減（敵行動+被ダメ）。intents は敵の宣言（type:damage×repeats）。",
           "系統的差の候補: entry powers / salivate 後の敵 Strength / move 順列 / dmg per turn /",
           "simulations。RNG 固有（初手順・Sand の挿入位置・reshuffle）は初手の一致率で触れる。", ""]
    overall = collections.Counter()
    for t in trials:
        spec = specs.get(t["spec_id"])
        if not spec:
            continue
        trace_name = f"trial_{t['trial_index']:04d}_agent.jsonl"
        lab_rows = rows_of(Path(args.pass_dir) / trace_name)
        lab_blocks = boss_combat_blocks(lab_rows)
        if not lab_blocks:
            out.append(f"## {t['trial_id']}: lab trace に boss combat がない ({trace_name})")
            continue
        real_rows = None
        real_trace = None
        for src in spec["sources"]:
            cand = traces_dir / src["trace"]
            if cand.is_file():
                real_rows = rows_of(cand)
                real_trace = src["trace"]
                break
        out.append(f"## {t['trial_id']}  (spec {t['spec_id']}, 元trace={real_trace or '見つからない'})")
        if not real_rows:
            out.append("- 元 trace がディスクにない")
            continue
        real_blocks = boss_combat_blocks(real_rows)
        if not real_blocks:
            out.append("- 元 trace に THE_INSATIABLE の戦闘ブロックがない")
            continue
        real_lines, real_sum = per_turn_table(real_blocks, f"実走 {real_trace}")
        lab_lines, lab_sum = per_turn_table(lab_blocks, "ラボ")
        opening_same = sum(1 for c in lab_sum["entry_hand"] if c in real_sum["entry_hand"])
        out.append("")
        out.append(f"- 入場 hand 一致: {opening_same}/{len(lab_sum['entry_hand'])} 枚（初手の引き順は shuffle 差で異なるのは想定内）")
        out.append(f"- 総ターン数: 実走 {real_sum['turns']} vs lab {lab_sum['turns']}。"
                   f"削り: 実走 最終敵HP {real_sum['final_enemy_hp']} vs lab {lab_sum['final_enemy_hp']}")
        systematic = summarize_systematic(real_sum, lab_sum, "実走", lab_sum)
        out.append("- 系統的判定:")
        for srow in systematic:
            out.append(f"  - {srow}")
        seq_match = sum(1 for x, y in zip(real_sum["move_seq"], lab_sum["move_seq"]) if x == y)
        out.append(f"  - 敵 move 系列の前方一致: {seq_match}/{max(len(lab_sum['move_seq']), len(real_sum['move_seq']))} "
                   f"実走={','.join(real_sum['move_seq'])[:180]}")
        out.append(f"    lab={','.join(lab_sum['move_seq'])[:180]}")
        if real_sum["salivate_str"] and lab_sum["salivate_str"] and \
                collections.Counter(real_sum["salivate_str"]) != collections.Counter(lab_sum["salivate_str"]):
            overall["salivate"] += 1
        if real_sum["entry_powers"] != lab_sum["entry_powers"]:
            overall["entry_powers"] += 1
        if real_sum["sims"] and lab_sum["sims"] and real_sum["sims"] != lab_sum["sims"]:
            overall["sims_diff"] += 1
        else:
            overall["sims_match"] += 1
        out += real_lines
        out += lab_lines
        out.append("")
    total_cmp = len([t for t in trials if t["spec_id"] in specs])
    out += [f"## サマリ（{total_cmp} 比較で方向が揃った差・確認事項）", ""]
    for k, v in overall.most_common():
        out.append(f"- {k}: {v}/{total_cmp}")
    Path(args.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(trials)} comparisons, summary {dict(overall)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
