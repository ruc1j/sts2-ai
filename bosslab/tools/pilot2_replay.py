#!/usr/bin/env python3
"""PILOT-2 (1): does search() rank moves by anything except the immediate term?

Replays recorded combat observations from astra_ctrl_v23+v24, re-runs the same
search() that the live agent ran (100 simulations, same seed = observation seq)
and compares

  * the action with the highest mean rollout value (what search() returns), and
  * the action with the highest immediate term alone
    (_step_score + _setup_bonus, the only part of a lost rollout's value that
    depends on the move),

split by the value bucket and by fight type.  Also records the rollout win rate
and the gap between the best and worst action's mean value.

Analysis only: imports combat.py / official_agent.py read-only, never writes to
them.  Observations come from the main checkout's data/ directory.

Usage:
    python3 bosslab/tools/pilot2_replay.py --out bosslab/results/pilot2_replay.json
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
import os
import random
import sys

MAIN = "/Users/mao/workspace/sts2-ai"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MAIN)

import combat as C  # noqa: E402
import official_agent as OA  # noqa: E402

ENEMY_FILES = ("enemies_overgrowth.json", "enemies_hive.json", "enemies_glory.json")
DATA = None
TAGS = ("astra_ctrl_v23", "astra_ctrl_v24")


def load_enemy_data():
    monsters = []
    for name in ENEMY_FILES:
        with open(os.path.join(MAIN, "data", name), encoding="utf-8-sig") as f:
            monsters.extend(json.load(f)["monsters"])
    return {"monsters": monsters}


def fight_kind(enemies):
    ids = [str(e.get("id", "")) for e in enemies or ()]
    if any(i.endswith(".QUEEN") for i in ids):
        return "QUEEN"
    if any("INSATIABLE" in i for i in ids):
        return "INSATIABLE"
    if any("VANTOM" in i for i in ids):
        return "VANTOM"
    return "other"


def search_detail(combat, data, simulations=5000, seed=0):
    """A copy of combat.search() that keeps the per-action internals."""
    actions = C.legal_actions(combat)
    if not actions:
        return [(C.END_TURN, 0.0)], []
    rounds = max(1, simulations // len(actions))
    out = []
    for action in actions:
        scores = []
        wins = 0
        immediate = 0.0
        for simulation in range(rounds):
            rng = random.Random(seed * 1_000_003 + simulation)
            state = C.step(combat, action, data, rng)
            card_value = C._action_card(combat, action)
            self_killed = action != C.END_TURN and state.player_hp <= 0
            immediate = 0.0 if action == C.END_TURN or state.player_hp <= 0 else (
                C._step_score(combat, state, data)
                + C._setup_bonus(combat, state, card_value, data)
            ) / 100
            for _ in range(60):
                if state.terminal:
                    break
                state = C.step(state, C._greedy_action(state, data), data, rng)
            won = (
                state.player_hp > 0
                and not any(
                    (e.alive or (e.model == C.TEST_SUBJECT and e.move == C.RESPAWN_MOVE)) and e.primary
                    for e in state.enemies
                )
                and not any(e.escaped and e.primary for e in state.enemies)
            )
            wins += 1 if won else 0
            scored_hp = max(0, state.player_hp)
            if won and C.RELIC_MEAT_ON_THE_BONE in state.player_relics and state.player_max_hp > 0 and scored_hp * 2 <= state.player_max_hp:
                scored_hp = min(state.player_max_hp, scored_hp + 12)
            scores.append(
                (1 if won else -1 if state.player_hp <= 0 else 0)
                + scored_hp / 100 + immediate - (0.01 if self_killed else 0.0)
            )
        out.append({
            "action": action,
            "value": sum(scores) / len(scores),
            "win_rate": wins / len(scores),
            "immediate": immediate,
        })
    ranked = sorted(out, key=lambda item: item["value"], reverse=True)
    return [(item["action"], item["value"]) for item in ranked], out


def run_one(task):
    path, index = task
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i == index:
                    row = json.loads(line)
                    break
            else:
                return None
    except (OSError, ValueError):
        return None
    if row.get("phase") != "combat":
        return None
    kind = fight_kind(row.get("enemies"))
    if kind == "other" and len(row.get("enemies") or ()) == 0:
        return None
    actions = row.get("legal_actions") or []
    if len(actions) < 2:
        return {"kind": kind, "skipped": "few_actions"}
    # Rebuild the combat exactly as rollout_choice does, by letting it build the
    # state and intercepting the search call.
    captured = {}

    def fake_search(combat, data, simulations=0, seed=0):
        if captured:
            return [(C.END_TURN, 0.0)]
        ordered, detail = search_detail(combat, data, simulations or 100, seed)
        captured["detail"] = detail
        captured["top"] = ordered[0]
        return ordered

    original = OA.search
    OA.search = fake_search
    try:
        OA.rollout_choice(row, actions, DATA, 100)
    except Exception as exc:  # noqa: BLE001 - modelling gaps are expected on old traces
        return {"kind": kind, "skipped": type(exc).__name__}
    finally:
        OA.search = original
    detail = captured.get("detail")
    if not detail:
        return {"kind": kind, "skipped": "no_search"}
    by_value = max(detail, key=lambda d: d["value"])
    by_immediate = max(detail, key=lambda d: d["immediate"])
    values = sorted((d["value"] for d in detail), reverse=True)
    return {
        "kind": kind,
        "seq": row.get("seq"),
        "turn": row.get("turn"),
        "n_actions": len(detail),
        "top_value": by_value["value"],
        "top_action": by_value["action"],
        "immediate_action": by_immediate["action"],
        "agree": by_value["action"] == by_immediate["action"],
        "value_gap": values[0] - values[-1],
        "top2_gap": values[0] - values[1] if len(values) > 1 else 0.0,
        "win_rate": sum(d["win_rate"] for d in detail) / len(detail),
        "max_win_rate": max(d["win_rate"] for d in detail),
        "recorded_value": row.get("search_value"),
        "recorded_source": row.get("decision_source"),
    }


def sample_tasks(rows_by_file):
    tasks = []
    rng = random.Random(0)
    other_pool = []
    for path, rows in rows_by_file.items():
        fight = []
        for i, row in enumerate(rows):
            if row.get("phase") == "combat":
                fight.append(i)
            elif row.get("phase") == "combat_end" and fight:
                kind = fight_kind(rows[fight[0]].get("enemies"))
                limit = {"QUEEN": 10, "INSATIABLE": 3, "VANTOM": 3}.get(kind)
                if limit:
                    step = max(1, len(fight) // limit)
                    tasks.extend((path, fight[j]) for j in range(0, len(fight), step)[:limit])
                else:
                    other_pool.extend((path, i) for i in fight)
                fight = []
    rng.shuffle(other_pool)
    tasks.extend(other_pool[:300])
    return tasks


def main(argv=None):
    global DATA
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", default=os.path.join(MAIN, "data"))
    ap.add_argument("--out", default=os.path.join(HERE, "pilot2_replay.json"))
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 1))
    args = ap.parse_args(argv)

    DATA = load_enemy_data()
    rows_by_file = {}
    for tag in TAGS:
        for path in sorted(glob.glob(os.path.join(args.data_dir, f"{tag}_*_agent.jsonl"))):
            with open(path, encoding="utf-8", errors="replace") as f:
                rows_by_file[path] = [json.loads(line) for line in f if line.strip()]
    tasks = sample_tasks(rows_by_file)
    print(f"traces {len(rows_by_file)}, sampled decisions {len(tasks)}", flush=True)

    with mp.Pool(args.workers, initializer=_init) as pool:
        results = pool.map(run_one, tasks, chunksize=4)
    results = [r for r in results if r]
    kept = [r for r in results if "skipped" not in r]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"sampled": len(tasks), "kept": len(kept), "rows": results}, f, indent=1)
    print(f"kept {len(kept)} of {len(tasks)} -> {args.out}")
    return 0


def _init():
    global DATA
    if DATA is None:
        DATA = load_enemy_data()


if __name__ == "__main__":
    sys.exit(main())
