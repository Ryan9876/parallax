from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

import provision_wave2_vercel as helper

EXPECTED_LINK = {
    "orgId": "team_JgE8AWWz36uzRbeR6V6EWg9k",
    "projectId": "prj_4lhve1AXZntfauaGHvkuaGWC6KJX",
}


def _ensure_seeded_link(repo: Path) -> None:
    path = repo / ".vercel" / "project.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise helper.ProvisioningError("canonical Vercel project link is missing or invalid") from exc
    if payload != EXPECTED_LINK:
        raise helper.ProvisioningError("canonical Vercel project link does not match parallax-api")


def _safe_detail(text: str) -> str:
    value = re.sub(r"(?:vcp|vca)_[A-Za-z0-9._-]+", "<redacted>", text)
    value = re.sub(r"Authorization:\s*Bearer\s+\S+", "Authorization: Bearer <redacted>", value, flags=re.I)
    return " ".join(value.split())[:500]


def _run(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _team_connector_present(repo: Path) -> bool:
    """Detect a valid team-level connector before it is attached to parallax-api."""
    result = _run(repo, ["vercel", "connect", "list", "--all-projects", "--format=json"])
    text = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode == 0 and helper.CONNECTOR in text


def _token_from_json(text: str) -> str | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    def walk(value):
        if isinstance(value, dict):
            for key in ("bearerToken", "access_token", "token", "value", "secret"):
                token = value.get(key)
                if isinstance(token, str) and 8 <= len(token) <= 8192 and token.strip() == token:
                    return token
            for child in value.values():
                found = walk(child)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found:
                    return found
        return None

    return walk(payload)


def _json_token(text: str) -> str:
    token = _token_from_json(text)
    if token is None:
        raise helper.ProvisioningError("Vercel token JSON did not contain a plaintext access token")
    return token


def _probe_existing_connectors(repo: Path) -> None:
    project = "parallax-api"
    for connector in ("github/alizarin-feather", "github/alizarin-grass"):
        attach = _run(
            repo,
            ["vercel", "connect", "attach", connector, "--project", project, "--environment", "preview", "--yes"],
        )
        if attach.returncode != 0:
            detail = _safe_detail((attach.stderr or "") + " " + (attach.stdout or ""))
            print(f"CONNECT_PROBE {connector}: attach_failed: {detail or 'no diagnostic'}")
            continue

        try:
            token_result = _run(
                repo,
                ["vercel", "connect", "token", connector, "--subject", "app", "--yes", "--format=json"],
            )
            if token_result.returncode != 0:
                detail = _safe_detail((token_result.stderr or "") + " " + (token_result.stdout or ""))
                print(f"CONNECT_PROBE {connector}: token_failed: {detail or 'no diagnostic'}")
                continue

            token = _token_from_json(token_result.stdout)
            if not token:
                print(f"CONNECT_PROBE {connector}: token_missing")
                continue

            request = urllib.request.Request(
                "https://api.github.com/repos/Ryan9876/parallax",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "User-Agent": "parallax-connect-probe",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            status = 0
            body = b""
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = int(response.status)
                    body = response.read()
            except urllib.error.HTTPError as exc:
                status = int(exc.code)
                body = exc.read()

            permissions = {}
            if status == 200:
                try:
                    repo_payload = json.loads(body.decode("utf-8"))
                    if isinstance(repo_payload, dict) and isinstance(repo_payload.get("permissions"), dict):
                        permissions = repo_payload["permissions"]
                except Exception:
                    permissions = {}
            print(
                f"CONNECT_PROBE {connector}: repo_status={status} "
                f"pull={bool(permissions.get('pull'))} push={bool(permissions.get('push'))}"
            )
        finally:
            detach = _run(repo, ["vercel", "connect", "detach", connector, "--project", project, "--yes"])
            if detach.returncode != 0:
                detail = _safe_detail((detach.stderr or "") + " " + (detach.stdout or ""))
                print(f"CONNECT_PROBE {connector}: detach_failed: {detail or 'no diagnostic'}")


def main(argv: list[str] | None = None) -> int:
    helper._ensure_link = _ensure_seeded_link
    helper._connector_present = _team_connector_present
    helper._json_token = _json_token
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-dir", default="services/api")
    known, _ = parser.parse_known_args(argv)
    repo = Path(known.api_dir).resolve()
    _probe_existing_connectors(repo)
    return helper.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
