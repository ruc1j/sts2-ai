"""Tests for bosslab/tools/ns_report.py using small synthetic run dirs."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "bosslab" / "tools" / "ns_report.py"
spec = importlib.util.spec_from_file_location("ns_report", str(TOOL))
N = importlib.util.module_from_spec(spec)
spec.loader.exec_module(N)

SHRUG = "CARD.SHRUG_IT_OFF"
BOSS = "MONSTER.THE_INSATIABLE"


def make_dir(root: Path, name: str, trials: list) -> Path:
    """trials: (spec, arm, boss_hp, shrug_plays, stalled)."""
    d = root / name
    d.mkdir()
    (d / "plan.json").write_text(json.dumps({"trials": [{"trial_id": f"{sp}|{arm}|0"} for sp, arm, *_ in trials]}))
    (d / "lab_meta.json").write_text(json.dumps({"plan": str(d / "plan.json")}))
    lines = []
    for i, (sp, arm, hp, plays, stalled) in enumerate(trials):
        if stalled:
            continue
        lines.append(json.dumps({
            "trial_index": i, "trial_id": f"{sp}|{arm}|0", "spec_id": sp, "encounter": "ENCOUNTER.THE_INSATIABLE",
            "result": {"won": False, "outcome_source": "combat_end_trace", "entry_player_hp": 80,
                       "final_player_hp": 0, "last_observed_turn": 6,
                       "enemy_hp_last_observed": [{"id": BOSS, "hp": hp, "max_hp": 400}]}}))
        tr = [{"turn": 1, "enemies": [{"id": BOSS, "hp": 400}], "type": "card", "card_id": "CARD.STRIKE_IRONCLAD"}]
        tr += [{"turn": 2, "enemies": [{"id": BOSS, "hp": 400}], "type": "card", "card_id": SHRUG}
               for _ in range(plays)]
        tr.append({"turn": 6, "enemies": [{"id": BOSS, "hp": hp}], "type": "end_turn"})
        (d / f"trial_{i:04d}_agent.jsonl").write_text("\n".join(json.dumps(r) for r in tr) + "\n")
    (d / "lab_results.jsonl").write_text("\n".join(lines) + "\n")
    return d


def panel_trials(n, base_plays, ns_plays, ns_hp, base_hp=300, stalled_spec=None):
    t = []
    for s in range(n):
        sp = f"s{s}"
        t.append((sp, "base", base_hp - s, base_plays, False))
        t.append((sp, "noshrug", ns_hp - s, ns_plays, sp == stalled_spec))
    return t


class NsReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _render(self, dev_kw, conf_kw, conf_stalled=None):
        dd = make_dir(self.root, "dev", panel_trials(12, **dev_kw))
        cd = make_dir(self.root, "conf", panel_trials(12, stalled_spec=conf_stalled, **conf_kw))
        return N.render(dd, cd, N.panel(dd), N.panel(cd))

    def test_complete_panels_with_firing_cond6_satisfied(self):
        good = dict(base_plays=3, ns_plays=1, ns_hp=250)
        text = self._render(good, good)
        self.assertIn("G''発火 12/12", text)
        self.assertIn("条件6: 充足", text)
        self.assertNotIn("pairing incomplete", text)

    def test_firing_below_threshold_is_hold(self):
        p = N.panel(make_dir(self.root, "d1", panel_trials(12, 1, 1, 250)))
        self.assertEqual(p["fire"]["fired"], 0)
        weak = dict(base_plays=1, ns_plays=1, ns_hp=250)
        text = self._render(weak, weak)
        self.assertIn("保留", text)
        self.assertIn("前提 G''", text)
        self.assertIn("不充足", text)

    def test_missing_confirm_trial_pairing_incomplete(self):
        good = dict(base_plays=3, ns_plays=1, ns_hp=250)
        text = self._render(good, good, conf_stalled="s3")
        self.assertIn("pairing incomplete", text)
        self.assertIn("s3|0", text)
        self.assertIn("条件6: 不充足", text)

    def test_reversed_direction_is_reject(self):
        bad = dict(base_plays=3, ns_plays=1, ns_hp=350)  # noshrug leaves the boss with more HP
        text = self._render(bad, bad)
        self.assertIn("不採用", text)

    def test_missing_confirm_is_provisional(self):
        dd = make_dir(self.root, "dev", panel_trials(12, 3, 1, 250))
        text = N.render(dd, self.root / "nope", N.panel(dd), None)
        self.assertIn("未実行", text)
        self.assertIn("暫定", text)

    def test_shave_uses_insatiable_and_restores_suffix(self):
        dd = make_dir(self.root, "dev", panel_trials(12, 3, 1, 250))
        before = N.A.QUEEN_ID_SUFFIX
        d = N.panel(dd)["delta"]
        self.assertEqual(N.A.QUEEN_ID_SUFFIX, before)
        self.assertEqual(d["Δshave"], 12)
        self.assertLess(d["shave_base"], d["shave_cand"])


if __name__ == "__main__":
    unittest.main()
