from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Protocol
from urllib.parse import urlparse

from .common import (
    AcceptedSourceLineage,
    AuthorizedProviderExecutor,
    ProviderActionSuccess,
    ProviderClientError,
    ProviderInvocation,
    ProviderProjectBinding,
    require_app_branch,
    require_https_url,
    require_repository_ref,
    require_sha256,
    require_source_lineage_id,
    require_source_revision,
    safe_provider_call,
)
from ..registry import ToolCapabilityRegistry


GITHUB_TOOL = "github"
ACTION_REPOSITORY_RESOLVE = "repository.resolve"
ACTION_SOURCE_TREE_READ = "source.tree.read"
ACTION_SOURCE_FILE_READ = "source.file.read"
ACTION_BRANCH_CREATE = "branch.create"
ACTION_COMMIT_WRITE = "commit.write"
ACTION_PULL_REQUEST_CREATE = "pull_request.create"
ACTION_PULL_REQUEST_READ = "pull_request.read"

MAX_TREE_ENTRIES = 512
MAX_FILE_BYTES = 256_000
MAX_COMMIT_FILES = 32
MAX_COMMIT_FILE_BYTES = 256_000
MAX_COMMIT_TOTAL_BYTES = 2_000_000
MAX_PR_TITLE = 160
MAX_PR_BODY = 8_000

_PATH = re.compile(r"^[A-Za-z0-9._-](?:[A-Za-z0-9._/ -]{0,238}[A-Za-z0-9._-])?$")
_SECRET_VALUE = re.compile(
    r"(?i)(api[_-]?key|secret|token|authorization|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{16,}"
)
_SECRET_PATH_PARTS = frozenset({".env", ".env.local", ".env.production", "secrets", "credentials"})


def _require_path(value: str) -> str:
    if not isinstance(value, str) or not _PATH.fullmatch(value):
        raise ValueError("source path must be a bounded relative text path")
    parts = value.split("/")
    lowered_parts = {part.casefold() for part in parts}
    if value.startswith("/") or ".." in parts or lowered_parts & _SECRET_PATH_PARTS:
        raise ValueError("source path is outside the safe publication boundary")
    return value


def _require_bounded_text(value: str, *, field: str, maximum: int, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be text")
    encoded = value.encode("utf-8")
    if (not value.strip() and not allow_empty) or len(encoded) > maximum:
        raise ValueError(f"{field} exceeds its bounded text contract")
    if "\x00" in value:
        raise ValueError(f"{field} must be UTF-8 text without NUL bytes")
    return value


def _reject_secret_literal(value: str, *, field: str) -> None:
    if _SECRET_VALUE.search(value):
        raise ValueError(f"{field} contains possible secret-bearing content")


def _require_pull_request_url(repository_ref: str, number: int, url: str) -> str:
    require_https_url(url, field="url", allowed_suffix="github.com")
    parsed = urlparse(url)
    if parsed.query:
        raise ValueError("pull request URL must not contain query parameters")
    owner_repo = repository_ref.removeprefix("github:")
    expected_path = f"/{owner_repo}/pull/{number}"
    if parsed.path.rstrip("/") != expected_path:
        raise ValueError("pull request URL does not match repository and pull request identity")
    return url


@dataclass(frozen=True, slots=True)
class GitHubRepositoryState:
    repository_ref: str
    default_branch: str
    head_revision: str

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_source_revision(self.default_branch, field="default_branch")
        require_source_revision(self.head_revision, field="head_revision")


@dataclass(frozen=True, slots=True)
class GitHubTreeEntry:
    path: str
    kind: str
    size: int
    object_revision: str

    def __post_init__(self) -> None:
        _require_path(self.path)
        if self.kind not in {"file", "tree"}:
            raise ValueError("tree entry kind must be file or tree")
        if not isinstance(self.size, int) or isinstance(self.size, bool) or not 0 <= self.size <= MAX_FILE_BYTES:
            raise ValueError("tree entry size is outside the bounded source contract")
        require_source_revision(self.object_revision, field="object_revision")


@dataclass(frozen=True, slots=True)
class GitHubTreeResult:
    repository_ref: str
    source_revision: str
    entries: tuple[GitHubTreeEntry, ...]

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_source_revision(self.source_revision)
        if not isinstance(self.entries, tuple) or len(self.entries) > MAX_TREE_ENTRIES:
            raise ValueError("tree result exceeds the bounded entry limit")
        if not all(isinstance(entry, GitHubTreeEntry) for entry in self.entries):
            raise TypeError("entries must contain GitHubTreeEntry values")


@dataclass(frozen=True, slots=True)
class GitHubFileResult:
    repository_ref: str
    source_revision: str
    path: str
    content: str
    content_sha256: str

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_source_revision(self.source_revision)
        _require_path(self.path)
        _require_bounded_text(self.content, field="content", maximum=MAX_FILE_BYTES, allow_empty=True)
        _reject_secret_literal(self.content, field="content")
        require_sha256(self.content_sha256, field="content_sha256")
        if sha256(self.content.encode("utf-8")).hexdigest() != self.content_sha256:
            raise ValueError("file content digest does not match content")


@dataclass(frozen=True, slots=True)
class GitHubCommitFile:
    path: str
    content: str
    content_sha256: str

    def __post_init__(self) -> None:
        _require_path(self.path)
        _require_bounded_text(self.content, field="content", maximum=MAX_COMMIT_FILE_BYTES, allow_empty=True)
        _reject_secret_literal(self.content, field="content")
        require_sha256(self.content_sha256, field="content_sha256")
        if sha256(self.content.encode("utf-8")).hexdigest() != self.content_sha256:
            raise ValueError("commit file digest does not match content")


@dataclass(frozen=True, slots=True)
class GitHubBranchResult:
    repository_ref: str
    branch_name: str
    base_revision: str
    head_revision: str

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_app_branch(self.branch_name)
        require_source_revision(self.base_revision, field="base_revision")
        require_source_revision(self.head_revision, field="head_revision")


@dataclass(frozen=True, slots=True)
class GitHubCommitResult:
    repository_ref: str
    branch_name: str
    parent_revision: str
    commit_revision: str
    lineage_id: str
    content_digest: str

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        require_app_branch(self.branch_name)
        require_source_revision(self.parent_revision, field="parent_revision")
        require_source_revision(self.commit_revision, field="commit_revision")
        require_source_lineage_id(self.lineage_id)
        require_sha256(self.content_digest, field="content_digest")


@dataclass(frozen=True, slots=True)
class GitHubPullRequestResult:
    repository_ref: str
    number: int
    head_branch: str
    head_revision: str
    base_branch: str
    state: str
    url: str

    def __post_init__(self) -> None:
        require_repository_ref(self.repository_ref)
        if not isinstance(self.number, int) or isinstance(self.number, bool) or not 1 <= self.number <= 2_147_483_647:
            raise ValueError("pull request number is invalid")
        require_app_branch(self.head_branch)
        require_source_revision(self.head_revision, field="head_revision")
        require_source_revision(self.base_branch, field="base_branch")
        if self.state not in {"OPEN", "CLOSED"}:
            raise ValueError("pull request state must be OPEN or CLOSED")
        _require_pull_request_url(self.repository_ref, self.number, self.url)


class GitHubProviderClient(Protocol):
    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState: ...

    def read_tree(
        self,
        repository_ref: str,
        source_revision: str,
        *,
        max_entries: int,
    ) -> GitHubTreeResult: ...

    def read_file(
        self,
        repository_ref: str,
        source_revision: str,
        path: str,
        *,
        max_bytes: int,
    ) -> GitHubFileResult: ...

    def create_branch(
        self,
        repository_ref: str,
        branch_name: str,
        base_revision: str,
    ) -> GitHubBranchResult: ...

    def commit_files(
        self,
        repository_ref: str,
        branch_name: str,
        expected_parent_revision: str,
        lineage: AcceptedSourceLineage,
        files: tuple[GitHubCommitFile, ...],
    ) -> GitHubCommitResult: ...

    def create_pull_request(
        self,
        repository_ref: str,
        head_branch: str,
        expected_head_revision: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> GitHubPullRequestResult: ...

    def read_pull_request(
        self,
        repository_ref: str,
        number: int,
    ) -> GitHubPullRequestResult: ...


class GitHubProviderActions:
    """Fixed GitHub source/review actions underneath the Wave 1 authority registry."""

    def __init__(self, registry: ToolCapabilityRegistry, client: GitHubProviderClient) -> None:
        self.executor = AuthorizedProviderExecutor(registry)
        self.client = client

    def _authorize(
        self,
        action: str,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
    ):
        return self.executor.authorize(
            binding=binding,
            invocation=invocation,
            tool=GITHUB_TOOL,
            action=action,
        )

    @staticmethod
    def _verify_repository(binding: ProviderProjectBinding, repository_ref: str) -> None:
        if repository_ref != binding.repository_ref:
            raise ProviderClientError("REPOSITORY_MISMATCH")

    @staticmethod
    def _verify_lineage(binding: ProviderProjectBinding, lineage: AcceptedSourceLineage) -> None:
        if not isinstance(lineage, AcceptedSourceLineage):
            raise TypeError("lineage must be AcceptedSourceLineage")
        if lineage.project_id != binding.project_ref:
            raise ValueError("accepted source lineage belongs to a different Project")

    def resolve_repository(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
    ) -> ProviderActionSuccess[GitHubRepositoryState]:
        request, decision = self._authorize(ACTION_REPOSITORY_RESOLVE, binding, invocation)
        try:
            value = safe_provider_call(lambda: self.client.resolve_repository(binding.repository_ref))
            self._verify_repository(binding, value.repository_ref)
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_REPOSITORY_RESOLVE,
                error=exc,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_REPOSITORY_RESOLVE,
            value=value,
            result_code="REPOSITORY_RESOLVED",
            result_identity=value.head_revision,
            source_revision=value.head_revision,
        )

    def read_tree(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        source_revision: str,
    ) -> ProviderActionSuccess[GitHubTreeResult]:
        require_source_revision(source_revision)
        request, decision = self._authorize(ACTION_SOURCE_TREE_READ, binding, invocation)
        try:
            value = safe_provider_call(
                lambda: self.client.read_tree(
                    binding.repository_ref,
                    source_revision,
                    max_entries=MAX_TREE_ENTRIES,
                )
            )
            self._verify_repository(binding, value.repository_ref)
            if value.source_revision != source_revision:
                raise ProviderClientError("SOURCE_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_SOURCE_TREE_READ,
                error=exc,
                source_revision=source_revision,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_SOURCE_TREE_READ,
            value=value,
            result_code="SOURCE_TREE_READ",
            result_identity=source_revision,
            source_revision=source_revision,
        )

    def read_file(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        source_revision: str,
        path: str,
    ) -> ProviderActionSuccess[GitHubFileResult]:
        require_source_revision(source_revision)
        _require_path(path)
        request, decision = self._authorize(ACTION_SOURCE_FILE_READ, binding, invocation)
        try:
            value = safe_provider_call(
                lambda: self.client.read_file(
                    binding.repository_ref,
                    source_revision,
                    path,
                    max_bytes=MAX_FILE_BYTES,
                )
            )
            self._verify_repository(binding, value.repository_ref)
            if value.source_revision != source_revision or value.path != path:
                raise ProviderClientError("SOURCE_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_SOURCE_FILE_READ,
                error=exc,
                source_revision=source_revision,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_SOURCE_FILE_READ,
            value=value,
            result_code="SOURCE_FILE_READ",
            result_identity=value.content_sha256,
            source_revision=source_revision,
        )

    def create_branch(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        branch_name: str,
        base_revision: str,
    ) -> ProviderActionSuccess[GitHubBranchResult]:
        require_app_branch(branch_name)
        require_source_revision(base_revision, field="base_revision")
        request, decision = self._authorize(ACTION_BRANCH_CREATE, binding, invocation)
        try:
            value = safe_provider_call(
                lambda: self.client.create_branch(binding.repository_ref, branch_name, base_revision)
            )
            self._verify_repository(binding, value.repository_ref)
            if value.branch_name != branch_name or value.base_revision != base_revision:
                raise ProviderClientError("SOURCE_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_BRANCH_CREATE,
                error=exc,
                source_revision=base_revision,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_BRANCH_CREATE,
            value=value,
            result_code="BRANCH_CREATED",
            result_identity=value.branch_name,
            source_revision=value.head_revision,
        )

    def commit_accepted_lineage(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        branch_name: str,
        expected_parent_revision: str,
        lineage: AcceptedSourceLineage,
        files: tuple[GitHubCommitFile, ...],
    ) -> ProviderActionSuccess[GitHubCommitResult]:
        require_app_branch(branch_name)
        require_source_revision(expected_parent_revision, field="expected_parent_revision")
        self._verify_lineage(binding, lineage)
        if not isinstance(files, tuple) or not 1 <= len(files) <= MAX_COMMIT_FILES:
            raise ValueError("commit files must be a bounded non-empty tuple")
        if not all(isinstance(item, GitHubCommitFile) for item in files):
            raise TypeError("files must contain GitHubCommitFile values")
        if len({item.path for item in files}) != len(files):
            raise ValueError("commit files must have unique paths")
        if sum(len(item.content.encode("utf-8")) for item in files) > MAX_COMMIT_TOTAL_BYTES:
            raise ValueError("commit files exceed the aggregate byte limit")

        request, decision = self._authorize(ACTION_COMMIT_WRITE, binding, invocation)
        try:
            value = safe_provider_call(
                lambda: self.client.commit_files(
                    binding.repository_ref,
                    branch_name,
                    expected_parent_revision,
                    lineage,
                    files,
                )
            )
            self._verify_repository(binding, value.repository_ref)
            if (
                value.branch_name != branch_name
                or value.parent_revision != expected_parent_revision
                or value.lineage_id != lineage.lineage_id
                or value.content_digest != lineage.content_digest
            ):
                raise ProviderClientError("LINEAGE_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_COMMIT_WRITE,
                error=exc,
                source_revision=expected_parent_revision,
                lineage=lineage,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_COMMIT_WRITE,
            value=value,
            result_code="COMMIT_WRITTEN",
            result_identity=value.commit_revision,
            source_revision=value.commit_revision,
            lineage=lineage,
        )

    def create_pull_request(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        head_branch: str,
        expected_head_revision: str,
        base_branch: str,
        lineage: AcceptedSourceLineage,
        title: str,
        body: str = "",
    ) -> ProviderActionSuccess[GitHubPullRequestResult]:
        require_app_branch(head_branch)
        require_source_revision(expected_head_revision, field="expected_head_revision")
        require_source_revision(base_branch, field="base_branch")
        self._verify_lineage(binding, lineage)
        _require_bounded_text(title, field="title", maximum=MAX_PR_TITLE)
        _require_bounded_text(body, field="body", maximum=MAX_PR_BODY, allow_empty=True)
        _reject_secret_literal(title, field="title")
        _reject_secret_literal(body, field="body")
        request, decision = self._authorize(ACTION_PULL_REQUEST_CREATE, binding, invocation)
        try:
            value = safe_provider_call(
                lambda: self.client.create_pull_request(
                    binding.repository_ref,
                    head_branch,
                    expected_head_revision,
                    base_branch,
                    title,
                    body,
                )
            )
            self._verify_repository(binding, value.repository_ref)
            if (
                value.head_branch != head_branch
                or value.head_revision != expected_head_revision
                or value.base_branch != base_branch
            ):
                raise ProviderClientError("SOURCE_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_PULL_REQUEST_CREATE,
                error=exc,
                source_revision=expected_head_revision,
                lineage=lineage,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_PULL_REQUEST_CREATE,
            value=value,
            result_code="PULL_REQUEST_CREATED",
            result_identity=f"pr:{value.number}",
            source_revision=expected_head_revision,
            lineage=lineage,
            safe_url=value.url,
        )

    def read_pull_request(
        self,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        *,
        number: int,
    ) -> ProviderActionSuccess[GitHubPullRequestResult]:
        if not isinstance(number, int) or isinstance(number, bool) or not 1 <= number <= 2_147_483_647:
            raise ValueError("pull request number is invalid")
        request, decision = self._authorize(ACTION_PULL_REQUEST_READ, binding, invocation)
        try:
            value = safe_provider_call(lambda: self.client.read_pull_request(binding.repository_ref, number))
            self._verify_repository(binding, value.repository_ref)
            if value.number != number:
                raise ProviderClientError("PULL_REQUEST_MISMATCH")
        except ProviderClientError as exc:
            raise self.executor.fail(
                request=request,
                decision=decision,
                binding=binding,
                action=ACTION_PULL_REQUEST_READ,
                error=exc,
            ) from exc
        return self.executor.succeed(
            request=request,
            decision=decision,
            binding=binding,
            action=ACTION_PULL_REQUEST_READ,
            value=value,
            result_code="PULL_REQUEST_READ",
            result_identity=f"pr:{value.number}",
            source_revision=value.head_revision,
            safe_url=value.url,
        )
