from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


_ENV_TARGETS = "PARALLAX_VERCEL_PREVIEW_TARGETS_JSON"
_ENV_OIDC = "VERCEL_OIDC_TOKEN"
_GITHUB_API_VERSION = "2026-03-10"
_GITHUB_CONNECTOR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_REPOSITORY = re.compile(r"^github:([^/\s]+)/([^/\s]+)$")
_REQUIRED_PERMISSIONS = ("contents:write", "metadata:read", "pull_requests:write")
_MAX_TARGETS = 64


def _bounded_http_error(exc: HTTPError) -> str:
    try:
        raw = exc.read(4096).decode("utf-8", errors="replace")
        payload = json.loads(raw)
    except Exception:
        return f"HTTP {exc.code}"
    if not isinstance(payload, dict):
        return f"HTTP {exc.code}"
    error = payload.get("error")
    message = payload.get("message")
    details: list[str] = []
    if isinstance(error, dict):
        for key in ("code", "message"):
            value = error.get(key)
            if isinstance(value, str) and value:
                details.append(value[:160])
    elif isinstance(error, str) and error:
        details.append(error[:160])
    if isinstance(message, str) and message:
        details.append(message[:160])
    suffix = " | ".join(details[:3])
    return f"HTTP {exc.code}" + (f": {suffix}" if suffix else "")


def _json_request(request: Request, *, label: str) -> tuple[object, object]:
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed provider endpoints only
            raw = response.read()
            headers = response.headers
    except HTTPError as exc:
        raise RuntimeError(f"{label} failed: {_bounded_http_error(exc)}") from exc
    except (TimeoutError, URLError) as exc:
        raise RuntimeError(f"{label} failed: network unavailable") from exc
    try:
        return json.loads(raw), headers
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned invalid JSON") from exc


def _targets(raw: str | None) -> tuple[dict[str, object], ...]:
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("production provider target registry is unavailable")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("production provider target registry is invalid JSON") from exc
    if not isinstance(payload, list) or not 1 <= len(payload) <= _MAX_TARGETS:
        raise RuntimeError("production provider target registry must be bounded and non-empty")
    targets: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise RuntimeError("production provider target registry contains a non-object entry")
        repository_ref = item.get("repository_ref")
        connector = item.get("github_connector")
        repo_id = item.get("github_repo_id")
        if not isinstance(repository_ref, str) or _REPOSITORY.fullmatch(repository_ref) is None:
            raise RuntimeError("production provider target has invalid GitHub repository identity")
        if not isinstance(connector, str) or _GITHUB_CONNECTOR.fullmatch(connector) is None:
            raise RuntimeError("production provider target has invalid GitHub Connect identity")
        if not isinstance(repo_id, int) or isinstance(repo_id, bool) or repo_id <= 0:
            raise RuntimeError("production provider target has invalid GitHub repository id")
        key = repository_ref.casefold()
        if key in seen:
            raise RuntimeError("production provider target registry contains duplicate repositories")
        seen.add(key)
        targets.append(item)
    return tuple(targets)


def _authorization_details(repository: str) -> list[dict[str, object]]:
    return [
        {
            "type": "github_app_installation",
            "repositories": [repository],
            "permissions": list(_REQUIRED_PERMISSIONS),
        }
    ]


def _preflight_target(target: dict[str, object], *, oidc: str) -> None:
    repository_ref = target["repository_ref"]
    connector = target["github_connector"]
    repo_id = target["github_repo_id"]
    assert isinstance(repository_ref, str)
    assert isinstance(connector, str)
    assert isinstance(repo_id, int)
    match = _REPOSITORY.fullmatch(repository_ref)
    assert match is not None
    owner, repo = match.group(1), match.group(2)
    repository = f"{owner}/{repo}"

    exchange, _ = _json_request(
        Request(
            f"https://api.vercel.com/v1/connect/token/{quote(connector, safe='')}",
            method="POST",
            data=json.dumps(
                {
                    "subject": {"type": "app"},
                    "authorizationDetails": _authorization_details(repository),
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {oidc}",
                "Content-Type": "application/json",
            },
        ),
        label="Vercel Connect scoped delivery credential preflight",
    )
    if not isinstance(exchange, dict):
        raise RuntimeError("Vercel Connect scoped delivery credential preflight returned invalid payload")
    token = exchange.get("token")
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError("Vercel Connect scoped delivery credential preflight returned no provider token")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token.strip()}",
        "X-GitHub-Api-Version": _GITHUB_API_VERSION,
        "User-Agent": "Parallax-Production-Delivery-Permission-Preflight",
    }
    scope, _ = _json_request(
        Request("https://api.github.com/installation/repositories?per_page=2", headers=headers),
        label="GitHub scoped installation preflight",
    )
    repositories = scope.get("repositories") if isinstance(scope, dict) else None
    if (
        not isinstance(scope, dict)
        or scope.get("total_count") != 1
        or not isinstance(repositories, list)
        or len(repositories) != 1
    ):
        raise RuntimeError("GitHub scoped installation is not exactly one repository")
    installed = repositories[0]
    full_name = installed.get("full_name") if isinstance(installed, dict) else None
    if not isinstance(full_name, str) or full_name.casefold() != repository.casefold():
        raise RuntimeError("GitHub scoped installation does not match registered repository")

    repository_payload, _ = _json_request(
        Request(f"https://api.github.com/repos/{quote(owner, safe='')}/{quote(repo, safe='')}", headers=headers),
        label="GitHub scoped repository identity preflight",
    )
    if not isinstance(repository_payload, dict) or repository_payload.get("id") != repo_id:
        raise RuntimeError("GitHub scoped repository numeric identity mismatch")
    permissions = repository_payload.get("permissions")
    if isinstance(permissions, dict) and permissions.get("push") is not True:
        raise RuntimeError("GitHub scoped delivery credential does not expose repository write capability")


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production delivery permission preflight: SKIP "
            f"(VERCEL_ENV={environment}; provider mutation authority remains production-only)"
        )
        return
    oidc = os.getenv(_ENV_OIDC)
    if not isinstance(oidc, str) or not oidc.strip():
        raise RuntimeError("production Vercel OIDC credential is unavailable")
    targets = _targets(os.getenv(_ENV_TARGETS))
    for target in targets:
        _preflight_target(target, oidc=oidc.strip())
    print(
        "Production delivery permission preflight: PASS "
        f"({len(targets)} exact repository target(s); scoped contents/pull-request write credential verified)"
    )


if __name__ == "__main__":
    main()
