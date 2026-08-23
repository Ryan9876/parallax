from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "specs" / "P2-V0.15.3.md"
VALIDATOR = ROOT / "scripts" / "validate_spec.py"


def test_implementation_runtime_spec_and_committed_dspy_plan_pass_protected_gate():
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--require-dspy", str(SPEC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "satisfies the Parallax spec + compiled plan + DSPy evidence gate" in result.stdout
