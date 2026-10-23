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
    predictions = [
        state
        for state in resolved
        if state.get("recommendation", {}).get("success_probability") is not None
        and state.get("outcome", {}).get("success") in {"yes", "no"}
    ]
    calibration_rows = []
    for state in predictions:
        probability = float(state["recommendation"]["success_probability"])
        observed = 1 if state["outcome"]["success"] == "yes" else 0
        calibration_rows.append({"predicted": probability, "observed": observed})
    brier = None
    if calibration_rows:
        brier = sum((row["predicted"] - row["observed"]) ** 2 for row in calibration_rows)
        brier /= len(calibration_rows)
    yes_count = sum(row["observed"] for row in calibration_rows)
    interval = wilson_interval(yes_count, len(calibration_rows))

    recommendations = [state for state in states if state.get("recommendation")]
    decisions = [state for state in states if state.get("human_decision")]
    adopted = sum(
        state.get("recommendation", {}).get("option_id")
        == state.get("human_decision", {}).get("option_id")
        for state in decisions
    )
    return {
        "ledger_events": ledger.verify(),
        "decisions": len(states),
        "resolved_decisions": len(resolved),
        "baseline_recorded": sum(bool(state.get("baseline")) for state in states),
        "recommendations": len(recommendations),
        "human_decisions": len(decisions),
        "recommendation_adoption": adopted / len(decisions) if decisions else None,
        "calibration": {
            "n": len(calibration_rows),
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
    lines.append(f"brier score: {calibration['brier_score']}")
    lines.append(f"observed success rate: {calibration['observed_success_rate']}")
    return "\n".join(lines)


def report_json(ledger: Ledger) -> str:
    return json.dumps(build_report(ledger), ensure_ascii=False, indent=2)
