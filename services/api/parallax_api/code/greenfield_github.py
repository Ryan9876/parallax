from __future__ import annotations

import base64
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from ..tools.providers.common import (
    AuthorizedProviderExecutor,
    ProviderActionSuccess,
    ProviderClientError,
    ProviderInvocation,
    ProviderProjectBinding,
    require_repository_ref,
    require_sha256,
    require_source_revision,
    safe_provider_call,
)
from ..tools.providers.github import GITHUB_TOOL
from ..tools.providers.github_client import GitHubRestProviderClient
from ..tools.registry import ToolCapabilityRegistry


ACTION_REPOSITORY_INSPECT = "repository.inspect"
ACTION_REPOSITORY_INITIALIZE_EMPTY = "repository.initialize-empty"
_BOOTSTRAP_PATH = ".parallax-greenfield"
_BOOTSTRAP_VERSION = "parallax-greenfield-v1"
_BOOTSTRAP_MESSAGE = "Initialize Parallax greenfield baseline"
_CLEANUP_MESSAGE = "Finalize Parallax empty greenfield baseline"
_ACTOR = {
    "name": "Parallax App Builder",
    "email": "parallax-app-builder@users.noreply.github.com",
    "date": "2000-01-01T00:00:00Z",
}


def _dict(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    return value


def _list(value: object) -> list[Any]:
    if not isinstance(value, list):
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    return value


def _text(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
    return value


def _bootstrap_content(provenance_digest: str) -> str:
    require_sha256(provenance_digest, field="provenance_digest")
    return f"{_BOOTSTRAP_VERSION}\nprovenance={provenance_digest}\n"


@dataclass(frozen=True, slots=True)
class GreenfieldRepositoryInspection:
    repository_ref: str
    default_branch: str
    head_revision: str | None

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_source_revision(self.default_branch, field="default_branch")
        if self.head_revision is not None:
            require_source_revision(self.head_revision, field="head_revision")

    @property
    def is_empty(self) -> bool:
        return self.head_revision is None


@dataclass(frozen=True, slots=True)
class GreenfieldBaselineResult:
    repository_ref: str
    default_branch: str
    baseline_revision: str
    bootstrap_revision: str
    provenance_digest: str
    initialized: bool

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_source_revision(self.default_branch, field="default_branch")
        require_source_revision(self.baseline_revision, field="baseline_revision")
        require_source_revision(self.bootstrap_revision, field="bootstrap_revision")
        require_sha256(self.provenance_digest, field="provenance_digest")
        if not isinstance(self.initialized, bool):
            raise TypeError("initialized must be bool")


class GreenfieldGitHubClient:
    """Narrow REST adapter for positive empty inspection and REVIEW-only initialization."""

    def __init__(self, delegate: GitHubRestProviderClient) -> None:
        if not isinstance(delegate, GitHubRestProviderClient):
            raise TypeError("greenfield GitHub operations require the protected REST client")
        self._delegate = delegate

    def inspect_repository(self, repository_ref: str) -> GreenfieldRepositoryInspection:
        owner, repository = repository_ref.removeprefix("github:").split("/", 1)
        response = self._delegate._send("GET", repository_ref, self._delegate._repo_path(repository_ref))
        self._delegate._raise_status(response, not_found="REPOSITORY_NOT_FOUND")
        payload = _dict(self._delegate._json(response))
        full_name = _text(payload.get("full_name"))
        if full_name.casefold() != f"{owner}/{repository}".casefold():
            raise ProviderClientError("REPOSITORY_MISMATCH")
        default_branch = _text(payload.get("default_branch"))
        head = self._delegate._get_ref(repository_ref, default_branch)
        return GreenfieldRepositoryInspection(repository_ref, default_branch, head)

    @staticmethod
    def _verify_actor(payload: dict[str, Any]) -> None:
        for field in ("author", "committer"):
            actor = _dict(payload.get(field))
            if any(actor.get(key) != value for key, value in _ACTOR.items()):
                raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")

    def _commit(self, repository_ref: str, revision: str) -> dict[str, Any]:
        require_source_revision(revision, field="revision")
        response = self._delegate._send(
            "GET",
            repository_ref,
            f"{self._delegate._repo_path(repository_ref)}/git/commits/{revision}",
        )
        self._delegate._raise_status(response, not_found="SOURCE_NOT_FOUND")
        return _dict(self._delegate._json(response))

    def _tree(self, repository_ref: str, revision: str) -> tuple[dict[str, Any], ...]:
        response = self._delegate._send(
            "GET",
            repository_ref,
            f"{self._delegate._repo_path(repository_ref)}/git/trees/{revision}",
            params={"recursive": "1"},
        )
        self._delegate._raise_status(response, not_found="SOURCE_NOT_FOUND")
        payload = _dict(self._delegate._json(response))
        if payload.get("truncated") is True:
            raise ProviderClientError("SOURCE_TREE_TRUNCATED")
        return tuple(_dict(item) for item in _list(payload.get("tree")))

    def _verify_baseline(
        self,
        repository_ref: str,
        default_branch: str,
        baseline_revision: str,
        provenance_digest: str,
    ) -> GreenfieldBaselineResult:
        cleanup = self._commit(repository_ref, baseline_revision)
        self._verify_actor(cleanup)
        if cleanup.get("message") != _CLEANUP_MESSAGE:
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        parents = _list(cleanup.get("parents"))
        if len(parents) != 1 or not isinstance(parents[0], dict):
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        bootstrap_revision = _text(parents[0].get("sha"))
        if self._tree(repository_ref, baseline_revision):
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")

        bootstrap = self._commit(repository_ref, bootstrap_revision)
        self._verify_actor(bootstrap)
        if bootstrap.get("message") != _BOOTSTRAP_MESSAGE or _list(bootstrap.get("parents")):
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        entries = self._tree(repository_ref, bootstrap_revision)
        if len(entries) != 1:
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        entry = entries[0]
        expected = _bootstrap_content(provenance_digest)
        if entry.get("path") != _BOOTSTRAP_PATH or entry.get("type") != "blob" or entry.get("mode") != "100644":
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        blob_sha = _text(entry.get("sha"))
        response = self._delegate._send(
            "GET",
            repository_ref,
            f"{self._delegate._repo_path(repository_ref)}/git/blobs/{blob_sha}",
        )
        self._delegate._raise_status(response, not_found="SOURCE_NOT_FOUND")
        blob = _dict(self._delegate._json(response))
        if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE")
        try:
            decoded = base64.b64decode("".join(blob["content"].split()), validate=True).decode("utf-8")
        except Exception as exc:
            raise ProviderClientError("PROVIDER_INVALID_RESPONSE") from exc
        if decoded != expected or sha256(decoded.encode("utf-8")).hexdigest() != sha256(expected.encode("utf-8")).hexdigest():
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        current = self._delegate._get_ref(repository_ref, default_branch)
        if current != baseline_revision:
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        return GreenfieldBaselineResult(
            repository_ref,
            default_branch,
            baseline_revision,
            bootstrap_revision,
            provenance_digest,
            False,
        )

    def initialize_empty_baseline(
        self,
        repository_ref: str,
        provenance_digest: str,
    ) -> GreenfieldBaselineResult:
        require_sha256(provenance_digest, field="provenance_digest")
        state = self.inspect_repository(repository_ref)
        if state.head_revision is not None:
            return self._verify_baseline(
                repository_ref,
                state.default_branch,
                state.head_revision,
                provenance_digest,
            )

        content = _bootstrap_content(provenance_digest)
        endpoint = f"{self._delegate._repo_path(repository_ref)}/contents/{_BOOTSTRAP_PATH}"
        create = self._delegate._send(
            "PUT",
            repository_ref,
            endpoint,
            json={
                "message": _BOOTSTRAP_MESSAGE,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
                "branch": state.default_branch,
                "committer": _ACTOR,
                "author": _ACTOR,
            },
        )
        self._delegate._raise_status(create, conflict="GREENFIELD_INITIALIZATION_CONFLICT")
        created = _dict(self._delegate._json(create))
        bootstrap_revision = _text(_dict(created.get("commit")).get("sha"))
        blob_sha = _text(_dict(created.get("content")).get("sha"))

        delete = self._delegate._send(
            "DELETE",
            repository_ref,
            endpoint,
            json={
                "message": _CLEANUP_MESSAGE,
                "sha": blob_sha,
                "branch": state.default_branch,
                "committer": _ACTOR,
                "author": _ACTOR,
            },
        )
        self._delegate._raise_status(delete, conflict="GREENFIELD_INITIALIZATION_CONFLICT")
        deleted = _dict(self._delegate._json(delete))
        baseline_revision = _text(_dict(deleted.get("commit")).get("sha"))
        result = self._verify_baseline(
            repository_ref,
            state.default_branch,
            baseline_revision,
            provenance_digest,
        )
        if result.bootstrap_revision != bootstrap_revision:
            raise ProviderClientError("GREENFIELD_BASELINE_MISMATCH")
        return GreenfieldBaselineResult(
            result.repository_ref,
            result.default_branch,
            result.baseline_revision,
            result.bootstrap_revision,
            result.provenance_digest,
            True,
        )


class GreenfieldGitHubActions:
    """Typed authority boundary for greenfield inspection and REVIEW initialization."""

    def __init__(
        self,
        registry: ToolCapabilityRegistry,
        client: GreenfieldGitHubClient,
    ) -> None:
        self.executor = AuthorizedProviderExecutor(registry)
        self.client = client

    def _run(
        self,
        *,
        action: str,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        operation,
        result_code: str,
    ) -> ProviderActionSuccess:
        request, decision = self.executor.authorize(
            binding=binding,
            invocation=invocation,
            tool=GITHUB_TOOL,
            action=action,
        )
        try:
            value = safe_provider_call(operation)
            if value.repository_ref != binding.repository_ref:
                raise ProviderClientError("REPOSITORY_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=action,
                error=exc,
            ) from exc
        identity = value.head_revision if isinstance(value, GreenfieldRepositoryInspection) else value.baseline_revision
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=action,
            value=value,
            result_code=result_code,
            result_identity=identity or value.default_branch,
            source_revision=identity,
        )

    def inspect_repository(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
    ) -> ProviderActionSuccess[GreenfieldRepositoryInspection]:
        return self._run(
            action=ACTION_REPOSITORY_INSPECT,
            binding=binding,
            invocation=invocation,
            operation=lambda: self.client.inspect_repository(binding.repository_ref),
            result_code="REPOSITORY_INSPECTED",
        )

    def initialize_empty_baseline(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        provenance_digest: str,
    ) -> ProviderActionSuccess[GreenfieldBaselineResult]:
        require_sha256(provenance_digest, field="provenance_digest")
        return self._run(
            action=ACTION_REPOSITORY_INITIALIZE_EMPTY,
            binding=binding,
            invocation=invocation,
            operation=lambda: self.client.initialize_empty_baseline(
                binding.repository_ref,
                provenance_digest,
            ),
            result_code="GREENFIELD_BASELINE_READY",
        )


__all__ = [
    "ACTION_REPOSITORY_INITIALIZE_EMPTY",
    "ACTION_REPOSITORY_INSPECT",
    "GreenfieldBaselineResult",
    "GreenfieldGitHubActions",
    "GreenfieldGitHubClient",
    "GreenfieldRepositoryInspection",
]
