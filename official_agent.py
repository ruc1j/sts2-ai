from __future__ import annotations

import argparse
import json
import os
import time

from combat import Combat, Enemy, search


CARD_NAMES = {
    "CARD.STRIKE_IRONCLAD": "Strike",
    "CARD.DEFEND_IRONCLAD": "Defend",
    "CARD.BASH": "Bash",
}
POWER_NAMES = {
    "POWER.FRAIL": "FrailPower",
    "POWER.STRENGTH": "StrengthPower",
    "POWER.VULNERABLE": "VulnerablePower",
    "POWER.WEAK": "WeakPower",
}


def choose(observation: dict, enemy_data: dict | None = None, simulations: int = 0) -> dict:
    actions = observation["legal_actions"]
    cards = [action for action in actions if action["type"] == "card"]
    # ponytail: rollouts cover starter cards and core combat powers; extend these mappings when reward-card search begins.
    if enemy_data and simulations and all(card["id"] in CARD_NAMES for card in observation["hand"]):
        try:
            return rollout_choice(observation, actions, enemy_data, simulations)
        except (KeyError, ValueError, NotImplementedError):
            pass
    priority = {"CARD.BASH": 4, "CARD.STRIKE_IRONCLAD": 3, "CARD.DEFEND_IRONCLAD": 2}
    if cards:
        return max(cards, key=lambda action: priority.get(action["card_id"], 1))
    return next(action for action in actions if action["type"] == "end_turn")


def rollout_choice(observation: dict, actions: list[dict], data: dict, simulations: int) -> dict:
    specs = {monster["id"]: monster for monster in data["monsters"]}
    enemies = []
    for observed in observation["enemies"]:
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
        player_powers=tuple(sorted((POWER_NAMES.get(power["id"], power["id"]), power["amount"]) for power in observation["player"]["powers"])),
        energy=observation["player"]["energy"],
        turn=observation["turn"],
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
    parser.add_argument("--enemy-data")
    parser.add_argument("--simulations", type=int, default=0)
    args = parser.parse_args()
    enemy_data = json.load(open(args.enemy_data, encoding="utf-8-sig")) if args.enemy_data else None
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
        time.sleep(0.025)


if __name__ == "__main__":
    main()
