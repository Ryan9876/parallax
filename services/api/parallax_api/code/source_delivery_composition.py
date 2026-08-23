from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import PurePosixPath
from typing import Protocol

from ..models import EngineeringRun
from ..projects.repository import ProjectRepository
from ..tools.providers import (
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
    GitHubCommitFile,
    GitHubProviderActions,
    ProviderActionEvidence,
    ProviderInvocation,
    ProviderProjectBinding,
    VercelPreviewActions,
    VercelPreviewStatus,
    VercelPreviewTarget,
)
from .domain import AttemptStatus, WorkflowStage
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import (
    LineageIdentityError,
    LineageNotFoundError,
    ProjectRunIdentity,
    SourceLineage,
    SourcePackage,
    SourceProvider,
)


class SourceDeliveryCompositionError(RuntimeError):
    """Fail-closed repository/bootstrap/delivery composition failure."""


class ProjectRepositoryBindingError(SourceDeliveryCompositionError):
    pass


class SourceBootstrapError(SourceDeliveryCompositionError):
    pass


class VerifiedDeliveryError(SourceDeliveryCompositionError):
    pass


class DurableSourceAllocator(Protocol):
    def initialize(self, identity: ProjectRunIdentity, provider: SourceProvider) -> MaterializedWorkspace: ...

    def current_lineage(self, identity: ProjectRunIdentity) -> SourceLineage: ...

    def reconstruct(self, identity: ProjectRunIdentity, lineage_id: str) -> MaterializedWorkspace: ...

    def cleanup(self, workspace: MaterializedWorkspace) -> None: ...


class ProjectBindingResolver(Protocol):
    def resolve(self, project_id: str) -> ProviderProjectBinding: ...


class PreviewTargetResolver(Protocol):
    def resolve(self, binding: ProviderProjectBinding) -> VercelPreviewTarget: ...


class ProviderInvocationFactory(Protocol):
    def for_action(self, *, tool: str, action: str, operation_key: str) -> ProviderInvocation: ...


_GITHUB_ACTIONS = frozenset(
    {
        ACTION_REPOSITORY_RESOLVE,
        ACTION_SOURCE_TREE_READ,
        ACTION_SOURCE_FILE_READ,
        ACTION_BRANCH_CREATE,
        ACTION_COMMIT_WRITE,
        ACTION_PULL_REQUEST_CREATE,
        ACTION_PULL_REQUEST_READ,
    }
)
_VERCEL_ACTIONS = frozenset({ACTION_PREVIEW_CREATE, ACTION_PREVIEW_READ})


class ScopedProviderInvocationFactory:
    """Server-owned mapping from fixed provider actions to fixed capability IDs."""

    def __init__(
        self,
        *,
        github_capability_id: str,
        vercel_capability_id: str,
        actor_ref: str,
    ) -> None:
        self.github_capability_id = github_capability_id
        self.vercel_capability_id = vercel_capability_id
        self.actor_ref = actor_ref
        ProviderInvocation("request:validation", github_capability_id, actor_ref)
        ProviderInvocation("request:validation", vercel_capability_id, actor_ref)

    def for_action(self, *, tool: str, action: str, operation_key: str) -> ProviderInvocation:
        if tool == GITHUB_TOOL and action in _GITHUB_ACTIONS:
            capability_id = self.github_capability_id
        elif tool == VERCEL_TOOL and action in _VERCEL_ACTIONS:
            capability_id = self.vercel_capability_id
        else:
            raise ValueError("provider action is outside the source-delivery composition boundary")
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise ValueError("operation_key is required")
        request_digest = sha256(f"{operation_key}|{tool}|{action}".encode("utf-8")).hexdigest()[:48]
        return ProviderInvocation(
            request_id=f"request:{request_digest}",
            capability_id=capability_id,
            actor_ref=self.actor_ref,
        )


class RegisteredPreviewTargetResolver:
    """Resolve Preview targets only from a server-owned exact registry."""

    def __init__(self, targets: tuple[VercelPreviewTarget, ...]) -> None:
        if not targets or not all(isinstance(target, VercelPreviewTarget) for target in targets):
            raise ValueError("at least one registered Vercel Preview target is required")
        if len({target.project_ref for target in targets}) != len(targets):
            raise ValueError("Preview targets must be unique per Project")
        self._targets = {target.project_ref: target for target in targets}

    def resolve(self, binding: ProviderProjectBinding) -> VercelPreviewTarget:
        target = self._targets.get(binding.project_ref)
        if target is None or target.repository_ref != binding.repository_ref:
            raise VerifiedDeliveryError("no registered Preview target matches canonical Project repository")
        return target


class OwnerScopedProjectBindingResolver:
    """Resolve canonical Project repository metadata inside one owner scope."""

    def __init__(self, repository: ProjectRepository, *, owner_subject: str) -> None:
        if not isinstance(owner_subject, str) or not owner_subject.strip():
            raise ValueError("owner_subject is required")
        self.repository = repository
        self.owner_subject = owner_subject

    def resolve(self, project_id: str) -> ProviderProjectBinding:
        project = self.repository.get_for_owner(project_id, self.owner_subject)
        if project is None:
            raise ProjectRepositoryBindingError("canonical owner-scoped Project is unavailable")
        if project.status != "active":
            raise ProjectRepositoryBindingError("canonical Project is not active")
        if not project.repository_ref:
            raise ProjectRepositoryBindingError("canonical Project has no repository binding")
        try:
            return ProviderProjectBinding(project_ref=project.id, repository_ref=project.repository_ref)
        except (TypeError, ValueError) as exc:
            raise ProjectRepositoryBindingError("canonical Project repository binding is invalid") from exc


class RepositoryBoundSourceProvider:
    """Read one immutable repository revision through existing authorized actions."""

    def __init__(
        self,
        *,
        identity: ProjectRunIdentity,
        binding: ProviderProjectBinding,
        github: GitHubProviderActions,
        invocations: ProviderInvocationFactory,
        operation_key: str,
    ) -> None:
        if binding.project_ref != identity.project_id:
            raise ProjectRepositoryBindingError("repository binding belongs to a different Project")
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise ValueError("operation_key is required")
        self.identity = identity
        self.binding = binding
        self.github = github
        self.invocations = invocations
        self.operation_key = operation_key

    def _invocation(self, action: str, suffix: str = "") -> ProviderInvocation:
        return self.invocations.for_action(
            tool=GITHUB_TOOL,
            action=action,
            operation_key=f"{self.operation_key}:{action}{suffix}",
        )

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        if identity != self.identity:
            raise SourceBootstrapError("repository source provider Project/run identity mismatch")
        repository = self.github.resolve_repository(
            self.binding,
            self._invocation(ACTION_REPOSITORY_RESOLVE),
        ).value
        revision = repository.head_revision
        tree = self.github.read_tree(
            self.binding,
            self._invocation(ACTION_SOURCE_TREE_READ),
            source_revision=revision,
        ).value
        files: dict[str, bytes] = {}
        for index, entry in enumerate(sorted(tree.entries, key=lambda item: item.path)):
            if entry.kind != "file":
                continue
            source = self.github.read_file(
                self.binding,
                self._invocation(ACTION_SOURCE_FILE_READ, f":{index}"),
                source_revision=revision,
                path=entry.path,
            ).value
            raw = source.content.encode("utf-8")
            if sha256(raw).hexdigest() != source.content_sha256:
                raise SourceBootstrapError("repository file digest changed inside protected read boundary")
            files[source.path] = raw
        if not files:
            raise SourceBootstrapError("repository bootstrap returned no publishable source files")
        return SourcePackage(
            source_kind="repository",
            source_ref=f"{self.binding.repository_ref}@{revision}",
            files=files,
        )


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    identity: ProjectRunIdentity
    lineage: SourceLineage
    initialized: bool


class RepositoryLineageBootstrap:
    """Initialize a missing durable root lineage without replacing an existing head."""

    def __init__(
        self,
        *,
        allocator: DurableSourceAllocator,
        projects: ProjectBindingResolver,
        github: GitHubProviderActions,
        invocations: ProviderInvocationFactory,
    ) -> None:
        self.allocator = allocator
        self.projects = projects
        self.github = github
        self.invocations = invocations

    @staticmethod
    def identity_for_run(run: EngineeringRun) -> ProjectRunIdentity:
        if not run.project_id:
            raise SourceBootstrapError("Engineering Run is not bound to a canonical Project")
        try:
            return ProjectRunIdentity(project_id=run.project_id, run_id=run.id)
        except (TypeError, ValueError, RuntimeError) as exc:
            raise SourceBootstrapError("Engineering Run Project/run identity is invalid") from exc

    def ensure(self, run: EngineeringRun, *, operation_key: str) -> BootstrapResult:
        identity = self.identity_for_run(run)
        try:
            current = self.allocator.current_lineage(identity)
        except (LineageIdentityError, LineageNotFoundError):
            current = None
        except Exception as exc:
            raise SourceBootstrapError("durable source-lineage head could not be resolved") from exc
        if current is not None:
            if current.project_id != identity.project_id or current.run_id != identity.run_id:
                raise SourceBootstrapError("durable source lineage belongs to a different Project/run")
            return BootstrapResult(identity=identity, lineage=current, initialized=False)

        binding = self.projects.resolve(identity.project_id)
        provider = RepositoryBoundSourceProvider(
            identity=identity,
            binding=binding,
            github=self.github,
            invocations=self.invocations,
            operation_key=f"{operation_key}:bootstrap",
        )
        workspace: MaterializedWorkspace | None = None
        try:
            workspace = self.allocator.initialize(identity, provider)
            lineage = workspace.lineage
            if (
                lineage.project_id != identity.project_id
                or lineage.run_id != identity.run_id
                or lineage.parent_lineage_id is not None
                or lineage.source_kind != "repository"
                or lineage.source_ref_digest is None
            ):
                raise SourceBootstrapError("initialized repository lineage violates root-lineage contract")
            return BootstrapResult(identity=identity, lineage=lineage, initialized=True)
        except SourceBootstrapError:
            raise
        except Exception as exc:
            raise SourceBootstrapError("repository-backed durable lineage initialization failed") from exc
        finally:
            if workspace is not None:
                try:
                    self.allocator.cleanup(workspace)
                except Exception as exc:
                    raise SourceBootstrapError("failed to clean disposable bootstrap materialization") from exc


@dataclass(frozen=True, slots=True)
class VerifiedDeliveryResult:
    project_id: str
    run_id: str
    repository_identity_digest: str
    lineage_id: str
    content_digest: str
    branch_name: str
    commit_revision: str
    pull_request_number: int
    pull_request_url: str
    preview_deployment_id: str
    preview_status: str
    preview_url: str | None
    evidence: tuple[ProviderActionEvidence, ...]


class VerifiedLineageDelivery:
    """Publish only the exact accepted VERIFY-bound lineage through bounded actions."""

    def __init__(
        self,
        *,
        allocator: DurableSourceAllocator,
        projects: ProjectBindingResolver,
        preview_targets: PreviewTargetResolver,
        github: GitHubProviderActions,
        vercel: VercelPreviewActions,
        invocations: ProviderInvocationFactory,
    ) -> None:
        self.allocator = allocator
        self.projects = projects
        self.preview_targets = preview_targets
        self.github = github
        self.vercel = vercel
        self.invocations = invocations

    @staticmethod
    def _identity(run: EngineeringRun) -> ProjectRunIdentity:
        return RepositoryLineageBootstrap.identity_for_run(run)

    @staticmethod
    def _attempt_evidence(attempt: object) -> dict[str, object]:
        raw = getattr(attempt, "evidence_json", None)
        if raw is None:
            raw = getattr(attempt, "evidence", None)
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(raw, str):
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise VerifiedDeliveryError("Engineering Run attempt evidence is invalid") from exc
            if isinstance(value, dict):
                return value
        return {}

    @classmethod
    def _verified_lineage_id(cls, run: EngineeringRun, identity: ProjectRunIdentity) -> str:
        if run.state != WorkflowStage.REVIEW.value:
            raise VerifiedDeliveryError("verified source may be delivered only at operator review")
        implementation: dict[str, object] | None = None
        verification: dict[str, object] | None = None
        for attempt in reversed(tuple(run.attempts)):
            if getattr(attempt, "status", None) != AttemptStatus.PASSED.value:
                continue
            stage = getattr(attempt, "stage", None)
            if verification is None and stage == WorkflowStage.VERIFY.value:
                verification = cls._attempt_evidence(attempt)
            if implementation is None and stage == WorkflowStage.IMPLEMENT.value:
                implementation = cls._attempt_evidence(attempt)
            if implementation is not None and verification is not None:
                break
        if implementation is None or verification is None:
            raise VerifiedDeliveryError("accepted IMPLEMENT and VERIFY evidence are required before delivery")
        lineage_id = implementation.get("source_lineage_ref")
        if not isinstance(lineage_id, str):
            raise VerifiedDeliveryError("accepted IMPLEMENT lineage identity is unavailable")
        if implementation.get("project_ref") != identity.project_id:
            raise VerifiedDeliveryError("accepted IMPLEMENT belongs to a different Project")
        if implementation.get("run_id") not in {None, identity.run_id}:
            raise VerifiedDeliveryError("accepted IMPLEMENT belongs to a different Engineering Run")
        if verification.get("project_ref") != identity.project_id:
            raise VerifiedDeliveryError("VERIFY evidence belongs to a different Project")
        if verification.get("run_id") not in {None, identity.run_id}:
            raise VerifiedDeliveryError("VERIFY evidence belongs to a different Engineering Run")
        if verification.get("source_lineage_ref") != lineage_id:
            raise VerifiedDeliveryError("VERIFY did not execute on the accepted IMPLEMENT lineage")
        if verification.get("lineage_bound_execution") is not True or verification.get("protected_success") is not True:
            raise VerifiedDeliveryError("VERIFY did not succeed on the exact accepted lineage")
        return lineage_id

    def _invocation(self, tool: str, action: str, operation_key: str) -> ProviderInvocation:
        return self.invocations.for_action(tool=tool, action=action, operation_key=operation_key)

    def _reconstruct_lineage(self, identity: ProjectRunIdentity, lineage_id: str) -> SourceLineage:
        workspace: MaterializedWorkspace | None = None
        try:
            workspace = self.allocator.reconstruct(identity, lineage_id)
            lineage = workspace.lineage
            if lineage.project_id != identity.project_id or lineage.run_id != identity.run_id:
                raise VerifiedDeliveryError("reconstructed lineage Project/run identity mismatch")
            if lineage.lineage_id != lineage_id:
                raise VerifiedDeliveryError("reconstructed lineage identity mismatch")
            return lineage
        except VerifiedDeliveryError:
            raise
        except Exception as exc:
            raise VerifiedDeliveryError("durable lineage reconstruction failed") from exc
        finally:
            if workspace is not None:
                try:
                    self.allocator.cleanup(workspace)
                except Exception as exc:
                    raise VerifiedDeliveryError("failed to clean lineage traversal materialization") from exc

    def _root_lineage(self, identity: ProjectRunIdentity, accepted: SourceLineage) -> SourceLineage:
        lineage = accepted
        seen = {lineage.lineage_id}
        for _ in range(128):
            parent = lineage.parent_lineage_id
            if parent is None:
                if lineage.source_kind != "repository" or lineage.source_ref_digest is None:
                    raise VerifiedDeliveryError("accepted lineage does not descend from a repository root")
                return lineage
            if parent in seen:
                raise VerifiedDeliveryError("source lineage contains a parent cycle")
            seen.add(parent)
            lineage = self._reconstruct_lineage(identity, parent)
        raise VerifiedDeliveryError("source lineage ancestry exceeds protected traversal bound")

    def _accepted_commit_files(
        self,
        identity: ProjectRunIdentity,
        accepted_lineage_id: str,
    ) -> tuple[SourceLineage, tuple[GitHubCommitFile, ...]]:
        workspace: MaterializedWorkspace | None = None
        try:
            workspace = self.allocator.reconstruct(identity, accepted_lineage_id)
            lineage = workspace.lineage
            if (
                lineage.project_id != identity.project_id
                or lineage.run_id != identity.run_id
                or lineage.lineage_id != accepted_lineage_id
                or lineage.parent_lineage_id is None
            ):
                raise VerifiedDeliveryError("only an accepted non-root implementation lineage may be delivered")
            root = workspace.path.resolve(strict=True)
            commit_files: list[GitHubCommitFile] = []
            for entry in lineage.files:
                pure = PurePosixPath(entry.path)
                if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                    raise VerifiedDeliveryError("accepted lineage contains an unsafe file path")
                target = workspace.path.joinpath(*pure.parts)
                if target.is_symlink() or not target.is_file():
                    raise VerifiedDeliveryError("accepted lineage file is unavailable in materialization")
                resolved = target.resolve(strict=True)
                if not resolved.is_relative_to(root):
                    raise VerifiedDeliveryError("accepted lineage file escaped materialization")
                raw = target.read_bytes()
                if len(raw) != entry.size or sha256(raw).hexdigest() != entry.sha256:
                    raise VerifiedDeliveryError("accepted lineage materialization does not match durable manifest")
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise VerifiedDeliveryError("accepted lineage contains non-text content outside provider boundary") from exc
                commit_files.append(GitHubCommitFile(entry.path, text, entry.sha256))
            if not commit_files:
                raise VerifiedDeliveryError("accepted lineage has no publishable files")
            return lineage, tuple(commit_files)
        except VerifiedDeliveryError:
            raise
        except Exception as exc:
            raise VerifiedDeliveryError("exact accepted lineage could not be materialized for delivery") from exc
        finally:
            if workspace is not None:
                try:
                    self.allocator.cleanup(workspace)
                except Exception as exc:
                    raise VerifiedDeliveryError("failed to clean delivery materialization") from exc

    def deliver(self, run: EngineeringRun, *, operation_key: str) -> VerifiedDeliveryResult:
        identity = self._identity(run)
        accepted_lineage_id = self._verified_lineage_id(run, identity)
        try:
            current = self.allocator.current_lineage(identity)
        except Exception as exc:
            raise VerifiedDeliveryError("current durable source lineage is unavailable") from exc
        if current.lineage_id != accepted_lineage_id:
            raise VerifiedDeliveryError("current durable lineage moved after verified implementation")

        accepted, files = self._accepted_commit_files(identity, accepted_lineage_id)
        if accepted.content_digest != current.content_digest:
            raise VerifiedDeliveryError("accepted lineage content digest changed")
        root = self._root_lineage(identity, accepted)
        binding = self.projects.resolve(identity.project_id)

        evidence: list[ProviderActionEvidence] = []
        repository = self.github.resolve_repository(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_REPOSITORY_RESOLVE, f"{operation_key}:publish:resolve"),
        )
        evidence.append(repository.evidence)
        protected_ref_digest = sha256(
            f"{binding.repository_ref}@{repository.value.head_revision}".encode("utf-8")
        ).hexdigest()
        if protected_ref_digest != root.source_ref_digest:
            raise VerifiedDeliveryError("repository parent moved after durable lineage bootstrap")

        lineage = AcceptedSourceLineage(
            project_id=identity.project_id,
            run_id=identity.run_id,
            lineage_id=accepted.lineage_id,
            content_digest=accepted.content_digest,
        )
        branch_name = f"parallax/{identity.project_id[:8]}-{identity.run_id[:8]}"
        branch = self.github.create_branch(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_BRANCH_CREATE, f"{operation_key}:publish:branch"),
            branch_name=branch_name,
            base_revision=repository.value.head_revision,
        )
        evidence.append(branch.evidence)
        commit = self.github.commit_accepted_lineage(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_COMMIT_WRITE, f"{operation_key}:publish:commit"),
            branch_name=branch_name,
            expected_parent_revision=repository.value.head_revision,
            lineage=lineage,
            files=files,
        )
        evidence.append(commit.evidence)
        pull_request = self.github.create_pull_request(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_PULL_REQUEST_CREATE, f"{operation_key}:publish:pr-create"),
            head_branch=branch_name,
            expected_head_revision=commit.value.commit_revision,
            base_branch=repository.value.default_branch,
            lineage=lineage,
            title="Parallax verified app-builder change",
            body=(
                f"Verified Parallax lineage `{accepted.lineage_id}` for Engineering Run `{identity.run_id}`. "
                "Operator review is required; this PR is not a production promotion."
            ),
        )
        evidence.append(pull_request.evidence)
        read_pull_request = self.github.read_pull_request(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_PULL_REQUEST_READ, f"{operation_key}:publish:pr-read"),
            number=pull_request.value.number,
        )
        evidence.append(read_pull_request.evidence)
        if (
            read_pull_request.value.state != "OPEN"
            or read_pull_request.value.head_branch != branch_name
            or read_pull_request.value.head_revision != commit.value.commit_revision
            or read_pull_request.value.base_branch != repository.value.default_branch
        ):
            raise VerifiedDeliveryError("GitHub pull request read-back did not match exact verified source")

        target = self.preview_targets.resolve(binding)
        if target.project_ref != identity.project_id or target.repository_ref != binding.repository_ref:
            raise VerifiedDeliveryError("Vercel Preview target does not match canonical Project repository")
        preview = self.vercel.create_preview(
            target,
            self._invocation(VERCEL_TOOL, ACTION_PREVIEW_CREATE, f"{operation_key}:publish:preview-create"),
            source_revision=commit.value.commit_revision,
            branch_name=branch_name,
            lineage=lineage,
        )
        evidence.append(preview.evidence)
        read_preview = self.vercel.read_preview(
            target,
            self._invocation(VERCEL_TOOL, ACTION_PREVIEW_READ, f"{operation_key}:publish:preview-read"),
            deployment_id=preview.value.deployment_id,
            expected_source_revision=commit.value.commit_revision,
        )
        evidence.append(read_preview.evidence)
        if read_preview.value.status in {VercelPreviewStatus.ERROR, VercelPreviewStatus.CANCELED}:
            raise VerifiedDeliveryError("Vercel Preview entered a terminal non-success state")

        return VerifiedDeliveryResult(
            project_id=identity.project_id,
            run_id=identity.run_id,
            repository_identity_digest=binding.repository_identity_digest,
            lineage_id=accepted.lineage_id,
            content_digest=accepted.content_digest,
            branch_name=branch_name,
            commit_revision=commit.value.commit_revision,
            pull_request_number=read_pull_request.value.number,
            pull_request_url=read_pull_request.value.url,
            preview_deployment_id=read_preview.value.deployment_id,
            preview_status=read_preview.value.status.value,
            preview_url=read_preview.value.url,
            evidence=tuple(evidence),
        )


@dataclass(frozen=True, slots=True)
class SourceDeliveryComposition:
    bootstrap: RepositoryLineageBootstrap
    delivery: VerifiedLineageDelivery


__all__ = [
    "BootstrapResult",
    "DurableSourceAllocator",
    "OwnerScopedProjectBindingResolver",
    "PreviewTargetResolver",
    "ProjectBindingResolver",
    "ProjectRepositoryBindingError",
    "ProviderInvocationFactory",
    "RegisteredPreviewTargetResolver",
    "RepositoryBoundSourceProvider",
    "RepositoryLineageBootstrap",
    "ScopedProviderInvocationFactory",
    "SourceBootstrapError",
    "SourceDeliveryComposition",
    "SourceDeliveryCompositionError",
    "VerifiedDeliveryError",
    "VerifiedDeliveryResult",
    "VerifiedLineageDelivery",
]
