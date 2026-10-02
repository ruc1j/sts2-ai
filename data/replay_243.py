#!/usr/bin/env python3
"""Replay one recorded decision against two versions of the agent.

The point is to separate "the mechanism changed the model" from "the run diverged for an
unrelated reason": the same observation, the same simulations, two code trees. `rollout_choice`
builds the Combat state internally and calls `search(state, data, simulations, seq)`, so `search`
is wrapped to capture the state it was handed; that state is then ranked with the same
simulations and seed in both trees.

Usage: python3 data/replay_243.py <record.json> <arm_dir> <control_dir>
"""
import json
import sys

RECORD = sys.argv[1]
TREES = sys.argv[2:]

with open(RECORD, encoding="utf-8-sig") as file:
    record = json.loads(file.read())

for tree in TREES:
    sys.path.insert(0, tree)
    for name in ("official_agent", "combat"):
        sys.modules.pop(name, None)
    import official_agent

    captured = {}
    original = official_agent.search

    def wrapped(state, data, simulations=5000, seed=0):
        captured.setdefault("state", state)
        captured.setdefault("seed", seed)
        return original(state, data, simulations, seed)

    official_agent.search = wrapped
    data = json.load(open(f"{tree}/data/enemies_hive.json", encoding="utf-8-sig"))
    action = official_agent.rollout_choice(record, record["legal_actions"], data, 100)
    print(f"--- {tree}")
    print("  chosen", action.get("card_id") or action.get("type"), "source", action.get("decision_source"))
    state = captured.get("state")
    if state is None:
        print("  search was not reached (heuristic fallback)")
        continue
    ranked = sorted(original(state, data, 100, captured["seed"]), key=lambda item: -item[1])
    print("  top3", [(name, round(value, 6)) for name, value in ranked[:3]])
