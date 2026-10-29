import importlib.util
import unittest
from pathlib import Path
from collections import Counter

# T38: the per-turn trace diff must locate diverging attack turns, read the leftover-minion signal, and
# flag a candidate that shaved the Amalgam but never finished it (dead enemies vanish from snapshots, so
# kill detection is "present early, absent from the last row", not hp==0).
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("trace_turn_diff", _TOOLS / "trace_turn_diff.py")
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)

AMID, QID = "MONSTER.TORCH_HEAD_AMALGAM", "MONSTER.QUEEN"  # ends with the module's suffixes


def _enemies(ahp, qhp, qint=0, aint=0):
    return [
        {"combat_id": 1, "id": AMID, "slot": "amalgam", "hp": ahp, "max_hp": 199,
         "intents": [{"type": "Attack", "damage": aint, "repeats": 1}]},
        {"combat_id": 2, "id": QID, "slot": "queen", "hp": qhp, "max_hp": 400,
         "intents": [{"type": "Attack", "damage": qint, "repeats": 1}]},
    ]


def _row(turn, hi, card, tid, ahp, qhp, qint=0, aint=0, dmg=8, ph=100):
    return {"turn": turn, "phase": "combat", "type": "card", "hand_index": hi, "target_id": tid,
            "player_hp": ph, "enemies": _enemies(ahp, qhp, qint, aint),
            "hand": [{"index": 0, "id": "CARD.A", "type": "Attack", "vars": [{"id": "Damage", "value": dmg}]},
                     {"index": 1, "id": card, "type": "Attack", "vars": [{"id": "Damage", "value": dmg}]}]}


class DiffTurnsTest(unittest.TestCase):
    def test_locates_diverging_turns(self):
        # base shoots the Amalgam every turn; the candidate diverges to Queen on turn 2 only.
        base = [_row(1, 1, "CARD.A", 1, 199, 400), _row(2, 1, "CARD.B", 1, 150, 400)]
        cand = [_row(1, 1, "CARD.A", 1, 199, 400), _row(2, 1, "CARD.B", 2, 150, 400)]
        self.assertEqual(T.diff_turns(base, cand), [2])

    def test_no_divergence_when_same_targets(self):
        base = [_row(1, 1, "CARD.A", 1, 199, 400)]
        cand = [_row(1, 1, "CARD.B", 1, 190, 400)]
        self.assertEqual(T.diff_turns(base, cand), [])


class AmalgamRollupTest(unittest.TestCase):
    def test_survived_with_damage_when_minion_left_alive(self):
        # candidate deals damage across turns but the Amalgam (hp 90) is still on the final board.
        cand = [_row(1, 1, "CARD.A", 1, 199, 400, dmg=60), _row(2, 1, "CARD.B", 2, 90, 340, dmg=60)]
        ru = T.pair_amalgam_rollup(cand, cand)
        self.assertTrue(ru["cand_saw"])
        self.assertFalse(ru["cand_killed"])
        self.assertEqual(ru["cand_final_hp"], 90)
        self.assertTrue(ru["cand_survived_with_damage"])

    def test_killed_when_minion_gone_from_final_row(self):
        # Amalgam present early, absent from the last row -> counted as killed (hp 0), never via min==0.
        alive = _row(1, 1, "CARD.A", 1, 199, 400)
        gone = {"turn": 2, "phase": "combat", "type": "card", "hand_index": 1, "target_id": 2,
                "player_hp": 80, "enemies": [{"combat_id": 2, "id": QID, "slot": "queen", "hp": 300,
                "max_hp": 400, "intents": []}],
                "hand": [{"index": 0, "id": "CARD.A", "type": "Attack", "vars": []},
                         {"index": 1, "id": "CARD.B", "type": "Attack", "vars": []}]}
        ru = T.pair_amalgam_rollup([alive, gone], [alive, gone])
        self.assertTrue(ru["cand_killed"])
        self.assertEqual(ru["cand_final_hp"], 0)
        self.assertFalse(ru["cand_survived_with_damage"])

    def test_no_amalgam_is_neither(self):
        rows = [{"turn": 1, "phase": "combat", "type": "card", "hand_index": 1, "target_id": 2,
                 "player_hp": 80, "enemies": [{"combat_id": 2, "id": QID, "slot": "queen", "hp": 300,
                 "max_hp": 400, "intents": []}],
                 "hand": [{"index": 0, "id": "CARD.A", "type": "Attack", "vars": []},
                          {"index": 1, "id": "CARD.B", "type": "Attack", "vars": []}]}]
        ru = T.pair_amalgam_rollup(rows, rows)
        self.assertFalse(ru["cand_saw"])
        self.assertIsNone(ru["cand_final_hp"])


class AttackChoicesTest(unittest.TestCase):
    def test_only_single_target_attacks_count(self):
        rows = [_row(1, 1, "CARD.ATT", 1, 199, 400),
                {"turn": 1, "phase": "combat", "type": "card", "hand_index": 0, "target_id": None,
                 "player_hp": 100, "enemies": _enemies(199, 400),  # AoE attack, target_id None -> skipped
                 "hand": [{"index": 0, "id": "CARD.AOE", "type": "Attack", "vars": []},
                          {"index": 1, "id": "CARD.A", "type": "Skill", "vars": []}]}]
        ch = T.attack_choices(rows)
        self.assertEqual(len(ch[1]), 1)  # only the single-target Attack is recorded
        self.assertEqual(ch[1][0][1], "amalgam")


if __name__ == "__main__":
    unittest.main()
