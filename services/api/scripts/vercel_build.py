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


def _run_one_time_preview_production_proof() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != "control/w4-source-context-hotfix":
        return

    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("preview release proof requires existing PARALLAX_ACCESS_TOKEN")

    repository_root = Path(__file__).resolve().parents[3]
    proof_script = repository_root / "scripts" / "w4_release_proof.py"
    if not proof_script.is_file():
        raise RuntimeError("Wave 4 release proof script is unavailable in preview checkout")

    env = os.environ.copy()
    env["PARALLAX_RELEASE_API_URL"] = "https://parallax-api-tan.vercel.app"
    env["PARALLAX_RELEASE_RUN_ID"] = "cfd265a8-0e51-4388-a9f7-5611aa1cf6c1"
    env["PARALLAX_RELEASE_BEARER_TOKEN"] = token
    subprocess.run(
        [
            sys.executable,
            str(proof_script),
            "--operation-key",
            "w4-prod-proof-bb37aef-preview-build-20260825",
            "--timeout",
            "240",
            "--evidence",
            "/tmp/w4-runtime-proof.json",
        ],
        check=True,
        env=env,
    )


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        # Wave 3 bootstrap evidence runs first so this hotfix can be verified in
        # production even while Wave 4 remains deliberately source-integrated
        # but not schema-promoted. The final read-only guard prevents the build
        # from exposing Wave 4 code until its additive migration actually exists.
        _run_isolated_preflight("scripts/production_lineage_composition_preflight.py")
        _run_isolated_preflight("scripts/production_projected_bootstrap_preflight.py")
        _run_isolated_preflight("scripts/production_run_event_schema_guard.py")
    else:
        print("Production lineage composition preflight: SKIP (non-production)")
        print("Production projected bootstrap preflight: SKIP (non-production)")
        print("Production run-event schema guard: SKIP (non-production)")

    _run_one_time_preview_production_proof()

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
