"""Tests for bosslab/agents/official_agent_H1.py (T17 candidate: chipped-first target choice).

H1 is a copy of official_agent.py whose only policy change is which enemy the Queen-fight single-target
attacks aim at: the Amalgam while its effective HP is at or below QUEENFIRST_H1_AMALGAM_HP (50), and the
Queen otherwise. Everything else (Rupture/Hellraiser/Inflame/Bloodletting setup, the block gate, lethal
ordering, and the whole map/reward/shop/rest/rest of combat) stays identical to the base. These tests pin
the target switch, pin that block / potion / end_turn / hand usage are unchanged, and guard the copy
against drift. The candidate short-circuits the Queen fight in the heuristic tail, so choose() needs no
enemy_data here and every decision is reproducible.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import official_agent

REPO = Path(__file__).resolve().parent
CANDIDATE = REPO / "bosslab" / "agents" / "official_agent_H1.py"
THRESHOLD = 50


def load_candidate():
    spec = importlib.util.spec_from_file_location("official_agent_H1", CANDIDATE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def decision(action: dict | None) -> dict:
    if action is None:
        return {}
    return {key: action.get(key) for key in ("type", "card_id", "hand_index", "target_id",
                                             "potion_id", "relic_id", "decision_source")}


def queen_fight(*, queen_hp: int = 400, amalgam_hp: int = 199, amalgam_block: int = 0, hp: int = 80,
                block: int = 0, incoming: int = 18, cards: list[dict] | None = None,
                legal: list[dict] | None = None) -> dict:
    cards = cards if cards is not None else [
        {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
         "vars": [{"id": "Damage", "value": 6}]},
    ]
    legal = legal if legal is not None else (
        [{"type": "card", "card_id": card["id"], "hand_index": index, "target_id": target}
         for index, card in enumerate(cards) if card["type"] == "Attack" for target in (1, 2)]
        + [{"type": "card", "card_id": card["id"], "hand_index": index}
           for index, card in enumerate(cards) if card["type"] != "Attack"]
        + [{"type": "end_turn"}])
    return {
        "player": {"hp": hp, "max_hp": max(hp, 80), "block": block, "energy": 3, "powers": [],
                   "relics": []},
        "hand": cards,
        "enemies": [
            {"combat_id": 1, "id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": amalgam_hp,
             "block": amalgam_block, "powers": [{"id": "POWER.MINION_POWER", "amount": 1}],
             "intents": [{"type": "SingleAttackIntent", "damage": incoming, "repeats": 1}]},
            {"combat_id": 2, "id": "MONSTER.QUEEN", "hp": queen_hp, "block": 0, "powers": [],
             "intents": []},
        ],
        "legal_actions": legal,
    }


class H1ChippedFirstTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CANDIDATE.is_file():
            raise cls.skipTest(f"{CANDIDATE} is missing")
        cls.candidate = load_candidate()

    def test_fresh_fight_aims_at_queen_while_base_aims_at_amalgam(self) -> None:
        # Amalgam at 199 effHP is above the threshold, so H1 chips the Queen where the base grinds.
        observation = queen_fight()
        self.assertEqual(1, official_agent.choose(dict(observation))["target_id"])
        action = self.candidate.choose(dict(observation))
        self.assertEqual(2, action["target_id"])
        self.assertEqual("queen_minion_h1", action["decision_source"])

    def test_chipped_amalgam_is_attacked_once_effective_hp_hits_the_threshold(self) -> None:
        # Not-yet-lethal Amalgam at or below the threshold (block counts toward effective HP).
        for hp, block in ((THRESHOLD, 0), (40, 10), (20, 25)):
            observation = queen_fight(amalgam_hp=hp, amalgam_block=block)
            action = self.candidate.choose(dict(observation))
            with self.subTest(hp=hp, block=block):
                self.assertEqual(1, action["target_id"])
                self.assertEqual("queen_minion_h1", action["decision_source"])
        # 40 hp + 15 block = 55 effective HP is above 50, so it stays on the Queen.
        action = self.candidate.choose(dict(queen_fight(amalgam_hp=40, amalgam_block=15)))
        self.assertEqual(2, action["target_id"])

    def test_setup_cards_are_played_before_attacking_she_does(self) -> None:
        # Base plays Inflame before the Amalgam attack; H1 (here aiming at the Queen) keeps the same
        # setup-first ordering and only re-aims the attack that follows.
        cards = [
            {"index": 0, "id": "CARD.INFLAME", "cost": 1, "type": "Skill", "vars": []},
            {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
             "vars": [{"id": "Damage", "value": 6}]},
        ]
        observation = queen_fight(cards=cards)
        base = official_agent.choose(dict(observation))
        candidate = self.candidate.choose(dict(observation))
        self.assertEqual("CARD.INFLAME", base["card_id"])
        self.assertEqual("CARD.INFLAME", candidate["card_id"])

    def test_defense_gates_are_shared_when_the_hit_would_kill(self) -> None:
        cards = [
            {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
             "vars": [{"id": "Damage", "value": 6}]},
            {"index": 1, "id": "CARD.EVIL_EYE", "cost": 1, "type": "Skill",
             "vars": [{"id": "Block", "value": 45}]},
        ]
        legal = [
            {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
            {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
            {"type": "card", "card_id": "CARD.EVIL_EYE", "hand_index": 1},
            {"type": "end_turn"},
        ]
        observation = queen_fight(hp=40, incoming=45, cards=cards, legal=legal)
        base = decision(official_agent.choose(dict(observation)))
        candidate = decision(self.candidate.choose(dict(observation)))
        self.assertEqual(base, candidate)
        self.assertEqual("CARD.EVIL_EYE", candidate["card_id"])
        self.assertIsNone(candidate["target_id"])

    def test_lethal_is_taken_by_both_and_a_chipped_amalgam_is_a_forced_kill(self) -> None:
        # Lethal on the Queen: both take it (lethal short-circuits before the target choice).
        observation = queen_fight(queen_hp=4, incoming=10)
        self.assertEqual(2, official_agent.choose(dict(observation))["target_id"])
        self.assertEqual(2, self.candidate.choose(dict(observation))["target_id"])
        # A chipped Amalgam killed outright: H1 keeps it in the forced-kill focus set, so the guaranteed
        # kill outranks Queen damage (40 damage kills the 30 HP Amalgam; the Queen at 400 is untouched).
        observation = queen_fight(
            amalgam_hp=30,
            cards=[{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
                    "vars": [{"id": "Damage", "value": 40}]}],
        )
        self.assertEqual(1, self.candidate.choose(dict(observation))["target_id"])

    def test_fights_without_the_queen_are_unchanged(self) -> None:
        fixtures = [
            {
                "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [], "relics": []},
                "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
                          "vars": [{"id": "Damage", "value": 6}]}],
                "enemies": [
                    {"combat_id": 1, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", "hp": 40, "block": 0,
                     "powers": [], "intents": [{"damage": 20, "repeats": 1}]},
                    {"combat_id": 2, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", "hp": 10, "block": 0,
                     "powers": [], "intents": [{"damage": 1, "repeats": 1}]},
                ],
                "legal_actions": [
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                    {"type": "end_turn"},
                ],
            },
            {
                "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [], "relics": []},
                "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
                          "vars": [{"id": "Damage", "value": 6}]}],
                "enemies": [
                    {"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 58, "block": 0,
                     "powers": [{"id": "POWER.MINION_POWER", "amount": 1}], "intents": [{"damage": 6, "repeats": 1}]},
                    {"combat_id": 2, "id": "MONSTER.KIN_PRIEST", "hp": 190, "block": 0, "powers": [],
                     "intents": [{"damage": 10, "repeats": 1}]},
                ],
                "legal_actions": [
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                    {"type": "end_turn"},
                ],
            },
        ]
        for index, observation in enumerate(fixtures):
            with self.subTest(fixture=index):
                self.assertEqual(decision(official_agent.choose(dict(observation))),
                                 decision(self.candidate.choose(dict(observation))))

    def test_candidate_and_base_differ_only_in_the_queen_target_choice(self) -> None:
        """A guard against drift: H1 stays a target-choice-only copy of official_agent.py."""
        if not CANDIDATE.is_file():
            self.skipTest(f"{CANDIDATE} is missing")
        text = CANDIDATE.read_text(encoding="utf-8")
        # The candidate marker and the renamed decision tags must be present, and the base tags gone.
        self.assertIn("# [H1 candidate]", text)
        for token in ('"queen_minion_h1"', '"rupture_before_h1"', '"queen_h1_energy"'):
            self.assertIn(token, text)
        for token in ('"queen_minion_direct"', '"rupture_before_queen_focus"', '"queen_focus_energy"'):
            self.assertNotIn(token, text)
        # The forced-kill set is now conditional on the same focus decision.
        self.assertIn('if focus_to_amalgam', text)
        # The threshold constant exists on the candidate only and is the documented value.
        self.assertEqual(THRESHOLD, getattr(self.candidate, "QUEENFIRST_H1_AMALGAM_HP"))
        self.assertFalse(hasattr(official_agent, "QUEENFIRST_H1_AMALGAM_HP"))
        # No shared table or scoring constant was touched.
        for name in ("STRONG_BLOCK_CARDS", "SHOP_POTION_SCORES", "RELIC_SCORES"):
            self.assertEqual(getattr(official_agent, name), getattr(self.candidate, name))


if __name__ == "__main__":
    unittest.main()
