"""Regression coverage for matching forecasts to the action that was actually taken."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from qone_core.cli import main
from qone_core.ledger import Ledger
from qone_core.report import build_report, format_report


class ReportOutcomeMatchingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.ledger = Ledger(Path(self.directory.name) / "ledger.jsonl")

    def record(self, decision_id, *, chosen="a", probability=0.8, success="yes", recommend=True):
        self.ledger.append("decision_created", {"decision_id": decision_id})
        if recommend:
            self.ledger.append(
                "recommendation_made",
                {"decision_id": decision_id, "option_id": "a", "success_probability": probability},
            )
        self.ledger.append("human_decision", {"decision_id": decision_id, "option_id": chosen})
        self.ledger.append("outcome_recorded", {"decision_id": decision_id, "success": success})

    def test_cli_override_flow_with_default_empty_notes(self):
        common = ["--data-dir", self.directory.name]

        def call(arguments):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(common + arguments)
            self.assertEqual(status, 0)
            return output.getvalue().strip()

        example = Path(__file__).resolve().parents[1] / "examples" / "decision.json"
        decision_id = call(["create", "--file", str(example)])
        call(["baseline", "--decision", decision_id, "--option", "draft"])
        call([
            "recommend", "--decision", decision_id, "--option", "draft",
            "--confidence", "0.8", "--success-probability", "0.9",
            "--rationale", "Synthetic CLI fixture", "--source", "synthetic-fixture",
        ])
        call(["decide", "--decision", decision_id, "--option", "meeting"])
        # notes is optional in the CLI and must remain optional in validation.
        call(["resolve", "--decision", decision_id, "--success", "yes"])
        report = json.loads(call(["report", "--json"]))
        self.assertEqual(report["calibration"]["n"], 0)
        self.assertEqual(report["calibration"]["exclusion_counts"], {
            "recommended_option_not_selected": 1
        })
        self.assertEqual(report["recommendation_adoption_n"], 1)
        self.assertEqual(report["recommendation_adoption"], 0)
        self.assertIn("calibration excluded: 1", call(["report"]))
        self.assertEqual(call(["verify"]), "verified 5 events")

    def test_override_is_unobserved_even_when_alternative_succeeds(self):
        self.record("overridden", chosen="b", probability=0.9)
        report = build_report(self.ledger)
        calibration = report["calibration"]
        self.assertEqual(calibration["n"], 0)
        self.assertIsNone(calibration["brier_score"])
        self.assertIsNone(calibration["wilson_95"])
        self.assertEqual(calibration["excluded_rows"], [
            {"decision_id": "overridden", "reason": "recommended_option_not_selected"}
        ])
        self.assertEqual(report["recommendation_adoption"], 0.0)
        self.assertIn("recommended_option_not_selected", format_report(report))

    def test_mixed_outcomes_keep_traceable_rows_and_recomputable_denominators(self):
        self.record("adopted-success", probability=0.8)
        self.record("adopted-failure", probability=0.3, success="no")
        self.record("override", chosen="b", probability=0.99)
        self.record("unknown", probability=0.6, success="unknown")
        self.record("partial", probability=0.6, success="partial")
        self.record("no-probability", probability=None)
        self.record("human-only", recommend=False)
        report = build_report(self.ledger)
        calibration = report["calibration"]
        self.assertEqual(calibration["candidate_decisions"], 6)
        self.assertEqual(calibration["n"], 2)
        self.assertEqual(calibration["excluded"], 4)
        self.assertEqual(calibration["exclusion_counts"], {
            "recommended_option_not_selected": 1,
            "non_binary_outcome": 2,
            "missing_probability": 1,
        })
        self.assertAlmostEqual(calibration["brier_score"], 0.065)
        self.assertEqual(calibration["observed_success_rate"], 0.5)
        self.assertEqual([row["decision_id"] for row in calibration["rows"]], [
            "adopted-success", "adopted-failure"
        ])
        self.assertEqual(report["recommendation_adoption_n"], 6)
        self.assertEqual(report["recommendation_adopted"], 5)
        self.assertAlmostEqual(report["recommendation_adoption"], 5 / 6)
        self.assertEqual(self.ledger.verify(), 27)

    def test_unresolved_prediction_does_not_count_as_failure(self):
        self.ledger.append("decision_created", {"decision_id": "waiting"})
        self.ledger.append("recommendation_made", {
            "decision_id": "waiting", "option_id": "a", "success_probability": 0.8
        })
        report = build_report(self.ledger)
        self.assertEqual(report["calibration"]["exclusion_counts"], {"unresolved": 1})
        self.assertIsNone(report["calibration"]["brier_score"])
        self.assertIsNone(report["recommendation_adoption"])

    def test_human_only_decision_has_no_adoption_denominator(self):
        self.record("human-only", recommend=False)
        report = build_report(self.ledger)
        self.assertEqual(report["recommendation_adoption_n"], 0)
        self.assertIsNone(report["recommendation_adoption"])
        self.assertEqual(report["calibration"]["candidate_decisions"], 0)

    def test_invalid_numeric_probability_from_library_caller_is_excluded(self):
        self.record("invalid-probability", probability=2)
        report = build_report(self.ledger)
        self.assertEqual(report["calibration"]["exclusion_counts"], {"invalid_probability": 1})
        self.assertIsNone(report["calibration"]["brier_score"])

    def test_resolved_event_without_human_choice_is_not_scored(self):
        self.ledger.append("decision_created", {"decision_id": "missing-choice"})
        self.ledger.append("recommendation_made", {
            "decision_id": "missing-choice", "option_id": "a", "success_probability": 0.8
        })
        self.ledger.append("outcome_recorded", {"decision_id": "missing-choice", "success": "yes"})
        report = build_report(self.ledger)
        self.assertEqual(report["calibration"]["exclusion_counts"], {"missing_human_decision": 1})
        self.assertIsNone(report["calibration"]["brier_score"])


if __name__ == "__main__":
    unittest.main()
