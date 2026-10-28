"""Tests for bosslab/tools/analyze_bosslab.py's Act 3 (QUEEN) continuous-metric layer.

The Act 3 panel's primary signal is how much of the Queen's own 400 HP a fight removed, not win/loss
(the real-run Act 3 base win rate sits near 7%, so a 0/12 vs 1/12 comparison is noise). These tests
pin how the numbers are derived from a BossLab result line and how the paired comparison behaves.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
TOOL = REPO / "bosslab" / "tools" / "analyze_bosslab.py"


def load_module():
    module_spec = importlib.util.spec_from_file_location("analyze_bosslab", TOOL)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def trial(*, arm: str = "base", spec: str = "s1", offset: str = "0", won: bool = False,
          queen_hp: int | None = 300, amalgam_hp: int | None = 199, entry_hp: int = 80,
          final_hp: int = 0, turns: int = 7) -> dict:
    enemies = []
    if amalgam_hp is not None:
        enemies.append({"id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": amalgam_hp, "max_hp": 199})
    if queen_hp is not None:
        enemies.append({"id": "MONSTER.QUEEN", "hp": queen_hp, "max_hp": 400})
    return {
        "trial_id": f"{spec}|{arm}|{offset}", "trial_index": 0, "spec_id": spec,
        "effective_seed": "SEED123456", "elapsed_ms": 60000, "encounter": "ENCOUNTER.QUEEN_BOSS",
        "_arm": arm, "_offset": offset,
        "result": {
            "won": won, "outcome_source": "combat_end_trace",
            "entry_player_hp": entry_hp, "entry_player_max_hp": 100, "final_player_hp": final_hp,
            "final_player_max_hp": 100, "last_observed_turn": turns,
            "enemy_hp_last_observed": enemies,
        },
    }


class ContinuousMetricsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TOOL.is_file():
            raise cls.skipTest(f"{TOOL} is missing")
        cls.mod = load_module()

    def test_queen_shave_is_a_fraction_of_her_own_400(self) -> None:
        metrics = self.mod.continuous_metrics(trial(queen_hp=300))
        self.assertAlmostEqual(0.25, metrics["queen_shaved"])
        self.assertFalse(metrics["amalgam_killed"])
        self.assertEqual(80, metrics["hp_lost"])
        self.assertEqual(7, metrics["turns"])

    def test_queen_absent_from_the_last_observation_means_she_died(self) -> None:
        metrics = self.mod.continuous_metrics(trial(queen_hp=None, amalgam_hp=None))
        self.assertAlmostEqual(1.0, metrics["queen_shaved"])
        self.assertTrue(metrics["amalgam_killed"])

    def test_a_win_counts_as_fully_shaved_even_if_the_row_still_lists_the_queen(self) -> None:
        # The bridge writes the last observation before the killing blow resolves, so a win can carry
        # the Queen at 1 HP; the fight still ended by her death.
        metrics = self.mod.continuous_metrics(trial(won=True, queen_hp=1, amalgam_hp=120))
        self.assertAlmostEqual(1.0, metrics["queen_shaved"])
        self.assertTrue(metrics["amalgam_killed"])

    def test_panel_detection_only_fires_for_queen_encounters(self) -> None:
        self.assertTrue(self.mod.is_queen_panel([trial()]))
        act2 = trial()
        act2["encounter"] = "ENCOUNTER.THE_INSATIABLE"
        self.assertFalse(self.mod.is_queen_panel([act2]))


class RunLabelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TOOL.is_file():
            raise cls.skipTest(f"{TOOL} is missing")
        cls.mod = load_module()

    def test_label_is_split_off_only_when_the_whole_token_is_not_a_path(self) -> None:
        dirs, labels = self.mod.parse_run_labels(
            ["/tmp/act3x/base", "queenfirst=/tmp/act3x/cand"])
        self.assertEqual(["/tmp/act3x/base", "/tmp/act3x/cand"], dirs)
        self.assertEqual(["", "queenfirst"], labels)

    def test_an_equal_sign_inside_an_existing_path_stays_part_of_the_path(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            nested = Path(tmp) / "a=b"
            nested.mkdir()
            dirs, labels = self.mod.parse_run_labels([str(nested)])
        self.assertEqual([str(nested)], dirs)
        self.assertEqual([""], labels)


class PairedContinuousTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not TOOL.is_file():
            raise cls.skipTest(f"{TOOL} is missing")
        cls.mod = load_module()

    def test_pairs_only_same_spec_and_offset(self) -> None:
        trials = [trial(arm="base", spec="s1", offset="0", queen_hp=300),
                  trial(arm="queenfirst", spec="s1", offset="0", queen_hp=200),
                  trial(arm="base", spec="s2", offset="0", queen_hp=400)]
        result = self.mod.paired_continuous(trials, "base", "queenfirst")
        self.assertEqual(1, result["pairs"])
        self.assertEqual(1, result["not_comparable"])
        row = next(row for row in result["rows"] if row["metric"] == "queen_shaved")
        self.assertAlmostEqual(0.25, row["base_mean"])
        self.assertAlmostEqual(0.5, row["other_mean"])
        self.assertEqual(1, row["better"])
        self.assertEqual(0, row["worse"])

    def test_numeric_metrics_are_not_coerced_to_counts(self) -> None:
        # A previous draft turned every value through a bool branch, which made the death-turn column
        # report 1.0 for every arm. Pin the numeric path so that cannot come back.
        trials = [trial(arm="base", turns=4), trial(arm="queenfirst", turns=9)]
        result = self.mod.paired_continuous(trials, "base", "queenfirst")
        row = next(row for row in result["rows"] if row["metric"] == "turns")
        self.assertAlmostEqual(4.0, row["base_mean"])
        self.assertAlmostEqual(9.0, row["other_mean"])
        self.assertEqual(1, row["better"])  # shorter deaths count as the candidate doing better

    def test_sign_test_is_reported_only_for_the_primary_metric(self) -> None:
        trials = [trial(arm="base", spec=f"s{i}", offset="0", queen_hp=400 - 20 * i)
                  for i in range(1, 5)]
        trials += [trial(arm="queenfirst", spec=f"s{i}", offset="0", queen_hp=200)
                   for i in range(1, 5)]
        rows = {row["metric"]: row for row in
                self.mod.paired_continuous(trials, "base", "queenfirst")["rows"]}
        self.assertIsNotNone(rows["queen_shaved"]["p"])
        self.assertIsNone(rows["amalgam_killed"]["p"])
        self.assertIsNone(rows["turns"]["p"])

    def test_equal_entries_count_as_ties_not_as_improvements(self) -> None:
        trials = [trial(arm="base", queen_hp=250), trial(arm="queenfirst", queen_hp=250)]
        rows = {row["metric"]: row for row in
                self.mod.paired_continuous(trials, "base", "queenfirst")["rows"]}
        self.assertEqual(1, rows["queen_shaved"]["tie"])
        self.assertEqual(0, rows["queen_shaved"]["better"])
        self.assertEqual(0, rows["queen_shaved"]["worse"])

    def test_known_unfaithful_specs_can_be_excluded_from_the_pairing(self) -> None:
        trials = [trial(arm="base", spec="s1", queen_hp=400),
                  trial(arm="queenfirst", spec="s1", queen_hp=300),
                  trial(arm="base", spec="s2", queen_hp=400),
                  trial(arm="queenfirst", spec="s2", queen_hp=400)]
        all_pairs = self.mod.paired_continuous(trials, "base", "queenfirst")
        clean = self.mod.paired_continuous(trials, "base", "queenfirst", exclude_specs={"s1"})
        row_all = next(row for row in all_pairs["rows"] if row["metric"] == "queen_shaved")
        row_clean = next(row for row in clean["rows"] if row["metric"] == "queen_shaved")
        # s1: the candidate shaves 25% against the base's 0%, so it counts as better. s2: both end
        # with the Queen untouched, so it counts as a tie. Excluding s1 leaves only the tie.
        self.assertEqual(1, row_all["better"])
        self.assertEqual(1, row_all["tie"])
        self.assertEqual(0, row_clean["better"])
        self.assertEqual(1, row_clean["tie"])

    def test_plan_flags_pick_up_entry_state_relics(self) -> None:
        if not self.mod.ENTRY_STATE_RELICS:
            self.skipTest("entry_state_relics.json is not in this checkout")
        relic = sorted(self.mod.ENTRY_STATE_RELICS)[0]
        bare = relic.split(".", 1)[1]
        planned = [{"spec_id": "s1", "relics": [bare]}, {"spec_id": "s2", "relics": ["RELIC.NO_SUCH_RELIC"]}]
        flags = self.mod.flag_specs_from_plan(planned)
        self.assertEqual({"s1"}, set(flags))
        self.assertEqual([relic], flags["s1"])

    def test_per_arm_summary_reports_median_and_mean(self) -> None:
        summary = self.mod.summarize_continuous([
            trial(arm="base", queen_hp=400), trial(arm="base", queen_hp=200)])
        self.assertEqual(2, summary["n"])
        self.assertAlmostEqual(0.25, summary["shaved_median"])
        self.assertAlmostEqual(0.25, summary["shaved_mean"])
        self.assertEqual(1, summary["untouched"])


if __name__ == "__main__":
    unittest.main()
