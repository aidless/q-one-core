"""Human-safety gates for recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    requires_human: bool
    reasons: tuple[str, ...]


def check_recommendation(
    state: dict[str, Any],
    confidence: float,
    personal_calibration_n: int = 0,
) -> GateResult:
    """Return a transparent gate decision; this function never authorizes an action."""
    reasons: list[str] = []
    if not state.get("baseline"):
        return GateResult(False, True, ("missing_baseline",))
    if confidence < 0.70:
        reasons.append("low_confidence")
    if state.get("risk") == "high":
        reasons.append("high_risk")
    if state.get("reversible") is False:
        reasons.append("irreversible")
    if personal_calibration_n < 20:
        reasons.append("insufficient_personal_calibration")
    return GateResult(True, True, tuple(reasons))
