"""Count how many recorded decisions a power fidelity fix actually changes.

The gap this measures: a power that the live observation reports but combat.py never reads, so the
rollout prices the rest of the fight without the mechanic (RampartPower re-grants 25 block to every
living TurretOperator at each player-turn start; StockPower respawns an Axebot with StockAmount-1).

This replays every recorded decision whose state carried that power through two code trees - the
commit that added the behaviour and its parent - with the same record, the same enemy data, the same
simulations and the same seed, and reports how many choices differ, grouped by seed.  The two trees
must differ by that commit only, otherwise a difference cannot be attributed to the fix.

It measures the population a fix is live on.  It is not evidence about run outcomes - that needs a
real run (`data/rampart_ab.sh` shows the panel form).

Usage: python3 data/attribution_rampart.py [arm_dir] [control_dir] [POWER.X] [enemy_data.json]
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

CHILD = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import official_agent

paths, enemy_data, power_id = sys.argv[2], sys.argv[3], sys.argv[4]
data = json.load(open(enemy_data, encoding="utf-8-sig"))
out = []
for line in open(paths, encoding="utf-8-sig"):
    record = json.loads(line)
    if record.get("phase") != "combat":
        continue
    if not any(
        power.get("id") == power_id
        for enemy in record.get("enemies") or ()
        for power in enemy.get("powers") or ()
    ):
        continue
    actions = record.get("legal_actions") or []
    if not actions:
        continue
    try:
        choice = official_agent.rollout_choice(record, actions, data, 100)
    except Exception as error:  # noqa: BLE001 - report the shape, never guess
        out.append({"seq": record.get("seq"), "error": type(error).__name__})
        continue
    out.append({
        "seq": record.get("seq"),
        "chosen": choice.get("card_id") or choice.get("type") or choice.get("option_id"),
        "source": choice.get("decision_source"),
    })
json.dump(out, sys.stdout)
'''


def main() -> int:
    trees = [
        Path(argument).resolve()
        for argument in (sys.argv[1:3] or [REPO, REPO / ".wt-ctrl-d67896f"])
    ]
    power_id = sys.argv[3] if len(sys.argv) > 3 else "POWER.RAMPART_POWER"
    enemy_data = Path(sys.argv[4]) if len(sys.argv) > 4 else REPO / "data/enemies_glory.json"
    token = power_id.encode()
    traces = sorted(REPO.glob("data/*_agent.jsonl"))
    rows: dict[tuple[str, int], dict[str, dict]] = {}
    for tree in trees:
        # One subprocess per trace so the (trace, seq) key stays unique.
        for trace in traces:
            if token not in trace.read_bytes():
                continue
            payload = subprocess.run(
                [sys.executable, "-c", CHILD, str(tree), str(trace), str(enemy_data), power_id],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            for entry in json.loads(payload):
                rows.setdefault((trace.name, entry["seq"]), {})[str(tree)] = entry

    diffs = Counter()
    per_seed = Counter()
    detail: list[tuple[str, int, str, str]] = []
    errors: Counter[str] = Counter()
    for (trace, seq), by_tree in sorted(rows.items()):
        values = [entry.get("chosen") for entry in by_tree.values()]
        for entry in by_tree.values():
            if entry.get("error"):
                errors[entry["error"]] += 1
        if len(set(values)) > 1:
            diffs["changed"] += 1
            # Trace names are "<label>_<SEED>_agent.jsonl"; the seed is the last segment.
            per_seed[trace[: -len("_agent.jsonl")].rsplit("_", 1)[-1]] += 1
            detail.append((trace, seq, str(values[0]), str(values[-1])))
        else:
            diffs["same"] += 1
    print(f"power: {power_id}  records compared: {len(rows)}  trees: {len(trees)}")
    print(f"decision changed: {diffs['changed']}  unchanged: {diffs['same']}  errors: {dict(errors)}")
    print(f"seeds with a changed decision: {len(per_seed)}")
    for seed, count in per_seed.most_common():
        print(f"  {seed}: {count}")
    for trace, seq, arm, control in detail[:25]:
        print(f"  {trace} seq {seq}: arm={arm} control={control}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
