from __future__ import annotations

import argparse
import json
import os
import random
import time
import traceback
from dataclasses import replace

from combat import Combat, Enemy, _resolve_move, search


CARD_NAMES = {
    "CARD.STRIKE_IRONCLAD": "Strike",
    "CARD.DEFEND_IRONCLAD": "Defend",
    "CARD.BASH": "Bash",
    "CARD.ANGER": "Anger",
    "CARD.BLUDGEON": "Bludgeon",
    "CARD.STOMP": "Stomp",
    "CARD.SHRUG_IT_OFF": "Shrug It Off",
    "CARD.BATTLE_TRANCE": "Battle Trance",
    "CARD.BULLY": "Bully",
    "CARD.DISMANTLE": "Dismantle",
    "CARD.SLIMED": "Slimed",
    "CARD.TOXIC": "Toxic",
    "CARD.BURN": "Burn",
    "CARD.DAZED": "Dazed",
    "CARD.INFECTION": "Infection",
    "CARD.FRANTIC_ESCAPE": "Frantic Escape",
    "CARD.IRON_WAVE": "Iron Wave",
    "CARD.TWIN_STRIKE": "Twin Strike",
    "CARD.CINDER": "Cinder",
    "CARD.ASHEN_STRIKE": "Ashen Strike",
    "CARD.HEMOKINESIS": "Hemokinesis",
    "CARD.PERFECTED_STRIKE": "Perfected Strike",
    "CARD.INFLAME": "Inflame",
    "CARD.PRIMAL_FORCE": "Primal Force",
    "CARD.UNRELENTING": "Unrelenting",
    "CARD.GIANT_ROCK": "Giant Rock",
    "CARD.RELAX": "Relax",
    "CARD.TREMBLE": "Tremble",
    "CARD.BREAKTHROUGH": "Breakthrough",
    "CARD.WHIRLWIND": "Whirlwind",
    "CARD.BLOODLETTING": "Bloodletting",
    "CARD.FEED": "Feed",
    "CARD.DOMINATE": "Dominate",
    "CARD.BYRD_SWOOP": "Byrd Swoop",
    "CARD.PILLAGE": "Pillage",
    "CARD.EQUILIBRIUM": "Equilibrium",
    "CARD.BREAK": "Break",
    "CARD.HOWL_FROM_BEYOND": "Howl From Beyond",
    "CARD.IMPERVIOUS": "Impervious",
    "CARD.RAMPAGE": "Rampage",
    "CARD.TAUNT": "Taunt",
    "CARD.THUNDERCLAP": "Thunderclap",
    "CARD.BOLAS": "Bolas",
    "CARD.DRAMATIC_ENTRANCE": "Dramatic Entrance",
    "CARD.FISTICUFFS": "Fisticuffs",
    "CARD.LIFT": "Lift",
    "CARD.THRUMMING_HATCHET": "Thrumming Hatchet",
    "CARD.ULTIMATE_DEFEND": "Ultimate Defend",
    "CARD.ULTIMATE_STRIKE": "Ultimate Strike",
    "CARD.FLAME_BARRIER": "Flame Barrier",
    "CARD.MOLTEN_FIST": "Molten Fist",
    "CARD.NOT_YET": "Not Yet",
    "CARD.OFFERING": "Offering",
    "CARD.PACTS_END": "Pacts End",
    "CARD.POMMEL_STRIKE": "Pommel Strike",
    "CARD.DRUM_OF_BATTLE": "Drum of Battle",
    "CARD.MASTER_OF_STRATEGY": "Master of Strategy",
    "CARD.PRODUCTION": "Production",
    "CARD.IMPATIENCE": "Impatience",
    "CARD.MIND_BLAST": "Mind Blast",
    "CARD.BODY_SLAM": "Body Slam",
    "CARD.BELIEVE_IN_YOU": "Believe in You",
    "CARD.FINESSE": "Finesse",
    "CARD.STONE_ARMOR": "Stone Armor",
    "CARD.FEEL_NO_PAIN": "Feel No Pain",
    "CARD.RUPTURE": "Rupture",
    "CARD.SECOND_WIND": "Second Wind",
    "CARD.ENLIGHTENMENT": "Enlightenment",
    "CARD.HEADBUTT": "Headbutt",
    "CARD.UPPERCUT": "Uppercut",
    "CARD.TRUE_GRIT": "True Grit",
    "CARD.BURNING_PACT": "Burning Pact",
    "CARD.FIEND_FIRE": "Fiend Fire",
    "CARD.INFERNAL_BLADE": "Infernal Blade",
    "CARD.MANGLE": "Mangle",
    "CARD.PECK": "Peck",
    "CARD.EXTERMINATE": "Exterminate",
    "CARD.SETUP_STRIKE": "Setup Strike",
    "CARD.EVIL_EYE": "Evil Eye",
    "CARD.BRAND": "Brand",
    "CARD.RAGE": "Rage",
    "CARD.SPITE": "Spite",
    "CARD.COLOSSUS": "Colossus",
    "CARD.VOLLEY": "Volley",
    "CARD.DISINTEGRATION": "Disintegration",
    "CARD.MIND_ROT": "Mind Rot",
    "CARD.BARRICADE": "Barricade",
    "CARD.PYRE": "Pyre",
    "CARD.ARMAMENTS": "Armaments",
}

CARD_TIERS = {
    **dict.fromkeys({
        "CARD.CRIMSON_MANTLE", "CARD.DARK_EMBRACE", "CARD.DOMINATE", "CARD.FIEND_FIRE",
        "CARD.IMPERVIOUS", "CARD.OFFERING", "CARD.PACTS_END", "CARD.PRIMAL_FORCE",
        "CARD.UNMOVABLE", "CARD.BATTLE_TRANCE", "CARD.BLOODLETTING", "CARD.BURNING_PACT",
        "CARD.COLOSSUS", "CARD.CRUELTY", "CARD.INFERNO", "CARD.UPPERCUT",
        "CARD.POMMEL_STRIKE", "CARD.TREMBLE",
    }, "S"),
    **dict.fromkeys({
        "CARD.CORRUPTION", "CARD.FEED", "CARD.PYRE", "CARD.STOKE", "CARD.BLUDGEON",
        "CARD.EXPECT_A_FIGHT", "CARD.FEEL_NO_PAIN", "CARD.FLAME_BARRIER", "CARD.HEMOKINESIS",
        "CARD.RAGE", "CARD.SECOND_WIND", "CARD.ANGER", "CARD.BLOOD_WALL", "CARD.HEADBUTT",
        "CARD.SHRUG_IT_OFF", "CARD.TAUNT",
    }, "A"),
    **dict.fromkeys({
        "CARD.BREAK", "CARD.AGGRESSION", "CARD.TEAR_ASUNDER", "CARD.THRASH",
        "CARD.ASHEN_STRIKE", "CARD.DISMANTLE", "CARD.EVIL_EYE", "CARD.FORGOTTEN_RITUAL", "CARD.MANGLE",
        "CARD.SPITE", "CARD.STOMP", "CARD.UNRELENTING", "CARD.WHIRLWIND", "CARD.BREAKTHROUGH", "CARD.PECK", "CARD.EXTERMINATE",
        "CARD.EQUILIBRIUM", "CARD.ULTIMATE_DEFEND", "CARD.ULTIMATE_STRIKE",
        "CARD.CINDER", "CARD.IRON_WAVE", "CARD.TWIN_STRIKE", "CARD.VOLLEY",
        "CARD.INFLAME",  # Strength scales every attack: boss firepower (was C)
    }, "B"),
    **dict.fromkeys({
        "CARD.BRAND", "CARD.CASCADE", "CARD.DEMON_FORM", "CARD.HELLRAISER", "CARD.BULLY",
        "CARD.DRUM_OF_BATTLE", "CARD.FIGHT_ME", "CARD.HOWL_FROM_BEYOND", "CARD.INFERNAL_BLADE",
        "CARD.JUGGLING", "CARD.PILLAGE", "CARD.RAMPAGE", "CARD.RUPTURE",
        "CARD.STAMPEDE", "CARD.STONE_ARMOR", "CARD.VICIOUS", "CARD.ARMAMENTS", "CARD.BODY_SLAM",
        "CARD.HAVOC", "CARD.MOLTEN_FIST", "CARD.PERFECTED_STRIKE", "CARD.SETUP_STRIKE",
        "CARD.SWORD_BOOMERANG", "CARD.THUNDERCLAP", "CARD.TRUE_GRIT", "CARD.FISTICUFFS", "CARD.IMPATIENCE", "CARD.MIND_BLAST",
    }, "C"),
    **dict.fromkeys({
        "CARD.BARRICADE", "CARD.CONFLAGRATION", "CARD.JUGGERNAUT", "CARD.MANGLE", "CARD.ONE_TWO_PUNCH",
        "CARD.BASH", "CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD", "CARD.SLIMED", "CARD.FRANTIC_ESCAPE",
        "CARD.NOT_YET", "CARD.MIDNIGHT", "CARD.TANK", "CARD.BLAZE", "CARD.DEMONIC_SHIELD", "CARD.OUTRAGE",
        "CARD.BYRD_SWOOP",
    }, "D"),
}

VULNERABLE_CORE = (
    "CARD.TREMBLE", "CARD.TAUNT", "CARD.THUNDERCLAP", "CARD.UPPERCUT",
    "CARD.MOLTEN_FIST", "CARD.BULLY", "CARD.DISMANTLE", "CARD.BREAK",
)
EXHAUST_CORE = (
    "CARD.TRUE_GRIT", "CARD.BURNING_PACT", "CARD.CORRUPTION", "CARD.FEEL_NO_PAIN", "CARD.DARK_EMBRACE",
)
VULNERABLE_APPLY = VULNERABLE_CORE[:4]
VULNERABLE_PAYOFF = VULNERABLE_CORE[4:]
EXHAUST_ENABLERS = EXHAUST_CORE[:2]
EXHAUST_PAYOFF = EXHAUST_CORE[2:]
UNCOMMITTED_SELF_DAMAGE = {
    "CARD.BLOODLETTING", "CARD.HEMOKINESIS", "CARD.BRAND", "CARD.BREAKTHROUGH",
    "CARD.BLOOD_WALL", "CARD.INFERNO", "CARD.OFFERING",
}
UNCOMMITTED_EXHAUST_PAYOFF = {"CARD.FEEL_NO_PAIN", "CARD.DARK_EMBRACE"}
POWER_NAMES = {
    "POWER.FRAIL": "FrailPower",
    "POWER.SLIPPERY_POWER": "SlipperyPower",
    "POWER.STRENGTH": "StrengthPower",
    "POWER.STRENGTH_POWER": "StrengthPower",
    "POWER.VULNERABLE": "VulnerablePower",
    "POWER.VULNERABLE_POWER": "VulnerablePower",
    "POWER.WEAK": "WeakPower",
    "POWER.WEAK_POWER": "WeakPower",
    "POWER.HARD_TO_KILL_POWER": "HardToKillPower",
    "POWER.ARTIFACT_POWER": "ArtifactPower",
    "POWER.BACK_ATTACK_LEFT_POWER": "BackAttackLeftPower",
    "POWER.BACK_ATTACK_RIGHT_POWER": "BackAttackRightPower",
    "POWER.CRAB_RAGE_POWER": "CrabRagePower",
    "POWER.FLUTTER_POWER": "FlutterPower",
    "POWER.SURROUNDED_POWER": "SurroundedPower",
    "POWER.ILLUSION_POWER": "IllusionPower",
    "POWER.MINION_POWER": "MinionPower",
    "POWER.PERSONAL_HIVE_POWER": "PersonalHivePower",
    "POWER.PLOW_POWER": "PlowPower",
    "POWER.RINGING_POWER": "RingingPower",
    "POWER.SANDPIT_POWER": "SandpitPower",
    "POWER.SHRINK_POWER": "ShrinkPower",
    "POWER.SLOW_POWER": "SlowPower",
    "POWER.SLUMBER_POWER": "SlumberPower",
    "POWER.DEXTERITY": "DexterityPower",
    "POWER.DEXTERITY_POWER": "DexterityPower",
    "POWER.SELF_FORMING_CLAY_POWER": "SelfFormingClayPower",
    "POWER.RUPTURE_POWER": "RupturePower",
    "POWER.TAINTED_POWER": "TaintedPower",
    "POWER.CONSTRICT_POWER": "ConstrictPower",
    "POWER.FLAME_BARRIER_POWER": "FlameBarrierPower",
    "POWER.REPTILE_TRINKET_POWER": "ReptileTrinketPower",
    "POWER.PLATING_POWER": "PlatingPower",
    "POWER.FEEL_NO_PAIN_POWER": "FeelNoPainPower",
    "POWER.DISINTEGRATION_POWER": "DisintegrationPower",
    "POWER.MIND_ROT_POWER": "MindRotPower",
    "POWER.MANGLE_POWER": "ManglePower",
    "POWER.SETUP_STRIKE_POWER": "SetupStrikePower",
    "POWER.THORNS_POWER": "ThornsPower",
    "POWER.VITAL_SPARK_POWER": "VitalSparkPower",
    "POWER.RAGE_POWER": "RagePower",
    "POWER.ADAPTABLE_POWER": "AdaptablePower",
    "POWER.ENRAGE_POWER": "EnragePower",
    "POWER.PAINFUL_STABS_POWER": "PainfulStabsPower",
    "POWER.NEMESIS_POWER": "NemesisPower",
    "POWER.BUFFER_POWER": "BufferPower",
}

KNOWN_CARD_DAMAGE = {
    "CARD.STRIKE_IRONCLAD": 6,
    "CARD.BASH": 8,
    "CARD.ANGER": 6,
    "CARD.BLUDGEON": 32,
    "CARD.STOMP": 12,
    "CARD.DISMANTLE": 8,
    "CARD.IRON_WAVE": 5,
    "CARD.TWIN_STRIKE": 10,
    "CARD.CINDER": 18,
    "CARD.HEMOKINESIS": 15,
    "CARD.UNRELENTING": 14,
    "CARD.GIANT_ROCK": 16,
    "CARD.BREAKTHROUGH": 9,
    "CARD.FEED": 10,
    "CARD.BYRD_SWOOP": 14,
    "CARD.PILLAGE": 6,
    "CARD.HEADBUTT": 9,
    "CARD.UPPERCUT": 13,
    "CARD.FIEND_FIRE": 7,
    "CARD.SPITE": 5,
    "CARD.VOLLEY": 10,
    "CARD.MANGLE": 15,
    "CARD.PECK": 6,
    "CARD.EXTERMINATE": 12,
    "CARD.SETUP_STRIKE": 7,
}
# Dynamic damage cards still need to count as attacks when a reward also offers a strong block.
ATTACK_REWARD_CARDS = set(KNOWN_CARD_DAMAGE) | {"CARD.ASHEN_STRIKE", "CARD.PERFECTED_STRIKE"}
KNOWN_CARD_BLOCK = {
    "CARD.DEFEND_IRONCLAD": 5,
    "CARD.SHRUG_IT_OFF": 8,
    "CARD.RELAX": 15,
    "CARD.IRON_WAVE": 5,
    "CARD.EQUILIBRIUM": 13,
    "CARD.TAUNT": 7,
    "CARD.TRUE_GRIT": 7,
    "CARD.EVIL_EYE": 8,
    "CARD.COLOSSUS": 5,
}


def _number(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _intent_incoming(enemy: dict) -> int:
    # CombatBridge reports intent damage via GetSingleDamage, which already includes
    # Strength/Weak/Vulnerable, so the observed damage is used as-is.
    return sum(max(0, _number(intent.get("damage"))) * max(1, _number(intent.get("repeats"), 1)) for intent in enemy.get("intents") or ())


_LAST_POTION_CONTEXT: tuple[object, ...] | None = None


def _potion_context(observation: dict) -> tuple[object, ...] | None:
    run = observation.get("run")
    turn = observation.get("turn")
    enemies = tuple((enemy.get("combat_id"), enemy.get("id")) for enemy in observation.get("enemies", ()))
    if not isinstance(run, dict) or run.get("act") is None or run.get("floor") is None or turn is None or not enemies:
        return None
    return (run["act"], run["floor"], turn, enemies)


def _potion_is_lethal_incoming(observation: dict) -> bool:
    hp = _number((observation.get("player") or {}).get("hp"))
    return sum(_intent_incoming(enemy) for enemy in observation.get("enemies", ())) >= hp


def _card_value(action: dict, hand: dict[int, dict], metric: str) -> int:
    card_id = action.get("card_id")
    card = hand.get(action.get("hand_index"), {})
    values = []
    calculated = []
    for variable in card.get("vars") or ():
        name = str(variable.get("id", "")).lower()
        if metric not in name:
            continue
        value = _number(variable.get("value"))
        (calculated if "calculated" in name else values).append(value)
    if calculated:
        return max(calculated)
    if values:
        return max(values)
    return (KNOWN_CARD_DAMAGE if metric == "damage" else KNOWN_CARD_BLOCK).get(card_id, 0)


def _is_self_damage(action: dict, hand: dict[int, dict]) -> bool:
    card = hand.get(action.get("hand_index"), {})
    if action.get("card_id") in UNCOMMITTED_SELF_DAMAGE or card.get("id") in UNCOMMITTED_SELF_DAMAGE:
        return True
    return any(
        any(marker in str(variable.get("id", "")).lower().replace("_", "") for marker in ("selfdamage", "hploss", "healthloss"))
        for variable in card.get("vars") or ()
    )


# Relic choices from Ancient events (e.g. PAEL at Act 2 start). Scores are tuned to the
# Ironclad deck: energy, draw, upgrades, and block are worth more; relics that bloat the
# deck with unplayable cards (PaelsHorn adds 2 Relax) are never taken.
RELIC_SCORES = {
    # PAEL
    "RELIC.PAELS_FLESH": 9,  # +1 max energy
    "RELIC.PAELS_BLOOD": 8,  # draw +1
    "RELIC.PAELS_LEGION": 7,  # block pet every combat
    "RELIC.PAELS_GROWTH": 6,  # Clone enchant on one card
    "RELIC.PAELS_CLAW": 5,  # Goopy enchant on eligible cards
    "RELIC.PAELS_TEARS": 5,  # energy refunds
    "RELIC.PAELS_EYE": 4,  # exhaust synergy
    "RELIC.PAELS_WING": 4,  # sacrifice card reward alternative
    "RELIC.PAELS_TOOTH": 4,  # removes upgradable cards
    "RELIC.PAELS_HORN": -10,  # adds 2 Relax to the deck: never take
    # OROBAS
    "RELIC.SAND_CASTLE": 8,  # upgrades 6 cards
    "RELIC.PRISMATIC_GEM": 8,  # +1 max energy
    "RELIC.GLASS_EYE": 7,  # choose 1 of 5 card rewards
    "RELIC.ALCHEMICAL_COFFER": 6,  # potion slot + potions
    "RELIC.RADIANT_PEARL": 5,  # turn-1 Luminesce
    "RELIC.DRIFTWOOD": 5,  # reroll card rewards
    "RELIC.ELECTRIC_SHRYMP": 5,  # Imbued enchant
    # TEZCATARA
    "RELIC.VERY_HOT_COCOA": 7,  # turn-1 energy burst
    "RELIC.YUMMY_COOKIE": 7,  # upgrades cards
    "RELIC.TOASTY_MITTENS": 7,  # draw + strength
    "RELIC.PUMPKIN_CANDLE": 7,  # periodic +1 energy
    "RELIC.GOLDEN_COMPASS": 6,  # golden path
    "RELIC.NUTRITIOUS_SOUP": 5,  # enchant Strike cards
    "RELIC.SEAL_OF_GOLD": 5,  # gold -> energy
    "RELIC.STORYBOOK": 5,  # Brightest Flame
    "RELIC.TOY_BOX": 5,  # periodic relics
    "RELIC.BIIIG_HUG": 4,  # removes cards
}

# Only buy shop relics whose value is known for this agent's modeled Ironclad effects. Unknown
# relics stay out of the shop policy until their effect is implemented and evaluated.
SHOP_RELIC_SCORES = {
    "RELIC.CLOAK_CLASP": 9,
    "RELIC.KUNAI": 8,
    "RELIC.SHURIKEN": 8,
    "RELIC.CENTENNIAL_PUZZLE": 8,
    "RELIC.ART_OF_WAR": 7,
    "RELIC.CAPTAINS_WHEEL": 7,
    "RELIC.HORN_CLEAT": 7,
    "RELIC.MERCURY_HOURGLASS": 7,
    "RELIC.HAPPY_FLOWER": 7,
    "RELIC.ORNAMENTAL_FAN": 6,
    "RELIC.KUSARIGAMA": 6,
    "RELIC.SCREAMING_FLAGON": 6,
    "RELIC.SPARKLING_ROUGE": 6,
    "RELIC.BRIMSTONE": 6,
    "RELIC.DEMON_TONGUE": 6,
    "RELIC.PENDULUM": 6,
    # Newly modeled combat relics.  Scores are the general-purpose baseline; axis bonuses
    # below raise a matching relic by one tier so a coherent deck gets first pick.
    "RELIC.POCKETWATCH": 8,
    "RELIC.MUMMIFIED_HAND": 8,
    "RELIC.CHARONS_ASHES": 7,
    "RELIC.SELF_FORMING_CLAY": 7,
    "RELIC.TUNGSTEN_ROD": 7,
    "RELIC.LIZARD_TAIL": 7,
    "RELIC.BURNING_STICKS": 6,
    "RELIC.GAME_PIECE": 6,
    "RELIC.PERMAFROST": 6,
    "RELIC.ORICHALCUM": 6,
    "RELIC.PARRYING_SHIELD": 6,
    "RELIC.PEN_NIB": 6,
    "RELIC.RED_SKULL": 6,
    "RELIC.BEATING_REMNANT": 6,
    "RELIC.JOSS_PAPER": 6,
    "RELIC.RIPPLE_BASIN": 6,
    "RELIC.VAMBRACE": 6,
    "RELIC.INTIMIDATING_HELMET": 6,
    "RELIC.CHEMICAL_X": 5,
    "RELIC.BELT_BUCKLE": 5,
    "RELIC.RAZOR_TOOTH": 5,
    "RELIC.STURDY_CLAMP": 5,
    "RELIC.BELLOWS": 5,
    "RELIC.CHANDELIER": 5,
    "RELIC.RUINED_HELMET": 5,
    "RELIC.UNSETTLING_LAMP": 5,
}

# Acquisition tiers are separate from card tiers because relic value is conditional on the
# deck's axis.  The matching sets are deliberately small: an unlisted relic keeps its general
# score instead of being guessed into a synergetic build.
RELIC_TIERS_BY_AXIS = {
    "general": {"S": {"RELIC.CLOAK_CLASP", "RELIC.KUNAI", "RELIC.SHURIKEN", "RELIC.CENTENNIAL_PUZZLE", "RELIC.POCKETWATCH", "RELIC.MUMMIFIED_HAND"},
                 "A": {"RELIC.ART_OF_WAR", "RELIC.CAPTAINS_WHEEL", "RELIC.HORN_CLEAT", "RELIC.MERCURY_HOURGLASS", "RELIC.HAPPY_FLOWER", "RELIC.LIZARD_TAIL", "RELIC.TUNGSTEN_ROD", "RELIC.SELF_FORMING_CLAY", "RELIC.CHARONS_ASHES"}},
    "strike": {"S": {"RELIC.KUNAI", "RELIC.SHURIKEN", "RELIC.PEN_NIB", "RELIC.ORNAMENTAL_FAN"},
                "A": {"RELIC.KUSARIGAMA", "RELIC.POCKETWATCH", "RELIC.MUMMIFIED_HAND", "RELIC.ART_OF_WAR"}},
    "self_damage": {"S": {"RELIC.RED_SKULL", "RELIC.DEMON_TONGUE", "RELIC.TUNGSTEN_ROD"},
                    "A": {"RELIC.BEATING_REMNANT", "RELIC.CENTENNIAL_PUZZLE", "RELIC.LIZARD_TAIL", "RELIC.SELF_FORMING_CLAY"}},
    "vulnerable": {"S": {"RELIC.SCREAMING_FLAGON", "RELIC.MERCURY_HOURGLASS", "RELIC.SPARKLING_ROUGE"},
                   "A": {"RELIC.PEN_NIB", "RELIC.POCKETWATCH", "RELIC.CLOAK_CLASP", "RELIC.CHARONS_ASHES"}},
    "exhaust": {"S": {"RELIC.CHARONS_ASHES", "RELIC.BURNING_STICKS", "RELIC.JOSS_PAPER"},
                "A": {"RELIC.PERMAFROST", "RELIC.GAME_PIECE", "RELIC.MUMMIFIED_HAND", "RELIC.SELF_FORMING_CLAY"}},
    "strength": {"S": {"RELIC.SPARKLING_ROUGE", "RELIC.BRIMSTONE", "RELIC.POCKETWATCH"},
                  "A": {"RELIC.HAPPY_FLOWER", "RELIC.MERCURY_HOURGLASS", "RELIC.MUMMIFIED_HAND", "RELIC.CLOAK_CLASP"}},
}
EVENT_RELIC_TIERS_BY_AXIS = {
    "general": {"S": {"RELIC.PAELS_FLESH", "RELIC.PAELS_BLOOD", "RELIC.PRISMATIC_GEM", "RELIC.SAND_CASTLE"},
                 "A": {"RELIC.PAELS_LEGION", "RELIC.GLASS_EYE", "RELIC.TOASTY_MITTENS", "RELIC.VERY_HOT_COCOA"}},
    "strike": {"S": {"RELIC.YUMMY_COOKIE", "RELIC.PAELS_FLESH", "RELIC.SAND_CASTLE"},
                "A": {"RELIC.PAELS_BLOOD", "RELIC.PUMPKIN_CANDLE", "RELIC.GLASS_EYE"}},
    "self_damage": {"S": {"RELIC.PAELS_FLESH", "RELIC.PAELS_TEARS", "RELIC.TOASTY_MITTENS"},
                    "A": {"RELIC.PAELS_BLOOD", "RELIC.PAELS_LEGION", "RELIC.VERY_HOT_COCOA"}},
    "vulnerable": {"S": {"RELIC.PAELS_FLESH", "RELIC.PAELS_LEGION", "RELIC.VERY_HOT_COCOA"},
                   "A": {"RELIC.PAELS_BLOOD", "RELIC.TOASTY_MITTENS", "RELIC.PUMPKIN_CANDLE"}},
    "exhaust": {"S": {"RELIC.PAELS_EYE", "RELIC.PAELS_BLOOD", "RELIC.SAND_CASTLE"},
                "A": {"RELIC.PAELS_LEGION", "RELIC.PAELS_FLESH", "RELIC.YUMMY_COOKIE"}},
    "strength": {"S": {"RELIC.PAELS_FLESH", "RELIC.TOASTY_MITTENS", "RELIC.PUMPKIN_CANDLE"},
                  "A": {"RELIC.PAELS_BLOOD", "RELIC.VERY_HOT_COCOA", "RELIC.SAND_CASTLE"}},
}
_RELIC_TIER_VALUE = {"S": 9, "A": 7, "B": 5, "C": 3, "D": 1}

# Stable event-option keys are intentionally kept separate from the relic tables.  Unknown
# events return an explicit fallback action so the C# bridge can keep the game's safe random
# handler; reviewer/decompile results can be added here without changing that fallback.
EVENT_OPTION_SCORES = {
    "BYRDONIS_NEST": {"TAKE": 100},
    "TABLET_OF_TRUTH": {"SMASH": 100},
    "MORPHIC_GROVE": {"LONER": 100},
    "WELLSPRING": {"BOTTLE": 100},
    "AROMA_OF_CHAOS": {"MAINTAIN_CONTROL": 100},
    # SwordOfStone is delayed until five elites are defeated; 166-run data shows the current
    # median run reaches only nine combats, so the immediate gold/HP trade is better for now.
    "SUNKEN_STATUE": {"DIVE_INTO_WATER": 100},
    # ChosenCheese grants +1 max HP after each combat; its 14-combat break-even is beyond the
    # current 9-combat median (9.9 average), so taking two free commons is better for now.
    "ROOM_FULL_OF_CHEESE": {"GORGE": 100},
    "WOOD_CARVINGS": {"TORUS": 100, "BIRD": 50},
    "THIS_OR_THAT": {"ORNATE": 60},
    "JUNGLE_MAZE_ADVENTURE": {"JOIN_FORCES": 60},
    "SELF_HELP_BOOK": {},  # scored below from the deck's current block needs
}


def _relic_axis(deck_ids: set[str]) -> str | None:
    axis = _axis(deck_ids)
    return axis or ("strength" if STRENGTH_CARDS & deck_ids else None)


def _shop_relic_score(relic: str, axis: str | None) -> int:
    score = SHOP_RELIC_SCORES.get(relic, -1)
    if score < 0:
        return score
    for tier, relics in RELIC_TIERS_BY_AXIS.get(axis or "general", {}).items():
        if relic in relics:
            score = max(score, _RELIC_TIER_VALUE[tier])
            break
    return score


def _event_relic_score(relic: str, axis: str | None) -> int:
    score = RELIC_SCORES.get(relic, 0)
    for tier, relics in EVENT_RELIC_TIERS_BY_AXIS.get(axis or "general", {}).items():
        if relic in relics:
            return max(score, _RELIC_TIER_VALUE[tier])
    return score


def choose_event(observation: dict) -> dict:
    actions = [
        action for action in observation.get("legal_actions", ())
        if action.get("type") in {"event_option", "event_relic"}
        and not action.get("is_locked")
        and not action.get("text_key", "").rsplit(".", 1)[-1].endswith("_LOCKED")
    ]
    if not actions:
        raise ValueError("no event relic actions")
    relic_actions = [action for action in actions if action.get("relic_id")]
    if relic_actions:
        actions = relic_actions
        block_starved = _block_starved(_deck_list(observation))
        axis = _relic_axis(_deck_ids(observation))
        player = observation.get("player", {})
        hp, max_hp = player.get("hp", 0), player.get("max_hp", 1)
        low_hp = hp <= max_hp // 2

        def relic_score(action: dict) -> int:
            relic = action.get("relic_id", "")
            value = _event_relic_score(relic, axis)
            if block_starved and relic == "RELIC.PAELS_LEGION":
                value += 2
            if low_hp and relic in {"RELIC.VERY_HOT_COCOA", "RELIC.PAELS_FLESH"}:
                value += 1
            return value

        return max(actions, key=relic_score)

    event_id = observation.get("event_id", "")

    def option_score(action: dict) -> int | None:
        scores = EVENT_OPTION_SCORES.get(event_id)
        if scores is None:
            return None
        text_key = action.get("text_key", "")
        option = text_key.rsplit(".", 1)[-1]
        if event_id == "SELF_HELP_BOOK":
            preferred = "READ_PASSAGE" if _block_starved(_deck_list(observation)) else "READ_THE_BACK"
            if option == preferred:
                return 100
            if option == "READ_ENTIRE_BOOK":
                return -1
            if option in {"READ_THE_BACK", "READ_PASSAGE"}:
                return 0
        return scores.get(text_key, scores.get(option))

    scored = [(option_score(action), action) for action in actions]
    known = [(score, action) for score, action in scored if score is not None]
    if known:
        return max(known, key=lambda item: (item[0], -item[1].get("option_index", 0)))[1]
    proceed = next((action for action in actions if action.get("is_proceed")), None)
    if proceed is not None:
        return proceed
    return {"type": "event_fallback"}


def choose(observation: dict, enemy_data: dict | None = None, simulations: int = 0) -> dict:
    global _LAST_POTION_CONTEXT
    if observation.get("phase") == "shop":
        return choose_shop(observation)
    if observation.get("phase") == "map":
        return choose_map(observation)
    if observation.get("phase") == "card_reward":
        return choose_card_reward(observation)
    if observation.get("phase") == "rest":
        return choose_rest(observation)
    if observation.get("phase") == "event":
        return choose_event(observation)
    actions = observation["legal_actions"]
    # TheGambitPower (decompiled): 50 block for 0 cost, but the very next unblocked hit taken
    # while it's active - this turn or any later turn, it has no self-expiry - kills the player
    # outright regardless of remaining HP. combat.py already excludes this card from the
    # simulator (unmodeled power), but the heuristic tail's "highest block card" fallback below
    # doesn't know that and used to auto-play it as an amazing defensive option every time,
    # turning the very next chip of unblocked damage into an instant death (VANTOM, 87 HP -> 0
    # in one hit with no attack anywhere near that size). Never auto-play it.
    cards = [action for action in actions if action["type"] == "card" and action["card_id"] != "CARD.THE_GAMBIT"]
    potions = [action for action in actions if action["type"] == "potion"]
    sandpit_critical = any(power["id"] == "POWER.SANDPIT_POWER" and 0 < power["amount"] <= 2 for enemy in observation.get("enemies", ()) for power in enemy.get("powers", ()))
    escape = next((action for action in cards if action["card_id"] == "CARD.FRANTIC_ESCAPE"), None)
    if sandpit_critical and escape:
        return escape
    potion_context = _potion_context(observation)
    if (
        potion_context is None
        or potion_context != _LAST_POTION_CONTEXT
        or _potion_is_lethal_incoming(observation)
    ) and (potion := choose_potion(observation, potions)):
        if potion_context is not None:
            _LAST_POTION_CONTEXT = potion_context
        return potion
    if turn := choose_crab_facing(observation, cards):
        return turn
    enemy_by_id = {enemy["combat_id"]: enemy for enemy in observation.get("enemies", ())}
    hand = {card.get("index"): card for card in observation.get("hand", ()) if card.get("index") is not None}
    enemy_incoming = {enemy["combat_id"]: _intent_incoming(enemy) for enemy in observation.get("enemies", ())}

    def damage(action: dict) -> int:
        enemy = enemy_by_id.get(action.get("target_id"))
        if not enemy:
            return 0
        # Slippery enemies reduce every hit to 1 until the power is spent.
        if any(power.get("id") == "POWER.SLIPPERY_POWER" and _number(power.get("amount")) > 0 for power in enemy.get("powers", ())):
            return 1
        value = _card_value(action, hand, "damage")
        # HardToKill (e.g. Exoskeleton) caps every hit at the power amount.
        caps = [_number(power.get("amount")) for power in enemy.get("powers", ()) if power.get("id") == "POWER.HARD_TO_KILL_POWER" and _number(power.get("amount")) > 0]
        return min(value, max(caps)) if caps else value

    def is_lethal(action: dict) -> bool:
        enemy = enemy_by_id.get(action.get("target_id"))
        return bool(enemy and damage(action) - enemy.get("block", 0) >= enemy["hp"])

    # rollouts cover the modeled cards in hand; unknown cards are treated as unplayable by the
    # simulator rather than abandoning the rollout entirely (e.g. Dominate used to disable it).
    if enemy_data and simulations and any(card["card_id"] in CARD_NAMES for card in cards):
        try:
            selected = rollout_choice(observation, actions, enemy_data, simulations)
            player = observation.get("player", {})
            hp, max_hp = player.get("hp", 0), player.get("max_hp", player.get("hp", 0))
            incoming = sum(enemy_incoming.values())
            # Keep the fallback's self-damage guard in front of rollouts too.  A rollout can
            # rationally trade 3 HP for Bloodletting's energy even when the live turn is already
            # dangerous; that is not a safe real-game choice unless it kills the target now.
            if not (_is_self_damage(selected, hand) and (hp <= max_hp // 2 or incoming >= max(1, hp // 2)) and not is_lethal(selected)):
                return selected
        except (KeyError, ValueError, NotImplementedError, StopIteration):
            pass

    lethal = [
        action for action in cards
        if is_lethal(action)
    ]
    if lethal:
        killers = [action for action in lethal if not _is_self_damage(action, hand)] or lethal
        # Finish off the enemy that is about to attack first, then the weakest one.
        return max(killers, key=lambda action: (enemy_incoming.get(action["target_id"], 0), -enemy_by_id[action["target_id"]].get("hp", 0), _card_value(action, hand, "damage")))
    incoming = sum(enemy_incoming.values())
    player = observation.get("player", {})
    hp, max_hp = player.get("hp", 0), player.get("max_hp", 0)
    summon_pending = any(
        "summon" in str(intent.get("type", "")).lower()
        for enemy in observation.get("enemies", ())
        for intent in enemy.get("intents") or ()
    )
    if hp <= max_hp // 2 or incoming >= max(1, hp // 2):
        safe_cards = [action for action in cards if not _is_self_damage(action, hand)]
        if safe_cards:
            cards = safe_cards
        elif cards:
            return next(action for action in actions if action["type"] == "end_turn")
    defenses = [action for action in cards if _card_value(action, hand, "block") > 0]
    if (observation.get("player", {}).get("block", 0) < incoming or summon_pending) and defenses:
        return max(defenses, key=lambda action: _card_value(action, hand, "block"))
    # MinionPower enemies (e.g. The Kin's Followers) do not need to die to win the fight -
    # CombatManager only checks primary enemies - so they should not distract focus fire.
    minion_ids = {enemy["combat_id"] for enemy in observation.get("enemies", ()) if any(power.get("id") == "POWER.MINION_POWER" and _number(power.get("amount")) > 0 for power in enemy.get("powers", ()))}
    priority = {"CARD.BASH": 4, "CARD.STRIKE_IRONCLAD": 3, "CARD.DEFEND_IRONCLAD": 2}
    if cards:
        def score(action: dict) -> tuple[int, int, int, int]:
            card = hand.get(action.get("hand_index"), {})
            attack = card.get("type") == "Attack" and action.get("target_id") in enemy_by_id
            # Focus fire: among equal-priority attacks, prefer non-minion enemies, then the weakest.
            return (
                priority.get(action["card_id"], 3 if card.get("type") == "Attack" else 1),
                damage(action) if attack else 0,
                (action.get("target_id") not in minion_ids) if attack else 0,
                -enemy_by_id[action["target_id"]].get("hp", 0) if attack else 0,
            )
        return max(cards, key=score)
    return next(action for action in actions if action["type"] == "end_turn")


def choose_crab_facing(observation: dict, cards: list[dict]) -> dict | None:
    facing = next((power.get("facing") for power in observation.get("player", {}).get("powers", ()) if power["id"] == "POWER.SURROUNDED_POWER"), None)
    if facing not in {"Left", "Right"}:
        return None
    threats = []
    for enemy in observation.get("enemies", ()):
        direction = "Left" if any(power["id"] == "POWER.BACK_ATTACK_LEFT_POWER" for power in enemy.get("powers", ())) else "Right" if any(power["id"] == "POWER.BACK_ATTACK_RIGHT_POWER" for power in enemy.get("powers", ())) else None
        incoming = sum(intent.get("damage", 0) * max(1, intent.get("repeats", 1)) for intent in enemy.get("intents") or ())
        if direction and incoming:
            threats.append((incoming, direction, enemy["combat_id"]))
    if not threats:
        return None
    _, direction, target_id = max(threats)
    if direction == facing:
        return None
    hand = {card["index"]: card for card in observation.get("hand", ())}
    return next((action for action in cards if action.get("target_id") == target_id and hand.get(action.get("hand_index"), {}).get("type") == "Attack"), None)


def choose_potion(observation: dict, actions: list[dict]) -> dict | None:
    if not actions:
        return None
    enemy_hp = {enemy["combat_id"]: enemy["hp"] for enemy in observation.get("enemies", ())}
    enemy_damage = {enemy["combat_id"]: _intent_incoming(enemy) for enemy in observation.get("enemies", ())}
    def use(ids: set[str], target_score: dict[int, int] | None = None) -> dict | None:
        candidates = [action for action in actions if action["potion_id"] in ids]
        return max(candidates, key=lambda action: target_score.get(action.get("target_id"), 0) if target_score else 0, default=None)
    player = observation.get("player", {})
    hp, max_hp = player.get("hp", 0), player.get("max_hp", 1)
    block = _number(player.get("block", 0))
    incoming = sum(_intent_incoming(enemy) for enemy in observation.get("enemies", ()))
    lucky = use({"POTION.LUCKY_TONIC"})
    if lucky and incoming > 0 and hp - incoming <= max_hp // 4:
        return lucky
    fire = next((action for action in actions if action["potion_id"] == "POTION.FIRE_POTION" and action.get("target_id") in enemy_hp and enemy_hp[action["target_id"]] <= 20), None)
    if fire:
        return fire
    healing = {"POTION.BLOOD_POTION", "POTION.CURE_ALL"}
    # Fortifier doubles the current block, so with no block it is wasted (sim19 used it at 0
    # block and gained nothing); only count it once the player already has block this turn.
    blocking = {"POTION.BLOCK_POTION", "POTION.SHIP_IN_A_BOTTLE"} | ({"POTION.FORTIFIER"} if block > 0 else set())
    # Speed Potion just grants Dexterity via SpeedPotionPower - same effect as Dexterity Potion.
    defensive_buffs = {
        "POTION.DEXTERITY_POTION", "POTION.SPEED_POTION", "POTION.GHOST_IN_A_JAR", "POTION.REGEN_POTION",
        "POTION.LIQUID_BRONZE", "POTION.FYSH_OIL", "POTION.HEART_OF_IRON",
    }
    recovery = healing | defensive_buffs | {"POTION.ENTROPIC_BREW"}
    # Shackling is deliberately excluded from `debuffs` below: its -7 Strength lasts the whole
    # fight, so it is reserved for the >=100 HP boss-length branch further down rather than
    # spent reactively on any dangerous *regular* fight (e.g. a Wriggler swarm) - sim13 burned
    # Shackling on a normal encounter and had nothing left for the boss that actually needed it.
    debuffs = {"POTION.WEAK_POTION", "POTION.VULNERABLE_POTION", "POTION.POISON_POTION", "POTION.POTION_OF_BINDING"}
    offensive = {
        "POTION.ATTACK_POTION", "POTION.COLORLESS_POTION", "POTION.DISTILLED_CHAOS", "POTION.DUPLICATOR",
        "POTION.EXPLOSIVE_AMPOULE", "POTION.FIRE_POTION", "POTION.FLEX_POTION", "POTION.POWER_POTION",
        "POTION.SKILL_POTION", "POTION.STRENGTH_POTION", "POTION.POTION_SHAPED_ROCK",
    }
    known = recovery | blocking | debuffs | offensive | {"POTION.ENERGY_POTION", "POTION.SWIFT_POTION", "POTION.LUCKY_TONIC", "POTION.SHACKLING_POTION"}
    def unknown_manual() -> dict | None:
        for action in actions:
            potion_id = str(action.get("potion_id", "")).upper()
            # SNECKO_OIL randomizes the energy cost (0-3) of every card drawn into hand; using
            # it as a blind emergency fallback can spike the cost of the exact card needed to
            # survive the turn, making a dangerous situation worse instead of better.
            # FOUL_POTION deals 12 damage to every creature INCLUDING the player - against a
            # high-HP boss this is a bad trade (a live run burned two full-HP casts, -24 HP, for
            # a negligible 24/408 dent), and "danger" here triggers on 2+ enemies alone, so it
            # can fire at full HP with nothing actually wrong yet. Unknown potions are only
            # considered below when HP or incoming damage is already dangerous.
            if potion_id and potion_id not in known and not any(marker in potion_id for marker in ("FAIRY", "REVIV", "SNECKO", "FOUL")):
                return action
        return None
    danger = hp <= max_hp // 2 or incoming >= max(1, hp // 2)
    threatening = incoming >= max(1, hp // 2)
    # Skill Potion is a hand-dependent gamble; save it for a turn whose incoming damage is
    # substantial enough to justify spending a scarce potion slot.
    offensive_now = offensive if threatening else offensive - {"POTION.SKILL_POTION"}
    hand = observation.get("hand") or ()
    boss_shackling = use({"POTION.SHACKLING_POTION"}) if max(enemy_hp.values(), default=0) >= 100 and incoming > 0 else None
    if incoming >= hp:
        energy = use({"POTION.ENERGY_POTION"}) if any(card.get("cost", 1) > 0 for card in hand) else None
        return use({"POTION.LUCKY_TONIC", "POTION.GHOST_IN_A_JAR"} | blocking) or use(debuffs, enemy_damage) or use(recovery) or boss_shackling or use(offensive_now, enemy_hp) or energy or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if hp <= max_hp // 2 and (len(enemy_hp) >= 2 or incoming >= hp // 2):
        if len(enemy_hp) >= 2:
            explosive = use({"POTION.EXPLOSIVE_AMPOULE"})
            if explosive:
                return explosive
        if any(card.get("cost", 1) > 0 for card in hand):
            energy = use({"POTION.ENERGY_POTION"})
            if energy:
                return energy
        return use(blocking) or use(debuffs, enemy_damage) or use(recovery) or boss_shackling or use(offensive_now, enemy_hp) or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if hp <= max_hp // 2:
        return use(recovery) or boss_shackling or use(offensive_now, enemy_hp) or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if incoming >= hp // 2:
        energy = use({"POTION.ENERGY_POTION"}) if any(card.get("cost", 1) > 0 for card in hand) else None
        return use(blocking) or use(debuffs, enemy_damage) or use(recovery) or boss_shackling or energy or use(offensive_now, enemy_hp) or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if max(enemy_hp.values(), default=0) >= 100:
        # Boss-length fights: ShacklingPotionPower subclasses TemporaryStrengthPower, whose
        # AfterSideTurnEnd removes the -7 Strength (and itself) once the AFFECTED CREATURE's own
        # side-turn ends - it only blunts the enemy's very next turn, not the whole fight (a
        # prior assumption here was wrong and wasted the potion on sleeping bosses like Bygone
        # Effigy that don't attack on an early turn). Only spend it once an attack is actually
        # incoming this decision, so the -7 lands on a turn that would otherwise deal damage.
        shackling = use({"POTION.SHACKLING_POTION"}) if incoming > 0 else None
        return shackling or use(offensive_now) or use({"POTION.VULNERABLE_POTION", "POTION.POISON_POTION", "POTION.FIRE_POTION"}, enemy_hp) or (unknown_manual() if danger else None)
    if not hand:
        return use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    return unknown_manual() if danger else None


def _deck_list(observation: dict) -> list[str]:
    player = observation.get("player", {})
    deck = observation.get("deck") or observation.get("deck_cards") or player.get("deck") or player.get("deck_cards") or ()
    return [card if isinstance(card, str) else card.get("id") or card.get("card_id") for card in deck]


def _deck_ids(observation: dict) -> set[str]:
    return set(_deck_list(observation))


def _axis(deck_ids: set[str]) -> str | None:
    if {"CARD.PERFECTED_STRIKE", "CARD.HELLRAISER"} & deck_ids:
        return "strike"
    if {"CARD.RUPTURE", "CARD.TEAR_ASUNDER"} & deck_ids:
        return "self_damage"
    has_apply = bool(set(VULNERABLE_APPLY) & deck_ids)
    has_payoff = bool(set(VULNERABLE_PAYOFF) & deck_ids)
    if has_payoff and ("CARD.BASH" in deck_ids or has_apply):
        return "vulnerable"
    if set(EXHAUST_ENABLERS) & deck_ids and set(EXHAUST_PAYOFF) & deck_ids:
        return "exhaust"
    return None


def _core_priority(deck_ids: set[str], available: set[str] | None = None) -> dict[str, int]:
    axis = _axis(deck_ids)
    if axis == "strike":
        cards = ["CARD.HELLRAISER"] if "CARD.PERFECTED_STRIKE" in deck_ids and "CARD.HELLRAISER" not in deck_ids else []
    elif axis == "self_damage":
        cards = [card for card in ("CARD.TEAR_ASUNDER", "CARD.OFFERING") if card not in deck_ids]
    elif axis == "vulnerable":
        cards = [card for card in VULNERABLE_CORE if card not in deck_ids]
    elif axis == "exhaust":
        cards = [card for card in EXHAUST_CORE if card not in deck_ids]
    else:
        # Axis seeds: Inflame (strength) leads - boss-fight verification showed the strength
        # axis deals the most damage - then Perfected Strike (strike) and Corruption (exhaust).
        # Rupture is only a seed once a self-damage enabler is already in the deck.
        first = ["CARD.INFLAME", "CARD.PERFECTED_STRIKE", "CARD.CORRUPTION"]
        if UNCOMMITTED_SELF_DAMAGE & deck_ids:
            first.insert(2, "CARD.RUPTURE")
        cards = [card for card in first if available and card in available]
    if available is not None:
        cards = [card for card in cards if card in available]
    return {card: len(cards) - index for index, card in enumerate(cards)}


def choose_shop(observation: dict) -> dict:
    actions = observation.get("legal_actions", ())
    deck_ids = _deck_ids(observation)
    deck_list = _deck_list(observation)
    shop_cards = {
        card.get("id") or card.get("card_id"): card for card in observation.get("cards", ())
    }
    deck_cards = observation.get("deck_cards") or ()
    high_cost_in_deck = sum(_number(card.get("cost"), 0) >= 3 for card in deck_cards)
    over_high_cost_cap = high_cost_in_deck >= 2
    over_unmodeled_cap = sum(card_id in UNMODELED_REWARDS for card_id in deck_list) >= UNMODELED_CAP
    defense_needed = _block_starved(deck_list)
    buys = [action for action in actions if action.get("type") == "buy_card"]
    axis = _relic_axis(deck_ids)
    core = _core_priority(deck_ids, {(action.get("card_id") or action.get("id")) for action in buys})
    tier_score = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

    def card_key(action: dict) -> tuple[int, int, int, int, int]:
        card_id = action.get("card_id") or action.get("id")
        if over_unmodeled_cap and card_id in UNMODELED_REWARDS:
            return (0, 0, 0, 0, 0)
        if over_high_cost_cap and _number(shop_cards.get(card_id, {}).get("energy_cost"), 0) >= 3:
            return (0, 0, 0, 0, 0)
        if card_id in core:
            return (4, core[card_id], tier_score.get(CARD_TIERS.get(card_id, "D"), 0), 0, 0)
        if not (set(EXHAUST_ENABLERS) & deck_ids) and card_id in UNCOMMITTED_EXHAUST_PAYOFF:
            return (0, 0, 0, 0, 0)
        tier = CARD_TIERS.get(card_id)
        allow_b_defense = defense_needed and tier == "B" and card_id in STRONG_BLOCK_CARDS
        if tier not in {"S", "A"} and not allow_b_defense:
            return (0, 0, 0, 0, 0)
        # A strong block is more valuable when the deck still lacks a real Act 2 answer.
        defense_bonus = 1 if defense_needed and card_id in STRONG_BLOCK_CARDS else 0
        return (2, tier_score[tier], defense_bonus, 0, 0)

    # A high-value known relic beats a non-core card, but an axis-defining card still wins.
    relics = [action for action in actions if action.get("type") == "buy_relic"]
    best_relic = max(
        relics,
        key=lambda action: _shop_relic_score(action.get("relic_id") or action.get("id"), axis),
        default=None,
    )
    relic_score = _shop_relic_score((best_relic or {}).get("relic_id") or (best_relic or {}).get("id"), axis)
    best_card = max(buys, key=card_key, default=None)
    if best_card and card_key(best_card)[0] == 4:
        return best_card
    if (
        best_card
        and card_key(best_card)[0] == 2
        and _draw_starved(deck_list)
        and (best_card.get("card_id") or best_card.get("id")) in DRAW_CARDS
        and relic_score < 7
    ):
        return best_card
    if best_relic is not None and relic_score >= 6:
        return best_relic
    if best_card and card_key(best_card)[0] == 2:
        return best_card
    removals = [action for action in actions if action.get("type") == "remove"]
    remove_id = "CARD.DEFEND_IRONCLAD" if "CARD.PERFECTED_STRIKE" in deck_ids else "CARD.STRIKE_IRONCLAD"
    preferred = next((action for action in removals if (action.get("card_id") or action.get("id")) == remove_id), None)
    if preferred:
        return preferred
    return next((action for action in actions if action.get("type") == "skip"), actions[0] if actions else {"type": "skip"})


def _log_rest_routing(observation: dict, player: dict, routes: list[tuple[dict, tuple[int, int, int] | None]]) -> None:
    # Opt-in diagnostic for choose_map's low-HP safety routing: dumps the candidate branches and
    # their (fight_count, distance, elite_count) tuples so a real run can be checked afterwards
    # for "no fight-free route existed" vs. "a better route existed and was not taken".
    path = os.environ.get("STS2AI_MAP_DEBUG")
    if not path:
        return
    points = {(p["col"], p["row"]): p["type"] for p in observation["map"]["points"]}
    entry = {
        "seq": observation.get("seq"),
        "hp": player.get("hp"),
        "max_hp": player.get("max_hp"),
        "candidates": [
            {"col": action["col"], "row": action["row"], "type": points.get((action["col"], action["row"])), "route": route}
            for action, route in routes
        ],
    }
    with open(path, "a", encoding="utf-8") as file:
        file.write(json.dumps(entry) + "\n")


def choose_map(observation: dict) -> dict:
    points = {(point["col"], point["row"]): point for point in observation["map"]["points"]}
    room_value = {"Ancient": 0, "Monster": 1, "Unknown": 1, "Shop": 1, "RestSite": 3, "Treasure": 3, "Elite": -5, "Boss": 0}
    memo: dict[tuple[int, int], int] = {}
    visiting: set[tuple[int, int]] = set()

    def value(coord: tuple[int, int]) -> int:
        if coord in memo:
            return memo[coord]
        if coord in visiting:
            return 0
        visiting.add(coord)
        point = points[coord]
        children = [(child["col"], child["row"]) for child in point["children"]]
        memo[coord] = room_value.get(point["type"], 0) + (max(map(value, children)) if children else 0)
        visiting.remove(coord)
        return memo[coord]

    player = observation.get("player", {})
    # Route toward rest sites and avoid elites once HP drops below three quarters (matches
    # choose_rest's own HEAL threshold, previously two thirds here). Normal-state routing below
    # only minimizes total Monster tiles over the whole remaining route to the boss - it has no
    # notion of "HP banked so far" at all, so a run can walk straight through several costly
    # fights back to back before this safety mode ever engages. A real run (Act1, floor ~1-6)
    # dropped 80 -> 52 HP across two ordinary Monster packs while still just outside the old
    # two-thirds cutoff (53.3), only reaching a rest site at 10 HP after a third costly fight it
    # had no choice but to walk through. Raising the trigger point buys an earlier, healthier
    # margin before the unavoidable fights on the way to whatever rest site is actually reachable.
    if player.get("max_hp", 0) and player.get("hp", player["max_hp"]) * 4 <= player["max_hp"] * 3:
        rest_paths: dict[tuple[int, int], tuple[int, int, int] | None] = {}
        rest_visiting: set[tuple[int, int]] = set()

        def rest_path(coord: tuple[int, int]) -> tuple[int, int, int] | None:
            if coord in rest_paths:
                return rest_paths[coord]
            if coord in rest_visiting:
                return None
            rest_visiting.add(coord)
            point = points[coord]
            elites = point["type"] == "Elite"
            if point["type"] == "RestSite":
                rest_paths[coord] = (0, 0, int(elites))
                rest_visiting.remove(coord)
                return rest_paths[coord]
            children = (rest_path((child["col"], child["row"])) for child in point["children"])
            reachable = [path for path in children if path is not None]
            fights = int(point["type"] in {"Monster", "Elite", "Boss"})
            rest_paths[coord] = None if not reachable else min(
                (fight_count + fights, distance + 1, elite_count + elites)
                for fight_count, distance, elite_count in reachable
            )
            rest_visiting.remove(coord)
            return rest_paths[coord]

        routes = [(action, rest_path((action["col"], action["row"]))) for action in observation["legal_actions"]]
        reachable = [(action, route) for action, route in routes if route is not None]
        _log_rest_routing(observation, player, routes)
        if reachable:
            return min(reachable, key=lambda choice: (*choice[1], -value((choice[0]["col"], choice[0]["row"]))))[0]

        safety_paths: dict[tuple[int, int], tuple[int, int]] = {}
        safety_visiting: set[tuple[int, int]] = set()

        def safety_path(coord: tuple[int, int]) -> tuple[int, int] | None:
            if coord in safety_paths:
                return safety_paths[coord]
            if coord in safety_visiting:
                return None
            safety_visiting.add(coord)
            point = points[coord]
            children = (safety_path((child["col"], child["row"])) for child in point["children"])
            reachable = [path for path in children if path is not None]
            fights = point["type"] in {"Monster", "Elite", "Boss"}
            safety_paths[coord] = (int(fights), int(not fights)) if not reachable else min(((fight_count + fights, noncombat_count + (not fights)) for fight_count, noncombat_count in reachable), key=lambda path: (path[0], -path[1]))
            safety_visiting.remove(coord)
            return safety_paths[coord]

        return min(observation["legal_actions"], key=lambda action: (safety_path((action["col"], action["row"]))[0], -safety_path((action["col"], action["row"]))[1], -value((action["col"], action["row"]))))

    legal_actions = observation["legal_actions"]
    # The whole map is revealed at act start, so plan a rough route from the current point to
    # the boss: minimize normal combat tiles first (the enemy pool escalates to a strong pool
    # from the 4th normal combat), then maximize rest sites, avoid elites, and prefer treasures.
    run = observation.get("run") or {}
    current_raw = run.get("current")
    current = (current_raw.get("col"), current_raw.get("row")) if isinstance(current_raw, dict) and current_raw else None
    boss = next((coord for coord, point in points.items() if point["type"] == "Boss"), None)

    def plan_paths(start: tuple[int, int]) -> list[list[tuple[int, int]]]:
        found: list[list[tuple[int, int]]] = []
        seen: set[tuple[int, int]] = set()

        def dfs(coord: tuple[int, int], path: list[tuple[int, int]]) -> None:
            if coord == boss:
                found.append(path)
                return
            if coord in seen:
                return
            seen.add(coord)
            for child in points[coord].get("children", ()):
                dfs((child["col"], child["row"]), path + [(child["col"], child["row"])])
            seen.remove(coord)

        dfs(start, [start])
        return found

    def route_key(path: list[tuple[int, int]]) -> tuple[int, int, int, int, int, int, int]:
        types = [points[coord]["type"] for coord in path]
        elite_run = unrested_elites = 0
        for room_type in types:
            if room_type == "RestSite":
                elite_run = 0
            elif room_type == "Elite":
                elite_run += 1
                unrested_elites += int(elite_run > 1)
        return (
            unrested_elites,
            types.count("Monster"),
            -types.count("RestSite"),
            types.count("Elite"),
            -types.count("Treasure"),
            types.count("Unknown"),
            -types.count("Shop"),
        )

    if boss is not None:
        starts = [current] if current is not None else [(action["col"], action["row"]) for action in legal_actions]
        candidates: list[list[tuple[int, int]]] = []
        for start in starts:
            if start in points:
                candidates.extend(plan_paths(start))
        if candidates:
            best = min(candidates, key=route_key)
            target = best[1] if current is not None and len(best) > 1 else best[0]
            for action in legal_actions:
                if action["col"] == target[0] and action["row"] == target[1]:
                    return action

    return max(legal_actions, key=lambda action: value((action["col"], action["row"])))


STRIKE_TAGGED_REWARDS = {"CARD.PERFECTED_STRIKE", "CARD.ASHEN_STRIKE", "CARD.TWIN_STRIKE", "CARD.SETUP_STRIKE"}

# Strength sources that scale every attack into boss firepower; once one is in the deck the
# others are prioritized so the axis keeps growing.
STRENGTH_CARDS = {"CARD.INFLAME", "CARD.PRIMAL_FORCE", "CARD.DOMINATE", "CARD.CRUELTY"}

# Reliable draw is the smallest common denominator across Ironclad builds. Keep this separate
# from the tier table so a draw-starved deck can prefer a modest draw card without forcing an axis.
DRAW_CARDS = {
    "CARD.BATTLE_TRANCE", "CARD.BURNING_PACT", "CARD.POMMEL_STRIKE", "CARD.DRUM_OF_BATTLE",
    "CARD.MASTER_OF_STRATEGY", "CARD.FINESSE",
}

# Cards the agent would rarely play, so taking them only bloats the deck (e.g. Relax's 3-cost
# block is too awkward for the greedy rollout to use consistently). Never pick these.
UNPLAYABLE_REWARDS = {"CARD.RELAX"}
# Keep tiered cards out of the deck until both the reward tier and combat model are registered.
UNMODELED_REWARDS = set(CARD_TIERS) - set(CARD_NAMES)
UNMODELED_CAP = 2

DEFENSE_PRIORITY = {
    "CARD.IMPERVIOUS", "CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER",
    "CARD.BLOOD_WALL", "CARD.SECOND_WIND", "CARD.STONE_ARMOR", "CARD.TAUNT",
    "CARD.IRON_WAVE", "CARD.TRUE_GRIT",
}

# Blocks of 8+ that can actually hold off Act 2's 28-36 hits. Taunt is included despite its
# 7-block base because its Vulnerable rider makes it a dedicated defensive solution; Defend (5),
# Iron Wave (5), Second Wind (5) and True Grit (7) are barely better than Defend.
STRONG_BLOCK_CARDS = {
    "CARD.IMPERVIOUS", "CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER",
    "CARD.BLOOD_WALL", "CARD.STONE_ARMOR", "CARD.TAUNT", "CARD.EVIL_EYE",
    "CARD.EQUILIBRIUM", "CARD.ULTIMATE_DEFEND",
}


def _block_starved(deck: list[str]) -> bool:
    # True when the deck needs defensive picks: block cards make up under 40% of the deck, or
    # the deck has fewer than 2 strong block cards (Shrug It Off, Flame Barrier, ...). Defend's
    # 5 block alone cannot hold off Act 2's 28-36 attacks, so a deck with only Defends is still
    # starved. sim19 died at exactly 1/3 block cards because the old 1/3 threshold never fired.
    block_cards = sum(card in DEFENSE_PRIORITY or card == "CARD.DEFEND_IRONCLAD" for card in deck)
    strong_blocks = sum(card in STRONG_BLOCK_CARDS for card in deck)
    # Once the deck reaches Act 2 size, two strong blocks are too thin for a long boss fight;
    # keep the early balanced-deck behavior (12 cards with two Shrugs) unchanged.
    strong_block_shortage = strong_blocks < (3 if len(deck) >= 16 else 2)
    return len(deck) >= 10 and (block_cards * 5 < len(deck) * 2 or strong_block_shortage)


def _draw_starved(deck: list[str]) -> bool:
    return len(deck) >= 10 and sum(card in DRAW_CARDS for card in deck) < 2


def choose_card_reward(observation: dict) -> dict:
    deck_list = _deck_list(observation)
    unmodeled_in_deck = sum(card_id in UNMODELED_REWARDS for card_id in deck_list)
    actions = [
        action for action in observation["legal_actions"]
        if action["type"] == "card_reward"
        and action["card_id"] not in UNPLAYABLE_REWARDS
        and (unmodeled_in_deck < UNMODELED_CAP or action["card_id"] not in UNMODELED_REWARDS)
    ]
    if not actions:
        # Every offered card is unplayable (e.g. only Relax was shown): take nothing.
        return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")
    tier_score = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    deck_ids = _deck_ids(observation)
    core = _core_priority(deck_ids, {action["card_id"] for action in actions})
    priority = {card_id: tier_score[tier] for card_id, tier in CARD_TIERS.items()}
    player = observation.get("player", {})
    if player.get("hp", 0) <= player.get("max_hp", 1) // 2 and "CARD.FEED" in priority:
        priority["CARD.FEED"] += 1
    if _axis(deck_ids) != "self_damage":
        uncommitted_count = sum(card in UNCOMMITTED_SELF_DAMAGE for card in deck_list)
        for card_id in UNCOMMITTED_SELF_DAMAGE:
            if card_id in priority:
                priority[card_id] -= 2 + (1 if uncommitted_count else 0)
    exhaust_ready = bool(set(EXHAUST_ENABLERS) & deck_ids)
    if not exhaust_ready:
        for card_id in UNCOMMITTED_EXHAUST_PAYOFF:
            if card_id in priority:
                priority[card_id] -= 1
    strike_axis = _axis(deck_ids) == "strike"
    # Perfected Strike (6 + 2 per Strike) hits ~16 with the starter deck's 5 Strikes, so a
    # seed is worth taking, but every Strike-tagged card grows the deck and the boss-fight
    # verification showed PS-heavy decks deal the least damage. Feed the strike axis only
    # while it is lean (1-2 copies); afterwards the strength axis (Inflame etc.) outranks it.
    strikes = sum(card in STRIKE_TAGGED_REWARDS or card == "CARD.STRIKE_IRONCLAD" for card in deck_list)
    perfected = sum(card == "CARD.PERFECTED_STRIKE" for card in deck_list)
    if strike_axis and strikes >= 5 and perfected < 2:
        for card_id in STRIKE_TAGGED_REWARDS:
            if card_id in priority:
                priority[card_id] += 2
    if STRENGTH_CARDS & deck_ids:
        for card_id in STRENGTH_CARDS:
            if card_id in priority:
                priority[card_id] += 1
    # Keep the deck from becoming all-offense: true strong-block solutions (Shrug It Off, Taunt,
    # ...) may override a tier, while weak block cards only win same-tier ties. This preserves the
    # sim19 fix without letting True Grit/Iron Wave crowd out deck acceleration forever.
    defense_needed = _block_starved(deck_list)
    draw_needed = _draw_starved(deck_list)
    cards = {card.get("id") or card.get("card_id"): card for card in observation.get("cards", ())}
    # A 3-energy/turn economy can only ever field so many 3+ cost cards a turn - stacking more of
    # them past a couple copies just clogs the hand with cards that sit dead, however strong each
    # one is individually. Deprioritize (not ban) further high-cost picks once the deck already
    # has HIGH_COST_CAP of them; this term sits ahead of core/tier so it overrides even a
    # deck-defining pick, matching "avoid multiple high-cost cards even if strong".
    HIGH_COST_CAP = 2
    deck_cards = (observation.get("player") or {}).get("deck") or observation.get("deck_cards") or ()
    high_cost_in_deck = sum(
        _number(card.get("cost"), 0) >= 3
        for card in deck_cards
        if isinstance(card, dict)
    )
    over_high_cost_cap = high_cost_in_deck >= HIGH_COST_CAP

    def is_high_cost(card_id: str) -> bool:
        return _number(cards.get(card_id, {}).get("cost"), 0) >= 3

    def is_attack_reward(action: dict) -> bool:
        card_id = action["card_id"]
        return cards.get(card_id, {}).get("type") == "Attack" or card_id in ATTACK_REWARD_CARDS

    def strong_defense_bonus(card_id: str) -> int:
        if not (defense_needed and card_id in STRONG_BLOCK_CARDS):
            return 0
        tier = tier_score.get(CARD_TIERS.get(card_id, "D"), 0)
        if any(
            is_attack_reward(action)
            and tier_score.get(CARD_TIERS.get(action["card_id"], "D"), 0) > tier
            for action in actions
        ):
            return 0
        return 2

    selected = max(actions, key=lambda action: (
        0 if over_high_cost_cap and is_high_cost(action["card_id"]) else 1,
        bool(core.get(action["card_id"])), core.get(action["card_id"], 0),
        strong_defense_bonus(action["card_id"]),
        1 if draw_needed and action["card_id"] in DRAW_CARDS else 0,
        priority.get(action["card_id"], 0),
        0 if not exhaust_ready and action["card_id"] in UNCOMMITTED_EXHAUST_PAYOFF else 1,
        1 if defense_needed and action["card_id"] in DEFENSE_PRIORITY else 0,
        1 if strike_axis and perfected < 2 and action["card_id"] in STRIKE_TAGGED_REWARDS else 0,
        1 if action["card_id"] not in deck_ids else 0,
    ))
    if core.get(selected["card_id"]) or priority.get(selected["card_id"], 0):
        return selected
    attacks = [action for action in actions if cards.get(action["card_id"], {}).get("type") == "Attack"]
    if attacks:
        rarity = {"Rare": 3, "Uncommon": 2, "Common": 1}
        return max(attacks, key=lambda action: (rarity.get(cards[action["card_id"]].get("rarity"), 0), -_number(cards[action["card_id"]].get("cost"), 99)))
    return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")


def choose_rest(observation: dict) -> dict:
    actions = observation["legal_actions"]
    hp, max_hp = observation["player"]["hp"], observation["player"]["max_hp"]
    near_boss = _number((observation.get("run") or {}).get("floor")) >= 13  # boss sits on the last of ~15-16 floors
    if hp < max_hp and (near_boss or hp * 4 < max_hp * 3):
        heal = next((action for action in actions if action["option_id"] == "HEAL"), None)
        if heal:
            return heal
    if hp * 4 >= max_hp * 3:
        hatch = next((action for action in actions if action["option_id"] == "HATCH"), None)
        if hatch:
            return hatch
    if hp < max_hp:
        heal = next((action for action in actions if action["option_id"] == "HEAL"), None)
        if heal:
            return heal
    return next((action for action in actions if action["option_id"] == "SMITH"), actions[0])


def rollout_choice(observation: dict, actions: list[dict], data: dict, simulations: int) -> dict:
    specs = {monster["id"]: monster for monster in data["monsters"]}
    enemies = []
    for observed in observation["enemies"]:
        # Pael's Legion and Byrdpip are relic-summoned player pets (9999 HP, no health bar,
        # NOTHING_MOVE forever), not real combat targets; neither has an entry in the exported
        # monster data and would otherwise crash every rollout in any fight where the player
        # owns that relic.
        if observed["id"] in {"MONSTER.PAELS_LEGION", "MONSTER.BYRDPIP"}:
            continue
        spec = specs[observed["id"]]
        enemy = Enemy(
            model=observed["id"],
            hp=observed["hp"],
            move=observed["move"],
            values=tuple(sorted(spec["values"].items())),
            slot=observed["slot"] or "",
            primary=not any(
                power.get("id") == "POWER.MINION_POWER" and _number(power.get("amount")) > 0
                for power in observed.get("powers", ())
            ),
            block=observed["block"],
            powers=tuple(sorted((POWER_NAMES.get(power["id"], power["id"]), power["amount"]) for power in observed["powers"])),
            history=tuple(observed["history"] or ()),
            respawns=2 if any(power.get("id") == "POWER.NEMESIS_POWER" for power in observed.get("powers", ())) else 1 if any(power.get("id") == "POWER.PAINFUL_STABS_POWER" for power in observed.get("powers", ())) else 0,
        )
        if not any(state["id"] == enemy.move for state in spec["states"]):
            # Some moves are synthesized at runtime and never appear in the exported state
            # machine - e.g. IllusionPower.AfterDeath (Parafright) SetMoveImmediate()s a
            # "REVIVE_MOVE" the exporter never saw. Left as-is, the next _enemy_turn() call
            # would look this move id up and raise StopIteration, crashing every rollout that
            # reaches this enemy's turn. Re-resolve back through the monster's own initial state.
            enemy = replace(enemy, move=_resolve_move(enemy, spec, random.Random(observation["seq"]), spec["initial_state"]))
        enemies.append(enemy)
    upgraded_card_ids = list(observation["player"].get("upgraded_cards") or ())
    upgraded_card_ids.extend(
        card["id"] for card in observation.get("hand", ())
        if card.get("upgrade", 0) > 0
    )
    upgraded_card_ids = tuple(dict.fromkeys(upgraded_card_ids))
    state = Combat(
        player_hp=observation["player"]["hp"],
        hand=tuple(CARD_NAMES.get(card["id"], card["id"]) for card in observation["hand"]),
        draw_pile=tuple(CARD_NAMES.get(card, card) for card in observation["draw_pile"]),
        discard_pile=tuple(CARD_NAMES.get(card, card) for card in observation["discard_pile"]),
        enemies=tuple(enemies),
        player_block=observation["player"]["block"],
        player_powers=tuple(sorted(((f"Surrounded{power['facing']}" if power["id"] == "POWER.SURROUNDED_POWER" and power.get("facing") else POWER_NAMES.get(power["id"], power["id"])), power["amount"]) for power in observation["player"]["powers"])),
        energy=observation["player"]["energy"],
        max_energy=observation["player"].get("max_energy", 3),
        turn=observation["turn"],
        exhaust_pile=tuple(CARD_NAMES.get(card, card) for card in observation.get("exhaust_pile", ())),
        player_relics=tuple(observation["player"].get("relics", ())),
        player_max_hp=observation["player"].get("max_hp", observation["player"]["hp"]),
        player_potions=tuple(potion["id"] for potion in observation.get("potions", ()) if potion),
        # The bridge exposes Lizard Tail but not its one-shot-used flag; below half HP, assume
        # it has already fired so rollouts never count on a second resurrection.
        lizard_tail_used=(
            "RELIC.LIZARD_TAIL" in observation["player"].get("relics", ())
            and observation["player"]["hp"] < observation["player"].get("max_hp", observation["player"]["hp"]) // 2
        ),
        belt_buckle_applied=(
            "RELIC.BELT_BUCKLE" in observation["player"].get("relics", ())
            and not any(observation.get("potions", ()))
        ),
        red_skull_active=(
            "RELIC.RED_SKULL" in observation["player"].get("relics", ())
            and observation["player"]["hp"] * 2 <= observation["player"].get("max_hp", observation["player"]["hp"])
        ),
        upgraded_cards=tuple(CARD_NAMES.get(card, card) for card in upgraded_card_ids),
    )
    best, value = search(state, data, simulations, observation["seq"])[0]
    if best == "End turn":
        selected = next(action for action in actions if action["type"] == "end_turn")
        return selected | {"simulations": simulations, "search_value": value}
    name, _, target = best.partition("@")
    model = next(model for model, short in CARD_NAMES.items() if short == name)
    if name == "Armaments":
        selected = next(action for action in actions if action.get("card_id") == model and action.get("target_id") is None)
        if target.isdigit():
            played_index = next(index for index, card in enumerate(observation["hand"]) if card["id"] == model)
            target_index = int(target) + (int(target) >= played_index)
            selected = selected | {"upgrade_hand_index": target_index}
        return selected | {"simulations": simulations, "search_value": value}
    target_id = observation["enemies"][int(target)]["combat_id"] if target else None
    selected = next(action for action in actions if action.get("card_id") == model and action.get("target_id") == target_id)
    return selected | {"simulations": simulations, "search_value": value}


def atomic_write(path: str, value: dict) -> None:
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as file:
        json.dump(value, file)
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal external agent for the official STS2 engine")
    parser.add_argument("observation")
    parser.add_argument("action")
    parser.add_argument("--enemy-data", nargs="+")
    parser.add_argument("--simulations", type=int, default=0)
    parser.add_argument("--error-log")
    args = parser.parse_args()
    enemy_data = None
    if args.enemy_data:
        enemy_data = {"monsters": [monster for path in args.enemy_data for monster in json.load(open(path, encoding="utf-8-sig"))["monsters"]]}
    last_seq = -1
    while True:
        try:
            with open(args.observation, encoding="utf-8") as file:
                observation = json.load(file)
            if observation.get("terminal"):
                return
            if observation["seq"] != last_seq:
                action = choose(observation, enemy_data, args.simulations) | {"seq": observation["seq"]}
                atomic_write(args.action, action)
                last_seq = observation["seq"]
        except (OSError, json.JSONDecodeError):
            pass
        except Exception:
            if "observation" in locals() and not observation.get("terminal") and observation.get("seq") != last_seq:
                if args.error_log:
                    with open(args.error_log, "a", encoding="utf-8") as file:
                        file.write(traceback.format_exc())
                action = next((action for action in observation.get("legal_actions", ()) if action["type"] == "end_turn"), None)
                if action:
                    atomic_write(args.action, action | {"seq": observation["seq"]})
                    last_seq = observation["seq"]
        time.sleep(0.025)


if __name__ == "__main__":
    main()
