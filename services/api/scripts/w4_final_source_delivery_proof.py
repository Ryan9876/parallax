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
VERCEL_PROJECT_ID = "prj_4lhve1AXZntfauaGHvkuaGWC6KJX"
PROOF_PATH = "services/api/w4-final-source-delivery-proof.txt"
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

The protected execution commands are already fixed server-side and require no choice or discovery:
- BUILD: `{BUILD_COMMAND}`
- TEST: `{TEST_COMMAND}`
- VERIFY: `{VERIFY_COMMAND}`
Use only those existing protected commands. Evidence is the existing bounded Engineering Run attempt evidence produced by the runtime: exact stage/tool identity, exit code, duration/digests and bounded excerpts, timeout/redaction facts, and exact accepted source-lineage binding where applicable. Do not invent another evidence format and do not expose unrestricted logs, credentials, raw provider payloads, or hidden reasoning.

The REVIEW contract is fixed: after protected VERIFY succeeds, autonomous execution stops at Engineering Run state `REVIEW` with stop reason `HUMAN_REQUIRED`. Do not transition to COMPLETE. No operator review action is part of this proof.

The delivery target is fixed server-side and requires no choice or discovery: canonical Project `{PROJECT_ID}`, repository `{REPOSITORY_REF}`, default/base branch `main`, deterministic runtime branch `parallax/<project-prefix>-<run-prefix>`, and the already registered Preview-only Vercel project `{VERCEL_PROJECT_ID}`. Existing authority permits only the bounded GitHub branch create, exact accepted-lineage commit, pull-request create/read, and Vercel Preview create/read actions. It does not permit merge, Vercel production promotion, production target selection, aliases/domains, environment mutation, secret mutation, broader repository access, or any other provider action.

Acceptance is exact: the one proof file exists with exactly the required line and newline; all pre-existing files are unchanged; BUILD, TEST, and VERIFY pass against the exact accepted lineage; the run stops at REVIEW/HUMAN_REQUIRED; source delivery records one exact GitHub branch/commit/open PR plus one Preview deployment under the registered Preview-only target; no merge or production publication occurs; and authority remains unchanged. There are no open design or implementation questions for this proof."""


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


def _create_approved_proof_spec(*, token: str) -> tuple[str, str, str]:
    conversation = _request_json(
        token=token,
        path="/v1/conversations",
        method="POST",
        body={"mode": "code", "project_id": PROJECT_ID},
    )
    conversation_id = conversation.get("id")
    spec_id = conversation.get("spec_id")
    if (
        not isinstance(conversation_id, str)
        or not isinstance(spec_id, str)
        or conversation.get("project_id") != PROJECT_ID
        or conversation.get("mode") != "code"
        or conversation.get("status") != "ACTIVE"
    ):
        raise RuntimeError(f"final production proof could not create a canonical Code conversation: {conversation!r}")

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
        timeout=120.0,
    )
    work_specification_id = draft.get("id")
    if (
        not isinstance(work_specification_id, str)
        or draft.get("conversation_id") != conversation_id
        or draft.get("status") != "DRAFT"
        or draft.get("revision") != 1
    ):
        raise RuntimeError(f"final production proof did not create a fresh draft Work Specification: {draft!r}")

    constraints = draft.get("constraints")
    acceptance = draft.get("acceptance_criteria")
    open_questions = draft.get("open_questions")
    if not isinstance(constraints, list) or not isinstance(acceptance, list) or not acceptance:
        raise RuntimeError("final production proof Work Specification is missing bounded constraints or acceptance criteria")
    if open_questions not in ([], None):
        raise RuntimeError(f"final production proof Work Specification retained open questions: {open_questions!r}")
    combined = "\n".join(
        [str(draft.get("objective") or "")]
        + [str(item) for item in constraints]
        + [str(item) for item in acceptance]
    )
    for required in (
        PROOF_PATH,
        PROOF_TEXT,
        "REVIEW",
        "HUMAN_REQUIRED",
        "BUILD",
        "TEST",
        "VERIFY",
    ):
        if required not in combined:
            raise RuntimeError(f"final production proof Work Specification lost required scope fact {required!r}")
    lowered = combined.casefold()
    for semantic in ("only", "preserve", "fixed protected", "preview", "no merge", "production"):
        if semantic not in lowered:
            raise RuntimeError(f"final production proof Work Specification lost required semantic {semantic!r}")

    approved = _request_json(
        token=token,
        path=f"/v1/work-specifications/{work_specification_id}/approve",
        method="POST",
    )
    if (
        approved.get("id") != work_specification_id
        or approved.get("conversation_id") != conversation_id
        or approved.get("status") != "APPROVED"
        or approved.get("revision") != 1
    ):
        raise RuntimeError(f"final production proof Work Specification was not explicitly approved: {approved!r}")
    return conversation_id, spec_id, work_specification_id


def _create_fresh_plan_run(
    *,
    token: str,
    conversation_id: str,
    spec_id: str,
    work_specification_id: str,
) -> str:
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
    revision = created.get("work_specification_revision")
    criteria = created.get("acceptance_criteria")
    if (
        not isinstance(run_id, str)
        or created.get("project_id") != PROJECT_ID
        or created.get("state") != "SPECIFY"
        or created.get("revision") != 0
        or created.get("work_specification_id") != work_specification_id
        or revision != 1
        or not isinstance(digest, str)
        or len(digest) != 64
        or not isinstance(criteria, list)
        or not criteria
    ):
        raise RuntimeError(f"fresh production proof run was not created at SPECIFY revision 0: {created!r}")

    acceptance_ids: list[str] = []
    for item in criteria:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise RuntimeError(f"fresh production proof returned malformed acceptance criteria: {criteria!r}")
        acceptance_ids.append(item["id"])

    advanced = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/advance",
        method="POST",
        body={
            "stage": "SPECIFY",
            "passed": True,
            "evidence": {
                "work_specification_id": work_specification_id,
                "work_specification_revision": revision,
                "work_specification_digest": digest,
                "acceptance_ids": acceptance_ids,
            },
            "operation_key": f"bind:{run_id}:{digest}",
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
    if metadata.get("preview_status") not in {"QUEUED", "BUILDING", "READY"}:
        raise RuntimeError(f"successful SOURCE_DELIVERY Preview is terminal/non-success: {metadata!r}")

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
                    "preview_status_at_delivery": metadata["preview_status"],
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != PROOF_BRANCH:
        return
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("final production proof requires existing PARALLAX_ACCESS_TOKEN")

    conversation_id, spec_id, work_specification_id = _create_approved_proof_spec(token=token)
    run_id = _create_fresh_plan_run(
        token=token,
        conversation_id=conversation_id,
        spec_id=spec_id,
        work_specification_id=work_specification_id,
    )
    print(
        "W4 final production proof setup: PASS "
        f"(conversation={conversation_id}, work_specification={work_specification_id}, run={run_id})"
    )

    repository_root = Path(__file__).resolve().parents[3]
    proof_script = repository_root / "scripts" / "w4_release_proof.py"
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


if __name__ == "__main__":
    main()
