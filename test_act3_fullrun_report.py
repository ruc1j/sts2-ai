import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

# T46: the full-run report must (a) count a Queen fight that has a non-combat row in the middle (the
# gap must not end the fight, so Amalgam killed later is still detected), (b) classify Amalgam as killed
# when it is absent from the fight's last combat row even if it entered already damaged, (c) type the
# Queen-entry deck with the panel-wide hand table (draw-pile cards carry type: null), and (d) skip
# in-flight runs that have a trace but no runmeta/manifest. Wilson intervals are checked against the
# hand-computed panel values.
_TOOLS = Path(__file__).resolve().parent / "bosslab" / "tools"
_spec = importlib.util.spec_from_file_location("act3_fullrun_report", _TOOLS / "act3_fullrun_report.py")
R = importlib.util.module_from_spec(_spec)
sys.modules["act3_fullrun_report"] = R
_spec.loader.exec_module(R)

AMALGAM, QUEEN = "MONSTER.TORCH_HEAD_AMALGAM", "MONSTER.QUEEN"


def _combat(seq, turn, enemies, *, hand=None, draw=None, hp=80, maxhp=87, potions=0):
    return {"seq": seq, "phase": "combat", "turn": turn,
            "player": {"hp": hp, "max_hp": maxhp, "potions": [{} for _ in range(potions)]},
            "hand": hand or [], "draw_pile": draw or [], "discard_pile": [], "exhaust_pile": [],
            "enemies": [{"id": eid, "hp": ehp, "max_hp": ehp} for eid, ehp in enemies]}


ROWS = [
    {"seq": 0, "phase": "map", "run": {"act": 0, "floor": 1}},
    {"seq": 1, "phase": "map", "run": {"act": 2, "floor": 1, "boss_encounter_id": "ENCOUNTER.QUEEN_BOSS"}},
    _combat(2, 1, [(AMALGAM, 150), (QUEEN, 400)],
            hand=[{"id": "CARD.STRIKE", "type": "Attack", "upgrade": 1}],
            draw=[{"id": "CARD.DEFEND", "type": None, "upgrade": 0}]),
    {"seq": 3, "phase": "interaction"},                      # gap inside the fight, must be skipped
    _combat(4, 2, [(QUEEN, 380)]),                           # Amalgam gone by here
    _combat(5, 3, [(QUEEN, 357)]),
    {"seq": 6, "phase": "combat_end", "won": False, "hp": 0},
]
TYPE_MAP = {"CARD.STRIKE": "Attack", "CARD.DEFEND": "Skill"}


class AnalyzeRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)

    def _write(self, tag, seed, rows, complete=True):
        stem = self.data / f"{tag}_{seed}"
        stem.with_name(stem.name + "_agent.jsonl").write_text(
            "\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        if complete:
            stem.with_name(stem.name + "_runmeta.json").write_text(json.dumps({"seed": seed, "exit": 1}),
                                                                   encoding="utf-8")

    def test_queen_fight_spans_gap_and_types_deck_panelwide(self):
        p = self.data / "x_agent.jsonl"
        p.write_text("\n".join(json.dumps(r) for r in ROWS), encoding="utf-8")
        rec = R.analyze_run("SEED", p, TYPE_MAP)
        self.assertTrue(rec["entered"])
        self.assertTrue(rec["fought_queen"])
        self.assertFalse(rec["cleared"])
        # Amalgam entered damaged (150<199) then left the board -> absent from the last Queen row == killed
        self.assertTrue(rec["amalgam_killed"])
        self.assertEqual(rec["death_turn"], 3)
        # removed 400-357 = 43 over 400
        self.assertAlmostEqual(rec["shave"], 43 / 400, places=4)
        deck = rec["queen_entry"]["deck"]
        # DEFEND (type null in the draw pile) is resolved to Skill by the panel-wide hand table
        self.assertEqual(deck.get("Attack"), 1)
        self.assertEqual(deck.get("Skill"), 1)
        self.assertEqual(deck.get("unknown"), 0)
        self.assertEqual(deck.get("deck_total"), 2)
        self.assertEqual(deck.get("upgraded"), 1)
        self.assertEqual(rec["queen_entry"]["hp"], 80)
        self.assertEqual(rec["queen_entry"]["max_hp"], 87)
        self.tmp.cleanup()

    def test_collect_runs_skips_incomplete(self):
        self._write("synthtag", "AAAABBBB11", ROWS, complete=True)
        self._write("synthtag", "CCCDDDDE22", ROWS, complete=False)   # trace only -> in-flight, skipped
        runs = R.collect_runs(self.data, ["synthtag"])
        self.assertEqual([r["seed"] for r in runs], ["AAAABBBB11"])
        self.tmp.cleanup()

    def test_wilson_matches_panel_values(self):
        self.assertEqual(R.wilson(45, 136), (25.7, 41.4))
        self.assertEqual(R.wilson(33, 45), (59.0, 84.0))
        self.assertEqual(R.wilson(19, 33), (40.8, 72.8))
        lo, hi = R.wilson(0, 136)
        self.assertEqual(lo, 0.0)
        self.assertLess(hi, 5.0)
        self.assertTrue(all(x != x for x in R.wilson(1, 0)))   # n=0 -> nan


if __name__ == "__main__":
    unittest.main()
