import json
import unittest
from itertools import pairwise


class OfficialAgentTraceTest(unittest.TestCase):
    def test_external_agent_completed_act_one(self) -> None:
        with open("data/official_agent_trace.jsonl", encoding="utf-8") as file:
            trace = [json.loads(line) for line in file]
        with open("data/official_act1_map.json", encoding="utf-8") as file:
            act_map = json.load(file)
        route = [item for item in trace if item.get("phase") == "map"]
        self.assertEqual((act_map["act"], act_map["rows"], len(act_map["points"])), ("ACT.OVERGROWTH", 17, 65))
        points = {(point["col"], point["row"]): point for point in act_map["points"]}
        for current, following in pairwise(route):
            self.assertIn({"col": following["col"], "row": following["row"]}, points[current["col"], current["row"]]["children"])
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
