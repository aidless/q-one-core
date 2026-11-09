"""Fail when version, CLI examples, and the honesty docs disagree.

Standard library only. `pyproject.toml` is the version source of truth.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COMMANDS = {
    "init",
    "create",
    "baseline",
    "recommend",
    "decide",
    "resolve",
    "verify",
    "report",
}
FAILURE_MODE_SNIPPETS = (
    "fork",
    "truncated",
    "rehashed",
    "Ledger.append",
    "DecisionService",
    "decided_by",
    "baseline",
    "fcntl",
)
# Split so this file does not itself contain the path needles it searches for.
PATH_NEEDLES = (
    "/ho" + "me/",
    "/Us" + "ers/",
    "/tm" + "p/",
    "liu" + "zewen",
    "C:\\Us" + "ers\\",
    "C:/Us" + "ers/",
)
SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
}
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".toml", ".txt", ".json"}


def marked(text: str, start: str, end: str) -> str | None:
    if start not in text or end not in text:
        return None
    return text.split(start, 1)[1].split(end, 1)[0]


def add_src_to_path() -> None:
    src = str(ROOT / "src")
    if src not in sys.path:
        sys.path.insert(0, src)


def _quoted(text: str, key: str) -> str | None:
    found = re.search(rf'(?m)^{key} = "([^"]+)"', text)
    return None if found is None else found.group(1)


def check_versions(errors: list[str]) -> tuple[str, str]:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    name = _quoted(pyproject, "name")
    version = _quoted(pyproject, "version")
    script = _quoted(pyproject, "qone")
    if not name or not version:
        errors.append("pyproject.toml is missing project name or version")
        return name or "", version or ""
    if script != "qone_core.cli:main":
        errors.append("pyproject console script qone must point at qone_core.cli:main")
    init_text = (ROOT / "src" / "qone_core" / "__init__.py").read_text(encoding="utf-8")
    found = re.search(r'^__version__\s*=\s*"([^"]+)"', init_text, re.MULTILINE)
    if found is None or found.group(1) != version:
        errors.append(f"qone_core.__version__ must equal pyproject version {version}")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    heading = re.search(r"^## (\d+\.\d+\.\d+)\b", changelog, re.MULTILINE)
    if heading is None or heading.group(1) != version:
        errors.append(f"first CHANGELOG version heading must be {version}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    identity = f"<!-- package-identity: {name} {version} -->"
    visible = f"Package `{name}` version `{version}`."
    if identity not in readme:
        errors.append(f"README is missing {identity}")
    if visible not in readme:
        errors.append(f"README is missing the visible package line for {name} {version}")
    if "python -m qone_core" not in readme and "python3 -m qone_core" not in readme:
        errors.append("README must show the python -m qone_core entry point")
    return name, version


def check_problem(readme: str, errors: list[str]) -> None:
    body = marked(readme, "<!-- problem:start -->", "<!-- problem:end -->")
    if body is None:
        errors.append("README is missing the problem markers")
        return
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not 2 <= len(lines) <= 3:
        errors.append(f"problem statement must be 2 or 3 lines, found {len(lines)}")
    joined = " ".join(lines).lower()
    for phrase in ("local", "life advice", "automate", "consequential", "does not"):
        if phrase not in joined:
            errors.append(f"problem statement is missing {phrase!r}")


def check_status(readme: str, errors: list[str]) -> None:
    if "## STATUS: WORK-IN-PROGRESS" not in readme:
        errors.append("README must keep ## STATUS: WORK-IN-PROGRESS")
        return
    section = readme.split("## STATUS: WORK-IN-PROGRESS", 1)[1].split("\n## ", 1)[0]
    for phrase in ("not grade A", "external validation", "PyPI", "star"):
        if phrase not in section:
            errors.append(f"STATUS section is missing {phrase!r}")
    if re.search(r"\b\d[\d,]*\s+stars\b", readme, re.IGNORECASE):
        errors.append("README states a star count")
    if re.search(r"\b\d[\d,]*\s+downloads\b", readme, re.IGNORECASE):
        errors.append("README states a download count")


def check_failure_modes(errors: list[str]) -> None:
    path = ROOT / "FAILURE_MODES.md"
    if not path.exists():
        errors.append("FAILURE_MODES.md is missing")
        return
    text = path.read_text(encoding="utf-8").casefold()
    for snippet in FAILURE_MODE_SNIPPETS:
        if snippet.casefold() not in text:
            errors.append(f"FAILURE_MODES.md is missing {snippet!r}")


def check_cli_demo(readme: str, errors: list[str]) -> None:
    body = marked(readme, "<!-- cli-demo:start -->", "<!-- cli-demo:end -->")
    if body is None:
        errors.append("README is missing the cli-demo markers")
        return
    add_src_to_path()
    from qone_core.cli import parser

    seen: set[str] = set()
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith(("```", "#", "export ")):
            continue
        try:
            tokens = split_command(line)
        except ValueError as exc:
            errors.append(f"could not parse CLI demo line: {line} ({exc})")
            continue
        if "-m" not in tokens:
            continue
        module_at = tokens.index("-m")
        if tokens[module_at + 1 : module_at + 2] != ["qone_core"]:
            errors.append(f"CLI demo must call -m qone_core: {line}")
            continue
        argv = tokens[module_at + 2 :]
        try:
            args = parser().parse_args(argv)
        except SystemExit:
            errors.append(f"CLI demo does not match the parser: {line}")
            continue
        seen.add(args.command)
    missing = REQUIRED_COMMANDS - seen
    if missing:
        errors.append(f"CLI demo is missing commands: {sorted(missing)}")
    example = json.loads((ROOT / "examples" / "decision.json").read_text(encoding="utf-8"))
    option_ids = {option["id"] for option in example["options"]}
    if "draft" not in option_ids:
        errors.append("examples/decision.json must include option id draft used by the CLI demo")


def split_command(line: str) -> list[str]:
    return shlex.split(line)


def check_absolute_paths(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS or part.endswith(".egg-info") for part in path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for needle in PATH_NEEDLES:
            if needle in text:
                relative = path.relative_to(ROOT)
                errors.append(f"{relative} contains a machine-local path marker")
                break


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Check version and honesty-doc drift").parse_args(argv)
    errors: list[str] = []
    check_versions(errors)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    check_problem(readme, errors)
    check_status(readme, errors)
    check_failure_modes(errors)
    check_cli_demo(readme, errors)
    if "DecisionService" not in readme or "Ledger.append" not in readme:
        errors.append("README must name both DecisionService and Ledger.append")
    check_absolute_paths(errors)
    if errors:
        for error in errors:
            print(f"drift: {error}", file=sys.stderr)
        return 1
    print("drift ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
