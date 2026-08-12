from __future__ import annotations

import argparse
import ast
import json
import random
import re
from dataclasses import dataclass, replace


STRIKE, DEFEND, BASH, ANGER, BLUDGEON, SHRUG, BATTLE_TRANCE, END_TURN = "Strike", "Defend", "Bash", "Anger", "Bludgeon", "Shrug It Off", "Battle Trance", "End turn"
STARTING_DECK = (STRIKE,) * 5 + (DEFEND,) * 4 + (BASH,)
CARD_COST = {STRIKE: 1, DEFEND: 1, BASH: 2, ANGER: 0, BLUDGEON: 3, SHRUG: 1, BATTLE_TRANCE: 0}
CARD_DAMAGE = {STRIKE: 6, BASH: 8, ANGER: 6, BLUDGEON: 32}


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
    return {monster["id"]: monster for monster in data["monsters"]}


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
        enemies.append(replace(enemy, move=_resolve_move(enemy, spec, rng)))
    hand, draw, _ = _draw(STARTING_DECK, (), 5, rng)
    return Combat(player_hp, hand, draw, (), tuple(enemies))


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
        if card not in CARD_COST or CARD_COST[card] > combat.energy:
            continue
        if card in {DEFEND, SHRUG, BATTLE_TRANCE}:
            actions.append(card)
        else:
            actions.extend(f"{card}@{index}" for index, enemy in enumerate(combat.enemies) if enemy.alive)
    return tuple(actions) + (END_TURN,)


def _damage_enemy(enemy: Enemy, damage: int) -> Enemy:
    if _power(enemy.powers, "SlipperyPower"):
        return replace(enemy, hp=enemy.hp - 1, powers=_add_power(enemy.powers, "SlipperyPower", -1))
    blocked = min(enemy.block, damage)
    return replace(enemy, block=enemy.block - blocked, hp=enemy.hp - damage + blocked)


def _enemy_turn(combat: Combat, index: int, data: dict, rng: random.Random) -> Combat:
    enemy = replace(combat.enemies[index], block=0)
    if not enemy.alive:
        return combat
    spec, move = _specs(data)[enemy.model], _state(_specs(data)[enemy.model], enemy.move)
    values, player_hp, player_block = _dict(enemy.values), combat.player_hp, combat.player_block
    player_powers, discard, draw = combat.player_powers, combat.discard_pile, combat.draw_pile
    enemies = list(combat.enemies)
    attack_intent = next((intent for intent in move.get("intents", ()) if "damage" in intent), {})
    for effect in move.get("effects", ()):
        command = effect["command"]
        if command == "DamageCmd.Attack":
            damage = int(attack_intent["damage"]) + _power(enemy.powers, "StrengthPower")
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
            amount = _amount(effect["amount"], values)
            if effect["target"] == "base.Creature":
                enemy = replace(enemy, powers=_add_power(enemy.powers, effect["model"], amount))
            elif effect["target"] == "targets":
                player_powers = _add_power(player_powers, effect["model"], amount)
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
            count = _amount(effect["arguments"][-2], values) if len(effect["arguments"]) > 2 else 1
            discard += (card,) * count
        elif command == "CreatureCmd.Add":
            enemies.append(_summon(effect["model"], data, rng))
        elif command in {"CreatureCmd.Kill", "CreatureCmd.SetMaxAndCurrentHp"}:
            raise NotImplementedError(f"effect: {spec['class']}.{move['id']} {command}")
    enemy = replace(enemy, history=enemy.history + (enemy.move,))
    enemy = replace(enemy, move=_resolve_move(enemy, spec, rng, move.get("next")))
    enemies[index] = enemy
    return replace(combat, player_hp=player_hp, player_block=player_block, player_powers=player_powers, discard_pile=discard, draw_pile=draw, enemies=tuple(enemies))


def step(combat: Combat, action: str, data: dict, rng: random.Random) -> Combat:
    if action not in legal_actions(combat):
        raise ValueError(f"illegal action: {action}")
    if action == END_TURN:
        for index in range(len(combat.enemies)):
            combat = _enemy_turn(combat, index, data, rng)
        hand, draw, discard = _draw(combat.draw_pile, combat.discard_pile + combat.hand, 5, rng)
        return replace(combat, hand=hand, draw_pile=draw, discard_pile=discard, player_block=0, energy=3, turn=combat.turn + 1)

    card, _, target = action.partition("@")
    hand = list(combat.hand)
    hand.remove(card)
    if card == BATTLE_TRANCE:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 3, rng)
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard + (card,))
    if card == SHRUG:
        drawn, draw, discard = _draw(combat.draw_pile, combat.discard_pile, 1, rng)
        block = 8 * 3 // 4 if _power(combat.player_powers, "FrailPower") else 8
        return replace(combat, hand=tuple(hand) + drawn, draw_pile=draw, discard_pile=discard + (card,), energy=combat.energy - 1, player_block=combat.player_block + block)
    combat = replace(combat, hand=tuple(hand), discard_pile=combat.discard_pile + (card,), energy=combat.energy - CARD_COST[card])
    if card == DEFEND:
        block = 5 * 3 // 4 if _power(combat.player_powers, "FrailPower") else 5
        return replace(combat, player_block=combat.player_block + block)
    enemies = list(combat.enemies)
    enemy = enemies[int(target)]
    damage = CARD_DAMAGE[card]
    if _power(combat.player_powers, "WeakPower"):
        damage = damage * 3 // 4
    if _power(enemy.powers, "VulnerablePower"):
        damage = damage * 3 // 2
    enemies[int(target)] = _damage_enemy(enemy, damage)
    if card == BASH:
        enemies[int(target)] = replace(enemies[int(target)], powers=_add_power(enemies[int(target)].powers, "VulnerablePower", 2))
    if card == ANGER:
        combat = replace(combat, discard_pile=combat.discard_pile + (ANGER,))
    return replace(combat, enemies=tuple(enemies))


def search(combat: Combat, data: dict, simulations: int = 5000, seed: int = 0) -> list[tuple[str, float]]:
    rng = random.Random(seed)
    results = []
    for action in legal_actions(combat):
        scores = []
        for _ in range(max(1, simulations // len(legal_actions(combat)))):
            state = step(combat, action, data, rng)
            for _ in range(60):
                if state.terminal:
                    break
                actions = legal_actions(state)
                state = step(state, rng.choice(actions[:-1]) if actions[:-1] else END_TURN, data, rng)
            won = not any(enemy.alive for enemy in state.enemies)
            scores.append((1 if won else -1 if state.player_hp <= 0 else 0) + state.player_hp / 1000)
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
