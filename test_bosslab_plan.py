"""Tests for the BossLab plan generator (bosslab/tools/make_bosslab_plan.py).

The plan tool turns fixed-entry specs into the trial list official_mod/BossLab.cs reads. These tests
feed it a two-spec fixture (one Act 2 entry, one Act 3 Queen entry carrying an enchantment, a
relic-granted power, and a residual power) and check what lands in the trials.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
TOOL = REPO / "bosslab" / "tools" / "make_bosslab_plan.py"

ACT2_SPEC = {
    "spec_id": "aaaaaaaaaaaa",
    "encounter_hint": "ENCOUNTER.THE_INSATIABLE_BOSS",
    "run_seed": "SEEDAAAAAA",
    "act_index": 1,
    "act_floor": 16,
    "total_floor_including_boss": 34,
    "history_per_act": [17, 16],
    "room_type": "Boss",
    "character": "CHARACTER.IRONCLAD",
    "unresolved": [],
    "player": {"hp": 70, "max_hp": 80, "block": 0, "energy": 3, "max_energy": 3,
               "relics": ["RELIC.BURNING_BLOOD"], "relic_counters": {}, "powers": []},
    "potions": ["POTION.FIRE_POTION"],
    "piles": {"hand": [{"id": "CARD.STRIKE_IRONCLAD", "upgrade": 0, "enchantment": "",
                        "vars_grown": False},
                       {"id": "CARD.DEFEND_IRONCLAD", "upgrade": 1, "enchantment": "",
                        "vars_grown": False}],
              "draw_pile": [], "discard_pile": [], "exhaust_pile": []},
    "deck_size": 2,
    "enemies": [{"id": "MONSTER.THE_INSATIABLE", "hp": 321, "max_hp": 321}],
    "recorded_outcome": {"won": False, "end_hp": 0},
    "sources": [{"trace": "fixture_SEEDAAAAAA_agent.jsonl", "tag": "fixture",
                 "seed": "SEEDAAAAAA", "entry_seq": 1}],
}

ACT3_SPEC = {
    "spec_id": "bbbbbbbbbbbb",
    "encounter_hint": "ENCOUNTER.QUEEN_BOSS",
    "run_seed": "SEEDBBBBBB",
    "act_index": 2,
    "act_floor": 15,
    "total_floor_including_boss": 48,
    "history_per_act": [17, 16, 14],
    "room_type": "Boss",
    "character": "CHARACTER.IRONCLAD",
    "unresolved": [],
    "entry_powers_observed": {"STRENGTH_POWER": 3, "RAGE_POWER": 5},
    "entry_powers_expected_from_relics": {"STRENGTH_POWER": 3},
    "entry_powers_residual": [{"id": "POWER.RAGE_POWER", "amount": 5}],
    "entry_mid_turn": False,
    "card_value_state": [],
    "relic_run_state": [],
    "player": {"hp": 68, "max_hp": 68, "block": 0, "energy": 3, "max_energy": 3,
               "relics": ["REL.BURNING_BLOOD", "RELIC.SWORD_OF_JADE"], "relic_counters": {},
               "powers": [{"id": "POWER.STRENGTH_POWER", "amount": 3},
                          {"id": "POWER.RAGE_POWER", "amount": 5}]},
    "potions": [],
    "piles": {"hand": [{"id": "CARD.STRIKE_IRONCLAD", "upgrade": 0,
                        "enchantment": "ENCHANTMENT.TEZCATARAS_EMBER", "enchantment_amount": 1,
                        "grown": []},
                       {"id": "CARD.SHRUG_IT_OFF", "upgrade": 0, "enchantment": "",
                        "enchantment_amount": 0, "grown": []}],
              "draw_pile": [], "discard_pile": [], "exhaust_pile": []},
    "deck_size": 2,
    "enemies": [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400},
                {"id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": 199, "max_hp": 199}],
    "recorded_outcome": {"won": False, "end_hp": 0},
    "sources": [{"trace": "fixture_SEEDBBBBBB_agent.jsonl", "tag": "fixture",
                 "seed": "SEEDBBBBBB", "entry_seq": 1}],
}


def run_tool(specs: list[dict], extra_args: list[str]) -> tuple[dict, Path]:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        spec_path = root / "specs.jsonl"
        spec_path.write_text("".join(json.dumps(s) + "\n" for s in specs), encoding="utf-8")
        out = root / "plan.json"
        command = [sys.executable, str(TOOL), "--specs", str(spec_path), "--out", str(out),
                   "--md", str(root / "plan.md")] + extra_args
        subprocess.run(command, check=True, capture_output=True, text=True)
        plan = json.loads(out.read_text(encoding="utf-8"))
        plan_path = out
    plan["_plan_path"] = str(plan_path)
    return plan, plan_path


def load_entry_effects():
    module_spec = importlib.util.spec_from_file_location(
        "relic_entry_effects", REPO / "bosslab" / "tools" / "relic_entry_effects.py")
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class BossLabPlanTest(unittest.TestCase):
    def setUp(self) -> None:
        if not TOOL.is_file():
            self.skipTest(f"{TOOL} is not present in this checkout")

    def test_act3_trial_carries_act_floor_history_and_encounter(self) -> None:
        plan, _ = run_tool([ACT3_SPEC], ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"])
        trial = plan["trials"][0]
        self.assertEqual(trial["encounter"], "ENCOUNTER.QUEEN_BOSS")
        self.assertEqual(trial["act_index"], 2)
        self.assertEqual(trial["act_floor"], 15)
        # Walked floors per act, excluding the boss room itself (EnterRoomDebug appends it).
        self.assertEqual(trial["history_per_act"], [17, 16, 14])
        self.assertEqual(trial["run_seed"], "SEEDBBBBBB")
        self.assertEqual(plan["encounters"], ["ENCOUNTER.QUEEN_BOSS"])

    def test_act3_trial_carries_enchantment_and_residual_powers(self) -> None:
        plan, _ = run_tool([ACT3_SPEC], ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"])
        trial = plan["trials"][0]
        enchanted = [card for card in trial["deck"] if card.get("enchantment")]
        self.assertEqual(len(enchanted), 1)
        self.assertEqual(enchanted[0]["id"], "CARD.STRIKE_IRONCLAD")
        self.assertEqual(enchanted[0]["enchantment"], "ENCHANTMENT.TEZCATARAS_EMBER")
        self.assertEqual(enchanted[0]["enchantment_amount"], 1)
        self.assertNotIn("enchantment", next(c for c in trial["deck"]
                                             if c["id"] == "CARD.SHRUG_IT_OFF"))
        # Only the leftover power is injected; Strength 3 comes from the injected relic list itself.
        self.assertEqual(trial["powers"], [{"id": "POWER.RAGE_POWER", "amount": 5}])

    def test_restore_entry_state_is_opt_in_and_carries_enemies_and_piles(self) -> None:
        spec = dict(ACT3_SPEC)
        spec["enemies"] = [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400}]
        base_args = ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"]
        plain, _ = run_tool([spec], base_args)
        for key in ("restore_entry_state", "enemies", "piles"):
            self.assertNotIn(key, plain["trials"][0])
        plan, _ = run_tool([spec], base_args + ["--restore-entry-state"])
        trial = plan["trials"][0]
        self.assertTrue(trial["restore_entry_state"])
        self.assertEqual(trial["enemies"], [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400}])
        self.assertEqual([p["pile_type"] for p in trial["piles"]], ["hand", "draw", "discard", "exhaust"])
        # Only the entry-state keys differ from the plain plan.
        extra = {"restore_entry_state", "enemies", "piles"}
        self.assertEqual({k: v for k, v in trial.items() if k not in extra}, plain["trials"][0])

    def test_unresolved_spec_is_dropped_without_the_flag(self) -> None:
        blocked = dict(ACT3_SPEC)
        blocked["unresolved"] = ["relic_counters"]
        plan, _ = run_tool([blocked], ["--arm", "base", "--max-specs", "5", "--trials-per-arm", "1"])
        self.assertEqual(plan["trials"], [])
        plan, _ = run_tool([blocked], ["--arm", "base", "--max-specs", "5", "--trials-per-arm", "1",
                                       "--allow-unresolved"])
        self.assertEqual(len(plan["trials"]), 1)

    def test_skip_specs_keeps_panels_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            skip = Path(raw) / "skip.txt"
            skip.write_text(ACT3_SPEC["spec_id"] + "\n", encoding="utf-8")
            plan, _ = run_tool([ACT2_SPEC, ACT3_SPEC],
                               ["--arm", "base", "--max-specs", "5", "--trials-per-arm", "1",
                                "--skip-specs", str(skip)])
            self.assertEqual({trial["spec_id"] for trial in plan["trials"]}, {"aaaaaaaaaaaa"})

    def test_arm_mutation_still_adds_plain_card(self) -> None:
        plan, _ = run_tool([ACT3_SPEC], ["--arm", "base", "--arm",
                                         "+trance=+CARD.BATTLE_TRANCE", "--max-specs", "1",
                                         "--trials-per-arm", "1"])
        arms = {trial["arm"]: trial for trial in plan["trials"]}
        self.assertEqual(sorted(arms), ["+trance", "base"])
        added = [card for card in arms["+trance"]["deck"] if card["id"] == "CARD.BATTLE_TRANCE"]
        self.assertEqual(added, [{"id": "CARD.BATTLE_TRANCE", "upgrade": 0}])
        self.assertEqual(len(arms["+trance"]["deck"]), len(arms["base"]["deck"]) + 1)

    def test_act2_specs_still_work_without_the_new_fields(self) -> None:
        plan, _ = run_tool([ACT2_SPEC], ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"])
        trial = plan["trials"][0]
        self.assertEqual(trial["act_index"], 1)
        self.assertEqual(trial["act_floor"], 16)
        self.assertEqual(trial["powers"], [])
        self.assertNotIn("enchantment", trial["deck"][0])

    def test_trial_without_entry_effect_relics_carries_empty_lists(self) -> None:
        plan, _ = run_tool([ACT3_SPEC], ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"])
        trial = plan["trials"][0]
        self.assertEqual([], trial["defer_relics"])
        self.assertEqual([], trial["flag_relics"])

    def test_trial_carries_defer_and_flag_relics_from_the_entry_effect_table(self) -> None:
        """STONE_CRACKER は入室後に付与、CROSSBOW は † 扱い、と plan が運ぶことの回帰。

        BossLab.cs は plan の defer_relics を見てレリックを入室後に足す（入室 hook が札を強化する
        系で、lab 側の RNG が二重に走ると hand/draw が実走とズレる）。analyze_bosslab.py は
        flag_relics を † として扱う。
        """
        held = dict(ACT3_SPEC)
        held["player"] = dict(ACT3_SPEC["player"],
                              relics=list(ACT3_SPEC["player"]["relics"])
                              + ["RELIC.STONE_CRACKER", "RELIC.CROSSBOW"])
        plan, _ = run_tool([held], ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"])
        trial = plan["trials"][0]
        self.assertEqual(["RELIC.STONE_CRACKER"], trial["defer_relics"])
        self.assertEqual(["RELIC.CROSSBOW"], trial["flag_relics"])
        summary = plan["relic_entry_effects"]
        self.assertEqual(["RELIC.STONE_CRACKER"], summary["defer_relics"])
        self.assertEqual(["RELIC.CROSSBOW"], summary["flag_relics"])
        self.assertEqual(1, summary["trials_with_defer"])
        self.assertEqual(1, summary["trials_with_flag"])

    def test_trial_carries_restored_relic_counters_from_the_spec(self) -> None:
        """PenNib の入場カウンタが trial.relic_counters で BossLab へ渡る回帰。"""
        spec = dict(ACT3_SPEC)
        spec["player"] = dict(ACT3_SPEC["player"],
                              relics=list(ACT3_SPEC["player"]["relics"]) + ["RELIC.PEN_NIB"],
                              relic_counters={"RELIC.PEN_NIB": 7})
        spec["relic_counters_observed"] = True
        plan, _ = run_tool([spec], ["--arm", "base", "--max-specs", "1", "--trials-per-arm", "1"])
        self.assertEqual({"RELIC.PEN_NIB": 7}, plan["trials"][0]["relic_counters"])

    def test_counter_relic_on_an_unobserved_trace_is_dropped(self) -> None:
        """旧ブリッジ trace のカウンタ付き spec は、unresolved が空でも plan から落とす。

        relic_counters 列を持たない trace から作ると、記録カウンタが不明で BossLab は 0 から
   戦闘を始めてしまう（10 回目の攻撃を二重/見逃し）。observed なら通す。
        """
        def pen_nib_spec(observed):
            spec = dict(ACT3_SPEC)
            spec["player"] = dict(ACT3_SPEC["player"],
                                  relics=list(ACT3_SPEC["player"]["relics"]) + ["RELIC.PEN_NIB"],
                                  relic_counters={"RELIC.PEN_NIB": 7})
            if observed is not None:
                spec["relic_counters_observed"] = observed
            return spec

        for observed in (False, None):  # explicit False and a spec predating the field
            plan, _ = run_tool([pen_nib_spec(observed)],
                               ["--arm", "base", "--max-specs", "5", "--trials-per-arm", "1"])
            self.assertEqual([], plan["trials"], f"observed={observed} must drop the counter spec")
        plan, _ = run_tool([pen_nib_spec(False)], ["--arm", "base", "--max-specs", "5",
                                                   "--trials-per-arm", "1", "--allow-unresolved"])
        self.assertEqual([], plan["trials"], "counter-safety is not an unresolved gate")
        plan, _ = run_tool([pen_nib_spec(True)], ["--arm", "base", "--max-specs", "5",
                                                  "--trials-per-arm", "1"])
        self.assertEqual(1, len(plan["trials"]))

    def test_relic_counters_are_known_helper(self) -> None:
        ee = load_entry_effects()
        self.assertEqual({"RELIC.PEN_NIB", "RELIC.NUNCHAKU", "RELIC.TUNING_FORK"},
                         set(ee.RESTORABLE_COUNTER_RELICS))
        # A player with no restorable counter relic is always safe, whatever the trace format.
        self.assertTrue(ee.relic_counters_are_known(["RELIC.BURNING_BLOOD", "RELIC.SWORD_OF_JADE"],
                                                    False))
        # PENDULUM's counter drives a card draw, so it is not restorable and never gated here.
        self.assertEqual([], ee.restorable_counter_relics(["RELIC.PENDULUM", "RELIC.CROSSBOW"]))
        # A restorable counter relic needs the observed column; observed or not flips the answer.
        self.assertFalse(ee.relic_counters_are_known(["RELIC.PEN_NIB"], False))
        self.assertTrue(ee.relic_counters_are_known(["RELIC.PEN_NIB"], True))


if __name__ == "__main__":
    unittest.main()
