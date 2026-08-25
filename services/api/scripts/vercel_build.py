from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "598b00f5-0ede-4b1c-8fc1-cd5ea9317056"
BRANCH = "control/w4-final-production-observer"
CONNECTOR = "github/parallax-runtime"
REPOSITORY = "Ryan9876/parallax"


def _json_request(request: Request, *, label: str) -> object:
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed provider endpoints only
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read(2048).decode("utf-8", errors="replace")
        raise RuntimeError(f"{label} failed HTTP {exc.code}: {raw[:500]}") from exc


def _request(token: str, path: str) -> object:
    return _json_request(
        Request(
            f"{BASE_URL}{path}",
            headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            method="GET",
        ),
        label=f"observer GET {path}",
    )


def _connect_permissions() -> dict[str, object]:
    oidc = (os.getenv("VERCEL_OIDC_TOKEN") or "").strip()
    if not oidc:
        return {"probe": "unavailable", "reason": "preview OIDC unavailable"}
    exchange = _json_request(
        Request(
            f"https://api.vercel.com/v1/connect/token/{quote(CONNECTOR, safe='')}",
            method="POST",
            data=json.dumps({"subject": {"type": "app"}}).encode("utf-8"),
            headers={"Authorization": f"Bearer {oidc}", "Content-Type": "application/json"},
        ),
        label="Vercel Connect exchange",
    )
    if not isinstance(exchange, dict) or not isinstance(exchange.get("token"), str):
        raise RuntimeError("Vercel Connect exchange returned no token")
    provider_token = exchange["token"]
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {provider_token}",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "Parallax-Read-Only-Permission-Probe",
    }
    repo = _json_request(
        Request(f"https://api.github.com/repos/{REPOSITORY}", headers=headers),
        label="GitHub repository permission probe",
    )
    installation = _json_request(
        Request("https://api.github.com/installation/repositories?per_page=2", headers=headers),
        label="GitHub installation scope probe",
    )
    permissions = repo.get("permissions") if isinstance(repo, dict) else None
    repositories = installation.get("repositories") if isinstance(installation, dict) else None
    installed_permissions = None
    if isinstance(repositories, list) and len(repositories) == 1 and isinstance(repositories[0], dict):
        installed_permissions = repositories[0].get("permissions")
    allow = {"pull", "push", "admin", "maintain", "triage"}
    return {
        "probe": "ok",
        "repository_permissions": {
            key: value for key, value in permissions.items() if key in allow
        } if isinstance(permissions, dict) else permissions,
        "installation_repository_permissions": {
            key: value for key, value in installed_permissions.items() if key in allow
        } if isinstance(installed_permissions, dict) else installed_permissions,
        "installation_total_count": installation.get("total_count") if isinstance(installation, dict) else None,
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
        events = event_page.get("events") if isinstance(event_page, dict) and isinstance(event_page.get("events"), list) else []
        print(json.dumps({
            "run_id": RUN_ID,
            "project_id": run.get("project_id") if isinstance(run, dict) else None,
            "state": run.get("state") if isinstance(run, dict) else None,
            "revision": run.get("revision") if isinstance(run, dict) else None,
            "delivery_failure": [
                {
                    "sequence": item.get("sequence"),
                    "failure_code": item.get("failure_code"),
                    "summary": item.get("summary"),
                }
                for item in events
                if isinstance(item, dict) and item.get("event_type") == "SOURCE_DELIVERY"
            ],
            "github_connect": _connect_permissions(),
        }, indent=2, sort_keys=True))
    public = Path("public")
    public.mkdir(parents=True, exist_ok=True)
    (public / "build-marker.txt").write_text("parallax-api-build\n", encoding="utf-8")


if __name__ == "__main__":
    main()
