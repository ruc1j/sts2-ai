import unittest

from official_agent import choose, choose_card_reward, choose_map, choose_rest


class OfficialAgentTest(unittest.TestCase):
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

    def test_map_looks_ahead(self) -> None:
        observation = {
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Boss", "children": []},
                {"col": 1, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

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


if __name__ == "__main__":
    unittest.main()
