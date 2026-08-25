from __future__ import annotations

import json

import pytest

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
