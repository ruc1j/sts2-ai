"""Measure how many reward decisions a CARD_TIERS entry would move.

`CARD_TIERS` is the reward ranking table.  35 cards that combat.py can play (`CARD_NAMES`) have no
entry there, so at reward time they score `priority.get(card_id, 0)` == 0 and
`CARD_TIERS.get(card_id, "D")` == tier D, which drops them into the deck>=15 Skip path.  In the
decision traces the most-offered of them (Purity 22 offers, Dramatic Entrance 9, Production 8) were
never taken once.

The decision trace only stores the card ids an offer contained, not the live observation the policy
saw, so this replays the paired `<label>_<SEED>_observations.jsonl` records instead: same seq, same
`cards` / `legal_actions` / `player.deck`.  The "replay reproduces the recorded pick" line reports how
faithful that replay is; if it is low, the flip counts below are measured against a baseline the run
itself did not use.

Nothing here changes policy code, and it is not adoption evidence - it says whether the gap is live.

Usage: python3 data/reward_tier_probe.py [CARD.X ...]
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import official_agent  # noqa: E402

# Cards combat.py models, CARD_TIERS does not rank, and real runs actually offered.
DEFAULT_CANDIDATES = ["CARD.PURITY", "CARD.DRAMATIC_ENTRANCE", "CARD.PRODUCTION", "CARD.FASTEN"]
TIER_TO_TRY = (sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in {"S", "A", "B", "C", "D"} else "B")
CANDIDATES_ARG = [argument for argument in sys.argv[1:] if argument.startswith("CARD.")]


def pick(action: dict) -> str:
    return action.get("card_id") or action.get("option_id") or action.get("type") or ""


def records() -> list[tuple[str, int, dict, str]]:
    """(seed, seq, observation, recorded pick) for every reward observation paired with its trace."""
    rows: list[tuple[str, int, dict, str]] = []
    for path in sorted(REPO.glob("data/*_observations.jsonl")):
        stem = path.name[: -len("_observations.jsonl")]
        seed = stem.rsplit("_", 1)[-1]
        trace = next(
            (candidate for candidate in (path.with_name(f"{stem}_agent.jsonl"), path.with_name(f"{stem}_trace.jsonl"))
             if candidate.exists()),
            None,
        )
        if trace is None:
            continue
        recorded: dict[int, str] = {}
        for line in trace.read_text(encoding="utf-8-sig").splitlines():
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if entry.get("phase") == "card_reward":
                recorded[entry.get("seq")] = pick(entry)
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            try:
                observation = json.loads(line)
            except ValueError:
                continue
            if observation.get("phase") != "card_reward" or not observation.get("legal_actions"):
                continue
            seq = observation.get("seq")
            if seq not in recorded:
                continue
            rows.append((seed, seq, observation, recorded[seq]))
    return rows


def main() -> int:
    candidates = CANDIDATES_ARG or DEFAULT_CANDIDATES
    rows = records()
    agree = 0
    for _seed, _seq, observation, recorded in rows:
        try:
            agree += pick(official_agent.choose_card_reward(observation)) == recorded
        except Exception:  # noqa: BLE001 - compare against the recorded pick, never guess
            continue
    print(f"reward observations paired with a trace: {len(rows)}")
    print(f"HEAD replay reproduces the recorded pick: {agree}/{len(rows)}")

    original = dict(official_agent.CARD_TIERS)
    for card_id in candidates:
        offered = [
            entry for entry in rows
            if any(card.get("id") == card_id for card in entry[2].get("cards") or ())
        ]
        taken = sum(1 for entry in offered if entry[3] == card_id)
        flips: collections.Counter[str] = collections.Counter()
        seeds: collections.Counter[str] = collections.Counter()
        for seed, _seq, observation, recorded in offered:
            try:
                baseline = pick(official_agent.choose_card_reward(observation))
            except Exception:  # noqa: BLE001
                continue
            official_agent.CARD_TIERS = {**original, card_id: TIER_TO_TRY}
            try:
                with_tier = pick(official_agent.choose_card_reward(observation))
            except Exception:  # noqa: BLE001
                with_tier = None
            official_agent.CARD_TIERS = original
            if with_tier == baseline:
                continue
            if with_tier == card_id:
                flips[f"-> take {card_id}"] += 1
            elif baseline == card_id:
                flips[f"take {card_id} -> other"] += 1
            else:
                flips["different other card"] += 1
            seeds[seed] += 1
        print(
            f"{card_id:26s} offered={len(offered):3d} recorded_pick={taken:2d} "
            f"flips_with_tier_{TIER_TO_TRY}={dict(flips) or '{}'} seeds={len(seeds)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
