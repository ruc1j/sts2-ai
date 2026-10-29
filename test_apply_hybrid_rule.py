import unittest
import importlib.util
import json
import tempfile
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


def _panel_dir(tmp: Path, plan: list) -> Path:
    """Write a minimal run dir: lab_results.jsonl + per-trial traces, for pair_attack_target_diff.

    plan = [(spec_id, offset, {slot: attack_count}), ...]; each slot becomes single-target Attack lines
    with target_id = enemy combat_id (1=amalgam, 2=queen), matching what CombatBridge writes."""
    cid = {"amalgam": 1, "queen": 2}
    mid = {"amalgam": "MONSTER.TORCH_HEAD_AMALGAM", "queen": "MONSTER.QUEEN"}
    d = tmp
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "lab_results.jsonl", "w", encoding="utf-8") as lab:
        for i, (spec, off, slots) in enumerate(plan):
            lab.write(json.dumps({
                "trial_index": i, "trial_id": f"{spec}|base|{off}", "spec_id": spec,
                "result": {"outcome_source": "combat_end_trace", "won": False,
                           "entry_player_hp": 80}}) + "\n")
            lines = []
            for slot, count in slots.items():
                for _ in range(count):
                    lines.append(json.dumps({
                        "phase": "combat", "turn": 1, "type": "card", "hand_index": 0,
                        "card_id": "CARD.STRIKE_IRONCLAD", "target_id": cid[slot],
                        "hand": [{"id": "CARD.STRIKE_IRONCLAD", "type": "Attack", "cost": 1}],
                        "enemies": [{"combat_id": cid[s], "slot": s, "id": mid[s], "hp": 100} for s in cid]}))
            (d / f"trial_{i:04d}_agent.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return d


def _fired(n: int) -> dict:
    return {"fired": n, "pairs": 12, "skipped_missing_trace": 0, "fired_detail": []}


class PairAttackTargetDiffTest(unittest.TestCase):
    def test_counts_entries_whose_attack_target_differs(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            base = _panel_dir(tmp / "base", [("sA", "o0", {"amalgam": 2}), ("sB", "o0", {"amalgam": 2}),
                                             ("sC", "o0", {"queen": 1})])
            cand = _panel_dir(tmp / "cand", [("sA", "o0", {"queen": 2}), ("sB", "o0", {"amalgam": 2}),
                                             ("sC", "o0", {"amalgam": 1})])
            r = hr.pair_attack_target_diff(base, cand)
            self.assertEqual(r["pairs"], 3)
            self.assertEqual(r["fired"], 2)  # sA and sC changed 殴り先; sB kept amalgam
            self.assertEqual({d[0] for d in r["fired_detail"]}, {"sA", "sC"})

    def test_same_targets_do_not_count_as_firing(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            base = _panel_dir(tmp / "b", [("sA", "o0", {"amalgam": 3})])
            cand = _panel_dir(tmp / "c", [("sA", "o0", {"amalgam": 3})])
            self.assertEqual(hr.pair_attack_target_diff(base, cand)["fired"], 0)

    def test_only_shared_specs_are_paired(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            base = _panel_dir(tmp / "b", [("sA", "o0", {"amalgam": 1}), ("sX", "o0", {"amalgam": 1})])
            cand = _panel_dir(tmp / "c", [("sA", "o0", {"queen": 1}), ("sY", "o0", {"queen": 1})])
            r = hr.pair_attack_target_diff(base, cand)
            self.assertEqual(r["pairs"], 1)  # only sA is in both dirs
            self.assertEqual(r["fired"], 1)


class FiringGateDecideTest(unittest.TestCase):
    # dev/confirm deltas that satisfy frozen conditions 1-6 for candidate H2 (larger Δfp -> chosen).
    DEV = {"H1": mk(Δshave=+4, Δfp=+1.0, p=0.01), "H2": mk(Δshave=+3, Δfp=+2.0, p=0.01)}
    CONF = {"H1": mk(Δshave=+3, Δfp=+2.0, p=0.01), "H2": mk(Δshave=+4, Δfp=+1.0, p=0.01)}

    def test_no_firing_input_keeps_frozen_behaviour(self):
        res = hr.decide(self.DEV, self.CONF, ["H1", "H2"])
        self.assertEqual(res["chosen"], "H2")
        self.assertEqual(res["verdict"], "採用")
        self.assertNotIn("前提 G", res["reason"])  # firing=None -> identical to 4693f2e

    def test_adopt_when_firing_clears_threshold_on_both_sets(self):
        firing = {"dev": {"H1": _fired(6), "H2": _fired(5)},
                  "confirm": {"H1": _fired(6), "H2": _fired(5)}}
        res = hr.decide(self.DEV, self.CONF, ["H1", "H2"], firing=firing)
        self.assertEqual(res["chosen"], "H2")
        self.assertIs(res["cond"]["G"], True)
        self.assertEqual(res["verdict"], "採用")
        self.assertIn("前提 G", res["reason"])

    def test_confirm_side_firing_short_is_measure_incapable_not_reject(self):
        firing = {"dev": {"H1": _fired(6), "H2": _fired(5)},          # both clear dev -> H2 chosen
                  "confirm": {"H1": _fired(6), "H2": _fired(2)}}       # chosen below 4 on confirm
        res = hr.decide(self.DEV, self.CONF, ["H1", "H2"], firing=firing)
        self.assertEqual(res["chosen"], "H2")
        self.assertIs(res["cond"]["G"], False)
        self.assertEqual(res["verdict"], "保留")
        self.assertIn("測定不能", res["reason"])  # never 不採用

    def test_no_dev_candidate_fires_is_measure_incapable(self):
        firing = {"dev": {"H1": _fired(1), "H2": _fired(0)}, "confirm": None}
        res = hr.decide(self.DEV, self.CONF, ["H1", "H2"], firing=firing)
        self.assertIsNone(res["chosen"])
        self.assertEqual(res["verdict"], "保留")
        self.assertIs(res["branch"], hr.SELECT_NOFIRE)
        self.assertIn("測定不能", res["reason"])

    def test_format_report_shows_firing_and_g(self):
        firing = {"dev": {"H1": _fired(6), "H2": _fired(5)}, "confirm": {"H1": _fired(6), "H2": _fired(2)}}
        res = hr.decide(self.DEV, self.CONF, ["H1", "H2"], firing=firing)
        text = hr.format_report(res, ["H1", "H2"])
        self.assertIn("前提 G", text)
        self.assertIn("dev2 発火 5/12", text)   # chosen H2 dev-side count shown
        self.assertIn("測定不能", text)




if __name__ == "__main__":
    unittest.main()
