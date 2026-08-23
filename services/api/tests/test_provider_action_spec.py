from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "specs" / "P2-V0.15.4.md"
VALIDATOR = ROOT / "scripts" / "validate_spec.py"


def _validate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args, str(SPEC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_provider_action_spec_passes_protected_spec_contract() -> None:
    result = _validate("--spec-only")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "satisfies the Parallax spec contract gate" in result.stdout


def test_provider_action_compiled_plan_has_protected_dspy_evidence() -> None:
    result = _validate("--require-dspy")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DSPy evidence" in result.stdout
