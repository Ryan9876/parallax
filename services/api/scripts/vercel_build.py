from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


_SCRIPT_ROOT = Path(__file__).resolve().parent
_API_ROOT = _SCRIPT_ROOT.parent


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def _run_isolated_preflight(script: str) -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("production durable bootstrap preflight requires uv")
    subprocess.run(
        [
            uv,
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


def _run_service_preflight(script: str) -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("production service-runtime preflight requires uv")
    script_path = (_API_ROOT / script).resolve()
    if script_path.parent != _SCRIPT_ROOT or script_path.suffix != ".py":
        raise RuntimeError("production service-runtime preflight script is outside the trusted scripts root")
    subprocess.run(
        [
            uv,
            "run",
            "--isolated",
            "--no-progress",
            "--no-python-downloads",
            "--no-dev",
            "--project",
            str(_API_ROOT),
            "python",
            str(script_path),
        ],
        check=True,
        cwd=_API_ROOT,
    )


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_delivery_permission_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment == "preview" and os.getenv("PARALLAX_DOTNET_SNAPSHOT_PROVISIONING") == "1":
        # Release-only provisioning path. It exists only on the governed work
        # branch and is removed before the runtime release is merged.
        _run_isolated_preflight("scripts/provision_dotnet_execution_snapshot.py")

    if environment == "production":
        # Production publication remains fail-closed on every runtime substrate
        # required for durable source bootstrap and exact-lineage execution.
        _run_isolated_preflight("scripts/production_lineage_composition_preflight.py")
        # W6 agentic activation imports the actual service control-plane runtime,
        # so its build canary must execute against the service project's declared
        # runtime dependencies rather than a duplicated ad hoc dependency list.
        _run_service_preflight("scripts/production_agentic_runtime_preflight.py")
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
