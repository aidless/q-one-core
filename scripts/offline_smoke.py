"""Offline CLI smoke for the core ledger.

Uses the Python standard library only. It does not install the package and
does not read or write a network. The ledger lives in a temporary directory.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], data_dir: Path) -> str:
    env = os.environ.copy()
    src = str(ROOT / "src")
    previous = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not previous else src + os.pathsep + previous
    completed = subprocess.run(
        [sys.executable, "-m", "qone_core", "--data-dir", str(data_dir), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(
            f"command failed ({completed.returncode}): {args}\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    return completed.stdout.strip()


def main() -> int:
    example = ROOT / "examples" / "decision.json"
    with tempfile.TemporaryDirectory(prefix="qone-smoke-") as temporary:
        data_dir = Path(temporary)
        init_out = run(["init"], data_dir)
        if "initialized" not in init_out:
            raise SystemExit(f"unexpected init output: {init_out}")
        decision_id = run(["create", "--file", str(example)], data_dir)
        if not decision_id.startswith("D-"):
            raise SystemExit(f"unexpected decision id: {decision_id}")
        run(
            [
                "baseline",
                "--decision",
                decision_id,
                "--option",
                "draft",
                "--note",
                "human baseline",
            ],
            data_dir,
        )
        run(
            [
                "recommend",
                "--decision",
                decision_id,
                "--option",
                "draft",
                "--confidence",
                "0.82",
                "--success-probability",
                "0.70",
                "--rationale",
                "The criterion rewards an early reviewable artifact.",
                "--source",
                "local-rule-v0.1",
            ],
            data_dir,
        )
        run(
            ["decide", "--decision", decision_id, "--option", "draft", "--by", "human"],
            data_dir,
        )
        run(
            [
                "resolve",
                "--decision",
                decision_id,
                "--success",
                "yes",
                "--notes",
                "A reviewable draft was ready.",
            ],
            data_dir,
        )
        verified = run(["verify"], data_dir)
        if verified != "verified 5 events":
            raise SystemExit(f"unexpected verify output: {verified}")
        report = run(["report"], data_dir)
        if "evidence status: descriptive_with_outcomes" not in report:
            raise SystemExit(f"unexpected report:\n{report}")
        print(verified)
        print("offline smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
