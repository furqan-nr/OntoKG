"""Instrument checks only; these tests do not constitute participant sessions."""
import csv
import json
from pathlib import Path
import unittest

import jws_objective_study as study


class InstrumentChecks(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((study.OUT / "task_manifest.json").read_text(encoding="utf-8"))

    def test_distinct_cases_and_unknown_evidence(self):
        tasks = self.manifest["tasks"]
        self.assertEqual(len(tasks), 12)
        self.assertEqual(len({(t["company"], t["window"]) for t in tasks}), 12)
        for task in tasks:
            if task["expected_judgment"] == "incomplete":
                self.assertTrue(task["withhold_benchmark"])
                self.assertGreater(study.Decimal(task["company_value"]), study.Decimal(task["sector_value"]))

    def test_counterbalancing(self):
        tasks = {t["task_id"]: t for t in self.manifest["tasks"]}
        for sequence in self.manifest["sequences"].values():
            self.assertEqual(len({t["task_id"] for t in sequence}), 12)
            for condition in ["A", "B"]:
                selected = [r for r in sequence if r["condition"] == condition]
                self.assertEqual(len(selected), 6)
                for truth in ["valid", "invalid", "incomplete"]:
                    self.assertEqual(sum(tasks[r["task_id"]]["expected_judgment"] == truth for r in selected), 2)
        for task in tasks:
            self.assertEqual(sum(next(r["condition"] for r in s if r["task_id"] == task) == "A"
                                 for s in self.manifest["sequences"].values()), 2)

    def test_empty_template_cannot_produce_human_results(self):
        response = study.OUT / "responses_template.csv"
        with self.assertRaisesRegex(ValueError, "No participant responses"):
            study.analyze(response)
        self.assertFalse(response.with_suffix(".analysis.json").exists())

    def test_malformed_record_validation_not_participant_data(self):
        # These isolated field-validation fixtures are never analyzed or saved.
        fixture = dict.fromkeys(study.FIELDS, "unit-test-only")
        fixture.update(judgment="valid", elapsed_seconds="1")
        study.validate_response_fields(fixture)
        for invalid_time in ["nan", "inf", "-inf", "0", "-1", "not-a-time"]:
            with self.assertRaisesRegex(ValueError, "finite and positive"):
                study.validate_response_fields({**fixture, "elapsed_seconds": invalid_time})
        with self.assertRaisesRegex(ValueError, "Judgment"):
            study.validate_response_fields({**fixture, "judgment": "maybe"})
        with self.assertRaisesRegex(ValueError, "Missing fields"):
            study.validate_response_fields({**fixture, "consent": None})


if __name__ == "__main__":
    unittest.main()
