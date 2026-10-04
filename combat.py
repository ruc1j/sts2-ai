from __future__ import annotations

import argparse
import ast
import json
import random
import re
from dataclasses import dataclass, replace
from functools import lru_cache


STRIKE, DEFEND, BASH, ANGER, BLUDGEON, STOMP, SHRUG, BATTLE_TRANCE, BULLY, DISMANTLE, SLIMED, FRANTIC_ESCAPE, IRON_WAVE, TWIN_STRIKE, END_TURN = "Strike", "Defend", "Bash", "Anger", "Bludgeon", "Stomp", "Shrug It Off", "Battle Trance", "Bully", "Dismantle", "Slimed", "Frantic Escape", "Iron Wave", "Twin Strike", "End turn"
CINDER, ASHEN_STRIKE, HEMOKINESIS, PERFECTED_STRIKE, INFLAME, PRIMAL_FORCE, UNRELENTING, GIANT_ROCK, RELAX, TREMBLE, BREAKTHROUGH, WHIRLWIND, BLOODLETTING, BLOOD_WALL, FEED, DOMINATE, STONE_ARMOR, FEEL_NO_PAIN, BARRICADE, PYRE = "Cinder", "Ashen Strike", "Hemokinesis", "Perfected Strike", "Inflame", "Primal Force", "Unrelenting", "Giant Rock", "Relax", "Tremble", "Breakthrough", "Whirlwind", "Bloodletting", "Blood Wall", "Feed", "Dominate", "Stone Armor", "Feel No Pain", "Barricade", "Pyre"
BYRD_SWOOP, PILLAGE, EQUILIBRIUM = "Byrd Swoop", "Pillage", "Equilibrium"
BREAK, HOWL_FROM_BEYOND, IMPERVIOUS, RAMPAGE, TAUNT, THUNDERCLAP = "Break", "Howl From Beyond", "Impervious", "Rampage", "Taunt", "Thunderclap"
BOLAS, DRAMATIC_ENTRANCE, FISTICUFFS, LIFT, THRUMMING_HATCHET, ULTIMATE_DEFEND, ULTIMATE_STRIKE = "Bolas", "Dramatic Entrance", "Fisticuffs", "Lift", "Thrumming Hatchet", "Ultimate Defend", "Ultimate Strike"
TOXIC, BURN, DAZED, FLAME_BARRIER, INFECTION = "Toxic", "Burn", "Dazed", "Flame Barrier", "Infection"
SECRET_WEAPON = "Secret Weapon"
MOLTEN_FIST, NOT_YET, OFFERING, PACTS_END, POMMEL_STRIKE = "Molten Fist", "Not Yet", "Offering", "Pacts End", "Pommel Strike"
DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE = "Drum of Battle", "Master of Strategy", "Production", "Impatience"
RUPTURE, INFERNO, CRUELTY = "Rupture", "Inferno", "Cruelty"
FASTEN = "Fasten"
DEMON_FORM = "Demon Form"
NEOWS_FURY = "Neow's Fury"
MAD_SCIENCE = "Mad Science"
MAUL, THRASH = "Maul", "Thrash"
FIGHT_ME, JUGGERNAUT, PURITY, SALVO, FLASH_OF_STEEL = "Fight Me", "Juggernaut", "Purity", "Salvo", "Flash of Steel"
STAMPEDE = "Stampede"
CASCADE = "Cascade"
APOTHEOSIS = "Apotheosis"
JUGGLING = "Juggling"
SECOND_WIND = "Second Wind"
ENLIGHTENMENT = "Enlightenment"
MIND_BLAST, BODY_SLAM, BELIEVE_IN_YOU, FINESSE = "Mind Blast", "Body Slam", "Believe in You", "Finesse"
HEADBUTT, UPPERCUT, TRUE_GRIT, BURNING_PACT = "Headbutt", "Uppercut", "True Grit", "Burning Pact"
FIEND_FIRE, EVIL_EYE, BRAND, INFERNAL_BLADE, MANGLE = "Fiend Fire", "Evil Eye", "Brand", "Infernal Blade", "Mangle"
RAGE, SPITE, COLOSSUS, VOLLEY = "Rage", "Spite", "Colossus", "Volley"
PECK = "Peck"
EXTERMINATE = "Exterminate"
CONFLAGRATION = "Conflagration"
SETUP_STRIKE = "Setup Strike"
TORIC_TOUGHNESS, SQUASH, TEAR_ASUNDER = "Toric Toughness", "Squash", "Tear Asunder"
HAVOC, STOKE, METAMORPHOSIS = "Havoc", "Stoke", "Metamorphosis"
VICIOUS = "Vicious"
PANACHE, ONE_TWO_PUNCH = "Panache", "One-Two Punch"
PANACHE_TRIGGER_CARDS = 5  # PanachePower's CardsLeft base value
# The game names this potion model GigantificationPotion, so its id carries the suffix: every one of the
# 1,838 observations of a carried Gigantification potion reads POTION.GIGANTIFICATION_POTION, and a
# constant without the suffix can never match an action the game offers.
POTION_DUPLICATOR, POTION_GIGANTIFICATION = "POTION.DUPLICATOR", "POTION.GIGANTIFICATION_POTION"
# GigantificationPotion is TargetType.AnyPlayer and all 18 recorded plays carry target_id None, so the
# simulator lists it as an untargeted potion and applies GigantificationPower to the player.
# Play-count powers. DuplicationPower (Duplicator) adds one extra resolution to the play it
# modifies; OneTwoPunchPower (One-Two Punch) does the same for Attacks only. Both are consumed by
# that play and removed at the end of the player's turn, so the model treats the extra resolution
# as the card's damage or block applying twice.
ARMAMENTS, UNMOVABLE, EXPECT_A_FIGHT, AGGRESSION, DARK_EMBRACE, CRIMSON_MANTLE, FORGOTTEN_RITUAL, SWORD_BOOMERANG, HELLRAISER = "Armaments", "Unmovable", "Expect a Fight", "Aggression", "Dark Embrace", "Crimson Mantle", "Forgotten Ritual", "Sword Boomerang", "Hellraiser"
POTION_BLOCK, POTION_SHIP, POTION_FIRE, POTION_EXPLOSIVE, POTION_SHAPED_ROCK = "POTION.BLOCK_POTION", "POTION.SHIP_IN_A_BOTTLE", "POTION.FIRE_POTION", "POTION.EXPLOSIVE_AMPOULE", "POTION.POTION_SHAPED_ROCK"
POTION_STRENGTH, POTION_DEXTERITY, POTION_FYSH, POTION_ENERGY = "POTION.STRENGTH_POTION", "POTION.DEXTERITY_POTION", "POTION.FYSH_OIL", "POTION.ENERGY_POTION"
POTION_BLOOD, POTION_HEART, POTION_BRONZE = "POTION.BLOOD_POTION", "POTION.HEART_OF_IRON", "POTION.LIQUID_BRONZE"
# Colorless potions the colorless-pool shops sell often.  Each one's effect is a single command in the
# decompiled model (PowerCmd.Apply / CardPileCmd.Draw / CreatureCmd.GainBlock), so they are cheap to
# model - and 1,738 of the 3,274 recorded potion plays in the corpus used a potion the model could not
# price at all.
POTION_SPEED_POTION, POTION_FLEX_POTION, POTION_SWIFT_POTION = "POTION.SPEED_POTION", "POTION.FLEX_POTION", "POTION.SWIFT_POTION"
POTION_WEAK_POTION, POTION_VULNERABLE_POTION = "POTION.WEAK_POTION", "POTION.VULNERABLE_POTION"
POTION_REGEN_POTION, POTION_FORTIFIER = "POTION.REGEN_POTION", "POTION.FORTIFIER"
POTION_POTION_OF_BINDING, POTION_LUCKY_TONIC, POTION_CURE_ALL = "POTION.POTION_OF_BINDING", "POTION.LUCKY_TONIC", "POTION.CURE_ALL"
POTION_FAIRY_IN_A_BOTTLE, POTION_FOUL_POTION = "POTION.FAIRY_IN_A_BOTTLE", "POTION.FOUL_POTION"
POTION_SNECKO_OIL, POTION_STABLE_SERUM = "POTION.SNECKO_OIL", "POTION.STABLE_SERUM"
POTION_SHACKLING_POTION, POTION_CLARITY, POTION_RADIANT_TINCTURE = "POTION.SHACKLING_POTION", "POTION.CLARITY", "POTION.RADIANT_TINCTURE"
ENCHANTMENT_TEZCATARAS_EMBER = "ENCHANTMENT.TEZCATARAS_EMBER"
ENCHANTMENT_CORRUPTED = "ENCHANTMENT.CORRUPTED"
# Status cards with CardModel.HasTurnEndInHandEffect: deal this much flat Unpowered damage if
# the card is still in hand when the player ends their turn (see step()'s END_TURN handling).
# Toxic/Burn are injected straight to PileType.Hand (Myte, Mecha Knight); Infection is added to
# PileType.Discard by Wriggler's WRIGGLE_MOVE and only bites once it's drawn into a later hand.
WOUND, DECAY, NORMALITY = "Wound", "Decay", "Normality"
# Unplayable curses whose only effect fires while they sit in hand at the player's turn end.
DOUBT, REGRET, SHAME = "Doubt", "Regret", "Shame"
BECKON, BAD_LUCK, WITHER = "Beckon", "Bad Luck", "Wither"
# Decay is a Curse that starts in the deck rather than being injected mid-combat, but its
# OnTurnEndInHand is the same 2 flat Unpowered damage.
# Wither is a Curse that uses the same hook for 3 flat Unpowered damage (block absorbs it).
HAND_INJECTED_STATUS = {TOXIC: 5, BURN: 2, INFECTION: 3, DECAY: 2, WITHER: 3}
# Cards the game generates into the player's piles mid-fight.  Every one of these card models is
# Status or Token rarity, so it has no DeckVersion, and ThievingHopper.ThieveryMove only ever picks
# candidates whose DeckVersion exists.  The 268 steals recorded in real runs took none of them.
NON_DECK_CARDS = {
    SLIMED, TOXIC, BURN, DAZED, INFECTION, WITHER, DECAY, WOUND, FRANTIC_ESCAPE, GIANT_ROCK,
}
# Same hook, but these carry ValueProp.Unblockable, so block does not absorb them.  Beckon is
# generated by SOUL_FYSH; Bad Luck is a curse.  Regret (damage = cards in hand) and
# Shame/Doubt (apply Frail/Weak instead of damage) use the same hook.
HAND_END_UNBLOCKABLE = {BECKON: 6, BAD_LUCK: 13}
STARTING_DECK = (STRIKE,) * 5 + (DEFEND,) * 4 + (BASH,)
STRATAGEM = "Stratagem"

CARD_COST = {
    STRIKE: 1, DEFEND: 1, FASTEN: 1, DEMON_FORM: 3, BASH: 2, ANGER: 0, BLUDGEON: 3, STOMP: 3, SHRUG: 1, BATTLE_TRANCE: 0, BULLY: 0, DISMANTLE: 1, SLIMED: 1, FRANTIC_ESCAPE: 1, IRON_WAVE: 1, TWIN_STRIKE: 1,
    SECRET_WEAPON: 0,
    CINDER: 2, ASHEN_STRIKE: 1, HEMOKINESIS: 1, PERFECTED_STRIKE: 2, INFLAME: 1, INFERNO: 1, CRUELTY: 1, PRIMAL_FORCE: 0, UNRELENTING: 2, GIANT_ROCK: 1, RELAX: 3, TREMBLE: 1, MANGLE: 3, BARRICADE: 3, PYRE: 2, BLOOD_WALL: 2,
    BREAKTHROUGH: 1, BLOODLETTING: 0, FEED: 1, DOMINATE: 1, BYRD_SWOOP: 0, PILLAGE: 1, EQUILIBRIUM: 2, PECK: 1, EXTERMINATE: 1, CONFLAGRATION: 1, SETUP_STRIKE: 1,
    BREAK: 1, HOWL_FROM_BEYOND: 3, IMPERVIOUS: 2, RAMPAGE: 1, TAUNT: 1, THUNDERCLAP: 1,
    BOLAS: 0, DRAMATIC_ENTRANCE: 0, FISTICUFFS: 1, LIFT: 1, THRUMMING_HATCHET: 1, ULTIMATE_DEFEND: 1, ULTIMATE_STRIKE: 1,
    FLAME_BARRIER: 2, MOLTEN_FIST: 1, NOT_YET: 2, OFFERING: 0, PACTS_END: 0, POMMEL_STRIKE: 1, DRUM_OF_BATTLE: 1, MASTER_OF_STRATEGY: 0, PRODUCTION: 0, ARMAMENTS: 1, UNMOVABLE: 2, EXPECT_A_FIGHT: 2, AGGRESSION: 1, DARK_EMBRACE: 2, CRIMSON_MANTLE: 1, FORGOTTEN_RITUAL: 1, SWORD_BOOMERANG: 1, HELLRAISER: 2,
    IMPATIENCE: 0, MIND_BLAST: 1, BODY_SLAM: 1, BELIEVE_IN_YOU: 0, FINESSE: 0, RUPTURE: 1, STONE_ARMOR: 1, FEEL_NO_PAIN: 1, SECOND_WIND: 1, ENLIGHTENMENT: 0,
    HEADBUTT: 1, NEOWS_FURY: 1, MAD_SCIENCE: 1, UPPERCUT: 2, TRUE_GRIT: 1, BURNING_PACT: 1, FIEND_FIRE: 2, EVIL_EYE: 1, BRAND: 0, INFERNAL_BLADE: 1, RAGE: 0, SPITE: 0, COLOSSUS: 1, VOLLEY: 0,
    TORIC_TOUGHNESS: 2, SQUASH: 1, TEAR_ASUNDER: 2, HAVOC: 1, STOKE: 1, METAMORPHOSIS: 2, VICIOUS: 1,
    MAUL: 1, THRASH: 1, FIGHT_ME: 2, JUGGERNAUT: 2, PURITY: 0, SALVO: 1, FLASH_OF_STEEL: 0,
    STAMPEDE: 2, CASCADE: 0,  # Cascade's cost is X, spent like Whirlwind's
    APOTHEOSIS: 2, JUGGLING: 1, PANACHE: 0, ONE_TWO_PUNCH: 1, STRATAGEM: 1,
}
# WHIRLWIND has an X cost and is resolved separately.
CARD_DAMAGE = {
    STRIKE: 6, BASH: 8, ANGER: 6, BLUDGEON: 32, DISMANTLE: 8, IRON_WAVE: 5, TWIN_STRIKE: 5, CINDER: 18, HEMOKINESIS: 15, UNRELENTING: 14, GIANT_ROCK: 16, BREAKTHROUGH: 9,
    FEED: 10, NEOWS_FURY: 10, BYRD_SWOOP: 14, PILLAGE: 6, HEADBUTT: 9, SQUASH: 10, TEAR_ASUNDER: 5, UPPERCUT: 13, SPITE: 5, VOLLEY: 10, MANGLE: 15, PECK: 2, SETUP_STRIKE: 7, SWORD_BOOMERANG: 3,
    BREAK: 20, RAMPAGE: 9, BOLAS: 3, FISTICUFFS: 7, THRUMMING_HATCHET: 11, ULTIMATE_STRIKE: 14,
    MOLTEN_FIST: 10, POMMEL_STRIKE: 9, MAUL: 5, THRASH: 4, FIGHT_ME: 5, SALVO: 12, FLASH_OF_STEEL: 5,
}
CARD_HITS = {TWIN_STRIKE: 2, MAUL: 2, THRASH: 2, FIGHT_ME: 2}
CARD_UPGRADE_DAMAGE = {BASH: 2, SQUASH: 2, TEAR_ASUNDER: 2, CINDER: 6, TWIN_STRIKE: 2, POMMEL_STRIKE: 1, MANGLE: 5, SETUP_STRIKE: 2, MAUL: 1, THRASH: 2, FIGHT_ME: 1, SALVO: 4, FLASH_OF_STEEL: 3,
    # Every entry below is that card's DynamicVars.Damage.UpgradeValueBy in the decompiled card body.
    # They were previously getting the flat +3 fallback, which is wrong in both directions: Bludgeon and
    # Break gain 10, Ultimate Strike and Unrelenting 6, Hemokinesis 5, and Bolas only 1.
    ANGER: 2, BLUDGEON: 10, BOLAS: 1, BREAK: 10, BREAKTHROUGH: 4, BYRD_SWOOP: 4, DISMANTLE: 2, FEED: 2,
    FISTICUFFS: 2, GIANT_ROCK: 4, HEMOKINESIS: 5, IRON_WAVE: 2, MOLTEN_FIST: 4, NEOWS_FURY: 4,
    ULTIMATE_STRIKE: 6, UNRELENTING: 6, VOLLEY: 4,
    # Rampage's upgrade is DynamicVars["Increase"].UpgradeValueBy(4m) - the Strength it gains per attack
    # you play, not its damage.
    RAMPAGE: 0}
# Damage dealt by AllEnemies attacks (looped over every alive enemy, like BREAKTHROUGH/WHIRLWIND).
ALL_ENEMY_DAMAGE = {BREAKTHROUGH: 9, HOWL_FROM_BEYOND: 16, DRAMATIC_ENTRANCE: 11, THUNDERCLAP: 4, PACTS_END: 17, STOMP: 12, EXTERMINATE: 3, CONFLAGRATION: 2}
ALL_ENEMY_HITS = {EXTERMINATE: 4, CONFLAGRATION: 4}
# Cards whose upgrade changes only the hit count (Conflagration: RepeatVar 4 -> 5, DamageVar unchanged).
ALL_ENEMY_UPGRADE_HITS = {CONFLAGRATION: 1}
# Normality caps the turn at this many cards while it is in hand.
NORMALITY_CARD_CAP = 3
# Pact's End deals no damage unless the exhaust pile already holds this many cards.
PACTS_END_EXHAUST_REQUIRED = 3
# Default +3 for upgraded AllEnemies attacks; Conflagration is the exception - its OnUpgrade only
# raises RepeatVar, so the damage must stay at its base 2.
ALL_ENEMY_UPGRADE_DAMAGE = {EXTERMINATE: 1, CONFLAGRATION: 0,
    # Same rule as CARD_UPGRADE_DAMAGE: the card's own DynamicVars.Damage.UpgradeValueBy.
    BREAKTHROUGH: 4, DRAMATIC_ENTRANCE: 4, HOWL_FROM_BEYOND: 5, PACTS_END: 6}
# Flat block granted by skills with no other effect (Frail halves it, same as Defend).
CARD_BLOCK = {DEFEND: 5, IRON_WAVE: 5, EQUILIBRIUM: 13, IMPERVIOUS: 30, LIFT: 11, ULTIMATE_DEFEND: 11, FLAME_BARRIER: 12, FINESSE: 4, TRUE_GRIT: 7, EVIL_EYE: 8, COLOSSUS: 5, ARMAMENTS: 5, BLOOD_WALL: 16, TORIC_TOUGHNESS: 5}
# Cards that both deal damage and apply Vulnerable to that same target (Bash's pattern).
CARD_VULNERABLE_TARGET = {BASH: 2, BREAK: 5, SQUASH: 2}

def _card_resolution_debuffs(card: str, upgraded: bool) -> tuple[tuple[str, int], ...]:
    """The debuffs one OnPlay resolution grants its target, in the order the card applies them.

    Bash, Break and Squash carry `PowerVar<VulnerablePower>` in CanonicalVars, and Uppercut applies
    WeakPower then VulnerablePower after its DamageCmd.  A play that resolves more than once (Throwing Axe,
    DuplicationPower, OneTwoPunchPower) runs OnPlay again, so each resolution re-applies them.
    """
    if card in CARD_VULNERABLE_TARGET:
        return (("VulnerablePower", CARD_VULNERABLE_TARGET[card] + (1 if card in {BASH, SQUASH} and upgraded else 0)),)
    if card == UPPERCUT:
        return (("WeakPower", 1 + (1 if upgraded else 0)), ("VulnerablePower", 1 + (1 if upgraded else 0)))
    return ()
# Flat card draw with no other effect - a Skill that just replaces itself with more options.
CARD_DRAW = {DRUM_OF_BATTLE: 2, MASTER_OF_STRATEGY: 3, POMMEL_STRIKE: 1, FINESSE: 1, OFFERING: 3, FLASH_OF_STEEL: 1}
# Score per drawn card inside _greedy_action's one-ply ordering, bounded by the energy left to
# spend on it. Deliberately below a Strike's 6 damage so a draw reorders around zero-score plays
# without outranking a real attack. Tuning knob.
GREEDY_DRAW_VALUE = 1.5
# A line that dies to the incoming enemy phase is a loss whatever it deals, so it must rank below
# any line that survives. Applied as a penalty rather than a skip so that among doomed lines the
# one dealing damage still wins (test_greedy_action_avoids_self_kill pins that). Tuning knob.
GREEDY_DEATH_PENALTY = 100.0
# Cards that require an enemy target because they deal damage (AllEnemies/RandomEnemy attacks
# still take an index here even though the actual targeting ignores it - see WHIRLWIND).
ATTACKS = {
    STRIKE, BASH, ANGER, BLUDGEON, STOMP, DISMANTLE, BULLY, IRON_WAVE, TWIN_STRIKE, CINDER, ASHEN_STRIKE, HEMOKINESIS, PERFECTED_STRIKE, UNRELENTING, GIANT_ROCK, BREAKTHROUGH,
    WHIRLWIND, FEED, BYRD_SWOOP, PILLAGE, BREAK, HOWL_FROM_BEYOND, RAMPAGE, THUNDERCLAP, BOLAS, DRAMATIC_ENTRANCE, FISTICUFFS, THRUMMING_HATCHET, ULTIMATE_STRIKE,
    MOLTEN_FIST, POMMEL_STRIKE, MIND_BLAST, BODY_SLAM, PACTS_END, HEADBUTT, NEOWS_FURY, SQUASH, TEAR_ASUNDER, UPPERCUT, FIEND_FIRE, SPITE, VOLLEY, MANGLE, PECK, EXTERMINATE, SETUP_STRIKE, SWORD_BOOMERANG,
    MAUL, THRASH, FIGHT_ME, SALVO, FLASH_OF_STEEL, CONFLAGRATION,
}
# Cards the game can never generate for this model's character: Stoke and Infernal Blade both draw
# from `Owner.Character.CardPool.GetUnlockedCards(...)` (decompiled), which is the character's own
# pool only - never the colorless pool.  The model can still score these cards when they enter the
# deck through rewards or events, so only the generation sets exclude them.
CARDS_OUTSIDE_THE_CHARACTER_POOL = {
    "Believe in You", "Bolas", "Byrd Swoop", "Dramatic Entrance", "Enlightenment", "Equilibrium",
    "Exterminate", "Fasten", "Finesse", "Fisticuffs", "Flash of Steel", "Giant Rock", "Impatience",
    "Lift", "Mad Science", "Master of Strategy", "Maul", "Metamorphosis", "Mind Blast",
    "Neow's Fury", "Panache", "Peck", "Production", "Purity", "Relax", "Salvo", "Squash",
    "Thrumming Hatchet", "Toric Toughness", "Ultimate Defend", "Ultimate Strike", "Volley",
}
# ponytail: generation pool is limited to modeled non-Basic attacks; expand it with the full
# CardPool when generated-card coverage becomes a measured bottleneck.
# Infernal Blade (decompiled) filters `Owner.Character.CardPool.GetUnlockedCards(...)` by
# CardType.Attack, so the same character-pool restriction as STOKE_GENERATION applies here.
INFERNAL_BLADE_ATTACKS = tuple(sorted((ATTACKS - {STRIKE, BASH}) - CARDS_OUTSIDE_THE_CHARACTER_POOL))
# ponytail: Stoke draws from the character's whole unlocked pool; this model can only generate
# cards it knows, so the pool is every modeled non-Basic, non-Status card that is also in that
# pool. Widen it when generated-card coverage becomes a measured bottleneck.
# What a player actually picks when a card asks them to exhaust one card from hand: dead weight
# first. Frantic Escape is deliberately absent - it is the only answer to Sandpit.
EXHAUST_FODDER = {WOUND, DAZED, SLIMED, TOXIC, BURN, INFECTION, DECAY, BECKON, BAD_LUCK}
# Cards the game refuses to upgrade: every one of these overrides MaxUpgradeLevel => 0 in the
# decompiled model (curses and status cards, plus Frantic Escape), so Apotheosis never touches
# them. Only names this model knows are listed.
NON_UPGRADABLE = {
    WOUND, DAZED, SLIMED, TOXIC, BURN, INFECTION, DECAY, BECKON, BAD_LUCK,
    DOUBT, REGRET, SHAME, NORMALITY, FRANTIC_ESCAPE,
}
STOKE_GENERATION = tuple(sorted(
    # Apotheosis sits in EventCardPool, so CardFactory.GetForCombat never generates it here.
    set(CARD_COST) - {STRIKE, DEFEND, BASH, SLIMED, FRANTIC_ESCAPE, TOXIC, BURN, DAZED, INFECTION, DECAY, WOUND, BECKON, BAD_LUCK, APOTHEOSIS}
    - CARDS_OUTSIDE_THE_CHARACTER_POOL
))
# CardType.Power cards represented by this compact Ironclad model.  The live bridge already
# applies any other power's effect; these are the power cards the rollout currently knows by name.
POWERS = {STAMPEDE, VICIOUS, INFLAME, RUPTURE, INFERNO, CRUELTY, STONE_ARMOR, FEEL_NO_PAIN, BARRICADE, PYRE, UNMOVABLE, AGGRESSION, DARK_EMBRACE, CRIMSON_MANTLE, HELLRAISER, FASTEN, DEMON_FORM, JUGGERNAUT, JUGGLING, PANACHE, STRATAGEM}
# Self-targeting skills and powers that never need a target.
UNTARGETED = {
    SECRET_WEAPON,
    DEFEND, SHRUG, BATTLE_TRANCE, SLIMED, FRANTIC_ESCAPE, RELAX, INFLAME, INFERNO, CRUELTY, PRIMAL_FORCE, BLOODLETTING, BLOOD_WALL, EQUILIBRIUM, IMPERVIOUS, LIFT, ULTIMATE_DEFEND, BARRICADE, PYRE, ARMAMENTS,
    FLAME_BARRIER, NOT_YET, OFFERING, DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE, BELIEVE_IN_YOU, FINESSE, RUPTURE, STONE_ARMOR, FEEL_NO_PAIN, SECOND_WIND, ENLIGHTENMENT,
    TRUE_GRIT, BURNING_PACT, EVIL_EYE, BRAND, INFERNAL_BLADE, RAGE, COLOSSUS, VOLLEY, UNMOVABLE, EXPECT_A_FIGHT, AGGRESSION, DARK_EMBRACE, CRIMSON_MANTLE, FORGOTTEN_RITUAL, SWORD_BOOMERANG, HELLRAISER,
    TORIC_TOUGHNESS, HAVOC, STOKE, METAMORPHOSIS, VICIOUS, FASTEN, DEMON_FORM, STAMPEDE, CASCADE, JUGGERNAUT, PURITY, APOTHEOSIS, JUGGLING, PANACHE, ONE_TWO_PUNCH,
STRATAGEM, }
# CardType.Skill cards (verified against each card's OnPlay base(cost, CardType.X, ...) constructor
# call), used by Infested Prism's VitalSparkPower/TaintedPower Tainted-card mechanic below.
SKILLS = {
    SECRET_WEAPON,
    DEFEND, SHRUG, BATTLE_TRANCE, PRIMAL_FORCE, RELAX, TREMBLE, BLOODLETTING, BLOOD_WALL, DOMINATE, EQUILIBRIUM, IMPERVIOUS, LIFT, ULTIMATE_DEFEND, TAUNT, ARMAMENTS,
    FLAME_BARRIER, NOT_YET, OFFERING, DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE, BELIEVE_IN_YOU, FINESSE, SECOND_WIND, ENLIGHTENMENT, FORGOTTEN_RITUAL,
    TRUE_GRIT, BURNING_PACT, EVIL_EYE, BRAND, INFERNAL_BLADE, RAGE, COLOSSUS, EXPECT_A_FIGHT, TORIC_TOUGHNESS, HAVOC, STOKE, METAMORPHOSIS, CASCADE, PURITY, APOTHEOSIS, ONE_TWO_PUNCH,
}
SELF_DAMAGE = {HEMOKINESIS: 2, BLOODLETTING: 3, BLOOD_WALL: 2, BREAKTHROUGH: 1, OFFERING: 6, BRAND: 1}
# CardModel.GetResultPileTypeForCardPlay sends a played card to the exhaust pile right away when it
# carries CardKeyword.Exhaust - on play, not at turn end.  Exhausting a card is what fires
# ForgottenSoul and Charon's Ashes, so this list is not cosmetic.  It is NOT the decompile's
# CardKeyword.Exhaust mentions: 119 card files mention that token, but 10 of the ones here mention it
# only in a hover tip and the recorded plays show the played card landing in the DISCARD - Burning Pact
# (37 plays, exhaust +1 for the target and discard +1 for itself), Evil Eye (74 plays, exhaust +0),
# True Grit (47 plays, exhaust +1 for its victim and discard +1), Howl From Beyond (6 plays, exhaust +0),
# Havoc (5), Brand (4).  Keeping those in here inflated the inferred play counters through the extra
# hand departure and made LetterOpener fire one Skill early.  Slimed is listed even though its own
# branch handles it, so the keyword stays visible next to the others.
# Ashen Strike (4 recorded plays: exhaust +0, discard +1) and Second Wind (43 recorded plays: every one
# has discard +1, the exhaust side is its own effect exhausting other cards) go to the DISCARD in the
# game, so they must not be in here - the extra exhaust inflated Ashen Strike's own damage, which scales
# with len(exhaust_before), and fired ForgottenSoul on plays where the game fired nothing.
EXHAUSTS = {METAMORPHOSIS, RELAX, TREMBLE, FEED, DOMINATE, NOT_YET, OFFERING, MASTER_OF_STRATEGY, PRODUCTION, ENLIGHTENMENT, FIEND_FIRE, INFERNAL_BLADE, FORGOTTEN_RITUAL, NEOWS_FURY, PURITY, APOTHEOSIS, DRAMATIC_ENTRANCE, IMPERVIOUS, MOLTEN_FIST, SLIMED, TOXIC}
# Cards tagged as Strike, used by Perfected Strike scaling.
# CanonicalTags per decompiled card (v0.107.1): Pommel Strike is tagged Strike too, so Perfected
# Strike counts it.  Panel replay over the Perfected Strike decisions resolved 27 of 31 mismatches
# once Pommel Strike was included (the remaining 4 have other causes).
STRIKE_TAGGED = {STRIKE, TWIN_STRIKE, PERFECTED_STRIKE, ASHEN_STRIKE, SETUP_STRIKE, POMMEL_STRIKE}

# Relics with an automatic in-combat effect the search() rollout needs to see to project future
# turns correctly (verified against each relic's decompiled OnPlay-equivalent hook body). Relics
# with only a one-time combat-start or turn<=1 effect are deliberately excluded here - the very
# first observation of a fight already reflects them (HP/block/energy/powers are read live from
# the game), and search() never re-simulates turn 1 once combat is already past it.
RELIC_BRIMSTONE, RELIC_MERCURY_HOURGLASS, RELIC_ART_OF_WAR = "RELIC.BRIMSTONE", "RELIC.MERCURY_HOURGLASS", "RELIC.ART_OF_WAR"
RELIC_SCREAMING_FLAGON, RELIC_CLOAK_CLASP = "RELIC.SCREAMING_FLAGON", "RELIC.CLOAK_CLASP"
RELIC_CANDELABRA, RELIC_CAPTAINS_WHEEL, RELIC_HORN_CLEAT = "RELIC.CANDELABRA", "RELIC.CAPTAINS_WHEEL", "RELIC.HORN_CLEAT"
RELIC_LOST_WISP, RELIC_PAPER_PHROG, RELIC_STRIKE_DUMMY = "RELIC.LOST_WISP", "RELIC.PAPER_PHROG", "RELIC.STRIKE_DUMMY"
RELIC_GREMLIN_HORN, RELIC_UNCEASING_TOP, RELIC_TOASTY_MITTENS = "RELIC.GREMLIN_HORN", "RELIC.UNCEASING_TOP", "RELIC.TOASTY_MITTENS"
RELIC_BRILLIANT_SCARF = "RELIC.BRILLIANT_SCARF"
# BrilliantScarf.ShouldModifyCost fires only while exactly Cards-1 cards have been played
# this turn, i.e. the turn's fifth card is free.
BRILLIANT_SCARF_FREE_AFTER = 4
RELIC_SPARKLING_ROUGE, RELIC_STONE_CALENDAR = "RELIC.SPARKLING_ROUGE", "RELIC.STONE_CALENDAR"
RELIC_MR_STRUGGLES = "RELIC.MR_STRUGGLES"
RELIC_HAPPY_FLOWER, RELIC_PENDULUM = "RELIC.HAPPY_FLOWER", "RELIC.PENDULUM"
RELIC_KUNAI, RELIC_SHURIKEN, RELIC_ORNAMENTAL_FAN, RELIC_KUSARIGAMA = "RELIC.KUNAI", "RELIC.SHURIKEN", "RELIC.ORNAMENTAL_FAN", "RELIC.KUSARIGAMA"
RELIC_LETTER_OPENER, RELIC_NUNCHAKU, RELIC_TUNING_FORK = "RELIC.LETTER_OPENER", "RELIC.NUNCHAKU", "RELIC.TUNING_FORK"
RELIC_DEMON_TONGUE, RELIC_CENTENNIAL_PUZZLE = "RELIC.DEMON_TONGUE", "RELIC.CENTENNIAL_PUZZLE"
RELIC_BEATING_REMNANT, RELIC_BELLOWS, RELIC_BELT_BUCKLE = "RELIC.BEATING_REMNANT", "RELIC.BELLOWS", "RELIC.BELT_BUCKLE"
RELIC_BOOK_OF_FIVE_RINGS, RELIC_BURNING_STICKS, RELIC_CHANDELIER = "RELIC.BOOK_OF_FIVE_RINGS", "RELIC.BURNING_STICKS", "RELIC.CHANDELIER"
RELIC_CHARONS_ASHES, RELIC_CHEMICAL_X, RELIC_GAME_PIECE = "RELIC.CHARONS_ASHES", "RELIC.CHEMICAL_X", "RELIC.GAME_PIECE"
RELIC_INTIMIDATING_HELMET, RELIC_JOSS_PAPER, RELIC_LAVA_LAMP = "RELIC.INTIMIDATING_HELMET", "RELIC.JOSS_PAPER", "RELIC.LAVA_LAMP"
RELIC_LIZARD_TAIL, RELIC_LUCKY_FYSH, RELIC_MEAT_ON_THE_BONE = "RELIC.LIZARD_TAIL", "RELIC.LUCKY_FYSH", "RELIC.MEAT_ON_THE_BONE"
RELIC_MUMMIFIED_HAND, RELIC_ORICHALCUM, RELIC_PARRYING_SHIELD = "RELIC.MUMMIFIED_HAND", "RELIC.ORICHALCUM", "RELIC.PARRYING_SHIELD"
RELIC_PEN_NIB, RELIC_PERMAFROST, RELIC_PETRIFIED_TOAD = "RELIC.PEN_NIB", "RELIC.PERMAFROST", "RELIC.PETRIFIED_TOAD"
RELIC_POCKETWATCH, RELIC_RAINBOW_RING, RELIC_RAZOR_TOOTH, RELIC_PAELS_BLOOD = "RELIC.POCKETWATCH", "RELIC.RAINBOW_RING", "RELIC.RAZOR_TOOTH", "RELIC.PAELS_BLOOD"
RELIC_PAELS_FLESH, RELIC_PAELS_TEARS, RELIC_VERY_HOT_COCOA = "RELIC.PAELS_FLESH", "RELIC.PAELS_TEARS", "RELIC.VERY_HOT_COCOA"
RELIC_FIDDLE, RELIC_BLOOD_SOAKED_ROSE, RELIC_POLLINOUS_CORE = "RELIC.FIDDLE", "RELIC.BLOOD_SOAKED_ROSE", "RELIC.POLLINOUS_CORE"
RELIC_FORGOTTEN_SOUL = "RELIC.FORGOTTEN_SOUL"
RELIC_RED_SKULL, RELIC_REPTILE_TRINKET, RELIC_RIPPLE_BASIN = "RELIC.RED_SKULL", "RELIC.REPTILE_TRINKET", "RELIC.RIPPLE_BASIN"
RELIC_RUINED_HELMET, RELIC_SELF_FORMING_CLAY, RELIC_STURDY_CLAMP = "RELIC.RUINED_HELMET", "RELIC.SELF_FORMING_CLAY", "RELIC.STURDY_CLAMP"
RELIC_TUNGSTEN_ROD, RELIC_UNSETTLING_LAMP, RELIC_VAMBRACE = "RELIC.TUNGSTEN_ROD", "RELIC.UNSETTLING_LAMP", "RELIC.VAMBRACE"
RELIC_THROWING_AXE = "RELIC.THROWING_AXE"
RELIC_VENERABLE_TEA_SET = "RELIC.VENERABLE_TEA_SET"
TEST_SUBJECT, RESPAWN_MOVE = "MONSTER.TEST_SUBJECT", "RESPAWN_MOVE"


@dataclass(frozen=True)
class Enemy:
    model: str
    hp: int
    move: str
    values: tuple[tuple[str, int | bool], ...]
    slot: str = ""
    block: int = 0
    powers: tuple[tuple[str, int], ...] = ()
    history: tuple[str, ...] = ()
    escaped: bool = False
    primary: bool = True
    respawns: int = 0

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.escaped


@dataclass(frozen=True)
class Card:
    name: str
    upgraded: bool = False
    enchantment: str | None = None
    # FranticEscape.OnPlay calls EnergyCost.AddThisCombat(1), so each copy gets permanently more
    # expensive for the rest of the combat every time that same copy is played.
    extra_cost: int = 0
    bound: bool = False
    # A card the game's own legal actions excluded at this decision (the Bound gate after the first
    # Bound play of the turn, a Snecko card that is currently too expensive, ...). The live legal
    # actions are authoritative for the rollout's first move, so this stays separate from the
    # affliction flag `bound`, which by itself does not block play.
    unplayable_this_turn: bool = False
    # Mad Science rolls a CardType and a RiderEffect per copy, so two copies of the same card id
    # can be a 3-hit attack and a Strength power. The bridge reports both per copy.
    variant: str | None = None
    rider: str | None = None
    variant_value: int = 0


CardValue = str | Card


def card_name(card: CardValue) -> str:
    return card.name if isinstance(card, Card) else card


@dataclass(frozen=True)
class Combat:
    player_hp: int
    hand: tuple[CardValue, ...]
    draw_pile: tuple[CardValue, ...]
    discard_pile: tuple[CardValue, ...]
    enemies: tuple[Enemy, ...]
    player_block: int = 0
    player_powers: tuple[tuple[str, int], ...] = ()
    energy: int = 3
    max_energy: int = 3
    # Pael's Tears carries unused energy across the enemy turn as a one-shot bonus.
    paels_tears_pending: bool = False
    turn: int = 1
    exhaust_pile: tuple[CardValue, ...] = ()
    played_this_turn: bool = False
    player_relics: tuple[str, ...] = ()
    # Per-turn combo counters (Kunai/Shuriken/Ornamental Fan/Kusarigama/Letter Opener) - reset
    # to 0 at the start of every player turn, unlike the *_combat counters below.
    attacks_played_this_turn: int = 0
    skills_played_this_turn: int = 0
    # UnmovablePower doubles the first N block-producing card plays each turn, not each
    # individual block grant (Evil Eye can grant block twice during one play).
    block_cards_this_turn: int = 0
    # Every card play, any type - drives SlowPower's damage-taken ramp (Bygone Effigy). Also
    # reset at the start of every player turn.
    cards_played_this_turn: int = 0
    # ChainsOfBindingPower.ShouldPlay: a Bound card is playable until one Bound card has been played
    # this turn, then the remaining Bound cards are gated off (the flag is cleared at turn end, and
    # the afflictions themselves are cleared there too).
    bound_played_this_turn: bool = False
    # ChainsOfBindingPower.AfterCardDrawn caps at its amount using CardAfflictionEntry counted
    # happened-this-turn, so the cap does not recover when an afflicted card leaves hand. The model
    # previously counted bound cards still in hand, which re-opened the cap.
    chains_afflicted_this_turn: int = 0
    # HellraiserPower safety cap: AutoPlay can recurse through exhaust-triggered draws.
    hellraiser_autoplays_this_turn: int = 0
    # Havoc/Pyre auto-plays one card per play, and the auto-played card's own play re-enters the
    # autoplay path while the power is active, so the recursion needs a safety cap. Real run evidence:
    # control (e808bdf) hit RecursionError at seq 138 with PyrePower active, before any cap existed.
    pyre_autoplays_this_turn: int = 0
    # Enlightenment.OnPlay: caps every hand card's cost at 1 for the rest of this turn (reduceOnly
    # - never raises a cheaper card). Reset alongside the other per-turn counters.
    enlightened_this_turn: bool = False
    # DuplicationPower / OneTwoPunchPower add one extra resolution to the play being resolved, so
    # that play's damage or block applies twice. Set per action, cleared at the start of every
    # action and every turn.
    play_duplicated: bool = False
    # PanachePower's CardsLeft: 5 cards played after the Panache play deal its damage to every
    # hittable enemy, then reset. The play that applied the power does not count.
    panache_cards_this_turn: int = 0
    # Whole-combat cumulative counters (Nunchaku/Tuning Fork) - never reset until the fight ends.
    attacks_played_combat: int = 0
    skills_played_combat: int = 0
    # Kunai / Shuriken grant their power in AfterCardPlayed, i.e. after the attack that triggered them
    # has resolved, so the 3rd attack of the turn does not benefit from its own relic bonus.  A grant
    # waiting here is folded into player_powers when the next card is played (or at the turn end).
    pending_combo_powers: tuple[tuple[str, int], ...] = ()
    # DemonTongue.AfterDamageReceived: only the first unblocked hit each turn heals; reset
    # alongside the per-turn combo counters.
    damaged_this_turn: bool = False
    # Spite checks damage received during the current player side, not the preceding enemy side.
    lost_hp_this_turn: bool = False
    exhausted_this_turn: bool = False
    # CentennialPuzzle.AfterDamageReceived: only the first unblocked hit of the whole combat
    # draws cards; never reset.
    centennial_puzzle_used: bool = False
    # State needed by the remaining combat relic hooks.  Optional/one-shot values are kept in
    # the combat snapshot so a rollout branch never mutates the live observation.
    player_max_hp: int = 80
    player_potions: tuple[str, ...] = ()
    belt_buckle_applied: bool = False
    damage_received_this_turn: int = 0
    cards_played_last_turn: int | None = None
    free_cards: tuple[CardValue, ...] = ()
    powers_played_this_turn: int = 0
    # ToricToughnessPower is Instanced: each copy played stores the block it actually granted and
    # re-grants exactly that much on each of the next two block clears.  One (stored, uses) pair
    # per live instance, since two copies can hold different stored amounts.
    toric_pending: tuple[tuple[int, int], ...] = ()
    # Times the player has taken unblocked damage this combat; Tear Asunder's hit count is 1 + this.
    unblocked_hits: int = 0
    # Maul.OnPlay buffs the Damage BaseValue of every Maul the player owns by Increase (1, 2 when
    # upgraded); Thrash.OnPlay exhausts a random attack from hand and adds its damage to itself.
    # Both are permanent, so within one rollout they stack on top of the per-copy damage the
    # bridge reported at the start of the search.
    maul_bonus: int = 0
    thrash_bonus: int = 0
    bellows_used: bool = False
    burning_sticks_used: bool = False
    joss_paper_count: int = 0
    permafrost_used: bool = False
    rainbow_ring_used: bool = False
    red_skull_active: bool = False
    lizard_tail_used: bool = False
    ruined_helmet_used: bool = False
    # ThrowingAxe.ModifyCardPlayCount adds one play to the first card we play in each combat, and
    # AfterModifyingCardPlayCount consumes it until the next CombatRoom.  The bridge exports the
    # game's own combat-long play counts, so cards_played_combat == 0 is the game's "not used yet".
    cards_played_combat: int = 0
    vambrace_used: bool = False
    unsettling_lamp_used: bool = False
    upgraded_cards: tuple[str, ...] = ()

    @property
    def terminal(self) -> bool:
        return self.player_hp <= 0 or not any(
            (enemy.alive or (enemy.model == TEST_SUBJECT and enemy.move == RESPAWN_MOVE)) and enemy.primary
            for enemy in self.enemies
        )


def card_is_upgraded(combat: Combat, card: CardValue) -> bool:
    return card.upgraded if isinstance(card, Card) else card in combat.upgraded_cards


def _is_upgradable_copy(combat: Combat, card: CardValue) -> bool:
    """A copy the game will accept an upgrade on: a card this model has a value for, one that
    does not override MaxUpgradeLevel 0 (curses and status cards), and not already upgraded."""
    name = card_name(card)
    return name in CARD_COST and name not in NON_UPGRADABLE and not card_is_upgraded(combat, card)


def _upgrade_card(card: CardValue) -> CardValue:
    return replace(card, upgraded=True) if isinstance(card, Card) else card


def _copy_card(name: str, source: CardValue) -> CardValue:
    return Card(name, source.upgraded, source.enchantment) if isinstance(source, Card) else name


def _remember_legacy_upgrades(combat: Combat, cards: tuple[CardValue, ...]) -> tuple[str, ...]:
    names = tuple(card_name(card) for card in cards if isinstance(card, str))
    return tuple(dict.fromkeys(combat.upgraded_cards + names))


def _dict(items: tuple[tuple, ...]) -> dict:
    return dict(items)


@lru_cache(maxsize=8192)
def _power_lookup(items: tuple[tuple[str, int], ...], name: str) -> int:
    return dict(items).get(name, 0)


def _power(items: tuple[tuple[str, int], ...], name: str) -> int:
    return _power_lookup(items, name)


def _add_power(items: tuple[tuple[str, int], ...], name: str, amount: int) -> tuple[tuple[str, int], ...]:
    powers = _dict(items)
    powers[name] = powers.get(name, 0) + amount
    if not powers[name]:
        del powers[name]
    return tuple(sorted(powers.items()))


def _tick_down_power(items: tuple[tuple[str, int], ...], name: str) -> tuple[tuple[str, int], ...]:
    return _add_power(items, name, -1) if _power(items, name) > 0 else items


# The three debuffs whose AfterSideTurnEnd hook is gated on the enemy side.
DEBUFF_POWERS = ("VulnerablePower", "WeakPower", "FrailPower")


def _tick_debuffs(powers: tuple[tuple[str, int], ...], running: tuple[str, ...]) -> tuple[tuple[str, int], ...]:
    """Tick only the debuffs that were already running when the enemy side began (see the snapshot in
    step()'s END_TURN path): a stack the enemy phase itself applied is exempt from this turn's tick."""
    for name in running:
        powers = _tick_down_power(powers, name)
    return powers


def _apply_enemy_debuff(enemy: Enemy, power: str, amount: int) -> Enemy:
    """Apply a visible debuff, consuming one Artifact stack when present."""
    if amount <= 0:
        return enemy
    if _power(enemy.powers, "ArtifactPower"):
        return replace(enemy, powers=_add_power(enemy.powers, "ArtifactPower", -1))
    return replace(enemy, powers=_add_power(enemy.powers, power, amount))


BLOCK_CARDS = set(CARD_BLOCK) | {SHRUG, RELAX, TAUNT, SECOND_WIND}
# Cards declaring CardTag.Defend, which is what FastenPower keys off.
DEFEND_TAGGED = {DEFEND, ULTIMATE_DEFEND}
DEBUFF_CARDS = set(CARD_VULNERABLE_TARGET) | {TAUNT, TREMBLE, THUNDERCLAP, DOMINATE, MOLTEN_FIST, UPPERCUT}


def _sync_red_skull(combat: Combat) -> Combat:
    """Keep Red Skull's conditional Strength in sync with the simulated HP."""
    if RELIC_RED_SKULL not in combat.player_relics or combat.player_max_hp <= 0:
        return combat
    active = combat.player_hp * 2 <= combat.player_max_hp
    if active == combat.red_skull_active:
        return combat
    powers = _add_power(combat.player_powers, "StrengthPower", 3 if active else -3)
    return replace(combat, player_powers=powers, red_skull_active=active)


def _sync_belt_buckle(combat: Combat) -> Combat:
    """Belt Buckle is already reflected at combat start; keep potion-free snapshots consistent."""
    if RELIC_BELT_BUCKLE not in combat.player_relics:
        return combat
    active = not combat.player_potions
    if active == combat.belt_buckle_applied:
        return combat
    return replace(
        combat,
        player_powers=_add_power(combat.player_powers, "DexterityPower", 2 if active else -2),
        belt_buckle_applied=active,
    )


def _survive_with_fairy_in_a_bottle(combat: Combat, hp: int, max_hp: int) -> tuple[int, tuple[str, ...]]:
    """Let FairyInABottle prevent the player's death, and return the HP and remaining potions.

    It is a PotionUsage.Automatic potion, so it is never offered as an action: CreatureCmd.Kill zeroes
    the HP, Hook.ShouldDie asks the models whether the creature really dies, this potion answers no, and
    AfterPreventingDeath heals Math.Max(MaxHp * 0.3m, 1m).  The player comes back at 30% of max HP with
    the potion gone.  Both damage paths need it - _apply_player_damage for card and effect damage, and
    _enemy_turn for the enemy's own attacks - because _enemy_turn tracks the player's HP in a local
    instead of routing through _apply_player_damage.  Without it the rollout prices a lethal turn as a
    loss that the game would have survived, and the agent has no reason to pick the potion up at all.
    """
    if hp > 0 or POTION_FAIRY_IN_A_BOTTLE not in combat.player_potions:
        return hp, combat.player_potions
    potions = list(combat.player_potions)
    potions.remove(POTION_FAIRY_IN_A_BOTTLE)
    return max(max_hp * 30 // 100, 1), tuple(potions)


def _apply_player_damage(combat: Combat, amount: int, *, trigger_inferno: bool = True) -> Combat:
    """Apply unblocked HP loss and the relics that modify it."""
    if amount <= 0:
        return combat
    tungsten = 1 if RELIC_TUNGSTEN_ROD in combat.player_relics else 0
    actual = max(0, amount - tungsten)
    if RELIC_BEATING_REMNANT in combat.player_relics:
        actual = min(actual, max(0, 20 - combat.damage_received_this_turn))
    # Tungsten Rod reduces each HP-loss event before Beating Remnant applies its turn-wide cap.
    if actual > 0 and _power(combat.player_powers, "BufferPower"):
        updated = replace(combat, player_powers=_add_power(combat.player_powers, "BufferPower", -1))
        return _trigger_inferno(updated) if trigger_inferno else updated
    hp = combat.player_hp - actual
    used_tail = combat.lizard_tail_used
    if hp <= 0 and RELIC_LIZARD_TAIL in combat.player_relics and not used_tail:
        hp = max(1, combat.player_max_hp // 2)
        used_tail = True
    hp, potions = _survive_with_fairy_in_a_bottle(combat, hp, combat.player_max_hp)
    powers = combat.player_powers
    if actual > 0 and RELIC_SELF_FORMING_CLAY in combat.player_relics:
        powers = _add_power(powers, "SelfFormingClayPower", 3)
    updated = _sync_red_skull(replace(
        combat, player_hp=hp, player_powers=powers, player_potions=potions,
        damage_received_this_turn=combat.damage_received_this_turn + actual,
        lost_hp_this_turn=combat.lost_hp_this_turn or actual > 0,
        lizard_tail_used=used_tail,
    ))
    return _trigger_inferno(updated) if trigger_inferno else updated


def _apply_reflected_damage(combat: Combat, amount: int) -> Combat:
    """Apply a ThornsPower reflection.

    ThornsPower.BeforeDamageReceived runs before the attack's own DamageCmd, so the player's block is
    still standing and absorbs the reflection first (Unpowered is not Unblockable).  Two panel
    decisions show it: EAIF2UUVCK seq 294 (block 7, Thorns 5, one hit) lost no HP, and VTW80ZJA2G
    seq 279 (block 5, Thorns 5, two hits) lost exactly the 5 that block could not cover.
    """
    if amount <= 0:
        return combat
    blocked = min(combat.player_block, amount)
    return _apply_player_damage(replace(combat, player_block=combat.player_block - blocked), amount - blocked)


def _after_exhaust(combat: Combat, cards: tuple[CardValue, ...], rng: random.Random, data: dict) -> Combat:
    """Resolve recurring exhaust hooks for one or more exhausted cards."""
    if not cards:
        return combat
    relics = combat.player_relics
    joss_count = combat.joss_paper_count + (len(cards) if RELIC_JOSS_PAPER in relics else 0)
    if RELIC_JOSS_PAPER in relics and joss_count >= 5:
        combat = replace(combat, joss_paper_count=joss_count % 5, exhausted_this_turn=True)
        combat = _draw_into_combat(combat, joss_count // 5, data, rng)
        joss_count %= 5
    else:
        combat = replace(combat, joss_paper_count=joss_count, exhausted_this_turn=True)
    burning_used = combat.burning_sticks_used
    if RELIC_BURNING_STICKS in relics and not burning_used:
        skill = next((card for card in cards if card_name(card) in SKILLS), None)
        if skill is not None:
            combat = replace(combat, hand=combat.hand + (skill,), burning_sticks_used=True)
            burning_used = True
    enemies = list(combat.enemies)
    if RELIC_CHARONS_ASHES in relics:
        for _ in cards:
            enemies = [_damage_enemy(enemy, 3, powered=False) if enemy.alive else enemy for enemy in enemies]
        combat = replace(combat, enemies=tuple(enemies))
    if RELIC_FORGOTTEN_SOUL in relics:
        # ForgottenSoul.AfterCardExhausted: 1 unpowered damage to one random hittable enemy per
        # exhausted card (Rng.CombatTargets), not to all of them like Charon's Ashes.
        for _ in cards:
            alive = [index for index, enemy in enumerate(enemies) if enemy.alive]
            if not alive:
                break
            target = rng.choice(alive)
            enemies = [
                _damage_enemy(enemy, 1, powered=False) if index == target and enemy.alive else enemy
                for index, enemy in enumerate(enemies)
            ]
        combat = replace(combat, enemies=tuple(enemies))
    draw_n = _power(combat.player_powers, "DarkEmbracePower") * len(cards)
    if draw_n:
        combat = _draw_into_combat(combat, draw_n, data, rng)
    block = _power(combat.player_powers, "FeelNoPainPower") * len(cards)
    return replace(
        combat, enemies=combat.enemies,
        player_block=combat.player_block + block, burning_sticks_used=combat.burning_sticks_used or burning_used,
        exhausted_this_turn=True,
    )


def _after_power_play(combat: Combat, rng: random.Random, data: dict) -> Combat:
    """Resolve relics whose trigger is a Power card being played."""
    if not combat.player_relics or not combat.powers_played_this_turn:
        return combat
    relics = combat.player_relics
    if RELIC_GAME_PIECE in relics:
        combat = _draw_into_combat(combat, 1, data, rng)
    if RELIC_PERMAFROST in relics and not combat.permafrost_used:
        combat = replace(combat, player_block=combat.player_block + 7, permafrost_used=True)
    if RELIC_MUMMIFIED_HAND in relics:
        candidates = [card for card in combat.hand if CARD_COST.get(card_name(card), 0) > 0]
        if not candidates:
            candidates = list(combat.hand)
        if candidates:
            combat = replace(combat, free_cards=combat.free_cards + (rng.choice(candidates),))
    if RELIC_RAINBOW_RING in relics and not combat.rainbow_ring_used:
        if combat.attacks_played_this_turn and combat.skills_played_this_turn:
            combat = replace(
                combat,
                player_powers=_add_power(_add_power(combat.player_powers, "StrengthPower", 1), "DexterityPower", 1),
                rainbow_ring_used=True,
            )
    return combat


def _amount(expression: str, values: dict) -> int:
    if isinstance(expression, (int, float)):
        return int(expression)
    expression = re.sub(r"(?<=\d)[mfd]\b", "", expression)

    def calculate(node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -calculate(node.operand)
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left, right = calculate(node.left), calculate(node.right)
            return left + right if isinstance(node.op, ast.Add) else left - right if isinstance(node.op, ast.Sub) else left * right
        if isinstance(node, ast.Attribute) and node.attr == "Count":
            # e.g. base.Creature.CombatState.Players.Count: this project only plays solo.
            return 1
        raise ValueError(f"unsupported amount: {expression}")

    return int(calculate(ast.parse(expression, mode="eval").body))


_SPECS_SOURCE: dict | None = None
_SPECS_CACHE: dict[str, dict] = {}


def _specs(data: dict) -> dict[str, dict]:
    global _SPECS_SOURCE, _SPECS_CACHE
    if data is not _SPECS_SOURCE:
        _SPECS_SOURCE = data
        _SPECS_CACHE = {monster["id"]: monster for monster in data.get("monsters", [])}
    return _SPECS_CACHE


STUNNED_MOVE = "STUNNED"


def _stunned_state(spec: dict) -> dict:
    """Return the state an enemy is in while the bridge reports its move as STUNNED.

    MonsterModel.stunnedMoveId ("STUNNED") is created at runtime by Creature.StunInternal
    (MoveState("STUNNED", <the monster's stun logic>, StunIntent), whose FollowUpStateId defaults to
    the last state in the state log), so the exporter never writes it into the state machine even
    though the bridge reports it as the enemy's current move: 1,590 recorded observations (Bowlbug
    Rock 1,046, Tunneler 431, Thieving Hopper 85, Slumbering Beetle 28).  Each of those monsters has
    its own stun state exported under its real name - Tunneler and Bowlbug Rock both have DIZZY_MOVE
    with a StunIntent and no effects - and that state carries the follow-up the game really resumes
    to: Tunneler DIZZY_MOVE -> BITE_MOVE covers the 382 observed STUNNED -> BITE_MOVE transitions,
    Bowlbug Rock DIZZY_MOVE -> HEADBUTT_MOVE covers 928.  A stunned monster does nothing on its turn
    (a Tunneler at STUNNED left the player at 88 HP across the enemy phase), and its move id is not
    added to the history, which is what the following observation shows.
    """
    stun_state = next(
        (
            state
            for state in spec["states"]
            if any(intent.get("type") == "StunIntent" for intent in state.get("intents", ()))
        ),
        None,
    )
    if stun_state is not None:
        return stun_state
    return {
        "id": STUNNED_MOVE,
        "type": "MoveState",
        "perform": "StunMove",
        "intents": [{"type": "StunIntent"}],
        "next": spec["initial_state"],
        "effects": [],
    }


def _move_state(spec: dict, enemy: Enemy) -> dict:
    if enemy.move == STUNNED_MOVE:
        return _stunned_state(spec)
    return _state(spec, enemy.move)


def _state(spec: dict, state_id: str) -> dict:
    return next(state for state in spec["states"] if state["id"] == state_id)


def _condition(expression: str, enemy: Enemy, enemies: tuple[Enemy, ...] = ()) -> bool:
    values = _dict(enemy.values)
    if "SlotName ==" in expression:
        return enemy.slot == re.search(r'"([^"]+)"', expression).group(1)
    if "HasBeetleCharged" in expression:
        # FrogKnight charges once, on the first turn it finds itself under half HP; afterwards
        # HasBeetleCharged stays true and it goes back to Tongue Lash. The move history is the
        # runtime record of that flag. The "!HasBeetleCharged && hp < MaxHp / 2" branch is the
        # exact negation of this, and the trailing "!" handling below applies it.
        ceiling = int(values.get("MaxInitialHp", enemy.hp) or enemy.hp)
        result = "BEETLE_CHARGE" in enemy.history or enemy.hp >= ceiling // 2
    elif "GetAllyCount()" in expression:
        # LivingShield.GetAllyCount explicitly excludes itself (unlike Fabricator's raw
        # GetTeammatesOf): it Shield Slams while any ally lives and Smashes once left alone.
        allies = sum(other.alive and other is not enemy for other in enemies)
        match = re.search(r"GetAllyCount\(\)\s*(==|>|>=|<|<=)\s*(\d+)", expression)
        operator, threshold = match.group(1), int(match.group(2))
        result = {
            "==": allies == threshold, ">": allies > threshold, ">=": allies >= threshold,
            "<": allies < threshold, "<=": allies <= threshold,
        }[operator]
    elif expression.lstrip("!") == "CanFabricate":
        # Fabricator.CanFabricate: GetTeammatesOf counts the whole enemy side including itself,
        # so it keeps building bots until four monsters are alive, then Disintegrates instead.
        result = sum(other.alive for other in enemies) < 4
    elif expression.lstrip("!") == "CanLay":
        # Ovicopter lays three ToughEgg minions while fewer than three remain alive.
        result = sum(other.alive and other.model == "MONSTER.TOUGH_EGG" for other in enemies) < 3
    elif "HasPower<" in expression:
        name = re.search(r"HasPower<([^>]+)>", expression).group(1)
        result = _power(enemy.powers, name) > 0
    elif ".IsFront" in expression:
        result = bool(values["IsFront"])
    elif ".IsAlone" in expression:
        result = bool(values["IsAlone"])
    elif "_curseOfKnowledgeCounter" in expression:
        # Knowledge Demon's private turn counter (not in the exported state machine); tracked
        # as a synthetic power, bumped in _enemy_turn when CURSE_OF_KNOWLEDGE_MOVE executes.
        match = re.search(r"(<|>=)\s*(\d+)", expression)
        threshold, counter = int(match.group(2)), _power(enemy.powers, "CurseOfKnowledgeCounter")
        result = counter < threshold if match.group(1) == "<" else counter >= threshold
    elif expression.lstrip("!") == "IsOffBalance":
        # ImbalancedPower.AfterDamageGiven: Bowlbug Rock's IsOffBalance flips true once its
        # Headbutt lands fully blocked. The exported value is a static False (not runtime state),
        # so this reads the synthetic power _enemy_turn sets/clears around HEADBUTT_MOVE/DIZZY_MOVE.
        result = _power(enemy.powers, "OffBalancePower") > 0
    elif expression in {"runtime", "HasAmalgamDied"} and enemy.model == "MONSTER.QUEEN":
        # Queen's exporter leaves the custom post-move predicate as "runtime".  Its only
        # runtime input is whether the Torch Head Amalgam is still alive; derive both branches
        # from the live formation instead of letting every Queen rollout fall back to heuristics.
        amalgam_alive = any(other.alive and other.model == "MONSTER.TORCH_HEAD_AMALGAM" for other in enemies)
        result = amalgam_alive if expression == "runtime" else not amalgam_alive
    elif expression.lstrip("!") in values:
        # A bare formation-level flag (like IsFront/IsAlone but without the "base.Creature."
        # prefix).
        result = bool(values[expression.lstrip("!")])
    else:
        raise NotImplementedError(f"condition: {expression}")
    return not result if expression.lstrip().startswith("!") else result


def _resolve_move(
    enemy: Enemy,
    spec: dict,
    rng: random.Random,
    state_id: str | None = None,
    enemies: tuple[Enemy, ...] = (),
) -> str:
    state_id = state_id or enemy.move
    if state_id == STUNNED_MOVE:
        # The stun id itself is not exported; resolve from the monster's own stun state (or its
        # opening move when the export has none, which is what the observed resumes do).
        state_id = _stunned_state(spec)["id"]
    while _state(spec, state_id)["type"] != "MoveState":
        branch = _state(spec, state_id)
        if branch["type"] == "ConditionalBranchState":
            state_id = next(option["state"] for option in branch["branches"] if _condition(option["condition"], enemy, enemies))
            continue
        choices = []
        for option in branch["branches"]:
            history, repeat = enemy.history, option["repeat"]
            allowed = repeat == "CanRepeatForever"
            allowed |= repeat == "CannotRepeat" and (not history or history[-1] != option["state"])
            allowed |= repeat == "UseOnlyOnce" and option["state"] not in history
            if repeat == "CanRepeatXTimes":
                count = 0
                for move in reversed(history):
                    if move != option["state"]:
                        break
                    count += 1
                allowed = count < option["max_times"]
            if option["cooldown"] and option["state"] in history[-option["cooldown"] :]:
                allowed = False
            if allowed and option["weight"]:
                choices.append((option["state"], float(option["weight"])))
        if not choices:
            # The game returns the first branch when every effective weight is zero.
            state_id = branch["branches"][0]["state"]
            continue
        roll = rng.random() * sum(weight for _, weight in choices)
        for state_id, weight in choices:
            roll -= weight
            if roll <= 0:
                break
    return state_id


def _draw(draw: tuple[CardValue, ...], discard: tuple[CardValue, ...], count: int, rng: random.Random) -> tuple[tuple[CardValue, ...], tuple[CardValue, ...], tuple[CardValue, ...]]:
    draw, discard, hand = list(draw), list(discard), []
    while len(hand) < count and (draw or discard):
        if not draw:
            draw, discard = discard, []
        hand.append(draw.pop(rng.randrange(len(draw))))
    return tuple(hand), tuple(draw), tuple(discard)


def _autoplay_drawn_strikes(combat: Combat, drawn: tuple[CardValue, ...], data: dict, rng: random.Random) -> Combat:
    """HellraiserPower auto-plays each Strike-tagged card immediately after it is drawn."""
    if not drawn or not _power(combat.player_powers, "HellraiserPower"):
        return combat
    for card in drawn:
        if (
            card_name(card) not in STRIKE_TAGGED
            or card not in combat.hand
            or combat.terminal
            or combat.hellraiser_autoplays_this_turn >= 9
        ):
            continue
        alive = [index for index, enemy in enumerate(combat.enemies) if enemy.alive]
        if not alive:
            break
        hand_index = combat.hand.index(card)
        action = f"card:{hand_index}@{rng.choice(alive)}" if isinstance(card, Card) else f"{card}@{rng.choice(alive)}"
        free_cards = combat.free_cards + (card,)
        candidate = replace(
            combat, free_cards=free_cards,
            hellraiser_autoplays_this_turn=combat.hellraiser_autoplays_this_turn + 1,
        )
        if action not in legal_actions(candidate):
            continue
        combat = step(candidate, action, data, rng)
    return combat


def _autoplay_top_of_draw(combat: Combat, data: dict, rng: random.Random) -> Combat:
    """Havoc: CardPileCmd.AutoPlayFromDrawPile(1, Top, forceExhaust) - the top card of the draw
    pile resolves for free and is exhausted instead of discarded.

    ponytail: this model keeps the draw pile as an unordered bag, so _draw hands back a random
    card rather than the true top one. Track draw order if card-order effects ever need it.
    """
    if combat.pyre_autoplays_this_turn >= 9:
        return combat
    drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
    if not drawn:
        return combat
    card = drawn[0]
    combat = replace(combat, draw_pile=draw, discard_pile=discard, hand=combat.hand + (card,))
    hand_index = len(combat.hand) - 1
    base = f"card:{hand_index}" if isinstance(card, Card) else card_name(card)
    candidate = replace(
        combat, free_cards=combat.free_cards + (card,),
        pyre_autoplays_this_turn=combat.pyre_autoplays_this_turn + 1,
    )
    options = legal_actions(candidate)
    alive = [index for index, enemy in enumerate(combat.enemies) if enemy.alive]
    action = None
    if base in options:
        action = base
    elif alive:
        targeted = f"{base}@{rng.choice(alive)}"
        action = targeted if targeted in options else None
    if action is None:
        # An unplayable status or curse still leaves hand and is exhausted by forceExhaust.
        combat = replace(combat, hand=combat.hand[:-1], exhaust_pile=combat.exhaust_pile + (card,))
        return _after_exhaust(combat, (card,), rng, data)
    after = step(candidate, action, data, rng)
    if after.discard_pile and after.discard_pile[-1] == card:
        after = replace(after, discard_pile=after.discard_pile[:-1], exhaust_pile=after.exhaust_pile + (card,))
        after = _after_exhaust(after, (card,), rng, data)
    return after


def _draw_into_combat(combat: Combat, count: int, data: dict, rng: random.Random, *, from_hand_draw: bool = False) -> Combat:
    # NoDrawPower.ShouldDraw allows the turn-start hand draw and blocks every other draw until it
    # is removed at the side turn end.
    if not from_hand_draw and _power(combat.player_powers, "NoDrawPower"):
        return combat
    # Fiddle.ShouldDraw: every draw that is not the start-of-turn hand draw is refused for the
    # owner (AfterPreventingDraw only flashes the relic). It still adds 2 to the hand draw.
    if not from_hand_draw and RELIC_FIDDLE in combat.player_relics:
        return combat
    # A shuffle happens whenever the draw pile cannot cover the draw on its own.
    reshuffled = len(combat.draw_pile) < count and bool(combat.discard_pile)
    drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, count, rng)
    # ChainsOfBindingPower.AfterCardDrawn afflicts cards the player draws with Bound, up to its amount
    # per turn. The per-turn count is the number of afflictions that happened this turn, not the number
    # of bound cards still in hand, so playing an afflicted card does not free up the cap.
    chains = _power(combat.player_powers, "ChainsOfBindingPower")
    if chains:
        already_afflicted = combat.chains_afflicted_this_turn
        marked = []
        for value in drawn:
            if isinstance(value, Card) and already_afflicted < chains:
                value = replace(value, bound=True)
                already_afflicted += 1
            marked.append(value)
        drawn = tuple(marked)
        combat = replace(combat, chains_afflicted_this_turn=already_afflicted)
    stratagem = _power(combat.player_powers, "StratagemPower")
    if reshuffled and stratagem and draw:
        # The game lets the player choose; the model takes the highest-damage-then-block cards, which is
        # what the agent is trying to build a deck for anyway.
        best = sorted(draw, key=lambda value: (CARD_DAMAGE.get(card_name(value), 0) + CARD_BLOCK.get(card_name(value), 0) * 2) * (2 if isinstance(value, Card) and value.upgraded else 1), reverse=True)[:stratagem]
        taken = {id(value) for value in best}
        draw = tuple(value for value in draw if id(value) not in taken)
        drawn = drawn + tuple(best)
    combat = replace(combat, hand=combat.hand + drawn, draw_pile=draw, discard_pile=discard)
    if not _power(combat.player_powers, "HellraiserPower"):
        return combat
    return _autoplay_drawn_strikes(combat, drawn, data, rng)


def _autoplay_from_draw_pile(combat: Combat, count: int, data: dict, rng: random.Random) -> Combat:
    """Play `count` cards off the draw pile for free (Cascade). Cards the model cannot play from
    hand - statuses, curses, a card with no legal target - are left in hand instead of vanishing."""
    for _ in range(count):
        if combat.terminal or not combat.draw_pile:
            break
        draw = list(combat.draw_pile)
        value = draw.pop(rng.randrange(len(draw)))
        hand_index = len(combat.hand)
        combat = replace(combat, draw_pile=tuple(draw), hand=combat.hand + (value,), free_cards=combat.free_cards + (value,))
        alive = [index for index, enemy in enumerate(combat.enemies) if enemy.alive]
        if not alive:
            break
        base = f"card:{hand_index}" if isinstance(value, Card) else card_name(value)
        action = next(
            (candidate for candidate in (f"{base}@{rng.choice(alive)}", base) if candidate in legal_actions(combat)),
            None,
        )
        if action is None:
            continue
        combat = step(combat, action, data, rng)
    return combat


def _autoplay_stampede(combat: Combat, data: dict, rng: random.Random) -> Combat:
    """StampedePower.AfterAutoPostPlayPhaseEntered: once the player ends the turn and before the
    turn-end hand effects, auto-play Amount random attacks left in hand, each free of energy."""
    for _ in range(_power(combat.player_powers, "StampedePower")):
        if combat.terminal:
            break
        alive = [index for index, enemy in enumerate(combat.enemies) if enemy.alive]
        candidates = [
            index for index, value in enumerate(combat.hand)
            if card_name(value) in ATTACKS and card_name(value) != WHIRLWIND
        ]
        if not alive or not candidates:
            break
        hand_index = rng.choice(candidates)
        value = combat.hand[hand_index]
        action = f"card:{hand_index}@{rng.choice(alive)}" if isinstance(value, Card) else f"{card_name(value)}@{rng.choice(alive)}"
        candidate = replace(combat, free_cards=combat.free_cards + (value,))
        if action not in legal_actions(candidate):
            continue
        combat = step(candidate, action, data, rng)
    return combat


def initial_combat(data: dict, encounter_id: str, rng: random.Random, player_hp: int = 80) -> Combat:
    encounters = {encounter["id"]: encounter for encounter in data["encounters"]}
    encounter = encounters[encounter_id]
    formation = rng.choice(encounter["formations"])
    specs = _specs(data)
    enemies = []
    for member in formation:
        spec = specs[member["monster"]]
        values = spec["values"] | member.get("values", {})
        enemy = Enemy(
            model=spec["id"],
            hp=rng.randint(values["MinInitialHp"], values["MaxInitialHp"]),
            move=spec["initial_state"],
            values=tuple(sorted(values.items())),
            slot=member.get("slot") or "",
        )
        enemy = replace(enemy, move=_resolve_move(enemy, spec, rng))
        if enemy.model == "MONSTER.CRUSHER":
            enemy = replace(enemy, powers=(("BackAttackLeftPower", 1), ("CrabRagePower", 1)))
        elif enemy.model == "MONSTER.ROCKET":
            enemy = replace(enemy, powers=(("BackAttackRightPower", 1), ("CrabRagePower", 1)))
        elif enemy.model == "MONSTER.EXOSKELETON":
            # Granted by Exoskeleton.AfterAddedToRoom in code (not exported in the state machine JSON).
            enemy = replace(enemy, powers=enemy.powers + (("HardToKillPower", 9),))
        elif enemy.model == "MONSTER.LOUSE_PROGENITOR":
            # CurlUpPower is granted by LouseProgenitor.AfterAddedToRoom (not exported).  The
            # block is applied after the first powered attack card finishes resolving; see
            # _apply_curl_up below.
            enemy = replace(enemy, powers=enemy.powers + (("CurlUpPower", int(values.get("CurlBlock", 14))),))
        elif enemy.model in {"MONSTER.KIN_FOLLOWER", "MONSTER.TORCH_HEAD_AMALGAM"}:
            # AfterAddedToRoom unconditionally grants MinionPower (OwnerIsSecondaryEnemy), not
            # exported in the state machine JSON. CombatManager only requires primary enemies
            # dead to end the fight, so these two do not need to be killed (The Kin's Priest and
            # the Queen's own HP are the real win condition).
            enemy = replace(enemy, primary=False)
        elif enemy.model == "MONSTER.SLUMBERING_BEETLE":
            # AfterAddedToRoom grants SlumberPower(3) (not exported); SNORE_NEXT's HasPower<>
            # check already resolves generically once this is present. PlatingPower(15), a
            # per-turn block regen while asleep, is not modeled - a smaller, defensive-only gap.
            enemy = replace(enemy, powers=enemy.powers + (("SlumberPower", 3),))
        elif enemy.model in {"MONSTER.PARAFRIGHT", "MONSTER.EYE_WITH_TEETH"}:
            # AfterAddedToRoom grants IllusionPower(1) (not exported); step()'s END_TURN handling
            # already revives IllusionPower holders at max HP, but nothing ever granted the power
            # to trigger it - this fixes that (dead code path until now).
            enemy = replace(enemy, powers=enemy.powers + (("IllusionPower", 1),))
        elif enemy.model == "MONSTER.INFESTED_PRISM":
            # AfterAddedToRoom grants VitalSparkPower(VitalSparkAmount) (not exported); see
            # step() and _enemy_turn for the Tainted-card -> player TaintedPower chain it drives.
            enemy = replace(enemy, powers=enemy.powers + (("VitalSparkPower", int(values.get("VitalSparkAmount", 0))),))
        elif enemy.model == "MONSTER.ENTOMANCER":
            # AfterAddedToRoom grants PersonalHivePower(1) (not exported); see step()/_enemy_turn
            # for the Dazed-into-draw-pile chain and PHEROMONE_SPIT_MOVE's growth cap.
            enemy = replace(enemy, powers=enemy.powers + (("PersonalHivePower", 1),))
        elif enemy.model == TEST_SUBJECT:
            # AdaptablePower/EnragePower are granted by AfterAddedToRoom, not the exported
            # state machine. AdaptablePower keeps the two-phase revival alive after death.
            enemy = replace(enemy, powers=(("AdaptablePower", 1), ("EnragePower", int(values["EnrageAmount"]))))
        elif enemy.model == "MONSTER.AXEBOT":
            # Axebot.AfterAddedToRoom applies StockPower(StockAmount) when StockAmount > 0 (the
            # property is `_stockOverrideAmount ?? 2`, so an encounter spawn always carries 2).
            # Without it _mark_enemy_death would end the fight at the first kill instead of
            # spawning the second and third copies.
            enemy = replace(enemy, powers=enemy.powers + (("StockPower", int(values.get("StockAmount", 0))),))
        if "PlatingAmount" in values:
            # PlatingPower: FrogKnight.cs and SlumberingBeetle.cs apply Plating(PlatingAmount = 15) in
            # AfterAddedToRoom, which the exported state machine does not carry.  BeforeSideTurnStart
            # gives an enemy holder Block = Amount while RoundNumber == 1, i.e. the plated enemy starts
            # the fight with that much Block - the model only ever handled the player-side copy of this
            # power (Iron Unpinion, Relic grants), so every plated fight was priced as if the block
            # appeared once and never came back.  The per-turn re-grant and the decay are in step()'s
            # player-turn-start section.
            plate = int(values["PlatingAmount"])
            enemy = replace(enemy, powers=enemy.powers + (("PlatingPower", plate),), block=plate)
        enemies.append(enemy)
    hand, draw, _ = _draw(STARTING_DECK, (), 5, rng)
    powers = (("SurroundedRight", 1),) if any(enemy.model == "MONSTER.ROCKET" for enemy in enemies) else ()
    return Combat(player_hp, hand, draw, (), tuple(enemies), player_powers=powers)


def _summon(model: str, data: dict, rng: random.Random) -> Enemy:
    spec = next(spec for spec in data["monsters"] if spec["class"] == model)
    values = spec["values"]
    enemy = Enemy(
        model=spec["id"],
        hp=rng.randint(values["MinInitialHp"], values["MaxInitialHp"]),
        move=spec["initial_state"],
        values=tuple(sorted(values.items())),
        primary=False,
    )
    if enemy.model in {"MONSTER.PARAFRIGHT", "MONSTER.EYE_WITH_TEETH"}:
        enemy = replace(enemy, powers=enemy.powers + (("IllusionPower", 1),))
    return replace(enemy, move=_resolve_move(enemy, spec, rng))


def _spawn_wrigglers(data: dict, rng: random.Random) -> tuple[Enemy, ...]:
    # PhrogParasite.AfterAddedToRoom grants InfestedPower(4) to itself (not exported); its
    # AfterDeath spawns 4 Wrigglers into slots wriggler1-4, each starting at SPAWNED_MOVE
    # (stunned - no attack this turn) before falling into the slot-based INIT_MOVE branch.
    # InfestedPower.ShouldStopCombatFromEnding forces the fight to continue past the Parasite's
    # death, so unlike a MinionPower add these Wrigglers are primary - they are the real fight now.
    spec = next(spec for spec in data["monsters"] if spec["class"] == "Wriggler")
    values = spec["values"]
    return tuple(
        Enemy(model=spec["id"], hp=rng.randint(values["MinInitialHp"], values["MaxInitialHp"]), move="SPAWNED_MOVE",
              values=tuple(sorted(values.items())), slot=f"wriggler{index + 1}")
        for index in range(4)
    )


def _effective_cost(combat: Combat, card: CardValue) -> int:
    name = card_name(card)
    cost = CARD_COST.get(name, 0)
    # CuriousPower (MadScience.OnPlay) lowers the energy cost of the owner's Power cards by its
    # stack, floored at 0. The bridge reports the already-modified cost in legal_actions, so without
    # this the rollout treats a powered-up Power card as unaffordable and never plays it.
    if name in POWERS:
        curious = _power(combat.player_powers, "CuriousPower")
        if curious:
            cost = max(cost - curious, 0)
    if isinstance(card, Card) and card.enchantment == ENCHANTMENT_TEZCATARAS_EMBER:
        cost = 0
    if name == APOTHEOSIS and card_is_upgraded(combat, card):
        cost = 1
    if name == BODY_SLAM and card_is_upgraded(combat, card):
        cost = 0
    if name == BARRICADE and card_is_upgraded(combat, card):
        cost = 2
    if name == UNMOVABLE and card_is_upgraded(combat, card):
        cost = 1
    if name == DARK_EMBRACE and card_is_upgraded(combat, card):
        cost = 1
    if name == HELLRAISER and card_is_upgraded(combat, card):
        cost = 1
    if name == EXPECT_A_FIGHT and card_is_upgraded(combat, card):
        cost = 1
    if name == STOMP:
        # Stomp's BeforeCardPlayed hook lowers its current-turn cost for each completed Attack.
        cost = max(0, cost - combat.attacks_played_this_turn)
    if name == INFERNAL_BLADE and card_is_upgraded(combat, card):
        cost = 0
    if name == HAVOC and card_is_upgraded(combat, card):
        cost = 0
    if combat.enlightened_this_turn and name != WHIRLWIND:
        cost = min(cost, 1)
    if isinstance(card, Card):
        cost += card.extra_cost
    if name in ATTACKS and _power(combat.player_powers, "TangledPower"):
        # TangledPower afflicts every Attack with Entangled (EnergyVar 1) for the turn.
        cost += 1
    if name in ATTACKS and _power(combat.player_powers, "FreeAttackPower"):
        # FreeAttackPower.TryModifyEnergyCostInCombatLate zeroes Attack costs while it lasts; each
        # Attack played decrements it (see step()).
        return 0
    if (
        RELIC_BRILLIANT_SCARF in combat.player_relics
        and combat.cards_played_this_turn == BRILLIANT_SCARF_FREE_AFTER
    ):
        # TryModifyEnergyCostInCombatLate zeroes the cost outright, so it wins over every
        # adjustment above.
        return 0
    return cost


def _spend_vigor(combat: Combat) -> tuple[Combat, int]:
    """VigorPower adds its amount to every hit of the next powered attack, then removes itself."""
    vigor = _power(combat.player_powers, "VigorPower")
    if not vigor:
        return combat, 0
    return replace(combat, player_powers=_add_power(combat.player_powers, "VigorPower", -vigor)), vigor


def _choose_exhaust_from_hand(combat: Combat, rng: random.Random) -> CardValue:
    """Pick the card to exhaust for the effects that let the player choose (Burning Pact, Brand,
    upgraded True Grit use CardSelectCmd.FromHand; unupgraded True Grit really is random).

    Modelling the choice as random made Burning Pact look like a gamble that could eat the best
    card in hand, and the search passed on it in all 55 hands it appeared in during
    astra_seed2_K7M2QX9BTR. ponytail: fodder first, then random - rank real cards by value only
    if the choice among genuinely useful cards is ever shown to matter.
    """
    fodder = [
        card for card in combat.hand
        if card_name(card) in EXHAUST_FODDER or card_name(card) not in CARD_COST
    ]
    pool = fodder or list(combat.hand)
    return pool[rng.randrange(len(pool))]


def _choose_exhaustible_from_hand(combat: Combat, count: int) -> tuple[CardValue, ...]:
    """Choose up to ``count`` dead-weight cards for an optional hand exhaust effect."""
    candidates = [
        card for card in combat.hand
        if card_name(card) in EXHAUST_FODDER or card_name(card) not in CARD_COST
    ]
    return tuple(candidates[:count])


def _grant_block(
    combat: Combat,
    base: int,
    rng: random.Random,
    *,
    vambrace_double: bool = False,
    unmovable_double: bool = False,
    apply_frail: bool = True,
    powered: bool = True,
) -> Combat:
    if powered:
        # DexterityPower.ModifyBlockAdditive is its only hook (StS2 Dexterity is a Block power, not a
        # damage one), and the -1 stacks TenderPower applies show up in the observation as Dexterity
        # already, so nothing is subtracted here on top of them.
        base += _power(combat.player_powers, "DexterityPower")
    block = base * 3 // 4 if apply_frail and _power(combat.player_powers, "FrailPower") else base
    plays = 2 if combat.play_duplicated else 1
    # Each resolution is its own grant, so the relic doublings apply to every resolution, not to the
    # combined total.
    per_grant = block
    if vambrace_double:
        per_grant *= 2
    if unmovable_double:
        per_grant *= 2
    block = per_grant * plays
    enemies = list(combat.enemies)
    juggernaut = _power(combat.player_powers, "JuggernautPower")
    alive = [index for index, enemy in enumerate(enemies) if enemy.alive]
    # JuggernautPower is AfterBlockGained, so each resolution that gains block triggers its own hit.
    if block > 0 and juggernaut and alive:
        for _ in range(plays):
            target = rng.choice(alive)
            enemies[target] = _damage_enemy(enemies[target], juggernaut, powered=False)
    return replace(combat, player_block=combat.player_block + block, enemies=tuple(enemies))


def _mark_test_subject_death(enemy: Enemy) -> Enemy:
    if (
        enemy.model == TEST_SUBJECT and enemy.hp <= 0
        and _power(enemy.powers, "AdaptablePower") and enemy.respawns < 2
    ):
        return replace(enemy, move=RESPAWN_MOVE)
    return enemy


def _mark_enemy_death(enemy: Enemy) -> Enemy:
    if (
        enemy.model == "MONSTER.WATERFALL_GIANT"
        and enemy.hp <= 0
        and _power(enemy.powers, "SteamEruptionPower")
    ):
        # SteamEruptionPower.AfterDeath prevents removal and forces the giant into its
        # infinite-HP ABOUT_TO_BLOW state instead of ending combat.
        return replace(enemy, hp=999999999, move="ABOUT_TO_BLOW_MOVE")
    stock = _power(enemy.powers, "StockPower")
    if stock > 0 and enemy.hp <= 0:
        # StockPower.AfterDeath (Axebot.cs is the only applier: AfterAddedToRoom applies
        # StockPower(StockAmount), StockAmount = _stockOverrideAmount ?? 2): the dead creature is
        # re-added on the same side and slot with `StockAmount = Amount - 1`, and
        # ShouldStopCombatFromEnding keeps the fight open until the last copy dies.  Because the
        # respawn sets the override, GenerateMoveStateMachine starts the new copy at BOOT_UP_MOVE
        # instead of HAMMER_UPPERCUT_MOVE, and the copy starts with an empty power list (a fresh
        # Creature, not a revived one).  MinInitialHp 70 / MaxInitialHp 78 are drawn from at random
        # in the game; no rng reaches this function, so the model uses the top of that range.
        # Real runs: one Axebot encounter ran 12 turns and the agent died with the third copy at
        # 26/76 HP left, while the model called the fight terminal at the first kill.
        powers = (("StockPower", stock - 1),) if stock > 1 else ()
        return replace(
            enemy, hp=int(_dict(enemy.values).get("MaxInitialHp", 1)), move="BOOT_UP_MOVE",
            block=0, powers=powers, respawns=enemy.respawns + 1,
        )
    return _mark_test_subject_death(enemy)


def legal_actions(combat: Combat) -> tuple[str, ...]:
    if combat.terminal:
        return ()
    if combat.cards_played_this_turn >= NORMALITY_CARD_CAP and any(
        card_name(value) == NORMALITY for value in combat.hand
    ):
        # Normality.ShouldPlay refuses every card once three have been played this turn, for as
        # long as the curse is sitting in hand. Unplayable itself, so it never leaves that way.
        return (END_TURN,)
    sloth = _power(combat.player_powers, "SlothPower")
    if sloth and combat.cards_played_this_turn >= sloth:
        # SlothPower.ShouldPlay refuses every card once Amount of them have been played this turn.
        return (END_TURN,)
    if combat.played_this_turn and _power(combat.player_powers, "RingingPower"):
        # RingingPower.ShouldPlay (Ceremonial Beast's BEAST_CRY_MOVE): every card in the deck is
        # afflicted with Ringing, and a Ringing card can't be played once any card has already
        # been played this turn - so the whole rest of the turn collapses to End turn only.
        return (END_TURN,)
    actions = []
    seen_cards = set()
    for hand_index, card_value in enumerate(combat.hand):
        name = card_name(card_value)
        # Bound is an affliction marker, not a blanket play blocker: `ShouldPlay` gates a Bound card
        # only after one Bound card has already been played this turn (real runs played Bound cards
        # 279 times, 45 turns playing two or more in the same turn). `unplayable_this_turn` is the
        # game's own verdict for the current decision and always wins.
        if isinstance(card_value, Card) and (
            card_value.unplayable_this_turn or (card_value.bound and combat.bound_played_this_turn)
        ):
            continue
        if card_value in seen_cards:
            continue
        seen_cards.add(card_value)
        action_name = f"card:{hand_index}" if isinstance(card_value, Card) else name
        if name == CASCADE:
            if combat.energy > 0 or card_value in combat.free_cards:
                actions.append(action_name)
            continue
        if name == WHIRLWIND:
            if combat.energy > 0 or card_value in combat.free_cards:
                actions.extend(f"{action_name}@{index}" for index, enemy in enumerate(combat.enemies) if enemy.alive)
            continue
        if name not in CARD_COST or (card_value not in combat.free_cards and _effective_cost(combat, card_value) > combat.energy):
            continue
        if name == ARMAMENTS and not card_is_upgraded(combat, card_value):
            remaining = list(combat.hand[:hand_index] + combat.hand[hand_index + 1:])
            targets = [
                index for index, target in enumerate(remaining)
                if card_name(target) in CARD_COST
                and card_name(target) not in {SLIMED, FRANTIC_ESCAPE}
                and not card_is_upgraded(combat, target)
            ]
            actions.extend(f"{action_name}@{index}" for index in targets)
            if not targets:
                actions.append(action_name)
            continue
        # Mad Science targets an enemy only on the copies that rolled Attack; Skill and Power
        # copies are self-targeted like any other untargeted card.
        if name in UNTARGETED or (name == MAD_SCIENCE and not (isinstance(card_value, Card) and card_value.variant == "Attack")):
            actions.append(action_name)
        else:
            actions.extend(f"{action_name}@{index}" for index, enemy in enumerate(combat.enemies) if enemy.alive)
    for potion in dict.fromkeys(combat.player_potions):
        if potion in {POTION_BLOCK, POTION_SHIP, POTION_STRENGTH, POTION_DEXTERITY, POTION_FYSH, POTION_ENERGY, POTION_BLOOD, POTION_HEART, POTION_BRONZE, POTION_DUPLICATOR, POTION_GIGANTIFICATION, POTION_SPEED_POTION, POTION_FLEX_POTION, POTION_SWIFT_POTION, POTION_REGEN_POTION, POTION_FORTIFIER, POTION_POTION_OF_BINDING, POTION_LUCKY_TONIC, POTION_CURE_ALL, POTION_SHACKLING_POTION, POTION_CLARITY, POTION_RADIANT_TINCTURE, POTION_SNECKO_OIL, POTION_STABLE_SERUM, POTION_FOUL_POTION}:
            actions.append(f"potion:{potion}")
        elif potion in {POTION_FIRE, POTION_EXPLOSIVE, POTION_SHAPED_ROCK, POTION_WEAK_POTION, POTION_VULNERABLE_POTION}:
            actions.extend(
                f"potion:{potion}@{index}"
                for index, enemy in enumerate(combat.enemies)
                if enemy.alive
            )
    return tuple(actions) + (END_TURN,)


def _attack_base_damage(enemy: Enemy, attack_intent: dict) -> int:
    """Base damage of an attack intent, before Strength/Tainted and the multiplicative powers."""
    if enemy.model == "MONSTER.THE_FORGOTTEN":
        # TheForgotten.DreadDamage is `13 + its own DexterityPower` and the value is a lambda, so
        # `export_enemies.ps1` leaves this state with no damage at all. The monster steals 2
        # Dexterity from the player on every Miasma turn (`DebilitatingSmogDexStealAmount`), which
        # is why the game's intent display reads 15/17/19 as the stacks grow. Without this the
        # forecast is 0 for the whole fight (15 recorded decisions in the new 10-seed population;
        # no decision on the fixed panel, so the panel cannot show it), and `_enemy_turn` used to
        # raise KeyError on the missing key, pushing every TheForgotten fight to the heuristic tail.
        return 13 + _power(enemy.powers, "DexterityPower")
    return int(attack_intent.get("damage") or 0)


def _enemy_attack_damage(
    enemy: Enemy,
    data: dict,
    player_powers: tuple[tuple[str, int], ...] = (),
) -> int:
    spec = _specs(data).get(enemy.model)
    if not spec:
        return 0
    move = next((state for state in spec["states"] if state["id"] == enemy.move), None)
    if not move:
        return 0
    attack = next((intent for intent in move.get("intents", ()) if "damage" in intent), None)
    if attack is None and enemy.model == "MONSTER.THE_FORGOTTEN":
        # Its DREAD intent is exported without a damage value (the value is a lambda), so the
        # generic "no damage key" check cannot see it.
        attack = next((intent for intent in move.get("intents", ()) if "Attack" in (intent.get("type") or "")), None)
    if attack is None:
        # A state with no attack intent deals nothing this turn (SALIVATE_MOVE only applies
        # StrengthPower), so Strength and Tainted ride on the *next* attack move, not on this one:
        # `_enemy_turn` applies no damage here and the game's own intent display shows 0. Across the
        # fixed panel's 2621 recorded combat decisions this forecast was over by the Strength
        # contribution on 90 decisions, inflating `min(blocked, exposed)` in `_step_score`.
        return 0
    base = _attack_base_damage(enemy, attack)
    damage = (
        base
        + _power(enemy.powers, "StrengthPower")
        + _power(player_powers, "TaintedPower")
    )
    if (_power(player_powers, "SurroundedRight") and _power(enemy.powers, "BackAttackLeftPower")) or (
        _power(player_powers, "SurroundedLeft") and _power(enemy.powers, "BackAttackRightPower")
    ):
        damage = damage * 3 // 2
    if _power(enemy.powers, "WeakPower"):
        damage = damage * 3 // 4
    if _power(player_powers, "VulnerablePower"):
        damage = damage * 3 // 2
    if _power(player_powers, "ColossusPower") and _power(enemy.powers, "VulnerablePower"):
        damage //= 2
    repeats = int(attack.get("repeats", 1))
    if enemy.model == TEST_SUBJECT and enemy.move == "MULTI_CLAW_MOVE":
        repeats += sum(move_id == "MULTI_CLAW_MOVE" for move_id in enemy.history)
    return max(0, damage * max(1, repeats))


def _damage_enemy(enemy: Enemy, damage: int, *, powered: bool = True) -> Enemy:
    slippery = _power(enemy.powers, "SlipperyPower")
    # SoarPower halves powered attacks against its owner; potions, relics, and powers pass
    # powered=False and are unaffected.
    if powered and _power(enemy.powers, "SoarPower"):
        damage //= 2
    # Flutter (e.g. Thieving Hopper) halves powered-attack damage and wears off per unblocked hit.
    flutter = _power(enemy.powers, "FlutterPower") if powered else 0
    if flutter:
        damage //= 2
    # HardToKill caps every hit at the power amount (Exoskeleton takes at most 9 per attack).
    cap = _power(enemy.powers, "HardToKillPower")
    if cap > 0:
        damage = min(damage, cap)
    blocked = min(enemy.block, damage)
    unblocked = damage - blocked
    powers = enemy.powers
    # SlipperyPower.ModifyHpLostAfterOsty runs after Block is consumed: cap only the remaining
    # HP loss to one, and decrement the counter only when at least one damage got through.
    if slippery and unblocked > 0:
        unblocked = 1
        powers = _add_power(powers, "SlipperyPower", -1)
    # IntangiblePower.ModifyHpLostAfterOsty caps HP loss at 1 the same way, but is a standing
    # power rather than a counter - nothing consumes it, only NemesisPower's toggle removes it.
    if _power(powers, "IntangiblePower") and unblocked > 0:
        unblocked = 1
    if flutter and unblocked > 0:
        powers = _add_power(powers, "FlutterPower", -1)
    hp = enemy.hp - unblocked
    # Plow (Ceremonial Beast): PlowPower.AfterDamageReceived fires on every unblocked hit while
    # charging and is a no-op until HP drops to the Plow amount (150); the hit that crosses that
    # line strips the Strength stacked up during the charge and stuns it into the calmer
    # Crush/Stomp follow-up pattern (a one-shot trigger - the power removes itself after firing).
    plow = _power(powers, "PlowPower")
    if plow and unblocked > 0 and hp <= plow:
        powers = _add_power(powers, "StrengthPower", -_power(powers, "StrengthPower"))
        powers = _add_power(powers, "PlowPower", -plow)
        return _mark_enemy_death(replace(enemy, block=enemy.block - blocked, hp=hp, powers=powers, move="STUN_MOVE"))
    burrowed = _power(powers, "BurrowedPower")
    if burrowed and enemy.block > 0 and enemy.block - blocked == 0:
        # BurrowedPower.AfterBlockBroken (Tunneler): once a hit reduces its Burrow block to zero
        # (including overkill damage, not just an exact match), it immediately stuns into
        # DIZZY_MOVE and strips BurrowedPower; AfterRemoved's "clear remaining Block" is a no-op
        # here since this only fires when no Block remains, never a partial hit that leaves some.
        return _mark_enemy_death(replace(enemy, block=0, hp=hp, powers=_add_power(powers, "BurrowedPower", -burrowed), move="DIZZY_MOVE"))
    return _mark_enemy_death(replace(enemy, block=enemy.block - blocked, hp=hp, powers=powers))


def _trigger_inferno(combat: Combat) -> Combat:
    """InfernoPower deals its amount to every living enemy after player-side HP loss."""
    amount = _power(combat.player_powers, "InfernoPower")
    if amount <= 0:
        return combat
    return replace(
        combat,
        enemies=tuple(_damage_enemy(enemy, amount, powered=False) if enemy.alive else enemy for enemy in combat.enemies),
    )


def _vulnerable_damage(combat: Combat, enemy: Enemy, damage: int) -> int:
    """Apply Vulnerable's powered-attack multiplier, including CrueltyPower's bonus."""
    if not _power(enemy.powers, "VulnerablePower"):
        return damage
    # PaperPhrog.ModifyVulnerableMultiplier: +0.25 on top of the base 1.5 for powered attacks.
    phrog = 25 if RELIC_PAPER_PHROG in combat.player_relics else 0
    return damage * (150 + phrog + _power(combat.player_powers, "CrueltyPower")) // 100


def _apply_debuff_multipliers(combat: Combat, enemy: Enemy, damage: int) -> int:
    """Apply the dealer-side WeakPower and the target-side VulnerablePower in one rounding step.

    ModifyDamageMultiplicative hooks return decimal factors that the game multiplies together before the
    amount is rounded.  Truncating between them loses points: an upgraded Strike (9) played at Weak by a
    boss that is Vulnerable is 9 x 3/4 x 1.5 = 10.125 -> 10 in the game, while the chained model gave
    9 x 3 // 4 = 6 then 6 x 150 // 100 = 9.  That was the largest residual in the boss-fight audit -
    QUEEN fights hold Weak 97-99 for the whole fight (QUEEN CARD.STRIKE_IRONCLAD -1 x69, CARD.ANGER -1
    x65, CARD.POMMEL_STRIKE -1 x23) - and Weak applies whether or not the target is Vulnerable
    (WeakPower.ModifyDamageMultiplicative: `dealer != Owner` or `!IsPoweredAttack()` returns 1m).
    """
    weak = _power(combat.player_powers, "WeakPower")
    vulnerable = _power(enemy.powers, "VulnerablePower")
    phrog = 25 if RELIC_PAPER_PHROG in combat.player_relics else 0
    slow = _power(enemy.powers, "SlowPower")
    numerator = 3 if weak else 1
    denominator = 4 if weak else 1
    if vulnerable:
        numerator *= 150 + phrog + _power(combat.player_powers, "CrueltyPower")
        denominator *= 100
    if slow:
        # SlowPower.ModifyDamageMultiplicative: `1m + 0.1m * SlowAmount` when the target is the holder and
        # the damage is a powered attack, so it is one more factor in the same chain as Weak and
        # Vulnerable, and the game truncates that chain once at the end.  combat.cards_played_this_turn
        # already counts the card resolving right now, hence the -1 (the game raises SlowAmount in
        # AfterCardPlayed, i.e. after the card's own damage resolved).  Folding it in is what the game
        # does; measured over the traces the current build could have produced it changed nothing, because
        # those Slow fights had no Weak or Vulnerable on the same hit, so no point was being lost to the
        # old two-step rounding.
        numerator *= 10 + max(0, combat.cards_played_this_turn - 1)
        denominator *= 10
    shrink = _power(combat.player_powers, "ShrinkPower")
    if shrink:
        # ShrinkPower.ModifyDamageMultiplicative scales the damage the holder DEALS - 0.7 at the amount
        # -1 that every Shrink observation in the corpus carries - so it is one more factor in this
        # chain rather than a separate truncation step of its own.
        numerator *= 70
        denominator *= 100
    if numerator == denominator:
        return damage
    return damage * numerator // denominator


def _apply_curl_up(before: tuple[Enemy, ...], enemies: list[Enemy], card: str) -> None:
    """Resolve Louse Progenitor's one-shot block after a powered attack card."""
    if card not in ATTACKS:
        return
    for index, old in enumerate(before):
        current = enemies[index]
        amount = _power(old.powers, "CurlUpPower")
        if (
            old.model == "MONSTER.LOUSE_PROGENITOR"
            and old.alive
            and current.alive
            and current.hp < old.hp
            and amount > 0
        ):
            enemies[index] = replace(
                current,
                block=current.block + amount,
                powers=_add_power(current.powers, "CurlUpPower", -amount),
            )


def _decimillipede_teammates_dead(enemies: tuple[Enemy, ...], index: int) -> bool:
    return not any(
        other.alive for i, other in enumerate(enemies)
        if i != index and other.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT")
    )


def _enemy_turn(combat: Combat, index: int, data: dict, rng: random.Random) -> Combat:
    # Hook.ShouldClearBlock consults every ShouldClearBlock override on the creature, and
    # BurrowedPower / BlurPower answer false for their owner: a burrowed Tunneler keeps whatever block
    # the player left it with, so the generic "block is gone at your turn" clear must not run on it.
    # Observed on act3_pop2_R8V2H6N4ZB seq 207: the Tunneler went 20 block -> 2 block across a turn
    # while burrowed (1,338 observations hold BURROWED_POWER).  Its AfterRemoved side already zeroes
    # the block when the burrow breaks (see _damage_enemy).
    burrowed = _power(combat.enemies[index].powers, "BurrowedPower") or _power(combat.enemies[index].powers, "BlurPower")
    enemy = combat.enemies[index] if burrowed else replace(combat.enemies[index], block=0)
    # CreatureCmd.Stun (from ImbalancedPower.AfterDamageGiven, see the attack branch below) skips the
    # owner's next turn without advancing its state machine, so the skip is carried as a synthetic
    # power and consumed here.
    stun = _power(enemy.powers, "StunnedPower")
    if stun:
        enemies = list(combat.enemies)
        enemies[index] = replace(enemy, powers=_add_power(enemy.powers, "StunnedPower", -stun))
        return replace(combat, enemies=tuple(enemies))
    if enemy.model == TEST_SUBJECT and enemy.move == RESPAWN_MOVE:
        values = _dict(enemy.values)
        respawns = enemy.respawns + 1
        if respawns == 1:
            revived = replace(
                enemy, hp=int(values["SecondFormHp"]), move="MULTI_CLAW_MOVE", respawns=respawns,
                powers=(("AdaptablePower", 1), ("PainfulStabsPower", 1)),
            )
        else:
            revived = replace(
                enemy, hp=int(values["ThirdFormHp"]), move="PHASE3_LACERATE_MOVE", respawns=respawns,
                powers=(("NemesisPower", 1), ("IntangiblePower", 1)),
            )
        enemies = list(combat.enemies)
        enemies[index] = revived
        return replace(combat, enemies=tuple(enemies))
    if not enemy.alive:
        # Decimillipede segments don't actually leave combat on death (unless every other
        # segment is already dead too) - they were tagged DEAD_MOVE at the moment of death and
        # keep progressing through their state machine (DEAD_MOVE -> REATTACH_MOVE) to revive.
        if not (enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT") and enemy.move in ("DEAD_MOVE", "REATTACH_MOVE")):
            return combat
    spec, move_id, move = _specs(data)[enemy.model], enemy.move, _move_state(_specs(data)[enemy.model], enemy)
    values, player_hp, player_block = _dict(enemy.values), combat.player_hp, combat.player_block
    # Axebot.StockAmount is a per-instance field (`_stockOverrideAmount ?? 2`), and StockPower.AfterDeath
    # sets it to Amount-1 before re-adding the creature.  BOOT_UP_MOVE's Strength amount is
    # `BootUpStrGain * (2 - StockAmount)`, and the export carries the static StockAmount 2, so without
    # this every copy would read 0 Strength instead of 0 / 3 / 6 for the first / second / third.  The
    # live power amount is the instance's StockAmount (AfterAddedToRoom applies StockPower(StockAmount)
    # only when it is > 0), so a copy carrying no StockPower is the last one, with StockAmount 0.
    if "StockAmount" in values:
        values = {**values, "StockAmount": _power(enemy.powers, "StockPower")}
    # PaperCutsPower.AfterDamageGiven drains the player's max HP by its amount on every powered
    # attack of the owner's that gets through with UnblockedDamage > 0. Blocking the hit prevents it
    # outright, which is the whole reason the model has to know: otherwise it reads these enemies as
    # ordinary chip damage and never pays for block against them.
    max_hp_loss = 0
    sandpit = _power(enemy.powers, "SandpitPower")
    if sandpit:
        if sandpit == 1:
            return replace(combat, player_hp=0)
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", -1))
    player_powers, discard, draw, hand = combat.player_powers, combat.discard_pile, combat.draw_pile, list(combat.hand)
    drawn = ()
    enemies = list(combat.enemies)
    damage_events: list[int] = []
    ruined_helmet_used = combat.ruined_helmet_used
    forced_move: str | None = None
    if enemy.model == "MONSTER.WATERFALL_GIANT" and move_id == "ABOUT_TO_BLOW_MOVE":
        # SteamEruptionPower.AfterDeath stores the eruption amount before removing the power.
        eruption = _power(enemy.powers, "SteamEruptionPower")
        if eruption:
            values["SteamEruptionDamage"] = eruption
            enemy = replace(enemy, values=tuple(sorted(values.items())))
    attack_intent = next((intent for intent in move.get("intents", ()) if "damage" in intent), {})
    # PHEROMONE_SPIT_MOVE's real effect is an if/else in SpitMove's method body (grow
    # PersonalHivePower+Strength while PersonalHivePower < 3, else Strength alone) that the
    # static exporter can't see - it just dumps every PowerCmd.Apply call in the method
    # textually, so the generic effects loop below is skipped for this move and replaced with
    # the correct branch after move-resolution (see the ENTOMANCER special case further down).
    entomancer_spit = enemy.model == "MONSTER.ENTOMANCER" and move_id == "PHEROMONE_SPIT_MOVE"
    effects = move.get("effects", ())
    if not effects and ("damage" in attack_intent or enemy.model == "MONSTER.THE_FORGOTTEN"):
        # TheForgotten reaches this branch through the model branch because its exported intent has
        # no damage key at all (DreadDamage is a lambda), so the generic check alone would leave the
        # attack silent and `_attack_base_damage` would never run.
        # Some monsters (e.g. the Decimillipede segments) export a real SingleAttackIntent/
        # MultiAttackIntent but an entirely empty effects list - the static exporter found no
        # DamageCmd.Attack call in the move's decompiled body. Left as-is, these attacks were
        # completely silent in the simulator (zero damage every hit), making the enemy look
        # harmless and search_value stay falsely positive through an otherwise lethal fight.
        # Fall back to a synthetic DamageCmd.Attack so the intent's own damage still lands.
        effects = ({"command": "DamageCmd.Attack"},)
    for effect in (() if entomancer_spit else effects):
        command = effect["command"]
        if command == "DamageCmd.Attack":
            # TaintedPower.ModifyDamageAdditive: flat bonus to every powered attack against the
            # player while it's up (see step()'s SKILLS handling for how it's granted/cleared).
            base_damage = _attack_base_damage(enemy, attack_intent)
            if enemy.model == "MONSTER.WATERFALL_GIANT" and move_id == "EXPLODE_MOVE":
                base_damage = _amount(effect["amount"], values)
            damage = (
                base_damage
                + _power(enemy.powers, "StrengthPower")
                + _power(player_powers, "TaintedPower")
            )
            if (_power(player_powers, "SurroundedRight") and _power(enemy.powers, "BackAttackLeftPower")) or (_power(player_powers, "SurroundedLeft") and _power(enemy.powers, "BackAttackRightPower")):
                damage = damage * 3 // 2
            flame_barrier = _power(player_powers, "FlameBarrierPower")
            repeats = int(attack_intent.get("repeats", 1))
            if enemy.model == TEST_SUBJECT and move_id == "MULTI_CLAW_MOVE":
                repeats += sum(move == "MULTI_CLAW_MOVE" for move in enemy.history)
            if _power(enemy.powers, "WeakPower"):
                damage = damage * 3 // 4
            if _power(player_powers, "VulnerablePower"):
                damage = damage * 3 // 2
            if _power(player_powers, "ColossusPower") and _power(enemy.powers, "VulnerablePower"):
                damage //= 2
            buffer = _power(player_powers, "BufferPower")
            for _ in range(repeats):
                blocked = min(player_block, damage)
                player_block -= blocked
                unblocked = damage - blocked
                if unblocked > 0:
                    max_hp_loss += _power(enemy.powers, "PaperCutsPower")
                if unblocked > 0 and buffer > 0:
                    # BufferPower.ModifyHpLostAfterOstyLate zeroes the HP loss for the next damage
                    # instance to its owner and then decrements.  Block is still consumed because the
                    # hook runs after it (Late, so effects that already zeroed the damage win first,
                    # which is why a fully blocked hit leaves the buffer standing).  Observed on
                    # GEFYYKH1YK seq 150: Byrdonis' 21 against block 10 with BufferPower 1 cost no HP;
                    # the model previously read that hit as 11 damage.
                    buffer -= 1
                    unblocked = 0
                damage_events.append(unblocked)
                if _power(player_powers, "ThornsPower") and enemy.alive:
                    enemy = _damage_enemy(enemy, _power(player_powers, "ThornsPower"), powered=False)
                if flame_barrier and enemy.alive:
                    # FlameBarrierPower.AfterDamageReceived fires on every damage instance, so a 3-hit
                    # attack reflects three times.  HUNTER_KILLER seq 260 (act3_pop2_T4K8M2W7QY):
                    # PUNCTURE_MOVE 7x3 fully blocked by 22 block against FlameBarrier 4 + Thorns 3 cost
                    # the Hunter Killer 4*3 + 3*3 = 21 HP, where the once-per-attack model had 4 + 9 = 13.
                    enemy = _damage_enemy(enemy, flame_barrier, powered=False)
            if buffer_consumed := (_power(player_powers, "BufferPower") - buffer):
                player_powers = _add_power(player_powers, "BufferPower", -buffer_consumed)
            # ImbalancedPower.AfterDamageGiven: when the owner's own attack lands with
            # WasFullyBlocked the attacker is stunned for its next turn. Bowlbug Rock is the
            # exception - it flips IsOffBalance instead (see _condition). This is a custom power
            # method the static exporter cannot see, so the model carries it as a synthetic power.
            if (
                damage > 0
                and _power(enemy.powers, "ImbalancedPower")
                and enemy.model != "MONSTER.BOWLBUG_ROCK"
                and all(event == 0 for event in damage_events[len(damage_events) - repeats:])
            ):
                enemy = replace(enemy, powers=_add_power(enemy.powers, "StunnedPower", 1))
            flame_barrier = _power(player_powers, "FlameBarrierPower")
        elif command == "PowerCmd.Apply":
            try:
                amount = _amount(effect["amount"], values)
            except (ValueError, KeyError):
                if (
                    enemy.model == "MONSTER.QUEEN"
                    and move_id == "BURN_BRIGHT_FOR_ME_MOVE"
                    and effect.get("target") == "item"
                    and effect.get("model") == "StrengthPower"
                ):
                    # BurnBrightForMeMove keeps this local value out of the exported values map.
                    amount = 1
                else:
                    # Unmodeled interactions (e.g. Thieving Hopper's swipe that steals a card)
                    # carry no numeric amount; skip them, they do not change HP.
                    continue
            if effect["target"] == "base.Creature":
                enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], amount))
                if effect["model"] == "RitualPower":
                    # RitualPower.AfterApplied flags an enemy owner once, so the turn end right after
                    # the application does not add Strength.
                    enemy = replace(enemy, powers=_add_power(enemy.powers, "RitualPendingPower", 1))
            # HexMove uses the singular "target" for the player; Ovicopter uses the same
            # exporter alias for a newly summoned egg, so do not treat every "target" as player-side.
            elif effect["target"] == "targets" or (
                effect["target"] == "target" and effect["model"] == "HexPower"
            ):
                if (
                    effect["model"] == "StrengthPower" and amount > 0
                    and RELIC_RUINED_HELMET in combat.player_relics and not ruined_helmet_used
                ):
                    amount *= 2
                    ruined_helmet_used = True
                player_powers = _add_power(player_powers, effect["model"], amount)
            elif effect["target"] == "item" and enemy.model == "MONSTER.QUEEN":
                # Queen's BurnBrightForMeMove targets every living teammate except the Queen.
                for mate_index, mate in enumerate(enemies):
                    if mate_index != index and mate.alive:
                        enemies[mate_index] = replace(mate, powers=_add_power(mate.powers, effect["model"], amount))
            elif "TeammatesOf" in effect["target"]:
                # GetTeammatesOf = GetCreaturesOnSide(side): every creature on the same side,
                # including the caster (e.g. Obscura's SAIL buffs itself as well as its minions).
                for mate_index, mate in enumerate(enemies):
                    if mate_index == index:
                        enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], amount))
                    elif mate.alive:
                        enemies[mate_index] = replace(mate, powers=_add_power(mate.powers, effect["model"], amount))
        elif command == "PowerCmd.Remove" and (
            effect.get("target") == "base.Creature" or effect.get("arguments") == ["base.Creature"]
        ):
            enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], -_power(enemy.powers, effect["model"])))
        elif command == "CreatureCmd.GainBlock":
            amount = _amount(effect["amount"], values)
            if effect.get("target") == "item":
                # Guardbot's GuardMove resolves item to every alive Fabricator in the room.
                for mate_index, mate in enumerate(enemies):
                    if mate.alive and mate.model == "MONSTER.FABRICATOR":
                        enemies[mate_index] = replace(mate, block=mate.block + amount)
            else:
                enemy = replace(enemy, block=enemy.block + amount)
        elif command == "CreatureCmd.Heal":
            enemy = replace(enemy, hp=enemy.hp + _amount(effect["arguments"][1], values))
        elif command == "CreatureCmd.Escape":
            enemy = replace(enemy, escaped=True)
        elif command.startswith("CardPileCmd."):
            card = effect.get("model", "Status")
            try:
                count = _amount(effect["arguments"][-2], values) if len(effect["arguments"]) > 2 else 1
            except (ValueError, KeyError):
                # Generated-card pile effects (e.g. Insatiable's Liquify, Soul Fysh's Beckon) carry
                # no numeric amount; skip them - their combat impact is modeled separately.
                continue
            if len(effect["arguments"]) > 1 and effect["arguments"][1] == "PileType.Hand":
                # Added straight to hand mid-enemy-turn (Myte's Toxic, Mecha Knight's Burn), not
                # to a pile the player draws from later - see HAND_INJECTED_STATUS.
                hand += [card] * count
            else:
                discard += (card,) * count
        elif command == "CreatureCmd.Add":
            count = 3 if enemy.model == "MONSTER.OVICOPTER" and move_id == "LAY_EGGS_MOVE" else 1
            enemies.extend(_summon(effect["model"], data, rng) for _ in range(count))
        elif command == "CreatureCmd.Kill" and effect.get("arguments") == ["base.Creature"]:
            # CreatureCmd.Kill zeroes current HP, then the monster move finishes.  Keep the
            # dead snapshot until the normal terminal/removal check after the move, matching
            # MonsterModel.PerformMove's post-move cleanup.
            enemy = _mark_enemy_death(replace(enemy, hp=0))
            if enemy.model == "MONSTER.WATERFALL_GIANT" and enemy.move == "ABOUT_TO_BLOW_MOVE":
                forced_move = "ABOUT_TO_BLOW_MOVE"
        elif command in {"CreatureCmd.Kill", "CreatureCmd.SetMaxAndCurrentHp"}:
            raise NotImplementedError(f"effect: {spec['class']}.{move['id']} {command}")
    if (
        enemy.model == "MONSTER.WATERFALL_GIANT"
        and move_id != "ABOUT_TO_BLOW_MOVE"
        and enemy.move == "ABOUT_TO_BLOW_MOVE"
    ):
        forced_move = "ABOUT_TO_BLOW_MOVE"
    if enemy.model == "MONSTER.FABRICATOR" and move_id in {"FABRICATE_MOVE", "FABRICATING_STRIKE_MOVE"}:
        # The exporter leaves both moves' effects empty because Fabricator spawns through its own
        # SpawnDefensiveBot/SpawnAggroBot helpers rather than a CreatureCmd.Add effect.  Fabricate
        # builds one of each kind, Fabricating Strike only an aggro bot; every bot gets MinionPower.
        # ponytail: SpawnBot also excludes whichever model it spawned last, which needs per-monster
        # state - draw uniformly instead and add the exclusion if bot mix ever matters.
        pools = [("MONSTER.GUARDBOT", "MONSTER.NOISEBOT")] if move_id == "FABRICATE_MOVE" else []
        pools.append(("MONSTER.ZAPBOT", "MONSTER.STABBOT"))
        for pool in pools:
            spawned = _summon(_specs(data)[rng.choice(pool)]["class"], data, rng)
            enemies.append(replace(spawned, powers=spawned.powers + (("MinionPower", 1),)))
    if enemy.model == "MONSTER.BOWLBUG_ROCK":
        if move_id == "HEADBUTT_MOVE" and damage_events and not sum(damage_events):
            # ImbalancedPower.AfterDamageGiven: a fully-blocked Headbutt sets IsOffBalance, which
            # POST_HEADBUTT (data/enemies_hive.json) reads via _condition to route into DIZZY_MOVE
            # next instead of repeating Headbutt.
            enemy = replace(enemy, powers=_add_power(enemy.powers, "OffBalancePower", 1))
        elif move_id == "DIZZY_MOVE":
            # DizzyMove clears IsOffBalance back to false once it executes.
            enemy = replace(enemy, powers=_add_power(enemy.powers, "OffBalancePower", -_power(enemy.powers, "OffBalancePower")))
    regen = _power(enemy.powers, "RegenPower")
    if regen and enemy.alive:
        # RegenPower.AfterSideTurnEnd heals the owner by its amount, then decrements. Enemies have
        # no max HP in this model, so cap the heal at whatever the export calls their initial HP.
        ceiling = _dict(enemy.values).get("MaxInitialHp")
        healed = enemy.hp + regen if ceiling is None else min(int(ceiling), enemy.hp + regen)
        enemy = replace(enemy, hp=healed, powers=_add_power(enemy.powers, "RegenPower", -1))
    shackled = _power(enemy.powers, "ShacklingPotionPower")
    if shackled:
        # TemporaryStrengthPower.AfterSideTurnEnd: the -7 Strength ShacklingPotion granted is restored
        # when the affected creature's own side turn ends, so the potion blunts exactly one enemy turn.
        enemy = replace(
            enemy,
            powers=_add_power(_add_power(enemy.powers, "ShacklingPotionPower", -shackled), "StrengthPower", shackled),
        )
    if _power(enemy.powers, "NemesisPower"):
        # NemesisPower.AfterSideTurnEnd flips a private bool each of the owner's turn ends,
        # alternately applying and removing IntangiblePower - so Test Subject's third form is
        # untouchable (every hit capped at 1) on every other player turn.
        intangible = _power(enemy.powers, "IntangiblePower")
        enemy = replace(enemy, powers=_add_power(enemy.powers, "IntangiblePower", -1 if intangible else 1))
    if move_id == "SNORE_MOVE":
        # SlumberPower.AfterSideTurnEnd decrements once per enemy turn and forces an immediate
        # wake-up (not a "next move" transition) once it reaches 0, so this must land before the
        # next-move resolution below (SlumberingBeetle also decrements it on taking unblocked
        # damage, not modeled - a safe, conservative wake-up estimate).
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SlumberPower", -1))
    if enemy.model == "MONSTER.TOUGH_EGG" and move_id == "HATCH_MOVE":
        values = _dict(enemy.values)
        enemy = replace(enemy, hp=rng.randint(values["HatchlingMinHp"], values["HatchlingMaxHp"]))
    # The stun id is a runtime synthetic state rather than a move the monster chose.  Logging it in
    # the history would make a later stun resume into "STUNNED" instead of the last real move.
    enemy = replace(enemy, history=enemy.history + (() if enemy.move == STUNNED_MOVE else (enemy.move,)))
    enemy = replace(enemy, move=forced_move or _resolve_move(enemy, spec, rng, move.get("next"), tuple(enemies)))
    if enemy.model == "MONSTER.THE_INSATIABLE" and move_id == "LIQUIFY_GROUND_MOVE":
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", 4))
        draw += (FRANTIC_ESCAPE,) * 3
        discard += (FRANTIC_ESCAPE,) * 3
    if enemy.model == "MONSTER.KNOWLEDGE_DEMON" and move_id == "CURSE_OF_KNOWLEDGE_MOVE":
        # Private turn counter (CurseOfKnowledge.cs), not in the exported state machine; read
        # back by _condition's CurseOfKnowledgeBranch handling above.
        enemy = replace(enemy, powers=_add_power(enemy.powers, "CurseOfKnowledgeCounter", 1))
    if entomancer_spit:
        # SpitMove: while PersonalHivePower < 3, grow it (+1) and Strength (+1); once capped,
        # +2 Strength alone. The exported effects list all three PowerCmd.Apply calls
        # unconditionally, which would triple Strength growth (+3/cast forever).
        if _power(enemy.powers, "PersonalHivePower") < 3:
            enemy = replace(enemy, powers=_add_power(_add_power(enemy.powers, "PersonalHivePower", 1), "StrengthPower", 1))
        else:
            enemy = replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", 2))
    if enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT") and move_id == "REATTACH_MOVE":
        # ReattachPower.DoReattach heals base.Amount (25) back onto the segment on its own next
        # turn after dying; not in the exported effects since it's a custom power method, not a
        # generic Cmd. DEAD_MOVE and REATTACH_MOVE are both no-op turns, so the segment sits out
        # two of its own turns before resuming attacks.
        enemy = replace(enemy, hp=enemy.hp + 25)
    # RitualPower.AfterSideTurnEnd (cultists) adds Strength equal to its stack at the end of the
    # owner's turn, but the turn on which it was applied is skipped: AfterApplied sets a one-shot
    # flag when the owner is an enemy. The flag is not exported or observed, so the model carries it
    # as RitualPendingPower when an enemy applies the power.
    ritual = _power(enemy.powers, "RitualPower")
    if ritual and enemy.alive:
        if _power(enemy.powers, "RitualPendingPower"):
            enemy = replace(enemy, powers=_add_power(enemy.powers, "RitualPendingPower", -1))
        else:
            enemy = replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", ritual))
    # HighVoltagePower.AfterSideTurnEnd (Zapbot) adds Strength every enemy turn end with no skip.
    # Zapbot applies it at combat start, so it only reaches the model through the observation.
    high_voltage = _power(enemy.powers, "HighVoltagePower")
    if high_voltage and enemy.alive:
        enemy = replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", high_voltage))
    if enemy.model == "MONSTER.BYRDONIS":
        # TerritorialPower.AfterSideTurnEnd (not exported): +1 Strength unconditionally every
        # turn, regardless of which move was performed.
        enemy = replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", 1))
    mangle = _power(enemy.powers, "ManglePower")
    if mangle:
        enemy = replace(
            enemy,
            powers=_add_power(
                _add_power(enemy.powers, "ManglePower", -mangle),
                "StrengthPower",
                mangle,
            ),
        )
    if enemy.model == "MONSTER.THIEVING_HOPPER" and move_id == "THIEVERY_MOVE":
        # ThievingHopper.ThieveryMove: the steal lives in the C# move body, not in the exported state
        # machine (the export only lists PowerCmd.Apply of the "swipe" marker and the 17-damage attack).
        # The move takes one card out of the player's Draw and Discard piles with
        # CardPileCmd.RemoveFromCombat before the attack, so the card is unplayable for the rest of the
        # fight.  Game-side priority is Uncommon, then Common/Rare/Event, then Basic/Quest, then
        # Ancient/Imbued, with a random card out of the first non-empty group; the model has no
        # per-card rarity, so the priority is approximated as "Strike/Defend last".  Real runs back
        # that ordering: of 268 recorded steals, 258 took a non-Basic card and 10 took a Strike.
        pool = [value for value in draw + discard if card_name(value) not in NON_DECK_CARDS]
        candidates = [value for value in pool if card_name(value) not in {STRIKE, DEFEND}] or pool
        if candidates:
            stolen = rng.choice(candidates)
            draw_index = next((position for position, value in enumerate(draw) if value == stolen), None)
            if draw_index is not None:
                draw = draw[:draw_index] + draw[draw_index + 1:]
            else:
                discard_index = next(position for position, value in enumerate(discard) if value == stolen)
                discard = discard[:discard_index] + discard[discard_index + 1:]
    if enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT"):
        # DecimillipedeSegment.BulkMove and ConstrictMove are exported as intents only (their "effects"
        # list is empty, so the synthetic DamageCmd fallback above carries the attack damage).  The C#
        # bodies also do two things the export cannot show: BulkMove applies StrengthPower(BulkStrength
        # = 2) to the segment itself, and ConstrictMove applies WeakPower(1) to the players.  Real runs
        # show segment Strength 0 at turn 1, 2 from turn 2, 4 from turn 5, and the player carrying Weak
        # on 285 turn-2 records in these fights.
        if move_id == "BULK_MOVE":
            enemy = replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", 2))
        elif move_id == "CONSTRICT_MOVE":
            player_powers = _add_power(player_powers, "WeakPower", 1)
    enemies[index] = enemy
    # Resolve HP-loss modifiers once all attacks in this enemy move have respected the current
    # block.  Tungsten Rod is per damage event; Beating Remnant caps the turn-wide total.
    damage_received = combat.damage_received_this_turn
    if damage_events:
        if RELIC_TUNGSTEN_ROD in combat.player_relics:
            damage_events = [max(0, amount - 1) for amount in damage_events]
        if RELIC_BEATING_REMNANT in combat.player_relics:
            remaining = max(0, 20 - damage_received)
            capped = []
            for amount in damage_events:
                taken = min(amount, remaining)
                capped.append(taken)
                remaining -= taken
            damage_events = capped
        actual_damage = sum(damage_events)
        if _power(enemy.powers, "PainfulStabsPower"):
            discard += (WOUND,) * sum(amount > 0 for amount in damage_events)
        player_hp = combat.player_hp - actual_damage
        if player_hp <= 0 and RELIC_LIZARD_TAIL in combat.player_relics and not combat.lizard_tail_used:
            player_hp = max(1, combat.player_max_hp // 2)
            lizard_tail_used = True
        else:
            lizard_tail_used = combat.lizard_tail_used
        damage_received += actual_damage
    else:
        actual_damage = 0
        lizard_tail_used = combat.lizard_tail_used
    # DemonTongue/CentennialPuzzle/SelfFormingClay all observe the unblocked result, not the
    # nominal intent damage.
    damaged_this_turn, centennial_puzzle_used = combat.damaged_this_turn, combat.centennial_puzzle_used
    relics = combat.player_relics
    if actual_damage > 0:
        if RELIC_DEMON_TONGUE in relics and not damaged_this_turn:
            player_hp += actual_damage
            damaged_this_turn = True
        if RELIC_CENTENNIAL_PUZZLE in relics and not centennial_puzzle_used:
            drawn, draw, discard = _draw(draw, discard, 3, rng)
            hand = hand + list(drawn)
            centennial_puzzle_used = True
        if RELIC_SELF_FORMING_CLAY in relics:
            player_powers = _add_power(player_powers, "SelfFormingClayPower", 3)
    # CreatureCmd.LoseMaxHp also pulls current HP down with the ceiling it just lowered.
    surviving_max_hp = max(1, combat.player_max_hp - max_hp_loss) if max_hp_loss else combat.player_max_hp
    if max_hp_loss:
        player_hp = min(player_hp, surviving_max_hp)
    player_hp, player_potions = _survive_with_fairy_in_a_bottle(combat, player_hp, surviving_max_hp)
    combat_after_damage = replace(
        combat, player_hp=player_hp, player_powers=player_powers, player_potions=player_potions,
        player_max_hp=surviving_max_hp,
        damage_received_this_turn=damage_received, lizard_tail_used=lizard_tail_used,
        # TearAsunder counts DamageReceivedEntry rows with UnblockedDamage > 0 for the whole
        # combat, so each individual repeat hit that got through counts once.
        unblocked_hits=combat.unblocked_hits + sum(amount > 0 for amount in damage_events),
    )
    combat_after_damage = _sync_red_skull(combat_after_damage)
    result = replace(
        combat_after_damage, player_block=player_block, player_powers=combat_after_damage.player_powers,
        discard_pile=discard, draw_pile=draw, hand=tuple(hand), enemies=tuple(enemies),
        damaged_this_turn=damaged_this_turn, centennial_puzzle_used=centennial_puzzle_used,
        ruined_helmet_used=ruined_helmet_used,
    )
    return _autoplay_drawn_strikes(result, drawn, data, rng)


def _enemy_vulnerable_total(combat: Combat) -> int:
    return sum(_power(enemy.powers, "VulnerablePower") for enemy in combat.enemies if enemy.alive)


def step(combat: Combat, action: str, data: dict, rng: random.Random) -> Combat:
    """Resolve one player action.

    ViciousPower.AfterPowerAmountChanged draws its amount whenever the owner applies Vulnerable,
    and the player can do that from Bash, Squash, Break, Taunt, Tremble, Thunderclap, Molten Fist,
    Dominate and potions. Detecting the increase once here beats threading a draw through every
    one of those call sites and missing one.
    """
    vicious = _power(combat.player_powers, "ViciousPower")
    before = _enemy_vulnerable_total(combat)
    alive_before = sum(1 for enemy in combat.enemies if enemy.alive)
    after = _step(combat, action, data, rng)
    if after.pending_combo_powers:
        # Kunai / Shuriken grant their power in AfterCardPlayed: the play that reached the 3rd attack
        # does not benefit from its own bonus, but the resulting state does carry the power.
        for power_name, power_amount in after.pending_combo_powers:
            after = replace(after, player_powers=_add_power(after.player_powers, power_name, power_amount))
        after = replace(after, pending_combo_powers=())
    if vicious and action != END_TURN and _enemy_vulnerable_total(after) > before and not after.terminal:
        after = _draw_into_combat(after, vicious, data, rng)
    if action == END_TURN or after.terminal:
        return after
    relics = after.player_relics
    # GremlinHorn.AfterDeath: 1 energy and 1 card for every enemy that dies.
    kills = alive_before - sum(1 for enemy in after.enemies if enemy.alive)
    if kills > 0 and RELIC_GREMLIN_HORN in relics:
        after = _draw_into_combat(replace(after, energy=after.energy + kills), kills, data, rng)
    # UnceasingTop.AfterHandEmptied: draws a card whenever the hand runs out during the play
    # phase. The relic deliberately does not fire around the hand draw or the hand flush, which
    # is why this sits on the player's own actions only.
    if RELIC_UNCEASING_TOP in relics and not after.hand and not after.terminal:
        after = _draw_into_combat(after, 1, data, rng)
    return after


def _step(combat: Combat, action: str, data: dict, rng: random.Random) -> Combat:
    if action not in legal_actions(combat):
        raise ValueError(f"illegal action: {action}")
    combat = _sync_belt_buckle(_sync_red_skull(combat))
    if action.startswith("potion:"):
        potion, _, target = action.partition(":")[2].partition("@")
        potions = list(combat.player_potions)
        potions.remove(potion)
        combat = _sync_belt_buckle(replace(combat, player_potions=tuple(potions)))
        if potion == POTION_BLOCK:
            return _grant_block(combat, 12, rng, apply_frail=False, powered=False)
        if potion == POTION_SHIP:
            return replace(
                _grant_block(combat, 10, rng, apply_frail=False, powered=False),
                player_powers=_add_power(combat.player_powers, "BlockNextTurnPower", 10),
            )
        if potion == POTION_STRENGTH:
            return replace(combat, player_powers=_add_power(combat.player_powers, "StrengthPower", 2))
        if potion == POTION_DEXTERITY:
            return replace(combat, player_powers=_add_power(combat.player_powers, "DexterityPower", 2))
        if potion == POTION_FYSH:
            return replace(
                combat,
                player_powers=_add_power(_add_power(combat.player_powers, "StrengthPower", 1), "DexterityPower", 1),
            )
        if potion == POTION_ENERGY:
            if _power(combat.player_powers, "NoEnergyGainPower"):
                return combat
            return replace(combat, energy=combat.energy + 2)
        if potion == POTION_BLOOD:
            return replace(combat, player_hp=min(combat.player_max_hp, combat.player_hp + combat.player_max_hp * 20 // 100))
        if potion == POTION_HEART:
            return replace(combat, player_powers=_add_power(combat.player_powers, "PlatingPower", 7))
        if potion == POTION_BRONZE:
            return replace(combat, player_powers=_add_power(combat.player_powers, "ThornsPower", 3))
        if potion == POTION_DUPLICATOR:
            return replace(combat, player_powers=_add_power(combat.player_powers, "DuplicationPower", 1))
        if potion == POTION_GIGANTIFICATION:
            return replace(combat, player_powers=_add_power(combat.player_powers, "GigantificationPower", 1))
        if potion == POTION_SPEED_POTION:
            # SpeedPotion.OnUse applies SpeedPotionPower 5, and SpeedPotionPower extends
            # TemporaryDexterityPower: the observations carry a matching DexterityPower next to the
            # marker, and the END_TURN handling here removes both when the player's turn ends.
            return replace(
                combat,
                player_powers=_add_power(_add_power(combat.player_powers, "SpeedPotionPower", 5), "DexterityPower", 5),
            )
        if potion == POTION_FLEX_POTION:
            return replace(
                combat,
                player_powers=_add_power(_add_power(combat.player_powers, "FlexPotionPower", 5), "StrengthPower", 5),
            )
        if potion == POTION_SWIFT_POTION:
            return _draw_into_combat(combat, 3, data, rng)
        if potion == POTION_REGEN_POTION:
            return replace(combat, player_powers=_add_power(combat.player_powers, "RegenPower", 5))
        if potion == POTION_FORTIFIER:
            # Fortifier.OnUse: CreatureCmd.GainBlock(target, target.Block * 2, Unpowered), i.e. it
            # doubles the Block already held and does nothing on an empty Block.
            return replace(combat, player_block=combat.player_block * 2)
        if potion == POTION_POTION_OF_BINDING:
            # PotionOfBinding.OnUse: PowerCmd.Apply<WeakPower>(1) and Apply<VulnerablePower>(1) over
            # combatState.HittableEnemies (TargetType.AllEnemies; all 124 recorded plays carry
            # target_id None).
            enemies = [
                replace(
                    enemy,
                    powers=_add_power(_add_power(enemy.powers, "WeakPower", 1), "VulnerablePower", 1),
                )
                if enemy.alive
                else enemy
                for enemy in combat.enemies
            ]
            return replace(combat, enemies=tuple(enemies))
        if potion == POTION_SHACKLING_POTION:
            # ShacklingPotionPower extends TemporaryStrengthPower with IsPositive = false: the
            # observations right after a play read SHACKLING_POTION_POWER 7 next to STRENGTH_POWER -7 on
            # every enemy (61 of 61 enemy observations), and the exported intent damage drops to match
            # (3 -> 0 for an Entomancer bees attack).  TemporaryStrengthPower.AfterSideTurnEnd restores
            # it once that creature's own turn ends, which _enemy_turn does below.
            enemies = [
                replace(
                    enemy,
                    powers=_add_power(_add_power(enemy.powers, "ShacklingPotionPower", 7), "StrengthPower", -7),
                )
                if enemy.alive
                else enemy
                for enemy in combat.enemies
            ]
            return replace(combat, enemies=tuple(enemies))
        if potion == POTION_LUCKY_TONIC:
            return replace(combat, player_powers=_add_power(combat.player_powers, "BufferPower", 1))
        if potion == POTION_SNECKO_OIL:
            # SneckoOil.OnUse: CardPileCmd.Draw(CardsVar 7).  The game also randomizes the energy cost
            # of the cards it draws, which the model does not represent, so this is the draw half.
            return _draw_into_combat(combat, 7, data, rng)
        if potion == POTION_STABLE_SERUM:
            # StableSerum.OnUse: Apply<RetainHandPower>(RepeatVar 2) - the hand carries into next turn.
            return replace(combat, player_powers=_add_power(combat.player_powers, "RetainHandPower", 2))
        if potion == POTION_FOUL_POTION:
            # FoulPotion is TargetType.AllEnemies in combat and its DamageVar(12, Unpowered) is dealt to
            # every non-pet creature in the combat - Owner included (the loop walks
            # CombatState.Creatures), so the player takes it too.
            combat = _apply_player_damage(combat, 12, trigger_inferno=True)
            enemies = [_damage_enemy(enemy, 12) if enemy.alive else enemy for enemy in combat.enemies]
            return replace(combat, enemies=tuple(enemies))
        if potion == POTION_CURE_ALL:
            return _draw_into_combat(replace(combat, energy=combat.energy + 1), 2, data, rng)
        if potion == POTION_CLARITY:
            # Clarity.OnUse: draw 1, then Apply<ClarityPower>(3) - ClarityPower.ModifyHandDraw adds a
            # card to each of the next three turn-start draws, which the new-turn handling already reads.
            return _draw_into_combat(
                replace(combat, player_powers=_add_power(combat.player_powers, "ClarityPower", 3)), 1, data, rng
            )
        if potion == POTION_RADIANT_TINCTURE:
            return replace(
                combat,
                energy=combat.energy + 1,
                player_powers=_add_power(combat.player_powers, "RadiancePower", 3),
            )
        if potion in {POTION_WEAK_POTION, POTION_VULNERABLE_POTION}:
            enemies = list(combat.enemies)
            power = "WeakPower" if potion == POTION_WEAK_POTION else "VulnerablePower"
            enemies[int(target)] = replace(
                enemies[int(target)], powers=_add_power(enemies[int(target)].powers, power, 3)
            )
            return replace(combat, enemies=tuple(enemies))
        enemies = list(combat.enemies)
        if potion == POTION_EXPLOSIVE:
            enemies = [_damage_enemy(enemy, 10, powered=False) if enemy.alive else enemy for enemy in enemies]
        else:
            enemies[int(target)] = _damage_enemy(enemies[int(target)], 20 if potion == POTION_FIRE else 15, powered=False)
        return replace(combat, enemies=tuple(enemies))
    if action == END_TURN:
        combat = _autoplay_stampede(combat, data, rng)
        if combat.terminal:
            return combat
        speed_dexterity = _power(combat.player_powers, "SpeedPotionPower")
        # RingingPower.AfterSideTurnEnd (Ceremonial Beast): removes itself once the player's own
        # turn ends, clearing the Ringing one-card-per-turn restriction for next turn.
        combat = replace(
            combat,
            player_powers=_add_power(
                _add_power(
                    _add_power(combat.player_powers, "RingingPower", -_power(combat.player_powers, "RingingPower")),
                    "RagePower", -_power(combat.player_powers, "RagePower"),
                ),
                "NoEnergyGainPower", -_power(combat.player_powers, "NoEnergyGainPower"),
            ),
            played_this_turn=False,
        )
        if speed_dexterity:
            combat = replace(
                combat,
                player_powers=_add_power(
                    _add_power(combat.player_powers, "SpeedPotionPower", -speed_dexterity),
                    "DexterityPower", -speed_dexterity,
                ),
            )
        # FlexPotionPower (TemporaryStrengthPower).AfterSideTurnEnd: removes itself and the
        # Strength it granted once the player's own turn ends.
        flex_strength = _power(combat.player_powers, "FlexPotionPower")
        if flex_strength:
            combat = replace(
                combat,
                player_powers=_add_power(
                    _add_power(combat.player_powers, "FlexPotionPower", -flex_strength),
                    "StrengthPower", -flex_strength,
                ),
            )
        setup_strike = _power(combat.player_powers, "SetupStrikePower")
        if setup_strike:
            combat = replace(
                combat,
                player_powers=_add_power(
                    _add_power(combat.player_powers, "SetupStrikePower", -setup_strike),
                    "StrengthPower", -setup_strike,
                ),
            )
        # HasTurnEndInHandEffect (Toxic, Burn): flat Unpowered damage for each copy still in
        # hand when the player's turn ends. RetainHandPower skips the normal hand flush, so the
        # retained cards stay in hand while the turn-end effects still resolve first.
        # Regret.OnTurnEndInHand: unblockable damage equal to the hand size captured at
        # BeforeSideTurnEnd, once per copy (each copy counts the whole hand, itself included).
        regret_damage = len(combat.hand) * sum(1 for card in combat.hand if card_name(card) == REGRET)
        # Doubt/Shame apply Weak/Frail with SkipNextDurationTick, so the stack survives the tick at
        # the end of the enemy side and costs the player their next turn.
        doubt_weak = sum(1 for card in combat.hand if card_name(card) == DOUBT)
        shame_frail = sum(1 for card in combat.hand if card_name(card) == SHAME)
        hand_damage = sum(HAND_INJECTED_STATUS.get(card_name(card), 0) for card in combat.hand)
        unblockable_hand_damage = sum(HAND_END_UNBLOCKABLE.get(card_name(card), 0) for card in combat.hand) + regret_damage
        relics = combat.player_relics
        # CloakClasp.BeforeSideTurnEnd: block equal to 1 per card still in hand, granted before
        # the hand is cleared to discard (and before the enemy turn below, so it can help block).
        cloak_clasp_block = len(combat.hand) if RELIC_CLOAK_CLASP in relics else 0
        # ScreamingFlagon.BeforeSideTurnEnd: 20 damage to every enemy if the hand ended up empty.
        screaming_flagon = RELIC_SCREAMING_FLAGON in relics and not combat.hand
        retain_hand = _power(combat.player_powers, "RetainHandPower") > 0
        # Both markers are per-turn. `bound` is cleared by ChainsOfBindingPower.BeforeSideTurnEnd;
        # `unplayable_this_turn` is the game's verdict for the turn that was observed, so it must not
        # leak into the next turn of the rollout (it used to ride on the same field as bound and got
        # cleared by accident).
        flushed_hand = tuple(
            replace(card, bound=False, unplayable_this_turn=False)
            if isinstance(card, Card) and (card.bound or card.unplayable_this_turn)
            else card
            for card in combat.hand
        )
        retained_hand = tuple(
            replace(card, unplayable_this_turn=False)
            if isinstance(card, Card) and card.unplayable_this_turn
            else card
            for card in combat.hand
        )
        combat = replace(
            combat, player_block=combat.player_block + cloak_clasp_block,
            discard_pile=combat.discard_pile + (() if retain_hand else flushed_hand),
            hand=retained_hand if retain_hand else (),
            paels_tears_pending=RELIC_PAELS_TEARS in relics and combat.energy > 0,
        )
        plating = _power(combat.player_powers, "PlatingPower")
        if plating:
            combat = replace(combat, player_block=combat.player_block + plating)
        # Toxic/Burn/Infection/Decay are not Unblockable, and the player's block is still up when
        # the turn-end hook runs (it clears at the start of the next player turn), so block absorbs
        # them first - at the cost of not being there for the enemy turn below.
        absorbed = min(combat.player_block, hand_damage)
        combat = replace(combat, player_block=combat.player_block - absorbed)
        combat = _apply_player_damage(combat, hand_damage - absorbed + unblockable_hand_damage, trigger_inferno=True)
        # Knowledge Demon's DisintegrationPower deals flat damage at the end of the player's
        # turn; the live bridge exposes it as a player power, so include it in rollouts.
        combat = _apply_player_damage(combat, _power(combat.player_powers, "DisintegrationPower"), trigger_inferno=True)
        if screaming_flagon:
            combat = replace(combat, enemies=tuple(_damage_enemy(enemy, 20, powered=False) if enemy.alive else enemy for enemy in combat.enemies))
        # ConstrictPower.AfterSideTurnEnd (Slithering Strangler): CreatureCmd.Damage for the
        # current stack amount every time the player's own turn ends - a block-respecting DOT
        # that stacks +3 every CONSTRICT cast and never decays on its own. Previously stored via
        # the generic PowerCmd.Apply handling in _enemy_turn with no damage ever applied, which
        # silently turned an escalating per-turn bleed into a free, permanently inert power.
        constrict = _power(combat.player_powers, "ConstrictPower")
        if constrict:
            blocked = min(combat.player_block, constrict)
            combat = replace(combat, player_block=combat.player_block - blocked)
            combat = _apply_player_damage(combat, constrict - blocked, trigger_inferno=True)
        # BeforeSideTurnEnd hooks.  Orichalcum checks the pre-hook block value, while Ripple
        # Basin independently rewards a turn with no attacks; both can trigger together.
        end_block = combat.player_block
        if RELIC_ORICHALCUM in relics and end_block == 0:
            end_block += 6
        if RELIC_RIPPLE_BASIN in relics and combat.attacks_played_this_turn == 0:
            end_block += 4
        combat = replace(combat, player_block=end_block)
        if RELIC_PARRYING_SHIELD in relics and end_block >= 10:
            alive = [i for i, enemy in enumerate(combat.enemies) if enemy.alive]
            if alive:
                hit = rng.choice(alive)
                enemies = list(combat.enemies)
                enemies[hit] = _damage_enemy(enemies[hit], 6, powered=False)
                combat = replace(combat, enemies=tuple(enemies))
        # WeakPower / VulnerablePower / FrailPower.AfterSideTurnEnd all tick down at the end of the
        # enemy side's turn, for owners on either side (confirmed in the decompile: each gates on
        # side == CombatSide.Enemy).  A stack applied *during* that enemy turn is exempt from the same
        # turn's tick - real runs show an Axebot Uppercut leaving the player at Weak 2 / Frail 2 during
        # player turn 2 and 1 / 1 during turn 3 - so the set of debuffs that were already running when
        # the enemy side starts is recorded here and ticked after the phase.  Anything the enemy phase
        # adds survives into the player's next turn, and a debuff the player applied during their own
        # turn still counts for the enemy's attacks.
        player_debuffs = tuple(name for name in DEBUFF_POWERS if _power(combat.player_powers, name))
        enemy_debuffs = [tuple(name for name in DEBUFF_POWERS if _power(enemy.powers, name)) for enemy in combat.enemies]
        for index in range(len(combat.enemies)):
            combat = _enemy_turn(combat, index, data, rng)
        enemies = list(combat.enemies)
        for index, enemy in enumerate(enemies):
            # IllusionPower minions (e.g. Parafright) revive at full health after the enemy phase.
            # IllusionPower.AfterDeath (C#) force-sets the creature's move to a synthetic
            # "REVIVE_MOVE" state built at runtime (SetMoveImmediate) that never appears in the
            # exported state machine JSON - left unresolved, the next _enemy_turn() call would
            # find this enemy alive again, look up that move id, and raise StopIteration
            # (confirmed via decompile: Parafright/EyeWithTeeth each export only their one real
            # attack state). Re-resolve back through the monster's own initial state instead.
            if not enemy.alive and _power(enemy.powers, "IllusionPower"):
                spec = _specs(data)[enemy.model]
                enemies[index] = replace(
                    enemy, hp=int(_dict(enemy.values).get("MaxInitialHp", 0)),
                    move=_resolve_move(enemy, spec, rng, spec["initial_state"]),
                )
        # The debuffs that were already running tick at the end of the enemy side's turn; the two
        # player powers with their own hooks tick alongside them.
        player_powers = _tick_down_power(_tick_down_power(combat.player_powers, "ColossusPower"), "RetainHandPower")
        player_powers = _tick_debuffs(player_powers, player_debuffs)
        if doubt_weak:
            player_powers = _add_power(player_powers, "WeakPower", doubt_weak)
        if shame_frail:
            player_powers = _add_power(player_powers, "FrailPower", shame_frail)
        enemies = [
            replace(
                enemy,
                powers=_tick_debuffs(enemy.powers, enemy_debuffs[index] if index < len(enemy_debuffs) else ()),
            )
            for index, enemy in enumerate(enemies)
        ]
        combat = replace(combat, enemies=tuple(enemies), player_powers=player_powers)
        # TaintedPower.AfterSideTurnEnd and FlameBarrierPower.AfterSideTurnEnd both remove
        # themselves once the enemy side's turn ends.
        player_powers = combat.player_powers
        player_powers = _add_power(player_powers, "TaintedPower", -_power(player_powers, "TaintedPower"))
        player_powers = _add_power(player_powers, "FlameBarrierPower", -_power(player_powers, "FlameBarrierPower"))
        player_powers = _add_power(player_powers, "ReptileTrinketPower", -_power(player_powers, "ReptileTrinketPower"))
        # DuplicationPower (Duplicator) and OneTwoPunchPower (One-Two Punch) remove themselves at the
        # end of the player's turn, so an unused counter never carries into the next turn.
        for play_count_power in ("DuplicationPower", "OneTwoPunchPower"):
            amount = _power(player_powers, play_count_power)
            if amount:
                player_powers = _add_power(player_powers, play_count_power, -amount)
        # Turn-start relics (AfterSideTurnStart/BeforeSideTurnStart/AfterBlockCleared for the
        # upcoming turn). new_turn is the turn number the player is about to begin.
        new_turn, extra_energy, extra_draw, extra_block, enemies = combat.turn + 1, 0, 0, 0, list(combat.enemies)
        inferno_self_damage = _power(player_powers, "InfernoSelfDamage")
        if inferno_self_damage:
            combat = _apply_player_damage(combat, inferno_self_damage, trigger_inferno=True)
            player_powers = combat.player_powers
            enemies = list(combat.enemies)
        crimson_mantle = _power(player_powers, "CrimsonMantlePower")
        # CrimsonMantlePower keeps its self-damage in a DynamicVar (CanonicalVars base 0, and
        # CrimsonMantle.cs calls IncrementSelfDamage once per card played), so the game exports no second
        # power for it: a state rebuilt from an observation carries the mantle counter but no marker, and
        # used to skip the Unblockable 1 self-damage on every turn start.  The counters seen in real runs
        # are 8 (6,028 observations), 10 (2,225) and 18 (47), i.e. one base play, one upgraded play, or
        # two plays, so counter // 8 recovers the number of plays for every value the game reports.
        crimson_self_damage = max(_power(player_powers, "CrimsonMantleSelfDamage"), crimson_mantle // 8)
        if crimson_self_damage:
            combat = _apply_player_damage(combat, crimson_self_damage, trigger_inferno=True)
            player_powers = combat.player_powers
            enemies = list(combat.enemies)
        extra_block += crimson_mantle
        block_next = _power(player_powers, "BlockNextTurnPower")
        if block_next:
            extra_block += block_next
            player_powers = _add_power(player_powers, "BlockNextTurnPower", -block_next)
        # DemonFormPower.AfterSideTurnStart grants its amount as Strength at the start of every
        # one of the player's turns, so the damage curve keeps climbing for the whole fight.
        demon_form = _power(player_powers, "DemonFormPower")
        if demon_form:
            player_powers = _add_power(player_powers, "StrengthPower", demon_form)
        if RELIC_BRIMSTONE in relics:
            player_powers = _add_power(player_powers, "StrengthPower", 2)
            enemies = [replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", 1)) if enemy.alive else enemy for enemy in enemies]
        if RELIC_MERCURY_HOURGLASS in relics:
            enemies = [_damage_enemy(enemy, 3, powered=False) if enemy.alive else enemy for enemy in enemies]
        if RELIC_MR_STRUGGLES in relics:
            # MrStruggles.AfterPlayerTurnStart: CreatureCmd.Damage(combatState.HittableEnemies,
            # TurnNumber, ValueProp.Unpowered) - every enemy takes the new turn number in damage at the
            # start of each player turn (turn 2 -> 2, turn 5 -> 5).  24 recorded runs hold the relic and
            # 548 turn boundaries show exactly that drop, including 141 where the enemy was Vulnerable:
            # Unpowered means Vulnerable and Strength do not amplify it.  Over a 12 turn QUEEN fight this
            # is 78 damage per enemy, which the rollout could not see at all.
            enemies = [_damage_enemy(enemy, new_turn, powered=False) if enemy.alive else enemy for enemy in enemies]
        if RELIC_STONE_CALENDAR in relics and new_turn == 7:
            enemies = [_damage_enemy(enemy, 52, powered=False) if enemy.alive else enemy for enemy in enemies]
        # ArtOfWar.AfterEnergyReset: +1 energy if no attack was played on the turn that just
        # ended (never fires transitioning into turn 2 - there is no "previous turn" to check).
        if RELIC_ART_OF_WAR in relics and combat.turn > 1 and combat.attacks_played_this_turn == 0:
            extra_energy += 1
        if RELIC_PAELS_FLESH in relics and new_turn >= 3 and combat.turn < 3:
            combat = replace(combat, max_energy=combat.max_energy + 1)
        if RELIC_PAELS_TEARS in relics and combat.paels_tears_pending:
            extra_energy += 2
        if RELIC_CANDELABRA in relics and new_turn == 2:
            extra_energy += 2
        if RELIC_CHANDELIER in relics and new_turn == 3:
            extra_energy += 3
        if RELIC_HAPPY_FLOWER in relics and new_turn % 3 == 0:
            extra_energy += 1
        if RELIC_PENDULUM in relics and new_turn % 3 == 0:
            extra_draw += 1
        if RELIC_CAPTAINS_WHEEL in relics and new_turn == 3:
            extra_block += 18
        if RELIC_HORN_CLEAT in relics and new_turn == 2:
            extra_block += 14
        if RELIC_SPARKLING_ROUGE in relics and new_turn == 3:
            player_powers = _add_power(_add_power(player_powers, "StrengthPower", 1), "DexterityPower", 1)
        if RELIC_SELF_FORMING_CLAY in relics:
            clay = _power(player_powers, "SelfFormingClayPower")
            if clay:
                extra_block += clay
                player_powers = _add_power(player_powers, "SelfFormingClayPower", -clay)
        # RadiancePower.AfterEnergyReset: +1 energy at the turn's energy reset, then Decrement.
        radiance = _power(player_powers, "RadiancePower")
        if radiance:
            extra_energy += 1
            player_powers = _add_power(player_powers, "RadiancePower", -1)
        tangled = _power(player_powers, "TangledPower")
        if tangled:
            # TangledPower.AfterSideTurnEnd removes itself, so the Attack surcharge lasts one turn.
            player_powers = _add_power(player_powers, "TangledPower", -tangled)
        # NoDrawPower.AfterSideTurnEnd removes itself, so it never survives into the next turn.
        no_draw = _power(player_powers, "NoDrawPower")
        if no_draw:
            player_powers = _add_power(player_powers, "NoDrawPower", -no_draw)
        regen = _power(player_powers, "RegenPower")
        if regen and combat.player_hp > 0:
            # RegenPower.AfterSideTurnEnd heals its owner by Amount at the end of the side's turn and
            # decrements.  _enemy_turn already does this for enemies; the player side was missing, so a
            # held Regen was invisible to the rollout.  Replaying the end_turn of every record where the
            # player held Regen matched only 605/811 (74.6%), and the game's HP was higher by exactly the
            # power amount in the top mismatch groups (+5 in 47, +4 in 37, +3 in 30, +2 in 19).
            combat = replace(combat, player_hp=min(combat.player_max_hp, combat.player_hp + regen))
            player_powers = _add_power(player_powers, "RegenPower", -1)
        if _power(player_powers, "PlatingPower") and new_turn > 1:
            player_powers = _add_power(player_powers, "PlatingPower", -1)
        if RELIC_POCKETWATCH in relics and new_turn > 1 and combat.cards_played_this_turn <= 3:
            extra_draw += 3
        if RELIC_PAELS_BLOOD in relics:
            extra_draw += 1
        # PlatingPower, enemy side.  BeforeSideTurnEndEarly re-grants Block = Amount (Unpowered) at the
        # end of the enemy side's turn, i.e. BEFORE anything the player's turn start does - including a
        # ToastyMittens exhaust and the ForgottenSoul damage it triggers.  Plating decrements 1-9, so the
        # decay is counted from turn 3 (turn 1's block came from initial_combat).
        decay = 1 if new_turn >= 3 else 0
        enemies = [
            replace(
                enemy,
                powers=_add_power(enemy.powers, "PlatingPower", -decay),
                block=enemy.block + max(_power(enemy.powers, "PlatingPower") - decay, 0),
            )
            if enemy.alive and _power(enemy.powers, "PlatingPower")
            else enemy
            for enemy in enemies
        ]
        # ToastyMittens.BeforeHandDraw: exhausts the top card of the draw pile and grants a
        # permanent +1 Strength, every single turn. The draw pile is unordered here, so the
        # exhausted card is a random one.
        if RELIC_TOASTY_MITTENS in relics:
            player_powers = _add_power(player_powers, "StrengthPower", 1)
            mittens_pile = list(combat.draw_pile)
            if mittens_pile:
                mittens_exhausted = mittens_pile.pop(rng.randrange(len(mittens_pile)))
                combat = replace(
                    combat, draw_pile=tuple(mittens_pile),
                    exhaust_pile=combat.exhaust_pile + (mittens_exhausted,),
                )
                # The relic's exhaust is a real card Exhaust, so the recurring exhaust hooks run on it.
                # This is the reason the QUEEN fight's boss lost exactly 1 HP on every turn: those runs
                # carry ToastyMittens and ForgottenSoul together, and ForgottenSoul.AfterCardExhausted
                # deals 1 unpowered damage to a random hittable enemy per Exhaust
                # (act3_verify_head_H2LV6ZJ4XW seq 555/561/577; 177 of 188 QUEEN end-turn replays were
                # off by exactly 1 before this line existed).
                combat = _after_exhaust(replace(combat, enemies=tuple(enemies), player_powers=player_powers), (mittens_exhausted,), rng, data)
                enemies = list(combat.enemies)
        # ClarityPower.ModifyHandDraw: +1 card, then AfterSideTurnStart decrements the counter.
        clarity = _power(player_powers, "ClarityPower")
        if clarity:
            extra_draw += 1
            player_powers = _add_power(player_powers, "ClarityPower", -1)
        # Fiddle.ModifyHandDrawLate: +2 on the start-of-turn hand draw, every turn.
        if RELIC_FIDDLE in relics:
            extra_draw += 2
        # BloodSoakedRose.ModifyMaxEnergy: +1 at every energy reset. The bridge's `max_energy` is the
        # game's effective value for the turn being observed, so a run holding the relic already
        # reports 4 at turn 1 - adding 1 again here double counts. Nothing to model: the effect is
        # already in the observation.
        draw_count = max(0, 5 + extra_draw - _power(player_powers, "MindRotPower"))
        hand = list(combat.hand)
        discard = list(combat.discard_pile)
        aggression = _power(player_powers, "AggressionPower")
        if aggression:
            candidates = [index for index, card in enumerate(discard) if card_name(card) in ATTACKS]
            selected_indices = rng.sample(candidates, min(aggression, len(candidates)))
            selected = [_upgrade_card(discard[index]) for index in selected_indices]
            for index in sorted(selected_indices, reverse=True):
                discard.pop(index)
            hand.extend(selected)
            upgraded_cards = _remember_legacy_upgrades(combat, tuple(selected))
        else:
            upgraded_cards = combat.upgraded_cards
        barricaded = bool(_power(player_powers, "BarricadePower"))
        retained_block = combat.player_block if barricaded else min(combat.player_block, 10) if RELIC_STURDY_CLAMP in relics else 0
        toric_pending = combat.toric_pending
        if toric_pending and not barricaded:
            # ToricToughnessPower.AfterBlockCleared: re-grant the stored block (ValueProp.Unpowered,
            # so no Dexterity and no Frail), then Decrement.  Barricade prevents the clear, so the
            # power never fires that turn.
            extra_block += sum(stored for stored, _ in toric_pending)
            toric_pending = tuple((stored, uses - 1) for stored, uses in toric_pending if uses > 1)
        # RampartPower.AfterSideTurnStart (LivingShield.cs applies Rampart 25 to itself; the grant
        # is not in the exported state machine JSON): at the start of every player turn each copy
        # grants its amount as Unpowered block to every living TurretOperator on the enemy side,
        # not to the Rampart owner.  That is why the block appears on an enemy carrying no power of
        # its own, and why the model saw 25 block vanish and never come back - the live observation
        # only carries the block for the turn it was read on.  Real runs: 560 decisions in 73 runs
        # held TurretOperator block 25 (turn 1 x175, turn 2 x163, turn 3 x50, turn 4 x5) while
        # LivingShield held RampartPower 25.  Killing the shield stops the regeneration, which the
        # rollout can only price once the grant is here.
        rampart = sum(_power(enemy.powers, "RampartPower") for enemy in enemies if enemy.alive)
        if rampart:
            enemies = [
                replace(enemy, block=enemy.block + rampart)
                if enemy.alive and enemy.model == "MONSTER.TURRET_OPERATOR"
                else enemy
                for enemy in enemies
            ]
        combat = replace(
            combat, hand=tuple(hand), discard_pile=tuple(discard), player_block=retained_block + extra_block,
            toric_pending=toric_pending,
            energy=combat.max_energy + extra_energy, turn=new_turn, player_powers=player_powers, enemies=tuple(enemies),
            upgraded_cards=upgraded_cards,
            paels_tears_pending=False,
            attacks_played_this_turn=0, skills_played_this_turn=0, block_cards_this_turn=0, cards_played_this_turn=0,
            bound_played_this_turn=False, chains_afflicted_this_turn=0,
            hellraiser_autoplays_this_turn=0, pyre_autoplays_this_turn=0,
            powers_played_this_turn=0, damaged_this_turn=False, lost_hp_this_turn=False, exhausted_this_turn=False, damage_received_this_turn=0,
            cards_played_last_turn=combat.cards_played_this_turn, enlightened_this_turn=False, free_cards=(),
            play_duplicated=False,
        )
        combat = _draw_into_combat(combat, draw_count, data, rng, from_hand_draw=True)
        # MayhemPower.AfterAutoPrePlayPhaseEntered: plays Amount cards off the draw pile before
        # the player may act.
        return _autoplay_from_draw_pile(combat, _power(combat.player_powers, "MayhemPower"), data, rng)

    action_card, _, target = action.partition("@")
    card_index = None
    if action_card.startswith("card:"):
        card_index = int(action_card[5:])
        played_value = combat.hand[card_index]
    else:
        played_value = action_card
    card = card_name(played_value)
    if isinstance(played_value, Card) and played_value.bound:
        # BeforeCardPlayed sets this before the play resolves, so the next Bound card in the same turn
        # is gated off by ShouldPlay (real runs played Bound cards 279 times).
        combat = replace(combat, bound_played_this_turn=True)
    # Play-count powers. DuplicationPower (Duplicator potion) adds one extra resolution to the play
    # it modifies and OneTwoPunchPower (One-Two Punch) does the same for Attacks only; the counter
    # is consumed by that play (AfterModifyingCardPlayCount) and both powers are removed at the end
    # of the player's turn. For an Attack the extra resolution is one more hit of the same damage,
    # and for a block card the grant is applied twice.
    play_duplicated = bool(
        _power(combat.player_powers, "DuplicationPower")
        or (card in ATTACKS and _power(combat.player_powers, "OneTwoPunchPower"))
    )
    # GigantificationPower marks the first powered Attack played on the turn and multiplies that
    # command's damage by 3, then decrements.
    gigantified = bool(
        card in ATTACKS
        and combat.attacks_played_this_turn == 0
        and _power(combat.player_powers, "GigantificationPower")
    )
    if play_duplicated:
        power_name = "DuplicationPower" if _power(combat.player_powers, "DuplicationPower") else "OneTwoPunchPower"
        combat = replace(
            combat,
            player_powers=_add_power(combat.player_powers, power_name, -1),
        )
    # The flag describes this play only, so it is reset for every action, not just the duplicated
    # one - a leftover True from an earlier play would double the next card's block for free.
    combat = replace(combat, play_duplicated=play_duplicated)
    # An increased play count re-runs the card's OnPlay, so its power applies again.
    # ThrowingAxe.ModifyCardPlayCount hands back playCount + 1 for the first card we play each combat.
    # The model already has a "this play happens twice" mechanism (play_duplicated), which the attack
    # branches consume as an extra hit, so the relic rides on it.  A card that some other effect already
    # duplicates would really play three times; the model doubles it, which is the rare case.
    if RELIC_THROWING_AXE in combat.player_relics and combat.cards_played_combat == 0:
        play_duplicated = True
    combat = replace(combat, play_duplicated=play_duplicated)
    plays = 2 if play_duplicated else 1
    plays = 2 if play_duplicated else 1
    if gigantified:
        combat = replace(combat, player_powers=_add_power(combat.player_powers, "GigantificationPower", -1))
    hand = list(combat.hand)
    if RELIC_BELLOWS in combat.player_relics and combat.turn == 1 and not combat.bellows_used:
        hand = [_upgrade_card(value) for value in hand]
        combat = replace(combat, upgraded_cards=_remember_legacy_upgrades(combat, tuple(hand)), bellows_used=True)
        if card_index is not None:
            played_value = hand[card_index]
            card = card_name(played_value)
    if card in SKILLS:
        # AfterCardPlayed fires once per resolution, so an increased play count runs these hooks again.
        for _ in range(plays):
            vital_spark = sum(_power(enemy.powers, "VitalSparkPower") for enemy in combat.enemies if enemy.alive)
            if vital_spark:
                # VitalSparkPower (Infested Prism's PULSATE_MOVE) taints every Skill card in the
                # deck; playing one grants TaintedPower equal to the current stack, which adds flat
                # damage to powered attacks against the player until the enemy's turn ends.
                combat = replace(combat, player_powers=_add_power(combat.player_powers, "TaintedPower", vital_spark))
            # EnragePower.AfterCardPlayed: every Skill grants its stack as Strength to the owner.
            # Apply this before the card branch returns so block/draw-only Skills are covered too.
            combat = replace(
                combat,
                enemies=tuple(
                    replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", _power(enemy.powers, "EnragePower")))
                    if enemy.alive and _power(enemy.powers, "EnragePower") else enemy
                    for enemy in combat.enemies
                ),
            )
    if card_index is None:
        hand.remove(played_value)
    else:
        hand.pop(card_index)
    free_cards = list(combat.free_cards)
    card_is_free = played_value in free_cards
    card_was_upgraded = card_is_upgraded(combat, played_value)
    card_cost = 0 if card_is_free else _effective_cost(combat, played_value)
    if card_is_free:
        free_cards.remove(played_value)
    block_card_has_gain = card in BLOCK_CARDS
    if card == SECOND_WIND:
        block_card_has_gain = any(card_name(value) not in ATTACKS for value in hand)
    unmovable_amount = _power(combat.player_powers, "UnmovablePower")
    unmovable_double = block_card_has_gain and combat.block_cards_this_turn < unmovable_amount
    if block_card_has_gain:
        # Each resolution counts as a card played, so the per-play counters advance once per resolution.
        combat = replace(combat, block_cards_this_turn=combat.block_cards_this_turn + plays)
    # Card-play-counting relics (Kunai/Shuriken/Ornamental Fan/Kusarigama/Letter Opener/
    # Nunchaku/Tuning Fork): all fire off a plain "every Nth attack/skill played" counter, either
    # reset each turn (the four "every 3rd attack" relics, Letter Opener's "every 3rd skill") or
    # cumulative for the whole fight (Nunchaku, Tuning Fork - both "every 10th").
    relics = combat.player_relics
    # The per-play counters advance once per resolution, so a duplicated play counts `plays` times.
    attacks_this_turn = combat.attacks_played_this_turn + (plays if card in ATTACKS else 0)
    skills_this_turn = combat.skills_played_this_turn + (plays if card in SKILLS else 0)
    attacks_combat = combat.attacks_played_combat + (plays if card in ATTACKS else 0)
    skills_combat = combat.skills_played_combat + (plays if card in SKILLS else 0)
    cards_combat = combat.cards_played_combat + plays
    cards_this_turn = combat.cards_played_this_turn + plays
    powers_this_turn = combat.powers_played_this_turn + (plays if card in POWERS else 0)
    # Relic counters (Pen Nib's attacks-played, Nunchaku's) are not in the observation - the bridge
    # writes relic ids only - so attacks_played_combat is 0 when a decision state is rebuilt.
    # `0 % 10 == 0` read that as "already activated", doubling every first attack of every combat.
    # The game activates these at the 10th attack, so treat them as inactive until the model has
    # counted 10 itself.
    pen_nib_double = RELIC_PEN_NIB in relics and card in ATTACKS and attacks_combat >= 10 and attacks_combat % 10 == 0
    helmet_block = 4 if RELIC_INTIMIDATING_HELMET in relics and (card_cost >= 2 or (card == WHIRLWIND and combat.energy >= 2)) else 0
    vambrace_double = RELIC_VAMBRACE in relics and not combat.vambrace_used and card in BLOCK_CARDS
    lamp_double = RELIC_UNSETTLING_LAMP in relics and not combat.unsettling_lamp_used and card in DEBUFF_CARDS
    energy_gain_allowed = not _power(combat.player_powers, "NoEnergyGainPower")
    combo_powers, combo_enemies, combo_block, combo_energy = combat.player_powers, list(combat.enemies), 0, 0
    combo_pending: list[tuple[str, int]] = []
    combo_block += helmet_block
    if card in ATTACKS and _power(combat.player_powers, "FreeAttackPower"):
        # FreeAttackPower.BeforeCardPlayed decrements once per Attack played from hand.
        combo_powers = _add_power(combo_powers, "FreeAttackPower", -1)
    if card in POWERS and RELIC_LOST_WISP in relics:
        # LostWisp.AfterCardPlayed: 8 Unpowered damage to every hittable enemy per Power card.
        combo_enemies = [
            _damage_enemy(enemy, 8, powered=False) if enemy.alive else enemy for enemy in combo_enemies
        ]
    if card in ATTACKS:
        combo_block += _power(combat.player_powers, "RagePower")
        if RELIC_KUNAI in relics and attacks_this_turn % 3 == 0:
            combo_pending.append(("DexterityPower", 1))
        if RELIC_SHURIKEN in relics and attacks_this_turn % 3 == 0:
            combo_pending.append(("StrengthPower", 1))
        if RELIC_ORNAMENTAL_FAN in relics and attacks_this_turn % 3 == 0:
            combo_block += 4
        if RELIC_KUSARIGAMA in relics and attacks_this_turn % 3 == 0:
            alive = [i for i, enemy in enumerate(combo_enemies) if enemy.alive]
            if alive:
                hit = rng.choice(alive)
                combo_enemies[hit] = _damage_enemy(combo_enemies[hit], 6, powered=False)
        if RELIC_NUNCHAKU in relics and attacks_combat >= 10 and attacks_combat % 10 == 0 and energy_gain_allowed:
            combo_energy += 1
    if card in SKILLS:
        if RELIC_LETTER_OPENER in relics and skills_this_turn % 3 == 0:
            combo_enemies = [_damage_enemy(enemy, 5, powered=False) if enemy.alive else enemy for enemy in combo_enemies]
        if RELIC_TUNING_FORK in relics and skills_combat % 10 == 0:
            combo_block += 7
    if card == RAGE:
        combo_powers = _add_power(combo_powers, "RagePower", 5 if card_was_upgraded else 3)
    if card == COLOSSUS:
        combo_powers = _add_power(combo_powers, "ColossusPower", 1)
    combat = replace(
        combat, played_this_turn=True, player_powers=combo_powers, enemies=tuple(combo_enemies),
        pending_combo_powers=combat.pending_combo_powers + tuple(combo_pending),
        player_block=combat.player_block + combo_block, energy=combat.energy + combo_energy,
        attacks_played_this_turn=attacks_this_turn, skills_played_this_turn=skills_this_turn,
        attacks_played_combat=attacks_combat, skills_played_combat=skills_combat, cards_played_this_turn=cards_this_turn,
        cards_played_combat=cards_combat,
        powers_played_this_turn=powers_this_turn, free_cards=tuple(free_cards),
        vambrace_used=combat.vambrace_used or vambrace_double,
        unsettling_lamp_used=combat.unsettling_lamp_used or lamp_double,
    )
    if card == METAMORPHOSIS:
        # Generates Cards (3, 5 upgraded) random Attacks straight into the draw pile, each free
        # for the rest of the combat, then exhausts itself.
        count = 5 if card_was_upgraded else 3
        generated = tuple(Card(rng.choice(INFERNAL_BLADE_ATTACKS)) for _ in range(count))
        spent = 0 if card_is_free else _effective_cost(combat, played_value)
        combat = replace(
            combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (played_value,),
            draw_pile=combat.draw_pile + generated, free_cards=combat.free_cards + generated,
            energy=combat.energy - spent,
        )
        return _after_exhaust(combat, (played_value,), rng, data)
    if card == STOKE:
        # Stoke exhausts the whole hand, then generates that many cards back into it (upgraded
        # when Stoke itself is). The generated cards are not free - they cost their own energy.
        exhausted = tuple(hand)
        spent = 0 if card_is_free else _effective_cost(combat, played_value)
        combat = replace(
            combat, hand=(), discard_pile=combat.discard_pile + (played_value,),
            exhaust_pile=combat.exhaust_pile + exhausted, energy=combat.energy - spent,
        )
        combat = _after_exhaust(combat, exhausted, rng, data)
        generated = tuple(
            Card(rng.choice(STOKE_GENERATION), upgraded=card_was_upgraded) for _ in exhausted
        )
        return replace(combat, hand=combat.hand + generated)
    if card == HAVOC:
        spent = 0 if card_is_free else _effective_cost(combat, played_value)
        combat = replace(
            combat, hand=tuple(hand), discard_pile=combat.discard_pile + (played_value,),
            energy=combat.energy - spent,
        )
        return _autoplay_top_of_draw(combat, data, rng)
    if card == BATTLE_TRANCE:
        combat = replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile + (played_value,))
        combat = _draw_into_combat(combat, 3, data, rng)
        # BattleTrance applies NoDraw after its own draw, so nothing else draws this turn.
        return replace(combat, player_powers=_add_power(combat.player_powers, "NoDrawPower", 1))
    if card == SLIMED:
        # Slimed.OnUse draws 1, then GetResultPileTypeForCardPlay sends it to the exhaust pile because it
        # carries CardKeyword.Exhaust.  Sending it to no pile at all lost both the exhaust and the hooks
        # that hang off it: the game dealt 1 from ForgottenSoul on every Slimed play in the runs that
        # hold the relic, which the model priced at 0.
        combat = _draw_into_combat(
            replace(combat, hand=tuple(hand), energy=combat.energy - (0 if card_is_free else 1)), 1, data, rng
        )
        return _after_exhaust(
            replace(combat, exhaust_pile=combat.exhaust_pile + (played_value,)), (played_value,), rng, data
        )
    if card == FRANTIC_ESCAPE:
        enemies = list(combat.enemies)
        for index, enemy in enumerate(enemies):
            if _power(enemy.powers, "SandpitPower"):
                enemies[index] = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", 1))
                break
        spent = 0 if card_is_free else _effective_cost(combat, played_value)
        # The copy that was played is the one that gets more expensive, so it returns to the
        # discard carrying its own increment.
        discarded = replace(played_value, extra_cost=played_value.extra_cost + 1) if isinstance(played_value, Card) else played_value
        return replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile + (discarded,), energy=combat.energy - spent, enemies=tuple(enemies))
    if card == SHRUG:
        base = 8 + (3 if card_was_upgraded else 0)
        combat = _grant_block(combat, base, rng, vambrace_double=vambrace_double, unmovable_double=unmovable_double)
        combat = replace(
            combat, hand=tuple(hand), discard_pile=combat.discard_pile + (played_value,),
            energy=combat.energy - (0 if card_is_free else 1),
        )
        # The play count increases how many times the card's commands resolve, so its draw runs again.
        return _draw_into_combat(combat, 1 * (2 if play_duplicated else 1), data, rng)
    if card in CARD_DRAW:
        combat = _draw_into_combat(
            replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile),
            (CARD_DRAW[card] + (1 if card == POMMEL_STRIKE and card_was_upgraded else 0)) * (2 if play_duplicated else 1), data, rng,
        )
        hand = list(combat.hand)
    if card == IMPATIENCE and not any(card_name(value) in ATTACKS for value in hand):
        combat = _draw_into_combat(replace(combat, hand=tuple(hand)), 2, data, rng)
        hand = list(combat.hand)
    # Enlightenment.OnPlay (reduceOnly): once played, every card costs at most 1 for the rest of
    # the turn. WHIRLWIND's X cost is exempt - it isn't a fixed cost to reduce.
    if card in {WHIRLWIND, VOLLEY, CASCADE}:
        spent = combat.energy
    else:
        spent = card_cost
    if card_is_free:
        spent = 0
    whirlwind_x = combat.energy + (2 if RELIC_CHEMICAL_X in relics else 0)
    whirlwind_damage = 5 * whirlwind_x if card == WHIRLWIND else 0
    volley_x = whirlwind_x if card == VOLLEY else 0
    energy = combat.energy - spent + (2 if energy_gain_allowed and card in {BLOODLETTING, BELIEVE_IN_YOU, PRODUCTION, OFFERING} else 0)
    if card == FORGOTTEN_RITUAL and energy_gain_allowed and combat.exhausted_this_turn:
        energy += 4 if card_was_upgraded else 3
    if card == EXPECT_A_FIGHT and energy_gain_allowed:
        energy += sum(card_name(value) in ATTACKS for value in hand)
    player_hp = combat.player_hp
    self_damage = SELF_DAMAGE.get(card, 0)
    if isinstance(played_value, Card) and played_value.enchantment == ENCHANTMENT_CORRUPTED and card in ATTACKS:
        self_damage += 2
    # GalvanicPower (enemy buff): BeforeCombatStart and AfterCardEnteredCombat afflict every one of
    # the player's Power cards with Galvanized, and AfterCardPlayed deals the power's amount as
    # Unpowered damage back at the player for each afflicted card played. Without this the rollout
    # plays Inflame/Rupture/Feel No Pain for free against an enemy charging 6 HP a piece.
    # ponytail: the affliction rides the card, so it outlives the enemy that applied it - taking the
    # largest amount any enemy in this fight brought (alive or dead) keeps that without tracking
    # per-card afflictions. Upgrade to per-card state if an enemy ever applies two different amounts.
    if card in POWERS:
        self_damage += max((_power(enemy.powers, "GalvanicPower") for enemy in combat.enemies), default=0)
    if self_damage:
        # Apply Tungsten Rod/Beating Remnant/Lizard Tail to card self-damage as well as enemy hits.
        # An increased play count re-runs OnPlay, so the self-damage happens once per resolution.
        damaged = _apply_player_damage(combat, self_damage * (2 if play_duplicated else 1), trigger_inferno=True)
        player_hp, combat = damaged.player_hp, damaged
    if card == NOT_YET:
        # No max-HP tracking in this model (Combat has no companion max_hp field), so the heal is
        # uncapped - a small, safe-direction gap since it can only ever make the sim think the
        # player has slightly more HP margin than they truly do.
        player_hp += 10
    player_powers = combat.player_powers
    if card == RUPTURE:
        player_powers = _add_power(player_powers, "RupturePower", (1) * plays)
    if card == STAMPEDE:
        # Stampede.OnPlay applies StampedePower with its Power var (1); the upgrade only makes the
        # card cheaper, it does not raise the counter.
        player_powers = _add_power(player_powers, "StampedePower", (1) * plays)
    if card == DEMON_FORM:
        # DemonForm.OnPlay applies DemonFormPower with its StrengthPower var (2, upgraded 3).
        player_powers = _add_power(player_powers, "DemonFormPower", (3 if card_was_upgraded else 2) * plays)
    if card == FASTEN:
        # Fasten.OnPlay applies FastenPower with its ExtraBlock var (4, upgraded 6).
        player_powers = _add_power(player_powers, "FastenPower", (6 if card_was_upgraded else 4) * plays)
    if card == AGGRESSION:
        player_powers = _add_power(player_powers, "AggressionPower", (1) * plays)
    if card == DARK_EMBRACE:
        player_powers = _add_power(player_powers, "DarkEmbracePower", (1) * plays)
    if card == CRIMSON_MANTLE:
        player_powers = _add_power(player_powers, "CrimsonMantlePower", (10 if card_was_upgraded else 8) * plays)
        player_powers = _add_power(player_powers, "CrimsonMantleSelfDamage", (1) * plays)
    if card == HELLRAISER:
        player_powers = _add_power(player_powers, "HellraiserPower", (1) * plays)
    if card == INFERNO:
        player_powers = _add_power(player_powers, "InfernoPower", (9 if card_was_upgraded else 6) * plays)
        # InfernoPower keeps this private counter separately from its retaliation amount.
        player_powers = _add_power(player_powers, "InfernoSelfDamage", (1) * plays)
    if card == CRUELTY:
        player_powers = _add_power(player_powers, "CrueltyPower", (50 if card_was_upgraded else 25) * plays)
    if card == JUGGERNAUT:
        player_powers = _add_power(player_powers, "JuggernautPower", (8 if card_was_upgraded else 6) * plays)
    if card == JUGGLING:
        # Juggling.OnPlay applies JugglingPower(1). Its upgrade only adds the Innate keyword, so
        # the counter amount never changes.
        player_powers = _add_power(player_powers, "JugglingPower", (1) * plays)
    if card == PANACHE:
        # Panache.OnPlay applies PanachePower with its PanacheDamage var (10, upgraded 14).
        player_powers = _add_power(player_powers, "PanachePower", (14 if card_was_upgraded else 10) * plays)
    if card == ONE_TWO_PUNCH:
        # OneTwoPunch.OnPlay applies OneTwoPunchPower with its Attacks var (1, upgraded 2).
        player_powers = _add_power(player_powers, "OneTwoPunchPower", (2 if card_was_upgraded else 1) * plays)
    # RupturePower.AfterDamageReceived: any unblocked damage a card deals to the player during
    # their own turn (Hemokinesis/Bloodletting/Breakthrough/Offering's self-damage here) grants
    # Strength equal to the Rupture stack.
    rupture = _power(player_powers, "RupturePower")
    if rupture and self_damage:
        player_powers = _add_power(player_powers, "StrengthPower", (rupture) * plays)
    if card == INFLAME:
        player_powers = _add_power(player_powers, "StrengthPower", (2) * plays)
    if card == FLAME_BARRIER:
        player_powers = _add_power(player_powers, "FlameBarrierPower", (4) * plays)
    if card == BARRICADE:
        player_powers = _add_power(player_powers, "BarricadePower", (1) * plays)
    if card == UNMOVABLE:
        player_powers = _add_power(player_powers, "UnmovablePower", (1) * plays)
    if card == EXPECT_A_FIGHT:
        player_powers = _add_power(player_powers, "NoEnergyGainPower", (1) * plays)
    if card == PRIMAL_FORCE:
        if isinstance(played_value, Card):
            hand = [Card(GIANT_ROCK, card_was_upgraded) if card_name(value) in ATTACKS else value for value in hand]
        else:
            hand = [GIANT_ROCK if card_name(value) in ATTACKS else value for value in hand]
    # SecretWeapon.OnPlay picks one CardType.Attack out of the draw pile and adds it to hand.  The
    # player makes that choice; the model prices it as the strongest Attack in the draw pile, which is
    # what our own heuristic would want there.  The chosen index is remembered so the post-play rewrite
    # removes exactly that copy from the draw pile.
    secret_weapon_draw_index: int | None = None
    if card == SECRET_WEAPON:
        candidates = [
            (CARD_DAMAGE.get(card_name(value), 0) + (2 if card_is_upgraded(combat, value) else 0), index)
            for index, value in enumerate(combat.draw_pile)
            if card_name(value) in ATTACKS
        ]
        if candidates:
            secret_weapon_draw_index = max(candidates)[1]
            hand.append(combat.draw_pile[secret_weapon_draw_index])
    # SecretWeapon carries CardKeyword.Exhaust on the base card, and OnUpgrade removes it.
    exhaust = card in EXHAUSTS or (card == SECRET_WEAPON and not card_was_upgraded)
    # CardModel.GetResultPileTypeForCardPlay sends the played card to PileType.None when it is a
    # CardType.Power card (and the Exhaust keyword wins first), so a Power leaves the combat entirely.
    # POWERS is already exactly the CardType.Power set the model can play - the decompile has 111 of them.
    # Every recorded play of the Power cards this model can play shows exhaust +0 and discard +0 - Inflame
    # 58, Stone Armor 35, Rupture 30, Crimson Mantle 22, Hellraiser 16, Unmovable 9, Vicious 4,
    # Aggression 3, Pyre 1, Juggernaut 1, Stampede 1 - while the model used to drop them into the discard,
    # which let a spent Power be shuffled back and replayed later in the same fight.
    leaves_combat = not exhaust and card in POWERS
    exhaust_before = combat.exhaust_pile
    played_pile_index = len(exhaust_before if exhaust else combat.discard_pile)
    exhaust_pile = exhaust_before + ((played_value,) if exhaust else ())
    enlightened = combat.enlightened_this_turn or card == ENLIGHTENMENT
    combat = replace(
        combat, hand=tuple(hand),
        discard_pile=combat.discard_pile + (() if (exhaust or leaves_combat) else (played_value,)),
        exhaust_pile=exhaust_pile,
        energy=energy, player_hp=player_hp, player_powers=player_powers, enlightened_this_turn=enlightened,
    )
    if secret_weapon_draw_index is not None:
        combat = replace(
            combat,
            draw_pile=combat.draw_pile[:secret_weapon_draw_index] + combat.draw_pile[secret_weapon_draw_index + 1:],
        )
    if card == ARMAMENTS:
        upgradable = tuple(
            index for index, value in enumerate(hand)
            if card_name(value) in CARD_COST
            and card_name(value) not in {SLIMED, FRANTIC_ESCAPE}
            and not card_is_upgraded(combat, value)
        )
        if card_was_upgraded:
            targets = upgradable
        elif target.isdigit():
            target_index = int(target)
            targets = (target_index,) if target_index in upgradable else ()
        else:
            targets = ()
        for index in targets:
            hand[index] = _upgrade_card(hand[index])
        combat = replace(
            combat,
            hand=tuple(hand),
            upgraded_cards=_remember_legacy_upgrades(combat, tuple(hand[index] for index in targets)),
        )
    if card == PYRE:
        combat = replace(combat, max_energy=combat.max_energy + (2 if card_was_upgraded else 1))
    combat = _sync_red_skull(combat)
    combat = _after_exhaust(combat, (played_value,) if exhaust else (), rng, data)
    if card == APOTHEOSIS:
        # Apotheosis.OnPlay runs CardCmd.Upgrade on every other upgradable copy in every pile
        # (hand, draw, discard, exhaust). The game keeps that upgrade for the rest of the run, but
        # a rollout only sees this fight, so the card scores what the rest of the current combat
        # gets out of the rewrite. Curses and status cards (MaxUpgradeLevel 0) are skipped.
        targets = tuple(
            value
            for pile in (combat.hand, combat.draw_pile, combat.discard_pile, combat.exhaust_pile, combat.free_cards)
            for value in pile
            if value != played_value and _is_upgradable_copy(combat, value)
        )
        def _upgraded(value: CardValue) -> CardValue:
            return _upgrade_card(value) if _is_upgradable_copy(combat, value) else value

        return replace(
            combat,
            hand=tuple(_upgraded(value) for value in combat.hand),
            draw_pile=tuple(_upgraded(value) for value in combat.draw_pile),
            discard_pile=tuple(_upgraded(value) for value in combat.discard_pile),
            exhaust_pile=tuple(_upgraded(value) for value in combat.exhaust_pile),
            free_cards=tuple(_upgraded(value) for value in combat.free_cards),
            upgraded_cards=_remember_legacy_upgrades(combat, targets),
        )
    if card in POWERS:
        for _ in range(plays):
            combat = _after_power_play(combat, rng, data)
    juggling_amount = _power(combat.player_powers, "JugglingPower")
    if juggling_amount and card in ATTACKS and attacks_this_turn == 3:
        # JugglingPower.AfterCardPlayed: the 3rd Attack played during the player's side puts one
        # clone of that Attack into hand. The counter is per-turn (AfterSideTurnEnd resets it), and
        # JugglingPower.AfterApplied seeds it with the attacks already played this turn.
        combat = replace(combat, hand=combat.hand + tuple(_copy_card(card, played_value) for _ in range(juggling_amount)))
    panache = _power(combat.player_powers, "PanachePower")
    if panache and card != PANACHE:
        # PanachePower.AfterCardPlayed: 5 cards played after the Panache play deal its amount as
        # unpowered damage to every hittable enemy, then the 5-card counter resets. The play that
        # applied the power is not counted (its `alreadyApplied` flag). AfterCardPlayed fires once per
        # resolution, so an increased play count advances the counter that many times.
        cards = combat.panache_cards_this_turn
        for _ in range(plays):
            cards += 1
            if cards >= PANACHE_TRIGGER_CARDS:
                cards = 0
                enemies = [
                    _damage_enemy(enemy, panache, powered=False) if enemy.alive else enemy
                    for enemy in combat.enemies
                ]
                combat = replace(combat, enemies=tuple(enemies), panache_cards_this_turn=cards)
        if cards != combat.panache_cards_this_turn:
            combat = replace(combat, panache_cards_this_turn=cards)
    fiend_fire_count = 0
    if card == FIEND_FIRE:
        # Fiend Fire exhausts the remaining hand, then hits once per exhausted card.
        fiend_fire_cards = tuple(combat.hand)
        combat = replace(combat, hand=(), exhaust_pile=combat.exhaust_pile + fiend_fire_cards)
        combat = _after_exhaust(combat, fiend_fire_cards, rng, data)
        fiend_fire_count = len(fiend_fire_cards)
    if card == INFERNAL_BLADE:
        generated = rng.choice(INFERNAL_BLADE_ATTACKS)
        generated_value = Card(generated) if isinstance(played_value, Card) else generated
        combat = replace(combat, hand=tuple(combat.hand) + (generated_value,), free_cards=combat.free_cards + (generated_value,))
    if RELIC_RAZOR_TOOTH in relics and (card in ATTACKS or card in SKILLS):
        if isinstance(played_value, Card):
            upgraded_value = _upgrade_card(played_value)
            pile = list(combat.exhaust_pile if exhaust else combat.discard_pile)
            pile[played_pile_index] = upgraded_value
            combat = replace(combat, **{"exhaust_pile" if exhaust else "discard_pile": tuple(pile)})
        else:
            combat = replace(combat, upgraded_cards=tuple(dict.fromkeys(combat.upgraded_cards + (card,))))
    if card in CARD_BLOCK:
        base = CARD_BLOCK[card]
        if card_was_upgraded:
            base += 4 if card == BLOOD_WALL else 3 if card in {DEFEND, EVIL_EYE, COLOSSUS} else 2 if card in {TRUE_GRIT, TORIC_TOUGHNESS} else 0 if card == ARMAMENTS else 1
        # FastenPower.ModifyBlockAdditive adds its amount to block from any card carrying
        # CardTag.Defend. In the decompiled card pool exactly two of the Ironclad's cards declare
        # that tag - DefendIronclad and UltimateDefend - so Shrug It Off, Iron Wave and the rest
        # are NOT boosted. Fasten does not tag itself either; it only looks the tag up for a tooltip.
        if card in DEFEND_TAGGED:
            base += _power(combat.player_powers, "FastenPower")
        before = combat.player_block
        combat = _grant_block(combat, base, rng, vambrace_double=vambrace_double, unmovable_double=unmovable_double)
        if card == TORIC_TOUGHNESS:
            # ToricToughness.OnPlay stores the block it actually granted (so Frail shrinks the
            # stored amount too), then applies the power with Amount = Turns = 2.
            return replace(combat, toric_pending=combat.toric_pending + ((combat.player_block - before, 2),))
    if card in {DEFEND, EQUILIBRIUM, IMPERVIOUS, LIFT, ULTIMATE_DEFEND, FLAME_BARRIER, FINESSE, COLOSSUS, ARMAMENTS, BLOOD_WALL}:
        return combat
    if card == RAGE:
        return combat
    if card == TRUE_GRIT:
        if combat.hand:
            # Only the upgraded TrueGrit lets the player choose; the base one is Rng-driven.
            sacrificed = (
                _choose_exhaust_from_hand(combat, rng) if card_was_upgraded
                else combat.hand[rng.randrange(len(combat.hand))]
            )
            hand = list(combat.hand)
            hand.remove(sacrificed)
            combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (sacrificed,))
            combat = _after_exhaust(combat, (sacrificed,), rng, data)
        return combat
    if card == EVIL_EYE:
        if combat.exhausted_this_turn:
            base = CARD_BLOCK[EVIL_EYE] + (3 if card_was_upgraded else 0)
            combat = _grant_block(combat, base, rng, vambrace_double=vambrace_double, unmovable_double=unmovable_double)
        return combat
    if card == BURNING_PACT:
        if combat.hand:
            sacrificed = _choose_exhaust_from_hand(combat, rng)
            hand = list(combat.hand)
            hand.remove(sacrificed)
            combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (sacrificed,))
            combat = _after_exhaust(combat, (sacrificed,), rng, data)
        return _draw_into_combat(combat, 2 + (1 if card_was_upgraded else 0), data, rng)
    if card == PURITY:
        selected = _choose_exhaustible_from_hand(combat, 5 if card_was_upgraded else 3)
        if selected:
            hand = list(combat.hand)
            for value in selected:
                hand.remove(value)
            combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + selected)
            combat = _after_exhaust(combat, selected, rng, data)
        return combat
    if card == BRAND:
        if combat.hand:
            sacrificed = _choose_exhaust_from_hand(combat, rng)
            hand = list(combat.hand)
            hand.remove(sacrificed)
            combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (sacrificed,))
            combat = _after_exhaust(combat, (sacrificed,), rng, data)
        return replace(combat, player_powers=_add_power(combat.player_powers, "StrengthPower", 1 + (1 if card_was_upgraded else 0)))
    if card == RELAX:
        base = 15 + (1 if card_was_upgraded else 0)
        return _grant_block(combat, base, rng, vambrace_double=vambrace_double, unmovable_double=unmovable_double)
    if card == SECOND_WIND:
        # SecondWind.OnPlay: exhausts every non-Attack card still in hand, gaining 5 block
        # (ValueProp.Move, so Frail doesn't reduce it) per card exhausted this way.
        non_attacks = tuple(value for value in combat.hand if card_name(value) not in ATTACKS)
        remaining = tuple(value for value in combat.hand if card_name(value) in ATTACKS)
        block = 5 * len(non_attacks)
        combat = replace(combat, hand=remaining, exhaust_pile=combat.exhaust_pile + non_attacks)
        combat = _grant_block(combat, block, rng, vambrace_double=vambrace_double, unmovable_double=unmovable_double, apply_frail=False)
        return _after_exhaust(combat, non_attacks, rng, data)
    if card == STONE_ARMOR:
        return replace(combat, player_powers=_add_power(combat.player_powers, "PlatingPower", 6 if card_was_upgraded else 4))
    # StratagemPower.AfterShuffle: each time the player's draw pile is shuffled the player picks the
    # power's amount of cards from the draw pile into hand.  Nothing consumes the stack, so it fires on
    # every later shuffle too.  Like the other untargeted Powers this returns without touching a pile.
    if card == STRATAGEM:
        return replace(combat, player_powers=_add_power(combat.player_powers, "StratagemPower", 1))
    if card == FEEL_NO_PAIN:
        return replace(combat, player_powers=_add_power(combat.player_powers, "FeelNoPainPower", 4 if card_was_upgraded else 3))
    if card == VICIOUS:
        return replace(combat, player_powers=_add_power(combat.player_powers, "ViciousPower", 2 if card_was_upgraded else 1))
    if card == MAD_SCIENCE:
        # MadScience.OnPlay switches on the copy's TinkerTimeType, then applies its RiderEffect.
        # The bridge reports both, and DynamicVars already carry this copy's scaled Damage/Block.
        variant = played_value.variant if isinstance(played_value, Card) else None
        rider = played_value.rider if isinstance(played_value, Card) else None
        amount = played_value.variant_value if isinstance(played_value, Card) else 0
        enemies = list(combat.enemies)
        player_powers = combat.player_powers
        if variant == "Attack" and target is not None:
            index = int(target)
            hits = 3 if rider == "Violence" else 1
            for _ in range(hits):
                if enemies[index].alive:
                    enemies[index] = _damage_enemy(enemies[index], amount + _power(player_powers, "StrengthPower"))
            combat = replace(combat, enemies=tuple(enemies))
        elif variant == "Skill":
            combat = _grant_block(combat, amount, rng)
        elif variant == "Power" and rider == "Expertise":
            player_powers = _add_power(player_powers, "StrengthPower", 2)
            player_powers = _add_power(player_powers, "DexterityPower", 2)
            combat = replace(combat, player_powers=player_powers)
        # Riders that stack on top of whichever half ran above. Chaos adds a random free card to
        # hand, which the model cannot name, so it is left out - a safe-direction omission.
        enemies, player_powers = list(combat.enemies), combat.player_powers
        if rider == "Sapping" and target is not None:
            index = int(target)
            enemies[index] = replace(enemies[index], powers=_add_power(_add_power(enemies[index].powers, "WeakPower", 2), "VulnerablePower", 2))
            combat = replace(combat, enemies=tuple(enemies))
        elif rider == "Choking" and target is not None:
            index = int(target)
            enemies[index] = replace(enemies[index], powers=_add_power(enemies[index].powers, "StranglePower", 6))
            combat = replace(combat, enemies=tuple(enemies))
        elif rider == "Energized":
            combat = replace(combat, energy=combat.energy + 2)
        elif rider == "Wisdom":
            combat = _draw_into_combat(combat, 3, data, rng)
        return combat
    if card == CASCADE:
        # Cascade.OnPlay: AutoPlayFromDrawPile(X, Top) - X cards off the draw pile are played for
        # free (X + 1 when upgraded), without being forced to exhaust. This model keeps the draw
        # pile unordered, so "top" is the same random pick _draw makes.
        return _autoplay_from_draw_pile(combat, whirlwind_x + (1 if card_was_upgraded else 0), data, rng)
    if card in {SECRET_WEAPON, INFLAME, PRIMAL_FORCE, INFERNO, CRUELTY, BLOODLETTING, NOT_YET, OFFERING, DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE, BELIEVE_IN_YOU, RUPTURE, ENLIGHTENMENT, INFERNAL_BLADE, BARRICADE, PYRE, UNMOVABLE, EXPECT_A_FIGHT, AGGRESSION, DARK_EMBRACE, CRIMSON_MANTLE, FORGOTTEN_RITUAL, HELLRAISER, FASTEN, DEMON_FORM, STAMPEDE, JUGGERNAUT, JUGGLING, PANACHE, ONE_TWO_PUNCH}:
        return combat
    enemies = list(combat.enemies)
    if card == TAUNT:
        base = 7 + (1 if card_was_upgraded else 0)
        enemy = enemies[int(target)]
        vulnerable = 1 * (2 if lamp_double else 1)
        enemies[int(target)] = _apply_enemy_debuff(enemy, "VulnerablePower", vulnerable)
        combat = _grant_block(combat, base, rng, vambrace_double=vambrace_double, unmovable_double=unmovable_double)
        return replace(combat, enemies=tuple(enemies))
    if card == PACTS_END and len(exhaust_before) < PACTS_END_EXHAUST_REQUIRED:
        # PactsEnd.OnPlay only attacks while CanDealDamage - the exhaust pile must already hold
        # at least its Cards value. Below that it is a 0-cost card that does nothing at all.
        return combat
    if card in ALL_ENEMY_DAMAGE or card == WHIRLWIND:
        damage = (whirlwind_damage if card == WHIRLWIND else ALL_ENEMY_DAMAGE[card]) + _power(combat.player_powers, "StrengthPower") + _power(combat.player_powers, "ReptileTrinketPower")
        combat, vigor = _spend_vigor(combat)
        damage += vigor
        if card_was_upgraded:
            damage += ALL_ENEMY_UPGRADE_DAMAGE.get(card, 3)
        if pen_nib_double:
            damage *= 2
        before = list(enemies)
        hits = ALL_ENEMY_HITS.get(card, 1) + (ALL_ENEMY_UPGRADE_HITS.get(card, 0) if card_was_upgraded else 0)
        for index, enemy in enumerate(enemies):
            if not enemy.alive:
                continue
            for _ in range(hits):
                if not enemies[index].alive:
                    break
                target_enemy = enemies[index]
                scaled = _apply_debuff_multipliers(combat, target_enemy, damage)
                enemies[index] = _damage_enemy(target_enemy, scaled)
        if card == THUNDERCLAP:
            for index, enemy in enumerate(enemies):
                if enemy.alive:
                    vulnerable = 2 if lamp_double else 1
                    enemies[index] = _apply_enemy_debuff(enemy, "VulnerablePower", vulnerable)
        for before_index, (before_enemy, after_enemy) in enumerate(zip(before, enemies)):
            if before_enemy.model == "MONSTER.PHROG_PARASITE" and before_enemy.alive and not after_enemy.alive:
                enemies += _spawn_wrigglers(data, rng)
            elif (
                before_enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT")
                and before_enemy.alive and not after_enemy.alive
                and not _decimillipede_teammates_dead(before, before_index)
            ):
                # ReattachPower.AfterDeath: SetMoveImmediate(DeadState) instead of leaving
                # combat - see _enemy_turn for the DEAD_MOVE -> REATTACH_MOVE revival.
                enemies[before_index] = replace(after_enemy, move="DEAD_MOVE")
        # ThornsPower.BeforeDamageReceived: every powered attack against a Thorns-holding enemy
        # reflects the stack's amount back at the attacker, before block, once per enemy hit.
        reflected = sum(_power(enemy.powers, "ThornsPower") for enemy in before if enemy.alive)
        # PersonalHivePower.AfterDamageReceived (Entomancer): every powered attack against a
        # holder inserts Amount Dazed cards into the draw pile at a random position - since
        # _draw() already pops randomly from draw_pile, appending is equivalent.
        hive = sum(_power(enemy.powers, "PersonalHivePower") for enemy in before if enemy.alive)
        _apply_curl_up(tuple(before), enemies, card)
        combat = replace(combat, enemies=tuple(enemies))
        combat = _apply_reflected_damage(combat, reflected)
        return replace(combat, draw_pile=combat.draw_pile + (DAZED,) * hive)
    if card == TREMBLE:
        enemy = enemies[int(target)]
        vulnerable = 6 if lamp_double else 3
        enemies[int(target)] = _apply_enemy_debuff(enemy, "VulnerablePower", vulnerable)
        return replace(combat, enemies=tuple(enemies))
    if card == DOMINATE:
        # Apply 1 Vulnerable, then gain Strength equal to the target's (post-apply) Vulnerable.
        enemy = enemies[int(target)]
        vulnerable = 2 if lamp_double else 1
        artifact = _power(enemy.powers, "ArtifactPower")
        enemies[int(target)] = _apply_enemy_debuff(enemy, "VulnerablePower", vulnerable)
        gained = 0 if artifact else _power(enemies[int(target)].powers, "VulnerablePower")
        return replace(combat, enemies=tuple(enemies), player_powers=_add_power(combat.player_powers, "StrengthPower", gained))
    if card == SWORD_BOOMERANG:
        damage = 3 + _power(combat.player_powers, "StrengthPower") + _power(combat.player_powers, "ReptileTrinketPower")
        if pen_nib_double:
            damage *= 2
        before = tuple(enemies)
        reflected, hive = 0, 0
        for _ in range(4 if card_was_upgraded else 3):
            alive = [index for index, candidate in enumerate(enemies) if candidate.alive]
            if not alive:
                break
            hit = rng.choice(alive)
            before_enemy = enemies[hit]
            scaled = _apply_debuff_multipliers(combat, before_enemy, damage)
            enemies[hit] = _damage_enemy(before_enemy, scaled)
            reflected += _power(before_enemy.powers, "ThornsPower")
            hive += _power(before_enemy.powers, "PersonalHivePower")
        for index, (before_enemy, after_enemy) in enumerate(zip(before, enemies)):
            if not (before_enemy.alive and not after_enemy.alive):
                continue
            for partner_index, partner in enumerate(enemies):
                if partner.alive and _power(partner.powers, "CrabRagePower"):
                    enemies[partner_index] = replace(partner, block=partner.block + 99, powers=_add_power(_add_power(partner.powers, "CrabRagePower", -1), "StrengthPower", 6))
            if before_enemy.model == "MONSTER.PHROG_PARASITE":
                enemies += _spawn_wrigglers(data, rng)
            elif before_enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT") and not _decimillipede_teammates_dead(tuple(enemies), index):
                enemies[index] = replace(enemies[index], move="DEAD_MOVE")
        _apply_curl_up(before, enemies, card)
        combat = replace(combat, enemies=tuple(enemies))
        combat = _apply_reflected_damage(combat, reflected)
        return replace(combat, draw_pile=combat.draw_pile + (DAZED,) * hive)
    if card == VOLLEY:
        damage = 14 if card_was_upgraded else 10
        damage += _power(combat.player_powers, "StrengthPower") + _power(combat.player_powers, "ReptileTrinketPower")
        if pen_nib_double:
            damage *= 2
        before = tuple(enemies)
        reflected, hive = 0, 0
        for _ in range(volley_x):
            alive = [index for index, candidate in enumerate(enemies) if candidate.alive]
            if not alive:
                break
            hit = rng.choice(alive)
            before_enemy = enemies[hit]
            scaled = _apply_debuff_multipliers(combat, before_enemy, damage)
            enemies[hit] = _damage_enemy(before_enemy, scaled)
            reflected += _power(before_enemy.powers, "ThornsPower")
            hive += _power(before_enemy.powers, "PersonalHivePower")
        for index, (before_enemy, after_enemy) in enumerate(zip(before, enemies)):
            if not (before_enemy.alive and not after_enemy.alive):
                continue
            for partner_index, partner in enumerate(enemies):
                if partner.alive and _power(partner.powers, "CrabRagePower"):
                    enemies[partner_index] = replace(partner, block=partner.block + 99, powers=_add_power(_add_power(partner.powers, "CrabRagePower", -1), "StrengthPower", 6))
            if before_enemy.model == "MONSTER.PHROG_PARASITE":
                enemies += _spawn_wrigglers(data, rng)
            elif before_enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT") and not _decimillipede_teammates_dead(tuple(enemies), index):
                enemies[index] = replace(enemies[index], move="DEAD_MOVE")
        _apply_curl_up(before, enemies, card)
        combat = replace(combat, enemies=tuple(enemies))
        combat = _apply_reflected_damage(combat, reflected)
        return replace(combat, draw_pile=combat.draw_pile + (DAZED,) * hive)
    before = tuple(enemies)
    enemy = enemies[int(target)]
    if card == SPITE:
        hits = 3 if card_was_upgraded and combat.lost_hp_this_turn else 2 if combat.lost_hp_this_turn else 1
    elif card == PECK:
        hits = 4 if card_was_upgraded else 3
    elif card == TEAR_ASUNDER:
        # CalculatedHits: one hit, plus one per unblocked-damage event taken this combat.
        hits = 1 + combat.unblocked_hits
    else:
        hits = fiend_fire_count if card == FIEND_FIRE else CARD_HITS.get(card, 1)
        if card == DISMANTLE and _power(enemy.powers, "VulnerablePower"):
            # Dismantle.OnPlay: hitCount = target.HasPower<VulnerablePower>() ? 2 : 1 - two separate
            # attacks, each with its own rounding, block absorption, and Slippery decrement.
            hits = 2
    if play_duplicated:
        hits *= 2
    if card == PERFECTED_STRIKE:
        strikes = sum(
            1 for value in combat.hand + combat.draw_pile + combat.discard_pile + combat.exhaust_pile
            if card_name(value) in STRIKE_TAGGED
        )
        damage = 6 + (3 if card_was_upgraded else 2) * strikes
    elif card == ASHEN_STRIKE:
        damage = 6 + 3 * len(exhaust_before)
    elif card == MIND_BLAST:
        damage = len(combat.draw_pile)
    elif card == BODY_SLAM:
        damage = combat.player_block
    elif card == FIEND_FIRE:
        damage = 7
    elif card in {MAUL, THRASH}:
        # Both cards raise their own Damage BaseValue permanently, and that growth survives the
        # fight, so a copy met mid-run already hits harder than its printed 5/4. The bridge's
        # `vars` cannot supply the real number: DamageVar.UpdateCardPreview runs the whole
        # ModifyDamage hook chain, so the reported Damage already has Strength, Weak, Frail and
        # enchantments folded in - reading it here would double-count everything below. The model
        # therefore starts from the printed value and only adds the growth it sees itself, which
        # under-rates a long-carried copy rather than over-rating one.
        damage = CARD_DAMAGE[card] + (CARD_UPGRADE_DAMAGE[card] if card_was_upgraded else 0)
        damage += combat.maul_bonus if card == MAUL else combat.thrash_bonus
    else:
        damage = 4 + 2 * _power(enemy.powers, "VulnerablePower") if card == BULLY else CARD_DAMAGE[card]
    if card_was_upgraded and card not in {UPPERCUT, SPITE, PECK, PERFECTED_STRIKE, BODY_SLAM, MAUL, THRASH}:
        damage += CARD_UPGRADE_DAMAGE.get(card, 3)
    if isinstance(played_value, Card) and played_value.enchantment == ENCHANTMENT_TEZCATARAS_EMBER and card in ATTACKS:
        damage += 3
    if isinstance(played_value, Card) and played_value.enchantment == ENCHANTMENT_CORRUPTED and card in ATTACKS:
        damage = damage * 3 // 2
    damage += _power(combat.player_powers, "StrengthPower") + _power(combat.player_powers, "ReptileTrinketPower")
    combat, vigor = _spend_vigor(combat)
    damage += vigor
    # StrikeDummy.ModifyDamageAdditive: +3 on any powered attack tagged Strike.
    if RELIC_STRIKE_DUMMY in combat.player_relics and card in STRIKE_TAGGED:
        damage += 3
    if pen_nib_double:
        damage *= 2
    if gigantified:
        # GigantificationPower marks exactly one powered Attack command per play (the first one on
        # the turn) and multiplies that command's damage by 3.
        damage = damage * 3
    base_damage = damage
    damage = _apply_debuff_multipliers(combat, enemy, damage)
    # OnPlay deals the damage and applies its own debuffs in the same resolution (Bash, Break, Squash,
    # Uppercut), so a play that resolves more than once has its later hits amplified by the Vulnerable the
    # earlier resolution applied.  Deal the hit, re-apply that resolution's debuffs, and price the remaining
    # hits from the target's new state.  The last resolution's debuffs go in below with the other
    # end-of-play effects, so the total stays one grant per resolution.
    resolution_debuffs = _card_resolution_debuffs(card, card_was_upgraded)
    for hit_index in range(hits):
        if not enemies[int(target)].alive:
            break
        enemies[int(target)] = _damage_enemy(enemies[int(target)], damage)
        if resolution_debuffs and hit_index + 1 < hits:
            state = enemies[int(target)]
            for power_name, amount in resolution_debuffs:
                state = _apply_enemy_debuff(state, power_name, amount * (2 if lamp_double else 1))
            enemies[int(target)] = state
            damage = _apply_debuff_multipliers(combat, enemies[int(target)], base_damage)
    if card == MOLTEN_FIST and enemies[int(target)].alive:
        vulnerable = _power(enemy.powers, "VulnerablePower")
        if vulnerable:
            enemies[int(target)] = _apply_enemy_debuff(enemies[int(target)], "VulnerablePower", vulnerable * (2 if lamp_double else 1))
    if card == MANGLE and enemies[int(target)].alive:
        amount = 15 if card_was_upgraded else 10
        enemies[int(target)] = replace(
            enemies[int(target)],
            powers=_add_power(
                _add_power(enemies[int(target)].powers, "StrengthPower", -amount),
                "ManglePower",
                amount,
            ),
        )
    if card == MAUL:
        combat = replace(combat, maul_bonus=combat.maul_bonus + (2 if card_was_upgraded else 1))
    if card == THRASH:
        attacks = [index for index, value in enumerate(hand) if card_name(value) in ATTACKS]
        if attacks:
            exhausted = hand.pop(attacks[rng.randrange(len(attacks))])
            gained = _thrash_gain(exhausted)
            combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (exhausted,), thrash_bonus=combat.thrash_bonus + gained)
            combat = _after_exhaust(combat, (exhausted,), rng, data)
    if card == CINDER and hand:
        sacrificed = hand.pop(rng.randrange(len(hand)))
        combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (sacrificed,))
        combat = _after_exhaust(combat, (sacrificed,), rng, data)
    player_powers = combat.player_powers
    if card == FIGHT_ME:
        player_powers = _add_power(player_powers, "StrengthPower", 4 if card_was_upgraded else 3)
        enemies[int(target)] = replace(
            enemies[int(target)],
            powers=_add_power(enemies[int(target)].powers, "StrengthPower", 1),
        )
    if card == SALVO:
        player_powers = _add_power(player_powers, "RetainHandPower", 1)
    if card == SETUP_STRIKE:
        amount = 3 if card_was_upgraded else 2
        player_powers = _add_power(_add_power(player_powers, "StrengthPower", amount), "SetupStrikePower", amount)
    if _power(player_powers, "SurroundedRight") and _power(enemy.powers, "BackAttackLeftPower"):
        player_powers = _add_power(_add_power(player_powers, "SurroundedRight", -1), "SurroundedLeft", 1)
    elif _power(player_powers, "SurroundedLeft") and _power(enemy.powers, "BackAttackRightPower"):
        player_powers = _add_power(_add_power(player_powers, "SurroundedLeft", -1), "SurroundedRight", 1)
    if card in CARD_VULNERABLE_TARGET:
        # The earlier resolutions already applied their grant inside the hit loop above, so this one adds
        # the grant for the last resolution only.  These cards hit once per resolution, so hits == play count.
        vulnerable = (CARD_VULNERABLE_TARGET[card] + (1 if card in {BASH, SQUASH} and card_was_upgraded else 0)) * (2 if lamp_double else 1)
        enemies[int(target)] = _apply_enemy_debuff(enemies[int(target)], "VulnerablePower", vulnerable)
    if card == UPPERCUT:
        # The status application is part of the play, so each resolution applies it again.  The earlier
        # resolutions were handled inside the hit loop, leaving this one for the last resolution.
        plays = 1
        weak = (1 + (1 if card_was_upgraded else 0)) * plays
        enemy = _apply_enemy_debuff(enemies[int(target)], "WeakPower", weak * (2 if lamp_double else 1))
        vulnerable = 1 * (2 if lamp_double else 1) * plays
        enemy = _apply_enemy_debuff(enemy, "VulnerablePower", vulnerable)
        if card_was_upgraded:
            enemy = _apply_enemy_debuff(enemy, "VulnerablePower", vulnerable)
        enemies[int(target)] = enemy
    if card == NEOWS_FURY and combat.discard_pile:
        # NeowsFury.OnPlay: after the hit, move up to Cards (2, upgraded 3) cards from the discard
        # pile into hand, capped by the space left in a 10-card hand. The real card lets the player
        # pick; the model takes the most recent cards that are not junk, which is the choice a
        # player would make without modelling a full card-value function.
        # ponytail: "not junk" is EXHAUST_FODDER; upgrade to a value-ranked pick if this card ever
        # looks mis-valued in a trace.
        wanted = (3 if card_was_upgraded else 2)
        room = max(0, 10 - len(combat.hand))
        discard, taken = list(combat.discard_pile), []
        for index in range(len(discard) - 1, -1, -1):
            if len(taken) >= min(wanted, room):
                break
            if card_name(discard[index]) in EXHAUST_FODDER:
                continue
            taken.append(discard.pop(index))
        combat = replace(combat, hand=combat.hand + tuple(taken), discard_pile=tuple(discard))
    if card == HEADBUTT and combat.discard_pile:
        discard = list(combat.discard_pile)
        selected = discard.pop(rng.randrange(len(discard)))
        combat = replace(combat, draw_pile=combat.draw_pile + (selected,), discard_pile=tuple(discard))
    if card == ANGER:
        combat = replace(combat, discard_pile=combat.discard_pile + (_copy_card(ANGER, played_value),))
    if card == PILLAGE:
        # Draw until a non-Attack card comes up (Pillage's do/while); each drawn card stays in hand.
        drawn_hand = list(combat.hand)
        while True:
            draw_pile, discard_pile = combat.draw_pile, combat.discard_pile
            if not (draw_pile or discard_pile):
                break
            one, draw_pile, discard_pile = _draw(draw_pile, discard_pile, 1, rng)
            if not one:
                break
            drawn_hand += one
            combat = replace(combat, hand=tuple(drawn_hand), draw_pile=draw_pile, discard_pile=discard_pile)
            combat = _autoplay_drawn_strikes(combat, one, data, rng)
            drawn_hand = list(combat.hand)
            if card_name(one[0]) not in ATTACKS:
                break
    if enemy.alive and not enemies[int(target)].alive:
        for index, partner in enumerate(enemies):
            if partner.alive and _power(partner.powers, "CrabRagePower"):
                enemies[index] = replace(partner, block=partner.block + 99, powers=_add_power(_add_power(partner.powers, "CrabRagePower", -1), "StrengthPower", 6))
        if enemy.model == "MONSTER.PHROG_PARASITE":
            enemies += _spawn_wrigglers(data, rng)
        elif enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT") and not _decimillipede_teammates_dead(enemies, int(target)):
            # ReattachPower.AfterDeath: SetMoveImmediate(DeadState) instead of leaving combat -
            # see _enemy_turn for the DEAD_MOVE -> REATTACH_MOVE revival.
            enemies[int(target)] = replace(enemies[int(target)], move="DEAD_MOVE")
    # ThornsPower.BeforeDamageReceived (e.g. Spiny Toad's PROTRUDING_SPIKES_MOVE): reflects the
    # stack's amount back at the attacker, before block, on every powered attack against it.
    reflected = _power(enemy.powers, "ThornsPower") * hits
    # PersonalHivePower.AfterDamageReceived (Entomancer): every powered attack against a holder
    # inserts Amount Dazed cards into the draw pile at a random position.
    hive = _power(enemy.powers, "PersonalHivePower")
    _apply_curl_up(before, enemies, card)
    combat = replace(combat, player_powers=player_powers, enemies=tuple(enemies))
    if card == FEED and enemy.alive and not enemies[int(target)].alive:
        # Feed.cs: the Attack is Fatal (shouldTriggerFatal = target.Powers.All(p => p.ShouldOwnerDeathTriggerFatal()))
        # and a Fatal kill runs CreatureCmd.GainMaxHp(Owner, MaxHp) - MaxHpVar(3), upgraded 4 - which raises
        # max HP and current HP by the same amount (traces show hp 54 -> 57 with max_hp 80 -> 83, and
        # hp 63 -> 66 with max_hp 101 -> 104).  Without this the rollout prices Feed as a plain 10 damage
        # attack and scores the kill 3 HP worse than the game values it.  The game gates the gain on the
        # target's powers allowing a Fatal death; the model takes any kill, which is the approximation to
        # revisit if a Fatal-immune holder shows up in a trace.
        gained = 4 if card_was_upgraded else 3
        combat = replace(combat, player_max_hp=combat.player_max_hp + gained, player_hp=combat.player_hp + gained)
    combat = _apply_reflected_damage(combat, reflected)
    return replace(combat, draw_pile=combat.draw_pile + (DAZED,) * hive)


def _thrash_gain(value: CardValue) -> int:
    """Damage Thrash absorbs from the attack it exhausts (its Damage var, not its full effect)."""
    name = card_name(value)
    damage = CARD_DAMAGE.get(name, ALL_ENEMY_DAMAGE.get(name, 0))
    if isinstance(value, Card) and value.upgraded and damage:
        damage += CARD_UPGRADE_DAMAGE.get(name, 3)
    return damage


def _step_score(combat: Combat, state: Combat, data: dict) -> float:
    """Score a single step: prevented damage + damage dealt - self-damage + effective block."""
    incoming = sum(_enemy_attack_damage(enemy, data, combat.player_powers) for enemy in combat.enemies if enemy.alive)
    exposed = max(0, incoming - combat.player_block)
    prevented = sum(
        _enemy_attack_damage(before, data, combat.player_powers)
        for before, after in zip(combat.enemies, state.enemies)
        if before.alive and not after.alive and not after.escaped
    )
    # Killing the primary enemy (the boss) wins the fight; credit its remaining HP so a
    # boss kill outranks killing a reviving minion.
    prevented += sum(max(0, before.hp) for before, after in zip(combat.enemies, state.enemies) if before.alive and before.primary and not after.alive and not after.escaped)
    # Cap damage at each enemy's remaining HP so overkill is not overvalued.
    dealt = sum(
        (max(0, before.hp) - max(0, after.hp)) * (
            1 if before.primary else 1.5 if after.hp <= 0 and _enemy_attack_damage(before, data, combat.player_powers) >= 4 else 0.5
        )
        for before, after in zip(combat.enemies, state.enemies)
        if before.alive and not after.escaped
    )
    dealt -= max(0, combat.player_hp - state.player_hp)  # penalize self-damage
    # Debuffs that survive the card play reduce the next enemy phase. Exclude kills here because
    # their attack is already credited by `prevented` above.
    threat_reduced = sum(
        max(
            0,
            _enemy_attack_damage(before, data, combat.player_powers)
            - _enemy_attack_damage(after, data, state.player_powers),
        )
        for before, after in zip(combat.enemies, state.enemies)
        if before.alive and after.alive
    )
    # Stripping Slippery enables full damage on later hits; credit each strip so the
    # policy keeps attacking Slippery bosses (e.g. VANTOM) instead of only blocking.
    dealt += sum(max(0, _power(before.powers, "SlipperyPower") - _power(after.powers, "SlipperyPower")) for before, after in zip(combat.enemies, state.enemies) if before.alive)
    blocked = state.player_block - combat.player_block
    # Sandpit upkeep (The Insatiable): sand drops by 1 every enemy turn and hitting 1 sinks the
    # player instantly, so Frantic Escape is worth an incoming hit when the pit is about to give
    # out (sand <= 3), but a no-op when sand is plentiful - attacking then would waste damage.
    sandpit_before = max((_power(enemy.powers, "SandpitPower") for enemy in combat.enemies if enemy.alive), default=0)
    sandpit_after = max((_power(enemy.powers, "SandpitPower") for enemy in state.enemies if enemy.alive), default=0)
    upkeep = (sandpit_after - sandpit_before) * 15 if 0 < sandpit_after <= 3 else 0
    # Cards that only draw (Battle Trance, Drum of Battle, ...) score 0 on every other term, so
    # without this they get played dead last - after energy is already spent on whatever scored
    # positive, wasting the extra options they were supposed to unlock this same turn. The bonus
    # is well below a single point of real damage/block so it only breaks ties among zero-score
    # plays, never outranks an actual attack or block. Guarded to real card plays (state.turn ==
    # combat.turn) since this is also called for End turn's own immediate score in search().
    drawn = len(state.hand) - (len(combat.hand) - 1) if state.turn == combat.turn else 0
    return prevented + dealt + threat_reduced + min(blocked, exposed) + upkeep + 0.3 * max(0, drawn)


def _projected_attack_value(combat: Combat, card: CardValue) -> int:
    """Estimate this turn's damage if a setup card has already been played."""
    name = card_name(card)
    alive = sum(enemy.alive for enemy in combat.enemies)
    strength = _power(combat.player_powers, "StrengthPower")
    if name == WHIRLWIND:
        return max(0, combat.energy) * alive * (5 + strength)
    if name == VOLLEY:
        return max(0, combat.energy) * (CARD_DAMAGE[VOLLEY] + strength)
    if name == SWORD_BOOMERANG:
        return (3 + strength) * (4 if card_is_upgraded(combat, card) else 3)
    hits = 1 + combat.unblocked_hits if name == TEAR_ASUNDER else CARD_HITS.get(name, 1)
    if name in ALL_ENEMY_DAMAGE:
        return ALL_ENEMY_DAMAGE[name] * alive * hits + strength * alive * hits
    return (CARD_DAMAGE.get(name, 0) + strength) * hits


def _setup_bonus(combat: Combat, state: Combat, card: CardValue, data: dict) -> int:
    """Prefer setup before attacks when the same turn can actually spend the payoff."""
    name = card_name(card)
    incoming = sum(_enemy_attack_damage(enemy, data, combat.player_powers) for enemy in combat.enemies if enemy.alive)
    if incoming >= state.player_hp + state.player_block or _power(state.player_powers, "RingingPower"):
        return 0
    if name == BLOODLETTING and any(card_name(value) == WHIRLWIND for value in state.hand):
        return _projected_attack_value(state, WHIRLWIND)
    if name == INFLAME:
        attacks = sorted(
            (value for value in state.hand if card_name(value) in ATTACKS and card_name(value) != WHIRLWIND),
            key=lambda value: 0 if value in state.free_cards else _effective_cost(state, value),
        )
        energy, selected = state.energy, []
        for value in attacks:
            cost = 0 if value in state.free_cards else _effective_cost(state, value)
            if cost > energy:
                break
            selected.append(value)
            energy -= cost
        if len(selected) >= 2:
            return sum(_projected_attack_value(state, name) for name in selected)
    return 0


def _action_card(combat: Combat, action: str) -> CardValue:
    token = action.partition("@")[0]
    return combat.hand[int(token[5:])] if token.startswith("card:") else token


def _greedy_action(combat: Combat, data: dict) -> str:
    """Pick a card action by prevented damage + damage dealt; block counts against incoming."""
    actions = legal_actions(combat)[:-1]  # exclude End turn
    if not actions:
        return END_TURN
    best, best_score = None, None
    incoming = sum(_enemy_attack_damage(enemy, data, combat.player_powers) for enemy in combat.enemies if enemy.alive)
    for action in actions:
        state = step(combat, action, data, random.Random(0))
        # Skip actions that kill the player unless they win the fight outright.
        if state.player_hp <= 0 and any(enemy.alive for enemy in state.enemies):
            continue
        # The same rule must hold for the enemy phase: a line that cannot survive the incoming hit
        # is a loss, so it must not outscore a line that survives. search() prices this because its
        # rollout runs the enemy turn, but _greedy_action scored only the play, so a buff or attack
        # beat the block card that keeps the player alive. Death is applied as a penalty, not a skip,
        # so among doomed lines the one that still deals damage stays preferred.
        doomed = any(enemy.alive for enemy in state.enemies) and state.player_hp - max(0, incoming - state.player_block) <= 0
        score = _step_score(combat, state, data)
        card_value = _action_card(combat, action)
        card = card_name(card_value)
        # Vulnerability applies (Bash/Tremble) strengthen later attacks by 50%; credit
        # that so they are played before the attacks they boost.
        if card in {BASH, TREMBLE}:
            score += sum(CARD_DAMAGE.get(card_name(value), 0) // 2 for value in state.hand if card_name(value) in ATTACKS and card_name(value) != card and CARD_COST.get(card_name(value), 99) <= state.energy)
        # Drawing is worth what the extra options are worth, and search() already prices that in:
        # its rollout plays the rest of the turn out of the bigger hand and the better line shows up
        # as final HP. _step_score must therefore NOT pay for it again - crediting it there once
        # cost 6 fights on P3V8N5K2RX by double-counting into search()'s own immediate term.
        #
        # This scorer is the part that is genuinely blind: search() only chooses the FIRST move of a
        # turn and _greedy_action plays every move after it, one ply at a time. A draw card scores 0
        # on damage and block, so here - and only here - it lost to anything dealing a single point
        # and got played once the energy was already gone, arriving with nothing left to spend on
        # what it drew. Measured across every recorded trace, that happened on 501 turns for Battle
        # Trance and 162 for Inflame under `rollout_success`.
        #
        # The credit is bounded by the energy still left after the play, so a draw card taken when
        # the bar is empty - exactly the late play this is meant to stop - still scores 0. Hand-cap
        # overflow and a draw wasted under NoDraw need no special case: `drawn` measures the hand
        # growth that actually happened.
        drawn = len(state.hand) - (len(combat.hand) - 1)
        if drawn > 0:
            score += GREEDY_DRAW_VALUE * min(drawn, max(0, state.energy))
        score += _setup_bonus(combat, state, card_value, data)
        if doomed:
            score -= GREEDY_DEATH_PENALTY
        if best_score is None or score > best_score:
            best, best_score = action, score
    return best if best is not None else END_TURN


def search(combat: Combat, data: dict, simulations: int = 5000, seed: int = 0) -> list[tuple[str, float]]:
    rng = random.Random(seed)
    results = []
    for action in legal_actions(combat):
        scores = []
        for _ in range(max(1, simulations // len(legal_actions(combat)))):
            state = step(combat, action, data, rng)
            # Credit this move's own effect (damage dealt, kills, block against incoming) the
            # same way _greedy_action scores every later turn - otherwise a genuinely useful
            # first move (e.g. Defend into a real attack) can lose to noise from 60 turns of
            # rollout whose outcome is dominated by draw/enemy RNG, not by this one decision
            # (observed: VANTOM's Slippery opening scored "End turn" above "Defend").
            card_value = _action_card(combat, action)
            # End turn has no effect of its own, but stepping it also runs the whole enemy turn,
            # so _step_score would hand it the block absorption and kill credit for a turn it did
            # not act in - block that was already standing before the decision. That made ending
            # the turn outscore a free Strike whenever any block was up (astra_goal_thin1 seq94:
            # End turn +10 vs Strike +6, while the Strike's rollouts ended 1.5 HP higher). Only
            # the rollout's own outcome should speak for End turn.
            # A first move that kills the player outright gets no credit for whatever block or
            # damage it produced on the way, and is scored below every other loss: the rollouts
            # may all lose, but only this line forecloses the fight on the spot.
            self_killed = action != END_TURN and state.player_hp <= 0
            immediate = 0.0 if action == END_TURN or state.player_hp <= 0 else (
                _step_score(combat, state, data) + _setup_bonus(combat, state, card_value, data)
            ) / 100
            for _ in range(60):
                if state.terminal:
                    break
                state = step(state, _greedy_action(state, data), data, rng)
            # An enemy that fled (e.g. Thieving Hopper) ends the fight but is NOT a win.
            won = (
                state.player_hp > 0
                and not any(
                    (enemy.alive or (enemy.model == TEST_SUBJECT and enemy.move == RESPAWN_MOVE)) and enemy.primary
                    for enemy in state.enemies
                )
                and not any(enemy.escaped and enemy.primary for enemy in state.enemies)
            )
            # Win/loss dominates; HP and the immediate-move score break ties so noisy rollouts still rank correctly.
            # The real game floors HP at 0, but _apply_player_damage lets it go negative. Without
            # the clamp a lost position ranks "die now at exactly 0" above "die later at -23", and
            # a move whose own self-damage is lethal outscores every alternative (astra_goal_scarf1
            # seq463: at 2 HP the search played Blood Wall for its 2 self-damage and killed itself
            # rather than block with Toric Toughness).
            scored_hp = max(0, state.player_hp)
            if won and RELIC_MEAT_ON_THE_BONE in state.player_relics and state.player_max_hp > 0 and scored_hp * 2 <= state.player_max_hp:
                scored_hp = min(state.player_max_hp, scored_hp + 12)
            scores.append(
                (1 if won else -1 if state.player_hp <= 0 else 0)
                + scored_hp / 100 + immediate - (0.01 if self_killed else 0.0)
            )
        results.append((action, sum(scores) / len(scores)))
    if not results:
        return [(END_TURN, 0.0)]
    return sorted(results, key=lambda item: item[1], reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Data-driven Ironclad encounter simulation")
    parser.add_argument("enemy_json")
    parser.add_argument("encounter")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--simulations", type=int, default=5000)
    args = parser.parse_args()
    with open(args.enemy_json, encoding="utf-8-sig") as file:
        data = json.load(file)
    combat = initial_combat(data, args.encounter, random.Random(args.seed))
    print(" | ".join(f"{index}:{enemy.model} hp={enemy.hp} move={enemy.move}" for index, enemy in enumerate(combat.enemies)))
    print("hand=" + ", ".join(card_name(card) for card in combat.hand))
    for action, value in search(combat, data, args.simulations, args.seed):
        print(f"{action:16} value={value:.5f}")


if __name__ == "__main__":
    main()
