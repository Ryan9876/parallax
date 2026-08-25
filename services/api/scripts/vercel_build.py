from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
PROOF_BRANCH = "control/w4-final-source-delivery-proof-2"
CONVERSATION_ID = "6efa6c8a-b2e8-4acf-ae90-e15f8c065c1b"
WORK_SPECIFICATION_ID = "04fc0bad-0bdc-4e9a-97e2-6ab9de56c289"
WORK_SPECIFICATION_DIGEST = "7753bbd56120bc08d70dcbd6d7f302fc975910895a00f4015f0e3f2cb71a8004"
PROJECT_ID = "b1f6984d-dc64-4220-bd51-51f6f215d175"


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


def _request_json(
    *,
    token: str,
    path: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed protected production target
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"production proof {method} {path} failed with HTTP {exc.code}: {raw[:1000]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"production proof {method} {path} returned non-object response")
    return payload


def _create_fresh_plan_run(*, token: str) -> str:
    created = _request_json(
        token=token,
        path="/v1/engineering-runs",
        method="POST",
        body={
            "conversation_id": CONVERSATION_ID,
            "spec_id": "P2-V0.13.0",
            "work_specification_id": WORK_SPECIFICATION_ID,
        },
    )
    run_id = created.get("id")
    if (
        not isinstance(run_id, str)
        or created.get("project_id") != PROJECT_ID
        or created.get("state") != "SPECIFY"
        or created.get("revision") != 0
    ):
        raise RuntimeError(f"fresh production proof run was not created at SPECIFY revision 0: {created!r}")

    acceptance_ids = [f"AC-{number:02d}" for number in range(1, 8)]
    advanced = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/advance",
        method="POST",
        body={
            "stage": "SPECIFY",
            "passed": True,
            "evidence": {
                "work_specification_id": WORK_SPECIFICATION_ID,
                "work_specification_revision": 1,
                "work_specification_digest": WORK_SPECIFICATION_DIGEST,
                "acceptance_ids": acceptance_ids,
            },
            "operation_key": f"bind:{run_id}:{WORK_SPECIFICATION_DIGEST}",
            "expected_revision": 0,
            "program_id": "protected-spec-binding-v0.8.0",
        },
    )
    run = advanced.get("run")
    if (
        not isinstance(run, dict)
        or run.get("id") != run_id
        or run.get("project_id") != PROJECT_ID
        or run.get("state") != "PLAN"
        or run.get("revision") != 1
    ):
        raise RuntimeError(f"fresh production proof run did not reach PLAN revision 1: {advanced!r}")
    return run_id


def _assert_review(*, token: str, run_id: str, evidence: dict[str, Any]) -> None:
    run = _request_json(token=token, path=f"/v1/engineering-runs/{run_id}")
    if run.get("state") != "REVIEW" or evidence.get("final_state") != "REVIEW":
        raise RuntimeError(
            f"fresh production autonomous proof stopped before REVIEW: state={run.get('state')!r}, evidence={evidence!r}"
        )
    attempts = run.get("attempts")
    if not isinstance(attempts, list):
        raise RuntimeError("fresh production proof returned no protected attempt history")
    required = ("IMPLEMENT", "BUILD", "TEST", "VERIFY")
    passed = {
        str(item.get("stage"))
        for item in attempts
        if isinstance(item, dict) and item.get("status") == "PASSED"
    }
    missing = [stage for stage in required if stage not in passed]
    if missing:
        raise RuntimeError(f"fresh production proof is missing passed protected stages: {missing}")
    if run.get("last_failure_code"):
        raise RuntimeError(f"fresh production proof retained failure code {run.get('last_failure_code')!r}")
    if evidence.get("credential_unavailable_absent") is not True:
        raise RuntimeError("fresh production proof did not prove credential failure absence")

    event_page = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/events?after_sequence=0&limit=200",
    )
    events = event_page.get("events")
    if not isinstance(events, list):
        raise RuntimeError("fresh production proof returned no persisted run-event page")
    deliveries = [
        item
        for item in events
        if isinstance(item, dict)
        and item.get("event_type") == "SOURCE_DELIVERY"
        and item.get("outcome") == "SUCCEEDED"
    ]
    if len(deliveries) != 1:
        raise RuntimeError(f"fresh production proof requires one successful SOURCE_DELIVERY event: {deliveries!r}")
    delivery = deliveries[0]
    metadata = delivery.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("successful SOURCE_DELIVERY event has no bounded metadata")
    required_delivery = {
        "branch_name": str,
        "commit_revision": str,
        "pull_request_number": int,
        "preview_deployment_id": str,
        "preview_status": str,
    }
    for key, expected_type in required_delivery.items():
        value = metadata.get(key)
        if not isinstance(value, expected_type) or isinstance(value, bool) or not value:
            raise RuntimeError(f"successful SOURCE_DELIVERY is missing {key}: {metadata!r}")
    if metadata.get("preview_status") != "READY":
        raise RuntimeError(f"successful SOURCE_DELIVERY Preview is not READY: {metadata!r}")

    print(
        json.dumps(
            {
                "gate": "Wave 4 final production SOURCE_DELIVERY proof",
                "run_id": run_id,
                "final_state": run.get("state"),
                "revision": run.get("revision"),
                "passed_required_stages": list(required),
                "accepted_lineage_ref": evidence.get("accepted_lineage_ref"),
                "event_count": evidence.get("event_count"),
                "highest_sequence": evidence.get("highest_sequence"),
                "stop_reason": evidence.get("stop_reason"),
                "credential_unavailable_absent": True,
                "delivery": {
                    "branch_name": metadata["branch_name"],
                    "commit_revision": metadata["commit_revision"],
                    "pull_request_number": metadata["pull_request_number"],
                    "preview_deployment_id": metadata["preview_deployment_id"],
                    "preview_status": metadata["preview_status"],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


def _run_final_proof() -> None:
    if (os.getenv("VERCEL_ENV") or "") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != PROOF_BRANCH:
        return
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("final production proof requires existing PARALLAX_ACCESS_TOKEN")

    repository_root = Path(__file__).resolve().parents[3]
    proof_script = repository_root / "scripts" / "w4_release_proof.py"
    run_id = _create_fresh_plan_run(token=token)
    print(f"W4 final production proof setup: PASS (fresh_project_bound_plan_run={run_id})")

    evidence_path = Path("/tmp/w4-final-runtime-proof.json")
    env = os.environ.copy()
    env["PARALLAX_RELEASE_API_URL"] = BASE_URL
    env["PARALLAX_RELEASE_RUN_ID"] = run_id
    env["PARALLAX_RELEASE_BEARER_TOKEN"] = token
    subprocess.run(
        [
            sys.executable,
            str(proof_script),
            "--operation-key",
            f"w4-final-prod-source-delivery-{run_id}",
            "--timeout",
            "600",
            "--evidence",
            str(evidence_path),
        ],
        check=True,
        env=env,
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise RuntimeError("Wave 4 runtime proof evidence is malformed")
    _assert_review(token=token, run_id=run_id, evidence=evidence)


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_delivery_permission_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        _run_isolated_preflight("scripts/production_lineage_composition_preflight.py")
        _run_isolated_preflight("scripts/production_projected_bootstrap_preflight.py")
        _run_isolated_preflight("scripts/production_execution_snapshot_preflight.py")
        _run_isolated_preflight("scripts/production_run_event_schema_guard.py")
    else:
        print("Production lineage composition preflight: SKIP (non-production)")
        print("Production projected bootstrap preflight: SKIP (non-production)")
        print("Production execution-snapshot preflight: SKIP (non-production)")
        print("Production run-event schema guard: SKIP (non-production)")

    _run_final_proof()

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
