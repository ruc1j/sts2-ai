import json
import unittest


class OfficialAgentTraceTest(unittest.TestCase):
    def test_external_agent_completed_combat(self) -> None:
        with open("data/official_agent_trace.jsonl", encoding="utf-8") as file:
            trace = [json.loads(line) for line in file]
        self.assertEqual(trace[0]["seq"], 0)
        self.assertEqual(trace[0]["type"], "card")
        self.assertTrue(trace[0]["card_id"].startswith("CARD."))
        self.assertEqual(trace[0]["simulations"], 1000)
        self.assertIsInstance(trace[0]["search_value"], float)
        self.assertTrue(trace[-1]["terminal"])


if __name__ == "__main__":
    unittest.main()
