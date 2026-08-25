from __future__ import annotations

import json
import os

from vercel.api import session
from vercel.sandbox import sync as sandbox

DEPENDENCIES = (
    "fastapi>=0.128,<0.129",
    "uvicorn[standard]>=0.48,<1",
    "sqlalchemy>=2.0.50,<3",
    "psycopg[binary]>=3.2,<4",
    "pydantic>=2.13,<3",
    "pydantic-settings>=2.10,<3",
    "dspy>=3.3,<4",
    "httpx>=0.28,<1",
    "vercel>=0.9,<0.10",
    "vercel-sandbox>=0.4,<0.5",
    "pytest>=9,<10",
)


def main() -> None:
    project_id = (os.getenv("VERCEL_PROJECT_ID") or "").strip()
    if not project_id:
        raise RuntimeError("execution snapshot provisioning requires Vercel project identity")

    snapshot_id: str | None = None
    installed: dict[str, str] = {}
    with session():
        with sandbox.create_sandbox(
            project_id=project_id,
            execution_time_limit=300,
            persistent=False,
            env={},
            destroy=False,
            tags={"parallax": "offline-execution-base-provisioning", "authority": "operator-release"},
        ) as instance:
            install = instance.run_process(
                "uv",
                ["pip", "install", "--system", *DEPENDENCIES],
                cwd="/vercel",
                env={},
                kill_after=240,
                capture_output=True,
            )
            if install.returncode != 0:
                raise RuntimeError(f"dependency snapshot install failed: {(install.stderr or '')[:1500]}")
            probe = instance.run_process(
                "python",
                [
                    "-c",
                    (
                        "import importlib.metadata,json;"
                        "names=['fastapi','sqlalchemy','psycopg','pydantic','pydantic-settings','dspy','httpx','vercel','vercel-sandbox','pytest'];"
                        "print(json.dumps({n:importlib.metadata.version(n) for n in names},sort_keys=True))"
                    ),
                ],
                cwd="/vercel",
                env={},
                kill_after=60,
                capture_output=True,
            )
            if probe.returncode != 0:
                raise RuntimeError(f"dependency snapshot probe failed: {(probe.stderr or '')[:1500]}")
            installed = json.loads((probe.stdout or "{}").strip())
            snapshot = instance.snapshot(expiration=0)
            snapshot_id = str(getattr(snapshot, "id", "") or "")
            if not snapshot_id.startswith("snap_"):
                raise RuntimeError("execution dependency snapshot did not return a valid snapshot ID")

    print(
        json.dumps(
            {
                "snapshot_id": snapshot_id,
                "source_contains_repository": False,
                "runtime_execution_network_policy": "deny-all (enforced by consumer, not provisioning sandbox)",
                "installed": installed,
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise RuntimeError("snapshot provisioning stops intentionally after recording immutable artifact identity")


if __name__ == "__main__":
    main()
