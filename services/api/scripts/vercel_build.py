from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
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


def _get_json(*, base_url: str, token: str, path: str, query: dict[str, Any] | None = None) -> Any:
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"
    request = Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed protected production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"production diagnostic GET {path} failed with HTTP {exc.code}: {raw[:500]}") from exc


def _run_preview_diagnostic() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != "control/w4-source-context-hotfix":
        return

    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("preview diagnostic requires existing PARALLAX_ACCESS_TOKEN")

    base_url = "https://parallax-api-tan.vercel.app"
    run_id = "3720afc8-3109-456e-895d-f4e81fd16a44"
    run = _get_json(base_url=base_url, token=token, path=f"/v1/engineering-runs/{run_id}")
    events_payload = _get_json(
        base_url=base_url,
        token=token,
        path=f"/v1/engineering-runs/{run_id}/events",
        query={"after_sequence": 0, "limit": 200},
    )
    if not isinstance(run, dict):
        raise RuntimeError("production diagnostic run response is invalid")
    attempts = run.get("attempts") if isinstance(run.get("attempts"), list) else []
    safe_attempts: list[dict[str, Any]] = []
    safe_evidence_fields = {
        "source_context_file_count",
        "source_context_total_bytes",
        "patch_count",
        "protected_stage_authority",
        "external_execution",
        "network_mutation",
        "git_mutation",
        "deployment_mutation",
        "lineage_bound_execution",
        "protected_success",
        "exit_code",
        "timed_out",
        "redacted",
    }
    for item in attempts:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        safe_attempts.append(
            {
                "stage": item.get("stage"),
                "status": item.get("status"),
                "failure_code": item.get("failure_code"),
                "evidence_keys": sorted(str(key) for key in evidence.keys()),
                "safe_evidence": {key: evidence.get(key) for key in sorted(safe_evidence_fields) if key in evidence},
            }
        )

    raw_events = events_payload.get("events") if isinstance(events_payload, dict) and isinstance(events_payload.get("events"), list) else []
    safe_events: list[dict[str, Any]] = []
    for item in raw_events:
        if not isinstance(item, dict):
            continue
        safe_events.append(
            {
                "sequence": item.get("sequence"),
                "event_type": item.get("event_type"),
                "stage": item.get("stage"),
                "outcome": item.get("outcome"),
                "subsystem": item.get("subsystem"),
                "failure_code": item.get("failure_code"),
                "source_lineage_ref": item.get("source_lineage_ref"),
                "evidence_ref": item.get("evidence_ref"),
            }
        )

    result = {
        "run_id": run_id,
        "state": run.get("state"),
        "revision": run.get("revision"),
        "resume_stage": run.get("resume_stage"),
        "last_failure_code": run.get("last_failure_code"),
        "attempts": safe_attempts,
        "events": safe_events,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    raise RuntimeError("diagnostic-only preview stops intentionally after sanitized run/event snapshot")


def main() -> None:
    _run("scripts/production_provider_preflight.py")
    _run("scripts/production_projected_source_preflight.py")

    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        _run_isolated_preflight("scripts/production_lineage_composition_preflight.py")
        _run_isolated_preflight("scripts/production_projected_bootstrap_preflight.py")
        _run_isolated_preflight("scripts/production_run_event_schema_guard.py")
    else:
        print("Production lineage composition preflight: SKIP (non-production)")
        print("Production projected bootstrap preflight: SKIP (non-production)")
        print("Production run-event schema guard: SKIP (non-production)")

    _run_preview_diagnostic()

    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
