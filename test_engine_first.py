import unittest

from official_agent import choose_card_reward

# Real card_reward record from seed VTW80ZJA2G (seq 79). The deck already has a strength-axis
# card, and the offer contains PRIMAL_FORCE. Before the change the pick was SHRUG_IT_OFF
# (strong-block shortage); with the strength term ahead of core/tier it is PRIMAL_FORCE.
OBSERVATION = {
    "phase": "card_reward",
    "cards": [{"id": "CARD.PRIMAL_FORCE"}],
    "player": {"deck": [{"id": "CARD.INFLAME"}], "hp": 80, "max_hp": 80},
    "legal_actions": [
        {"type": "card_reward", "card_id": "CARD.PRIMAL_FORCE"},
        {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
        {"type": "card_reward_alternative", "option_id": "Skip"},
    ],
    "run": {"act": 1, "floor": 5},
}


class EngineFirstRewardTest(unittest.TestCase):
    def test_strength_term_beats_block_shortage_pick_when_deck_has_an_engine_card(self) -> None:
        self.assertEqual(choose_card_reward(OBSERVATION)["card_id"], "CARD.PRIMAL_FORCE")


if __name__ == "__main__":
    unittest.main()
