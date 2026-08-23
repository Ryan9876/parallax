from __future__ import annotations

from hashlib import sha256

from parallax_api.tools import (
    ToolActionPolicy,
    ToolCapability,
    ToolCapabilityRegistry,
    ToolConsequence,
    ToolOutcome,
)
from parallax_api.tools.providers import (
    ACTION_BRANCH_CREATE,
    ACTION_COMMIT_WRITE,
    ACTION_PREVIEW_CREATE,
    ACTION_PREVIEW_READ,
    ACTION_PULL_REQUEST_CREATE,
    ACTION_PULL_REQUEST_READ,
    ACTION_REPOSITORY_RESOLVE,
    ACTION_SOURCE_FILE_READ,
    ACTION_SOURCE_TREE_READ,
    GITHUB_TOOL,
    VERCEL_TOOL,
    AcceptedSourceLineage,
    GitHubBranchResult,
    GitHubCommitFile,
    GitHubCommitResult,
    GitHubFileResult,
    GitHubProviderActions,
    GitHubPullRequestResult,
    GitHubRepositoryState,
    GitHubTreeEntry,
    GitHubTreeResult,
    ProviderActionState,
    ProviderInvocation,
    ProviderProjectBinding,
    VercelPreviewActions,
    VercelPreviewResult,
    VercelPreviewStatus,
    VercelPreviewTarget,
)


PROJECT_ID = "7e643661-99d6-4b31-9af7-d86d30b01c14"
REPOSITORY_REF = "github:acme/example-app"
BASE_REVISION = "0123456789abcdef0123456789abcdef01234567"
COMMIT_REVISION = "89abcdef0123456789abcdef0123456789abcdef"
LINEAGE = AcceptedSourceLineage(
    lineage_ref="lineage:accepted:1",
    content_digest="a" * 64,
)
BINDING = ProviderProjectBinding(project_ref=PROJECT_ID, repository_ref=REPOSITORY_REF)


def _registry() -> ToolCapabilityRegistry:
    github_actions = (
        ToolActionPolicy(ACTION_REPOSITORY_RESOLVE, ToolConsequence.READ),
        ToolActionPolicy(ACTION_SOURCE_TREE_READ, ToolConsequence.READ),
        ToolActionPolicy(ACTION_SOURCE_FILE_READ, ToolConsequence.READ),
        ToolActionPolicy(ACTION_BRANCH_CREATE, ToolConsequence.MUTATE),
        ToolActionPolicy(ACTION_COMMIT_WRITE, ToolConsequence.MUTATE),
        ToolActionPolicy(ACTION_PULL_REQUEST_CREATE, ToolConsequence.MUTATE),
        ToolActionPolicy(ACTION_PULL_REQUEST_READ, ToolConsequence.READ),
    )
    vercel_actions = (
        ToolActionPolicy(ACTION_PREVIEW_CREATE, ToolConsequence.MUTATE),
        ToolActionPolicy(ACTION_PREVIEW_READ, ToolConsequence.READ),
    )
    return ToolCapabilityRegistry(
        (
            ToolCapability(
                capability_id="cap:github:app",
                project_ref=PROJECT_ID,
                tool=GITHUB_TOOL,
                actions=github_actions,
            ),
            ToolCapability(
                capability_id="cap:vercel:preview",
                project_ref=PROJECT_ID,
                tool=VERCEL_TOOL,
                actions=vercel_actions,
            ),
        )
    )


def _invocation(capability_id: str, request_id: str) -> ProviderInvocation:
    return ProviderInvocation(
        request_id=request_id,
        capability_id=capability_id,
        actor_ref="actor:app-builder",
    )


class FakeGitHubClient:
    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState:
        return GitHubRepositoryState(repository_ref, "main", BASE_REVISION)

    def read_tree(self, repository_ref: str, source_revision: str, *, max_entries: int) -> GitHubTreeResult:
        assert max_entries >= 2
        return GitHubTreeResult(
            repository_ref,
            source_revision,
            (
                GitHubTreeEntry("src", "tree", 0, "tree-src"),
                GitHubTreeEntry("src/app.py", "file", 16, "blob-app"),
            ),
        )

    def read_file(self, repository_ref: str, source_revision: str, path: str, *, max_bytes: int) -> GitHubFileResult:
        content = "print('hello')\n"
        assert max_bytes >= len(content)
        return GitHubFileResult(
            repository_ref,
            source_revision,
            path,
            content,
            sha256(content.encode()).hexdigest(),
        )

    def create_branch(self, repository_ref: str, branch_name: str, base_revision: str) -> GitHubBranchResult:
        return GitHubBranchResult(repository_ref, branch_name, base_revision, base_revision)

    def commit_files(
        self,
        repository_ref: str,
        branch_name: str,
        expected_parent_revision: str,
        lineage: AcceptedSourceLineage,
        files: tuple[GitHubCommitFile, ...],
    ) -> GitHubCommitResult:
        assert files
        return GitHubCommitResult(
            repository_ref,
            branch_name,
            expected_parent_revision,
            COMMIT_REVISION,
            lineage.lineage_ref,
            lineage.content_digest,
        )

    def create_pull_request(
        self,
        repository_ref: str,
        head_branch: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> GitHubPullRequestResult:
        assert title and isinstance(body, str)
        return GitHubPullRequestResult(
            repository_ref,
            42,
            head_branch,
            base_branch,
            "OPEN",
            "https://github.com/acme/example-app/pull/42",
        )

    def read_pull_request(self, repository_ref: str, number: int) -> GitHubPullRequestResult:
        return GitHubPullRequestResult(
            repository_ref,
            number,
            "parallax/run-1",
            "main",
            "OPEN",
            f"https://github.com/acme/example-app/pull/{number}",
        )


class FakeVercelClient:
    def create_preview(
        self,
        vercel_project_ref: str,
        repository_ref: str,
        source_revision: str,
        branch_name: str,
        lineage: AcceptedSourceLineage,
    ) -> VercelPreviewResult:
        assert branch_name == "parallax/run-1"
        assert lineage == LINEAGE
        return VercelPreviewResult(
            vercel_project_ref,
            repository_ref,
            "dpl_preview_1",
            source_revision,
            VercelPreviewStatus.READY,
            "https://example-app-git-run-1-acme.vercel.app",
        )

    def read_preview(self, vercel_project_ref: str, deployment_id: str) -> VercelPreviewResult:
        return VercelPreviewResult(
            vercel_project_ref,
            REPOSITORY_REF,
            deployment_id,
            COMMIT_REVISION,
            VercelPreviewStatus.READY,
            "https://example-app-git-run-1-acme.vercel.app",
        )


def test_authorized_github_source_branch_commit_and_pull_request_flow() -> None:
    actions = GitHubProviderActions(_registry(), FakeGitHubClient())

    repository = actions.resolve_repository(
        BINDING,
        _invocation("cap:github:app", "req:repo"),
    )
    assert repository.value.head_revision == BASE_REVISION
    assert repository.audit.outcome is ToolOutcome.SUCCEEDED

    tree = actions.read_tree(
        BINDING,
        _invocation("cap:github:app", "req:tree"),
        source_revision=BASE_REVISION,
    )
    assert len(tree.value.entries) == 2

    source = actions.read_file(
        BINDING,
        _invocation("cap:github:app", "req:file"),
        source_revision=BASE_REVISION,
        path="src/app.py",
    )
    assert source.value.content == "print('hello')\n"

    branch = actions.create_branch(
        BINDING,
        _invocation("cap:github:app", "req:branch"),
        branch_name="parallax/run-1",
        base_revision=BASE_REVISION,
    )
    assert branch.value.branch_name == "parallax/run-1"

    content = "print('updated')\n"
    commit_file = GitHubCommitFile(
        "src/app.py",
        content,
        sha256(content.encode()).hexdigest(),
    )
    commit = actions.commit_accepted_lineage(
        BINDING,
        _invocation("cap:github:app", "req:commit"),
        branch_name="parallax/run-1",
        expected_parent_revision=BASE_REVISION,
        lineage=LINEAGE,
        files=(commit_file,),
    )
    assert commit.value.commit_revision == COMMIT_REVISION
    assert commit.evidence.lineage_digest == LINEAGE.content_digest
    assert commit.evidence.state is ProviderActionState.SUCCEEDED

    pull_request = actions.create_pull_request(
        BINDING,
        _invocation("cap:github:app", "req:pr-create"),
        head_branch="parallax/run-1",
        base_branch="main",
        title="Parallax app-builder change",
    )
    assert pull_request.value.number == 42
    assert pull_request.evidence.safe_url.endswith("/pull/42")

    read_back = actions.read_pull_request(
        BINDING,
        _invocation("cap:github:app", "req:pr-read"),
        number=42,
    )
    assert read_back.value.state == "OPEN"


def test_authorized_vercel_preview_flow_is_bound_to_source_and_project() -> None:
    actions = VercelPreviewActions(_registry(), FakeVercelClient())
    target = VercelPreviewTarget(PROJECT_ID, REPOSITORY_REF, "vercel:project:example-app")

    created = actions.create_preview(
        target,
        _invocation("cap:vercel:preview", "req:preview-create"),
        source_revision=COMMIT_REVISION,
        branch_name="parallax/run-1",
        lineage=LINEAGE,
    )
    assert created.value.status is VercelPreviewStatus.READY
    assert created.audit.outcome is ToolOutcome.SUCCEEDED
    assert created.evidence.safe_url == "https://example-app-git-run-1-acme.vercel.app"
    first_digest = created.evidence.digest

    replay = actions.create_preview(
        target,
        _invocation("cap:vercel:preview", "req:preview-create-2"),
        source_revision=COMMIT_REVISION,
        branch_name="parallax/run-1",
        lineage=LINEAGE,
    )
    assert replay.evidence.digest == first_digest

    read_back = actions.read_preview(
        target,
        _invocation("cap:vercel:preview", "req:preview-read"),
        deployment_id="dpl_preview_1",
        expected_source_revision=COMMIT_REVISION,
    )
    assert read_back.value.status is VercelPreviewStatus.READY
