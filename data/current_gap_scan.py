#!/usr/bin/env python3
"""Find where the *current* code fails on recorded runs.

Corpus counters (decision_source in a trace) mix the code versions that produced them: a trace recorded
two months ago still reports the exceptions the code of that day raised.  This scan replays recorded
combat observations through the checked-out code instead, so what it counts is what HEAD would do today.

Each sampled record is replayed with its own legal_actions and a merged enemy export (all four acts), so
a monster whose export only exists in another act's file cannot hide behind a KeyError of our making.

Usage: python3 data/current_gap_scan.py [sample_size] [simulations]
"""
import json
import random
import sys
import traceback
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import official_agent  # noqa: E402  (repo root must be importable from data/)

DEBUFFS = ("POWER.WEAK_POWER", "POWER.VULNERABLE_POWER", "POWER.FRAIL_POWER")


def merged_enemy_data() -> dict:
    monsters: dict[str, dict] = {}
    encounters: list[dict] = []
    for path in sorted(REPO.glob("data/enemies_*.json")):
        with path.open(encoding="utf-8-sig") as handle:
            document = json.load(handle)
        for monster in document["monsters"]:
            monsters.setdefault(monster["id"], monster)
        encounters += document.get("encounters") or []
    return {"monsters": list(monsters.values()), "encounters": encounters}


def combat_records(path):
    with path.open(encoding="utf-8-sig") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if record.get("phase") != "combat":
                continue
            # The four oldest traces were recorded before the bridge emitted EnemyState.Slot; the
            # current bridge always does, so fill it in rather than reporting a gap that no live run has.
            for enemy in record.get("enemies") or ():
                enemy.setdefault("slot", "")
            yield record


def main() -> int:
    sample_size = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    simulations = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    data = merged_enemy_data()
    traces = sorted(REPO.glob("data/*_agent.jsonl"))
    rng = random.Random(0)
    sampled: list[tuple[str, dict]] = []
    for path in traces:
        records = list(combat_records(path))
        if not records:
            continue
        # Spread the sample over whole runs instead of over the first fights of every run.
        stride = max(1, len(records) // max(1, sample_size // len(traces) + 1))
        sampled += [(path.name, record) for record in records[::stride]]
    rng.shuffle(sampled)
    sampled = sampled[:sample_size]

    exceptions: Counter[str] = Counter()
    by_monster: Counter[str] = Counter()
    rejected: Counter[str] = Counter()
    shown = 0
    for name, record in sampled:
        monsters = "+".join(sorted(e["id"].replace("MONSTER.", "") for e in record.get("enemies") or ()))
        try:
            choice = official_agent.rollout_choice(record, record.get("legal_actions") or [], data, simulations)
        except Exception as error:  # noqa: BLE001 - the point of the scan is to see every failure class
            label = f"{type(error).__name__}: {error}" if isinstance(error, KeyError) else type(error).__name__
            exceptions[label] += 1
            by_monster[f"{monsters} :: {label}"] += 1
            if shown < 3:
                shown += 1
                print(f"FAIL {name} seq {record.get('seq')} turn {record.get('turn')} {monsters}")
                print("   " + "\n   ".join(traceback.format_exc().splitlines()[-5:]))
        else:
            if choice is None:
                rejected["no_choice"] += 1
                by_monster[f"{monsters} :: no_choice"] += 1
    print(f"records replayed through HEAD: {len(sampled)}  traces: {len(traces)}  simulations: {simulations}")
    print("exceptions:", dict(exceptions.most_common()))
    print("rejected rollouts:", dict(rejected.most_common()))
    print("top encounter / failure pairs:")
    for key, value in by_monster.most_common(12):
        print(f"   {value:4d}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
