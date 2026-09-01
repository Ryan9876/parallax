from __future__ import annotations

from pathlib import Path
import sys

import pytest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import vercel_build


def test_service_preflight_uses_isolated_project_runtime(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    monkeypatch.setattr(vercel_build.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)

    def fake_run(args, **kwargs):
        calls.append((list(args), dict(kwargs)))

    monkeypatch.setattr(vercel_build.subprocess, "run", fake_run)

    vercel_build._run_service_preflight("scripts/production_agentic_runtime_preflight.py")

    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[:2] == ["/usr/bin/uv", "run"]
    assert "--isolated" in command
    assert "--no-python-downloads" in command
    assert "--no-dev" in command
    assert "--project" in command
    project_index = command.index("--project")
    assert command[project_index + 1] == str(vercel_build._API_ROOT)
    assert "--no-project" not in command
    assert "--with" not in command
    assert command[-2] == "python"
    assert command[-1] == str(
        (vercel_build._API_ROOT / "scripts/production_agentic_runtime_preflight.py").resolve()
    )
    assert kwargs == {"check": True, "cwd": vercel_build._API_ROOT}


def test_service_preflight_rejects_script_outside_trusted_root(monkeypatch) -> None:
    monkeypatch.setattr(vercel_build.shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)

    with pytest.raises(RuntimeError, match="outside the trusted scripts root"):
        vercel_build._run_service_preflight("parallax_api/main.py")


def test_service_preflight_fails_closed_without_uv(monkeypatch) -> None:
    monkeypatch.setattr(vercel_build.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="requires uv"):
        vercel_build._run_service_preflight("scripts/production_agentic_runtime_preflight.py")


def test_production_build_uses_project_runtime_for_service_canaries(monkeypatch, tmp_path: Path) -> None:
    events: list[tuple[str, tuple[str, ...]]] = []
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(vercel_build, "_run", lambda *args: events.append(("plain", tuple(args))))
    monkeypatch.setattr(
        vercel_build,
        "_run_isolated_preflight",
        lambda script: events.append(("isolated", (script,))),
    )
    monkeypatch.setattr(
        vercel_build,
        "_run_service_preflight",
        lambda script: events.append(("service", (script,))),
    )

    vercel_build.main()

    assert events == [
        ("plain", ("scripts/production_provider_preflight.py",)),
        ("plain", ("scripts/production_delivery_permission_preflight.py",)),
        ("plain", ("scripts/production_projected_source_preflight.py",)),
        ("isolated", ("scripts/production_lineage_composition_preflight.py",)),
        ("service", ("scripts/production_agentic_runtime_preflight.py",)),
        ("isolated", ("scripts/production_projected_bootstrap_preflight.py",)),
        ("isolated", ("scripts/production_execution_snapshot_preflight.py",)),
        ("service", ("scripts/production_candidate_validation_canary.py",)),
        ("isolated", ("scripts/production_run_event_schema_guard.py",)),
    ]
