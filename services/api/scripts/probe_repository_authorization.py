from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen


_CONNECTOR = "github/parallax-runtime"
_REPOSITORY = "Ryan9876/sickbeard"
_PERMISSIONS = ("contents:write", "metadata:read", "pull_requests:write")
_MAX_RESPONSE_BYTES = 32_768
_MAX_URL_BYTES = 4_096


def _request_authorization(oidc: str) -> dict[str, object]:
    body = {
        "subject": {"type": "app"},
        "authorizationDetails": [
            {
                "type": "github_app_installation",
                "repositories": [_REPOSITORY],
                "permissions": list(_PERMISSIONS),
            }
        ],
        "expiresInMs": 300_000,
    }
    request = Request(
        f"https://api.vercel.com/v1/connect/authorize/{quote(_CONNECTOR, safe='')}",
        method="POST",
        data=json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {oidc}",
            "Content-Type": "application/json",
            "User-Agent": "Parallax-W9-Repository-Authorization-Probe",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310 - fixed Vercel endpoint only
            raw = response.read(_MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        raise RuntimeError(f"Connect authorization probe failed with HTTP {exc.code}") from exc
    except (TimeoutError, URLError) as exc:
        raise RuntimeError("Connect authorization probe failed: provider unavailable") from exc
    if len(raw) > _MAX_RESPONSE_BYTES:
        raise RuntimeError("Connect authorization probe returned an oversized response")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Connect authorization probe returned invalid JSON") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Connect authorization probe returned an invalid payload")
    return payload


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

    payload = _request_authorization(oidc.strip())
    scheme, hostname = _safe_url_facts(payload.get("url"))
    request_present = isinstance(payload.get("request"), str) and bool(payload.get("request"))
    verifier_present = isinstance(payload.get("verifier"), str) and bool(payload.get("verifier"))
    expires_at = payload.get("expiresAt")
    expires_present = isinstance(expires_at, (int, float)) and not isinstance(expires_at, bool) and expires_at > 0
    connector = payload.get("connector")
    connector_uid = connector.get("uid") if isinstance(connector, dict) else None
    connector_match = connector_uid == _CONNECTOR
    if not request_present or not verifier_present or not expires_present or not connector_match:
        raise RuntimeError("Connect authorization probe response omitted required bounded evidence")

    # Deliberately do not print the authorization URL, request identifier, verifier,
    # OIDC token, or any provider bearer. This probe creates only the short-lived
    # authorization request; it does not follow the URL or complete consent.
    print(
        "PARALLAX_REPOSITORY_AUTHORIZATION_PROBE "
        f"status=PASS scheme={scheme} host={hostname} "
        "request_present=true verifier_present=true expires_present=true connector_match=true "
        "consent_followed=false repository_mutated=false"
    )


if __name__ == "__main__":
    main()
