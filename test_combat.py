import json
import random
import unittest

from combat import ANGER, BATTLE_TRANCE, BULLY, DEFEND, DISMANTLE, FRANTIC_ESCAPE, SHRUG, SLIMED, Combat, END_TURN, Enemy, initial_combat, legal_actions, step


class CombatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open("data/enemies_overgrowth.json", encoding="utf-8-sig") as file:
            cls.data = json.load(file)

    def test_generates_and_runs_multi_enemy_turn(self) -> None:
        combat = initial_combat(self.data, "ENCOUNTER.SLIMES_WEAK", random.Random(0))
        self.assertEqual(len(combat.enemies), 3)
        self.assertTrue(any("@2" in action for action in legal_actions(combat)))
        after = step(combat, END_TURN, self.data, random.Random(0))
        self.assertEqual(after.turn, 2)

    def test_anger_adds_copy_to_discard(self) -> None:
        combat = Combat(80, (ANGER,), (), (), (Enemy("MONSTER.DUMMY", 20, "MOVE", ()),))
        after = step(combat, "Anger@0", {}, random.Random(0))
        self.assertEqual(after.discard_pile, (ANGER, ANGER))

    def test_shrug_blocks_and_draws(self) -> None:
        combat = Combat(80, (SHRUG,), (DEFEND,), (), (Enemy("MONSTER.DUMMY", 20, "MOVE", ()),))
        after = step(combat, SHRUG, {}, random.Random(0))
        self.assertEqual((after.player_block, after.hand), (8, (DEFEND,)))

    def test_battle_trance_draws_three(self) -> None:
        combat = Combat(80, (BATTLE_TRANCE,), (DEFEND, DEFEND, DEFEND), (), (Enemy("MONSTER.DUMMY", 20, "MOVE", ()),))
        after = step(combat, BATTLE_TRANCE, {}, random.Random(0))
        self.assertEqual((after.energy, len(after.hand)), (3, 3))

    def test_slimed_draws_then_exhausts(self) -> None:
        combat = Combat(80, (SLIMED,), (DEFEND,), (), (Enemy("MONSTER.DUMMY", 20, "MOVE", ()),))
        after = step(combat, SLIMED, {}, random.Random(0))
        self.assertEqual((after.energy, after.hand, after.discard_pile), (2, (DEFEND,), ()))

    def test_frantic_escape_extends_sandpit_countdown(self) -> None:
        enemy = Enemy("MONSTER.THE_INSATIABLE", 321, "THRASH_MOVE", (), powers=(("SandpitPower", 3),))
        after = step(Combat(80, (FRANTIC_ESCAPE,), (), (), (enemy,)), FRANTIC_ESCAPE, {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("SandpitPower", 4),))

    def test_crab_attack_turns_away_from_the_dangerous_claw(self) -> None:
        left = Enemy("MONSTER.CRUSHER", 20, "MOVE", (), powers=(("BackAttackLeftPower", 1),))
        combat = Combat(80, (ANGER,), (), (), (left,), player_powers=(("SurroundedRight", 1),))
        after = step(combat, "Anger@0", {}, random.Random(0))
        self.assertEqual(after.player_powers, (("SurroundedLeft", 1),))

    def test_bully_and_dismantle_scale_with_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("VulnerablePower", 2),))
        bully = step(Combat(80, (BULLY,), (), (), (enemy,)), "Bully@0", {}, random.Random(0))
        dismantle = step(Combat(80, (DISMANTLE,), (), (), (enemy,)), "Dismantle@0", {}, random.Random(0))
        self.assertEqual((bully.enemies[0].hp, dismantle.enemies[0].hp), (28, 16))

    def test_slippery_reduces_an_attack_to_one_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "MOVE", (), powers=(("SlipperyPower", 8),))
        combat = Combat(80, (ANGER,), (), (), (enemy,))
        after = step(combat, "Anger@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].powers), (19, (("SlipperyPower", 7),)))

    def test_all_overgrowth_encounters_run(self) -> None:
        for encounter in self.data["encounters"]:
            with self.subTest(encounter=encounter["id"]):
                rng = random.Random(0)
                combat = initial_combat(self.data, encounter["id"], rng)
                for _ in range(100):
                    if combat.terminal:
                        break
                    combat = step(combat, rng.choice(legal_actions(combat)), self.data, rng)


if __name__ == "__main__":
    unittest.main()
