#!/usr/bin/env python3
"""Look for enemy-phase damage that the recorded intents cannot explain.

For every player turn in a recorded fight, the enemy side acts between the last decision of turn N and
the first decision of turn N+1.  The intents shown at that last decision are the damage the game is
displaying, i.e. already inclusive of enemy Strength and player Vulnerable, so the player's HP drop
across the enemy phase cannot exceed their total - block only reduces it.  A drop above that total means
some damage source is missing from the observation, and the grouping below names the monsters involved.

Self-damage is excluded: cards and status cards that cost or burn the player's own HP are listed in
SELF_DAMAGE, and a turn where the player played one of them is skipped.

Usage: python3 data/damage_source_scan.py
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SELF_DAMAGE = {
    "CARD.BLOODLETTING_IRONCLAD", "CARD.OFFERING_IRONCLAD", "CARD.HEMOKINESIS_IRONCLAD",
    "CARD.RECKLESS_CHARGE_IRONCLAD", "CARD.BLOOD_WALL_IRONCLAD", "CARD.SECOND_WIND_IRONCLAD",
    "POTION.BLOOD_POTION",
}
# Card ids as the observation spells them (CARD.BURN, not CARD.BURN_STATUS).  Skipping a turn whose hand
# holds one of these keeps the status-card turn-end burn out of the measurement.
STATUS_IN_HAND = {
    "CARD.TOXIC", "CARD.BURN", "CARD.INFECTION", "CARD.DECAY", "CARD.WITHER", "CARD.SLIMED",
    "CARD.DAZED", "CARD.WOUND", "CARD.FRANTIC_ESCAPE",
}
# Player-side powers whose own hooks cost the player HP at the end of their turn (modeled in
# combat.py); their amount comes out of the observed drop before comparing to the intents.
SELF_DAMAGE_POWERS = ("ConstrictPower",)


def fights(path):
    current = []
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("phase") == "combat":
                current.append(record)
            elif current:
                yield current
                current = []
    if current:
        yield current


def intent_total(record) -> int:
    total = 0
    for enemy in record.get("enemies") or ():
        if enemy.get("hp", 0) <= 0:
            continue
        for intent in enemy.get("intents") or ():
            damage = int(intent.get("damage") or 0)
            if damage <= 0:
                continue
            total += damage * max(1, int(intent.get("repeats") or 1))
    return total


def main() -> int:
    flagged = Counter()
    gaps = defaultdict(list)
    turns = 0
    for path in sorted(REPO.glob("data/*_agent.jsonl")):
        for fight in fights(path):
            by_turn: dict[int, list] = defaultdict(list)
            for record in fight:
                turn = record.get("turn")
                if isinstance(turn, int) and (record.get("player") or {}).get("hp") is not None:
                    by_turn[turn].append(record)
            for turn in sorted(by_turn):
                last = by_turn[turn][-1]
                following = by_turn.get(turn + 1)
                if not following:
                    continue
                first = following[0]
                if (last.get("card_id") in SELF_DAMAGE) or (last.get("potion_id") in SELF_DAMAGE):
                    continue
                hand_names = {card.get("id") for card in (last.get("hand") or ())}
                if hand_names & STATUS_IN_HAND:
                    continue
                expected = intent_total(last)
                own = sum(
                    power.get("amount", 0)
                    for power in (last.get("player") or {}).get("powers") or ()
                    if power.get("id", "").replace("POWER.", "") in SELF_DAMAGE_POWERS
                )
                drop = int(last["player"]["hp"]) - int(first["player"]["hp"]) - own
                if drop <= 0:
                    continue
                turns += 1
                if drop > expected:
                    monsters = "+".join(sorted(e["id"].replace("MONSTER.", "") for e in last.get("enemies") or () if e.get("hp", 0) > 0))
                    flagged[monsters] += 1
                    gaps[monsters].append((path.name, last.get("seq"), turn, expected, drop))
    print(f"player turns measured: {turns}")
    print("turns where the HP drop exceeded the displayed intent total:")
    for monsters, count in flagged.most_common(12):
        worst = max(gaps[monsters], key=lambda row: row[4] - row[3])
        print(f"   {count:4d}  {monsters}   worst gap {worst[4] - worst[3]} (expected {worst[3]} -> lost {worst[4]})  {worst[0]} seq {worst[1]} turn {worst[2]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
