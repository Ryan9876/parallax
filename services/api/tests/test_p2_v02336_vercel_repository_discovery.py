from __future__ import annotations

import json

import httpx
import pytest

from parallax_api.code.delivery_readiness import VercelProjectReadinessRestClient
from parallax_api.code.production_delivery import EnvironmentVercelCredentialProvider
from parallax_api.tools.providers.common import ProviderClientError


REPOSITORY_REF = "github:Ryan9876/parallax-qa1"
REPOSITORY_ID = 987654321
TEAM_ID = "team_JgE8AWWz36uzRbeR6V6EWg9k"
READINESS_REF = f"readiness:{TEAM_ID}"
TOKEN = "vercel-readiness-test-token"
PROJECT_NAME = "parallax-qa1-px-11111111"


def _credentials() -> EnvironmentVercelCredentialProvider:
    return EnvironmentVercelCredentialProvider(
        TOKEN,
        allowed_targets=frozenset({READINESS_REF}),
    )


def _project(project_id: str = "prj_qa1", *, repo_id: int = REPOSITORY_ID):
    return {
        "id": project_id,
        "name": PROJECT_NAME,
        "accountId": TEAM_ID,
        "link": {"type": "github", "repoId": repo_id},
    }


def _client(handler) -> VercelProjectReadinessRestClient:
    return VercelProjectReadinessRestClient(
        _credentials(),
        credential_ref=READINESS_REF,
        team_id=TEAM_ID,
        transport=httpx.MockTransport(handler),
    )


def _assert_exact_query(request: httpx.Request) -> None:
    assert request.method == "GET"
    assert request.url.path == "/v9/projects"
    assert request.url.params.get("teamId") == TEAM_ID
    assert request.url.params.get("repoId") == str(REPOSITORY_ID)
    assert request.url.params.get("limit") == "2"


def _ensure(client: VercelProjectReadinessRestClient):
    return client.ensure(
        repository_ref=REPOSITORY_REF,
        github_repo_id=REPOSITORY_ID,
        production_branch="main",
        project_name=PROJECT_NAME,
    )


def test_exact_repo_filter_reuses_one_readback_verified_target():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v9/projects":
            _assert_exact_query(request)
            return httpx.Response(
                200,
                json={"projects": [_project()], "pagination": {"next": None}},
            )
        if request.url.path == "/v9/projects/prj_qa1":
            return httpx.Response(200, json=_project())
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    result = _ensure(_client(handler))
    assert result.created is False
    assert result.target.project_id == "prj_qa1"
    assert result.target.github_repo_id == REPOSITORY_ID


def test_filtered_provider_repo_mismatch_fails_before_mutation():
    mutations = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal mutations
        if request.method != "GET":
            mutations += 1
        _assert_exact_query(request)
        return httpx.Response(
            200,
            json={
                "projects": [_project(repo_id=REPOSITORY_ID + 1)],
                "pagination": {"next": None},
            },
        )

    with pytest.raises(ProviderClientError, match="TARGET_REPOSITORY_MISMATCH"):
        _ensure(_client(handler))
    assert mutations == 0


def test_filtered_provider_malformed_project_fails_closed():
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_exact_query(request)
        return httpx.Response(
            200,
            json={"projects": [{"id": "prj_bad"}], "pagination": {"next": None}},
        )

    with pytest.raises(ProviderClientError, match="TARGET_REPOSITORY_UNVERIFIED"):
        _ensure(_client(handler))


@pytest.mark.parametrize(
    ("pagination", "expected"),
    [
        (None, "PROVIDER_INVALID_RESPONSE"),
        ({}, "PROVIDER_INVALID_RESPONSE"),
        ({"next": 123}, "TARGET_DISCOVERY_UNBOUNDED"),
    ],
)
def test_incomplete_filtered_discovery_fails_closed(pagination, expected):
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_exact_query(request)
        payload = {"projects": []}
        if pagination is not None:
            payload["pagination"] = pagination
        return httpx.Response(200, json=payload)

    with pytest.raises(ProviderClientError, match=expected):
        _ensure(_client(handler))


def test_two_exact_candidates_are_ambiguous_even_with_continuation():
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_exact_query(request)
        return httpx.Response(
            200,
            json={
                "projects": [_project("prj_one"), _project("prj_two")],
                "pagination": {"next": 123},
            },
        )

    with pytest.raises(ProviderClientError, match="TARGET_AMBIGUOUS"):
        _ensure(_client(handler))


def test_creation_conflict_reconciliation_uses_same_exact_filter():
    list_calls = 0
    post_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal list_calls, post_calls
        if request.url.path == "/v9/projects":
            _assert_exact_query(request)
            list_calls += 1
            projects = [] if list_calls == 1 else [_project()]
            return httpx.Response(
                200,
                json={"projects": projects, "pagination": {"next": None}},
            )
        if request.url.path == "/v11/projects":
            post_calls += 1
            assert json.loads(request.content) == {
                "name": PROJECT_NAME,
                "gitRepository": {"type": "github", "repo": "Ryan9876/parallax-qa1"},
            }
            return httpx.Response(
                409,
                json={"error": {"code": "project_already_exists"}},
            )
        if request.url.path == "/v9/projects/prj_qa1":
            return httpx.Response(200, json=_project())
        if request.url.path == "/v6/deployments":
            assert request.url.params.get("projectId") == "prj_qa1"
            assert request.url.params.get("target") == "production"
            return httpx.Response(200, json={"deployments": []})
        raise AssertionError(f"unexpected request: {request.method} {request.url}")

    result = _ensure(_client(handler))
    assert result.created is False
    assert result.target.project_id == "prj_qa1"
    assert list_calls == 2
    assert post_calls == 1
