from __future__ import annotations

import json

import pytest

from scripts import vercel_build
from scripts.production_delivery_permission_preflight import (
    _authorization_details,
    _require_repository_write_permission,
    _targets,
)


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


def test_delivery_permission_preflight_requires_explicit_repository_write_capability() -> None:
    with pytest.raises(RuntimeError, match="repository write capability"):
        _require_repository_write_permission({"id": 1340272514})
    with pytest.raises(RuntimeError, match="repository write capability"):
        _require_repository_write_permission({"permissions": {"push": False, "pull": True}})

    _require_repository_write_permission({"permissions": {"push": True, "pull": True}})


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
