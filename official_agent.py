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
    "CARD.ANGER": "Anger",
    "CARD.BLUDGEON": "Bludgeon",
    "CARD.SHRUG_IT_OFF": "Shrug It Off",
    "CARD.BATTLE_TRANCE": "Battle Trance",
}
POWER_NAMES = {
    "POWER.FRAIL": "FrailPower",
    "POWER.SLIPPERY_POWER": "SlipperyPower",
    "POWER.STRENGTH": "StrengthPower",
    "POWER.VULNERABLE": "VulnerablePower",
    "POWER.WEAK": "WeakPower",
}


def choose(observation: dict, enemy_data: dict | None = None, simulations: int = 0) -> dict:
    if observation.get("phase") == "map":
        return choose_map(observation)
    if observation.get("phase") == "card_reward":
        return choose_card_reward(observation)
    if observation.get("phase") == "rest":
        return choose_rest(observation)
    actions = observation["legal_actions"]
    cards = [action for action in actions if action["type"] == "card"]
    # ponytail: rollouts cover starter cards and core combat powers; extend these mappings when reward-card search begins.
    if enemy_data and simulations and all(card["card_id"] in CARD_NAMES for card in cards):
        try:
            return rollout_choice(observation, actions, enemy_data, simulations)
        except (KeyError, ValueError, NotImplementedError):
            pass
    enemy_hp = {enemy["combat_id"]: enemy["hp"] for enemy in observation.get("enemies", ())}
    damage = {"CARD.STRIKE_IRONCLAD": 6, "CARD.BASH": 8}
    lethal = [action for action in cards if action.get("target_id") in enemy_hp and enemy_hp[action["target_id"]] <= damage.get(action["card_id"], 0)]
    if lethal:
        return lethal[0]
    incoming = sum(intent.get("damage", 0) * max(1, intent.get("repeats", 1)) for enemy in observation.get("enemies", ()) for intent in enemy.get("intents") or ())
    defenses = [action for action in cards if action["card_id"] == "CARD.DEFEND_IRONCLAD"]
    if observation.get("player", {}).get("block", 0) < incoming and defenses:
        return defenses[0]
    priority = {"CARD.BASH": 4, "CARD.STRIKE_IRONCLAD": 3, "CARD.DEFEND_IRONCLAD": 2}
    if cards:
        return max(cards, key=lambda action: priority.get(action["card_id"], 1))
    return next(action for action in actions if action["type"] == "end_turn")


def choose_map(observation: dict) -> dict:
    points = {(point["col"], point["row"]): point for point in observation["map"]["points"]}
    room_value = {"Ancient": 0, "Monster": 1, "Unknown": 1, "Shop": 1, "RestSite": 3, "Treasure": 3, "Elite": -5, "Boss": 0}
    memo: dict[tuple[int, int], int] = {}

    def value(coord: tuple[int, int]) -> int:
        if coord in memo:
            return memo[coord]
        point = points[coord]
        children = [(child["col"], child["row"]) for child in point["children"]]
        memo[coord] = room_value.get(point["type"], 0) + (max(map(value, children)) if children else 0)
        return memo[coord]

    return max(observation["legal_actions"], key=lambda action: value((action["col"], action["row"])))


def choose_card_reward(observation: dict) -> dict:
    actions = [action for action in observation["legal_actions"] if action["type"] == "card_reward"]
    priority = {
        "CARD.BLUDGEON": 10,
        "CARD.BATTLE_TRANCE": 8,
        "CARD.SHRUG_IT_OFF": 7,
        "CARD.ANGER": 6,
    }
    selected = max(actions, key=lambda action: priority.get(action["card_id"], 0))
    if priority.get(selected["card_id"], 0):
        return selected
    return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")


def choose_rest(observation: dict) -> dict:
    actions = observation["legal_actions"]
    hp, max_hp = observation["player"]["hp"], observation["player"]["max_hp"]
    if hp < max_hp:
        heal = next((action for action in actions if action["option_id"] == "HEAL"), None)
        if heal:
            return heal
    return next((action for action in actions if action["option_id"] == "SMITH"), actions[0])


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
