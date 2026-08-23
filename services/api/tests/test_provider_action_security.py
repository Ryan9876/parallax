from __future__ import annotations

from dataclasses import fields
from hashlib import sha256

import pytest

from parallax_api.tools import (
    HumanApproval,
    ToolActionPolicy,
    ToolCapability,
    ToolCapabilityRegistry,
    ToolConsequence,
    ToolOutcome,
)
from parallax_api.tools.providers import (
    ACTION_BRANCH_CREATE,
    ACTION_PREVIEW_CREATE,
    ACTION_REPOSITORY_RESOLVE,
    GITHUB_TOOL,
    VERCEL_TOOL,
    AcceptedSourceLineage,
    GitHubBranchResult,
    GitHubCommitFile,
    GitHubProviderActions,
    GitHubRepositoryState,
    ProviderActionDenied,
    ProviderActionFailed,
    ProviderClientError,
    ProviderInvocation,
    ProviderProjectBinding,
    VercelPreviewActions,
    VercelPreviewResult,
    VercelPreviewStatus,
    VercelPreviewTarget,
)


PROJECT_ID = "7e643661-99d6-4b31-9af7-d86d30b01c14"
OTHER_PROJECT_ID = "c50ad114-56ed-45ce-b01a-5a263ded2ea2"
REPOSITORY_REF = "github:acme/example-app"
OTHER_REPOSITORY_REF = "github:acme/other-app"
BASE_REVISION = "0123456789abcdef0123456789abcdef01234567"
LINEAGE = AcceptedSourceLineage("lineage:accepted:security", "b" * 64)
BINDING = ProviderProjectBinding(PROJECT_ID, REPOSITORY_REF)


class CountingGitHubClient:
    def __init__(self) -> None:
        self.calls = 0
        self.return_wrong_repository = False
        self.fail = False

    def resolve_repository(self, repository_ref: str) -> GitHubRepositoryState:
        self.calls += 1
        if self.fail:
            raise ProviderClientError("PROVIDER_UNAVAILABLE")
        return GitHubRepositoryState(
            OTHER_REPOSITORY_REF if self.return_wrong_repository else repository_ref,
            "main",
            BASE_REVISION,
        )

    def create_branch(self, repository_ref: str, branch_name: str, base_revision: str) -> GitHubBranchResult:
        self.calls += 1
        return GitHubBranchResult(repository_ref, branch_name, base_revision, base_revision)


class MismatchedVercelClient:
    def create_preview(
        self,
        vercel_project_ref: str,
        repository_ref: str,
        source_revision: str,
        branch_name: str,
        lineage: AcceptedSourceLineage,
    ) -> VercelPreviewResult:
        return VercelPreviewResult(
            "vercel:project:wrong",
            repository_ref,
            "dpl_wrong",
            source_revision,
            VercelPreviewStatus.READY,
            "https://wrong.vercel.app",
        )

    def read_preview(self, vercel_project_ref: str, deployment_id: str) -> VercelPreviewResult:
        raise ProviderClientError("PROVIDER_UNAVAILABLE", result_identity=deployment_id)


def _invocation(capability: str, request_id: str, approval_id: str | None = None) -> ProviderInvocation:
    return ProviderInvocation(request_id, capability, "actor:worker", approval_id)


def test_wrong_project_authority_denies_without_calling_provider() -> None:
    client = CountingGitHubClient()
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                "cap:github:wrong-project",
                OTHER_PROJECT_ID,
                GITHUB_TOOL,
                (ToolActionPolicy(ACTION_REPOSITORY_RESOLVE, ToolConsequence.READ),),
            ),
        )
    )
    actions = GitHubProviderActions(registry, client)

    with pytest.raises(ProviderActionDenied) as exc_info:
        actions.resolve_repository(
            BINDING,
            _invocation("cap:github:wrong-project", "req:wrong-project"),
        )

    assert client.calls == 0
    assert exc_info.value.audit.outcome is ToolOutcome.DENIED
    assert exc_info.value.audit.deny_reason.value == "PROJECT_MISMATCH"


def test_missing_human_approval_denies_mutation_before_provider_call() -> None:
    client = CountingGitHubClient()
    request_id = "req:approval"
    capability_id = "cap:github:approved-branch"
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                capability_id,
                PROJECT_ID,
                GITHUB_TOOL,
                (
                    ToolActionPolicy(
                        ACTION_BRANCH_CREATE,
                        ToolConsequence.MUTATE,
                        requires_human_approval=True,
                    ),
                ),
            ),
        ),
        approvals=(
            HumanApproval(
                "approval:branch",
                request_id,
                capability_id,
                PROJECT_ID,
                GITHUB_TOOL,
                ACTION_BRANCH_CREATE,
                "human:release-operator",
            ),
        ),
    )
    actions = GitHubProviderActions(registry, client)

    with pytest.raises(ProviderActionDenied) as missing:
        actions.create_branch(
            BINDING,
            _invocation(capability_id, request_id),
            branch_name="parallax/approved",
            base_revision=BASE_REVISION,
        )
    assert missing.value.audit.deny_reason.value == "APPROVAL_REQUIRED"
    assert client.calls == 0

    success = actions.create_branch(
        BINDING,
        _invocation(capability_id, request_id, "approval:branch"),
        branch_name="parallax/approved",
        base_revision=BASE_REVISION,
    )
    assert success.audit.approval_id == "approval:branch"
    assert client.calls == 1


def test_provider_failure_and_repository_mismatch_are_failed_not_success() -> None:
    client = CountingGitHubClient()
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                "cap:github:read",
                PROJECT_ID,
                GITHUB_TOOL,
                (ToolActionPolicy(ACTION_REPOSITORY_RESOLVE, ToolConsequence.READ),),
            ),
        )
    )
    actions = GitHubProviderActions(registry, client)

    client.fail = True
    with pytest.raises(ProviderActionFailed) as failed:
        actions.resolve_repository(BINDING, _invocation("cap:github:read", "req:provider-fail"))
    assert failed.value.audit.outcome is ToolOutcome.FAILED
    assert failed.value.audit.result_code == "PROVIDER_UNAVAILABLE"

    client.fail = False
    client.return_wrong_repository = True
    with pytest.raises(ProviderActionFailed) as mismatch:
        actions.resolve_repository(BINDING, _invocation("cap:github:read", "req:repo-mismatch"))
    assert mismatch.value.audit.outcome is ToolOutcome.FAILED
    assert mismatch.value.audit.result_code == "REPOSITORY_MISMATCH"


def test_publication_inputs_fail_closed_on_secret_paths_content_and_unbounded_branches() -> None:
    content = "api_key=abcdefghijklmnop1234567890"
    with pytest.raises(ValueError, match="secret-bearing"):
        GitHubCommitFile("src/config.py", content, sha256(content.encode()).hexdigest())

    safe_content = "print('ok')\n"
    with pytest.raises(ValueError, match="publication boundary"):
        GitHubCommitFile(".env", safe_content, sha256(safe_content.encode()).hexdigest())

    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                "cap:github:branch",
                PROJECT_ID,
                GITHUB_TOOL,
                (ToolActionPolicy(ACTION_BRANCH_CREATE, ToolConsequence.MUTATE),),
            ),
        )
    )
    with pytest.raises(ValueError, match="parallax"):
        GitHubProviderActions(registry, CountingGitHubClient()).create_branch(
            BINDING,
            _invocation("cap:github:branch", "req:branch"),
            branch_name="main",
            base_revision=BASE_REVISION,
        )


def test_provider_binding_rejects_urls_noncanonical_project_and_unsafe_preview_url() -> None:
    with pytest.raises(ValueError, match="github:owner/repository"):
        ProviderProjectBinding(PROJECT_ID, "https://github.com/acme/example-app")
    with pytest.raises(ValueError, match="canonical Project.id"):
        ProviderProjectBinding("project:opaque", REPOSITORY_REF)
    with pytest.raises(ValueError, match="allowed provider domain"):
        VercelPreviewResult(
            "vercel:project:example-app",
            REPOSITORY_REF,
            "dpl_bad_url",
            BASE_REVISION,
            VercelPreviewStatus.READY,
            "https://evil.example/preview",
        )


def test_vercel_target_mismatch_is_failed_and_production_promotion_is_impossible() -> None:
    registry = ToolCapabilityRegistry(
        (
            ToolCapability(
                "cap:vercel:preview",
                PROJECT_ID,
                VERCEL_TOOL,
                (ToolActionPolicy(ACTION_PREVIEW_CREATE, ToolConsequence.MUTATE),),
            ),
        )
    )
    actions = VercelPreviewActions(registry, MismatchedVercelClient())
    target = VercelPreviewTarget(PROJECT_ID, REPOSITORY_REF, "vercel:project:example-app")

    with pytest.raises(ProviderActionFailed) as mismatch:
        actions.create_preview(
            target,
            _invocation("cap:vercel:preview", "req:preview-mismatch"),
            source_revision=BASE_REVISION,
            branch_name="parallax/run-security",
            lineage=LINEAGE,
        )
    assert mismatch.value.audit.outcome is ToolOutcome.FAILED
    assert mismatch.value.audit.result_code == "TARGET_MISMATCH"

    with pytest.raises(PermissionError, match="production promotion"):
        actions.production_promotion(target)


def test_provider_contracts_have_no_generic_transport_or_secret_fields() -> None:
    forbidden = {
        "token",
        "api_key",
        "authorization",
        "headers",
        "environment",
        "env",
        "method",
        "url",
        "command",
        "shell",
        "subprocess",
        "raw_payload",
        "raw_response",
    }
    for model in (ProviderInvocation, ProviderProjectBinding, AcceptedSourceLineage, VercelPreviewTarget):
        assert not ({field.name for field in fields(model)} & forbidden)

    with pytest.raises(ValueError):
        ToolCapability(
            "cap:raw-http",
            PROJECT_ID,
            "http",
            (ToolActionPolicy("request", ToolConsequence.READ),),
        )
