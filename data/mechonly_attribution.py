#!/usr/bin/env python3
"""Split the mechanisms-only batch's decision diffs by which mechanism is present in BOTH arms.

The generation sets are pinned to the control shapes in `data/mechonly_agent.py`, so a divergence in a
harness run can only come from the mechanism implementations. A diff counts for a mechanism only when that
mechanism is in the observed state at the same decision in both arms; positions where the mechanism is
present in one arm only are path luck and cannot be attributed.

Usage: python3 data/mechonly_attribution.py [seed ...]
"""
import json
import os
import sys
import collections

CONTROL_DIR = ".wt-ctrl-e808bdf"
MECHANICS = [
    "POWER.DUPLICATION_POWER",
    "POWER.GIGANTIFICATION_POWER",
    "POWER.PANACHE_POWER",
    "POWER.ONE_TWO_PUNCH_POWER",
    "POWER.CHAINS_OF_BINDING_POWER",
    "CARD.WITHER",
    "CARD.PANACHE",
    "CARD.ONE_TWO_PUNCH",
    "RELIC.FIDDLE",
    "RELIC.BLOOD_SOAKED_ROSE",
    "RELIC.FORGOTTEN_SOUL",
]

# Mechanisms whose trigger condition is the card being in hand at the end of the turn.
HAND_PRESENCE_MECHANICS = {"CARD.WITHER"}


def combat_records(path):
    out = {}
    for line in open(path, encoding="utf-8-sig"):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("phase") == "combat":
            out[entry.get("seq")] = entry
    return out


def present(record):
    # Only the power or relic in the observed state is the mechanism. A card name in hand is table
    # knowledge, not the mechanism: the arm knows the card's cost/damage/type while control did not, and
    # that difference can flip a ranking without the power ever being active. Exceptions are the
    # hand-at-turn-end statuses (Wither), whose condition is the card being in hand.
    player = record.get("player") or {}
    ids = set(player.get("relics") or []) | {power["id"] for power in (player.get("powers") or [])}
    ids |= {card.get("id") for card in (record.get("hand") or []) if card.get("id") in HAND_PRESENCE_MECHANICS}
    return {key for key in MECHANICS if key in ids}


def main() -> None:
    args = list(sys.argv[1:])
    arm_tag = "mechonly"
    control_tag = "mechpanel_ctrl"
    control_dir = CONTROL_DIR
    seeds = []
    index = 0
    while index < len(args):
        if args[index] == "--arm-tag":
            arm_tag = args[index + 1]
            index += 2
        elif args[index] == "--ctrl-tag":
            control_tag = args[index + 1]
            index += 2
        elif args[index] == "--ctrl-dir":
            control_dir = args[index + 1]
            index += 2
        else:
            seeds.append(args[index])
            index += 1
    if not seeds:
        seeds = [
            "H2LV6ZJ4XW", "AM8C6YXHSG", "R8V2H6N4ZB", "P3V8N5K2RX",
            "N8CQ4ZKP2W", "D1W9Y3B7FC", "B3N8V5T1WQ", "Q6N3V8K2MT",
        ]
    for seed in seeds:
        arm_path = f"data/{arm_tag}_{seed}_agent.jsonl"
        if not os.path.exists(arm_path):
            print(f"{seed}: arm run not started yet")
            continue
        arm = combat_records(arm_path)
        control = combat_records(f"{control_dir}/data/{control_tag}_{seed}_agent.jsonl")
        shared = sorted(set(arm) & set(control))
        if not shared:
            print(f"{seed}: no aligned combat records")
            continue
        diffs = [seq for seq in shared if arm[seq].get("card_id") != control[seq].get("card_id")]
        by_mechanism = collections.Counter()
        none = 0
        for seq in diffs:
            both = present(arm[seq]) & present(control[seq])
            if not both:
                none += 1
            for key in both:
                by_mechanism[key] += 1
        arm_exc = sum(1 for entry in arm.values() if entry.get("decision_source") == "agent_exception_fallback")
        ctrl_exc = sum(
            1 for entry in control.values() if entry.get("decision_source") == "agent_exception_fallback"
        )
        print(
            f"{seed}: aligned {len(shared)} diffs {len(diffs)} "
            f"by-mechanism {dict(by_mechanism.most_common())} no-mechanism {none} "
            f"exceptions arm {arm_exc} control {ctrl_exc}"
        )


if __name__ == "__main__":
    main()
