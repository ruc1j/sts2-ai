#!/usr/bin/env python3
"""Replay each recorded combat action through the model and compare with what the game did next.

For every pair of consecutive combat observations (L, F) in a recorded run, this rebuilds the model's
combat state from L the same way the live rollout does (by capturing the state handed to
`official_agent.search`), applies the action the agent actually took at L through `combat.step`, and
then asks the question a fidelity check should ask: does the model's next state agree with F, the state
the game really reported?

Card plays are compared on the targeted enemy's HP (and the player's HP).  End-of-turn actions are
compared on the player's HP, which is the enemy phase - incoming damage, block, power ticks - being
simulated one turn ahead.  Anything that disagrees is a candidate gap, grouped below by card or by the
enemies that acted.

Usage: python3 data/model_match_audit.py [pair_limit]
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import combat  # noqa: E402
import official_agent  # noqa: E402

REQUIRED = {"id", "hp", "block", "powers", "move", "intents", "combat_id", "slot", "history"}
SKIPPED_MONSTERS = {"MONSTER.PAELS_LEGION", "MONSTER.BYRDPIP"}


def merged_enemy_data() -> dict:
    monsters: dict[str, dict] = {}
    for path in sorted(REPO.glob("data/enemies_*.json")):
        with path.open(encoding="utf-8-sig") as handle:
            for monster in json.load(handle)["monsters"]:
                monsters.setdefault(monster["id"], monster)
    return {"monsters": list(monsters.values()), "encounters": []}


def combat_records(path):
    records = []
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("phase") != "combat":
                continue
            if any(not REQUIRED.issubset(enemy) for enemy in record.get("enemies") or ()):
                return []
            records.append(record)
    return records


def model_state(record, data):
    """Build the Combat the live rollout would build for this observation."""
    captured = {}

    def capture(state, enemy_data, simulations, seed):
        captured["state"] = state
        return [(combat.END_TURN, 0.0)]

    with patch("official_agent.search", side_effect=capture):
        official_agent.rollout_choice(record, record.get("legal_actions") or [], data, 1)
    return captured.get("state")


def compact_target(record, target_id):
    rank = 0
    for enemy in record.get("enemies") or ():
        if enemy["id"] in SKIPPED_MONSTERS:
            continue
        if enemy["combat_id"] == target_id:
            return rank
        rank += 1
    return None


def recorded_action(record, state, data):
    """Translate the agent's recorded action into a simulator action."""
    card_id = record.get("card_id")
    if card_id is None:
        if record.get("potion_id"):
            return f"potion:{record['potion_index']}" if record.get("potion_index") is not None else None
        return combat.END_TURN
    modelled = official_agent.CARD_NAMES.get(card_id, card_id)
    index = record.get("hand_index")
    hand = getattr(state, "hand", ())
    if isinstance(index, int) and index < len(hand) and combat.card_name(hand[index]) == modelled:
        card_index = index
    else:
        card_index = next(
            (position for position, card in enumerate(hand) if combat.card_name(card) == modelled), None
        )
    if card_index is None:
        return None
    target_id = record.get("target_id")
    if target_id is None:
        return f"card:{card_index}"
    target = compact_target(record, target_id)
    return f"card:{card_index}@{target}" if target is not None else None


def same_fight(previous, following) -> bool:
    """Reject pairs that straddle a fight boundary: the next room's first observation has a fresh HP
    and a fresh combat id set, which is not the state a one-step simulation should predict."""
    before = {enemy["combat_id"] for enemy in previous.get("enemies") or ()}
    after = {enemy["combat_id"] for enemy in following.get("enemies") or ()}
    if not before or not after or not (before & after):
        return False
    previous_turn, following_turn = previous.get("turn"), following.get("turn")
    if isinstance(previous_turn, int) and isinstance(following_turn, int) and following_turn < previous_turn:
        return False
    return abs(int(following["player"]["hp"]) - int(previous["player"]["hp"])) <= 100


def main() -> int:
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    data = merged_enemy_data()
    tally = Counter()
    mismatch = Counter()
    shown = 0
    for path in sorted(REPO.glob("data/*_agent.jsonl")):
        records = combat_records(path)
        for previous, following in zip(records, records[1:]):
            if len(list(tally.elements())) >= limit:
                break
            if not same_fight(previous, following):
                tally["fight_boundary"] += 1
                continue
            action = None
            state = model_state(previous, data)
            if state is None:
                continue
            action = recorded_action(previous, state, data)
            if action is None:
                tally["no_equivalent_action"] += 1
                continue
            try:
                after = combat.step(state, action, data, random.Random(previous.get("seq", 0)))
            except Exception as error:  # noqa: BLE001 - a step that cannot run is itself the finding
                tally[f"step_raised:{type(error).__name__}"] += 1
                continue
            card_play = previous.get("card_id") is not None
            if card_play:
                target_id = previous.get("target_id")
                expected = next((e["hp"] for e in following["enemies"] if e["combat_id"] == target_id), None)
                modelled_index = compact_target(previous, target_id)
                got = after.enemies[modelled_index].hp if modelled_index is not None and modelled_index < len(after.enemies) else None
                if expected is None or got is None:
                    tally["uncomparable"] += 1
                    continue
                key = "card_enemy_hp"
            else:
                expected = following["player"]["hp"]
                got = after.player_hp
                key = "endturn_player_hp"
            tally[key + ("_match" if expected == got else "_mismatch")] += 1
            if expected != got:
                if card_play:
                    group = official_agent.CARD_NAMES.get(previous["card_id"], previous["card_id"])
                else:
                    group = "+".join(sorted(e["id"].replace("MONSTER.", "") for e in previous["enemies"] if e["id"] not in SKIPPED_MONSTERS and e["hp"] > 0))
                mismatch[(key, group)] += 1
                if shown < 6:
                    shown += 1
                    print(f"MISMATCH {key} {path.name} seq {previous.get('seq')} action {action} model={got} game={expected} ({group})")
    matched = sum(value for key, value in tally.items() if key.endswith("_match"))
    failed = sum(value for key, value in tally.items() if key.endswith("_mismatch"))
    print("tally:", dict(tally.most_common()))
    print(f"compared states: {matched + failed}  agreement: {matched} ({100 * matched / max(matched + failed, 1):.1f}%)")
    print("worst mismatch groups:")
    for key, value in mismatch.most_common(14):
        print(f"   {value:4d}  {key[0]}  {key[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
