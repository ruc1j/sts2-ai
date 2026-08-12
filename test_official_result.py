import json
import unittest


class OfficialActOneResultTest(unittest.TestCase):
    def test_ironclad_completed_act_one(self) -> None:
        with open("data/official_act1_result.json", encoding="utf-8") as file:
            result = json.load(file)
        self.assertEqual(result["game_version"], "v0.107.1")
        self.assertEqual(result["character"], "CHARACTER.IRONCLAD")
        self.assertEqual(result["seed"], "FV2EVHXLCW")
        self.assertEqual(result["requested_seed"], result["seed"])
        self.assertTrue(result["act_1_complete"])
        self.assertEqual(len(result["route"]), 17)
        self.assertEqual(result["route"][-1], "Boss")


if __name__ == "__main__":
    unittest.main()
