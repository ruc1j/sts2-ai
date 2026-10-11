import json
import random
import unittest
from dataclasses import replace

from combat import (
    AGGRESSION, ANGER, ASHEN_STRIKE, BASH, BATTLE_TRANCE, BELIEVE_IN_YOU, BLOODLETTING, BLOOD_WALL, BLUDGEON, BAD_LUCK, BECKON, BODY_SLAM, BOLAS, BRAND, BREAK, BREAKTHROUGH, BULLY, BURNING_PACT, BYRD_SWOOP, CINDER, CRIMSON_MANTLE, DARK_EMBRACE, DAZED, DEFEND,
    CRUELTY, DECAY, CONFLAGRATION, DISMANTLE, DOMINATE, DRUM_OF_BATTLE, HAVOC, NORMALITY, INFERNAL_BLADE_ATTACKS, METAMORPHOSIS, STOKE, STOKE_GENERATION, card_name, VICIOUS, STRATAGEM, EQUILIBRIUM, FEED, FINESSE, FISTICUFFS, FLAME_BARRIER, FRANTIC_ESCAPE, GIANT_ROCK, HELLRAISER, HEMOKINESIS, IMPATIENCE, INFERNO,
    IMPERVIOUS, INFECTION, INFLAME, IRON_WAVE, LIFT, MASTER_OF_STRATEGY, MIND_BLAST, MOLTEN_FIST, NOT_YET, OFFERING, PACTS_END, PERFECTED_STRIKE, PILLAGE, POMMEL_STRIKE,
    ENLIGHTENMENT, ENCHANTMENT_CORRUPTED, ENCHANTMENT_TEZCATARAS_EMBER, EVIL_EYE, EXTERMINATE, FIEND_FIRE, HEADBUTT, INFERNAL_BLADE, MANGLE, PECK, PRIMAL_FORCE, PRODUCTION, RELAX, RELIC_ART_OF_WAR, RELIC_BRIMSTONE, RELIC_CANDELABRA, RELIC_CAPTAINS_WHEEL, RELIC_CENTENNIAL_PUZZLE, RELIC_CLOAK_CLASP, SETUP_STRIKE,
    RELIC_BEATING_REMNANT, RELIC_BELLOWS, RELIC_BRILLIANT_SCARF, RELIC_BELT_BUCKLE, RELIC_DEMON_TONGUE, RELIC_LIZARD_TAIL, RELIC_KUNAI, RELIC_KUSARIGAMA, RELIC_LOST_WISP, RELIC_PAPER_PHROG, RELIC_STRIKE_DUMMY, RELIC_MERCURY_HOURGLASS, RELIC_MR_STRUGGLES, RELIC_NUNCHAKU, RELIC_PEN_NIB, RELIC_PAELS_BLOOD, RELIC_PAELS_FLESH, RELIC_PAELS_TEARS, RELIC_REPTILE_TRINKET, RELIC_RAZOR_TOOTH, RELIC_RUINED_HELMET, RELIC_SELF_FORMING_CLAY, RELIC_SCREAMING_FLAGON, RELIC_TUNGSTEN_ROD, RELIC_UNSETTLING_LAMP, RELIC_VAMBRACE, RELIC_FIDDLE, RELIC_BLOOD_SOAKED_ROSE, RELIC_FORGOTTEN_SOUL, RELIC_TOASTY_MITTENS, RELIC_SHURIKEN, RELIC_STONE_CALENDAR, RELIC_THROWING_AXE, SECRET_WEAPON, COLOSSUS, RAGE, RUPTURE, SECOND_WIND, SHRUG, SLIMED, SPITE, STONE_ARMOR, FEEL_NO_PAIN, STARTING_DECK, STRIKE, VOLLEY,
    SQUASH, STOMP, TAUNT, TEAR_ASUNDER, TEST_SUBJECT, THUNDERCLAP, TORIC_TOUGHNESS, TOXIC, TREMBLE, TRUE_GRIT, TWIN_STRIKE, UPPERCUT, UNRELENTING, WHIRLWIND, WOUND, ARMAMENTS, BARRICADE, PYRE, UNMOVABLE, EXPECT_A_FIGHT, FORGOTTEN_RITUAL, SWORD_BOOMERANG, POTION_BLOCK, POTION_SHIP, POTION_FIRE, POTION_EXPLOSIVE, POTION_SHAPED_ROCK, POTION_STRENGTH, POTION_DEXTERITY, POTION_FYSH, POTION_ENERGY, POTION_BLOOD, POTION_HEART, POTION_BRONZE, POTION_SPEED_POTION, POTION_FLEX_POTION, POTION_SWIFT_POTION, POTION_REGEN_POTION, POTION_FORTIFIER, POTION_WEAK_POTION, POTION_VULNERABLE_POTION, POTION_POTION_OF_BINDING, POTION_LUCKY_TONIC, POTION_CURE_ALL, POTION_SHACKLING_POTION, POTION_CLARITY, POTION_RADIANT_TINCTURE, POTION_DUPLICATOR, POTION_GIGANTIFICATION, POTION_FAIRY_IN_A_BOTTLE, POTION_FOUL_POTION, POTION_SNECKO_OIL, POTION_STABLE_SERUM, PANACHE, ONE_TWO_PUNCH, Card, Combat, END_TURN, Enemy, _greedy_action, _power, initial_combat, legal_actions, search, step,
    _action_card, _after_exhaust, _apply_player_damage, _draw_into_combat, _effective_cost, _enemy_attack_damage, _enemy_turn, _resolve_move, _step_score, _summon,
    FASTEN, DEMON_FORM, NEOWS_FURY, MAD_SCIENCE, CARD_BLOCK, ULTIMATE_STRIKE, RAMPAGE,
    MAUL, THRASH, FIGHT_ME, JUGGERNAUT, PURITY, SALVO, FLASH_OF_STEEL, OMNISLICE, STAMPEDE, CASCADE, DOUBT, REGRET, SHAME, WITHER, APOTHEOSIS, JUGGLING, CARDS_OUTSIDE_THE_CHARACTER_POOL,
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
    def test_saved_pen_nib_counter_overrides_combat_history_and_advances(self) -> None:
        state = Combat(80, (STRIKE, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
                       player_relics=(RELIC_PEN_NIB,), attacks_played_combat=1,
                       relic_counters=((RELIC_PEN_NIB, 9),))
        first = step(state, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(first.enemies[0].hp, 38)
        self.assertEqual(dict(first.relic_counters)[RELIC_PEN_NIB], 0)
        second = step(first, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(second.enemies[0].hp, 32)
        self.assertEqual(dict(second.relic_counters)[RELIC_PEN_NIB], 1)
        self.assertEqual(dict(step(second, END_TURN, DUMMY_DATA, random.Random(0)).relic_counters)[RELIC_PEN_NIB], 1)
        fresh_counter = replace(state, attacks_played_combat=9, relic_counters=((RELIC_PEN_NIB, 0),))
        self.assertEqual(step(fresh_counter, "Strike@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 44)

    def test_saved_relic_counters_are_independent(self) -> None:
        tuning_fork = "RELIC.TUNING_FORK"
        state = Combat(80, (ANGER, DEFEND), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
                       player_relics=(RELIC_PEN_NIB, RELIC_NUNCHAKU, tuning_fork),
                       relic_counters=((RELIC_PEN_NIB, 0), (RELIC_NUNCHAKU, 9), (tuning_fork, 9)))
        attack = step(state, "Anger@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((attack.enemies[0].hp, attack.energy), (44, 4))
        self.assertEqual(dict(attack.relic_counters), {RELIC_PEN_NIB: 1, RELIC_NUNCHAKU: 0, tuning_fork: 9})
        defend = step(attack, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(defend.player_block, 12)
        self.assertEqual(dict(defend.relic_counters), {RELIC_PEN_NIB: 1, RELIC_NUNCHAKU: 0, tuning_fork: 0})

    def test_pen_nib_only_doubles_the_resolution_that_reaches_ten(self) -> None:
        for counter in (8, 9):
            for card, damage in ((STRIKE, 18), (SWORD_BOOMERANG, 27), (VOLLEY, 60),
                                 (THUNDERCLAP, 16 if counter == 8 else 14)):
                with self.subTest(counter=counter, card=card):
                    state = Combat(80, (card,), (), (), (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),),
                                   energy=2, player_relics=(RELIC_PEN_NIB,),
                                   relic_counters=((RELIC_PEN_NIB, counter),), player_powers=(("DuplicationPower", 1),))
                    action = card if card in {SWORD_BOOMERANG, VOLLEY} else f"{card}@0"
                    after = step(state, action, DUMMY_DATA, random.Random(0))
                    self.assertEqual(after.enemies[0].hp, 100 - damage)
                    self.assertEqual(dict(after.relic_counters)[RELIC_PEN_NIB], (counter + 2) % 10)

    def test_enemy_multi_hit_rounds_weak_and_vulnerable_once_per_hit(self) -> None:
        # QUEEN in astra_goal_r2 seq473: (3 + 2) * .75 * 1.5 floors to 5, five times.
        data = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
            "id": "HIT_MOVE", "type": "MoveState", "next": "HIT_MOVE",
            "intents": [{"type": "MultiAttackIntent", "damage": 3, "repeats": 5}],
        }]}]}
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", (),
                      powers=(("StrengthPower", 2), ("WeakPower", 1)))
        state = Combat(30, (), (STRIKE,) * 10, (), (enemy,), player_block=9,
                       player_powers=(("VulnerablePower", 95),))
        self.assertEqual(_enemy_attack_damage(enemy, data, state.player_powers), 25)
        after = step(state, END_TURN, data, random.Random(0))
        self.assertEqual(after.player_hp, 14)

    def test_negative_enemy_strength_cannot_add_block_during_a_hit(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", (), powers=(("StrengthPower", -12),))
        state = Combat(30, (), (), (), (enemy,))
        after = _enemy_turn(state, 0, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block), (30, 0))

    def test_regen_resolves_before_enemy_attacks_and_respects_hp_cap(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ())
        for hp, expected in ((8, 3), (79, 70)):
            with self.subTest(hp=hp):
                state = Combat(hp, (), (), (), (enemy,), player_powers=(("RegenPower", 5),))
                after = step(state, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
                self.assertEqual((after.player_hp, _power(after.player_powers, "RegenPower")), (expected, 4))

    def test_fairy_revives_between_hits_and_can_be_consumed_twice(self) -> None:
        data = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
            "id": "HIT_MOVE", "type": "MoveState", "next": "HIT_MOVE",
            "intents": [{"type": "MultiAttackIntent", "damage": 10, "repeats": 4}],
        }]}]}
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ())
        for count, expected in ((1, 0), (2, 24)):
            with self.subTest(potions=count):
                state = Combat(5, (), (), (), (enemy,), player_potions=(POTION_FAIRY_IN_A_BOTTLE,) * count)
                after = step(state, END_TURN, data, random.Random(0))
                self.assertEqual(max(0, after.player_hp), expected)
                self.assertEqual(after.player_potions, ())

    def test_fortifier_adds_twice_existing_block_and_triggers_juggernaut_once(self) -> None:
        state = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),),
                       player_block=9, player_potions=(POTION_FORTIFIER,),
                       player_powers=(("JuggernautPower", 3), ("DexterityPower", 5), ("FrailPower", 1)))
        after = step(state, f"potion:{POTION_FORTIFIER}", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_block, after.enemies[0].hp), (27, 97))

    def test_replay_sources_stack_and_are_all_consumed(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        for relics, plays in (((), 3), ((RELIC_THROWING_AXE,), 4)):
            with self.subTest(plays=plays):
                state = Combat(80, (STRIKE,), (), (), (enemy,), energy=1, player_relics=relics,
                               player_powers=(("DuplicationPower", 1), ("OneTwoPunchPower", 1)))
                after = step(state, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
                self.assertEqual((after.enemies[0].hp, after.energy), (100 - 6 * plays, 0))
                self.assertEqual(after.discard_pile, (STRIKE,))
                self.assertEqual(after.cards_played_this_turn, plays)
                self.assertEqual((_power(after.player_powers, "DuplicationPower"),
                                  _power(after.player_powers, "OneTwoPunchPower")), (0, 0))

    def test_replayed_all_enemy_attack_hits_each_enemy_for_each_resolution(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),) * 2
        state = Combat(80, (BREAKTHROUGH,), (), (), enemies, energy=1,
                       player_powers=(("DuplicationPower", 1), ("OneTwoPunchPower", 1)))
        after = step(state, f"{BREAKTHROUGH}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after.enemies], [73, 73])
        self.assertEqual((after.player_hp, after.energy, after.discard_pile), (77, 0, (BREAKTHROUGH,)))

    def test_replayed_thunderclap_applies_vulnerable_between_resolutions(self) -> None:
        state = Combat(80, (THUNDERCLAP,), (), (), (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),),
                       player_powers=(("DuplicationPower", 1),))
        after = step(state, f"{THUNDERCLAP}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "VulnerablePower")), (90, 2))

    def test_stacked_replay_applies_each_block_grant_but_not_the_next_potion(self) -> None:
        state = Combat(80, (DEFEND,), (), (), (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),),
                       player_relics=(RELIC_THROWING_AXE,), player_powers=(("DuplicationPower", 1),),
                       player_potions=(POTION_BLOCK,))
        after = step(state, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 15)
        after = step(after, f"potion:{POTION_BLOCK}", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 27)

    def test_panache_resets_at_turn_end(self) -> None:
        state = Combat(80, (DEFEND,) * 4, (DEFEND,) * 5, (),
                       (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),), energy=4,
                       player_powers=(("PanachePower", 10),))
        for _ in range(4):
            state = step(state, DEFEND, DUMMY_DATA, random.Random(0))
        state = step(state, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(state.panache_cards_this_turn, 0)
        after = step(state, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.panache_cards_this_turn), (100, 1))

    def test_debuff_potions_consume_artifact_in_application_order(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("ArtifactPower", 1),))
        cases = (
            (POTION_WEAK_POTION, "@0", (0, 0, 0)),
            (POTION_VULNERABLE_POTION, "@0", (0, 0, 0)),
            (POTION_POTION_OF_BINDING, "", (0, 0, 1)),
            (POTION_SHACKLING_POTION, "", (0, 0, 0)),
        )
        for potion, target, expected in cases:
            with self.subTest(potion=potion):
                state = Combat(80, (), (), (), (enemy,), player_potions=(potion,))
                after = step(state, f"potion:{potion}{target}", DUMMY_DATA, random.Random(0))
                powers = after.enemies[0].powers
                self.assertEqual(tuple(_power(powers, name) for name in
                                       ("ArtifactPower", "WeakPower", "VulnerablePower")), expected)
                self.assertEqual(_power(powers, "StrengthPower"), 0)
                self.assertEqual(_power(powers, "ShacklingPotionPower"), 0)

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

    def test_search_returns_safe_action_for_terminal_snapshot(self) -> None:
        combat = Combat(0, (), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),))
        self.assertEqual(search(combat, DUMMY_DATA, simulations=1, seed=0), [(END_TURN, 0.0)])

    def test_barricade_preserves_block_across_turns(self) -> None:
        combat = Combat(80, (BARRICADE,), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),), player_block=12, energy=3)
        after_card = step(combat, BARRICADE, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after_card.player_powers, "BarricadePower"), 1)
        after_turn = step(after_card, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after_turn.player_block, 12)
        self.assertNotIn(BARRICADE, legal_actions(replace(combat, energy=2)))
        self.assertIn(BARRICADE, legal_actions(replace(combat, energy=2, upgraded_cards=(BARRICADE,))))

    def test_blood_wall_trades_two_hp_for_sixteen_block(self) -> None:
        combat = Combat(20, (BLOOD_WALL,), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),), energy=3)
        after = step(combat, BLOOD_WALL, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block, after.energy), (18, 16, 1))
        upgraded = step(replace(combat, upgraded_cards=(BLOOD_WALL,)), BLOOD_WALL, DUMMY_DATA, random.Random(0))
        self.assertEqual((upgraded.player_hp, upgraded.player_block), (18, 20))

    def test_block_potion_is_legal_and_consumed_without_energy(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),), energy=0, player_potions=(POTION_BLOCK,))
        self.assertIn(f"potion:{POTION_BLOCK}", legal_actions(combat))
        after = step(combat, f"potion:{POTION_BLOCK}", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_block, after.energy, after.player_potions), (12, 0, ()))

    def test_damage_potions_target_enemy_and_are_consumed(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_potions=(POTION_FIRE, POTION_SHAPED_ROCK))
        fire = step(combat, f"potion:{POTION_FIRE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((fire.enemies[0].hp, fire.player_potions), (30, (POTION_SHAPED_ROCK,)))
        rock = step(fire, f"potion:{POTION_SHAPED_ROCK}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((rock.enemies[0].hp, rock.player_potions), (15, ()))

    def test_unpowered_potion_ignores_flutter(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", (), powers=(("FlutterPower", 2),))
        combat = Combat(80, (), (), (), (enemy,), player_potions=(POTION_FIRE,))
        after = step(combat, f"potion:{POTION_FIRE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "FlutterPower")), (30, 2))

    def test_last_potion_syncs_belt_buckle_immediately(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),), player_potions=(POTION_BLOCK,), player_relics=(RELIC_BELT_BUCKLE,))
        after = step(combat, f"potion:{POTION_BLOCK}", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_potions, _power(after.player_powers, "DexterityPower"), after.belt_buckle_applied), ((), 2, True))

    def test_dexterity_adds_to_powered_block_before_frail(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (DEFEND,), (), (), (enemy,), energy=1, player_powers=(("DexterityPower", 2),))
        self.assertEqual(step(combat, DEFEND, DUMMY_DATA, random.Random(0)).player_block, 7)
        frail = replace(combat, player_powers=(("DexterityPower", 2), ("FrailPower", 1)))
        self.assertEqual(step(frail, DEFEND, DUMMY_DATA, random.Random(0)).player_block, 5)

    def test_speed_potion_dexterity_expires_at_turn_end(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (DEFEND,), (), (), (enemy,), energy=1, player_powers=(("DexterityPower", 7), ("SpeedPotionPower", 5)))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((_power(after.player_powers, "DexterityPower"), _power(after.player_powers, "SpeedPotionPower")), (2, 0))

    def test_unpowered_block_potion_ignores_dexterity(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,), player_powers=(("DexterityPower", 2),), player_potions=(POTION_BLOCK,))
        self.assertEqual(step(combat, f"potion:{POTION_BLOCK}", DUMMY_DATA, random.Random(0)).player_block, 12)

    def test_belt_buckle_dexterity_applies_to_defend_when_empty(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (DEFEND,), (), (), (enemy,), energy=1, player_relics=(RELIC_BELT_BUCKLE,))
        after = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual((_power(after.player_powers, "DexterityPower"), after.player_block), (2, 7))

    def test_ship_in_a_bottle_grants_block_now_and_next_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,), player_potions=(POTION_SHIP,))
        after_potion = step(combat, f"potion:{POTION_SHIP}", DUMMY_DATA, random.Random(0))
        self.assertEqual((after_potion.player_block, _power(after_potion.player_powers, "BlockNextTurnPower")), (10, 10))
        after_turn = step(after_potion, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_turn.player_block, _power(after_turn.player_powers, "BlockNextTurnPower")), (10, 0))

    def test_explosive_ampoule_hits_all_enemies_unpowered(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()))
        combat = Combat(80, (), (), (), enemies, player_potions=(POTION_EXPLOSIVE,))
        after = step(combat, f"potion:{POTION_EXPLOSIVE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after.enemies], [10, 10])

    def test_fixed_potions_apply_their_observed_player_effects(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        cases = (
            (POTION_STRENGTH, "StrengthPower", 2),
            (POTION_DEXTERITY, "DexterityPower", 2),
            (POTION_FYSH, "StrengthPower", 1),
        )
        for potion, power, amount in cases:
            after = step(Combat(80, (), (), (), (enemy,), player_potions=(potion,)), f"potion:{potion}", DUMMY_DATA, random.Random(0))
            self.assertEqual(_power(after.player_powers, power), amount)
        fysh = step(Combat(80, (), (), (), (enemy,), player_potions=(POTION_FYSH,)), f"potion:{POTION_FYSH}", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(fysh.player_powers, "DexterityPower"), 1)

    def test_energy_blood_heart_and_bronze_potions(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        energy = step(Combat(80, (), (), (), (enemy,), energy=1, player_potions=(POTION_ENERGY,)), f"potion:{POTION_ENERGY}", DUMMY_DATA, random.Random(0))
        self.assertEqual(energy.energy, 3)
        blood = step(Combat(40, (), (), (), (enemy,), player_potions=(POTION_BLOOD,)), f"potion:{POTION_BLOOD}", DUMMY_DATA, random.Random(0))
        self.assertEqual(blood.player_hp, 56)
        heart = step(Combat(80, (), (), (), (enemy,), player_potions=(POTION_HEART,)), f"potion:{POTION_HEART}", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(heart.player_powers, "PlatingPower"), 7)
        bronze = step(Combat(80, (), (), (), (enemy,), player_potions=(POTION_BRONZE,)), f"potion:{POTION_BRONZE}", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(bronze.player_powers, "ThornsPower"), 3)

    def test_liquid_bronze_reflects_powered_enemy_attacks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "HIT_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,), player_potions=(POTION_BRONZE,))
        after_potion = step(combat, f"potion:{POTION_BRONZE}", ATTACKING_DUMMY_DATA, random.Random(0))
        after_turn = step(after_potion, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after_turn.player_hp, after_turn.enemies[0].hp), (70, 17))

    def test_buffer_prevents_one_hp_loss_event(self) -> None:
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),), player_powers=(("BufferPower", 1),))
        after = _apply_player_damage(combat, 5)
        self.assertEqual((after.player_hp, _power(after.player_powers, "BufferPower")), (80, 0))
        self.assertEqual(_apply_player_damage(after, 5).player_hp, 75)
        thorny = Combat(80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", (), powers=(("ThornsPower", 5),)),), player_powers=(("BufferPower", 1),), energy=1)
        reflected = step(thorny, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((reflected.player_hp, _power(reflected.player_powers, "BufferPower")), (80, 0))

    def test_pyre_adds_persistent_energy(self) -> None:
        combat = Combat(80, (PYRE,), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),), energy=3)
        after_card = step(combat, PYRE, DUMMY_DATA, random.Random(0))
        self.assertEqual(after_card.max_energy, 4)
        after_turn = step(after_card, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_turn.max_energy, after_turn.energy), (4, 4))

    def test_aggression_recovers_and_upgrades_a_discarded_attack_next_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (AGGRESSION,), (), (STRIKE, DEFEND), (enemy,), energy=1)
        after_play = step(combat, AGGRESSION, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after_play.player_powers, "AggressionPower"), 1)
        after_turn = step(after_play, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertIn(STRIKE, after_turn.hand)
        self.assertEqual(after_turn.upgraded_cards, (STRIKE,))

    def test_aggression_recovers_only_available_attacks_when_stacked(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (AGGRESSION, AGGRESSION), (), (STRIKE, DEFEND), (enemy,), energy=2)
        after_play = step(combat, AGGRESSION, DUMMY_DATA, random.Random(0))
        after_play = step(after_play, AGGRESSION, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after_play.player_powers, "AggressionPower"), 2)
        after_turn = step(after_play, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after_turn.hand.count(STRIKE), 1)
        self.assertEqual(after_turn.upgraded_cards, (STRIKE,))

    def test_dark_embrace_draws_when_a_card_is_exhausted(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (DARK_EMBRACE, RELAX), (STRIKE,), (), (enemy,), energy=5)
        combat = step(combat, DARK_EMBRACE, DUMMY_DATA, random.Random(0))
        after = step(combat, RELAX, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "DarkEmbracePower"), 1)
        self.assertIn(STRIKE, after.hand)
        self.assertIn(RELAX, after.exhaust_pile)

    def test_crimson_mantle_self_damage_and_unpowered_block(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (CRIMSON_MANTLE,), (), (), (enemy,), energy=1, player_powers=(("DexterityPower", 2),))
        after_play = step(combat, CRIMSON_MANTLE, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_play.player_hp, after_play.player_block, _power(after_play.player_powers, "CrimsonMantlePower")), (80, 0, 8))
        after_turn = step(after_play, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_turn.player_hp, after_turn.player_block, _power(after_turn.player_powers, "CrimsonMantleSelfDamage")), (79, 8, 1))

    def test_crimson_mantle_stacks_and_upgrade_changes_block(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (CRIMSON_MANTLE, CRIMSON_MANTLE), (), (), (enemy,), energy=2, upgraded_cards=(CRIMSON_MANTLE,))
        after_play = step(combat, CRIMSON_MANTLE, DUMMY_DATA, random.Random(0))
        after_play = step(after_play, CRIMSON_MANTLE, DUMMY_DATA, random.Random(0))
        after_turn = step(after_play, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_turn.player_hp, after_turn.player_block, _power(after_turn.player_powers, "CrimsonMantlePower"), _power(after_turn.player_powers, "CrimsonMantleSelfDamage")), (78, 20, 20, 2))

    def test_inferno_reacts_to_player_side_damage_and_hits_all_enemies(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()))
        combat = Combat(80, (INFERNO,), (), (), enemies, energy=1)
        self.assertIn(INFERNO, legal_actions(combat))
        after_play = step(combat, INFERNO, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_play.energy, _power(after_play.player_powers, "InfernoPower"), _power(after_play.player_powers, "InfernoSelfDamage")), (0, 6, 1))
        upgraded = step(replace(combat, upgraded_cards=(INFERNO,)), INFERNO, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(upgraded.player_powers, "InfernoPower"), 9)
        after_turn = step(after_play, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_turn.player_hp, [enemy.hp for enemy in after_turn.enemies]), (79, [94, 94]))

    def test_inferno_reacts_to_thorns_reflection_after_a_card_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("ThornsPower", 5),))
        combat = Combat(80, (INFERNO, STRIKE), (), (), (enemy,), energy=2)
        after_power = step(combat, INFERNO, DUMMY_DATA, random.Random(0))
        after_attack = step(after_power, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after_attack.player_hp, after_attack.enemies[0].hp), (75, 88))

    def test_cruelty_increases_vulnerable_powered_attack_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("VulnerablePower", 1),))
        combat = Combat(80, (CRUELTY, STRIKE), (), (), (enemy,), energy=2)
        self.assertIn(CRUELTY, legal_actions(combat))
        after_power = step(combat, CRUELTY, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after_power.player_powers, "CrueltyPower"), 25)
        after_attack = step(after_power, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after_attack.enemies[0].hp, 90)
        upgraded = step(replace(combat, upgraded_cards=(CRUELTY,)), CRUELTY, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(upgraded.player_powers, "CrueltyPower"), 50)

    def test_forgotten_ritual_gains_energy_only_after_prior_exhaust(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        base = Combat(80, (FORGOTTEN_RITUAL,), (), (), (enemy,), energy=3)
        no_exhaust = step(base, FORGOTTEN_RITUAL, DUMMY_DATA, random.Random(0))
        self.assertEqual((no_exhaust.energy, no_exhaust.exhausted_this_turn, no_exhaust.exhaust_pile), (2, True, (FORGOTTEN_RITUAL,)))
        prior = step(replace(base, exhausted_this_turn=True), FORGOTTEN_RITUAL, DUMMY_DATA, random.Random(0))
        self.assertEqual(prior.energy, 5)
        blocked = step(replace(base, exhausted_this_turn=True, player_powers=(("NoEnergyGainPower", 1),)), FORGOTTEN_RITUAL, DUMMY_DATA, random.Random(0))
        self.assertEqual(blocked.energy, 2)

    def test_hellraiser_autoplays_a_strike_drawn_at_turn_start_for_free(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (HELLRAISER,), (STRIKE,), (), (enemy,), energy=3)
        powered = step(combat, HELLRAISER, DUMMY_DATA, random.Random(0))
        self.assertEqual((_power(powered.player_powers, "HellraiserPower"), powered.energy), (1, 1))
        after_turn = step(powered, END_TURN, DUMMY_DATA, random.Random(0))
        after_turn = step(powered, END_TURN, DUMMY_DATA, random.Random(0))
        # Hellraiser is a CardType.Power card, so playing it sends the card to PileType.None - it is not in
        # the discard to be shuffled back and replayed.  The turn-start draw brings the Strike back, which
        # HellraiserPower plays for free.
        self.assertEqual(
            (after_turn.enemies[0].hp, after_turn.energy, after_turn.hand, HELLRAISER in after_turn.discard_pile or HELLRAISER in after_turn.exhaust_pile or HELLRAISER in after_turn.hand),
            (94, 3, (), False),
        )
        self.assertEqual((after_turn.hellraiser_autoplays_this_turn, after_turn.free_cards), (1, ()))

    def test_stratagem_pulls_cards_from_the_draw_pile_on_every_shuffle(self) -> None:
        # StratagemPower.AfterShuffle fires whenever the player's draw pile is shuffled and is never
        # consumed: the player picks its amount of cards from the draw pile into hand.  The model takes
        # the highest damage-then-block cards, since that is the deck the agent is building toward.
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ())
        combat = Combat(80, (STRATAGEM, BATTLE_TRANCE), (DEFEND,), (BASH, STRIKE, DEFEND, STRIKE, BASH), (enemy,), energy=3)
        played = step(combat, STRATAGEM, DUMMY_DATA, random.Random(0))
        self.assertEqual(
            (_power(played.player_powers, "StratagemPower"), played.hand, played.discard_pile),
            (1, (BATTLE_TRANCE,), (BASH, STRIKE, DEFEND, STRIKE, BASH)),
        )
        # Battle Trance draws 3 and only 1 card is left in the draw pile, so the discard is shuffled in.
        drawn = step(played, BATTLE_TRANCE, DUMMY_DATA, random.Random(0))
        self.assertEqual(len(drawn.hand), 4)
        self.assertIn(BASH, drawn.hand)
        self.assertEqual(_power(drawn.player_powers, "StratagemPower"), 1)

    def test_power_cards_leave_the_combat_when_played(self) -> None:
        # CardModel.GetResultPileTypeForCardPlay returns PileType.None for CardType.Power cards, so a played
        # Power is gone from the combat piles - recorded plays of Inflame (58), Stone Armor (35), Rupture (30)
        # and Crimson Mantle (22) all show exhaust +0 and discard +0.  A spent Power must not come back into
        # the draw cycle and be replayed later in the same fight.
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ())
        combat = Combat(80, (INFLAME,), (DEFEND,), (STRIKE,), (enemy,), energy=3)
        after = step(combat, INFLAME, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.hand, after.discard_pile, after.draw_pile, after.exhaust_pile), ((), (STRIKE,), (DEFEND,), ()))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 2)
        drawn = step(replace(after, hand=()), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertNotIn(INFLAME, drawn.hand + drawn.draw_pile + drawn.discard_pile)

    def test_hellraiser_autoplays_strike_drawn_by_shrug(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (HELLRAISER, SHRUG), (STRIKE,), (), (enemy,), energy=3)
        combat = step(combat, HELLRAISER, DUMMY_DATA, random.Random(0))
        after = step(combat, SHRUG, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.player_block, after.energy, after.hand), (94, 8, 0, ()))

    def test_hellraiser_upgrade_lowers_its_cost(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        base = Combat(80, (HELLRAISER,), (), (), (enemy,), energy=1)
        self.assertNotIn(HELLRAISER, legal_actions(base))
        self.assertIn(HELLRAISER, legal_actions(replace(base, upgraded_cards=(HELLRAISER,))))

    def test_hellraiser_caps_autoplay_at_nine_per_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 1000, "IDLE_MOVE", ())
        combat = Combat(80, (), (STRIKE,) * 12, (), (enemy,), player_powers=(("HellraiserPower", 1),))
        after = _draw_into_combat(combat, 12, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.hellraiser_autoplays_this_turn, after.enemies[0].hp, after.hand.count(STRIKE)), (9, 946, 3))

    def test_sword_boomerang_retargets_each_hit(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()))
        combat = Combat(80, (SWORD_BOOMERANG,), (), (), enemies, energy=1)
        self.assertIn(SWORD_BOOMERANG, legal_actions(combat))
        self.assertNotIn(f"{SWORD_BOOMERANG}@0", legal_actions(combat))
        after = step(combat, SWORD_BOOMERANG, DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after.enemies], [97, 94])
        upgraded = step(replace(combat, upgraded_cards=(SWORD_BOOMERANG,)), SWORD_BOOMERANG, DUMMY_DATA, random.Random(0))
        self.assertEqual(sum(100 - enemy.hp for enemy in upgraded.enemies), 12)

    def test_armaments_blocks_and_upgrades_hand(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(80, (ARMAMENTS, STRIKE, DEFEND), (), (), (enemy,), energy=1)
        self.assertEqual(legal_actions(combat)[:2], (f"{ARMAMENTS}@0", f"{ARMAMENTS}@1"))
        after_card = step(combat, f"{ARMAMENTS}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after_card.player_block, 5)
        self.assertEqual(after_card.upgraded_cards, (STRIKE,))
        upgraded = replace(combat, upgraded_cards=(ARMAMENTS,))
        after_upgraded = step(upgraded, ARMAMENTS, DUMMY_DATA, random.Random(0))
        self.assertEqual(after_upgraded.player_block, 5)
        self.assertEqual(after_upgraded.upgraded_cards, (ARMAMENTS, STRIKE, DEFEND))

    def test_apotheosis_upgrades_every_upgradable_copy_in_every_pile(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())
        combat = Combat(
            80,
            (Card(APOTHEOSIS, upgraded=True), Card(BASH)),
            (Card(DEFEND), Card(TOXIC)),
            (STRIKE,),
            (enemy,),
            energy=3,
        )
        self.assertEqual(_effective_cost(combat, Card(APOTHEOSIS)), 2)
        self.assertEqual(_effective_cost(combat, Card(APOTHEOSIS, upgraded=True)), 1)
        self.assertIn("card:0", legal_actions(combat))
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        # Exhaust keyword fires, and the played copy is never its own upgrade target.
        self.assertEqual(after.exhaust_pile, (Card(APOTHEOSIS, upgraded=True),))
        upgraded = {
            card_name(value)
            for pile in (after.hand, after.draw_pile, after.discard_pile)
            for value in pile
            if getattr(value, "upgraded", False)
        }
        # TOXIC sits in the draw pile but overrides MaxUpgradeLevel 0, so Apotheosis skips it.
        self.assertEqual(upgraded, {BASH, DEFEND})
        # A legacy name-string copy is remembered through upgraded_cards.
        self.assertEqual(after.upgraded_cards, (STRIKE,))
        # The upgrade is visible to the rest of the fight: BASH is 8 + 2 upgraded.
        played = step(after, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(played.enemies[0].hp, 20 - 10)

    def test_juggling_power_clones_the_third_attack_played_in_a_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(
            80,
            (Card(JUGGLING), Card(STRIKE), Card(STRIKE), Card(STRIKE)),
            (),
            (),
            (enemy,),
            energy=5,
        )
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "JugglingPower"), 1)
        first = step(after, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(first.attacks_played_this_turn, 1)
        self.assertEqual(len(first.hand), 2)
        second = step(first, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(second.attacks_played_this_turn, 2)
        self.assertEqual(len(second.hand), 1)
        third = step(second, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(third.attacks_played_this_turn, 3)
        # The third Attack puts a clone of itself into hand.
        self.assertEqual([card_name(value) for value in third.hand], [STRIKE])
        # The counter is per-turn: the next turn starts clean.
        ended = step(third, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(ended.attacks_played_this_turn, 0)

    def test_ritual_power_stacks_strength_at_enemy_turn_end_after_its_apply_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", (), powers=(("RitualPower", 2), ("RitualPendingPower", 1)))
        combat = Combat(80, (), (), (), (enemy,), energy=3)
        applied = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        # AfterApplied flags an enemy owner once: the turn end right after the cast adds nothing.
        self.assertEqual((_power(applied.enemies[0].powers, "RitualPendingPower"), _power(applied.enemies[0].powers, "StrengthPower")), (0, 0))
        later = step(applied, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(later.enemies[0].powers, "StrengthPower"), 2)

    def test_high_voltage_power_stacks_strength_every_enemy_turn_end(self) -> None:
        # Zapbot applies HighVoltagePower at combat start, so this only arrives through the
        # observation's powers, which is why POWER_NAMES needed the mapping.
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", (), powers=(("HighVoltagePower", 1),))
        combat = Combat(80, (), (), (), (enemy,), energy=3)
        first = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(first.enemies[0].powers, "StrengthPower"), 1)
        second = step(first, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(second.enemies[0].powers, "StrengthPower"), 2)

    def test_curious_power_discounts_the_players_power_cards(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ())
        combat = Combat(80, (DEMON_FORM,), (), (), (enemy,), energy=1, player_powers=(("CuriousPower", 2),))
        # Demon Form is 3; Mad Science's CuriousPower stack of 2 makes it 1, so at 1 energy it is
        # playable - without the discount the rollout never sees it as legal.
        self.assertIn(DEMON_FORM, legal_actions(combat))
        after = step(combat, DEMON_FORM, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 0)
        self.assertEqual(_power(after.player_powers, "DemonFormPower"), 2)

    def test_imbalanced_stuns_the_attacker_after_a_fully_blocked_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "HIT_MOVE", (), powers=(("ImbalancedPower", 1),))
        combat = Combat(30, (), (), (), (enemy,), player_block=10)
        blocked = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(blocked.player_hp, 30)
        self.assertEqual(_power(blocked.enemies[0].powers, "StunnedPower"), 1)
        skipped = step(blocked, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(skipped.player_hp, 30)
        resumed = step(skipped, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(resumed.player_hp, 20)

    def test_card_instances_keep_individual_upgrades_across_piles(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(
            80,
            (Card(STRIKE), Card(STRIKE, upgraded=True), Card(DEFEND), Card(DEFEND, upgraded=True)),
            (),
            (),
            (enemy,),
            energy=4,
        )
        actions = legal_actions(combat)
        self.assertIn("card:0@0", actions)
        self.assertIn("card:1@0", actions)
        self.assertIn("card:2", actions)
        self.assertIn("card:3", actions)
        self.assertNotIn(f"{STRIKE}@0", actions)
        self.assertEqual(step(combat, "card:0@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 94)
        self.assertEqual(step(combat, "card:1@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 91)
        self.assertEqual(step(combat, "card:2", DUMMY_DATA, random.Random(0)).player_block, 5)
        self.assertEqual(step(combat, "card:3", DUMMY_DATA, random.Random(0)).player_block, 8)

        armaments = Combat(80, (Card(ARMAMENTS), Card(STRIKE), Card(STRIKE)), (), (), (enemy,), energy=1)
        self.assertIn("card:0@0", legal_actions(armaments))
        upgraded = step(armaments, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(upgraded.hand, (Card(STRIKE, upgraded=True), Card(STRIKE)))
        next_turn = step(upgraded, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(next_turn.hand.count(Card(STRIKE, upgraded=True)), 1)
        self.assertEqual(next_turn.hand.count(Card(STRIKE)), 1)

    def test_tezcataras_ember_is_per_card_and_persists_through_redraw(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        enchanted = Card(STRIKE, enchantment=ENCHANTMENT_TEZCATARAS_EMBER)
        combat = Combat(80, (enchanted, Card(STRIKE)), (), (), (enemy,), energy=0)
        self.assertEqual(legal_actions(combat), ("card:0@0", END_TURN))

        after = step(combat, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 91)
        self.assertEqual(after.discard_pile, (enchanted,))
        redrawn = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertIn(enchanted, redrawn.hand)

        upgraded = Card(STRIKE, upgraded=True, enchantment=ENCHANTMENT_TEZCATARAS_EMBER)
        upgraded_after = step(
            Combat(80, (upgraded,), (), (), (enemy,), energy=0),
            "card:0@0", DUMMY_DATA, random.Random(0),
        )
        self.assertEqual(upgraded_after.enemies[0].hp, 88)
        self.assertEqual(upgraded_after.discard_pile, (upgraded,))

    def test_corrupted_enchantment_increases_damage_and_hurts_player(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 30, "IDLE_MOVE", ())
        corrupted = Card(STRIKE, enchantment=ENCHANTMENT_CORRUPTED)
        after = step(Combat(20, (corrupted,), (), (), (enemy,), energy=1), "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.player_hp), (21, 18))

    def test_upgraded_defend_and_shrug_match_card_values(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        for name, expected_block in ((DEFEND, 8), (SHRUG, 11)):
            with self.subTest(card=name):
                card = Card(name, upgraded=True)
                combat = Combat(80, (card,), (), (), (enemy,), energy=1)
                after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
                self.assertEqual(after.player_block, expected_block)

    def test_razor_tooth_upgrades_played_card_before_fiend_fire_exhausts_hand(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(
            80, (Card(FIEND_FIRE), Card(STRIKE)), (), (), (enemy,), energy=2,
            player_relics=(RELIC_RAZOR_TOOTH,),
        )
        after = step(combat, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.exhaust_pile, (Card(FIEND_FIRE, upgraded=True), Card(STRIKE)))

    def test_peck_has_three_hits_and_four_when_upgraded(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        base = Combat(80, (PECK,), (), (), (enemy,), energy=1)
        upgraded = replace(base, upgraded_cards=(PECK,))
        self.assertEqual(step(base, "Peck@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 94)
        self.assertEqual(step(upgraded, "Peck@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 92)

    def test_conflagration_hits_all_enemies_four_times_and_upgrades_hits(self) -> None:
        # Decompiled (v0.107.1): Conflagration is a 1-energy AllEnemies attack with DamageVar(2) and
        # RepeatVar(4); the upgrade adds a repeat, not damage.  It was missing from the model, so a
        # deck holding it left the card invisible to legal_actions and search (astra hands showed it
        # with the decision falling through to the heuristic tail).
        enemies = (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY2", 100, "IDLE_MOVE", ()))
        combat = Combat(80, (CONFLAGRATION,), (), (), enemies, energy=1)
        upgraded = replace(combat, upgraded_cards=(CONFLAGRATION,))
        self.assertEqual([enemy.hp for enemy in step(combat, "Conflagration@0", DUMMY_DATA, random.Random(0)).enemies], [92, 92])
        self.assertEqual([enemy.hp for enemy in step(upgraded, "Conflagration@0", DUMMY_DATA, random.Random(0)).enemies], [90, 90])

    def test_exterminate_hits_all_enemies_four_times_and_upgrades_damage(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY2", 100, "IDLE_MOVE", ()))
        combat = Combat(80, (EXTERMINATE,), (), (), enemies, energy=1)
        upgraded = replace(combat, upgraded_cards=(EXTERMINATE,))
        self.assertEqual([enemy.hp for enemy in step(combat, "Exterminate@0", DUMMY_DATA, random.Random(0)).enemies], [88, 88])
        self.assertEqual([enemy.hp for enemy in step(upgraded, "Exterminate@0", DUMMY_DATA, random.Random(0)).enemies], [84, 84])

    def test_exterminate_respects_hard_to_kill_per_hit(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("HardToKillPower", 9),))
        combat = Combat(80, (EXTERMINATE,), (), (), (enemy,), energy=1, player_powers=(("StrengthPower", 10),))
        self.assertEqual(step(combat, "Exterminate@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 64)

    def test_setup_strike_buffs_followup_attacks_for_one_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (SETUP_STRIKE, STRIKE), (), (), (enemy,), energy=2)
        after_setup = step(combat, "Setup Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after_setup.enemies[0].hp, _power(after_setup.player_powers, "StrengthPower"), _power(after_setup.player_powers, "SetupStrikePower")), (93, 2, 2))
        after_strike = step(after_setup, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after_strike.enemies[0].hp, 85)
        after_turn = step(after_strike, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((_power(after_turn.player_powers, "StrengthPower"), _power(after_turn.player_powers, "SetupStrikePower")), (0, 0))

    def test_upgraded_setup_strike_gains_three_strength_and_two_extra_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (SETUP_STRIKE,), (), (), (enemy,), energy=1, upgraded_cards=(SETUP_STRIKE,))
        after = step(combat, "Setup Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.player_powers, "StrengthPower"), _power(after.player_powers, "SetupStrikePower")), (91, 3, 3))

    def test_upgrade_damage_matches_each_cards_own_upgrade_value_by(self) -> None:
        # Every pair below is (card, base damage, upgraded damage) read off the decompiled card body:
        # DynamicVars.Damage base value and DynamicVars.Damage.UpgradeValueBy.  Before this table was
        # filled in, most of these cards were getting combat.py's flat +3 upgrade fallback, which is
        # wrong in both directions (Bludgeon gained 7 too little, Bolas 2 too much).
        verified = (
            (BLUDGEON, 32, 42), (BREAK, 20, 30), (ULTIMATE_STRIKE, 14, 20), (UNRELENTING, 14, 20),
            (HEMOKINESIS, 15, 20), (GIANT_ROCK, 16, 20), (MOLTEN_FIST, 10, 14),
            (NEOWS_FURY, 10, 14), (BYRD_SWOOP, 14, 18), (BREAKTHROUGH, 9, 13), (IRON_WAVE, 5, 7),
            (ANGER, 6, 8), (FEED, 10, 12), (FISTICUFFS, 7, 9), (DISMANTLE, 8, 10), (BOLAS, 3, 4),
            # Volley and Peck are excluded: their total damage is energy- or hit-count driven.
            # Rampage's upgrade raises the Strength it gains per attack played, not its damage.
            (RAMPAGE, 9, 9),
        )
        for card, base, upgraded in verified:
            for wanted, was_upgraded in ((base, False), (upgraded, True)):
                enemy = Enemy("MONSTER.DUMMY", 300, "IDLE_MOVE", ())
                combat = Combat(
                    80, (card, DEFEND, DEFEND), (), (), (enemy,), energy=4,
                    upgraded_cards=(card,) if was_upgraded else (),
                )
                action = next(
                    (candidate for candidate in legal_actions(combat)
                     if card_name(_action_card(combat, candidate)) == card_name(card)),
                    f"{card_name(card)}@0",
                )
                after = step(combat, action, DUMMY_DATA, random.Random(0))
                self.assertEqual(
                    300 - after.enemies[0].hp, wanted,
                    f"{card_name(card)}{' upgraded' if was_upgraded else ''} should deal {wanted}",
                )

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

    def test_pen_nib_does_not_double_before_the_counter_has_been_counted(self) -> None:
        # The observation carries relic ids but no counters, so a rebuilt decision state always has
        # attacks_played_combat = 0.  `0 % 10 == 0` read that as "activated" and doubled the first
        # attack of every combat (the same guard now protects the Nunchaku rule).
        combat = Combat(80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), energy=1,
            player_relics=(RELIC_PEN_NIB,))
        after = step(combat, "Strike@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 44)

    def test_vambrace_doubles_first_block_card(self) -> None:
        combat = Combat(80, (DEFEND,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), player_relics=(RELIC_VAMBRACE,))
        self.assertEqual(step(combat, DEFEND, DUMMY_DATA, random.Random(0)).player_block, 10)

    def test_a_duplicate_play_sees_the_vulnerable_its_earlier_resolution_applied(self) -> None:
        # Bash deals damage and applies VulnerablePower inside the same OnPlay resolution, so when the play
        # resolves twice (Throwing Axe) the second hit is amplified.  The recorded game shows exactly this:
        # data/counts_arm_D6A1F8C3E5_agent.jsonl seq 298 took 25 from an upgraded Bash (10 then 10 x 3/2).
        combat = Combat(
            80, (Card(BASH, True),), (), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ()),),
            player_relics=(RELIC_THROWING_AXE,),
        )
        after = step(combat, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(60 - after.enemies[0].hp, 25)
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 6)  # 3 per resolution.

        # Uppercut applies WeakPower and VulnerablePower after its DamageCmd (UpperCut.cs), so the same
        # ordering gives 13 then 13 x 3/2 = 19 for 32 total - seq 314 of the same trace.
        combat = Combat(
            80, (UPPERCUT,), (), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ()),),
            player_relics=(RELIC_THROWING_AXE,),
        )
        after = step(combat, f"{UPPERCUT}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(60 - after.enemies[0].hp, 32)
        self.assertEqual(
            sorted((name, amount) for name, amount in after.enemies[0].powers),
            [("VulnerablePower", 2), ("WeakPower", 2)],
        )

    def test_secret_weapon_pulls_an_attack_from_the_draw_pile_and_exhausts(self) -> None:
        # SecretWeapon.OnPlay selects one CardType.Attack from the draw pile and adds it to hand, and the
        # base card carries CardKeyword.Exhaust while OnUpgrade removes the keyword.  The model takes the
        # strongest Attack in the draw pile, since the real choice is made by the player.
        combat = Combat(
            80, (SECRET_WEAPON, STRIKE), (IRON_WAVE, DEFEND), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ()),),
        )
        after = step(combat, SECRET_WEAPON, DUMMY_DATA, random.Random(0))
        self.assertEqual([card_name(value) for value in after.hand], [STRIKE, IRON_WAVE])
        self.assertEqual([card_name(value) for value in after.draw_pile], [DEFEND])
        self.assertEqual([card_name(value) for value in after.exhaust_pile], [SECRET_WEAPON])
        self.assertEqual(after.discard_pile, ())

        upgraded = Combat(
            80, (Card(SECRET_WEAPON, True),), (BASH,), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ()),),
        )
        played = step(upgraded, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual([card_name(value) for value in played.hand], [BASH])
        self.assertEqual(played.draw_pile, ())
        self.assertEqual(played.exhaust_pile, ())
        self.assertEqual([card_name(value) for value in played.discard_pile], [SECRET_WEAPON])

    def test_throwing_axe_adds_one_play_to_the_first_card_of_each_combat(self) -> None:
        # ThrowingAxe.ModifyCardPlayCount returns playCount + 1 for our own card until
        # AfterModifyingCardPlayCount consumes it, and AfterRoomEntered(CombatRoom) re-arms it.  So the
        # first card of every combat is played twice and the rest of that combat plays normally.
        combat = Combat(
            80, (STRIKE, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            player_relics=(RELIC_THROWING_AXE,),
        )
        first = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(first.enemies[0].hp, 38)  # 50 - 6 - 6: the play happens twice.
        self.assertEqual(first.cards_played_combat, 2)
        second = step(first, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(second.enemies[0].hp, 32)  # the relic is spent, so this play is single.
        fresh = Combat(
            80, (STRIKE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            player_relics=(RELIC_THROWING_AXE,),
        )
        self.assertEqual(step(fresh, f"{STRIKE}@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 38)  # re-armed in a new combat.

    def test_unmovable_doubles_only_the_first_block_card_each_turn(self) -> None:
        combat = Combat(
            80, (DEFEND, SHRUG), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            player_powers=(("UnmovablePower", 1),), energy=3,
        )
        first = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        second = step(first, SHRUG, DUMMY_DATA, random.Random(0))
        self.assertEqual((first.player_block, first.block_cards_this_turn), (10, 1))
        self.assertEqual((second.player_block, second.block_cards_this_turn), (18, 2))
        next_turn = step(second, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(next_turn.block_cards_this_turn, 0)

    def test_unmovable_stacks_multiplicatively_with_vambrace(self) -> None:
        combat = Combat(
            80, (DEFEND,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            player_powers=(("UnmovablePower", 1),), player_relics=(RELIC_VAMBRACE,),
        )
        after = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 20)

    def test_unmovable_counts_block_cards_played_before_power(self) -> None:
        combat = Combat(
            80, (DEFEND, UNMOVABLE, DEFEND), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            energy=4, max_energy=4,
        )
        after_first_defend = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        after_power = step(after_first_defend, UNMOVABLE, DUMMY_DATA, random.Random(0))
        after_second_defend = step(after_power, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual((after_power.player_block, after_power.block_cards_this_turn), (5, 1))
        self.assertEqual((after_second_defend.player_block, after_second_defend.block_cards_this_turn), (10, 2))

    def test_unmovable_doubles_evil_eye_grants_once_per_card_play(self) -> None:
        combat = Combat(
            80, (TREMBLE, EVIL_EYE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            player_powers=(("UnmovablePower", 1),), energy=2,
        )
        after_tremble = step(combat, f"{TREMBLE}@0", DUMMY_DATA, random.Random(0))
        after_evil_eye = step(after_tremble, EVIL_EYE, DUMMY_DATA, random.Random(0))
        self.assertEqual(after_evil_eye.player_block, 32)
        self.assertEqual(after_evil_eye.block_cards_this_turn, 1)

    def test_unmovable_card_costs_one_when_upgraded_and_grants_power(self) -> None:
        combat = Combat(80, (UNMOVABLE,), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),), energy=1, upgraded_cards=(UNMOVABLE,))
        self.assertIn(UNMOVABLE, legal_actions(combat))
        after = step(combat, UNMOVABLE, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "UnmovablePower"), 1)

    def test_expect_a_fight_gains_energy_for_attacks_in_hand(self) -> None:
        combat = Combat(
            80, (EXPECT_A_FIGHT, STRIKE, ANGER, DEFEND), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            energy=2,
        )
        after = step(combat, EXPECT_A_FIGHT, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 2)
        self.assertEqual(_power(after.player_powers, "NoEnergyGainPower"), 1)

    def test_expect_a_fight_is_one_cost_upgraded(self) -> None:
        combat = Combat(
            80, (EXPECT_A_FIGHT, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            energy=1, upgraded_cards=(EXPECT_A_FIGHT,),
        )
        self.assertIn(EXPECT_A_FIGHT, legal_actions(combat))
        after = step(combat, EXPECT_A_FIGHT, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 1)

    def test_expect_a_fight_blocks_later_energy_gain_until_turn_end(self) -> None:
        combat = Combat(
            80, (EXPECT_A_FIGHT, BLOODLETTING, STRIKE), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            energy=2,
        )
        after_expect = step(combat, EXPECT_A_FIGHT, DUMMY_DATA, random.Random(0))
        after_bloodletting = step(after_expect, BLOODLETTING, DUMMY_DATA, random.Random(0))
        self.assertEqual(after_bloodletting.energy, 1)
        after_turn = step(after_bloodletting, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after_turn.player_powers, "NoEnergyGainPower"), 0)

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

    def test_the_debuff_and_economy_potions_apply_the_game_side_effects(self) -> None:
        # 393 recorded potion plays used one of these six and the simulator had no model for any of them,
        # so the rollout could not price the option the agent was holding.  Each branch is the single
        # command the decompiled potion model runs in OnUse, and every one of those 393 plays carries
        # target_id None, so all six are listed as untargeted.
        idle = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ())
        plain = Combat(50, (), (), (), (idle,), energy=1)
        for potion in (POTION_POTION_OF_BINDING, POTION_LUCKY_TONIC, POTION_CURE_ALL, POTION_SHACKLING_POTION, POTION_CLARITY, POTION_RADIANT_TINCTURE):
            self.assertIn(f"potion:{potion}", legal_actions(replace(plain, player_potions=(potion,))))
        rng = random.Random(0)
        tonic = step(replace(plain, player_potions=(POTION_LUCKY_TONIC,)), f"potion:{POTION_LUCKY_TONIC}", DUMMY_DATA, rng)
        self.assertEqual(_power(tonic.player_powers, "BufferPower"), 1)
        cured = step(replace(plain, player_potions=(POTION_CURE_ALL,), draw_pile=(DEFEND, DEFEND, DEFEND)), f"potion:{POTION_CURE_ALL}", DUMMY_DATA, rng)
        self.assertEqual((cured.energy, len(cured.hand)), (2, 2))
        clarified = step(replace(plain, player_potions=(POTION_CLARITY,), draw_pile=(DEFEND, DEFEND, DEFEND)), f"potion:{POTION_CLARITY}", DUMMY_DATA, rng)
        self.assertEqual((len(clarified.hand), _power(clarified.player_powers, "ClarityPower")), (1, 3))
        radiant = step(replace(plain, player_potions=(POTION_RADIANT_TINCTURE,)), f"potion:{POTION_RADIANT_TINCTURE}", DUMMY_DATA, rng)
        self.assertEqual((radiant.energy, _power(radiant.player_powers, "RadiancePower")), (2, 3))

        attacker = Enemy("MONSTER.DUMMY", 60, "HIT_MOVE", ())
        facing = Combat(50, (), (), (), (attacker,), energy=1)
        bound = step(replace(facing, player_potions=(POTION_POTION_OF_BINDING,)), f"potion:{POTION_POTION_OF_BINDING}", ATTACKING_DUMMY_DATA, rng)
        self.assertEqual((_power(bound.enemies[0].powers, "WeakPower"), _power(bound.enemies[0].powers, "VulnerablePower")), (1, 1))
        # After a Shackling play the observations read SHACKLING_POTION_POWER 7 next to STRENGTH_POWER -7
        # on every enemy (61 of 61 enemy observations), and TemporaryStrengthPower.AfterSideTurnEnd puts
        # the Strength back once that creature's own turn ends, so it blunts exactly one enemy turn.
        shackled = step(replace(facing, player_potions=(POTION_SHACKLING_POTION,)), f"potion:{POTION_SHACKLING_POTION}", ATTACKING_DUMMY_DATA, rng)
        self.assertEqual((_power(shackled.enemies[0].powers, "ShacklingPotionPower"), _power(shackled.enemies[0].powers, "StrengthPower")), (7, -7))
        resolved = step(shackled, END_TURN, ATTACKING_DUMMY_DATA, rng)
        self.assertEqual((_power(resolved.enemies[0].powers, "ShacklingPotionPower"), _power(resolved.enemies[0].powers, "StrengthPower")), (0, 0))
        self.assertEqual(resolved.player_hp, 47)  # the 10 damage attack landed as 10 - 7

    def test_gigantification_potion_uses_the_id_the_game_reports(self) -> None:
        # The game's model class is GigantificationPotion, so the observation says
        # POTION.GIGANTIFICATION_POTION.  The constant used to be POTION.GIGANTIFICATION, which matched
        # nothing: 1,838 observations of a carried Gigantification potion were invisible to the rollout,
        # and its 22 recorded plays all carry target_id None (TargetType.AnyPlayer), so it belongs in the
        # untargeted list rather than the enemy-targeted one.
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ())
        combat = Combat(60, (), (), (), (enemy,), player_potions=(POTION_GIGANTIFICATION,))
        actions = legal_actions(combat)
        self.assertIn("potion:POTION.GIGANTIFICATION_POTION", actions)
        self.assertNotIn("potion:POTION.GIGANTIFICATION_POTION@0", actions)
        after = step(combat, "potion:POTION.GIGANTIFICATION_POTION", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "GigantificationPower"), 1)

    def test_the_colorless_potions_the_shops_sell_are_simulatable(self) -> None:
        # 1,738 of the 3,274 potion plays recorded in real runs used a potion the simulator had no model
        # for, so the rollout could not price the option the agent was actually holding.  Each effect here
        # is the single command the decompiled potion model runs in OnUse.
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ())
        combat = Combat(60, (), (), (), (enemy,), player_potions=(POTION_SPEED_POTION, POTION_FLEX_POTION, POTION_SWIFT_POTION, POTION_REGEN_POTION, POTION_FORTIFIER, POTION_WEAK_POTION))
        self.assertIn("potion:POTION.SPEED_POTION", legal_actions(replace(combat, player_potions=(POTION_SPEED_POTION,))))
        self.assertIn("potion:POTION.FORTIFIER", legal_actions(replace(combat, player_potions=(POTION_FORTIFIER,))))
        self.assertIn("potion:POTION.WEAK_POTION@0", legal_actions(replace(combat, player_potions=(POTION_WEAK_POTION,))))
        self.assertIn("potion:POTION.VULNERABLE_POTION@0", legal_actions(replace(combat, player_potions=(POTION_VULNERABLE_POTION,))))
        data = DUMMY_DATA
        rng = random.Random(0)
        speed = step(replace(combat, player_potions=(POTION_SPEED_POTION,)), "potion:POTION.SPEED_POTION", data, rng)
        self.assertEqual((_power(speed.player_powers, "SpeedPotionPower"), _power(speed.player_powers, "DexterityPower")), (5, 5))
        flex = step(replace(combat, player_potions=(POTION_FLEX_POTION,)), "potion:POTION.FLEX_POTION", data, rng)
        self.assertEqual((_power(flex.player_powers, "FlexPotionPower"), _power(flex.player_powers, "StrengthPower")), (5, 5))
        swift = step(replace(combat, player_potions=(POTION_SWIFT_POTION,), draw_pile=(DEFEND, DEFEND, DEFEND, DEFEND)), "potion:POTION.SWIFT_POTION", data, rng)
        self.assertEqual(len(swift.hand), 3)
        regen = step(replace(combat, player_potions=(POTION_REGEN_POTION,)), "potion:POTION.REGEN_POTION", data, rng)
        self.assertEqual(_power(regen.player_powers, "RegenPower"), 5)
        fortified = step(replace(combat, player_potions=(POTION_FORTIFIER,), player_block=9), "potion:POTION.FORTIFIER", data, rng)
        self.assertEqual(fortified.player_block, 27)
        weak = step(replace(combat, player_potions=(POTION_WEAK_POTION,)), "potion:POTION.WEAK_POTION@0", data, rng)
        self.assertEqual(_power(weak.enemies[0].powers, "WeakPower"), 3)
        vulnerable = step(replace(combat, player_potions=(POTION_VULNERABLE_POTION,)), "potion:POTION.VULNERABLE_POTION@0", data, rng)
        self.assertEqual(_power(vulnerable.enemies[0].powers, "VulnerablePower"), 3)

    def test_slow_ramp_rounds_once_with_the_other_damage_multipliers(self) -> None:
        # WeakPower (3/4), VulnerablePower (150/100) and SlowPower (1 + 0.1 * SlowAmount) are
        # ModifyDamageMultiplicative hooks: the game multiplies the factors together and truncates the
        # result once.  Rounding each step on its own loses points.  An upgraded Strike (9) played at Weak
        # against a Vulnerable, Slow holder, with the Slow ramp at 1.2 (cards_played_this_turn counts the
        # play resolving right now, so the ramp reads 2 earlier cards), is 9 x 3/4 x 1.5 x 1.2 = 12.15
        # -> 12.  Truncating between the factors gave 9 x 3 // 4 = 6, then 6 x 150 // 100 = 9, then
        # 9 x 12 // 10 = 10 - two points lost on one hit.
        slow = Enemy("MONSTER.BYGONE_EFFIGY", 60, "IDLE_MOVE", (), powers=(("SlowPower", 1), ("VulnerablePower", 1)))
        state = Combat(60, (Card("Strike", upgraded=True),), (), (), (slow,), energy=2,
                       player_powers=(("WeakPower", 1),), cards_played_this_turn=2)
        after = step(state, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(60 - after.enemies[0].hp, 12)

    def test_fairy_in_a_bottle_prevents_death_and_heals_thirty_percent(self) -> None:
        # FairyInABottle is PotionUsage.Automatic: CreatureCmd.Kill zeroes the HP, Hook.ShouldDie lets the
        # potion prevent the death, and AfterPreventingDeath heals Math.Max(MaxHp * 0.3m, 1m).  The agent
        # is never offered it as an action, so this is the only place the model can know about it.
        attacker = Enemy("MONSTER.DUMMY", 60, "HIT_MOVE", ())
        state = Combat(5, (), (), (), (attacker,), player_max_hp=80, energy=0,
                       player_potions=(POTION_FAIRY_IN_A_BOTTLE,))
        saved = step(state, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(saved.player_hp, 24)
        self.assertEqual(saved.player_potions, ())
        doomed = step(replace(state, player_potions=()), END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertLessEqual(doomed.player_hp, 0)

    def test_foul_potion_hits_every_creature_in_the_combat_including_the_player(self) -> None:
        # FoulPotion damages CombatState.Creatures (pets excluded), so the owner takes its own 12.
        state = Combat(50, (), (), (), (Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ()),
                                        Enemy("MONSTER.DUMMY", 20, "IDLE_MOVE", ())),
                       energy=0, player_potions=(POTION_FOUL_POTION,))
        after = step(state, f"potion:{POTION_FOUL_POTION}", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 38)
        self.assertEqual([enemy.hp for enemy in after.enemies], [8, 8])

    def test_stable_serum_retains_the_hand_for_two_turns(self) -> None:
        # StableSerum.OnUse: Apply<RetainHandPower>(RepeatVar 2).
        state = Combat(50, (), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),),
                       energy=0, player_potions=(POTION_STABLE_SERUM,))
        after = step(state, f"potion:{POTION_STABLE_SERUM}", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "RetainHandPower"), 2)

    def test_snecko_oil_draws_seven_cards(self) -> None:
        # SneckoOil.OnUse: CardPileCmd.Draw(CardsVar 7).  Its energy-cost randomization is not modeled.
        state = Combat(50, (DEFEND,), (STRIKE,) * 8, (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),),
                       energy=0, player_potions=(POTION_SNECKO_OIL,))
        after = step(state, f"potion:{POTION_SNECKO_OIL}", DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), 8)

    def test_feed_raises_max_hp_and_heals_when_it_kills_the_target(self) -> None:
        # Feed.cs is a Fatal Attack: on a kill it calls CreatureCmd.GainMaxHp(Owner, MaxHp), MaxHpVar(3)
        # (upgraded 4), which raises max HP and current HP together.  The recorded game went hp 54 -> 57
        # with max_hp 80 -> 83 on such a kill, and the rollout scored the same play 3 HP worse.
        victim = Enemy("MONSTER.SHRINKER_BEETLE", 9, "IDLE_MOVE", ())
        state = Combat(54, (Card("Feed"),), (), (), (victim,), energy=2)
        killed = step(state, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertFalse(killed.enemies[0].alive)
        self.assertEqual((killed.player_hp, killed.player_max_hp), (57, 83))
        survivor = Enemy("MONSTER.SHRINKER_BEETLE", 40, "IDLE_MOVE", ())
        missed = step(Combat(54, (Card("Feed"),), (), (), (survivor,), energy=2), "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((missed.player_hp, missed.player_max_hp), (54, 80))

    def test_shuriken_strength_counts_from_the_attack_after_the_third(self) -> None:
        # ShurikenRelic grants its Strength in AfterCardPlayed, so the attack that reaches the 3rd attack
        # of the turn still deals its own damage and the next attack is the one that carries +1.  The
        # model used to fold the bonus into the triggering play, which priced that attack 1 higher than
        # the game did (72 recorded plays in the corpus replay once the turn's attack count became visible).
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        seeded = Combat(
            80, (Card("Strike"), Card("Strike")), (), (), (enemy,), energy=3,
            player_relics=(RELIC_SHURIKEN,), attacks_played_this_turn=2,
        )
        third = step(seeded, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(100 - third.enemies[0].hp, 6)
        self.assertEqual(_power(third.player_powers, "StrengthPower"), 1)
        fourth = step(third, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(third.enemies[0].hp - fourth.enemies[0].hp, 7)

    def test_weak_and_vulnerable_multiply_attack_damage_before_the_rounding(self) -> None:
        # ModifyDamageMultiplicative hooks return decimal factors, and the game multiplies them together
        # before it rounds the damage.  Truncating between Weak (3/4) and Vulnerable (1.5) loses points:
        # an upgraded Strike (9) played by a Weak player onto a Vulnerable boss is 9 * 0.75 * 1.5 =
        # 10.125 -> 10 in the game, where the chained model gave 9 * 3 // 4 = 6 then 6 * 150 // 100 = 9.
        # QUEEN fights are where this showed up - they hold Weak 97-99 for the whole fight - and the
        # boss-fight audit had CARD.STRIKE_IRONCLAD off by 1 in 69 cases and CARD.ANGER in 65.
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", (), powers=(("VulnerablePower", 1),))
        combat = Combat(80, (Card("Strike", True),), (), (), (enemy,), energy=1, player_powers=(("WeakPower", 99),))
        after = step(combat, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 50)
        # Weak alone still rounds once, and Vulnerable alone is unchanged.
        only_weak = step(Combat(80, (Card("Strike", True),), (), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ()),), energy=1, player_powers=(("WeakPower", 99),)), "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(only_weak.enemies[0].hp, 54)  # 9 * 3 / 4 = 6.75 -> 6
        only_vuln = step(Combat(80, (Card("Strike", True),), (), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", (), powers=(("VulnerablePower", 1),)),), energy=1), "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(only_vuln.enemies[0].hp, 47)  # 9 * 3 / 2 = 13.5 -> 13

    def test_toasty_mittens_exhaust_runs_the_exhaust_relics(self) -> None:
        # ToastyMittens exhausts the top card of the draw pile at the start of every turn, and that
        # Exhaust goes through the same recurring hooks as a card's own Exhaust.  The QUEEN fights in real
        # runs carry ToastyMittens and ForgottenSoul together, and ForgottenSoul.AfterCardExhausted deals
        # 1 unpowered damage to one random hittable enemy per Exhaust - which is why the boss lost exactly
        # 1 HP on every turn there (act3_verify_head_H2LV6ZJ4XW seq 555/561/577; 177 of 188 QUEEN end-turn
        # replays were off by exactly 1 before this hook was wired).
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ())
        combat = Combat(60, (), (STRIKE, DEFEND), (), (enemy,), player_relics=(RELIC_TOASTY_MITTENS, RELIC_FORGOTTEN_SOUL))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 49)
        self.assertEqual(len(after.exhaust_pile), 1)
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 1)

    def test_burrowed_enemy_keeps_its_block_across_turns(self) -> None:
        # Hook.ShouldClearBlock asks every ShouldClearBlock override, and BurrowedPower (like BlurPower)
        # returns false for its owner: the burrowed Tunneler's remaining block is not wiped at its turn
        # boundary.  act3_pop2_R8V2H6N4ZB seq 207 shows 20 block -> 2 block across one burrowed turn.
        burrowed = Enemy("MONSTER.DUMMY", 54, "IDLE_MOVE", (), block=20, powers=(("BurrowedPower", 1),))
        after = step(Combat(60, (), (), (), (burrowed,)), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].block, 20)
        plain = Enemy("MONSTER.DUMMY", 54, "IDLE_MOVE", (), block=20)
        after = step(Combat(60, (), (), (), (plain,)), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].block, 0)

    def test_flame_barrier_reflects_once_per_hit_of_a_multi_hit_attack(self) -> None:
        # FlameBarrierPower.AfterDamageReceived fires on every damage instance, not once per attack:
        # `await CreatureCmd.Damage(dealer, Amount, Unpowered)` inside the hook.  The recorded
        # HUNTER_KILLER fight (act3_pop2_T4K8M2W7QY seq 260) is the measurement - PUNCTURE_MOVE 7x3 was
        # fully blocked by 22 block against FlameBarrier 4 + Thorns 3, and the Hunter Killer went
        # 62 -> 41 HP, i.e. 4*3 + 3*3 = 21, where the once-per-attack model scored 4 + 9 = 13.
        enemy = Enemy("MONSTER.DUMMY", 60, "HIT_MOVE", ())
        combat = Combat(50, (), (), (), (enemy,), player_powers=(("FlameBarrierPower", 4), ("ThornsPower", 3)))
        after = step(combat, END_TURN, EFFECTLESS_ATTACK_DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 60 - (4 + 3) * 2)  # a 5x2 attack reflects 2 Flame Barrier hits
        self.assertEqual(after.player_hp, 40)  # 5 damage per hit, no block

    def test_crimson_mantle_damages_itself_at_turn_start_from_the_observed_counter_alone(self) -> None:
        # CrimsonMantlePower stores SelfDamage in a DynamicVar, so the game exports only
        # POWER.CRIMSON_MANTLE_POWER (8,300 observations; the counters are 8, 10 and 18).  A rollout state
        # rebuilt from such an observation has no self-damage marker and used to skip the 1 Unblockable
        # damage every turn start, which showed up as the game being exactly 1 HP lower each turn in
        # VANTOM (335 cases), QUEEN (238) and THE_INSATIABLE (199) end-turn replays.
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ())
        combat = Combat(60, (), (), (), (enemy,), player_powers=(("CrimsonMantlePower", 8),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block), (59, 8))
        upgraded = step(Combat(60, (), (), (), (enemy,), player_powers=(("CrimsonMantlePower", 10),)), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((upgraded.player_hp, upgraded.player_block), (59, 10))
        two_plays = step(Combat(60, (), (), (), (enemy,), player_powers=(("CrimsonMantlePower", 18),)), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((two_plays.player_hp, two_plays.player_block), (58, 18))

    def test_player_regen_heals_at_the_end_of_the_turn_and_decrements_by_one(self) -> None:
        # RegenPower.AfterSideTurnEnd heals its owner by Amount and then decrements by 1 (recorded runs
        # show a held Regen of 5, 4, 3, 2, 1 on consecutive turns).  The enemy side was already modeled;
        # the player side was missing, which left 206 of 811 recorded end-of-turns unexplained by the model.
        enemy = Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ())
        combat = Combat(40, (), (), (), (enemy,), player_powers=(("RegenPower", 3),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, _power(after.player_powers, "RegenPower")), (43, 2))
        capped = step(Combat(79, (), (), (), (enemy,), player_powers=(("RegenPower", 3),)), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(capped.player_hp, 80)  # player_max_hp, which the enemy side also respects

    def test_mr_struggles_ticks_the_new_turn_number_into_every_enemy(self) -> None:
        # MrStruggles.AfterPlayerTurnStart deals TurnNumber damage to every hittable enemy at the start
        # of each player turn (turn 2 -> 2 damage, turn 5 -> 5).  24 recorded runs hold the relic and 548
        # turn boundaries in their traces show exactly that drop; 141 of those had the enemy Vulnerable and
        # the drop was still the plain turn number, because the damage is ValueProp.Unpowered.
        plain = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ())
        vulnerable = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", (), powers=(("VulnerablePower", 1),))
        combat = Combat(80, (), (), (), (plain, vulnerable), turn=1, player_relics=(RELIC_MR_STRUGGLES,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after.enemies], [58, 58])
        after2 = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after2.enemies], [55, 55])  # 3 more on the way into turn 3

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

    def test_paels_blood_draws_one_extra_card_each_turn(self) -> None:
        combat = Combat(
            80, (), (DEFEND,) * 10, (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            player_relics=(RELIC_PAELS_BLOOD,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), 6)

    def test_paels_flesh_adds_energy_from_turn_three(self) -> None:
        combat = Combat(
            80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            turn=2, player_relics=(RELIC_PAELS_FLESH,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.turn, after.energy), (3, 4))

    def test_paels_flesh_does_not_add_energy_again_after_turn_three(self) -> None:
        combat = Combat(
            80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            turn=3, max_energy=4, player_relics=(RELIC_PAELS_FLESH,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.turn, after.energy, after.max_energy), (4, 4, 4))

    def test_paels_flesh_stays_at_observed_max_energy_on_later_turns(self) -> None:
        combat = Combat(
            80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            turn=5, max_energy=4, player_relics=(RELIC_PAELS_FLESH,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.turn, after.energy, after.max_energy), (6, 4, 4))

    def test_paels_tears_refunds_unused_energy_on_next_turn(self) -> None:
        combat = Combat(
            80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            energy=1, player_relics=(RELIC_PAELS_TEARS,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, after.paels_tears_pending), (5, False))

    def test_paels_tears_does_not_refund_when_energy_is_empty(self) -> None:
        combat = Combat(
            80, (), (), (), (Enemy("MONSTER.DUMMY", 50, "IDLE_MOVE", ()),),
            energy=0, player_relics=(RELIC_PAELS_TEARS,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 3)

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

    def test_juggernaut_damages_an_enemy_when_block_is_gained(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "MOVE", ())
        combat = Combat(80, (DEFEND,), (), (), (enemy,), player_powers=(("JuggernautPower", 6),))
        after = step(combat, DEFEND, {}, random.Random(0))
        self.assertEqual((after.player_block, after.enemies[0].hp), (5, 14))

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

    def test_enemy_attack_forecast_is_zero_when_the_move_has_no_attack_intent(self) -> None:
        # SALIVATE_MOVE applies StrengthPower only: the game displays damage 0 for it and
        # `_enemy_turn` applies nothing, so Strength must not be carried into this turn's forecast.
        buff_only_data = {
            "monsters": [
                {
                    "id": "MONSTER.DUMMY",
                    "values": {},
                    "states": [{"id": "SALIVATE_MOVE", "intents": [{"type": "BuffIntent"}]}],
                }
            ]
        }
        enemy = Enemy("MONSTER.DUMMY", 40, "SALIVATE_MOVE", (), powers=(("StrengthPower", 2),))
        self.assertEqual(_enemy_attack_damage(enemy, buff_only_data, (("TaintedPower", 1),)), 0)

    def test_enemy_attack_forecast_uses_the_forgotten_dexterity_formula(self) -> None:
        # TheForgotten.DreadDamage => 13 + own DexterityPower, and the exported JSON has no damage
        # value for that state because the value is a lambda. The monster steals 2 Dexterity from
        # the player per Miasma turn, so the game's intent display reads 15 then 17.
        forgotten_data = {
            "monsters": [
                {
                    "id": "MONSTER.THE_FORGOTTEN",
                    "values": {},
                    "states": [{"id": "DREAD", "intents": [{"type": "SingleAttackIntent", "repeats": 1}]}],
                }
            ]
        }
        enemy = Enemy("MONSTER.THE_FORGOTTEN", 111, "DREAD", (), powers=(("DexterityPower", 2),))
        self.assertEqual(_enemy_attack_damage(enemy, forgotten_data, ()), 15)
        enemy = Enemy("MONSTER.THE_FORGOTTEN", 111, "DREAD", (), powers=(("DexterityPower", 4),))
        self.assertEqual(_enemy_attack_damage(enemy, forgotten_data, ()), 17)

    def test_the_forgotten_dread_actually_damages_through_the_enemy_turn(self) -> None:
        # `_enemy_turn` used to raise KeyError on the missing damage key, so a TheForgotten fight
        # never ran through the simulator and every decision fell to the heuristic tail.
        forgotten_data = {
            "monsters": [
                {
                    "id": "MONSTER.THE_FORGOTTEN",
                    "values": {},
                    "initial_state": "DREAD",
                    "states": [
                        {
                            "id": "DREAD",
                            "type": "MoveState",
                            "next": "DREAD",
                            "intents": [{"type": "SingleAttackIntent", "repeats": 1}],
                        }
                    ],
                }
            ]
        }
        enemy = Enemy("MONSTER.THE_FORGOTTEN", 111, "DREAD", (), powers=(("DexterityPower", 2),))
        combat = Combat(60, (), (), (), (enemy,), energy=0)
        after = step(combat, END_TURN, forgotten_data, random.Random(0))
        self.assertEqual(after.player_hp, 45)
        # Miasma steals 2 Dexterity from the player and hands it to the monster, so the next DREAD
        # reads 17 as the stack grows (the game's own intent display shows the same numbers).
        growth = {"monsters": [{"id": "MONSTER.THE_FORGOTTEN", "values": {"DebilitatingSmogDexStealAmount": 2},
                                "initial_state": "MIASMA",
                                "states": [
                                    {"id": "MIASMA", "type": "MoveState", "next": "DREAD",
                                     "intents": [{"type": "DebuffIntent"}],
                                     "effects": [{"command": "PowerCmd.Apply", "model": "DexterityPower",
                                                  "target": "targets", "amount": "-DebilitatingSmogDexStealAmount"},
                                                 {"command": "PowerCmd.Apply", "model": "DexterityPower",
                                                  "target": "base.Creature", "amount": "DebilitatingSmogDexStealAmount"}]},
                                    {"id": "DREAD", "type": "MoveState", "next": "MIASMA",
                                     "intents": [{"type": "SingleAttackIntent", "repeats": 1}], "effects": []},
                                ]}]}
        fight = Combat(70, (), (), (), (Enemy("MONSTER.THE_FORGOTTEN", 106, "MIASMA", (("DebilitatingSmogDexStealAmount", 2),)),), energy=0)
        first = step(fight, END_TURN, growth, random.Random(0))
        self.assertEqual((first.player_hp, _power(first.enemies[0].powers, "DexterityPower")), (70, 2))
        second = step(first, END_TURN, growth, random.Random(0))
        self.assertEqual((second.player_hp, _power(second.enemies[0].powers, "DexterityPower")), (55, 2))
        third = step(second, END_TURN, growth, random.Random(0))
        self.assertEqual((third.player_hp, _power(third.enemies[0].powers, "DexterityPower")), (55, 4))
        fourth = step(third, END_TURN, growth, random.Random(0))
        self.assertEqual((fourth.player_hp, _power(fourth.enemies[0].powers, "DexterityPower")), (38, 4))

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

    def test_artifact_cancels_one_enemy_debuff_and_is_consumed(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("ArtifactPower", 1),))
        after = step(Combat(80, (TREMBLE, TREMBLE), (), (), (enemy,), energy=2), f"{TREMBLE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, ())
        after = step(after, f"{TREMBLE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 3),))

    def test_artifact_cancels_dominate_strength_chain(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("ArtifactPower", 1), ("VulnerablePower", 2)))
        after = step(Combat(80, (DOMINATE,), (), (), (enemy,)), f"{DOMINATE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 2),))
        self.assertEqual(after.player_powers, ())

    def test_artifact_follows_uppercut_weak_then_vulnerable_order(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("ArtifactPower", 1),))
        after = step(Combat(80, (UPPERCUT,), (), (), (enemy,), energy=2), f"{UPPERCUT}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 1),))

    def test_unsettling_lamp_doubles_uppercut_debuffs_once(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = Combat(80, (UPPERCUT,), (), (), (enemy,), energy=2, player_relics=(RELIC_UNSETTLING_LAMP,))
        after = step(combat, f"{UPPERCUT}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].powers, (("VulnerablePower", 2), ("WeakPower", 2)))
        self.assertTrue(after.unsettling_lamp_used)

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

    def test_soar_halves_powered_attack_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("SoarPower", 1),))
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 37)  # SoarPower halves the powered 6-damage Strike.

    def test_soar_does_not_reduce_unpowered_potion_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("SoarPower", 1),))
        combat = Combat(80, (), (), (), (enemy,), player_potions=(POTION_FIRE,))
        after = step(combat, f"potion:{POTION_FIRE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 20)

    def test_soar_power_normalizes_from_official_id(self) -> None:
        from official_agent import POWER_NAMES

        normalized = POWER_NAMES.get("POWER.SOAR_POWER", "POWER.SOAR_POWER")
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=((normalized, 1),))
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 37)

    def test_slippery_reduces_an_attack_to_one_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "MOVE", (), powers=(("SlipperyPower", 8),))
        combat = Combat(80, (ANGER,), (), (), (enemy,))
        after = step(combat, "Anger@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].powers), (19, (("SlipperyPower", 7),)))

    def test_slippery_does_not_consume_on_fully_blocked_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "MOVE", (), block=6, powers=(("SlipperyPower", 8),))
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].block, after.enemies[0].powers), (20, 0, (("SlipperyPower", 8),)))

    def test_slippery_caps_unpowered_damage_after_block(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 20, "MOVE", (), block=2, powers=(("SlipperyPower", 8),))
        combat = Combat(80, (), (), (), (enemy,), player_potions=(POTION_FIRE,))
        after = step(combat, f"potion:{POTION_FIRE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].block, after.enemies[0].powers), (19, 0, (("SlipperyPower", 7),)))

    def test_slippery_consumes_after_soar_reduced_damage(self) -> None:
        enemy = Enemy(
            "MONSTER.DUMMY", 20, "MOVE", (), block=2,
            powers=(("SlipperyPower", 8), ("SoarPower", 1)),
        )
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].block, after.enemies[0].powers), (19, 0, (("SlipperyPower", 7), ("SoarPower", 1))))

    def test_hard_to_kill_caps_each_hit(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 30, "MOVE", (), powers=(("HardToKillPower", 9),))
        combat = Combat(80, (GIANT_ROCK,), (), (), (enemy,))
        after = step(combat, f"{GIANT_ROCK}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 21)  # 16 damage is capped at 9 per hit

    def test_louse_curl_up_blocks_after_the_whole_attack_card(self) -> None:
        enemy = Enemy("MONSTER.LOUSE_PROGENITOR", 100, "MOVE", (), powers=(("CurlUpPower", 14),))
        combat = Combat(80, (TWIN_STRIKE,), (), (), (enemy,))
        after = step(combat, f"{TWIN_STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.enemies[0].block, after.enemies[0].powers), (90, 14, ()))

    def test_louse_curl_up_normalizes_from_official_id(self) -> None:
        # Regression: CombatBridge reports POWER.CURL_UP_POWER, while combat.py checks the
        # normalized CurlUpPower name when the first attack triggers the curl block.
        from official_agent import POWER_NAMES
        normalized = POWER_NAMES.get("POWER.CURL_UP_POWER", "POWER.CURL_UP_POWER")
        enemy = Enemy("MONSTER.LOUSE_PROGENITOR", 136, "BITE_MOVE", (), powers=((normalized, 14),))
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", self.data, random.Random(0))
        self.assertEqual((after.enemies[0].block, after.enemies[0].powers), (14, ()))

    def test_louse_progenitor_starts_curled(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        combat = initial_combat(hive, "ENCOUNTER.LOUSE_PROGENITOR_NORMAL", random.Random(0))
        louse = combat.enemies[0]
        self.assertEqual(_power(louse.powers, "CurlUpPower"), 14)

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
        self.assertNotIn("MinionPower", dict(combat.player_powers))
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

    def test_pacts_end_hits_every_enemy_only_once_the_exhaust_pile_is_deep_enough(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 100, "MOVE", ()), Enemy("MONSTER.DUMMY", 100, "MOVE", ()))
        base = Combat(80, (PACTS_END,), (), (), enemies, energy=1)
        # CanDealDamage needs three cards already exhausted; with fewer it resolves for nothing.
        after = step(replace(base, exhaust_pile=(STRIKE, STRIKE)), f"{PACTS_END}@0", {}, random.Random(0))
        self.assertTrue(all(enemy.hp == 100 for enemy in after.enemies))
        after = step(replace(base, exhaust_pile=(STRIKE,) * 3), f"{PACTS_END}@0", {}, random.Random(0))
        self.assertTrue(all(enemy.hp == 83 for enemy in after.enemies))

    def test_pommel_strike_deals_damage_and_draws(self) -> None:
        base = Combat(80, (POMMEL_STRIKE,), STARTING_DECK, (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1)
        after = step(base, f"{POMMEL_STRIKE}@0", {}, random.Random(0))
        upgraded = step(replace(base, upgraded_cards=(POMMEL_STRIKE,)), f"{POMMEL_STRIKE}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, len(after.hand)), (91, 1))
        self.assertEqual((upgraded.enemies[0].hp, len(upgraded.hand)), (90, 2))

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

    def test_buffer_power_zeroes_the_next_unblocked_enemy_hit(self) -> None:
        # BufferPower.ModifyHpLostAfterOstyLate runs after block is consumed, so the hit still spends
        # block but its HP loss becomes 0 and the power decrements.  Observed on GEFYYKH1YK seq 150:
        # Byrdonis' 21 against block 10 with BufferPower 1 cost no HP.  A fully blocked hit leaves the
        # buffer standing, because the Late hook only fires when damage actually reached HP.
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ())
        combat = Combat(20, (), (), (), (enemy,), energy=0, player_block=5, player_powers=(("BufferPower", 1),))
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block, _power(after.player_powers, "BufferPower")), (20, 0, 0))

        blocked_only = Combat(20, (), (), (), (enemy,), energy=0, player_block=10, player_powers=(("BufferPower", 1),))
        after = step(blocked_only, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block, _power(after.player_powers, "BufferPower")), (20, 0, 1))

    def test_buffer_power_only_covers_one_hit_of_a_multi_hit_attack(self) -> None:
        data = {"monsters": [{"id": "MONSTER.DUMMY", "states": [{
            "id": "HIT_MOVE", "type": "MoveState", "intents": [{"type": "MultiAttackIntent", "damage": 10.0, "repeats": 2}],
            "next": "HIT_MOVE", "effects": [{"command": "DamageCmd.Attack", "arguments": ["Damage"], "amount": 10}],
        }]}]}
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ())
        combat = Combat(30, (), (), (), (enemy,), energy=0, player_powers=(("BufferPower", 1),))
        after = step(combat, END_TURN, data, random.Random(0))
        self.assertEqual((after.player_hp, _power(after.player_powers, "BufferPower")), (20, 0))

    def test_perfected_strike_counts_pommel_strike_as_a_strike(self) -> None:
        # PommelStrike carries CardTag.Strike (decompiled v0.107.1), so Perfected Strike's multiplier
        # counts it: 6 base + 2 per Strike-tagged card in the combat state = 10 here (was 8 before the
        # tag was added, which is what the panel replay mismatched on).
        perfected = Card(PERFECTED_STRIKE, False)
        pommel = Card(POMMEL_STRIKE, False)
        combat = Combat(80, (perfected,), (pommel,), (), (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),), energy=3)
        self.assertEqual(step(combat, "card:0@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 90)

    def test_upgraded_ashen_strike_scales_by_four_without_flat_bonus(self) -> None:
        # Ashen Strike+ keeps the 6 base and raises the per-exhausted-card bonus to 4 (observed vars
        # CalculationBase 6 / ExtraDamage 4). AED v2 seq156 dealt 6 with an empty exhaust pile while the
        # model added the generic +3 upgrade bonus and predicted 9.
        ashen = Card(ASHEN_STRIKE, True)
        dummy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        empty = Combat(80, (ashen,), (), (), (dummy,), energy=3)
        self.assertEqual(step(empty, "card:0@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 94)
        two = Combat(80, (ashen,), (), (), (dummy,), energy=3, exhaust_pile=(STRIKE, DEFEND))
        self.assertEqual(step(two, "card:0@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 86)

    def test_perfected_strike_counts_ultimate_strike_as_a_strike(self) -> None:
        # C510 v5 seq209: Perfected Strike showed 33 with Ultimate Strike as one of eight Strikes, while
        # the model counted seven and predicted 30.  6 base + 2 per Strike (two cards here) = 10.
        perfected = Card(PERFECTED_STRIKE, False)
        ultimate = Card(ULTIMATE_STRIKE, False)
        combat = Combat(80, (perfected,), (ultimate,), (), (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),), energy=3)
        self.assertEqual(step(combat, "card:0@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 90)

    def test_thorns_reflection_is_absorbed_by_block(self) -> None:
        # ThornsPower.BeforeDamageReceived fires before the attack's own DamageCmd, so block is still
        # standing (Unpowered is not Unblockable).  Observed on EAIF2UUVCK seq 294: block 7 absorbed a
        # 5 reflection with no HP loss.
        thorns = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("ThornsPower", 5),))
        combat = Combat(80, (STRIKE,), (), (), (thorns,), energy=1, player_block=7)
        after = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block, after.enemies[0].hp), (80, 2, 94))

    def test_thorns_reflection_hits_hp_only_after_block_is_spent(self) -> None:
        # One reflection per hit, each absorbed by whatever block is left at that moment: VTW80ZJA2G
        # seq 279, Twin Strike (2 hits) against Thorns 5 with block 5 lost exactly 5 HP.
        thorns = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("ThornsPower", 5),))
        combat = Combat(80, (TWIN_STRIKE,), (), (), (thorns,), energy=1, player_block=5)
        after = step(combat, f"{TWIN_STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block, after.enemies[0].hp), (75, 0, 90))

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
        base_damage = step(Combat(80, (BODY_SLAM,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=1, player_block=13), f"{BODY_SLAM}@0", {}, random.Random(0))
        self.assertEqual(base_damage.enemies[0].hp, 87)
        base_cost = Combat(80, (BODY_SLAM,), (), (), (Enemy("MONSTER.DUMMY", 100, "MOVE", ()),), energy=0, player_block=10)
        upgraded = replace(base_cost, upgraded_cards=(BODY_SLAM,))
        self.assertNotIn(f"{BODY_SLAM}@0", legal_actions(base_cost))
        self.assertIn(f"{BODY_SLAM}@0", legal_actions(upgraded))
        after = step(upgraded, f"{BODY_SLAM}@0", {}, random.Random(0))
        self.assertEqual((after.energy, after.enemies[0].hp), (0, 90))

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

    def test_orichalcum_blocks_infection_before_a_non_attacking_enemy_turn(self) -> None:
        # astra_goal_r1 seq70: HP80, no block, Infection; the next observation still has HP80.
        state = Combat(80, (INFECTION,), (STRIKE,) * 10, (),
                       (Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ()),),
                       player_relics=("RELIC.ORICHALCUM",))
        self.assertEqual(step(state, END_TURN, DUMMY_DATA, random.Random(0)).player_hp, 80)

    def test_orichalcum_checks_block_before_plating_and_status_damage(self) -> None:
        state = Combat(80, (INFECTION,), (STRIKE,) * 10, (),
                       (Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ()),),
                       player_relics=("RELIC.ORICHALCUM",))
        for initial_block, plating, expected_hp in ((2, 0, 69), (0, 4, 77)):
            with self.subTest(initial_block=initial_block, plating=plating):
                before = replace(state, player_block=initial_block,
                                 player_powers=(("PlatingPower", plating),))
                after = step(before, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
                self.assertEqual(after.player_hp, expected_hp)

    def test_turn_end_block_grants_trigger_juggernaut_without_dexterity_or_frail(self) -> None:
        state = Combat(80, (INFECTION,), (STRIKE,) * 10, (),
                       (Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ()),),
                       player_relics=("RELIC.ORICHALCUM", "RELIC.RIPPLE_BASIN", RELIC_CLOAK_CLASP),
                       player_powers=(("PlatingPower", 4), ("JuggernautPower", 6),
                                      ("DexterityPower", 10), ("FrailPower", 2)))
        after = step(state, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 80)  # 4 + 6 + 4 + 1 block covers Infection plus attack.
        self.assertEqual(after.enemies[0].hp, 76)  # Four grants, each dealing six damage.

    def test_wither_curse_deals_damage_at_turn_end_and_block_absorbs_it(self) -> None:
        # Wither is a Curse (MaxUpgradeLevel 0) with HasTurnEndInHandEffect: 3 flat Unpowered
        # damage, not Unblockable, so the block still standing when the hook runs absorbs it.
        # Before this the card was invisible to the model because CARD_NAMES had no entry, so
        # the raw observation id never matched the name the turn-end hook looks up.
        wither = Combat(80, (WITHER,), (STRIKE,) * 10, (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),))
        after = step(wither, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 80 - 3)
        blocked = replace(wither, player_block=2)
        after = step(blocked, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.player_block), (79, 0))

    def test_chains_of_binding_afflicts_cards_drawn_during_the_rollout(self) -> None:
        # The live hand already carries the game's Bound flags, but a card drawn inside a rollout
        # has to be afflicted by the power itself, or the model treats it as playable.
        combat = Combat(
            80, (), tuple(Card(name) for name in (STRIKE, DEFEND, BASH, ANGER, BLUDGEON, STOMP, IRON_WAVE)),
            (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),),
            player_powers=(("ChainsOfBindingPower", 3),),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        bound = sum(1 for card in after.hand if isinstance(card, Card) and card.bound)
        self.assertEqual((len(after.hand), bound), (5, 3))
        # Before any Bound card is played, every Bound card is playable (ShouldPlay gates only after
        # the first Bound play of the turn). Real runs played Bound cards 279 times, including 45 turns
        # where two or more were played in the same turn.
        self.assertEqual(len([action for action in legal_actions(after) if action.startswith("card:")]), 5)
        # Once one Bound card is played, the rest of that turn's Bound cards are gated off.
        bound_action = next(
            action for action in legal_actions(after)
            if action.startswith("card:")
            and isinstance(after.hand[int(action[5:].split("@")[0])], Card)
            and after.hand[int(action[5:].split("@")[0])].bound
        )
        after_play = step(after, bound_action, DUMMY_DATA, random.Random(0))
        self.assertTrue(after_play.bound_played_this_turn)
        remaining = [index for index, card in enumerate(after_play.hand) if isinstance(card, Card) and card.bound]
        self.assertEqual(len(remaining), 2)
        playable = {int(action[5:].split("@")[0]) for action in legal_actions(after_play) if action.startswith("card:")}
        # The unbound copies are still playable; the bound ones are gated off for the rest of the turn.
        self.assertEqual(playable, set(range(len(after_play.hand))) - set(remaining))
        # The cap is per turn: drawing further cards adds no Bound once 3 are afflicted.
        after = _draw_into_combat(after, 2, DUMMY_DATA, random.Random(0))
        self.assertEqual(sum(1 for card in after.hand if isinstance(card, Card) and card.bound), 3)
        after = _draw_into_combat(after, 2, DUMMY_DATA, random.Random(0))
        self.assertEqual(sum(1 for card in after.hand if isinstance(card, Card) and card.bound), 3)

    def test_fiddle_adds_two_to_the_hand_draw_and_refuses_every_other_draw(self) -> None:
        combat = Combat(
            80, (), (STRIKE,) * 12, (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),),
            player_relics=(RELIC_FIDDLE,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), 7)  # 5 + Fiddle.ModifyHandDrawLate
        # Dark Embrace would draw 1 per exhausted card, but Fiddle's ShouldDraw refuses it.
        after = replace(after, player_powers=(("DarkEmbracePower", 1),))
        after = _after_exhaust(after, (STRIKE,), random.Random(0), DUMMY_DATA)
        self.assertEqual(len(after.hand), 7)

    def test_blood_soaked_rose_is_not_double_counted_at_energy_reset(self) -> None:
        # The bridge reports the game's effective max_energy for the observed turn, so a run holding
        # Blood-Soaked Rose already shows 4 at turn 1. A state built from an observation must reset to
        # the same 4, not 4 + 1.
        combat = Combat(
            80, (), (STRIKE,) * 12, (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),),
            max_energy=4, energy=4, player_relics=(RELIC_BLOOD_SOAKED_ROSE,),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.turn, after.energy, after.max_energy), (2, 4, 4))

    def test_forgotten_soul_damage_lands_on_one_random_enemy_per_exhausted_card(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()))
        combat = Combat(80, (), (STRIKE,) * 12, (), enemies, player_relics=(RELIC_FORGOTTEN_SOUL,))
        after = _after_exhaust(combat, (STRIKE, STRIKE), random.Random(0), DUMMY_DATA)
        self.assertEqual(sum(enemy.hp for enemy in after.enemies), 20 - 2)

    def test_duplication_power_resolves_the_next_play_twice(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(
            80, (TWIN_STRIKE,), (), (), (enemy,), energy=1,
            player_powers=(("DuplicationPower", 1),),
        )
        after = step(combat, f"{TWIN_STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 40 - 4 * 5)  # 2 hits, each resolving twice
        self.assertEqual(_power(after.player_powers, "DuplicationPower"), 0)

    def test_duplication_power_doubles_the_next_block_card_grant(self) -> None:
        combat = Combat(
            80, (DEFEND,), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),), energy=1,
            player_powers=(("DuplicationPower", 1),),
        )
        after = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 10)  # 5 base, applied twice
        self.assertEqual(_power(after.player_powers, "DuplicationPower"), 0)

    def test_play_duplicated_re_resolves_draw_effects(self) -> None:
        # DuplicationPower increases the play count, and the game runs the card's commands once per
        # play - so Shrug It Off (block 5 + draw 1) draws twice as well as granting block twice.
        draw = tuple(Card(STRIKE) for _ in range(4))
        combat = Combat(
            80, (Card(SHRUG),), draw, (), (Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ()),), energy=1,
            player_powers=(("DuplicationPower", 1),),
        )
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 16)  # Shrug grants 8, applied twice
        self.assertEqual(len(after.hand), 2)

    def test_play_duplicated_re_resolves_status_effects(self) -> None:
        # The status application is part of OnPlay, so an increased play count applies it again.
        combat = Combat(
            80, (Card(BASH),), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),), energy=2,
            player_powers=(("DuplicationPower", 1),),
        )
        after = step(combat, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 4)  # table value 2, applied twice

    def test_play_duplicated_re_applies_power_card_effects(self) -> None:
        # OnPlay runs once per play, so a Power card with an increased play count applies its power twice.
        combat = Combat(
            80, (Card(DEMON_FORM),), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),), energy=3,
            player_powers=(("DuplicationPower", 1),),
        )
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "DemonFormPower"), 4)  # 2 applied twice

    def test_juggernaut_triggers_once_per_play_resolution(self) -> None:
        # JuggernautPower is AfterBlockGained, so each resolution that gains block fires its own hit.
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(
            80, (DEFEND,), (), (), (enemy,), energy=1,
            player_powers=(("JuggernautPower", 3), ("DuplicationPower", 1),),
        )
        after = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 10)  # 5 base, applied twice
        self.assertEqual(after.enemies[0].hp, 40 - 3 * 2)

    def test_panache_counter_advances_once_per_play_resolution(self) -> None:
        # PanachePower.AfterCardPlayed counts each play, so a duplicated play advances the counter twice.
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(
            80, (DEFEND,), (), (), (enemy,), energy=1,
            player_powers=(("PanachePower", 10), ("DuplicationPower", 1),),
            panache_cards_this_turn=4,
        )
        after = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 40 - 10)  # counter reached 5 on the second resolution
        # The game resets CardsLeft to 5 after the trigger, so the next resolution counts from zero again.
        self.assertEqual(after.panache_cards_this_turn, 1)

    def test_play_duplicated_advances_the_per_play_counters_twice(self) -> None:
        # Card-play counters (used by Kunai/Shuriken/Unmovable style relics) count each resolution.
        combat = Combat(
            80, (DEFEND,), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),), energy=1,
            player_powers=(("DuplicationPower", 1),),
        )
        after = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(
            (after.cards_played_this_turn, after.skills_played_this_turn, after.block_cards_this_turn),
            (2, 2, 2),
        )

    def test_chains_affliction_cap_counts_entries_not_cards_in_hand(self) -> None:
        # ChainsOfBindingPower.AfterCardDrawn counts CardAfflictionEntry happened this turn, so playing
        # an afflicted card does not free up the per-turn cap.
        draw = tuple(Card(STRIKE) for _ in range(4))
        combat = Combat(
            80, (Card(SHRUG), Card(POMMEL_STRIKE)), draw, (),
            (Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ()),), energy=3,
            player_powers=(("ChainsOfBindingPower", 1),),
        )
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))       # Shrug: draw 1 -> afflicted
        self.assertEqual(sum(1 for card in after.hand if card.bound), 1)
        bound_index = next(i for i, card in enumerate(after.hand) if card.bound)
        after = step(after, f"card:{bound_index}@0", DUMMY_DATA, random.Random(0))  # the first Bound is playable
        after = step(after, f"card:{after.hand.index(Card(POMMEL_STRIKE))}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.chains_afflicted_this_turn, 1)
        self.assertEqual(sum(1 for card in after.hand if card.bound), 0)

    def test_one_two_punch_card_grants_the_power_and_doubles_attacks_only(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (ONE_TWO_PUNCH, STRIKE, DEFEND), (), (), (enemy,), energy=3)
        after = step(combat, ONE_TWO_PUNCH, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "OneTwoPunchPower"), 1)
        after = step(after, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 40 - 12)  # Attack: the play resolves twice
        self.assertEqual(_power(after.player_powers, "OneTwoPunchPower"), 0)
        after = step(after, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 5)  # consumed by the Attack, so not doubled

    def test_gigantification_multiplies_only_the_first_attack_of_the_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ())
        combat = Combat(
            80, (STRIKE, STRIKE), (), (), (enemy,), energy=2,
            player_powers=(("GigantificationPower", 1),),
        )
        first = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((first.enemies[0].hp, _power(first.player_powers, "GigantificationPower")), (60 - 18, 0))
        second = step(first, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(second.enemies[0].hp, 60 - 18 - 6)

    def test_panache_damage_fires_after_five_cards_played_in_the_turn(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 30, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY", 30, "IDLE_MOVE", ()))
        combat = Combat(80, (PANACHE, DEFEND, DEFEND, DEFEND, DEFEND, DEFEND), (), (), enemies, energy=5)
        combat = step(combat, PANACHE, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "PanachePower"), 10)
        for _ in range(4):
            combat = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
            self.assertEqual(sum(enemy.hp for enemy in combat.enemies), 60)  # the applying play is not counted
        combat = step(combat, DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(sum(enemy.hp for enemy in combat.enemies), 60 - 20)  # 10 Unpowered to each
        self.assertEqual(combat.panache_cards_this_turn, 0)  # CardsLeft resets to 5

    def test_play_count_powers_are_removed_at_the_end_of_the_player_turn(self) -> None:
        combat = Combat(
            80, (), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),),
            player_powers=(("DuplicationPower", 1), ("OneTwoPunchPower", 1)),
        )
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(
            (_power(after.player_powers, "DuplicationPower"), _power(after.player_powers, "OneTwoPunchPower")),
            (0, 0),
        )

    def test_duplicator_and_gigantification_potions_apply_their_powers(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,), player_potions=(POTION_DUPLICATOR, POTION_GIGANTIFICATION))
        self.assertIn(f"potion:{POTION_DUPLICATOR}", legal_actions(combat))
        # GigantificationPotion is TargetType.AnyPlayer and every one of the 18 recorded plays in real runs
        # carries target_id None, so it is listed untargeted rather than per-enemy.
        self.assertIn(f"potion:{POTION_GIGANTIFICATION}", legal_actions(combat))
        after = step(combat, f"potion:{POTION_DUPLICATOR}", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "DuplicationPower"), 1)
        after = step(after, f"potion:{POTION_GIGANTIFICATION}", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "GigantificationPower"), 1)

    def test_battle_trance_blocks_further_draws_until_the_next_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (BATTLE_TRANCE, DRUM_OF_BATTLE), (STRIKE,) * 12, (), (enemy,))
        after = step(combat, BATTLE_TRANCE, DUMMY_DATA, random.Random(0))
        self.assertEqual((len(after.hand), _power(after.player_powers, "NoDrawPower")), (4, 1))
        # Drum of Battle still resolves, but NoDraw eats its two cards.
        after = step(after, DRUM_OF_BATTLE, DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), 3)
        # The power is removed at the side turn end, so the next hand is drawn normally.
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((len(after.hand), _power(after.player_powers, "NoDrawPower")), (5, 0))

    def test_radiance_grants_one_energy_per_turn_then_decrements(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (), (STRIKE,) * 12, (), (enemy,), player_powers=(("RadiancePower", 2),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, _power(after.player_powers, "RadiancePower")), (4, 1))
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, _power(after.player_powers, "RadiancePower")), (4, 0))
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 3)

    def test_frog_knight_charges_once_below_half_health(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        values = next(m for m in glory["monsters"] if m["id"] == "MONSTER.FROG_KNIGHT")["values"]
        spec = next(m for m in glory["monsters"] if m["id"] == "MONSTER.FROG_KNIGHT")

        def branch(hp: int, history: tuple[str, ...]) -> str:
            enemy = Enemy("MONSTER.FROG_KNIGHT", hp, "HALF_HEALTH", tuple(sorted(values.items())), history=history)
            return _resolve_move(enemy, spec, random.Random(0), "HALF_HEALTH")

        # 191 max HP, so the charge waits until below 95.
        self.assertEqual(branch(120, ()), "TONGUE_LASH")
        self.assertEqual(branch(80, ()), "BEETLE_CHARGE")
        # Once it has charged it never charges again, however low it gets.
        self.assertEqual(branch(20, ("BEETLE_CHARGE",)), "TONGUE_LASH")

    def test_vicious_draws_whenever_the_player_applies_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (VICIOUS, BASH, STRIKE), (STRIKE,) * 8, (), (enemy,), energy=6)
        after = step(combat, VICIOUS, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "ViciousPower"), 1)
        # Bash applies Vulnerable, so one card is drawn on top of the usual hand.
        before = len(after.hand)
        after = step(after, f"{BASH}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 2)
        self.assertEqual(len(after.hand), before)  # Bash left hand, one card drawn back in
        # A plain Strike applies no Vulnerable, so nothing is drawn.
        before = len(after.hand)
        after = step(after, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), before - 1)

    def test_vicious_upgraded_draws_two(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (BASH,), (STRIKE,) * 8, (), (enemy,), energy=3, player_powers=(("ViciousPower", 2),))
        after = step(combat, f"{BASH}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), 2)  # Bash left hand, two drawn

    def test_metamorphosis_seeds_the_draw_pile_with_free_attacks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ())
        combat = Combat(80, (METAMORPHOSIS,), (), (), (enemy,), energy=2)
        after = step(combat, METAMORPHOSIS, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, len(after.draw_pile), after.exhaust_pile), (0, 3, (METAMORPHOSIS,)))
        self.assertTrue(all(card_name(c) in INFERNAL_BLADE_ATTACKS for c in after.draw_pile))
        # Every generated card is free for the rest of the combat.
        self.assertEqual(set(after.draw_pile), set(after.free_cards))
        upgraded = step(replace(combat, upgraded_cards=(METAMORPHOSIS,)), METAMORPHOSIS, DUMMY_DATA, random.Random(0))
        self.assertEqual(len(upgraded.draw_pile), 5)

    def test_free_attack_power_zeroes_attacks_and_is_spent_per_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE, STRIKE, DEFEND), (), (), (enemy,), energy=0, player_powers=(("FreeAttackPower", 1),))
        self.assertEqual(_effective_cost(combat, STRIKE), 0)  # Attacks are free
        self.assertEqual(_effective_cost(combat, DEFEND), 1)  # Skills still cost
        after = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        # One Attack spent the only charge, so the next one is full price again and unaffordable.
        self.assertEqual((_power(after.player_powers, "FreeAttackPower"), after.energy), (0, 0))
        self.assertNotIn(f"{STRIKE}@0", legal_actions(after))

    def test_normality_in_hand_caps_the_turn_at_three_cards(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE,) * 4 + (NORMALITY,), (STRIKE,) * 8, (), (enemy,), energy=5)
        for _ in range(3):
            self.assertIn(f"{STRIKE}@0", legal_actions(combat))
            combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        # Three cards spent and the curse still in hand: nothing else may be played this turn.
        self.assertEqual((combat.energy, legal_actions(combat)), (2, (END_TURN,)))
        # The cap is lifted for the next turn.
        combat = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertIn(f"{STRIKE}@0", legal_actions(combat))

    def test_normality_only_caps_while_it_is_in_hand(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ())
        # Same position with the curse still in the draw pile: no cap.
        combat = Combat(80, (STRIKE,) * 4, (NORMALITY,) + (STRIKE,) * 8, (), (enemy,), energy=5)
        for _ in range(3):
            combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertIn(f"{STRIKE}@0", legal_actions(combat))

    def test_sloth_caps_the_number_of_cards_played_in_a_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE,) * 4, (STRIKE,) * 8, (), (enemy,), energy=4, player_powers=(("SlothPower", 2),))
        for _ in range(2):
            self.assertIn(f"{STRIKE}@0", legal_actions(combat))
            combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        # Two cards spent: the cap closes the turn even with energy and cards left.
        self.assertEqual((combat.energy, legal_actions(combat)), (2, (END_TURN,)))

    def test_burning_pact_exhausts_dead_weight_rather_than_a_random_card(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        hand = (BURNING_PACT, BLUDGEON, WOUND, BLUDGEON)
        combat = Combat(80, hand, (STRIKE,) * 8, (), (enemy,), energy=1)
        after = step(combat, BURNING_PACT, DUMMY_DATA, random.Random(0))
        # The Wound goes, never one of the Bludgeons.
        self.assertEqual(after.exhaust_pile, (WOUND,))
        self.assertEqual(sum(card_name(c) == BLUDGEON for c in after.hand), 2)

    def test_true_grit_only_chooses_when_upgraded(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        hand = (TRUE_GRIT, WOUND, BLUDGEON)
        base = Combat(80, hand, (STRIKE,) * 8, (), (enemy,), energy=1)
        upgraded = step(replace(base, upgraded_cards=(TRUE_GRIT,)), TRUE_GRIT, DUMMY_DATA, random.Random(0))
        self.assertEqual(upgraded.exhaust_pile, (WOUND,))
        # Unupgraded True Grit really is random, so it can take the Bludgeon.
        picks = {
            card_name(step(base, TRUE_GRIT, DUMMY_DATA, random.Random(seed)).exhaust_pile[0])
            for seed in range(12)
        }
        self.assertIn(BLUDGEON, picks)

    def test_stoke_exhausts_the_hand_and_refills_it_with_generated_cards(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (STOKE, STRIKE, DEFEND, BASH), (), (), (enemy,), energy=1)
        after = step(combat, STOKE, DUMMY_DATA, random.Random(0))
        # The three other cards are exhausted and three generated ones take their place.
        self.assertEqual((after.energy, len(after.hand)), (0, 3))
        self.assertEqual(sorted(map(card_name, after.exhaust_pile)), sorted([STRIKE, DEFEND, BASH]))
        self.assertTrue(all(card_name(card) in STOKE_GENERATION for card in after.hand))
        self.assertEqual(after.discard_pile, (STOKE,))

    def test_generated_cards_come_only_from_the_characters_own_pool(self) -> None:
        # Stoke.cs and InfernalBlade.cs both draw from `Owner.Character.CardPool.GetUnlockedCards`,
        # so a colorless card can never be the generated card in an Ironclad run even when the model
        # knows it (Fasten, Lift, Panache are ColorlessCardPool members).  Adding a card to
        # CARD_COST used to widen the generation set silently through this derivation.
        self.assertNotIn(PANACHE, STOKE_GENERATION)
        self.assertNotIn(FASTEN, STOKE_GENERATION)
        self.assertNotIn(LIFT, STOKE_GENERATION)
        # One-Two Punch is in IroncladCardPool, so it is a legal generation.
        self.assertIn(ONE_TWO_PUNCH, STOKE_GENERATION)
        self.assertIn(PERFECTED_STRIKE, INFERNAL_BLADE_ATTACKS)
        self.assertFalse(set(STOKE_GENERATION) & CARDS_OUTSIDE_THE_CHARACTER_POOL)
        self.assertFalse(set(INFERNAL_BLADE_ATTACKS) & CARDS_OUTSIDE_THE_CHARACTER_POOL)

    def test_tangled_surcharges_attacks_for_one_turn_only(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE, DEFEND), (STRIKE,) * 8, (), (enemy,), player_powers=(("TangledPower", 1),))
        self.assertEqual(_effective_cost(combat, STRIKE), 2)  # Attack pays the Entangled surcharge
        self.assertEqual(_effective_cost(combat, DEFEND), 1)  # Skills are untouched
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((_power(after.player_powers, "TangledPower"), _effective_cost(after, STRIKE)), (0, 1))

    def test_tender_does_not_take_damage_off_attacks(self) -> None:
        # TenderPower has no damage hook: it applies DexterityPower(-1) stacks and hands Strength and
        # Dexterity back at AfterSideTurnEnd equal to the cards played this turn.  Dexterity is a Block
        # power in this game (DexterityPower.ModifyBlockAdditive is its only hook), so no Attack loses
        # value as the turn goes on.  L3PN5HBQ8T seq 283 is the measurement: Tender active, three cards
        # already played, a Strike (6) against an enemy while the player had Strength -2 dealt 4 in the
        # game, where the model -1 per earlier card dealt 1.
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE, STRIKE), (STRIKE,) * 8, (), (enemy,), energy=3,
                        player_powers=(("TenderPower", 1),))
        after = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 94)
        after = step(after, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 88)

    def test_enemy_regen_heals_and_decrements_up_to_its_initial_hp(self) -> None:
        values = (("MaxInitialHp", 50), ("MinInitialHp", 50))
        enemy = Enemy("MONSTER.DUMMY", 45, "IDLE_MOVE", values, powers=(("RegenPower", 3),))
        combat = Combat(80, (), (STRIKE,) * 8, (), (enemy,))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "RegenPower")), (48, 2))
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "RegenPower")), (50, 1))

    def test_havoc_plays_the_top_of_the_draw_pile_for_free_and_exhausts_it(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        # The draw pile is an unordered bag in this model, so it holds one kind of card to keep
        # the autoplayed card deterministic.
        combat = Combat(80, (HAVOC,), (STRIKE, STRIKE), (), (enemy,), energy=1)
        after = step(combat, HAVOC, DUMMY_DATA, random.Random(0))
        # Havoc costs its 1, the drawn Strike resolves for nothing, and is exhausted not discarded.
        self.assertEqual((after.energy, after.enemies[0].hp), (0, 94))
        self.assertEqual((after.exhaust_pile, after.discard_pile), ((STRIKE,), (HAVOC,)))
        self.assertEqual(after.draw_pile, (STRIKE,))

    def test_havoc_exhausts_an_unplayable_top_card_without_playing_it(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (HAVOC,), (WOUND, WOUND), (), (enemy,), energy=1)
        after = step(combat, HAVOC, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 100)
        self.assertEqual(after.exhaust_pile, (WOUND,))
        self.assertNotIn(WOUND, after.hand)

    def test_intangible_caps_every_hit_at_one_without_wearing_off(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", (), powers=(("IntangiblePower", 1),))
        combat = Combat(80, (BLUDGEON, STRIKE), (), (), (enemy,), energy=4)
        after = step(combat, f"{BLUDGEON}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 99)  # 32 damage capped to 1
        after = step(after, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        # Unlike Slippery, taking a hit does not consume it.
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "IntangiblePower")), (98, 1))

    def test_nemesis_toggles_intangible_every_enemy_turn(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        values = next(m for m in glory["monsters"] if m["id"] == TEST_SUBJECT)["values"]
        enemy = Enemy(
            TEST_SUBJECT, 300, "PHASE3_LACERATE_MOVE", tuple(sorted(values.items())),
            powers=(("NemesisPower", 1), ("IntangiblePower", 1)), respawns=2,
        )
        combat = Combat(300, (), (STRIKE,) * 10, (), (enemy,))
        # Third form arrives Intangible; Nemesis flips it off at the end of its next turn, then on.
        states = []
        for _ in range(3):
            combat = step(combat, END_TURN, glory, random.Random(0))
            states.append(_power(combat.enemies[0].powers, "IntangiblePower"))
        self.assertEqual(states, [0, 1, 0])

    def test_search_never_prefers_a_first_move_that_kills_the_player(self) -> None:
        # astra_goal_scarf1 seq463: at 2 HP against a respawning boss every line lost, and the
        # old scoring picked Blood Wall - its 2 self-damage killed the player on the spot, which
        # scored better than dying later at negative HP.
        enemy = Enemy("MONSTER.DUMMY", 400, "HIT_MOVE", ())
        combat = Combat(2, (BLOOD_WALL, PRIMAL_FORCE), (), (), (enemy,), energy=3)
        ranked = search(combat, ATTACKING_DUMMY_DATA, 40, seed=0)
        self.assertEqual(dict(ranked)[BLOOD_WALL], min(value for _, value in ranked))
        self.assertNotEqual(ranked[0][0], BLOOD_WALL)
        # Blood Wall really is lethal here, so the penalty is not masking a survivable line.
        self.assertEqual(step(combat, BLOOD_WALL, ATTACKING_DUMMY_DATA, random.Random(0)).player_hp, 0)

    def test_brilliant_scarf_makes_the_turns_fifth_card_free(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ())
        combat = Combat(
            80, (STRIKE,) * 5, (), (), (enemy,), energy=4, player_relics=(RELIC_BRILLIANT_SCARF,),
        )
        for _ in range(4):
            combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.energy, combat.cards_played_this_turn), (0, 4))
        # Out of energy, but the fifth card of the turn costs nothing.
        self.assertIn(f"{STRIKE}@0", legal_actions(combat))
        combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((combat.energy, combat.enemies[0].hp), (0, 200 - 30))

    def test_brilliant_scarf_does_not_discount_the_sixth_card(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ())
        combat = Combat(
            80, (STRIKE,) * 6, (), (), (enemy,), energy=5, player_relics=(RELIC_BRILLIANT_SCARF,),
        )
        for _ in range(5):
            combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        # The fifth card was free, so one energy is left - but the sixth is full price again.
        self.assertEqual((combat.energy, combat.cards_played_this_turn), (1, 5))
        combat = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(combat.energy, 0)

    def test_strike_dummy_and_paper_phrog_modify_attack_damage(self) -> None:
        vulnerable = Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", (), powers=(("VulnerablePower", 2),))
        # Strike 6 (+3 Strike Dummy) = 9, then Vulnerable 1.5 + Paper Phrog 0.25 = 1.75x -> 15.
        combat = Combat(80, (STRIKE,), (), (), (vulnerable,), player_relics=(RELIC_STRIKE_DUMMY, RELIC_PAPER_PHROG))
        self.assertEqual(step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 60 - 15)
        # Neither relic: 6 damage at the plain 1.5x -> 9.
        combat = Combat(80, (STRIKE,), (), (), (vulnerable,))
        self.assertEqual(step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 60 - 9)
        # Strike Dummy only applies to Strike-tagged attacks, not to Bash.
        combat = Combat(80, (BASH,), (), (), (Enemy("MONSTER.DUMMY", 60, "IDLE_MOVE", ()),), player_relics=(RELIC_STRIKE_DUMMY,))
        self.assertEqual(step(combat, f"{BASH}@0", DUMMY_DATA, random.Random(0)).enemies[0].hp, 60 - 8)

    def test_lost_wisp_hits_every_enemy_on_each_power_card(self) -> None:
        enemies = (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()), Enemy("MONSTER.DUMMY", 30, "IDLE_MOVE", ()))
        combat = Combat(80, (INFLAME, STRIKE), (), (), enemies, player_relics=(RELIC_LOST_WISP,))
        after = step(combat, INFLAME, DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after.enemies], [32, 22])
        # Only Power cards trigger it - the follow-up Strike hits one enemy for its own damage.
        after = step(after, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual([enemy.hp for enemy in after.enemies], [32 - 6 - 2, 22])

    def test_vigor_boosts_every_hit_of_one_attack_then_is_spent(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 80, "IDLE_MOVE", ())
        combat = Combat(80, (TWIN_STRIKE, STRIKE), (), (), (enemy,), player_powers=(("VigorPower", 8),))
        # Twin Strike is 5 damage x2 hits; Vigor adds 8 to each hit, then removes itself.
        after = step(combat, f"{TWIN_STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.player_powers, "VigorPower")), (80 - 26, 0))
        after = step(after, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 80 - 26 - 6)  # no Vigor left for the follow-up

    def test_turn_end_hand_damage_is_absorbed_by_block_but_beckon_is_not(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ())
        # Toxic (5) has no Unblockable prop, so standing block eats it before HP.
        combat = Combat(80, (TOXIC,), (STRIKE,) * 10, (), (enemy,), player_block=7)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 80)
        # Beckon (6) is Unblockable, so the same 7 block does nothing for it.
        combat = Combat(80, (BECKON,), (STRIKE,) * 10, (), (enemy,), player_block=7)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 80 - 6)

    def test_decay_curse_burns_two_hp_at_turn_end_and_is_never_playable(self) -> None:
        combat = Combat(80, (DECAY,), (STRIKE,) * 10, (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),))
        self.assertEqual(legal_actions(combat), (END_TURN,))  # Unplayable curse, never a legal move
        combat = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(combat.player_hp, 80 - 2)  # HasTurnEndInHandEffect: 2 flat Unpowered damage

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

    def test_slimed_exhausts_itself_and_fires_forgotten_soul(self) -> None:
        # Slimed carries CardKeyword.Exhaust: Slimed.OnUse draws 1, then
        # CardModel.GetResultPileTypeForCardPlay sends the played card to the exhaust pile.  The game
        # dealt 1 to the enemy on every Slimed play in runs holding RELIC_FORGOTTEN_SOUL (the
        # SLIMED_BERSERKER CARD.SLIMED game+1 group, 5 cases), which the model priced at 0 because it
        # sent the played card to no pile at all.
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (SLIMED, STRIKE), (DEFEND,) * 4, (), (enemy,), energy=1,
                        player_relics=(RELIC_FORGOTTEN_SOUL,))
        after = step(combat, SLIMED, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.exhaust_pile, (SLIMED,))
        self.assertEqual(after.enemies[0].hp, 39)
        self.assertIn(DEFEND, after.hand)

    def test_slimed_without_the_relic_exhausts_without_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (SLIMED, STRIKE), (DEFEND,) * 4, (), (enemy,), energy=1)
        after = step(combat, SLIMED, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.exhaust_pile, after.enemies[0].hp), ((SLIMED,), 40))

    def test_cinder_damages_and_exhausts_a_random_hand_card(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        after = step(Combat(80, (CINDER, STRIKE, DEFEND), (), (), (enemy,)), f"{CINDER}@0", {}, random.Random(0))
        upgraded = step(Combat(80, (CINDER, STRIKE, DEFEND), (), (), (enemy,), upgraded_cards=(CINDER,)), f"{CINDER}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 22)
        self.assertEqual(upgraded.enemies[0].hp, 16)
        self.assertEqual(len(after.exhaust_pile), 1)
        self.assertEqual(sorted(after.hand), sorted({STRIKE, DEFEND} - set(after.exhaust_pile)))

    def test_toasty_mittens_gains_strength_and_exhausts_a_card_every_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (), (STRIKE,) * 8, (), (enemy,), player_relics=("RELIC.TOASTY_MITTENS",))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 1)
        self.assertEqual(len(after.exhaust_pile), 1)
        again = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(again.player_powers, "StrengthPower"), 2)  # it stacks every turn

    def test_gremlin_horn_pays_energy_and_a_card_for_a_kill(self) -> None:
        dying = Enemy("MONSTER.DUMMY", 6, "IDLE_MOVE", ())
        other = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE,), (DEFEND, DEFEND), (), (dying, other), player_relics=("RELIC.GREMLIN_HORN",))
        after = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertFalse(after.enemies[0].alive)
        self.assertEqual(after.energy, 3)  # 3 - 1 for the Strike, + 1 for the kill
        self.assertEqual(len(after.hand), 1)

    def test_unceasing_top_draws_when_the_hand_runs_out(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (STRIKE,), (DEFEND, DEFEND), (), (enemy,), player_relics=("RELIC.UNCEASING_TOP",))
        after = step(combat, f"{STRIKE}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.hand, (DEFEND,))

    def test_clarity_draws_one_extra_card_and_counts_down(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        draw = (STRIKE,) * 8
        combat = Combat(80, (), draw, (), (enemy,), player_powers=(("ClarityPower", 2),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(len(after.hand), 6)
        self.assertEqual(_power(after.player_powers, "ClarityPower"), 1)

    def test_mayhem_plays_cards_off_the_draw_pile_at_turn_start(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (), (STRIKE,) * 8, (), (enemy,), player_powers=(("MayhemPower", 1),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 94)  # one free Strike before the player may act

    def test_flex_potion_strength_expires_at_the_players_turn_end(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,), player_powers=(("StrengthPower", 5), ("FlexPotionPower", 3)))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 2)
        self.assertEqual(_power(after.player_powers, "FlexPotionPower"), 0)

    def test_cascade_plays_x_cards_off_the_draw_pile_for_free(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (CASCADE,), (STRIKE, STRIKE, DEFEND), (), (enemy,), energy=2)
        after = step(combat, CASCADE, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 0)  # the X cost takes everything
        self.assertEqual(len(after.draw_pile), 1)  # two cards left the pile and resolved
        self.assertLess(after.enemies[0].hp, 100)

    def test_cascade_needs_energy(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        self.assertEqual(legal_actions(Combat(80, (CASCADE,), (STRIKE,), (), (enemy,), energy=0)), (END_TURN,))

    def test_curses_left_in_hand_hit_the_player_at_turn_end(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        after = step(Combat(80, (DOUBT, REGRET, SHAME, STRIKE), (), (), (enemy,)), END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 76)  # Regret: unblockable damage equal to the hand size
        self.assertEqual(_power(after.player_powers, "WeakPower"), 1)  # Doubt, past the tick
        self.assertEqual(_power(after.player_powers, "FrailPower"), 1)  # Shame

    def test_the_per_turn_unplayable_marker_does_not_leak_into_the_next_turn(self) -> None:
        marked = Card(STRIKE, unplayable_this_turn=True)
        combat = Combat(80, (marked,), (), (), (Enemy("MONSTER.DUMMY", 10, "IDLE_MOVE", ()),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertFalse(any(isinstance(card, Card) and card.unplayable_this_turn for card in after.discard_pile))
        # RetainHandPower keeps the copy in hand across the flush; the marker must still be cleared.
        retained = step(
            replace(combat, player_powers=(("RetainHandPower", 1),)), END_TURN, DUMMY_DATA, random.Random(0)
        )
        self.assertTrue(any(isinstance(card, Card) and card.name == STRIKE for card in retained.hand))
        self.assertFalse(any(isinstance(card, Card) and card.unplayable_this_turn for card in retained.hand))

    def test_top_of_draw_autoplay_recursion_is_capped(self) -> None:
        # Playing Havoc auto-plays the top card of the draw pile; if that card is also Havoc, its play
        # re-enters the same path. Real run evidence: control (e808bdf) raised RecursionError at seq 138
        # with PyrePower active and Havoc in the draw pile. The cap stops the recursion.
        draw = tuple(Card(HAVOC) for _ in range(20))
        combat = Combat(
            80, (Card(HAVOC),), draw, (), (Enemy("MONSTER.DUMMY", 200, "IDLE_MOVE", ()),),
            energy=3, player_powers=(("PyrePower", 1),),
        )
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        self.assertLessEqual(after.pyre_autoplays_this_turn, 9)
        self.assertGreater(after.pyre_autoplays_this_turn, 1)
        # The cap is per turn.
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.pyre_autoplays_this_turn, 0)

    def test_curses_are_never_playable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        self.assertEqual(legal_actions(Combat(80, (DOUBT, REGRET, SHAME), (), (), (enemy,))), (END_TURN,))

    def test_stampede_autoplays_attacks_left_in_hand_at_turn_end(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = step(Combat(80, (STAMPEDE, STRIKE, DEFEND), (), (), (enemy,), energy=2), STAMPEDE, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(combat.player_powers, "StampedePower"), 1)
        self.assertEqual(combat.energy, 0)
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 94)  # the Strike was auto-played for free

    def test_stampede_does_nothing_without_an_attack_in_hand(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (DEFEND,), (), (), (enemy,), player_powers=(("StampedePower", 1),))
        after = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 100)

    def test_maul_hits_twice_and_each_play_buffs_every_copy(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        after = step(Combat(80, (MAUL, MAUL), (), (), (enemy,)), f"{MAUL}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 90)  # 5 damage, 2 hits
        self.assertEqual(after.maul_bonus, 1)
        again = step(after, f"{MAUL}@0", {}, random.Random(0))
        self.assertEqual(again.enemies[0].hp, 78)  # (5 + 1) * 2
        upgraded = step(Combat(80, (MAUL,), (), (), (enemy,), upgraded_cards=(MAUL,)), f"{MAUL}@0", {}, random.Random(0))
        self.assertEqual((upgraded.enemies[0].hp, upgraded.maul_bonus), (88, 2))  # 6 damage, Increase 2

    def test_thrash_exhausts_an_attack_from_hand_and_absorbs_its_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        after = step(Combat(80, (THRASH, STRIKE, DEFEND), (), (), (enemy,)), f"{THRASH}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 92)  # 4 damage, 2 hits
        self.assertEqual(after.exhaust_pile, (STRIKE,))  # only the attack can be taken
        self.assertEqual(after.hand, (DEFEND,))
        self.assertEqual(after.thrash_bonus, 6)

    def test_thrash_without_an_attack_in_hand_only_hits(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        after = step(Combat(80, (THRASH, DEFEND), (), (), (enemy,)), f"{THRASH}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.exhaust_pile, after.thrash_bonus), (92, (), 0))

    def test_perfected_strike_scales_with_strike_tagged_cards(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        base = Combat(80, (PERFECTED_STRIKE, STRIKE), (STRIKE, STRIKE), (), (enemy,))
        base_after = step(base, f"{PERFECTED_STRIKE}@0", {}, random.Random(0))
        self.assertEqual(base_after.enemies[0].hp, 26)  # 6 + 2 * 4 strikes
        combat = Combat(
            80,
            (Card(PERFECTED_STRIKE, upgraded=True), Card(STRIKE), STRIKE),
            (Card(STRIKE, upgraded=True), STRIKE),
            (),
            (enemy,),
        )
        after = step(combat, "card:0@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 19)  # 6 + 3 * 5 strikes

    def test_upgraded_bash_increases_damage_and_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        base = step(Combat(80, (BASH,), (), (), (enemy,), energy=2), f"{BASH}@0", {}, random.Random(0))
        upgraded = step(replace(Combat(80, (BASH,), (), (), (enemy,), energy=2), upgraded_cards=(BASH,)), f"{BASH}@0", {}, random.Random(0))
        self.assertEqual((base.enemies[0].hp, _power(base.enemies[0].powers, "VulnerablePower")), (92, 2))
        self.assertEqual((upgraded.enemies[0].hp, _power(upgraded.enemies[0].powers, "VulnerablePower")), (90, 3))

    def test_ashen_strike_scales_with_exhaust_pile(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 30, "MOVE", ())
        combat = Combat(80, (ASHEN_STRIKE,), (), (), (enemy,), exhaust_pile=(STRIKE, STRIKE, BASH))
        after = step(combat, f"{ASHEN_STRIKE}@0", {}, random.Random(0))
        # The 4 recorded Ashen Strike plays all show exhaust +0 and discard +1: the card itself goes to
        # the discard, so only the three cards already exhausted scale its damage (6 + 3 x 3 = 15).
        self.assertEqual((after.enemies[0].hp, after.exhaust_pile, after.discard_pile), (15, (STRIKE, STRIKE, BASH), (ASHEN_STRIKE,)))

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
        # Second Wind exhausts non-Attacks from hand (its own effect) but lands in the discard itself -
        # every one of the 43 recorded plays has discard +1.
        self.assertEqual((after.player_block, after.hand, set(after.exhaust_pile), SECOND_WIND in after.discard_pile), (10, (STRIKE,), {DEFEND, SHRUG}, True))

    def test_inflame_adds_strength_to_attacks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "MOVE", ())
        combat = step(Combat(80, (INFLAME, STRIKE), (), (), (enemy,)), INFLAME, {}, random.Random(0))
        self.assertEqual(combat.player_powers, (("StrengthPower", 2),))
        after = step(combat, f"{STRIKE}@0", {}, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 32)  # 6 + 2 strength

    def test_fight_me_hits_twice_and_applies_strength_to_both_sides(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        combat = Combat(80, (FIGHT_ME,), (), (), (enemy,), energy=2)
        after = step(combat, f"{FIGHT_ME}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, _power(after.enemies[0].powers, "StrengthPower")), (90, 1))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 3)
        upgraded = step(replace(combat, upgraded_cards=(FIGHT_ME,)), f"{FIGHT_ME}@0", {}, random.Random(0))
        self.assertEqual((upgraded.enemies[0].hp, _power(upgraded.player_powers, "StrengthPower")), (88, 4))

    def test_juggernaut_converts_block_to_unpowered_damage(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        combat = Combat(80, (JUGGERNAUT, DEFEND), (), (), (enemy,), energy=3)
        after_power = step(combat, JUGGERNAUT, {}, random.Random(0))
        self.assertEqual(_power(after_power.player_powers, "JuggernautPower"), 6)
        after_block = step(after_power, DEFEND, {}, random.Random(0))
        self.assertEqual((after_block.player_block, after_block.enemies[0].hp), (5, 94))

    def test_purity_exhausts_only_dead_weight_from_hand(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        combat = Combat(80, (PURITY, WOUND, SLIMED, STRIKE, DEFEND), (), (), (enemy,))
        after = step(combat, PURITY, {}, random.Random(0))
        self.assertEqual(after.exhaust_pile, (PURITY, WOUND, SLIMED))
        self.assertEqual(after.hand, (STRIKE, DEFEND))

    def test_salvo_draws_retained_hand_through_the_enemy_turn(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (SALVO, DEFEND), (STRIKE,) * 8, (), (enemy,), energy=1)
        after_salvo = step(combat, f"{SALVO}@0", {}, random.Random(0))
        self.assertEqual((after_salvo.enemies[0].hp, _power(after_salvo.player_powers, "RetainHandPower")), (88, 1))
        after_turn = step(after_salvo, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertIn(DEFEND, after_turn.hand)
        self.assertEqual(_power(after_turn.player_powers, "RetainHandPower"), 0)

    def test_flash_of_steel_hits_and_draws(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "MOVE", ())
        combat = Combat(80, (FLASH_OF_STEEL,), (STRIKE,), (), (enemy,))
        after = step(combat, f"{FLASH_OF_STEEL}@0", {}, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.hand), (95, (STRIKE,)))

    def test_omnislice_passes_the_first_hit_to_the_other_enemies_unpowered(self) -> None:
        # Omnislice.OnPlay (decompiled): the target takes a normal 8-damage attack, then every other
        # hittable enemy takes that hit's TotalDamage + OverkillDamage as Unpowered damage, so the
        # target's Vulnerable counts once and the others' Vulnerable does not apply again.
        enemies = (
            Enemy("MONSTER.DUMMY", 40, "MOVE", (), powers=(("VulnerablePower", 1),), block=5),
            Enemy("MONSTER.DUMMY", 30, "MOVE", (), powers=(("VulnerablePower", 1),)),
            Enemy("MONSTER.DUMMY", 30, "MOVE", (), block=4),
        )
        combat = Combat(80, (OMNISLICE,), (), (), enemies, player_powers=(("StrengthPower", 2),))
        self.assertIn(f"{OMNISLICE}@0", legal_actions(combat))
        after = step(combat, f"{OMNISLICE}@0", {}, random.Random(0))
        self.assertEqual(
            [(enemy.hp, enemy.block) for enemy in after.enemies],
            [(30, 0), (15, 0), (19, 0)],
        )
        self.assertEqual(after.energy, 3)

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

    def test_rampart_re_grants_turret_block_at_every_player_turn_start(self) -> None:
        # RampartPower.AfterSideTurnStart grants its amount to every living TurretOperator at the
        # start of the player's turn, not to the Rampart owner, and the turret's own block is
        # cleared when its enemy turn begins - so the turret starts each turn with 25 block again
        # for as long as the LivingShield lives.
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        specs = {monster["id"]: monster for monster in glory["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = (), block: int = 0) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), block=block, powers=powers)

        shield = make("MONSTER.LIVING_SHIELD", 55, "SHIELD_SLAM_MOVE", powers=(("RampartPower", 25),))
        turret = make("MONSTER.TURRET_OPERATOR", 41, "UNLOAD_MOVE", block=25)
        after = step(Combat(80, (DEFEND,), (), (), (shield, turret)), END_TURN, glory, random.Random(0))
        self.assertEqual((after.turn, after.enemies[0].block, after.enemies[1].block), (2, 0, 25))

    def test_rampart_stops_granting_block_once_the_shield_is_dead(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        specs = {monster["id"]: monster for monster in glory["monsters"]}

        def make(model: str, hp: int, move: str, powers: tuple[tuple[str, int], ...] = (), block: int = 0) -> Enemy:
            spec = specs[model]
            return Enemy(model=model, hp=hp, move=move, values=tuple(sorted(spec["values"].items())), block=block, powers=powers)

        shield = make("MONSTER.LIVING_SHIELD", 5, "SHIELD_SLAM_MOVE", powers=(("RampartPower", 25),))
        turret = make("MONSTER.TURRET_OPERATOR", 41, "UNLOAD_MOVE", block=25)
        played = step(Combat(80, (STRIKE,), (), (), (shield, turret)), f"{STRIKE}@0", {}, random.Random(0))
        self.assertFalse(played.enemies[0].alive)
        after = step(played, END_TURN, glory, random.Random(0))
        self.assertEqual(after.enemies[1].block, 0)

    def test_axebot_respawns_from_stock_power_until_the_stock_runs_out(self) -> None:
        # StockPower.AfterDeath re-adds a fresh Axebot with StockAmount-1 (Axebot.cs), and the new copy
        # starts at BOOT_UP_MOVE because the respawn sets the stock override.  The third copy carries no
        # StockPower, so it is the one that can actually die.
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        spec = next(monster for monster in glory["monsters"] if monster["id"] == "MONSTER.AXEBOT")
        values = tuple(sorted(spec["values"].items()))

        def axebot(hp: int, powers: tuple[tuple[str, int], ...], respawns: int) -> Enemy:
            return Enemy(model="MONSTER.AXEBOT", hp=hp, move=spec["initial_state"], values=values, powers=powers, respawns=respawns)

        first = step(Combat(80, (STRIKE,), (), (), (axebot(1, (("StockPower", 2),), 0),)), f"{STRIKE}@0", glory, random.Random(0))
        self.assertEqual(
            (first.enemies[0].alive, first.enemies[0].move, first.enemies[0].powers, first.enemies[0].respawns),
            (True, "BOOT_UP_MOVE", (("StockPower", 1),), 1),
        )
        second = step(Combat(80, (STRIKE,), (), (), (axebot(1, (("StockPower", 1),), 1),)), f"{STRIKE}@0", glory, random.Random(0))
        self.assertEqual(
            (second.enemies[0].alive, second.enemies[0].move, second.enemies[0].powers, second.enemies[0].respawns),
            (True, "BOOT_UP_MOVE", (), 2),
        )
        third = step(Combat(80, (STRIKE,), (), (), (axebot(1, (), 2),)), f"{STRIKE}@0", glory, random.Random(0))
        self.assertFalse(third.enemies[0].alive)

    def test_axebot_boot_up_strength_grows_with_each_stock_copy(self) -> None:
        # BOOT_UP_MOVE's Strength amount is `BootUpStrGain * (2 - StockAmount)` and Axebot.StockAmount is
        # the per-instance value (2 for the spawned copy, then Amount-1 on each respawn), so the copies
        # boot up with 0 / 3 / 6 Strength.  The exported StockAmount is the static 2 for all three.
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        spec = next(monster for monster in glory["monsters"] if monster["id"] == "MONSTER.AXEBOT")
        values = tuple(sorted(spec["values"].items()))
        strengths = []
        for stock in (2, 1, 0):
            powers = (("StockPower", stock),) if stock else ()
            enemy = Enemy(model="MONSTER.AXEBOT", hp=70, move="BOOT_UP_MOVE", values=values, powers=powers)
            after = step(Combat(80, (), (), (), (enemy,), turn=1), END_TURN, glory, random.Random(0))
            strengths.append(_power(after.enemies[0].powers, "StrengthPower"))
        self.assertEqual(strengths, [0, 3, 6])

    def test_thieving_hopper_steals_a_non_basic_card_from_the_player_piles(self) -> None:
        # ThievingHopper.ThieveryMove removes one card from the player's Draw and Discard piles with
        # CardPileCmd.RemoveFromCombat before its attack, so the card is unplayable for the rest of the
        # fight.  Basics are the last priority and cards the fight itself generated (no DeckVersion)
        # are never candidates, so the Wound here has to survive.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.THIEVING_HOPPER")
        hopper = Enemy(model=spec["id"], hp=79, move="THIEVERY_MOVE", values=tuple(sorted(spec["values"].items())))
        combat = Combat(80, (Card(STRIKE),), (Card(INFLAME), Card(STRIKE), Card(DEFEND), Card(SHRUG)), (Card(WOUND),), (hopper,))
        after = step(combat, END_TURN, hive, random.Random(0))
        before = sorted(card_name(value) for value in combat.hand + combat.draw_pile + combat.discard_pile)
        after_names = sorted(card_name(value) for value in after.hand + after.draw_pile + after.discard_pile + after.exhaust_pile)
        removed = [name for name in before if after_names.count(name) < before.count(name)]
        self.assertEqual(len(after_names), len(before) - 1)
        self.assertEqual(len(removed), 1)
        self.assertNotIn(removed[0], {STRIKE, DEFEND, WOUND})
        self.assertIn(WOUND, after_names)

    def test_thieving_hopper_steals_a_basic_when_only_basics_are_stealable(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.THIEVING_HOPPER")
        hopper = Enemy(model=spec["id"], hp=79, move="THIEVERY_MOVE", values=tuple(sorted(spec["values"].items())))
        combat = Combat(80, (Card(STRIKE),), (Card(STRIKE), Card(DEFEND)), (Card(WOUND),), (hopper,))
        after = step(combat, END_TURN, hive, random.Random(0))
        after_names = sorted(card_name(value) for value in after.hand + after.draw_pile + after.discard_pile + after.exhaust_pile)
        self.assertEqual(len(after_names), 3)
        self.assertIn(WOUND, after_names)
        self.assertEqual(sorted(name for name in after_names if name != WOUND), [STRIKE, STRIKE])

    def test_plated_enemy_re_grants_block_every_turn_and_its_plate_thins(self) -> None:
        # FrogKnight.AfterAddedToRoom applies PlatingPower(15) (not exported), PlatingPower.BeforeSideTurnStart
        # gives that as Block on round 1, BeforeSideTurnEndEarly re-grants Block = Amount after each of its
        # turns, and AfterSideTurnStart drops the amount by 1 from the second round.  The observed run
        # values for turns 1-9 are 15, 15, 14, 13, 12, 11, 10, 9, 8 for both the amount and the Block.
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        rng = random.Random(0)
        combat = initial_combat(glory, "ENCOUNTER.FROG_KNIGHT_NORMAL", rng, player_hp=400)
        self.assertEqual((combat.enemies[0].block, _power(combat.enemies[0].powers, "PlatingPower")), (15, 15))
        seen = []
        for _ in range(3):
            combat = step(combat, END_TURN, glory, rng)
            seen.append((combat.enemies[0].block, _power(combat.enemies[0].powers, "PlatingPower")))
        self.assertEqual(seen, [(15, 15), (14, 14), (13, 13)])

    def test_plating_stops_granting_block_once_the_plated_enemy_is_dead(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        spec = next(monster for monster in glory["monsters"] if monster["id"] == "MONSTER.FROG_KNIGHT")
        plate = int(spec["values"]["PlatingAmount"])
        frog = Enemy(model=spec["id"], hp=1, move=spec["initial_state"], values=tuple(sorted(spec["values"].items())), block=plate, powers=(("PlatingPower", plate),))
        # A second, unplated enemy keeps the fight going so the turn transition - where the re-grant
        # happens - is reached.
        mate = next(monster for monster in glory["monsters"] if monster["id"] == "MONSTER.TURRET_OPERATOR")
        partner = Enemy(model=mate["id"], hp=50, move=mate["initial_state"], values=tuple(sorted(mate["values"].items())))
        after = step(Combat(80, (BLUDGEON,), (), (), (frog, partner)), f"{BLUDGEON}@0", glory, random.Random(0))
        after = step(after, END_TURN, glory, random.Random(0))
        self.assertFalse(after.enemies[0].alive)
        self.assertEqual(after.enemies[0].block, 0)

    def test_decimillipede_bulk_gains_strength_and_constrict_applies_weak(self) -> None:
        # The segment export lists intents only for BULK_MOVE and CONSTRICT_MOVE (no effects), so the
        # C# bodies' StrengthPower(2) on itself and WeakPower(1) on the players have to be carried in
        # code.  Real runs show segments at Strength 2 and the player carrying Weak from turn 2 on.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        spec = next(monster for monster in hive["monsters"] if monster["id"] == "MONSTER.DECIMILLIPEDE_SEGMENT_FRONT")

        def segment(move: str, strength: int = 0) -> Enemy:
            powers = (("StrengthPower", strength),) if strength else ()
            return Enemy(model=spec["id"], hp=60, move=move, values=(), powers=powers)

        constricted = step(Combat(80, (), (), (), (segment("CONSTRICT_MOVE"),), turn=1), END_TURN, hive, random.Random(0))
        # The Weak it applies is not visible at the next player decision yet: step()'s end-of-turn
        # transition ticks player Weak/Vulnerable down after the enemy side and consumes a freshly
        # applied stack in the same transition (see CODEWIKI "player debuff tick").  The application
        # itself is here so the tick fix has something to make visible.
        self.assertLessEqual(_power(constricted.player_powers, "WeakPower"), 1)
        bulked = step(Combat(80, (), (), (), (segment("BULK_MOVE"),), turn=1), END_TURN, hive, random.Random(0))
        self.assertEqual(_power(bulked.enemies[0].powers, "StrengthPower"), 2)
        # The stacked Strength then scales the segment's next attack: Writhe is 5 damage twice, so with
        # Strength 2 it lands 14 on an unblocked player.
        scaled = step(Combat(80, (), (), (), (segment("WRITHE_MOVE", strength=2),), turn=1), END_TURN, hive, random.Random(0))
        self.assertEqual(80 - scaled.player_hp, 14)

    def test_enemy_applied_debuffs_survive_the_turn_that_applied_them(self) -> None:
        # WeakPower / VulnerablePower / FrailPower tick at the end of the enemy side's turn, but a stack
        # applied during that turn is exempt from it.  An Axebot's Hammer Uppercut (Weak 2 + Frail 2) is
        # observed in real runs as Weak 2 / Frail 2 during player turn 2 and 1 / 1 during player turn 3;
        # ticking the fresh stack in the same transition made the player read the debuff one turn late
        # (and left Frail - which nothing used to tick at all - on the player forever).
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        spec = next(monster for monster in glory["monsters"] if monster["id"] == "MONSTER.AXEBOT")
        axebot = Enemy(model=spec["id"], hp=400, move="HAMMER_UPPERCUT_MOVE", values=tuple(sorted(spec["values"].items())))
        rng = random.Random(0)
        combat = Combat(300, (), (), (), (axebot,), turn=1)
        after_first = step(combat, END_TURN, glory, rng)
        self.assertEqual(
            (_power(after_first.player_powers, "WeakPower"), _power(after_first.player_powers, "FrailPower")),
            (2, 2),
        )
        after_second = step(after_first, END_TURN, glory, rng)
        self.assertEqual(
            (_power(after_second.player_powers, "WeakPower"), _power(after_second.player_powers, "FrailPower")),
            (1, 1),
        )

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

    def test_greedy_prefers_the_block_that_survives_over_a_doomed_attack(self) -> None:
        # The greedy scorer priced only the play, so a doomed attack (Bash for 8, then the enemy
        # hits for 10 at 8 HP) beat the block card that keeps the player alive. search() prices the
        # enemy phase because its rollout runs it, so this made the continuation inconsistent with
        # the value it reports.
        enemy = Enemy("MONSTER.DUMMY", 100, "HIT_MOVE", ())
        combat = Combat(8, (BASH, DEFEND), (), (), (enemy,), energy=2)
        self.assertEqual(_greedy_action(combat, ATTACKING_DUMMY_DATA), DEFEND)

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

    def test_greedy_plays_inflame_before_multiple_attacks(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (INFLAME, ANGER, STRIKE), (), (), (enemy,), energy=3)
        self.assertEqual(_greedy_action(combat, DUMMY_DATA), INFLAME)

    def test_greedy_plays_bloodletting_before_whirlwind(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        combat = Combat(80, (BLOODLETTING, WHIRLWIND), (), (), (enemy,), energy=3)
        self.assertEqual(_greedy_action(combat, DUMMY_DATA), BLOODLETTING)

    def test_search_keeps_setup_before_the_payoff_attack(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 100, "IDLE_MOVE", ())
        inflame = Combat(80, (INFLAME, ANGER, STRIKE), (), (), (enemy,), energy=3)
        whirlwind = Combat(80, (BLOODLETTING, WHIRLWIND), (), (), (enemy,), energy=3)
        self.assertEqual(search(inflame, DUMMY_DATA, simulations=100, seed=0)[0][0], INFLAME)
        self.assertEqual(search(whirlwind, DUMMY_DATA, simulations=100, seed=0)[0][0], BLOODLETTING)

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

    def test_spectral_knight_hex_applies_to_player_from_glory_json(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        spec = next(monster for monster in glory["monsters"] if monster["id"] == "MONSTER.SPECTRAL_KNIGHT")
        enemy = Enemy(
            "MONSTER.SPECTRAL_KNIGHT", 93, "HEX", tuple(sorted(spec["values"].items()))
        )
        after = step(Combat(80, (), (), (), (enemy,)), END_TURN, glory, random.Random(0))
        self.assertEqual((after.enemies[0].move, _power(after.player_powers, "HexPower")), ("SOUL_SLASH", 2))

    def test_creature_kill_explodes_gas_bomb_and_waterfall_giant_from_json(self) -> None:
        with open("data/enemies_underdocks.json", encoding="utf-8-sig") as file:
            underdocks = json.load(file)
        specs = {monster["id"]: monster for monster in underdocks["monsters"]}
        for model, hp in (("MONSTER.GAS_BOMB", 7), ("MONSTER.WATERFALL_GIANT", 240)):
            spec = specs[model]
            enemy = Enemy(model, hp, "EXPLODE_MOVE", tuple(sorted(spec["values"].items())))
            after = step(Combat(80, (), (), (), (enemy,)), END_TURN, underdocks, random.Random(0))
            self.assertEqual(after.enemies[0].hp, 0)
            self.assertTrue(after.terminal)

    def test_waterfall_steam_eruption_keeps_giant_until_final_explosion(self) -> None:
        with open("data/enemies_underdocks.json", encoding="utf-8-sig") as file:
            underdocks = json.load(file)
        spec = next(monster for monster in underdocks["monsters"] if monster["id"] == "MONSTER.WATERFALL_GIANT")
        enemy = Enemy(
            "MONSTER.WATERFALL_GIANT", 240, "EXPLODE_MOVE", tuple(sorted(spec["values"].items())),
            powers=(("SteamEruptionPower", 15),),
        )
        combat = Combat(80, (), (), (), (enemy,))
        combat = step(combat, END_TURN, underdocks, random.Random(0))
        self.assertEqual((combat.enemies[0].hp, combat.enemies[0].move, _power(combat.enemies[0].powers, "SteamEruptionPower")), (999999999, "ABOUT_TO_BLOW_MOVE", 15))
        combat = step(combat, END_TURN, underdocks, random.Random(0))
        self.assertEqual((combat.enemies[0].move, _power(combat.enemies[0].powers, "SteamEruptionPower")), ("EXPLODE_MOVE", 0))
        combat = step(combat, END_TURN, underdocks, random.Random(0))
        self.assertEqual((combat.player_hp, combat.enemies[0].hp, combat.enemies[0].alive, combat.terminal), (65, 0, False, True))

    def test_waterfall_lethal_player_attack_enters_about_to_blow(self) -> None:
        with open("data/enemies_underdocks.json", encoding="utf-8-sig") as file:
            underdocks = json.load(file)
        spec = next(monster for monster in underdocks["monsters"] if monster["id"] == "MONSTER.WATERFALL_GIANT")
        for move in ("PRESSURIZE_MOVE", "RAM_MOVE"):
            enemy = Enemy(
                "MONSTER.WATERFALL_GIANT", 5, move, tuple(sorted(spec["values"].items())),
                powers=(("SteamEruptionPower", 3),),
            )
            after = step(Combat(80, (STRIKE,), (), (), (enemy,)), f"{STRIKE}@0", underdocks, random.Random(0))
            self.assertEqual((after.enemies[0].hp, after.enemies[0].move, _power(after.enemies[0].powers, "SteamEruptionPower"), after.terminal), (999999999, "ABOUT_TO_BLOW_MOVE", 3, False))

    def test_guardbot_gives_block_to_fabricator_from_glory_json(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        specs = {monster["id"]: monster for monster in glory["monsters"]}
        fabricator = specs["MONSTER.FABRICATOR"]
        guardbot = specs["MONSTER.GUARDBOT"]
        enemies = (
            Enemy("MONSTER.FABRICATOR", 150, "DISINTEGRATE_MOVE", tuple(sorted(fabricator["values"].items()))),
            Enemy("MONSTER.GUARDBOT", 16, "GUARD_MOVE", tuple(sorted(guardbot["values"].items()))),
        )
        after = _enemy_turn(Combat(80, (), (), (), enemies), 1, glory, random.Random(0))
        self.assertEqual((after.enemies[0].block, after.enemies[1].block), (15, 0))

    def test_queen_burn_bright_buffs_torch_head_amalgam_from_glory_json(self) -> None:
        with open("data/enemies_glory.json", encoding="utf-8-sig") as file:
            glory = json.load(file)
        specs = {monster["id"]: monster for monster in glory["monsters"]}
        queen = specs["MONSTER.QUEEN"]
        amalgam = specs["MONSTER.TORCH_HEAD_AMALGAM"]
        enemies = (
            Enemy("MONSTER.TORCH_HEAD_AMALGAM", 199, "TACKLE_MOVE", tuple(sorted(amalgam["values"].items())), primary=False),
            Enemy("MONSTER.QUEEN", 400, "BURN_BRIGHT_FOR_ME_MOVE", tuple(sorted(queen["values"].items()))),
        )
        after = _enemy_turn(Combat(80, (), (), (), enemies), 1, glory, random.Random(0))
        self.assertEqual((_power(after.enemies[0].powers, "StrengthPower"), after.enemies[1].block), (1, 20))

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

    def test_frantic_escape_copy_gets_more_expensive_each_play(self) -> None:
        enemy = Enemy("MONSTER.THE_INSATIABLE", 100, "IDLE_MOVE", (), powers=(("SandpitPower", 3),))
        combat = Combat(80, (Card(FRANTIC_ESCAPE), Card(FRANTIC_ESCAPE)), (), (), (enemy,))
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, _power(after.enemies[0].powers, "SandpitPower")), (2, 4))
        self.assertEqual(after.discard_pile, (Card(FRANTIC_ESCAPE, extra_cost=1),))
        # The untouched copy still costs 1; only the played one drifted up.
        after = replace(after, hand=after.hand + after.discard_pile, discard_pile=())
        self.assertEqual(
            [_effective_cost(after, value) for value in after.hand], [1, 2],
        )
        after = step(after, "card:1", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.energy, after.discard_pile), (0, (Card(FRANTIC_ESCAPE, extra_cost=2),)))

    def test_tear_asunder_hits_once_per_unblocked_hit_taken(self) -> None:
        for taken, expected_hp in [(0, 35), (2, 25), (5, 10)]:
            with self.subTest(taken=taken):
                enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
                combat = Combat(80, (TEAR_ASUNDER,), (), (), (enemy,), unblocked_hits=taken)
                after = step(combat, f"{TEAR_ASUNDER}@0", DUMMY_DATA, random.Random(0))
                self.assertEqual((after.enemies[0].hp, after.energy), (expected_hp, 1))

    def test_tear_asunder_counts_each_unblocked_repeat_hit(self) -> None:
        # ATTACKING_DUMMY_DATA hits once for 10 a turn; 5 block absorbs half of the first one.
        combat = Combat(80, (), (), (), (Enemy("MONSTER.DUMMY", 40, "HIT_MOVE", ()),), player_block=5)
        after = step(combat, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_hp, after.unblocked_hits), (75, 1))
        after = replace(after, player_block=99)
        after = step(after, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        # Fully blocked, so no DamageReceivedEntry with unblocked damage and no extra hit.
        self.assertEqual((after.player_hp, after.unblocked_hits), (75, 1))

    def test_squash_deals_ten_and_applies_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (SQUASH,), (), (), (enemy,))
        self.assertIn(f"{SQUASH}@0", legal_actions(combat))
        after = step(combat, f"{SQUASH}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.enemies[0].hp, after.energy), (30, 2))
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 2)

    def test_squash_upgrade_adds_damage_and_vulnerable(self) -> None:
        enemy = Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ())
        combat = Combat(80, (SQUASH,), (), (), (enemy,), upgraded_cards=(SQUASH,))
        after = step(combat, f"{SQUASH}@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 28)
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 3)

    def test_toric_toughness_regrants_stored_block_on_two_clears(self) -> None:
        combat = Combat(80, (TORIC_TOUGHNESS,), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),))
        self.assertIn(TORIC_TOUGHNESS, legal_actions(combat))
        after = step(combat, TORIC_TOUGHNESS, DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_block, after.energy, after.toric_pending), (5, 1, ((5, 2),)))
        # Each of the next two block clears re-grants the stored 5; the third turn has none left.
        blocks = []
        for _ in range(3):
            after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
            blocks.append(after.player_block)
        self.assertEqual((blocks, after.toric_pending), ([5, 5, 0], ()))

    def test_toric_toughness_stores_the_block_frail_actually_granted(self) -> None:
        combat = Combat(
            80, (TORIC_TOUGHNESS,), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),),
            player_powers=(("FrailPower", 2),), upgraded_cards=(TORIC_TOUGHNESS,),
        )
        after = step(combat, TORIC_TOUGHNESS, DUMMY_DATA, random.Random(0))
        # Upgraded 7 block, Frail cuts it to 5, and the stored amount is that reduced value.
        self.assertEqual((after.player_block, after.toric_pending), (5, ((5, 2),)))
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        # The re-grant is Unpowered, so Frail does not shrink it a second time.
        self.assertEqual(after.player_block, 5)

    def test_toric_toughness_does_not_fire_while_barricade_keeps_block(self) -> None:
        combat = Combat(
            80, (TORIC_TOUGHNESS,), (), (), (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),),
            player_powers=(("BarricadePower", 1),),
        )
        after = step(combat, TORIC_TOUGHNESS, DUMMY_DATA, random.Random(0))
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        # Block is retained instead of cleared, so AfterBlockCleared never runs and no use is spent.
        self.assertEqual((after.player_block, after.toric_pending), (5, ((5, 2),)))

    def test_toric_toughness_keeps_each_copy_stored_amount_separate(self) -> None:
        combat = Combat(
            80, (Card(TORIC_TOUGHNESS), Card(TORIC_TOUGHNESS, upgraded=True)), (), (),
            (Enemy("MONSTER.DUMMY", 40, "IDLE_MOVE", ()),), energy=4,
        )
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        after = step(after, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual((after.player_block, after.toric_pending), (12, ((5, 2), (7, 2))))
        after = step(after, END_TURN, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 12)

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

    def test_bowlbug_rock_fully_blocked_headbutt_triggers_dizzy(self) -> None:
        # ImbalancedPower.AfterDamageGiven -> POST_HEADBUTT (data/enemies_hive.json): a Headbutt
        # that lands fully blocked sets IsOffBalance, routing into DIZZY_MOVE instead of repeating.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        enemy = Enemy("MONSTER.BOWLBUG_ROCK", 45, "HEADBUTT_MOVE", (("IsOffBalance", False),))
        combat = Combat(80, (), (), (), (enemy,), player_block=20)  # >= Headbutt's 15 damage
        after = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual(after.enemies[0].move, "DIZZY_MOVE")
        self.assertEqual(_power(after.enemies[0].powers, "OffBalancePower"), 1)

    def test_bowlbug_rock_dizzy_move_clears_off_balance_and_resumes_headbutt(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        enemy = Enemy("MONSTER.BOWLBUG_ROCK", 45, "DIZZY_MOVE", (("IsOffBalance", False),), powers=(("OffBalancePower", 1),))
        combat = Combat(80, (), (), (), (enemy,))
        after = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual(after.enemies[0].move, "HEADBUTT_MOVE")
        self.assertEqual(_power(after.enemies[0].powers, "OffBalancePower"), 0)

    def test_bowlbug_rock_unblocked_headbutt_keeps_repeating(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        enemy = Enemy("MONSTER.BOWLBUG_ROCK", 45, "HEADBUTT_MOVE", (("IsOffBalance", False),))
        combat = Combat(80, (), (), (), (enemy,))  # no block: Headbutt lands unblocked
        after = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual(after.enemies[0].move, "HEADBUTT_MOVE")
        self.assertEqual(_power(after.enemies[0].powers, "OffBalancePower"), 0)
        self.assertEqual(after.player_hp, 65)

    def test_tunneler_burrow_break_stuns_and_clears_burrowed_power(self) -> None:
        # BurrowedPower.AfterBlockBroken: breaking all 32 Block in one hit immediately stuns
        # Tunneler to DIZZY_MOVE and removes BurrowedPower (data/enemies_hive.json MONSTER.TUNNELER).
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        enemy = Enemy("MONSTER.TUNNELER", 87, "BELOW_MOVE", (), block=32, powers=(("BurrowedPower", 1),))
        combat = Combat(80, (BLUDGEON,), (), (), (enemy,))
        after = step(combat, f"{BLUDGEON}@0", hive, random.Random(0))  # Bludgeon deals exactly 32
        self.assertEqual(
            (after.enemies[0].move, after.enemies[0].block, _power(after.enemies[0].powers, "BurrowedPower")),
            ("DIZZY_MOVE", 0, 0),
        )

    def test_enemy_reported_as_stunned_does_nothing_and_resumes_its_opening_move(self) -> None:
        # The bridge reports MonsterModel.stunnedMoveId ("STUNNED") as the enemy's current move; no
        # export contains that id (1,590 recorded observations).  A stunned monster performs nothing
        # on its turn - a recorded Tunneler at STUNNED left the player at 88 HP across the enemy
        # phase - and resumes its opening move, with the stun id left out of the move history.
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        history = ("BITE_MOVE", "BURROW_MOVE", "BELOW_MOVE", "BELOW_MOVE")
        enemy = Enemy("MONSTER.TUNNELER", 34, "STUNNED", (), history=history)
        combat = Combat(88, (DEFEND,), (), (), (enemy,), player_block=5, energy=1)
        after = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual((after.player_hp, after.enemies[0].move), (88, "BITE_MOVE"))
        self.assertEqual(after.enemies[0].history, history)

    def test_tunneler_dizzy_move_returns_to_bite(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        enemy = Enemy("MONSTER.TUNNELER", 87, "DIZZY_MOVE", ())
        combat = Combat(80, (), (), (), (enemy,))
        after = step(combat, END_TURN, hive, random.Random(0))
        self.assertEqual(after.enemies[0].move, "BITE_MOVE")

    def test_tunneler_partial_hit_keeps_burrowed_power_and_block(self) -> None:
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        enemy = Enemy("MONSTER.TUNNELER", 87, "BELOW_MOVE", (), block=32, powers=(("BurrowedPower", 1),))
        combat = Combat(80, (STRIKE,), (), (), (enemy,))
        after = step(combat, f"{STRIKE}@0", hive, random.Random(0))  # Strike deals 6, well short of 32
        self.assertEqual(
            (after.enemies[0].move, after.enemies[0].block, _power(after.enemies[0].powers, "BurrowedPower")),
            ("BELOW_MOVE", 26, 1),
        )

    def test_tunneler_burrowed_power_normalizes_from_official_id(self) -> None:
        # Regression: POWER_NAMES lacked "POWER.BURROWED_POWER" -> "BurrowedPower", so a real
        # official observation (which reports the power under its "POWER.BURROWED_POWER" id, not
        # the internal name) normalized to the wrong string and this whole stun transition never
        # fired outside of tests that injected "BurrowedPower" directly.
        from official_agent import POWER_NAMES
        with open("data/enemies_hive.json", encoding="utf-8-sig") as file:
            hive = json.load(file)
        normalized = POWER_NAMES.get("POWER.BURROWED_POWER", "POWER.BURROWED_POWER")
        enemy = Enemy("MONSTER.TUNNELER", 87, "BELOW_MOVE", (), block=32, powers=((normalized, 1),))
        combat = Combat(80, (BLUDGEON,), (), (), (enemy,))
        after = step(combat, f"{BLUDGEON}@0", hive, random.Random(0))  # Bludgeon deals exactly 32
        self.assertEqual(
            (after.enemies[0].move, after.enemies[0].block, _power(after.enemies[0].powers, "BurrowedPower")),
            ("DIZZY_MOVE", 0, 0),
        )


if __name__ == "__main__":
    unittest.main()


class GalvanicAndPaperCutsTest(unittest.TestCase):
    """The two enemy mechanics that leave the model optimistic when they are missing."""

    def test_galvanic_charges_hp_for_each_power_card(self) -> None:
        combat = Combat(
            enemies=(Enemy(model="MONSTER.DUMMY", hp=30, move="IDLE_MOVE", values=(),
                           powers=(("GalvanicPower", 6),), primary=True),),
            hand=(INFLAME,), draw_pile=(), discard_pile=(), energy=3, player_hp=50,
        )
        after = step(combat, INFLAME, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_hp, 44)

    def test_paper_cuts_drains_max_hp_only_when_the_hit_lands(self) -> None:
        enemy = Enemy(model="MONSTER.DUMMY", hp=30, move="HIT_MOVE", values=(),
                      powers=(("PaperCutsPower", 2),), primary=True)
        base = Combat(enemies=(enemy,), hand=(), draw_pile=(), discard_pile=(),
                      energy=0, player_hp=50, player_max_hp=80)
        exposed = step(base, END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        blocked = step(replace(base, player_block=99), END_TURN, ATTACKING_DUMMY_DATA, random.Random(0))
        self.assertEqual(exposed.player_max_hp, 78)
        self.assertEqual(blocked.player_max_hp, 80)


class FastenTest(unittest.TestCase):
    """FastenPower boosts block from CardTag.Defend cards only - Defend, not Shrug It Off."""

    def _combat(self, hand, powers=()):
        return Combat(
            enemies=(Enemy(model="MONSTER.DUMMY", hp=30, move="IDLE_MOVE", values=(), primary=True),),
            hand=hand, draw_pile=(), discard_pile=(), energy=3, player_hp=50, player_powers=powers,
        )

    def test_fasten_grants_the_power(self) -> None:
        after = step(self._combat((FASTEN,)), FASTEN, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "FastenPower"), 4)

    def test_fasten_boosts_defend_but_not_shrug(self) -> None:
        powers = (("FastenPower", 4),)
        defended = step(self._combat((DEFEND,), powers), DEFEND, DUMMY_DATA, random.Random(0))
        shrugged = step(self._combat((SHRUG,), powers), SHRUG, DUMMY_DATA, random.Random(0))
        plain = step(self._combat((DEFEND,)), DEFEND, DUMMY_DATA, random.Random(0))
        self.assertEqual(defended.player_block, plain.player_block + 4)
        self.assertEqual(shrugged.player_block, CARD_BLOCK.get(SHRUG, shrugged.player_block))


class DemonFormTest(unittest.TestCase):
    """Demon Form was in hand 218 times across the traces and played once - it had no cost entry."""

    def test_playing_demon_form_grants_the_power(self) -> None:
        combat = Combat(
            enemies=(Enemy(model="MONSTER.DUMMY", hp=30, move="IDLE_MOVE", values=(), primary=True),),
            hand=(DEMON_FORM,), draw_pile=(), discard_pile=(), energy=3, player_hp=50,
        )
        self.assertIn(DEMON_FORM, legal_actions(combat))
        after = step(combat, DEMON_FORM, DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "DemonFormPower"), 2)

    def test_strength_climbs_every_player_turn(self) -> None:
        combat = Combat(
            enemies=(Enemy(model="MONSTER.DUMMY", hp=300, move="IDLE_MOVE", values=(), primary=True),),
            hand=(), draw_pile=(STRIKE,) * 10, discard_pile=(), energy=3, player_hp=50,
            player_powers=(("DemonFormPower", 2),),
        )
        for expected in (2, 4, 6):
            combat = step(combat, END_TURN, DUMMY_DATA, random.Random(0))
            self.assertEqual(_power(combat.player_powers, "StrengthPower"), expected)


class NeowsFuryTest(unittest.TestCase):
    """Neow's Fury hits, then pulls playable cards back out of the discard pile."""

    def _combat(self, discard, hand=()):
        return Combat(
            enemies=(Enemy(model="MONSTER.DUMMY", hp=80, move="IDLE_MOVE", values=(), primary=True),),
            hand=(NEOWS_FURY,) + hand, draw_pile=(), discard_pile=discard, energy=3, player_hp=50,
        )

    def test_deals_damage_and_returns_two_cards(self) -> None:
        combat = self._combat((STRIKE, DEFEND, BASH))
        after = step(combat, NEOWS_FURY + "@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 70)
        self.assertEqual(len(after.hand), 2)
        self.assertEqual(len(after.discard_pile), 1)
        self.assertNotIn(NEOWS_FURY, after.hand)

    def test_skips_junk_when_pulling_from_discard(self) -> None:
        combat = self._combat((STRIKE, WOUND, WOUND))
        after = step(combat, NEOWS_FURY + "@0", DUMMY_DATA, random.Random(0))
        self.assertEqual([card_name(c) for c in after.hand], [STRIKE])


class MadScienceTest(unittest.TestCase):
    """Each Mad Science copy rolls its own CardType and RiderEffect; the bridge reports both."""

    def _combat(self, card):
        return Combat(
            enemies=(Enemy(model="MONSTER.DUMMY", hp=80, move="IDLE_MOVE", values=(), primary=True),),
            hand=(card,), draw_pile=(STRIKE,) * 5, discard_pile=(), energy=3, player_hp=50,
        )

    def test_attack_copy_hits_once(self) -> None:
        card = Card(MAD_SCIENCE, variant="Attack", variant_value=16)
        after = step(self._combat(card), "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 64)

    def test_attack_applies_strength_weak_and_target_vulnerable_once(self) -> None:
        for strength, weak, vulnerable, expected in ((4, 0, 1, 24), (4, 0, 0, 16), (10, 1, 1, 24)):
            with self.subTest(strength=strength, weak=weak, vulnerable=vulnerable):
                card = Card(MAD_SCIENCE, upgraded=True, variant="Attack", variant_value=12)
                state = replace(self._combat(card), player_powers=(("StrengthPower", strength), ("WeakPower", weak)))
                state = replace(state, enemies=(replace(state.enemies[0], powers=(("VulnerablePower", vulnerable),)),))
                after = step(state, "card:0@0", DUMMY_DATA, random.Random(0))
                self.assertEqual(after.enemies[0].hp, 80 - expected)
                self.assertEqual(after.attacks_played_combat, 1)

    def test_sapping_repeat_sees_pen_nib_and_its_first_vulnerable(self) -> None:
        card = Card(MAD_SCIENCE, variant="Attack", rider="Sapping", variant_value=12)
        state = replace(self._combat(card), player_powers=(("StrengthPower", 4), ("DuplicationPower", 1)),
                        player_relics=(RELIC_PEN_NIB,), relic_counters=((RELIC_PEN_NIB, 9),))
        after = step(state, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 80 - 32 - 24)
        self.assertEqual(dict(after.relic_counters)[RELIC_PEN_NIB], 1)
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 4)

    def test_sapping_uses_artifact_for_weak_before_vulnerable(self) -> None:
        card = Card(MAD_SCIENCE, variant="Attack", rider="Sapping", variant_value=12)
        state = self._combat(card)
        state = replace(state, enemies=(replace(state.enemies[0], powers=(("ArtifactPower", 1),)),))
        after = step(state, "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 68)
        self.assertEqual(_power(after.enemies[0].powers, "WeakPower"), 0)
        self.assertEqual(_power(after.enemies[0].powers, "VulnerablePower"), 2)

    def test_skill_modifiers_and_saved_skill_counter_use_its_actual_type(self) -> None:
        card = Card(MAD_SCIENCE, variant="Skill", variant_value=8)
        state = replace(self._combat(card), player_powers=(("DexterityPower", 2), ("FrailPower", 1)),
                        player_relics=("RELIC.TUNING_FORK",), relic_counters=(("RELIC.TUNING_FORK", 9),))
        after = step(state, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 7 + 7)
        self.assertEqual(after.skills_played_combat, 1)

    def test_power_uses_curious_discount_and_leaves_combat(self) -> None:
        card = Card(MAD_SCIENCE, variant="Power", rider="Expertise")
        state = replace(self._combat(card), player_powers=(("CuriousPower", 1),), player_relics=(RELIC_LOST_WISP,))
        after = step(state, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 3)
        self.assertEqual(after.powers_played_this_turn, 1)
        self.assertEqual(after.discard_pile, ())
        self.assertEqual(after.enemies[0].hp, 72)

    def test_second_wind_keeps_attack_copy_and_exhausts_skill_copy(self) -> None:
        attack = Card(MAD_SCIENCE, variant="Attack", variant_value=12)
        skill = Card(MAD_SCIENCE, variant="Skill", variant_value=8)
        state = replace(self._combat(attack), hand=(SECOND_WIND, attack, skill, DEFEND))
        after = step(state, SECOND_WIND, DUMMY_DATA, random.Random(0))
        self.assertEqual(after.hand, (attack,))
        self.assertEqual(after.player_block, 10)
        self.assertIn(skill, after.exhaust_pile)

    def test_violence_rider_hits_three_times(self) -> None:
        card = Card(MAD_SCIENCE, variant="Attack", rider="Violence", variant_value=16)
        after = step(self._combat(card), "card:0@0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.enemies[0].hp, 80 - 48)

    def test_skill_copy_blocks_and_needs_no_target(self) -> None:
        card = Card(MAD_SCIENCE, variant="Skill", variant_value=8)
        combat = self._combat(card)
        self.assertIn("card:0", legal_actions(combat))
        after = step(combat, "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.player_block, 8)

    def test_power_copy_with_expertise_grants_strength_and_dexterity(self) -> None:
        card = Card(MAD_SCIENCE, variant="Power", rider="Expertise")
        after = step(self._combat(card), "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(_power(after.player_powers, "StrengthPower"), 2)
        self.assertEqual(_power(after.player_powers, "DexterityPower"), 2)

    def test_energized_rider_refunds_energy(self) -> None:
        card = Card(MAD_SCIENCE, variant="Skill", rider="Energized", variant_value=8)
        after = step(self._combat(card), "card:0", DUMMY_DATA, random.Random(0))
        self.assertEqual(after.energy, 3 - 1 + 2)
