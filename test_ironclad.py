import random
import unittest

from ironclad import BASH, DEFEND, END_TURN, STRIKE, State, search, step


class IroncladTest(unittest.TestCase):
    def test_bash_then_strike_uses_vulnerable(self) -> None:
        state = State(80, 17, 0, (BASH, STRIKE))
        state = step(state, BASH, random.Random(0))
        state = step(state, STRIKE, random.Random(0))
        self.assertEqual(state.enemy_hp, 0)

    def test_search_finds_lethal(self) -> None:
        state = State(10, 6, 20, (STRIKE, DEFEND), energy=1)
        self.assertEqual(search(state, simulations=300, seed=0)[0][0], STRIKE)

    def test_enemy_strength_cycle(self) -> None:
        enemy = {
            "class": "FuzzyWurmCrawler",
            "values": {"AcidGoopDamage": 4},
            "states": [
                {"id": "FIRST", "type": "MoveState", "intents": [{"damage": 4}], "effects": [], "next": "INHALE"},
                {"id": "INHALE", "type": "MoveState", "intents": [], "effects": [{"command": "PowerCmd.Apply", "model": "StrengthPower", "target": "base.Creature", "amount": "7m"}], "next": "ATTACK"},
                {"id": "ATTACK", "type": "MoveState", "intents": [{"damage": 4}], "effects": [], "next": "FIRST"},
            ],
        }
        state = State(80, 55, 0, (), enemy_state="FIRST")
        state = step(state, END_TURN, random.Random(0), enemy)
        state = step(state, END_TURN, random.Random(0), enemy)
        state = step(state, END_TURN, random.Random(0), enemy)
        self.assertEqual((state.player_hp, state.enemy_strength), (65, 7))


if __name__ == "__main__":
    unittest.main()
