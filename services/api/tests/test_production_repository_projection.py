from __future__ import annotations

import base64
from hashlib import sha256
from pathlib import Path
import subprocess
from threading import Barrier, Lock
from types import SimpleNamespace

import httpx
import pytest

from parallax_api.code.production_source_projection import (
    _PROJECTED_READ_WORKERS,
    ProjectedGitHubFileResult,
    ProjectedGitHubReadClient,
    ProjectedRepositoryBoundSourceProvider,
    is_lineage_secret_sensitive_path,
)
from parallax_api.code.workspace_lineage import (
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePolicyError,
)
from parallax_api.tools.providers import (
    GitHubCommitFile,
    GitHubFileResult,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
    ProviderClientError,
    ProviderInvocation,
    ProviderProjectBinding,
)
from parallax_api.tools.providers.credentials import ProviderCredentialKind, ScopedBearerCredential
from parallax_api.tools.providers.github import MAX_FILE_BYTES, MAX_TREE_ENTRIES
from parallax_api.tools.providers.github_client import GitHubRestProviderClient


PROJECT_ID = "11111111-1111-1111-1111-111111111111"
RUN_ID = "22222222-2222-2222-2222-222222222222"
REPOSITORY = "github:Ryan9876/parallax"
REVISION = "a" * 40


class _Invocations:
    def for_action(self, *, tool: str, action: str, operation_key: str) -> ProviderInvocation:
        assert tool == "github"
        assert action
        assert operation_key
        return ProviderInvocation(
            request_id="request:projection",
            capability_id="cap:projection",
            actor_ref="actor:projection",
        )


class _GitHub:
    def __init__(self) -> None:
        self.file_reads: list[str] = []
        self._contents = {
            "apps/client/assets/parallax-lens-mark.svg": "<svg></svg>\n",
            "apps/client/src/components/ParallaxLogo.tsx": "export const ParallaxLogo = () => null;\n",
        }

    def resolve_repository(self, binding, invocation):
        assert binding.repository_ref == REPOSITORY
        return SimpleNamespace(value=GitHubRepositoryState(REPOSITORY, "main", REVISION))

    def read_tree(self, binding, invocation, *, source_revision: str):
        assert source_revision == REVISION
        entries = (
            GitHubTreeEntry("apps/client/.env.example", "file", 20, "1" * 40),
            GitHubTreeEntry("apps/client/assets/parallax-lens-mark.svg", "file", 12, "2" * 40),
            GitHubTreeEntry("apps/client/src/components/ParallaxLogo.tsx", "file", 40, "3" * 40),
            GitHubTreeEntry("services/api/private.pem", "file", 20, "4" * 40),
            GitHubTreeEntry("tools/.ssh/config", "file", 20, "5" * 40),
        )
        return SimpleNamespace(value=GitHubTreeResult(REPOSITORY, REVISION, entries))

    def read_file(self, binding, invocation, *, source_revision: str, path: str):
        assert source_revision == REVISION
        self.file_reads.append(path)
        content = self._contents[path]
        return SimpleNamespace(
            value=GitHubFileResult(
                REPOSITORY,
                REVISION,
                path,
                content,
                sha256(content.encode()).hexdigest(),
            )
        )


class _ConcurrentGitHub(_GitHub):
    def __init__(self) -> None:
        super().__init__()
        self._barrier = Barrier(2)
        self._lock = Lock()
        self.active_reads = 0
        self.max_active_reads = 0

    def read_file(self, binding, invocation, *, source_revision: str, path: str):
        with self._lock:
            self.active_reads += 1
            self.max_active_reads = max(self.max_active_reads, self.active_reads)
        try:
            # This intentionally requires two provider reads to overlap. The
            # former sequential implementation cannot cross this barrier.
            self._barrier.wait(timeout=2)
            return super().read_file(
                binding,
                invocation,
                source_revision=source_revision,
                path=path,
            )
        finally:
            with self._lock:
                self.active_reads -= 1


class _CredentialProvider:
    def credential_for_repository(self, repository_ref: str) -> ScopedBearerCredential:
        assert repository_ref == REPOSITORY
        return ScopedBearerCredential(
            provider="github",
            resource_ref=repository_ref,
            kind=ProviderCredentialKind.GITHUB_APP_INSTALLATION,
            secret="projection-test-token",
            expires_at=None,
        )


def test_lineage_safe_projection_omits_secret_sensitive_paths_before_file_reads():
    github = _GitHub()
    identity = ProjectRunIdentity(PROJECT_ID, RUN_ID)
    provider = ProjectedRepositoryBoundSourceProvider(
        identity=identity,
        binding=ProviderProjectBinding(PROJECT_ID, REPOSITORY),
        github=github,
        invocations=_Invocations(),
        operation_key="op:projection",
    )

    package = provider.load(identity)

    assert tuple(sorted(package.files)) == (
        "apps/client/assets/parallax-lens-mark.svg",
        "apps/client/src/components/ParallaxLogo.tsx",
    )
    assert sorted(github.file_reads) == list(sorted(package.files))
    assert package.source_ref == f"{REPOSITORY}@{REVISION}:projection:lineage-safe-v2"


def test_lineage_safe_projection_overlaps_reads_within_fixed_worker_bound():
    github = _ConcurrentGitHub()
    identity = ProjectRunIdentity(PROJECT_ID, RUN_ID)
    provider = ProjectedRepositoryBoundSourceProvider(
        identity=identity,
        binding=ProviderProjectBinding(PROJECT_ID, REPOSITORY),
        github=github,
        invocations=_Invocations(),
        operation_key="op:projection-concurrent",
    )

    package = provider.load(identity)

    assert github.max_active_reads == 2
    assert github.max_active_reads <= _PROJECTED_READ_WORKERS
    assert sorted(github.file_reads) == list(sorted(package.files))


def test_projection_matches_durable_lineage_secret_path_boundary():
    excluded = (
        "apps/client/.env.example",
        "services/api/.env.production",
        "services/api/credentials.json",
        "services/api/private.pem",
        "tools/.ssh/config",
    )
    for path in excluded:
        assert is_lineage_secret_sensitive_path(path)
        with pytest.raises(SourcePolicyError):
            SourceLineageStore._normalize_source_path(path)

    allowed = "apps/client/src/components/ParallaxLogo.tsx"
    assert not is_lineage_secret_sensitive_path(allowed)
    assert SourceLineageStore._normalize_source_path(allowed) == allowed


def test_canonical_source_read_allows_auth_code_but_publication_rejects_same_secret_like_literal():
    content = 'const token = "replace-with-user-token-value";\n'
    digest = sha256(content.encode()).hexdigest()

    result = ProjectedGitHubFileResult(
        REPOSITORY,
        REVISION,
        "apps/client/src/lib/auth.ts",
        content,
        digest,
    )
    assert result.content == content

    with pytest.raises(ValueError, match="possible secret-bearing content"):
        GitHubCommitFile("apps/client/src/lib/auth.ts", content, digest)


def test_projected_rest_read_accepts_auth_source_and_refuses_secret_sensitive_path_before_http():
    content = 'const authorization = "replace-with-auth-fixture-value";\n'
    encoded = base64.b64encode(content.encode()).decode()
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert request.url.path == "/repos/Ryan9876/parallax/contents/apps/client/src/lib/auth.ts"
        assert request.url.params["ref"] == REVISION
        return httpx.Response(
            200,
            json={
                "type": "file",
                "encoding": "base64",
                "path": "apps/client/src/lib/auth.ts",
                "size": len(content.encode()),
                "content": encoded,
            },
        )

    delegate = GitHubRestProviderClient(
        _CredentialProvider(),
        transport=httpx.MockTransport(handler),
    )
    client = ProjectedGitHubReadClient(delegate)

    result = client.read_file(
        REPOSITORY,
        REVISION,
        "apps/client/src/lib/auth.ts",
        max_bytes=MAX_FILE_BYTES,
    )
    assert result.content == content
    assert calls == ["/repos/Ryan9876/parallax/contents/apps/client/src/lib/auth.ts"]

    with pytest.raises(ProviderClientError, match="SOURCE_PATH_EXCLUDED"):
        client.read_file(
            REPOSITORY,
            REVISION,
            "apps/client/.env.example",
            max_bytes=MAX_FILE_BYTES,
        )
    assert len(calls) == 1


def test_current_parallax_repository_is_compatible_with_projected_provider_source_contract():
    """Self-hosting gate for the exact repository shape production must bootstrap."""

    root = Path(__file__).resolve().parents[3]
    listed = subprocess.run(
        ["git", "ls-tree", "-r", "-t", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert len(listed) <= MAX_TREE_ENTRIES, (
        f"tracked repository tree has {len(listed)} entries; protected provider limit is {MAX_TREE_ENTRIES}"
    )

    rejected: list[str] = []
    checked = 0
    for line in listed:
        metadata, separator, path = line.partition("\t")
        assert separator and path
        fields = metadata.split()
        assert len(fields) == 3
        _mode, kind, _object_revision = fields
        if kind != "blob" or is_lineage_secret_sensitive_path(path):
            continue
        candidate = root / path
        raw = candidate.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            rejected.append(f"{path}:SOURCE_FILE_TOO_LARGE")
            continue
        try:
            content = raw.decode("utf-8", errors="strict")
            ProjectedGitHubFileResult(REPOSITORY, REVISION, path, content, sha256(raw).hexdigest())
        except UnicodeDecodeError:
            rejected.append(f"{path}:UNSUPPORTED_SOURCE_CONTENT")
        except (TypeError, ValueError) as exc:
            rejected.append(f"{path}:{type(exc).__name__}")
        checked += 1

    assert checked > 0
    assert rejected == [], "projected provider source rejects tracked files: " + ", ".join(rejected)
