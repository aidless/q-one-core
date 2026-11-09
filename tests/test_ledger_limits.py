"""Hash-chain limits that verify() does not catch.

A matching prev_hash/hash chain is necessary for verify() to pass. It is not
an external commitment. These tests fix the limits documented in FAILURE_MODES.md.
"""

import json
import tempfile
import unittest
from pathlib import Path

from qone_core.ledger import GENESIS, Ledger, LedgerError, event_hash


class LedgerLimitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "ledger.jsonl"
        self.ledger = Ledger(self.path)
        self.ledger.append("decision_created", {"decision_id": "D-a"})
        self.ledger.append("baseline_recorded", {"decision_id": "D-a", "option_id": "x"})
        self.ledger.append("human_decision", {"decision_id": "D-a", "option_id": "x"})

    def _events(self):
        return [json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines()]

    def _write(self, events):
        text = "".join(
            json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
            for event in events
        )
        self.path.write_text(text, encoding="utf-8")

    def test_byte_edit_without_rehash_fails_verify(self):
        raw = self.path.read_text(encoding="utf-8")
        self.path.write_text(raw.replace("D-a", "D-b", 1), encoding="utf-8")
        with self.assertRaises(LedgerError):
            self.ledger.verify()

    def test_rehashed_suffix_still_verifies(self):
        events = self._events()
        events[0]["payload"]["decision_id"] = "D-rewritten"
        events[0]["hash"] = event_hash(events[0])
        events[1]["prev_hash"] = events[0]["hash"]
        events[1]["payload"]["decision_id"] = "D-rewritten"
        events[1]["hash"] = event_hash(events[1])
        events[2]["prev_hash"] = events[1]["hash"]
        events[2]["payload"]["decision_id"] = "D-rewritten"
        events[2]["hash"] = event_hash(events[2])
        self._write(events)
        self.assertEqual(self.ledger.verify(), 3)
        self.assertEqual(self.ledger.get("D-rewritten")["status"], "decided")

    def test_truncated_prefix_still_verifies(self):
        lines = self.path.read_text(encoding="utf-8").splitlines()
        self.path.write_text(lines[0] + "\n", encoding="utf-8")
        self.assertEqual(self.ledger.verify(), 1)
        self.assertEqual(self.ledger.get("D-a")["status"], "created")

    def test_two_forks_each_verify(self):
        prefix = self.path.read_text(encoding="utf-8").splitlines()[0] + "\n"
        left = self.temp.name + "/left.jsonl"
        right = self.temp.name + "/right.jsonl"
        Path(left).write_text(prefix, encoding="utf-8")
        Path(right).write_text(prefix, encoding="utf-8")
        Ledger(left).append("baseline_recorded", {"decision_id": "D-a", "option_id": "left"})
        Ledger(right).append("baseline_recorded", {"decision_id": "D-a", "option_id": "right"})
        self.assertEqual(Ledger(left).verify(), 2)
        self.assertEqual(Ledger(right).verify(), 2)
        self.assertNotEqual(Ledger(left).events()[-1]["hash"], Ledger(right).events()[-1]["hash"])
        self.assertEqual(Ledger(left).events()[0]["prev_hash"], GENESIS)
