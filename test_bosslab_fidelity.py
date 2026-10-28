"""Tests for the BossLab fidelity checker (bosslab/tools/bosslab_fidelity.py).

The checker compares a trial's first in-game observation with the spec it was built from and with the
original run's boss-entry observation. Two behaviours here were wrong for Act 3 and are pinned:

  * the original-run locator used a hardcoded Act 2 monster, so Act 3 specs were compared against the
    Act 2 boss in the same trace (which produced 9 bogus mismatches per trial);
  * the per-card cost/value comparison counted copies, so it reported noise whenever the shuffle put a
    different number of copies in hand, instead of only real value differences.
"""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent
TOOL = REPO / "bosslab" / "tools" / "bosslab_fidelity.py"


def load_tool():
    module_spec = importlib.util.spec_from_file_location("bosslab_fidelity", TOOL)
    assert module_spec and module_spec.loader
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def obs(seq: int, enemies: list[dict], cards: list[dict], **extra) -> dict:
    payload = {"seq": seq, "phase": "combat", "turn": 1, "enemies": enemies,
               "hand": cards, "draw_pile": [], "discard_pile": [], "exhaust_pile": [],
               "player": {"hp": 80, "max_hp": 80, "block": 0, "energy": 3, "max_energy": 3,
                          "relics": [], "relic_counters": {}, "powers": []},
               "potions": []}
    payload.update(extra)
    return payload


class BossLabFidelityTest(unittest.TestCase):
    def setUp(self) -> None:
        if not TOOL.is_file():
            self.skipTest(f"{TOOL} is not present in this checkout")
        self.tool = load_tool()

    def test_locator_uses_the_specs_own_monster_not_act2_boss(self) -> None:
        queen_spec = {"spec_id": "q", "enemies": [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400}],
                      "sources": [{"trace": "run_agent.jsonl", "entry_seq": 2}]}
        rows = [obs(0, [{"id": "MONSTER.THE_INSATIABLE", "hp": 321, "max_hp": 321}], [], phase="combat"),
                obs(1, [{"id": "MONSTER.THE_INSATIABLE", "hp": 300, "max_hp": 321}], []),
                obs(2, [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400},
                        {"id": "MONSTER.TORCH_HEAD_AMALGAM", "hp": 199, "max_hp": 199}], []),
                ]
        with self.subTest("entry_seq matches the Queen row"), tempfile_trace(rows) as trace_dir:
            found = self.tool.orig_boss_obs(queen_spec, trace_dir)
            self.assertIsNotNone(found)
            self.assertTrue(any(str(enemy["id"]).endswith("QUEEN") for enemy in found["enemies"]))

    def test_locator_falls_back_to_the_matching_monster_without_entry_seq(self) -> None:
        spec = {"spec_id": "q", "enemies": [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400}],
                "sources": [{"trace": "run_agent.jsonl"}]}
        rows = [obs(0, [{"id": "MONSTER.THE_INSATIABLE", "hp": 321, "max_hp": 321}], []),
                obs(5, [{"id": "MONSTER.QUEEN", "hp": 400, "max_hp": 400}], [])]
        with tempfile_trace(rows) as trace_dir:
            found = self.tool.orig_boss_obs(spec, trace_dir)
            self.assertEqual(5, (found or {}).get("seq"))

    def test_value_compare_ignores_copy_counts_and_flags_real_changes(self) -> None:
        def strike(value: str) -> dict:
            return {"id": "CARD.STRIKE_IRONCLAD", "upgrade": 0, "enchantment": "", "cost": 1,
                    "vars": [{"id": "Damage", "value": value}]}

        lab = obs(0, [], [strike("9"), strike("9"), strike("9")])
        same_values_other_count = obs(0, [], [strike("9"), strike("9")])
        different_value = obs(0, [], [strike("6")])
        rows, compared, skipped = self.tool.compare_card_values(lab, same_values_other_count)
        self.assertEqual([], rows)
        self.assertEqual(1, compared)
        self.assertEqual(0, skipped)
        rows, _compared, _skipped = self.tool.compare_card_values(lab, different_value)
        self.assertEqual(1, len(rows))
        self.assertEqual("CARD.STRIKE_IRONCLAD+0+", rows[0][0])

    def test_values_are_skipped_when_only_one_side_previewed_them(self) -> None:
        previewed = obs(0, [], [{"id": "CARD.SHRUG_IT_OFF", "upgrade": 0, "enchantment": "",
                                 "cost": 1, "vars": [{"id": "Block", "value": 10}]}])
        unpreviewed = obs(0, [], [{"id": "CARD.SHRUG_IT_OFF", "upgrade": 0, "enchantment": "",
                                   "cost": None, "vars": []}])
        rows, compared, skipped = self.tool.compare_card_values(previewed, unpreviewed)
        self.assertEqual([], rows)
        self.assertEqual(0, compared)
        self.assertEqual(1, skipped)


class tempfile_trace:
    """Context manager writing a one-trace directory that the locator can read."""

    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def __enter__(self) -> Path:
        import tempfile
        self._dir = tempfile.TemporaryDirectory()
        root = Path(self._dir.name)
        (root / "run_agent.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in self.rows),
            encoding="utf-8")
        return root

    def __exit__(self, *_exc) -> None:
        self._dir.cleanup()


if __name__ == "__main__":
    unittest.main()
