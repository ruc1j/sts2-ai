import unittest
from unittest.mock import patch

from data.model_match_audit import recorded_action


class ModelMatchAuditTest(unittest.TestCase):
    def test_targeted_potion_keeps_recorded_target_after_skipping_pet(self) -> None:
        record = {
            "potion_id": "POTION.FIRE_POTION",
            "target_id": 3,
            "enemies": [
                {"id": "MONSTER.BYRDPIP", "combat_id": 1},
                {"id": "MONSTER.TORCH_HEAD_AMALGAM", "combat_id": 2},
                {"id": "MONSTER.QUEEN", "combat_id": 3},
            ],
        }
        with patch("data.model_match_audit.combat.legal_actions", return_value=[
            "potion:POTION.FIRE_POTION@0", "potion:POTION.FIRE_POTION@1",
        ]):
            self.assertEqual(recorded_action(record, None, {}), "potion:POTION.FIRE_POTION@1")
            record["target_id"] = 99
            self.assertIsNone(recorded_action(record, None, {}))


if __name__ == "__main__":
    unittest.main()
