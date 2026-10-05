import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from data import run_usability, shop_preaction_audit


class ShopPreactionAuditTest(unittest.TestCase):
    def test_legacy_removal_recomputes_affordability_from_entry_gold(self) -> None:
        record = {
            "action": "remove", "purchased": True, "gold": 180,
            "offers": [
                {"kind": "removal", "id": "remove", "cost": 100, "affordable": False},
                {"kind": "relic", "id": "RELIC.THE_ABACUS", "cost": 200, "affordable": False},
                {"kind": "relic", "id": "RELIC.EXPENSIVE", "cost": 300, "affordable": False},
            ],
        }
        gold, offers = shop_preaction_audit.preaction_state(record)
        self.assertEqual(gold, 280)
        self.assertEqual([offer["affordable"] for offer in offers], [True, True, False])
        self.assertFalse(record["offers"][1]["affordable"])

    def test_missing_purchased_item_price_is_unknown(self) -> None:
        record = {"action": "buy_relic", "purchased": True, "relic_id": "RELIC.ANCHOR",
                  "gold": 10, "offers": []}
        self.assertIsNone(shop_preaction_audit.chosen_cost(record))
        self.assertEqual(shop_preaction_audit.preaction_state(record), (None, None))

    def test_snapshot_preserves_bought_offer_and_stock_state(self) -> None:
        offers = [{"kind": "relic", "id": "RELIC.ANCHOR", "cost": 155,
                   "stocked": True, "affordable": True},
                  {"kind": "removal", "id": "remove", "cost": 75,
                   "stocked": False, "affordable": False}]
        record = {"action": "buy_relic", "purchased": True, "gold": 10, "offers": [],
                  "gold_before": 165, "offers_before": offers}
        self.assertEqual(shop_preaction_audit.preaction_state(record), (165, offers))

    def test_failed_purchase_does_not_add_a_cost(self) -> None:
        record = {"action": "remove", "purchased": False, "gold": 180,
                  "offers": [{"kind": "removal", "id": "remove", "cost": 100, "affordable": True}]}
        self.assertEqual(shop_preaction_audit.chosen_cost(record), 0)
        self.assertEqual(shop_preaction_audit.preaction_state(record)[0], 180)

    def test_cli_accepts_spaced_json_and_marks_unknown_entry_state(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            trace = Path(folder) / "shop.jsonl"
            trace.write_text(json.dumps({"seq": 5, "phase": "shop", "action": "buy_relic",
                                         "relic_id": "RELIC.ANCHOR", "purchased": True,
                                         "gold": 10, "offers": []}) + "\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(shop_preaction_audit.main(["audit", str(trace)]), 0)
            self.assertIn("不明", output.getvalue())
            self.assertNotIn("入店 gold   10", output.getvalue())


class RunUsabilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.trace = Path(self.folder.name) / "test_SEED_agent.jsonl"
        self.modlog = Path(self.folder.name) / "test_SEED_mod.log"
        self.result = Path(self.folder.name) / "test_SEED_result.json"

    def write_trace(self, *records) -> None:
        self.trace.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")

    def test_one_won_combat_does_not_prove_run_completion(self) -> None:
        self.write_trace({"phase": "combat_end", "won": True, "hp": 73})
        self.assertEqual(run_usability.verdict(self.trace, None)[0], "check")

    def test_stale_log_after_won_combat_is_incomplete(self) -> None:
        self.write_trace({"phase": "combat_end", "won": True, "hp": 73})
        self.modlog.write_text("Waiting for rewards\n", encoding="utf-8")
        old = time.time() - 600
        os.utime(self.modlog, (old, old))
        self.assertEqual(run_usability.verdict(self.trace, self.modlog)[0], "unusable")

    def test_death_and_death_followed_by_terminal_are_usable(self) -> None:
        death = {"phase": "combat_end", "won": False, "hp": 0}
        for records in ((death,), (death, {"terminal": True})):
            with self.subTest(records=records):
                self.write_trace(*records)
                self.assertEqual(run_usability.verdict(self.trace, None)[0], "usable")

    def test_act_three_result_confirms_completion(self) -> None:
        self.write_trace({"phase": "card_reward", "type": "card_reward_alternative"})
        self.result.write_text(json.dumps({"act_3_complete": True}), encoding="utf-8")
        self.assertEqual(run_usability.verdict(self.trace, None)[0], "usable")

    def test_stale_result_or_partial_act_does_not_confirm_completion(self) -> None:
        self.write_trace({"phase": "combat_end", "won": True, "hp": 73}, {"terminal": True})
        self.result.write_text(json.dumps({"act_3_complete": True}), encoding="utf-8")
        old = self.trace.stat().st_mtime - 10
        os.utime(self.result, (old, old))
        self.assertEqual(run_usability.verdict(self.trace, None)[0], "check")
        self.result.write_text(json.dumps({"act_1_complete": True, "act_3_complete": False}), encoding="utf-8")
        self.assertEqual(run_usability.verdict(self.trace, None)[0], "check")

    def test_cli_accepts_explicit_log_path(self) -> None:
        self.write_trace({"phase": "combat_end", "won": False, "hp": 0})
        self.modlog.write_text("not JSON\n", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(run_usability.main(["audit", str(self.trace), str(self.modlog)]), 0)
        self.assertEqual(output.getvalue().count("seed SEED:"), 1)


if __name__ == "__main__":
    unittest.main()
