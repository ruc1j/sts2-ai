import json
import unittest
from itertools import pairwise
from pathlib import Path


class OfficialAgentTraceTest(unittest.TestCase):
    def test_external_agent_completed_act_one(self) -> None:
        with open("data/official_agent_trace.jsonl", encoding="utf-8") as file:
            trace = [json.loads(line) for line in file]
        with open("data/map_FV2EVHXLCW_overgrowth.json", encoding="utf-8") as file:
            act_map = json.load(file)
        route = [item for item in trace if item.get("phase") == "map"]
        self.assertEqual((act_map["seed"], act_map["act"], act_map["rows"] - 1, len(act_map["points"])), ("FV2EVHXLCW", "Overgrowth", 17, 65))
        points = {point["id"]: point for point in act_map["points"]}
        for current, following in pairwise(route):
            current_id = f"{current['col']}:{current['row']}"
            following_id = f"{following['col']}:{following['row']}"
            self.assertIn(following_id, points[current_id]["children"])
        self.assertEqual(len(route), 17)
        endings = [item for item in trace if item.get("phase") == "combat_end"]
        self.assertEqual(len(endings), 10)
        self.assertTrue(all(item["won"] for item in endings))
        combat = next(item for item in trace if item.get("phase") == "combat")
        self.assertTrue(combat["card_id"].startswith("CARD."))
        self.assertEqual(combat["simulations"], 1000)
        self.assertIsInstance(combat["search_value"], float)
        self.assertNotIn("decision_source", combat)  # legacy fixture captured before instrumentation
        self.assertEqual(trace[-1]["phase"], "card_reward")

    def test_new_combat_trace_requires_decision_source(self) -> None:
        # This compact fixture is a real combat-trace excerpt captured after the bridge
        # instrumentation landed; the full pre-instrumentation fixture above stays legacy.
        with open("data/decision_source_trace.jsonl", encoding="utf-8") as file:
            trace = [json.loads(line) for line in file]
        combat = [item for item in trace if item.get("phase") == "combat"]
        self.assertTrue(combat)
        for item in combat:
            self.assertIsInstance(item.get("decision_source"), str)
            self.assertTrue(item["decision_source"])
            self.assertIn("decision_reason", item)
        fallback = next(item for item in combat if item["decision_source"] == "heuristic_fallback")
        self.assertEqual(fallback["decision_reason"], "rollout_disabled_no_playable_card")

        bridge = Path("official_mod/CombatBridge.cs").read_text(encoding="utf-8")
        self.assertIn('JsonPropertyName("decision_source")', bridge)
        self.assertIn('JsonPropertyName("decision_reason")', bridge)
        self.assertIn("decision_source = action.DecisionSource", bridge)
        self.assertIn("decision_reason = action.DecisionReason", bridge)

    def test_combat_end_does_not_count_game_over_overlay_as_win(self) -> None:
        bridge = Path("official_mod/CombatBridge.cs").read_text(encoding="utf-8")
        self.assertIn("using MegaCrit.Sts2.Core.Nodes.Screens.GameOverScreen;", bridge)
        self.assertIn("using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;", bridge)
        self.assertIn("bool gameOver = NOverlayStack.Instance?.Peek() is NGameOverScreen;", bridge)
        self.assertIn("won = player.Creature.CurrentHp > 0 && !gameOver", bridge)

    def test_phase_bridges_propagate_decision_source(self) -> None:
        for name in ("MapBridge", "RewardBridge", "RestBridge", "ShopBridge", "EventBridge"):
            source = Path(f"official_mod/{name}.cs").read_text(encoding="utf-8")
            with self.subTest(bridge=name):
                self.assertIn('JsonPropertyName("decision_source")', source)
                self.assertIn('JsonPropertyName("decision_reason")', source)
                self.assertIn("decision_source = action.DecisionSource", source)
                self.assertIn("decision_reason = action.DecisionReason", source)


if __name__ == "__main__":
    unittest.main()
