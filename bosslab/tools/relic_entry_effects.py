"""Relics whose own entry-time effect the recorded entry already contains, and how BossLab handles it.

The lab builds a run and then jumps into the boss room with ``RunManager.EnterRoomDebug``. Room entry
fires the injected relics' entry hooks. For most relics that is exactly what we want: the recorded
run's entry observation was produced by the same hooks, so letting them fire reproduces the entry
(Strength from Vajra, Plating from Gorget, Vigor from Akabeko). For three families it double-applies a
change that the recorded deck / HP / potion list already contains, and the divergence shows up in the
fidelity check:

``defer_relic_addition``
    The relic permanently changed the deck at room entry, and the hook also consumes draw-card RNG.
    BossLab attaches these after room entry so the hook never fires (RELIC.STONE_CRACKER upgrades two
    random upgradable draw cards at ``AfterRoomEntered``, StoneCracker.cs:20-28).
``reapply_recorded_hp``
    The relic heals (or otherwise moves HP) at entry. BossLab re-asserts the recorded HP after room
    entry (RELIC.PANTOGRAPH heals at boss combat start, Pantograph.cs:27-32; RELIC.PLANISPHERE heals on
    entering an Unknown map point, Planisphere.cs:23-31).
``widen_potion_slots``
    The relic raises the potion slot count in ``AfterObtained``, which silent addition skips, so the
    extra potions in the recorded entry used to be dropped by the 3-slot cap. BossLab widens the slots
    to the recorded potion list instead (RELIC.POTION_BELT, PotionBelt.cs:19-21; RELIC.PHIAL_HOLSTER,
    PhialHolster.cs:26-28; RELIC.ALCHEMICAL_COFFER, AlchemicalCoffer.cs:20-23).
``flag_unfixed``
    The relic adds cards to the opening hand at the first turn's start or draw. The recorded run's own
    fight did the same, so the lab must keep the relic firing early, but which card the game's RNG
    produces (and where the draw puts it) need not match the recorded run, and an entry observation
    taken before that hook predates the card entirely. Nothing here fixes it, so the plan generator
    carries these as ``flag_relics`` and analyze_bosslab.py marks the spec with a dagger.

Not listed here, because they need no handling: relics that only grant a power at entry (they reproduce
by design, and the plan generator already subtracts them from the residual power injection), and relics
whose permanent deck change happens in ``AfterObtained`` (RELIC.POMANDER, Pomander.cs:17-22, and
RELIC.YUMMY_COOKIE, YummyCookie.cs:70-75 upgrade cards there; silent addition never runs that hook, so
the deck stays exactly as the plan loaded it).

Usage::

    python3 bosslab/tools/relic_entry_effects.py            # print the table
    python3 bosslab/tools/relic_entry_effects.py --check     # re-derive it from the decompile

The check mode compares the table against the decompiled sources and fails when a listed relic's
evidence lines no longer mention the hook or the command it names, or when a relic that belongs to one
of the families here is missing from it. It is the guard for a game update, not part of the test suite,
because it needs ``pwsh -File ./decompile_game.ps1`` to have run.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# relic id -> (handling, hook that must not re-fire, the command it calls, evidence file:lines)
ENTRY_EFFECTS: dict[str, dict[str, str]] = {
    "RELIC.STONE_CRACKER": {
        "handling": "defer_relic_addition",
        "hook": "AfterRoomEntered",
        "calls": "CardCmd.Upgrade",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/StoneCracker.cs:20-28",
        "why": "upgrades 2 random upgradable draw cards on entering the boss room and shuffles the "
               "draw pile first, so re-firing it in the lab upgrades different cards and shifts the "
               "opening hand",
    },
    "RELIC.PANTOGRAPH": {
        "handling": "reapply_recorded_hp",
        "hook": "BeforeCombatStart",
        "calls": "CreatureCmd.Heal",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/Pantograph.cs:27-32",
        "why": "heals its HealVar 25 when the room is the boss room; the recorded entry HP is already "
               "the healed value",
    },
    "RELIC.PLANISPHERE": {
        "handling": "reapply_recorded_hp",
        "hook": "AfterRoomEntered",
        "calls": "CreatureCmd.Heal",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/Planisphere.cs:23-31",
        "why": "heals when the room entered has no map point behind it, which the padded boss entry "
               "looks like",
    },
    "RELIC.MEAL_TICKET": {
        "handling": "reapply_recorded_hp",
        "hook": "AfterRoomEntered",
        "calls": "CreatureCmd.Heal",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/MealTicket.cs:22-27",
        "why": "merchant-room-only heal; harmless in a boss entry but the same class of change, so it "
               "is covered by the HP re-assert",
    },
    "RELIC.ETERNAL_FEATHER": {
        "handling": "reapply_recorded_hp",
        "hook": "AfterRoomEntered",
        "calls": "CreatureCmd.Heal",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/EternalFeather.cs:24-31",
        "why": "rest-site heal; same reason as MealTicket",
    },
    "RELIC.POTION_BELT": {
        "handling": "widen_potion_slots",
        "hook": "AfterObtained",
        "calls": "PlayerCmd.GainMaxPotionCount",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/PotionBelt.cs:19-21",
        "why": "the extra slot exists in the recorded entry but silent relic addition never runs "
               "AfterObtained, so the belt's own gain is missing",
    },
    "RELIC.PHIAL_HOLSTER": {
        "handling": "widen_potion_slots",
        "hook": "AfterObtained",
        "calls": "PlayerCmd.GainMaxPotionCount",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/PhialHolster.cs:26-28",
        "why": "same shape as Potion Belt (PotionSlots var 1), and it also procured 2 potions at "
               "pickup, which the recorded potion list already shows",
    },
    "RELIC.ALCHEMICAL_COFFER": {
        "handling": "widen_potion_slots",
        "hook": "AfterObtained",
        "calls": "PlayerCmd.GainMaxPotionCount",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/AlchemicalCoffer.cs:20-23",
        "why": "same shape as Potion Belt",
    },
    "RELIC.CROSSBOW": {
        "handling": "flag_unfixed",
        "hook": "AfterSideTurnStart",
        "calls": "CardPileCmd.AddGeneratedCardsToCombat",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/Crossbow.cs:17-36",
        "why": "adds a random unlocked Attack card to the hand at the first turn's start; the card the "
               "lab's RNG picks need not be the recorded run's, and an entry observation taken before "
               "the hook lists no card at all",
    },
    "RELIC.TOOLBOX": {
        "handling": "flag_unfixed",
        "hook": "BeforeHandDraw",
        "calls": "CardPileCmd",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/Toolbox.cs:22-31",
        "why": "generates colorless cards into the combat before the first draw",
    },
    "RELIC.BIG_HAT": {
        "handling": "flag_unfixed",
        "hook": "AfterSideTurnStart",
        "calls": "CardPileCmd",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/BigHat.cs:23-35",
        "why": "adds an Ethereal card to the opening hand",
    },
    "RELIC.ORANGE_DOUGH": {
        "handling": "flag_unfixed",
        "hook": "AfterSideTurnStart",
        "calls": "CardPileCmd",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/OrangeDough.cs:21-28",
        "why": "adds colorless cards to the opening hand",
    },
    "RELIC.POWER_CELL": {
        "handling": "flag_unfixed",
        "hook": "BeforeSideTurnStart",
        "calls": "CardPileCmd.Add",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/PowerCell.cs:21-30",
        "why": "shuffles the draw pile and adds chosen zero-cost cards to the opening hand on turn 1, "
               "consuming draw RNG the recorded run spent in the same place only if the pile order "
               "already matched",
    },
    "RELIC.BLESSED_ANTLER": {
        "handling": "flag_unfixed",
        "hook": "BeforeHandDraw",
        "calls": "CardPileCmd",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/BlessedAntler.cs:45-55",
        "why": "adds Dazed cards to the hand on turn 1",
    },
    "RELIC.FUNERARY_MASK": {
        "handling": "flag_unfixed",
        "hook": "BeforeHandDraw",
        "calls": "CardPileCmd",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/FuneraryMask.cs:23-31",
        "why": "adds Soul cards to the hand on turn 1",
    },
    "RELIC.JEWELED_MASK": {
        "handling": "flag_unfixed",
        "hook": "BeforeHandDraw",
        "calls": "CardPileCmd.Add",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/JeweledMask.cs:17-26",
        "why": "picks a random Power card out of the draw pile with the combat card RNG and adds it to "
               "the opening hand free of cost",
    },
    "RELIC.RADIANT_PEARL": {
        "handling": "flag_unfixed",
        "hook": "BeforeHandDraw",
        "calls": "CardPileCmd",
        "evidence": "MegaCrit.Sts2.Core.Models.Relics/RadiantPearl.cs:32-41",
        "why": "adds Luminesce cards to the hand on turn 1",
    },

}

HANDLINGS = ("defer_relic_addition", "reapply_recorded_hp", "widen_potion_slots", "flag_unfixed")

RELICS_DIR = "MegaCrit.Sts2.Core.Models.Relics"

# Relics whose own run state the trace never shows (RELIC.FUR_COAT, RELIC.TEA_OF_DISCOURTESY,
# RELIC.BONE_TEA and the other 11 in entry_state_relics.json) are dropped from plans by the spec
# extractor before this table matters, so they are not listed above.


def relic_id_of_class(stem: str) -> str:
    return "RELIC." + re.sub(r"(?<!^)([A-Z])", r"_\1", stem).upper().strip("_")


def handling_for(relic_id: str) -> dict | None:
    """The handling record for a relic id, accepting the bare ``STONE_CRACKER`` form too."""
    key = relic_id.upper()
    if not key.startswith("RELIC."):
        key = "RELIC." + key
    return ENTRY_EFFECTS.get(key)


def defer_relics_for(relics) -> list[str]:
    """Relic ids from the list that BossLab must attach only after room entry."""
    return [relic for relic in relics
            if (handling_for(str(relic)) or {}).get("handling") == "defer_relic_addition"]


def flag_relics_for(relics) -> list[str]:
    """Relic ids from the list that stay unfixed in the lab, for the dagger marking."""
    return [relic for relic in relics
            if (handling_for(str(relic)) or {}).get("handling") == "flag_unfixed"]


def by_handling(handling: str) -> dict[str, dict]:
    return {relic: meta for relic, meta in ENTRY_EFFECTS.items() if meta["handling"] == handling}


def _hook_body(text: str, hook: str) -> str | None:
    match = re.search(r"public override (?:async )?Task %s\([^)]*\)[^\n]*\n(.*?)\n\t\}" % re.escape(hook),
                      text, re.S)
    return match.group(0) if match else None


ADD_CARD_CALLS = ("AddGenerated", "CardPileCmd.Add", "AddToCombatAndPreview", "PreviewCardPileAdd")
ENTRY_ROOM_HOOKS = ("AfterRoomEntered", "BeforeCombatStart")
FIRST_TURN_HOOKS = ("AfterSideTurnStart", "BeforeSideTurnStart", "BeforeHandDraw")


def _source_for_class(root: Path, relic: str) -> Path | None:
    """Find the decompiled file for a relic id (the game names classes `StoneCracker`, the ids use
    `STONE_CRACKER`, so compare with underscores dropped and case folded)."""
    wanted = relic[len("RELIC."):].replace("_", "").lower()
    for source in sorted(root.glob("*.cs")):
        if source.stem.replace("_", "").lower() == wanted:
            return source
    return None


def _adds_cards(body: str) -> bool:
    return any(call in body for call in ADD_CARD_CALLS)


def expected_handling(source: Path) -> tuple[str, str] | None:
    """(handling, hook) this relic's decompiled source implies, or None when nothing here needs
    handling. Relics carrying a [SavedProperty] are excluded from plans upstream (their run state is
    invisible in the trace), so they are not this table's business."""
    text = source.read_text(encoding="utf-8", errors="replace")
    if "[SavedProperty]" in text:
        return None
    for hook in ENTRY_ROOM_HOOKS + FIRST_TURN_HOOKS + ("AfterObtained",):
        body = _hook_body(text, hook)
        if not body:
            continue
        if "PlayerCmd.GainMaxPotionCount" in body:
            return ("widen_potion_slots", hook)
        if hook in ENTRY_ROOM_HOOKS and "CardCmd.Upgrade" in body:
            return ("defer_relic_addition", hook)
        if hook in ENTRY_ROOM_HOOKS and "CreatureCmd.Heal" in body:
            return ("reapply_recorded_hp", hook)
        if hook in FIRST_TURN_HOOKS and (_adds_cards(body) or "CardCmd.Upgrade" in body):
            return ("flag_unfixed", hook)
    return None


def check_against_decompile(decompile: Path) -> list[str]:
    """Problems found by re-deriving the table from the decompiled sources: missing evidence, changed
    bodies, and relics that belong to a family here but are absent from the table."""
    problems: list[str] = []
    root = decompile / RELICS_DIR
    if not root.is_dir():
        return [f"decompiled sources not found: {root} (run decompile_game.ps1 first)"]
    for relic, meta in sorted(ENTRY_EFFECTS.items()):
        source = _source_for_class(root, relic)
        if source is None:
            problems.append(f"{relic}: no decompiled source for this relic id")
            continue
        text = source.read_text(encoding="utf-8", errors="replace")
        body = _hook_body(text, meta["hook"])
        if body is None:
            problems.append(f"{relic}: hook {meta['hook']} not found in {source.stem}.cs")
            continue
        if meta["calls"] not in body:
            problems.append(f"{relic}: {meta['hook']} no longer calls {meta['calls']} "
                            f"({source.stem}.cs)")
        derived = expected_handling(source)
        if derived is None or derived[0] != meta["handling"]:
            problems.append(f"{relic}: table says {meta['handling']} but the source now implies "
                            f"{derived[0] if derived else None} ({source.stem}.cs)")
    for source in sorted(root.glob("*.cs")):
        derived = expected_handling(source)
        if derived is None:
            continue
        relic = relic_id_of_class(source.stem)
        if relic not in ENTRY_EFFECTS:
            problems.append(f"unlisted relic: {relic} is {derived[0]} via {derived[1]} "
                            f"({source.stem}.cs)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="re-derive the table from the decompiled sources and report drift")
    parser.add_argument("--decompile", default=str(Path(os.environ.get("TMPDIR", "/tmp")) /
                                                   "sts2-ai-decompiled"))
    parser.add_argument("--json", action="store_true", help="print the table as JSON")
    args = parser.parse_args()

    if args.check:
        problems = check_against_decompile(Path(args.decompile))
        for problem in problems:
            print(f"DRIFT: {problem}")
        if problems:
            return 1
        print(f"ok: {len(ENTRY_EFFECTS)} relics classified, decompile evidence matches")
        return 0

    if args.json:
        print(json.dumps(ENTRY_EFFECTS, ensure_ascii=False, indent=1, sort_keys=True))
        return 0

    for handling in HANDLINGS:
        group = by_handling(handling)
        print(f"{handling} ({len(group)}):")
        for relic, meta in sorted(group.items()):
            print(f"  {relic}  [{meta['hook']} -> {meta['calls']}] {meta['evidence']}")
            print(f"      {meta['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
