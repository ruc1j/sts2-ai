#!/usr/bin/env python3
"""Replay one recorded decision against two versions of the agent.

The point is to separate "the mechanism changed the model" from "the run diverged for an
unrelated reason": the same observation, the same simulations, two code trees.

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
    import combat

    data = json.load(open(f"{tree}/data/enemies_hive.json", encoding="utf-8-sig"))
    state = official_agent.rollout_state(record) if hasattr(official_agent, "rollout_state") else None
    action = official_agent.rollout_choice(record, record["legal_actions"], data, 100)
    print(tree, "chosen", action.get("card_id") or action.get("type"), "source", action.get("decision_source"))
    if state is not None:
        ranked = combat.search(state, data, 100, 0)
        print(tree, "top3", [(name, round(value, 6)) for name, value in ranked[:3]])
