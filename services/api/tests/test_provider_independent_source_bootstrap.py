from __future__ import annotations

import httpx
import pytest

from parallax_api.tools.providers.common import ProviderClientError
from parallax_api.tools.providers.public_github_client import (
    LazyAuthenticatedGitHubReadClient,
    PublicFirstGitHubReadClient,
    PublicGitHubReadClient,
)


REPOSITORY = "github:Ryan9876/ot-time"
REVISION = "a" * 40
BLOB = "b" * 40


def _public_transport(request: httpx.Request) -> httpx.Response:
    assert request.headers.get("authorization") is None
    if request.url.path == "/repos/Ryan9876/ot-time":
        return httpx.Response(
            200,
            json={"full_name": "Ryan9876/ot-time", "default_branch": "main", "private": False},
        )
    if request.url.path == "/repos/Ryan9876/ot-time/git/ref/heads/main":
        return httpx.Response(200, json={"object": {"sha": REVISION}})
    if request.url.path == f"/repos/Ryan9876/ot-time/git/trees/{REVISION}":
        return httpx.Response(
            200,
            json={
                "truncated": False,
                "tree": [
                    {"path": "README.md", "sha": BLOB, "type": "blob", "mode": "100644", "size": 5}
                ],
            },
        )
    if request.url.path == "/repos/Ryan9876/ot-time/contents/README.md":
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "path": "README.md",
                "size": 5,
                "content": "aGVsbG8=",
            },
        )
    raise AssertionError(f"unexpected public GitHub request: {request.method} {request.url}")


def test_public_repository_reads_never_construct_authenticated_provider() -> None:
    constructed = False

    def authenticated_factory():
        nonlocal constructed
        constructed = True
        raise AssertionError("public repository bootstrap must not construct a credentialed client")

    public = PublicGitHubReadClient(transport=httpx.MockTransport(_public_transport))
    client = PublicFirstGitHubReadClient(
        public,
        LazyAuthenticatedGitHubReadClient(authenticated_factory),
    )

    repository = client.resolve_repository(REPOSITORY)
    assert repository.head_revision == REVISION
    tree = client.read_tree(REPOSITORY, REVISION, max_entries=20)
    assert tuple(item.path for item in tree.entries) == ("README.md",)
    source = client.read_file(REPOSITORY, REVISION, "README.md", max_bytes=100)
    assert source.content == "hello"
    assert constructed is False


@pytest.mark.parametrize("method_name", ["create_branch", "commit_files", "create_pull_request", "read_pull_request"])
def test_public_first_bootstrap_denies_write_surface(method_name: str) -> None:
    client = PublicFirstGitHubReadClient(
        PublicGitHubReadClient(transport=httpx.MockTransport(_public_transport)),
        LazyAuthenticatedGitHubReadClient(lambda: (_ for _ in ()).throw(AssertionError())),
    )
    with pytest.raises(ProviderClientError, match="PROVIDER_AUTH_DENIED"):
        getattr(client, method_name)()


def test_private_repository_visibility_falls_back_to_exact_credential_path() -> None:
    def hidden(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is None
        return httpx.Response(404, json={"message": "Not Found"})

    class ExactCredentialPath:
        def resolve_repository(self, repository_ref: str):
            assert repository_ref == REPOSITORY
            raise ProviderClientError("REPOSITORY_AUTHORIZATION_REQUIRED")

    constructed = 0

    def authenticated_factory():
        nonlocal constructed
        constructed += 1
        return ExactCredentialPath()

    client = PublicFirstGitHubReadClient(
        PublicGitHubReadClient(transport=httpx.MockTransport(hidden)),
        LazyAuthenticatedGitHubReadClient(authenticated_factory),
    )
    with pytest.raises(ProviderClientError, match="REPOSITORY_AUTHORIZATION_REQUIRED"):
        client.resolve_repository(REPOSITORY)
    assert constructed == 1


def test_ambiguous_anonymous_repository_metadata_does_not_gain_public_authority() -> None:
    def ambiguous(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"full_name": "Ryan9876/ot-time", "default_branch": "main"},
        )

    constructed = False

    def authenticated_factory():
        nonlocal constructed
        constructed = True
        raise AssertionError("ambiguous anonymous metadata must fail closed")

    client = PublicFirstGitHubReadClient(
        PublicGitHubReadClient(transport=httpx.MockTransport(ambiguous)),
        LazyAuthenticatedGitHubReadClient(authenticated_factory),
    )
    with pytest.raises(ProviderClientError, match="REPOSITORY_NOT_PUBLIC"):
        client.resolve_repository(REPOSITORY)
    assert constructed is False
