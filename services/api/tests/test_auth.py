from __future__ import annotations

from fastapi.testclient import TestClient

from parallax_api.config import settings
from parallax_api.main import create_app
from parallax_api.session import (
    SESSION_COOKIE_NAME,
    SESSION_HEADER_NAME,
    SESSION_HEADER_VALUE,
    issue_session_token,
)


def test_operational_probes_are_public_but_application_routes_require_bearer():
    original = settings.access_token
    object.__setattr__(settings, "access_token", "a" * 32)
    try:
        client = TestClient(create_app(create_schema=True))
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200

        denied = client.get("/v1/conversations")
        assert denied.status_code == 401
        assert denied.json() == {"detail": "Authentication required"}

        invalid = client.get("/v1/conversations", headers={"Authorization": "Bearer wrong"})
        assert invalid.status_code == 401

        allowed = client.get(
            "/v1/conversations",
            headers={"Authorization": f"Bearer {'a' * 32}"},
        )
        assert allowed.status_code == 200
    finally:
        object.__setattr__(settings, "access_token", original)


def test_browser_session_is_http_only_bounded_and_requires_marker_header():
    original_token = settings.access_token
    original_environment = settings.environment
    secret = "s" * 48
    object.__setattr__(settings, "access_token", secret)
    object.__setattr__(settings, "environment", "production")
    try:
        client = TestClient(create_app(create_schema=True), base_url="https://testserver")

        established = client.post(
            "/v1/session",
            headers={"Authorization": f"Bearer {secret}"},
        )
        assert established.status_code == 200
        assert established.json()["authenticated"] is True
        assert secret not in established.text

        set_cookie = established.headers["set-cookie"].lower()
        assert SESSION_COOKIE_NAME in set_cookie
        assert "httponly" in set_cookie
        assert "secure" in set_cookie
        assert "samesite=none" in set_cookie
        assert secret not in established.headers["set-cookie"]

        cookie_only = client.get("/v1/conversations")
        assert cookie_only.status_code == 401

        session_headers = {SESSION_HEADER_NAME: SESSION_HEADER_VALUE}
        allowed = client.get("/v1/conversations", headers=session_headers)
        assert allowed.status_code == 200

        session_status = client.get("/v1/session", headers=session_headers)
        assert session_status.status_code == 200
        assert session_status.json() == {"authenticated": True}

        valid_cookie = client.cookies.get(SESSION_COOKIE_NAME)
        assert valid_cookie
        client.cookies.set(SESSION_COOKIE_NAME, f"{valid_cookie}tampered")
        tampered = client.get("/v1/conversations", headers=session_headers)
        assert tampered.status_code == 401

        expired_cookie, _ = issue_session_token(secret, now=0)
        client.cookies.set(SESSION_COOKIE_NAME, expired_cookie)
        expired = client.get("/v1/conversations", headers=session_headers)
        assert expired.status_code == 401

        client.post("/v1/session", headers={"Authorization": f"Bearer {secret}"})
        ended = client.delete("/v1/session")
        assert ended.status_code == 200
        assert ended.json() == {"authenticated": False}
        assert "max-age=0" in ended.headers["set-cookie"].lower()

        after_logout = client.get("/v1/conversations", headers=session_headers)
        assert after_logout.status_code == 401
    finally:
        object.__setattr__(settings, "access_token", original_token)
        object.__setattr__(settings, "environment", original_environment)
