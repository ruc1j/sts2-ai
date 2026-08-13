from __future__ import annotations

import argparse
import json
import os
import time
import traceback

from combat import Combat, Enemy, search


CARD_NAMES = {
    "CARD.STRIKE_IRONCLAD": "Strike",
    "CARD.DEFEND_IRONCLAD": "Defend",
    "CARD.BASH": "Bash",
    "CARD.ANGER": "Anger",
    "CARD.BLUDGEON": "Bludgeon",
    "CARD.SHRUG_IT_OFF": "Shrug It Off",
    "CARD.BATTLE_TRANCE": "Battle Trance",
    "CARD.BULLY": "Bully",
    "CARD.DISMANTLE": "Dismantle",
    "CARD.SLIMED": "Slimed",
    "CARD.FRANTIC_ESCAPE": "Frantic Escape",
    "CARD.IRON_WAVE": "Iron Wave",
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
    "CARD.RUPTURE": "Rupture",
    "CARD.SECOND_WIND": "Second Wind",
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
        "CARD.SHRUG_IT_OFF",
    }, "A"),
    **dict.fromkeys({
        "CARD.BREAK", "CARD.AGGRESSION", "CARD.TEAR_ASUNDER", "CARD.THRASH",
        "CARD.ASHEN_STRIKE", "CARD.DISMANTLE", "CARD.EVIL_EYE", "CARD.FORGOTTEN_RITUAL",
        "CARD.SPITE", "CARD.STOMP", "CARD.UNRELENTING", "CARD.WHIRLWIND", "CARD.BREAKTHROUGH",
        "CARD.CINDER", "CARD.IRON_WAVE", "CARD.TAUNT", "CARD.TWIN_STRIKE",
        "CARD.INFLAME",  # Strength scales every attack: boss firepower (was C)
    }, "B"),
    **dict.fromkeys({
        "CARD.BRAND", "CARD.CASCADE", "CARD.DEMON_FORM", "CARD.HELLRAISER", "CARD.BULLY",
        "CARD.DRUM_OF_BATTLE", "CARD.FIGHT_ME", "CARD.HOWL_FROM_BEYOND", "CARD.INFERNAL_BLADE",
        "CARD.JUGGLING", "CARD.PILLAGE", "CARD.RAMPAGE", "CARD.RUPTURE",
        "CARD.STAMPEDE", "CARD.STONE_ARMOR", "CARD.VICIOUS", "CARD.ARMAMENTS", "CARD.BODY_SLAM",
        "CARD.HAVOC", "CARD.MOLTEN_FIST", "CARD.PERFECTED_STRIKE", "CARD.SETUP_STRIKE",
        "CARD.SWORD_BOOMERANG", "CARD.THUNDERCLAP", "CARD.TRUE_GRIT",
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
    "POWER.SURROUNDED_POWER": "SurroundedPower",
    "POWER.ILLUSION_POWER": "IllusionPower",
    "POWER.MINION_POWER": "MinionPower",
}

KNOWN_CARD_DAMAGE = {
    "CARD.STRIKE_IRONCLAD": 6,
    "CARD.BASH": 8,
    "CARD.ANGER": 6,
    "CARD.BLUDGEON": 32,
    "CARD.DISMANTLE": 8,
    "CARD.IRON_WAVE": 5,
    "CARD.CINDER": 18,
    "CARD.HEMOKINESIS": 15,
    "CARD.UNRELENTING": 14,
    "CARD.GIANT_ROCK": 16,
    "CARD.BREAKTHROUGH": 9,
    "CARD.FEED": 10,
    "CARD.BYRD_SWOOP": 14,
    "CARD.PILLAGE": 6,
}
KNOWN_CARD_BLOCK = {
    "CARD.DEFEND_IRONCLAD": 5,
    "CARD.SHRUG_IT_OFF": 8,
    "CARD.RELAX": 15,
    "CARD.IRON_WAVE": 5,
    "CARD.EQUILIBRIUM": 13,
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


def choose_event(observation: dict) -> dict:
    actions = [action for action in observation.get("legal_actions", ()) if action.get("type") == "event_relic"]
    if not actions:
        raise ValueError("no event relic actions")
    block_starved = _block_starved(_deck_list(observation))
    player = observation.get("player", {})
    hp, max_hp = player.get("hp", 0), player.get("max_hp", 1)
    low_hp = hp <= max_hp // 2

    def score(action: dict) -> int:
        relic = action.get("relic_id", "")
        value = RELIC_SCORES.get(relic, 0)
        # Block-starved decks value the block pet even more.
        if block_starved and relic == "RELIC.PAELS_LEGION":
            value += 2
        # At low HP the turn-1 energy burst helps end fights faster.
        if low_hp and relic in {"RELIC.VERY_HOT_COCOA", "RELIC.PAELS_FLESH"}:
            value += 1
        return value

    return max(actions, key=score)


def choose(observation: dict, enemy_data: dict | None = None, simulations: int = 0) -> dict:
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
    cards = [action for action in actions if action["type"] == "card"]
    potions = [action for action in actions if action["type"] == "potion"]
    sandpit = any(power["id"] == "POWER.SANDPIT_POWER" and power["amount"] > 0 for enemy in observation.get("enemies", ()) for power in enemy.get("powers", ()))
    escape = next((action for action in cards if action["card_id"] == "CARD.FRANTIC_ESCAPE"), None)
    if sandpit and escape:
        return escape
    if turn := choose_crab_facing(observation, cards):
        return turn
    if potion := choose_potion(observation, potions):
        return potion
    # rollouts cover the modeled cards in hand; unknown cards are treated as unplayable by the
    # simulator rather than abandoning the rollout entirely (e.g. Dominate used to disable it).
    if enemy_data and simulations and any(card["card_id"] in CARD_NAMES for card in cards):
        try:
            return rollout_choice(observation, actions, enemy_data, simulations)
        except (KeyError, ValueError, NotImplementedError, StopIteration):
            pass
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

    lethal = [
        action for action in cards
        if action.get("target_id") in enemy_by_id
        and damage(action) - enemy_by_id[action["target_id"]].get("block", 0) >= enemy_by_id[action["target_id"]]["hp"]
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
    if hp <= max_hp // 2 or incoming > 0:
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
    blocking = {"POTION.BLOCK_POTION"} | ({"POTION.FORTIFIER"} if block > 0 else set())
    # Speed Potion just grants Dexterity via SpeedPotionPower - same effect as Dexterity Potion.
    defensive_buffs = {"POTION.DEXTERITY_POTION", "POTION.SPEED_POTION", "POTION.GHOST_IN_A_JAR", "POTION.REGEN_POTION", "POTION.LIQUID_BRONZE"}
    recovery = healing | defensive_buffs | {"POTION.ENTROPIC_BREW"}
    # Shackling is deliberately excluded from `debuffs` below: its -7 Strength lasts the whole
    # fight, so it is reserved for the >=100 HP boss-length branch further down rather than
    # spent reactively on any dangerous *regular* fight (e.g. a Wriggler swarm) - sim13 burned
    # Shackling on a normal encounter and had nothing left for the boss that actually needed it.
    debuffs = {"POTION.WEAK_POTION", "POTION.VULNERABLE_POTION", "POTION.POISON_POTION"}
    offensive = {
        "POTION.ATTACK_POTION", "POTION.COLORLESS_POTION", "POTION.DISTILLED_CHAOS", "POTION.DUPLICATOR",
        "POTION.EXPLOSIVE_AMPOULE", "POTION.FIRE_POTION", "POTION.FLEX_POTION", "POTION.POWER_POTION",
        "POTION.SKILL_POTION", "POTION.STRENGTH_POTION",
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
            # can fire at full HP with nothing actually wrong yet.
            if potion_id and potion_id not in known and not any(marker in potion_id for marker in ("FAIRY", "REVIV", "SNECKO", "FOUL")):
                return action
        return None
    danger = hp <= max_hp // 2 or incoming >= max(1, hp // 2) or len(enemy_hp) >= 2
    if incoming >= hp:
        return use({"POTION.LUCKY_TONIC", "POTION.GHOST_IN_A_JAR"} | blocking) or use(debuffs, enemy_damage) or use(recovery) or use(offensive, enemy_hp) or (unknown_manual() if danger else None)
    hand = observation.get("hand") or ()
    if hp <= max_hp // 2 and (len(enemy_hp) >= 2 or incoming >= hp // 2):
        if len(enemy_hp) >= 2:
            explosive = use({"POTION.EXPLOSIVE_AMPOULE"})
            if explosive:
                return explosive
        if any(card.get("cost", 1) > 0 for card in hand):
            energy = use({"POTION.ENERGY_POTION"})
            if energy:
                return energy
        return use(blocking) or use(debuffs, enemy_damage) or use(recovery) or use(offensive, enemy_hp) or (unknown_manual() if danger else None)
    if hp <= max_hp // 2:
        return use(recovery) or use(offensive, enemy_hp) or (unknown_manual() if danger else None)
    if incoming >= hp // 2:
        return use(blocking) or use(debuffs, enemy_damage) or use(offensive, enemy_hp) or (unknown_manual() if danger else None)
    if max(enemy_hp.values(), default=0) >= 100:
        # Boss-length fights: ShacklingPotionPower subclasses TemporaryStrengthPower, whose
        # AfterSideTurnEnd removes the -7 Strength (and itself) once the AFFECTED CREATURE's own
        # side-turn ends - it only blunts the enemy's very next turn, not the whole fight (a
        # prior assumption here was wrong and wasted the potion on sleeping bosses like Bygone
        # Effigy that don't attack on an early turn). Only spend it once an attack is actually
        # incoming this decision, so the -7 lands on a turn that would otherwise deal damage.
        shackling = use({"POTION.SHACKLING_POTION"}) if incoming > 0 else None
        return shackling or use({"POTION.STRENGTH_POTION", "POTION.FLEX_POTION", "POTION.POWER_POTION", "POTION.COLORLESS_POTION", "POTION.ATTACK_POTION", "POTION.SKILL_POTION", "POTION.DUPLICATOR", "POTION.DISTILLED_CHAOS", "POTION.EXPLOSIVE_AMPOULE"}) or use({"POTION.VULNERABLE_POTION", "POTION.POISON_POTION", "POTION.FIRE_POTION"}, enemy_hp) or (unknown_manual() if danger else None)
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
        # axis deals the most damage - then Perfected Strike (strike), Rupture (self-damage),
        # Corruption (exhaust).
        first = ("CARD.INFLAME", "CARD.PERFECTED_STRIKE", "CARD.RUPTURE", "CARD.CORRUPTION")
        cards = [card for card in first if available and card in available]
    if available is not None:
        cards = [card for card in cards if card in available]
    return {card: len(cards) - index for index, card in enumerate(cards)}


def choose_shop(observation: dict) -> dict:
    actions = observation.get("legal_actions", ())
    deck_ids = _deck_ids(observation)
    buys = [action for action in actions if action.get("type") == "buy_card"]
    core = _core_priority(deck_ids, {(action.get("card_id") or action.get("id")) for action in buys})
    required = [action for action in buys if (action.get("card_id") or action.get("id")) in core]
    if required:
        return max(required, key=lambda action: core[(action.get("card_id") or action.get("id"))])
    removals = [action for action in actions if action.get("type") == "remove"]
    remove_id = "CARD.DEFEND_IRONCLAD" if "CARD.PERFECTED_STRIKE" in deck_ids else "CARD.STRIKE_IRONCLAD"
    preferred = next((action for action in removals if (action.get("card_id") or action.get("id")) == remove_id), None)
    if preferred:
        return preferred
    return next((action for action in actions if action.get("type") == "skip"), actions[0] if actions else {"type": "skip"})


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
    # Route toward rest sites and avoid elites once HP drops below two thirds.
    if player.get("max_hp", 0) and player.get("hp", player["max_hp"]) * 3 <= player["max_hp"] * 2:
        rest_paths: dict[tuple[int, int], tuple[int, int] | None] = {}
        rest_visiting: set[tuple[int, int]] = set()

        def rest_path(coord: tuple[int, int]) -> tuple[int, int] | None:
            if coord in rest_paths:
                return rest_paths[coord]
            if coord in rest_visiting:
                return None
            rest_visiting.add(coord)
            point = points[coord]
            elites = point["type"] == "Elite"
            if point["type"] == "RestSite":
                rest_paths[coord] = (0, int(elites))
                rest_visiting.remove(coord)
                return rest_paths[coord]
            children = (rest_path((child["col"], child["row"])) for child in point["children"])
            reachable = [path for path in children if path is not None]
            rest_paths[coord] = None if not reachable else min((distance + 1, elite_count + elites) for distance, elite_count in reachable)
            rest_visiting.remove(coord)
            return rest_paths[coord]

        routes = [(action, rest_path((action["col"], action["row"]))) for action in observation["legal_actions"]]
        reachable = [(action, route) for action, route in routes if route is not None]
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

    def route_key(path: list[tuple[int, int]]) -> tuple[int, int, int, int, int, int]:
        types = [points[coord]["type"] for coord in path]
        return (
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


STRIKE_TAGGED_REWARDS = {"CARD.PERFECTED_STRIKE", "CARD.ASHEN_STRIKE"}

# Strength sources that scale every attack into boss firepower; once one is in the deck the
# others are prioritized so the axis keeps growing.
STRENGTH_CARDS = {"CARD.INFLAME", "CARD.PRIMAL_FORCE", "CARD.DOMINATE", "CARD.CRUELTY"}

# Cards the agent would rarely play, so taking them only bloats the deck (e.g. Relax's 3-cost
# block is too awkward for the greedy rollout to use consistently). Never pick these.
UNPLAYABLE_REWARDS = {"CARD.RELAX"}

DEFENSE_PRIORITY = {
    "CARD.IMPERVIOUS", "CARD.UNMOVABLE", "CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER",
    "CARD.BLOOD_WALL", "CARD.SECOND_WIND", "CARD.STONE_ARMOR",
    "CARD.IRON_WAVE", "CARD.TRUE_GRIT",
}

# Blocks of 8+ that can actually hold off Act 2's 28-36 hits. Defend (5), Iron Wave (5) and
# Second Wind (5) and True Grit (7) are barely better than Defend, so they do not count as
# strong when judging whether a deck can survive without more defensive picks.
STRONG_BLOCK_CARDS = {
    "CARD.IMPERVIOUS", "CARD.UNMOVABLE", "CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER",
    "CARD.BLOOD_WALL", "CARD.STONE_ARMOR",
}


def _block_starved(deck: list[str]) -> bool:
    # True when the deck needs defensive picks: block cards make up under 40% of the deck, or
    # the deck has fewer than 2 strong block cards (Shrug It Off, Flame Barrier, ...). Defend's
    # 5 block alone cannot hold off Act 2's 28-36 attacks, so a deck with only Defends is still
    # starved. sim19 died at exactly 1/3 block cards because the old 1/3 threshold never fired.
    block_cards = sum(card in DEFENSE_PRIORITY or card == "CARD.DEFEND_IRONCLAD" for card in deck)
    strong_blocks = sum(card in STRONG_BLOCK_CARDS for card in deck)
    return len(deck) >= 10 and (block_cards * 5 < len(deck) * 2 or strong_blocks < 2)


def choose_card_reward(observation: dict) -> dict:
    actions = [action for action in observation["legal_actions"] if action["type"] == "card_reward" and action["card_id"] not in UNPLAYABLE_REWARDS]
    if not actions:
        # Every offered card is unplayable (e.g. only Relax was shown): take nothing.
        return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")
    tier_score = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
    deck_ids = _deck_ids(observation)
    core = _core_priority(deck_ids, {action["card_id"] for action in actions})
    priority = {card_id: tier_score[tier] for card_id, tier in CARD_TIERS.items()}
    if _axis(deck_ids) != "self_damage":
        for card_id in UNCOMMITTED_SELF_DAMAGE:
            if card_id in priority:
                priority[card_id] -= 1
    strike_axis = _axis(deck_ids) == "strike"
    deck_list = _deck_list(observation)
    # Perfected Strike (6 + 2 per Strike) hits ~16 with the starter deck's 5 Strikes, so a
    # seed is worth taking, but every Strike-tagged card grows the deck and the boss-fight
    # verification showed PS-heavy decks deal the least damage. Feed the strike axis only
    # while it is lean (1-2 copies); afterwards the strength axis (Inflame etc.) outranks it.
    strikes = sum(card in STRIKE_TAGGED_REWARDS or card == "CARD.STRIKE_IRONCLAD" for card in deck_list)
    perfected = sum(card == "CARD.PERFECTED_STRIKE" for card in deck_list)
    if strikes >= 5 and perfected < 2:
        for card_id in STRIKE_TAGGED_REWARDS:
            if card_id in priority:
                priority[card_id] += 2
    if STRENGTH_CARDS & deck_ids:
        for card_id in STRENGTH_CARDS:
            if card_id in priority:
                priority[card_id] += 1
    # Keep the deck from becoming all-offense: once block cards are under 40% of the deck (or the
    # deck relies on weak Defends with fewer than 2 strong block cards), defensive picks (Shrug It
    # Off etc.) outrank same-tier offensive cards so Act 2 fights cost less HP.
    defense_needed = _block_starved(deck_list)
    cards = {card.get("id") or card.get("card_id"): card for card in observation.get("cards", ())}
    # A 3-energy/turn economy can only ever field so many 3+ cost cards a turn - stacking more of
    # them past a couple copies just clogs the hand with cards that sit dead, however strong each
    # one is individually. Deprioritize (not ban) further high-cost picks once the deck already
    # has HIGH_COST_CAP of them; this term sits ahead of core/tier so it overrides even a
    # deck-defining pick, matching "avoid multiple high-cost cards even if strong".
    HIGH_COST_CAP = 2
    high_cost_in_deck = sum(_number(cards.get(card_id, {}).get("cost"), 0) >= 3 for card_id in deck_list)
    over_high_cost_cap = high_cost_in_deck >= HIGH_COST_CAP

    def is_high_cost(card_id: str) -> bool:
        return _number(cards.get(card_id, {}).get("cost"), 0) >= 3

    selected = max(actions, key=lambda action: (
        0 if over_high_cost_cap and is_high_cost(action["card_id"]) else 1,
        bool(core.get(action["card_id"])), core.get(action["card_id"], 0), 2 if defense_needed and action["card_id"] in DEFENSE_PRIORITY else 0,
        priority.get(action["card_id"], 0), 1 if defense_needed and action["card_id"] in DEFENSE_PRIORITY else 0,
        1 if strike_axis and perfected < 2 and action["card_id"] in STRIKE_TAGGED_REWARDS else 0,
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
        enemies.append(Enemy(
            model=observed["id"],
            hp=observed["hp"],
            move=observed["move"],
            values=tuple(sorted(spec["values"].items())),
            slot=observed["slot"] or "",
            block=observed["block"],
            powers=tuple(sorted((POWER_NAMES.get(power["id"], power["id"]), power["amount"]) for power in observed["powers"])),
            history=tuple(observed["history"] or ()),
        ))
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
    )
    best, value = search(state, data, simulations, observation["seq"])[0]
    if best == "End turn":
        selected = next(action for action in actions if action["type"] == "end_turn")
        return selected | {"simulations": simulations, "search_value": value}
    name, _, target = best.partition("@")
    model = next(model for model, short in CARD_NAMES.items() if short == name)
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
