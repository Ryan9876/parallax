from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


RUN_ID = "d99ae8c6-ebc0-42bf-aaa6-da5e436eda4e"
BASE_URL = "https://parallax-api-tan.vercel.app"


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def _request_json(*, token: str, path: str, timeout: float = 60.0) -> dict[str, Any]:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed protected production target
            raw = response.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"production diagnostic GET {path} failed with HTTP {exc.code}: {raw[:500]}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"production diagnostic GET {path} returned non-object response")
    return payload


def _safe_attempt(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"malformed": True}
    evidence = item.get("evidence")
    return {
        "stage": item.get("stage"),
        "status": item.get("status"),
        "failure_code": item.get("failure_code"),
        "program_id": item.get("program_id"),
        "evidence_keys": sorted(evidence.keys()) if isinstance(evidence, dict) else [],
    }


def _safe_event(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {"malformed": True}
    lineage = item.get("source_lineage_ref")
    return {
        "sequence": item.get("sequence"),
        "event_type": item.get("event_type"),
        "stage": item.get("stage"),
        "status": item.get("status"),
        "failure_code": item.get("failure_code"),
        "has_source_lineage_ref": isinstance(lineage, str) and bool(lineage),
    }


def _diagnose() -> None:
    if (os.getenv("VERCEL_ENV") or "") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != "control/w4-production-review-proof":
        return
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("production diagnostic requires existing PARALLAX_ACCESS_TOKEN")

    run = _request_json(token=token, path=f"/v1/engineering-runs/{RUN_ID}")
    event_page = _request_json(
        token=token,
        path=f"/v1/engineering-runs/{RUN_ID}/events?after_sequence=0&limit=200",
    )
    attempts = run.get("attempts") if isinstance(run.get("attempts"), list) else []
    events = event_page.get("events") if isinstance(event_page.get("events"), list) else []
    diagnostic = {
        "gate": "Wave 4 fresh production run diagnostic",
        "run_id": RUN_ID,
        "state": run.get("state"),
        "revision": run.get("revision"),
        "last_failure_code": run.get("last_failure_code"),
        "attempts": [_safe_attempt(item) for item in attempts],
        "events": [_safe_event(item) for item in events],
        "event_count": len(events),
    }
    print(json.dumps(diagnostic, indent=2, sort_keys=True))


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_projected_source_preflight.py")
    _diagnose()
    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
