"""Command-line interface for the Q-One Core protocol."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .gate import check_recommendation
from .ledger import Ledger, LedgerError
from .models import (
    ValidationError,
    validate_decision,
    validate_outcome,
    validate_recommendation,
)
from .report import build_report, format_report


def _ledger(args: argparse.Namespace) -> Ledger:
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return Ledger(data_dir / "ledger.jsonl")


def _load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _option_ids(state: dict[str, Any]) -> set[str]:
    return {option["id"] for option in state.get("options", [])}


def _require_state(ledger: Ledger, decision_id: str) -> dict[str, Any]:
    try:
        return ledger.get(decision_id)
    except KeyError as exc:
        raise ValidationError(str(exc)) from exc


def _require_option(state: dict[str, Any], option_id: str) -> None:
    if option_id not in _option_ids(state):
        raise ValidationError(f"unknown option for decision: {option_id}")


def cmd_init(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    count = ledger.verify()
    print(f"initialized {ledger.path} ({count} events)")
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    decision = validate_decision(_load_json(args.file))
    if decision["decision_id"] in ledger.project_all():
        raise ValidationError(f"decision already exists: {decision['decision_id']}")
    ledger.append("decision_created", decision)
    print(decision["decision_id"])
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    state = _require_state(ledger, args.decision)
    if state.get("status") in {"resolved", "abandoned"}:
        raise ValidationError("cannot record a baseline for a terminal decision")
    if state.get("baseline"):
        raise ValidationError("baseline already recorded")
    _require_option(state, args.option)
    ledger.append(
        "baseline_recorded",
        {"decision_id": args.decision, "option_id": args.option, "note": args.note},
    )
    print(f"baseline recorded for {args.decision}")
    return 0


def cmd_recommend(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    state = _require_state(ledger, args.decision)
    if state.get("status") in {"decided", "resolved", "abandoned"}:
        raise ValidationError("cannot recommend after a human decision")
    if state.get("recommendation"):
        raise ValidationError("recommendation already recorded")
    gate = check_recommendation(state, args.confidence, args.personal_calibration_n)
    if not gate.allowed:
        raise ValidationError("recommendation blocked: " + ", ".join(gate.reasons))
    recommendation = validate_recommendation(
        {
            "option_id": args.option,
            "confidence": args.confidence,
            "success_probability": args.success_probability,
            "rationale": args.rationale,
            "source": args.source,
            "gate_reasons": list(gate.reasons),
        },
        _option_ids(state),
    )
    recommendation["decision_id"] = args.decision
    recommendation["personal_calibration_n"] = args.personal_calibration_n
    ledger.append("recommendation_made", recommendation)
    print(f"recommendation recorded for {args.decision}")
    return 0


def cmd_decide(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    state = _require_state(ledger, args.decision)
    if state.get("status") in {"resolved", "abandoned"}:
        raise ValidationError("cannot decide a terminal decision")
    if not state.get("baseline"):
        raise ValidationError("record a baseline before the human decision")
    _require_option(state, args.option)
    if (state.get("risk") == "high" or state.get("reversible") is False) and not args.reason:
        raise ValidationError("a reason is required for high-risk or irreversible decisions")
    ledger.append(
        "human_decision",
        {
            "decision_id": args.decision,
            "option_id": args.option,
            "decided_by": args.by,
            "reason": args.reason or "",
            "recommendation_overridden": bool(
                state.get("recommendation")
                and state["recommendation"].get("option_id") != args.option
            ),
        },
    )
    print(f"human decision recorded for {args.decision}")
    return 0


def cmd_resolve(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    state = _require_state(ledger, args.decision)
    if state.get("status") != "decided":
        raise ValidationError("only a decided decision can be resolved")
    outcome = validate_outcome(
        {"decision_id": args.decision, "success": args.success, "notes": args.notes}
    )
    ledger.append("outcome_recorded", outcome)
    print(f"outcome recorded for {args.decision}")
    return 0


def cmd_abandon(args: argparse.Namespace) -> int:
    ledger = _ledger(args)
    state = _require_state(ledger, args.decision)
    if state.get("status") in {"resolved", "abandoned"}:
        raise ValidationError("decision is already terminal")
    ledger.append(
        "decision_abandoned", {"decision_id": args.decision, "reason": args.reason}
    )
    print(f"decision abandoned: {args.decision}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state = _require_state(_ledger(args), args.decision)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    count = _ledger(args).verify()
    print(f"verified {count} events")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    report = build_report(_ledger(args))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_report(report))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="qone", description="Q-One Core decision ledger")
    root.add_argument(
        "--data-dir",
        default=os.environ.get("QONE_DATA_DIR", ".qone-data"),
        help="directory containing ledger.jsonl (default: .qone-data)",
    )
    commands = root.add_subparsers(dest="command", required=True)

    command = commands.add_parser("init", help="create or verify a local ledger")
    command.set_defaults(handler=cmd_init)

    command = commands.add_parser("create", help="append a decision from a JSON file")
    command.add_argument("--file", required=True)
    command.set_defaults(handler=cmd_create)

    command = commands.add_parser("baseline", help="record the pre-agent baseline")
    command.add_argument("--decision", required=True)
    command.add_argument("--option", required=True)
    command.add_argument("--note", default="")
    command.set_defaults(handler=cmd_baseline)

    command = commands.add_parser("recommend", help="append an agent recommendation")
    command.add_argument("--decision", required=True)
    command.add_argument("--option", required=True)
    command.add_argument("--confidence", type=float, required=True)
    command.add_argument("--success-probability", type=float)
    command.add_argument("--rationale", required=True)
    command.add_argument("--source", required=True)
    command.add_argument("--personal-calibration-n", type=int, default=0)
    command.set_defaults(handler=cmd_recommend)

    command = commands.add_parser("decide", help="record the human decision")
    command.add_argument("--decision", required=True)
    command.add_argument("--option", required=True)
    command.add_argument("--by", default="human")
    command.add_argument("--reason", default="")
    command.set_defaults(handler=cmd_decide)

    command = commands.add_parser("resolve", help="record an observed outcome")
    command.add_argument("--decision", required=True)
    command.add_argument("--success", choices=["yes", "no", "partial", "unknown"], required=True)
    command.add_argument("--notes", default="")
    command.set_defaults(handler=cmd_resolve)

    command = commands.add_parser("abandon", help="close a decision without an outcome")
    command.add_argument("--decision", required=True)
    command.add_argument("--reason", required=True)
    command.set_defaults(handler=cmd_abandon)

    command = commands.add_parser("show", help="show the projected state of a decision")
    command.add_argument("--decision", required=True)
    command.set_defaults(handler=cmd_show)

    command = commands.add_parser("verify", help="verify the ledger hash chain")
    command.set_defaults(handler=cmd_verify)

    command = commands.add_parser("report", help="print evidence-aware aggregate metrics")
    command.add_argument("--json", action="store_true")
    command.set_defaults(handler=cmd_report)
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ValidationError, LedgerError, KeyError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
