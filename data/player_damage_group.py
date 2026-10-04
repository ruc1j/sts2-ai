"""Count card plays where the recorded game and combat.py disagree about the player's own HP.

The boss-fight audits keep showing a group where playing an Attack costs the player HP that combat.py
does not charge (CARD.FEED, CARD.STRIKE_IRONCLAD, CARD.CASCADE ...).  Measuring it over the whole corpus
is misleading: the corpus contains traces written by older builds of the mod, and some card state the
current bridge exports (card enchantments, for instance) was simply absent from those traces, so the
model could not have known it.  Restricting the same measurement to the traces of the last two days
dropped the group from 551 cases to 50, which is the number worth chasing.

Usage: python3 data/player_damage_group.py [days]
"""
from __future__ import annotations

import collections
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import combat
from model_match_audit import combat_records, model_state, recorded_action, same_fight

ENEMY_DATA = Path("/tmp/sts2-ai-enemies-merged.json")


def trace_reports_enchantments(path: Path) -> bool:
    """True when this trace's combat records carry the card `enchantment` field."""
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if '"hand"' not in line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if record.get("phase") != "combat":
            continue
        hand = record.get("hand")
        if isinstance(hand, list) and any(isinstance(card, dict) and "enchantment" in card for card in hand):
            return True
    return False


def main(days: int) -> int:
    data = json.loads(ENEMY_DATA.read_text(encoding="utf-8-sig"))
    cutoff = time.time() - days * 86400
    by_card: collections.Counter = collections.Counter()
    by_monster: collections.Counter = collections.Counter()
    by_power: collections.Counter = collections.Counter()
    seeds: set[str] = set()
    total = 0
    for path in sorted(Path("data").glob("*_agent.jsonl")):
        if path.stat().st_mtime < cutoff:
            continue
        # A date is only a proxy.  What matters is whether the build that wrote this trace exported card
        # enchantments at all: commit fe94c71 added them to the trace's hand records, and before it the
        # agent genuinely could not see that a card carries Corrupted (x1.5 damage plus 2 unblockable
        # damage to the owner on play), which showed up as a phantom discrepancy on every play of an
        # enchanted card.  Only traces that carry the field can be attributed to the model.
        if not trace_reports_enchantments(path):
            continue
        seed = path.name[: -len("_agent.jsonl")].rsplit("_", 1)[-1]
        if len(seed) != 10:
            continue
        for prev, nxt in zip(combat_records(path), combat_records(path)[1:]):
            card_id = prev.get("card_id")
            if not card_id or not same_fight(prev, nxt):
                continue
            # Only transitions inside one turn: a card play whose next record is a new turn would fold the
            # enemy's whole turn into the comparison.
            if prev.get("turn") != nxt.get("turn"):
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
            delta = nxt["player"]["hp"] - max(0, after.player_hp)
            if not delta:
                continue
            total += 1
            seeds.add(seed)
            by_card[(card_id.replace("CARD.", ""), delta)] += 1
            by_monster[(tuple(sorted(e["id"].replace("MONSTER.", "") for e in prev["enemies"])), delta)] += 1
            by_power[(tuple(sorted(q["id"].replace("POWER.", "") for q in prev["player"]["powers"])), delta)] += 1
    print(f"traces from the last {days} day(s): {total} card plays where the player HP delta disagrees")
    print(f"seeds: {len(seeds)}")
    for label, tally in (("by card", by_card), ("by monster set", by_monster), ("by player powers", by_power)):
        print(label + ":")
        for key, count in tally.most_common(8):
            print(f"   {count:5d}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 2))
