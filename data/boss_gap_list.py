"""Rank the remaining combat-model gaps, using only traces the current mod build could have produced.

The audit compares each recorded action against combat.py's step.  Over the whole corpus that ranking is
distorted: traces written before commit fe94c71 never carried a card's enchantment, so every play of a
Corrupted card (x1.5 damage plus 2 unblockable damage to the owner) looked like a model gap in those
traces.  Filter on the capability - does this trace's combat record carry the enchantment field - and the
list changes shape.

Usage: python3 data/boss_gap_list.py [max_groups]
"""
from __future__ import annotations

import os
import collections
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import combat
import official_agent
from model_match_audit import combat_records, merged_enemy_data, model_state, recorded_action, same_fight
from player_damage_group import trace_reports_enchantments


def main(limit: int) -> int:
    data = merged_enemy_data()
    # The agent infers the play counters from the actions it chose and the piles it saw, so the audit has
    # to hand back the recorded action before the next observation or the counters the live agent had
    # (LetterOpener, Kusarigama, Shuriken, SlowPower's ramp) are not the ones being measured.
    previous_action: dict | None = None
    groups: collections.Counter = collections.Counter()
    replays = mismatches = 0
    pattern = os.environ.get("TRACE_GLOB", "*_agent.jsonl")  # TRACE_GLOB narrows the corpus, e.g. "counts_arm_*_agent.jsonl"
    for path in sorted(Path("data").glob(pattern)):
        if not trace_reports_enchantments(path):
            continue
        # Advance EVERY combat record, not only the ones we compare.  Skipping a record means skipping the
        # play the agent made at it, and the last decision of a turn is exactly the one whose next record
        # starts a new turn - so skipping turn-crossing pairs left the counters one play short every
        # turn, which is what the LetterOpener and SlowPower groups were measuring instead of the model.
        official_agent._reset_play_counters()
        previous_action = None
        records = combat_records(path)
        for index, prev in enumerate(records):
            nxt = records[index + 1] if index + 1 < len(records) else None
            comparable = (
                nxt is not None
                and same_fight(prev, nxt)
                and prev.get("turn") == nxt.get("turn")
            )
            official_agent._PENDING_ACTION = previous_action
            previous_action = None
            if prev.get("card_id"):
                previous_action = {
                    "type": "card",
                    "card_id": prev["card_id"],
                    "hand_index": prev.get("hand_index", 0),
                }
            elif prev.get("action_type") == "end_turn":
                previous_action = {"type": "end_turn"}
            if not comparable:
                official_agent._advance_play_counters(prev)
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
            # Pair enemies by combat_id, not position.  A killed monster leaves the combat entirely, so
            # the following record simply has fewer enemies; pairing by index reported its damage as 0
            # and invented whole groups of "the model dealt 5 / 14 / 22 too much".  Missing in the next
            # record means dead, and the delta is the HP it had.
            next_hp = {
                enemy.get("combat_id"): max(0, enemy["hp"])
                for enemy in nxt["enemies"]
                if enemy.get("combat_id") is not None
            }
            game_enemy = sum(
                max(0, enemy["hp"]) - next_hp.get(enemy.get("combat_id"), 0)
                for enemy in prev["enemies"]
                if enemy.get("combat_id") is not None
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
