"""Audit official-run traces for model-fidelity gaps.

Two independent signals, both recommended by CLAUDE.md:

1. Cards that entered the deck but were never played during the run. A card rated
   highly for a reward pick yet never playable is usually unmodeled in combat.py
   (silently absent from legal_actions), not merely a bad pick.
2. Powers that appear on the player or an enemy in the trace but have no branch in
   combat.py, so the simulator cannot see the mechanic at all.

Run from the repository root:

    python3 data/audit_trace_fidelity.py
    python3 data/audit_trace_fidelity.py data/mechonly_arm_b3_*.jsonl
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import Counter
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _bare_literals(path: Path) -> set[str]:
    """Single-line double-quoted literals (the model names powers and cards bare)."""
    return set(re.findall(r'"([^"\\\n]+)"', path.read_text()))


def _model_power_name(trace_name: str) -> str:
    """POWER.CHAINS_OF_BINDING_POWER -> ChainsOfBindingPower (the name combat.py uses)."""
    name = trace_name.split(".", 1)[1] if "." in trace_name else trace_name
    return "".join(part.title() for part in name.split("_"))


def _pile_cards(record: dict) -> list[str]:
    cards: list[str] = []
    for key in ("hand", "draw_pile", "discard_pile", "exhaust_pile"):
        for card in record.get(key) or ():
            card_id = card.get("id") or card.get("card_id")
            if card_id:
                cards.append(card_id)
    return cards


def audit(
    paths: list[Path],
    card_names: set[str],
    card_tiers: set[str],
    combat_literals: set[str],
) -> None:
    picked: Counter[str] = Counter()
    played: Counter[str] = Counter()
    offers_of: Counter[str] = Counter()
    chosen_of: Counter[str] = Counter()
    offered_unknown: set[str] = set()
    unmodeled_picked: Counter[str] = Counter()
    powers: Counter[str] = Counter()
    power_runs: defaultdict[str, int] = defaultdict(int)
    records = 0

    for path in paths:
        deck_seen: set[str] = set()
        run_played: set[str] = set()
        run_powers: set[str] = set()
        with path.open() as handle:
            for line in handle:
                record = json.loads(line)
                if record.get("phase") != "combat":
                    if record.get("phase") == "card_reward" and record.get("card_id"):
                        picked[record["card_id"]] += 1
                        deck_seen.add(record["card_id"])
                        offered = [
                            card_id for card_id in (record.get("cards") or ())
                            if isinstance(card_id, str)
                        ]
                        for card_id in offered:
                            offers_of[card_id] += 1
                            if card_id not in card_tiers:
                                offered_unknown.add(card_id)
                        if record["card_id"] in offered_unknown:
                            chosen_of[record["card_id"]] += 1
                    continue
                records += 1
                deck_seen.update(_pile_cards(record))
                if record.get("type") == "card" and record.get("card_id"):
                    played[record["card_id"]] += 1
                    run_played.add(record["card_id"])
                entity_powers: set[str] = set()
                for power in (record.get("player") or {}).get("powers") or ():
                    entity_powers.add(power.get("id") or power.get("name"))
                for enemy in record.get("enemies") or ():
                    for power in enemy.get("powers") or ():
                        entity_powers.add(power.get("id") or power.get("name"))
                entity_powers.discard(None)
                for name in entity_powers:
                    powers[name] += 1
                run_powers |= entity_powers
        for name in run_powers:
            power_runs[name] += 1
        for card_id in deck_seen - run_played:
            unmodeled_picked[card_id] += 1

    print(f"traces: {len(paths)}  combat records: {records}")

    print("\n== deck cards never played in the run that picked them ==")
    rows = sorted(
        unmodeled_picked.items(),
        key=lambda item: (-item[1], item[0]),
    )
    for card_id, runs in rows:
        modeled = "MODELED" if card_id in card_names else "NO NAME"
        reward = picked.get(card_id, 0)
        print(f"  {card_id:44s} runs={runs:3d} reward_picks={reward:3d} {modeled}")

    print("\n== reward cards offered that have no CARD_TIERS entry ==")
    for name in sorted(offered_unknown):
        tiered = "TIERED" if name in card_tiers else "NO TIER"
        modeled = "MODELED" if name in card_names else "NO NAME"
        print(
            f"  {name:44s} offers={offers_of[name]:3d} chosen={chosen_of.get(name, 0):3d} "
            f"{tiered} {modeled}"
        )

    print("\n== powers seen in traces ==")
    for name, count in sorted(powers.items(), key=lambda item: (-item[1], item[0])):
        modeled = "COMBAT" if _model_power_name(name) in combat_literals or name in combat_literals else "MISSING"
        print(f"  {name:44s} records={count:6d} runs={power_runs[name]:3d} {modeled}")


def main() -> int:
    patterns = sys.argv[1:] or ["data/*_agent.jsonl"]
    paths: list[Path] = []
    for pattern in patterns:
        paths.extend(Path(match) for match in sorted(glob.glob(pattern)))
    if not paths:
        print("no traces matched", patterns)
        return 1
    sys.path.insert(0, str(REPO))
    import official_agent

    audit(
        paths,
        set(official_agent.CARD_NAMES),
        set(official_agent.CARD_TIERS),
        _bare_literals(REPO / "combat.py"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
