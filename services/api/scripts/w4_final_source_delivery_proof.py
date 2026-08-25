from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE_URL = "https://parallax-api-tan.vercel.app"
PROOF_BRANCH = "control/w4-final-source-delivery-proof-7"
PROJECT_ID = "b1f6984d-dc64-4220-bd51-51f6f215d175"
REPOSITORY_REF = "github:Ryan9876/parallax"
VERCEL_PROJECT_ID = "prj_wLXC5JjjetJf0H97kncRlqczD3OC"
PROOF_PATH = "apps/client/w4-final-source-delivery-proof.txt"
PROOF_TEXT = "Parallax Wave 4 final source delivery proof."

BUILD_COMMAND = "python -m compileall -q services/api/parallax_api scripts"
TEST_COMMAND = (
    "python -m pytest -q services/api/tests/test_code_execution_kernel.py "
    "services/api/tests/test_code_autonomy.py"
)
VERIFY_COMMAND = (
    "python -m pytest -q services/api/tests/test_code_execution_kernel.py "
    "-k 'protected or execution or approved'"
)

PROOF_OBJECTIVE = f"""Parallax Wave 4 final production source-delivery proof.

Make exactly one candidate-lineage source change: create `{PROOF_PATH}` with UTF-8 content exactly `{PROOF_TEXT}` followed by one newline. Preserve every pre-existing file byte-for-byte. Do not modify code, configuration, dependencies, tests, provider authority, credentials, Project settings, Vercel settings, deployment configuration, or any other path.

The protected execution commands are fixed server-side and require no choice or discovery:
- BUILD: `{BUILD_COMMAND}`
- TEST: `{TEST_COMMAND}`
- VERIFY: `{VERIFY_COMMAND}`
Use only those existing protected commands. Evidence is the existing bounded Engineering Run attempt evidence produced by the runtime: stage/tool identity, exit code, duration/digests and bounded excerpts, timeout/redaction facts, and exact accepted source-lineage binding where applicable. Do not expose unrestricted logs, credentials, raw provider payloads, or hidden reasoning.

The REVIEW contract is fixed: after protected VERIFY succeeds, autonomous execution stops at Engineering Run state `REVIEW` with stop reason `HUMAN_REQUIRED`. Do not transition to COMPLETE and do not perform operator review.

The delivery target is fixed server-side: canonical Project `{PROJECT_ID}`, repository `{REPOSITORY_REF}`, base branch `main`, deterministic runtime branch `parallax/<project-prefix>-<run-prefix>`, and registered Preview-only Vercel client project `{VERCEL_PROJECT_ID}` rooted at `apps/client`. Existing authority permits only bounded GitHub branch create, exact accepted-lineage commit, pull-request create/read, and Vercel Preview create/read. It does not permit merge, Vercel production promotion, production target selection, aliases/domains, environment mutation, secret mutation, broader repository access, or any other provider action.

Acceptance is exact: the one proof file exists with exactly the required line and newline; all pre-existing files are unchanged; BUILD, TEST, and VERIFY pass against the exact accepted lineage; the run stops at REVIEW/HUMAN_REQUIRED; source delivery records one exact GitHub branch/commit/open PR plus one Preview deployment under the registered client Preview target; no merge or production publication occurs; and authority remains unchanged. There are no open design or implementation questions."""


def _request_json(*, token: str, path: str, method: str = "GET", body: dict[str, Any] | None = None, timeout: float = 120.0) -> dict[str, Any]:
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
        raise RuntimeError(f"production proof {method} {path} failed with HTTP {exc.code}: {raw[:1200]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"production proof {method} {path} returned non-object response")
    return payload


def _create_approved_spec(token: str) -> tuple[str, str, str]:
    conversation = _request_json(
        token=token,
        path="/v1/conversations",
        method="POST",
        body={"mode": "code", "project_id": PROJECT_ID},
    )
    conversation_id = conversation.get("id")
    spec_id = conversation.get("spec_id")
    if not isinstance(conversation_id, str) or not isinstance(spec_id, str) or conversation.get("project_id") != PROJECT_ID:
        raise RuntimeError(f"proof Code conversation is invalid: {conversation!r}")

    _request_json(
        token=token,
        path=f"/v1/conversations/{conversation_id}/messages",
        method="POST",
        body={"role": "user", "content": PROOF_OBJECTIVE},
    )
    draft = _request_json(
        token=token,
        path=f"/v1/conversations/{conversation_id}/work-specifications/draft",
        method="POST",
        timeout=180.0,
    )
    work_specification_id = draft.get("id")
    if not isinstance(work_specification_id, str) or draft.get("status") != "DRAFT" or draft.get("revision") != 1:
        raise RuntimeError(f"proof Work Specification draft is invalid: {draft!r}")
    if draft.get("open_questions") not in ([], None):
        raise RuntimeError(f"proof Work Specification retained open questions: {draft.get('open_questions')!r}")
    combined = "\n".join(
        [str(draft.get("objective") or "")]
        + [str(item) for item in draft.get("constraints", [])]
        + [str(item) for item in draft.get("acceptance_criteria", [])]
    )
    for required in (PROOF_PATH, PROOF_TEXT, "BUILD", "TEST", "VERIFY", "REVIEW", "Preview"):
        if required not in combined:
            raise RuntimeError(f"proof Work Specification lost required scope fact {required!r}")
    lowered = combined.casefold()
    if "only" not in lowered or "preserve" not in lowered or "merge" not in lowered or "production" not in lowered:
        raise RuntimeError("proof Work Specification lost bounded one-file/no-production semantics")

    approved = _request_json(
        token=token,
        path=f"/v1/work-specifications/{work_specification_id}/approve",
        method="POST",
    )
    if approved.get("status") != "APPROVED" or approved.get("id") != work_specification_id:
        raise RuntimeError(f"proof Work Specification approval failed: {approved!r}")
    return conversation_id, spec_id, work_specification_id


def _create_plan_run(token: str, conversation_id: str, spec_id: str, work_specification_id: str) -> str:
    created = _request_json(
        token=token,
        path="/v1/engineering-runs",
        method="POST",
        body={
            "conversation_id": conversation_id,
            "spec_id": spec_id,
            "work_specification_id": work_specification_id,
        },
    )
    run_id = created.get("id")
    digest = created.get("work_specification_digest")
    criteria = created.get("acceptance_criteria")
    if not isinstance(run_id, str) or created.get("state") != "SPECIFY" or created.get("revision") != 0 or not isinstance(digest, str) or len(digest) != 64 or not isinstance(criteria, list) or not criteria:
        raise RuntimeError(f"proof Engineering Run creation failed: {created!r}")
    acceptance_ids = [item.get("id") for item in criteria if isinstance(item, dict) and isinstance(item.get("id"), str)]
    if len(acceptance_ids) != len(criteria):
        raise RuntimeError("proof Engineering Run acceptance map is malformed")
    advanced = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/advance",
        method="POST",
        body={
            "stage": "SPECIFY",
            "passed": True,
            "evidence": {
                "work_specification_id": work_specification_id,
                "work_specification_revision": 1,
                "work_specification_digest": digest,
                "acceptance_ids": acceptance_ids,
            },
            "operation_key": f"bind:{run_id}:{digest}",
            "expected_revision": 0,
            "program_id": "protected-spec-binding-v0.8.0",
        },
    )
    run = advanced.get("run")
    if not isinstance(run, dict) or run.get("state") != "PLAN" or run.get("revision") != 1:
        raise RuntimeError(f"proof Engineering Run did not reach PLAN: {advanced!r}")
    return run_id


def _validate_delivery(token: str, run_id: str, evidence: dict[str, Any]) -> None:
    run = _request_json(token=token, path=f"/v1/engineering-runs/{run_id}")
    if run.get("state") != "REVIEW" or run.get("revision") != 6 or run.get("last_failure_code") is not None:
        raise RuntimeError(f"proof run did not reach clean REVIEW: {run!r}")
    attempts = run.get("attempts")
    if not isinstance(attempts, list):
        raise RuntimeError("proof run has no attempt history")
    passed = {item.get("stage") for item in attempts if isinstance(item, dict) and item.get("status") == "PASSED"}
    missing = [stage for stage in ("IMPLEMENT", "BUILD", "TEST", "VERIFY") if stage not in passed]
    if missing:
        raise RuntimeError(f"proof missing protected passed stages: {missing}")

    event_page = _request_json(token=token, path=f"/v1/engineering-runs/{run_id}/events?after_sequence=0&limit=200")
    events = event_page.get("events")
    if not isinstance(events, list):
        raise RuntimeError("proof event page is invalid")
    deliveries = [item for item in events if isinstance(item, dict) and item.get("event_type") == "SOURCE_DELIVERY" and item.get("outcome") == "SUCCEEDED"]
    if len(deliveries) != 1:
        raise RuntimeError(f"proof requires exactly one successful SOURCE_DELIVERY: {deliveries!r}")
    metadata = deliveries[0].get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("proof SOURCE_DELIVERY metadata is invalid")
    for key in ("branch_name", "commit_revision", "preview_deployment_id", "preview_status"):
        if not isinstance(metadata.get(key), str) or not metadata[key]:
            raise RuntimeError(f"proof SOURCE_DELIVERY missing {key}: {metadata!r}")
    if not isinstance(metadata.get("pull_request_number"), int):
        raise RuntimeError(f"proof SOURCE_DELIVERY missing pull_request_number: {metadata!r}")
    if metadata.get("preview_status") not in {"QUEUED", "BUILDING", "READY"}:
        raise RuntimeError(f"proof Preview entered terminal failure before delivery record: {metadata!r}")

    print(json.dumps({
        "gate": "Wave 4 final target-affecting production source-delivery proof",
        "run_id": run_id,
        "state": run.get("state"),
        "revision": run.get("revision"),
        "stop_reason": evidence.get("stop_reason"),
        "accepted_lineage_ref": evidence.get("accepted_lineage_ref"),
        "branch_name": metadata["branch_name"],
        "commit_revision": metadata["commit_revision"],
        "pull_request_number": metadata["pull_request_number"],
        "preview_deployment_id": metadata["preview_deployment_id"],
        "preview_status_at_record": metadata["preview_status"],
    }, indent=2, sort_keys=True))


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "") != "preview" or (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != PROOF_BRANCH:
        return
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("final proof requires existing PARALLAX_ACCESS_TOKEN")

    conversation_id, spec_id, work_specification_id = _create_approved_spec(token)
    run_id = _create_plan_run(token, conversation_id, spec_id, work_specification_id)
    print(f"W4 target-affecting proof setup: PASS (conversation={conversation_id}, work_specification={work_specification_id}, run={run_id})")

    repository_root = Path(__file__).resolve().parents[3]
    evidence_path = Path("/tmp/w4-final-runtime-proof.json")
    env = os.environ.copy()
    env["PARALLAX_RELEASE_API_URL"] = BASE_URL
    env["PARALLAX_RELEASE_RUN_ID"] = run_id
    env["PARALLAX_RELEASE_BEARER_TOKEN"] = token
    subprocess.run([
        sys.executable,
        str(repository_root / "scripts" / "w4_release_proof.py"),
        "--operation-key",
        f"w4-final-prod-source-delivery-{run_id}",
        "--timeout",
        "600",
        "--evidence",
        str(evidence_path),
    ], check=True, env=env)
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if not isinstance(evidence, dict):
        raise RuntimeError("final runtime proof evidence is malformed")
    _validate_delivery(token, run_id, evidence)


if __name__ == "__main__":
    main()
