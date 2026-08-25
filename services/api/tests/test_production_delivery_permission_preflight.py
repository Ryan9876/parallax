from __future__ import annotations

import json
from urllib.request import Request

import pytest

from scripts import production_delivery_permission_preflight as delivery_preflight
from scripts import vercel_build
from scripts.production_delivery_permission_preflight import _authorization_details, _targets


def test_delivery_authorization_is_exact_repository_and_minimum_mutation_scope() -> None:
    assert _authorization_details("Ryan9876/parallax") == [
        {
            "type": "github_app_installation",
            "repositories": ["Ryan9876/parallax"],
            "permissions": [
                "contents:write",
                "metadata:read",
                "pull_requests:write",
            ],
        }
    ]


def test_delivery_target_registry_rejects_duplicate_repository_identity_case_insensitively() -> None:
    raw = json.dumps(
        [
            {
                "repository_ref": "github:Ryan9876/parallax",
                "github_connector": "github/parallax-runtime",
                "github_repo_id": 1340272514,
            },
            {
                "repository_ref": "github:ryan9876/PARALLAX",
                "github_connector": "github/parallax-runtime",
                "github_repo_id": 1340272514,
            },
        ]
    )
    with pytest.raises(RuntimeError, match="duplicate repositories"):
        _targets(raw)


def test_delivery_preflight_accepts_exact_scoped_token_without_repository_push_heuristic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Request]] = []
    responses = iter(
        [
            ({"token": "scoped-installation-token"}, {}),
            (
                {
                    "total_count": 1,
                    "repositories": [{"full_name": "Ryan9876/parallax"}],
                },
                {},
            ),
            ({"id": 1340272514}, {}),
        ]
    )

    def fake_json_request(request: Request, *, label: str):
        calls.append((label, request))
        return next(responses)

    monkeypatch.setattr(delivery_preflight, "_json_request", fake_json_request)

    delivery_preflight._preflight_target(
        {
            "repository_ref": "github:Ryan9876/parallax",
            "github_connector": "github/parallax-runtime",
            "github_repo_id": 1340272514,
        },
        oidc="vercel-oidc",
    )

    assert len(calls) == 3
    token_request = calls[0][1]
    assert json.loads(token_request.data) == {
        "subject": {"type": "app"},
        "authorizationDetails": [
            {
                "type": "github_app_installation",
                "repositories": ["Ryan9876/parallax"],
                "permissions": ["contents:write", "metadata:read", "pull_requests:write"],
            }
        ],
    }


def test_delivery_preflight_rejects_wrong_numeric_repository_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = iter(
        [
            ({"token": "scoped-installation-token"}, {}),
            (
                {
                    "total_count": 1,
                    "repositories": [{"full_name": "Ryan9876/parallax"}],
                },
                {},
            ),
            ({"id": 999}, {}),
        ]
    )
    monkeypatch.setattr(
        delivery_preflight,
        "_json_request",
        lambda request, *, label: next(responses),
    )

    with pytest.raises(RuntimeError, match="numeric identity mismatch"):
        delivery_preflight._preflight_target(
            {
                "repository_ref": "github:Ryan9876/parallax",
                "github_connector": "github/parallax-runtime",
                "github_repo_id": 1340272514,
            },
            oidc="vercel-oidc",
        )


def test_vercel_build_runs_delivery_permission_preflight_before_projected_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(vercel_build, "_run", lambda *args: calls.append(args))
    monkeypatch.setenv("VERCEL_ENV", "preview")
    monkeypatch.chdir(tmp_path)

    vercel_build.main()

    assert calls[:3] == [
        ("scripts/production_provider_preflight.py",),
        ("scripts/production_delivery_permission_preflight.py",),
        ("scripts/production_projected_source_preflight.py",),
    ]
