from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from dataclasses import dataclass, replace


STRIKE = "Strike"
DEFEND = "Defend"
BASH = "Bash"
END_TURN = "End turn"
STARTING_DECK = (STRIKE,) * 5 + (DEFEND,) * 4 + (BASH,)


@dataclass(frozen=True)
class State:
    player_hp: int
    enemy_hp: int
    enemy_attack: int
    hand: tuple[str, ...]
    draw_pile: tuple[str, ...] = ()
    discard_pile: tuple[str, ...] = ()
    player_block: int = 0
    enemy_block: int = 0
    enemy_vulnerable: int = 0
    energy: int = 3
    turn: int = 1
    enemy_strength: int = 0
    enemy_state: str = ""
    enemy_history: tuple[str, ...] = ()

    @property
    def terminal(self) -> bool:
        return self.player_hp <= 0 or self.enemy_hp <= 0


CARD_COST = {STRIKE: 1, DEFEND: 1, BASH: 2}


def legal_actions(state: State) -> tuple[str, ...]:
    if state.terminal:
        return ()
    cards = tuple(dict.fromkeys(card for card in state.hand if CARD_COST[card] <= state.energy))
    return cards + (END_TURN,)


def _draw(
    draw_pile: tuple[str, ...], discard_pile: tuple[str, ...], count: int, rng: random.Random
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    draw = list(draw_pile)
    discard = list(discard_pile)
    hand: list[str] = []
    while len(hand) < count and (draw or discard):
        if not draw:
            draw, discard = discard, []
        hand.append(draw.pop(rng.randrange(len(draw))))
    return tuple(hand), tuple(draw), tuple(discard)


def _amount(expression: str, enemy: dict) -> int:
    value = expression.removesuffix("m")
    if value.lstrip("-").isdigit():
        return int(value)
    return int(enemy["values"][value])


def _enemy_attack(state: State, enemy: dict | None) -> int:
    if not enemy:
        return state.enemy_attack
    move = next(item for item in enemy["states"] if item["id"] == state.enemy_state)
    return sum(
        (int(intent["damage"]) + state.enemy_strength) * int(intent.get("repeats", 1))
        for intent in move.get("intents", ())
        if "damage" in intent
    )


def _next_enemy_state(state: State, enemy: dict, rng: random.Random) -> str:
    states = {item["id"]: item for item in enemy["states"]}
    next_id = states[state.enemy_state].get("next")
    while next_id and states[next_id]["type"] != "MoveState":
        branch = states[next_id]
        if branch["type"] != "RandomBranchState":
            raise NotImplementedError(f"runtime conditional branch: {enemy['class']}.{next_id}")
        choices = []
        for option in branch["branches"]:
            history = state.enemy_history
            repeat = option["repeat"]
            allowed = repeat == "CanRepeatForever"
            allowed |= repeat == "CannotRepeat" and (not history or history[-1] != option["state"])
            allowed |= repeat == "UseOnlyOnce" and option["state"] not in history
            if repeat == "CanRepeatXTimes":
                consecutive = next((i for i, item in enumerate(reversed(history), 1) if item != option["state"]), len(history) + 1) - 1
                allowed = consecutive < option["max_times"]
            if option["cooldown"] and option["state"] in history[-option["cooldown"] :]:
                allowed = False
            if allowed and option["weight"]:
                choices.append((option["state"], float(option["weight"])))
        roll = rng.random() * sum(weight for _, weight in choices)
        for next_id, weight in choices:
            roll -= weight
            if roll <= 0:
                break
    if not next_id:
        raise ValueError(f"enemy state has no successor: {enemy['class']}.{state.enemy_state}")
    return next_id


def step(state: State, action: str, rng: random.Random, enemy: dict | None = None) -> State:
    if action not in legal_actions(state):
        raise ValueError(f"illegal action: {action}")

    if action == END_TURN:
        damage = max(0, _enemy_attack(state, enemy) - state.player_block)
        strength = state.enemy_strength
        next_enemy_state = state.enemy_state
        history = state.enemy_history
        if enemy:
            move = next(item for item in enemy["states"] if item["id"] == state.enemy_state)
            for effect in move.get("effects", ()):
                if effect["command"] == "PowerCmd.Apply" and effect.get("model") == "StrengthPower" and effect["target"] == "base.Creature":
                    strength += _amount(effect["amount"], enemy)
            history += (state.enemy_state,)
            next_enemy_state = _next_enemy_state(replace(state, enemy_history=history), enemy, rng)
        hand, draw, discard = _draw(
            state.draw_pile,
            state.discard_pile + state.hand,
            5,
            rng,
        )
        return replace(
            state,
            player_hp=state.player_hp - damage,
            player_block=0,
            enemy_block=0,
            enemy_vulnerable=max(0, state.enemy_vulnerable - 1),
            energy=3,
            hand=hand,
            draw_pile=draw,
            discard_pile=discard,
            turn=state.turn + 1,
            enemy_strength=strength,
            enemy_state=next_enemy_state,
            enemy_history=history,
        )

    hand = list(state.hand)
    hand.remove(action)
    next_state = replace(
        state,
        energy=state.energy - CARD_COST[action],
        hand=tuple(hand),
        discard_pile=state.discard_pile + (action,),
    )
    if action == DEFEND:
        return replace(next_state, player_block=next_state.player_block + 5)

    raw_damage = 6 if action == STRIKE else 8
    damage = raw_damage * 3 // 2 if state.enemy_vulnerable else raw_damage
    blocked = min(state.enemy_block, damage)
    next_state = replace(
        next_state,
        enemy_block=state.enemy_block - blocked,
        enemy_hp=state.enemy_hp - (damage - blocked),
    )
    return replace(next_state, enemy_vulnerable=state.enemy_vulnerable + 2) if action == BASH else next_state


@dataclass
class _Stats:
    visits: int = 0
    value: float = 0.0

    @property
    def mean(self) -> float:
        return self.value / self.visits if self.visits else float("-inf")


def _score(state: State) -> float:
    if state.enemy_hp <= 0:
        return 1 + state.player_hp / 1_000 - state.turn / 10_000
    if state.player_hp <= 0:
        return -1 - state.enemy_hp / 1_000
    return (state.player_hp - state.enemy_hp) / 1_000 - state.turn / 10_000


def _rollout(state: State, rng: random.Random, depth: int, enemy: dict | None) -> float:
    for _ in range(depth):
        if state.terminal:
            break
        actions = legal_actions(state)
        playable = actions[:-1]
        action = rng.choice(playable) if playable else END_TURN
        state = step(state, action, rng, enemy)
    return _score(state)


def _simulate(
    state: State,
    stats: dict[tuple[State, str], _Stats],
    rng: random.Random,
    depth: int,
    enemy: dict | None,
) -> float:
    if state.terminal or depth == 0:
        return _score(state)

    actions = legal_actions(state)
    unvisited = [action for action in actions if not stats[state, action].visits]
    if unvisited:
        action = rng.choice(unvisited)
        value = _rollout(step(state, action, rng, enemy), rng, depth - 1, enemy)
    else:
        total = sum(stats[state, action].visits for action in actions)
        action = max(
            actions,
            key=lambda candidate: stats[state, candidate].mean
            + 0.1 * math.sqrt(math.log(total) / stats[state, candidate].visits),
        )
        value = _simulate(step(state, action, rng, enemy), stats, rng, depth - 1, enemy)

    result = stats[state, action]
    result.visits += 1
    result.value += value
    return value


def search(state: State, simulations: int = 5_000, seed: int = 0, enemy: dict | None = None) -> list[tuple[str, int, float]]:
    if state.terminal:
        return []
    rng = random.Random(seed)
    stats: dict[tuple[State, str], _Stats] = defaultdict(_Stats)
    for _ in range(simulations):
        _simulate(state, stats, rng, depth=60, enemy=enemy)
    return sorted(
        ((action, stats[state, action].visits, stats[state, action].mean) for action in legal_actions(state)),
        key=lambda result: (result[1], result[2]),
        reverse=True,
    )


def initial_state(enemy_hp: int, enemy_attack: int, seed: int = 0) -> State:
    rng = random.Random(seed)
    hand, draw, _ = _draw(STARTING_DECK, (), 5, rng)
    return State(80, enemy_hp, enemy_attack, hand, draw)


def load_enemy(path: str, name: str) -> dict:
    with open(path, encoding="utf-8-sig") as file:
        monsters = json.load(file)["monsters"]
    normalized = name.lower().replace("_", "").replace("-", "")
    matches = [monster for monster in monsters if monster["class"].lower() == normalized]
    if len(matches) != 1:
        raise ValueError(f"enemy not found: {name}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal Ironclad combat search")
    parser.add_argument("--enemy-hp", type=int, default=40)
    parser.add_argument("--enemy-attack", type=int, default=8)
    parser.add_argument("--simulations", type=int, default=5_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--enemy-data")
    parser.add_argument("--enemy")
    args = parser.parse_args()
    enemy = load_enemy(args.enemy_data, args.enemy) if args.enemy_data and args.enemy else None
    state = initial_state(args.enemy_hp, args.enemy_attack, args.seed)
    if enemy:
        rng = random.Random(args.seed)
        state = replace(
            state,
            enemy_hp=rng.randint(enemy["values"]["MinInitialHp"], enemy["values"]["MaxInitialHp"]),
            enemy_state=enemy["initial_state"],
        )
    print(f"turn={state.turn} hp={state.player_hp} enemy={state.enemy_hp} incoming={_enemy_attack(state, enemy)}")
    print(f"hand={', '.join(state.hand)}")
    for action, visits, value in search(state, args.simulations, args.seed, enemy):
        print(f"{action:8} visits={visits:5} value={value:9.5f}")


if __name__ == "__main__":
    main()
