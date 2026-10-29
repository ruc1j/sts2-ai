import importlib.util
import json
import sys
import unittest
from pathlib import Path

# T41 item 2: the Python side only builds and integrity-checks the entry write-back record the 20892cd C#
# hook consumes (we do not build the C#). A record built from a captured combat-start must be well-formed
# (every enemy hp within bounds, exactly the four piles, every card carries id/upgrade), reproduce the
# observation exactly, and stay default-off unless a plan trial or env turns the hook on.
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("entry_record", _TOOLS / "entry_record.py")
T = importlib.util.module_from_spec(_spec)
sys.modules["entry_record"] = T
_spec.loader.exec_module(T)

AMID, QID = "MONSTER.TORCH_HEAD_AMALGAM", "MONSTER.QUEEN"
CAUSE_SPECS = ("8aa46daede55", "e030d2f11e5f")  # FORGOTTEN_SOUL / BLESSED_ANTLER double-fired-entry specs


def _obs():
    return {
        "phase": "combat", "turn": 1, "player": {"hp": 78, "max_hp": 90, "relic_counters": {}},
        "enemies": [{"id": AMID, "hp": 198, "max_hp": 199}, {"id": QID, "hp": 400, "max_hp": 400}],
        "draw_pile": [{"id": "CARD.BASH", "upgrade": 1, "enchantment": None},
                 {"id": "CARD.DEFEND", "upgrade": 0, "enchantment": "ENCHANT.TRANSFORM"}],
        "hand": [{"index": 0, "id": "CARD.STRIKE_IRONCLAD", "upgrade": 0, "enchantment": None}],
        "discard_pile": [],
        "exhaust_pile": [{"id": "CARD.ULTIMATE_DEFEND", "upgrade": 1, "enchantment": None}],
    }


class BuildAndValidateTest(unittest.TestCase):
    def test_record_from_observation_is_well_formed_and_reproduces_it(self):
        obs = _obs()
        rec = T.build_entry_record(obs)
        self.assertEqual(T.entry_record_problems(rec), [])   # no integrity problems
        self.assertTrue(T.record_reproduces_observation(rec, obs))
        self.assertFalse(rec["restore_entry_state"])          # default off

    def test_enemy_hp_above_max_is_flagged(self):
        obs = _obs()
        obs["enemies"][0]["hp"] = 500  # > max_hp 199
        rec = T.build_entry_record(obs)
        self.assertTrue(any("out of range" in p for p in T.entry_record_problems(rec)))

    def test_missing_and_duplicate_piles_are_flagged(self):
        rec = T.build_entry_record(_obs())
        rec["piles"] = [p for p in rec["piles"] if p["pile_type"] != "exhaust_pile"]
        rec["piles"].append({"pile_type": "draw_pile", "cards": []})   # now 'draw_pile' duplicated, 'exhaust_pile' missing
        problems = T.entry_record_problems(rec)
        self.assertTrue(any("duplicate pile_type" in p for p in problems))
        self.assertTrue(any("missing pile" in p for p in problems))

    def test_non_int_upgrade_is_flagged(self):
        rec = T.build_entry_record(_obs())
        rec["piles"][0]["cards"][0]["upgrade"] = None
        self.assertTrue(any("non-int upgrade" in p for p in T.entry_record_problems(rec)))

    def test_record_mismatch_when_a_card_is_dropped(self):
        obs = _obs()
        rec = T.build_entry_record(obs)
        rec["piles"][3]["cards"] = []  # observation had an exhausted card, record dropped it
        self.assertFalse(T.record_reproduces_observation(rec, obs))


class RestoreFlagTest(unittest.TestCase):
    def test_default_off(self):
        self.assertFalse(T.restore_flag_enabled(plan_trial={}, env={}))

    def test_env_turns_it_on(self):
        self.assertTrue(T.restore_flag_enabled(plan_trial={}, env={T.RESTORE_ENV: "1"}))

    def test_plan_trial_turns_it_on(self):
        self.assertTrue(T.restore_flag_enabled(plan_trial={"restore_entry_state": True}, env={}))


class RealFid5Test(unittest.TestCase):
    """If the committed fid5 traces are present, the two double-fired-entry specs must round-trip through the
    record (proving the capture reproduces the recorded entry enemy HP the hook must replay)."""
    _FID = Path(__file__).resolve().parent / "data" / "bosslab_act3_fid5"

    def _first_obs(self, spec_id):
        lab = self._FID / "lab_results.jsonl"
        if not lab.is_file():
            return None
        for l in lab.read_text(encoding="utf-8").splitlines():
            if not l.strip():
                continue
            rec = json.loads(l)
            if rec.get("spec_id") != spec_id:
                continue
            f = self._FID / f"trial_{int(rec['trial_index']):04d}_agent.jsonl"
            if not f.is_file():
                return None
            for rl in f.read_text(encoding="utf-8").splitlines():
                o = json.loads(rl)
                if o.get("phase") == "combat":
                    return o
        return None

    def test_cause_specs_round_trip_integrity(self):
        seen = 0
        for spec in CAUSE_SPECS:
            obs = self._first_obs(spec)
            if obs is None:
                continue
            seen += 1
            rec = T.build_entry_record(obs)
            self.assertEqual(T.entry_record_problems(rec), [], spec)
            self.assertTrue(T.record_reproduces_observation(rec, obs), spec)
            # the recorded enemy hp equals the observed entry hp the hook must replay (write-back target).
            for e in rec["enemies"]:
                self.assertLessEqual(e["hp"], e["max_hp"])
        if seen == 0:
            self.skipTest("committed fid5 traces not present in this checkout")


if __name__ == "__main__":
    unittest.main()
