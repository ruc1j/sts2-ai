import json
import unittest
from itertools import pairwise


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
        self.assertEqual(trace[-1]["phase"], "card_reward")


if __name__ == "__main__":
    unittest.main()
