"""Evidence-aware summary reports for a decision ledger."""

from __future__ import annotations

import json
import math
from typing import Any

from .ledger import Ledger


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
    return max(0.0, centre - spread), min(1.0, centre + spread)


def build_report(ledger: Ledger) -> dict[str, Any]:
    states = list(ledger.project_all().values())
    resolved = [state for state in states if state.get("status") == "resolved"]
    candidates = [state for state in states if state.get("recommendation")]
    calibration_rows = []
    excluded_rows = []
    exclusion_counts: dict[str, int] = {}
    for state in candidates:
        recommendation = state["recommendation"]
        probability = recommendation.get("success_probability")
        choice = state.get("human_decision", {}).get("option_id")
        success = state.get("outcome", {}).get("success")
        reason = None
        if probability is None:
            reason = "missing_probability"
        elif state.get("status") != "resolved":
            reason = "unresolved"
        elif not choice:
            reason = "missing_human_decision"
        elif choice != recommendation.get("option_id"):
            # The outcome of another action cannot label this recommendation's forecast.
            reason = "recommended_option_not_selected"
        elif success not in {"yes", "no"}:
            reason = "non_binary_outcome"
        elif (
            isinstance(probability, bool)
            or not isinstance(probability, (int, float))
            or not math.isfinite(probability)
            or not 0 <= probability <= 1
        ):
            reason = "invalid_probability"
        if reason:
            excluded_rows.append({"decision_id": state["decision_id"], "reason": reason})
            exclusion_counts[reason] = exclusion_counts.get(reason, 0) + 1
            continue
        calibration_rows.append(
            {
                "decision_id": state["decision_id"],
                "option_id": choice,
                "predicted": float(probability),
                "observed": 1 if success == "yes" else 0,
            }
        )
    brier = None
    if calibration_rows:
        brier = sum((row["predicted"] - row["observed"]) ** 2 for row in calibration_rows)
        brier /= len(calibration_rows)
    yes_count = sum(row["observed"] for row in calibration_rows)
    interval = wilson_interval(yes_count, len(calibration_rows))

    recommendations = [state for state in states if state.get("recommendation")]
    decisions = [state for state in states if state.get("human_decision")]
    recommendation_decisions = [state for state in decisions if state.get("recommendation")]
    adopted = sum(
        state["recommendation"]["option_id"] == state["human_decision"]["option_id"]
        for state in recommendation_decisions
    )
    return {
        "ledger_events": ledger.verify(),
        "decisions": len(states),
        "resolved_decisions": len(resolved),
        "baseline_recorded": sum(bool(state.get("baseline")) for state in states),
        "recommendations": len(recommendations),
        "human_decisions": len(decisions),
        "recommendation_adoption_n": len(recommendation_decisions),
        "recommendation_adopted": adopted,
        "recommendation_adoption": adopted / len(recommendation_decisions)
        if recommendation_decisions
        else None,
        "calibration": {
            "candidate_decisions": len(candidates),
            "n": len(calibration_rows),
            "excluded": len(excluded_rows),
            "exclusion_counts": exclusion_counts,
            "excluded_rows": excluded_rows,
            "selection_note": (
                "Only resolved binary outcomes for the selected recommended option are scored. "
                "This selected subset does not measure unchosen options or causal improvement."
            ),
            "brier_score": brier,
            "observed_success_rate": yes_count / len(calibration_rows)
            if calibration_rows
            else None,
            "wilson_95": interval,
            "rows": calibration_rows,
        },
        "evidence_status": "descriptive_only" if not calibration_rows else "descriptive_with_outcomes",
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        f"ledger events: {report['ledger_events']}",
        f"decisions: {report['decisions']} ({report['resolved_decisions']} resolved)",
        f"baselines: {report['baseline_recorded']}",
        f"recommendations: {report['recommendations']}",
        f"human decisions: {report['human_decisions']}",
        f"recommendation adoption: {report['recommendation_adoption']}",
        f"evidence status: {report['evidence_status']}",
    ]
    calibration = report["calibration"]
    lines.append(f"calibration n: {calibration['n']}")
    lines.append(f"calibration excluded: {calibration['excluded']}")
    if calibration["exclusion_counts"]:
        lines.append(f"calibration exclusion reasons: {calibration['exclusion_counts']}")
    lines.append(f"calibration scope: {calibration['selection_note']}")
    lines.append(f"brier score: {calibration['brier_score']}")
    lines.append(f"observed success rate: {calibration['observed_success_rate']}")
    return "\n".join(lines)


def report_json(ledger: Ledger) -> str:
    return json.dumps(build_report(ledger), ensure_ascii=False, indent=2)
