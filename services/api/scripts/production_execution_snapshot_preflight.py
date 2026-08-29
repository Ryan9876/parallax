from __future__ import annotations

import json
import os
from pathlib import Path
import sys

from vercel.api import session
from vercel.sandbox import NetworkPolicy, SnapshotSource
from vercel.sandbox import sync as sandbox


_API_ROOT = Path(__file__).resolve().parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from parallax_api.execution_environment import execution_snapshot_id_for_profile


_SOURCE_ROOT = "/vercel/sandbox"
_DOTNET_SDK_VERSION = "8.0.424"


def _restore(project_id: str, snapshot_id: str, *, tag: str):
    return sandbox.create_sandbox(
        project_id=project_id,
        source=SnapshotSource(snapshot_id=snapshot_id),
        execution_time_limit=90,
        persistent=False,
        network_policy=NetworkPolicy.deny_all(),
        env={},
        destroy=True,
        tags={"parallax": "execution-snapshot-preflight", "profile": tag},
    )


def _require_exact_snapshot(instance: object, snapshot_id: str, *, label: str) -> None:
    if getattr(instance, "current_snapshot_id", None) != snapshot_id:
        raise RuntimeError(f"production {label} execution snapshot identity verification failed")


def _require_empty_source_root(instance: object, *, label: str) -> None:
    result = instance.run_process(
        "python",
        [
            "-c",
            (
                "import json,os;"
                f"root={_SOURCE_ROOT!r};"
                "entries=sorted(os.listdir(root))[:20] if os.path.isdir(root) else [];"
                "print(json.dumps({'entries':entries},sort_keys=True));"
                "raise SystemExit(1 if entries else 0)"
            ),
        ],
        cwd="/vercel",
        env={},
        kill_after=30,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"production {label} execution snapshot unexpectedly contains repository source")
    payload = json.loads((result.stdout or "{}").strip())
    if payload.get("entries"):
        raise RuntimeError(f"production {label} execution snapshot unexpectedly contains repository source")


def _preflight_common(project_id: str, snapshot_id: str) -> None:
    with _restore(project_id, snapshot_id, tag="python-node-common") as instance:
        _require_exact_snapshot(instance, snapshot_id, label="common")
        python_result = instance.run_process(
            "python",
            [
                "-c",
                (
                    "import importlib.util,json,shutil;"
                    "required=['pytest','sqlalchemy','pydantic','fastapi'];"
                    "missing=[name for name in required if importlib.util.find_spec(name) is None];"
                    "print(json.dumps({'missing':missing,'uv':bool(shutil.which('uv'))},sort_keys=True));"
                    "raise SystemExit(1 if missing or not shutil.which('uv') else 0)"
                ),
            ],
            cwd="/vercel",
            env={},
            kill_after=60,
            capture_output=True,
        )
        if python_result.returncode != 0:
            raise RuntimeError(
                "production common execution snapshot Python readiness probe failed: "
                f"{(python_result.stderr or '')[:1000]}"
            )
        python_payload = json.loads((python_result.stdout or "{}").strip())
        if python_payload.get("missing") or python_payload.get("uv") is not True:
            raise RuntimeError("production common execution snapshot is missing required Python tooling")

        node_result = instance.run_process(
            "node",
            ["--version"],
            cwd="/vercel",
            env={},
            kill_after=30,
            capture_output=True,
        )
        if node_result.returncode != 0 or not (node_result.stdout or "").strip().startswith("v"):
            raise RuntimeError("production common execution snapshot Node readiness probe failed")
        _require_empty_source_root(instance, label="common")


def _preflight_dotnet(project_id: str, snapshot_id: str) -> None:
    with _restore(project_id, snapshot_id, tag="dotnet-v1") as instance:
        _require_exact_snapshot(instance, snapshot_id, label=".NET")
        result = instance.run_process(
            "dotnet",
            ["--info"],
            cwd="/vercel",
            env={},
            kill_after=30,
            capture_output=True,
        )
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode != 0 or _DOTNET_SDK_VERSION not in output:
            raise RuntimeError("production .NET execution snapshot readiness probe failed")
        _require_empty_source_root(instance, label=".NET")


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "production":
        print("Production execution-snapshot preflight: SKIP (non-production)")
        return

    project_id = (os.getenv("VERCEL_PROJECT_ID") or "").strip()
    if not project_id:
        raise RuntimeError("production execution snapshot preflight requires Vercel project identity")

    common_snapshot_id = execution_snapshot_id_for_profile("python-v1")
    node_snapshot_id = execution_snapshot_id_for_profile("node-v1")
    if node_snapshot_id != common_snapshot_id:
        raise RuntimeError("production Python and Node execution snapshot mapping drifted")
    dotnet_snapshot_id = execution_snapshot_id_for_profile("dotnet-v1")
    if dotnet_snapshot_id == common_snapshot_id:
        raise RuntimeError("production .NET execution snapshot must be dedicated")

    with session():
        _preflight_common(project_id, common_snapshot_id)
        _preflight_dotnet(project_id, dotnet_snapshot_id)

    print(
        "Production execution-snapshot preflight: PASS "
        f"(common_snapshot={common_snapshot_id}; dotnet_snapshot={dotnet_snapshot_id}; "
        "deny-all restore verified; Python/Node/.NET toolchains verified; no repository source present)"
    )


if __name__ == "__main__":
    main()
