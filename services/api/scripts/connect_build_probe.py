from __future__ import annotations

import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONNECT_URL = "https://api.vercel.com/v1/connect/token/github%2Fparallax-runtime"
REPOSITORY_URL = "https://api.github.com/repos/Ryan9876/parallax"
SCOPE_URL = "https://api.github.com/installation/repositories?per_page=2"
GITHUB_API_VERSION = "2026-03-10"


def _bounded_http_error(exc: HTTPError) -> str:
    try:
        raw = exc.read(4096).decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except Exception:
        return f"HTTP {exc.code}"
    if not isinstance(payload, dict):
        return f"HTTP {exc.code}"
    candidates: list[str] = []
    for key in ("code", "message", "error"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            candidates.append(value[:240])
        elif isinstance(value, dict):
            for nested in ("code", "message"):
                nested_value = value.get(nested)
                if isinstance(nested_value, str) and nested_value:
                    candidates.append(nested_value[:240])
    detail = " | ".join(candidates[:3])
    return f"HTTP {exc.code}" + (f": {detail}" if detail else "")


def _json_request(request: Request) -> object:
    try:
        with urlopen(request, timeout=20) as response:
            payload = response.read()
    except HTTPError as exc:
        raise RuntimeError(_bounded_http_error(exc)) from exc
    except URLError as exc:
        raise RuntimeError("provider preflight network failure") from exc
    return json.loads(payload)


def main() -> None:
    if os.getenv("VERCEL_ENV") != "preview":
        print("Connect build preflight skipped outside Preview")
        return

    oidc = os.getenv("VERCEL_OIDC_TOKEN")
    if not oidc:
        raise RuntimeError("VERCEL_OIDC_TOKEN unavailable during Preview build")

    connect_payload = _json_request(
        Request(
            CONNECT_URL,
            method="POST",
            data=json.dumps({"subject": {"type": "app"}}).encode(),
            headers={
                "Authorization": f"Bearer {oidc}",
                "Content-Type": "application/json",
            },
        )
    )
    if not isinstance(connect_payload, dict):
        raise RuntimeError("Connect preflight returned invalid payload")
    provider_token = connect_payload.get("token")
    if not isinstance(provider_token, str) or not provider_token:
        raise RuntimeError("Connect preflight returned no provider token")

    github_headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {provider_token}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
        "User-Agent": "Parallax-Preview-Provider-Preflight",
    }
    scope_payload = _json_request(Request(SCOPE_URL, headers=github_headers))
    if not isinstance(scope_payload, dict):
        raise RuntimeError("GitHub scope preflight returned invalid payload")
    repositories = scope_payload.get("repositories")
    if scope_payload.get("total_count") != 1 or not isinstance(repositories, list) or len(repositories) != 1:
        raise RuntimeError("GitHub installation scope is not exactly one repository")
    full_name = repositories[0].get("full_name") if isinstance(repositories[0], dict) else None
    if not isinstance(full_name, str) or full_name.casefold() != "ryan9876/parallax":
        raise RuntimeError("GitHub installation scope does not match Parallax")

    repository_payload = _json_request(Request(REPOSITORY_URL, headers=github_headers))
    if not isinstance(repository_payload, dict):
        raise RuntimeError("GitHub repository preflight returned invalid payload")
    if repository_payload.get("id") != 1340272514:
        raise RuntimeError("GitHub repository identity mismatch")
    if repository_payload.get("default_branch") != "main":
        raise RuntimeError("GitHub repository default branch mismatch")

    print("Vercel OIDC -> Connect -> exact GitHub installation/repository preflight: PASS")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Connect build preflight failed: {exc}", file=sys.stderr)
        raise
