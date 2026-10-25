"""Append-only JSONL ledger with a tamper-evident hash chain."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


GENESIS = "0" * 64
EVENT_TYPES = {
    "decision_created",
    "baseline_recorded",
    "recommendation_made",
    "human_decision",
    "outcome_recorded",
    "decision_abandoned",
}


class LedgerError(RuntimeError):
    """Raised when a ledger cannot be read or fails integrity validation."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def event_hash(event: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in event.items() if key != "hash"}
    return hashlib.sha256(canonical_json(unsigned).encode("utf-8")).hexdigest()


class Ledger:
    """A local JSONL ledger. Each write is serialized and fsynced."""

    def __init__(self, path: str | os.PathLike[str]):
        self.path = Path(path)
        self.lock_path = self.path.with_name(f"{self.path.name}.lock")

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    raise LedgerError(f"blank line at ledger line {line_number}")
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LedgerError(f"invalid JSON at ledger line {line_number}") from exc
                if not isinstance(event, dict):
                    raise LedgerError(f"ledger line {line_number} is not an object")
                events.append(event)
        return events

    @staticmethod
    def _verify_events(events: list[dict[str, Any]]) -> None:
        previous = GENESIS
        for expected_seq, event in enumerate(events, start=1):
            if event.get("seq") != expected_seq:
                raise LedgerError(f"sequence mismatch at event {expected_seq}")
            if event.get("type") not in EVENT_TYPES:
                raise LedgerError(f"unknown event type at event {expected_seq}")
            if event.get("prev_hash") != previous:
                raise LedgerError(f"previous hash mismatch at event {expected_seq}")
            if event.get("hash") != event_hash(event):
                raise LedgerError(f"event hash mismatch at event {expected_seq}")
            previous = event["hash"]

    def verify(self) -> int:
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            return len(events)

    def _append_unlocked(self, events, event_type, payload):
        event = {
            "seq": len(events) + 1,
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "type": event_type,
            "payload": payload,
            "prev_hash": events[-1]["hash"] if events else GENESIS,
        }
        event["hash"] = event_hash(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(event) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return event

    def transact(self, event_type: str, prepare: Callable) -> dict[str, Any]:
        """Validate and append one transition while holding the same writer lock."""
        if event_type not in EVENT_TYPES:
            raise LedgerError(f"unknown event type: {event_type}")
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            payload = prepare(self.project_events(events))
            if not isinstance(payload, dict):
                raise LedgerError("event payload must be an object")
            return self._append_unlocked(events, event_type, payload)

    def append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Low-level append for trusted imports; product callers use DecisionService."""
        return self.transact(event_type, lambda states: payload)

    def events(self) -> list[dict[str, Any]]:
        with self._lock():
            events = self._read_unlocked()
            self._verify_events(events)
            return events

    def project_all(self) -> dict[str, dict[str, Any]]:
        return self.project_events(self.events())

    @staticmethod
    def project_events(events) -> dict[str, dict[str, Any]]:
        states: dict[str, dict[str, Any]] = {}
        for event in events:
            payload = event["payload"]
            decision_id = payload.get("decision_id")
            if not isinstance(decision_id, str):
                continue
            state = states.setdefault(
                decision_id,
                {
                    "decision_id": decision_id,
                    "status": "unknown",
                    "events": [],
                },
            )
            state["events"].append(event)
            event_type = event["type"]
            if event_type == "decision_created":
                state.update(payload)
                state["status"] = "created"
            elif event_type == "baseline_recorded":
                state["baseline"] = payload
                state["status"] = "baseline_recorded"
            elif event_type == "recommendation_made":
                state["recommendation"] = payload
                state["status"] = "recommended"
            elif event_type == "human_decision":
                state["human_decision"] = payload
                state["status"] = "decided"
            elif event_type == "outcome_recorded":
                state["outcome"] = payload
                state["status"] = "resolved"
            elif event_type == "decision_abandoned":
                state["abandonment"] = payload
                state["status"] = "abandoned"
        return states

    def get(self, decision_id: str) -> dict[str, Any]:
        try:
            return self.project_all()[decision_id]
        except KeyError as exc:
            raise KeyError(f"unknown decision: {decision_id}") from exc
