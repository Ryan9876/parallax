from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "c5b1d060-6a2f-4500-9f0b-a137a2931296"
API_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(API_ROOT))

from parallax_api.code.source_context import BoundedSourceContextSelector, SourceContextError  # noqa: E402


def request_json(token: str, path: str, *, timeout: float = 60.0) -> Any:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"diagnostic GET {path} failed with HTTP {exc.code}: {raw[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"diagnostic GET {path} is unreachable: {exc.reason}") from exc


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "").strip().lower() != "preview":
        raise RuntimeError("W4 production diagnostic runner is preview-only")
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN") or "").strip()
    if len(token) < 32:
        raise RuntimeError("Parallax preview access credential is unavailable")

    run = request_json(token, f"/v1/engineering-runs/{RUN_ID}")
    if not isinstance(run, dict):
        raise RuntimeError("diagnostic run response is invalid")
    events = request_json(token, f"/v1/engineering-runs/{RUN_ID}/events?after_sequence=0&limit=200")
    specification = request_json(
        token,
        f"/v1/conversations/{run['conversation_id']}/work-specifications/approved",
    )
    if not isinstance(specification, dict):
        raise RuntimeError("diagnostic Work Specification response is invalid")

    attempts = []
    for item in run.get("attempts", []):
        if isinstance(item, dict):
            attempts.append({
                "stage": item.get("stage"),
                "status": item.get("status"),
                "failure_code": item.get("failure_code"),
            })
    event_rows = []
    if isinstance(events, dict):
        for item in events.get("events", []):
            if isinstance(item, dict):
                event_rows.append({
                    "sequence": item.get("sequence"),
                    "event_type": item.get("event_type"),
                    "stage": item.get("stage"),
                    "outcome": item.get("outcome"),
                    "failure_code": item.get("failure_code"),
                })

    selector_result: dict[str, Any]
    try:
        snapshot = BoundedSourceContextSelector().select(
            REPO_ROOT,
            objective=str(specification.get("objective") or ""),
            acceptance_texts=tuple(str(item) for item in specification.get("acceptance_criteria", [])),
        )
        selector_result = {
            "status": "PASS",
            "file_count": len(snapshot.files),
            "total_bytes": snapshot.total_bytes,
            "selected_paths": [item.path for item in snapshot.files],
        }
    except SourceContextError as exc:
        selector_result = {
            "status": "FAIL",
            "error_class": type(exc).__name__,
            "message": str(exc),
        }

    safe = {
        "run_id": RUN_ID,
        "state": run.get("state"),
        "revision": run.get("revision"),
        "last_failure_code": run.get("last_failure_code"),
        "attempts": attempts,
        "events": event_rows,
        "source_context_selector": selector_result,
        "work_specification": {
            "title": specification.get("title"),
            "objective": specification.get("objective"),
            "constraints": specification.get("constraints"),
            "acceptance_criteria": specification.get("acceptance_criteria"),
            "risks": specification.get("risks"),
        },
    }
    print(json.dumps(safe, indent=2, sort_keys=True))
    raise RuntimeError("diagnostic-only preview intentionally stops after sanitized state capture")


if __name__ == "__main__":
    main()
