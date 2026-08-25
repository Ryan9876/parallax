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
    base_url: str,
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
    request = Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed protected production target
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"production proof {method} {path} failed with HTTP {exc.code}: {raw[:1000]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"production proof {method} {path} returned a non-object response")
    return payload


def _create_fresh_proof_plan_run(*, base_url: str, token: str) -> str:
    conversation_id = "6efa6c8a-b2e8-4acf-ae90-e15f8c065c1b"
    work_specification_id = "04fc0bad-0bdc-4e9a-97e2-6ab9de56c289"
    work_specification_digest = "7753bbd56120bc08d70dcbd6d7f302fc975910895a00f4015f0e3f2cb71a8004"
    project_id = "b1f6984d-dc64-4220-bd51-51f6f215d175"
    acceptance_ids = [f"AC-{number:02d}" for number in range(1, 8)]

    created = _request_json(
        base_url=base_url,
        token=token,
        path="/v1/engineering-runs",
        method="POST",
        body={
            "conversation_id": conversation_id,
            "spec_id": "P2-V0.13.0",
            "work_specification_id": work_specification_id,
        },
    )
    run_id = created.get("id")
    if (
        not isinstance(run_id, str)
        or created.get("project_id") != project_id
        or created.get("state") != "SPECIFY"
        or created.get("revision") != 0
    ):
        raise RuntimeError(f"fresh production proof run was not created at SPECIFY revision 0: {created!r}")

    advanced = _request_json(
        base_url=base_url,
        token=token,
        path=f"/v1/engineering-runs/{run_id}/advance",
        method="POST",
        body={
            "stage": "SPECIFY",
            "passed": True,
            "evidence": {
                "work_specification_id": work_specification_id,
                "work_specification_revision": 1,
                "work_specification_digest": work_specification_digest,
                "acceptance_ids": acceptance_ids,
            },
            "operation_key": f"bind:{run_id}:{work_specification_digest}",
            "expected_revision": 0,
            "program_id": "protected-spec-binding-v0.8.0",
        },
    )
    run = advanced.get("run")
    if (
        not isinstance(run, dict)
        or run.get("id") != run_id
        or run.get("project_id") != project_id
        or run.get("state") != "PLAN"
        or run.get("revision") != 1
    ):
        raise RuntimeError(f"fresh production proof run did not reach PLAN revision 1: {advanced!r}")
    return run_id


def _assert_review_completion(*, base_url: str, token: str, run_id: str, evidence: dict[str, Any]) -> None:
    if evidence.get("final_state") != "REVIEW":
        raise RuntimeError(f"fresh production autonomous proof stopped before REVIEW: {evidence!r}")
    run = _request_json(base_url=base_url, token=token, path=f"/v1/engineering-runs/{run_id}", timeout=60)
    attempts = run.get("attempts")
    if not isinstance(attempts, list):
        raise RuntimeError("fresh production proof run returned no protected attempt history")
    required = ("IMPLEMENT", "BUILD", "TEST", "VERIFY")
    passed_stages = {
        str(item.get("stage"))
        for item in attempts
        if isinstance(item, dict) and item.get("status") == "PASSED"
    }
    missing = [stage for stage in required if stage not in passed_stages]
    if missing:
        raise RuntimeError(f"fresh production proof is missing passed protected stages: {missing}")
    if run.get("last_failure_code"):
        raise RuntimeError(f"fresh production proof retained failure code {run.get('last_failure_code')!r}")
    print(
        json.dumps(
            {
                "gate": "Wave 4 final production REVIEW proof",
                "run_id": run_id,
                "final_state": run.get("state"),
                "revision": run.get("revision"),
                "passed_required_stages": list(required),
                "accepted_lineage_ref": evidence.get("accepted_lineage_ref"),
                "event_count": evidence.get("event_count"),
                "stop_reason": evidence.get("stop_reason"),
                "credential_unavailable_absent": evidence.get("credential_unavailable_absent"),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _run_one_time_preview_production_proof() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != "control/w4-production-review-proof":
        return

    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("preview release proof requires existing PARALLAX_ACCESS_TOKEN")

    repository_root = Path(__file__).resolve().parents[3]
    proof_script = repository_root / "scripts" / "w4_release_proof.py"
    if not proof_script.is_file():
        raise RuntimeError("Wave 4 release proof script is unavailable in preview checkout")

    base_url = "https://parallax-api-tan.vercel.app"
    run_id = _create_fresh_proof_plan_run(base_url=base_url, token=token)
    print(f"W4 final production proof setup: PASS (fresh_project_bound_plan_run={run_id})")

    evidence_path = Path("/tmp/w4-runtime-review-proof.json")
    env = os.environ.copy()
    env["PARALLAX_RELEASE_API_URL"] = base_url
    env["PARALLAX_RELEASE_RUN_ID"] = run_id
    env["PARALLAX_RELEASE_BEARER_TOKEN"] = token
    subprocess.run(
        [
            sys.executable,
            str(proof_script),
            "--operation-key",
            f"w4-final-prod-review-proof-{run_id}",
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
    _assert_review_completion(base_url=base_url, token=token, run_id=run_id, evidence=evidence)


def main() -> None:
    _run("scripts/production_provider_preflight.py")
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

    _run_one_time_preview_production_proof()

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
