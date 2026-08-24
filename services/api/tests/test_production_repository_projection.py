from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

from parallax_api.code.production_source_projection import (
    ProjectedGitHubFileResult,
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
    ProviderInvocation,
    ProviderProjectBinding,
)
from parallax_api.tools.providers.github import MAX_FILE_BYTES, MAX_TREE_ENTRIES


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
    assert github.file_reads == list(sorted(package.files))
    assert package.source_ref == f"{REPOSITORY}@{REVISION}:projection:lineage-safe-v2"


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
