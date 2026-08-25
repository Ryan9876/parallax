from __future__ import annotations

import json
import os

from vercel.api import session
from vercel.sandbox import NetworkPolicy, SnapshotSource
from vercel.sandbox import sync as sandbox

from parallax_api.execution_environment import execution_snapshot_id


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "production":
        print("Production execution-snapshot preflight: SKIP (non-production)")
        return

    project_id = (os.getenv("VERCEL_PROJECT_ID") or "").strip()
    if not project_id:
        raise RuntimeError("production execution snapshot preflight requires Vercel project identity")
    snapshot_id = execution_snapshot_id()

    with session():
        with sandbox.create_sandbox(
            project_id=project_id,
            source=SnapshotSource(snapshot_id=snapshot_id),
            execution_time_limit=90,
            persistent=False,
            network_policy=NetworkPolicy.deny_all(),
            env={},
            destroy=True,
            tags={"parallax": "execution-snapshot-preflight"},
        ) as instance:
            if getattr(instance, "source_snapshot_id", None) != snapshot_id:
                raise RuntimeError("production execution snapshot identity verification failed")
            result = instance.run_process(
                "python",
                [
                    "-c",
                    (
                        "import importlib.util,json,os,shutil;"
                        "required=['pytest','sqlalchemy','pydantic','fastapi'];"
                        "missing=[name for name in required if importlib.util.find_spec(name) is None];"
                        "root='/vercel/sandbox';"
                        "print(json.dumps({"
                        "'missing':missing,"
                        "'source_root_exists':os.path.isdir(root),"
                        "'source_root_entries':sorted(os.listdir(root))[:20] if os.path.isdir(root) else [],"
                        "'uv':bool(shutil.which('uv'))"
                        "},sort_keys=True));"
                        "raise SystemExit(1 if missing else 0)"
                    ),
                ],
                cwd="/vercel",
                env={},
                kill_after=60,
                capture_output=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"production execution snapshot dependency probe failed: {(result.stderr or '')[:1000]}")
            payload = json.loads((result.stdout or "{}").strip())
            if payload.get("missing"):
                raise RuntimeError("production execution snapshot is missing required offline dependencies")
            if payload.get("source_root_entries"):
                raise RuntimeError("production execution snapshot unexpectedly contains repository source")

    print(
        "Production execution-snapshot preflight: PASS "
        f"(snapshot={snapshot_id}; deny-all restore verified; offline dependencies verified; source-free root verified)"
    )


if __name__ == "__main__":
    main()
