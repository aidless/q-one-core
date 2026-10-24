import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from qone_core.ledger import Ledger
from qone_core.models import ValidationError, validate_decision
from qone_core.service import DecisionService


def example():
    return {"decision_id": "D-test", "question": "先学什么？", "domain": "learning",
            "success_criterion": "完成一个练习", "deadline": "2030-01-01T00:00:00Z",
            "reversible": True, "risk": "low", "options": [{"id": "a", "label": "练习"}, {"id": "b", "label": "看书"}]}


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Ledger(Path(self.temp.name) / "events.jsonl")
        self.service = DecisionService(self.ledger)
        self.service.create(example())

    def test_full_human_workflow_and_no_duplicate_settlement(self):
        self.service.baseline("D-test", "a")
        self.service.decide("D-test", "b")
        self.service.resolve("D-test", "partial", "还需练习")
        self.assertEqual(self.ledger.get("D-test")["status"], "resolved")
        before = self.ledger.events()
        with self.assertRaises(ValidationError):
            self.service.resolve("D-test", "yes")
        self.assertEqual(before, self.ledger.events())

    def test_competing_baselines_only_one_is_appended(self):
        def attempt(option):
            try:
                DecisionService(Ledger(self.ledger.path)).baseline("D-test", option)
                return True
            except ValidationError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt, ("a", "b"))), 1)
        self.assertEqual(self.ledger.verify(), 2)

    def test_invalid_transitions_do_not_mutate(self):
        for operation in (lambda: self.service.decide("D-test", "a"),
                          lambda: self.service.baseline("D-test", "outside"),
                          lambda: self.service.create(example())):
            with self.assertRaises(ValidationError):
                operation()
        self.assertEqual(self.ledger.verify(), 1)

    def test_irreversible_decision_requires_reason(self):
        self.service.create(example() | {"decision_id": "D-high", "reversible": False})
        self.service.baseline("D-high", "a")
        with self.assertRaises(ValidationError):
            self.service.decide("D-high", "a")
        for reason in (None, 123, []):
            with self.assertRaises(ValidationError):
                self.service.decide("D-high", "a", reason)
        self.service.decide("D-high", "a", "已核实约束")

    def test_finite_cost_schema_and_timezone_validation(self):
        invalids = [{"schema_version": True}, {"schema_version": 2}, {"deadline": "2030-01-01"},
                    {"options": [{"id": "a", "label": "x", "expected_cost_hours": float("inf")}, {"id": "b", "label": "y"}]}]
        for change in invalids:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                validate_decision(example() | change)
