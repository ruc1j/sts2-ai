#!/usr/bin/env python3
"""Replay each dev2-base observation through base / queenfirst / H1 / H2 and tabulate target choice.

Leader asked (T17) to see, before the real-machine run, at which player turns each candidate would
aim its single-target attacks at the Amalgam versus the Queen, using the base dev2 run's own recorded
observations. The candidates and the base all short-circuit the Queen fight in the heuristic tail
before any rollout, so replaying an observation without enemy_data reproduces the target choice
exactly (the Amalgam/Queen decision never needs the simulator). _PENDING_ACTION is cleared between
calls so one observation never leaks its action counters into the next.

Per (trial, player turn) the run reports: what the Amalgam effective HP and expected Amalgam incoming
were at the turn's first observation, and, among that turn's attack decisions, whether each policy
aimed at the Amalgam or the Queen (or took neither = block / end_turn / potion / buff). Usage:
    python3 bosslab/tools/reproduce_h_targets.py [--out bosslab/results/...]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REPO = Path(__file__).resolve().parents[2]
AGENTS = REPO / "bosslab" / "agents"
RUN = "bosslab_act3_dev2"

import official_agent  # noqa: E402


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODELS = {
    "base": official_agent,
    "queenfirst": load("queenfirst", AGENTS / "official_agent_queenfirst.py"),
    "H1": load("h1", AGENTS / "official_agent_H1.py"),
    "H2": load("h2", AGENTS / "official_agent_H2.py"),
    "H3a": load("h3a", AGENTS / "official_agent_H3a.py"),
    "H3b": load("h3b", AGENTS / "official_agent_H3b.py"),
    "H3c": load("h3c", AGENTS / "official_agent_H3c.py"),
}


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


def slot_of(obs: dict, target_id) -> str:
    if target_id is None:
        return "none"
    for e in obs.get("enemies", ()):
        if e.get("combat_id") == target_id:
            if e.get("id") == "MONSTER.TORCH_HEAD_AMALGAM":
                return "A"
            if e.get("id") == "MONSTER.QUEEN":
                return "Q"
            return "other"
    return "gone"


def first_metrics(obs: dict) -> tuple[int, int]:
    """(Amalgam effective HP, expected Amalgam incoming) from the enemies list of one observation."""
    eff = incoming = 0
    for e in obs.get("enemies", ()):
        if e.get("id") == "MONSTER.TORCH_HEAD_AMALGAM":
            eff += int(e.get("hp") or 0) + int(e.get("block") or 0)
            dmg = 0
            for it in e.get("intents", ()):
                dmg += int(it.get("damage") or 0) * max(1, int(it.get("repeats") or 1))
            incoming += dmg
    return eff, incoming


def replay(obs: dict, model) -> str:
    model._PENDING_ACTION = None
    try:
        action = model.choose(dict(obs))
    except Exception:  # noqa: BLE001 - a rollout/edge that needs enemy_data; only target matters
        return slot_of(obs, obs.get("_fallback"))  # unreachable in practice for these rows
    return slot_of(obs, action.get("target_id"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(REPO / "bosslab/results/act3_queenfirst_h1h2_dev2.md"))
    args = ap.parse_args()

    lines = [
        "# dev2 base 観測から H1/H2 の殴り先を手番ごとに再現 (T17 item2 続)",
        "",
        "各手番の最初の観測で Amalgam 実効HP / Amalgam の予想被ダメを算出し、その手番の攻撃判断が",
        "Amalgam(A) か Queen(Q) か (それ以外=防御/ターン終了/ポーション/強化=『-』) を各ポリシーで再現。",
        "H1閾値=50、H2=その手番のHP+ブロック、H3a=最初のQUEENFIRST_H3_OPEN_TURNS(2)ターンだけA、",
        "H3b=実効HP<=150でA（閾値上げの診断）、H3c=Amalgam予想被ダメが(HP+blk)の5割以上でA（危険前に削り）。",
        "全ポリシー同じ観測に流し、enemy_data無しの決定的heuristic再現（Queen短絡とfocused_minionsが殴り先を決める）。",
        "",
    ]
    totals = {k: {"A": 0, "Q": 0, "none": 0, "other": 0, "gone": 0} for k in MODELS}
    COLS = list(MODELS)
    diff_turns = {k: {"vs_base": 0, "vs_Q": 0} for k in MODELS}
    n_turns = 0

    for path in sorted(REPO.glob(f"data/{RUN}/trial_*_agent.jsonl")):
        rows = rows_of(path)
        if not rows:
            continue
        per_turn: dict[int, dict] = {}
        for row in rows:
            t = int(row.get("turn") or 0)
            entry = per_turn.setdefault(t, {"first": row, "last": row, "picks": {k: set() for k in MODELS}})
            entry["last"] = row
            for k, m in MODELS.items():
                entry["picks"][k].add(replay(row, m))
        lines.append(f"## trial {path.name.split('_')[1]}  ({path.stem.split('_agent')[0]})")
        lines.append("")
        lines.append("| turn | Amalgam実効HP | Amalgam予想被ダメ | HP+blk | " + " | ".join(COLS) + " |")
        lines.append("| --- | --- | --- | --- | " + " | ".join("---" for _ in COLS) + " |")
        for t in sorted(per_turn):
            entry = per_turn[t]
            eff, inc = first_metrics(entry["first"])
            pl = entry["first"].get("player", {})
            surv = int(pl.get("hp") or 0) + int(pl.get("block") or 0)

            def verdict(k: str) -> str:
                picks = entry["picks"][k]
                if "A" in picks:
                    return "A"
                if "Q" in picks:
                    return "Q"
                return "none" if "none" in picks else ("other" if "other" in picks else "-")

            row_cells = {k: verdict(k) for k in MODELS}
            for k, v in row_cells.items():
                totals[k][v if v in totals[k] else "other"] += 1
            b, q = row_cells["base"], row_cells["queenfirst"]
            n_turns += 1
            for k in COLS:
                if row_cells[k] != b:
                    diff_turns[k]["vs_base"] += 1
                if row_cells[k] != q:
                    diff_turns[k]["vs_Q"] += 1
            lines.append(f"| {t} | {eff} | {inc} | {surv} | " + " | ".join(row_cells[k] for k in COLS) + " |")
        lines.append("")

    lines.append("## 集計")
    lines.append("")
    lines.append(f"- 手番数 {n_turns}")
    lines.append(f"- Amalgam(A)/Queen(Q) 選択: " + "  ".join(
        f"{k} A={totals[k]['A']} Q={totals[k]['Q']} 攻撃以外={totals[k]['none']+totals[k]['other']+totals[k]['gone']}"
        for k in MODELS))
    for k in COLS:
        if k == "base":
            continue
        lines.append(f"- {k}: base と異なる手番 {diff_turns[k]['vs_base']}  queenfirst と異なる手番 {diff_turns[k]['vs_Q']}")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    for k in COLS:
        if k == "base":
            continue
        print(f"  {k}: vs base {diff_turns[k]['vs_base']}  vs queenfirst {diff_turns[k]['vs_Q']}  "
              f"A={totals[k]['A']} Q={totals[k]['Q']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
