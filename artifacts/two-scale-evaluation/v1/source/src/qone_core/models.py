"""Input validation and stable data shapes for Q-One Core."""

from __future__ import annotations

from datetime import datetime, timezone
from secrets import token_hex
from math import isfinite
from typing import Any


class ValidationError(ValueError):
    """Raised when a decision or event payload violates the protocol."""


RISK_LEVELS = {"low", "medium", "high"}
OUTCOMES = {"yes", "no", "partial", "unknown"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_decision_id() -> str:
    return f"D-{datetime.now(timezone.utc):%Y%m%d}-{token_hex(3)}"


def _text(value: Any, field: str, *, required: bool = True) -> str | None:
    if not required and (value is None or (isinstance(value, str) and not value.strip())):
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field} must be a non-empty string")
    return value.strip()


def _probability(value: Any, field: str, *, required: bool = True) -> float | None:
    if value is None and not required:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be a number between 0 and 1")
    result = float(value)
    if not 0 <= result <= 1:
        raise ValidationError(f"{field} must be a number between 0 and 1")
    return result


def validate_option(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValidationError("each option must be an object")
    option_id = _text(raw.get("id"), "option.id")
    label = _text(raw.get("label"), "option.label")
    expected_cost = raw.get("expected_cost_hours", 0)
    if isinstance(expected_cost, bool) or not isinstance(expected_cost, (int, float)):
        raise ValidationError("option.expected_cost_hours must be a non-negative number")
    if not isfinite(float(expected_cost)) or expected_cost < 0:
        raise ValidationError("option.expected_cost_hours must be a non-negative number")
    notes = _text(raw.get("notes"), "option.notes", required=False)
    return {
        "id": option_id,
        "label": label,
        "expected_cost_hours": float(expected_cost),
        "notes": notes or "",
    }


def validate_decision(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValidationError("decision must be an object")
    options = raw.get("options")
    if not isinstance(options, list) or not 2 <= len(options) <= 8:
        raise ValidationError("decision.options must contain between 2 and 8 options")
    normalized_options = [validate_option(option) for option in options]
    ids = [option["id"] for option in normalized_options]
    if len(set(ids)) != len(ids):
        raise ValidationError("decision option ids must be unique")

    version = raw.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise ValidationError("unsupported decision schema version")
    deadline = _text(raw.get("deadline"), "deadline")
    try:
        parsed = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
    except ValueError as exc:
        raise ValidationError("deadline must be an ISO timestamp with timezone") from exc
    risk = raw.get("risk", "medium")
    if not isinstance(risk, str) or risk not in RISK_LEVELS:
        raise ValidationError(f"decision.risk must be one of {sorted(RISK_LEVELS)}")
    reversible = raw.get("reversible")
    if not isinstance(reversible, bool):
        raise ValidationError("decision.reversible must be a boolean")

    return {
        "schema_version": version,
        "decision_id": _text(raw.get("decision_id"), "decision_id", required=False)
        or new_decision_id(),
        "question": _text(raw.get("question"), "question"),
        "domain": _text(raw.get("domain"), "domain"),
        "success_criterion": _text(raw.get("success_criterion"), "success_criterion"),
        "deadline": deadline,
        "reversible": reversible,
        "risk": risk,
        "options": normalized_options,
        "context": _text(raw.get("context"), "context", required=False) or "",
    }


def validate_recommendation(raw: Any, option_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValidationError("recommendation must be an object")
    option_id = _text(raw.get("option_id"), "recommendation.option_id")
    if option_id not in option_ids:
        raise ValidationError("recommendation.option_id is not a decision option")
    confidence = _probability(raw.get("confidence"), "recommendation.confidence")
    success_probability = _probability(
        raw.get("success_probability"),
        "recommendation.success_probability",
        required=False,
    )
    return {
        "option_id": option_id,
        "confidence": confidence,
        "success_probability": success_probability,
        "rationale": _text(raw.get("rationale"), "recommendation.rationale"),
        "source": _text(raw.get("source"), "recommendation.source"),
        "gate_reasons": list(raw.get("gate_reasons", [])),
        "requires_human": True,
        "auto_eligible": False,
    }


def validate_outcome(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValidationError("outcome must be an object")
    success = raw.get("success")
    if not isinstance(success, str) or success not in OUTCOMES:
        raise ValidationError(f"outcome.success must be one of {sorted(OUTCOMES)}")
    return {
        "decision_id": _text(raw.get("decision_id"), "outcome.decision_id"),
        "success": success,
        "notes": _text(raw.get("notes"), "outcome.notes", required=False) or "",
    }
