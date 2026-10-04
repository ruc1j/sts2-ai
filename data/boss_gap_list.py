"""Rank the remaining combat-model gaps, using only traces the current mod build could have produced.

The audit compares each recorded action against combat.py's step.  Over the whole corpus that ranking is
distorted: traces written before commit fe94c71 never carried a card's enchantment, so every play of a
Corrupted card (x1.5 damage plus 2 unblockable damage to the owner) looked like a model gap in those
traces.  Filter on the capability - does this trace's combat record carry the enchantment field - and the
list changes shape.

Usage: python3 data/boss_gap_list.py [max_groups]
"""
from __future__ import annotations

import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import combat
from model_match_audit import combat_records, merged_enemy_data, model_state, recorded_action, same_fight
from player_damage_group import trace_reports_enchantments


def main(limit: int) -> int:
    data = merged_enemy_data()
    groups: collections.Counter = collections.Counter()
    replays = mismatches = 0
    for path in sorted(Path("data").glob("*_agent.jsonl")):
        if not trace_reports_enchantments(path):
            continue
        for prev, nxt in zip(combat_records(path), combat_records(path)[1:]):
            if not same_fight(prev, nxt) or prev.get("turn") != nxt.get("turn"):
                continue
            state = model_state(prev, data)
            if state is None:
                continue
            action = recorded_action(prev, state, data)
            if action is None:
                continue
            try:
                after = combat.step(state, action, data, random.Random(prev.get("seq", 0)))
            except Exception:
                continue
            replays += 1
            boss = sorted(enemy["id"].replace("MONSTER.", "") for enemy in prev["enemies"])[0]
            card = prev.get("card_id") or "END_TURN"
            game_enemy = sum(
                max(0, enemy["hp"]) - max(0, nxt["enemies"][index]["hp"])
                for index, enemy in enumerate(prev["enemies"])
                if index < len(nxt["enemies"])
                and nxt["enemies"][index].get("combat_id") == enemy.get("combat_id")
                and nxt["enemies"][index]["id"] == enemy["id"]
            )
            model_enemy = sum(
                max(0, enemy["hp"]) - max(0, after.enemies[index].hp)
                for index, enemy in enumerate(prev["enemies"])
                if index < len(after.enemies) and after.enemies[index].model == enemy["id"]
            )
            player = nxt["player"]["hp"] - max(0, after.player_hp)
            if game_enemy != model_enemy:
                groups[(boss, "enemy_hp", card, f"game{game_enemy - model_enemy:+d}")] += 1
            if player:
                groups[(boss, "player_hp", card, f"game{player:+d}")] += 1
            if game_enemy == model_enemy and not player:
                mismatches += 1
    print(f"traces the current build could have produced: {replays} actions replayed, {mismatches} matching")
    print(f"remaining gap groups (top {limit}):")
    for key, count in groups.most_common(limit):
        print(f"   {count:5d}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 12))
