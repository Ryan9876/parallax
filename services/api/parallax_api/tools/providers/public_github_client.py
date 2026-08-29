from __future__ import annotations

from collections.abc import Callable

import httpx

from .common import ProviderClientError
from .github_client import GitHubRestProviderClient


class _UnavailableCredentialProvider:
    def credential_for_repository(self, repository_ref: str):
        raise ProviderClientError("CREDENTIAL_UNAVAILABLE")


class PublicGitHubReadClient(GitHubRestProviderClient):
    """Anonymous GitHub REST access restricted to the inherited GET-only read surface.

    The repository metadata response must explicitly prove ``private == false``
    before anonymous source authority is accepted. A private or ambiguous response
    is not treated as public and cannot fall through to anonymous source reads.
    """

    def __init__(
        self,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout_seconds: float = 15.0,
    ) -> None:
        super().__init__(
            _UnavailableCredentialProvider(),
            transport=transport,
            timeout_seconds=timeout_seconds,
        )

    def _send(
        self,
        method: str,
        repository_ref: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        if method.upper() != "GET" or json is not None:
            raise ProviderClientError("PROVIDER_AUTH_DENIED")
        try:
            return self._http.request(
                "GET",
                path,
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "User-Agent": "Parallax-App-Builder-Public-Read",
                },
                params=params,
            )
        except httpx.TimeoutException as exc:
            raise ProviderClientError("PROVIDER_TIMEOUT") from exc
        except httpx.RequestError as exc:
            raise ProviderClientError("PROVIDER_UNAVAILABLE") from exc
        except ProviderClientError:
            raise
        except Exception as exc:
            raise ProviderClientError("PROVIDER_ERROR") from exc

    def resolve_repository(self, repository_ref: str):
        response = self._send("GET", repository_ref, self._repo_path(repository_ref))
        self._raise_status(response, not_found="REPOSITORY_NOT_FOUND")
        payload = self._json(response)
        if not isinstance(payload, dict) or payload.get("private") is not False:
            raise ProviderClientError("REPOSITORY_NOT_PUBLIC")
        # Reuse the established exact-identity/default-branch/head validation.
        return super().resolve_repository(repository_ref)


class LazyAuthenticatedGitHubReadClient:
    """Construct the credentialed client only after anonymous visibility fails."""

    def __init__(self, factory: Callable[[], GitHubRestProviderClient]) -> None:
        self._factory = factory
        self._client: GitHubRestProviderClient | None = None

    def _get(self) -> GitHubRestProviderClient:
        if self._client is None:
            self._client = self._factory()
        return self._client

    def resolve_repository(self, repository_ref: str):
        return self._get().resolve_repository(repository_ref)

    def read_tree(self, repository_ref: str, source_revision: str, *, max_entries: int):
        return self._get().read_tree(repository_ref, source_revision, max_entries=max_entries)

    def read_file(self, repository_ref: str, source_revision: str, path: str, *, max_bytes: int):
        return self._get().read_file(repository_ref, source_revision, path, max_bytes=max_bytes)


class PublicFirstGitHubReadClient:
    """Use credential-free public reads first; fall back only when necessary.

    A verified public repository normally never asks a deployment provider for
    a GitHub token. GitHub can throttle a shared anonymous egress address even
    for a public repository; that narrow failure falls back to the existing
    exact-repository credential path. Ambiguous metadata is rejected rather
    than reclassified as private.
    """

    def __init__(
        self,
        public_client: PublicGitHubReadClient,
        authenticated_client: LazyAuthenticatedGitHubReadClient,
    ) -> None:
        self._public = public_client
        self._authenticated = authenticated_client
        self._selected: object | None = None

    def resolve_repository(self, repository_ref: str):
        try:
            value = self._public.resolve_repository(repository_ref)
            self._selected = self._public
            return value
        except ProviderClientError as exc:
            if str(exc) not in {"REPOSITORY_NOT_FOUND", "PROVIDER_RATE_LIMITED"}:
                raise
        value = self._authenticated.resolve_repository(repository_ref)
        self._selected = self._authenticated
        return value

    def _reader(self):
        if self._selected is None:
            raise ProviderClientError("REPOSITORY_NOT_RESOLVED")
        return self._selected

    def read_tree(self, repository_ref: str, source_revision: str, *, max_entries: int):
        return self._reader().read_tree(repository_ref, source_revision, max_entries=max_entries)

    def read_file(self, repository_ref: str, source_revision: str, path: str, *, max_bytes: int):
        return self._reader().read_file(repository_ref, source_revision, path, max_bytes=max_bytes)

    def create_branch(self, *args, **kwargs):
        raise ProviderClientError("PROVIDER_AUTH_DENIED")

    def commit_files(self, *args, **kwargs):
        raise ProviderClientError("PROVIDER_AUTH_DENIED")

    def create_pull_request(self, *args, **kwargs):
        raise ProviderClientError("PROVIDER_AUTH_DENIED")

    def read_pull_request(self, *args, **kwargs):
        raise ProviderClientError("PROVIDER_AUTH_DENIED")


__all__ = [
    "LazyAuthenticatedGitHubReadClient",
    "PublicFirstGitHubReadClient",
    "PublicGitHubReadClient",
]
