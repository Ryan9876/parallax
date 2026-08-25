#!/usr/bin/env python3
"""Wave 4 protected runtime/observability release proof.

This gate is intentionally an observer/caller, not a new execution authority. It
requires an already-authorized fresh Project-bound Engineering Run at PLAN and
invokes the production autonomous endpoint exactly once. It then verifies that
persisted observability facts prove repository/bootstrap execution advanced
beyond PLAN. It never provides provider credentials, PAT fallbacks, merge or
production-promotion behavior.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CREDENTIAL_FAILURE = "CREDENTIAL_UNAVAILABLE"
POST_PLAN_EVENT_TYPES = {"SOURCE_LINEAGE_ACCEPTED", "SOURCE_DELIVERY", "PROVIDER_RESULT", "EVALUATION_RESULT", "REVIEW_REQUIRED"}
POST_PLAN_STAGES = {"IMPLEMENT", "BUILD", "TEST", "VERIFY", "REVIEW"}


class ReleaseProofFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class HttpResult:
    status: int
    payload: Any


def _contains_credential_unavailable(value: Any) -> bool:
    try:
        encoded = json.dumps(value, sort_keys=True)
    except TypeError:
        encoded = str(value)
    return CREDENTIAL_FAILURE in encoded


def _request_json(
    *,
    base_url: str,
    path: str,
    token: str,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> HttpResult:
    url = f"{base_url.rstrip('/')}{path}"
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
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - operator-supplied protected target
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else None
            return HttpResult(status=response.status, payload=payload)
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = {"detail": raw[:1000]}
        return HttpResult(status=exc.code, payload=payload)
    except URLError as exc:
        raise ReleaseProofFailure(f"protected target is unreachable: {exc.reason}") from exc


def _require_success(result: HttpResult, *, step: str) -> Any:
    if _contains_credential_unavailable(result.payload):
        raise ReleaseProofFailure(f"{step} exposed {CREDENTIAL_FAILURE}; production readiness is blocked")
    if result.status < 200 or result.status >= 300:
        raise ReleaseProofFailure(f"{step} failed with HTTP {result.status}: {result.payload!r}")
    return result.payload


def _validate_run(run: Any, *, require_plan: bool) -> dict[str, Any]:
    if not isinstance(run, dict):
        raise ReleaseProofFailure("Engineering Run response is not an object")
    if not run.get("project_id") or run.get("project_binding_status") != "PROJECT_BOUND":
        raise ReleaseProofFailure("release proof requires a Project-bound Engineering Run")
    state = run.get("state")
    revision = run.get("revision")
    if require_plan and state != "PLAN":
        raise ReleaseProofFailure(f"release proof requires a fresh PLAN run; observed {state!r}")
    if not isinstance(revision, int) or revision < 0:
        raise ReleaseProofFailure("Engineering Run revision is invalid")
    return run


def _validate_events(payload: Any) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ReleaseProofFailure("protected observability replay did not return an event page")
    events = payload["events"]
    if not events:
        raise ReleaseProofFailure("protected observability replay returned no persisted events")
    sequences = [item.get("sequence") for item in events if isinstance(item, dict)]
    if len(sequences) != len(events) or any(not isinstance(value, int) for value in sequences):
        raise ReleaseProofFailure("persisted event sequence is malformed")
    if sequences != sorted(set(sequences)):
        raise ReleaseProofFailure(f"persisted event sequence is non-monotonic or duplicated: {sequences}")
    if _contains_credential_unavailable(events):
        raise ReleaseProofFailure(f"persisted observability contains {CREDENTIAL_FAILURE}; production readiness is blocked")

    post_plan = [
        item
        for item in events
        if isinstance(item, dict)
        and (item.get("event_type") in POST_PLAN_EVENT_TYPES or item.get("stage") in POST_PLAN_STAGES)
    ]
    if not post_plan:
        raise ReleaseProofFailure("no persisted post-PLAN runtime/provider fact was observed")

    lineage = next(
        (
            item.get("source_lineage_ref")
            for item in post_plan
            if isinstance(item.get("source_lineage_ref"), str) and item.get("source_lineage_ref")
        ),
        None,
    )
    if not lineage:
        raise ReleaseProofFailure("no accepted run-owned source lineage was projected into persisted observability")
    return events, lineage


def run_live(args: argparse.Namespace) -> dict[str, Any]:
    token = os.getenv(args.token_env)
    if not isinstance(token, str) or not token.strip():
        raise ReleaseProofFailure(f"operator credential env {args.token_env} is unavailable")
    token = token.strip()

    initial_result = _request_json(
        base_url=args.base_url,
        path=f"/v1/engineering-runs/{args.run_id}",
        token=token,
        timeout=args.timeout,
    )
    initial = _validate_run(_require_success(initial_result, step="read fresh Engineering Run"), require_plan=True)

    autonomy_result = _request_json(
        base_url=args.base_url,
        path=f"/v1/engineering-runs/{args.run_id}/autonomous",
        token=token,
        method="POST",
        body={
            "operation_key": args.operation_key,
            "expected_revision": initial["revision"],
        },
        timeout=args.timeout,
    )
    autonomy = _require_success(autonomy_result, step="real autonomous repository/runtime path")
    if not isinstance(autonomy, dict) or not isinstance(autonomy.get("run"), dict):
        raise ReleaseProofFailure("autonomous endpoint returned an invalid result")
    final_run = _validate_run(autonomy["run"], require_plan=False)
    if final_run.get("state") == "PLAN":
        raise ReleaseProofFailure("autonomous execution did not advance beyond PLAN")
    steps = autonomy.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ReleaseProofFailure("autonomous execution returned no governed execution steps")

    events_result = _request_json(
        base_url=args.base_url,
        path=f"/v1/engineering-runs/{args.run_id}/events",
        token=token,
        query={"after_sequence": 0, "limit": 200},
        timeout=args.timeout,
    )
    events, lineage = _validate_events(_require_success(events_result, step="persisted observability replay"))

    tree_result = _request_json(
        base_url=args.base_url,
        path=f"/v1/engineering-runs/{args.run_id}/source/{lineage}/tree",
        token=token,
        query={"offset": 0, "limit": 100},
        timeout=args.timeout,
    )
    tree = _require_success(tree_result, step="exact-lineage Live Build source projection")
    if not isinstance(tree, dict) or tree.get("lineage_id") != lineage:
        raise ReleaseProofFailure("Live Build source projection did not bind to the accepted exact lineage")

    evidence = {
        "gate": "W4-S5 protected runtime release proof",
        "run_id": args.run_id,
        "initial_state": initial.get("state"),
        "initial_revision": initial.get("revision"),
        "final_state": final_run.get("state"),
        "final_revision": final_run.get("revision"),
        "stop_reason": autonomy.get("stop_reason"),
        "step_count": len(steps),
        "event_count": len(events),
        "highest_sequence": events[-1].get("sequence"),
        "accepted_lineage_ref": lineage,
        "source_file_count": tree.get("file_count"),
        "credential_unavailable_absent": True,
        "protected_target": args.base_url,
    }
    target = Path(args.evidence)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return evidence


def self_test() -> dict[str, Any]:
    try:
        _require_success(HttpResult(503, {"detail": "source_bootstrap_failed result_code=CREDENTIAL_UNAVAILABLE"}), step="autonomous")
    except ReleaseProofFailure as exc:
        assert CREDENTIAL_FAILURE in str(exc)
    else:
        raise AssertionError("credential-unavailable negative case unexpectedly passed")

    valid = {
        "events": [
            {"sequence": 1, "event_type": "RUN_CREATED", "stage": None, "source_lineage_ref": None},
            {"sequence": 2, "event_type": "STAGE_RESULT", "stage": "PLAN", "source_lineage_ref": None},
            {"sequence": 3, "event_type": "SOURCE_LINEAGE_ACCEPTED", "stage": "IMPLEMENT", "source_lineage_ref": f"src:{'a' * 64}"},
        ],
        "next_after_sequence": 3,
        "has_more": False,
    }
    events, lineage = _validate_events(valid)
    assert len(events) == 3 and lineage.startswith("src:")

    for invalid in (
        {"events": []},
        {"events": [{"sequence": 2, "event_type": "SOURCE_LINEAGE_ACCEPTED", "stage": "IMPLEMENT", "source_lineage_ref": f"src:{'a' * 64}"}, {"sequence": 1, "event_type": "STAGE_RESULT", "stage": "TEST", "source_lineage_ref": None}]},
        {"events": [{"sequence": 1, "event_type": "PROVIDER_RESULT", "stage": "IMPLEMENT", "failure_code": CREDENTIAL_FAILURE, "source_lineage_ref": f"src:{'a' * 64}"}]},
    ):
        try:
            _validate_events(invalid)
        except ReleaseProofFailure:
            pass
        else:
            raise AssertionError(f"invalid release-proof event page unexpectedly passed: {invalid!r}")

    return {
        "credential_unavailable_rejected": True,
        "monotonic_persisted_events_required": True,
        "accepted_lineage_projection_required": True,
        "empty_or_invalid_observability_rejected": True,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--self-test", action="store_true", help="Run deterministic negative/positive gate contract tests without network access")
    result.add_argument("--base-url", default=os.getenv("PARALLAX_RELEASE_API_URL"), help="Authorized production-like Parallax API base URL")
    result.add_argument("--run-id", default=os.getenv("PARALLAX_RELEASE_RUN_ID"), help="Fresh Project-bound Engineering Run ID currently at PLAN")
    result.add_argument("--token-env", default="PARALLAX_RELEASE_BEARER_TOKEN", help="Environment variable containing the operator bearer token")
    result.add_argument("--operation-key", default="w4-s5-release-proof", help="Idempotent autonomous operation key")
    result.add_argument("--timeout", type=float, default=30.0)
    result.add_argument("--evidence", default="release-evidence/w4-runtime-proof.json")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.self_test:
            print(json.dumps(self_test(), indent=2, sort_keys=True))
            return 0
        if not args.base_url or not args.run_id:
            raise ReleaseProofFailure("live proof requires --base-url/PARALLAX_RELEASE_API_URL and --run-id/PARALLAX_RELEASE_RUN_ID")
        print(json.dumps(run_live(args), indent=2, sort_keys=True))
        return 0
    except (ReleaseProofFailure, AssertionError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
