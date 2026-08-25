from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


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


def _inspect_sandbox_sdk() -> None:
    if (os.getenv("VERCEL_ENV") or "") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != "control/w4-sandbox-sdk-inspect":
        return
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("Sandbox SDK inspection requires uv")
    code = r'''
from importlib.metadata import version
import inspect
from vercel.sandbox import sync as sandbox

filesystem_type = sandbox.SyncSandboxFilesystem
batch_type = sandbox.SyncSandboxFilesystemBatch
print(
    "Sandbox SDK lifecycle inspection: "
    f"vercel={version('vercel')} vercel-sandbox={version('vercel-sandbox')} "
    f"batch_doc={inspect.getdoc(filesystem_type.batch)!r} "
    f"batch_enter={hasattr(batch_type, '__enter__')} batch_exit={hasattr(batch_type, '__exit__')} "
    f"batch_enter_sig={str(inspect.signature(batch_type.__enter__)) if hasattr(batch_type, '__enter__') else None} "
    f"batch_exit_sig={str(inspect.signature(batch_type.__exit__)) if hasattr(batch_type, '__exit__') else None} "
    f"batch_class_doc={inspect.getdoc(batch_type)!r}"
)
'''
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
            "vercel-sandbox>=0.4,<0.5",
            "python",
            "-c",
            code,
        ],
        check=True,
    )


def main() -> None:
    _inspect_sandbox_sdk()
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_delivery_permission_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        # Production publication remains fail-closed on every runtime substrate
        # required for durable source bootstrap and exact-lineage execution.
        _run_isolated_preflight("scripts/production_lineage_composition_preflight.py")
        _run_isolated_preflight("scripts/production_projected_bootstrap_preflight.py")
        _run_isolated_preflight("scripts/production_execution_snapshot_preflight.py")
        _run_isolated_preflight("scripts/production_run_event_schema_guard.py")
    else:
        print("Production lineage composition preflight: SKIP (non-production)")
        print("Production projected bootstrap preflight: SKIP (non-production)")
        print("Production execution-snapshot preflight: SKIP (non-production)")
        print("Production run-event schema guard: SKIP (non-production)")

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
