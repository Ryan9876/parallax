from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import delete

from parallax_api.config import settings
from parallax_api.db import SessionLocal
from parallax_api.main import create_app
from parallax_api.models import AuthorizedUser
from parallax_api.services.google_identity import VerifiedGoogleIdentity
from parallax_api.session import SESSION_COOKIE_NAME, SESSION_HEADER_NAME, SESSION_HEADER_VALUE


SECRET = "g" * 48
SESSION_HEADERS = {SESSION_HEADER_NAME: SESSION_HEADER_VALUE}


def _reset_users() -> None:
    with SessionLocal() as session:
        session.execute(delete(AuthorizedUser))
        session.commit()


def _insert_user(email: str, *, role: str = "member", status: str = "active") -> AuthorizedUser:
    with SessionLocal() as session:
        user = AuthorizedUser(
            email=email.casefold(),
            normalized_email=email.casefold(),
            role=role,
            status=status,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def _identity(user_id: str, email: str, name: str = "Test User") -> VerifiedGoogleIdentity:
    return VerifiedGoogleIdentity(
        auth_user_id=user_id,
        email=email.casefold(),
        display_name=name,
        avatar_url="https://example.test/avatar.png",
    )


def test_google_login_requires_explicit_allowlist_and_binds_identity(monkeypatch):
    import parallax_api.routes.session as session_route

    original_token = settings.access_token
    original_environment = settings.environment
    object.__setattr__(settings, "access_token", SECRET)
    object.__setattr__(settings, "environment", "production")
    _reset_users()
    try:
        owner = _insert_user("owner@example.com", role="owner")
        monkeypatch.setattr(
            session_route,
            "verify_google_identity",
            lambda token: _identity("google-owner-1", "owner@example.com", "Owner Example"),
        )
        client = TestClient(create_app(create_schema=True), base_url="https://testserver")

        established = client.post(
            "/v1/session/google",
            headers={"Authorization": "Bearer transient-google-token"},
        )
        assert established.status_code == 200
        assert established.json()["authenticated"] is True
        assert "transient-google-token" not in established.text
        assert "transient-google-token" not in established.headers["set-cookie"]
        assert SESSION_COOKIE_NAME in established.headers["set-cookie"]
        assert "httponly" in established.headers["set-cookie"].lower()
        assert "secure" in established.headers["set-cookie"].lower()

        me = client.get("/v1/access/me", headers=SESSION_HEADERS)
        assert me.status_code == 200
        assert me.json()["id"] == owner.id
        assert me.json()["email"] == "owner@example.com"
        assert me.json()["role"] == "owner"
        assert me.json()["auth_method"] == "google"
        assert me.json()["bound"] is True

        with SessionLocal() as session:
            stored = session.get(AuthorizedUser, owner.id)
            assert stored is not None
            assert stored.auth_user_id == "google-owner-1"
            assert stored.display_name == "Owner Example"
            assert stored.last_login_at is not None
    finally:
        _reset_users()
        object.__setattr__(settings, "access_token", original_token)
        object.__setattr__(settings, "environment", original_environment)


def test_authenticated_google_user_without_authorization_is_denied(monkeypatch):
    import parallax_api.routes.session as session_route

    original_token = settings.access_token
    original_environment = settings.environment
    object.__setattr__(settings, "access_token", SECRET)
    object.__setattr__(settings, "environment", "production")
    _reset_users()
    try:
        monkeypatch.setattr(
            session_route,
            "verify_google_identity",
            lambda token: _identity("google-outsider", "outsider@example.com"),
        )
        client = TestClient(create_app(create_schema=True), base_url="https://testserver")
        denied = client.post(
            "/v1/session/google",
            headers={"Authorization": "Bearer valid-but-not-authorized"},
        )
        assert denied.status_code == 403
        assert denied.json() == {"detail": "Access not granted"}
        assert SESSION_COOKIE_NAME not in client.cookies
    finally:
        _reset_users()
        object.__setattr__(settings, "access_token", original_token)
        object.__setattr__(settings, "environment", original_environment)


def test_owner_can_manage_members_and_revocation_invalidates_existing_session(monkeypatch):
    import parallax_api.routes.session as session_route

    original_token = settings.access_token
    original_environment = settings.environment
    object.__setattr__(settings, "access_token", SECRET)
    object.__setattr__(settings, "environment", "production")
    _reset_users()
    try:
        _insert_user("owner@example.com", role="owner")
        monkeypatch.setattr(
            session_route,
            "verify_google_identity",
            lambda token: _identity("google-owner-2", "owner@example.com"),
        )
        app = create_app(create_schema=True)
        owner_client = TestClient(app, base_url="https://testserver")
        assert owner_client.post(
            "/v1/session/google",
            headers={"Authorization": "Bearer owner-google-token"},
        ).status_code == 200

        added = owner_client.post(
            "/v1/access/users",
            headers=SESSION_HEADERS,
            json={"email": "Member@Example.com"},
        )
        assert added.status_code == 201
        member_id = added.json()["id"]
        assert added.json()["email"] == "member@example.com"
        assert added.json()["role"] == "member"

        listed = owner_client.get("/v1/access/users", headers=SESSION_HEADERS)
        assert listed.status_code == 200
        assert {item["email"] for item in listed.json()} == {"owner@example.com", "member@example.com"}

        monkeypatch.setattr(
            session_route,
            "verify_google_identity",
            lambda token: _identity("google-member-1", "member@example.com", "Member Example"),
        )
        member_client = TestClient(app, base_url="https://testserver")
        assert member_client.post(
            "/v1/session/google",
            headers={"Authorization": "Bearer member-google-token"},
        ).status_code == 200
        assert member_client.get("/v1/conversations", headers=SESSION_HEADERS).status_code == 200
        assert member_client.post(
            "/v1/access/users",
            headers=SESSION_HEADERS,
            json={"email": "another@example.com"},
        ).status_code == 403

        revoked = owner_client.patch(
            f"/v1/access/users/{member_id}",
            headers=SESSION_HEADERS,
            json={"status": "revoked"},
        )
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"
        assert member_client.get("/v1/conversations", headers=SESSION_HEADERS).status_code == 401

        reactivated = owner_client.patch(
            f"/v1/access/users/{member_id}",
            headers=SESSION_HEADERS,
            json={"status": "active"},
        )
        assert reactivated.status_code == 200
        assert reactivated.json()["status"] == "active"
    finally:
        _reset_users()
        object.__setattr__(settings, "access_token", original_token)
        object.__setattr__(settings, "environment", original_environment)


def test_owner_cannot_be_revoked(monkeypatch):
    import parallax_api.routes.session as session_route

    original_token = settings.access_token
    original_environment = settings.environment
    object.__setattr__(settings, "access_token", SECRET)
    object.__setattr__(settings, "environment", "production")
    _reset_users()
    try:
        owner = _insert_user("owner@example.com", role="owner")
        monkeypatch.setattr(
            session_route,
            "verify_google_identity",
            lambda token: _identity("google-owner-3", "owner@example.com"),
        )
        client = TestClient(create_app(create_schema=True), base_url="https://testserver")
        assert client.post(
            "/v1/session/google",
            headers={"Authorization": "Bearer owner-token"},
        ).status_code == 200
        blocked = client.patch(
            f"/v1/access/users/{owner.id}",
            headers=SESSION_HEADERS,
            json={"status": "revoked"},
        )
        assert blocked.status_code == 409
    finally:
        _reset_users()
        object.__setattr__(settings, "access_token", original_token)
        object.__setattr__(settings, "environment", original_environment)
