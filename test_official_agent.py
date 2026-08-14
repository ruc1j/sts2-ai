import json
import os
import tempfile
import unittest
from unittest.mock import patch

from official_agent import CARD_NAMES, CARD_TIERS, POWER_NAMES, RELIC_SCORES, choose, choose_card_reward, choose_event, choose_map, choose_rest, choose_shop, rollout_choice
from combat import BURN, DAZED, INFECTION, TOXIC


class OfficialAgentTest(unittest.TestCase):
    def test_maps_ceremonial_beast_plow_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.PLOW_POWER"], "PlowPower")

    def test_maps_ceremonial_beast_ringing_power_for_rollouts(self) -> None:
        self.assertEqual(POWER_NAMES["POWER.RINGING_POWER"], "RingingPower")

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
        self.assertEqual(captured["combat"].hand, (TOXIC,))

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
        self.assertEqual(candidates[(0, "Monster")], [1, 1, 0])
        self.assertEqual(candidates[(1, "Unknown")], [0, 1, 0])

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

    def test_reward_skips_unsupported_cards(self) -> None:
        observation = {
            "cards": [{"id": "CARD.UNKNOWN", "rarity": "Uncommon"}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_takes_anger_for_the_normal_fights(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

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

    def test_shaped_rock_targets_the_highest_hp_enemy(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.POTION_SHAPED_ROCK", "target_id": 1},
                {"type": "potion", "potion_id": "POTION.POTION_SHAPED_ROCK", "target_id": 2},
                {"type": "end_turn"},
            ],
            "player": {"hp": 30, "max_hp": 80},
            "hand": [],
            "enemies": [
                {"combat_id": 1, "hp": 44, "intents": [{"damage": 7, "repeats": 1}]},
                {"combat_id": 2, "hp": 168, "intents": [{"damage": 8, "repeats": 1}]},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

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
        self.assertEqual(choose(observation)["potion_id"], "POTION.POTION_SHAPED_ROCK")

    def test_uses_colorless_potion_proactively_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.COLORLESS_POTION")

    def test_uses_weak_potion_against_lethal_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.WEAK_POTION", "target_id": 7}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 40, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.WEAK_POTION")

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

    def test_uses_entropic_brew_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.ENTROPIC_BREW", "target_id": None}],
            "player": {"hp": 30, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.ENTROPIC_BREW")

    def test_does_not_manually_use_fairy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.FAIRY_IN_A_BOTTLE", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [],
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
        self.assertEqual(choose(observation)["card_id"], "CARD.PERFECTED_STRIKE")

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

    def test_card_tiers_include_the_required_axes(self) -> None:
        self.assertEqual(CARD_TIERS["CARD.PERFECTED_STRIKE"], "C")
        self.assertEqual(CARD_TIERS["CARD.RUPTURE"], "C")
        self.assertEqual(CARD_TIERS["CARD.TREMBLE"], "S")
        self.assertEqual(CARD_TIERS["CARD.CORRUPTION"], "A")

    def test_card_tiers_cover_source_unranked_cards(self) -> None:
        known = {"CARD.MIDNIGHT", "CARD.TANK", "CARD.BLAZE", "CARD.DEMONIC_SHIELD", "CARD.OUTRAGE"}
        self.assertTrue(known <= CARD_TIERS.keys())
        self.assertEqual({CARD_TIERS[card] for card in known}, {"D"})


if __name__ == "__main__":
    unittest.main()
