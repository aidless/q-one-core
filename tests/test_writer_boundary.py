"""Observed writer boundary: DecisionService enforces transitions; Ledger.append does not.

These tests record current behavior. They are not a claim that the CLI is a
locked product API.
"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from qone_core.cli import main
from qone_core.ledger import Ledger
from qone_core.models import ValidationError
from qone_core.service import DecisionService


def example(decision_id="D-test"):
    return {
        "decision_id": decision_id,
        "question": "Which option?",
        "domain": "work",
        "success_criterion": "A reviewable draft exists",
        "deadline": "2030-01-01T00:00:00Z",
        "reversible": True,
        "risk": "low",
        "options": [
            {"id": "draft", "label": "Write"},
            {"id": "meeting", "label": "Meet"},
        ],
    }


def recommendation(option_id="draft"):
    return {
        "option_id": option_id,
        "confidence": 0.82,
        "success_probability": 0.70,
        "rationale": "Synthetic fixture",
        "source": "test",
    }


class WriterBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Ledger(Path(self.temp.name) / "ledger.jsonl")
        self.service = DecisionService(self.ledger)
        self.service.create(example())

    def test_service_rejects_recommendation_without_baseline(self):
        with self.assertRaises(ValidationError):
            self.service.recommend("D-test", recommendation())
        self.assertEqual(self.ledger.verify(), 1)

    def test_append_records_recommendation_without_baseline(self):
        self.ledger.append("recommendation_made", {"decision_id": "D-test", **recommendation()})
        self.assertEqual(self.ledger.verify(), 2)
        self.assertEqual(self.ledger.get("D-test")["status"], "recommended")
        self.assertNotIn("baseline", self.ledger.get("D-test"))

    def test_append_accepts_a_second_baseline(self):
        self.ledger.append(
            "baseline_recorded",
            {"decision_id": "D-test", "option_id": "draft", "note": "first"},
        )
        self.ledger.append(
            "baseline_recorded",
            {"decision_id": "D-test", "option_id": "meeting", "note": "later"},
        )
        self.assertEqual(self.ledger.verify(), 3)
        self.assertEqual(self.ledger.get("D-test")["baseline"]["option_id"], "meeting")

    def test_service_rejects_a_second_baseline(self):
        self.service.baseline("D-test", "draft")
        with self.assertRaises(ValidationError):
            self.service.baseline("D-test", "meeting")
        self.assertEqual(self.ledger.get("D-test")["baseline"]["option_id"], "draft")
        self.assertEqual(self.ledger.verify(), 2)

    def test_service_always_records_human_decider(self):
        self.service.baseline("D-test", "draft")
        self.service.decide("D-test", "draft", "")
        payload = self.ledger.get("D-test")["human_decision"]
        self.assertEqual(payload["decided_by"], "human")

    def test_append_can_record_recommendation_before_baseline(self):
        self.ledger.append("recommendation_made", {"decision_id": "D-test", **recommendation()})
        self.ledger.append(
            "baseline_recorded",
            {"decision_id": "D-test", "option_id": "draft", "note": "after the recommendation"},
        )
        state = self.ledger.get("D-test")
        self.assertEqual(state["status"], "baseline_recorded")
        self.assertEqual(state["recommendation"]["option_id"], "draft")
        self.assertEqual(state["baseline"]["note"], "after the recommendation")
        self.assertEqual([event["type"] for event in state["events"]], [
            "decision_created",
            "recommendation_made",
            "baseline_recorded",
        ])

    def test_cli_by_flag_is_stored_verbatim(self):
        example_path = Path(self.temp.name) / "decision.json"
        fresh = Path(self.temp.name) / "cli"
        fresh.mkdir()
        example_path.write_text(json.dumps(example("D-cli")), encoding="utf-8")

        def call(args):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(["--data-dir", str(fresh)] + args)
            self.assertEqual(status, 0, args)
            return output.getvalue().strip()

        decision_id = call(["create", "--file", str(example_path)])
        call(["baseline", "--decision", decision_id, "--option", "draft"])
        call(
            [
                "decide",
                "--decision",
                decision_id,
                "--option",
                "draft",
                "--by",
                "not-a-person",
            ]
        )
        state = Ledger(fresh / "ledger.jsonl").get(decision_id)
        self.assertEqual(state["human_decision"]["decided_by"], "not-a-person")
