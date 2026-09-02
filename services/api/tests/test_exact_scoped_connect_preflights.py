from __future__ import annotations

import json
from urllib.request import Request

import pytest

from scripts import production_projected_source_preflight as projected_preflight
from scripts import production_provider_preflight as provider_preflight


REPOSITORY = "Ryan9876/parallax"
CONNECTOR = "github/parallax-runtime"
OIDC = "vercel-oidc-test-value"


def _provider_target() -> provider_preflight.Target:
    return provider_preflight.Target(
        repository_ref=f"github:{REPOSITORY}",
        github_connector=CONNECTOR,
        github_repo_id=1340272514,
        production_branch="main",
        vercel_token_env="PARALLAX_VERCEL_TOKEN_PARALLAX",
    )


def _projected_target() -> projected_preflight.Target:
    return projected_preflight.Target(
        repository_ref=f"github:{REPOSITORY}",
        github_connector=CONNECTOR,
        production_branch="main",
    )


def _exact_read_authorization() -> list[dict[str, object]]:
    return [
        {
            "type": "github_app_installation",
            "repositories": [REPOSITORY],
            "permissions": ["contents:read", "metadata:read"],
        }
    ]


def test_provider_preflight_requests_exact_read_scoped_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Request]] = []

    def fake_json_request(request: Request, *, label: str) -> object:
        calls.append((label, request))
        return {"token": "exact-read-token"}

    monkeypatch.setattr(provider_preflight, "_json_request", fake_json_request)

    assert provider_preflight._connect_token(_provider_target(), oidc=OIDC) == "exact-read-token"
    request = calls[0][1]
    assert json.loads(request.data) == {
        "subject": {"type": "app"},
        "authorizationDetails": _exact_read_authorization(),
    }


def test_provider_preflight_rejects_broad_derived_token_before_source_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels: list[str] = []
    responses = iter(
        [
            {"token": "broad-token"},
            {
                "total_count": 2,
                "repositories": [
                    {"full_name": REPOSITORY},
                    {"full_name": "Ryan9876/parallax-qa1"},
                ],
            },
        ]
    )

    def fake_json_request(request: Request, *, label: str) -> object:
        labels.append(label)
        return next(responses)

    monkeypatch.setattr(provider_preflight, "_json_request", fake_json_request)
    monkeypatch.setenv("PARALLAX_VERCEL_TOKEN_PARALLAX", "vercel-project-token")

    with pytest.raises(RuntimeError, match="not exactly one repository"):
        provider_preflight._preflight_target(_provider_target(), oidc=OIDC)

    assert labels == [
        "Vercel Connect credential preflight",
        "GitHub installation-scope preflight",
    ]


def test_projected_source_preflight_requests_exact_read_scoped_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Request]] = []

    def fake_json_request(request: Request, *, label: str) -> object:
        calls.append((label, request))
        return {"token": "exact-projected-source-token"}

    monkeypatch.setattr(projected_preflight, "_json_request", fake_json_request)

    assert (
        projected_preflight._connect_token(CONNECTOR, REPOSITORY, oidc=OIDC)
        == "exact-projected-source-token"
    )
    request = calls[0][1]
    assert json.loads(request.data) == {
        "subject": {"type": "app"},
        "authorizationDetails": _exact_read_authorization(),
    }


def test_projected_source_preflight_rejects_broad_token_before_source_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    labels: list[str] = []
    responses = iter(
        [
            {"token": "broad-projected-source-token"},
            {
                "total_count": 2,
                "repositories": [
                    {"full_name": REPOSITORY},
                    {"full_name": "Ryan9876/parallax-qa1"},
                ],
            },
        ]
    )

    def fake_json_request(request: Request, *, label: str) -> object:
        labels.append(label)
        return next(responses)

    monkeypatch.setattr(projected_preflight, "_json_request", fake_json_request)

    with pytest.raises(RuntimeError, match="not exactly one repository"):
        projected_preflight._preflight_target(_projected_target(), oidc=OIDC)

    assert labels == [
        "Vercel Connect projected-source preflight",
        "GitHub projected-source scoped installation preflight",
    ]
