import json
import os
import random
import tempfile
import unittest
from unittest.mock import patch

from official_agent import CARD_NAMES, CARD_TIERS, SHOP_POTION_SCORES, DEFENSE_PRIORITY, NEOW_RELIC_PRIORITY, POWER_NAMES, POTION_BLOCK, POTION_EXPLOSIVE, POTION_FIRE, RELIC_SCORES, STRONG_BLOCK_CARDS, _rollout_allowed_potions, choose, choose_card_reward, choose_event, choose_map, choose_potion, choose_rest, choose_shop, rollout_choice
from combat import BURN, Card, DAZED, END_TURN, INFECTION, TOXIC, legal_actions as combat_legal_actions, step


class OfficialAgentTest(unittest.TestCase):
    def test_maps_ceremonial_beast_plow_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.PLOW_POWER"], "PlowPower")

    def test_maps_ceremonial_beast_ringing_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.RINGING_POWER"], "RingingPower")

    def test_maps_waterfall_steam_eruption_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.STEAM_ERUPTION_POWER"], "SteamEruptionPower")

    def test_maps_player_powers_from_official_ids_for_rollouts(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY", "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "turn": 1,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 3,
                "powers": [
                    {"id": "POWER.BARRICADE_POWER", "amount": 1},
                    {"id": "POWER.BLOCK_NEXT_TURN_POWER", "amount": 10},
                    {"id": "POWER.COLOSSUS_POWER", "amount": 1},
                    {"id": "POWER.HELLRAISER_POWER", "amount": 1},
                ],
            },
            "hand": [], "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["powers"] = dict(state.player_powers)
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(
            captured["powers"],
            {
                "BarricadePower": 1,
                "BlockNextTurnPower": 10,
                "ColossusPower": 1,
                "HellraiserPower": 1,
            },
        )

    def test_maps_inferno_and_cruelty_into_rollout_cards_and_powers(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY", "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "turn": 1,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 3,
                "powers": [
                    {"id": "POWER.INFERNO_POWER", "amount": 6},
                    {"id": "POWER.CRUELTY_POWER", "amount": 25},
                ],
            },
            "hand": [
                {"index": 0, "id": "CARD.INFERNO", "type": "Power", "cost": 1},
                {"index": 1, "id": "CARD.CRUELTY", "type": "Power", "cost": 1},
            ],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.INFERNO", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.CRUELTY", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["hand"] = state.hand
            captured["powers"] = dict(state.player_powers)
            captured["legal_actions"] = combat_legal_actions(state)
            return [(END_TURN, 0.0)]

        with patch("official_agent.search", side_effect=capture):
            selected = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["hand"], (Card("Inferno"), Card("Cruelty")))
        self.assertEqual(captured["powers"], {"InfernoPower": 6, "CrueltyPower": 25})
        self.assertIn("card:0", captured["legal_actions"])
        self.assertIn("card:1", captured["legal_actions"])
        self.assertEqual(selected["type"], "end_turn")

    def test_soar_power_normalizes_from_official_id_for_rollout_state(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY", "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "turn": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [], "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 40, "block": 0,
                "powers": [{"id": "POWER.SOAR_POWER", "amount": 1}],
                "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["powers"] = dict(state.enemies[0].powers)
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["powers"], {"SoarPower": 1})

    def test_frail_power_normalizes_from_official_id_for_rollout_state(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY", "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "turn": 1,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 1,
                "powers": [{"id": "POWER.FRAIL_POWER", "amount": 2}],
            },
            "hand": [], "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 40, "block": 0, "powers": [],
                "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["powers"] = dict(state.player_powers)
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["powers"], {"FrailPower": 2})

    def test_waterfall_steam_power_uses_official_id_in_rollout_state(self) -> None:
        with open("data/enemies_underdocks.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1,
            "turn": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 2, "id": "MONSTER.WATERFALL_GIANT", "hp": 5, "block": 0,
                "powers": [{"id": "POWER.STEAM_ERUPTION_POWER", "amount": 3}],
                "intents": [], "move": "PRESSURIZE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "target_id": 2}, {"type": "end_turn"}],
        }
        captured = {}

        def capture(state, enemy_data, _simulations, _seed):
            captured["power"] = dict(state.enemies[0].powers)
            captured["after"] = step(state, "card:0@0", enemy_data, random.Random(0))
            return [("Strike@0", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            selected = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["power"]["SteamEruptionPower"], 3)
        self.assertEqual(
            (captured["after"].enemies[0].hp, captured["after"].enemies[0].move, captured["after"].terminal),
            (999999999, "ABOUT_TO_BLOW_MOVE", False),
        )
        self.assertEqual((selected["target_id"], selected["simulations"]), (2, 1))

    def test_rollout_preserves_waterfall_steam_damage_from_observed_explode_intent(self) -> None:
        with open("data/enemies_underdocks.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 2,
            "turn": 3,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 3,
                "powers": [{"id": "POWER.VULNERABLE_POWER", "amount": 1}],
            },
            "hand": [], "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 2, "id": "MONSTER.WATERFALL_GIANT", "hp": 999999999, "block": 0,
                "powers": [],
                "intents": [{"type": "DeathBlowIntent", "damage": 22, "raw_damage": 15, "repeats": 1}],
                "move": "EXPLODE_MOVE", "history": ["ABOUT_TO_BLOW_MOVE"], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, enemy_data, _simulations, _seed):
            captured["values"] = dict(state.enemies[0].values)
            captured["after"] = step(state, END_TURN, enemy_data, random.Random(0))
            return [(END_TURN, 0.0)]

        with patch("official_agent.search", side_effect=capture):
            selected = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["values"]["SteamEruptionDamage"], 15)
        self.assertEqual((captured["after"].player_hp, captured["after"].enemies[0].hp, captured["after"].terminal), (58, 0, True))
        self.assertEqual((selected["simulations"], selected["search_value"]), (1, 0.0))

    def test_maps_insatiable_sandpit_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.SANDPIT_POWER"], "SandpitPower")

    def test_maps_kaiser_crab_rage_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.CRAB_RAGE_POWER"], "CrabRagePower")

    def test_maps_act2_enemy_powers_for_rollouts(self) -> None:
        self.assertEqual(
            {power_id: POWER_NAMES[power_id] for power_id in (
                "POWER.FLUTTER_POWER",
                "POWER.PERSONAL_HIVE_POWER",
                "POWER.SHRINK_POWER",
                "POWER.SLOW_POWER",
                "POWER.SLUMBER_POWER",
                "POWER.THORNS_POWER",
                "POWER.VITAL_SPARK_POWER",
            )},
            {
                "POWER.FLUTTER_POWER": "FlutterPower",
                "POWER.PERSONAL_HIVE_POWER": "PersonalHivePower",
                "POWER.SHRINK_POWER": "ShrinkPower",
                "POWER.SLOW_POWER": "SlowPower",
                "POWER.SLUMBER_POWER": "SlumberPower",
                "POWER.THORNS_POWER": "ThornsPower",
                "POWER.VITAL_SPARK_POWER": "VitalSparkPower",
            },
        )

    def test_maps_rage_and_spite_for_rollouts(self) -> None:
        self.assertEqual(CARD_NAMES["CARD.RAGE"], "Rage")
        self.assertEqual(CARD_NAMES["CARD.SPITE"], "Spite")
        self.assertEqual(CARD_NAMES["CARD.COLOSSUS"], "Colossus")
        self.assertEqual(CARD_NAMES["CARD.VOLLEY"], "Volley")
        self.assertEqual(POWER_NAMES["POWER.RAGE_POWER"], "RagePower")

    def test_maps_stone_armor_and_feel_no_pain_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.PLATING_POWER"], "PlatingPower")
        self.assertEqual(POWER_NAMES["POWER.FEEL_NO_PAIN_POWER"], "FeelNoPainPower")
        self.assertTrue({"CARD.STONE_ARMOR", "CARD.FEEL_NO_PAIN"} <= set(CARD_NAMES))

    def test_maps_bridge_status_cards_for_rollouts(self) -> None:
        self.assertEqual(
            {CARD_NAMES[card_id] for card_id in ("CARD.TOXIC", "CARD.BURN", "CARD.DAZED", "CARD.INFECTION")},
            {TOXIC, BURN, DAZED, INFECTION},
        )

    def test_rollout_maps_toxic_hand_card_to_turn_end_damage_model(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY", "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {"hp": 1, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.TOXIC"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["combat"].hand, (Card("Toxic"),))

    def test_maps_knowledge_demon_powers_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.DISINTEGRATION_POWER"], "DisintegrationPower")
        self.assertEqual(POWER_NAMES["POWER.MIND_ROT_POWER"], "MindRotPower")

    def test_prefers_bash(self) -> None:
        actions = [
            {"type": "end_turn"},
            {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD"},
            {"type": "card", "card_id": "CARD.BASH"},
        ]
        self.assertEqual(choose({"legal_actions": actions})["card_id"], "CARD.BASH")

    def test_blocks_incoming_damage(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD"},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD"},
            ],
            "player": {"block": 0},
            "enemies": [{"combat_id": 1, "hp": 20, "intents": [{"damage": 8, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_rage_played_before_an_affordable_attack(self) -> None:
        # D6 live trace (turn1 Act1 boss): Rage was played after Anger/Strike/Defend, forfeiting
        # the whole turn's Rage block since it only applies to Attacks played after it.
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.RAGE", "cost": 1, "type": "Skill"},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack"},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.RAGE", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 30, "block": 0, "powers": [], "intents": [], "move": "IDLE", "history": []}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.RAGE")

    def test_rage_not_forced_when_no_attack_is_affordable_after_it(self) -> None:
        # Rage costs 1 and Strike costs 2 here, so playing Rage would leave only 1 energy - not
        # enough for the Strike - meaning Rage alone would just end the turn. Don't force it.
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 2, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.RAGE", "cost": 1, "type": "Skill"},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "cost": 2, "type": "Attack"},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.RAGE", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 30, "block": 0, "powers": [], "intents": [], "move": "IDLE", "history": []}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.STRIKE_IRONCLAD")

    def test_nonurgent_rage_defers_to_rollout(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.RAGE", "cost": 1, "type": "Skill"},
                {"index": 1, "id": "CARD.PERFECTED_STRIKE", "cost": 2, "type": "Attack", "vars": [{"id": "Damage", "value": 20}]},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.RAGE", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.PERFECTED_STRIKE", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][1]
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.PERFECTED_STRIKE")
        self.assertEqual(action["decision_source"], "rollout_success")

    def test_attack_precedes_headbutt_when_discard_is_empty(self) -> None:
        observation = {
            "player": {"hp": 40, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.HEADBUTT", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 9}]},
                {"index": 1, "id": "CARD.PERFECTED_STRIKE", "cost": 2, "type": "Attack", "vars": [{"id": "CalculatedDamage", "value": 22}]},
            ],
            "discard_pile": [],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.HEADBUTT", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.PERFECTED_STRIKE", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=observation["legal_actions"][0]):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_reason"]), ("CARD.PERFECTED_STRIKE", "headbutt_setup"))

    def test_rupture_precedes_bloodletting_when_both_are_legal(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.RUPTURE", "cost": 1, "type": "Power"},
                {"index": 1, "id": "CARD.BLOODLETTING", "cost": 0, "type": "Skill", "vars": [{"id": "HpLoss", "value": 3}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.RUPTURE", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=observation["legal_actions"][1]):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_reason"]), ("CARD.RUPTURE", "rupture_before_bloodletting"))

    def test_rupture_precedes_queen_minion_focus(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.RUPTURE", "cost": 1, "type": "Power"},
                {"index": 1, "id": "CARD.BLOODLETTING", "cost": 0, "type": "Skill"},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": 100, "block": 0, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 10, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.QUEEN", "hp": 400, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.RUPTURE", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 1, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.RUPTURE", "rupture_before_queen_focus"))

        observation["player"]["powers"] = [{"id": "POWER.RUPTURE_POWER", "amount": 1}]
        observation["legal_actions"] = observation["legal_actions"][1:]
        action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.BLOODLETTING", "queen_focus_energy"))

        observation["player"]["powers"] = []
        action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.BLOODLETTING", "queen_focus_energy"))

    def test_free_inflame_precedes_attack(self) -> None:
        strike = {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1}
        observation = {
            "player": {"hp": 77, "max_hp": 91, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 9}]},
                {"index": 1, "id": "CARD.INFLAME", "cost": 0, "type": "Power"},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 321, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [strike, {"type": "card", "card_id": "CARD.INFLAME", "hand_index": 1}, {"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=strike):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.INFLAME", "free_inflame_direct"))

    def test_rage_yields_to_stronger_defense_when_incoming_exceeds_rage_block(self) -> None:
        for incoming, hp, expected in (
            (0, 30, "CARD.RAGE"),
            (4, 30, "CARD.DEFEND_IRONCLAD"),
            (8, 30, "CARD.DEFEND_IRONCLAD"),
            (12, 30, "CARD.DEFEND_IRONCLAD"),
            (30, 30, "CARD.DEFEND_IRONCLAD"),
            (8, 4, "CARD.DEFEND_IRONCLAD"),
        ):
            with self.subTest(incoming=incoming, hp=hp):
                observation = {
                    "player": {"hp": hp, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
                    "hand": [
                        {"index": 0, "id": "CARD.RAGE", "cost": 1, "type": "Skill"},
                        {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack"},
                        {"index": 2, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill"},
                    ],
                    "legal_actions": [
                        {"type": "card", "card_id": "CARD.RAGE", "hand_index": 0, "target_id": None},
                        {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                        {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 2, "target_id": None},
                        {"type": "end_turn"},
                    ],
                    "enemies": [{
                        "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "block": 0,
                        "powers": [], "intents": [{"damage": incoming, "repeats": 1}],
                    }],
                }
                self.assertEqual(choose(observation)["card_id"], expected)

    def test_rollout_cannot_choose_nonblocking_play_on_lethal_incoming(self) -> None:
        observation = {
            "seq": 1,
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 10, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack"},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill"},
            ],
            "enemies": [{"combat_id": 1, "hp": 30, "intents": [{"damage": 10, "repeats": 1}]}],
        }
        with patch("official_agent.rollout_choice", return_value=observation["legal_actions"][0]):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=1)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_unsafe_fallback_uses_free_full_draw_before_spending_energy(self) -> None:
        bash = {"type": "card", "card_id": "CARD.BASH", "hand_index": 0, "target_id": 1}
        battle_trance = {"type": "card", "card_id": "CARD.BATTLE_TRANCE", "hand_index": 1, "target_id": None}
        observation = {
            "legal_actions": [bash, battle_trance, {"type": "end_turn"}],
            "player": {"hp": 15, "max_hp": 105, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.BASH", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 20}]},
                {"index": 1, "id": "CARD.BATTLE_TRANCE", "type": "Skill", "cost": 0, "vars": [{"id": "Cards", "value": 3}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 63, "block": 0, "intents": [{"damage": 30, "repeats": 1}], "powers": []}],
        }
        with patch("official_agent.rollout_choice", return_value=bash):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.BATTLE_TRANCE")
        self.assertEqual(action["decision_reason"], "rollout_rejected_unsafe")

    def test_sandpit_taunt_precedes_free_battle_trance(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BATTLE_TRANCE", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.TAUNT", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 2, "target_id": 1},
                {"type": "end_turn"},
            ],
            "player": {"hp": 26, "max_hp": 80, "block": 0, "energy": 2, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.BATTLE_TRANCE", "type": "Skill", "cost": 0, "vars": [{"id": "Cards", "value": 4}]},
                {"index": 1, "id": "CARD.TAUNT", "type": "Skill", "cost": 1, "vars": [{"id": "Block", "value": 8}]},
                {"index": 2, "id": "CARD.BASH", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 10}]},
            ],
            "draw_pile": [{"id": "CARD.ANGER"}] * 3 + [{"id": "CARD.SHRUG_IT_OFF"}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 77, "block": 0, "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 3}], "intents": [{"damage": 12, "repeats": 2}]}],
        }
        action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.TAUNT", "sandpit_taunt_before_draw"))

    def test_rollout_guard_uses_unblocked_incoming(self) -> None:
        for hp, expected_card, expected_source in (
            (15, "CARD.STRIKE_IRONCLAD", "rollout_success"),
            (9, "CARD.DEFEND_IRONCLAD", "heuristic_fallback"),
        ):
            with self.subTest(hp=hp):
                observation = {
                    "seq": 1,
                    "legal_actions": [
                        {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                        {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                        {"type": "end_turn"},
                    ],
                    "player": {"hp": hp, "max_hp": 80, "block": 8},
                    "hand": [
                        {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack"},
                        {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill"},
                    ],
                    "enemies": [{"combat_id": 1, "hp": 30, "intents": [{"damage": 17, "repeats": 1}]}],
                }
                with patch("official_agent.rollout_choice", return_value=observation["legal_actions"][0]):
                    action = choose(observation, enemy_data={"monsters": []}, simulations=1)
                self.assertEqual(action["card_id"], expected_card)
                self.assertEqual(action["decision_source"], expected_source)
                if hp == 9:
                    self.assertEqual(action["decision_reason"], "rollout_rejected_unsafe")

    def test_rollout_allows_nonblocking_damage_mitigation(self) -> None:
        for card_id, vars_, hp, block, incoming in (
            ("CARD.UPPERCUT", [{"id": "Damage", "value": 13}, {"id": "Weak", "value": 1}], 10, 0, 10),
            ("CARD.UPPERCUT", [{"id": "Damage", "value": 13}, {"id": "Weak", "value": 1}], 7, 1, 10),
            ("CARD.MANGLE", [{"id": "Damage", "value": 15}], 10, 0, 10),
        ):
            with self.subTest(card_id=card_id):
                selected = {"type": "card", "card_id": card_id, "hand_index": 0, "target_id": 1}
                observation = {
                    "seq": 1,
                    "legal_actions": [selected, {"type": "card", "card_id": "CARD.BLUDGEON", "hand_index": 1, "target_id": 1}, {"type": "end_turn"}],
                    "player": {"hp": hp, "max_hp": 80, "block": block, "energy": 3},
                    "hand": [
                        {"index": 0, "id": card_id, "type": "Attack", "vars": vars_},
                        {"index": 1, "id": "CARD.BLUDGEON", "type": "Attack", "vars": [{"id": "Damage", "value": 32}]},
                    ],
                    "enemies": [{"combat_id": 1, "hp": 100, "block": 0, "intents": [{"damage": incoming, "repeats": 1}], "powers": []}],
                }
                with patch("official_agent.rollout_choice", return_value=selected):
                    action = choose(observation, enemy_data={"monsters": []}, simulations=1)
                self.assertEqual(action["card_id"], card_id)
                self.assertEqual(action["decision_source"], "rollout_success")

    def test_rollout_allows_safe_self_damage_against_vulnerable_ovicopter(self) -> None:
        selected = {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 0, "target_id": 1}
        observation = {
            "legal_actions": [selected, {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1}, {"type": "end_turn"}],
            "player": {"hp": 32, "max_hp": 87, "block": 0, "energy": 1, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.HEMOKINESIS", "type": "Attack", "cost": 1, "vars": [{"id": "HpLoss", "value": 2}, {"id": "Damage", "value": 15}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.OVICOPTER", "hp": 73, "block": 7, "intents": [{"damage": 19, "repeats": 1}],
                "powers": [{"id": "POWER.VULNERABLE_POWER", "amount": 2}],
            }],
        }
        with patch("official_agent.rollout_choice", return_value=selected):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.HEMOKINESIS", "rollout_success"))

    def test_devoted_sculptor_attack_precedes_unupgraded_true_grit(self) -> None:
        true_grit = {"type": "card", "card_id": "CARD.TRUE_GRIT", "hand_index": 0, "target_id": None}
        anger = {"type": "card", "card_id": "CARD.ANGER", "hand_index": 1, "target_id": 1}
        observation = {
            "player": {"hp": 67, "max_hp": 80, "block": 0, "energy": 4, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.TRUE_GRIT", "upgrade": 0, "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 7}]},
                {"index": 1, "id": "CARD.ANGER", "upgrade": 0, "cost": 0, "type": "Attack", "vars": [{"id": "Damage", "value": 8}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DEVOTED_SCULPTOR", "hp": 75, "block": 0, "powers": [], "intents": [{"damage": 39, "repeats": 1}]}],
            "legal_actions": [true_grit, anger, {"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=true_grit):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_reason"]), ("CARD.ANGER", "devoted_race_before_true_grit"))

    def test_frog_knight_rest_turn_attack_precedes_temporary_block(self) -> None:
        defend = {"type": "card", "card_id": "CARD.TRUE_GRIT", "hand_index": 0, "target_id": None}
        maul = {"type": "card", "card_id": "CARD.MAUL", "hand_index": 1, "target_id": 1}
        observation = {
            "player": {"hp": 48, "max_hp": 80, "block": 0, "energy": 4, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.TRUE_GRIT", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 7}]},
                {"index": 1, "id": "CARD.MAUL", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.FROG_KNIGHT", "hp": 169, "block": 0, "powers": [], "intents": [{"type": "Buff", "damage": 0, "repeats": 0}]}],
            "legal_actions": [defend, maul, {"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=defend):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_reason"]), ("CARD.MAUL", "frog_knight_rest_attack"))

    def test_multi_card_kill_beats_the_unsafe_rollout_guard(self) -> None:
        # astra_sims400_R9TB3LKD6M seq137: 6 HP, 3 energy, VANTOM on 16, and 7+8+6 in hand. The
        # guard only knew single-card lethals, so it swapped the opener for Defend and left the
        # boss alive on 1 HP. Killing the sole attacker removes the whole incoming hit.
        selected = {"type": "card", "card_id": "CARD.SETUP_STRIKE", "hand_index": 0, "target_id": 1}
        observation = {
            "seq": 1,
            "legal_actions": [
                selected,
                {"type": "card", "card_id": "CARD.PILLAGE", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 2, "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {
                "hp": 6, "max_hp": 80, "block": 0, "energy": 3,
                "powers": [{"id": "POWER.STRENGTH_POWER", "amount": 40}],
            },
            "hand": [
                {"index": 0, "id": "CARD.SETUP_STRIKE", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 7}]},
                {"index": 1, "id": "CARD.PILLAGE", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 9}]},
                {"index": 2, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "cost": 1, "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{
                "combat_id": 1, "hp": 23, "block": 0,
                "intents": [{"damage": 20, "repeats": 1}],
                "powers": [{"id": "POWER.VULNERABLE_POWER", "amount": 1}],
            }],
        }
        with patch("official_agent.rollout_choice", return_value=observation["legal_actions"][2]):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.PILLAGE")
        self.assertEqual(action["decision_source"], "multi_lethal_direct")

    def test_vulnerable_setup_starts_multi_card_lethal(self) -> None:
        observation = {
            "player": {"hp": 5, "max_hp": 91, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
                {"index": 1, "id": "CARD.ANGER", "cost": 0, "type": "Attack", "vars": [{"id": "Damage", "value": 12}]},
                {"index": 2, "id": "CARD.BASH", "cost": 2, "type": "Attack", "vars": [{"id": "Damage", "value": 14}, {"id": "Power", "value": 2}]},
                {"index": 3, "id": "CARD.ANGER", "cost": 0, "type": "Attack", "vars": [{"id": "Damage", "value": 12}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 40, "block": 0, "powers": [], "intents": [{"damage": 12, "repeats": 2}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 0},
                {"type": "card", "card_id": "CARD.ANGER", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 2, "target_id": 1},
                {"type": "card", "card_id": "CARD.ANGER", "hand_index": 3, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.BASH", "vulnerable_multi_lethal_direct"))

        observation["enemies"][0]["powers"] = [{"id": "POWER.THORNS_POWER", "amount": 5}]
        self.assertNotEqual(choose(observation, enemy_data={"monsters": []}, simulations=1).get("decision_source"), "vulnerable_multi_lethal_direct")

    def test_vulnerable_setup_kills_ovicopter_instead_of_its_minions(self) -> None:
        observation = {
            "player": {"hp": 11, "max_hp": 80, "block": 0, "energy": 3, "powers": [], "relics": ["RELIC.NUNCHAKU"]},
            "hand": [
                {"index": 0, "id": "CARD.UPPERCUT", "cost": 2, "type": "Attack", "vars": [{"id": "Damage", "value": 13}, {"id": "Power", "value": 1}]},
                {"index": 1, "id": "CARD.ASHEN_STRIKE", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 3, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.OVICOPTER", "hp": 30, "block": 0, "powers": [], "intents": [{"damage": 13, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.TOUGH_EGG", "hp": 1, "block": 0, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 4, "repeats": 1}]},
                {"combat_id": 3, "id": "MONSTER.TOUGH_EGG", "hp": 2, "block": 0, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 4, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": card_id, "hand_index": hand_index, "target_id": target}
                for card_id, hand_index in (("CARD.UPPERCUT", 0), ("CARD.ASHEN_STRIKE", 1), ("CARD.STRIKE_IRONCLAD", 2))
                for target in (1, 2, 3)
            ] + [{"type": "end_turn"}],
        }
        action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["target_id"], action["decision_source"]), ("CARD.UPPERCUT", 1, "vulnerable_multi_lethal_direct"))

    def test_kills_parafright_when_ignoring_its_revival_would_be_fatal(self) -> None:
        observation = {
            "player": {"hp": 1, "max_hp": 80, "block": 0, "energy": 3},
            "hand": [{"index": 0, "id": "CARD.UPPERCUT", "cost": 2, "type": "Attack", "vars": [{"id": "Damage", "value": 13}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.THE_OBSCURA", "hp": 60, "block": 0, "powers": [], "intents": []},
                {"combat_id": 3, "id": "MONSTER.PARAFRIGHT", "hp": 9, "block": 0, "powers": [{"id": "POWER.ILLUSION_POWER", "amount": 1}], "intents": [{"damage": 19, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.UPPERCUT", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.UPPERCUT", "hand_index": 0, "target_id": 3},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual((action["target_id"], action["decision_source"]), (3, "lethal_direct"))

    def test_vulnerable_potion_kills_attacker_when_remaining_block_survives(self) -> None:
        observation = {
            "player": {"hp": 1, "max_hp": 80, "block": 0, "energy": 3},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.SHRUG_IT_OFF", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 16}]},
                {"index": 2, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.THE_OBSCURA", "hp": 61, "block": 0, "powers": [], "intents": [{"damage": 19, "repeats": 1}]},
                {"combat_id": 3, "id": "MONSTER.PARAFRIGHT", "hp": 9, "block": 0, "powers": [], "intents": [{"damage": 25, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 3},
                {"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 2},
                {"type": "potion", "potion_id": "POTION.VULNERABLE_POTION", "target_id": 1},
                {"type": "potion", "potion_id": "POTION.VULNERABLE_POTION", "target_id": 3},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual((action["potion_id"], action["target_id"], action["decision_source"]), ("POTION.VULNERABLE_POTION", 3, "vulnerable_survival_potion"))
        observation["hand"][0]["vars"][0]["value"] = 10
        observation["enemies"][0]["intents"] = []
        observation["enemies"][1]["hp"] = 15
        observation["enemies"][1]["intents"][0]["damage"] = 16
        self.assertNotEqual(choose(observation).get("decision_source"), "vulnerable_survival_potion")

    def test_unsafe_rollout_guard_still_rejects_a_kill_the_turn_cannot_reach(self) -> None:
        # Same shape, but 16 damage of hand against 30 HP - no kill, so the guard still blocks.
        selected = {"type": "card", "card_id": "CARD.SETUP_STRIKE", "hand_index": 0, "target_id": 1}
        observation = {
            "seq": 1,
            "legal_actions": [
                selected,
                {"type": "card", "card_id": "CARD.PILLAGE", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 2, "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 6, "max_hp": 80, "block": 0, "energy": 3},
            "hand": [
                {"index": 0, "id": "CARD.SETUP_STRIKE", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 7}]},
                {"index": 1, "id": "CARD.PILLAGE", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 9}]},
                {"index": 2, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "cost": 1, "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 30, "block": 0, "intents": [{"damage": 20, "repeats": 1}], "powers": []}],
        }
        with patch("official_agent.rollout_choice", return_value=selected):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["decision_reason"], "rollout_rejected_unsafe")

    def test_dead_enemy_intent_does_not_trigger_unsafe_rollout_guard(self) -> None:
        selected = {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2}
        observation = {
            "seq": 1,
            "legal_actions": [selected, {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 10, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DEAD", "hp": 0, "block": 0, "intents": [{"damage": 10, "repeats": 1}], "powers": []},
                {"combat_id": 2, "id": "MONSTER.LIVE", "hp": 50, "block": 0, "intents": [], "powers": []},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=selected):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.STRIKE_IRONCLAD")
        self.assertEqual(action["decision_source"], "rollout_success")

    def test_low_hp_safe_self_damage_attack_beats_idle_block(self) -> None:
        bloodletting = {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None}
        breakthrough = {"type": "card", "card_id": "CARD.BREAKTHROUGH", "hand_index": 1, "target_id": None}
        observation = {
            "player": {"hp": 2, "max_hp": 130, "block": 0, "energy": 2, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "cost": 0, "type": "Skill", "vars": [{"id": "HpLoss", "value": 3}]},
                {"index": 1, "id": "CARD.BREAKTHROUGH", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 19}, {"id": "HpLoss", "value": 1}]},
                {"index": 2, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.QUEEN", "hp": 97, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [
                bloodletting,
                breakthrough,
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 2, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=bloodletting):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.BREAKTHROUGH")

    def test_map_route_prefers_boss_reachable_path(self) -> None:
        # The col-1 branch dead-ends at a Treasure, so the planner follows the col-0 branch to the boss.
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Boss", "children": []},
                {"col": 1, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_low_hp_prefers_nearest_reachable_rest(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "Monster", "children": [{"col": 1, "row": 2}]},
                {"col": 1, "row": 2, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_two_thirds_hp_prefers_nearest_reachable_rest(self) -> None:
        observation = {
            "player": {"hp": 52, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "Monster", "children": [{"col": 1, "row": 2}]},
                {"col": 1, "row": 2, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_three_quarters_hp_prefers_nearest_reachable_rest(self) -> None:
        # 58/80 sat just outside the old two-thirds cutoff (53.3) - a real run walked straight
        # through it and two more costly Monster packs before finally reaching a rest site at
        # 10 HP. The trigger now sits at three quarters (matching choose_rest's own HEAL
        # threshold) so this exact HP band routes toward rest instead.
        observation = {
            "player": {"hp": 58, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "Monster", "children": [{"col": 1, "row": 2}]},
                {"col": 1, "row": 2, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_low_hp_prefers_fewer_fights_over_a_nearer_rest(self) -> None:
        # A direct Monster followed by a rest is worse than taking a non-combat node first
        # when the player is already low enough for the safety route.
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Unknown", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_map_debug_logs_rest_routing_candidates_when_enabled(self) -> None:
        observation = {
            "seq": 42,
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Unknown", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            log_path = os.path.join(tmp, "map_debug.jsonl")
            with patch.dict(os.environ, {"STS2AI_MAP_DEBUG": log_path}):
                choose_map(observation)
            with open(log_path, encoding="utf-8") as file:
                entry = json.loads(file.readline())
        self.assertEqual(entry["seq"], 42)
        self.assertEqual(entry["hp"], 20)
        candidates = {(c["col"], c["type"]): c["route"] for c in entry["candidates"]}
        # Certain combat weighs 2 and an Unknown 1 at this HP, so the Monster route is the worse
        # of the two even though both reach a rest site in one step.
        self.assertEqual(candidates[(0, "Monster")], [2, 1, 0])
        self.assertEqual(candidates[(1, "Unknown")], [1, 1, 0])

    def test_just_above_three_quarters_hp_uses_normal_routing(self) -> None:
        # One HP above the new cutoff (61/80): rest-priority routing must not engage yet.
        observation = {
            "player": {"hp": 61, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "Monster", "children": [{"col": 1, "row": 2}]},
                {"col": 1, "row": 2, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_two_thirds_hp_still_prefers_value_when_no_rest_is_reachable(self) -> None:
        observation = {
            "player": {"hp": 52, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Boss", "children": []},
                {"col": 1, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_avoids_elite_on_equally_short_rest_route(self) -> None:
        observation = {
            "player": {"hp": 40, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Elite", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": [{"col": 0, "row": 2}]},
                {"col": 1, "row": 1, "type": "RestSite", "children": []},
                {"col": 0, "row": 2, "type": "Treasure", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_ignores_unreachable_rest_routes(self) -> None:
        observation = {
            "player": {"hp": 39, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Treasure", "children": []},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 1, "row": 1, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_prefers_unknown_when_no_rest_is_reachable(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Unknown", "children": []},
                {"col": 0, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_critical_hp_prefers_a_safe_room_over_an_unknown(self) -> None:
        # astra_seed_K7M2QX9BTR died here: at 12/85 the only choices were an Unknown and a Shop,
        # and it walked into the Unknown, which turned out to be an Ovicopter pack.
        observation = {
            "player": {"hp": 12, "max_hp": 85},
            "map": {"points": [
                {"col": 2, "row": 13, "type": "Unknown", "children": []},
                {"col": 3, "row": 13, "type": "Shop", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 2, "row": 13}, {"type": "map", "col": 3, "row": 13}],
        }
        self.assertEqual(choose_map(observation)["col"], 3)
        # Above a third of max HP the gamble is worth taking again, so routing is unchanged.
        observation["player"] = {"hp": 40, "max_hp": 85}
        self.assertEqual(choose_map(observation)["col"], 2)

    def test_low_hp_uses_existing_value_when_all_routes_fight(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Treasure", "children": []},
                {"col": 1, "row": 1, "type": "Unknown", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_low_hp_map_cycle_is_safe(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 0}]},
                {"col": 1, "row": 0, "type": "Unknown", "children": [{"col": 1, "row": 0}]},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_map_route_minimizes_monster_tiles(self) -> None:
        # Both branches end at the boss with one rest, but col-0 steps on 2 monsters vs col-1's 1.
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Monster", "children": [{"col": 0, "row": 2}]},
                {"col": 1, "row": 1, "type": "RestSite", "children": [{"col": 1, "row": 2}]},
                {"col": 0, "row": 2, "type": "RestSite", "children": [{"col": 0, "row": 3}]},
                {"col": 1, "row": 2, "type": "Treasure", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Boss", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_map_route_prefers_rests_at_equal_monsters(self) -> None:
        # Equal monster counts: col-0 offers a rest site, col-1 only a treasure.
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": [{"col": 0, "row": 2}]},
                {"col": 1, "row": 1, "type": "Monster", "children": [{"col": 1, "row": 2}]},
                {"col": 0, "row": 2, "type": "Monster", "children": [{"col": 0, "row": 3}]},
                {"col": 1, "row": 2, "type": "Treasure", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Boss", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_map_route_avoids_elites_at_equal_monsters(self) -> None:
        # Equal monsters and rests: col-1 avoids the elite and keeps the treasure.
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": [{"col": 0, "row": 2}]},
                {"col": 1, "row": 1, "type": "RestSite", "children": [{"col": 1, "row": 2}]},
                {"col": 0, "row": 2, "type": "Elite", "children": [{"col": 0, "row": 3}]},
                {"col": 1, "row": 2, "type": "Treasure", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Boss", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_map_route_avoids_unrested_elite_chain(self) -> None:
        # Do not trade a second elite without a rest for two ordinary fights and one rested elite.
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Treasure", "children": [{"col": 0, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": [{"col": 0, "row": 2}]},
                {"col": 0, "row": 2, "type": "Elite", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Unknown", "children": [{"col": 0, "row": 4}]},
                {"col": 0, "row": 4, "type": "Elite", "children": [{"col": 0, "row": 5}]},
                {"col": 0, "row": 5, "type": "RestSite", "children": [{"col": 0, "row": 6}]},
                {"col": 0, "row": 6, "type": "Boss", "children": []},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 1, "row": 1, "type": "Unknown", "children": [{"col": 1, "row": 2}]},
                {"col": 1, "row": 2, "type": "Monster", "children": [{"col": 1, "row": 3}]},
                {"col": 1, "row": 3, "type": "RestSite", "children": [{"col": 1, "row": 4}]},
                {"col": 1, "row": 4, "type": "Elite", "children": [{"col": 1, "row": 5}]},
                {"col": 1, "row": 5, "type": "RestSite", "children": [{"col": 0, "row": 6}]},
            ]},
            "legal_actions": [
                {"type": "map", "col": 0, "row": 0},
                {"type": "map", "col": 1, "row": 0},
            ],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_map_route_plans_suffix_from_current_position(self) -> None:
        # Current position is mid-map; the plan continues from there (0 monsters via col-1).
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "run": {"current": {"col": 1, "row": 1}},
            "map": {"points": [
                {"col": 1, "row": 1, "type": "RestSite", "children": [{"col": 0, "row": 2}, {"col": 1, "row": 2}]},
                {"col": 0, "row": 2, "type": "Monster", "children": [{"col": 0, "row": 3}]},
                {"col": 1, "row": 2, "type": "RestSite", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Boss", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 2}, {"type": "map", "col": 1, "row": 2}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_map_route_falls_back_to_value_without_boss(self) -> None:
        # No boss point on the map: the route planner is skipped and the value heuristic decides.
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Treasure", "children": []},
                {"col": 1, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_reward_prefers_known_strong_card(self) -> None:
        observation = {
            "cards": [
                {"id": "CARD.STRIKE", "rarity": "Common"},
                {"id": "CARD.BLUDGEON", "rarity": "Rare"},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.STRIKE"},
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BLUDGEON")

    def test_reward_reads_existing_deck_costs_before_adding_high_cost_card(self) -> None:
        observation = {
            "player": {"deck": [
                {"id": "CARD.BLUDGEON", "cost": 3},
                {"id": "CARD.UNMOVABLE", "cost": 3},
            ]},
            "cards": [
                {"id": "CARD.BLUDGEON", "rarity": "Rare", "cost": 3},
                {"id": "CARD.SHRUG_IT_OFF", "rarity": "Uncommon", "cost": 1},
                {"id": "CARD.ANGER", "rarity": "Common", "cost": 0},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_overrides_attack_tier_when_large_deck_lacks_strong_block(self) -> None:
        observation = {
            "player": {"deck": [
                *({"id": "CARD.STRIKE_IRONCLAD", "cost": 1} for _ in range(5)),
                *({"id": "CARD.DEFEND_IRONCLAD", "cost": 1} for _ in range(4)),
                {"id": "CARD.BASH", "cost": 2}, {"id": "CARD.BLUDGEON", "cost": 3},
                {"id": "CARD.TAUNT", "cost": 1}, {"id": "CARD.PRIMAL_FORCE", "cost": 0},
                {"id": "CARD.ANGER", "cost": 0}, {"id": "CARD.EVIL_EYE", "cost": 1},
                {"id": "CARD.COLOSSUS", "cost": 1}, {"id": "CARD.AGGRESSION", "cost": 1},
                {"id": "CARD.POMMEL_STRIKE", "cost": 1}, {"id": "CARD.SHRUG_IT_OFF", "cost": 1},
            ]},
            "cards": [
                {"id": "CARD.POMMEL_STRIKE", "rarity": "Rare", "cost": 1},
                {"id": "CARD.SHRUG_IT_OFF", "rarity": "Uncommon", "cost": 1},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.POMMEL_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_overrides_attack_tier_when_large_deck_block_density_is_low(self) -> None:
        observation = {
            "player": {"deck": [
                *({"id": "CARD.STRIKE_IRONCLAD", "cost": 1} for _ in range(5)),
                *({"id": "CARD.DEFEND_IRONCLAD", "cost": 1} for _ in range(4)),
                {"id": "CARD.BASH", "cost": 2}, {"id": "CARD.BLUDGEON", "cost": 3},
                {"id": "CARD.EVIL_EYE", "cost": 1}, {"id": "CARD.EVIL_EYE", "cost": 1},
                {"id": "CARD.SHRUG_IT_OFF", "cost": 1}, {"id": "CARD.COLOSSUS", "cost": 1},
                {"id": "CARD.AGGRESSION", "cost": 1}, {"id": "CARD.ANGER", "cost": 0},
                {"id": "CARD.EXPECT_A_FIGHT", "cost": 1}, {"id": "CARD.INFLAME", "cost": 1},
            ]},
            "cards": [
                {"id": "CARD.TAUNT", "rarity": "Uncommon", "cost": 1},
                {"id": "CARD.POMMEL_STRIKE", "rarity": "Rare", "cost": 1},
                {"id": "CARD.SHRUG_IT_OFF", "rarity": "Uncommon", "cost": 1},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TAUNT"},
                {"type": "card_reward", "card_id": "CARD.POMMEL_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_colossus_is_defense_priority_but_not_strong_block(self) -> None:
        # D6 fix: Colossus (5 block) should count as a defense pick, but stay out of
        # STRONG_BLOCK_CARDS since it is barely better than Defend.
        self.assertIn("CARD.COLOSSUS", DEFENSE_PRIORITY)
        self.assertNotIn("CARD.COLOSSUS", STRONG_BLOCK_CARDS)

    def _d6_shortage_deck(self) -> list[dict]:
        # 16 cards, 1 strong block (Taunt) - the D6 loss (29 cards, 1 strong block) in miniature,
        # sized at the >= 16 boundary the shortage check uses.
        return [
            *({"id": "CARD.STRIKE_IRONCLAD", "cost": 1} for _ in range(5)),
            *({"id": "CARD.DEFEND_IRONCLAD", "cost": 1} for _ in range(4)),
            {"id": "CARD.BASH", "cost": 2}, {"id": "CARD.BLUDGEON", "cost": 3},
            {"id": "CARD.PRIMAL_FORCE", "cost": 0}, {"id": "CARD.POMMEL_STRIKE", "cost": 1},
            {"id": "CARD.AGGRESSION", "cost": 1}, {"id": "CARD.TAUNT", "cost": 1},
            {"id": "CARD.COLOSSUS", "cost": 1},
        ]

    def test_reward_skips_off_axis_pick_when_deck_lacks_strong_block(self) -> None:
        # D6 (Act3 TEST_SUBJECT loss): a large deck stuck on 1 strong block kept taking A/S-tier
        # off-axis attacks (Anger, Headbutt, Dark Embrace, Expect a Fight) because their tier
        # cleared the B-tier-only Skip check below. With deck>=16 and <3 strong blocks, an
        # unsupported pick must be skipped regardless of tier.
        observation = {
            "player": {"deck": self._d6_shortage_deck()},
            "cards": [{"id": "CARD.ANGER", "rarity": "Common", "cost": 0}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_still_takes_supported_picks_when_deck_lacks_strong_block(self) -> None:
        # Same shortage as above, but core/DEFENSE_PRIORITY/DRAW_CARDS/Colossus picks must still
        # win over the off-axis Anger, not fall through to Skip.
        cases = {
            "defense": ("CARD.SHRUG_IT_OFF", {"id": "CARD.SHRUG_IT_OFF", "rarity": "Uncommon", "cost": 1}),
            "colossus": ("CARD.COLOSSUS", {"id": "CARD.COLOSSUS", "rarity": "Uncommon", "cost": 1}),
            "draw": ("CARD.DRUM_OF_BATTLE", {"id": "CARD.DRUM_OF_BATTLE", "rarity": "Uncommon", "cost": 1}),
            "core": ("CARD.INFLAME", {"id": "CARD.INFLAME", "rarity": "Rare", "cost": 1}),
        }
        for label, (expected_id, card) in cases.items():
            with self.subTest(label):
                observation = {
                    "player": {"deck": self._d6_shortage_deck()},
                    "cards": [{"id": "CARD.ANGER", "rarity": "Common", "cost": 0}, card],
                    "legal_actions": [
                        {"type": "card_reward", "card_id": "CARD.ANGER"},
                        {"type": "card_reward", "card_id": expected_id},
                        {"type": "card_reward_alternative", "option_id": "Skip"},
                    ],
                }
                self.assertEqual(choose_card_reward(observation)["card_id"], expected_id)

    def test_reward_takes_strong_block_pick_when_deck_lacks_strong_block(self) -> None:
        # The score's strong_defense_bonus must also be honored by the final shortage gate.
        for card_id in ("CARD.EQUILIBRIUM", "CARD.EVIL_EYE", "CARD.ULTIMATE_DEFEND"):
            with self.subTest(card_id):
                observation = {
                    "player": {"deck": self._d6_shortage_deck()},
                    "cards": [
                        {"id": "CARD.ANGER", "rarity": "Common", "cost": 0},
                        {"id": card_id, "rarity": "Uncommon", "cost": 1},
                    ],
                    "legal_actions": [
                        {"type": "card_reward", "card_id": "CARD.ANGER"},
                        {"type": "card_reward", "card_id": card_id},
                        {"type": "card_reward_alternative", "option_id": "Skip"},
                    ],
                }
                self.assertEqual(choose_card_reward(observation)["card_id"], card_id)

    def test_reward_draw_pick_exemption_respects_draw_needed_under_block_shortage(self) -> None:
        # D6 rerun (Act2 boss loss, turn3 Byrd Swoop->Iron Wave->Strike->Rage): the
        # strong_block_shortage skip exempted every DRAW_CARDS pick unconditionally, so a deck
        # already past _draw_starved's <2 threshold kept taking more Battle Trance (ended at 3+
        # copies, 24 cards, 0 strong blocks). The exemption must gate on draw_needed instead.
        base_deck = self._d6_shortage_deck()  # 16 cards, 1 strong block, 1 draw card (Pommel Strike)
        observation = {
            "player": {"deck": base_deck},
            "cards": [{"id": "CARD.BATTLE_TRANCE", "rarity": "Uncommon", "cost": 0}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        with self.subTest("one_draw_card_still_taken"):
            self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")
        observation_with_two_draw_cards = {
            **observation,
            "player": {"deck": base_deck + [{"id": "CARD.DRUM_OF_BATTLE", "cost": 1}]},
        }
        with self.subTest("two_draw_cards_now_skipped"):
            self.assertEqual(choose_card_reward(observation_with_two_draw_cards)["option_id"], "Skip")

    def test_reward_skips_unsupported_cards(self) -> None:
        observation = {
            "cards": [{"id": "CARD.UNKNOWN", "rarity": "Uncommon"}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_allows_unmodeled_card_before_cap(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.HELLRAISER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.HELLRAISER")

    def test_reward_allows_modeled_aggression(self) -> None:
        observation = {
            "player": {"deck": ["CARD.AGGRESSION", "CARD.CORRUPTION"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.AGGRESSION"},
                {"type": "card_reward", "card_id": "CARD.HELLRAISER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.AGGRESSION")

    def test_reward_takes_anger_for_the_normal_fights(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

    def test_reward_uses_known_boss_axis(self) -> None:
        observation = {
            "run": {"boss_encounter_id": "ENCOUNTER.THE_INSATIABLE_BOSS"},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_uses_kin_boss_axis_for_strong_block(self) -> None:
        observation = {
            "run": {"boss_encounter_id": "ENCOUNTER.THE_KIN_BOSS"},
            "cards": [
                {"id": "CARD.BLUDGEON", "rarity": "Rare", "cost": 3},
                {"id": "CARD.SHRUG_IT_OFF", "rarity": "Uncommon", "cost": 1},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_skips_unknown_skill(self) -> None:
        observation = {
            "cards": [{"id": "CARD.UNKNOWN_SKILL", "type": "Skill", "rarity": "Uncommon", "cost": 1}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_SKILL"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_uses_metadata_for_unknown_attack(self) -> None:
        observation = {
            "cards": [
                {"id": "CARD.UNKNOWN_COMMON", "type": "Attack", "rarity": "Common", "cost": 0},
                {"id": "CARD.UNKNOWN_RARE_EXPENSIVE", "type": "Attack", "rarity": "Rare", "cost": 2},
                {"id": "CARD.UNKNOWN_RARE_CHEAP", "type": "Attack", "rarity": "Rare", "cost": 1},
                {"id": "CARD.UNKNOWN_SKILL", "type": "Skill", "rarity": "Rare", "cost": 0},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_COMMON"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_RARE_EXPENSIVE"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_RARE_CHEAP"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_SKILL"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.UNKNOWN_RARE_CHEAP")

    def test_reward_keeps_known_card_for_a_large_deck(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE"}] * 14},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_reward_seeds_strike_axis_with_strike_heavy_deck(self) -> None:
        # The starter deck already has 5 Strikes, so Perfected Strike hits ~16 immediately;
        # it must beat a one-shot BLUDGEON so the boss-fight strike axis gets seeded.
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 5},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_seeds_strength_axis_with_inflame(self) -> None:
        # Inflame is now an axis seed: it must beat a one-shot BLUDGEON in a fresh deck.
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.INFLAME"},
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.INFLAME")

    def test_reward_seeds_self_damage_axis_from_one_offer(self) -> None:
        # Neither half of the Rupture engine could enter first: the enabler is docked priority
        # until Rupture is in the deck, and Rupture was a seed only once an enabler was. An offer
        # holding both (astra_base_H2LV6ZJ4XW act1 f2) took neither. Fuel on screen counts as fuel.
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward", "card_id": "CARD.INFLAME"},
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.RUPTURE")

    def test_reward_does_not_seed_rupture_without_any_fuel(self) -> None:
        # No enabler in the deck and none on offer: Rupture is a C-tier card with nothing to pay it.
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_feeds_started_strength_axis(self) -> None:
        # Once Inflame is in the deck, other Strength sources (Dominate) outrank same-tier cards.
        observation = {
            "player": {"deck": [{"id": "CARD.INFLAME"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.DOMINATE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.DOMINATE")

    def test_reward_prefers_inflame_over_perfected_strike_as_seed(self) -> None:
        # Boss-fight verification showed the strength axis deals the most damage, so when both
        # seeds are offered Inflame must win even in a Strike-heavy starter deck.
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 5},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.INFLAME"},
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.INFLAME")

    def test_reward_does_not_take_third_perfected_strike(self) -> None:
        # With 2 Perfected Strikes already in the deck a third copy only bloats it (PS axes
        # dealt the least boss damage in verification); the strength axis must win instead.
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 5 + [{"id": "CARD.PERFECTED_STRIKE"}] * 2 + [{"id": "CARD.INFLAME"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.DOMINATE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.DOMINATE")

    def test_rest_heals_when_hurt(self) -> None:
        observation = {
            "player": {"hp": 37, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HEAL")

    def test_rest_heals_before_boss(self) -> None:
        observation = {
            "player": {"hp": 64, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HEAL")

    def test_rest_hatches_egg_when_healthy(self) -> None:
        observation = {
            "player": {"hp": 65, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}, {"option_id": "HATCH"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HATCH")

    def test_uses_lethal_fire_potion(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.FIRE_POTION", "target_id": 7}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 20, "intents": []}],
        }
        self.assertEqual(choose(observation)["type"], "potion")

    def test_uses_dexterity_potion_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None}],
            "player": {"hp": 40, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")

    def test_uses_speed_potion_when_low(self) -> None:
        # Speed Potion grants Dexterity, same effect as Dexterity Potion (SpeedPotion.cs).
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.SPEED_POTION", "target_id": None}],
            "player": {"hp": 40, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SPEED_POTION")

    def test_uses_regen_potion_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None}],
            "player": {"hp": 36, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.REGEN_POTION")

    def test_low_hp_multiple_enemies_falls_back_to_dexterity(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None}],
            "player": {"hp": 15, "max_hp": 80},
            "hand": [],
            "enemies": [
                {"combat_id": 1, "hp": 30, "intents": []},
                {"combat_id": 2, "hp": 30, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")

    def test_nonlethal_danger_uses_only_one_potion_per_turn(self) -> None:
        observation = {
            "run": {"act": 98, "floor": 97},
            "turn": 4,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 35, "max_hp": 70},
            "hand": [],
            "enemies": [
                {"combat_id": 101, "id": "MONSTER.A", "hp": 30, "intents": [{"damage": 10, "repeats": 1}]},
                {"combat_id": 102, "id": "MONSTER.B", "hp": 30, "intents": [{"damage": 10, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_avoids_primal_force_after_duplicator_same_turn(self) -> None:
        observation = {
            "run": {"act": 98, "floor": 97, "room_type": "Boss"},
            "turn": 4,
            "legal_actions": [
                {"type": "card", "card_id": "CARD.PRIMAL_FORCE", "hand_index": 0, "target_id": None},
                {"type": "potion", "potion_id": "POTION.DUPLICATOR", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.PRIMAL_FORCE", "type": "Skill", "cost": 0, "vars": []}],
            "enemies": [{
                "combat_id": 104, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [],
                "intents": [{"damage": 20, "repeats": 1}],
            }],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DUPLICATOR")
        observation["legal_actions"] = [
            {"type": "card", "card_id": "CARD.PRIMAL_FORCE", "hand_index": 0, "target_id": None},
            {"type": "end_turn"},
        ]
        action = choose(observation)
        self.assertEqual(action["type"], "end_turn")
        self.assertNotEqual(action.get("card_id"), "CARD.PRIMAL_FORCE")

    def test_lethal_danger_can_use_another_potion_same_turn(self) -> None:
        observation = {
            "run": {"act": 98, "floor": 98},
            "turn": 4,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 70},
            "hand": [],
            "enemies": [{"combat_id": 103, "id": "MONSTER.C", "hp": 30, "intents": [{"damage": 25, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")
        observation["legal_actions"] = [
            {"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None},
            {"type": "end_turn"},
        ]
        self.assertEqual(choose(observation)["potion_id"], "POTION.REGEN_POTION")

    def test_monster_dexterity_potions_do_not_stack_same_turn(self) -> None:
        observation = {
            "run": {"act": 98, "floor": 99, "room_type": "Monster"},
            "turn": 4,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SPEED_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 70},
            "enemies": [{"combat_id": 103, "id": "MONSTER.C", "hp": 30, "intents": [{"damage": 25, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SPEED_POTION")
        observation["legal_actions"] = [
            {"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None},
            {"type": "end_turn"},
        ]
        self.assertEqual(choose(observation)["type"], "end_turn")
        self.assertEqual(_rollout_allowed_potions(observation, observation["legal_actions"]), ())

    def test_does_not_use_vulnerable_potion_for_lethal_survival(self) -> None:
        observation = {
            "run": {"act": 991, "floor": 992, "room_type": "Monster"},
            "turn": 4,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.VULNERABLE_POTION", "target_id": 104},
                {"type": "end_turn"},
            ],
            "player": {"hp": 7, "max_hp": 70},
            "enemies": [{"combat_id": 104, "id": "MONSTER.C", "hp": 30, "intents": [{"damage": 25, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_weak_potion_for_lethal_survival(self) -> None:
        observation = {
            "run": {"act": 993, "floor": 994, "room_type": "Monster"},
            "turn": 4,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.WEAK_POTION", "target_id": 105},
                {"type": "end_turn"},
            ],
            "player": {"hp": 7, "max_hp": 70},
            "enemies": [{"combat_id": 105, "id": "MONSTER.C", "hp": 30, "intents": [{"damage": 25, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.WEAK_POTION")

    def test_keeps_vulnerable_potion_for_offense(self) -> None:
        observation = {
            "run": {"act": 995, "floor": 996, "room_type": "Elite"},
            "turn": 2,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.VULNERABLE_POTION", "target_id": 106},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 106, "id": "MONSTER.C", "hp": 100, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.VULNERABLE_POTION")

    def test_buffer_makes_followup_potion_nonurgent(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 4},
            "turn": 3,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None},
                {"type": "potion", "potion_id": "POTION.HEART_OF_IRON", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80, "powers": []},
            "enemies": [{"combat_id": 1, "id": "MONSTER.C", "hp": 30, "intents": [{"damage": 25, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.LUCKY_TONIC")
        observation["legal_actions"] = [
            {"type": "potion", "potion_id": "POTION.HEART_OF_IRON", "target_id": None},
            {"type": "end_turn"},
        ]
        observation["player"]["powers"] = [{"id": "POWER.BUFFER_POWER", "amount": 1}]
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_potions_in_monster_room_but_not_elite_room(self) -> None:
        base = {
            "turn": 1,
            "player": {"hp": 60, "max_hp": 80},
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 123, "max_hp": 123, "intents": []}],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
        }
        monster = {**base, "run": {"act": 0, "floor": 5, "room_type": "Monster"}}
        elite = {**base, "run": {"act": 0, "floor": 5, "room_type": "Elite"}}
        self.assertEqual(choose(monster)["type"], "end_turn")
        self.assertEqual(choose(elite)["potion_id"], "POTION.STRENGTH_POTION")

    def test_potion_reward_swaps_out_the_worst_potion_only_when_it_is_an_upgrade(self) -> None:
        def observation(offered: str) -> dict:
            return {
                "phase": "potion_reward",
                "run": {"act": 1, "floor": 5},
                "player": {"hp": 50, "max_hp": 80},
                "offered": {"id": offered},
                "potions": [
                    {"index": 0, "id": "POTION.BLOCK_POTION"},
                    {"index": 1, "id": "POTION.WEAK_POTION"},
                    {"index": 2, "id": "POTION.FIRE_POTION"},
                ],
                "legal_actions": [
                    {"type": "discard", "index": 0, "potion_id": "POTION.BLOCK_POTION"},
                    {"type": "discard", "index": 1, "potion_id": "POTION.WEAK_POTION"},
                    {"type": "discard", "index": 2, "potion_id": "POTION.FIRE_POTION"},
                    {"type": "skip", "index": -1, "potion_id": None},
                ],
            }
        worst = min(
            ("POTION.BLOCK_POTION", "POTION.WEAK_POTION", "POTION.FIRE_POTION"),
            key=lambda potion: SHOP_POTION_SCORES.get(potion, -1),
        )
        better = max(SHOP_POTION_SCORES, key=lambda potion: SHOP_POTION_SCORES[potion])
        action = choose(observation(better))
        self.assertEqual((action["type"], action["potion_id"]), ("discard", worst))
        # An offer that does not beat the worst held potion is not worth a slot.
        action = choose(observation(worst))
        self.assertEqual(action["type"], "skip")

    def test_entropic_brew_waits_for_an_open_potion_slot(self) -> None:
        # Drinking it on a full belt frees only its own slot, so it trades one potion for one.
        observation = {
            "run": {"act": 1, "floor": 8, "room_type": "Elite"},
            "turn": 1,
            "potions": [
                {"index": 0, "id": "POTION.SPEED_POTION"},
                {"index": 1, "id": "POTION.FAIRY_IN_A_BOTTLE"},
                {"index": 2, "id": "POTION.ENTROPIC_BREW"},
            ],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.ENTROPIC_BREW", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 60, "max_hp": 80},
            "enemies": [{"combat_id": 1, "id": "MONSTER.X", "hp": 120, "max_hp": 120, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        actions = [a for a in observation["legal_actions"] if a["type"] == "potion"]
        self.assertIsNone(choose_potion(observation, actions))
        # With a slot already open it yields two or more potions, so it is worth drinking.
        observation["potions"][1] = None
        self.assertEqual(choose_potion(observation, actions)["potion_id"], "POTION.ENTROPIC_BREW")

    def test_elite_potion_danger_uses_damage_after_current_block(self) -> None:
        observation = {
            "run": {"act": 2, "floor": 10, "room_type": "Elite"},
            "turn": 3,
            "player": {"hp": 79, "max_hp": 87, "block": 19},
            "enemies": [{"combat_id": 1, "id": "MONSTER.X", "hp": 158, "max_hp": 300, "intents": [{"damage": 40, "repeats": 1}]}],
        }
        actions = [{"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None}]
        self.assertIsNone(choose_potion(observation, actions))

    def test_saves_major_potion_after_defensive_potion_in_monster_room(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 5, "room_type": "Monster"},
            "turn": 2,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 40, "max_hp": 40, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")
        observation["legal_actions"] = [
            {"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None},
            {"type": "end_turn"},
        ]
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_second_potion_in_same_monster_room_across_turns(self) -> None:
        observation = {
            "run": {"act": 77, "floor": 88, "room_type": "Monster"},
            "turn": 3,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SPEED_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 26, "max_hp": 80},
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 40, "intents": [{"damage": 14, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SPEED_POTION")
        observation["turn"] = 4
        observation["legal_actions"] = [
            {"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None},
            {"type": "end_turn"},
        ]
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_potion_for_nonlethal_monster_threat(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 5, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.BLOCK_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 40, "max_hp": 80, "block": 0},
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 100, "intents": [{"damage": 30, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_potion_when_existing_block_covers_monster_hit(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 5, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.BLOCK_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80, "block": 12},
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 100, "intents": [{"damage": 10, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_potion_when_buffer_covers_monster_hit(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 6, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.BLOCK_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80, "block": 0, "powers": [{"id": "POWER.BUFFER_POWER", "amount": 1}]},
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 100, "intents": [{"damage": 10, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_low_hp_multiple_enemies_uses_swift_potion(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SWIFT_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 8, "max_hp": 80},
            "hand": [],
            "enemies": [
                {"combat_id": 1, "hp": 20, "intents": [{"damage": 5, "repeats": 1}]},
                {"combat_id": 2, "hp": 20, "intents": [{"damage": 5, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SWIFT_POTION")

    def test_monster_potion_waits_for_lethal_card(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 4, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SPEED_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
            "player": {"hp": 19, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 1, "block": 0, "intents": [{"damage": 10, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.STRIKE_IRONCLAD")

    def test_monster_potion_waits_for_targetless_aoe_lethal_card(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 5, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SPEED_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.HOWL_FROM_BEYOND", "hand_index": 0, "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 19, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.HOWL_FROM_BEYOND", "type": "Attack", "vars": [{"id": "Damage", "value": 16}]}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 10, "block": 0, "intents": [{"damage": 10, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.HOWL_FROM_BEYOND")

    def test_potion_is_suppressed_by_lethal_card_without_incoming(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 6, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FIRE_POTION", "target_id": 1},
                {"type": "card", "card_id": "CARD.HOWL_FROM_BEYOND", "hand_index": 0, "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.HOWL_FROM_BEYOND", "type": "Attack", "vars": [{"id": "Damage", "value": 16}]}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.RUBY", "hp": 10, "block": 0, "intents": []}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.HOWL_FROM_BEYOND")

    def test_monster_potion_remains_for_unfinished_incoming_enemy(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 4, "room_type": "Monster"},
            "turn": 1,
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SPEED_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
            "player": {"hp": 8, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.RUBY", "hp": 1, "block": 0, "intents": [{"damage": 5, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.SAPPHIRE", "hp": 20, "block": 0, "intents": [{"damage": 5, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SPEED_POTION")

    def test_low_hp_incoming_falls_back_to_regen(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None}],
            "player": {"hp": 36, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 30, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.REGEN_POTION")

    def test_low_hp_lethal_incoming_uses_lucky_tonic_first(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None},
                {"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.LUCKY_TONIC")

    def test_high_hp_half_incoming_saves_lucky_tonic(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 48, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 24, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_half_hp_incoming_uses_recovery_potion(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.CURE_ALL", "target_id": None},
                {"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 41, "max_hp": 80},
            "hand": [],
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 28, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.CURE_ALL")

    def test_pre_hit_low_quarter_uses_lucky_tonic(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 44, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 33, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.LUCKY_TONIC")

    def test_low_hp_uses_unknown_manual_potion_as_safe_fallback(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.UNKNOWN_MANUAL", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.UNKNOWN_MANUAL")

    def test_low_hp_skips_snecko_oil_fallback(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.SNECKO_OIL", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_certain_death_uses_snecko_oil_when_cards_can_be_drawn(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.SNECKO_OIL", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 4, "max_hp": 80, "block": 0},
            "hand": [{"id": "CARD.NORMALITY"}],
            "draw_pile": [{"id": "CARD.FLAME_BARRIER"}],
            "enemies": [{"combat_id": 1, "hp": 41, "intents": [{"damage": 22, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SNECKO_OIL")

    def test_full_hp_two_enemy_fight_skips_foul_potion_fallback(self) -> None:
        # FOUL_POTION damages every creature including the player; "danger" alone triggers on
        # 2+ enemies even at full HP, so it must not be grabbed blindly here.
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.FOUL_POTION", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 82, "max_hp": 82},
            "enemies": [
                {"combat_id": 1, "hp": 209, "intents": [{"damage": 10, "repeats": 1}]},
                {"combat_id": 2, "hp": 199, "intents": [{"damage": 10, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_full_hp_multi_enemy_fight_skips_unknown_potions(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.OROBIC_ACID", "target_id": None},
                {"type": "potion", "potion_id": "POTION.LIQUID_MEMORIES", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [
                {"combat_id": 1, "hp": 20, "intents": []},
                {"combat_id": 2, "hp": 20, "intents": []},
                {"combat_id": 3, "hp": 20, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_never_auto_plays_the_gambit_despite_its_huge_block(self) -> None:
        # TheGambitPower (decompiled): the next unblocked hit taken while it's active kills the
        # player outright regardless of HP, no self-expiry. The "highest block card" defensive
        # fallback used to grab this over Defend every time since 50 block dwarfs everything
        # else - it must never be chosen automatically.
        observation = {
            "legal_actions": [
                {"type": "card", "card_id": "CARD.THE_GAMBIT", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
            "hand": [
                {"index": 0, "id": "CARD.THE_GAMBIT", "type": "Skill", "block": 50},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "block": 5},
            ],
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "enemies": [{"combat_id": 1, "hp": 100, "block": 0, "intents": [{"damage": 7, "repeats": 1}], "powers": []}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_low_hp_uses_offensive_selection_potion(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_index": 0, "potion_id": "POTION.POWER_POTION", "target_id": None},
                {"type": "potion", "potion_index": 1, "potion_id": "POTION.FLEX_POTION", "target_id": None},
                {"type": "potion", "potion_index": 2, "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 8, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.POWER_POTION")

    def test_does_not_use_economy_potion_for_lethal_monster_hit(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 8, "room_type": "Monster"},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.CLARITY", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 8, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 100, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_economy_potion_on_nonurgent_boss_turn(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 17, "room_type": "Boss"},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.CLARITY", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.CLARITY")

    def test_uses_gigantification_as_lethal_offense(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 8, "room_type": "Monster"},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.GIGANTIFICATION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 8, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 100, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.GIGANTIFICATION")

    def test_shaped_rock_targets_the_highest_hp_enemy(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 5, "room_type": "Monster"},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.POTION_SHAPED_ROCK", "target_id": 1},
                {"type": "potion", "potion_id": "POTION.POTION_SHAPED_ROCK", "target_id": 2},
                {"type": "end_turn"},
            ],
            "player": {"hp": 30, "max_hp": 80},
            "hand": [],
            "enemies": [
                {"combat_id": 1, "hp": 12, "intents": [{"damage": 7, "repeats": 1}]},
                {"combat_id": 2, "hp": 8, "intents": [{"damage": 8, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 1)

    def test_lethal_incoming_uses_attack_potion_when_no_defense_exists(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_index": 1, "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.COLORLESS_POTION")

    def test_explosive_ampoule_is_used_against_multiple_enemies_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.EXPLOSIVE_AMPOULE", "target_id": 1}],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [
                {"combat_id": 1, "hp": 28, "intents": []},
                {"combat_id": 2, "hp": 34, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.EXPLOSIVE_AMPOULE")

    def test_energy_potion_requires_a_payable_hand_card(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.ENERGY_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "hand": [{"index": 0, "cost": 0}],
            "enemies": [
                {"combat_id": 1, "hp": 28, "intents": []},
                {"combat_id": 2, "hp": 34, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_energy_potion_when_lethal_incoming_has_payable_hand_card(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 0},
                {"type": "potion", "potion_id": "POTION.ENERGY_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 7, "max_hp": 80},
            "hand": [{"index": 0, "cost": 1}],
            "enemies": [
                {"combat_id": 1, "hp": 48, "intents": [{"damage": 8, "repeats": 1}]},
                {"combat_id": 2, "hp": 42, "intents": [{"damage": 8, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.ENERGY_POTION")

    def test_uses_strength_potion_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 123, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.STRENGTH_POTION")

    def test_uses_power_potion_proactively_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.POWER_POTION")

    def test_uses_shaped_rock_proactively_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.POTION_SHAPED_ROCK", "target_id": 7},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_shaped_rock_when_enemy_block_prevents_lethal_damage(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 5, "room_type": "Monster"},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.POTION_SHAPED_ROCK", "target_id": 7},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 10, "block": 10, "intents": []}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_colorless_potion_proactively_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.COLORLESS_POTION")

    def test_saves_skill_potion_for_a_threatening_boss_turn(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.STRENGTH_POTION")

    def test_uses_skill_potion_when_boss_incoming_is_high(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": [{"damage": 40, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_uses_skill_potion_on_any_attacking_long_boss_turn(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_saves_major_potions_for_boss_from_high_hp_regular(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.LOUSE_PROGENITOR", "hp": 80, "max_hp": 136, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_fysh_before_a_hit_at_three_fifths_hp(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 48, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 200, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.FYSH_OIL")
        observation["player"]["hp"] = 49
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_binding_on_the_first_threatening_boss_turn(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.POTION_OF_BINDING", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 66, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 302, "intents": [{"damage": 40, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.POTION_OF_BINDING")
        observation["enemies"][0]["intents"][0]["damage"] = 12
        self.assertEqual(choose(observation)["potion_id"], "POTION.STRENGTH_POTION")

    def test_saves_colorless_potion_on_a_safe_boss_turn(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 379, "intents": []}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_colorless_potion_for_a_later_boss_attack_cycle(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 39, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 157, "intents": [{"damage": 11, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_colorless_potion_on_a_nonlethal_threatening_boss_turn(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 39, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 157, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_colorless_potion_on_a_critical_nonlethal_boss_attack(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 17, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 149, "intents": [{"damage": 11, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_colorless_potion_on_a_critical_nonattacking_boss_turn(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.KNOWLEDGE_DEMON", "hp": 157, "intents": []}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_major_potion_against_known_boss(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.THE_INSATIABLE", "slot": "boss", "hp": 321, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_saves_skill_potion_in_a_low_hp_nonthreatening_fight(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.POWER_POTION")

    def test_uses_skill_potion_on_low_hp_attacking_long_boss(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.THE_INSATIABLE", "slot": "boss", "hp": 321, "intents": [{"damage": 8, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_uses_skill_potion_on_low_hp_boss_before_next_attack(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.THE_INSATIABLE", "hp": 321, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_uses_skill_before_recovery_on_lethal_boss_turn(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None},
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 24, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.THE_INSATIABLE", "hp": 166, "intents": [{"damage": 29, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_uses_skill_before_recovery_at_critical_boss_hp(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None},
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 24, "max_hp": 80},
            "enemies": [{"combat_id": 7, "id": "MONSTER.THE_INSATIABLE", "hp": 166, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_boss_floor_context_uses_act_specific_thresholds(self) -> None:
        for act, floor, expected in (
            (0, 16, "POTION.STRENGTH_POTION"), (0, 17, "POTION.SKILL_POTION"),
            (1, 15, "POTION.STRENGTH_POTION"), (1, 16, "POTION.SKILL_POTION"),
            (2, 14, "POTION.STRENGTH_POTION"), (2, 15, "POTION.SKILL_POTION"),
        ):
            with self.subTest(act=act, floor=floor):
                observation = {
                    "run": {"act": act, "floor": floor},
                    "legal_actions": [
                        {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                        {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                        {"type": "end_turn"},
                    ],
                    "player": {"hp": 20, "max_hp": 80},
                    "enemies": [{"combat_id": 7, "id": "MONSTER.THE_INSATIABLE", "hp": 321, "intents": []}],
                }
                self.assertEqual(choose(observation)["potion_id"], expected)

    def test_uses_weak_potion_against_lethal_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.WEAK_POTION", "target_id": 7}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 40, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.WEAK_POTION")

    def test_uses_ship_in_a_bottle_against_lethal_incoming(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.SHIP_IN_A_BOTTLE", "target_id": None}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 40, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SHIP_IN_A_BOTTLE")

    def test_uses_new_defensive_and_debuff_potions_when_low(self) -> None:
        cases = (
            ("POTION.FYSH_OIL", 0, "POTION.FYSH_OIL"),
            ("POTION.HEART_OF_IRON", 0, "POTION.HEART_OF_IRON"),
            ("POTION.POTION_OF_BINDING", 12, "POTION.POTION_OF_BINDING"),
        )
        for potion_id, incoming, expected in cases:
            with self.subTest(potion_id=potion_id):
                observation = {
                    "legal_actions": [{"type": "potion", "potion_id": potion_id, "target_id": None}],
                    "player": {"hp": 20, "max_hp": 80, "block": 0},
                    "enemies": [{"combat_id": 7, "hp": 40, "intents": [{"damage": incoming, "repeats": 1}]}] if incoming else [],
                }
                self.assertEqual(choose(observation)["potion_id"], expected)

    def test_uses_shackling_potion_first_in_boss_fight(self) -> None:
        # ShacklingPotionPower subclasses TemporaryStrengthPower, whose AfterSideTurnEnd removes
        # the -7 Strength once the enemy's own turn ends - it only blunts the enemy's very next
        # attack, so it should fire once an attack is actually incoming, ahead of offensive potions.
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SHACKLING_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 321, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SHACKLING_POTION")

    def test_uses_shackling_potion_when_low_hp_boss_is_attacking(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SHACKLING_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 9, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 190, "intents": [{"damage": 16, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SHACKLING_POTION")

    def test_withholds_shackling_potion_while_boss_is_not_attacking(self) -> None:
        # Bygone Effigy's opening turns (SLEEP_MOVE/WAKE_MOVE) deal no damage; spending Shackling
        # here would waste it entirely since it expires before any attack lands (regression: a
        # live run burned it on turn 1 against a sleeping boss for zero effect).
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SHACKLING_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 127, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.STRENGTH_POTION")

    def test_saves_shackling_potion_from_a_dangerous_regular_swarm(self) -> None:
        # sim13: Shackling got spent reactively on a low-HP Wriggler swarm (danger triggered by
        # enemy count/incoming, not boss length) and was gone by the time the actual boss (HP
        # >=100) needed it. Low-HP multi-enemy danger must not reach into Shackling.
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SHACKLING_POTION", "target_id": None},
                {"type": "potion", "potion_id": "POTION.BLOCK_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80, "block": 0},
            "enemies": [
                {"combat_id": 1, "hp": 18, "intents": [{"damage": 6, "repeats": 1}]},
                {"combat_id": 2, "hp": 19, "intents": [{"damage": 6, "repeats": 1}]},
                {"combat_id": 3, "hp": 20, "intents": [{"damage": 6, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.BLOCK_POTION")

    def test_uses_fortifier_when_block_exists(self) -> None:
        # Fortifier doubles the current block, so with block already up it is a good pick
        # against big incoming damage.
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FORTIFIER", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 60, "max_hp": 80, "block": 8},
            "enemies": [{"combat_id": 1, "hp": 40, "intents": [{"damage": 35, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.FORTIFIER")

    def test_saves_fortifier_when_current_or_affordable_block_survives(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card", "card_id": "CARD.FLAME_BARRIER", "hand_index": 0},
                {"type": "potion", "potion_id": "POTION.FORTIFIER", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 7, "max_hp": 80, "block": 14, "energy": 3},
            "hand": [{"index": 0, "id": "CARD.FLAME_BARRIER", "cost": 2, "type": "Skill", "vars": [{"id": "Block", "value": 32}]}],
            "enemies": [
                {"combat_id": 1, "hp": 21, "intents": [{"damage": 16, "repeats": 1}]},
                {"combat_id": 2, "hp": 100, "intents": [{"damage": 10, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.FLAME_BARRIER")
        observation["legal_actions"] = [
            {"type": "potion", "potion_id": "POTION.FORTIFIER", "target_id": None},
            {"type": "end_turn"},
        ]
        observation["player"]["block"] = 20
        observation["hand"] = []
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_saves_fortifier_when_no_block(self) -> None:
        # With zero block Fortifier gains nothing (it doubles current block), so it must be
        # saved and a different defensive potion used instead.
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FORTIFIER", "target_id": None},
                {"type": "potion", "potion_id": "POTION.WEAK_POTION", "target_id": 1},
                {"type": "end_turn"},
            ],
            "player": {"hp": 60, "max_hp": 80, "block": 0},
            "enemies": [{"combat_id": 1, "hp": 40, "intents": [{"damage": 35, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.WEAK_POTION")

    def test_does_not_use_fortifier_when_it_is_the_only_potion_without_block(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FORTIFIER", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 60, "max_hp": 80, "block": 0},
            "enemies": [{"combat_id": 1, "hp": 40, "intents": [{"damage": 35, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_does_not_manually_use_entropic_brew_when_low(self) -> None:
        # EntropicBrew (decompiled) only refills open potion slots with new random potions - it
        # has no heal/block/damage effect, so unlike a real recovery potion it does nothing to
        # help survive a low-HP turn and must not be burned reactively as one.
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.ENTROPIC_BREW", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 30, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_does_not_manually_use_fairy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.FAIRY_IN_A_BOTTLE", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_does_not_manually_use_bottled_potential_when_dangerous(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.BOTTLED_POTENTIAL", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 17, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 60, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_frantic_escape_before_other_cards(self) -> None:
        observation = {
            "enemies": [{"powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 1},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.FRANTIC_ESCAPE")

    def test_sandpit_uses_free_battle_trance_before_paid_draw(self) -> None:
        observation = {
            "player": {"hp": 14, "max_hp": 80, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.SHRUG_IT_OFF", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 8}, {"id": "Cards", "value": 1}]},
                {"index": 1, "id": "CARD.BATTLE_TRANCE", "cost": 0, "type": "Skill", "vars": [{"id": "Cards", "value": 3}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 98, "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}], "intents": [{"damage": 12, "repeats": 2}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 0},
                {"type": "card", "card_id": "CARD.BATTLE_TRANCE", "hand_index": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_plays_crimson_mantle_before_fiend_fire_on_safe_turn(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "energy": 8},
            "hand": [
                {"index": 0, "id": "CARD.CRIMSON_MANTLE", "cost": 1, "type": "Power"},
                {"index": 1, "id": "CARD.FIEND_FIRE", "cost": 2, "type": "Attack", "vars": [{"id": "Damage", "value": 7}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 321, "intents": [{"damage": 0, "repeats": 0}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.CRIMSON_MANTLE", "hand_index": 0},
                {"type": "card", "card_id": "CARD.FIEND_FIRE", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.CRIMSON_MANTLE")

    def test_plays_offering_before_fiend_fire_on_safe_turn(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "energy": 2},
            "hand": [
                {"index": 0, "id": "CARD.OFFERING", "cost": 0, "type": "Skill", "vars": [{"id": "HpLossRect", "value": 6}]},
                {"index": 1, "id": "CARD.FIEND_FIRE", "cost": 2, "type": "Attack", "vars": [{"id": "Damage", "value": 7}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 321, "intents": [{"damage": 0, "repeats": 0}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.OFFERING", "hand_index": 0},
                {"type": "card", "card_id": "CARD.FIEND_FIRE", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.OFFERING")

    def test_uses_cheapest_frantic_escape_when_duplicates_are_legal(self) -> None:
        observation = {
            "player": {"energy": 3},
            "hand": [
                {"index": 0, "id": "CARD.FRANTIC_ESCAPE", "type": "Skill", "cost": 2},
                {"index": 1, "id": "CARD.FRANTIC_ESCAPE", "type": "Skill", "cost": 1},
                {"index": 2, "id": "CARD.FLAME_BARRIER", "type": "Skill", "cost": 2},
            ],
            "enemies": [{"powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 0},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 1},
                {"type": "card", "card_id": "CARD.FLAME_BARRIER", "hand_index": 2},
            ],
        }
        self.assertEqual(choose(observation)["hand_index"], 1)

    def test_lethal_attack_precedes_sandpit_escape(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.FRANTIC_ESCAPE", "type": "Skill"},
            ],
            "enemies": [{
                "combat_id": 1,
                "hp": 5,
                "block": 0,
                "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 1}],
                "intents": [],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.STRIKE_IRONCLAD")

    def test_uses_potion_before_sandpit_escape_when_incoming_is_lethal(self) -> None:
        observation = {
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [{
                "combat_id": 1,
                "id": "MONSTER.THE_INSATIABLE",
                "slot": "boss",
                "hp": 321,
                "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}],
                "intents": [{"damage": 12, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 0},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_uses_potion_before_sandpit_escape_at_critical_hp(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [{
                "combat_id": 1,
                "id": "MONSTER.THE_INSATIABLE",
                "slot": "boss",
                "hp": 321,
                "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}],
                "intents": [{"damage": 12, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 0},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_uses_potion_before_sandpit_escape_on_half_hp_threat(self) -> None:
        observation = {
            "player": {"hp": 53, "max_hp": 80},
            "enemies": [{
                "combat_id": 1,
                "id": "MONSTER.THE_INSATIABLE",
                "slot": "boss",
                "hp": 166,
                "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 1}],
                "intents": [{"damage": 30, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 0},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.SKILL_POTION")

    def test_allows_reserved_potion_on_threatening_floor_boss(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 16},
            "turn": 7,
            "player": {"hp": 53, "max_hp": 80},
            "enemies": [{
                "combat_id": 1,
                "id": "MONSTER.THE_INSATIABLE",
                "hp": 166,
                "max_hp": 321,
                "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 1}],
                "intents": [{"damage": 30, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None},
                {"type": "potion", "potion_id": "POTION.SKILL_POTION", "target_id": None},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 0},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["type"], "potion")

    def test_uses_block_potion_on_threatening_act1_boss(self) -> None:
        observation = {
            "run": {"act": 0, "floor": 17},
            "player": {"hp": 37, "max_hp": 80, "block": 0},
            "enemies": [{
                "combat_id": 1,
                "id": "MONSTER.CEREMONIAL_BEAST",
                "hp": 188,
                "max_hp": 252,
                "intents": [{"damage": 18, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.LIQUID_BRONZE", "target_id": None},
                {"type": "potion", "potion_id": "POTION.BLOCK_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.BLOCK_POTION")

    def test_uses_draw_card_when_sandpit_is_critical_without_frantic_escape(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack"},
                {"index": 1, "id": "CARD.SHRUG_IT_OFF", "type": "Skill"},
            ],
            "enemies": [{"powers": [{"id": "POWER.SANDPIT_POWER", "amount": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0},
                {"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_does_not_repeat_frantic_escape_after_sandpit_is_safe(self) -> None:
        observation = {
            "enemies": [{"combat_id": 1, "hp": 100, "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 3}], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 1},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.STRIKE_IRONCLAD")

    def test_targets_crab_to_face_the_larger_attack(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [{"index": 0, "type": "Attack"}],
            "enemies": [{"combat_id": 7, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 12, "repeats": 1}]}],
            "legal_actions": [{"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7}],
        }
        self.assertEqual(choose(observation)["target_id"], 7)

    def test_crab_facing_ignores_threat_on_current_side(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "powers": [{"id": "POWER.BACK_ATTACK_RIGHT_POWER", "amount": 1}], "intents": [{"damage": 30, "repeats": 1}]},
                {"combat_id": 2, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 20, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_crab_facing_ignores_threat_without_legal_attack(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 30, "repeats": 1}]},
                {"combat_id": 2, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 20, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_lethal_attack_precedes_crab_facing_change(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.BASH", "type": "Attack", "vars": [{"id": "Damage", "value": 8}]},
            ],
            "enemies": [
                {"combat_id": 7, "hp": 50, "block": 0, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 12, "repeats": 1}]},
                {"combat_id": 8, "hp": 6, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7},
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 1, "target_id": 8},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual(action["target_id"], 8)
        self.assertEqual(action["decision_source"], "lethal_direct")

    def test_targetless_aoe_lethal_precedes_crab_facing_change(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [
                {"index": 0, "id": "CARD.HOWL_FROM_BEYOND", "type": "Attack", "vars": [{"id": "Damage", "value": 16}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{
                "combat_id": 7,
                "hp": 10,
                "block": 0,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 20, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.HOWL_FROM_BEYOND", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 7},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.HOWL_FROM_BEYOND")

    def test_crab_facing_chooses_highest_damage_attack(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.BASH", "type": "Attack", "vars": [{"id": "Damage", "value": 8}]},
            ],
            "enemies": [{
                "combat_id": 7, "hp": 50, "block": 0,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 12, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7},
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 1, "target_id": 7},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual(action["card_id"], "CARD.BASH")
        self.assertEqual(action["decision_source"], "crab_facing_direct")

    def test_crab_facing_counts_twin_strike_hits(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "energy": 1, "powers": [{"id": "POWER.SURROUNDED_POWER", "facing": "Right"}]},
            "hand": [
                {"index": 0, "id": "CARD.TWIN_STRIKE", "type": "Attack", "vars": [{"id": "Damage", "value": 5}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{
                "combat_id": 7, "hp": 100, "block": 0,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 20, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.TWIN_STRIKE", "hand_index": 0, "target_id": 7},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 7},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.TWIN_STRIKE")

    def test_aoe_selection_counts_whirlwind_energy_hits(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 4, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.WHIRLWIND", "type": "Attack", "vars": [{"id": "Damage", "value": 5}]},
                {"index": 1, "id": "CARD.HOWL_FROM_BEYOND", "type": "Attack", "vars": [{"id": "Damage", "value": 16}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 100, "block": 0, "powers": [], "intents": [{"damage": 25, "repeats": 1}]},
                {"combat_id": 2, "hp": 100, "block": 0, "powers": [], "intents": [{"damage": 25, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.WHIRLWIND", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.HOWL_FROM_BEYOND", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.WHIRLWIND")

    def test_crab_facing_avoids_self_damage_when_safe_attack_exists(self) -> None:
        observation = {
            "player": {"hp": 2, "max_hp": 80, "powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 15}]},
            ],
            "enemies": [{
                "combat_id": 7, "hp": 100, "block": 0,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 30, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7},
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 1, "target_id": 7},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.STRIKE_IRONCLAD")

    def test_crab_facing_rejects_self_damage_that_would_kill_player(self) -> None:
        observation = {
            "player": {"hp": 2, "max_hp": 80, "powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [{"index": 0, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 15}]}],
            "enemies": [{
                "combat_id": 7, "hp": 100, "block": 0,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 30, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 0, "target_id": 7},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_defensive_potion_before_crab_facing_when_incoming_is_dangerous(self) -> None:
        observation = {
            "player": {
                "hp": 60,
                "max_hp": 80,
                "powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}],
            },
            "hand": [{"index": 0, "type": "Attack"}],
            "enemies": [{
                "combat_id": 7,
                "hp": 120,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 35, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7},
                {"type": "potion", "potion_id": "POTION.BLOCK_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.BLOCK_POTION")

    def test_uses_energy_potion_before_crab_facing_when_incoming_is_dangerous(self) -> None:
        observation = {
            "player": {
                "hp": 60,
                "max_hp": 80,
                "powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}],
            },
            "hand": [{"index": 0, "type": "Attack", "cost": 1}],
            "enemies": [{
                "combat_id": 7,
                "hp": 120,
                "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}],
                "intents": [{"damage": 35, "repeats": 1}],
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7},
                {"type": "potion", "potion_id": "POTION.ENERGY_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.ENERGY_POTION")

    def test_unknown_card_does_not_crash_fallback(self) -> None:
        observation = {
            "player": {"block": 0},
            "hand": [{"index": 0, "type": "Attack", "vars": []}],
            "enemies": [{"combat_id": 1, "hp": 20, "intents": []}],
            "legal_actions": [{"type": "card", "card_id": "CARD.UNKNOWN", "hand_index": 0, "target_id": 1}, {"type": "end_turn"}],
        }
        self.assertEqual(choose(observation)["type"], "card")

    def test_fallback_uses_observed_damage_for_unknown_card(self) -> None:
        observation = {
            "player": {"block": 0},
            "hand": [{"index": 0, "type": "Attack", "vars": [{"id": "Damage", "value": 20}]}],
            "enemies": [{"combat_id": 1, "hp": 20, "block": 0, "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.UNKNOWN_ATTACK", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.UNKNOWN_ATTACK")

    def test_fallback_uses_observed_block_for_unknown_card(self) -> None:
        observation = {
            "player": {"block": 0},
            "hand": [
                {"index": 0, "type": "Skill", "vars": [{"id": "Block", "value": 10}]},
                {"index": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 20, "intents": [{"damage": 10, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.UNKNOWN_SKILL", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.UNKNOWN_SKILL")

    def test_low_hp_avoids_uncommitted_self_damage_when_attack_and_defend_are_legal(self) -> None:
        observation = {
            "player": {"hp": 28, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 15}]},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 3, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 3, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_low_hp_avoids_self_damage_for_a_safe_card_without_observed_damage_or_block(self) -> None:
        observation = {
            "player": {"hp": 28, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.CINDER", "type": "Skill", "vars": []},
                {"index": 2, "id": "CARD.INFLAME", "type": "Power", "vars": []},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.CINDER", "hand_index": 1, "target_id": None},
                {"type": "card", "card_id": "CARD.INFLAME", "hand_index": 2, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.CINDER")

    def test_low_hp_ends_turn_when_only_self_damage_cards_are_legal(self) -> None:
        observation = {
            "player": {"hp": 14, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 15}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_rollout_cannot_override_low_hp_self_damage_guard(self) -> None:
        observation = {
            "player": {"hp": 28, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        rolled = {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None}
        with patch("official_agent.rollout_choice", return_value=rolled):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=100)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_rollout_cannot_hide_corrupted_enchantment_self_damage(self) -> None:
        corrupted = {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1}
        observation = {
            "player": {"hp": 17, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "enchantment": "ENCHANTMENT.CORRUPTED", "vars": [{"id": "Damage", "value": 9}]},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 100, "intents": [{"damage": 0, "repeats": 0}]}],
            "legal_actions": [corrupted, {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1}, {"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=corrupted):
            self.assertNotEqual(choose(observation, enemy_data={"monsters": []}, simulations=100).get("card_id"), "CARD.STRIKE_IRONCLAD")

    def test_corrupted_lethal_does_not_trade_the_players_last_hp(self) -> None:
        observation = {
            "player": {"hp": 2, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "enchantment": "ENCHANTMENT.CORRUPTED", "vars": [{"id": "Damage", "value": 9}]}],
            "enemies": [{"combat_id": 1, "hp": 9, "intents": [{"damage": 0, "repeats": 0}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_plays_unmovable_before_block_when_the_pair_survives_lethal_damage(self) -> None:
        strike = {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 1}
        observation = {
            "player": {"hp": 16, "max_hp": 80, "block": 0, "energy": 3},
            "hand": [
                {"index": 0, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
                {"index": 1, "id": "CARD.UNMOVABLE", "cost": 2, "type": "Power", "vars": []},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 41, "intents": [{"damage": 22, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 0},
                {"type": "card", "card_id": "CARD.UNMOVABLE", "hand_index": 1},
                strike,
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=strike):
            action = choose(observation, enemy_data={"monsters": []}, simulations=100)
        self.assertEqual((action["card_id"], action["decision_reason"]), ("CARD.UNMOVABLE", "unmovable_before_block"))

    def test_plays_unmovable_instead_of_wasting_block_on_a_safe_turn(self) -> None:
        corrupted = {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1}
        observation = {
            "player": {"hp": 8, "max_hp": 80, "block": 0, "energy": 2},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "enchantment": "ENCHANTMENT.CORRUPTED", "vars": [{"id": "Damage", "value": 9}]},
                {"index": 1, "id": "CARD.FLAME_BARRIER", "cost": 2, "type": "Skill", "vars": [{"id": "Block", "value": 16}]},
                {"index": 2, "id": "CARD.UNMOVABLE", "cost": 2, "type": "Power", "vars": []},
            ],
            "enemies": [{"combat_id": 1, "hp": 110, "intents": [{"type": "Buff", "damage": 0, "repeats": 0}]}],
            "legal_actions": [
                corrupted,
                {"type": "card", "card_id": "CARD.FLAME_BARRIER", "hand_index": 1},
                {"type": "card", "card_id": "CARD.UNMOVABLE", "hand_index": 2},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=corrupted):
            action = choose(observation, enemy_data={"monsters": []}, simulations=100)
        self.assertEqual((action["card_id"], action["decision_reason"]), ("CARD.UNMOVABLE", "unmovable_over_wasted_block"))

    def test_active_unmovable_uses_the_block_card_that_survives_lethal_damage(self) -> None:
        observation = {
            "player": {"hp": 8, "max_hp": 80, "block": 0, "energy": 3, "powers": [{"id": "POWER.UNMOVABLE_POWER", "amount": 1}]},
            "hand": [
                {"index": 0, "id": "CARD.SHRUG_IT_OFF", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 8}]},
                {"index": 1, "id": "CARD.FLAME_BARRIER", "cost": 2, "type": "Skill", "vars": [{"id": "Block", "value": 16}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 100, "intents": [{"damage": 22, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 0},
                {"type": "card", "card_id": "CARD.FLAME_BARRIER", "hand_index": 1},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.FLAME_BARRIER", "unmovable_lethal_defense"))

    def test_rollout_allows_survivable_bloodletting_when_sandpit_is_critical(self) -> None:
        bloodletting = {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None}
        observation = {
            "player": {"hp": 46, "max_hp": 110, "block": 0, "energy": 1, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "cost": 0, "type": "Skill", "vars": [{"id": "HpLoss", "value": 3}]},
                {"index": 1, "id": "CARD.STONE_ARMOR", "cost": 1, "type": "Power"},
            ],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 105,
                "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}],
                "intents": [{"damage": 12, "repeats": 2}],
            }],
            "legal_actions": [
                bloodletting,
                {"type": "card", "card_id": "CARD.STONE_ARMOR", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=bloodletting):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=100)["card_id"], "CARD.BLOODLETTING")

    def test_rollout_plays_tremble_before_an_affordable_attack(self) -> None:
        headbutt = {"type": "card", "card_id": "CARD.HEADBUTT", "hand_index": 0, "target_id": 1}
        observation = {
            "player": {"hp": 46, "max_hp": 110, "block": 0, "energy": 3},
            "hand": [
                {"index": 0, "id": "CARD.HEADBUTT", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 9}]},
                {"index": 1, "id": "CARD.TREMBLE", "cost": 1, "type": "Skill", "vars": [{"id": "VulnerablePower", "value": 3}]},
                {"index": 2, "id": "CARD.BLOODLETTING", "cost": 0, "type": "Skill", "vars": [{"id": "HpLoss", "value": 3}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_INSATIABLE", "hp": 125, "intents": [{"damage": 12, "repeats": 2}], "powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}]}],
            "legal_actions": [
                headbutt,
                {"type": "card", "card_id": "CARD.TREMBLE", "hand_index": 1},
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 2},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=headbutt):
            action = choose(observation, enemy_data={"monsters": []}, simulations=100)
        self.assertEqual(action["card_id"], "CARD.TREMBLE")

    def test_rollout_allows_safe_self_damage_with_rupture_active(self) -> None:
        observation = {
            "player": {
                "hp": 14, "max_hp": 81, "block": 19, "energy": 2,
                "powers": [
                    {"id": "POWER.RUPTURE_POWER", "amount": 2},
                    {"id": "POWER.STRENGTH_POWER", "amount": 38},
                ],
            },
            "hand": [
                {"index": 0, "id": "CARD.BREAKTHROUGH", "cost": 1, "type": "Attack", "vars": [
                    {"id": "Damage", "value": 9}, {"id": "HpLoss", "value": 1},
                ]},
                {"index": 1, "id": "CARD.SHRUG_IT_OFF", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 8}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 220, "intents": [{"damage": 28, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BREAKTHROUGH", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][0]
        with patch("official_agent.rollout_choice", return_value=rolled):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=1)["card_id"], "CARD.BREAKTHROUGH")

        observation["player"].update(hp=13, block=19, energy=0)
        observation["hand"] = [
            {"index": 0, "id": "CARD.BLOODLETTING", "cost": 0, "type": "Skill", "vars": [{"id": "HpLoss", "value": 3}]},
        ]
        observation["legal_actions"] = [
            {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
            {"type": "end_turn"},
        ]
        with patch("official_agent.rollout_choice", return_value=observation["legal_actions"][0]):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=1)["card_id"], "CARD.BLOODLETTING")

    def test_rollout_allows_blood_wall_self_damage_when_it_blocks(self) -> None:
        observation = {
            "player": {"hp": 28, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.BLOOD_WALL", "type": "Skill", "vars": [{"id": "Block", "value": 16}]}],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOOD_WALL", "hand_index": 0, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][0]
        with patch("official_agent.rollout_choice", return_value=rolled):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=100)["card_id"], "CARD.BLOOD_WALL")

    def test_rollout_allows_self_damage_when_incoming_is_not_dangerous(self) -> None:
        observation = {
            "player": {"hp": 50, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]}],
            "enemies": [{"combat_id": 1, "hp": 190, "intents": [{"damage": 9, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        rolled = {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None}
        with patch("official_agent.rollout_choice", return_value=rolled):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=100)["card_id"], "CARD.BLOODLETTING")

    def test_lethal_self_damage_remains_allowed_to_finish_enemy(self) -> None:
        observation = {
            "player": {"hp": 14, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 50}]}],
            "enemies": [{"combat_id": 1, "hp": 20, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.HEMOKINESIS")

    def test_lethal_prefers_killing_the_enemy_that_will_attack(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 5, "block": 0, "intents": [{"damage": 22, "repeats": 1}]},
                {"combat_id": 2, "hp": 5, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 1)

    def test_rollout_cannot_override_lethal_attack(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 5, "block": 0, "intents": [{"damage": 20, "repeats": 1}]},
                {"combat_id": 2, "hp": 40, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][1]
        with patch("official_agent.rollout_choice", return_value=rolled):
            self.assertEqual(choose(observation, enemy_data={"monsters": []}, simulations=100)["target_id"], 1)

    def test_multi_primary_focuses_the_next_attack_on_the_greatest_threat(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 40, "powers": [], "intents": [{"damage": 24, "repeats": 1}]},
                {"combat_id": 2, "hp": 10, "powers": [], "intents": [{"damage": 24, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual(action["target_id"], 2)
        self.assertEqual(action["decision_source"], "generic_multi_primary_focus_direct")

    def test_multi_primary_focus_defers_to_block_before_losing_more_than_half_hp(self) -> None:
        strike = {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2}
        shrug = {"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 1}
        observation = {
            "player": {"hp": 27, "max_hp": 87, "block": 0, "energy": 1},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 5}]},
                {"index": 1, "id": "CARD.SHRUG_IT_OFF", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 9}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 27, "powers": [], "intents": []},
                {"combat_id": 2, "hp": 86, "powers": [], "intents": [{"damage": 16, "repeats": 1}]},
            ],
            "legal_actions": [strike, {**strike, "target_id": 1}, shrug, {"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=shrug):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["card_id"], action["decision_source"]), ("CARD.SHRUG_IT_OFF", "rollout_success"))

    def test_decimillipede_attack_focuses_highest_hp_segment(self) -> None:
        back = {"type": "card", "card_id": "CARD.IRON_WAVE", "hand_index": 0, "target_id": 3}
        observation = {
            "player": {"hp": 27, "max_hp": 80, "block": 20, "energy": 1},
            "hand": [{"index": 0, "id": "CARD.IRON_WAVE", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 6}, {"id": "Block", "value": 7}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", "hp": 17, "powers": [], "intents": [{"damage": 7, "repeats": 2}]},
                {"combat_id": 2, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", "hp": 44, "powers": [], "intents": [{"damage": 6, "repeats": 1}]},
                {"combat_id": 3, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_BACK", "hp": 32, "powers": [], "intents": [{"damage": 8, "repeats": 1}]},
            ],
            "legal_actions": [
                {**back, "target_id": target_id} for target_id in (1, 2, 3)
            ] + [{"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=back):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["target_id"], action["decision_reason"]), (2, "decimillipede_focus"))

    def test_decimillipede_does_not_finish_one_segment_while_others_live(self) -> None:
        low_segment = {"type": "card", "card_id": "CARD.HEADBUTT", "hand_index": 0, "target_id": 1}
        observation = {
            "player": {"hp": 40, "max_hp": 80, "block": 20, "energy": 1},
            "hand": [{"index": 0, "id": "CARD.HEADBUTT", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 10}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", "hp": 5, "powers": [], "intents": [{"damage": 6, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", "hp": 20, "powers": [], "intents": [{"damage": 6, "repeats": 1}]},
            ],
            "legal_actions": [
                low_segment,
                {"type": "card", "card_id": "CARD.HEADBUTT", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", return_value=low_segment):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["target_id"], action["decision_reason"]), (2, "decimillipede_focus"))

    def test_sets_up_two_card_kill_and_keeps_energy_for_block(self) -> None:
        hand = [
            {"index": 0, "id": "CARD.SETUP_STRIKE", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 5.25}, {"id": "StrengthPower", "value": 2}]},
            {"index": 1, "id": "CARD.PILLAGE", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 4.5}]},
            {"index": 2, "id": "CARD.SHRUG_IT_OFF", "cost": 1, "type": "Skill", "vars": [{"id": "Block", "value": 16}]},
        ]
        actions = [
            {"type": "card", "card_id": card["id"], "hand_index": card["index"], "target_id": target}
            for card in hand[:2] for target in (1, 2)
        ] + [{"type": "card", "card_id": "CARD.SHRUG_IT_OFF", "hand_index": 2}, {"type": "end_turn"}]
        observation = {
            "player": {"hp": 43, "max_hp": 80, "block": 0, "energy": 3}, "hand": hand,
            "enemies": [
                {"combat_id": 1, "hp": 10, "powers": [], "intents": [{"damage": 4, "repeats": 2}]},
                {"combat_id": 2, "hp": 86, "powers": [], "intents": [{"damage": 16, "repeats": 1}]},
            ],
            "legal_actions": actions,
        }
        action = choose(observation)
        self.assertEqual((action["target_id"], action["decision_source"]), (1, "two_card_lethal_setup_direct"))

    def test_ovicopter_turn_lethal_beats_single_egg_lethal(self) -> None:
        hand = [
            {"index": 0, "id": "CARD.PERFECTED_STRIKE", "cost": 2, "type": "Attack", "vars": [{"id": "CalculatedDamage", "value": 22}]},
            {"index": 1, "id": "CARD.BODY_SLAM", "cost": 0, "type": "Attack", "vars": [{"id": "CalculatedDamage", "value": 13}]},
        ]
        actions = [
            {"type": "card", "card_id": card["id"], "hand_index": card["index"], "target_id": target}
            for card in hand for target in (1, 2)
        ] + [{"type": "end_turn"}]
        observation = {
            "player": {"hp": 6, "max_hp": 87, "block": 13, "energy": 2}, "hand": hand,
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.OVICOPTER", "hp": 27, "block": 0, "powers": [], "intents": [{"damage": 10, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.TOUGH_EGG", "hp": 20, "block": 0, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 4, "repeats": 1}]},
            ],
            "legal_actions": actions,
        }
        action = choose(observation)
        self.assertEqual((action["target_id"], action["decision_source"]), (1, "ovicopter_turn_lethal_direct"))

    def test_nonurgent_multi_primary_focus_defers_to_rollout(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.INFLAME", "type": "Power", "cost": 1},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 6}]},
                {"index": 2, "id": "CARD.ANGER", "type": "Attack", "cost": 0, "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []},
                {"combat_id": 2, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.INFLAME", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 2},
                {"type": "card", "card_id": "CARD.ANGER", "hand_index": 2, "target_id": 1},
                {"type": "card", "card_id": "CARD.ANGER", "hand_index": 2, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][0]
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.INFLAME")

    def test_obscura_focus_ignores_reviving_parafright_lethal(self) -> None:
        rolled = {"type": "card", "card_id": "CARD.IRON_WAVE", "hand_index": 0, "target_id": 1}
        observation = {
            "player": {"hp": 10, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.IRON_WAVE", "cost": 1, "type": "Attack", "vars": [{"id": "Damage", "value": 17}, {"id": "Block", "value": 5}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.PARAFRIGHT", "hp": 12, "block": 0, "powers": [], "intents": [{"damage": 4, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.THE_OBSCURA", "hp": 46, "block": 6, "powers": [], "intents": [{"damage": 7, "repeats": 1}]},
            ],
            "legal_actions": [rolled, {**rolled, "target_id": 2}, {"type": "end_turn"}],
        }
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual((action["target_id"], action["decision_reason"]), (2, "obscura_focus"))
        self.assertEqual(action["decision_source"], "rollout_success")

    def test_queen_boss_focuses_torch_head_amalgam(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": 199, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 18, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.QUEEN", "hp": 400, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 1)

    def test_fallback_focuses_highest_hp_decimillipede_segment(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", "hp": 40, "powers": [], "intents": [{"damage": 20, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", "hp": 10, "powers": [], "intents": [{"damage": 1, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 1)

    def test_nonurgent_kin_follower_focus_defers_to_rollout(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 58, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 6, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.KIN_PRIEST", "hp": 190, "powers": [], "intents": [{"damage": 10, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][1] | {"simulations": 17, "search_value": 2.5}
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["target_id"], 1)
        self.assertEqual(action["decision_source"], "rollout_success")
        self.assertEqual(action["decision_reason"], "kin_follower_focus")
        self.assertEqual(action["simulations"], 17)
        self.assertNotIn("search_value", action)

    def test_kin_fallback_focuses_lowest_hp_follower(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 30, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 20, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.KIN_FOLLOWER", "hp": 20, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 1, "repeats": 1}]},
                {"combat_id": 3, "id": "MONSTER.KIN_PRIEST", "hp": 190, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 3},
                {"type": "end_turn"},
            ],
        }
        for _ in range(2):
            action = choose(observation)
            self.assertEqual(action["target_id"], 2)

    def test_kin_rollout_keeps_lethal_body_target(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 20, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": []},
                {"combat_id": 2, "id": "MONSTER.KIN_PRIEST", "hp": 5, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][1]
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["target_id"], 2)
        self.assertEqual(action["decision_source"], "lethal_direct")

    def test_kin_rollout_leaves_defense_action_untargeted(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [
                {"index": 0, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [{"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 20, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": []}, {"combat_id": 2, "id": "MONSTER.KIN_PRIEST", "hp": 100, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][0]
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action, {**rolled, "decision_source": "rollout_success"})

    def test_non_kin_rollout_target_is_unchanged(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "powers": [], "intents": []}, {"combat_id": 2, "id": "MONSTER.DUMMY", "hp": 100, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][1]
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["target_id"], 2)
        self.assertNotIn("decision_reason", action)

    def test_urgent_kin_turn_still_focuses_an_attacking_follower(self) -> None:
        observation = {
            "player": {"hp": 30, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 20, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 2, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.KIN_FOLLOWER", "hp": 30, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 12, "repeats": 1}]},
                {"combat_id": 3, "id": "MONSTER.KIN_PRIEST", "hp": 100, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 3},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual(action["target_id"], 1)
        self.assertEqual(action["decision_source"], "kin_follower_urgent_direct")

    def test_lethal_prefers_weaker_enemy_when_both_attack(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 9, "block": 0, "intents": [{"damage": 10, "repeats": 1}]},
                {"combat_id": 2, "hp": 3, "block": 0, "intents": [{"damage": 10, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_multi_enemy_threat_prefers_all_enemy_attack(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.THUNDERCLAP", "type": "Attack", "vars": [{"id": "Damage", "value": 4}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": [{"damage": 10, "repeats": 1}], "powers": []},
                {"combat_id": 2, "hp": 50, "block": 0, "intents": [{"damage": 10, "repeats": 1}], "powers": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.THUNDERCLAP", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.THUNDERCLAP", "hand_index": 0, "target_id": 2},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.THUNDERCLAP")

    def test_nonurgent_three_enemy_aoe_defers_to_rollout(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.THUNDERCLAP", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 4}]},
                {"index": 1, "id": "CARD.INFLAME", "type": "Power", "cost": 1},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []},
                {"combat_id": 2, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []},
                {"combat_id": 3, "id": "MONSTER.DUMMY", "hp": 100, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.THUNDERCLAP", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.INFLAME", "hand_index": 1, "target_id": None},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 2},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 3},
                {"type": "end_turn"},
            ],
        }
        rolled = observation["legal_actions"][1]
        with patch("official_agent.rollout_choice", return_value=rolled):
            action = choose(observation, enemy_data={"monsters": []}, simulations=1)
        self.assertEqual(action["card_id"], "CARD.INFLAME")
        self.assertEqual(action["decision_source"], "rollout_success")

    def test_multi_enemy_threat_does_not_choose_unsafe_aoe_over_block(self) -> None:
        observation = {
            "player": {"hp": 10, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.THUNDERCLAP", "type": "Attack", "vars": [{"id": "Damage", "value": 4}]},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": [{"damage": 5, "repeats": 1}], "powers": []},
                {"combat_id": 2, "hp": 50, "block": 0, "intents": [{"damage": 5, "repeats": 1}], "powers": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.THUNDERCLAP", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        action = choose(observation)
        self.assertEqual(action["card_id"], "CARD.DEFEND_IRONCLAD")
        self.assertEqual(action["decision_source"], "heuristic_fallback")

    def test_multi_enemy_threat_avoids_self_damage_aoe(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BREAKTHROUGH", "type": "Attack", "vars": [{"id": "Damage", "value": 9}, {"id": "SelfDamage", "value": 3}]},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": [{"damage": 10, "repeats": 1}], "powers": []},
                {"combat_id": 2, "hp": 50, "block": 0, "intents": [{"damage": 10, "repeats": 1}], "powers": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BREAKTHROUGH", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_focus_fire_prefers_weakest_enemy_when_nothing_is_lethal(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": []},
                {"combat_id": 2, "hp": 20, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_lethal_ignores_slippery_enemy(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 5, "block": 0, "powers": [{"id": "POWER.SLIPPERY_POWER", "amount": 8}], "intents": []},
                {"combat_id": 2, "hp": 5, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_lethal_accounts_for_hard_to_kill_cap(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.GIANT_ROCK", "type": "Attack", "vars": [{"id": "Damage", "value": 16}]}],
            "enemies": [
                # 16 damage is capped at 9 by HardToKill, so this Exoskeleton is NOT lethal.
                {"combat_id": 1, "hp": 12, "block": 0, "powers": [{"id": "POWER.HARD_TO_KILL_POWER", "amount": 9}], "intents": []},
                {"combat_id": 2, "hp": 10, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.GIANT_ROCK", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.GIANT_ROCK", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_lethal_accounts_for_soar_power(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.OWL_MAGISTRATE", "hp": 5, "block": 0, "powers": [{"id": "POWER.SOAR_POWER", "amount": 1}], "intents": [{"damage": 20, "repeats": 1}]},
                {"combat_id": 2, "id": "MONSTER.DUMMY", "hp": 6, "block": 0, "powers": [], "intents": [{"damage": 1, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_rest_heals_near_boss(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 14},
            "player": {"hp": 64, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}, {"option_id": "HATCH"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HEAL")

    def test_rest_hatches_mid_act_when_healthy(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 5},
            "player": {"hp": 64, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}, {"option_id": "HATCH"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HATCH")

    def test_focus_fire_does_not_change_card_priority(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BASH", "type": "Attack", "vars": [{"id": "Damage", "value": 8}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": []},
                {"combat_id": 2, "hp": 20, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 0, "target_id": 2},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.BASH")

    def test_reward_takes_modeled_bully(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BULLY"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BULLY")

    def test_reward_prefers_feed_when_low_hp(self) -> None:
        observation = {
            "player": {"hp": 27, "max_hp": 80},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.EXPECT_A_FIGHT"},
                {"type": "card_reward", "card_id": "CARD.FEED"},
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.FEED")

    def test_shop_buys_one_missing_required_card(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD"],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "buy_card", "card_id": "CARD.RUPTURE"},
                {"type": "skip"},
            ],
        }
        action = choose(observation)
        self.assertEqual(action["card_id"], "CARD.PERFECTED_STRIKE")
        self.assertEqual(action["decision_source"], "phase_shop")

    def test_shop_prefers_basic_remove_over_ordinary_card_only(self) -> None:
        cases = [
            (["CARD.STRIKE_IRONCLAD"], "CARD.ANGER", "remove"),
            (["CARD.STRIKE_IRONCLAD"], "CARD.INFLAME", "buy_card"),
            (["CARD.STRIKE_IRONCLAD", "CARD.INFLAME"], "CARD.INFLAME", "remove"),
        ]
        for deck, card_id, expected_type in cases:
            with self.subTest(deck=deck, card_id=card_id):
                observation = {
                    "phase": "shop",
                    "deck": deck,
                    "legal_actions": [
                        {"type": "buy_card", "card_id": card_id},
                        {"type": "remove", "card_id": "CARD.STRIKE_IRONCLAD"},
                        {"type": "skip"},
                    ],
                }
                self.assertEqual(choose_shop(observation)["type"], expected_type)

    def test_shop_removes_basic_before_starvation_driven_block_buy(self) -> None:
        # A block-starved Act 2 deck: the old order bought a strong block card here every time,
        # which grew the deck and left the starvation flag still set on the next visit.
        deck = ["CARD.STRIKE_IRONCLAD"] * 10 + ["CARD.BASH"] * 8 + ["CARD.DEFEND_IRONCLAD"] * 6
        observation = {
            "phase": "shop",
            "run": {"act": 1},
            "deck": deck,
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.BLOOD_WALL"},
                {"type": "remove", "card_id": "CARD.STRIKE_IRONCLAD"},
                {"type": "skip"},
            ],
        }
        action = choose_shop(observation)
        self.assertEqual((action["type"], action["card_id"]), ("remove", "CARD.STRIKE_IRONCLAD"))
        # With nothing left to thin, the same shop still buys the block card.
        observation["legal_actions"] = [
            {"type": "buy_card", "card_id": "CARD.BLOOD_WALL"},
            {"type": "skip"},
        ]
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.BLOOD_WALL")

    def test_shop_removes_legal_curse_before_high_value_purchase(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD", "CARD.CURSE"],
            "deck_cards": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "removable": True},
                {"index": 1, "id": "CARD.CURSE", "type": "Curse", "removable": True},
            ],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "remove", "card_index": 1, "card_id": "CARD.CURSE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["type"], "remove")

    def test_shop_ignores_nonremovable_curse(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD", "CARD.CURSE"],
            "player": {
                "deck_cards": [
                    {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "removable": True},
                    {"index": 1, "id": "CARD.CURSE", "type": "Curse", "removable": False},
                ],
            },
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_large_deck_card_policy_matches_shop_and_reward(self) -> None:
        def stable_deck(size):
            return (
                ["CARD.FLAME_BARRIER"] * 3
                + ["CARD.POMMEL_STRIKE"] * 2
                + ["CARD.STRIKE_IRONCLAD"] * (size - 5)
            )

        def assert_choice(label, deck, act, expected):
            card_id = "CARD.ANGER"
            shop = {
                "phase": "shop",
                "run": {"act": act},
                "deck": deck,
                "legal_actions": [{"type": "buy_card", "card_id": card_id}, {"type": "skip"}],
            }
            reward = {
                "run": {"act": act},
                "player": {"deck": deck},
                "legal_actions": [
                    {"type": "card_reward", "card_id": card_id},
                    {"type": "card_reward_alternative", "option_id": "Skip"},
                ],
            }
            with self.subTest(label=f"{label}_shop"):
                selected = choose_shop(shop)
                self.assertEqual(selected.get("card_id") == card_id, expected)
                if not expected:
                    self.assertEqual(selected["type"], "skip")
            with self.subTest(label=f"{label}_reward"):
                selected = choose_card_reward(reward)
                self.assertEqual(selected.get("card_id") == card_id, expected)
                if not expected:
                    self.assertEqual(selected["option_id"], "Skip")

        cases = [
            ("act1_below_limit", stable_deck(19), 0, True),
            ("act1_limit", stable_deck(20), 0, False),
            ("act2_below_limit", stable_deck(24), 1, True),
            ("act2_limit", stable_deck(25), 1, False),
            ("act3_below_limit", stable_deck(29), 2, True),
            ("act3_limit", stable_deck(30), 2, False),
        ]
        for case in cases:
            assert_choice(*case)

    def test_large_deck_limit_uses_low_cost_battle_trance_margin(self) -> None:
        def observation(size, battle_specs):
            deck = (
                ["CARD.FLAME_BARRIER"] * 3
                + ["CARD.POMMEL_STRIKE"] * 2
                + ["CARD.STRIKE_IRONCLAD"] * (size - 5)
            )
            metadata = [
                {"index": index, "id": card_id, "type": "Skill", "cost": 1, "upgrade": 0}
                for index, card_id in enumerate(deck)
            ]
            for index, (cost, upgrade) in enumerate(battle_specs, start=5):
                deck[index] = "CARD.BATTLE_TRANCE"
                metadata[index] |= {"id": "CARD.BATTLE_TRANCE", "cost": cost, "upgrade": upgrade}
            return {
                "phase": "shop",
                "run": {"act": 1},
                "deck": deck,
                "deck_cards": metadata,
                "legal_actions": [
                    {"type": "buy_card", "card_id": "CARD.ANGER"},
                    {"type": "skip"},
                ],
            }

        cases = [
            ("low_cost", 26, [(1, 0)], "buy_card"),
            ("cost_two", 26, [(2, 0)], "skip"),
            ("normal_then_upgraded", 27, [(1, 0), (1, 1)], "buy_card"),
            ("upgraded_then_normal", 27, [(1, 1), (1, 0)], "buy_card"),
        ]
        for label, size, battle_specs, expected_type in cases:
            with self.subTest(label=label):
                self.assertEqual(choose_shop(observation(size, battle_specs))["type"], expected_type)

    def test_shop_uses_known_boss_axis(self) -> None:
        observation = {
            "phase": "shop",
            "run": {"boss_encounter_id": "ENCOUNTER.THE_INSATIABLE_BOSS"},
            "deck": [],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.BLUDGEON"},
                {"type": "buy_card", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_shop_buys_high_value_potion_over_mid_value_relic(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD"] * 12,
            "legal_actions": [
                {"type": "buy_potion", "potion_id": "POTION.SHACKLING_POTION"},
                {"type": "buy_relic", "relic_id": "RELIC.ART_OF_WAR"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["type"], "buy_potion")

    def test_shop_keeps_top_relic_over_potion(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD"] * 12,
            "legal_actions": [
                {"type": "buy_potion", "potion_id": "POTION.SHACKLING_POTION"},
                {"type": "buy_relic", "relic_id": "RELIC.CLOAK_CLASP"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["type"], "buy_relic")

    def test_shop_buys_strong_block_over_mid_value_relic_when_defense_starved(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD"] * 12,
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "buy_relic", "relic_id": "RELIC.ART_OF_WAR"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_shop_removes_defend_after_perfected_strike(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD", "CARD.PERFECTED_STRIKE", "CARD.DEFEND_IRONCLAD"],
            "legal_actions": [
                {"type": "remove", "card_id": "CARD.STRIKE_IRONCLAD"},
                {"type": "remove", "card_id": "CARD.DEFEND_IRONCLAD"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_reward_prefers_tier_card_over_unknown_card(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_core_beats_s_tier_card(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_prefers_perfected_strike_over_vulnerable_core_when_unresolved(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.TREMBLE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_strike_axis_prefers_second_perfected_strike(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.PERFECTED_STRIKE"}, {"id": "CARD.STRIKE_IRONCLAD"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_without_strike_axis_keeps_first_tier_card(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.RUPTURE"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TRUE_GRIT")

    def test_reward_does_not_seed_strike_axis_after_self_damage_axis(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 5 + [{"id": "CARD.RUPTURE"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.IRON_WAVE"},
                {"type": "card_reward", "card_id": "CARD.RAMPAGE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.IRON_WAVE")

    def test_reward_switches_core_after_axis_is_owned(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.PERFECTED_STRIKE"}, {"id": "CARD.RUPTURE"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.HELLRAISER"},
                {"type": "card_reward", "card_id": "CARD.TEAR_ASUNDER"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.HELLRAISER")

    def test_shop_core_beats_s_tier_card_and_buys_once(self) -> None:
        observation = {
            "phase": "shop",
            "deck": [],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "buy_card", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_shop_strike_axis_does_not_buy_rupture(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.PERFECTED_STRIKE"],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.RUPTURE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["type"], "skip")

    def test_shop_completes_self_damage_engine_despite_strike_axis(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.PERFECTED_STRIKE", "CARD.BLOODLETTING"],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.RUPTURE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.RUPTURE")

    def test_shop_skips_duplicate_engine_and_debuff_cards(self) -> None:
        for card_id in ("CARD.BLOODLETTING", "CARD.UPPERCUT"):
            with self.subTest(card_id=card_id):
                observation = {
                    "phase": "shop",
                    "deck": ["CARD.RUPTURE", card_id],
                    "legal_actions": [
                        {"type": "buy_card", "card_id": card_id},
                        {"type": "skip"},
                    ],
                }
                self.assertEqual(choose_shop(observation)["type"], "skip")

    def test_unresolved_deck_uses_tiers_without_random_core(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_uncommitted_self_damage_does_not_force_bloodletting(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_reward_avoids_second_uncommitted_self_damage_card(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.BLOODLETTING"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward", "card_id": "CARD.EVIL_EYE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.EVIL_EYE")

    def test_uncommitted_self_damage_loses_same_tier_to_normal_card(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

    def test_uncommitted_rupture_does_not_force_core(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_self_damage_enabler_seeds_rupture_core(self) -> None:
        observation = {
            "player": {"deck": ["CARD.BLOODLETTING"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.RUPTURE")

    def test_self_damage_axis_prefers_follow_up(self) -> None:
        observation = {
            "player": {"deck": ["CARD.RUPTURE"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TEAR_ASUNDER"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TEAR_ASUNDER")

    def test_vulnerable_axis_prefers_missing_apply(self) -> None:
        observation = {
            "player": {"deck": ["CARD.BASH", "CARD.MOLTEN_FIST"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TREMBLE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TREMBLE")

    def test_exhaust_axis_prefers_missing_payoff(self) -> None:
        observation = {
            "player": {"deck": ["CARD.TRUE_GRIT", "CARD.CORRUPTION"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.DARK_EMBRACE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.DARK_EMBRACE")

    def test_uncommitted_exhaust_payoff_does_not_force_high_tier(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.FEEL_NO_PAIN"},
                {"type": "card_reward", "card_id": "CARD.TWIN_STRIKE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TWIN_STRIKE")

    def test_exhaust_enabler_keeps_payoff_priority(self) -> None:
        observation = {
            "player": {"deck": ["CARD.TRUE_GRIT"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.FEEL_NO_PAIN"},
                {"type": "card_reward", "card_id": "CARD.TWIN_STRIKE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.FEEL_NO_PAIN")

    def test_shop_uncommitted_exhaust_payoff_does_not_force_high_tier(self) -> None:
        observation = {
            "phase": "shop",
            "deck": [],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.DARK_EMBRACE"},
                {"type": "buy_card", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_shop_prefers_missing_draw_over_mid_value_relic(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD"] * 5 + ["CARD.DEFEND_IRONCLAD"] * 5,
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.BURNING_PACT"},
                {"type": "buy_relic", "relic_id": "RELIC.PARRYING_SHIELD"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.BURNING_PACT")

    def test_reward_prefers_strong_defense_when_deck_lacks_block(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_prefers_higher_tier_attack_over_strong_defense(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.EVIL_EYE"},
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

    def test_reward_prefers_higher_tier_attack_over_stone_armor(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.STONE_ARMOR"},
                {"type": "card_reward", "card_id": "CARD.ASHEN_STRIKE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ASHEN_STRIKE")

    def test_reward_prefers_strong_defense_at_one_third_block(self) -> None:
        # sim19 died with exactly 8 block of 24 cards (33%): the old "under a third" threshold
        # never fired. Strong defense must be prioritized until the deck clears the threshold.
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 16 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 8},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_prefers_strong_defense_when_block_is_only_defends(self) -> None:
        # 6 of 13 cards are block (>40%), but they are all weak Defends (5 block): fewer than
        # 2 strong block cards means the deck is still defense-needy and strong defense stays
        # a priority.
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 7 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 6},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_prefers_strong_defense_when_block_is_only_iron_waves(self) -> None:
        # 6 of 13 cards are block (>40%), but Iron Wave is also only 5 block: without 2 strong
        # (8+) block cards the deck is still judged defense-needy, so strong defense remains
        # preferable.
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 7 + [{"id": "CARD.IRON_WAVE"}] * 6},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_keeps_s_tier_offense_when_deck_is_balanced(self) -> None:
        # Balanced: 6 block of 12 cards (>40%) with 2 strong blocks (Shrug It Off x2).
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 6 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4 + [{"id": "CARD.SHRUG_IT_OFF"}] * 2},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_reward_prefers_strong_defense_in_a_large_deck_with_two_strong_blocks(self) -> None:
        # At 17 cards, two strong blocks are too thin for Act 2 even when total block cards clear
        # the 40% line; a third real answer is preferable to another strike-axis card.
        observation = {
            "player": {"deck": (
                [{"id": "CARD.STRIKE_IRONCLAD"}] * 7
                + [{"id": "CARD.DEFEND_IRONCLAD"}] * 8
                + [{"id": "CARD.SHRUG_IT_OFF"}] * 2
            )},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.FLAME_BARRIER"},
                {"type": "card_reward", "card_id": "CARD.SETUP_STRIKE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.FLAME_BARRIER")

    def test_reward_skips_low_tier_card_in_a_large_deck_without_a_shortage(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 5},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.CINDER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_keeps_low_tier_card_for_large_deck_defense_or_draw_shortage(self) -> None:
        deck = [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 5
        for card_id in ("CARD.TRUE_GRIT", "CARD.FINESSE"):
            with self.subTest(card_id=card_id):
                observation = {
                    "player": {"deck": deck},
                    "legal_actions": [
                        {"type": "card_reward", "card_id": card_id},
                        {"type": "card_reward_alternative", "option_id": "Skip"},
                    ],
                }
                self.assertEqual(choose_card_reward(observation)["card_id"], card_id)

    def test_reward_defense_does_not_override_core(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_never_takes_relax_when_alternatives_exist(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RELAX"},
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

    def test_reward_skips_when_only_relax_is_offered(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RELAX"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_prefers_high_tier_energy_over_weak_block(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BLOODLETTING")

    def test_reward_prefers_same_tier_taunt_over_offense_when_defense_is_needed(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.HEADBUTT"},
                {"type": "card_reward", "card_id": "CARD.TAUNT"},
                {"type": "card_reward", "card_id": "CARD.HAVOC"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TAUNT")

    def test_reward_prefers_new_same_tier_card_over_duplicate(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.TREMBLE"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TREMBLE"},
                {"type": "card_reward", "card_id": "CARD.FIEND_FIRE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.FIEND_FIRE")

    def test_reward_prefers_pommel_strike_over_true_grit_when_defense_is_needed(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 5 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4 + [{"id": "CARD.BASH"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.POMMEL_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.JUGGLING"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.POMMEL_STRIKE")

    def test_event_never_picks_paels_horn(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_HORN"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_FLESH"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_neow_priority_beats_presented_order(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "NEOW",
            "legal_actions": [
                {"type": "event_option", "option_index": 0, "relic_id": "RELIC.NEOWS_TORMENT"},
                {"type": "event_option", "option_index": 1, "relic_id": "RELIC.SMALL_CAPSULE"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.SMALL_CAPSULE")

    def test_neow_priority_ignores_deck_and_hp(self) -> None:
        for player, deck in [
            ({"hp": 80, "max_hp": 80}, []),
            ({"hp": 1, "max_hp": 80}, ["CARD.STRIKE_IRONCLAD"] * 20),
        ]:
            observation = {
                "phase": "event",
                "event_id": "NEOW",
                "player": player,
                "deck": deck,
                "legal_actions": [
                    {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.GOLDEN_PEARL"},
                    {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.NEOWS_TALISMAN"},
                ],
            }
            self.assertEqual(choose_event(observation)["relic_id"], "RELIC.NEOWS_TALISMAN")

    def test_neow_priority_excludes_locked_and_ranks_unknown_last(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "NEOW",
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.UNKNOWN"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.SMALL_CAPSULE", "is_locked": True},
                {"type": "event_relic", "option_index": 2, "relic_id": "RELIC.LARGE_CAPSULE"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.LARGE_CAPSULE")

    def test_neow_unknown_relic_uses_presented_order(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "NEOW",
            "legal_actions": [
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.UNKNOWN_A"},
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.UNKNOWN_B"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.UNKNOWN_A")

    def test_neow_only_proceed_option_keeps_existing_processing(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "NEOW",
            "legal_actions": [{"type": "event_option", "option_index": 0, "is_proceed": True}],
        }
        self.assertEqual(choose_event(observation)["option_index"], 0)

    def test_neow_priority_has_28_unique_relics(self) -> None:
        self.assertEqual(len(NEOW_RELIC_PRIORITY), 28)
        self.assertEqual(len(set(NEOW_RELIC_PRIORITY)), 28)

    def test_event_option_wire_format_picks_paels_flesh(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "legal_actions": [
                {"type": "event_option", "option_index": 0, "relic_id": "RELIC.PAELS_HORN"},
                {"type": "event_option", "option_index": 1, "relic_id": "RELIC.PAELS_FLESH"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_event_prefers_energy_over_weaker_relic(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_EYE"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_LEGION"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_LEGION")

    def test_event_relic_tier_follows_exhaust_axis(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "deck": ["CARD.CORRUPTION", "CARD.TRUE_GRIT"],
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_EYE"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_LEGION"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_EYE")

    def test_event_block_starved_prefers_block_pet(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "deck": ["CARD.STRIKE_IRONCLAD"] * 12,
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_FLESH"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_LEGION"},
            ],
        }
        # Block pet gets +2 for block-starved decks but still loses to +1 max energy.
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_event_low_hp_boosts_energy_relics(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 30, "max_hp": 80},
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_FLESH"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_HORN"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_event_option_table_preserves_hardcoded_choices(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "BYRDONIS_NEST",
            "legal_actions": [
                {"type": "event_option", "option_index": 0, "text_key": "BYRDONIS_NEST.LEAVE"},
                {"type": "event_option", "option_index": 1, "text_key": "BYRDONIS_NEST.TAKE"},
            ],
        }
        self.assertEqual(choose_event(observation)["option_index"], 1)

    def test_unknown_event_returns_bridge_fallback(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "UNKNOWN_EVENT",
            "legal_actions": [{"type": "event_option", "option_index": 0, "text_key": "UNKNOWN_EVENT.CHOICE"}],
        }
        self.assertEqual(choose_event(observation)["type"], "event_fallback")

    def test_event_with_only_proceed_option_can_close(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "UNKNOWN_EVENT",
            "legal_actions": [{"type": "event_option", "option_index": 0, "text_key": "UNKNOWN_EVENT.PROCEED", "is_proceed": True}],
        }
        self.assertEqual(choose_event(observation)["option_index"], 0)

    def test_event_option_scores_prefer_immediate_sunken_statue_reward(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "SUNKEN_STATUE",
            "legal_actions": [
                {"type": "event_option", "option_index": 0, "text_key": "SUNKEN_STATUE.DIVE_INTO_WATER"},
                {"type": "event_option", "option_index": 1, "text_key": "SUNKEN_STATUE.GRAB_SWORD"},
            ],
        }
        self.assertEqual(choose_event(observation)["option_index"], 0)

    def test_self_help_book_prefers_block_when_block_starved(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "SELF_HELP_BOOK",
            "deck": ["CARD.STRIKE_IRONCLAD"] * 12,
            "legal_actions": [
                {"type": "event_option", "option_index": 0, "text_key": "SELF_HELP_BOOK.READ_THE_BACK"},
                {"type": "event_option", "option_index": 1, "text_key": "SELF_HELP_BOOK.READ_PASSAGE"},
                {"type": "event_option", "option_index": 2, "text_key": "SELF_HELP_BOOK.READ_ENTIRE_BOOK"},
            ],
        }
        self.assertEqual(choose_event(observation)["option_index"], 1)

    def test_self_help_book_prefers_damage_when_block_is_sufficient(self) -> None:
        observation = {
            "phase": "event",
            "event_id": "SELF_HELP_BOOK",
            "deck": ["CARD.SHRUG_IT_OFF"] * 4 + ["CARD.STRIKE_IRONCLAD"] * 6,
            "legal_actions": [
                {"type": "event_option", "option_index": 0, "text_key": "SELF_HELP_BOOK.READ_THE_BACK"},
                {"type": "event_option", "option_index": 1, "text_key": "SELF_HELP_BOOK.READ_PASSAGE"},
                {"type": "event_option", "option_index": 2, "text_key": "SELF_HELP_BOOK.READ_ENTIRE_BOOK"},
            ],
        }
        self.assertEqual(choose_event(observation)["option_index"], 0)

    def test_event_relic_scores_cover_all_ancients(self) -> None:
        pael = {"RELIC.PAELS_CLAW", "RELIC.PAELS_TOOTH", "RELIC.PAELS_GROWTH", "RELIC.PAELS_LEGION",
                "RELIC.PAELS_FLESH", "RELIC.PAELS_TEARS", "RELIC.PAELS_HORN", "RELIC.PAELS_WING",
                "RELIC.PAELS_EYE", "RELIC.PAELS_BLOOD"}
        orobas = {"RELIC.ELECTRIC_SHRYMP", "RELIC.GLASS_EYE", "RELIC.SAND_CASTLE", "RELIC.ALCHEMICAL_COFFER",
                  "RELIC.DRIFTWOOD", "RELIC.RADIANT_PEARL", "RELIC.PRISMATIC_GEM"}
        tezcatara = {"RELIC.NUTRITIOUS_SOUP", "RELIC.VERY_HOT_COCOA", "RELIC.YUMMY_COOKIE", "RELIC.BIIIG_HUG",
                     "RELIC.STORYBOOK", "RELIC.TOASTY_MITTENS", "RELIC.GOLDEN_COMPASS", "RELIC.PUMPKIN_CANDLE",
                     "RELIC.TOY_BOX", "RELIC.SEAL_OF_GOLD"}
        self.assertTrue(pael <= RELIC_SCORES.keys())
        self.assertTrue(orobas <= RELIC_SCORES.keys())
        self.assertTrue(tezcatara <= RELIC_SCORES.keys())

    def test_feed_is_modeled_for_rollout_and_lethal(self) -> None:
        self.assertIn("CARD.FEED", CARD_NAMES)
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.FEED", "type": "Attack", "vars": [{"id": "Damage", "value": 10}]}],
            "enemies": [{"combat_id": 1, "hp": 10, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.FEED", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.FEED")

    def test_dominate_is_modeled_for_rollout(self) -> None:
        # Dominate used to disable the rollout entirely because it was missing from CARD_NAMES;
        # it must now be recognized so the search runs even while it sits in hand.
        self.assertIn("CARD.DOMINATE", CARD_NAMES)

    def test_boss_fight_cards_are_modeled_for_rollout(self) -> None:
        # The Insatiable boss fight used Byrd Swoop / Pillage / Equilibrium; unmodeled cards in
        # hand disabled the turn-1 rollout. All three must now be recognized by the simulator.
        self.assertTrue({"CARD.BYRD_SWOOP", "CARD.PILLAGE", "CARD.EQUILIBRIUM"} <= set(CARD_NAMES))
        self.assertEqual(CARD_NAMES["CARD.BLOOD_WALL"], "Blood Wall")

    def test_rollout_runs_with_one_unknown_card_in_hand(self) -> None:
        # The rollout gate used to require ALL hand cards to be modeled (any unknown card
        # disabled the search entirely); one unknown card must not abandon the rollout.
        import json
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD"},
                {"index": 1, "id": "CARD.UNKNOWN_CARD"},
            ],
            "draw_pile": [],
            "discard_pile": [],
            "exhaust_pile": [],
            "turn": 1,
            "enemies": [{"combat_id": 1, "id": "MONSTER.THE_OBSCURA", "hp": 20, "block": 0, "powers": [], "intents": [{"damage": 8, "repeats": 1}], "move": "PIERCING_GAZE_MOVE", "history": [], "slot": "obscura"}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        # The rollout must run (returning the Strike action with a search value) instead of
        # silently falling back to the heuristic because CARD.UNKNOWN_CARD is in hand.
        action = choose(observation, data, 200)
        self.assertEqual(action["card_id"], "CARD.STRIKE_IRONCLAD")
        self.assertIn("simulations", action)

    def test_rollout_keeps_potions_empty_when_no_potion_is_allowed(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0, "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": ""}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.search", return_value=[("End turn", 0.0)]) as searched:
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(searched.call_args.args[0].player_potions, ())
        self.assertEqual(_rollout_allowed_potions(observation, observation["legal_actions"]), ())

    def test_rollout_saves_explosive_ampoule_while_every_enemy_is_slippery(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack"}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.VANTOM", "hp": 173, "max_hp": 173, "powers": [{"id": "POWER.SLIPPERY_POWER", "amount": 8}], "intents": [{"damage": 7, "repeats": 1}]}],
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.EXPLOSIVE_AMPOULE", "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")
        self.assertEqual(_rollout_allowed_potions(observation, observation["legal_actions"]), ())

    def test_rollout_can_choose_an_allowed_block_potion(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "run": {"act": 77, "floor": 99, "room_type": "Monster"},
            "turn": 2,
            "player": {"hp": 20, "max_hp": 80, "block": 0, "energy": 3, "powers": {}, "relics": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "potions": [{"id": POTION_BLOCK}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0, "powers": [], "intents": [{"damage": 10, "repeats": 1}], "move": "IDLE_MOVE", "history": [], "slot": ""}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "potion", "potion_id": POTION_BLOCK, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.search", return_value=(
            ("potion:" + POTION_BLOCK, 1.0),
        )) as searched:
            action = choose(observation, data, 1)
        self.assertEqual(action["potion_id"], POTION_BLOCK)
        self.assertEqual(action["decision_source"], "rollout_success")
        self.assertEqual(searched.call_args.args[0].player_potions, (POTION_BLOCK,))

    def test_rollout_exception_tags_heuristic_fallback(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 50, "block": 0, "powers": [], "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.rollout_choice", side_effect=KeyError("test")):
            action = choose(observation, {"monsters": []}, 1)
        self.assertEqual(action["decision_source"], "heuristic_fallback")
        self.assertEqual(action["decision_reason"], "rollout_exception_key_error")

    def test_missing_indexed_rollout_card_uses_heuristic_fallback(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 50, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.search", return_value=[("card:99@0", 1.0)]):
            action = choose(observation, data, 1)
        self.assertEqual(action["card_id"], "CARD.STRIKE_IRONCLAD")
        self.assertEqual(action["decision_source"], "heuristic_fallback")
        self.assertEqual(action["decision_reason"], "rollout_exception_stop_iteration")

    def test_rollout_can_conserve_modeled_fysh_oil(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "run": {"act": 1, "floor": 16, "room_type": "Boss"},
            "turn": 2,
            "player": {"hp": 45, "max_hp": 80, "block": 0, "energy": 3, "powers": [], "relics": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "potions": [{"id": "POTION.FYSH_OIL"}],
            "enemies": [{"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 123, "max_hp": 123, "block": 0, "powers": [], "intents": [{"damage": 15, "repeats": 1}], "move": "IDLE_MOVE", "history": [], "slot": ""}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "potion", "potion_id": "POTION.FYSH_OIL", "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.FYSH_OIL")
        with patch("official_agent.search", return_value=(("End turn", 0.0),)) as searched:
            self.assertEqual(choose(observation, data, 1)["type"], "end_turn")
        self.assertEqual(searched.call_args.args[0].player_potions, ("POTION.FYSH_OIL",))

    def test_rollout_ignores_relic_summoned_player_pets(self) -> None:
        # Pael's Legion and Byrdpip are relic-summoned player pets (not real enemies, no
        # data/enemies_*.json entry) that used to crash rollout_choice's spec lookup for the
        # whole fight whenever the player owned that relic.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.THE_OBSCURA", "hp": 20, "block": 0, "powers": [], "intents": [{"damage": 8, "repeats": 1}], "move": "PIERCING_GAZE_MOVE", "history": [], "slot": "obscura"},
                {"combat_id": 2, "id": "MONSTER.PAELS_LEGION", "hp": 9999, "block": 0, "powers": [], "intents": [], "move": "NOTHING_MOVE", "history": [], "slot": ""},
                {"combat_id": 3, "id": "MONSTER.BYRDPIP", "hp": 9999, "block": 0, "powers": [], "intents": [], "move": "NOTHING_MOVE", "history": [], "slot": ""},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        action = rollout_choice(observation, observation["legal_actions"], data, 200)
        self.assertEqual(action["card_id"], "CARD.STRIKE_IRONCLAD")

    def test_rollout_maps_card_target_after_skipping_leading_pet(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1,
            "turn": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [
                {"combat_id": 99, "id": "MONSTER.PAELS_LEGION", "hp": 9999, "block": 0, "powers": [], "intents": [], "move": "NOTHING_MOVE", "history": [], "slot": ""},
                {"combat_id": 11, "id": "MONSTER.SPECTRAL_KNIGHT", "hp": 30, "block": 0, "powers": [], "intents": [], "move": "HEX", "history": [], "slot": "left"},
                {"combat_id": 12, "id": "MONSTER.MAGI_KNIGHT", "hp": 30, "block": 0, "powers": [], "intents": [], "move": "POWER_SHIELD_MOVE", "history": [], "slot": "right"},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 11},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 12},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.search", return_value=[("Strike@1", 1.0)]):
            action = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual((action["target_id"], action["simulations"], action["search_value"]), (12, 1, 1.0))

    def test_rollout_maps_potion_target_after_skipping_leading_pet(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1,
            "run": {"act": 1, "floor": 2, "room_type": "Monster"},
            "turn": 1,
            "player": {"hp": 20, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "potions": [{"id": POTION_FIRE}],
            "enemies": [
                {"combat_id": 99, "id": "MONSTER.PAELS_LEGION", "hp": 9999, "block": 0, "powers": [], "intents": [], "move": "NOTHING_MOVE", "history": [], "slot": ""},
                {"combat_id": 11, "id": "MONSTER.SPECTRAL_KNIGHT", "hp": 30, "block": 0, "powers": [], "intents": [], "move": "HEX", "history": [], "slot": "left"},
                {"combat_id": 12, "id": "MONSTER.MAGI_KNIGHT", "hp": 10, "block": 0, "powers": [], "intents": [{"damage": 20, "repeats": 1}], "move": "POWER_SHIELD_MOVE", "history": [], "slot": "right"},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 11},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 12},
                {"type": "potion", "potion_id": POTION_FIRE, "target_id": 11},
                {"type": "potion", "potion_id": POTION_FIRE, "target_id": 12},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.search", return_value=[("potion:" + POTION_FIRE + "@1", 2.0)]):
            action = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual((action["target_id"], action["simulations"], action["search_value"]), (12, 1, 2.0))

    def test_rollout_maps_vantom_targetless_aoe_actions(self) -> None:
        with open("data/enemies_overgrowth.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 117,
            "run": {"act": 1, "floor": 16, "room_type": "Boss"},
            "turn": 3,
            "player": {"hp": 78, "max_hp": 85, "block": 0, "energy": 2, "powers": []},
            "hand": [{"index": 0, "id": "CARD.THUNDERCLAP"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "potions": [{"id": POTION_EXPLOSIVE}],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.VANTOM", "hp": 169, "block": 0,
                "powers": [{"id": "POWER.SLIPPERY_POWER", "amount": 4}],
                "intents": [{"damage": 26, "repeats": 1}], "move": "DISMEMBER_MOVE",
                "history": ["INK_BLOT_MOVE", "INKY_LANCE_MOVE"], "slot": "",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.THUNDERCLAP", "hand_index": 0, "target_id": None},
                {"type": "potion", "potion_id": POTION_EXPLOSIVE, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        for best in ("Thunderclap@0", "potion:" + POTION_EXPLOSIVE + "@0"):
            with self.subTest(best=best), patch("official_agent.search", return_value=[(best, 1.0)]):
                action = rollout_choice(observation, observation["legal_actions"], data, 1)
            self.assertIsNone(action["target_id"])

    def test_rollout_marks_minion_enemies_secondary(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "minion"},
                {"combat_id": 2, "id": "MONSTER.DUMMY", "hp": 20, "block": 0, "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss"},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertFalse(captured["combat"].enemies[0].primary)
        self.assertTrue(captured["combat"].enemies[1].primary)

    def test_rollout_preserves_upgrades_in_deck_and_hand(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [],
                "upgraded_cards": ["CARD.TWIN_STRIKE"],
            },
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "upgrade": 1}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["combat"].hand, (Card("Strike", upgraded=True),))
        self.assertEqual(captured["combat"].upgraded_cards, ())

    def test_rollout_keeps_duplicate_card_upgrades_by_hand_index(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [],
                # New card records carry their own upgrade state; this legacy field must not
                # upgrade the unupgraded copies below.
                "upgraded_cards": ["CARD.STRIKE_IRONCLAD"],
            },
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "upgrade": 1},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "upgrade": 0},
            ],
            "draw_pile": [{"id": "CARD.STRIKE_IRONCLAD", "upgrade": 0}],
            "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [("card:1@0", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            action = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(action["hand_index"], 1)
        self.assertEqual(action["target_id"], 1)
        self.assertEqual(captured["combat"].hand, (Card("Strike", upgraded=True), Card("Strike")))
        self.assertEqual(captured["combat"].draw_pile, (Card("Strike"),))
        self.assertEqual(captured["combat"].upgraded_cards, ())

    def test_rollout_decodes_legacy_string_piles_with_upgraded_cards(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {
                "hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [],
                "upgraded_cards": ["CARD.STRIKE_IRONCLAD"],
            },
            "hand": [{"index": 0, "id": "CARD.DEFEND_IRONCLAD", "upgrade": 0}],
            "draw_pile": ["CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD"],
            "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [(END_TURN, 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["combat"].hand, (Card("Defend"),))
        self.assertEqual(captured["combat"].draw_pile, ("Strike", "Defend"))
        self.assertEqual(captured["combat"].upgraded_cards, ("Strike",))

    def test_rollout_preserves_enchantments_in_all_card_piles(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        ember = "ENCHANTMENT.TEZCATARAS_EMBER"
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "upgrade": 0, "enchantment": ember}],
            "draw_pile": [{"id": "CARD.DEFEND_IRONCLAD", "upgrade": 0, "enchantment": ember}],
            "discard_pile": [{"id": "CARD.BASH", "upgrade": 0, "enchantment": ember}],
            "exhaust_pile": [{"id": "CARD.ANGER", "upgrade": 0, "enchantment": None}],
            "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "end_turn"}],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [(END_TURN, 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(captured["combat"].hand, (Card("Strike", enchantment=ember),))
        self.assertEqual(captured["combat"].draw_pile, (Card("Defend", enchantment=ember),))
        self.assertEqual(captured["combat"].discard_pile, (Card("Bash", enchantment=ember),))
        self.assertEqual(captured["combat"].exhaust_pile, (Card("Anger"),))
        self.assertEqual(captured["combat"].upgraded_cards, ())

    def test_rollout_maps_indexed_armaments_to_selected_hand(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "upgrade": 0},
                {"index": 1, "id": "CARD.ARMAMENTS", "upgrade": 0},
                {"index": 2, "id": "CARD.DEFEND_IRONCLAD", "upgrade": 0},
                {"index": 3, "id": "CARD.ARMAMENTS", "upgrade": 0},
            ],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.ARMAMENTS", "hand_index": 1, "target_id": None},
                {"type": "card", "card_id": "CARD.ARMAMENTS", "hand_index": 3, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        with patch("official_agent.search", return_value=[("card:3@0", 0.0)]):
            action = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(action["hand_index"], 3)
        self.assertEqual(action["upgrade_hand_index"], 0)

    def test_rollout_sends_armaments_hand_target(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY", "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 1, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.ARMAMENTS"},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD"},
                {"index": 2, "id": "CARD.DEFEND_IRONCLAD"},
            ],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [{"type": "card", "card_id": "CARD.ARMAMENTS", "hand_index": 0, "target_id": None}, {"type": "end_turn"}],
        }
        with patch("official_agent.search", return_value=[("Armaments@0", 0.0)]):
            action = rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertEqual(action["upgrade_hand_index"], 1)

    def test_rollout_does_not_reuse_lizard_tail_below_half_hp(self) -> None:
        data = {"monsters": [{
            "id": "MONSTER.DUMMY",
            "values": {},
            "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}],
        }]}
        observation = {
            "seq": 1,
            "player": {
                "hp": 30, "max_hp": 80, "block": 0, "energy": 3, "powers": [],
                "relics": ["RELIC.LIZARD_TAIL"],
            },
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.DUMMY", "hp": 20, "block": 0,
                "powers": [], "intents": [], "move": "IDLE_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        captured = {}

        def capture(state, _data, _simulations, _seed):
            captured["combat"] = state
            return [("End turn", 0.0)]

        with patch("official_agent.search", side_effect=capture):
            rollout_choice(observation, observation["legal_actions"], data, 1)
        self.assertTrue(captured["combat"].lizard_tail_used)

    def test_rollout_sanitizes_a_synthetic_bridge_reported_move(self) -> None:
        # IllusionPower.AfterDeath (Parafright) SetMoveImmediate()s a "REVIVE_MOVE" built at
        # runtime that never appears in the exported state machine JSON. If the bridge polls the
        # live observation during that window, blindly trusting observed["move"] used to crash
        # every rollout that reached this enemy's turn (StopIteration from an unresolvable move
        # id) instead of just falling back to its own initial state.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1,
            "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": []},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD"}],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [], "turn": 1,
            "enemies": [
                {"combat_id": 1, "id": "MONSTER.THE_OBSCURA", "hp": 20, "block": 0, "powers": [], "intents": [{"damage": 8, "repeats": 1}], "move": "PIERCING_GAZE_MOVE", "history": [], "slot": "obscura"},
                {"combat_id": 2, "id": "MONSTER.PARAFRIGHT", "hp": 21, "block": 0, "powers": [{"id": "POWER.ILLUSION_POWER", "amount": 1}], "intents": [], "move": "REVIVE_MOVE", "history": [], "slot": "illusion"},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        action = rollout_choice(observation, observation["legal_actions"], data, 200)
        self.assertIn("simulations", action)  # the rollout completed rather than crashing

    def test_rollout_infers_a_bound_card_from_the_legal_actions(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 1, "turn": 1,
            "player": {"hp": 30, "max_hp": 80, "block": 0, "energy": 1, "powers": [
                {"id": "POWER.CHAINS_OF_BINDING_POWER", "amount": 3},
            ]},
            "hand": [
                {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack"},
                {"index": 1, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill"},
            ],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.QUEEN", "hp": 400, "block": 0,
                "powers": [], "intents": [{"damage": 10, "repeats": 1}],
                "move": "PUPPET_STRINGS_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        action = rollout_choice(observation, observation["legal_actions"], data, 20)
        self.assertNotEqual(action.get("hand_index"), 0)

    def test_rollout_excludes_a_snecko_card_that_is_currently_too_expensive(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        observation = {
            "seq": 288, "turn": 8,
            "player": {"hp": 18, "max_hp": 80, "block": 21, "energy": 2, "powers": []},
            "hand": [
                {"index": 0, "id": "CARD.RAGE", "cost": 3, "type": "Skill"},
                {"index": 1, "id": "CARD.ASHEN_STRIKE", "cost": 0, "type": "Attack"},
            ],
            "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{
                "combat_id": 1, "id": "MONSTER.OVICOPTER", "hp": 47, "block": 0,
                "powers": [], "intents": [{"damage": 28, "repeats": 1, "raw_damage": 16}],
                "move": "BIG_ATTACK_MOVE", "history": [], "slot": "boss",
            }],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.ASHEN_STRIKE", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        action = rollout_choice(observation, observation["legal_actions"], data, 20)
        self.assertNotEqual(action.get("hand_index"), 0)

    def test_card_tiers_include_the_required_axes(self) -> None:
        self.assertEqual(CARD_TIERS["CARD.PERFECTED_STRIKE"], "C")
        self.assertEqual(CARD_TIERS["CARD.RUPTURE"], "C")
        self.assertEqual(CARD_TIERS["CARD.TREMBLE"], "S")
        self.assertEqual(CARD_TIERS["CARD.CORRUPTION"], "A")

    def test_modeled_cards_with_no_attack_fallback_are_rewardable(self) -> None:
        for card_id in ("CARD.EQUILIBRIUM", "CARD.ULTIMATE_DEFEND", "CARD.IMPATIENCE"):
            observation = {
                "cards": [{"id": card_id, "type": "Skill", "rarity": "Uncommon", "cost": 1}],
                "legal_actions": [
                    {"type": "card_reward", "card_id": card_id},
                    {"type": "card_reward_alternative", "option_id": "Skip"},
                ],
            }
            self.assertEqual(choose_card_reward(observation)["card_id"], card_id)

    def test_card_tiers_cover_source_unranked_cards(self) -> None:
        known = {"CARD.MIDNIGHT", "CARD.TANK", "CARD.BLAZE", "CARD.DEMONIC_SHIELD", "CARD.OUTRAGE"}
        self.assertTrue(known <= CARD_TIERS.keys())
        self.assertEqual({CARD_TIERS[card] for card in known}, {"D"})


if __name__ == "__main__":
    unittest.main()
