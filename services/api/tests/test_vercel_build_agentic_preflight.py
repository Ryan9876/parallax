from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "vercel_build.py"
SPEC = importlib.util.spec_from_file_location("parallax_vercel_build", BUILD_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
vercel_build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vercel_build)


def test_agentic_preflight_runner_uses_uv_project_environment(monkeypatch) -> None:
    calls: list[tuple[list[str], bool]] = []
    monkeypatch.setattr(vercel_build.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    monkeypatch.setattr(
        vercel_build.subprocess,
        "run",
        lambda args, check: calls.append((list(args), check)),
    )

    vercel_build._run_project_preflight("scripts/production_agentic_runtime_preflight.py")

    assert calls == [
        (
            [
                "/usr/bin/uv",
                "run",
                "--no-progress",
                "--no-python-downloads",
                "python",
                "scripts/production_agentic_runtime_preflight.py",
            ],
            True,
        )
    ]
    command = calls[0][0]
    # The Wave 6 canary imports the ordinary API runtime graph and therefore must
    # inherit the current API project dependencies. `--no-project` or an isolated
    # tool environment would recreate the production failure this guard prevents.
    assert "--no-project" not in command
    assert "--isolated" not in command


def test_project_preflight_fails_closed_without_uv(monkeypatch) -> None:
    monkeypatch.setattr(vercel_build.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="requires uv"):
        vercel_build._run_project_preflight("scripts/production_agentic_runtime_preflight.py")
