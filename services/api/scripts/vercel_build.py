from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
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


def _get_json(*, base_url: str, token: str, path: str, query: dict[str, object] | None = None):
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
        raise RuntimeError(f"diagnostic GET {path} failed with HTTP {exc.code}: {raw[:500]}") from exc


def _run_preview_diagnostic() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "preview":
        return
    if (os.getenv("VERCEL_GIT_COMMIT_REF") or "") != "control/w4-final-run-diagnostic":
        return
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("preview run diagnostic requires existing PARALLAX_ACCESS_TOKEN")

    base_url = "https://parallax-api-tan.vercel.app"
    run_id = "b4b64e2d-f9a8-4601-9070-0ebe0c2165ae"
    run = _get_json(base_url=base_url, token=token, path=f"/v1/engineering-runs/{run_id}")
    events_page = _get_json(
        base_url=base_url,
        token=token,
        path=f"/v1/engineering-runs/{run_id}/events",
        query={"after_sequence": 0, "limit": 200},
    )
    if not isinstance(run, dict):
        raise RuntimeError("run diagnostic returned non-object run")

    safe_attempts = []
    for attempt in run.get("attempts") or []:
        if not isinstance(attempt, dict):
            continue
        evidence = attempt.get("evidence") if isinstance(attempt.get("evidence"), dict) else {}
        safe_attempts.append(
            {
                "stage": attempt.get("stage"),
                "status": attempt.get("status"),
                "failure_code": attempt.get("failure_code"),
                "model_id": attempt.get("model_id"),
                "tool_id": attempt.get("tool_id"),
                "evidence": {
                    key: evidence.get(key)
                    for key in (
                        "tool_id",
                        "exit_code",
                        "duration_ms",
                        "stdout_excerpt",
                        "stderr_excerpt",
                        "timed_out",
                        "redacted",
                        "protected_success",
                        "executor",
                        "network_policy",
                        "source_context_file_count",
                        "source_context_total_bytes",
                        "patch_count",
                        "source_lineage_ref",
                        "base_source_lineage_ref",
                        "lineage_bound_execution",
                    )
                    if key in evidence
                },
            }
        )

    safe_events = []
    raw_events = events_page.get("events") if isinstance(events_page, dict) else []
    for event in raw_events or []:
        if not isinstance(event, dict):
            continue
        safe_events.append(
            {
                "sequence": event.get("sequence"),
                "event_type": event.get("event_type"),
                "stage": event.get("stage"),
                "outcome": event.get("outcome"),
                "subsystem": event.get("subsystem"),
                "failure_code": event.get("failure_code"),
                "source_lineage_ref": event.get("source_lineage_ref"),
                "evidence_ref": event.get("evidence_ref"),
                "summary": event.get("summary"),
            }
        )

    print(
        json.dumps(
            {
                "run_id": run_id,
                "state": run.get("state"),
                "revision": run.get("revision"),
                "resume_stage": run.get("resume_stage"),
                "last_failure_code": run.get("last_failure_code"),
                "attempts": safe_attempts,
                "events": safe_events,
            },
            indent=2,
            sort_keys=True,
        )
    )
    raise RuntimeError("diagnostic-only preview stops intentionally")


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
