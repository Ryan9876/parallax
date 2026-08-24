from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--quiet",
                "vercel>=0.9,<0.10",
            ],
            check=True,
        )
        _run("scripts/production_blob_sdk_preflight.py")
    else:
        print("Production Blob SDK preflight: SKIP (non-production)")

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
