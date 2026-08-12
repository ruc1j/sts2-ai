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
}
POWER_NAMES = {
    "POWER.FRAIL": "FrailPower",
    "POWER.SLIPPERY_POWER": "SlipperyPower",
    "POWER.STRENGTH": "StrengthPower",
    "POWER.VULNERABLE": "VulnerablePower",
    "POWER.WEAK": "WeakPower",
    "POWER.BACK_ATTACK_LEFT_POWER": "BackAttackLeftPower",
    "POWER.BACK_ATTACK_RIGHT_POWER": "BackAttackRightPower",
    "POWER.SURROUNDED_POWER": "SurroundedPower",
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
    potions = [action for action in actions if action["type"] == "potion"]
    sandpit = any(power["id"] == "POWER.SANDPIT_POWER" and power["amount"] > 0 for enemy in observation.get("enemies", ()) for power in enemy.get("powers", ()))
    escape = next((action for action in cards if action["card_id"] == "CARD.FRANTIC_ESCAPE"), None)
    if sandpit and escape:
        return escape
    if turn := choose_crab_facing(observation, cards):
        return turn
    if potion := choose_potion(observation, potions):
        return potion
    # ponytail: rollouts cover starter cards and core combat powers; extend these mappings when reward-card search begins.
    if enemy_data and simulations and all(card["card_id"] in CARD_NAMES for card in cards):
        try:
            return rollout_choice(observation, actions, enemy_data, simulations)
        except (KeyError, ValueError, NotImplementedError, StopIteration):
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
    hand = {card["index"]: card for card in observation.get("hand", ())}
    def score(action: dict) -> tuple[int, int]:
        card = hand.get(action.get("hand_index"), {})
        damage = max((var["value"] for var in card.get("vars", ()) if var["id"] in {"Damage", "CalculatedDamage"}), default=0)
        return priority.get(action["card_id"], 0), int(damage) if card.get("type") == "Attack" else 0
    priority = {"CARD.BASH": 4, "CARD.STRIKE_IRONCLAD": 3, "CARD.DEFEND_IRONCLAD": 2}
    if cards:
        return max(cards, key=lambda action: (priority.get(action["card_id"], 3 if hand.get(action.get("hand_index"), {}).get("type") == "Attack" else 1), score(action)[1]))
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
    enemy_damage = {enemy["combat_id"]: sum(intent.get("damage", 0) * max(1, intent.get("repeats", 1)) for intent in enemy.get("intents") or ()) for enemy in observation.get("enemies", ())}
    def use(ids: set[str], target_score: dict[int, int] | None = None) -> dict | None:
        candidates = [action for action in actions if action["potion_id"] in ids]
        return max(candidates, key=lambda action: target_score.get(action.get("target_id"), 0) if target_score else 0, default=None)
    fire = next((action for action in actions if action["potion_id"] == "POTION.FIRE_POTION" and action.get("target_id") in enemy_hp and enemy_hp[action["target_id"]] <= 20), None)
    if fire:
        return fire
    player = observation.get("player", {})
    hp, max_hp = player.get("hp", 0), player.get("max_hp", 1)
    incoming = sum(intent.get("damage", 0) * max(1, intent.get("repeats", 1)) for enemy in observation.get("enemies", ()) for intent in enemy.get("intents") or ())
    healing = {"POTION.BLOOD_POTION", "POTION.CURE_ALL"}
    blocking = {"POTION.BLOCK_POTION", "POTION.FORTIFIER"}
    defensive_buffs = {"POTION.DEXTERITY_POTION", "POTION.GHOST_IN_A_JAR", "POTION.REGEN_POTION", "POTION.LIQUID_BRONZE"}
    if incoming >= hp:
        return use({"POTION.GHOST_IN_A_JAR", "POTION.BLOCK_POTION", "POTION.FORTIFIER", "POTION.SHACKLING_POTION"}) or use({"POTION.WEAK_POTION"}, enemy_damage)
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
        return use(blocking | {"POTION.SHACKLING_POTION"}) or use({"POTION.WEAK_POTION"}, enemy_damage)
    if hp <= max_hp // 2:
        return use(healing | defensive_buffs | {"POTION.ENTROPIC_BREW"})
    if incoming >= hp // 2:
        return use(blocking | {"POTION.SHACKLING_POTION"}) or use({"POTION.WEAK_POTION"}, enemy_damage)
    if max(enemy_hp.values(), default=0) >= 100:
        return use({"POTION.STRENGTH_POTION", "POTION.FLEX_POTION", "POTION.DUPLICATOR", "POTION.DISTILLED_CHAOS", "POTION.EXPLOSIVE_AMPOULE"}) or use({"POTION.VULNERABLE_POTION", "POTION.POISON_POTION", "POTION.FIRE_POTION"}, enemy_hp)
    if not hand:
        return use({"POTION.SWIFT_POTION"})
    return None


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
    if player.get("max_hp", 0) and player.get("hp", player["max_hp"]) * 2 <= player["max_hp"]:
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

    return max(observation["legal_actions"], key=lambda action: value((action["col"], action["row"])))


def choose_card_reward(observation: dict) -> dict:
    actions = [action for action in observation["legal_actions"] if action["type"] == "card_reward"]
    priority = {
        "CARD.BLUDGEON": 10,
        "CARD.BATTLE_TRANCE": 8,
        "CARD.SHRUG_IT_OFF": 7,
        "CARD.DISMANTLE": 7,
        "CARD.BULLY": 6,
        "CARD.ANGER": 6,
    }
    selected = max(actions, key=lambda action: priority.get(action["card_id"], 0))
    if priority.get(selected["card_id"], 0):
        return selected
    return next(action for action in observation["legal_actions"] if action.get("option_id") == "Skip")


def choose_rest(observation: dict) -> dict:
    actions = observation["legal_actions"]
    hp, max_hp = observation["player"]["hp"], observation["player"]["max_hp"]
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
