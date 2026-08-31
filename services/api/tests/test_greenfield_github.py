from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from parallax_api.code.greenfield_github import GreenfieldGitHubClient
from parallax_api.tools.providers import ProviderClientError
from parallax_api.tools.providers.credentials import ProviderCredentialKind, ScopedBearerCredential
from parallax_api.tools.providers.github_client import GitHubRestProviderClient


REPOSITORY = "github:Ryan9876/empty-target"
DEFAULT_BRANCH = "main"
BOOTSTRAP = "a" * 40
BASELINE = "b" * 40
BLOB = "c" * 40
PROVENANCE = "d" * 64
CONTENT = f"parallax-greenfield-v1\nprovenance={PROVENANCE}\n"
ACTOR = {
    "name": "Parallax App Builder",
    "email": "parallax-app-builder@users.noreply.github.com",
    "date": "2000-01-01T00:00:00Z",
}


class _Credentials:
    def credential_for_repository(self, repository_ref: str) -> ScopedBearerCredential:
        assert repository_ref == REPOSITORY
        return ScopedBearerCredential(
            provider="github",
            resource_ref=repository_ref,
            kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
            secret="greenfield-test-token",
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )


def _client(handler) -> GreenfieldGitHubClient:
    delegate = GitHubRestProviderClient(_Credentials(), transport=httpx.MockTransport(handler))
    return GreenfieldGitHubClient(delegate)


def _repo() -> httpx.Response:
    return httpx.Response(
        200,
        json={"full_name": "Ryan9876/empty-target", "default_branch": DEFAULT_BRANCH},
    )


def _commit(message: str, parents: list[dict[str, str]]) -> dict[str, object]:
    return {"message": message, "parents": parents, "author": ACTOR, "committer": ACTOR}


def test_positive_empty_inspection_is_distinct_from_not_found() -> None:
    def empty(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(404, json={"message": "Not Found"})
        raise AssertionError(request.url)

    result = _client(empty).inspect_repository(REPOSITORY)
    assert result.is_empty is True
    assert result.head_revision is None
    assert result.default_branch == DEFAULT_BRANCH

    def missing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    with pytest.raises(ProviderClientError, match="REPOSITORY_NOT_FOUND"):
        _client(missing).inspect_repository(REPOSITORY)


def test_real_github_empty_ref_409_is_narrowly_normalized() -> None:
    def empty_409(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(409, json={"message": "Git Repository is empty."})
        raise AssertionError(request.url)

    result = _client(empty_409).inspect_repository(REPOSITORY)
    assert result.is_empty is True
    assert result.head_revision is None

    def unrelated_409(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(409, json={"message": "Reference conflict"})
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="PROVIDER_CONFLICT"):
        _client(unrelated_409).inspect_repository(REPOSITORY)

    def malformed_409(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/repos/Ryan9876/empty-target":
            return _repo()
        if request.url.path.endswith("/git/ref/heads/main"):
            return httpx.Response(409, text="not-json")
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="PROVIDER_INVALID_RESPONSE"):
        _client(malformed_409).inspect_repository(REPOSITORY)


def test_initializer_creates_marker_deletes_it_and_verifies_empty_head() -> None:
    writes: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            if not writes:
                return httpx.Response(404, json={"message": "Not Found"})
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith("/contents/.parallax-greenfield") and request.method == "PUT":
            writes.append("create")
            payload = __import__("json").loads(request.content)
            assert base64.b64decode(payload["content"]).decode() == CONTENT
            assert payload["branch"] == DEFAULT_BRANCH
            assert payload["author"] == ACTOR == payload["committer"]
            return httpx.Response(201, json={"commit": {"sha": BOOTSTRAP}, "content": {"sha": BLOB}})
        if path.endswith("/contents/.parallax-greenfield") and request.method == "DELETE":
            writes.append("delete")
            payload = __import__("json").loads(request.content)
            assert payload["sha"] == BLOB
            assert payload["author"] == ACTOR == payload["committer"]
            return httpx.Response(200, json={"commit": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(200, json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}]))
        if path.endswith(f"/git/trees/{BASELINE}"):
            return httpx.Response(200, json={"truncated": False, "tree": []})
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            return httpx.Response(200, json=_commit("Initialize Parallax greenfield baseline", []))
        if path.endswith(f"/git/trees/{BOOTSTRAP}"):
            return httpx.Response(200, json={"truncated": False, "tree": [{"path": ".parallax-greenfield", "type": "blob", "mode": "100644", "sha": BLOB}]})
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(CONTENT.encode()).decode()})
        raise AssertionError((request.method, request.url))

    result = _client(handler).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert writes == ["create", "delete"]
    assert result.initialized is True
    assert result.baseline_revision == BASELINE
    assert result.bootstrap_revision == BOOTSTRAP


def test_existing_exact_baseline_is_replayed_read_only_and_conflict_fails_closed() -> None:
    methods: list[str] = []

    def exact(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(200, json=_commit("Finalize Parallax empty greenfield baseline", [{"sha": BOOTSTRAP}]))
        if path.endswith(f"/git/trees/{BASELINE}"):
            return httpx.Response(200, json={"truncated": False, "tree": []})
        if path.endswith(f"/git/commits/{BOOTSTRAP}"):
            return httpx.Response(200, json=_commit("Initialize Parallax greenfield baseline", []))
        if path.endswith(f"/git/trees/{BOOTSTRAP}"):
            return httpx.Response(200, json={"truncated": False, "tree": [{"path": ".parallax-greenfield", "type": "blob", "mode": "100644", "sha": BLOB}]})
        if path.endswith(f"/git/blobs/{BLOB}"):
            return httpx.Response(200, json={"encoding": "base64", "content": base64.b64encode(CONTENT.encode()).decode()})
        raise AssertionError(request.url)

    replay = _client(exact).initialize_empty_baseline(REPOSITORY, PROVENANCE)
    assert replay.initialized is False
    assert set(methods) == {"GET"}

    def conflict(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/Ryan9876/empty-target":
            return _repo()
        if path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": BASELINE}})
        if path.endswith(f"/git/commits/{BASELINE}"):
            return httpx.Response(200, json=_commit("unrelated user commit", [{"sha": BOOTSTRAP}]))
        raise AssertionError(request.url)

    with pytest.raises(ProviderClientError, match="GREENFIELD_BASELINE_MISMATCH"):
        _client(conflict).initialize_empty_baseline(REPOSITORY, PROVENANCE)
