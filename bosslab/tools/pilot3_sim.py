#!/usr/bin/env python3
"""PILOT-3 (3): play a recorded boss entry state to the end inside combat.py.

The policy under test is `search` alone (100 simulations per decision), so the
result is a model-internal measurement - not evidence about the real game.
Each fight starts from the Combat state the live agent saw on the turn it
entered the fight, which is rebuilt through the same `rollout_choice` state
construction the live agent used.

    python3 bosslab/tools/pilot3_sim.py build --out /tmp/entries.json
    python3 bosslab/tools/pilot3_sim.py run --root <checkout> --entries /tmp/entries.json \
        --out /tmp/sim_main.json
"""
from __future__ import annotations

import argparse
import glob
import json
import multiprocessing as mp
import os
import random
import statistics
import sys

MAIN = "/Users/mao/workspace/sts2-ai"
HERE = os.path.dirname(os.path.abspath(__file__))
ENEMY_FILES = ("enemies_overgrowth.json", "enemies_hive.json", "enemies_glory.json")
DATA = None
ROOT = None


def _load_data(root):
    monsters = []
    for name in ENEMY_FILES:
        with open(os.path.join(root, "data", name), encoding="utf-8-sig") as f:
            monsters.extend(json.load(f)["monsters"])
    return {"monsters": monsters}


def _init(root):
    global ROOT, DATA
    ROOT = root
    sys.path.insert(0, root)
    DATA = _load_data(root)


def build_entries(limit_queen=59, limit_insatiable=30):
    entries = []
    for tag in ("astra_ctrl_v23", "astra_ctrl_v24"):
        for path in sorted(glob.glob(os.path.join(MAIN, "data", f"{tag}_*_agent.jsonl"))):
            rows = []
            with open(path, encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.strip():
                        rows.append(json.loads(line))
            current = None
            for i, row in enumerate(rows):
                if row.get("phase") != "combat":
                    if row.get("phase") == "combat_end":
                        current = None
                    continue
                ids = {str(e.get("id", "")) for e in row.get("enemies") or ()}
                kind = ("QUEEN" if any(x.endswith(".QUEEN") for x in ids)
                        else "INSATIABLE" if any("INSATIABLE" in x for x in ids) else None)
                if kind is None:
                    current = None
                    continue
                if current != kind:
                    if kind == "QUEEN" and sum(1 for e in entries if e["kind"] == "QUEEN") < limit_queen:
                        entries.append({"kind": kind, "seed": os.path.basename(path), "obs": row})
                    elif kind == "INSATIABLE" and sum(1 for e in entries if e["kind"] == "INSATIABLE") < limit_insatiable:
                        entries.append({"kind": kind, "seed": os.path.basename(path), "obs": row})
                    current = kind
    return entries


def play(obs, rng):
    import official_agent as OA
    import combat as C
    captured = {}

    def fake_search(combat, data, simulations=0, seed=0):
        captured.setdefault("combat", combat)
        return [(C.END_TURN, 0.0)]

    original = OA.search
    OA.search = fake_search
    try:
        OA.rollout_choice(obs, obs.get("legal_actions") or [], DATA, 100)
    finally:
        OA.search = original
    state = captured.get("combat")
    if state is None:
        return None
    specs = {monster["id"]: monster for monster in DATA["monsters"]}
    entry_hp = {e.model: e.hp for e in state.enemies}
    decisions = 0
    while decisions < 200:
        if state.player_hp <= 0:
            break
        primaries = [e for e in state.enemies if e.primary]
        if primaries and all(not e.alive for e in primaries):
            break
        if state.terminal:
            break
        ranked = C.search(state, DATA, 100, decisions)
        action = ranked[0][0]
        state = C.step(state, action, DATA, rng)
        decisions += 1
    # Queen-only shave against the exported maximum HP (EVALUATION.md's metric)
    final = {e.model: max(0, e.hp) for e in state.enemies}
    queen = next((e for e in state.enemies if e.model.endswith(".QUEEN")), None)
    primary_models = [e.model for e in state.enemies if e.primary]
    won = bool(primary_models) and all(
        not e.alive for e in state.enemies if e.primary
    ) and state.player_hp > 0
    result = {
        "won": won,
        "turns": state.turn,
        "decisions": decisions,
        "player_hp": state.player_hp,
    }
    if queen is not None or any(m.endswith(".QUEEN") for m in entry_hp):
        model = next(m for m in entry_hp if m.endswith(".QUEEN"))
        values = (specs.get(model) or {}).get("values") or {}
        max_hp = values.get("MaxInitialHp") or values.get("MinInitialHp") or entry_hp[model]
        final_hp = final.get(model, 0)
        result["queen_shave"] = max(0.0, min(1.0, 1.0 - final_hp / max_hp))
        result["queen_max_hp"] = max_hp
    if any("INSATIABLE" in m for m in entry_hp):
        model = next(m for m in entry_hp if "INSATIABLE" in m)
        values = (specs.get(model) or {}).get("values") or {}
        max_hp = values.get("MaxInitialHp") or values.get("MinInitialHp") or entry_hp[model]
        result["enemy_shave"] = max(0.0, min(1.0, 1.0 - final.get(model, 0) / max_hp))
    return result


def _run(task):
    try:
        return play(task["obs"], random.Random(task["offset"]))
    except Exception as exc:  # noqa: BLE001 - report, do not hide
        return {"error": type(exc).__name__}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--out", required=True)
    run = sub.add_parser("run")
    run.add_argument("--root", required=True)
    run.add_argument("--entries", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--offsets", type=int, default=2)
    run.add_argument("--workers", type=int, default=3)
    args = ap.parse_args(argv)

    if args.command == "build":
        entries = build_entries()
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(entries, f)
        print(f"{len(entries)} entries -> {args.out}")
        return 0

    with open(args.entries, encoding="utf-8") as f:
        entries = json.load(f)
    tasks = [{"obs": e["obs"], "offset": off, "kind": e["kind"], "seed": e["seed"]}
             for e in entries for off in range(args.offsets)]
    with mp.Pool(args.workers, initializer=_init, initargs=(args.root,)) as pool:
        results = pool.map(_run, tasks, chunksize=1)
    for task, result in zip(tasks, results):
        if result:
            result["kind"] = task["kind"]
            result["seed"] = task["seed"]
            result["offset"] = task["offset"]
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1)
    errors = sum(1 for r in results if r and "error" in r)
    print(f"{len(results)} fights, {errors} errors -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
