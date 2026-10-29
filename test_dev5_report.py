import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

# T36.2: the one-command dev5 report must (a) locate firing to diverging turns, (b) show paired Queen
# shave, (c) show firepower/survival per arm, (d) read the frozen 4693f2e gate - and never crash on a
# partially-run panel. Fixtures build synthetic run dirs (lab_results.jsonl + per-trial agent traces).
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("dev5_report", _TOOLS / "dev5_report.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)
RELIABLE = "combat_end_trace"


def _dir(root: Path, name: str, trials: list[dict]) -> Path:
    """Write one run dir: a lab_results.jsonl plus the trial_NNNN_agent.jsonl traces it references."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    lab = []
    for t in trials:
        spec, off, idx = t["spec"], t["off"], t["index"]
        lab.append({"trial_id": f"{spec}|base|{off}", "spec_id": spec, "trial_index": idx,
                    "result": {"outcome_source": RELIABLE, "won": t["won"],
                               "entry_player_hp": 80, "final_player_hp": 70,
                               "last_observed_turn": t["turn"],
                               "enemy_hp_last_observed": [
                                   {"id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": t.get("amalgam_hp", 199), "max_hp": 199},
                                   {"id": "MONSTER.QUEEN", "hp": t["queen_hp"], "max_hp": 400}]}})
        rows = []
        for (tn, slot, qh, ah) in t["steps"]:
            rows.append({"type": "card", "turn": tn, "hand_index": 0, "hand": [{"type": "Attack"}],
                         "target_id": 1 if slot == "amalgam" else 2,
                         "enemies": [{"slot": "amalgam", "combat_id": 1, "id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": ah},
                                     {"slot": "queen", "combat_id": 2, "id": "MONSTER.QUEEN", "hp": qh}]})
        (d / f"trial_{idx:04d}_agent.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    (d / "lab_results.jsonl").write_text("\n".join(json.dumps(r) for r in lab), encoding="utf-8")
    return d


def _base_trials(n=4):
    """n base entries: Amalgam-focused every turn, Queen untouched, no wins."""
    return [{"spec": f"s{i}", "off": 0, "index": i, "won": False, "queen_hp": 400, "turn": 4,
             "steps": [(tn, "amalgam", 400, 199) for tn in (1, 2, 3, 4)]} for i in range(n)]


def _cand_trials(n=4):
    """n candidate entries that arm: Queen targeted on turn 2 (diverging) and Queen cut 400->300."""
    out = []
    for i in range(n):
        steps = [(1, "amalgam", 400, 199), (2, "queen", 300, 199), (3, "queen", 300, 199), (4, "queen", 300, 199)]
        out.append({"spec": f"s{i}", "off": 0, "index": i, "won": False, "queen_hp": 300, "turn": 4, "steps": steps})
    return out


class FiringTurnTest(unittest.TestCase):
    def test_reports_diverging_turn_numbers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            c = _dir(root, "cand", _cand_trials())
            r = D.H.pair_attack_target_turns(b, c)
            self.assertEqual(r["pairs"], 4)
            self.assertEqual(r["fired"], 4)
            for spec, off, turns in r["fired_detail"]:  # every pair arms Queen from turn 2 on
                self.assertEqual(turns, [2, 3, 4])

    def test_fired_count_matches_whole_fight_measure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            c = _dir(root, "cand", _cand_trials())
            self.assertEqual(D.H.pair_attack_target_turns(b, c)["fired"],
                             D.H.pair_attack_target_diff(b, c)["fired"])

    def test_identical_candidate_fires_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            c = _dir(root, "cand", _base_trials())
            self.assertEqual(D.H.pair_attack_target_turns(b, c)["fired"], 0)


class ReportTest(unittest.TestCase):
    def test_happy_path_full_table_and_sufficed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            c = _dir(root, "cand", _cand_trials())
            text = D.build_report(b, [("cand", c)])
            self.assertIn("(a)", text)
            self.assertIn("(b)", text)
            self.assertIn("総火力/ターン", text)
            self.assertIn("発火 4/4", text)             # firing count reaches the G threshold
            self.assertIn("条件充足=Yes", text)          # Δshave>0, Δfp>0, Δwin>=0 all clear
            self.assertIn("保留（暫定", text)            # confirm5 not run -> provisional, not final

    def test_missing_candidate_dir_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            text = D.build_report(b, [("cand", root / "does_not_exist")])
            self.assertIn("実行データ無し", text)
            self.assertIn("測定不能", text)               # no candidate with data -> G not satisfiable

    def test_partial_missing_trace_is_counted_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            c = _dir(root, "cand", _cand_trials())
            (c / "trial_0001_agent.jsonl").unlink()       # drop one candidate pair's trace
            text = D.build_report(b, [("cand", c)])
            self.assertIn("照合できず 1 組", text)          # the gap is reported, not an exception
            self.assertIn("発火 3/4", text)               # 3 pairs still comparable and firing

    def test_confirm_supplied_yields_final_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            b = _dir(root, "base", _base_trials())
            c = _dir(root, "cand", _cand_trials())
            cb = _dir(root, "cbase", _base_trials())
            cc = _dir(root, "ccand", _cand_trials())
            text = D.build_report(b, [("cand", c)], confirm_base=cb, confirm_cands=[f"cand={cc}"])
            self.assertNotIn("保留（暫定", text)           # confirm measured -> verdict is final
            self.assertIn("前提 G 総合", text)


if __name__ == "__main__":
    unittest.main()
