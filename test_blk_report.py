"""Tests for bosslab/tools/blk_report.py using small synthetic run dirs."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent / "bosslab" / "tools" / "blk_report.py"
spec = importlib.util.spec_from_file_location("blk_report", str(TOOL))
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)

SHRUG, FLAME = "CARD.SHRUG_IT_OFF", "CARD.FLAME_BARRIER"


def make_dir(root: Path, name: str, trials: list) -> Path:
    """trials: (spec, arm, queen_hp, block_plays, stalled). Writes lab_results.jsonl and traces."""
    d = root / name
    d.mkdir()
    plan = {"trials": [{"trial_id": f"{sp}|{arm}|0"} for sp, arm, *_ in trials]}
    (d / "plan.json").write_text(json.dumps(plan))
    (d / "lab_meta.json").write_text(json.dumps({"plan": str(d / "plan.json")}))
    lines = []
    for i, (sp, arm, qhp, plays, stalled) in enumerate(trials):
        if stalled:
            continue
        row = {"trial_index": i, "trial_id": f"{sp}|{arm}|0", "spec_id": sp,
               "encounter": "ENCOUNTER.QUEEN_BOSS",
               "result": {"won": False, "outcome_source": "combat_end_trace", "entry_player_hp": 90,
                          "final_player_hp": 0, "last_observed_turn": 6,
                          "enemy_hp_last_observed": [{"id": "MONSTER.QUEEN", "hp": qhp, "max_hp": 400}]}}
        lines.append(json.dumps(row))
        tr = [{"turn": 1, "enemies": [{"id": "MONSTER.QUEEN", "hp": 400}], "type": "card",
               "card_id": "CARD.STRIKE_IRONCLAD"}]
        tr += [{"turn": 2, "enemies": [{"id": "MONSTER.QUEEN", "hp": 400}], "type": "card",
                "card_id": SHRUG if k % 2 else FLAME} for k in range(plays)]
        tr.append({"turn": 6, "enemies": [{"id": "MONSTER.QUEEN", "hp": qhp}], "type": "end_turn"})
        (d / f"trial_{i:04d}_agent.jsonl").write_text("\n".join(json.dumps(r) for r in tr) + "\n")
    (d / "lab_results.jsonl").write_text("\n".join(lines) + "\n")
    return d


def panel_trials(n, add_plays, add_hp, base_hp=300, stalled_spec=None):
    t = []
    for s in range(n):
        sp = f"s{s}"
        t.append((sp, "base", base_hp - s, 1, False))
        for arm in ("add2", "add4"):
            t.append((sp, arm, add_hp - s, add_plays, sp == stalled_spec and arm == "add2"))
    return t


class BlkReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_firing_and_deltas(self):
        d = make_dir(self.root, "dev", panel_trials(6, add_plays=3, add_hp=250))
        p = B.panel(d)
        for arm in B.ADD_ARMS:
            self.assertEqual(p[arm]["fire"]["fired"], 6)
            self.assertEqual(p[arm]["delta"]["Δshave"], 6)
            self.assertEqual(p[arm]["incomplete"], [])

    def test_no_firing_when_plays_not_above_base(self):
        d = make_dir(self.root, "dev", panel_trials(6, add_plays=1, add_hp=250))
        self.assertEqual(B.panel(d)["add2"]["fire"]["fired"], 0)

    def test_stalled_pair_reported_incomplete(self):
        d = make_dir(self.root, "dev", panel_trials(6, add_plays=3, add_hp=250, stalled_spec="s2"))
        p = B.panel(d)
        self.assertEqual(p["add2"]["incomplete"], [("s2", "0")])
        self.assertEqual(p["add2"]["delta"]["not_comparable"], 1)
        self.assertEqual(p["add4"]["incomplete"], [])

    def test_report_missing_confirm_is_provisional(self):
        d = make_dir(self.root, "dev", panel_trials(6, add_plays=3, add_hp=250))
        dev = B.panel(d)
        text = B.render(d, self.root / "nope", dev, None)
        self.assertIn("未実行", text)
        self.assertIn("暫定", text)
        self.assertIn("判定できない", text)

    def test_verdict_with_both_panels(self):
        dd = make_dir(self.root, "dev", panel_trials(6, add_plays=3, add_hp=250))
        cd = make_dir(self.root, "conf", panel_trials(12, add_plays=3, add_hp=250))
        text = B.render(dd, cd, B.panel(dd), B.panel(cd))
        self.assertIn("G'発火 6/6", text)
        self.assertIn("G'発火 12/12", text)

    def _cond6(self, conf_stalled):
        dd = make_dir(self.root, "dev", panel_trials(6, add_plays=3, add_hp=250))
        cd = make_dir(self.root, "conf", panel_trials(12, add_plays=3, add_hp=250, stalled_spec=conf_stalled))
        text = B.render(dd, cd, B.panel(dd), B.panel(cd))
        return text

    def test_condition6_complete_panels(self):
        text = self._cond6(None)
        self.assertIn("dev の pairs を confirm に合わせて", text)
        self.assertIn("条件6: 充足", text)

    def test_condition6_stalled_confirm_pair(self):
        text = self._cond6("s3")
        self.assertIn("不適用", text)
        self.assertIn("pairing incomplete", text)
        self.assertIn("条件6: 不充足", text)


if __name__ == "__main__":
    unittest.main()
