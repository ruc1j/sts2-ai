#!/usr/bin/env python3
"""Scan the decompiled relic sources for run state the BossLab cannot carry.

`SerializableRelic` can carry a relic's own props (`SavedProperties`), but the trace never shows them,
so a plan cannot say what a relic's counters/flags were at the boss entry. BossLab creates relics
fresh, which means any relic whose *combat-entry* behaviour reads such a prop fires differently in the
lab than it did in the recorded run. This script lists exactly those relics so
`.dsh/extract_act3_specs.py` can drop the specs that hold them.

Two facts came from running the Act 3 lab on 2026-10-28 (12 trials, `.dsh/act3_boss_losses.md` §7):
`RELIC.TEA_OF_DISCOURTESY` (`CombatsLeft`, `BeforeCombatStart` adds 2 `CARD.DAZED`) put two extra
cards into the draw pile in 2 trials where the recorded run had already spent it, and
`RELIC.VENERABLE_TEA_SET` (`GainEnergyInNextCombat`) accounted for an entry-energy difference in
another. Both are in the list this script generates.

Usage: python3 .dsh/scan_relic_run_state.py [--decompile DIR] [--out .dsh/relic_run_state.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

# Hooks that fire before the boss fight's first recorded decision, so their state must already match.
ENTRY_HOOKS = {
    "BeforeCombatStart", "AfterCombatStart", "AfterRoomEntered", "BeforeSideTurnStart",
    "AfterSideTurnStart", "BeforeHandDraw", "AfterHandDraw", "BeforePlayHandStart",
    "AfterEnergyReset", "DuringHandPlay", "AfterPlayerTurnStart",
}
# Kept for reference: the game APIs an entry-time hook can use to change what the first decision
# of the fight sees (cards, powers, block/energy/heal). The classification below does not need it,
# because a hook that reads run state is a problem whether or not it calls one of these.


def relic_id_of(stem: str) -> str:
    return "RELIC." + re.sub(r"(?<!^)([A-Z])", r"_\1", stem).upper().strip("_")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    default_decompile = Path(os.environ.get("TMPDIR", "/tmp")) / "sts2-ai-decompiled"
    parser.add_argument("--decompile", default=str(default_decompile))
    parser.add_argument("--out", default=str(Path(__file__).resolve().parent / "relic_run_state.json"))
    args = parser.parse_args()

    root = Path(args.decompile) / "MegaCrit.Sts2.Core.Models.Relics"
    if not root.is_dir():
        raise SystemExit(f"decompiled sources not found: {root} (run decompile_game.ps1 first)")

    flagged: dict[str, dict] = {}
    other: dict[str, dict] = {}
    for source in sorted(root.glob("*.cs")):
        text = source.read_text(encoding="utf-8", errors="replace")
        props = re.findall(
            r"\[SavedProperty\][^\n]*\n\s*(?:private|public|protected|internal)?\s*"
            r"(?:static\s*)?\w+(?:<[^>]*>)?\s+(\w+)\s*\{", text)
        if not props:
            continue
        bodies = dict(zip(re.findall(r"public override (?:async )?Task (\w+)\(", text),
                         re.split(r"public override (?:async )?Task \w+\(", text)[1:]))
        used_up = bool(re.search(r"IsUsedUp\s*=>", text))
        # The lab can only go wrong where the entry-time hook actually reads state the trace does not
        # show: its own saved prop, the used-up flag derived from it, or the run's room position.
        state_read = re.compile(
            "|".join([re.escape(name) for name in props] +
                     [r"IsUsedUp", r"CurrentRoomCount", r"CurrentActCount", r"RunState\w*\."]))
        entry_reads_state = False
        for hook, body in bodies.items():
            if hook in ENTRY_HOOKS and state_read.search(body.split("public ")[0]):
                entry_reads_state = True
                break
        record = {
            "class": source.stem,
            "saved_props": props,
            "hooks": sorted(bodies),
            "entry_behaviour": entry_reads_state,
            "has_is_used_up": used_up,
            "evidence": f"MegaCrit.Sts2.Core.Models.Relics/{source.stem}.cs",
        }
        if record["entry_behaviour"]:
            flagged[relic_id_of(source.stem)] = record
        else:
            other[relic_id_of(source.stem)] = record

    payload = {
        "entry_state_relics": flagged,
        "other_saved_prop_relics": other,
        "note": ("entry_state_relics are excluded from Act 3 plans by extract_act3_specs.py: their "
                 "entry behaviour depends on a [SavedProperty] the trace never shows, so the lab's "
                 "freshly created relic fires where the recorded run had already spent it (or stays "
                 "silent where the recorded run still had state left). other_saved_prop_relics have "
                 "run state too but no entry-time effect on the first decision; their counters, when "
                 "the trace shows them, are handled as relic_counters specs instead."),
    }
    out = Path(args.out)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {out}: entry-state relics {len(flagged)}, other saved-prop relics {len(other)}")
    for relic, info in sorted(flagged.items()):
        print(f"  {relic:32s} props={info['saved_props']} hooks={info['hooks']} used_up={info['has_is_used_up']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
