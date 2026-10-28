import unittest
import importlib.util
from pathlib import Path

# Lock the accept/keep/reject and candidate-selection branches against synthetic inputs BEFORE the
# confirm4 real-machine result is seen, per bosslab/results/act3_hybrid_decision_rule.md (4693f2e).
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("apply_hybrid_rule", _TOOLS / "apply_hybrid_rule.py")
hr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hr)


def mk(Δshave, Δfp, Δwin=0, p=0.04, better=None, worse=None, pairs=12, nc=0):
    """A synthetic candidate-vs-base delta dict as candidate_delta() returns."""
    if better is None:
        better = max(0, Δshave) if Δshave > 0 else 0
        worse = max(0, -Δshave) if Δshave < 0 else 0
    return {
        "Δshave": Δshave, "better": better, "worse": worse, "tie": 12 - better - worse, "p": p,
        "Δfp": Δfp, "fp_base": 37.0, "fp_cand": 37.0 + (Δfp if Δfp is not None else 0),
        "Δwin": Δwin, "cand_wins": 1 + (1 if Δwin > 0 else 0), "base_wins": 1,
        "pairs": pairs, "not_comparable": nc,
    }


class SelectCandidateTest(unittest.TestCase):
    def test_both_sufficed_picks_larger_deltafp(self):
        dev = {"H1": mk(Δshave=+4, Δfp=+1.0, Δwin=0), "H2": mk(Δshave=+3, Δfp=+2.0, Δwin=0)}
        chosen, branch = hr.select_candidate(dev, ["H1", "H2"])
        self.assertEqual(chosen, "H2")  # larger Δfp wins when the gap exceeds 0.5
        self.assertIs(branch, hr.SELECT_BOTH)

    def test_both_sufficed_tie_on_deltafp_picks_larger_delta_shave(self):
        dev = {"H1": mk(Δshave=+4, Δfp=+1.0), "H2": mk(Δshave=+6, Δfp=+1.1)}  # Δfp within 0.5 -> tie band
        chosen, _ = hr.select_candidate(dev, ["H1", "H2"])
        self.assertEqual(chosen, "H2")  # within 0.5 band -> larger Δshave
        self.assertIs(hr.select_candidate(dev, ["H1", "H2"])[1], hr.SELECT_BOTH)

    def test_both_sufficed_fully_tied_prefers_H1(self):
        dev = {"H1": mk(Δshave=+4, Δfp=+1.0), "H2": mk(Δshave=+4, Δfp=+1.0)}
        chosen, branch = hr.select_candidate(dev, ["H1", "H2"])
        self.assertEqual(chosen, "H1")  # still tied -> H1 (削り済み優先の従属則)
        self.assertIs(branch, hr.SELECT_BOTH)

    def test_one_sufficed_picks_that_one(self):
        dev = {"H1": mk(Δshave=+6, Δfp=-4.0), "H2": mk(Δshave=+3, Δfp=+2.0)}  # H1 fails Δfp gate
        chosen, branch = hr.select_candidate(dev, ["H1", "H2"])
        self.assertEqual(chosen, "H2")
        self.assertIs(branch, hr.SELECT_ONE)

    def test_none_sufficed_record_sends_most_delta_shave(self):
        dev = {"H1": mk(Δshave=+6, Δfp=-4.0), "H2": mk(Δshave=+4, Δfp=-1.0)}  # neither passes Δfp
        chosen, branch = hr.select_candidate(dev, ["H1", "H2"])
        self.assertEqual(chosen, "H1")  # record-only send: largest Δshave>0
        self.assertIs(branch, hr.SELECT_NONE)

    def test_none_sufficed_no_positive_shave_no_chosen(self):
        dev = {"H1": mk(Δshave=-2, Δfp=-4.0), "H2": mk(Δshave=0, Δfp=-1.0)}
        chosen, branch = hr.select_candidate(dev, ["H1", "H2"])
        self.assertIsNone(chosen)
        self.assertIs(branch, hr.SELECT_NONE)


class DecideTest(unittest.TestCase):
    def test_accept_when_all_six_conditions_hold(self):
        dev = {"H1": mk(Δshave=+6, Δfp=+1.0, Δwin=+1, p=0.03),
               "H2": mk(Δshave=+2, Δfp=+1.0, Δwin=0)}
        confirm = {"H1": mk(Δshave=+5, Δfp=+0.5, Δwin=+1, p=0.02)}
        res = hr.decide(dev, confirm, ["H1", "H2"])
        self.assertEqual(res["chosen"], "H1")
        self.assertTrue(all(res["cond"][n] is True for n in (1, 2, 3, 4, 5, 6)))
        self.assertEqual(res["verdict"], "採用")

    def test_keep_when_shave_improves_but_firepower_gate_fails(self):
        dev = {"H1": mk(Δshave=+6, Δfp=+1.0, Δwin=0), "H2": mk(Δshave=+2, Δfp=+1.0, Δwin=0)}
        confirm = {"H1": mk(Δshave=+4, Δfp=-0.7, Δwin=0, p=0.02)}  # Δfp < 0 on confirm -> cond3 fails
        res = hr.decide(dev, confirm, ["H1", "H2"])
        self.assertEqual(res["chosen"], "H1")
        self.assertFalse(res["cond"][3])
        self.assertEqual(res["verdict"], "保留")

    def test_keep_when_significance_gate_fails(self):
        dev = {"H1": mk(Δshave=+3, Δfp=+1.0, Δwin=0), "H2": mk(Δshave=+2, Δfp=+1.0, Δwin=0)}
        confirm = {"H1": mk(Δshave=+2, Δfp=+1.0, Δwin=0, p=0.146)}  # p > 0.05 -> cond5 fails
        res = hr.decide(dev, confirm, ["H1", "H2"])
        self.assertFalse(res["cond"][5])
        self.assertEqual(res["verdict"], "保留")

    def test_keep_when_dev_candidate_directions_split(self):
        dev = {"H1": mk(Δshave=+6, Δfp=+1.0), "H2": mk(Δshave=-3, Δfp=+1.0)}  # H2 shave worse -> cond2 fails
        confirm = {"H1": mk(Δshave=+5, Δfp=+1.0, Δwin=0, p=0.02)}
        res = hr.decide(dev, confirm, ["H1", "H2"])
        self.assertFalse(res["cond"][2])
        self.assertEqual(res["verdict"], "保留")

    def test_reject_when_confirm_shave_worse_and_firepower_worse(self):
        dev = {"H1": mk(Δshave=+6, Δfp=-4.0), "H2": mk(Δshave=+4, Δfp=-1.0)}  # record-send H1
        confirm = {"H1": mk(Δshave=-3, Δfp=-2.0, p=0.02)}  # both primary signals worse on confirm
        res = hr.decide(dev, confirm, ["H1", "H2"])
        self.assertEqual(res["chosen"], "H1")
        self.assertEqual(res["verdict"], "不採用")
        self.assertIn("主信号", res["reason"])

    def test_reject_when_incomparable_entries(self):
        dev = {"H1": mk(Δshave=+6, Δfp=+1.0, Δwin=0), "H2": mk(Δshave=+2, Δfp=+1.0, Δwin=0)}
        confirm = {"H1": mk(Δshave=+5, Δfp=+1.0, Δwin=0, p=0.02, pairs=11, nc=1)}  # cond6 fails
        res = hr.decide(dev, confirm, ["H1", "H2"])
        self.assertFalse(res["cond"][6])
        self.assertEqual(res["verdict"], "不採用")
        self.assertIn("前提・実装", res["reason"])

    def test_provisional_when_confirm_not_measured(self):
        dev = {"H1": mk(Δshave=+6, Δfp=-4.0), "H2": mk(Δshave=+4, Δfp=-1.0)}
        res = hr.decide(dev, None, ["H1", "H2"])  # confirm4 pending -> provisional
        self.assertEqual(res["chosen"], "H1")
        self.assertEqual(res["verdict"], "保留（暫定）")
        for n in (1, 3, 4, 5, 6):
            self.assertIsNone(res["cond"][n])  # confirm-dependent conditions unevaluated


if __name__ == "__main__":
    unittest.main()
