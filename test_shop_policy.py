import unittest

from official_agent import choose_shop


def shop_observation(*, deck, cards, legal_actions, gold=200, relics=None, potions=None, removal=None):
    return {
        "phase": "shop",
        "gold": gold,
        "player": {"gold": gold, "deck": deck, "hp": 70, "max_hp": 80},
        "cards": cards,
        "relics": relics or [],
        "potions": potions or [],
        "removal": removal,
        "legal_actions": legal_actions,
    }


class ShopPolicyTest(unittest.TestCase):
    def test_buys_perfected_strike_when_strike_core_is_present(self):
        perfected = {
            "type": "buy_card",
            "card_index": 0,
            "slot_index": 1,
            "card_id": "CARD.PERFECTED_STRIKE",
        }
        observation = shop_observation(
            deck=["CARD.STRIKE_IRONCLAD"] * 5,
            cards=[
                {"index": 0, "slot_index": 1, "id": "CARD.PERFECTED_STRIKE", "type": "Attack", "rarity": "Common", "cost": 75, "affordable": True},
                {"index": 1, "slot_index": 2, "id": "CARD.RANDOM_ATTACK", "type": "Attack", "rarity": "Common", "cost": 50, "affordable": True},
            ],
            legal_actions=[perfected, {"type": "buy_card", "card_index": 1, "slot_index": 2, "card_id": "CARD.RANDOM_ATTACK"}, {"type": "skip"}],
        )
        self.assertEqual(choose_shop(observation), perfected)

    def test_skips_mediocre_cards(self):
        observation = shop_observation(
            deck=["CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD"],
            cards=[{"index": 0, "slot_index": 1, "id": "CARD.RANDOM_ATTACK", "type": "Attack", "rarity": "Common", "cost": 50, "affordable": True}],
            legal_actions=[{"type": "buy_card", "card_index": 0, "slot_index": 1, "card_id": "CARD.RANDOM_ATTACK"}, {"type": "skip"}],
        )
        self.assertEqual(choose_shop(observation)["type"], "skip")

    def test_buys_known_relic_over_non_core_card(self):
        relic = {"type": "buy_relic", "relic_index": 0, "slot_index": 3, "relic_id": "RELIC.KUNAI"}
        observation = shop_observation(
            deck=["CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD"],
            cards=[{"index": 0, "slot_index": 1, "id": "CARD.BATTLE_TRANCE", "type": "Skill", "rarity": "Uncommon", "cost": 75, "affordable": True}],
            relics=[{"index": 0, "slot_index": 3, "id": "RELIC.KUNAI", "cost": 150, "affordable": True}],
            legal_actions=[{"type": "buy_card", "card_index": 0, "slot_index": 1, "card_id": "CARD.BATTLE_TRANCE"}, relic, {"type": "skip"}],
        )
        self.assertEqual(choose_shop(observation), relic)

    def test_axis_tier_prefers_self_damage_relic(self):
        relic = {"type": "buy_relic", "relic_index": 0, "slot_index": 3, "relic_id": "RELIC.RED_SKULL"}
        observation = shop_observation(
            deck=["CARD.RUPTURE", "CARD.HEMOKINESIS"],
            cards=[{"index": 0, "slot_index": 1, "id": "CARD.BATTLE_TRANCE", "type": "Skill", "rarity": "Uncommon", "cost": 75, "affordable": True}],
            relics=[{"index": 0, "slot_index": 3, "id": "RELIC.RED_SKULL", "cost": 150, "affordable": True}],
            legal_actions=[{"type": "buy_card", "card_index": 0, "slot_index": 1, "card_id": "CARD.BATTLE_TRANCE"}, relic, {"type": "skip"}],
        )
        self.assertEqual(choose_shop(observation), relic)

    def test_strength_axis_can_buy_brimstone(self):
        relic = {"type": "buy_relic", "relic_index": 0, "slot_index": 3, "relic_id": "RELIC.BRIMSTONE"}
        observation = shop_observation(
            deck=["CARD.INFLAME"],
            cards=[{"index": 0, "slot_index": 1, "id": "CARD.BATTLE_TRANCE", "type": "Skill", "rarity": "Uncommon", "cost": 75, "affordable": True}],
            relics=[{"index": 0, "slot_index": 3, "id": "RELIC.BRIMSTONE", "cost": 150, "affordable": True}],
            legal_actions=[{"type": "buy_card", "card_index": 0, "slot_index": 1, "card_id": "CARD.BATTLE_TRANCE"}, relic, {"type": "skip"}],
        )
        self.assertEqual(choose_shop(observation), relic)

    def test_buys_premium_card_when_no_known_relic(self):
        card = {"type": "buy_card", "card_index": 0, "slot_index": 1, "card_id": "CARD.BATTLE_TRANCE"}
        observation = shop_observation(
            deck=["CARD.STRIKE_IRONCLAD", "CARD.DEFEND_IRONCLAD"],
            cards=[{"index": 0, "slot_index": 1, "id": "CARD.BATTLE_TRANCE", "type": "Skill", "rarity": "Uncommon", "cost": 75, "affordable": True}],
            relics=[{"index": 0, "slot_index": 3, "id": "RELIC.UNKNOWN", "cost": 100, "affordable": True}],
            legal_actions=[card, {"type": "buy_relic", "relic_index": 0, "slot_index": 3, "relic_id": "RELIC.UNKNOWN"}, {"type": "skip"}],
        )
        self.assertEqual(choose_shop(observation), card)

    def test_removal_does_not_delete_strikes_in_strike_axis(self):
        remove_defend = {"type": "remove", "slot_index": 7, "card_index": 2, "card_id": "CARD.DEFEND_IRONCLAD"}
        observation = shop_observation(
            deck=["CARD.STRIKE_IRONCLAD", "CARD.PERFECTED_STRIKE", "CARD.DEFEND_IRONCLAD"],
            cards=[],
            removal={"slot_index": 7, "id": "remove", "cost": 100, "affordable": True},
            legal_actions=[
                {"type": "remove", "slot_index": 7, "card_index": 0, "card_id": "CARD.STRIKE_IRONCLAD"},
                {"type": "remove", "slot_index": 7, "card_index": 2, "card_id": "CARD.DEFEND_IRONCLAD"},
                {"type": "skip"},
            ],
        )
        self.assertEqual(choose_shop(observation), remove_defend)

    def test_shop_action_is_one_object_and_can_skip(self):
        observation = shop_observation(
            deck=["CARD.STRIKE_IRONCLAD"],
            cards=[],
            legal_actions=[{"type": "skip"}],
        )
        action = choose_shop(observation)
        self.assertIsInstance(action, dict)
        self.assertEqual(action["type"], "skip")


if __name__ == "__main__":
    unittest.main()
