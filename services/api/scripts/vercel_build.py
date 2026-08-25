from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "598b00f5-0ede-4b1c-8fc1-cd5ea9317056"
BRANCH = "control/w4-final-production-observer"


def _request(token: str, path: str) -> object:
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
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"observer GET {path} failed HTTP {exc.code}: {raw[:500]}") from exc


def _bounded_attempt(item: dict[str, object]) -> dict[str, object]:
    evidence = item.get("evidence")
    if not isinstance(evidence, dict):
        evidence = {}
    return {
        "stage": item.get("stage"),
        "status": item.get("status"),
        "failure_code": item.get("failure_code"),
        "operation_key": item.get("operation_key"),
        "project_ref": evidence.get("project_ref"),
        "run_id": evidence.get("run_id"),
        "source_lineage_ref": evidence.get("source_lineage_ref"),
        "base_source_lineage_ref": evidence.get("base_source_lineage_ref"),
        "lineage_bound_execution": evidence.get("lineage_bound_execution"),
        "protected_success": evidence.get("protected_success"),
        "workspace_digest": evidence.get("workspace_digest"),
    }


def _bounded_event(item: dict[str, object]) -> dict[str, object]:
    metadata = item.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    return {
        "sequence": item.get("sequence"),
        "event_type": item.get("event_type"),
        "stage": item.get("stage"),
        "status": item.get("status"),
        "failure_code": item.get("failure_code"),
        "source_lineage_ref": item.get("source_lineage_ref"),
        "evidence_ref": item.get("evidence_ref"),
        "summary": item.get("summary"),
        "metadata": metadata,
    }


def main() -> None:
    if (
        (os.getenv("VERCEL_ENV") or "") == "preview"
        and (os.getenv("VERCEL_GIT_COMMIT_REF") or "") == BRANCH
    ):
        token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
        if not token:
            raise RuntimeError("observer requires existing PARALLAX_ACCESS_TOKEN")
        run = _request(token, f"/v1/engineering-runs/{RUN_ID}")
        event_page = _request(token, f"/v1/engineering-runs/{RUN_ID}/events?after_sequence=0&limit=200")
        if not isinstance(run, dict):
            raise RuntimeError("observer run response malformed")
        attempts = run.get("attempts") if isinstance(run.get("attempts"), list) else []
        events = event_page.get("events") if isinstance(event_page, dict) and isinstance(event_page.get("events"), list) else []
        print(json.dumps({
            "run_id": RUN_ID,
            "project_id": run.get("project_id"),
            "state": run.get("state"),
            "revision": run.get("revision"),
            "last_failure_code": run.get("last_failure_code"),
            "attempts": [
                _bounded_attempt(item)
                for item in attempts if isinstance(item, dict)
            ],
            "event_count": len(events),
            "events": [
                _bounded_event(item)
                for item in events if isinstance(item, dict)
            ],
        }, indent=2, sort_keys=True))
    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
