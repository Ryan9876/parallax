from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import inspect

import httpx
import pytest

from parallax_api.tools.providers.common import AcceptedSourceLineage, ProviderClientError
from parallax_api.tools.providers.credentials import (
    ProviderCredentialKind,
    ScopedBearerCredential,
)
from parallax_api.tools.providers.github import GitHubCommitFile
from parallax_api.tools.providers.github_client import GitHubRestProviderClient
from parallax_api.tools.providers.vercel_client import VercelApiTarget, VercelPreviewRestClient
import parallax_api.tools.providers.credentials as credential_module
import parallax_api.tools.providers.github_client as github_client_module
import parallax_api.tools.providers.vercel_client as vercel_client_module


PROJECT_ID = "7e643661-99d6-4b31-9af7-d86d30b01c14"
RUN_ID = "1cf43021-4653-4e9c-bf54-68fd7d72ea35"
REPOSITORY_REF = "github:acme/example-app"
BASE = "0" * 40
OTHER = "9" * 40
LINEAGE = AcceptedSourceLineage(PROJECT_ID, RUN_ID, "src:" + "a" * 64, "b" * 64)


def _code(exc: ProviderClientError) -> str:
    return exc.result.result_code


class StaticGitHubCredentials:
    def __init__(self, credential: object) -> None:
        self.credential = credential

    def credential_for_repository(self, repository_ref: str):
        return self.credential


class StaticVercelCredentials:
    def __init__(self, credential: object) -> None:
        self.credential = credential

    def credential_for_project(self, vercel_project_ref: str):
        return self.credential


def _github_credential(*, expires_delta: timedelta = timedelta(minutes=5)) -> ScopedBearerCredential:
    return ScopedBearerCredential(
        provider="github",
        resource_ref=REPOSITORY_REF,
        kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
        secret="fake-sensitive-github-token-value",
        expires_at=datetime.now(timezone.utc) + expires_delta,
    )


def _vercel_credential(*, expires_delta: timedelta = timedelta(minutes=5)) -> ScopedBearerCredential:
    return ScopedBearerCredential(
        provider="vercel",
        resource_ref="vercel:project:example-app",
        kind=ProviderCredentialKind.VERCEL_SCOPED,
        secret="fake-sensitive-vercel-token-value",
        expires_at=datetime.now(timezone.utc) + expires_delta,
    )


def test_scoped_credential_is_resource_bound_expiry_aware_and_redacted() -> None:
    credential = _github_credential()
    rendered = repr(credential)
    assert "fake-sensitive-github-token-value" not in rendered
    assert "<redacted>" in rendered
    assert "fake-sensitive-github-token-value" not in str(credential)

    expired = _github_credential(expires_delta=timedelta(seconds=-1))
    with pytest.raises(ProviderClientError) as exc_info:
        expired.authorization_value()
    assert _code(exc_info.value) == "CREDENTIAL_EXPIRED"


def test_missing_expired_and_wrong_scope_credentials_never_reach_transport() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    for credential, expected in (
        (None, "CREDENTIAL_UNAVAILABLE"),
        (_github_credential(expires_delta=timedelta(seconds=-1)), "CREDENTIAL_EXPIRED"),
        (
            ScopedBearerCredential(
                provider="github",
                resource_ref="github:acme/other-app",
                kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
                secret="fake-other-repository-token",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            ),
            "CREDENTIAL_SCOPE_MISMATCH",
        ),
    ):
        client = GitHubRestProviderClient(
            StaticGitHubCredentials(credential),
            transport=httpx.MockTransport(handler),
        )
        with pytest.raises(ProviderClientError) as exc_info:
            client.resolve_repository(REPOSITORY_REF)
        assert _code(exc_info.value) == expected
    assert calls == 0


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (401, "PROVIDER_AUTH_DENIED"),
        (403, "PROVIDER_AUTH_DENIED"),
        (429, "PROVIDER_RATE_LIMITED"),
        (500, "PROVIDER_UNAVAILABLE"),
        (503, "PROVIDER_UNAVAILABLE"),
    ],
)
def test_github_http_failures_are_normalized_without_raw_provider_body(status: int, expected: str) -> None:
    secret_body = {"message": "token=fake-provider-secret-should-never-surface"}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=secret_body)

    client = GitHubRestProviderClient(
        StaticGitHubCredentials(_github_credential()),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.resolve_repository(REPOSITORY_REF)
    assert _code(exc_info.value) == expected
    assert "fake-provider-secret" not in str(exc_info.value)
    assert "fake-provider-secret" not in repr(exc_info.value)


def test_transport_timeout_is_normalized_without_transport_diagnostics() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("fake-sensitive-network-diagnostic", request=request)

    client = GitHubRestProviderClient(
        StaticGitHubCredentials(_github_credential()),
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.resolve_repository(REPOSITORY_REF)
    assert _code(exc_info.value) == "PROVIDER_TIMEOUT"
    assert "fake-sensitive-network-diagnostic" not in str(exc_info.value)


def test_github_stale_parent_fails_before_any_write() -> None:
    write_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal write_calls
        if request.method != "GET":
            write_calls += 1
        if request.url.path == "/repos/acme/example-app/git/ref/heads/parallax/run-1":
            return httpx.Response(
                200,
                json={"ref": "refs/heads/parallax/run-1", "object": {"sha": OTHER}},
            )
        if request.url.path == f"/repos/acme/example-app/git/commits/{OTHER}":
            return httpx.Response(
                200,
                json={"sha": OTHER, "message": "unrelated", "tree": {"sha": "2" * 40}, "parents": [{"sha": BASE}]},
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = GitHubRestProviderClient(
        StaticGitHubCredentials(_github_credential()),
        transport=httpx.MockTransport(handler),
    )
    content = "print('safe')\n"
    file = GitHubCommitFile("src/app.py", content, sha256(content.encode()).hexdigest())
    with pytest.raises(ProviderClientError) as exc_info:
        client.commit_files(REPOSITORY_REF, "parallax/run-1", BASE, LINEAGE, (file,))
    assert _code(exc_info.value) == "STALE_PARENT"
    assert write_calls == 0


def test_github_rejects_truncated_or_unsupported_source_tree() -> None:
    def truncated(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"truncated": True, "tree": []})

    client = GitHubRestProviderClient(
        StaticGitHubCredentials(_github_credential()),
        transport=httpx.MockTransport(truncated),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.read_tree(REPOSITORY_REF, BASE, max_entries=10)
    assert _code(exc_info.value) == "SOURCE_TREE_TRUNCATED"

    def symlink(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "truncated": False,
                "tree": [{"path": "unsafe", "mode": "120000", "type": "blob", "sha": "3" * 40, "size": 4}],
            },
        )

    client = GitHubRestProviderClient(
        StaticGitHubCredentials(_github_credential()),
        transport=httpx.MockTransport(symlink),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.read_tree(REPOSITORY_REF, BASE, max_entries=10)
    assert _code(exc_info.value) == "UNSUPPORTED_SOURCE_ENTRY"


TARGET = VercelApiTarget(
    vercel_project_ref="vercel:project:example-app",
    project_id="prj_example",
    project_name="example-app",
    team_id="team_example",
    repository_ref=REPOSITORY_REF,
    github_repo_id=12345,
    production_branch="parallax/production",
)


def test_vercel_production_branch_is_rejected_before_transport() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    client = VercelPreviewRestClient(
        StaticVercelCredentials(_vercel_credential()),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.create_preview(
            TARGET.vercel_project_ref,
            REPOSITORY_REF,
            BASE,
            "parallax/production",
            LINEAGE,
        )
    assert _code(exc_info.value) == "PRODUCTION_BRANCH_FORBIDDEN"
    assert calls == 0


def test_vercel_production_readback_can_never_be_preview_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v9/projects/prj_example":
            return httpx.Response(200, json={"id": "prj_example", "name": "example-app", "link": {"type": "github", "repoId": 12345}})
        if request.url.path == "/v6/deployments":
            return httpx.Response(200, json={"deployments": []})
        if request.url.path == "/v13/deployments" and request.method == "POST":
            return httpx.Response(200, json={"id": "dpl_bad", "readyState": "QUEUED"})
        if request.url.path == "/v13/deployments/dpl_bad" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "dpl_bad",
                    "target": "production",
                    "readyState": "READY",
                    "url": "bad.vercel.app",
                    "project": {"id": "prj_example", "name": "example-app"},
                    "gitSource": {"type": "github", "repoId": 12345, "ref": "parallax/run-1", "sha": BASE},
                },
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    client = VercelPreviewRestClient(
        StaticVercelCredentials(_vercel_credential()),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.create_preview(TARGET.vercel_project_ref, REPOSITORY_REF, BASE, "parallax/run-1", LINEAGE)
    assert _code(exc_info.value) == "PRODUCTION_SCOPE_FORBIDDEN"


def test_vercel_repository_mismatch_fails_before_transport() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    client = VercelPreviewRestClient(
        StaticVercelCredentials(_vercel_credential()),
        {TARGET.vercel_project_ref: TARGET},
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ProviderClientError) as exc_info:
        client.create_preview(
            TARGET.vercel_project_ref,
            "github:acme/other-app",
            BASE,
            "parallax/run-1",
            LINEAGE,
        )
    assert _code(exc_info.value) == "REPOSITORY_MISMATCH"
    assert calls == 0


def test_concrete_clients_expose_no_generic_or_production_mutation_surface() -> None:
    forbidden = {
        "request",
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "merge",
        "promote",
        "production",
        "alias",
        "domain",
        "environment",
        "secret",
        "shell",
        "command",
    }
    for client_type in (GitHubRestProviderClient, VercelPreviewRestClient):
        public = {name for name in dir(client_type) if not name.startswith("_")}
        assert not (public & forbidden)

    assert {name for name in dir(VercelPreviewRestClient) if not name.startswith("_")} == {
        "create_preview",
        "read_preview",
    }


def test_client_modules_have_no_environment_or_embedded_broad_pat_loader() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (credential_module, github_client_module, vercel_client_module)
    )
    assert "os.environ" not in source
    assert "GITHUB_TOKEN" not in source
    assert "VERCEL_TOKEN" not in source
    assert "personal access token" not in source.casefold()
