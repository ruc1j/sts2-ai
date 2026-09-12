from __future__ import annotations

import argparse
import json
import os
import random
import time
import traceback
from dataclasses import replace
from itertools import combinations

from combat import (
    ALL_ENEMY_DAMAGE, BRILLIANT_SCARF_FREE_AFTER, CARD_COST, EXHAUSTS, PACTS_END_EXHAUST_REQUIRED, Card, Combat, Enemy, POTION_BLOCK, POTION_BLOOD, POTION_BRONZE, POTION_DEXTERITY, POTION_ENERGY,
    POTION_EXPLOSIVE, POTION_FIRE, POTION_FYSH, POTION_HEART, POTION_SHAPED_ROCK, POTION_SHIP,
    POTION_STRENGTH, SELF_DAMAGE, _resolve_move, card_name, search,
)


CARD_NAMES = {
    "CARD.STRIKE_IRONCLAD": "Strike",
    "CARD.DEFEND_IRONCLAD": "Defend",
    "CARD.BASH": "Bash",
    "CARD.ANGER": "Anger",
    "CARD.AGGRESSION": "Aggression",
    "CARD.DARK_EMBRACE": "Dark Embrace",
    "CARD.CRIMSON_MANTLE": "Crimson Mantle",
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
    "CARD.DECAY": "Decay",
    "CARD.NORMALITY": "Normality",
    "CARD.FRANTIC_ESCAPE": "Frantic Escape",
    "CARD.IRON_WAVE": "Iron Wave",
    "CARD.TWIN_STRIKE": "Twin Strike",
    "CARD.CINDER": "Cinder",
    "CARD.ASHEN_STRIKE": "Ashen Strike",
    "CARD.HEMOKINESIS": "Hemokinesis",
    "CARD.PERFECTED_STRIKE": "Perfected Strike",
    "CARD.INFLAME": "Inflame",
    "CARD.INFERNO": "Inferno",
    "CARD.CRUELTY": "Cruelty",
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
    "CARD.TORIC_TOUGHNESS": "Toric Toughness",
    "CARD.SQUASH": "Squash",
    "CARD.HAVOC": "Havoc",
    "CARD.STOKE": "Stoke",
    "CARD.METAMORPHOSIS": "Metamorphosis",
    "CARD.VICIOUS": "Vicious",
    "CARD.TEAR_ASUNDER": "Tear Asunder",
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
    "CARD.FASTEN": "Fasten",
    "CARD.MAD_SCIENCE": "Mad Science",
    "CARD.NEOWS_FURY": "Neow's Fury",
    "CARD.DEMON_FORM": "Demon Form",
    "CARD.ULTIMATE_STRIKE": "Ultimate Strike",
    "CARD.FLAME_BARRIER": "Flame Barrier",
    "CARD.MOLTEN_FIST": "Molten Fist",
    "CARD.NOT_YET": "Not Yet",
    "CARD.OFFERING": "Offering",
    "CARD.BLOOD_WALL": "Blood Wall",
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
    "CARD.UNMOVABLE": "Unmovable",
    "CARD.EXPECT_A_FIGHT": "Expect a Fight",
    "CARD.FORGOTTEN_RITUAL": "Forgotten Ritual",
    "CARD.SWORD_BOOMERANG": "Sword Boomerang",
    "CARD.HELLRAISER": "Hellraiser",
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
    # The live bridge only ever emits the _POWER form; without it Frail was silently dropped from
    # every rollout state and the model overestimated its own block by a third.
    "POWER.FRAIL_POWER": "FrailPower",
    "POWER.VIGOR_POWER": "VigorPower",
    "POWER.INTANGIBLE_POWER": "IntangiblePower",
    "POWER.TANGLED_POWER": "TangledPower",
    "POWER.SLOTH_POWER": "SlothPower",
    "POWER.FREE_ATTACK_POWER": "FreeAttackPower",
    "POWER.VICIOUS_POWER": "ViciousPower",
    "POWER.TENDER_POWER": "TenderPower",
    "POWER.REGEN_POWER": "RegenPower",
    "POWER.TORIC_TOUGHNESS_POWER": "ToricToughnessPower",
    "POWER.NEMESIS_POWER": "NemesisPower",
    "POWER.NO_DRAW_POWER": "NoDrawPower",
    "POWER.RADIANCE_POWER": "RadiancePower",
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
    "POWER.CURL_UP_POWER": "CurlUpPower",
    "POWER.FLUTTER_POWER": "FlutterPower",
    "POWER.SURROUNDED_POWER": "SurroundedPower",
    "POWER.ILLUSION_POWER": "IllusionPower",
    "POWER.MINION_POWER": "MinionPower",
    "POWER.PERSONAL_HIVE_POWER": "PersonalHivePower",
    "POWER.PLOW_POWER": "PlowPower",
    "POWER.RINGING_POWER": "RingingPower",
    "POWER.SANDPIT_POWER": "SandpitPower",
    "POWER.FASTEN_POWER": "FastenPower",
    "POWER.DEMON_FORM_POWER": "DemonFormPower",
    # The observation reports these under their own ids; without the mapping combat.py never
    # sees them (the same gap that made FrailPower dead for every rollout - see CODEWIKI).
    "POWER.GALVANIC_POWER": "GalvanicPower",
    "POWER.PAPER_CUTS_POWER": "PaperCutsPower",
    "POWER.SHRINK_POWER": "ShrinkPower",
    "POWER.SLOW_POWER": "SlowPower",
    "POWER.SLUMBER_POWER": "SlumberPower",
    "POWER.SOAR_POWER": "SoarPower",
    "POWER.DEXTERITY": "DexterityPower",
    "POWER.DEXTERITY_POWER": "DexterityPower",
    "POWER.SPEED_POTION_POWER": "SpeedPotionPower",
    "POWER.SELF_FORMING_CLAY_POWER": "SelfFormingClayPower",
    "POWER.RUPTURE_POWER": "RupturePower",
    "POWER.JUGGERNAUT_POWER": "JuggernautPower",
    "POWER.INFERNO_POWER": "InfernoPower",
    "POWER.CRUELTY_POWER": "CrueltyPower",
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
    "POWER.UNMOVABLE_POWER": "UnmovablePower",
    "POWER.NO_ENERGY_GAIN_POWER": "NoEnergyGainPower",
    "POWER.AGGRESSION_POWER": "AggressionPower",
    "POWER.DARK_EMBRACE_POWER": "DarkEmbracePower",
    "POWER.BARRICADE_POWER": "BarricadePower",
    "POWER.BLOCK_NEXT_TURN_POWER": "BlockNextTurnPower",
    "POWER.COLOSSUS_POWER": "ColossusPower",
    "POWER.HELLRAISER_POWER": "HellraiserPower",
    "POWER.CRIMSON_MANTLE_POWER": "CrimsonMantlePower",
    "POWER.BURROWED_POWER": "BurrowedPower",
    "POWER.STEAM_ERUPTION_POWER": "SteamEruptionPower",
}

KNOWN_CARD_DAMAGE = {
    "CARD.STRIKE_IRONCLAD": 6,
    "CARD.BASH": 8,
    "CARD.ANGER": 6,
    "CARD.BLUDGEON": 32,
    "CARD.STOMP": 12,
    "CARD.DISMANTLE": 8,
    "CARD.IRON_WAVE": 5,
    "CARD.TWIN_STRIKE": 5,
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
    "CARD.SWORD_BOOMERANG": 9,
    "CARD.WHIRLWIND": 5,
}
# These cards expose their canonical damage per hit; _card_value applies the live hit count.
CARD_HIT_COUNTS = {"CARD.TWIN_STRIKE": 2}
# Dynamic damage cards still need to count as attacks when a reward also offers a strong block.
ATTACK_REWARD_CARDS = set(KNOWN_CARD_DAMAGE) | {"CARD.ASHEN_STRIKE", "CARD.PERFECTED_STRIKE"}
KNOWN_CARD_BLOCK = {
    "CARD.DEFEND_IRONCLAD": 5,
    "CARD.SHRUG_IT_OFF": 8,
    "CARD.RELAX": 15,
    "CARD.IRON_WAVE": 5,
    "CARD.EQUILIBRIUM": 13,
    "CARD.BLOOD_WALL": 16,
    "CARD.TAUNT": 7,
    "CARD.TRUE_GRIT": 7,
    "CARD.EVIL_EYE": 8,
    "CARD.COLOSSUS": 5,
    # Immediate block only; the two delayed re-grants land on later turns.
    "CARD.TORIC_TOUGHNESS": 5,
}


def _number(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _intent_incoming(enemy: dict) -> int:
    # CombatBridge reports intent damage via GetSingleDamage, which already includes
    # Strength/Weak/Vulnerable, so the observed damage is used as-is.
    if "hp" in enemy and _number(enemy.get("hp")) <= 0:
        return 0
    return sum(max(0, _number(intent.get("damage"))) * max(1, _number(intent.get("repeats"), 1)) for intent in enemy.get("intents") or ())


_LAST_POTION_CONTEXT: tuple[object, ...] | None = None
_LAST_POTION_ID: str | None = None
_POTION_USED_ROOM: tuple[object, object] | None = None
ROLLOUT_POTION_IDS = {
    POTION_BLOCK, POTION_SHIP, POTION_FIRE, POTION_EXPLOSIVE, POTION_SHAPED_ROCK,
    POTION_STRENGTH, POTION_DEXTERITY, POTION_FYSH, POTION_ENERGY, POTION_BLOOD, POTION_HEART, POTION_BRONZE,
}


def _potion_context(observation: dict) -> tuple[object, ...] | None:
    run = observation.get("run")
    turn = observation.get("turn")
    enemies = tuple((enemy.get("combat_id"), enemy.get("id")) for enemy in observation.get("enemies", ()))
    if not isinstance(run, dict) or run.get("act") is None or run.get("floor") is None or turn is None or not enemies:
        return None
    return (run["act"], run["floor"], turn, enemies)


def _potion_room(observation: dict) -> tuple[object, object] | None:
    run = observation.get("run")
    if not isinstance(run, dict) or run.get("room_type") != "Monster" or run.get("act") is None or run.get("floor") is None:
        return None
    return (run["act"], run["floor"])


def _potion_is_lethal_incoming(observation: dict) -> bool:
    player = observation.get("player") or {}
    hp = _number(player.get("hp"))
    incoming = sum(_intent_incoming(enemy) for enemy in observation.get("enemies", ()))
    incoming = max(0, incoming - _number(player.get("block")))
    hits = [
        max(0, _number(intent.get("damage")))
        for enemy in observation.get("enemies", ())
        if enemy.get("hp") is None or _number(enemy.get("hp")) > 0
        for intent in enemy.get("intents") or ()
        for _ in range(max(1, _number(intent.get("repeats"), 1)))
    ]
    if any(power.get("id") == "POWER.BUFFER_POWER" and _number(power.get("amount")) > 0 for power in player.get("powers", ())):
        incoming = max(0, incoming - max(hits, default=0))
    return incoming >= hp


def _card_hit_count(card_id: str | None, energy: int | None = None) -> int:
    if card_id == "CARD.WHIRLWIND":
        return _number(energy, 1) if energy is not None else 1
    return CARD_HIT_COUNTS.get(card_id, 1)


def _card_value(action: dict, hand: dict[int, dict], metric: str, energy: int | None = None) -> int:
    card_id = action.get("card_id")
    card = hand.get(action.get("hand_index"), {})
    if metric == "vulnerable" and card_id in {"CARD.BASH", "CARD.BREAK", "CARD.SQUASH", "CARD.UPPERCUT"}:
        return 1
    values = []
    calculated = []
    for variable in card.get("vars") or ():
        name = str(variable.get("id", "")).lower()
        if metric not in name:
            continue
        value = _number(variable.get("value"))
        (calculated if "calculated" in name else values).append(value)
    if calculated:
        value = max(calculated)
    elif values:
        value = max(values)
    else:
        value = (KNOWN_CARD_DAMAGE if metric == "damage" else KNOWN_CARD_BLOCK).get(card_id, 0)
    return value * _card_hit_count(card_id, energy) if metric == "damage" else value


def _is_self_damage(action: dict, hand: dict[int, dict]) -> bool:
    card = hand.get(action.get("hand_index"), {})
    if card.get("enchantment") == "ENCHANTMENT.CORRUPTED":
        return True
    if action.get("card_id") in UNCOMMITTED_SELF_DAMAGE or card.get("id") in UNCOMMITTED_SELF_DAMAGE:
        return True
    return any(
        any(marker in str(variable.get("id", "")).lower().replace("_", "") for marker in ("selfdamage", "hploss", "healthloss"))
        for variable in card.get("vars") or ()
    )


def _self_damage_value(action: dict, hand: dict[int, dict]) -> int:
    card = hand.get(action.get("hand_index"), {})
    observed = [
        _number(variable.get("value"))
        for variable in card.get("vars") or ()
        if any(marker in str(variable.get("id", "")).lower().replace("_", "") for marker in ("selfdamage", "hploss", "healthloss"))
    ]
    card_name = CARD_NAMES.get(action.get("card_id") or card.get("id"), "")
    return max(observed, default=SELF_DAMAGE.get(card_name, 0)) + (2 if card.get("enchantment") == "ENCHANTMENT.CORRUPTED" else 0)


# Fixed Act 1 Neow order. This intentionally ignores the deck and player HP; other events use
# the conditional relic scoring below.
NEOW_RELIC_PRIORITY = (
    "RELIC.SMALL_CAPSULE", "RELIC.LARGE_CAPSULE", "RELIC.NEOWS_TALISMAN", "RELIC.GOLDEN_PEARL",
    "RELIC.LOST_COFFER", "RELIC.PHIAL_HOLSTER", "RELIC.FISHING_ROD", "RELIC.NUTRITIOUS_OYSTER",
    "RELIC.STONE_HUMIDIFIER", "RELIC.SCROLL_BOXES", "RELIC.POMANDER", "RELIC.ARCANE_SCROLL",
    "RELIC.LEAD_PAPERWEIGHT", "RELIC.NEW_LEAF", "RELIC.NEOWS_TORMENT", "RELIC.PRECISE_SCISSORS",
    "RELIC.BOOMING_CONCH", "RELIC.SILVER_CRUCIBLE", "RELIC.LAVA_ROCK", "RELIC.WINGED_BOOTS",
    "RELIC.KALEIDOSCOPE", "RELIC.PRECARIOUS_SHEARS", "RELIC.SILKEN_TRESS", "RELIC.LEAFY_POULTICE",
    "RELIC.HEFTY_TABLET", "RELIC.CURSED_PEARL", "RELIC.NEOWS_BONES", "RELIC.MASSIVE_SCROLL",
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

# Shop potions are a one-use answer to the next elite/boss, so prefer only known defensive or
# high-impact options and leave unknown/self-damaging potions for the normal reward path.
SHOP_POTION_SCORES = {
    "POTION.SHACKLING_POTION": 9, "POTION.GHOST_IN_A_JAR": 9,
    "POTION.BLOCK_POTION": 8, "POTION.SHIP_IN_A_BOTTLE": 8,
    "POTION.HEART_OF_IRON": 8, "POTION.FYSH_OIL": 8,
    "POTION.DEXTERITY_POTION": 8, "POTION.SPEED_POTION": 8,
    "POTION.REGEN_POTION": 7, "POTION.CURE_ALL": 7,
    "POTION.ENERGY_POTION": 7, "POTION.SKILL_POTION": 7,
    "POTION.STRENGTH_POTION": 7, "POTION.POWER_POTION": 7,
    "POTION.LUCKY_TONIC": 7, "POTION.POTION_OF_BINDING": 7,
}
SHOP_POTION_MIN_SCORE = 7

# The bridge reports boss slots directly. Keep the HP fallback for older unit fixtures that omit
# both slot and id, but do not mistake a high-HP regular (e.g. Louse Progenitor) for a boss.
RESERVED_COMBAT_POTIONS = {
    "POTION.SHACKLING_POTION", "POTION.GHOST_IN_A_JAR", "POTION.BLOCK_POTION",
    "POTION.SHIP_IN_A_BOTTLE", "POTION.HEART_OF_IRON", "POTION.FYSH_OIL",
    "POTION.DEXTERITY_POTION", "POTION.SPEED_POTION", "POTION.REGEN_POTION",
    "POTION.CURE_ALL", "POTION.SKILL_POTION", "POTION.POWER_POTION", "POTION.STRENGTH_POTION",
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
    event_id = observation.get("event_id", "")
    if event_id == "NEOW":
        neow_relic_actions = [action for action in actions if action.get("relic_id")]
        if neow_relic_actions:
            priority = {relic_id: index for index, relic_id in enumerate(NEOW_RELIC_PRIORITY)}
            return min(
                neow_relic_actions,
                key=lambda action: priority.get(action.get("relic_id"), len(priority)),
            )
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


def _tag_action(action: dict, source: str, reason: str | None = None) -> dict:
    tagged = dict(action)
    tagged["decision_source"] = source
    if reason is not None:
        tagged["decision_reason"] = reason
    return tagged


def choose(observation: dict, enemy_data: dict | None = None, simulations: int = 0) -> dict:
    global _LAST_POTION_CONTEXT, _LAST_POTION_ID, _POTION_USED_ROOM
    if observation.get("phase") == "shop":
        return _tag_action(choose_shop(observation), "phase_shop")
    if observation.get("phase") == "map":
        return _tag_action(choose_map(observation), "phase_map")
    if observation.get("phase") == "card_reward":
        return _tag_action(choose_card_reward(observation), "phase_card_reward")
    if observation.get("phase") == "rest":
        return _tag_action(choose_rest(observation), "phase_rest")
    if observation.get("phase") == "event":
        return _tag_action(choose_event(observation), "phase_event")
    if observation.get("phase") == "potion_reward":
        return _tag_action(choose_potion_reward(observation), "phase_potion_reward")
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
    hand = {card.get("index"): card for card in observation.get("hand", ()) if card.get("index") is not None}
    player = observation.get("player", {})
    card_energy = _number(player.get("energy"))
    if "RELIC.CHEMICAL_X" in (player.get("relics") or ()):
        card_energy += 2

    def card_value(action: dict, metric: str) -> int:
        return _card_value(action, hand, metric, card_energy)

    sandpit_critical = any(power["id"] == "POWER.SANDPIT_POWER" and 0 < power["amount"] <= 2 for enemy in observation.get("enemies", ()) for power in enemy.get("powers", ()))
    escape = min(
        (action for action in cards if action["card_id"] == "CARD.FRANTIC_ESCAPE"),
        key=lambda action: _number(hand.get(action.get("hand_index"), {}).get("cost"), 1),
        default=None,
    )
    potion_context = _potion_context(observation)
    potion_room = _potion_room(observation)
    if potion_context is None:
        _LAST_POTION_CONTEXT = None
        _LAST_POTION_ID = None
    elif potion_context != _LAST_POTION_CONTEXT:
        _LAST_POTION_ID = None
    if potion_room is None:
        _POTION_USED_ROOM = None
    duplicator_primal_force_guard = (
        potion_context is not None
        and potion_context == _LAST_POTION_CONTEXT
        and _LAST_POTION_ID == "POTION.DUPLICATOR"
    )
    if duplicator_primal_force_guard:
        # Duplicator replays PrimalForce.OnPlay; the replay tries to transform generated
        # Giant Rocks again and the engine crashes because those cards have no hand node.
        actions = [action for action in actions if action.get("card_id") != "CARD.PRIMAL_FORCE"]
        cards = [action for action in cards if action.get("card_id") != "CARD.PRIMAL_FORCE"]
    potion_lethal = _potion_is_lethal_incoming(observation)
    potion_hp = _number((observation.get("player") or {}).get("hp"))
    potion_max_hp = _number((observation.get("player") or {}).get("max_hp"), potion_hp)
    potion_threatening = sum(_intent_incoming(enemy) for enemy in observation.get("enemies", ())) >= max(1, potion_hp // 2)
    potion_urgent = potion_lethal or (
        sandpit_critical and (potion_hp <= max(1, potion_max_hp // 3) or potion_threatening)
    )
    potion_already_used = potion_room is not None and potion_room == _POTION_USED_ROOM
    if not enemy_data:
        rollout_reason = "rollout_disabled_no_data"
    elif not simulations:
        rollout_reason = "rollout_disabled_no_simulations"
    elif not any(card["card_id"] in CARD_NAMES for card in cards):
        rollout_reason = "rollout_disabled_no_playable_card"
    else:
        rollout_reason = None
    rollout_enabled = rollout_reason is None and not duplicator_primal_force_guard

    enemy_by_id = {
        enemy.get("combat_id"): enemy
        for enemy in observation.get("enemies", ())
        if enemy.get("combat_id") is not None
    }
    enemy_incoming = {
        enemy.get("combat_id"): _intent_incoming(enemy)
        for enemy in observation.get("enemies", ())
        if enemy.get("combat_id") is not None
    }

    def damage(action: dict, enemy: dict | None = None) -> int:
        if enemy is None:
            enemy = enemy_by_id.get(action.get("target_id"))
        if enemy is None:
            return 0
        if (
            action.get("card_id") == "CARD.PACTS_END"
            and len(observation.get("exhaust_pile") or ()) < PACTS_END_EXHAUST_REQUIRED
        ):
            # CanDealDamage is false, so the card resolves for nothing. Without this the lethal
            # gate "confirms" a kill and burns the turn (astra_goal_suicide1 seq483 played it at
            # 9 boss HP with one card exhausted, dealt 0, and died to the next attack).
            return 0
        hits = _card_hit_count(action.get("card_id"), card_energy)
        # Slippery enemies reduce every hit to 1 until the power is spent; Intangible (Test
        # Subject's third form, toggled on and off by Nemesis) does the same without wearing off.
        if any(
            power.get("id") in {"POWER.SLIPPERY_POWER", "POWER.INTANGIBLE_POWER"}
            and _number(power.get("amount")) > 0
            for power in enemy.get("powers", ())
        ):
            return hits
        value = card_value(action, "damage")
        if value <= 0:
            value = ALL_ENEMY_DAMAGE.get(CARD_NAMES.get(action.get("card_id")), 0)
        if (
            hand.get(action.get("hand_index"), {}).get("type") == "Attack"
            and any(
                power.get("id") in {"POWER.VULNERABLE", "POWER.VULNERABLE_POWER"}
                and _number(power.get("amount")) > 0
                for power in enemy.get("powers", ())
            )
        ):
            cruelty = next((
                _number(power.get("amount")) for power in player.get("powers", ())
                if power.get("id") == "POWER.CRUELTY_POWER"
            ), 0)
            phrog = 25 if "RELIC.PAPER_PHROG" in (player.get("relics") or ()) else 0
            value = value * (150 + phrog + cruelty) // 100
        # SoarPower halves each powered card hit before HardToKill caps it.  Keep this in the
        # heuristic too, otherwise the pre-rollout lethal gate can select a false kill.
        if any(power.get("id") == "POWER.SOAR_POWER" and _number(power.get("amount")) > 0 for power in enemy.get("powers", ())):
            value = (value // hits // 2) * hits
        # HardToKill (e.g. Exoskeleton) caps every hit at the power amount.
        caps = [_number(power.get("amount")) for power in enemy.get("powers", ()) if power.get("id") == "POWER.HARD_TO_KILL_POWER" and _number(power.get("amount")) > 0]
        if caps and hits:
            return min(value // hits, max(caps)) * hits
        return value

    def lethal_targets(action: dict) -> tuple[dict, ...]:
        target_id = action.get("target_id")
        if target_id is None and action.get("card_id") in ALL_ENEMY_CARDS:
            targets = enemy_by_id.values()
        elif target_id in enemy_by_id:
            targets = (enemy_by_id[target_id],)
        else:
            return ()
        return tuple(
            enemy
            for enemy in targets
            if _number(enemy.get("hp")) > 0
            and damage(action, enemy) - _number(enemy.get("block")) >= _number(enemy.get("hp"))
        )

    def is_lethal(action: dict) -> bool:
        return bool(lethal_targets(action))

    lethal = [
        action for action in cards
        if is_lethal(action)
        and (not _is_self_damage(action, hand) or _self_damage_value(action, hand) < _number(player.get("hp")))
    ]
    alive_decimillipede_ids = {
        enemy.get("combat_id")
        for enemy in enemy_by_id.values()
        if str(enemy.get("id", "")).startswith("MONSTER.DECIMILLIPEDE_SEGMENT")
        and _number(enemy.get("hp")) > 0
    }
    if len(alive_decimillipede_ids) > 1:
        lethal = [action for action in lethal if action.get("target_id") not in alive_decimillipede_ids]
    obscura_id = next((enemy.get("combat_id") for enemy in enemy_by_id.values() if enemy.get("id") == "MONSTER.THE_OBSCURA" and _number(enemy.get("hp")) > 0), None)
    obscura_present = obscura_id is not None
    if obscura_present:
        lethal = [
            action for action in lethal
            if any(enemy.get("id") != "MONSTER.PARAFRIGHT" for enemy in lethal_targets(action))
            or (
                sum(enemy_incoming.values()) - _number(player.get("block")) - card_value(action, "block") >= _number(player.get("hp"))
                and sum(enemy_incoming.values())
                - sum(enemy_incoming.get(enemy.get("combat_id"), 0) for enemy in lethal_targets(action))
                - _number(player.get("block"))
                - card_value(action, "block") < _number(player.get("hp"))
            )
        ]
    incoming_threats = {combat_id for combat_id, value in enemy_incoming.items() if value > 0}
    lethal_attacks = [action for action in lethal if not _is_self_damage(action, hand)]
    lethal_target_ids = {
        enemy.get("combat_id")
        for action in lethal_attacks
        for enemy in lethal_targets(action)
        if enemy.get("combat_id") is not None
    }
    potion_lethal_now = bool(lethal_attacks) and (
        not incoming_threats or incoming_threats <= lethal_target_ids
    )
    def affordable_block(excluded_index: int | None, budget: int) -> int:
        defenses = {
            action.get("hand_index"): action for action in cards
            if action.get("hand_index") != excluded_index and card_value(action, "block") > 0
        }
        return max((
            sum(card_value(action, "block") for action in group)
            for count in range(len(defenses) + 1)
            for group in combinations(defenses.values(), count)
            if sum(_number(hand.get(action.get("hand_index"), {}).get("cost")) for action in group) <= budget
        ), default=0)

    for potion in (action for action in potions if action.get("potion_id") == "POTION.VULNERABLE_POTION"):
        target = enemy_by_id.get(potion.get("target_id"))
        if not target or enemy_incoming.get(potion.get("target_id"), 0) <= 0 or any(
            power.get("id") in {"POWER.VULNERABLE", "POWER.VULNERABLE_POWER"} and _number(power.get("amount")) > 0
            for power in target.get("powers", ())
        ):
            continue
        if sum(enemy_incoming.values()) - _number(player.get("block")) - affordable_block(None, card_energy) < _number(player.get("hp")):
            continue
        for attack in (
            action for action in cards
            if action.get("target_id") == potion.get("target_id")
            and hand.get(action.get("hand_index"), {}).get("type") == "Attack"
            and not _is_self_damage(action, hand)
        ):
            target_hp = _number(target.get("hp")) + _number(target.get("block"))
            if damage(attack, target) >= target_hp or damage(attack, target) * 3 // 2 < target_hp:
                continue
            budget = card_energy - _number(hand.get(attack.get("hand_index"), {}).get("cost"))
            remaining = sum(enemy_incoming.values()) - enemy_incoming.get(potion.get("target_id"), 0)
            if remaining - _number(player.get("block")) - card_value(attack, "block") - affordable_block(attack.get("hand_index"), budget) < _number(player.get("hp")):
                return _tag_action(potion, "vulnerable_survival_potion")
    direct_potion = choose_potion(observation, potions)
    dexterity_potions = {"POTION.DEXTERITY_POTION", "POTION.SPEED_POTION"}
    duplicate_dexterity_potion = (
        potion_room is not None
        and potion_context is not None
        and potion_context == _LAST_POTION_CONTEXT
        and _LAST_POTION_ID in dexterity_potions
        and (direct_potion or {}).get("potion_id") in dexterity_potions
    )
    if (
        (not rollout_enabled or potion_urgent or (direct_potion or {}).get("potion_id") not in ROLLOUT_POTION_IDS)
        and (not sandpit_critical or potion_urgent)
        and (
            potion_context is None
            or potion_context != _LAST_POTION_CONTEXT
            or potion_urgent
        )
        and (not potion_already_used or potion_lethal)
        and not duplicate_dexterity_potion
        and not potion_lethal_now
        and direct_potion
    ):
        if potion_context is not None:
            _LAST_POTION_CONTEXT = potion_context
            _LAST_POTION_ID = direct_potion.get("potion_id")
        if potion_room is not None:
            _POTION_USED_ROOM = potion_room
        return _tag_action(direct_potion, "direct_potion")
    if sandpit_critical and not lethal:
        if escape:
            return _tag_action(escape, "sandpit_escape")
        draw_cards = [action for action in cards if action["card_id"] in DRAW_CARDS]
        battle_trance = next((action for action in draw_cards if action.get("card_id") == "CARD.BATTLE_TRANCE" and _number(hand.get(action.get("hand_index"), {}).get("cost")) == 0), None)
        if battle_trance and not any(power.get("id") == "POWER.NO_DRAW_POWER" for power in player.get("powers", ())):
            draw = max(
                (_number(variable.get("value")) for variable in hand[battle_trance["hand_index"]].get("vars", ()) if variable.get("id") == "Cards"),
                default=0,
            )
            if draw and len(hand) + draw <= 10:
                return _tag_action(battle_trance, "sandpit_draw")
        if draw_cards:
            return _tag_action(max(draw_cards, key=lambda action: (card_value(action, "block"), card_value(action, "damage"))), "sandpit_draw")
    if not lethal and (turn := choose_crab_facing(observation, cards)):
        return _tag_action(turn, "crab_facing_direct")

    free_inflame = next((
        action for action in cards
        if action.get("card_id") == "CARD.INFLAME"
        and hand.get(action.get("hand_index"), {}).get("cost") == 0
    ), None)
    if free_inflame:
        return _tag_action(free_inflame, "free_inflame_direct")

    # In a multi-enemy fight, a modeled rollout can still favor a single-target line because it
    # undervalues the next combined hit. Prefer an available all-enemy card before rolling out
    # when that combined threat is already large; lethal single-target attacks remain untouched.
    hp, max_hp = player.get("hp", 0), player.get("max_hp", player.get("hp", 0))
    incoming = sum(enemy_incoming.values())
    aoe = [action for action in cards if action["card_id"] in ALL_ENEMY_CARDS and not _is_self_damage(action, hand)]
    current_block = _number(player.get("block"))
    defense_block = max((card_value(action, "block") for action in cards), default=0)
    defense_can_survive = defense_block > 0 and incoming - current_block - defense_block < hp
    # Enemies that are actually swinging this turn - a defending or buffing enemy adds nothing to
    # the combined hit this shortcut is meant to answer.
    attackers = sum(1 for damage in enemy_incoming.values() if damage > 0)
    if (
        attackers > 1
        and aoe
        and not lethal
        and (incoming < hp + current_block or not defense_can_survive)
        and incoming >= max(1, hp // 2)
    ):
        return _tag_action(max(aoe, key=lambda action: card_value(action, "damage")), "aoe_threat_direct")

    # Queen's Torch Head Amalgam is marked as a secondary minion, but it is the only enemy
    # dealing damage while the Queen buffs/defends.  Focus it before the generic minion rule
    # hides it from target selection; lethal attacks and the AOE branch above still win first.
    queen_present = any(enemy.get("id") == "MONSTER.QUEEN" for enemy in observation.get("enemies", ()))
    queen_minion_ids = {
        enemy["combat_id"]
        for enemy in observation.get("enemies", ())
        if queen_present and enemy.get("id") == "MONSTER.TORCH_HEAD_AMALGAM"
    }
    queen_focusable = [
        action
        for action in cards
        if action.get("target_id") in queen_minion_ids
        and card_value(action, "damage") > 0
        and not _is_self_damage(action, hand)
    ]
    if queen_focusable and not lethal:
        rupture_active = any(power.get("id") == "POWER.RUPTURE_POWER" for power in player.get("powers", ()))
        if not rupture_active:
            rupture = next((action for action in cards if action.get("card_id") == "CARD.RUPTURE"), None)
            if rupture:
                return _tag_action(rupture, "rupture_before_queen_focus")
        bloodletting = next((action for action in cards if action.get("card_id") == "CARD.BLOODLETTING"), None)
        if bloodletting and _self_damage_value(bloodletting, hand) + max(0, incoming - current_block) < hp:
            return _tag_action(bloodletting, "queen_focus_energy")
        urgent = hp <= max_hp // 2 or incoming >= max(1, hp // 2)
        defenses = [action for action in cards if card_value(action, "block") > 0]
        remaining = max(0, incoming - _number(player.get("block")))
        best_block = max((card_value(action, "block") for action in defenses), default=0)
        if not urgent or best_block < remaining:
            return _tag_action(max(queen_focusable, key=lambda action: card_value(action, "damage")), "queen_minion_direct")

    ovicopter = next((enemy for enemy in enemy_by_id.values() if enemy.get("id") == "MONSTER.OVICOPTER"), None)
    if lethal and ovicopter and not any(ovicopter in lethal_targets(action) for action in lethal):
        finishers = [action for action in cards if action.get("target_id") == ovicopter.get("combat_id") and damage(action, ovicopter) > 0]
        for setup in (action for action in finishers if card_value(action, "vulnerable") > 0):
            nunchaku_out = (
                "RELIC.NUNCHAKU" in player.get("relics", ())
                and incoming - current_block - defense_block >= hp
            )
            budget = card_energy + int(nunchaku_out) - _number(hand[setup.get("hand_index")].get("cost"))
            total = damage(setup, ovicopter)
            for action in sorted(finishers, key=lambda candidate: -damage(candidate, ovicopter)):
                if action.get("hand_index") == setup.get("hand_index"):
                    continue
                cost = _number(hand[action.get("hand_index")].get("cost"))
                if cost <= budget:
                    budget -= cost
                    total += damage(action, ovicopter) * 3 // 2
            if total >= _number(ovicopter.get("hp")) + _number(ovicopter.get("block")):
                return _tag_action(setup, "vulnerable_multi_lethal_direct")
        for first in finishers:
            for second in finishers:
                if first.get("hand_index") == second.get("hand_index"):
                    continue
                cost = sum(_number(hand[action.get("hand_index")].get("cost")) for action in (first, second))
                if cost <= card_energy and damage(first, ovicopter) + damage(second, ovicopter) >= _number(ovicopter.get("hp")) + _number(ovicopter.get("block")):
                    return _tag_action(max((first, second), key=lambda action: damage(action, ovicopter)), "ovicopter_turn_lethal_direct")

    if lethal:
        killers = [action for action in lethal if not _is_self_damage(action, hand)] or lethal
        # Never let stochastic rollout trade a guaranteed kill for a different target; this is
        # especially important when a dangerous minion can be finished immediately.
        def lethal_key(action: dict) -> tuple[int, int, int, int]:
            targets = lethal_targets(action)
            return (
                sum(enemy_incoming.get(enemy.get("combat_id"), 0) for enemy in targets),
                len(targets),
                -min((_number(enemy.get("hp")) for enemy in targets), default=0),
                max((damage(action, enemy) for enemy in targets), default=0),
            )
        return _tag_action(max(killers, key=lethal_key), "lethal_direct")

    # Rage (Whenever you play an Attack this turn, gain Block) only pays off for attacks played
    # AFTER it - a D6 live trace played Anger/Strike/Defend first and Rage last, forfeiting the
    # whole turn's Rage block. Force Rage ahead of an attack whenever one is still affordable
    # afterward, unless an incoming hit exceeds its base block and a stronger defense is ready.
    rage = next((action for action in cards if action["card_id"] == "CARD.RAGE"), None)
    if rage:
        remaining_energy = _number(player.get("energy")) - _number(hand.get(rage.get("hand_index"), {}).get("cost"), 1)
        attack_after_rage = any(
            action.get("card_id") != "CARD.RAGE"
            and not _is_self_damage(action, hand)
            and card_value(action, "damage") > 0
            and _number(hand.get(action.get("hand_index"), {}).get("cost"), 1) <= remaining_energy
            for action in cards
        )
        remaining = max(0, incoming - _number(player.get("block")))
        if attack_after_rage and (remaining > 0 or not rollout_enabled):
            # combat.py models Rage as 3 block per attack (5 when upgraded).
            rage_block = 5 if _number(hand.get(rage.get("hand_index"), {}).get("upgrade")) else 3
            defenses = [action for action in cards if card_value(action, "block") > 0]
            best_defense = max(defenses, key=lambda action: card_value(action, "block"), default=None)
            if best_defense and remaining > rage_block and card_value(best_defense, "block") > rage_block:
                return _tag_action(best_defense, "rage_defense_direct")
            return _tag_action(rage, "rage_direct")

    # In urgent multi-primary fights, spreading single-target damage leaves every attacker alive.
    # Keep lethal and urgent-defense decisions above this light tie-break, then focus the
    # next attack on the enemy with the largest incoming hit (lowest HP breaks ties).
    minion_ids = {
        enemy["combat_id"]
        for enemy in observation.get("enemies", ())
        if any(power.get("id") == "POWER.MINION_POWER" and _number(power.get("amount")) > 0 for power in enemy.get("powers", ()))
    }
    if obscura_present:
        minion_ids.update(enemy["combat_id"] for enemy in enemy_by_id.values() if enemy.get("id") == "MONSTER.PARAFRIGHT")
    kin_follower_ids = {
        enemy["combat_id"]
        for enemy in observation.get("enemies", ())
        if enemy.get("id") == "MONSTER.KIN_FOLLOWER"
        and enemy.get("combat_id") is not None
        and _number(enemy.get("hp")) > 0
    }
    kin_focus_id = min(
        kin_follower_ids,
        key=lambda combat_id: (
            _number(enemy_by_id[combat_id].get("hp")),
            -enemy_incoming.get(combat_id, 0),
            combat_id,
        ),
        default=None,
    )
    primary_ids = {
        combat_id
        for combat_id, enemy in enemy_by_id.items()
        if _number(enemy.get("hp")) > 0 and combat_id not in minion_ids
    } | kin_follower_ids
    primary_ids -= {
        enemy["combat_id"]
        for enemy in observation.get("enemies", ())
        if str(enemy.get("id", "")).startswith("MONSTER.DECIMILLIPEDE_SEGMENT")
    }
    decimillipede_ids = {
        enemy["combat_id"]
        for enemy in observation.get("enemies", ())
        if str(enemy.get("id", "")).startswith("MONSTER.DECIMILLIPEDE_SEGMENT")
        and _number(enemy.get("hp")) > 0
    }
    decimillipede_focus_id = max(
        decimillipede_ids,
        key=lambda combat_id: (_number(enemy_by_id[combat_id].get("hp")), enemy_incoming.get(combat_id, 0)),
        default=None,
    )
    focusable = [
        action
        for action in cards
        if action.get("target_id") in primary_ids
        and card_value(action, "damage") > 0
        and not _is_self_damage(action, hand)
    ]
    urgent = hp <= max_hp // 2 or incoming >= max(1, hp // 2)
    two_card_kills = []
    if len(primary_ids) > 1 and urgent:
        for first in focusable:
            target_id = first.get("target_id")
            for second in focusable:
                if second.get("target_id") != target_id or second.get("hand_index") == first.get("hand_index"):
                    continue
                cost = sum(_number(hand.get(action.get("hand_index"), {}).get("cost")) for action in (first, second))
                setup_strength = card_value(first, "strength") if first.get("card_id") == "CARD.SETUP_STRIKE" else 0
                if cost < card_energy and card_value(first, "damage") + card_value(second, "damage") + setup_strength >= _number(enemy_by_id[target_id].get("hp")):
                    two_card_kills.append(first)
                    break
    if two_card_kills:
        return _tag_action(
            max(two_card_kills, key=lambda action: (enemy_incoming.get(action["target_id"], 0), card_value(action, "damage"))),
            "two_card_lethal_setup_direct",
        )
    if (
        len(primary_ids) > 1 and focusable and not lethal and urgent and not kin_follower_ids
        and (defense_block <= 0 or incoming * 2 < hp)
    ):
        source = "generic_multi_primary_focus_direct"
        return _tag_action(
            max(
                focusable,
                key=lambda action: (
                    action["target_id"] in kin_follower_ids,
                    enemy_incoming.get(action["target_id"], 0),
                    -enemy_by_id[action["target_id"]].get("hp", 0),
                    card_value(action, "damage"),
                ),
            ),
            source,
        )
    # The Kin's Followers are the immediate damage source; keep attacking one during an urgent
    # turn when no available block card can cover the remaining hit and the player still survives.
    if len(primary_ids) > 1 and kin_follower_ids and not lethal and urgent and incoming < hp + player.get("block", 0):
        kin_focusable = [action for action in focusable if action.get("target_id") in kin_follower_ids]
        remaining = max(0, incoming - player.get("block", 0))
        best_block = max((card_value(action, "block") for action in cards), default=0)
        if kin_focusable and (not remaining or best_block < remaining):
            preferred = [action for action in kin_focusable if action.get("target_id") == kin_focus_id]
            if preferred:
                kin_focusable = preferred
            return _tag_action(
                max(kin_focusable, key=lambda action: card_value(action, "damage")),
                "kin_follower_urgent_direct",
            )

    def mitigation_incoming(action: dict) -> int:
        card_id = action.get("card_id")
        if card_id not in {"CARD.UPPERCUT", "CARD.MANGLE"}:
            return incoming
        target_id = action.get("target_id")
        target = enemy_by_id.get(target_id)
        current = enemy_incoming.get(target_id, 0)
        if target is None or current <= 0:
            return incoming
        repeats = lambda intent: max(1, _number(intent.get("repeats"), 1))
        if card_id == "CARD.UPPERCUT":
            projected = sum(
                max(0, _number(intent.get("damage")) * 3 // 4) * repeats(intent)
                for intent in target.get("intents") or ()
            )
        else:
            upgrade = _number(hand.get(action.get("hand_index"), {}).get("upgrade"))
            strength_reduction = 15 if upgrade else 10
            projected = sum(
                max(0, _number(intent.get("damage")) - strength_reduction) * repeats(intent)
                for intent in target.get("intents") or ()
            )
        return incoming - current + projected

    def turn_can_clear_threats() -> bool:
        """True when the attacks affordable this turn can finish the only enemy that is swinging.

        `is_lethal` asks whether one card kills; this asks whether the turn does. Killing the
        attacker removes the entire incoming hit, so a multi-card kill beats blocking part of it -
        but only while a single enemy is the threat, since killing one of several leaves the rest.
        """
        threats = [
            enemy for enemy in observation.get("enemies", ())
            if _intent_incoming(enemy) > 0 and _number(enemy.get("hp")) > 0
        ]
        if len(threats) != 1:
            return False
        target = threats[0]
        budget, total = card_energy, 0
        for action in sorted(cards, key=lambda candidate: -damage(candidate, target)):
            dealt = damage(action, target)
            if dealt <= 0:
                continue
            cost = _number(hand.get(action.get("hand_index"), {}).get("cost"), 0)
            if cost < 0 or cost > budget:
                continue
            budget -= cost
            total += dealt
        return total >= _number(target.get("hp"))

    if incoming - current_block >= hp:
        threats = [enemy for enemy in observation.get("enemies", ()) if _intent_incoming(enemy) > 0]
        if len(threats) == 1:
            target = threats[0]
            for setup in focusable:
                if card_value(setup, "vulnerable") <= 0:
                    continue
                budget = card_energy - _number(hand.get(setup.get("hand_index"), {}).get("cost"))
                followups = sorted(
                    (
                        action for action in focusable
                        if action.get("hand_index") != setup.get("hand_index")
                        and action.get("target_id") == target.get("combat_id")
                    ),
                    key=lambda action: -damage(action, target),
                )
                total = damage(setup, target)
                attack_count = 1
                for action in followups:
                    cost = _number(hand.get(action.get("hand_index"), {}).get("cost"))
                    if cost <= budget:
                        budget -= cost
                        total += damage(action, target) * 3 // 2
                        attack_count += 1
                thorns = next((
                    _number(power.get("amount")) for power in target.get("powers", ())
                    if power.get("id") == "POWER.THORNS_POWER"
                ), 0)
                if total >= _number(target.get("hp")) + _number(target.get("block")) and thorns * attack_count < hp:
                    return _tag_action(setup, "vulnerable_multi_lethal_direct")

    if (
        hp <= max(1, max_hp // 4)
        and any(
            power.get("id") == "POWER.STRENGTH_POWER" and _number(power.get("amount")) >= 40
            for power in player.get("powers", ())
        )
        and turn_can_clear_threats()
    ):
        threat_id = next(
            enemy["combat_id"] for enemy in observation.get("enemies", ())
            if _intent_incoming(enemy) > 0 and _number(enemy.get("hp")) > 0
        )
        finishers = [
            action for action in cards
            if action.get("target_id") == threat_id and card_value(action, "damage") > 0
        ]
        if finishers:
            return _tag_action(max(finishers, key=lambda action: (
                not _is_self_damage(action, hand),
                not hand.get(action.get("hand_index"), {}).get("bound", False),
                card_value(action, "damage"),
            )), "multi_lethal_direct")

    taunt = next((action for action in cards if action.get("card_id") == "CARD.TAUNT"), None)
    battle_trance = next((action for action in cards if action.get("card_id") == "CARD.BATTLE_TRANCE"), None)
    if (
        taunt and battle_trance
        and incoming >= max(1, hp // 2)
        and any(
            power.get("id") == "POWER.SANDPIT_POWER" and _number(power.get("amount")) >= 3
            for enemy in observation.get("enemies", ()) for power in enemy.get("powers", ())
        )
        and _number(hand.get(battle_trance.get("hand_index"), {}).get("cost")) == 0
        and _number(hand.get(taunt.get("hand_index"), {}).get("cost")) <= card_energy
        and not any(power.get("id") == "POWER.NO_DRAW_POWER" for power in player.get("powers", ()))
    ):
        draw = max(
            (_number(variable.get("value")) for variable in hand[battle_trance["hand_index"]].get("vars", ()) if variable.get("id") == "Cards"),
            default=0,
        )
        if draw and len(hand) + draw <= 10:
            return _tag_action(taunt, "sandpit_taunt_before_draw")

    if (
        incoming - current_block >= hp
        and any(power.get("id") == "POWER.UNMOVABLE_POWER" and _number(power.get("amount")) > 0 for power in player.get("powers", ()))
    ):
        defenses = [action for action in cards if card_value(action, "block") > 0]
        best_defense = max(defenses, key=lambda action: card_value(action, "block"), default=None)
        if best_defense and incoming - current_block - card_value(best_defense, "block") < hp:
            return _tag_action(best_defense, "unmovable_lethal_defense")

    # Fiend Fire destroys the rest of the hand.  On a safe turn, preserve a long-fight power
    # when both cards can be paid for; Z6 otherwise exhausts Crimson Mantle on the Act 2 boss's
    # opening buff turn despite starting with eight energy.
    fiend_fire = next((action for action in cards if action.get("card_id") == "CARD.FIEND_FIRE"), None)
    offering = next((action for action in cards if action.get("card_id") == "CARD.OFFERING"), None)
    crimson_mantle = next((action for action in cards if action.get("card_id") == "CARD.CRIMSON_MANTLE"), None)
    if fiend_fire and offering and incoming == 0:
        combined_cost = sum(
            _number(hand.get(action.get("hand_index"), {}).get("cost"))
            for action in (fiend_fire, offering)
        )
        if combined_cost <= card_energy and _self_damage_value(offering, hand) < hp:
            return _tag_action(offering, "offering_before_fiend_fire")
    if fiend_fire and crimson_mantle and incoming == 0:
        combined_cost = sum(
            _number(hand.get(action.get("hand_index"), {}).get("cost"))
            for action in (fiend_fire, crimson_mantle)
        )
        if combined_cost <= card_energy:
            return _tag_action(crimson_mantle, "crimson_mantle_before_fiend_fire")

    # rollouts cover the modeled cards in hand; unknown cards are treated as unplayable by the
    # simulator rather than abandoning the rollout entirely (e.g. Dominate used to disable it).
    if rollout_enabled:
        try:
            selected = rollout_choice(observation, actions, enemy_data, simulations)
            rollout_decision_reason = None
            frog_knight = next((enemy for enemy in enemy_by_id.values() if enemy.get("id") == "MONSTER.FROG_KNIGHT"), None)
            selected_card = hand.get(selected.get("hand_index"), {})
            if frog_knight and incoming == 0 and card_value(selected, "damage") <= 0 and card_value(selected, "block") > 0:
                attacks = [
                    action for action in cards
                    if action.get("target_id") == frog_knight.get("combat_id")
                    and not _is_self_damage(action, hand)
                    and card_value(action, "damage") > 0
                    and _number(hand.get(action.get("hand_index"), {}).get("cost")) <= card_energy
                ]
                if attacks:
                    selected = max(attacks, key=lambda action: card_value(action, "damage"))
                    rollout_decision_reason = "frog_knight_rest_attack"
            devoted = next((enemy for enemy in enemy_by_id.values() if enemy.get("id") == "MONSTER.DEVOTED_SCULPTOR"), None)
            if devoted and selected.get("card_id") == "CARD.TRUE_GRIT" and not _number(hand.get(selected.get("hand_index"), {}).get("upgrade")) and incoming < hp + current_block:
                race_attacks = [
                    action for action in cards
                    if action.get("target_id") == devoted.get("combat_id")
                    and not _is_self_damage(action, hand)
                    and card_value(action, "damage") > 0
                    and _number(hand.get(action.get("hand_index"), {}).get("cost")) <= card_energy
                ]
                if race_attacks:
                    selected = max(race_attacks, key=lambda action: (
                        _number(hand.get(action.get("hand_index"), {}).get("cost")) == 0,
                        action.get("card_id") == "CARD.MAUL",
                        card_value(action, "damage"),
                    ))
                    rollout_decision_reason = "devoted_race_before_true_grit"
            if (
                selected.get("card_id") == "CARD.BLOODLETTING"
                and not any(power.get("id") == "POWER.RUPTURE_POWER" for power in player.get("powers", ()))
            ):
                rupture = next((action for action in cards if action.get("card_id") == "CARD.RUPTURE"), None)
                if rupture:
                    selected = rupture
                    rollout_decision_reason = "rupture_before_bloodletting"
            if selected.get("card_id") == "CARD.HEADBUTT" and not observation.get("discard_pile"):
                headbutt_cost = _number(hand.get(selected.get("hand_index"), {}).get("cost"))
                setup_attacks = [
                    action for action in cards
                    if action.get("card_id") != "CARD.HEADBUTT"
                    and hand.get(action.get("hand_index"), {}).get("type") == "Attack"
                    and CARD_NAMES.get(action.get("card_id")) not in EXHAUSTS
                    and headbutt_cost + _number(hand.get(action.get("hand_index"), {}).get("cost")) <= card_energy
                    and card_value(action, "damage") >= 15
                ]
                if setup_attacks:
                    selected = max(setup_attacks, key=lambda action: card_value(action, "damage"))
                    rollout_decision_reason = "headbutt_setup"
            selected_card = hand.get(selected.get("hand_index"), {})
            if (
                obscura_present
                and selected.get("target_id") in minion_ids
                and selected_card.get("type") == "Attack"
            ):
                selected = next((action for action in actions if action.get("hand_index") == selected.get("hand_index") and action.get("target_id") == obscura_id), selected)
                rollout_decision_reason = "obscura_focus"
            if (
                urgent
                and decimillipede_focus_id is not None
                and selected.get("target_id") in decimillipede_ids
                and selected.get("target_id") != decimillipede_focus_id
                and selected_card.get("type") == "Attack"
            ):
                selected = next((
                    action for action in actions
                    if action.get("hand_index") == selected.get("hand_index")
                    and action.get("target_id") == decimillipede_focus_id
                ), selected)
                rollout_decision_reason = "decimillipede_focus"
            if (
                kin_focus_id is not None
                and selected.get("type") == "card"
                and selected.get("target_id") is not None
                and selected_card.get("type") == "Attack"
                and not is_lethal(selected)
                and selected.get("target_id") != kin_focus_id
            ):
                focused = next(
                    (
                        action for action in actions
                        if action.get("type") == "card"
                        and action.get("hand_index") == selected.get("hand_index")
                        and action.get("card_id") == selected.get("card_id")
                        and action.get("target_id") == kin_focus_id
                    ),
                    None,
                )
                if focused is not None:
                    rollout_simulations = selected.get("simulations")
                    selected = dict(focused)
                    if rollout_simulations is not None:
                        selected["simulations"] = rollout_simulations
                    rollout_decision_reason = "kin_follower_focus"
            # The rollout can miss a live enemy intent when its move/power is only partially
            # modeled. Never spend the last HP on a non-blocking, non-lethal play unless the card
            # itself reduces the next hit enough to survive (e.g. Uppercut's Weak or Mangle's
            # Strength reduction).
            rollout_is_unsafe = (
                max(0, mitigation_incoming(selected) - current_block) >= hp
                and card_value(selected, "block") <= 0
                and not is_lethal(selected)
                and not turn_can_clear_threats()
            )
            rupture_self_damage_is_safe = (
                any(power.get("id") == "POWER.RUPTURE_POWER" for power in player.get("powers", ()))
                and any(
                    power.get("id") == "POWER.STRENGTH_POWER" and _number(power.get("amount")) >= 20
                    for power in player.get("powers", ())
                )
                and _self_damage_value(selected, hand) + max(0, incoming - current_block) < hp
            )
            vulnerable_self_damage_is_safe = (
                enemy_by_id.get(selected.get("target_id"), {}).get("id") == "MONSTER.OVICOPTER"
                and
                any(
                    power.get("id") == "POWER.VULNERABLE_POWER" and _number(power.get("amount")) > 0
                    for power in enemy_by_id.get(selected.get("target_id"), {}).get("powers", ())
                )
                and card_value(selected, "damage") > 0
                and _self_damage_value(selected, hand) + max(0, incoming - current_block) < hp
            )
            sandpit_self_damage_is_safe = (
                sandpit_critical
                and selected.get("card_id") == "CARD.BLOODLETTING"
                and _self_damage_value(selected, hand) + max(0, incoming - current_block) < hp
            )
            # Keep the fallback's self-damage guard in front of rollouts too.  A rollout can
            # rationally trade 3 HP for Bloodletting's energy even when the live turn is already
            # dangerous; that is not a safe real-game choice unless it kills the target now.
            if not rollout_is_unsafe and not (_is_self_damage(selected, hand) and card_value(selected, "block") <= 0 and (hp <= max_hp // 2 or incoming >= max(1, hp // 2)) and not is_lethal(selected) and not rupture_self_damage_is_safe and not vulnerable_self_damage_is_safe and not sandpit_self_damage_is_safe):
                tremble = next((action for action in cards if action.get("card_id") == "CARD.TREMBLE"), None)
                target = enemy_by_id.get(selected.get("target_id"))
                if (
                    tremble
                    and sandpit_critical
                    and any(action.get("card_id") == "CARD.BLOODLETTING" for action in cards)
                    and selected_card.get("type") == "Attack"
                    and target
                    and not any(
                        power.get("id") in {"POWER.VULNERABLE", "POWER.VULNERABLE_POWER"}
                        and _number(power.get("amount")) > 0
                        for power in target.get("powers", ())
                    )
                    and sum(
                        _number(hand.get(action.get("hand_index"), {}).get("cost"))
                        for action in (tremble, selected)
                    ) <= card_energy
                ):
                    return _tag_action(tremble, "rollout_success", "tremble_before_attack")
                if selected.get("type") == "potion":
                    if potion_context is not None:
                        _LAST_POTION_CONTEXT = potion_context
                        _LAST_POTION_ID = selected.get("potion_id")
                    if potion_room is not None:
                        _POTION_USED_ROOM = potion_room
                return _tag_action(selected, "rollout_success", rollout_decision_reason)
            rollout_reason = "rollout_rejected_unsafe" if rollout_is_unsafe else "rollout_rejected_self_damage"
        except (KeyError, ValueError, NotImplementedError, StopIteration) as error:
            rollout_reason = {
                KeyError: "rollout_exception_key_error",
                ValueError: "rollout_exception_value_error",
                NotImplementedError: "rollout_exception_not_implemented",
                StopIteration: "rollout_exception_stop_iteration",
            }[type(error)]

    incoming = sum(enemy_incoming.values())
    player = observation.get("player", {})
    hp, max_hp = player.get("hp", 0), player.get("max_hp", 0)
    summon_pending = any(
        "summon" in str(intent.get("type", "")).lower()
        for enemy in observation.get("enemies", ())
        for intent in enemy.get("intents") or ()
    )
    if rollout_reason == "rollout_rejected_self_damage" and incoming == 0 and hp <= max_hp // 2:
        unmovable = next((action for action in cards if action.get("card_id") == "CARD.UNMOVABLE"), None)
        if unmovable:
            return _tag_action(unmovable, "heuristic_fallback", "unmovable_over_wasted_block")
    if hp <= max_hp // 2 or incoming >= max(1, hp // 2):
        safe_cards = [
            action for action in cards
            if not _is_self_damage(action, hand)
            or (incoming == 0 and _self_damage_value(action, hand) == hp - 1)
        ]
        if safe_cards:
            cards = safe_cards
        elif cards:
            return _tag_action(next(action for action in actions if action["type"] == "end_turn"), "heuristic_fallback", rollout_reason)
    if rollout_reason == "rollout_rejected_unsafe" and max(0, incoming - _number(player.get("block"))) >= hp:
        unmovable = next((action for action in cards if action.get("card_id") == "CARD.UNMOVABLE"), None)
        block_cards = [action for action in cards if card_value(action, "block") > 0]
        if unmovable and block_cards:
            best_block = max(block_cards, key=lambda action: card_value(action, "block"))
            combined_cost = sum(_number(hand.get(action.get("hand_index"), {}).get("cost")) for action in (unmovable, best_block))
            if combined_cost <= card_energy and incoming - _number(player.get("block")) - 2 * card_value(best_block, "block") < hp:
                return _tag_action(unmovable, "heuristic_fallback", "unmovable_before_block")
    if rollout_reason == "rollout_rejected_unsafe" and max(0, incoming - _number(player.get("block"))) >= hp:
        battle_trance = next((action for action in cards if action.get("card_id") == "CARD.BATTLE_TRANCE"), None)
        if battle_trance and not any(power.get("id") == "POWER.NO_DRAW_POWER" for power in player.get("powers", ())):
            draw = max(
                (_number(variable.get("value")) for variable in hand[battle_trance["hand_index"]].get("vars", ()) if variable.get("id") == "Cards"),
                default=0,
            )
            if draw and len(hand) + draw <= 10:
                return _tag_action(battle_trance, "heuristic_fallback", rollout_reason)
    defenses = [action for action in cards if card_value(action, "block") > 0]
    if rollout_reason == "rollout_rejected_unsafe" and defenses:
        # The search already said this turn kills us. Block is only worth energy if it can actually
        # prevent that death - otherwise every point spent on it is a point not spent on the one
        # line that still wins, killing the enemy. sweepF_1HQFTX7N3N died to VANTOM with the boss
        # on 1 HP after this branch spent 2 of 3 energy on Evil Eye + Defend (13 block) against
        # incoming that went straight through it, leaving only Pommel Strike's 9 damage on the table.
        remaining, reachable = card_energy, 0
        for action in sorted(defenses, key=lambda action: -card_value(action, "block")):
            cost = _number(hand.get(action.get("hand_index"), {}).get("cost"))
            if cost > remaining:
                continue
            remaining -= cost
            reachable += card_value(action, "block")
        if incoming - _number(player.get("block")) - reachable >= hp:
            defenses = []
    if (observation.get("player", {}).get("block", 0) < incoming or summon_pending) and defenses:
        return _tag_action(max(defenses, key=lambda action: card_value(action, "block")), "heuristic_fallback", rollout_reason)
    # MinionPower enemies do not need to die to win; KIN_FOLLOWER is explicitly focused below.
    priority = {"CARD.BASH": 4, "CARD.STRIKE_IRONCLAD": 3, "CARD.DEFEND_IRONCLAD": 2}
    if cards:
        def score(action: dict) -> tuple[int, int, int, int, int, int]:
            card = hand.get(action.get("hand_index"), {})
            attack = card.get("type") == "Attack" and action.get("target_id") in enemy_by_id
            # Focus fire: among equal-priority attacks, prefer non-minion enemies, then the weakest.
            return (
                priority.get(action["card_id"], 3 if card.get("type") == "Attack" else 1),
                int(kin_focus_id is not None and attack and action.get("target_id") == kin_focus_id),
                int(decimillipede_focus_id is not None and attack and action.get("target_id") == decimillipede_focus_id),
                damage(action) if attack else 0,
                (action.get("target_id") not in minion_ids) if attack else 0,
                -enemy_by_id[action["target_id"]].get("hp", 0) if attack else 0,
            )
        return _tag_action(max(cards, key=score), "heuristic_fallback", rollout_reason)
    return _tag_action(next(action for action in actions if action["type"] == "end_turn"), "heuristic_fallback", rollout_reason)


def choose_crab_facing(observation: dict, cards: list[dict]) -> dict | None:
    facing = next((power.get("facing") for power in observation.get("player", {}).get("powers", ()) if power["id"] == "POWER.SURROUNDED_POWER"), None)
    if facing not in {"Left", "Right"}:
        return None
    hand = {card["index"]: card for card in observation.get("hand", ())}
    player = observation.get("player", {})
    card_energy = _number(player.get("energy"))
    if "RELIC.CHEMICAL_X" in (player.get("relics") or ()):
        card_energy += 2
    attack_targets = {
        action.get("target_id")
        for action in cards
        if hand.get(action.get("hand_index"), {}).get("type") == "Attack"
    }
    threats = []
    for enemy in observation.get("enemies", ()):
        direction = "Left" if any(power["id"] == "POWER.BACK_ATTACK_LEFT_POWER" for power in enemy.get("powers", ())) else "Right" if any(power["id"] == "POWER.BACK_ATTACK_RIGHT_POWER" for power in enemy.get("powers", ())) else None
        incoming = sum(intent.get("damage", 0) * max(1, intent.get("repeats", 1)) for intent in enemy.get("intents") or ())
        if direction and direction != facing and incoming and enemy.get("combat_id") in attack_targets:
            threats.append((incoming, direction, enemy["combat_id"]))
    if not threats:
        return None
    _, direction, target_id = max(threats)
    candidates = [
        action
        for action in cards
        if action.get("target_id") == target_id
        and hand.get(action.get("hand_index"), {}).get("type") == "Attack"
    ]
    safe_candidates = [action for action in candidates if not _is_self_damage(action, hand)]
    if safe_candidates:
        candidates = safe_candidates
    else:
        hp = _number(observation.get("player", {}).get("hp"))
        candidates = [action for action in candidates if _self_damage_value(action, hand) < hp]
    return max(candidates, key=lambda action: _card_value(action, hand, "damage", card_energy), default=None)


def choose_potion(observation: dict, actions: list[dict]) -> dict | None:
    if not actions:
        return None
    # EntropicBrew.OnUse loops `while HasOpenPotionSlots`, and the belt frees the brew's own slot
    # first, so drinking it on a full belt trades it for exactly one random potion (observed:
    # astra_base_K7M2QX9BTR seq117 -> seq118, Entropic Brew replaced by a Strength Potion). With
    # a slot already open it yields two or more. It has no combat effect either way and is usable
    # AnyTime, so holding it until a slot frees up costs nothing.
    if any(str(action.get("potion_id")) == "POTION.ENTROPIC_BREW" for action in actions):
        slots = observation.get("potions")
        if isinstance(slots, list) and slots and all(slot for slot in slots):
            actions = [action for action in actions if str(action.get("potion_id")) != "POTION.ENTROPIC_BREW"]
            if not actions:
                return None
    enemy_hp = {enemy["combat_id"]: enemy["hp"] for enemy in observation.get("enemies", ())}
    enemy_max_hp = {
        enemy["combat_id"]: _number(enemy.get("max_hp"), enemy.get("hp", 0))
        for enemy in observation.get("enemies", ())
    }
    enemy_damage = {enemy["combat_id"]: _intent_incoming(enemy) for enemy in observation.get("enemies", ())}
    if observation.get("enemies") and all(
        any(power.get("id") == "POWER.SLIPPERY_POWER" and _number(power.get("amount")) > 0 for power in enemy.get("powers", ()))
        for enemy in observation["enemies"] if _number(enemy.get("hp")) > 0
    ):
        actions = [action for action in actions if action.get("potion_id") != "POTION.EXPLOSIVE_AMPOULE"]
    def use(ids: set[str], target_score: dict[int, int] | None = None) -> dict | None:
        candidates = [action for action in actions if action["potion_id"] in ids]
        return max(candidates, key=lambda action: target_score.get(action.get("target_id"), 0) if target_score else 0, default=None)
    rock_actions = [action for action in actions if action["potion_id"] == "POTION.POTION_SHAPED_ROCK" and action.get("target_id") in enemy_hp]
    lethal_rocks = []
    for action in rock_actions:
        enemy = next(enemy for enemy in observation.get("enemies", ()) if enemy.get("combat_id") == action.get("target_id"))
        powers = enemy.get("powers", ())
        if any(power.get("id") == "POWER.SLIPPERY_POWER" and _number(power.get("amount")) > 0 for power in powers):
            dealt = 1
        else:
            caps = [_number(power.get("amount")) for power in powers if power.get("id") == "POWER.HARD_TO_KILL_POWER" and _number(power.get("amount")) > 0]
            dealt = min(15, max(caps)) if caps else 15
            dealt = max(0, dealt - _number(enemy.get("block")))
        if dealt >= _number(enemy.get("hp")):
            lethal_rocks.append(action)
    if lethal_rocks:
        return max(lethal_rocks, key=lambda action: enemy_hp[action.get("target_id")])
    player = observation.get("player", {})
    hp, max_hp = player.get("hp", 0), player.get("max_hp", 1)
    block = _number(player.get("block", 0))
    incoming = sum(_intent_incoming(enemy) for enemy in observation.get("enemies", ()))
    hand = observation.get("hand") or ()
    run = observation.get("run") or {}
    room_type = str(run.get("room_type") or "")
    # Ordinary Monster rooms are the most common source of potion depletion. Preserve potions
    # unless the effective hit is lethal, or HP is critical and the next hit is substantial;
    # Elite/Boss rooms keep the full policy below.  Do not spend a potion merely because a
    # low-HP monster has a harmless intent or because existing block already covers the hit.
    effective_incoming = max(0, incoming - block)
    if any(power.get("id") == "POWER.BUFFER_POWER" and _number(power.get("amount")) > 0 for power in player.get("powers", ())):
        effective_incoming = max(
            0,
            effective_incoming
            - max(
                (max(0, _number(intent.get("damage"))) for enemy in observation.get("enemies", ()) for intent in enemy.get("intents") or ()),
                default=0,
            ),
        )
    legal_card_indices = {
        action.get("hand_index")
        for action in observation.get("legal_actions", ())
        if action.get("type") == "card"
    }
    survivable_block_card = effective_incoming >= hp and any(
        card.get("index") in legal_card_indices
        and 0 <= _number(card.get("cost"), -1) <= _number(player.get("energy"))
        and block + max((_number(var.get("value")) for var in card.get("vars", ()) if var.get("id") == "Block"), default=0) + hp > incoming
        for card in hand
    )
    monster_emergency = effective_incoming >= hp or (
        hp <= max(1, max_hp // 3)
        and effective_incoming >= max(1, (hp + 1) // 2)
    )
    if room_type == "Monster" and not monster_emergency:
        return None
    snecko = use({"POTION.SNECKO_OIL"})
    if (
        snecko
        and effective_incoming >= hp
        and len(observation.get("hand") or ()) < 10
        and (observation.get("draw_pile") or observation.get("discard_pile"))
    ):
        return snecko
    lucky = use({"POTION.LUCKY_TONIC"})
    if lucky and incoming > 0 and hp - incoming <= max_hp // 4:
        return lucky
    fire = next((action for action in actions if action["potion_id"] == "POTION.FIRE_POTION" and action.get("target_id") in enemy_hp and enemy_hp[action["target_id"]] <= 20), None)
    if fire:
        return fire
    healing = {"POTION.BLOOD_POTION", "POTION.CURE_ALL"}
    # Fortifier doubles the current block, so with no block it is wasted (sim19 used it at 0
    # block and gained nothing); only count it once the player already has block this turn.
    preserve_fortifier = survivable_block_card or (hp <= max(1, max_hp // 3) and effective_incoming < hp)
    blocking = {"POTION.BLOCK_POTION", "POTION.SHIP_IN_A_BOTTLE"} | ({"POTION.FORTIFIER"} if block > 0 and not preserve_fortifier else set())
    # Speed Potion just grants Dexterity via SpeedPotionPower - same effect as Dexterity Potion.
    defensive_buffs = {
        "POTION.DEXTERITY_POTION", "POTION.SPEED_POTION", "POTION.GHOST_IN_A_JAR", "POTION.REGEN_POTION",
        "POTION.LIQUID_BRONZE", "POTION.FYSH_OIL", "POTION.HEART_OF_IRON",
    }
    recovery = healing | defensive_buffs
    # Shackling is deliberately excluded from `debuffs` below: its -7 Strength lasts the whole
    # fight, so it is reserved for the >=100 HP boss-length branch further down rather than
    # spent reactively on any dangerous *regular* fight (e.g. a Wriggler swarm) - sim13 burned
    # Shackling on a normal encounter and had nothing left for the boss that actually needed it.
    debuffs = {"POTION.WEAK_POTION", "POTION.VULNERABLE_POTION", "POTION.POISON_POTION", "POTION.POTION_OF_BINDING"}
    survival_debuffs = {"POTION.WEAK_POTION", "POTION.POTION_OF_BINDING"}
    offensive = {
        "POTION.ATTACK_POTION", "POTION.COLORLESS_POTION", "POTION.DISTILLED_CHAOS", "POTION.DUPLICATOR",
        "POTION.EXPLOSIVE_AMPOULE", "POTION.FIRE_POTION", "POTION.FLEX_POTION", "POTION.POWER_POTION",
        "POTION.SKILL_POTION", "POTION.STRENGTH_POTION", "POTION.GIGANTIFICATION",
    }
    # EntropicBrew (decompiled): refills open potion slots with new random potions - it has no
    # combat effect of its own (no heal, no block, no damage), so it belongs with the other
    # non-defensive economy potions, not with `recovery`. Miscategorizing it as recovery let it
    # fire in emergency branches where it does nothing to survive the current turn, burning a
    # potion slot alongside the real defensive potion that followed it.
    economy = {
        "POTION.CLARITY", "POTION.STABLE_SERUM", "POTION.RADIANT_TINCTURE", "POTION.LIQUID_MEMORIES",
        "POTION.GAMBLERS_BREW", "POTION.OROBIC_ACID", "POTION.FRUIT_JUICE", "POTION.ENTROPIC_BREW",
    }
    known = recovery | blocking | debuffs | offensive | economy | {
        "POTION.ENERGY_POTION", "POTION.SWIFT_POTION", "POTION.LUCKY_TONIC", "POTION.SHACKLING_POTION",
        "POTION.FORTIFIER",
        "POTION.POTION_SHAPED_ROCK", "POTION.BLESSING_OF_THE_FORGE",
    }
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
            if potion_id and potion_id not in known and not any(marker in potion_id for marker in ("BOTTLED", "FAIRY", "REVIV", "SNECKO", "FOUL")):
                return action
        return None
    danger = hp <= max_hp // 2 or incoming >= max(1, hp // 2)
    threatening = incoming >= max(1, hp // 2)
    # Skill Potion is a hand-dependent gamble; save it for a turn whose incoming damage is
    # substantial enough to justify spending a scarce potion slot.
    offensive_now = offensive if threatening else offensive - {"POTION.SKILL_POTION"}
    has_slot = any(enemy.get("slot") for enemy in observation.get("enemies", ()))
    boss_slot = any(str(enemy.get("slot")).lower() == "boss" for enemy in observation.get("enemies", ()))
    boss_floor = {0: 17, 1: 16, 2: 15}.get(_number(run.get("act")))
    boss_context = boss_slot or (boss_floor is not None and _number(run.get("floor")) >= boss_floor)
    # A non-lethal boss turn is the worst time to gamble on random cards: keep Colorless for
    # the next attack cycle, even when HP is already critical.  Spend it only when the current
    # incoming damage is actually lethal.
    reserve_boss_colorless = boss_context and incoming < hp
    max_enemy_hp = max(enemy_max_hp.values(), default=0)
    fallback_boss = not has_slot and not any(enemy.get("id") for enemy in observation.get("enemies", ())) and max_enemy_hp >= 100
    boss_like = boss_slot or fallback_boss
    regular_monster = room_type == "Monster"
    elite_or_boss = room_type in {"Elite", "Boss"} or boss_like or boss_context
    high_hp_regular = max_enemy_hp >= 100 and not elite_or_boss
    major_allowed = elite_or_boss or (
        not regular_monster
        and (
            not high_hp_regular
            or incoming >= max(1, (hp * 3 + 3) // 4)
            or hp <= max(1, max_hp // 3)
        )
    )
    if max_enemy_hp >= 100 and major_allowed and ((boss_context and hp <= max(1, max_hp // 3)) or (fallback_boss and incoming > 0)):
        offensive_now = offensive_now | {"POTION.SKILL_POTION"}
    # On a long boss, keep Colorless through every non-lethal turn above critical HP, including
    # the early incoming>=HP/2 branch; the next attack cycle can be worse than the current hit.
    offensive_safe = offensive_now - ({"POTION.COLORLESS_POTION"} if reserve_boss_colorless else set())

    def use_major_aware(ids: set[str], target_score: dict[int, int] | None = None) -> dict | None:
        allowed = ids if major_allowed else ids - RESERVED_COMBAT_POTIONS
        if not major_allowed and incoming >= max(1, hp // 2):
            allowed |= ids & (blocking | defensive_buffs | {"POTION.LUCKY_TONIC"})
        if not major_allowed and hp <= max(1, max_hp // 3):
            allowed |= ids & (blocking | defensive_buffs | {"POTION.LUCKY_TONIC"})
        return use(allowed, target_score)

    boss_shackling = use_major_aware({"POTION.SHACKLING_POTION"}) if max_enemy_hp >= 100 and incoming > 0 else None
    boss_skill = use_major_aware({"POTION.SKILL_POTION"}) if max_enemy_hp >= 100 and (boss_context or fallback_boss) else None
    if incoming >= hp:
        energy = use({"POTION.ENERGY_POTION"}) if any(card.get("cost", 1) > 0 for card in hand) else None
        return use_major_aware({"POTION.LUCKY_TONIC", "POTION.GHOST_IN_A_JAR"} | blocking) or use(survival_debuffs, enemy_damage) or boss_skill or use_major_aware(recovery) or boss_shackling or use_major_aware(offensive_safe, enemy_hp) or energy or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if hp <= max_hp // 2 and (len(enemy_hp) >= 2 or incoming >= hp // 2):
        if len(enemy_hp) >= 2:
            explosive = use({"POTION.EXPLOSIVE_AMPOULE"})
            if explosive:
                return explosive
        if any(card.get("cost", 1) > 0 for card in hand):
            energy = use({"POTION.ENERGY_POTION"})
            if energy:
                return energy
        return use_major_aware(blocking) or use(survival_debuffs, enemy_damage) or use_major_aware(recovery) or boss_shackling or use_major_aware(offensive_safe, enemy_hp) or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if hp <= max_hp // 2:
        if boss_context and boss_skill and hp <= max(1, max_hp // 3):
            return boss_skill
        return use_major_aware(recovery) or boss_shackling or use_major_aware(offensive_safe, enemy_hp) or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if effective_incoming < hp // 2 <= incoming and use({"POTION.FYSH_OIL"}):
        return None
    if incoming >= hp // 2:
        energy = use({"POTION.ENERGY_POTION"}) if any(card.get("cost", 1) > 0 for card in hand) else None
        return use_major_aware(blocking) or use(survival_debuffs, enemy_damage) or use_major_aware(recovery) or boss_shackling or energy or use_major_aware(offensive_safe, enemy_hp) or use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    if max_enemy_hp >= 100:
        # Boss-length fights: ShacklingPotionPower subclasses TemporaryStrengthPower, whose
        # AfterSideTurnEnd removes the -7 Strength (and itself) once the AFFECTED CREATURE's own
        # side-turn ends - it only blunts the enemy's very next turn, not the whole fight (a
        # prior assumption here was wrong and wasted the potion on sleeping bosses like Bygone
        # Effigy that don't attack on an early turn). Only spend it once an attack is actually
        # incoming this decision, so the -7 lands on a turn that would otherwise deal damage.
        shackling = use_major_aware({"POTION.SHACKLING_POTION"}) if incoming > 0 else None
        # Fysh Oil grants both Strength and Dexterity; at three-fifths HP it is a pre-hit stabilizer
        # rather than a speculative damage potion, even when a high-HP regular still reserves
        # other boss potions.
        fysh = use({"POTION.FYSH_OIL"}) if incoming > 0 and hp <= max(1, (max_hp * 3) // 5) else None
        binding = use({"POTION.POTION_OF_BINDING"}) if boss_context and incoming >= max(1, hp // 2) else None
        # Skill Potion is also worth firing on any attacking boss turn: unlike a regular fight,
        # the next hit is part of a sustained sequence, so waiting for HP/2 can leave no safe
        # turn to spend the generated block card.
        boss_offensive = offensive_safe | ({"POTION.SKILL_POTION"} if incoming > 0 else set())
        economy_potion = use(economy) if elite_or_boss else None
        # Colorless is a scarce emergency hand: on a long boss, spending it at a merely
        # moderate hit leaves no answer for the next attack cycle (Knowledge Demon killed the
        # run after Colorless at 39/80 HP and incoming 11). Keep it until HP is critical or the
        # current hit is lethal.
        return shackling or fysh or binding or economy_potion or use_major_aware(boss_offensive) or use({"POTION.VULNERABLE_POTION", "POTION.POISON_POTION", "POTION.FIRE_POTION"}, enemy_hp) or (unknown_manual() if danger else None)
    if not hand:
        return use({"POTION.SWIFT_POTION"}) or (unknown_manual() if danger else None)
    return unknown_manual() if danger else None


def _rollout_allowed_potions(observation: dict, actions: list[dict]) -> tuple[str, ...]:
    candidates = [action for action in actions if action.get("type") == "potion" and action.get("potion_id") in ROLLOUT_POTION_IDS]
    if not candidates:
        return ()
    room = _potion_room(observation)
    if room is not None and room == _POTION_USED_ROOM and not _potion_is_lethal_incoming(observation):
        return ()
    selected = choose_potion(observation, candidates)
    dexterity_potions = {"POTION.DEXTERITY_POTION", "POTION.SPEED_POTION"}
    if (
        selected
        and room is not None
        and _potion_context(observation) == _LAST_POTION_CONTEXT
        and _LAST_POTION_ID in dexterity_potions
        and selected.get("potion_id") in dexterity_potions
    ):
        return ()
    return (selected["potion_id"],) if selected else ()


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
    if available:
        if "CARD.RUPTURE" in available and UNCOMMITTED_SELF_DAMAGE & deck_ids:
            return {"CARD.RUPTURE": 1}
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
        # Fuel already held, or fuel on this very screen. Without the second half the axis cannot
        # start at all: the enabler is docked 2-3 priority until Rupture arrives, and Rupture is
        # not a seed until an enabler arrives. H2LV6ZJ4XW was offered Rupture and Bloodletting
        # together and took neither.
        if UNCOMMITTED_SELF_DAMAGE & deck_ids or (available and UNCOMMITTED_SELF_DAMAGE & available):
            first.insert(0, "CARD.RUPTURE")
        cards = [card for card in first if available and card in available]
    if available is not None:
        cards = [card for card in cards if card in available]
    return {card: len(cards) - index for index, card in enumerate(cards)}


# This is a conservative acquisition guideline, not a measured rotation speed. Only repeatable,
# low-cost cards with a positive hand-size gain contribute extra capacity.
_REPEATABLE_DRAW_COUNTS = {
    "CARD.BATTLE_TRANCE": (3, 4),
    "CARD.DRUM_OF_BATTLE": (2, 2),
    "CARD.POMMEL_STRIKE": (1, 2),
}


def _large_deck_addition_allowed(
    observation: dict, deck_list: list[str], deck_ids: set[str], card_id: str, core: dict[str, int]
) -> bool:
    run = observation.get("run") or {}
    act = _number(run.get("act"), 0) if isinstance(run, dict) else 0
    limit = (20, 25, 30)[min(max(act, 0), 2)]
    deck_cards = observation.get("deck_cards") or (observation.get("player") or {}).get("deck_cards") or ()
    if not deck_cards:
        deck_cards = (observation.get("player") or {}).get("deck") or deck_list
    # Battle Trance also applies NoDraw, so only the largest copy contributes toward the margin.
    trance_extra = 0
    rotation_extra = 0
    for card in deck_cards:
        card_id_in_deck = card.get("id") or card.get("card_id") if isinstance(card, dict) else card
        draw_counts = _REPEATABLE_DRAW_COUNTS.get(card_id_in_deck)
        if draw_counts is None:
            continue
        if isinstance(card, dict):
            cost = card.get("cost")
            if cost is not None and _number(cost, 2) > 1:
                continue
            upgraded = _number(card.get("upgrade")) > 0
        else:
            upgraded = False
        card_extra = max(draw_counts[upgraded] - 1, 0)
        if card_id_in_deck == "CARD.BATTLE_TRANCE":
            trance_extra = max(trance_extra, card_extra)
        else:
            rotation_extra += card_extra
    limit += min(6, rotation_extra + trance_extra)
    if len(deck_list) < limit:
        return True
    return (
        (card_id in core and card_id not in deck_ids)
        or (sum(card in STRONG_BLOCK_CARDS for card in deck_list) < 3 and card_id in STRONG_BLOCK_CARDS)
        or (sum(card in DRAW_CARDS for card in deck_list) < 2 and card_id in DRAW_CARDS)
    )


def choose_shop(observation: dict) -> dict:
    actions = observation.get("legal_actions", ())
    removals = [action for action in actions if action.get("type") == "remove"]
    deck_cards = observation.get("deck_cards") or (observation.get("player") or {}).get("deck_cards") or ()
    deck_by_index = {
        card.get("index"): card
        for card in deck_cards
        if isinstance(card, dict) and card.get("index") is not None
    }
    for action in removals:
        card = deck_by_index.get(action.get("card_index"))
        if (
            card is not None
            and card.get("type") == "Curse"
            and (card.get("id") or card.get("card_id")) == action.get("card_id")
        ):
            return action
    deck_ids = _deck_ids(observation)
    deck_list = _deck_list(observation)
    shop_cards = {
        card.get("id") or card.get("card_id"): card for card in observation.get("cards", ())
    }
    high_cost_in_deck = sum(_number(card.get("cost"), 0) >= 3 for card in deck_cards)
    over_high_cost_cap = high_cost_in_deck >= 2
    over_unmodeled_cap = sum(card_id in UNMODELED_REWARDS for card_id in deck_list) >= UNMODELED_CAP
    defense_needed = _block_starved(deck_list)
    buys = [
        action for action in actions
        if action.get("type") == "buy_card"
        and not (
            (action.get("card_id") or action.get("id")) in {"CARD.BLOODLETTING", "CARD.UPPERCUT"}
            and (action.get("card_id") or action.get("id")) in deck_ids
        )
    ]
    axis = _relic_axis(deck_ids)
    core = _core_priority(deck_ids, {(action.get("card_id") or action.get("id")) for action in buys})
    buys = [
        action for action in buys
        if _large_deck_addition_allowed(observation, deck_list, deck_ids, action.get("card_id") or action.get("id"), core)
    ]
    tier_score = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}

    def card_key(action: dict) -> tuple[int, int, int, int, int]:
        card_id = action.get("card_id") or action.get("id")
        boss_bonus = _boss_card_bonus(observation, card_id)
        if over_unmodeled_cap and card_id in UNMODELED_REWARDS:
            return (0, 0, 0, 0, 0)
        if over_high_cost_cap and _number(shop_cards.get(card_id, {}).get("energy_cost"), 0) >= 3:
            return (0, 0, 0, 0, 0)
        if card_id in core and card_id not in deck_ids:
            return (4, core[card_id], tier_score.get(CARD_TIERS.get(card_id, "D"), 0), 0, 0)
        if not (set(EXHAUST_ENABLERS) & deck_ids) and card_id in UNCOMMITTED_EXHAUST_PAYOFF:
            return (0, 0, 0, 0, 0)
        tier = CARD_TIERS.get(card_id)
        allow_b_defense = defense_needed and tier == "B" and card_id in STRONG_BLOCK_CARDS
        if tier not in {"S", "A"} and not allow_b_defense:
            return (0, 0, 0, 0, 0)
        # A strong block is more valuable when the deck still lacks a real Act 2 answer.
        defense_bonus = 1 if defense_needed and card_id in STRONG_BLOCK_CARDS else 0
        return (2, tier_score[tier], boss_bonus, defense_bonus, 0)

    # A high-value known relic beats a non-core card, but an axis-defining card still wins.
    relics = [action for action in actions if action.get("type") == "buy_relic"]
    potions_for_sale = [action for action in actions if action.get("type") == "buy_potion"]
    best_relic = max(
        relics,
        key=lambda action: _shop_relic_score(action.get("relic_id") or action.get("id"), axis),
        default=None,
    )
    relic_score = _shop_relic_score((best_relic or {}).get("relic_id") or (best_relic or {}).get("id"), axis)
    best_potion = max(
        potions_for_sale,
        key=lambda action: SHOP_POTION_SCORES.get(action.get("potion_id") or action.get("id"), -1),
        default=None,
    )
    potion_score = SHOP_POTION_SCORES.get((best_potion or {}).get("potion_id") or (best_potion or {}).get("id"), -1)
    best_card = max(buys, key=card_key, default=None)
    if best_card and card_key(best_card)[0] == 4:
        return best_card
    if best_potion and potion_score >= SHOP_POTION_MIN_SCORE and relic_score < 8:
        return best_potion
    # Basic removal outranks the starvation-driven buys below.  _block_starved compares block
    # cards against deck size, so buying block also grows the deck and the ratio barely moves -
    # deleting a Strike raises the same ratio without adding a card.  Only an unowned core card
    # and a potion come ahead of thinning the deck.  Shop turns are sequential, so this decides
    # what happens first, not what happens at all: a later call still reaches the buys below.
    # Once the primary basic is gone the shop used to stop thinning entirely, even with removals on
    # offer and gold to spare - astra_goal_cards1 left five Defends untouched through every Act 2
    # shop and grew to 28 cards. Fall back to the other basic, but keep 3 copies so the deck does
    # not lose its cheap filler; the Perfected Strike axis has no fallback because it needs its
    # Strike count.
    remove_ids = (
        ("CARD.DEFEND_IRONCLAD",) if "CARD.PERFECTED_STRIKE" in deck_ids
        else ("CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD")
    )
    for index, remove_id in enumerate(remove_ids):
        if index and deck_list.count(remove_id) < 4:
            continue
        preferred = next((action for action in removals if (action.get("card_id") or action.get("id")) == remove_id), None)
        if preferred:
            return preferred
    if (
        best_card
        and card_key(best_card)[0] == 2
        and defense_needed
        and (best_card.get("card_id") or best_card.get("id")) in STRONG_BLOCK_CARDS
        and relic_score < 8
    ):
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
        # An Unknown room is a gamble that can turn out to be a fight, so it sits between a
        # guaranteed-safe room and a guaranteed fight: certain combat weighs 2, an Unknown weighs 1
        # once HP is down to a third of max, and everything else 0. astra_seed_K7M2QX9BTR walked
        # into an Unknown at 12/85 with a Shop as the only other option; the Unknown was an
        # Ovicopter pack and the run died there. Weighing Unknown the same as a Monster instead
        # would throw away the (correct) preference for a maybe-fight over a certain one.
        critical_hp = player.get("hp", player["max_hp"]) * 3 <= player["max_hp"]

        def fight_weight(room: str) -> int:
            if room in {"Monster", "Elite", "Boss"}:
                return 2
            return 1 if critical_hp and room == "Unknown" else 0
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
            fights = fight_weight(point["type"])
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
            fights = fight_weight(point["type"])
            safety_paths[coord] = (fights, int(not fights)) if not reachable else min(((fight_count + fights, noncombat_count + (not fights)) for fight_count, noncombat_count in reachable), key=lambda path: (path[0], -path[1]))
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
        # Measured HP budget of the route rather than a fixed order of tile counts: an ordinary
        # Act 2 fight costs 17.0 HP, an elite 32.2, and a rest site restores about 26. Ranking the
        # counts instead had the planner trade one ordinary fight for one elite (about fifteen HP
        # worse), and pricing only the fights had it trade away rest sites it needed.
        hp_cost = (
            types.count("Monster") * 17
            + types.count("Elite") * 32
            - types.count("RestSite") * 26
        )
        return (
            unrested_elites,
            hp_cost,
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
    "CARD.BATTLE_TRANCE", "CARD.BURNING_PACT", "CARD.POMMEL_STRIKE", "CARD.SHRUG_IT_OFF", "CARD.DRUM_OF_BATTLE",
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
    "CARD.IRON_WAVE", "CARD.TRUE_GRIT", "CARD.COLOSSUS",
}

# Blocks of 8+ that can actually hold off Act 2's 28-36 hits. Taunt is included despite its
# 7-block base because its Vulnerable rider makes it a dedicated defensive solution; Defend (5),
# Iron Wave (5), Second Wind (5) and True Grit (7) are barely better than Defend.
STRONG_BLOCK_CARDS = {
    "CARD.IMPERVIOUS", "CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER",
    "CARD.BLOOD_WALL", "CARD.STONE_ARMOR", "CARD.TAUNT", "CARD.EVIL_EYE",
    "CARD.EQUILIBRIUM", "CARD.ULTIMATE_DEFEND",
}

# All-enemy attacks are the only reliable way to stop a multi-enemy turn from snowballing.
# Keep this list in sync with combat.py's ALL_ENEMY_DAMAGE plus Whirlwind's special X-cost path.
ALL_ENEMY_CARDS = {
    "CARD.BREAKTHROUGH", "CARD.HOWL_FROM_BEYOND", "CARD.DRAMATIC_ENTRANCE",
    "CARD.THUNDERCLAP", "CARD.PACTS_END", "CARD.STOMP", "CARD.EXTERMINATE",
    "CARD.WHIRLWIND",
}

# Boss-specific axes are intentionally small: the bridge only exposes the encounter identity,
# so use it to nudge known survival checks without replacing the general tier model.
BOSS_CARD_AXES = {
    "ENCOUNTER.THE_INSATIABLE_BOSS": STRONG_BLOCK_CARDS | DRAW_CARDS,
    "ENCOUNTER.KNOWLEDGE_DEMON_BOSS": STRONG_BLOCK_CARDS | DRAW_CARDS,
    "ENCOUNTER.CEREMONIAL_BEAST_BOSS": STRONG_BLOCK_CARDS | DRAW_CARDS,
    "ENCOUNTER.QUEEN_BOSS": STRONG_BLOCK_CARDS | DRAW_CARDS | ALL_ENEMY_CARDS,
    "ENCOUNTER.THE_KIN_BOSS": STRONG_BLOCK_CARDS,
}


def _boss_card_bonus(observation: dict, card_id: str) -> int:
    run = observation.get("run") or {}
    boss_ids = {
        str(run.get(key)).upper()
        for key in ("boss_encounter_id", "second_boss_encounter_id")
        if run.get(key)
    }
    return 2 if any(card_id in BOSS_CARD_AXES.get(boss_id, ()) for boss_id in boss_ids) else 0


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
    actions = [
        action for action in actions
        if _large_deck_addition_allowed(observation, deck_list, deck_ids, action["card_id"], core)
    ]
    if not actions:
        return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")
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
    # Only large decks use the hard override: early runs still allow a high-tier attack to win
    # over a defensive pick while the deck is small enough to recover its block density quickly.
    strong_block_shortage = len(deck_list) >= 16 and sum(card in STRONG_BLOCK_CARDS for card in deck_list) < 3
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
        if len(deck_list) < 16 and not strong_block_shortage and any(
            is_attack_reward(action)
            and tier_score.get(CARD_TIERS.get(action["card_id"], "D"), 0) > tier
            for action in actions
        ):
            return 0
        return 2

    selected = max(actions, key=lambda action: (
        0 if over_high_cost_cap and is_high_cost(action["card_id"]) else 1,
        bool(core.get(action["card_id"])), core.get(action["card_id"], 0),
        _boss_card_bonus(observation, action["card_id"]),
        strong_defense_bonus(action["card_id"]),
        1 if draw_needed and action["card_id"] in DRAW_CARDS else 0,
        priority.get(action["card_id"], 0),
        0 if not exhaust_ready and action["card_id"] in UNCOMMITTED_EXHAUST_PAYOFF else 1,
        1 if defense_needed and action["card_id"] in DEFENSE_PRIORITY else 0,
        1 if strike_axis and perfected < 2 and action["card_id"] in STRIKE_TAGGED_REWARDS else 0,
        1 if action["card_id"] not in deck_ids else 0,
    ))
    selected_id = selected["card_id"]
    selected_tier = tier_score.get(CARD_TIERS.get(selected_id, "D"), 0)
    selected_supported = bool(
        core.get(selected_id)
        or _boss_card_bonus(observation, selected_id)
        or strong_defense_bonus(selected_id)
        or (draw_needed and selected_id in DRAW_CARDS)
        or (defense_needed and selected_id in DEFENSE_PRIORITY)
    )
    # A 16+ card deck with under 3 strong blocks (D6: 29 cards, 1 strong block) cannot afford to
    # keep taking off-axis A/S-tier attacks (Anger, Headbutt, Dark Embrace, Expect a Fight) just
    # because their tier clears the B-tier-only check below - skip anything that isn't core, a
    # defense pick, or a needed draw pick, regardless of tier, until the block shortage is
    # resolved. Gate the draw exemption on draw_needed (<2 draw cards already) - otherwise a
    # deck that already has 2+ draw cards keeps taking more of them (D6: 3+ Battle Trance, 24
    # cards, 0 strong blocks) since every one of them slipped past this skip unconditionally.
    if strong_block_shortage and not (
        core.get(selected_id)
        or strong_defense_bonus(selected_id)
        or selected_id in DEFENSE_PRIORITY
        or (draw_needed and selected_id in DRAW_CARDS)
    ):
        return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")
    # Once the deck has enough cards to cover the early fights, a plain B/C/D-tier pick only
    # dilutes the draw. Keep cards that solve the current axis or a measured defense/draw
    # shortage, but use the reward's Skip alternative for everything else.
    if len(deck_list) >= 15 and selected_tier <= tier_score["B"] and not selected_supported:
        return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")
    if selected_supported or priority.get(selected["card_id"], 0):
        return selected
    attacks = [action for action in actions if cards.get(action["card_id"], {}).get("type") == "Attack"]
    if attacks:
        rarity = {"Rare": 3, "Uncommon": 2, "Common": 1}
        return max(attacks, key=lambda action: (rarity.get(cards[action["card_id"]].get("rarity"), 0), -_number(cards[action["card_id"]].get("cost"), 99)))
    return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")


def choose_potion_reward(observation: dict) -> dict:
    """Pick which held potion to discard for an offered one, or keep the belt as it is.

    The stock rewards handler drops a potion reward on the floor whenever the belt is full, so
    without this the choice never reached the agent at all. Swap only when the offer scores
    strictly higher than the worst potion held - a sideways trade wastes the reward and a
    downgrade is worse than skipping.
    """
    actions = observation["legal_actions"]
    skip = next((action for action in actions if action.get("type") == "skip"), None)
    discards = [action for action in actions if action.get("type") == "discard"]
    if not discards:
        return skip or actions[0]
    offered = (observation.get("offered") or {}).get("id")
    offered_score = SHOP_POTION_SCORES.get(offered, -1)
    worst = min(discards, key=lambda action: SHOP_POTION_SCORES.get(action.get("potion_id"), -1))
    worst_score = SHOP_POTION_SCORES.get(worst.get("potion_id"), -1)
    if offered_score > worst_score:
        return worst
    return skip or worst


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


def _observation_card(value: object) -> str | Card:
    if isinstance(value, Card):
        return value
    if isinstance(value, dict):
        card_id = value.get("id", "")
        name = CARD_NAMES.get(card_id, card_id)
        enchantment = value.get("enchantment")
        if not isinstance(enchantment, str):
            enchantment = None
        # Frantic Escape is the one card whose copies drift above their base cost during a combat
        # (EnergyCost.AddThisCombat), and the observation reports each copy's current cost.
        extra_cost = max(_number(value.get("cost")) - 1, 0) if card_id == "CARD.FRANTIC_ESCAPE" else 0
        # Mad Science rolls a CardType and a RiderEffect per copy; the bridge reports `type` and
        # `rider`, and this copy's scaled Damage/Block sits in its own vars.
        variant = rider = None
        variant_value = 0
        if card_id == "CARD.MAD_SCIENCE":
            variant = value.get("type") if isinstance(value.get("type"), str) else None
            rider = value.get("rider") if isinstance(value.get("rider"), str) else None
            wanted = "Block" if variant == "Skill" else "Damage"
            variant_value = next(
                (_number(variable.get("value")) for variable in value.get("vars") or () if variable.get("id") == wanted),
                0,
            )
        return Card(
            name, _number(value.get("upgrade")) > 0,
            enchantment=enchantment, extra_cost=extra_cost, bound=bool(value.get("bound")),
            variant=variant, rider=rider, variant_value=variant_value,
        )
    name = card_name(value)
    return CARD_NAMES.get(name, name)


def _rollout_cards(observation: dict) -> tuple[
    tuple[str | Card, ...], tuple[str | Card, ...], tuple[str | Card, ...], tuple[str | Card, ...], tuple[str, ...]
]:
    hand_values = tuple(observation.get("hand", ()))
    draw_values = tuple(observation.get("draw_pile", ()))
    discard_values = tuple(observation.get("discard_pile", ()))
    exhaust_values = tuple(observation.get("exhaust_pile", ()))
    has_legacy_snapshot = any(
        isinstance(value, str)
        for pile in (draw_values, discard_values, exhaust_values)
        for value in pile
    )
    upgraded_cards = ()
    if has_legacy_snapshot:
        upgraded_cards = tuple(
            dict.fromkeys(
                CARD_NAMES.get(card_id, card_id)
                for card_id in (observation.get("player", {}).get("upgraded_cards") or ())
            )
        )
    hand = tuple(_observation_card(value) for value in hand_values)
    # The live legal actions are authoritative for the rollout's first move. Besides Bound,
    # temporary cost changes such as Snecko Oil can make the modeled base cost stale.
    legal_indices = {
        action.get("hand_index")
        for action in observation.get("legal_actions", ())
        if action.get("type") == "card"
    }
    hand = tuple(
        replace(card, bound=True)
        if isinstance(card, Card) and index not in legal_indices and _number(value.get("cost"), -1) >= 0
        else card
        for index, (card, value) in enumerate(zip(hand, hand_values))
    )
    return (
        hand,
        tuple(_observation_card(value) for value in draw_values),
        tuple(_observation_card(value) for value in discard_values),
        tuple(_observation_card(value) for value in exhaust_values),
        upgraded_cards,
    )


def _rollout_target_id(target: str, observation: dict, compact_to_observation_index: list[int]) -> int | None:
    if not target:
        return None
    index = int(target)
    return observation["enemies"][compact_to_observation_index[index]]["combat_id"]


def _map_rollout_card_action(
    best: str,
    actions: list[dict],
    observation: dict,
    compact_to_observation_index: list[int],
) -> dict:
    token, _, target = best.partition("@")
    if token.startswith("card:"):
        hand_index = int(token[len("card:"):])
        candidates = [
            action for action in actions
            if action.get("type") == "card" and action.get("hand_index") == hand_index
        ]
        selected = next((action for action in candidates if action.get("target_id") is None), None)
        if selected is None:
            selected = next(iter(candidates))
    else:
        model = next(model for model, short in CARD_NAMES.items() if short == token)
        candidates = [
            action for action in actions
            if action.get("type") == "card" and action.get("card_id") == model
        ]
        selected = next((action for action in candidates if action.get("target_id") is None), None)
        if selected is None:
            selected = next(iter(candidates))
        hand_index = selected.get("hand_index")

    if selected.get("card_id") == "CARD.ARMAMENTS" and target.isdigit():
        if hand_index is None:
            raise ValueError("Armaments action has no hand index")
        relative_target = int(target)
        target_index = relative_target + (relative_target >= hand_index)
        return selected | {"upgrade_hand_index": target_index}

    if target:
        target_id = _rollout_target_id(target, observation, compact_to_observation_index)
        selected_target = next((action for action in candidates if action.get("target_id") == target_id), None)
        if selected_target is not None:
            selected = selected_target
        elif not token.startswith("card:") or selected.get("card_id") in ALL_ENEMY_CARDS:
            # Legacy rollouts represented targetless all-enemy cards as name@<enemy index>
            # even though the bridge action has no target_id.
            selected = next(action for action in candidates if action.get("target_id") is None)
        else:
            raise ValueError(f"rollout target is not legal: {best}")
    return selected


def rollout_choice(observation: dict, actions: list[dict], data: dict, simulations: int) -> dict:
    specs = {monster["id"]: monster for monster in data["monsters"]}
    enemies = []
    compact_to_observation_index = []
    for observation_index, observed in enumerate(observation["enemies"]):
        # Pael's Legion and Byrdpip are relic-summoned player pets (9999 HP, no health bar,
        # NOTHING_MOVE forever), not real combat targets; neither has an entry in the exported
        # monster data and would otherwise crash every rollout in any fight where the player
        # owns that relic.
        if observed["id"] in {"MONSTER.PAELS_LEGION", "MONSTER.BYRDPIP"}:
            continue
        spec = specs[observed["id"]]
        values = dict(spec["values"])
        if observed["id"] == "MONSTER.WATERFALL_GIANT" and observed["move"] == "EXPLODE_MOVE":
            intent = next(
                (
                    intent for intent in observed.get("intents", ())
                    if _number(intent.get("raw_damage"), _number(intent.get("damage"))) > 0
                ),
                None,
            )
            if intent is not None:
                values["SteamEruptionDamage"] = _number(intent.get("raw_damage"), _number(intent.get("damage")))
        enemy = Enemy(
            model=observed["id"],
            hp=observed["hp"],
            move=observed["move"],
            values=tuple(sorted(values.items())),
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
        compact_to_observation_index.append(observation_index)
    hand, draw_pile, discard_pile, exhaust_pile, upgraded_cards = _rollout_cards(observation)
    allowed_potions = _rollout_allowed_potions(observation, actions)
    state = Combat(
        player_hp=observation["player"]["hp"],
        hand=hand,
        draw_pile=draw_pile,
        discard_pile=discard_pile,
        enemies=tuple(enemies),
        player_block=observation["player"]["block"],
        player_powers=tuple(sorted(((f"Surrounded{power['facing']}" if power["id"] == "POWER.SURROUNDED_POWER" and power.get("facing") else POWER_NAMES.get(power["id"], power["id"])), power["amount"]) for power in observation["player"]["powers"])),
        energy=observation["player"]["energy"],
        max_energy=observation["player"].get("max_energy", 3),
        turn=observation["turn"],
        exhaust_pile=exhaust_pile,
        player_relics=tuple(observation["player"].get("relics", ())),
        # Brilliant Scarf zeroes every hand card's cost while exactly four cards have been played
        # this turn, and the bridge exposes no cards-played counter - but the discount is visible
        # in the hand: a card whose modeled base cost is positive shows up at 0. Restoring the
        # counter is what lets the rollout see that free fifth card and spend it (endturn1 seq476
        # ended the turn holding a free Giant Rock against a 121 HP boss).
        cards_played_this_turn=(
            BRILLIANT_SCARF_FREE_AFTER
            if "RELIC.BRILLIANT_SCARF" in observation["player"].get("relics", ())
            and any(
                _number(card.get("cost"), -1) == 0 and CARD_COST.get(CARD_NAMES.get(card.get("id"), ""), 0) > 0
                for card in observation.get("hand") or ()
            )
            else 0
        ),
        player_max_hp=observation["player"].get("max_hp", observation["player"]["hp"]),
        player_potions=allowed_potions,
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
        upgraded_cards=upgraded_cards,
        # ponytail: the bridge exposes the Toric power's remaining uses but not the block it
        # stored, so assume the unupgraded 5. Under-counting block is the safe direction; expose
        # the power's Block var from CombatBridge if this turns out to matter.
        # Tear Asunder's CalculatedHits is 1 + the combat's unblocked-damage events, so a copy in
        # hand reports the counter directly. Without one in hand nothing reads it, so 0 is fine.
        unblocked_hits=max(
            (
                _number(var.get("value")) - 1
                for card in observation.get("hand") or ()
                if card.get("id") == "CARD.TEAR_ASUNDER"
                for var in card.get("vars") or ()
                if var.get("id") == "CalculatedHits"
            ),
            default=0,
        ),
        toric_pending=tuple(
            (KNOWN_CARD_BLOCK["CARD.TORIC_TOUGHNESS"], _number(power["amount"]))
            for power in observation["player"]["powers"]
            if power["id"] == "POWER.TORIC_TOUGHNESS_POWER" and _number(power["amount"]) > 0
        ),
    )
    best, value = search(state, data, simulations, observation["seq"])[0]
    if best == "End turn":
        selected = next(action for action in actions if action["type"] == "end_turn")
        return selected | {"simulations": simulations, "search_value": value}
    if best.startswith("potion:"):
        potion, _, target = best[len("potion:"):].partition("@")
        target_id = (
            None
            if potion == POTION_EXPLOSIVE
            else observation["enemies"][compact_to_observation_index[int(target)]]["combat_id"] if target else None
        )
        selected = next(
            action for action in actions
            if action.get("type") == "potion"
            and action.get("potion_id") == potion
            and action.get("target_id") == target_id
        )
        return selected | {"simulations": simulations, "search_value": value}
    selected = _map_rollout_card_action(best, actions, observation, compact_to_observation_index)
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
                    atomic_write(args.action, action | {"seq": observation["seq"], "decision_source": "agent_exception_fallback"})
                    last_seq = observation["seq"]
        time.sleep(0.025)


if __name__ == "__main__":
    main()
