#!/usr/bin/env python3
"""Split each arm-vs-control decision diff into mechanism-only and knowledge-only.

Three variants are replayed on the same observation record:

1. control (`e808bdf`)                      -> what control actually chose
2. arm code with the card tables pinned to control shapes -> mechanism only, no knowledge difference
3. arm code with its own tables (and the generation sets pinned to control shapes) -> mechanism + knowledge

A diff counts as mechanism-only when variant 2 differs from variant 1. When variant 2 equals variant 1
but variant 3 differs from variant 1, the divergence is a card-table knowledge difference, not the
mechanism. The three variants are compared to each other, not to the recorded decision: the live process
keeps per-run module-level state, so a single-record replay does not always reproduce what the run chose
(measured: 260/280 control rollout decisions reproduce). Run this only when no game run is in flight.

Usage: python3 data/mech_vs_knowledge.py <seed> [seed ...]
"""
import glob
import json
import sys

CONTROL_DIR = ".wt-ctrl-e808bdf"
MECH_PREFIX = "mechonly"  # the pinned-generation harness runs in the main checkout
CONTROL_PREFIX = "mechpanel_ctrl"

TABLES = ("CARD_COST", "CARD_NAMES", "SKILLS", "ATTACKS", "STATUS", "CURSES", "POWERS",
          "UNTARGETED", "SELF_DAMAGE", "END_TURN", "STOKE_GENERATION", "INFERNAL_BLADE_ATTACKS")


def load_module(tree):
    for module in ("official_agent", "combat"):
        sys.modules.pop(module, None)
    sys.path.insert(0, tree)
    combat = __import__("combat")
    agent = __import__("official_agent")
    sys.path.remove(tree)
    return agent, combat


def enemy_data(record):
    for path in glob.glob("data/enemies_*.json"):
        data = json.load(open(path, encoding="utf-8-sig"))
        if all(m["id"] in {x["id"] for x in data["monsters"]} for m in record["enemies"]):
            return data
    return None


def main() -> None:
    seeds = sys.argv[1:]
    if not seeds:
        seeds = ["H2LV6ZJ4XW", "AM8C6YXHSG", "R8V2H6N4ZB", "P3V8N5K2RX"]

    control_agent, control_combat = load_module(CONTROL_DIR)
    control_tables = {name: getattr(control_combat, name, None) for name in TABLES}

    arm_agent, arm_combat = load_module(".")

    for seed in seeds:
        arm_path = f"data/{MECH_PREFIX}_{seed}_agent.jsonl"
        control_path = f"{CONTROL_DIR}/data/{CONTROL_PREFIX}_{seed}_agent.jsonl"
        arm, control = {}, {}
        for path, out in ((arm_path, arm), (control_path, control)):
            for line in open(path, encoding="utf-8-sig"):
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("phase") == "combat":
                    out[entry.get("seq")] = entry
        shared = sorted(set(arm) & set(control))
        mechanism_only = 0
        knowledge_only = 0
        reproduced = 0
        for seq in shared:
            if arm[seq].get("card_id") == control[seq].get("card_id"):
                continue
            data = enemy_data(arm[seq])
            if data is None:
                continue
            # variant 1: control
            choice_control = control_agent.rollout_choice(arm[seq], arm[seq]["legal_actions"], data, 100).get("card_id")
            if choice_control == control[seq].get("card_id"):
                reproduced += 1
            # variant 2: arm code with control-shaped tables. The generation sets stay pinned to the
            # control shapes for both variants, because the recorded arm run used the pinned harness;
            # only the card tables are varied here.
            for name, value in control_tables.items():
                if value is not None:
                    setattr(arm_combat, name, value)
            choice_mech = arm_agent.rollout_choice(arm[seq], arm[seq]["legal_actions"], data, 100).get("card_id")
            # variant 3: arm code with its own tables, generation sets pinned as in the recorded run
            arm_agent, arm_combat = load_module(".")
            for name in ("STOKE_GENERATION", "INFERNAL_BLADE_ATTACKS"):
                setattr(arm_combat, name, control_tables[name])
            choice_arm = arm_agent.rollout_choice(arm[seq], arm[seq]["legal_actions"], data, 100).get("card_id")
            if choice_mech != choice_control:
                mechanism_only += 1
            elif choice_arm != choice_control:
                knowledge_only += 1
        print(f"{seed}: diffs {sum(1 for s in shared if arm[s].get('card_id') != control[s].get('card_id'))} "
              f"mechanism-only {mechanism_only} knowledge-only {knowledge_only} "
              f"control-replay-reproduces-record {reproduced}")


if __name__ == "__main__":
    main()
