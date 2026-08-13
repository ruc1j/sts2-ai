from __future__ import annotations

import argparse
import ast
import json
import random
import re
from dataclasses import dataclass, replace


STRIKE, DEFEND, BASH, ANGER, BLUDGEON, SHRUG, BATTLE_TRANCE, BULLY, DISMANTLE, SLIMED, FRANTIC_ESCAPE, IRON_WAVE, END_TURN = "Strike", "Defend", "Bash", "Anger", "Bludgeon", "Shrug It Off", "Battle Trance", "Bully", "Dismantle", "Slimed", "Frantic Escape", "Iron Wave", "End turn"
CINDER, ASHEN_STRIKE, HEMOKINESIS, PERFECTED_STRIKE, INFLAME, PRIMAL_FORCE, UNRELENTING, GIANT_ROCK, RELAX, TREMBLE, BREAKTHROUGH, WHIRLWIND, BLOODLETTING, FEED, DOMINATE, STONE_ARMOR, FEEL_NO_PAIN = "Cinder", "Ashen Strike", "Hemokinesis", "Perfected Strike", "Inflame", "Primal Force", "Unrelenting", "Giant Rock", "Relax", "Tremble", "Breakthrough", "Whirlwind", "Bloodletting", "Feed", "Dominate", "Stone Armor", "Feel No Pain"
BYRD_SWOOP, PILLAGE, EQUILIBRIUM = "Byrd Swoop", "Pillage", "Equilibrium"
BREAK, HOWL_FROM_BEYOND, IMPERVIOUS, RAMPAGE, TAUNT, THUNDERCLAP = "Break", "Howl From Beyond", "Impervious", "Rampage", "Taunt", "Thunderclap"
BOLAS, DRAMATIC_ENTRANCE, FISTICUFFS, LIFT, THRUMMING_HATCHET, ULTIMATE_DEFEND, ULTIMATE_STRIKE = "Bolas", "Dramatic Entrance", "Fisticuffs", "Lift", "Thrumming Hatchet", "Ultimate Defend", "Ultimate Strike"
TOXIC, BURN, DAZED, FLAME_BARRIER, INFECTION = "Toxic", "Burn", "Dazed", "Flame Barrier", "Infection"
MOLTEN_FIST, NOT_YET, OFFERING, PACTS_END, POMMEL_STRIKE = "Molten Fist", "Not Yet", "Offering", "Pacts End", "Pommel Strike"
DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE = "Drum of Battle", "Master of Strategy", "Production", "Impatience"
RUPTURE = "Rupture"
SECOND_WIND = "Second Wind"
ENLIGHTENMENT = "Enlightenment"
MIND_BLAST, BODY_SLAM, BELIEVE_IN_YOU, FINESSE = "Mind Blast", "Body Slam", "Believe in You", "Finesse"
# Status cards with CardModel.HasTurnEndInHandEffect: deal this much flat Unpowered damage if
# the card is still in hand when the player ends their turn (see step()'s END_TURN handling).
# Toxic/Burn are injected straight to PileType.Hand (Myte, Mecha Knight); Infection is added to
# PileType.Discard by Wriggler's WRIGGLE_MOVE and only bites once it's drawn into a later hand.
HAND_INJECTED_STATUS = {TOXIC: 5, BURN: 2, INFECTION: 3}
STARTING_DECK = (STRIKE,) * 5 + (DEFEND,) * 4 + (BASH,)
CARD_COST = {
    STRIKE: 1, DEFEND: 1, BASH: 2, ANGER: 0, BLUDGEON: 3, SHRUG: 1, BATTLE_TRANCE: 0, BULLY: 0, DISMANTLE: 1, SLIMED: 1, FRANTIC_ESCAPE: 1, IRON_WAVE: 1,
    CINDER: 2, ASHEN_STRIKE: 1, HEMOKINESIS: 1, PERFECTED_STRIKE: 2, INFLAME: 1, PRIMAL_FORCE: 0, UNRELENTING: 2, GIANT_ROCK: 1, RELAX: 3, TREMBLE: 1,
    BREAKTHROUGH: 1, BLOODLETTING: 0, FEED: 1, DOMINATE: 1, BYRD_SWOOP: 0, PILLAGE: 1, EQUILIBRIUM: 2,
    BREAK: 1, HOWL_FROM_BEYOND: 3, IMPERVIOUS: 2, RAMPAGE: 1, TAUNT: 1, THUNDERCLAP: 1,
    BOLAS: 0, DRAMATIC_ENTRANCE: 0, FISTICUFFS: 1, LIFT: 1, THRUMMING_HATCHET: 1, ULTIMATE_DEFEND: 1, ULTIMATE_STRIKE: 1,
    FLAME_BARRIER: 2, MOLTEN_FIST: 1, NOT_YET: 2, OFFERING: 0, PACTS_END: 0, POMMEL_STRIKE: 1, DRUM_OF_BATTLE: 1, MASTER_OF_STRATEGY: 0, PRODUCTION: 0,
    IMPATIENCE: 0, MIND_BLAST: 1, BODY_SLAM: 1, BELIEVE_IN_YOU: 0, FINESSE: 0, RUPTURE: 1, STONE_ARMOR: 1, FEEL_NO_PAIN: 1, SECOND_WIND: 1, ENLIGHTENMENT: 0,
}
# WHIRLWIND has an X cost and is resolved separately.
CARD_DAMAGE = {
    STRIKE: 6, BASH: 8, ANGER: 6, BLUDGEON: 32, DISMANTLE: 8, IRON_WAVE: 5, CINDER: 18, HEMOKINESIS: 15, UNRELENTING: 14, GIANT_ROCK: 16, BREAKTHROUGH: 9,
    FEED: 10, BYRD_SWOOP: 14, PILLAGE: 6,
    BREAK: 20, RAMPAGE: 9, BOLAS: 3, FISTICUFFS: 7, THRUMMING_HATCHET: 11, ULTIMATE_STRIKE: 14,
    MOLTEN_FIST: 10, POMMEL_STRIKE: 9,
}
# Damage dealt by AllEnemies attacks (looped over every alive enemy, like BREAKTHROUGH/WHIRLWIND).
ALL_ENEMY_DAMAGE = {BREAKTHROUGH: 9, HOWL_FROM_BEYOND: 16, DRAMATIC_ENTRANCE: 11, THUNDERCLAP: 4, PACTS_END: 17}
# Flat block granted by skills with no other effect (Frail halves it, same as Defend).
CARD_BLOCK = {DEFEND: 5, IRON_WAVE: 5, EQUILIBRIUM: 13, IMPERVIOUS: 30, LIFT: 11, ULTIMATE_DEFEND: 11, FLAME_BARRIER: 12, FINESSE: 4}
# Cards that both deal damage and apply Vulnerable to that same target (Bash's pattern).
CARD_VULNERABLE_TARGET = {BASH: 2, BREAK: 5}
# Flat card draw with no other effect - a Skill that just replaces itself with more options.
CARD_DRAW = {DRUM_OF_BATTLE: 2, MASTER_OF_STRATEGY: 3, POMMEL_STRIKE: 1, FINESSE: 1, OFFERING: 3}
# Cards that require an enemy target because they deal damage (AllEnemies/RandomEnemy attacks
# still take an index here even though the actual targeting ignores it - see WHIRLWIND).
ATTACKS = {
    STRIKE, BASH, ANGER, BLUDGEON, DISMANTLE, BULLY, IRON_WAVE, CINDER, ASHEN_STRIKE, HEMOKINESIS, PERFECTED_STRIKE, UNRELENTING, GIANT_ROCK, BREAKTHROUGH,
    WHIRLWIND, FEED, BYRD_SWOOP, PILLAGE, BREAK, HOWL_FROM_BEYOND, RAMPAGE, THUNDERCLAP, BOLAS, DRAMATIC_ENTRANCE, FISTICUFFS, THRUMMING_HATCHET, ULTIMATE_STRIKE,
    MOLTEN_FIST, POMMEL_STRIKE, MIND_BLAST, BODY_SLAM, PACTS_END,
}
# CardType.Power cards represented by this compact Ironclad model.  The live bridge already
# applies any other power's effect; these are the power cards the rollout currently knows by name.
POWERS = {INFLAME, RUPTURE, STONE_ARMOR, FEEL_NO_PAIN}
# Self-targeting skills and powers that never need a target.
UNTARGETED = {
    DEFEND, SHRUG, BATTLE_TRANCE, SLIMED, FRANTIC_ESCAPE, RELAX, INFLAME, PRIMAL_FORCE, BLOODLETTING, EQUILIBRIUM, IMPERVIOUS, LIFT, ULTIMATE_DEFEND,
    FLAME_BARRIER, NOT_YET, OFFERING, DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE, BELIEVE_IN_YOU, FINESSE, RUPTURE, STONE_ARMOR, FEEL_NO_PAIN, SECOND_WIND, ENLIGHTENMENT,
}
# CardType.Skill cards (verified against each card's OnPlay base(cost, CardType.X, ...) constructor
# call), used by Infested Prism's VitalSparkPower/TaintedPower Tainted-card mechanic below.
SKILLS = {
    DEFEND, SHRUG, BATTLE_TRANCE, PRIMAL_FORCE, RELAX, TREMBLE, BLOODLETTING, DOMINATE, EQUILIBRIUM, IMPERVIOUS, LIFT, ULTIMATE_DEFEND, TAUNT,
    FLAME_BARRIER, NOT_YET, OFFERING, DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE, BELIEVE_IN_YOU, FINESSE, SECOND_WIND, ENLIGHTENMENT,
}
SELF_DAMAGE = {HEMOKINESIS: 2, BLOODLETTING: 3, BREAKTHROUGH: 1, OFFERING: 6}
EXHAUSTS = {ASHEN_STRIKE, RELAX, TREMBLE, FEED, DOMINATE, NOT_YET, OFFERING, MASTER_OF_STRATEGY, PRODUCTION, SECOND_WIND, ENLIGHTENMENT}
# Cards tagged as Strike, used by Perfected Strike scaling.
STRIKE_TAGGED = {STRIKE, PERFECTED_STRIKE, ASHEN_STRIKE}

# Relics with an automatic in-combat effect the search() rollout needs to see to project future
# turns correctly (verified against each relic's decompiled OnPlay-equivalent hook body). Relics
# with only a one-time combat-start or turn<=1 effect are deliberately excluded here - the very
# first observation of a fight already reflects them (HP/block/energy/powers are read live from
# the game), and search() never re-simulates turn 1 once combat is already past it.
RELIC_BRIMSTONE, RELIC_MERCURY_HOURGLASS, RELIC_ART_OF_WAR = "RELIC.BRIMSTONE", "RELIC.MERCURY_HOURGLASS", "RELIC.ART_OF_WAR"
RELIC_SCREAMING_FLAGON, RELIC_CLOAK_CLASP = "RELIC.SCREAMING_FLAGON", "RELIC.CLOAK_CLASP"
RELIC_CANDELABRA, RELIC_CAPTAINS_WHEEL, RELIC_HORN_CLEAT = "RELIC.CANDELABRA", "RELIC.CAPTAINS_WHEEL", "RELIC.HORN_CLEAT"
RELIC_SPARKLING_ROUGE, RELIC_STONE_CALENDAR = "RELIC.SPARKLING_ROUGE", "RELIC.STONE_CALENDAR"
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
RELIC_POCKETWATCH, RELIC_RAINBOW_RING, RELIC_RAZOR_TOOTH = "RELIC.POCKETWATCH", "RELIC.RAINBOW_RING", "RELIC.RAZOR_TOOTH"
RELIC_RED_SKULL, RELIC_REPTILE_TRINKET, RELIC_RIPPLE_BASIN = "RELIC.RED_SKULL", "RELIC.REPTILE_TRINKET", "RELIC.RIPPLE_BASIN"
RELIC_RUINED_HELMET, RELIC_SELF_FORMING_CLAY, RELIC_STURDY_CLAMP = "RELIC.RUINED_HELMET", "RELIC.SELF_FORMING_CLAY", "RELIC.STURDY_CLAMP"
RELIC_TUNGSTEN_ROD, RELIC_UNSETTLING_LAMP, RELIC_VAMBRACE = "RELIC.TUNGSTEN_ROD", "RELIC.UNSETTLING_LAMP", "RELIC.VAMBRACE"
RELIC_VENERABLE_TEA_SET = "RELIC.VENERABLE_TEA_SET"


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

    @property
    def alive(self) -> bool:
        return self.hp > 0 and not self.escaped


@dataclass(frozen=True)
class Combat:
    player_hp: int
    hand: tuple[str, ...]
    draw_pile: tuple[str, ...]
    discard_pile: tuple[str, ...]
    enemies: tuple[Enemy, ...]
    player_block: int = 0
    player_powers: tuple[tuple[str, int], ...] = ()
    energy: int = 3
    max_energy: int = 3
    turn: int = 1
    exhaust_pile: tuple[str, ...] = ()
    played_this_turn: bool = False
    player_relics: tuple[str, ...] = ()
    # Per-turn combo counters (Kunai/Shuriken/Ornamental Fan/Kusarigama/Letter Opener) - reset
    # to 0 at the start of every player turn, unlike the *_combat counters below.
    attacks_played_this_turn: int = 0
    skills_played_this_turn: int = 0
    # Every card play, any type - drives SlowPower's damage-taken ramp (Bygone Effigy). Also
    # reset at the start of every player turn.
    cards_played_this_turn: int = 0
    # Enlightenment.OnPlay: caps every hand card's cost at 1 for the rest of this turn (reduceOnly
    # - never raises a cheaper card). Reset alongside the other per-turn counters.
    enlightened_this_turn: bool = False
    # Whole-combat cumulative counters (Nunchaku/Tuning Fork) - never reset until the fight ends.
    attacks_played_combat: int = 0
    skills_played_combat: int = 0
    # DemonTongue.AfterDamageReceived: only the first unblocked hit each turn heals; reset
    # alongside the per-turn combo counters.
    damaged_this_turn: bool = False
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
    free_cards: tuple[str, ...] = ()
    powers_played_this_turn: int = 0
    bellows_used: bool = False
    burning_sticks_used: bool = False
    joss_paper_count: int = 0
    permafrost_used: bool = False
    rainbow_ring_used: bool = False
    red_skull_active: bool = False
    lizard_tail_used: bool = False
    ruined_helmet_used: bool = False
    vambrace_used: bool = False
    unsettling_lamp_used: bool = False
    upgraded_cards: tuple[str, ...] = ()

    @property
    def terminal(self) -> bool:
        return self.player_hp <= 0 or not any(enemy.alive and enemy.primary for enemy in self.enemies)


def _dict(items: tuple[tuple, ...]) -> dict:
    return dict(items)


def _power(items: tuple[tuple[str, int], ...], name: str) -> int:
    return _dict(items).get(name, 0)


def _add_power(items: tuple[tuple[str, int], ...], name: str, amount: int) -> tuple[tuple[str, int], ...]:
    powers = _dict(items)
    powers[name] = powers.get(name, 0) + amount
    if not powers[name]:
        del powers[name]
    return tuple(sorted(powers.items()))


BLOCK_CARDS = set(CARD_BLOCK) | {SHRUG, RELAX, TAUNT, SECOND_WIND}
DEBUFF_CARDS = set(CARD_VULNERABLE_TARGET) | {TAUNT, TREMBLE, THUNDERCLAP, DOMINATE, MOLTEN_FIST}


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


def _apply_player_damage(combat: Combat, amount: int) -> Combat:
    """Apply unblocked HP loss and the relics that modify it."""
    if amount <= 0:
        return combat
    tungsten = 1 if RELIC_TUNGSTEN_ROD in combat.player_relics else 0
    actual = max(0, amount - tungsten)
    if RELIC_BEATING_REMNANT in combat.player_relics:
        actual = min(actual, max(0, 20 - combat.damage_received_this_turn))
    # Tungsten Rod reduces each HP-loss event before Beating Remnant applies its turn-wide cap.
    hp = combat.player_hp - actual
    used_tail = combat.lizard_tail_used
    if hp <= 0 and RELIC_LIZARD_TAIL in combat.player_relics and not used_tail:
        hp = max(1, combat.player_max_hp // 2)
        used_tail = True
    powers = combat.player_powers
    if actual > 0 and RELIC_SELF_FORMING_CLAY in combat.player_relics:
        powers = _add_power(powers, "SelfFormingClayPower", 3)
    return _sync_red_skull(replace(
        combat, player_hp=hp, player_powers=powers,
        damage_received_this_turn=combat.damage_received_this_turn + actual,
        lizard_tail_used=used_tail,
    ))


def _after_exhaust(combat: Combat, cards: tuple[str, ...], rng: random.Random) -> Combat:
    """Resolve recurring exhaust hooks for one or more exhausted cards."""
    if not cards:
        return combat
    relics = combat.player_relics
    hand, draw, discard = list(combat.hand), combat.draw_pile, combat.discard_pile
    joss_count = combat.joss_paper_count + (len(cards) if RELIC_JOSS_PAPER in relics else 0)
    if RELIC_JOSS_PAPER in relics and joss_count >= 5:
        drawn, draw, discard = _draw(draw, discard, joss_count // 5, rng)
        hand.extend(drawn)
        joss_count %= 5
    burning_used = combat.burning_sticks_used
    if RELIC_BURNING_STICKS in relics and not burning_used:
        skill = next((card for card in cards if card in SKILLS), None)
        if skill is not None:
            hand.append(skill)
            burning_used = True
    enemies = list(combat.enemies)
    if RELIC_CHARONS_ASHES in relics:
        for _ in cards:
            enemies = [_damage_enemy(enemy, 3) if enemy.alive else enemy for enemy in enemies]
    block = _power(combat.player_powers, "FeelNoPainPower") * len(cards)
    return replace(
        combat, hand=tuple(hand), draw_pile=draw, discard_pile=discard, enemies=tuple(enemies),
        player_block=combat.player_block + block, joss_paper_count=joss_count, burning_sticks_used=burning_used,
    )


def _after_power_play(combat: Combat, rng: random.Random) -> Combat:
    """Resolve relics whose trigger is a Power card being played."""
    if not combat.player_relics or not combat.powers_played_this_turn:
        return combat
    relics = combat.player_relics
    if RELIC_GAME_PIECE in relics:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
        combat = replace(combat, hand=combat.hand + drawn, draw_pile=draw, discard_pile=discard)
    if RELIC_PERMAFROST in relics and not combat.permafrost_used:
        combat = replace(combat, player_block=combat.player_block + 7, permafrost_used=True)
    if RELIC_MUMMIFIED_HAND in relics:
        candidates = [card for card in combat.hand if CARD_COST.get(card, 0) > 0]
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


def _specs(data: dict) -> dict[str, dict]:
    return {monster["id"]: monster for monster in data.get("monsters", [])}


def _state(spec: dict, state_id: str) -> dict:
    return next(state for state in spec["states"] if state["id"] == state_id)


def _condition(expression: str, enemy: Enemy) -> bool:
    values = _dict(enemy.values)
    if "SlotName ==" in expression:
        return enemy.slot == re.search(r'"([^"]+)"', expression).group(1)
    if "HasPower<" in expression:
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
    elif expression.lstrip("!") in values:
        # A bare formation-level flag (like IsFront/IsAlone but without the "base.Creature."
        # prefix), e.g. Bowlbug Rock's POST_HEADBUTT branch on IsOffBalance.
        result = bool(values[expression.lstrip("!")])
    else:
        raise NotImplementedError(f"condition: {expression}")
    return not result if expression.lstrip().startswith("!") else result


def _resolve_move(enemy: Enemy, spec: dict, rng: random.Random, state_id: str | None = None) -> str:
    state_id = state_id or enemy.move
    while _state(spec, state_id)["type"] != "MoveState":
        branch = _state(spec, state_id)
        if branch["type"] == "ConditionalBranchState":
            state_id = next(option["state"] for option in branch["branches"] if _condition(option["condition"], enemy))
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


def _draw(draw: tuple[str, ...], discard: tuple[str, ...], count: int, rng: random.Random) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    draw, discard, hand = list(draw), list(discard), []
    while len(hand) < count and (draw or discard):
        if not draw:
            draw, discard = discard, []
        hand.append(draw.pop(rng.randrange(len(draw))))
    return tuple(hand), tuple(draw), tuple(discard)


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


def legal_actions(combat: Combat) -> tuple[str, ...]:
    if combat.terminal:
        return ()
    if combat.played_this_turn and _power(combat.player_powers, "RingingPower"):
        # RingingPower.ShouldPlay (Ceremonial Beast's BEAST_CRY_MOVE): every card in the deck is
        # afflicted with Ringing, and a Ringing card can't be played once any card has already
        # been played this turn - so the whole rest of the turn collapses to End turn only.
        return (END_TURN,)
    actions = []
    for card in dict.fromkeys(combat.hand):
        if card == WHIRLWIND:
            if combat.energy > 0:
                actions.extend(f"{card}@{index}" for index, enemy in enumerate(combat.enemies) if enemy.alive)
            continue
        if card not in CARD_COST or (card not in combat.free_cards and CARD_COST[card] > combat.energy):
            continue
        if card in UNTARGETED:
            actions.append(card)
        else:
            actions.extend(f"{card}@{index}" for index, enemy in enumerate(combat.enemies) if enemy.alive)
    return tuple(actions) + (END_TURN,)


def _enemy_attack_damage(enemy: Enemy, data: dict) -> int:
    spec = _specs(data).get(enemy.model)
    if not spec:
        return 0
    move = next((state for state in spec["states"] if state["id"] == enemy.move), None)
    if not move:
        return 0
    attack = next((intent for intent in move.get("intents", ()) if "damage" in intent), {})
    damage = int(attack.get("damage", 0)) + _power(enemy.powers, "StrengthPower")
    if _power(enemy.powers, "WeakPower"):
        damage = damage * 3 // 4
    return max(0, damage * max(1, int(attack.get("repeats", 1))))


def _damage_enemy(enemy: Enemy, damage: int) -> Enemy:
    if _power(enemy.powers, "SlipperyPower"):
        return replace(enemy, hp=enemy.hp - 1, powers=_add_power(enemy.powers, "SlipperyPower", -1))
    # Flutter (e.g. Thieving Hopper) halves powered-attack damage and wears off per unblocked hit.
    flutter = _power(enemy.powers, "FlutterPower")
    if flutter:
        damage //= 2
    # HardToKill caps every hit at the power amount (Exoskeleton takes at most 9 per attack).
    cap = _power(enemy.powers, "HardToKillPower")
    if cap > 0:
        damage = min(damage, cap)
    blocked = min(enemy.block, damage)
    unblocked = damage - blocked
    powers = enemy.powers
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
        return replace(enemy, block=enemy.block - blocked, hp=hp, powers=powers, move="STUN_MOVE")
    return replace(enemy, block=enemy.block - blocked, hp=hp, powers=powers)


def _decimillipede_teammates_dead(enemies: tuple[Enemy, ...], index: int) -> bool:
    return not any(
        other.alive for i, other in enumerate(enemies)
        if i != index and other.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT")
    )


def _enemy_turn(combat: Combat, index: int, data: dict, rng: random.Random) -> Combat:
    enemy = replace(combat.enemies[index], block=0)
    if not enemy.alive:
        # Decimillipede segments don't actually leave combat on death (unless every other
        # segment is already dead too) - they were tagged DEAD_MOVE at the moment of death and
        # keep progressing through their state machine (DEAD_MOVE -> REATTACH_MOVE) to revive.
        if not (enemy.model.startswith("MONSTER.DECIMILLIPEDE_SEGMENT") and enemy.move in ("DEAD_MOVE", "REATTACH_MOVE")):
            return combat
    spec, move_id, move = _specs(data)[enemy.model], enemy.move, _state(_specs(data)[enemy.model], enemy.move)
    values, player_hp, player_block = _dict(enemy.values), combat.player_hp, combat.player_block
    sandpit = _power(enemy.powers, "SandpitPower")
    if sandpit:
        if sandpit == 1:
            return replace(combat, player_hp=0)
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", -1))
    player_powers, discard, draw, hand = combat.player_powers, combat.discard_pile, combat.draw_pile, list(combat.hand)
    enemies = list(combat.enemies)
    damage_events: list[int] = []
    ruined_helmet_used = combat.ruined_helmet_used
    attack_intent = next((intent for intent in move.get("intents", ()) if "damage" in intent), {})
    # PHEROMONE_SPIT_MOVE's real effect is an if/else in SpitMove's method body (grow
    # PersonalHivePower+Strength while PersonalHivePower < 3, else Strength alone) that the
    # static exporter can't see - it just dumps every PowerCmd.Apply call in the method
    # textually, so the generic effects loop below is skipped for this move and replaced with
    # the correct branch after move-resolution (see the ENTOMANCER special case further down).
    entomancer_spit = enemy.model == "MONSTER.ENTOMANCER" and move_id == "PHEROMONE_SPIT_MOVE"
    effects = move.get("effects", ())
    if not effects and "damage" in attack_intent:
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
            damage = int(attack_intent["damage"]) + _power(enemy.powers, "StrengthPower") + _power(player_powers, "TaintedPower")
            if (_power(player_powers, "SurroundedRight") and _power(enemy.powers, "BackAttackLeftPower")) or (_power(player_powers, "SurroundedLeft") and _power(enemy.powers, "BackAttackRightPower")):
                damage = damage * 3 // 2
            repeats = int(attack_intent.get("repeats", 1))
            if _power(enemy.powers, "WeakPower"):
                damage = damage * 3 // 4
            if _power(player_powers, "VulnerablePower"):
                damage = damage * 3 // 2
            for _ in range(repeats):
                blocked = min(player_block, damage)
                player_block -= blocked
                unblocked = damage - blocked
                damage_events.append(unblocked)
            # FlameBarrierPower.AfterDamageReceived: reflects a flat amount back at the attacker
            # once per attack (approximated the same way as the symmetric enemy-side ThornsPower,
            # not per individual repeat hit).
            flame_barrier = _power(player_powers, "FlameBarrierPower")
            if flame_barrier:
                enemy = _damage_enemy(enemy, flame_barrier)
        elif command == "PowerCmd.Apply":
            try:
                amount = _amount(effect["amount"], values)
            except (ValueError, KeyError):
                # Unmodeled interactions (e.g. Thieving Hopper's swipe that steals a card)
                # carry no numeric amount; skip them, they do not change HP.
                continue
            if effect["target"] == "base.Creature":
                enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], amount))
            elif effect["target"] == "targets":
                if (
                    effect["model"] == "StrengthPower" and amount > 0
                    and RELIC_RUINED_HELMET in combat.player_relics and not ruined_helmet_used
                ):
                    amount *= 2
                    ruined_helmet_used = True
                player_powers = _add_power(player_powers, effect["model"], amount)
            elif "TeammatesOf" in effect["target"]:
                # GetTeammatesOf = GetCreaturesOnSide(side): every creature on the same side,
                # including the caster (e.g. Obscura's SAIL buffs itself as well as its minions).
                for mate_index, mate in enumerate(enemies):
                    if mate_index == index:
                        enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], amount))
                    elif mate.alive:
                        enemies[mate_index] = replace(mate, powers=_add_power(mate.powers, effect["model"], amount))
        elif command == "PowerCmd.Remove" and effect.get("target") == "base.Creature":
            enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], -_power(enemy.powers, effect["model"])))
        elif command == "CreatureCmd.GainBlock":
            enemy = replace(enemy, block=enemy.block + _amount(effect["amount"], values))
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
            enemies.append(_summon(effect["model"], data, rng))
        elif command in {"CreatureCmd.Kill", "CreatureCmd.SetMaxAndCurrentHp"}:
            raise NotImplementedError(f"effect: {spec['class']}.{move['id']} {command}")
    if move_id == "SNORE_MOVE":
        # SlumberPower.AfterSideTurnEnd decrements once per enemy turn and forces an immediate
        # wake-up (not a "next move" transition) once it reaches 0, so this must land before the
        # next-move resolution below (SlumberingBeetle also decrements it on taking unblocked
        # damage, not modeled - a safe, conservative wake-up estimate).
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SlumberPower", -1))
    enemy = replace(enemy, history=enemy.history + (enemy.move,))
    enemy = replace(enemy, move=_resolve_move(enemy, spec, rng, move.get("next")))
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
    if enemy.model == "MONSTER.BYRDONIS":
        # TerritorialPower.AfterSideTurnEnd (not exported): +1 Strength unconditionally every
        # turn, regardless of which move was performed.
        enemy = replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", 1))
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
    combat_after_damage = replace(
        combat, player_hp=player_hp, player_powers=player_powers,
        damage_received_this_turn=damage_received, lizard_tail_used=lizard_tail_used,
    )
    combat_after_damage = _sync_red_skull(combat_after_damage)
    return replace(
        combat_after_damage, player_block=player_block, player_powers=combat_after_damage.player_powers,
        discard_pile=discard, draw_pile=draw, hand=tuple(hand), enemies=tuple(enemies),
        damaged_this_turn=damaged_this_turn, centennial_puzzle_used=centennial_puzzle_used,
        ruined_helmet_used=ruined_helmet_used,
    )


def step(combat: Combat, action: str, data: dict, rng: random.Random) -> Combat:
    if action not in legal_actions(combat):
        raise ValueError(f"illegal action: {action}")
    combat = _sync_belt_buckle(_sync_red_skull(combat))
    if action == END_TURN:
        # RingingPower.AfterSideTurnEnd (Ceremonial Beast): removes itself once the player's own
        # turn ends, clearing the Ringing one-card-per-turn restriction for next turn.
        combat = replace(combat, player_powers=_add_power(combat.player_powers, "RingingPower", -_power(combat.player_powers, "RingingPower")), played_this_turn=False)
        # HasTurnEndInHandEffect (Toxic, Burn): flat Unpowered damage for each copy still in
        # hand when the player's turn ends, then the hand is cleared to discard as normal - a
        # monster move can inject fresh copies straight into the (now empty) hand during its own
        # turn below, and those survive to be drawn alongside next turn's hand.
        hand_damage = sum(HAND_INJECTED_STATUS.get(card, 0) for card in combat.hand)
        relics = combat.player_relics
        # CloakClasp.BeforeSideTurnEnd: block equal to 1 per card still in hand, granted before
        # the hand is cleared to discard (and before the enemy turn below, so it can help block).
        cloak_clasp_block = len(combat.hand) if RELIC_CLOAK_CLASP in relics else 0
        # ScreamingFlagon.BeforeSideTurnEnd: 20 damage to every enemy if the hand ended up empty.
        screaming_flagon = RELIC_SCREAMING_FLAGON in relics and not combat.hand
        combat = replace(
            combat, player_block=combat.player_block + cloak_clasp_block,
            discard_pile=combat.discard_pile + combat.hand, hand=(),
        )
        plating = _power(combat.player_powers, "PlatingPower")
        if plating:
            combat = replace(combat, player_block=combat.player_block + plating)
        combat = _apply_player_damage(combat, hand_damage)
        if screaming_flagon:
            combat = replace(combat, enemies=tuple(_damage_enemy(enemy, 20) if enemy.alive else enemy for enemy in combat.enemies))
        # ConstrictPower.AfterSideTurnEnd (Slithering Strangler): CreatureCmd.Damage for the
        # current stack amount every time the player's own turn ends - a block-respecting DOT
        # that stacks +3 every CONSTRICT cast and never decays on its own. Previously stored via
        # the generic PowerCmd.Apply handling in _enemy_turn with no damage ever applied, which
        # silently turned an escalating per-turn bleed into a free, permanently inert power.
        constrict = _power(combat.player_powers, "ConstrictPower")
        if constrict:
            blocked = min(combat.player_block, constrict)
            combat = replace(combat, player_block=combat.player_block - blocked)
            combat = _apply_player_damage(combat, constrict - blocked)
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
                enemies[hit] = _damage_enemy(enemies[hit], 6)
                combat = replace(combat, enemies=tuple(enemies))
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
        combat = replace(combat, enemies=tuple(enemies))
        # TaintedPower.AfterSideTurnEnd and FlameBarrierPower.AfterSideTurnEnd both remove
        # themselves once the enemy side's turn ends.
        player_powers = combat.player_powers
        player_powers = _add_power(player_powers, "TaintedPower", -_power(player_powers, "TaintedPower"))
        player_powers = _add_power(player_powers, "FlameBarrierPower", -_power(player_powers, "FlameBarrierPower"))
        player_powers = _add_power(player_powers, "ReptileTrinketPower", -_power(player_powers, "ReptileTrinketPower"))
        # Turn-start relics (AfterSideTurnStart/BeforeSideTurnStart/AfterBlockCleared for the
        # upcoming turn). new_turn is the turn number the player is about to begin.
        new_turn, extra_energy, extra_draw, extra_block, enemies = combat.turn + 1, 0, 0, 0, list(combat.enemies)
        if RELIC_BRIMSTONE in relics:
            player_powers = _add_power(player_powers, "StrengthPower", 2)
            enemies = [replace(enemy, powers=_add_power(enemy.powers, "StrengthPower", 1)) if enemy.alive else enemy for enemy in enemies]
        if RELIC_MERCURY_HOURGLASS in relics:
            enemies = [_damage_enemy(enemy, 3) if enemy.alive else enemy for enemy in enemies]
        if RELIC_STONE_CALENDAR in relics and new_turn == 7:
            enemies = [_damage_enemy(enemy, 52) if enemy.alive else enemy for enemy in enemies]
        # ArtOfWar.AfterEnergyReset: +1 energy if no attack was played on the turn that just
        # ended (never fires transitioning into turn 2 - there is no "previous turn" to check).
        if RELIC_ART_OF_WAR in relics and combat.turn > 1 and combat.attacks_played_this_turn == 0:
            extra_energy += 1
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
        if _power(player_powers, "PlatingPower") and new_turn > 1:
            player_powers = _add_power(player_powers, "PlatingPower", -1)
        if RELIC_POCKETWATCH in relics and new_turn > 1 and combat.cards_played_this_turn <= 3:
            extra_draw += 3
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 5 + extra_draw, rng)
        retained_block = min(combat.player_block, 10) if RELIC_STURDY_CLAMP in relics else 0
        return replace(
            combat, hand=combat.hand + drawn, draw_pile=draw, discard_pile=discard, player_block=retained_block + extra_block,
            energy=combat.max_energy + extra_energy, turn=new_turn, player_powers=player_powers, enemies=tuple(enemies),
            attacks_played_this_turn=0, skills_played_this_turn=0, cards_played_this_turn=0,
            powers_played_this_turn=0, damaged_this_turn=False, damage_received_this_turn=0,
            cards_played_last_turn=combat.cards_played_this_turn, enlightened_this_turn=False, free_cards=(),
        )

    card, _, target = action.partition("@")
    if RELIC_BELLOWS in combat.player_relics and combat.turn == 1 and not combat.bellows_used:
        upgraded = tuple(dict.fromkeys(combat.upgraded_cards + combat.hand))
        combat = replace(combat, upgraded_cards=upgraded, bellows_used=True)
    hand = list(combat.hand)
    if card in SKILLS:
        vital_spark = sum(_power(enemy.powers, "VitalSparkPower") for enemy in combat.enemies if enemy.alive)
        if vital_spark:
            # VitalSparkPower (Infested Prism's PULSATE_MOVE) taints every Skill card in the
            # deck; playing one grants TaintedPower equal to the current stack, which adds flat
            # damage to powered attacks against the player until the enemy's turn ends.
            combat = replace(combat, player_powers=_add_power(combat.player_powers, "TaintedPower", vital_spark))
    hand.remove(card)
    free_cards = list(combat.free_cards)
    card_is_free = card in free_cards
    card_was_upgraded = card in combat.upgraded_cards
    if card_is_free:
        free_cards.remove(card)
    # Card-play-counting relics (Kunai/Shuriken/Ornamental Fan/Kusarigama/Letter Opener/
    # Nunchaku/Tuning Fork): all fire off a plain "every Nth attack/skill played" counter, either
    # reset each turn (the four "every 3rd attack" relics, Letter Opener's "every 3rd skill") or
    # cumulative for the whole fight (Nunchaku, Tuning Fork - both "every 10th").
    relics = combat.player_relics
    attacks_this_turn = combat.attacks_played_this_turn + (1 if card in ATTACKS else 0)
    skills_this_turn = combat.skills_played_this_turn + (1 if card in SKILLS else 0)
    attacks_combat = combat.attacks_played_combat + (1 if card in ATTACKS else 0)
    skills_combat = combat.skills_played_combat + (1 if card in SKILLS else 0)
    cards_this_turn = combat.cards_played_this_turn + 1
    powers_this_turn = combat.powers_played_this_turn + (1 if card in POWERS else 0)
    pen_nib_double = RELIC_PEN_NIB in relics and card in ATTACKS and attacks_combat % 10 == 0
    helmet_block = 4 if RELIC_INTIMIDATING_HELMET in relics and (CARD_COST.get(card, 0) >= 2 or (card == WHIRLWIND and combat.energy >= 2)) else 0
    vambrace_double = RELIC_VAMBRACE in relics and not combat.vambrace_used and card in BLOCK_CARDS
    lamp_double = RELIC_UNSETTLING_LAMP in relics and not combat.unsettling_lamp_used and card in DEBUFF_CARDS
    combo_powers, combo_enemies, combo_block, combo_energy = combat.player_powers, list(combat.enemies), 0, 0
    combo_block += helmet_block
    if card in ATTACKS:
        if RELIC_KUNAI in relics and attacks_this_turn % 3 == 0:
            combo_powers = _add_power(combo_powers, "DexterityPower", 1)
        if RELIC_SHURIKEN in relics and attacks_this_turn % 3 == 0:
            combo_powers = _add_power(combo_powers, "StrengthPower", 1)
        if RELIC_ORNAMENTAL_FAN in relics and attacks_this_turn % 3 == 0:
            combo_block += 4
        if RELIC_KUSARIGAMA in relics and attacks_this_turn % 3 == 0:
            alive = [i for i, enemy in enumerate(combo_enemies) if enemy.alive]
            if alive:
                hit = rng.choice(alive)
                combo_enemies[hit] = _damage_enemy(combo_enemies[hit], 6)
        if RELIC_NUNCHAKU in relics and attacks_combat % 10 == 0:
            combo_energy += 1
    if card in SKILLS:
        if RELIC_LETTER_OPENER in relics and skills_this_turn % 3 == 0:
            combo_enemies = [_damage_enemy(enemy, 5) if enemy.alive else enemy for enemy in combo_enemies]
        if RELIC_TUNING_FORK in relics and skills_combat % 10 == 0:
            combo_block += 7
    combat = replace(
        combat, played_this_turn=True, player_powers=combo_powers, enemies=tuple(combo_enemies),
        player_block=combat.player_block + combo_block, energy=combat.energy + combo_energy,
        attacks_played_this_turn=attacks_this_turn, skills_played_this_turn=skills_this_turn,
        attacks_played_combat=attacks_combat, skills_played_combat=skills_combat, cards_played_this_turn=cards_this_turn,
        powers_played_this_turn=powers_this_turn, free_cards=tuple(free_cards),
        vambrace_used=combat.vambrace_used or vambrace_double,
        unsettling_lamp_used=combat.unsettling_lamp_used or lamp_double,
    )
    if card == BATTLE_TRANCE:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 3, rng)
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard + (card,))
    if card == SLIMED:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard, energy=combat.energy - (0 if card_is_free else 1))
    if card == FRANTIC_ESCAPE:
        enemies = list(combat.enemies)
        for index, enemy in enumerate(enemies):
            if _power(enemy.powers, "SandpitPower"):
                enemies[index] = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", 1))
                break
        return replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile + (card,), energy=combat.energy - (0 if card_is_free else 1), enemies=tuple(enemies))
    if card == SHRUG:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
        base = 8 + (1 if card_was_upgraded else 0)
        block = base * 3 // 4 if _power(combat.player_powers, "FrailPower") else base
        if vambrace_double:
            block *= 2
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard + (card,), energy=combat.energy - (0 if card_is_free else 1), player_block=combat.player_block + block)
    if card in CARD_DRAW:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, CARD_DRAW[card], rng)
        hand = hand + list(drawn)
        combat = replace(combat, draw_pile=draw, discard_pile=discard)
    if card == IMPATIENCE and not any(card_name in ATTACKS for card_name in hand):
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 2, rng)
        hand = hand + list(drawn)
        combat = replace(combat, draw_pile=draw, discard_pile=discard)
    # Enlightenment.OnPlay (reduceOnly): once played, every card costs at most 1 for the rest of
    # the turn. WHIRLWIND's X cost is exempt - it isn't a fixed cost to reduce.
    if card == WHIRLWIND:
        spent = combat.energy
    elif combat.enlightened_this_turn:
        spent = min(CARD_COST[card], 1)
    else:
        spent = CARD_COST[card]
    if card_is_free:
        spent = 0
    whirlwind_x = combat.energy + (2 if RELIC_CHEMICAL_X in relics else 0)
    whirlwind_damage = 5 * whirlwind_x if card == WHIRLWIND else 0
    energy = combat.energy - spent + (2 if card in {BLOODLETTING, BELIEVE_IN_YOU, PRODUCTION, OFFERING} else 0)
    player_hp = combat.player_hp
    self_damage = SELF_DAMAGE.get(card, 0)
    if self_damage:
        # Apply Tungsten Rod/Beating Remnant/Lizard Tail to card self-damage as well as enemy hits.
        damaged = _apply_player_damage(combat, self_damage)
        player_hp, combat = damaged.player_hp, damaged
    if card == NOT_YET:
        # No max-HP tracking in this model (Combat has no companion max_hp field), so the heal is
        # uncapped - a small, safe-direction gap since it can only ever make the sim think the
        # player has slightly more HP margin than they truly do.
        player_hp += 10
    player_powers = combat.player_powers
    if card == RUPTURE:
        player_powers = _add_power(player_powers, "RupturePower", 1)
    # RupturePower.AfterDamageReceived: any unblocked damage a card deals to the player during
    # their own turn (Hemokinesis/Bloodletting/Breakthrough/Offering's self-damage here) grants
    # Strength equal to the Rupture stack.
    rupture = _power(player_powers, "RupturePower")
    if rupture and card in SELF_DAMAGE:
        player_powers = _add_power(player_powers, "StrengthPower", rupture)
    if card == INFLAME:
        player_powers = _add_power(player_powers, "StrengthPower", 2)
    if card == FLAME_BARRIER:
        player_powers = _add_power(player_powers, "FlameBarrierPower", 4)
    if card == PRIMAL_FORCE:
        hand = [GIANT_ROCK if card_name in ATTACKS else card_name for card_name in hand]
    exhaust = card in EXHAUSTS
    exhaust_before = combat.exhaust_pile
    exhaust_pile = exhaust_before + ((card,) if exhaust else ())
    enlightened = combat.enlightened_this_turn or card == ENLIGHTENMENT
    combat = replace(
        combat, hand=tuple(hand), discard_pile=combat.discard_pile + (() if exhaust else (card,)), exhaust_pile=exhaust_pile,
        energy=energy, player_hp=player_hp, player_powers=player_powers, enlightened_this_turn=enlightened,
    )
    combat = _sync_red_skull(combat)
    combat = _after_exhaust(combat, (card,) if exhaust else (), rng)
    if card in POWERS:
        combat = _after_power_play(combat, rng)
    if RELIC_RAZOR_TOOTH in relics and (card in ATTACKS or card in SKILLS):
        combat = replace(combat, upgraded_cards=combat.upgraded_cards + (card,))
    if card in CARD_BLOCK:
        base = CARD_BLOCK[card]
        if card_was_upgraded:
            base += 1
        block = base * 3 // 4 if _power(combat.player_powers, "FrailPower") else base
        if vambrace_double:
            block *= 2
        combat = replace(combat, player_block=combat.player_block + block)
    if card in {DEFEND, EQUILIBRIUM, IMPERVIOUS, LIFT, ULTIMATE_DEFEND, FLAME_BARRIER, FINESSE}:
        return combat
    if card == RELAX:
        base = 15 + (1 if card_was_upgraded else 0)
        block = base * 3 // 4 if _power(combat.player_powers, "FrailPower") else base
        if vambrace_double:
            block *= 2
        return replace(combat, player_block=combat.player_block + block)
    if card == SECOND_WIND:
        # SecondWind.OnPlay: exhausts every non-Attack card still in hand, gaining 5 block
        # (ValueProp.Move, so Frail doesn't reduce it) per card exhausted this way.
        non_attacks = tuple(name for name in combat.hand if name not in ATTACKS)
        remaining = tuple(name for name in combat.hand if name in ATTACKS)
        block = 5 * len(non_attacks)
        if vambrace_double:
            block *= 2
        combat = replace(combat, hand=remaining, exhaust_pile=combat.exhaust_pile + non_attacks, player_block=combat.player_block + block)
        return _after_exhaust(combat, non_attacks, rng)
    if card == STONE_ARMOR:
        return replace(combat, player_powers=_add_power(combat.player_powers, "PlatingPower", 6 if card_was_upgraded else 4))
    if card == FEEL_NO_PAIN:
        return replace(combat, player_powers=_add_power(combat.player_powers, "FeelNoPainPower", 4 if card_was_upgraded else 3))
    if card in {INFLAME, PRIMAL_FORCE, BLOODLETTING, NOT_YET, OFFERING, DRUM_OF_BATTLE, MASTER_OF_STRATEGY, PRODUCTION, IMPATIENCE, BELIEVE_IN_YOU, RUPTURE, ENLIGHTENMENT}:
        return combat
    enemies = list(combat.enemies)
    if card == TAUNT:
        base = 7 + (1 if card_was_upgraded else 0)
        block = base * 3 // 4 if _power(combat.player_powers, "FrailPower") else base
        if vambrace_double:
            block *= 2
        enemy = enemies[int(target)]
        vulnerable = 1 * (2 if lamp_double else 1)
        enemies[int(target)] = replace(enemy, powers=_add_power(enemy.powers, "VulnerablePower", vulnerable))
        return replace(combat, player_block=combat.player_block + block, enemies=tuple(enemies))
    if card in ALL_ENEMY_DAMAGE or card == WHIRLWIND:
        damage = (whirlwind_damage if card == WHIRLWIND else ALL_ENEMY_DAMAGE[card]) + _power(combat.player_powers, "StrengthPower") + _power(combat.player_powers, "ReptileTrinketPower")
        if card_was_upgraded:
            damage += 3
        if _power(combat.player_powers, "WeakPower"):
            damage = damage * 3 // 4
        if _power(combat.player_powers, "ShrinkPower"):
            damage = damage * 7 // 10
        if pen_nib_double:
            damage *= 2
        before = list(enemies)
        for index, enemy in enumerate(enemies):
            if not enemy.alive:
                continue
            scaled = damage * 3 // 2 if _power(enemy.powers, "VulnerablePower") else damage
            # SlowPower.ModifyDamageMultiplicative (Bygone Effigy): +10% powered-attack damage
            # taken per card played earlier this turn (combat.cards_played_this_turn already
            # counts the card resolving right now, hence the -1).
            if _power(enemy.powers, "SlowPower"):
                scaled = scaled * (10 + combat.cards_played_this_turn - 1) // 10
            enemies[index] = _damage_enemy(enemy, scaled)
        if card == THUNDERCLAP:
            for index, enemy in enumerate(enemies):
                if enemy.alive:
                    vulnerable = 2 if lamp_double else 1
                    enemies[index] = replace(enemy, powers=_add_power(enemy.powers, "VulnerablePower", vulnerable))
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
        return replace(combat, enemies=tuple(enemies), player_hp=combat.player_hp - reflected, draw_pile=combat.draw_pile + (DAZED,) * hive)
    if card == TREMBLE:
        enemy = enemies[int(target)]
        vulnerable = 6 if lamp_double else 3
        enemies[int(target)] = replace(enemy, powers=_add_power(enemy.powers, "VulnerablePower", vulnerable))
        return replace(combat, enemies=tuple(enemies))
    if card == DOMINATE:
        # Apply 1 Vulnerable, then gain Strength equal to the target's (post-apply) Vulnerable.
        enemy = enemies[int(target)]
        vulnerable = 2 if lamp_double else 1
        enemies[int(target)] = replace(enemy, powers=_add_power(enemy.powers, "VulnerablePower", vulnerable))
        gained = _power(enemies[int(target)].powers, "VulnerablePower")
        return replace(combat, enemies=tuple(enemies), player_powers=_add_power(combat.player_powers, "StrengthPower", gained))
    enemy = enemies[int(target)]
    if card == PERFECTED_STRIKE:
        strikes = sum(1 for name in combat.hand + combat.draw_pile + combat.discard_pile + combat.exhaust_pile if name in STRIKE_TAGGED)
        damage = 6 + 2 * strikes
    elif card == ASHEN_STRIKE:
        damage = 6 + 3 * len(exhaust_before)
    elif card == MIND_BLAST:
        damage = len(combat.draw_pile)
    elif card == BODY_SLAM:
        damage = combat.player_block
    else:
        damage = 4 + 2 * _power(enemy.powers, "VulnerablePower") if card == BULLY else CARD_DAMAGE[card]
    if card_was_upgraded:
        damage += 3
    damage += _power(combat.player_powers, "StrengthPower") + _power(combat.player_powers, "ReptileTrinketPower")
    if card == DISMANTLE and _power(enemy.powers, "VulnerablePower"):
        damage *= 2
    if _power(combat.player_powers, "WeakPower"):
        damage = damage * 3 // 4
    if _power(combat.player_powers, "ShrinkPower"):
        damage = damage * 7 // 10
    if pen_nib_double:
        damage *= 2
    if _power(enemy.powers, "VulnerablePower"):
        damage = damage * 3 // 2
    # SlowPower.ModifyDamageMultiplicative (Bygone Effigy): +10% powered-attack damage taken per
    # card played earlier this turn (combat.cards_played_this_turn already counts the card
    # resolving right now, hence the -1).
    if _power(enemy.powers, "SlowPower"):
        damage = damage * (10 + combat.cards_played_this_turn - 1) // 10
    enemies[int(target)] = _damage_enemy(enemy, damage)
    if card == MOLTEN_FIST and enemies[int(target)].alive:
        vulnerable = _power(enemy.powers, "VulnerablePower")
        if vulnerable:
            enemies[int(target)] = replace(enemies[int(target)], powers=_add_power(enemies[int(target)].powers, "VulnerablePower", vulnerable * (2 if lamp_double else 1)))
    if card == CINDER and hand:
        sacrificed = hand.pop(rng.randrange(len(hand)))
        combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (sacrificed,))
        combat = _after_exhaust(combat, (sacrificed,), rng)
    player_powers = combat.player_powers
    if _power(player_powers, "SurroundedRight") and _power(enemy.powers, "BackAttackLeftPower"):
        player_powers = _add_power(_add_power(player_powers, "SurroundedRight", -1), "SurroundedLeft", 1)
    elif _power(player_powers, "SurroundedLeft") and _power(enemy.powers, "BackAttackRightPower"):
        player_powers = _add_power(_add_power(player_powers, "SurroundedLeft", -1), "SurroundedRight", 1)
    if card in CARD_VULNERABLE_TARGET:
        vulnerable = CARD_VULNERABLE_TARGET[card] * (2 if lamp_double else 1)
        enemies[int(target)] = replace(enemies[int(target)], powers=_add_power(enemies[int(target)].powers, "VulnerablePower", vulnerable))
    if card == ANGER:
        combat = replace(combat, discard_pile=combat.discard_pile + (ANGER,))
    if card == PILLAGE:
        # Draw until a non-Attack card comes up (Pillage's do/while); each drawn card stays in hand.
        drawn_hand = list(combat.hand)
        draw_pile, discard_pile = combat.draw_pile, combat.discard_pile
        while True:
            if not (draw_pile or discard_pile):
                break
            one, draw_pile, discard_pile = _draw(draw_pile, discard_pile, 1, rng)
            drawn_hand += one
            if not one or one[0] not in ATTACKS:
                break
        combat = replace(combat, hand=tuple(drawn_hand), draw_pile=draw_pile, discard_pile=discard_pile)
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
    reflected = _power(enemy.powers, "ThornsPower")
    # PersonalHivePower.AfterDamageReceived (Entomancer): every powered attack against a holder
    # inserts Amount Dazed cards into the draw pile at a random position.
    hive = _power(enemy.powers, "PersonalHivePower")
    return replace(combat, enemies=tuple(enemies), player_powers=player_powers, player_hp=combat.player_hp - reflected, draw_pile=combat.draw_pile + (DAZED,) * hive)


def _step_score(combat: Combat, state: Combat, data: dict) -> float:
    """Score a single step: prevented damage + damage dealt - self-damage + effective block."""
    incoming = sum(_enemy_attack_damage(enemy, data) for enemy in combat.enemies if enemy.alive)
    exposed = max(0, incoming - combat.player_block)
    prevented = sum(_enemy_attack_damage(before, data) for before, after in zip(combat.enemies, state.enemies) if before.alive and not after.alive and not after.escaped)
    # Killing the primary enemy (the boss) wins the fight; credit its remaining HP so a
    # boss kill outranks killing a reviving minion.
    prevented += sum(max(0, before.hp) for before, after in zip(combat.enemies, state.enemies) if before.alive and before.primary and not after.alive and not after.escaped)
    # Cap damage at each enemy's remaining HP so overkill is not overvalued.
    dealt = sum(max(0, before.hp) - max(0, after.hp) for before, after in zip(combat.enemies, state.enemies) if before.alive and not after.escaped)
    dealt -= max(0, combat.player_hp - state.player_hp)  # penalize self-damage
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
    return prevented + dealt + min(blocked, exposed) + upkeep + 0.3 * max(0, drawn)


def _greedy_action(combat: Combat, data: dict) -> str:
    """Pick a card action by prevented damage + damage dealt; block counts against incoming."""
    actions = legal_actions(combat)[:-1]  # exclude End turn
    if not actions:
        return END_TURN
    best, best_score = None, -1.0
    for action in actions:
        state = step(combat, action, data, random.Random(0))
        # Skip actions that kill the player unless they win the fight outright.
        if state.player_hp <= 0 and any(enemy.alive for enemy in state.enemies):
            continue
        score = _step_score(combat, state, data)
        card = action.partition("@")[0]
        # Vulnerability applies (Bash/Tremble) strengthen later attacks by 50%; credit
        # that so they are played before the attacks they boost.
        if card in {BASH, TREMBLE}:
            score += sum(CARD_DAMAGE.get(name, 0) // 2 for name in state.hand if name in ATTACKS and name != card and CARD_COST.get(name, 99) <= state.energy)
        if score > best_score:
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
            immediate = _step_score(combat, state, data) / 100
            for _ in range(60):
                if state.terminal:
                    break
                state = step(state, _greedy_action(state, data), data, rng)
            # An enemy that fled (e.g. Thieving Hopper) ends the fight but is NOT a win.
            won = not any(enemy.alive for enemy in state.enemies) and not any(enemy.escaped for enemy in state.enemies)
            # Win/loss dominates; HP and the immediate-move score break ties so noisy rollouts still rank correctly.
            scored_hp = state.player_hp
            if won and RELIC_MEAT_ON_THE_BONE in state.player_relics and state.player_max_hp > 0 and scored_hp * 2 <= state.player_max_hp:
                scored_hp = min(state.player_max_hp, scored_hp + 12)
            scores.append((1 if won else -1 if state.player_hp <= 0 else 0) + scored_hp / 100 + immediate)
        results.append((action, sum(scores) / len(scores)))
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
    print("hand=" + ", ".join(combat.hand))
    for action, value in search(combat, data, args.simulations, args.seed):
        print(f"{action:16} value={value:.5f}")


if __name__ == "__main__":
    main()
