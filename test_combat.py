import json
import random
import unittest
from dataclasses import replace

from combat import (
    ANGER, ASHEN_STRIKE, BASH, BATTLE_TRANCE, BELIEVE_IN_YOU, BLOODLETTING, BODY_SLAM, BOLAS, BRAND, BREAK, BREAKTHROUGH, BULLY, BURNING_PACT, BYRD_SWOOP, CINDER, DAZED, DEFEND,
    DISMANTLE, DOMINATE, DRUM_OF_BATTLE, EQUILIBRIUM, FEED, FINESSE, FISTICUFFS, FLAME_BARRIER, FRANTIC_ESCAPE, GIANT_ROCK, HEMOKINESIS, IMPATIENCE,
    IMPERVIOUS, INFECTION, INFLAME, IRON_WAVE, LIFT, MASTER_OF_STRATEGY, MIND_BLAST, MOLTEN_FIST, NOT_YET, OFFERING, PACTS_END, PERFECTED_STRIKE, PILLAGE, POMMEL_STRIKE,
    ENLIGHTENMENT, EVIL_EYE, FIEND_FIRE, HEADBUTT, INFERNAL_BLADE, MANGLE, PRIMAL_FORCE, PRODUCTION, RELAX, RELIC_ART_OF_WAR, RELIC_BRIMSTONE, RELIC_CANDELABRA, RELIC_CAPTAINS_WHEEL, RELIC_CENTENNIAL_PUZZLE, RELIC_CLOAK_CLASP,
    RELIC_BEATING_REMNANT, RELIC_BELLOWS, RELIC_BELT_BUCKLE, RELIC_DEMON_TONGUE, RELIC_LIZARD_TAIL, RELIC_KUNAI, RELIC_KUSARIGAMA, RELIC_MERCURY_HOURGLASS, RELIC_NUNCHAKU, RELIC_PEN_NIB, RELIC_REPTILE_TRINKET, RELIC_RUINED_HELMET, RELIC_SELF_FORMING_CLAY, RELIC_SCREAMING_FLAGON, RELIC_TUNGSTEN_ROD, RELIC_VAMBRACE, COLOSSUS, RAGE, RUPTURE, SECOND_WIND, SHRUG, SLIMED, SPITE, STONE_ARMOR, FEEL_NO_PAIN, STARTING_DECK, STRIKE, VOLLEY,
    STOMP, TAUNT, TEST_SUBJECT, THUNDERCLAP, TOXIC, TREMBLE, TRUE_GRIT, TWIN_STRIKE, UPPERCUT, UNRELENTING, WHIRLWIND, WOUND, Combat, END_TURN, Enemy, _greedy_action, _power, initial_combat, legal_actions, search, step,
    _apply_player_damage, _enemy_attack_damage, _resolve_move, _step_score, _summon,
)

# A single harmless, no-op monster used to isolate turn-transition relic effects (Brimstone,
# ScreamingFlagon, etc.) from needing real exported enemy data.
DUMMY_DATA = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{"id": "IDLE_MOVE", "type": "MoveState", "intents": [], "next": "IDLE_MOVE", "effects": []}]}]}
# Same, but attacks for 10 each turn - used to test relics that trigger on the player taking
# unblocked damage (DemonTongue, CentennialPuzzle) or block relics (CloakClasp).
ATTACKING_DUMMY_DATA = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
    "id": "HIT_MOVE", "type": "MoveState", "intents": [{"type": "SingleAttackIntent", "damage": 10.0, "repeats": 1}], "next": "HIT_MOVE",
    "effects": [{"command": "DamageCmd.Attack", "arguments": ["Damage"], "amount": 10}],
}]}]}
# A move with a real attack intent but no "effects" key at all (the Decimillipede segment export
# gap) - used to verify the synthetic DamageCmd.Attack fallback in _enemy_turn.
EFFECTLESS_ATTACK_DUMMY_DATA = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
    "id": "HIT_MOVE", "type": "MoveState", "intents": [{"type": "MultiAttackIntent", "damage": 5.0, "repeats": 2}], "next": "HIT_MOVE",
}]}]}


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

    def test_queen_runtime_branch_follows_torch_head_life(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        queen_spec = next(monster for monster in data["monsters"] if monster["id"] == "MONSTER.QUEEN")
        queen = Enemy("MONSTER.QUEEN", 400, "BURN_BRIGHT_FOR_ME_BRANCH", tuple(sorted(queen_spec["values"].items())))
        amalgam = Enemy("MONSTER.TORCH_HEAD_AMALGAM", 199, "TACKLE_MOVE", (), primary=False)
        self.assertEqual(
            _resolve_move(queen, queen_spec, random.Random(0), enemies=(amalgam, queen)),
            "BURN_BRIGHT_FOR_ME_MOVE",
        )
        self.assertEqual(
            _resolve_move(queen, queen_spec, random.Random(0), enemies=(replace(amalgam, hp=0), queen)),
            "OFF_WITH_YOUR_HEAD_MOVE",
        )

    def test_end_turn_restores_max_energy_not_hardcoded_three(self) -> None:
        combat = initial_combat(self.data, "ENCOUNTER.SLIMES_WEAK", random.Random(0))
        combat = replace(combat, energy=1, max_energy=4)
        after = step(combat, END_TURN, self.data, random.Random(0))
        self.assertEqual(after.energy, 4)

    def test_knowledge_demon_powers_are_applied_to_rollouts(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ())
        combat = Combat(20, (), (STRIKE,) * 5, (), (enemy,), player_powers=(("DisintegrationPower", 5), ("MindRotPower", 1)))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 15)
        self.assertEqual(len(after.hand), 4)

    def test_kunai_grants_dexterity_every_third_attack_this_turn(self) -> None:
        combat = Combat(80, (STRIKE, STRIKE, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_KUNAI,))
        for _ in range(3):
            combat = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "DexterityPower"), 1)

    def test_kunai_does_not_trigger_on_the_second_attack(self) -> None:
        combat = Combat(80, (STRIKE, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_KUNAI,))
        for _ in range(2):
            combat = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "DexterityPower"), 0)

    def test_tungsten_and_beating_remnant_apply_in_same_order_for_all_hp_loss(self) -> None:
        relics = (RELIC_TUNGSTEN_ROD, RELIC_BEATING_REMNANT)
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=relics, damage_received_this_turn=19)
        self.assertEqual(_apply_player_damage(combat, 5).player_hp, 79)
        attack_data = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
            "id": "HIT_MOVE", "type": "MoveState", "intents": [{"type": "SingleAttackIntent", "damage": 5.0, "repeats": 1}], "next": "HIT_MOVE",
            "effects": [{"command": "DamageCmd.Attack", "arguments": ["Damage"], "amount": 5}],
        }]}]}
        after = step(replace(combat, damage_received_this_turn=19, enemies=(Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),)), END_TURN, attack_data, random.Random(0))
        self.assertEqual(after.player_hp, 79)

    def test_belt_buckle_grants_dexterity_when_potion_slots_are_empty(self) -> None:
        combat = Combat(80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_BELT_BUCKLE,))
        after = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "DexterityPower"), 2)

    def test_bellows_upgrades_only_the_initial_hand(self) -> None:
        combat = Combat(80, (STRIKE,), (DEFEND,), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_BELLOWS,))
        combat = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.upgraded_cards, (STRIKE,))

    def test_reptile_trinket_power_adds_damage_until_turn_end(self) -> None:
        combat = Combat(80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_REPTILE_TRINKET,), player_powers=(("ReptileTrinketPower", 3),))
        after = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 41)
        next_turn = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(next_turn.player_powers, "ReptileTrinketPower"), 0)

    def test_lizard_tail_prevents_lethal_damage_and_self_forming_clay_stacks(self) -> None:
        attack_data = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
            "id": "HIT_MOVE", "type": "MoveState", "intents": [{"type": "SingleAttackIntent", "damage": 100.0, "repeats": 1}], "next": "HIT_MOVE",
            "effects": [{"command": "DamageCmd.Attack", "arguments": ["Damage"], "amount": 100}],
        }]}]}
        tail = step(Combat(20, (), (), (), (Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),), player_relics=(RELIC_LIZARD_TAIL,)), END_TURN, attack_data, random.Random(0))
        self.assertEqual(tail.player_hp, 40)
        clay = step(Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),), player_relics=(RELIC_SELF_FORMING_CLAY,)), END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(clay.player_block, 3)

    def test_pen_nib_doubles_tenth_attack(self) -> None:
        combat = Combat(80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_PEN_NIB,), attacks_played_combat=9)
        after = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 38)

    def test_vambrace_doubles_first_block_card(self) -> None:
        combat = Combat(80, (DEFEND,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_VAMBRACE,))
        self.assertEqual(step(combat, DEFEND, DUMMY_DATA, random.Random(0)).player_block, 10)

    def test_ruined_helmet_doubles_first_received_strength(self) -> None:
        data = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
            "id": "BUFF_MOVE", "type": "MoveState", "intents": [], "next": "BUFF_MOVE",
            "effects": [{"command": "PowerCmd.Apply", "target": "targets", "model": "StrengthPower", "amount": 2}],
        }]}]}
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "BUFF_MOVE", ()),), player_relics=(RELIC_RUINED_HELMET,))
        after = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 4)

    def test_nunchaku_grants_energy_on_the_tenth_attack_of_the_combat(self) -> None:
        # ANGER costs 0 energy, so the Nunchaku energy gain isn't masked by the card's own cost.
        combat = Combat(80, (ANGER,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_NUNCHAKU,), attacks_played_combat=9)
        after = step(combat, "Anger@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.attacks_played_combat, after.energy), (10, 4))

    def test_kusarigama_deals_bonus_damage_on_the_third_attack(self) -> None:
        combat = Combat(80, (STRIKE, STRIKE, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_KUSARIGAMA,))
        for _ in range(3):
            combat = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(combat.enemies[0].hp, 50 - 6 * 3 - 6)

    def test_candelabra_grants_energy_entering_turn_two_only(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_CANDELABRA,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.turn, after.energy), (2, 5))
        after2 = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after2.turn, after2.energy), (3, 3))

    def test_captains_wheel_grants_block_entering_turn_three(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_CAPTAINS_WHEEL,), turn=2)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.turn, after.player_block), (3, 18))

    def test_art_of_war_grants_energy_if_no_attack_played_last_turn(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_ART_OF_WAR,), turn=2, attacks_played_this_turn=0)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 4)

    def test_art_of_war_withholds_energy_if_an_attack_was_played_last_turn(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_ART_OF_WAR,), turn=2, attacks_played_this_turn=1)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 3)

    def test_brimstone_buffs_strength_for_player_and_enemies_every_turn(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_BRIMSTONE,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 2)
        self.assertEqual(_power(after.enemies[0].powers, "StrengthPower"), 1)

    def test_mercury_hourglass_damages_all_enemies_every_turn(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_MERCURY_HOURGLASS,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 47)

    def test_screaming_flagon_damages_all_enemies_when_hand_is_empty(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_SCREAMING_FLAGON,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 30)

    def test_screaming_flagon_does_not_trigger_with_cards_in_hand(self) -> None:
        combat = Combat(80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_SCREAMING_FLAGON,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 50)

    def test_cloak_clasp_blocks_the_incoming_attack_with_cards_in_hand(self) -> None:
        combat = Combat(80, (STRIKE, DEFEND, BASH), (), (), (Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),), player_relics=(RELIC_CLOAK_CLASP,))
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        # 3 cards in hand -> 3 block against a 10-damage hit, so only 7 gets through.
        self.assertEqual(after.player_hp, 73)

    def test_demon_tongue_heals_once_on_the_first_hit_of_the_turn(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),), player_relics=(RELIC_DEMON_TONGUE,))
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        # Takes 10 unblocked damage, then heals the same amount back: net HP unchanged. The
        # once-per-turn flag itself is expected back at False - BeforeSideTurnStart clears it
        # for the new turn step() has just transitioned into.
        self.assertEqual(after.player_hp, 80)
        self.assertFalse(after.damaged_this_turn)

    def test_centennial_puzzle_draws_three_once_per_combat(self) -> None:
        combat = Combat(80, (), (DEFEND,) * 10, (), (Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),), player_relics=(RELIC_CENTENNIAL_PUZZLE,))
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        # 5 normal end-of-turn cards + 3 from Centennial Puzzle.
        self.assertEqual(len(after.hand), 8)
        self.assertTrue(after.centennial_puzzle_used)

    def test_constrict_power_damages_the_player_at_their_own_turn_end(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_powers=(("ConstrictPower", 6),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 74)

    def test_constrict_power_damage_is_blocked_by_existing_block(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_block=4, player_powers=(("ConstrictPower", 6),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 78)

    def test_slow_power_ramps_damage_with_cards_played_this_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("SlowPower", 1),))
        combat = Combat(80, (DEFEND, DEFEND, CINDER), (), (), (enemy,), energy=5)
        combat = step(combat, DEFEND, {}, random.Random(0))
        combat = step(combat, DEFEND, {}, random.Random(0))
        # Two cards already played this turn: 18 base damage * (10 + 2) / 10 = 21.
        combat = step(combat, "Cinder@0", {}, random.Random(0))
        self.assertEqual(combat.enemies[0].hp, 100 - 21)

    def test_slow_power_does_not_boost_the_first_card_of_the_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("SlowPower", 1),))
        combat = Combat(80, (CINDER,), (), (), (enemy,))
        combat = step(combat, "Cinder@0", {}, random.Random(0))
        self.assertEqual(combat.enemies[0].hp, 100 - 18)

    def test_attack_intent_without_effects_list_still_deals_damage(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "HIT_MOVE", ()),))
        after = step(combat, END_TURN, EFFECTLESS_ATTACK_DUMMY_DATA, random.Random(0))
        # MultiAttackIntent damage=5 repeats=2, with no effects list to drive the generic loop.
        self.assertEqual(after.player_hp, 70)

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

    def test_enemy_attack_forecast_includes_player_damage_modifiers(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "HIT_MOVE", (), powers=(("BackAttackLeftPower", 1),))
        self.assertEqual(
            _enemy_attack_damage(enemy, ATTACKING_DUMMY_DATA, (("VulnerablePower", 1),)),
            15,
        )
        self.assertEqual(
            _enemy_attack_damage(
                enemy,
                ATTACKING_DUMMY_DATA,
                (("SurroundedRight", 1), ("TaintedPower", 2)),
            ),
            18,
        )

    def test_step_score_rewards_reducing_next_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "HIT_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,))
        weakened = replace(combat, enemies=(replace(enemy, powers=(("WeakPower", 1),)),))
        self.assertGreater(_step_score(combat, weakened, ATTACKING_DUMMY_DATA), 0)

    def test_step_score_discounts_partial_minion_damage(self) -> None:
        primary = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        minion = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", (), primary=False)
        combat = Combat(80, (), (), (), (primary, minion))
        primary_hit = replace(combat, enemies=(replace(primary, hp=30), minion))
        minion_hit = replace(combat, enemies=(primary, replace(minion, hp=30)))
        self.assertGreater(
            _step_score(combat, primary_hit, DUMMY_DATA),
            _step_score(combat, minion_hit, DUMMY_DATA),
        )

    def test_step_score_prioritizes_primary_over_partial_minion_damage(self) -> None:
        primary = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        idle_minion = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", (), primary=False)
        combat = Combat(80, (), (), (), (primary, idle_minion))
        primary_hit = replace(combat, enemies=(replace(primary, hp=30), idle_minion))
        idle_minion_hit = replace(combat, enemies=(primary, replace(idle_minion, hp=30)))
        self.assertGreater(_step_score(combat, primary_hit, DUMMY_DATA), _step_score(combat, idle_minion_hit, DUMMY_DATA))
        attacking_minion = replace(idle_minion, move="HIT_MOVE")
        attacking_combat = replace(combat, enemies=(primary, attacking_minion))
        attacking_primary_hit = replace(attacking_combat, enemies=(replace(primary, hp=30), attacking_minion))
        attacking_minion_hit = replace(attacking_combat, enemies=(primary, replace(attacking_minion, hp=30)))
        self.assertGreater(_step_score(attacking_combat, attacking_primary_hit, ATTACKING_DUMMY_DATA), _step_score(attacking_combat, attacking_minion_hit, ATTACKING_DUMMY_DATA))

    def test_step_score_still_prioritizes_a_lethal_high_threat_minion(self) -> None:
        primary = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        minion = Enemy("MONSTER.DUMMY", 10, "HIT_MOVE", (), primary=False)
        combat = Combat(80, (), (), (), (primary, minion))
        primary_hit = replace(combat, enemies=(replace(primary, hp=30), minion))
        minion_kill = replace(combat, enemies=(primary, replace(minion, hp=0)))
        self.assertGreater(
            _step_score(combat, minion_kill, ATTACKING_DUMMY_DATA),
            _step_score(combat, primary_hit, ATTACKING_DUMMY_DATA),
        )

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

    def test_ovicopter_summons_three_eggs_and_resolves_can_lay(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(data, "ENCOUNTER.OVICOPTER_NORMAL", rng)
        combat = step(combat, END_TURN, data, rng)
        self.assertEqual(sum(enemy.model == "MONSTER.TOUGH_EGG" for enemy in combat.enemies), 3)
        combat = step(combat, END_TURN, data, rng)
        eggs = [enemy for enemy in combat.enemies if enemy.model == "MONSTER.TOUGH_EGG"]
        self.assertTrue(all(19 <= enemy.hp <= 22 for enemy in eggs))
        combat = step(combat, END_TURN, data, rng)
        ovicopter = next(enemy for enemy in combat.enemies if enemy.model == "MONSTER.OVICOPTER")
        self.assertEqual(ovicopter.move, "NUTRITIONAL_PASTE_MOVE")

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

    def test_test_subject_revives_twice_before_combat_can_end(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        spec = next(monster for monster in data["monsters"] if monster["id"] == TEST_SUBJECT)
        values = tuple(sorted(spec["values"].items()))
        first = Enemy(TEST_SUBJECT, 1, "BITE_MOVE", values, powers=(("AdaptablePower", 1), ("EnragePower", 2)))
        combat = step(Combat(80, (STRIKE,), (), (), (first,)), f"{STRIKE}@0", data, random.Random(0))
        self.assertEqual(combat.enemies[0].move, "RESPAWN_MOVE")
        self.assertFalse(combat.terminal)
        combat = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual((combat.enemies[0].hp, combat.enemies[0].respawns), (200, 1))
        second = replace(combat.enemies[0], hp=1)
        combat = step(replace(combat, enemies=(second,), hand=(STRIKE,)), f"{STRIKE}@0", data, random.Random(0))
        combat = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual((combat.enemies[0].hp, combat.enemies[0].respawns), (300, 2))
        self.assertFalse(combat.terminal)

    def test_test_subject_enrage_strengthens_on_every_skill(self) -> None:
        enemy = Enemy(TEST_SUBJECT, 100, "BITE_MOVE", (), powers=(("EnragePower", 2),))
        combat = step(Combat(80, (DEFEND,), (), (), (enemy,)), DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.enemies[0].powers, "StrengthPower"), 2)

    def test_test_subject_painful_stabs_adds_wounds_for_unblocked_hits(self) -> None:
        data = {"monsters": [{"id": TEST_SUBJECT, "states": [{
            "id": "HIT_MOVE", "type": "MoveState", "intents": [{"type": "SingleAttackIntent", "damage": 4.0, "repeats": 1}],
            "next": "HIT_MOVE", "effects": [{"command": "DamageCmd.Attack"}],
        }]}]}
        enemy = Enemy(TEST_SUBJECT, 100, "HIT_MOVE", (), powers=(("PainfulStabsPower", 1),))
        combat = step(Combat(80, (), (), (), (enemy,)), END_TURN, data, random.Random(0))
        self.assertEqual(combat.hand, (WOUND,))

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

    def test_mangle_reduces_strength_for_one_enemy_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", (), powers=(("StrengthPower", 2),))
        combat = step(Combat(80, (MANGLE,), (), (), (enemy,), energy=3), "Mangle@0", ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.enemies[0].hp, _power(combat.enemies[0].powers, "StrengthPower"), _power(combat.enemies[0].powers, "ManglePower")), (85, -8, 10))
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, _power(after.enemies[0].powers, "StrengthPower"), _power(after.enemies[0].powers, "ManglePower")), (78, 2, 0))

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

    def test_twin_strike_hits_twice_and_upgrade_adds_two_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        normal = step(Combat(80, (TWIN_STRIKE,), (), (), (enemy,), energy=1), f"{TWIN_STRIKE}@0", DUMMY_DATA, random.Random(0))
        upgraded = step(Combat(80, (TWIN_STRIKE,), (), (), (enemy,), energy=1, upgraded_cards=(TWIN_STRIKE,)), f"{TWIN_STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(normal.enemies[0].hp, 90)
        self.assertEqual(upgraded.enemies[0].hp, 86)

    def test_rage_grants_attack_block_until_turn_end(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = step(Combat(80, (RAGE, STRIKE), (), (), (enemy,), energy=1), RAGE, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "RagePower"), 3)
        combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.player_block, combat.enemies[0].hp), (3, 94))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "RagePower"), 0)

    def test_colossus_blocks_and_halves_attacks_from_vulnerable_enemy(self) -> None:
        vulnerable = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", (), powers=(("VulnerablePower", 1),))
        combat = step(Combat(80, (COLOSSUS,), (), (), (vulnerable,), energy=1), COLOSSUS, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.player_block, _power(combat.player_powers, "ColossusPower")), (5, 1))
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, _power(after.player_powers, "ColossusPower")), (80, 0))

    def test_colossus_upgrade_adds_three_block(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        after = step(Combat(80, (COLOSSUS,), (), (), (enemy,), upgraded_cards=(COLOSSUS,)), COLOSSUS, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 8)

    def test_volley_spends_energy_for_random_hits(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        normal = step(Combat(80, (VOLLEY,), (), (), (enemy,), energy=3), VOLLEY, DUMMY_DATA, random.Random(0))
        upgraded = step(Combat(80, (VOLLEY,), (), (), (enemy,), energy=2, upgraded_cards=(VOLLEY,)), VOLLEY, DUMMY_DATA, random.Random(0))
        self.assertEqual((normal.enemies[0].hp, normal.energy, upgraded.enemies[0].hp, upgraded.energy), (70, 0, 72, 0))

    def test_spite_repeats_after_unblocked_damage_and_upgrades_repeat_count(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        untouched = step(Combat(80, (SPITE,), (), (), (enemy,)), f"{SPITE}@0", DUMMY_DATA, random.Random(0))
        damaged = step(Combat(80, (SPITE,), (), (), (enemy,), lost_hp_this_turn=True), f"{SPITE}@0", DUMMY_DATA, random.Random(0))
        upgraded = step(Combat(80, (SPITE,), (), (), (enemy,), lost_hp_this_turn=True, upgraded_cards=(SPITE,)), f"{SPITE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((untouched.enemies[0].hp, damaged.enemies[0].hp, upgraded.enemies[0].hp), (95, 90, 85))

    def test_spite_tracks_player_side_self_damage_and_resets_after_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (BLOODLETTING, SPITE), (), (), (enemy,), energy=1)
        combat = step(combat, BLOODLETTING, DUMMY_DATA, random.Random(0))
        self.assertTrue(combat.lost_hp_this_turn)
        combat = step(combat, f"{SPITE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(combat.enemies[0].hp, 90)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertFalse(after.lost_hp_this_turn)

    def test_spite_ignores_enemy_side_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ())
        combat = Combat(80, (), (SPITE,), (), (enemy,))
        combat = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(combat.player_hp, 70)
        after = step(combat, f"{SPITE}@0", ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 95)

    def test_stomp_hits_all_enemies_and_costs_less_after_attacks(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 40, "MOVE", ()), Enemy("MONSTER.DUMMY", 30, "MOVE", ()))
        combat = Combat(80, (STRIKE, STOMP), (), (), enemies, energy=3)
        combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertIn(f"{STOMP}@0", legal_actions(combat))
        after = step(combat, f"{STOMP}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, after.enemies[0].hp, after.enemies[1].hp), (0, 22, 18))

    def test_upgraded_stomp_deals_fifteen_to_all_enemies(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 40, "MOVE", ()), Enemy("MONSTER.DUMMY", 30, "MOVE", ()))
        after = step(Combat(80, (STOMP,), (), (), enemies, energy=3, upgraded_cards=(STOMP,)), f"{STOMP}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[1].hp), (25, 15))

    def test_mind_blast_damage_scales_with_draw_pile_size(self) -> None:
        after = step(Combat(80, (MIND_BLAST,), STARTING_DECK, (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), f"{MIND_BLAST}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 100 - len(STARTING_DECK))

    def test_body_slam_damage_scales_with_player_block(self) -> None:
        after = step(Combat(80, (BODY_SLAM,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1, player_block=13), f"{BODY_SLAM}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 87)

    def test_headbutt_deals_damage_and_returns_a_discard_card_to_draw(self) -> None:
        after = step(Combat(80, (HEADBUTT,), (), (STRIKE,), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), f"{HEADBUTT}@0", {}, random.Random(1))
        self.assertEqual(after.enemies[0].hp, 91)
        self.assertIn(STRIKE, after.draw_pile)

    def test_uppercut_applies_weak_and_vulnerable(self) -> None:
        after = step(Combat(80, (UPPERCUT,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=2), f"{UPPERCUT}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 87)
        self.assertEqual(dict(after.enemies[0].powers), {"VulnerablePower": 1, "WeakPower": 1})

    def test_upgraded_uppercut_only_increases_debuffs(self) -> None:
        after = step(Combat(80, (UPPERCUT,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=2, upgraded_cards=(UPPERCUT,)), f"{UPPERCUT}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 87)
        self.assertEqual(dict(after.enemies[0].powers), {"VulnerablePower": 2, "WeakPower": 2})

    def test_true_grit_blocks_and_exhausts_a_hand_card(self) -> None:
        after = step(Combat(80, (TRUE_GRIT, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), TRUE_GRIT, {}, random.Random(0))
        self.assertEqual(after.player_block, 7)
        self.assertEqual(after.hand, ())
        self.assertEqual(after.exhaust_pile, (STRIKE,))

    def test_burning_pact_exhausts_and_draws(self) -> None:
        after = step(Combat(80, (BURNING_PACT, STRIKE), (DEFEND, DEFEND), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), BURNING_PACT, {}, random.Random(0))
        self.assertEqual(after.exhaust_pile, (STRIKE,))
        self.assertEqual(len(after.hand), 2)

    def test_fiend_fire_exhausts_the_hand_and_hits_once_per_card(self) -> None:
        after = step(Combat(80, (FIEND_FIRE, STRIKE, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=2), f"{FIEND_FIRE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 86)
        self.assertEqual(after.exhaust_pile, (FIEND_FIRE, STRIKE, STRIKE))

    def test_infernal_blade_generates_a_free_attack_and_exhausts(self) -> None:
        after = step(Combat(80, (INFERNAL_BLADE,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), INFERNAL_BLADE, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.exhaust_pile, (INFERNAL_BLADE,))
        self.assertEqual(after.free_cards, after.hand)
        self.assertEqual(after.energy, 0)
        self.assertTrue(after.hand)

    def test_upgraded_infernal_blade_costs_zero(self) -> None:
        after = step(Combat(80, (INFERNAL_BLADE,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1, upgraded_cards=(INFERNAL_BLADE,)), INFERNAL_BLADE, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 1)

    def test_evil_eye_doubles_block_after_an_exhaust(self) -> None:
        after = step(Combat(80, (EVIL_EYE,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1, exhausted_this_turn=True), EVIL_EYE, {}, random.Random(0))
        self.assertEqual(after.player_block, 16)

    def test_brand_exhausts_a_card_and_gains_strength(self) -> None:
        after = step(Combat(80, (BRAND, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1), BRAND, {}, random.Random(0))
        self.assertEqual((after.player_hp, after.exhaust_pile, _power(after.player_powers, "StrengthPower")), (79, (STRIKE,), 1))

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

    def test_wriggler_wriggle_move_adds_infection_to_discard_pile(self) -> None:
        with open("data/enemies_overgrowth.json", encoding="utf-8-sig") as file:
            data = json.load(file)
        enemy = Enemy("MONSTER.WRIGGLER", 20, "WRIGGLE_MOVE", ())
        combat = step(Combat(80, (), STARTING_DECK, (), (enemy,)), END_TURN, data, random.Random(0))
        self.assertEqual(combat.discard_pile.count(INFECTION), 1)  # CardPileCmd.AddToCombatAndPreview -> PileType.Discard
        self.assertEqual(_power(combat.enemies[0].powers, "StrengthPower"), 2)  # WriggleMove's own StrengthPower buff

    def test_infection_card_deals_damage_only_once_drawn_into_hand_at_turn_end(self) -> None:
        # draw_pile padded with Strikes so the post-end-turn redraw doesn't need to reshuffle the
        # just-discarded Infection straight back into hand, keeping this turn's effect isolated.
        combat = Combat(80, (INFECTION,), (STRIKE,) * 10, (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),))
        combat = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(combat.player_hp, 80 - 3)  # HasTurnEndInHandEffect: 3 flat Unpowered damage
        self.assertEqual(combat.hand.count(INFECTION), 0)  # discarded normally afterward, like any other card

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

    def test_rupture_grants_strength_when_a_self_damage_card_is_played(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (RUPTURE, HEMOKINESIS), (), (), (enemy,))
        combat = step(combat, RUPTURE, {}, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "RupturePower"), 1)
        combat = step(combat, f"{HEMOKINESIS}@0", {}, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "StrengthPower"), 1)

    def test_enlightenment_caps_later_card_costs_at_one(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (ENLIGHTENMENT, PERFECTED_STRIKE), (), (), (enemy,), energy=3)
        combat = step(combat, ENLIGHTENMENT, {}, random.Random(0))
        self.assertTrue(combat.enlightened_this_turn)
        # PERFECTED_STRIKE normally costs 2; capped at 1 after Enlightenment, leaving 2 energy.
        combat = step(combat, f"{PERFECTED_STRIKE}@0", {}, random.Random(0))
        self.assertEqual(combat.energy, 2)

    def test_second_wind_exhausts_non_attacks_for_block(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (SECOND_WIND, DEFEND, SHRUG, STRIKE), (), (), (enemy,))
        after = step(combat, SECOND_WIND, {}, random.Random(0))
        # DEFEND and SHRUG (non-Attack) exhaust for 5 block each; STRIKE (Attack) stays in hand.
        self.assertEqual((after.player_block, after.hand, set(after.exhaust_pile)), (10, (STRIKE,), {SECOND_WIND, DEFEND, SHRUG}))

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

    def test_stone_armor_grants_decaying_end_turn_block(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "HIT_MOVE", ())
        combat = Combat(80, (STONE_ARMOR,), (), (), (enemy,), energy=1)
        combat = step(combat, STONE_ARMOR, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "PlatingPower"), 4)
        combat = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.player_hp, _power(combat.player_powers, "PlatingPower")), (74, 3))
        combat = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.player_hp, _power(combat.player_powers, "PlatingPower")), (67, 2))

    def test_feel_no_pain_blocks_each_exhausted_card(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (FEEL_NO_PAIN, TREMBLE), (), (), (enemy,), energy=2)
        combat = step(combat, FEEL_NO_PAIN, DUMMY_DATA, random.Random(0))
        combat = step(combat, f"{TREMBLE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((_power(combat.player_powers, "FeelNoPainPower"), combat.player_block), (3, 3))

    def test_tremble_applies_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (TREMBLE,), (), (), (enemy,)), f"{TREMBLE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 3),))

    def test_vulnerable_and_weak_decay_after_enemy_side_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", (), powers=(("WeakPower", 2),))
        combat = Combat(
            80, (BASH,), (), (), (enemy,),
            player_powers=(("VulnerablePower", 2), ("WeakPower", 2)), energy=2,
        )
        combat = step(combat, "Bash@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(dict(combat.enemies[0].powers), {"VulnerablePower": 2, "WeakPower": 2})
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(dict(after.enemies[0].powers), {"VulnerablePower": 1, "WeakPower": 1})
        self.assertEqual(dict(after.player_powers), {"VulnerablePower": 1, "WeakPower": 1})

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

    def test_illusion_power_minion_attacks_normally_the_cycle_after_reviving(self) -> None:
        # IllusionPower.AfterDeath (C#) force-sets the dying creature's move to a synthetic
        # "REVIVE_MOVE" built at runtime (SetMoveImmediate) that never appears in the exported
        # state machine JSON. The revival branch above only restored hp, leaving move stuck on
        # that unresolvable id - the very next _enemy_turn() to find this enemy alive again
        # would look it up and raise StopIteration instead of attacking.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.PARAFRIGHT")
        values = tuple(sorted(spec["values"].items()))
        minion = Enemy("MONSTER.PARAFRIGHT", 5, "SLAM_MOVE", values, powers=(("IllusionPower", 1), ("MinionPower", 1)), primary=False)
        boss = Enemy("MONSTER.PARAFRIGHT", 50, "SLAM_MOVE", values)
        combat = step(Combat(80, (ANGER,), (), (), (minion, boss)), f"{ANGER}@0", {}, random.Random(0))
        revived = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual(revived.enemies[0].move, "SLAM_MOVE")
        attacked = step(revived, END_TURN, hive, random.Random(0))
        self.assertLess(attacked.player_hp, revived.player_hp)  # SlamMove actually lands, no crash

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

    def test_search_treats_primary_kill_as_win_without_killing_minions(self) -> None:
        boss = Enemy("MONSTER.DUMMY", 1, "IDLE_MOVE", (), primary=True)
        minion = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", (), primary=False)
        # Keep the played Strike out of the first rollout cycle so killing the boss immediately
        # is the only winning line; the old all-enemies win check preferred hitting the minion.
        combat = Combat(80, (STRIKE,), (DEFEND,) * 10, (DEFEND,) * 10, (boss, minion))
        best, _ = search(combat, DUMMY_DATA, 300, 0)[0]
        self.assertEqual(best, f"{STRIKE}@0")

    def test_search_does_not_count_thorns_suicide_as_win(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 1, "IDLE_MOVE", (), powers=(("ThornsPower", 5),))
        combat = Combat(1, (STRIKE,), (), (), (enemy,))
        values = dict(search(combat, DUMMY_DATA, 300, 0))
        self.assertLess(values[f"{STRIKE}@0"], 0)

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
