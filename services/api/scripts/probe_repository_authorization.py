from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


_CONNECTOR = "github/parallax-runtime"
_TARGET_REPOSITORY = "Ryan9876/sickbeard"
_CONTROL_REPOSITORY = "Ryan9876/parallax"
_PERMISSIONS = ("contents:write", "metadata:read", "pull_requests:write")
_MAX_RESPONSE_BYTES = 32_768
_MAX_URL_BYTES = 4_096
_SAFE_CODE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


def _authorization_details(repository: str) -> list[dict[str, object]]:
    return [
        {
            "type": "github_app_installation",
            "repositories": [repository],
            "permissions": list(_PERMISSIONS),
        }
    ]


def _request_json(*, path: str, oidc: str, body: dict[str, object]) -> tuple[int, dict[str, object]]:
    request = Request(
        f"https://api.vercel.com{path}",
        method="POST",
        data=json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {oidc}",
            "Content-Type": "application/json",
            "User-Agent": "Parallax-W9-Repository-Authorization-Probe",
        },
    )
    status: int
    raw: bytes
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Vercel endpoint only
            status = int(response.status)
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        status = int(exc.code)
        raw = exc.read(_MAX_RESPONSE_BYTES + 1)
    except (TimeoutError, URLError) as exc:
        raise RuntimeError("Connect authorization probe failed: provider unavailable") from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise RuntimeError("Connect authorization probe returned an oversized response")
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}
    return status, payload if isinstance(payload, dict) else {}


def _error_code(payload: dict[str, object]) -> str:
    candidates: list[object] = [payload.get("code")]
    error = payload.get("error")
    if isinstance(error, dict):
        candidates.extend((error.get("code"), error.get("type")))
    elif isinstance(error, str):
        candidates.append(error)
    for value in candidates:
        if isinstance(value, str) and _SAFE_CODE.fullmatch(value):
            return value
    return "unknown"


def _safe_url_facts(value: object) -> tuple[str, str]:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > _MAX_URL_BYTES:
        raise RuntimeError("Connect authorization probe returned an invalid URL")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("Connect authorization probe returned an unsafe URL")
    if parsed.port not in {None, 443}:
        raise RuntimeError("Connect authorization probe returned an unexpected URL port")
    if parsed.fragment:
        raise RuntimeError("Connect authorization probe returned an unexpected URL fragment")
    return parsed.scheme, parsed.hostname.lower()


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    marker = os.getenv("PARALLAX_REPOSITORY_AUTHORIZATION_PROBE")
    if environment != "preview" or marker != "1":
        raise RuntimeError("repository authorization probe is preview-only and marker-gated")
    oidc = os.getenv("VERCEL_OIDC_TOKEN")
    if not isinstance(oidc, str) or not oidc.strip():
        raise RuntimeError("repository authorization probe requires Vercel OIDC")
    oidc = oidc.strip()
    connector_path = quote(_CONNECTOR, safe="")

    # Control: prove whether this preview OIDC can use the already attached connector
    # for an exact repository whose authorization is known to exist. Never print token data.
    token_status, token_payload = _request_json(
        path=f"/v1/connect/token/{connector_path}",
        oidc=oidc,
        body={
            "subject": {"type": "app"},
            "authorizationDetails": _authorization_details(_CONTROL_REPOSITORY),
        },
    )
    token_present = token_status == 200 and isinstance(token_payload.get("token"), str) and bool(token_payload.get("token"))
    token_error = _error_code(token_payload) if token_status != 200 else "none"

    authorization_status, authorization_payload = _request_json(
        path=f"/v1/connect/authorize/{connector_path}",
        oidc=oidc,
        body={
            "subject": {"type": "app"},
            "authorizationDetails": _authorization_details(_TARGET_REPOSITORY),
            "expiresInMs": 300_000,
        },
    )

    if authorization_status == 200:
        scheme, hostname = _safe_url_facts(authorization_payload.get("url"))
        request_present = isinstance(authorization_payload.get("request"), str) and bool(authorization_payload.get("request"))
        verifier_present = isinstance(authorization_payload.get("verifier"), str) and bool(authorization_payload.get("verifier"))
        expires_at = authorization_payload.get("expiresAt")
        expires_present = isinstance(expires_at, (int, float)) and not isinstance(expires_at, bool) and expires_at > 0
        connector = authorization_payload.get("connector")
        connector_uid = connector.get("uid") if isinstance(connector, dict) else None
        connector_match = connector_uid == _CONNECTOR
        if not request_present or not verifier_present or not expires_present or not connector_match:
            raise RuntimeError("Connect authorization probe response omitted required bounded evidence")
        print(
            "PARALLAX_REPOSITORY_AUTHORIZATION_PROBE "
            f"status=PASS token_http={token_status} token_present={str(token_present).lower()} token_error={token_error} "
            f"authorization_http=200 authorization_error=none scheme={scheme} host={hostname} "
            "request_present=true verifier_present=true expires_present=true connector_match=true "
            "consent_followed=false repository_mutated=false"
        )
        return

    authorization_error = _error_code(authorization_payload)
    # A failed authorization request is capability evidence, not a build-system failure.
    # Keep the preview build green so logs preserve the exact bounded classification.
    print(
        "PARALLAX_REPOSITORY_AUTHORIZATION_PROBE "
        f"status=UNAVAILABLE token_http={token_status} token_present={str(token_present).lower()} token_error={token_error} "
        f"authorization_http={authorization_status} authorization_error={authorization_error} "
        "consent_followed=false repository_mutated=false"
    )


if __name__ == "__main__":
    main()
