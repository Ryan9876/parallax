from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def _uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("production durable bootstrap preflight requires uv")
    return uv


def _run_isolated_preflight(script: str) -> None:
    subprocess.run(
        [
            _uv(),
            "run",
            "--isolated",
            "--no-project",
            "--no-progress",
            "--no-python-downloads",
            "--with",
            "vercel>=0.9,<0.10",
            "--with",
            "sqlalchemy>=2.0.50,<3",
            "--with",
            "psycopg[binary]>=3.2,<4",
            "python",
            script,
        ],
        check=True,
    )


def _run_project_preflight(script: str) -> None:
    """Run a repository-owned preflight with the API project's full runtime deps."""

    subprocess.run(
        [
            _uv(),
            "run",
            "--no-progress",
            "--no-python-downloads",
            "python",
            script,
        ],
        check=True,
    )


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_delivery_permission_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        # Production publication remains fail-closed on every runtime substrate
        # required for durable source bootstrap and exact-lineage execution.
        _run_isolated_preflight("scripts/production_lineage_composition_preflight.py")
        # W6 selected-candidate replay imports the ordinary API runtime graph. Run
        # it in the API project environment so the canary proves the deployed
        # dependency set instead of a bare build interpreter. `uv run` keeps this
        # repository-owned and fail-closed while the private Blob substrate was
        # already proven by the preceding isolated lineage preflight.
        _run_project_preflight("scripts/production_agentic_runtime_preflight.py")
        _run_isolated_preflight("scripts/production_projected_bootstrap_preflight.py")
        _run_isolated_preflight("scripts/production_execution_snapshot_preflight.py")
        _run_isolated_preflight("scripts/production_run_event_schema_guard.py")
    else:
        print("Production lineage composition preflight: SKIP (non-production)")
        print("Production agentic runtime preflight: SKIP (non-production)")
        print("Production projected bootstrap preflight: SKIP (non-production)")
        print("Production execution-snapshot preflight: SKIP (non-production)")
        print("Production run-event schema guard: SKIP (non-production)")

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
