from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
REPOSITORY_REF = "github:Ryan9876/parallax"
PROJECT_NAME = "Wave 4 Production Release Proof"
OBJECTIVE = (
    "Production release proof only. Create one candidate-lineage text file at "
    "release-proof/w4-production-runtime-proof.txt containing exactly "
    "'Parallax Wave 4 production runtime proof.' Preserve all existing files, "
    "do not broaden tool/provider authority, do not merge or publish production, "
    "and stop at the governed REVIEW boundary after BUILD, TEST, and VERIFY evidence is recorded."
)


def request_json(token: str, path: str, *, method: str = "GET", body: dict[str, Any] | None = None, timeout: float = 120.0) -> Any:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            detail = raw[:1000]
        raise RuntimeError(f"production API {method} {path} failed with HTTP {exc.code}: {detail!r}") from exc
    except URLError as exc:
        raise RuntimeError(f"production API {method} {path} is unreachable: {exc.reason}") from exc


def ensure_project(token: str) -> dict[str, Any]:
    projects = request_json(token, "/v1/projects")
    if not isinstance(projects, list):
        raise RuntimeError("production Project list is invalid")
    for project in projects:
        if isinstance(project, dict) and project.get("repository_ref") == REPOSITORY_REF:
            return project
    project = request_json(
        token,
        "/v1/projects",
        method="POST",
        body={
            "name": PROJECT_NAME,
            "description": "Disposable owner-scoped Project used only for the governed Wave 4 production runtime recovery proof.",
            "repository_ref": REPOSITORY_REF,
        },
    )
    if not isinstance(project, dict) or not project.get("id"):
        raise RuntimeError("production proof Project creation returned an invalid response")
    return project


def create_plan_run(token: str, project: dict[str, Any]) -> dict[str, Any]:
    conversation = request_json(
        token,
        "/v1/conversations",
        method="POST",
        body={"mode": "code", "project_id": project["id"]},
    )
    if not isinstance(conversation, dict) or not conversation.get("id"):
        raise RuntimeError("production proof Code conversation creation failed")
    conversation_id = str(conversation["id"])

    request_json(
        token,
        f"/v1/conversations/{conversation_id}/messages",
        method="POST",
        body={"role": "user", "content": OBJECTIVE},
    )
    draft = request_json(
        token,
        f"/v1/conversations/{conversation_id}/work-specifications/draft",
        method="POST",
        timeout=180.0,
    )
    if not isinstance(draft, dict) or not draft.get("id") or draft.get("status") != "DRAFT":
        raise RuntimeError("production proof Work Specification draft is invalid")
    approved = request_json(
        token,
        f"/v1/work-specifications/{draft['id']}/approve",
        method="POST",
    )
    if not isinstance(approved, dict) or approved.get("status") != "APPROVED":
        raise RuntimeError("production proof Work Specification was not approved")

    run = request_json(
        token,
        "/v1/engineering-runs/activate",
        method="POST",
        body={"conversation_id": conversation_id, "work_specification_id": approved["id"]},
    )
    if not isinstance(run, dict) or not run.get("id"):
        raise RuntimeError("production proof Engineering Run activation returned an invalid response")
    if run.get("project_id") != project.get("id") or run.get("project_binding_status") != "PROJECT_BOUND":
        raise RuntimeError("production proof Engineering Run lost canonical Project binding")
    if run.get("state") != "PLAN":
        raise RuntimeError(f"production proof Engineering Run must activate at PLAN; observed {run.get('state')!r}")
    return run


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "").strip().lower() != "preview":
        raise RuntimeError("W4 production proof runner is preview-only")

    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN") or "").strip()
    if len(token) < 32:
        raise RuntimeError("Parallax preview access credential is unavailable")

    repo_root = Path(__file__).resolve().parents[3]
    proof = repo_root / "scripts" / "w4_release_proof.py"
    if not proof.is_file():
        raise RuntimeError("W4 release proof script is unavailable")

    project = ensure_project(token)
    run = create_plan_run(token, project)

    env = os.environ.copy()
    env["PARALLAX_RELEASE_BEARER_TOKEN"] = token
    env["PARALLAX_RELEASE_API_URL"] = BASE_URL
    env["PARALLAX_RELEASE_RUN_ID"] = str(run["id"])

    subprocess.run(
        [
            sys.executable,
            str(proof),
            "--operation-key",
            f"w4-production-recovery-proof-{run['id']}",
            "--timeout",
            "180",
            "--evidence",
            str(repo_root / "release-evidence" / "w4-production-runtime-proof.json"),
        ],
        cwd=repo_root,
        env=env,
        check=True,
    )
    print(f"W4 production runtime proof: PASS (run_id={run['id']})")


if __name__ == "__main__":
    main()
