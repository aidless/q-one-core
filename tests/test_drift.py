"""The honesty checks must pass on a fresh tree, with no network and no pytest plugins."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DriftTests(unittest.TestCase):
    def test_version_and_docs_drift_check_passes(self):
        script = ROOT / "scripts" / "check_drift.py"
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("drift ok", completed.stdout)

    def test_offline_cli_smoke_verifies_without_install(self):
        script = ROOT / "scripts" / "offline_smoke.py"
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            completed.returncode,
            0,
            completed.stdout + completed.stderr,
        )
        self.assertIn("verified 5 events", completed.stdout)
        self.assertIn("offline smoke ok", completed.stdout)
