"""Tests for bosslab/agents/official_agent_queenfirst.py (the Act 3 target-choice candidate).

The candidate is a copy of official_agent.py with exactly two policy changes, both inside the
`queen_present`-guarded rules: attacks in a Queen fight aim at the Queen instead of the Torch Head
Amalgam, and the Amalgam is dropped from the forced-kill `focused_minions` set. These tests pin the
behavior the panel measures, and pin that nothing else moved: the same module run on a fight without
the Queen has to return the base policy's action.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import official_agent

REPO = Path(__file__).resolve().parent
CANDIDATE = REPO / "bosslab" / "agents" / "official_agent_queenfirst.py"


def load_candidate():
    module_spec = importlib.util.spec_from_file_location("official_agent_queenfirst", CANDIDATE)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def decision(action: dict | None) -> dict:
    """The part of an action a run compares: what was played, where, and under which rule."""
    if action is None:
        return {}
    return {key: action.get(key) for key in ("type", "card_id", "hand_index", "target_id",
                                             "potion_id", "relic_id", "decision_source")}


def queen_fight(*, queen_hp: int = 400, amalgam_hp: int = 199, hp: int = 80, block: int = 0,
                incoming: int = 18, cards: list[dict] | None = None,
                legal: list[dict] | None = None) -> dict:
    cards = cards if cards is not None else [
        {"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
         "vars": [{"id": "Damage", "value": 6}]},
    ]
    legal = legal if legal is not None else (
        [{"type": "card", "card_id": card["id"], "hand_index": index, "target_id": target}
         for index, card in enumerate(cards) if card["type"] == "Attack"
         for target in (1, 2)]
        + [{"type": "card", "card_id": card["id"], "hand_index": index}
           for index, card in enumerate(cards) if card["type"] != "Attack"]
        + [{"type": "end_turn"}])
    return {
        "player": {"hp": hp, "max_hp": max(hp, 80), "block": block, "energy": 3, "powers": [],
                   "relics": []},
        "hand": cards,
        "enemies": [
            {"combat_id": 1, "id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": amalgam_hp, "block": 0,
             "powers": [{"id": "POWER.MINION_POWER", "amount": 1}],
             "intents": [{"type": "SingleAttackIntent", "damage": incoming, "repeats": 1}]},
            {"combat_id": 2, "id": "MONSTER.QUEEN", "hp": queen_hp, "block": 0, "powers": [],
             "intents": []},
        ],
        "legal_actions": legal,
    }


class QueenFirstCandidateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CANDIDATE.is_file():
            raise cls.skipTest(f"{CANDIDATE} is missing")
        cls.candidate = load_candidate()

    def test_queen_fight_aims_at_the_queen_while_base_aims_at_the_amalgam(self) -> None:
        observation = queen_fight()
        self.assertEqual(1, official_agent.choose(dict(observation))["target_id"])
        action = self.candidate.choose(dict(observation))
        self.assertEqual(2, action["target_id"])
        self.assertEqual("queen_direct", action["decision_source"])

    def test_queen_setup_cards_are_played_before_attacking_she_does(self) -> None:
        # The base plays Inflame before the Amalgam-focused attack; the candidate keeps the same
        # ordering, only re-aiming the attacks that come after it.
        cards = [
            {"index": 0, "id": "CARD.INFLAME", "cost": 1, "type": "Skill", "vars": []},
            {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
             "vars": [{"id": "Damage", "value": 6}]},
        ]
        observation = queen_fight(cards=cards)
        base = official_agent.choose(dict(observation))
        candidate = self.candidate.choose(dict(observation))
        self.assertEqual(("CARD.INFLAME", base["card_id"]), ("CARD.INFLAME", candidate["card_id"]))
        self.assertTrue(base["card_id"] == "CARD.INFLAME" and candidate["card_id"] == "CARD.INFLAME")

    def test_defense_gates_are_shared_when_the_hit_would_kill(self) -> None:
        # hp 40, a 45 damage hit and a 45 block card: the shortcut's block gate holds in both
        # policies (urgent, block covers the incoming, and blocking survives), so the same defense
        # is played and the target change never reaches this turn.
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

    def test_lethal_on_the_queen_is_taken_by_both_policies(self) -> None:
        observation = queen_fight(queen_hp=4, incoming=10)
        base = official_agent.choose(dict(observation))
        candidate = self.candidate.choose(dict(observation))
        self.assertEqual(2, base["target_id"])
        self.assertEqual(2, candidate["target_id"])

    def test_fights_without_the_queen_are_unchanged(self) -> None:
        fixtures = [
            {
                "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [],
                           "relics": []},
                "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
                          "vars": [{"id": "Damage", "value": 6}]}],
                "enemies": [
                    {"combat_id": 1, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", "hp": 40,
                     "block": 0, "powers": [], "intents": [{"damage": 20, "repeats": 1}]},
                    {"combat_id": 2, "id": "MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", "hp": 10,
                     "block": 0, "powers": [], "intents": [{"damage": 1, "repeats": 1}]},
                ],
                "legal_actions": [
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0,
                     "target_id": 1},
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0,
                     "target_id": 2},
                    {"type": "end_turn"},
                ],
            },
            {
                "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "powers": [],
                           "relics": []},
                "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "cost": 1, "type": "Attack",
                          "vars": [{"id": "Damage", "value": 6}]}],
                "enemies": [
                    {"combat_id": 1, "id": "MONSTER.KIN_FOLLOWER", "hp": 58, "block": 0,
                     "powers": [{"id": "POWER.MINION_POWER", "amount": 1}],
                     "intents": [{"damage": 6, "repeats": 1}]},
                    {"combat_id": 2, "id": "MONSTER.KIN_PRIEST", "hp": 190, "block": 0,
                     "powers": [], "intents": [{"damage": 10, "repeats": 1}]},
                ],
                "legal_actions": [
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0,
                     "target_id": 1},
                    {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0,
                     "target_id": 2},
                    {"type": "end_turn"},
                ],
            },
        ]
        for index, observation in enumerate(fixtures):
            with self.subTest(fixture=index):
                self.assertEqual(decision(official_agent.choose(dict(observation))),
                                 decision(self.candidate.choose(dict(observation))))

    def test_queen_fight_with_no_playable_attack_is_unchanged(self) -> None:
        cards = [{"index": 0, "id": "CARD.DEFEND_IRONCLAD", "cost": 1, "type": "Skill",
                  "vars": [{"id": "Block", "value": 5}]}]
        observation = queen_fight(cards=cards, legal=[
            {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 0},
            {"type": "end_turn"},
        ])
        self.assertEqual(decision(official_agent.choose(dict(observation))),
                         decision(self.candidate.choose(dict(observation))))

    def test_candidate_and_base_differ_only_in_the_queen_targeting_rules(self) -> None:
        """A guard against future drift: the copy must stay a two-rule change of official_agent.py."""
        base_lines = Path("official_agent.py").read_text(encoding="utf-8-sig").splitlines()
        candidate_lines = CANDIDATE.read_text(encoding="utf-8").splitlines()
        marker = "# [candidate: queen-first]"
        added = [line for line in candidate_lines if line.startswith("    # ")
                 and line not in base_lines]
        changed_targets = [line for line in candidate_lines
                           if "queen_focus_ids" in line or "queen_direct" in line
                           or "queen_hp =" in line]
        self.assertIn(marker, CANDIDATE.read_text(encoding="utf-8"))
        self.assertTrue(any("focused_minions" in line for line in candidate_lines
                            if 'focused_minions = {"MONSTER.KIN_FOLLOWER"}' in line))
        self.assertNotIn('focused_minions = {"MONSTER.TORCH_HEAD_AMALGAM"',
                         CANDIDATE.read_text(encoding="utf-8"))
        self.assertTrue(changed_targets)
        self.assertTrue(added)
        # No other module-level constant or table was touched.
        for name in ("STRONG_BLOCK_CARDS", "SHOP_POTION_SCORES", "RELIC_SCORES"):
            self.assertEqual(getattr(official_agent, name), getattr(self.candidate, name))


if __name__ == "__main__":
    unittest.main()
