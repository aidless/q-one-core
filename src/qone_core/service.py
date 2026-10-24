"""Transactional product API over the backwards-compatible event ledger."""

from __future__ import annotations

from typing import Any

from .gate import check_recommendation
from .ledger import Ledger
from .models import ValidationError, validate_decision, validate_outcome, validate_recommendation


class DecisionService:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger

    @staticmethod
    def _state(states, decision_id, allowed):
        if decision_id not in states:
            raise ValidationError("decision not found")
        state = states[decision_id]
        if state["status"] not in allowed:
            raise ValidationError(f"transition not allowed from {state['status']}")
        return state

    @staticmethod
    def _option(state, option_id):
        if option_id not in {option["id"] for option in state["options"]}:
            raise ValidationError("option is not part of this decision")

    def create(self, raw: dict[str, Any]):
        decision = validate_decision(raw)
        def prepare(states):
            if decision["decision_id"] in states:
                raise ValidationError("decision ID already exists")
            return decision
        self.ledger.transact("decision_created", prepare)
        return self.ledger.get(decision["decision_id"])

    def baseline(self, decision_id, option_id, note=""):
        def prepare(states):
            state = self._state(states, decision_id, {"created"})
            self._option(state, option_id)
            return {"decision_id": decision_id, "option_id": option_id, "note": str(note)}
        return self.ledger.transact("baseline_recorded", prepare)

    def recommend(self, decision_id, raw, run_id=None, evidence_ids=None):
        def prepare(states):
            state = self._state(states, decision_id, {"baseline_recorded"})
            result = validate_recommendation(raw, {o["id"] for o in state["options"]})
            gate = check_recommendation(state, result["confidence"], 0)
            if not gate.allowed:
                raise ValidationError(", ".join(gate.reasons))
            result.update(decision_id=decision_id, gate_reasons=list(gate.reasons),
                          run_id=run_id, evidence_ids=list(evidence_ids or []))
            return result
        return self.ledger.transact("recommendation_made", prepare)

    def decide(self, decision_id, option_id, reason=""):
        if not isinstance(reason, str):
            raise ValidationError("reason must be text")
        def prepare(states):
            state = self._state(states, decision_id, {"baseline_recorded", "recommended"})
            self._option(state, option_id)
            if (state["risk"] == "high" or not state["reversible"]) and not str(reason).strip():
                raise ValidationError("a reason is required for this decision")
            return {"decision_id": decision_id, "option_id": option_id,
                    "reason": str(reason), "decided_by": "human",
                    "recommendation_overridden": bool(state.get("recommendation")
                        and state["recommendation"]["option_id"] != option_id)}
        return self.ledger.transact("human_decision", prepare)

    def resolve(self, decision_id, success, notes=""):
        def prepare(states):
            self._state(states, decision_id, {"decided"})
            return validate_outcome({"decision_id": decision_id, "success": success, "notes": notes})
        return self.ledger.transact("outcome_recorded", prepare)

    def abandon(self, decision_id, reason):
        def prepare(states):
            self._state(states, decision_id, {"created", "baseline_recorded", "recommended", "decided"})
            if not isinstance(reason, str) or not reason.strip():
                raise ValidationError("abandonment reason is required")
            return {"decision_id": decision_id, "reason": reason.strip()}
        return self.ledger.transact("decision_abandoned", prepare)
