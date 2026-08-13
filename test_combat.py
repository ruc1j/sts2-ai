import json
import random
import unittest
from dataclasses import replace

from combat import (
    ANGER, ASHEN_STRIKE, BASH, BATTLE_TRANCE, BELIEVE_IN_YOU, BLOODLETTING, BODY_SLAM, BOLAS, BREAK, BREAKTHROUGH, BULLY, BYRD_SWOOP, CINDER, DAZED, DEFEND,
    DISMANTLE, DOMINATE, DRUM_OF_BATTLE, EQUILIBRIUM, FEED, FINESSE, FISTICUFFS, FLAME_BARRIER, FRANTIC_ESCAPE, GIANT_ROCK, HEMOKINESIS, IMPATIENCE,
    IMPERVIOUS, INFLAME, IRON_WAVE, LIFT, MASTER_OF_STRATEGY, MIND_BLAST, MOLTEN_FIST, NOT_YET, OFFERING, PACTS_END, PERFECTED_STRIKE, PILLAGE, POMMEL_STRIKE,
    PRIMAL_FORCE, PRODUCTION, RELAX, SHRUG, SLIMED, STARTING_DECK, STRIKE, TAUNT, THUNDERCLAP, TOXIC, TREMBLE, UNRELENTING, WHIRLWIND, Combat, END_TURN,
    Enemy, _greedy_action, _power, initial_combat, legal_actions, search, step, _summon,
)


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

    def test_greedy_keeps_the_sandpit_alive(self) -> None:
        # With sand at 2 the next enemy turn would sink the player (sandpit 1 -> instant loss);
        # Frantic Escape restores 1 sand, so the greedy policy must prefer it over attacking.
        enemy = Enemy("MONSTER.THE_INSATIABLE", 321, "THRASH_MOVE", (), powers=(("SandpitPower", 2),))
        combat = Combat(80, (FRANTIC_ESCAPE, STRIKE), (), (), (enemy,))
        self.assertEqual(_greedy_action(combat, {}), FRANTIC_ESCAPE)

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

    def test_break_deals_damage_and_applies_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (BREAK,), (), (), (enemy,)), f"{BREAK}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, dict(after.enemies[0].powers)), (20, {"VulnerablePower": 5}))

    def test_taunt_gains_block_and_applies_vulnerable_without_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (TAUNT,), (), (), (enemy,)), f"{TAUNT}@0", {}, random.Random(0))
        self.assertEqual((after.player_block, after.enemies[0].hp, dict(after.enemies[0].powers)), (7, 40, {"VulnerablePower": 1}))

    def test_thunderclap_hits_and_weakens_every_enemy(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 40, "MOVE", ()), Enemy("MONSTER.DUMMY2", 40, "MOVE", ()))
        after = step(Combat(80, (THUNDERCLAP,), (), (), enemies), f"{THUNDERCLAP}@0", {}, random.Random(0))
        self.assertEqual([(e.hp, dict(e.powers)) for e in after.enemies], [(36, {"VulnerablePower": 1}), (36, {"VulnerablePower": 1})])

    def test_impervious_and_lift_grant_block_untargeted(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        self.assertEqual(step(Combat(80, (IMPERVIOUS,), (), (), (enemy,)), IMPERVIOUS, {}, random.Random(0)).player_block, 30)
        self.assertEqual(step(Combat(80, (LIFT,), (), (), (enemy,)), LIFT, {}, random.Random(0)).player_block, 11)

    def test_flat_damage_cards_deal_their_listed_damage(self) -> None:
        for card, damage in ((BOLAS, 3), (FISTICUFFS, 7)):
            enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
            after = step(Combat(80, (card,), (), (), (enemy,)), f"{card}@0", {}, random.Random(0))
            self.assertEqual(100 - after.enemies[0].hp, damage)

    def test_shrink_power_reduces_player_damage(self) -> None:
        # Shrinker Beetle's SHRINKER_MOVE applies ShrinkPower to the player (ShrinkPower.cs:
        # ModifyDamageMultiplicative cuts the *owner's* powered-attack damage by 30%, not
        # damage taken - a permanent self-debuff, not a defensive enemy power).
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (STRIKE,), (), (), (enemy,), player_powers=(("ShrinkPower", -1),))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 36)  # 6 damage * 0.7 = 4 (int division)

    def test_slippery_reduces_an_attack_to_one_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "MOVE", (), powers=(("SlipperyPower", 8),))
        combat = Combat(80, (ANGER,), (), (), (enemy,))
        after = step(combat, "Anger@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].powers), (19, (("SlipperyPower", 7),)))

    def test_hard_to_kill_caps_each_hit(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 30, "MOVE", (), powers=(("HardToKillPower", 9),))
        combat = Combat(80, (GIANT_ROCK,), (), (), (enemy,))
        after = step(combat, f"{GIANT_ROCK}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 21)  # 16 damage is capped at 9 per hit

    def test_plow_power_strips_strength_and_stuns_below_threshold(self) -> None:
        enemy = Enemy("MONSTER.CEREMONIAL_BEAST", 160, "PLOW_MOVE", (), powers=(("PlowPower", 150), ("StrengthPower", 6)))
        combat = Combat(80, (GIANT_ROCK,), (), (), (enemy,))
        after = step(combat, f"{GIANT_ROCK}@0", {}, random.Random(0))  # 16 damage: 160 -> 144, crosses the 150 threshold
        self.assertEqual((after.enemies[0].hp, after.enemies[0].move, dict(after.enemies[0].powers)), (144, "STUN_MOVE", {}))

    def test_plow_power_is_inert_above_threshold(self) -> None:
        enemy = Enemy("MONSTER.CEREMONIAL_BEAST", 252, "PLOW_MOVE", (), powers=(("PlowPower", 150), ("StrengthPower", 2)))
        combat = Combat(80, (GIANT_ROCK,), (), (), (enemy,))
        after = step(combat, f"{GIANT_ROCK}@0", {}, random.Random(0))  # 16 damage: 252 -> 236, still above 150
        self.assertEqual((after.enemies[0].hp, after.enemies[0].move, dict(after.enemies[0].powers)), (236, "PLOW_MOVE", {"PlowPower": 150, "StrengthPower": 2}))

    def test_exoskeleton_starts_with_hard_to_kill(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        combat = initial_combat(hive, "ENCOUNTER.EXOSKELETONS_WEAK", random.Random(0))
        self.assertTrue(combat.enemies)
        for enemy in combat.enemies:
            self.assertEqual(dict(enemy.powers).get("HardToKillPower"), 9)

    def test_byrdonis_gains_strength_every_turn(self) -> None:
        with open("data/enemies_overgrowth.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(data, "ENCOUNTER.BYRDONIS_ELITE", rng)
        for _ in range(2):
            combat = step(combat, END_TURN, data, rng)
        byrdonis = next(e for e in combat.enemies if e.model == "MONSTER.BYRDONIS")
        self.assertGreaterEqual(_power(byrdonis.powers, "StrengthPower"), 2)

    def test_slumbering_beetle_wakes_after_three_turns_asleep(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(data, "ENCOUNTER.SLUMBERING_BEETLE_NORMAL", rng)
        beetle = next(e for e in combat.enemies if e.model == "MONSTER.SLUMBERING_BEETLE")
        self.assertEqual(dict(beetle.powers).get("SlumberPower"), 3)
        self.assertEqual(beetle.move, "SNORE_MOVE")
        for _ in range(3):
            combat = step(combat, END_TURN, data, rng)
        beetle = next(e for e in combat.enemies if e.model == "MONSTER.SLUMBERING_BEETLE")
        self.assertEqual(beetle.move, "ROLL_OUT_MOVE")

    def test_phrog_parasite_death_spawns_four_wrigglers_and_continues(self) -> None:
        with open("data/enemies_overgrowth.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.PHROG_PARASITE", 5, "INFECT_MOVE", ())
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", data, random.Random(0))
        self.assertFalse(after.terminal)  # InfestedPower.ShouldStopCombatFromEnding: not a win yet
        self.assertEqual([e.model for e in after.enemies].count("MONSTER.WRIGGLER"), 4)
        self.assertTrue(all(e.primary and e.move == "SPAWNED_MOVE" for e in after.enemies if e.model == "MONSTER.WRIGGLER"))

    def test_decimillipede_segment_revives_after_dying_while_a_teammate_lives(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        front = Enemy("MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", 6, "WRITHE_MOVE", ())
        middle = Enemy("MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", 40, "WRITHE_MOVE", ())
        rng = random.Random(0)
        combat = step(Combat(80, (STRIKE,), (), (), (front, middle)), f"{STRIKE}@0", data, rng)
        self.assertEqual(combat.enemies[0].move, "DEAD_MOVE")
        self.assertFalse(combat.enemies[0].alive)
        self.assertFalse(combat.terminal)  # ReattachPower: not a real death while Middle lives
        combat = step(combat, END_TURN, data, rng)  # DEAD_MOVE turn: no-op
        self.assertEqual(combat.enemies[0].move, "REATTACH_MOVE")
        self.assertFalse(combat.enemies[0].alive)
        combat = step(combat, END_TURN, data, rng)  # REATTACH_MOVE turn: heals back to life
        self.assertEqual(combat.enemies[0].hp, 25)
        self.assertTrue(combat.enemies[0].alive)

    def test_infested_prism_vital_spark_taints_skill_cards_into_bonus_damage(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.INFESTED_PRISM", 161, "JAB_MOVE", (), powers=(("VitalSparkPower", 4),))
        combat = step(Combat(80, (SHRUG,), (), (), (enemy,)), SHRUG, data, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "TaintedPower"), 4)  # AfterCardPlayed on the Tainted Shrug It Off
        combat = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual(combat.player_hp, 80 - (15 + 4 - 8))  # JabDamage + TaintedPower, minus Shrug's block
        self.assertEqual(_power(combat.player_powers, "TaintedPower"), 0)  # AfterSideTurnEnd clears it

    def test_flame_barrier_grants_block_and_reflects_the_next_enemy_hit(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.MYTE", 65, "BITE_MOVE", ())
        combat = step(Combat(80, (FLAME_BARRIER,), (), (), (enemy,), energy=2), FLAME_BARRIER, data, random.Random(0))
        self.assertEqual((combat.player_block, _power(combat.player_powers, "FlameBarrierPower")), (12, 4))
        combat = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual((combat.player_hp, combat.enemies[0].hp), (79, 61))  # Bite 13-12 block, reflect 4 back
        self.assertEqual(_power(combat.player_powers, "FlameBarrierPower"), 0)  # cleared after the enemy's turn

    def test_molten_fist_deals_damage_and_doubles_existing_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", (), powers=(("VulnerablePower", 2),))
        after = step(Combat(80, (MOLTEN_FIST,), (), (), (enemy,)), f"{MOLTEN_FIST}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "VulnerablePower")), (85, 4))  # 100-15(10*1.5 vuln), Vulnerable 2+2

    def test_not_yet_heals_and_exhausts(self) -> None:
        after = step(Combat(70, (NOT_YET,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=2), NOT_YET, {}, random.Random(0))
        self.assertEqual((after.player_hp, after.exhaust_pile), (80, (NOT_YET,)))

    def test_offering_self_damages_gains_energy_and_draws(self) -> None:
        after = step(Combat(80, (OFFERING,), STARTING_DECK, (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), OFFERING, {}, random.Random(0))
        self.assertEqual((after.player_hp, after.energy, len(after.hand)), (74, 3, 3))

    def test_pacts_end_hits_every_enemy(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 100, "MOVE", ()), Enemy("MONSTER.DUMMY", 100, "MOVE", ()))
        after = step(Combat(80, (PACTS_END,), (), (), enemies, energy=1), f"{PACTS_END}@0", {}, random.Random(0))
        self.assertTrue(all(enemy.hp == 83 for enemy in after.enemies))

    def test_pommel_strike_deals_damage_and_draws(self) -> None:
        after = step(Combat(80, (POMMEL_STRIKE,), STARTING_DECK, (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), f"{POMMEL_STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, len(after.hand)), (91, 1))

    def test_mind_blast_damage_scales_with_draw_pile_size(self) -> None:
        after = step(Combat(80, (MIND_BLAST,), STARTING_DECK, (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), f"{MIND_BLAST}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 100 - len(STARTING_DECK))

    def test_body_slam_damage_scales_with_player_block(self) -> None:
        after = step(Combat(80, (BODY_SLAM,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1, player_block=13), f"{BODY_SLAM}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 87)

    def test_believe_in_you_grants_energy(self) -> None:
        after = step(Combat(80, (BELIEVE_IN_YOU,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), BELIEVE_IN_YOU, {}, random.Random(0))
        self.assertEqual(after.energy, 3)

    def test_finesse_grants_block_and_draws(self) -> None:
        after = step(Combat(80, (FINESSE,), STARTING_DECK, (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), FINESSE, {}, random.Random(0))
        self.assertEqual((after.player_block, len(after.hand)), (4, 1))

    def test_impatience_draws_only_when_hand_has_no_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        without_attack = step(Combat(80, (IMPATIENCE,), STARTING_DECK, (), (enemy,), energy=1), IMPATIENCE, {}, random.Random(0))
        self.assertEqual(len(without_attack.hand), 2)
        with_attack = step(Combat(80, (IMPATIENCE, STRIKE), STARTING_DECK, (), (enemy,), energy=1), IMPATIENCE, {}, random.Random(0))
        self.assertEqual(len(with_attack.hand), 1)

    def test_drum_of_battle_master_of_strategy_and_production(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        drum = step(Combat(80, (DRUM_OF_BATTLE,), STARTING_DECK, (), (enemy,), energy=1), DRUM_OF_BATTLE, {}, random.Random(0))
        self.assertEqual(len(drum.hand), 2)
        strategy = step(Combat(80, (MASTER_OF_STRATEGY,), STARTING_DECK, (), (enemy,), energy=1), MASTER_OF_STRATEGY, {}, random.Random(0))
        self.assertEqual((len(strategy.hand), strategy.exhaust_pile), (3, (MASTER_OF_STRATEGY,)))
        production = step(Combat(80, (PRODUCTION,), (), (), (enemy,), energy=1), PRODUCTION, {}, random.Random(0))
        self.assertEqual(production.energy, 3)

    def test_ringing_power_restricts_to_one_card_per_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        combat = Combat(80, (STRIKE, DEFEND), (), (), (enemy,), player_powers=(("RingingPower", 1),))
        self.assertIn(f"{STRIKE}@0", legal_actions(combat))  # nothing played yet this turn
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(legal_actions(after), (END_TURN,))  # Ringing: only one card per turn

    def test_ringing_power_clears_after_the_players_turn_ends(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.SPINY_TOAD", 100, "TONGUE_LASH_MOVE", ())
        combat = Combat(80, (STRIKE,), STARTING_DECK, (), (enemy,), player_powers=(("RingingPower", 1),))
        after = step(combat, f"{STRIKE}@0", data, random.Random(0))
        self.assertEqual(legal_actions(after), (END_TURN,))
        after = step(after, END_TURN, data, random.Random(0))
        self.assertEqual(_power(after.player_powers, "RingingPower"), 0)
        self.assertTrue(any(action != END_TURN for action in legal_actions(after)))

    def test_thorns_power_reflects_damage_on_single_target_attack(self) -> None:
        enemy = Enemy("MONSTER.SPINY_TOAD", 100, "MOVE", (), powers=(("ThornsPower", 5),))
        after = step(Combat(80, (STRIKE,), (), (), (enemy,)), f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.player_hp, after.enemies[0].hp), (75, 94))  # 80-5 reflected, 100-6 Strike damage

    def test_thorns_power_reflects_damage_once_per_enemy_on_whirlwind(self) -> None:
        thorny = Enemy("MONSTER.SPINY_TOAD", 100, "MOVE", (), powers=(("ThornsPower", 5),))
        plain = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        combat = Combat(80, (WHIRLWIND,), (), (), (thorny, plain), energy=2)
        after = step(combat, f"{WHIRLWIND}@0", {}, random.Random(0))
        self.assertEqual(after.player_hp, 75)  # only the Thorns-holding target reflects

    def test_entomancer_pheromone_spit_caps_personal_hive_and_slows_strength(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.ENTOMANCER", 200, "PHEROMONE_SPIT_MOVE", (), powers=(("PersonalHivePower", 1),))
        combat = Combat(80, (), (), (), (enemy,))
        rng = random.Random(0)
        for _ in range(4):
            combat = step(combat, END_TURN, data, rng)
            combat = replace(combat, enemies=(replace(combat.enemies[0], move="PHEROMONE_SPIT_MOVE"),))
        enemy = combat.enemies[0]
        self.assertEqual(_power(enemy.powers, "PersonalHivePower"), 3)  # 1 -> 2 -> 3, then capped
        self.assertEqual(_power(enemy.powers, "StrengthPower"), 6)  # +1, +1, then +2, +2 once capped (not +3 x4)

    def test_entomancer_personal_hive_inserts_dazed_into_draw_pile_on_hit(self) -> None:
        enemy = Enemy("MONSTER.ENTOMANCER", 200, "BEES_MOVE", (), powers=(("PersonalHivePower", 2),))
        after = step(Combat(80, (STRIKE,), (), (), (enemy,)), f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.draw_pile.count(DAZED), 2)

    def test_myte_toxic_move_injects_hand_cards_that_burn_hp_next_turn_end(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.MYTE", 65, "TOXIC_MOVE", ())
        combat = step(Combat(80, (), STARTING_DECK, (), (enemy,)), END_TURN, data, random.Random(0))
        self.assertEqual(combat.hand.count(TOXIC), 2)  # CardPileCmd.AddToCombatAndPreview -> PileType.Hand
        self.assertEqual(combat.player_hp, 80)  # StatusIntent only, no damage yet
        combat = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual(combat.player_hp, 80 - 2 * 5 - 13)  # 2x Toxic (5 each) + Myte's next BiteMove (13)
        self.assertEqual(combat.hand.count(TOXIC), 0)  # discarded at turn end, not redrawn out of a real deck

    def test_decimillipede_last_segment_stays_dead_and_ends_combat(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        front = Enemy("MONSTER.DECIMILLIPEDE_SEGMENT_FRONT", 6, "WRITHE_MOVE", ())
        middle = Enemy("MONSTER.DECIMILLIPEDE_SEGMENT_MIDDLE", -3, "DEAD_MOVE", ())
        combat = step(Combat(80, (STRIKE,), (), (), (front, middle)), f"{STRIKE}@0", data, random.Random(0))
        self.assertFalse(combat.enemies[0].alive)
        self.assertNotEqual(combat.enemies[0].move, "DEAD_MOVE")  # ShouldOwnerDeathTriggerFatal: no revival
        self.assertTrue(combat.terminal)

    def test_all_overgrowth_encounters_run(self) -> None:
        for encounter in self.data["encounters"]:
            with self.subTest(encounter=encounter["id"]):
                rng = random.Random(0)
                combat = initial_combat(self.data, encounter["id"], rng)
                for _ in range(100):
                    if combat.terminal:
                        break
                    combat = step(combat, rng.choice(legal_actions(combat)), self.data, rng)

    def test_cinder_damages_and_exhausts_a_random_hand_card(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (CINDER, STRIKE, DEFEND), (), (), (enemy,)), f"{CINDER}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 22)
        self.assertEqual(len(after.exhaust_pile), 1)
        self.assertEqual(sorted(after.hand), sorted({STRIKE, DEFEND} - set(after.exhaust_pile)))

    def test_perfected_strike_scales_with_strike_tagged_cards(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (PERFECTED_STRIKE, STRIKE), (STRIKE, STRIKE), (), (enemy,))
        after = step(combat, f"{PERFECTED_STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 26)  # 6 + 2 * 4 strikes

    def test_ashen_strike_scales_with_exhaust_pile(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 30, "MOVE", ())
        combat = Combat(80, (ASHEN_STRIKE,), (), (), (enemy,), exhaust_pile=(STRIKE, STRIKE, BASH))
        after = step(combat, f"{ASHEN_STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.exhaust_pile), (15, (STRIKE, STRIKE, BASH, ASHEN_STRIKE)))

    def test_hemokinesis_self_damages(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (HEMOKINESIS,), (), (), (enemy,)), f"{HEMOKINESIS}@0", {}, random.Random(0))
        self.assertEqual((after.player_hp, after.enemies[0].hp), (78, 25))

    def test_inflame_adds_strength_to_attacks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = step(Combat(80, (INFLAME, STRIKE), (), (), (enemy,)), INFLAME, {}, random.Random(0))
        self.assertEqual(combat.player_powers, (("StrengthPower", 2),))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 32)  # 6 + 2 strength

    def test_breakthrough_hits_all_enemies_and_self_damages(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 20, "MOVE", ()), Enemy("MONSTER.DUMMY", 30, "MOVE", ()))
        after = step(Combat(80, (BREAKTHROUGH,), (), (), enemies), f"{BREAKTHROUGH}@0", {}, random.Random(0))
        self.assertEqual((after.player_hp, after.enemies[0].hp, after.enemies[1].hp), (79, 11, 21))

    def test_whirlwind_spends_all_energy_on_all_enemies(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 40, "MOVE", ()), Enemy("MONSTER.DUMMY", 30, "MOVE", ()))
        combat = Combat(80, (WHIRLWIND,), (), (), enemies, energy=3)
        self.assertIn(f"{WHIRLWIND}@0", legal_actions(combat))
        after = step(combat, f"{WHIRLWIND}@0", {}, random.Random(0))
        self.assertEqual((after.energy, after.enemies[0].hp, after.enemies[1].hp), (0, 25, 15))

    def test_whirlwind_is_unplayable_without_energy(self) -> None:
        combat = Combat(80, (WHIRLWIND,), (), (), (Enemy("MONSTER.DUMMY", 40, "MOVE", ()),), energy=0)
        self.assertNotIn(f"{WHIRLWIND}@0", legal_actions(combat))

    def test_bloodletting_trades_hp_for_energy(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (BLOODLETTING,), (), (), (enemy,)), BLOODLETTING, {}, random.Random(0))
        self.assertEqual((after.player_hp, after.energy), (77, 5))

    def test_feed_deals_damage_and_exhausts(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (FEED,), (), (), (enemy,)), f"{FEED}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.discard_pile, after.exhaust_pile), (30, (), (FEED,)))

    def test_flutter_halves_attack_damage_and_wears_off(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("FlutterPower", 5),))
        after = step(Combat(80, (STRIKE,), (), (), (enemy,)), f"{STRIKE}@0", {}, random.Random(0))
        # 6 damage halved to 3; the unblocked hit consumes one Flutter stack.
        self.assertEqual((after.enemies[0].hp, dict(after.enemies[0].powers).get("FlutterPower")), (37, 4))

    def test_flutter_halves_vulnerable_boosted_damage(self) -> None:
        # Matches the observed Thieving Hopper fight: 18 damage * 1.5 Vulnerable = 27, halved to 13.
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("VulnerablePower", 2), ("FlutterPower", 5)))
        after = step(Combat(80, (CINDER,), (), (), (enemy,)), f"{CINDER}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, dict(after.enemies[0].powers).get("FlutterPower")), (27, 4))

    def test_flutter_does_not_wear_off_on_blocked_hits(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), block=10, powers=(("FlutterPower", 5),))
        after = step(Combat(80, (STRIKE,), (), (), (enemy,)), f"{STRIKE}@0", {}, random.Random(0))
        # 6 halved to 3 and fully blocked: Flutter stays untouched.
        self.assertEqual((after.enemies[0].hp, dict(after.enemies[0].powers).get("FlutterPower")), (40, 5))

    def test_search_attacks_instead_of_letting_the_hopper_escape(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.THIEVING_HOPPER")
        enemy = Enemy("MONSTER.THIEVING_HOPPER", 5, "ESCAPE_MOVE", tuple(sorted(spec["values"].items())), powers=(("EscapeArtistPower", 1),))
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        best, _ = search(combat, hive, 600, 0)[0]
        # Ending the turn lets the hopper flee (no win); finishing it is the only real win.
        self.assertEqual(best, f"{STRIKE}@0")

    def test_thieving_hopper_encounter_runs_and_terminates(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(hive, "ENCOUNTER.THIEVING_HOPPER_WEAK", rng)
        for _ in range(60):
            if combat.terminal:
                break
            combat = step(combat, rng.choice(legal_actions(combat)), hive, rng)
        # The hopper flees after its attack chain, so the fight always terminates.
        self.assertTrue(combat.terminal)

    def test_iron_wave_deals_damage_and_blocks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (IRON_WAVE,), (), (), (enemy,)), f"{IRON_WAVE}@0", {}, random.Random(0))
        self.assertEqual((after.player_block, after.enemies[0].hp), (5, 35))

    def test_relax_blocks_and_exhausts(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (RELAX,), (), (), (enemy,)), RELAX, {}, random.Random(0))
        self.assertEqual((after.player_block, after.exhaust_pile, after.discard_pile), (15, (RELAX,), ()))

    def test_tremble_applies_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (TREMBLE,), (), (), (enemy,)), f"{TREMBLE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 3),))

    def test_primal_force_transforms_attacks_into_giant_rocks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (PRIMAL_FORCE, STRIKE, DEFEND), (), (), (enemy,)), PRIMAL_FORCE, {}, random.Random(0))
        self.assertEqual(tuple(sorted(after.hand)), (DEFEND, GIANT_ROCK))

    def test_unrelenting_and_giant_rock_deal_flat_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        unrelenting = step(Combat(80, (UNRELENTING,), (), (), (enemy,)), f"{UNRELENTING}@0", {}, random.Random(0))
        rock = step(Combat(80, (GIANT_ROCK,), (), (), (enemy,)), f"{GIANT_ROCK}@0", {}, random.Random(0))
        self.assertEqual((unrelenting.enemies[0].hp, rock.enemies[0].hp), (26, 24))

    def test_illusion_power_minion_revives_after_enemy_phase(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.PARAFRIGHT")
        values = tuple(sorted(spec["values"].items()))
        minion = Enemy("MONSTER.PARAFRIGHT", 5, "SLAM_MOVE", values, powers=(("IllusionPower", 1), ("MinionPower", 1)), primary=False)
        boss = Enemy("MONSTER.PARAFRIGHT", 50, "SLAM_MOVE", values)
        combat = step(Combat(80, (ANGER,), (), (), (minion, boss)), f"{ANGER}@0", {}, random.Random(0))
        self.assertFalse(combat.enemies[0].alive)
        after = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 21)

    def test_search_prefers_killing_an_attacking_minion(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        specs = {monster["id"]: monster for monster in hive["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = (), primary: bool = True) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), powers=powers, primary=primary)

        minion = make("MONSTER.PARAFRIGHT", 5, "SLAM_MOVE", powers=(("IllusionPower", 1), ("MinionPower", 1), ("StrengthPower", 6)), primary=False)
        boss = make("MONSTER.THE_OBSCURA", 64, "HARDENING_STRIKE_MOVE", powers=(("StrengthPower", 6),))
        combat = Combat(45, (BASH, IRON_WAVE), (), (), (minion, boss), player_powers=(("StrengthPower", 4),), energy=2, turn=4)
        best, _ = search(combat, hive, 1500, 0)[0]
        # Finishing off the attacking minion prevents 21 damage and should be the top pick.
        # With SAIL now buffing the boss too, Iron Wave (kills the minion AND blocks 5) edges out
        # the pure-damage Bash against the scaling boss.
        self.assertEqual(best, f"{IRON_WAVE}@0")

    def test_greedy_action_prefers_killing_the_attacking_minion(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        specs = {monster["id"]: monster for monster in hive["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = (), primary: bool = True) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), powers=powers, primary=primary)

        minion = make("MONSTER.PARAFRIGHT", 2, "SLAM_MOVE", powers=(("IllusionPower", 1), ("MinionPower", 1), ("StrengthPower", 6)), primary=False)
        boss = make("MONSTER.THE_OBSCURA", 65, "HARDENING_STRIKE_MOVE", powers=(("StrengthPower", 6),))
        combat = Combat(46, (HEMOKINESIS, STRIKE), (), (), (minion, boss), player_powers=(("StrengthPower", 4),), energy=3, turn=5)
        # Finishing the 2-HP minion prevents 22 damage; Strike does so without self-damage.
        self.assertEqual(_greedy_action(combat, hive), f"{STRIKE}@0")

    def test_greedy_action_avoids_self_kill(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        specs = {monster["id"]: monster for monster in hive["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = ()) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), powers=powers)

        minion = make("MONSTER.PARAFRIGHT", 2, "SLAM_MOVE", powers=(("IllusionPower", 1), ("MinionPower", 1), ("StrengthPower", 6)))
        boss = make("MONSTER.THE_OBSCURA", 65, "HARDENING_STRIKE_MOVE", powers=(("StrengthPower", 6),))
        combat = Combat(1, (HEMOKINESIS, STRIKE), (), (), (minion, boss), player_powers=(("StrengthPower", 4),), energy=3, turn=5)
        # Hemokinesis would deal 2 self-damage and kill the player; the policy must not pick it.
        self.assertEqual(_greedy_action(combat, hive), f"{STRIKE}@0")

    def test_greedy_prefers_boss_kill_over_minion(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        specs = {monster["id"]: monster for monster in hive["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = (), primary: bool = True) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), powers=powers, primary=primary)

        minion = make("MONSTER.PARAFRIGHT", 21, "SLAM_MOVE", powers=(("IllusionPower", 1), ("MinionPower", 1), ("StrengthPower", 6)), primary=False)
        boss = make("MONSTER.THE_OBSCURA", 5, "HARDENING_STRIKE_MOVE", powers=(("StrengthPower", 6),))
        combat = Combat(40, (BASH, IRON_WAVE), (), (), (minion, boss), player_powers=(("StrengthPower", 4),), energy=2, turn=3)
        # The boss is killable and killing it wins the fight: target the boss (Iron Wave also blocks).
        self.assertEqual(_greedy_action(combat, hive), f"{IRON_WAVE}@1")

    def test_greedy_plays_vulnerability_before_attacks(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        specs = {monster["id"]: monster for monster in hive["monsters"]}
        boss = Enemy(
            model="MONSTER.THE_OBSCURA",
            hp=100,
            move="HARDENING_STRIKE_MOVE",
            values=tuple(sorted(specs["MONSTER.THE_OBSCURA"]["values"].items())),
            powers=(("StrengthPower", 6),),
        )
        combat = Combat(50, (BASH, STRIKE, STRIKE), (), (), (boss,), player_powers=(("StrengthPower", 4),), energy=4, turn=1)
        # Bash first so the strikes benefit from Vulnerable.
        self.assertEqual(_greedy_action(combat, hive), f"{BASH}@0")

    def test_sail_buffs_teammates_and_self(self) -> None:
        # GetTeammatesOf returns every creature on the same side, including the caster: the
        # real fight trace shows Obscura itself at Strength 3 -> 6 -> 9 as SAIL repeats.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        specs = {monster["id"]: monster for monster in hive["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = (), primary: bool = True) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), powers=powers, primary=primary)

        boss = make("MONSTER.THE_OBSCURA", 123, "SAIL_MOVE")
        minion = make("MONSTER.PARAFRIGHT", 21, "SLAM_MOVE", powers=(("IllusionPower", 1), ("MinionPower", 1)), primary=False)
        after = step(Combat(80, (DEFEND,), (), (), (boss, minion)), END_TURN, hive, random.Random(0))
        self.assertEqual(after.enemies[1].powers, (("IllusionPower", 1), ("MinionPower", 1), ("StrengthPower", 3)))
        self.assertEqual(after.enemies[0].powers, (("StrengthPower", 3),))

    def test_dominate_applies_vulnerable_and_gains_strength(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("VulnerablePower", 2),))
        after = step(Combat(80, (DOMINATE,), (), (), (enemy,)), f"{DOMINATE}@0", {}, random.Random(0))
        # 1 Vulnerable applied on top of 2, then the player gains Strength equal to the total.
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 3),))
        self.assertEqual(after.player_powers, (("StrengthPower", 3),))
        self.assertEqual((after.exhaust_pile, after.discard_pile), ((DOMINATE,), ()))

    def test_dominate_requires_a_target(self) -> None:
        combat = Combat(80, (DOMINATE,), (), (), (Enemy("MONSTER.DUMMY", 40, "MOVE", ()),))
        self.assertIn(f"{DOMINATE}@0", legal_actions(combat))

    def test_parafright_revives_at_max_hp_after_dying(self) -> None:
        # Parafright.AfterAddedToRoom grants IllusionPower(1) (not exported); step()'s END_TURN
        # handling has always known how to revive IllusionPower holders, but nothing ever
        # granted them the power - this was dead code until _summon/initial_combat granted it.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        parafright = _summon("Parafright", data, random.Random(0))
        self.assertEqual(_power(parafright.powers, "IllusionPower"), 1)
        boss = Enemy("MONSTER.THE_OBSCURA", 999, "PIERCING_GAZE_MOVE", (("MinInitialHp", 999), ("MaxInitialHp", 999)))
        combat = Combat(80, (STRIKE,), (), (), (replace(parafright, hp=1), boss))
        after = step(combat, f"{STRIKE}@0", data, random.Random(0))
        self.assertFalse(after.enemies[0].alive)
        revived = step(after, END_TURN, data, random.Random(0))
        self.assertEqual(revived.enemies[0].hp, parafright.hp)
        self.assertTrue(revived.enemies[0].alive)

    def test_hive_boss_encounter_simulates(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(hive, "ENCOUNTER.THE_OBSCURA_NORMAL", rng)
        for _ in range(200):
            if combat.terminal:
                break
            combat = step(combat, rng.choice(legal_actions(combat)), hive, rng)

    def test_insatiable_liquify_does_not_crash(self) -> None:
        # Liquify's CardPileCmd.AddGeneratedCardToCombat carries no numeric amount; the
        # generator must skip it instead of crashing on "null" (this used to disable the
        # turn-1 rollout in the Insatiable boss fight).
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.THE_INSATIABLE")
        enemy = Enemy("MONSTER.THE_INSATIABLE", 321, "LIQUIFY_GROUND_MOVE", tuple(sorted(spec["values"].items())))
        combat = Combat(80, (DEFEND,), (), (), (enemy,))
        after = step(combat, END_TURN, hive, random.Random(0))
        # Liquify grants Sandpit 4 and adds Frantic Escape cards; the phase completes without error.
        self.assertEqual(dict(after.enemies[0].powers).get("SandpitPower"), 4)

    def test_byrd_swoop_is_a_free_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (BYRD_SWOOP, STRIKE), (), (), (enemy,))
        self.assertIn(f"{BYRD_SWOOP}@0", legal_actions(combat))
        after = step(combat, f"{BYRD_SWOOP}@0", {}, random.Random(0))
        self.assertEqual((after.energy, after.enemies[0].hp), (3, 26))

    def test_pillage_deals_damage_and_draws_to_a_non_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        # Random(0) pops index 1 first: Strike comes up, Pillage keeps drawing, Defend stops it.
        combat = Combat(80, (PILLAGE,), (DEFEND, STRIKE), (), (enemy,))
        after = step(combat, f"{PILLAGE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.energy, after.hand), (34, 2, (STRIKE, DEFEND)))

    def test_pillage_stops_after_a_non_attack_draw(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        # Random(0) pops index 1 first: Defend (non-Attack) stops the draw immediately.
        combat = Combat(80, (PILLAGE,), (STRIKE, DEFEND), (), (enemy,))
        after = step(combat, f"{PILLAGE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.hand), (34, (DEFEND,)))

    def test_equilibrium_blocks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (EQUILIBRIUM,), (), (), (enemy,))
        self.assertIn(EQUILIBRIUM, legal_actions(combat))
        after = step(combat, EQUILIBRIUM, {}, random.Random(0))
        self.assertEqual((after.player_block, after.energy), (13, 1))

    def test_insatiable_boss_encounter_search_runs(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(hive, "ENCOUNTER.THE_INSATIABLE_BOSS", rng)
        for _ in range(60):
            if combat.terminal:
                break
            combat = step(combat, rng.choice(legal_actions(combat)), hive, rng)

    def test_knowledge_demon_boss_survives_curse_of_knowledge_branch(self) -> None:
        # PONDER_MOVE.next is a ConditionalBranchState keyed off a private turn counter
        # (see _condition's CurseOfKnowledgeBranch handling); reached by turn ~4, so 60 turns
        # of always-end-turn play exercises it repeatedly without ever raising.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(hive, "ENCOUNTER.KNOWLEDGE_DEMON_BOSS", rng, player_hp=9999)
        for _ in range(60):
            if combat.terminal:
                break
            combat = step(combat, END_TURN, hive, rng)
        self.assertGreaterEqual(_power(combat.enemies[0].powers, "CurseOfKnowledgeCounter"), 3)


if __name__ == "__main__":
    unittest.main()
