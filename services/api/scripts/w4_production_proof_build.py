from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "c5b1d060-6a2f-4500-9f0b-a137a2931296"


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
    events = request_json(token, f"/v1/engineering-runs/{RUN_ID}/events?after_sequence=0&limit=200")
    attempts = []
    if isinstance(run, dict):
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

    safe = {
        "run_id": RUN_ID,
        "state": run.get("state") if isinstance(run, dict) else None,
        "revision": run.get("revision") if isinstance(run, dict) else None,
        "last_failure_code": run.get("last_failure_code") if isinstance(run, dict) else None,
        "attempts": attempts,
        "events": event_rows,
    }
    print(json.dumps(safe, indent=2, sort_keys=True))
    raise RuntimeError("diagnostic-only preview intentionally stops after sanitized state capture")


if __name__ == "__main__":
    main()
