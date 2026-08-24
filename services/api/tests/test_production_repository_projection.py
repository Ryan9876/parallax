from __future__ import annotations

from types import SimpleNamespace

import pytest

from parallax_api.code.production_source_projection import (
    ProjectedRepositoryBoundSourceProvider,
    is_lineage_secret_sensitive_path,
)
from parallax_api.code.workspace_lineage import (
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePolicyError,
)
from parallax_api.tools.providers import (
    GitHubFileResult,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
    ProviderInvocation,
    ProviderProjectBinding,
)


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
        from hashlib import sha256

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
    assert package.source_ref == f"{REPOSITORY}@{REVISION}:projection:lineage-safe-v1"


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
