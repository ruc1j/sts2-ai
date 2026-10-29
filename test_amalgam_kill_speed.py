import importlib.util
import sys
import unittest
from pathlib import Path

# T40: the Amalgam kill-speed survey must detect a kill as "present on a turn, then gone from the next
# turn" (dead enemies vanish from snapshots, so hp==0 is never observed), classify the start deck via the
# global card map, and only report a wasted lethal turn when hand damage actually covered the remaining HP.
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("amalgam_kill_speed", _TOOLS / "amalgam_kill_speed.py")
T = importlib.util.module_from_spec(_spec)
sys.modules["amalgam_kill_speed"] = T
_spec.loader.exec_module(T)

AMID, QID = "MONSTER.TORCH_HEAD_AMALGAM", "MONSTER.QUEEN"


def _row(turn, ahp=None, qhp=400, ph=100, energy=3, hand=None):
    enemies = [{"combat_id": 2, "id": QID, "slot": "queen", "hp": qhp, "max_hp": 400, "intents": []}]
    if ahp is not None:
        enemies.insert(0, {"combat_id": 1, "id": AMID, "slot": "amalgam", "hp": ahp, "max_hp": 199, "intents": []})
    return {"turn": turn, "phase": "combat", "type": "card", "hand_index": 0, "target_id": 1,
            "player_hp": ph, "enemies": enemies, "player": {"energy": energy, "max_energy": energy,
            "hp": ph, "max_hp": 100, "powers": [], "relics": []},
            "hand": hand or [], "draw_pile": [], "discard_pile": [], "exhaust_pile": []}


class KillInfoTest(unittest.TestCase):
    def test_present_then_absent_is_a_kill_on_the_last_present_turn(self):
        rows = [_row(1, 199), _row(2, 120, ph=80), _row(3, 60, ph=40), _row(4, None, ph=30)]  # gone at turn 4 start
        k = T.kill_info(rows)
        self.assertTrue(k["killed"])
        self.assertEqual(k["kill_turn"], 3)          # killed during the last turn it was seen (turn 3)
        self.assertEqual(k["hp_at_kill"], 40)        # player HP at the start of the killing turn
        self.assertFalse(k["no_amalgam"])

    def test_present_through_the_end_is_not_killed(self):
        rows = [_row(1, 199), _row(2, 150), _row(3, 140)]  # amalgam never disappears -> survived
        self.assertFalse(T.kill_info(rows)["killed"])

    def test_never_present_is_flagged_no_amalgam(self):
        rows = [_row(1, None), _row(2, None)]
        k = T.kill_info(rows)
        self.assertFalse(k["killed"])
        self.assertTrue(k["no_amalgam"])


class BestAffordableDamageTest(unittest.TestCase):
    def test_greedy_spends_energy_on_the_biggest_affordable_attacks(self):
        hand = [
            {"id": "CARD.BASH", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 18}]},
            {"id": "CARD.UPPERCUT", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 12}]},
            {"id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "cost": 1, "vars": [{"id": "Damage", "value": 6}]},
            {"id": "CARD.FREE", "type": "Attack", "cost": 0, "vars": [{"id": "Damage", "value": 40}]},
            {"id": "CARD.DEFEND", "type": "Skill", "cost": 1, "vars": [{"id": "Block", "value": 5}]},
        ]
        # energy 3: free 40 + best-cost fit (BASH 18@2 + STRIKE 6@1 = 24) = 64; never spends on the Skill.
        self.assertEqual(T._best_affordable_damage(hand, 3), 64)

    def test_quest_or_unplayable_costs_are_ignored(self):
        hand = [{"id": "CARD.EGG", "type": "Quest", "cost": -1, "vars": []},
                {"id": "CARD.ATT", "type": "Attack", "cost": 5, "vars": [{"id": "Damage", "value": 30}]}]
        self.assertEqual(T._best_affordable_damage(hand, 3), 0)  # attack costs more than available energy


class MissedKillsTest(unittest.TestCase):
    def test_flags_a_turn_where_hand_damage_covered_remaining_but_survived(self):
        # amalgam at 50 HP; hand can deal 60 to it, but only 20 lands (amalgam ends at 30) -> a missed kill.
        rows = [_row(1, ahp=50, ph=90, energy=3,
                      hand=[{"id": "CARD.BIG", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 60}]}]),
                _row(1, ahp=30, ph=90, energy=1,
                      hand=[{"id": "CARD.BIG", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 60}]}])]
        m = T.missed_kills(rows)
        self.assertTrue(m["had_missed"])
        self.assertEqual(m["missed_turns"], 1)

    def test_no_miss_when_not_enough_damage_to_finish(self):
        rows = [_row(1, ahp=199, ph=90, energy=3,
                      hand=[{"id": "CARD.SMALL", "type": "Attack", "cost": 2, "vars": [{"id": "Damage", "value": 18}]}]),
                _row(1, ahp=181, ph=90, energy=1, hand=[])]
        self.assertFalse(T.missed_kills(rows)["had_missed"])  # 18 < 199 remaining, never a lethal opportunity


if __name__ == "__main__":
    unittest.main()
