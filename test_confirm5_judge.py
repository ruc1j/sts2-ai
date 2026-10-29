import importlib.util
import sys
import unittest
from pathlib import Path

# T39: the separate confirm5 entry must reproduce the frozen 4693f2e branches per candidate — prerequisite
# G before anything, then 不採用 (both-set shave non-positive, or shave+firepower worse), then 採用
# (conditions 1,3,4,5,6), else 保留; a candidate whose confirm5 side has not run is provisional 保留.
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("apply_hybrid_rule", _TOOLS / "apply_hybrid_rule.py")
H = importlib.util.module_from_spec(_spec)
sys.modules["apply_hybrid_rule"] = H
_spec.loader.exec_module(H)


def _delta(shave, better, worse, tie, p, fp, win, pairs=12, nc=0):
    return {"Δshave": shave, "better": better, "worse": worse, "tie": tie, "p": p,
            "Δfp": fp, "fp_base": 42.6, "fp_cand": (42.6 + fp) if fp is not None else float("nan"),
            "Δwin": win, "cand_wins": 2 + win, "base_wins": 2, "pairs": pairs, "not_comparable": nc}


def _fire(fired, pairs=12):
    return {"pairs": pairs, "fired": fired, "skipped_missing_trace": 0, "fired_detail": []}


class JudgeCandidateTest(unittest.TestCase):
    def test_adopt_when_all_conditions_and_g_hold(self):
        dev = _delta(2, 7, 5, 0, 0.1, 0.4, 0)
        conf = _delta(3, 8, 5, -1, 0.02, 0.2, 0)  # Δwin>=0 via base2→cand2 (win delta 0)
        res = H.judge_candidate(dev, conf, _fire(11), _fire(12))
        self.assertEqual(res["verdict"], "採用")
        self.assertTrue(all(res["cond"][k] for k in (1, 3, 4, 5, 6)))

    def test_hold_as_uncalibratable_when_g_fails(self):
        dev = _delta(2, 7, 5, 0, 0.1, 0.4, 0)
        conf = _delta(3, 8, 5, -1, 0.02, 0.2, 0)
        res = H.judge_candidate(dev, conf, _fire(3), _fire(12))  # dev5 firing below threshold
        self.assertEqual(res["verdict"], "保留")
        self.assertIn("firing", res["reason"].lower())

    def test_reject_when_shave_non_positive_on_both_sets(self):
        dev = _delta(-1, 5, 6, 1, 1.0, 0.4, 0)
        conf = _delta(0, 6, 6, 0, 1.0, 0.2, 0)
        res = H.judge_candidate(dev, conf, _fire(11), _fire(12))
        self.assertEqual(res["verdict"], "不採用")

    def test_reject_when_shave_and_firepower_worse(self):
        dev = _delta(-1, 5, 6, 1, 1.0, -2.0, 0)  # shave worse and firepower below base on dev5
        conf = _delta(2, 7, 5, 0, 0.2, 0.1, 0)
        res = H.judge_candidate(dev, conf, _fire(11), _fire(12))
        self.assertEqual(res["verdict"], "不採用")

    def test_hold_when_direction_mismatches(self):
        dev = _delta(2, 7, 5, 0, 0.1, 0.4, 0)   # dev5 says candidate better
        conf = _delta(0, 6, 6, 0, 1.0, 0.1, 0)   # confirm5 says tie -> condition 1 fails, not REJECT
        res = H.judge_candidate(dev, conf, _fire(11), _fire(12))
        self.assertEqual(res["verdict"], "保留")
        self.assertFalse(res["cond"][1])
        self.assertFalse(res["direction_match"])

    def test_hold_when_significance_or_win_fails(self):
        dev = _delta(2, 7, 5, 0, 0.1, 0.4, 0)
        conf_hi_p = _delta(2, 7, 5, 0, 0.30, 0.4, 0)  # p > 0.05 -> condition 5 fails
        self.assertEqual(H.judge_candidate(dev, conf_hi_p, _fire(11), _fire(12))["verdict"], "保留")
        conf_neg_win = _delta(2, 7, 5, 0, 0.02, 0.4, -1)  # Δwin < 0 -> condition 4 fails
        self.assertEqual(H.judge_candidate(dev, conf_neg_win, _fire(11), _fire(12))["verdict"], "保留")

    def test_provisional_hold_when_confirm5_not_run(self):
        dev = _delta(2, 7, 5, 0, 0.1, 0.4, 0)
        res = H.judge_candidate(dev, None, _fire(11), None)
        self.assertEqual(res["verdict"], "保留")
        self.assertIsNone(res["cond"][1])
        text = H.format_candidate_report("H3c", res)
        self.assertIn("未実行（確認用待ち）", text)  # confirm-side delta line is pending, report does not crash


if __name__ == "__main__":
    unittest.main()
