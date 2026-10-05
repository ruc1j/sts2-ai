#!/usr/bin/env python3
"""Inspect raw control and arm panel traces; see docs/EVALUATION.md for acceptance.

Per panel seed this reports wins/losses from the decision trace, whether the newly modeled
mechanics appear in that run, and the first paired combat row with a different card id.
Presence is not activation or causal evidence. All planned seeds belong in the overall comparison,
including seeds without the target mechanic. Control artifacts live in the control worktree.
Totals are raw combat wins, not run wins; completion and artifact validity need separate review.

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
    "POWER.RAMPART_POWER",
    "POWER.STOCK_POWER",
    "POWER.PLATING_POWER",
    "POWER.WEAK_POWER",
    "POWER.VULNERABLE_POWER",
    "POWER.FRAIL_POWER",
    "POWER.SWIPE_POWER",
    "POWER.REATTACH_POWER",
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
                # This is a text presence hint, not proof that the effect activated.
                # Exclude card_reward lines that merely list offered cards.
                if entry.get("phase") == "combat":
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
    shared_seeds = shared_arm = shared_control = 0
    print("RAW DIAGNOSTICS ONLY: combat wins are not run wins. "
          "Review completion, manifests and logs using docs/EVALUATION.md before acceptance.")
    for seed in seeds:
        arm, control = scan(arm_tag, seed, arm_dir), scan(control_tag, seed, control_dir)
        arm_total += arm["wins"]
        control_total += control["wins"]
        divergence = next(
            ((a, b) for a, b in zip(arm["rows"], control["rows"]) if a[1] != b[1]),
            None,
        )
        # Shared presence helps locate replay candidates; it does not establish causal attribution.
        # Keep one-sided acquisition and absent mechanics in the full panel comparison.
        shared = sorted(set(arm["fired"]) & set(control["fired"]))
        if shared:
            shared_seeds += 1
            shared_arm += arm["wins"]
            shared_control += control["wins"]
        print(
            f"{seed}: combats control {control['wins']}W/{control['losses']}L "
            f"arm {arm['wins']}W/{arm['losses']}L "
            f"delta {arm['wins'] - control['wins']:+d} "
            f"pair={shared or 'none'} "
            f"arm_present={dict(arm['fired']) or 'none'} control_present={dict(control['fired']) or 'none'} "
            f"first_card_id_difference={divergence} "
            f"raw_act3_result arm={arm['act3']} control={control['act3']}"
        )
    print(f"RAW COMBAT WINS control {control_total} arm {arm_total} delta {arm_total - control_total:+d}")
    print(f"SHARED PRESENCE (not activation or an acceptance subset) {shared_seeds} seeds: "
          f"combat wins control {shared_control} arm {shared_arm} delta {shared_arm - shared_control:+d}")


if __name__ == "__main__":
    main()
