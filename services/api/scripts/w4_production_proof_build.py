from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "").strip().lower() != "preview":
        raise RuntimeError("W4 production proof runner is preview-only")

    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN") or "").strip()
    if len(token) < 32:
        raise RuntimeError("Parallax preview access credential is unavailable")

    repo_root = Path(__file__).resolve().parents[3]
    proof = repo_root / "scripts" / "w4_release_proof.py"
    if not proof.is_file():
        raise RuntimeError("W4 release proof script is unavailable")

    env = os.environ.copy()
    env["PARALLAX_RELEASE_BEARER_TOKEN"] = token
    env["PARALLAX_RELEASE_API_URL"] = "https://parallax-api-tan.vercel.app"
    env["PARALLAX_RELEASE_RUN_ID"] = "cfd265a8-0e51-4388-a9f7-5611aa1cf6c1"

    subprocess.run(
        [
            sys.executable,
            str(proof),
            "--operation-key",
            "w4-production-recovery-proof-20260825",
            "--evidence",
            str(repo_root / "release-evidence" / "w4-production-runtime-proof.json"),
        ],
        cwd=repo_root,
        env=env,
        check=True,
    )
    print("W4 production runtime proof: PASS")


if __name__ == "__main__":
    main()
