#!/usr/bin/env python3
"""One-shot Wave 6 production release proof.

This script is validation-only. It uses the existing protected production bearer
available to the Vercel API project, creates a fresh Engineering Run against the
already-approved disposable release-proof Project/Work Specification, exercises
the ordinary production autonomous route, verifies Wave 6 agentic evidence and
exact-lineage delivery through REVIEW, then replays the same autonomous operation
to prove no duplicate canonical mutation or Preview publication occurs.

It never prints credentials and never performs merge, production promotion,
alias/domain, environment, secret, or Project-authority mutation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
PROOF_BRANCH = "control/w6-final-production-proof"
PROJECT_ID = "b1f6984d-dc64-4220-bd51-51f6f215d175"
CONVERSATION_ID = "417a8874-140a-4d6f-9800-8f0eedb8d4f9"
WORK_SPECIFICATION_ID = "7b93c74f-8fa3-41e2-8e65-be15478e87c9"
WORK_SPECIFICATION_REVISION = 1
WORK_SPECIFICATION_DIGEST = "c3654eb1ab012da3b7a26075d30c17141c3cfd0b1c6f9a7834714bb3860baf5a"
SPEC_ID = "P2-V0.13.0"
PROOF_PATH = "apps/client/w4-final-source-delivery-proof.txt"
PROOF_TEXT = "Parallax Wave 4 final source delivery proof.\n"
ACCEPTANCE_IDS = [f"AC-{number:02d}" for number in range(1, 9)]


class ProofFailure(RuntimeError):
    pass


def _request_json(
    *,
    token: str,
    path: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    timeout: float = 900.0,
) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed protected target
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            detail = {"detail": raw[:1200]}
        raise ProofFailure(f"{method} {path} failed with HTTP {exc.code}: {detail!r}") from exc
    except URLError as exc:
        raise ProofFailure(f"protected production target is unreachable: {exc.reason}") from exc
    if not isinstance(payload, dict):
        raise ProofFailure(f"{method} {path} returned a non-object response")
    return payload


def _create_fresh_plan_run(token: str) -> dict[str, Any]:
    created = _request_json(
        token=token,
        path="/v1/engineering-runs",
        method="POST",
        body={
            "conversation_id": CONVERSATION_ID,
            "spec_id": SPEC_ID,
            "work_specification_id": WORK_SPECIFICATION_ID,
        },
    )
    run_id = created.get("id")
    if (
        not isinstance(run_id, str)
        or created.get("project_id") != PROJECT_ID
        or created.get("project_binding_status") != "PROJECT_BOUND"
        or created.get("state") != "SPECIFY"
        or created.get("revision") != 0
    ):
        raise ProofFailure(f"fresh proof run was not canonical SPECIFY revision 0: {created!r}")

    advanced = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/advance",
        method="POST",
        body={
            "stage": "SPECIFY",
            "passed": True,
            "evidence": {
                "work_specification_id": WORK_SPECIFICATION_ID,
                "work_specification_revision": WORK_SPECIFICATION_REVISION,
                "work_specification_digest": WORK_SPECIFICATION_DIGEST,
                "acceptance_ids": ACCEPTANCE_IDS,
            },
            "operation_key": f"w6-proof-bind:{run_id}:{WORK_SPECIFICATION_DIGEST}",
            "expected_revision": 0,
            "program_id": "protected-spec-binding-v0.8.0",
        },
    )
    run = advanced.get("run")
    if (
        not isinstance(run, dict)
        or run.get("id") != run_id
        or run.get("project_id") != PROJECT_ID
        or run.get("work_specification_id") != WORK_SPECIFICATION_ID
        or run.get("work_specification_digest") != WORK_SPECIFICATION_DIGEST
        or run.get("state") != "PLAN"
        or run.get("revision") != 1
    ):
        raise ProofFailure(f"fresh proof run did not bind the exact approved specification at PLAN: {advanced!r}")
    return run


def _attempt(run: dict[str, Any], stage: str) -> dict[str, Any]:
    attempts = run.get("attempts")
    if not isinstance(attempts, list):
        raise ProofFailure("Engineering Run returned no attempt history")
    matches = [item for item in attempts if isinstance(item, dict) and item.get("stage") == stage]
    passed = [item for item in matches if item.get("status") == "PASSED"]
    if len(passed) != 1 or len(matches) != 1:
        raise ProofFailure(f"fresh proof expected exactly one passed {stage} attempt; observed {matches!r}")
    return passed[0]


def _assert_agentic_attempts(run: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    plan = _attempt(run, "PLAN")
    plan_evidence = plan.get("evidence")
    if not isinstance(plan_evidence, dict):
        raise ProofFailure("PLAN evidence is unavailable")
    if plan_evidence.get("decision_kind") != "SERVER_OWNED_AGENTIC_PLAN":
        raise ProofFailure(f"PLAN did not use the Wave 6 server-owned agentic planner: {plan_evidence!r}")
    if plan_evidence.get("canonical_source_writer_count") != 1:
        raise ProofFailure("Wave 6 PLAN did not preserve the single canonical source writer")
    if plan_evidence.get("operator_selected_agents") is not False:
        raise ProofFailure("Wave 6 PLAN incorrectly reports operator-selected agents")
    selected_agent_count = plan_evidence.get("selected_agent_count")
    if not isinstance(selected_agent_count, int) or selected_agent_count < 1:
        raise ProofFailure("Wave 6 PLAN did not select a bounded agent team")
    if sorted(plan_evidence.get("acceptance_ids_covered") or []) != ACCEPTANCE_IDS:
        raise ProofFailure("Wave 6 PLAN evidence does not cover the exact accepted criteria")

    implement = _attempt(run, "IMPLEMENT")
    implement_evidence = implement.get("evidence")
    if not isinstance(implement_evidence, dict):
        raise ProofFailure("IMPLEMENT evidence is unavailable")
    lineage = implement_evidence.get("source_lineage_ref")
    if not isinstance(lineage, str) or not lineage.startswith("src:") or len(lineage) != 68:
        raise ProofFailure("IMPLEMENT did not persist an exact accepted source lineage")
    controller = implement_evidence.get("controller_evidence")
    if not isinstance(controller, dict):
        raise ProofFailure("IMPLEMENT does not contain bounded Wave 6 controller evidence")
    selected_candidate = controller.get("selected_candidate_id")
    proposal_digest = controller.get("selected_proposal_digest")
    if not isinstance(selected_candidate, str) or not selected_candidate:
        raise ProofFailure("Wave 6 controller evidence lacks selected candidate identity")
    if not isinstance(proposal_digest, str) or len(proposal_digest) != 64:
        raise ProofFailure("Wave 6 controller evidence lacks selected proposal digest")
    for key in (
        "source_lineage_accepted",
        "engineering_run_transitioned",
        "review_completed",
        "production_deployed",
    ):
        if controller.get(key) is not False:
            raise ProofFailure(f"Wave 6 candidate evidence asserted forbidden authority: {key}")

    for stage in ("BUILD", "TEST", "VERIFY"):
        attempt = _attempt(run, stage)
        evidence = attempt.get("evidence")
        if not isinstance(evidence, dict):
            raise ProofFailure(f"{stage} evidence is unavailable")
        if evidence.get("source_lineage_ref") != lineage:
            raise ProofFailure(f"{stage} did not execute against exact IMPLEMENT lineage")
        if evidence.get("exit_code") != 0 or evidence.get("protected_success") is not True:
            raise ProofFailure(f"{stage} did not persist protected success evidence")

    return lineage, selected_candidate, controller


def _events(token: str, run_id: str) -> list[dict[str, Any]]:
    payload = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/events",
        query={"after_sequence": 0, "limit": 200},
    )
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        raise ProofFailure("production proof has no persisted run-event evidence")
    if payload.get("has_more") is True:
        raise ProofFailure("production proof exceeded the bounded event page")
    sequences = [event.get("sequence") for event in events if isinstance(event, dict)]
    if len(sequences) != len(events) or sequences != sorted(set(sequences)):
        raise ProofFailure("production proof run-event sequence is malformed")
    return events


def _delivery_identity(events: list[dict[str, Any]], lineage: str) -> dict[str, Any]:
    deliveries = [
        event for event in events
        if event.get("event_type") == "SOURCE_DELIVERY" and event.get("outcome") == "SUCCEEDED"
    ]
    if len(deliveries) != 1:
        raise ProofFailure(f"expected exactly one successful source-delivery event; observed {deliveries!r}")
    event = deliveries[0]
    if event.get("stage") != "REVIEW" or event.get("source_lineage_ref") != lineage:
        raise ProofFailure("source delivery is not bound to REVIEW and the exact accepted lineage")
    metadata = event.get("metadata")
    if not isinstance(metadata, dict):
        raise ProofFailure("source-delivery metadata is unavailable")
    identity = {
        key: metadata.get(key)
        for key in (
            "content_digest",
            "branch_name",
            "commit_revision",
            "pull_request_number",
            "preview_deployment_id",
            "preview_status",
        )
    }
    for key in ("content_digest", "branch_name", "commit_revision", "preview_deployment_id"):
        if not isinstance(identity[key], str) or not identity[key]:
            raise ProofFailure(f"source-delivery identity is missing {key}")
    if not isinstance(identity["pull_request_number"], int) or identity["pull_request_number"] < 1:
        raise ProofFailure("source-delivery identity is missing pull_request_number")
    if identity["preview_status"] != "READY":
        raise ProofFailure(f"bounded Preview is not READY: {identity['preview_status']!r}")
    return identity


def _assert_exact_mutation(token: str, run_id: str, lineage: str) -> str:
    tree = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/source/{lineage}/tree",
        query={"offset": 0, "limit": 100},
    )
    if tree.get("lineage_id") != lineage or tree.get("project_id") != PROJECT_ID:
        raise ProofFailure("accepted source tree drifted from canonical Project/run lineage")
    parent = tree.get("parent_lineage_id")
    if not isinstance(parent, str) or not parent.startswith("src:"):
        raise ProofFailure("accepted implementation lineage lacks exact parent lineage")

    source_file = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/source/{lineage}/file",
        query={"path": PROOF_PATH},
    )
    if source_file.get("availability") != "TEXT" or source_file.get("text") != PROOF_TEXT:
        raise ProofFailure(f"proof file bytes are not exact: {source_file!r}")

    diff = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/source-diff",
        query={"from_lineage": parent, "to_lineage": lineage},
    )
    files = diff.get("files")
    if diff.get("changed_count") != 1 or not isinstance(files, list) or len(files) != 1:
        raise ProofFailure(f"accepted lineage contains more than the one approved mutation: {diff!r}")
    item = files[0]
    if not isinstance(item, dict) or item.get("path") != PROOF_PATH or item.get("change_type") != "ADDED":
        raise ProofFailure(f"accepted lineage mutation is not the approved proof file: {files!r}")
    return parent


def _worker_health(token: str, run_id: str) -> dict[str, Any]:
    return _request_json(token=token, path=f"/v1/engineering-runs/{run_id}/worker-health")


def _bounded_event_signature(events: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (
            event.get("sequence"),
            event.get("event_key"),
            event.get("event_type"),
            event.get("outcome"),
            event.get("source_lineage_ref"),
            event.get("evidence_ref"),
        )
        for event in events
    ]


def run_proof() -> dict[str, Any]:
    if (os.getenv("VERCEL_ENV") or "") != "preview":
        raise ProofFailure("Wave 6 final production proof is preview-only")
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != PROOF_BRANCH:
        raise ProofFailure("Wave 6 final production proof may run only on its validation branch")
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise ProofFailure("existing protected PARALLAX_ACCESS_TOKEN is unavailable")

    initial = _create_fresh_plan_run(token)
    run_id = initial["id"]
    operation_key = f"w6-final-production-proof:{run_id}"

    first = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/autonomous",
        method="POST",
        body={"operation_key": operation_key, "expected_revision": initial["revision"]},
    )
    first_run = first.get("run")
    if (
        not isinstance(first_run, dict)
        or first_run.get("state") != "REVIEW"
        or first.get("stop_reason") != "REVIEW_REQUIRED"
        or first_run.get("last_failure_code") is not None
    ):
        raise ProofFailure(f"Wave 6 production run did not stop cleanly at REVIEW: {first!r}")
    steps = first.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ProofFailure("Wave 6 production run returned no governed execution steps")

    lineage, selected_candidate, controller = _assert_agentic_attempts(first_run)
    parent_lineage = _assert_exact_mutation(token, run_id, lineage)
    first_events = _events(token, run_id)
    first_delivery = _delivery_identity(first_events, lineage)
    first_health = _worker_health(token, run_id)
    if first_health.get("project_id") != PROJECT_ID or first_health.get("run_id") != run_id:
        raise ProofFailure("durable worker health is not Project/run bound")
    if first_health.get("human_required") is True:
        raise ProofFailure("durable worker unexpectedly requires human recovery before REVIEW")

    first_revision = first_run.get("revision")
    first_attempt_count = len(first_run.get("attempts") or [])
    event_signature = _bounded_event_signature(first_events)

    replay = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{run_id}/autonomous",
        method="POST",
        body={"operation_key": operation_key, "expected_revision": first_revision},
    )
    replay_run = replay.get("run")
    if (
        not isinstance(replay_run, dict)
        or replay_run.get("state") != "REVIEW"
        or replay.get("stop_reason") != "REVIEW_REQUIRED"
        or replay_run.get("revision") != first_revision
        or replay.get("steps") != []
    ):
        raise ProofFailure(f"REVIEW replay was not a stable terminal replay: {replay!r}")
    if len(replay_run.get("attempts") or []) != first_attempt_count:
        raise ProofFailure("REVIEW replay created a duplicate protected attempt")

    replay_events = _events(token, run_id)
    replay_delivery = _delivery_identity(replay_events, lineage)
    if _bounded_event_signature(replay_events) != event_signature:
        raise ProofFailure("REVIEW replay created or changed persisted run-event evidence")
    if replay_delivery != first_delivery:
        raise ProofFailure("REVIEW replay changed GitHub/Preview delivery identity")
    replay_health = _worker_health(token, run_id)
    for key in (
        "execution_id",
        "lease_generation",
        "state",
        "current_step",
        "source_lineage_ref",
        "last_known_good_lineage_ref",
        "checkpoint_revision",
    ):
        if replay_health.get(key) != first_health.get(key):
            raise ProofFailure(f"REVIEW replay changed durable worker identity at {key}")

    evidence = {
        "gate": "Wave 6 final authenticated production proof",
        "run_id": run_id,
        "project_id": PROJECT_ID,
        "work_specification_id": WORK_SPECIFICATION_ID,
        "final_state": "REVIEW",
        "stop_reason": "REVIEW_REQUIRED",
        "final_revision": first_revision,
        "accepted_lineage_ref": lineage,
        "parent_lineage_ref": parent_lineage,
        "selected_candidate_id": selected_candidate,
        "selected_proposal_digest": controller.get("selected_proposal_digest"),
        "candidate_authority_claims_false": True,
        "exact_mutation_path": PROOF_PATH,
        "protected_stages_passed": ["PLAN", "IMPLEMENT", "BUILD", "TEST", "VERIFY"],
        "delivery": first_delivery,
        "event_count": len(first_events),
        "worker_execution_id": first_health.get("execution_id"),
        "worker_lease_generation": first_health.get("lease_generation"),
        "worker_state": first_health.get("state"),
        "replay_revision_stable": True,
        "replay_attempt_count_stable": True,
        "replay_event_identity_stable": True,
        "replay_delivery_identity_stable": True,
        "replay_worker_identity_stable": True,
        "production_merge_or_promotion_performed": False,
    }
    target = Path("/tmp/w6-final-production-proof.json")
    target.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def main() -> int:
    try:
        print(json.dumps(run_proof(), indent=2, sort_keys=True))
        return 0
    except (ProofFailure, AssertionError, ValueError, KeyError) as exc:
        print(f"Wave 6 final production proof: FAIL — {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
