from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials

from parallax_api.routes import session as session_route
from parallax_api.services.github_actions_identity import GitHubActionsIdentityError


class _Repository:
    def __init__(self, user):
        self.user = user
        self.requested_email = None

    def get_by_email(self, email):
        self.requested_email = email
        return self.user


def _credentials():
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials="x" * 64)


def test_qa_automation_session_maps_only_to_active_bound_qa_user(monkeypatch):
    user = SimpleNamespace(id="qa-user-id", role="owner", status="active", auth_user_id="google-user-id")
    repository = _Repository(user)
    monkeypatch.setattr(session_route, "AuthorizedUserRepository", lambda _: repository)
    monkeypatch.setattr(session_route, "verify_github_actions_identity", lambda _: object())

    captured = {}

    def fake_set_session_cookie(response, *, subject, role, auth_method):
        captured.update(subject=subject, role=role, auth_method=auth_method)
        return {"authenticated": True}

    monkeypatch.setattr(session_route, "_set_session_cookie", fake_set_session_cookie)

    result = session_route.establish_qa_automation_session(
        Response(),
        session=object(),
        credentials=_credentials(),
    )

    assert result == {"authenticated": True}
    assert repository.requested_email == "parallax.qa.ai@gmail.com"
    assert captured == {
        "subject": "qa-user-id",
        "role": "owner",
        "auth_method": "google",
    }


@pytest.mark.parametrize(
    "user",
    [
        None,
        SimpleNamespace(id="qa", role="owner", status="revoked", auth_user_id="google-user-id"),
        SimpleNamespace(id="qa", role="owner", status="active", auth_user_id=None),
    ],
)
def test_qa_automation_session_denies_missing_inactive_or_unbound_user(monkeypatch, user):
    monkeypatch.setattr(session_route, "AuthorizedUserRepository", lambda _: _Repository(user))
    monkeypatch.setattr(session_route, "verify_github_actions_identity", lambda _: object())

    with pytest.raises(HTTPException) as exc:
        session_route.establish_qa_automation_session(
            Response(),
            session=object(),
            credentials=_credentials(),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Access not granted"


def test_qa_automation_session_denies_invalid_machine_assertion(monkeypatch):
    def reject(_):
        raise GitHubActionsIdentityError("invalid")

    monkeypatch.setattr(session_route, "verify_github_actions_identity", reject)

    with pytest.raises(HTTPException) as exc:
        session_route.establish_qa_automation_session(
            Response(),
            session=object(),
            credentials=_credentials(),
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "QA automation authentication could not be verified"


def test_qa_automation_session_requires_bearer_token():
    with pytest.raises(HTTPException) as exc:
        session_route.establish_qa_automation_session(
            Response(),
            session=object(),
            credentials=None,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "QA automation authentication required"
