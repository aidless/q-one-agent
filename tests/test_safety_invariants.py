"""Offline contract and fault-injection checks for three safety invariants.

The matrix is recomputed on every run. It does not contact Ollama, Laya weights,
or a cloud provider. A returned cost-heuristic recommendation on a fault is a
failure of the no-silent-fallback invariant.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fault_matrix_lib import REPORT_PATH, build_report, dump_report


class SafetyInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()

    def test_fault_matrix_never_emits_heuristic_or_unsafe_flags(self):
        self.assertFalse(self.report["live_provider_contacted"])
        self.assertEqual(len(self.report["fault_cells"]), 15)
        for cell in self.report["fault_cells"]:
            with self.subTest(adapter=cell["adapter"], fault=cell["fault"]):
                self.assertTrue(cell["invariant_ok"], cell)
                self.assertFalse(cell["heuristic_called"])
                self.assertFalse(cell["heuristic_emitted"])
                self.assertFalse(cell["decision_mutated"])
                self.assertEqual(cell["human_decision_keys"], [])
                self.assertIn(cell["outcome_kind"], {"raise", "explicit_failure"})
                self.assertNotEqual(cell["outcome"], "return:cost-heuristic-v0.1")
                self.assertNotIn("cost-heuristic-v0.1", cell["message"])

    def test_hostile_model_flags_cannot_mark_auto_execute_or_human_decision(self):
        self.assertEqual(len(self.report["hostile_success"]), 3)
        for cell in self.report["hostile_success"]:
            with self.subTest(adapter=cell["adapter"]):
                self.assertEqual(cell["outcome_kind"], "return")
                self.assertFalse(cell["heuristic_emitted"])
                self.assertFalse(cell["heuristic_called"])
                self.assertFalse(cell["auto_eligible"])
                self.assertTrue(cell["requires_human"])
                self.assertIsNone(cell["success_probability"])
                self.assertEqual(cell["human_decision_keys"], [])
                self.assertFalse(cell["source"].startswith("cost-heuristic"))
                self.assertTrue(cell["source"].startswith(cell["adapter"] + ":"))

    def test_roundtrip_uses_vendored_core_validator_not_a_made_up_schema_file(self):
        pin = self.report["core_pin"]
        self.assertEqual(pin["commit"], "2d243b33c0beede7cf05d1ab2212f5fb45d39c6a")
        self.assertIn("does not publish a recommendation JSON Schema", pin["note"])
        trip = self.report["schema_roundtrip"]
        self.assertEqual(trip["engine_core_validator"], "accepted")
        self.assertEqual(trip["engine_local_schema"], "accepted")
        self.assertEqual(trip["run_model_core_validator"], "accepted")
        self.assertEqual(trip["run_model_local_schema"], "rejected")
        self.assertEqual(trip["run_model_missing_local_keys"], ["decision_id", "gate_reasons"])
        self.assertTrue(trip["vendored_validator_overwrites_flags"])
        self.assertFalse(trip["engine_auto_eligible"])
        self.assertTrue(trip["engine_requires_human"])
        self.assertFalse(trip["run_model_auto_eligible"])
        self.assertTrue(trip["run_model_requires_human"])
        self.assertEqual(trip["engine_human_decision_keys"], [])
        self.assertEqual(trip["run_model_human_decision_keys"], [])
        self.assertIn("MockTransport", trip["run_model_injection"])

    def test_cli_demo_is_labeled_heuristic_and_does_not_write_human_decision(self):
        demo = self.report["cli_heuristic_demo"]
        self.assertEqual(demo["source"], "cost-heuristic-v0.1")
        self.assertEqual(demo["option_id"], "meeting")
        self.assertTrue(demo["requires_human"])
        self.assertFalse(demo["auto_eligible"])
        self.assertIsNone(demo["success_probability"])
        self.assertEqual(demo["human_decision_keys"], [])
        self.assertNotIn("decided_by", demo["stdout"])

    def test_committed_matrix_matches_recompute(self):
        actual = dump_report(self.report)
        committed = REPORT_PATH.read_text(encoding="utf-8")
        self.assertEqual(committed, actual)


if __name__ == "__main__":
    unittest.main()
