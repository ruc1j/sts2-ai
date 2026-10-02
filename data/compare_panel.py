#!/usr/bin/env python3
"""Compare the control and arm panel traces for the 2026-10-04 measurement.

Per panel seed this reports wins/losses from the decision trace, whether the newly modeled
mechanics appear in that run, and the first decision where the two arms differ. A seed with no
occurrence of any mechanic cannot show an effect, so a +/-0 there is "unmeasurable", not "no
effect". Control artifacts live in the control worktree's data/ directory.

Usage: python3 data/compare_panel.py <arm_tag> <control_tag> [arm_dir] [control_dir] [seed ...]

With no seeds given the fixed 8-seed panel is used. Pass seeds to compare another panel, for
example the mechanism panel where the newly modeled ids actually appear in the records.
"""
import glob
import json
import sys

PANEL = "9X9WQB4QIH NFH3RMVJ6D EAIF2UUVCK 73P61QQZNU AM8C6YXHSG VTW80ZJA2G GEFYYKH1YK SWRUL944UU".split()

MECHANICS = {
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
}


def scan(tag: str, seed: str, directory: str) -> dict:
    record = {"wins": 0, "losses": 0, "fired": {}, "rows": [], "act3": None}
    for path in glob.glob(f"{directory}/data/{tag}_{seed}_result.json"):
        try:
            with open(path, encoding="utf-8-sig") as file:
                record["act3"] = json.load(file).get("act_3_complete")
        except (OSError, ValueError):
            pass
    try:
        with open(f"{directory}/data/{tag}_{seed}_agent.jsonl", encoding="utf-8-sig") as file:
            for line in file:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if entry.get("phase") == "combat_end" and "won" in entry:
                    if entry.get("won") is True:
                        record["wins"] += 1
                    elif entry.get("won") is False:
                        record["losses"] += 1
                if entry.get("phase") == "combat":
                    record["rows"].append((entry.get("seq"), entry.get("card_id"), entry.get("decision_source")))
                for key in MECHANICS:
                    if key in line:
                        record["fired"][key] = record["fired"].get(key, 0) + 1
    except OSError:
        pass
    return record


def main() -> None:
    arm_tag, control_tag = sys.argv[1], sys.argv[2]
    arm_dir = sys.argv[3] if len(sys.argv) > 3 else "."
    control_dir = sys.argv[4] if len(sys.argv) > 4 else ".wt-ctrl-e808bdf"
    seeds = sys.argv[5:] or PANEL
    arm_total = control_total = 0
    for seed in seeds:
        arm, control = scan(arm_tag, seed, arm_dir), scan(control_tag, seed, control_dir)
        arm_total += arm["wins"]
        control_total += control["wins"]
        divergence = next(
            ((a, b) for a, b in zip(arm["rows"], control["rows"]) if a[1] != b[1]),
            None,
        )
        # A run-level A/B only measures a mechanism when the mechanism is present in BOTH arms:
        # relic acquisition is path-dependent, so one arm can simply never encounter it.
        print(
            f"{seed}: control {control['wins']}W/{control['losses']}L "
            f"arm {arm['wins']}W/{arm['losses']}L "
            f"delta {arm['wins'] - control['wins']:+d} "
            f"arm_fired={dict(arm['fired']) or 'none'} control_fired={dict(control['fired']) or 'none'} "
            f"first_divergence={divergence} "
            f"act3 arm={arm['act3']} control={control['act3']}"
        )
    print(f"TOTAL control {control_total} arm {arm_total} delta {arm_total - control_total:+d}")


if __name__ == "__main__":
    main()
