from __future__ import annotations

import argparse
import ast
import json
import random
import re
from dataclasses import dataclass, replace


STRIKE, DEFEND, BASH, ANGER, BLUDGEON, SHRUG, BATTLE_TRANCE, BULLY, DISMANTLE, SLIMED, FRANTIC_ESCAPE, IRON_WAVE, END_TURN = "Strike", "Defend", "Bash", "Anger", "Bludgeon", "Shrug It Off", "Battle Trance", "Bully", "Dismantle", "Slimed", "Frantic Escape", "Iron Wave", "End turn"
CINDER, ASHEN_STRIKE, HEMOKINESIS, PERFECTED_STRIKE, INFLAME, PRIMAL_FORCE, UNRELENTING, GIANT_ROCK, RELAX, TREMBLE, BREAKTHROUGH, WHIRLWIND, BLOODLETTING, FEED, DOMINATE = "Cinder", "Ashen Strike", "Hemokinesis", "Perfected Strike", "Inflame", "Primal Force", "Unrelenting", "Giant Rock", "Relax", "Tremble", "Breakthrough", "Whirlwind", "Bloodletting", "Feed", "Dominate"
BYRD_SWOOP, PILLAGE, EQUILIBRIUM = "Byrd Swoop", "Pillage", "Equilibrium"
STARTING_DECK = (STRIKE,) * 5 + (DEFEND,) * 4 + (BASH,)
CARD_COST = {STRIKE: 1, DEFEND: 1, BASH: 2, ANGER: 0, BLUDGEON: 3, SHRUG: 1, BATTLE_TRANCE: 0, BULLY: 0, DISMANTLE: 1, SLIMED: 1, FRANTIC_ESCAPE: 1, IRON_WAVE: 1, CINDER: 2, ASHEN_STRIKE: 1, HEMOKINESIS: 1, PERFECTED_STRIKE: 2, INFLAME: 1, PRIMAL_FORCE: 0, UNRELENTING: 2, GIANT_ROCK: 1, RELAX: 3, TREMBLE: 1, BREAKTHROUGH: 1, BLOODLETTING: 0, FEED: 1, DOMINATE: 1, BYRD_SWOOP: 0, PILLAGE: 1, EQUILIBRIUM: 2}
# WHIRLWIND has an X cost and is resolved separately.
CARD_DAMAGE = {STRIKE: 6, BASH: 8, ANGER: 6, BLUDGEON: 32, DISMANTLE: 8, IRON_WAVE: 5, CINDER: 18, HEMOKINESIS: 15, UNRELENTING: 14, GIANT_ROCK: 16, BREAKTHROUGH: 9, FEED: 10, BYRD_SWOOP: 14, PILLAGE: 6}
# Cards that require an enemy target because they deal damage.
ATTACKS = {STRIKE, BASH, ANGER, BLUDGEON, DISMANTLE, BULLY, IRON_WAVE, CINDER, ASHEN_STRIKE, HEMOKINESIS, PERFECTED_STRIKE, UNRELENTING, GIANT_ROCK, BREAKTHROUGH, WHIRLWIND, FEED, BYRD_SWOOP, PILLAGE}
# Self-targeting skills and powers that never need a target.
UNTARGETED = {DEFEND, SHRUG, BATTLE_TRANCE, SLIMED, FRANTIC_ESCAPE, RELAX, INFLAME, PRIMAL_FORCE, BLOODLETTING, EQUILIBRIUM}
SELF_DAMAGE = {HEMOKINESIS: 2, BLOODLETTING: 3, BREAKTHROUGH: 1}
EXHAUSTS = {ASHEN_STRIKE, RELAX, TREMBLE, FEED, DOMINATE}
# Cards tagged as Strike, used by Perfected Strike scaling.
STRIKE_TAGGED = {STRIKE, PERFECTED_STRIKE, ASHEN_STRIKE}


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
    turn: int = 1
    exhaust_pile: tuple[str, ...] = ()

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


def _amount(expression: str, values: dict) -> int:
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
    return replace(enemy, move=_resolve_move(enemy, spec, rng))


def legal_actions(combat: Combat) -> tuple[str, ...]:
    if combat.terminal:
        return ()
    actions = []
    for card in dict.fromkeys(combat.hand):
        if card == WHIRLWIND:
            if combat.energy > 0:
                actions.extend(f"{card}@{index}" for index, enemy in enumerate(combat.enemies) if enemy.alive)
            continue
        if card not in CARD_COST or CARD_COST[card] > combat.energy:
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
    return replace(enemy, block=enemy.block - blocked, hp=enemy.hp - unblocked, powers=powers)


def _enemy_turn(combat: Combat, index: int, data: dict, rng: random.Random) -> Combat:
    enemy = replace(combat.enemies[index], block=0)
    if not enemy.alive:
        return combat
    spec, move_id, move = _specs(data)[enemy.model], enemy.move, _state(_specs(data)[enemy.model], enemy.move)
    values, player_hp, player_block = _dict(enemy.values), combat.player_hp, combat.player_block
    sandpit = _power(enemy.powers, "SandpitPower")
    if sandpit:
        if sandpit == 1:
            return replace(combat, player_hp=0)
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", -1))
    player_powers, discard, draw = combat.player_powers, combat.discard_pile, combat.draw_pile
    enemies = list(combat.enemies)
    attack_intent = next((intent for intent in move.get("intents", ()) if "damage" in intent), {})
    for effect in move.get("effects", ()):
        command = effect["command"]
        if command == "DamageCmd.Attack":
            damage = int(attack_intent["damage"]) + _power(enemy.powers, "StrengthPower")
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
                player_hp -= damage - blocked
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
            discard += (card,) * count
        elif command == "CreatureCmd.Add":
            enemies.append(_summon(effect["model"], data, rng))
        elif command in {"CreatureCmd.Kill", "CreatureCmd.SetMaxAndCurrentHp"}:
            raise NotImplementedError(f"effect: {spec['class']}.{move['id']} {command}")
    enemy = replace(enemy, history=enemy.history + (enemy.move,))
    enemy = replace(enemy, move=_resolve_move(enemy, spec, rng, move.get("next")))
    if enemy.model == "MONSTER.THE_INSATIABLE" and move_id == "LIQUIFY_GROUND_MOVE":
        enemy = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", 4))
        draw += (FRANTIC_ESCAPE,) * 3
        discard += (FRANTIC_ESCAPE,) * 3
    enemies[index] = enemy
    return replace(combat, player_hp=player_hp, player_block=player_block, player_powers=player_powers, discard_pile=discard, draw_pile=draw, enemies=tuple(enemies))


def step(combat: Combat, action: str, data: dict, rng: random.Random) -> Combat:
    if action not in legal_actions(combat):
        raise ValueError(f"illegal action: {action}")
    if action == END_TURN:
        for index in range(len(combat.enemies)):
            combat = _enemy_turn(combat, index, data, rng)
        enemies = list(combat.enemies)
        for index, enemy in enumerate(enemies):
            # IllusionPower minions (e.g. Parafright) revive at full health after the enemy phase.
            if not enemy.alive and _power(enemy.powers, "IllusionPower"):
                enemies[index] = replace(enemy, hp=int(_dict(enemy.values).get("MaxInitialHp", 0)))
        combat = replace(combat, enemies=tuple(enemies))
        hand, draw, discard = _draw(combat.draw_pile, combat.discard_pile + combat.hand, 5, rng)
        return replace(combat, hand=hand, draw_pile=draw, discard_pile=discard, player_block=0, energy=3, turn=combat.turn + 1)

    card, _, target = action.partition("@")
    hand = list(combat.hand)
    hand.remove(card)
    if card == BATTLE_TRANCE:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 3, rng)
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard + (card,))
    if card == SLIMED:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard, energy=combat.energy - 1)
    if card == FRANTIC_ESCAPE:
        enemies = list(combat.enemies)
        for index, enemy in enumerate(enemies):
            if _power(enemy.powers, "SandpitPower"):
                enemies[index] = replace(enemy, powers=_add_power(enemy.powers, "SandpitPower", 1))
                break
        return replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile + (card,), energy=combat.energy - 1, enemies=tuple(enemies))
    if card == SHRUG:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
        block = 8 * 3 // 4 if _power(combat.player_powers, "FrailPower") else 8
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard + (card,), energy=combat.energy - 1, player_block=combat.player_block + block)
    spent = combat.energy if card == WHIRLWIND else CARD_COST[card]
    whirlwind_damage = 5 * combat.energy if card == WHIRLWIND else 0
    energy = combat.energy - spent + (2 if card == BLOODLETTING else 0)
    player_hp = combat.player_hp - SELF_DAMAGE.get(card, 0)
    player_powers = combat.player_powers
    if card == INFLAME:
        player_powers = _add_power(player_powers, "StrengthPower", 2)
    if card == PRIMAL_FORCE:
        hand = [GIANT_ROCK if card_name in ATTACKS else card_name for card_name in hand]
    exhaust = card in EXHAUSTS
    exhaust_before = combat.exhaust_pile
    exhaust_pile = exhaust_before + ((card,) if exhaust else ())
    combat = replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile + (() if exhaust else (card,)), exhaust_pile=exhaust_pile, energy=energy, player_hp=player_hp, player_powers=player_powers)
    if card in {DEFEND, IRON_WAVE, EQUILIBRIUM}:
        base = 13 if card == EQUILIBRIUM else 5
        block = base * 3 // 4 if _power(combat.player_powers, "FrailPower") else base
        combat = replace(combat, player_block=combat.player_block + block)
    if card in {DEFEND, EQUILIBRIUM}:
        return combat
    if card == RELAX:
        block = 15 * 3 // 4 if _power(combat.player_powers, "FrailPower") else 15
        return replace(combat, player_block=combat.player_block + block)
    if card in {INFLAME, PRIMAL_FORCE, BLOODLETTING}:
        return combat
    enemies = list(combat.enemies)
    if card in {BREAKTHROUGH, WHIRLWIND}:
        damage = (9 if card == BREAKTHROUGH else whirlwind_damage) + _power(combat.player_powers, "StrengthPower")
        if _power(combat.player_powers, "WeakPower"):
            damage = damage * 3 // 4
        for index, enemy in enumerate(enemies):
            if not enemy.alive:
                continue
            scaled = damage * 3 // 2 if _power(enemy.powers, "VulnerablePower") else damage
            enemies[index] = _damage_enemy(enemy, scaled)
        return replace(combat, enemies=tuple(enemies))
    if card == TREMBLE:
        enemy = enemies[int(target)]
        enemies[int(target)] = replace(enemy, powers=_add_power(enemy.powers, "VulnerablePower", 3))
        return replace(combat, enemies=tuple(enemies))
    if card == DOMINATE:
        # Apply 1 Vulnerable, then gain Strength equal to the target's (post-apply) Vulnerable.
        enemy = enemies[int(target)]
        enemies[int(target)] = replace(enemy, powers=_add_power(enemy.powers, "VulnerablePower", 1))
        gained = _power(enemies[int(target)].powers, "VulnerablePower")
        return replace(combat, enemies=tuple(enemies), player_powers=_add_power(combat.player_powers, "StrengthPower", gained))
    enemy = enemies[int(target)]
    if card == PERFECTED_STRIKE:
        strikes = sum(1 for name in combat.hand + combat.draw_pile + combat.discard_pile + combat.exhaust_pile if name in STRIKE_TAGGED)
        damage = 6 + 2 * strikes
    elif card == ASHEN_STRIKE:
        damage = 6 + 3 * len(exhaust_before)
    else:
        damage = 4 + 2 * _power(enemy.powers, "VulnerablePower") if card == BULLY else CARD_DAMAGE[card]
    damage += _power(combat.player_powers, "StrengthPower")
    if card == DISMANTLE and _power(enemy.powers, "VulnerablePower"):
        damage *= 2
    if _power(combat.player_powers, "WeakPower"):
        damage = damage * 3 // 4
    if _power(enemy.powers, "VulnerablePower"):
        damage = damage * 3 // 2
    enemies[int(target)] = _damage_enemy(enemy, damage)
    if card == CINDER and hand:
        sacrificed = hand.pop(rng.randrange(len(hand)))
        combat = replace(combat, hand=tuple(hand), exhaust_pile=combat.exhaust_pile + (sacrificed,))
    player_powers = combat.player_powers
    if _power(player_powers, "SurroundedRight") and _power(enemy.powers, "BackAttackLeftPower"):
        player_powers = _add_power(_add_power(player_powers, "SurroundedRight", -1), "SurroundedLeft", 1)
    elif _power(player_powers, "SurroundedLeft") and _power(enemy.powers, "BackAttackRightPower"):
        player_powers = _add_power(_add_power(player_powers, "SurroundedLeft", -1), "SurroundedRight", 1)
    if card == BASH:
        enemies[int(target)] = replace(enemies[int(target)], powers=_add_power(enemies[int(target)].powers, "VulnerablePower", 2))
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
    return replace(combat, enemies=tuple(enemies), player_powers=player_powers)


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
    return prevented + dealt + min(blocked, exposed) + upkeep


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
            # Credit prevented damage: enemies dead after the first step were about to hit us.
            prevented = sum(_enemy_attack_damage(before, data) for before, after in zip(combat.enemies, state.enemies) if before.alive and not after.alive and not after.escaped)
            for _ in range(60):
                if state.terminal:
                    break
                state = step(state, _greedy_action(state, data), data, rng)
            # An enemy that fled (e.g. Thieving Hopper) ends the fight but is NOT a win.
            won = not any(enemy.alive for enemy in state.enemies) and not any(enemy.escaped for enemy in state.enemies)
            # Win/loss dominates; HP and prevented damage break ties so noisy rollouts still rank correctly.
            scores.append((1 if won else -1 if state.player_hp <= 0 else 0) + state.player_hp / 100 + prevented / 100)
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
