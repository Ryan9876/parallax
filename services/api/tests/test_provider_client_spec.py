from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[3]
SPEC = ROOT / "specs" / "P2-V0.15.7.md"
VALIDATOR = ROOT / "scripts" / "validate_spec.py"


def test_provider_clients_workstream_spec_passes_protected_spec_only_gate() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--spec-only", str(SPEC)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "satisfies the Parallax spec contract gate" in result.stdout
