from __future__ import annotations

from io import BytesIO
import tarfile

import httpx
import pytest

from parallax_api.code.public_github_archive import PublicGitHubArchiveReadClient
from parallax_api.tools.providers.common import ProviderClientError
from parallax_api.tools.providers.public_github_client import (
    LazyAuthenticatedGitHubReadClient,
    PublicFirstGitHubReadClient,
)


REPOSITORY = "github:Ryan9876/sickbeard"
REVISION = "a" * 40


def _pkt_line(value: bytes) -> bytes:
    return f"{len(value) + 4:04x}".encode("ascii") + value


def _advertisement() -> bytes:
    return b"".join(
        (
            _pkt_line(b"# service=git-upload-pack\n"),
            b"0000",
            _pkt_line(
                f"{REVISION} HEAD\x00symref=HEAD:refs/heads/main object-format=sha1 agent=git/github\n".encode(
                    "ascii"
                )
            ),
            _pkt_line(f"{REVISION} refs/heads/main\n".encode("ascii")),
            b"0000",
        )
    )


def _archive(*, include_secret: bool = False, include_symlink: bool = False) -> bytes:
    target = BytesIO()
    root = f"sickbeard-{REVISION}"
    with tarfile.open(fileobj=target, mode="w:gz") as bundle:
        for path, content in (
            ("README.md", b"hello\n"),
            ("src/app.py", b"print('ok')\n"),
        ):
            info = tarfile.TarInfo(f"{root}/{path}")
            info.size = len(content)
            info.mode = 0o644
            bundle.addfile(info, BytesIO(content))
        if include_secret:
            content = b"SHOULD_NOT_BE_READ"
            info = tarfile.TarInfo(f"{root}/.env")
            info.size = len(content)
            info.mode = 0o600
            bundle.addfile(info, BytesIO(content))
        if include_symlink:
            info = tarfile.TarInfo(f"{root}/unsafe-link")
            info.type = tarfile.SYMTYPE
            info.linkname = "README.md"
            bundle.addfile(info)
    return target.getvalue()


def _transport(*, include_secret: bool = False, include_symlink: bool = False):
    archive = _archive(include_secret=include_secret, include_symlink=include_symlink)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is None
        if request.url.host == "github.com":
            assert request.url.path == "/Ryan9876/sickbeard.git/info/refs"
            assert request.url.params.get("service") == "git-upload-pack"
            return httpx.Response(
                200,
                headers={"content-type": "application/x-git-upload-pack-advertisement"},
                content=_advertisement(),
            )
        if request.url.host == "codeload.github.com":
            assert request.url.path == f"/Ryan9876/sickbeard/tar.gz/{REVISION}"
            return httpx.Response(200, content=archive)
        raise AssertionError(f"unexpected public source request: {request.method} {request.url}")

    return httpx.MockTransport(handler)


def test_public_source_resolves_exact_head_and_reads_commit_archive_without_rest() -> None:
    client = PublicGitHubArchiveReadClient(transport=_transport())

    repository = client.resolve_repository(REPOSITORY)
    assert repository.default_branch == "main"
    assert repository.head_revision == REVISION

    tree = client.read_tree(REPOSITORY, REVISION, max_entries=20)
    assert tuple(item.path for item in tree.entries) == ("README.md", "src/app.py")

    source = client.read_file(REPOSITORY, REVISION, "src/app.py", max_bytes=1_000)
    assert source.content == "print('ok')\n"
    assert source.source_revision == REVISION


def test_public_source_omits_secret_sensitive_archive_paths_before_projection() -> None:
    client = PublicGitHubArchiveReadClient(transport=_transport(include_secret=True))
    client.resolve_repository(REPOSITORY)

    tree = client.read_tree(REPOSITORY, REVISION, max_entries=20)
    assert ".env" not in {item.path for item in tree.entries}
    with pytest.raises(ProviderClientError, match="SOURCE_PATH_EXCLUDED"):
        client.read_file(REPOSITORY, REVISION, ".env", max_bytes=1_000)


def test_public_source_rejects_symlinks_like_existing_git_tree_policy() -> None:
    client = PublicGitHubArchiveReadClient(transport=_transport(include_symlink=True))
    with pytest.raises(ProviderClientError, match="UNSUPPORTED_SOURCE_ENTRY"):
        client.resolve_repository(REPOSITORY)


def test_hidden_public_source_may_enter_exact_private_credential_path() -> None:
    def hidden(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is None
        return httpx.Response(404)

    class ExactCredentialPath:
        def resolve_repository(self, repository_ref: str):
            assert repository_ref == REPOSITORY
            return "credentialed-resolution"

    constructed = 0

    def authenticated_factory():
        nonlocal constructed
        constructed += 1
        return ExactCredentialPath()

    client = PublicFirstGitHubReadClient(
        PublicGitHubArchiveReadClient(transport=httpx.MockTransport(hidden)),
        LazyAuthenticatedGitHubReadClient(authenticated_factory),
    )
    assert client.resolve_repository(REPOSITORY) == "credentialed-resolution"
    assert constructed == 1


def test_public_source_rate_limit_does_not_create_deployment_provider_dependency() -> None:
    def rate_limited(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is None
        return httpx.Response(429, headers={"retry-after": "60"})

    constructed = False

    def authenticated_factory():
        nonlocal constructed
        constructed = True
        raise AssertionError("public-source throttling must not construct a credentialed fallback")

    client = PublicFirstGitHubReadClient(
        PublicGitHubArchiveReadClient(transport=httpx.MockTransport(rate_limited)),
        LazyAuthenticatedGitHubReadClient(authenticated_factory),
    )
    with pytest.raises(ProviderClientError, match="PROVIDER_RATE_LIMITED"):
        client.resolve_repository(REPOSITORY)
    assert constructed is False
