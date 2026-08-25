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
    if (
        (os.getenv("VERCEL_ENV") or "") == "preview"
        and (os.getenv("VERCEL_GIT_COMMIT_REF") or "") == "control/w4-production-review-proof"
    ):
        _run("scripts/w4_preimplement_diagnostic.py")
    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
