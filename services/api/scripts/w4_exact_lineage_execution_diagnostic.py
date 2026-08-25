from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.lineage_sandbox_execution import SameLineageVercelSandboxExecutor
from parallax_api.code.runtime_composition import production_durable_lineage_allocator
from parallax_api.code.sandbox_execution import ProtectedCommandRegistry
from parallax_api.db import make_engine


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "b4b64e2d-f9a8-4601-9070-0ebe0c2165ae"
LINEAGE_ID = "src:08ab485bcb21f62e8a62183fedfffd8798fbae4997f15a1fe1b2e18c46e007be"


def _get_json(token: str, path: str) -> object:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed protected production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raise RuntimeError(f"production diagnostic GET {path} failed with HTTP {exc.code}") from exc


def main() -> None:
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("exact-lineage execution diagnostic requires existing Parallax access credential")

    run = _get_json(token, f"/v1/engineering-runs/{RUN_ID}")
    if not isinstance(run, dict):
        raise RuntimeError("production proof run is unavailable")
    project_id = str(run.get("project_id") or "")
    if not project_id:
        raise RuntimeError("production proof run is missing canonical Project identity")

    engine = make_engine(environment="preview")
    allocator = production_durable_lineage_allocator(
        engine,
        materialization_root=Path(tempfile.gettempdir()) / "w4-offline-lineage-proof",
    )
    if allocator is None:
        raise RuntimeError("durable lineage allocator is unavailable")

    try:
        executor = SameLineageVercelSandboxExecutor(allocator)
        registry = ProtectedCommandRegistry()
        results: list[dict[str, object]] = []
        for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):
            spec = registry.spec_for(stage, operation_key=f"w4-offline-proof:{stage.value.lower()}")
            evidence = executor.execute_on_lineage(
                spec,
                project_ref=project_id,
                run_id=RUN_ID,
                source_lineage_ref=LINEAGE_ID,
            )
            result = {
                "stage": stage.value,
                "protected_success": evidence.get("protected_success"),
                "exit_code": evidence.get("exit_code"),
                "timed_out": evidence.get("timed_out"),
                "network_policy": evidence.get("network_policy"),
                "executor": evidence.get("executor"),
                "execution_snapshot_id": evidence.get("execution_snapshot_id"),
                "execution_snapshot_verified": evidence.get("execution_snapshot_verified"),
                "execution_working_directory": evidence.get("execution_working_directory"),
                "lineage_source_transfer": evidence.get("lineage_source_transfer"),
                "source_lineage_ref": LINEAGE_ID,
                "source_file_count": evidence.get("source_file_count"),
                "stdout_excerpt": str(evidence.get("stdout_excerpt") or "")[:500],
                "stderr_excerpt": str(evidence.get("stderr_excerpt") or "")[:500],
            }
            results.append(result)
            if evidence.get("protected_success") is not True:
                print(json.dumps({"run_id": RUN_ID, "lineage_id": LINEAGE_ID, "results": results}, indent=2, sort_keys=True))
                raise RuntimeError(f"exact-lineage {stage.value} diagnostic failed")

        print(
            json.dumps(
                {
                    "gate": "exact-lineage offline execution proof",
                    "run_id": RUN_ID,
                    "lineage_id": LINEAGE_ID,
                    "results": results,
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
