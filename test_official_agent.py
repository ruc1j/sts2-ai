import unittest

from official_agent import CARD_TIERS, RELIC_SCORES, choose, choose_card_reward, choose_event, choose_map, choose_rest, choose_shop


class OfficialAgentTest(unittest.TestCase):
    def test_prefers_bash(self) -> None:
        actions = [
            {"type": "end_turn"},
            {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD"},
            {"type": "card", "card_id": "CARD.BASH"},
        ]
        self.assertEqual(choose({"legal_actions": actions})["card_id"], "CARD.BASH")

    def test_blocks_incoming_damage(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD"},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD"},
            ],
            "player": {"block": 0},
            "enemies": [{"combat_id": 1, "hp": 20, "intents": [{"damage": 8, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_map_looks_ahead(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Boss", "children": []},
                {"col": 1, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_prefers_nearest_reachable_rest(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Treasure", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": []},
                {"col": 1, "row": 1, "type": "Monster", "children": [{"col": 1, "row": 2}]},
                {"col": 1, "row": 2, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_low_hp_avoids_elite_on_equally_short_rest_route(self) -> None:
        observation = {
            "player": {"hp": 40, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Elite", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "RestSite", "children": [{"col": 0, "row": 2}]},
                {"col": 1, "row": 1, "type": "RestSite", "children": []},
                {"col": 0, "row": 2, "type": "Treasure", "children": [{"col": 0, "row": 3}]},
                {"col": 0, "row": 3, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_ignores_unreachable_rest_routes(self) -> None:
        observation = {
            "player": {"hp": 39, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Treasure", "children": []},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 1, "row": 1, "type": "RestSite", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_prefers_unknown_when_no_rest_is_reachable(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Unknown", "children": []},
                {"col": 0, "row": 1, "type": "Treasure", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_low_hp_uses_existing_value_when_all_routes_fight(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 1}]},
                {"col": 1, "row": 0, "type": "Monster", "children": [{"col": 1, "row": 1}]},
                {"col": 0, "row": 1, "type": "Treasure", "children": []},
                {"col": 1, "row": 1, "type": "Unknown", "children": []},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 0)

    def test_low_hp_map_cycle_is_safe(self) -> None:
        observation = {
            "player": {"hp": 20, "max_hp": 80},
            "map": {"points": [
                {"col": 0, "row": 0, "type": "Monster", "children": [{"col": 0, "row": 0}]},
                {"col": 1, "row": 0, "type": "Unknown", "children": [{"col": 1, "row": 0}]},
            ]},
            "legal_actions": [{"type": "map", "col": 0, "row": 0}, {"type": "map", "col": 1, "row": 0}],
        }
        self.assertEqual(choose_map(observation)["col"], 1)

    def test_reward_prefers_known_strong_card(self) -> None:
        observation = {
            "cards": [
                {"id": "CARD.STRIKE", "rarity": "Common"},
                {"id": "CARD.BLUDGEON", "rarity": "Rare"},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.STRIKE"},
                {"type": "card_reward", "card_id": "CARD.BLUDGEON"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BLUDGEON")

    def test_reward_skips_unsupported_cards(self) -> None:
        observation = {
            "cards": [{"id": "CARD.UNKNOWN", "rarity": "Uncommon"}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_takes_anger_for_the_normal_fights(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

    def test_reward_skips_unknown_skill(self) -> None:
        observation = {
            "cards": [{"id": "CARD.UNKNOWN_SKILL", "type": "Skill", "rarity": "Uncommon", "cost": 1}],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_SKILL"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_uses_metadata_for_unknown_attack(self) -> None:
        observation = {
            "cards": [
                {"id": "CARD.UNKNOWN_COMMON", "type": "Attack", "rarity": "Common", "cost": 0},
                {"id": "CARD.UNKNOWN_RARE_EXPENSIVE", "type": "Attack", "rarity": "Rare", "cost": 2},
                {"id": "CARD.UNKNOWN_RARE_CHEAP", "type": "Attack", "rarity": "Rare", "cost": 1},
                {"id": "CARD.UNKNOWN_SKILL", "type": "Skill", "rarity": "Rare", "cost": 0},
            ],
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_COMMON"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_RARE_EXPENSIVE"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_RARE_CHEAP"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN_SKILL"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.UNKNOWN_RARE_CHEAP")

    def test_reward_keeps_known_card_for_a_large_deck(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE"}] * 14},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_rest_heals_when_hurt(self) -> None:
        observation = {
            "player": {"hp": 37, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HEAL")

    def test_rest_heals_before_boss(self) -> None:
        observation = {
            "player": {"hp": 64, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HEAL")

    def test_rest_hatches_egg_when_healthy(self) -> None:
        observation = {
            "player": {"hp": 65, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}, {"option_id": "HATCH"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HATCH")

    def test_uses_lethal_fire_potion(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.FIRE_POTION", "target_id": 7}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 20, "intents": []}],
        }
        self.assertEqual(choose(observation)["type"], "potion")

    def test_uses_dexterity_potion_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None}],
            "player": {"hp": 40, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")

    def test_uses_regen_potion_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None}],
            "player": {"hp": 36, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.REGEN_POTION")

    def test_low_hp_multiple_enemies_falls_back_to_dexterity(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.DEXTERITY_POTION", "target_id": None}],
            "player": {"hp": 15, "max_hp": 80},
            "hand": [],
            "enemies": [
                {"combat_id": 1, "hp": 30, "intents": []},
                {"combat_id": 2, "hp": 30, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.DEXTERITY_POTION")

    def test_low_hp_incoming_falls_back_to_regen(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.REGEN_POTION", "target_id": None}],
            "player": {"hp": 36, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 30, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.REGEN_POTION")

    def test_low_hp_lethal_incoming_uses_lucky_tonic_first(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None},
                {"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.LUCKY_TONIC")

    def test_high_hp_half_incoming_saves_lucky_tonic(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 48, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 24, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_pre_hit_low_quarter_uses_lucky_tonic(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.LUCKY_TONIC", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 44, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 33, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.LUCKY_TONIC")

    def test_low_hp_uses_unknown_manual_potion_as_safe_fallback(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.UNKNOWN_MANUAL", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.UNKNOWN_MANUAL")

    def test_low_hp_uses_offensive_selection_potion(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_index": 0, "potion_id": "POTION.POWER_POTION", "target_id": None},
                {"type": "potion", "potion_index": 1, "potion_id": "POTION.FLEX_POTION", "target_id": None},
                {"type": "potion", "potion_index": 2, "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 8, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.POWER_POTION")

    def test_lethal_incoming_uses_attack_potion_when_no_defense_exists(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_index": 1, "potion_id": "POTION.COLORLESS_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 12, "max_hp": 80},
            "enemies": [{"combat_id": 1, "hp": 143, "intents": [{"damage": 20, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.COLORLESS_POTION")

    def test_explosive_ampoule_is_used_against_multiple_enemies_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.EXPLOSIVE_AMPOULE", "target_id": 1}],
            "player": {"hp": 20, "max_hp": 80},
            "enemies": [
                {"combat_id": 1, "hp": 28, "intents": []},
                {"combat_id": 2, "hp": 34, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.EXPLOSIVE_AMPOULE")

    def test_energy_potion_requires_a_payable_hand_card(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "potion", "potion_id": "POTION.ENERGY_POTION", "target_id": None},
                {"type": "end_turn"},
            ],
            "player": {"hp": 20, "max_hp": 80},
            "hand": [{"index": 0, "cost": 0}],
            "enemies": [
                {"combat_id": 1, "hp": 28, "intents": []},
                {"combat_id": 2, "hp": 34, "intents": []},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_strength_potion_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.STRENGTH_POTION", "target_id": None}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 123, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.STRENGTH_POTION")

    def test_uses_power_potion_proactively_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.POWER_POTION", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.POWER_POTION")

    def test_uses_colorless_potion_proactively_against_high_health_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.COLORLESS_POTION", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 80, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 173, "intents": []}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.COLORLESS_POTION")

    def test_uses_weak_potion_against_lethal_enemy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.WEAK_POTION", "target_id": 7}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [{"combat_id": 7, "hp": 40, "intents": [{"damage": 12, "repeats": 1}]}],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.WEAK_POTION")

    def test_uses_entropic_brew_when_low(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.ENTROPIC_BREW", "target_id": None}],
            "player": {"hp": 30, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["potion_id"], "POTION.ENTROPIC_BREW")

    def test_does_not_manually_use_fairy(self) -> None:
        observation = {
            "legal_actions": [{"type": "potion", "potion_id": "POTION.FAIRY_IN_A_BOTTLE", "target_id": None}, {"type": "end_turn"}],
            "player": {"hp": 10, "max_hp": 80},
            "enemies": [],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_uses_frantic_escape_before_other_cards(self) -> None:
        observation = {
            "enemies": [{"powers": [{"id": "POWER.SANDPIT_POWER", "amount": 2}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0},
                {"type": "card", "card_id": "CARD.FRANTIC_ESCAPE", "hand_index": 1},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.FRANTIC_ESCAPE")

    def test_targets_crab_to_face_the_larger_attack(self) -> None:
        observation = {
            "player": {"powers": [{"id": "POWER.SURROUNDED_POWER", "amount": 1, "facing": "Right"}]},
            "hand": [{"index": 0, "type": "Attack"}],
            "enemies": [{"combat_id": 7, "powers": [{"id": "POWER.BACK_ATTACK_LEFT_POWER", "amount": 1}], "intents": [{"damage": 12, "repeats": 1}]}],
            "legal_actions": [{"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 7}],
        }
        self.assertEqual(choose(observation)["target_id"], 7)

    def test_unknown_card_does_not_crash_fallback(self) -> None:
        observation = {
            "player": {"block": 0},
            "hand": [{"index": 0, "type": "Attack", "vars": []}],
            "enemies": [{"combat_id": 1, "hp": 20, "intents": []}],
            "legal_actions": [{"type": "card", "card_id": "CARD.UNKNOWN", "hand_index": 0, "target_id": 1}, {"type": "end_turn"}],
        }
        self.assertEqual(choose(observation)["type"], "card")

    def test_fallback_uses_observed_damage_for_unknown_card(self) -> None:
        observation = {
            "player": {"block": 0},
            "hand": [{"index": 0, "type": "Attack", "vars": [{"id": "Damage", "value": 20}]}],
            "enemies": [{"combat_id": 1, "hp": 20, "block": 0, "intents": []}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.UNKNOWN_ATTACK", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.UNKNOWN_ATTACK")

    def test_fallback_uses_observed_block_for_unknown_card(self) -> None:
        observation = {
            "player": {"block": 0},
            "hand": [
                {"index": 0, "type": "Skill", "vars": [{"id": "Block", "value": 10}]},
                {"index": 1, "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 20, "intents": [{"damage": 10, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.UNKNOWN_SKILL", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 1, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.UNKNOWN_SKILL")

    def test_low_hp_avoids_uncommitted_self_damage_when_attack_and_defend_are_legal(self) -> None:
        observation = {
            "player": {"hp": 28, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 15}]},
                {"index": 2, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
                {"index": 3, "id": "CARD.DEFEND_IRONCLAD", "type": "Skill", "vars": [{"id": "Block", "value": 5}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 2, "target_id": 1},
                {"type": "card", "card_id": "CARD.DEFEND_IRONCLAD", "hand_index": 3, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_low_hp_avoids_self_damage_for_a_safe_card_without_observed_damage_or_block(self) -> None:
        observation = {
            "player": {"hp": 28, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.CINDER", "type": "Skill", "vars": []},
                {"index": 2, "id": "CARD.INFLAME", "type": "Power", "vars": []},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.CINDER", "hand_index": 1, "target_id": None},
                {"type": "card", "card_id": "CARD.INFLAME", "hand_index": 2, "target_id": None},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.CINDER")

    def test_low_hp_ends_turn_when_only_self_damage_cards_are_legal(self) -> None:
        observation = {
            "player": {"hp": 14, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BLOODLETTING", "type": "Skill", "vars": [{"id": "Damage", "value": 3}]},
                {"index": 1, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 15}]},
            ],
            "enemies": [{"combat_id": 1, "hp": 50, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BLOODLETTING", "hand_index": 0, "target_id": None},
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 1, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["type"], "end_turn")

    def test_lethal_self_damage_remains_allowed_to_finish_enemy(self) -> None:
        observation = {
            "player": {"hp": 14, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.HEMOKINESIS", "type": "Attack", "vars": [{"id": "Damage", "value": 50}]}],
            "enemies": [{"combat_id": 1, "hp": 20, "intents": [{"type": "SingleAttackIntent", "damage": 12, "repeats": 1}]}],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.HEMOKINESIS", "hand_index": 0, "target_id": 1},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.HEMOKINESIS")

    def test_lethal_prefers_killing_the_enemy_that_will_attack(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 5, "block": 0, "intents": [{"damage": 22, "repeats": 1}]},
                {"combat_id": 2, "hp": 5, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 1)

    def test_lethal_prefers_weaker_enemy_when_both_attack(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 9, "block": 0, "intents": [{"damage": 10, "repeats": 1}]},
                {"combat_id": 2, "hp": 3, "block": 0, "intents": [{"damage": 10, "repeats": 1}]},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_focus_fire_prefers_weakest_enemy_when_nothing_is_lethal(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": []},
                {"combat_id": 2, "hp": 20, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_lethal_ignores_slippery_enemy(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]}],
            "enemies": [
                {"combat_id": 1, "hp": 5, "block": 0, "powers": [{"id": "POWER.SLIPPERY_POWER", "amount": 8}], "intents": []},
                {"combat_id": 2, "hp": 5, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_lethal_accounts_for_hard_to_kill_cap(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [{"index": 0, "id": "CARD.GIANT_ROCK", "type": "Attack", "vars": [{"id": "Damage", "value": 16}]}],
            "enemies": [
                # 16 damage is capped at 9 by HardToKill, so this Exoskeleton is NOT lethal.
                {"combat_id": 1, "hp": 12, "block": 0, "powers": [{"id": "POWER.HARD_TO_KILL_POWER", "amount": 9}], "intents": []},
                {"combat_id": 2, "hp": 10, "block": 0, "powers": [], "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.GIANT_ROCK", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.GIANT_ROCK", "hand_index": 0, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["target_id"], 2)

    def test_rest_heals_near_boss(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 14},
            "player": {"hp": 64, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}, {"option_id": "HATCH"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HEAL")

    def test_rest_hatches_mid_act_when_healthy(self) -> None:
        observation = {
            "run": {"act": 1, "floor": 5},
            "player": {"hp": 64, "max_hp": 80},
            "legal_actions": [{"option_id": "SMITH"}, {"option_id": "HEAL"}, {"option_id": "HATCH"}],
        }
        self.assertEqual(choose_rest(observation)["option_id"], "HATCH")

    def test_focus_fire_does_not_change_card_priority(self) -> None:
        observation = {
            "player": {"hp": 80, "max_hp": 80, "block": 0},
            "hand": [
                {"index": 0, "id": "CARD.BASH", "type": "Attack", "vars": [{"id": "Damage", "value": 8}]},
                {"index": 1, "id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "vars": [{"id": "Damage", "value": 6}]},
            ],
            "enemies": [
                {"combat_id": 1, "hp": 50, "block": 0, "intents": []},
                {"combat_id": 2, "hp": 20, "block": 0, "intents": []},
            ],
            "legal_actions": [
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 0, "target_id": 1},
                {"type": "card", "card_id": "CARD.BASH", "hand_index": 0, "target_id": 2},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 1},
                {"type": "card", "card_id": "CARD.STRIKE_IRONCLAD", "hand_index": 1, "target_id": 2},
                {"type": "end_turn"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.BASH")

    def test_reward_takes_modeled_bully(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BULLY"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BULLY")

    def test_shop_buys_one_missing_required_card(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD"],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "buy_card", "card_id": "CARD.RUPTURE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_shop_removes_defend_after_perfected_strike(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.STRIKE_IRONCLAD", "CARD.PERFECTED_STRIKE", "CARD.DEFEND_IRONCLAD"],
            "legal_actions": [
                {"type": "remove", "card_id": "CARD.STRIKE_IRONCLAD"},
                {"type": "remove", "card_id": "CARD.DEFEND_IRONCLAD"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.DEFEND_IRONCLAD")

    def test_reward_prefers_tier_card_over_unknown_card(self) -> None:
        observation = {
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.UNKNOWN"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_core_beats_s_tier_card(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_prefers_perfected_strike_over_vulnerable_core_when_unresolved(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.TREMBLE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_strike_axis_prefers_second_perfected_strike(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.PERFECTED_STRIKE"}, {"id": "CARD.STRIKE_IRONCLAD"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_without_strike_axis_keeps_first_tier_card(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.RUPTURE"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.RUPTURE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TRUE_GRIT")

    def test_reward_switches_core_after_axis_is_owned(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.PERFECTED_STRIKE"}, {"id": "CARD.RUPTURE"}]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.HELLRAISER"},
                {"type": "card_reward", "card_id": "CARD.TEAR_ASUNDER"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.HELLRAISER")

    def test_shop_core_beats_s_tier_card_and_buys_once(self) -> None:
        observation = {
            "phase": "shop",
            "deck": [],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "buy_card", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_shop_strike_axis_does_not_buy_rupture(self) -> None:
        observation = {
            "phase": "shop",
            "deck": ["CARD.PERFECTED_STRIKE"],
            "legal_actions": [
                {"type": "buy_card", "card_id": "CARD.RUPTURE"},
                {"type": "skip"},
            ],
        }
        self.assertEqual(choose_shop(observation)["type"], "skip")

    def test_unresolved_deck_uses_tiers_without_random_core(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_uncommitted_self_damage_does_not_force_bloodletting(self) -> None:
        observation = {
            "player": {"deck": []},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_self_damage_axis_prefers_follow_up(self) -> None:
        observation = {
            "player": {"deck": ["CARD.RUPTURE"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TEAR_ASUNDER"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TEAR_ASUNDER")

    def test_vulnerable_axis_prefers_missing_apply(self) -> None:
        observation = {
            "player": {"deck": ["CARD.BASH", "CARD.MOLTEN_FIST"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.TREMBLE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TREMBLE")

    def test_exhaust_axis_prefers_missing_payoff(self) -> None:
        observation = {
            "player": {"deck": ["CARD.TRUE_GRIT", "CARD.CORRUPTION"]},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.DARK_EMBRACE"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.DARK_EMBRACE")

    def test_reward_prefers_defense_when_deck_lacks_block(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.SHRUG_IT_OFF")

    def test_reward_keeps_s_tier_offense_when_deck_is_balanced(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 6 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4 + [{"id": "CARD.ANGER"}] * 2},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward", "card_id": "CARD.BATTLE_TRANCE"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.BATTLE_TRANCE")

    def test_reward_defense_does_not_override_core(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.PERFECTED_STRIKE"},
                {"type": "card_reward", "card_id": "CARD.SHRUG_IT_OFF"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.PERFECTED_STRIKE")

    def test_reward_never_takes_relax_when_alternatives_exist(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RELAX"},
                {"type": "card_reward", "card_id": "CARD.ANGER"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.ANGER")

    def test_reward_skips_when_only_relax_is_offered(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.RELAX"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["option_id"], "Skip")

    def test_reward_defense_wins_tie_against_self_damage_offense(self) -> None:
        observation = {
            "player": {"deck": [{"id": "CARD.STRIKE_IRONCLAD"}] * 10 + [{"id": "CARD.DEFEND_IRONCLAD"}] * 4},
            "legal_actions": [
                {"type": "card_reward", "card_id": "CARD.BLOODLETTING"},
                {"type": "card_reward", "card_id": "CARD.TRUE_GRIT"},
                {"type": "card_reward_alternative", "option_id": "Skip"},
            ],
        }
        self.assertEqual(choose_card_reward(observation)["card_id"], "CARD.TRUE_GRIT")

    def test_event_never_picks_paels_horn(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_HORN"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_FLESH"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_event_prefers_energy_over_weaker_relic(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_EYE"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_LEGION"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_LEGION")

    def test_event_block_starved_prefers_block_pet(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 80, "max_hp": 80},
            "deck": ["CARD.STRIKE_IRONCLAD"] * 12,
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_FLESH"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_LEGION"},
            ],
        }
        # Block pet gets +2 for block-starved decks but still loses to +1 max energy.
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_event_low_hp_boosts_energy_relics(self) -> None:
        observation = {
            "phase": "event",
            "player": {"hp": 30, "max_hp": 80},
            "legal_actions": [
                {"type": "event_relic", "option_index": 0, "relic_id": "RELIC.PAELS_FLESH"},
                {"type": "event_relic", "option_index": 1, "relic_id": "RELIC.PAELS_HORN"},
            ],
        }
        self.assertEqual(choose_event(observation)["relic_id"], "RELIC.PAELS_FLESH")

    def test_event_relic_scores_cover_all_ancients(self) -> None:
        pael = {"RELIC.PAELS_CLAW", "RELIC.PAELS_TOOTH", "RELIC.PAELS_GROWTH", "RELIC.PAELS_LEGION",
                "RELIC.PAELS_FLESH", "RELIC.PAELS_TEARS", "RELIC.PAELS_HORN", "RELIC.PAELS_WING",
                "RELIC.PAELS_EYE", "RELIC.PAELS_BLOOD"}
        orobas = {"RELIC.ELECTRIC_SHRYMP", "RELIC.GLASS_EYE", "RELIC.SAND_CASTLE", "RELIC.ALCHEMICAL_COFFER",
                  "RELIC.DRIFTWOOD", "RELIC.RADIANT_PEARL", "RELIC.PRISMATIC_GEM"}
        tezcatara = {"RELIC.NUTRITIOUS_SOUP", "RELIC.VERY_HOT_COCOA", "RELIC.YUMMY_COOKIE", "RELIC.BIIIG_HUG",
                     "RELIC.STORYBOOK", "RELIC.TOASTY_MITTENS", "RELIC.GOLDEN_COMPASS", "RELIC.PUMPKIN_CANDLE",
                     "RELIC.TOY_BOX", "RELIC.SEAL_OF_GOLD"}
        self.assertTrue(pael <= RELIC_SCORES.keys())
        self.assertTrue(orobas <= RELIC_SCORES.keys())
        self.assertTrue(tezcatara <= RELIC_SCORES.keys())

    def test_card_tiers_include_the_required_axes(self) -> None:
        self.assertEqual(CARD_TIERS["CARD.PERFECTED_STRIKE"], "C")
        self.assertEqual(CARD_TIERS["CARD.RUPTURE"], "C")
        self.assertEqual(CARD_TIERS["CARD.TREMBLE"], "S")
        self.assertEqual(CARD_TIERS["CARD.CORRUPTION"], "A")

    def test_card_tiers_cover_source_unranked_cards(self) -> None:
        known = {"CARD.MIDNIGHT", "CARD.TANK", "CARD.BLAZE", "CARD.DEMONIC_SHIELD", "CARD.OUTRAGE"}
        self.assertTrue(known <= CARD_TIERS.keys())
        self.assertEqual({CARD_TIERS[card] for card in known}, {"D"})


if __name__ == "__main__":
    unittest.main()
