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

    def test_reward_takes_unknown_attack(self) -> None:
        observation = {
            "cards": [{"id": "CARD.CINDER", "type": "Attack", "rarity": "Common", "cost": 2}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.CINDER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.CINDER")

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

    def test_targets_crab_to_face_the_larger_attack(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [{"index": 0, "type": "Attack"}],
            "enemies": [{"combat_id": 7, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 12, "repeats": 1}]}],
            "legal_actions": [{"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7}],
        }
        self.assertEqual(choose(observation)["target_id"], 7)


if __name__ == "__main__":
    unittest.main()
