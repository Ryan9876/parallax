from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import PurePosixPath
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..models import EngineeringAttempt, EngineeringRun, utcnow
from ..projects.repository import ProjectRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from ..tools.contracts import (
    AuthorityDenyReason,
    ToolAuditRecord,
    ToolConsequence,
    ToolOutcome,
)
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
    ProviderActionState,
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


_DELIVERY_RECORD_KIND = "verified_source_delivery"
_DELIVERY_RECORD_VERSION = 1
_DELIVERY_RECORD_STAGE = "SOURCE_DELIVERY"
_DELIVERY_RECORD_STATUS = "RECORDED"
_DELIVERY_RECORD_PROGRAM = "verified-source-delivery-v0.15.9"
_DELIVERY_RECORD_TOOL = "github+vercel"
_MAX_DELIVERY_ACTIONS = 8
_MAX_ATTEMPT_EVIDENCE_BYTES = 24_000


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


class DeliveryRecordStore(Protocol):
    def load(self, *, run_id: str, lineage_id: str) -> dict[str, object] | None: ...

    def persist(
        self,
        *,
        run: EngineeringRun,
        lineage_id: str,
        payload: dict[str, object],
    ) -> tuple[dict[str, object], bool]: ...


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
class ProviderActionAuditPair:
    evidence: ProviderActionEvidence
    audit: ToolAuditRecord

    def __post_init__(self) -> None:
        if self.evidence.state is not ProviderActionState.SUCCEEDED:
            raise VerifiedDeliveryError("durable delivery records require successful provider evidence")
        if self.audit.outcome is not ToolOutcome.SUCCEEDED or not self.audit.authority_allowed:
            raise VerifiedDeliveryError("durable delivery records require successful authorized tool audit")
        if self.audit.deny_reason is not None:
            raise VerifiedDeliveryError("successful provider audit cannot retain a deny reason")
        if self.audit.tool != self.evidence.provider:
            raise VerifiedDeliveryError("provider evidence/audit tool mismatch")
        if self.audit.action != self.evidence.action:
            raise VerifiedDeliveryError("provider evidence/audit action mismatch")
        if self.audit.project_ref != self.evidence.project_ref:
            raise VerifiedDeliveryError("provider evidence/audit Project mismatch")
        if self.evidence.result_status is not None and self.audit.result_code != self.evidence.result_status:
            raise VerifiedDeliveryError("provider evidence/audit result code mismatch")
        if self.evidence.result_identity is not None and self.audit.result_identity != self.evidence.result_identity:
            raise VerifiedDeliveryError("provider evidence/audit result identity mismatch")

    def to_record(self) -> dict[str, object]:
        evidence = self.evidence
        audit = self.audit
        return {
            "evidence": {
                "provider": evidence.provider,
                "action": evidence.action,
                "state": evidence.state.value,
                "project_ref": evidence.project_ref,
                "repository_identity_digest": evidence.repository_identity_digest,
                "source_revision": evidence.source_revision,
                "lineage_id": evidence.lineage_id,
                "lineage_digest": evidence.lineage_digest,
                "result_identity": evidence.result_identity,
                "result_status": evidence.result_status,
                "safe_url": evidence.safe_url,
            },
            "audit": {
                "request_id": audit.request_id,
                "capability_id": audit.capability_id,
                "project_ref": audit.project_ref,
                "tool": audit.tool,
                "action": audit.action,
                "actor_ref": audit.actor_ref,
                "consequence": audit.consequence.value if audit.consequence is not None else None,
                "authority_allowed": audit.authority_allowed,
                "outcome": audit.outcome.value,
                "deny_reason": audit.deny_reason.value if audit.deny_reason is not None else None,
                "approval_id": audit.approval_id,
                "request_digest": audit.request_digest,
                "result_digest": audit.result_digest,
                "result_code": audit.result_code,
                "result_identity": audit.result_identity,
            },
        }

    @classmethod
    def from_record(cls, payload: object) -> ProviderActionAuditPair:
        if not isinstance(payload, dict):
            raise VerifiedDeliveryError("durable provider action/audit pair is invalid")
        evidence_raw = payload.get("evidence")
        audit_raw = payload.get("audit")
        if not isinstance(evidence_raw, dict) or not isinstance(audit_raw, dict):
            raise VerifiedDeliveryError("durable provider action/audit pair is incomplete")
        try:
            evidence = ProviderActionEvidence(
                provider=evidence_raw["provider"],
                action=evidence_raw["action"],
                state=ProviderActionState(evidence_raw["state"]),
                project_ref=evidence_raw["project_ref"],
                repository_identity_digest=evidence_raw["repository_identity_digest"],
                source_revision=evidence_raw.get("source_revision"),
                lineage_id=evidence_raw.get("lineage_id"),
                lineage_digest=evidence_raw.get("lineage_digest"),
                result_identity=evidence_raw.get("result_identity"),
                result_status=evidence_raw.get("result_status"),
                safe_url=evidence_raw.get("safe_url"),
            )
            consequence_raw = audit_raw.get("consequence")
            deny_reason_raw = audit_raw.get("deny_reason")
            audit = ToolAuditRecord(
                request_id=audit_raw["request_id"],
                capability_id=audit_raw.get("capability_id"),
                project_ref=audit_raw["project_ref"],
                tool=audit_raw["tool"],
                action=audit_raw["action"],
                actor_ref=audit_raw["actor_ref"],
                consequence=ToolConsequence(consequence_raw) if consequence_raw is not None else None,
                authority_allowed=audit_raw["authority_allowed"],
                outcome=ToolOutcome(audit_raw["outcome"]),
                deny_reason=AuthorityDenyReason(deny_reason_raw) if deny_reason_raw is not None else None,
                approval_id=audit_raw.get("approval_id"),
                request_digest=audit_raw["request_digest"],
                result_digest=audit_raw.get("result_digest"),
                result_code=audit_raw.get("result_code"),
                result_identity=audit_raw.get("result_identity"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise VerifiedDeliveryError("durable provider action/audit pair failed validation") from exc
        return cls(evidence=evidence, audit=audit)


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
    actions: tuple[ProviderActionAuditPair, ...]
    replayed: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.actions, tuple) or not self.actions or len(self.actions) > _MAX_DELIVERY_ACTIONS:
            raise VerifiedDeliveryError("delivery action/audit evidence exceeds protected action bound")
        if not all(isinstance(item, ProviderActionAuditPair) for item in self.actions):
            raise VerifiedDeliveryError("delivery action evidence must retain matching audit records")
        if len({item.audit.request_id for item in self.actions}) != len(self.actions):
            raise VerifiedDeliveryError("delivery action/audit request identities must be unique")
        if any(item.evidence.project_ref != self.project_id for item in self.actions):
            raise VerifiedDeliveryError("delivery action evidence belongs to a different Project")
        if not isinstance(self.replayed, bool):
            raise TypeError("replayed must be bool")

    @property
    def evidence(self) -> tuple[ProviderActionEvidence, ...]:
        return tuple(item.evidence for item in self.actions)

    @property
    def audits(self) -> tuple[ToolAuditRecord, ...]:
        return tuple(item.audit for item in self.actions)

    def to_record(self) -> dict[str, object]:
        return {
            "record_kind": _DELIVERY_RECORD_KIND,
            "record_version": _DELIVERY_RECORD_VERSION,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "repository_identity_digest": self.repository_identity_digest,
            "lineage_id": self.lineage_id,
            "content_digest": self.content_digest,
            "branch_name": self.branch_name,
            "commit_revision": self.commit_revision,
            "pull_request_number": self.pull_request_number,
            "pull_request_url": self.pull_request_url,
            "preview_deployment_id": self.preview_deployment_id,
            "preview_status": self.preview_status,
            "preview_url": self.preview_url,
            "actions": [item.to_record() for item in self.actions],
        }

    @classmethod
    def from_record(cls, payload: object, *, replayed: bool) -> VerifiedDeliveryResult:
        if not isinstance(payload, dict):
            raise VerifiedDeliveryError("durable source-delivery record is invalid")
        if payload.get("record_kind") != _DELIVERY_RECORD_KIND or payload.get("record_version") != _DELIVERY_RECORD_VERSION:
            raise VerifiedDeliveryError("durable source-delivery record version is unsupported")

        required_text = (
            "project_id",
            "run_id",
            "repository_identity_digest",
            "lineage_id",
            "content_digest",
            "branch_name",
            "commit_revision",
            "pull_request_url",
            "preview_deployment_id",
            "preview_status",
        )
        for field in required_text:
            if not isinstance(payload.get(field), str) or not payload[field]:
                raise VerifiedDeliveryError(f"durable source-delivery record {field} is invalid")
        if not isinstance(payload.get("pull_request_number"), int) or payload["pull_request_number"] < 1:
            raise VerifiedDeliveryError("durable source-delivery record pull request identity is invalid")
        preview_url = payload.get("preview_url")
        if preview_url is not None and (not isinstance(preview_url, str) or not preview_url):
            raise VerifiedDeliveryError("durable source-delivery record preview URL is invalid")
        actions_raw = payload.get("actions")
        if not isinstance(actions_raw, list) or not actions_raw or len(actions_raw) > _MAX_DELIVERY_ACTIONS:
            raise VerifiedDeliveryError("durable source-delivery action evidence is invalid")
        actions = tuple(ProviderActionAuditPair.from_record(item) for item in actions_raw)
        return cls(
            project_id=payload["project_id"],
            run_id=payload["run_id"],
            repository_identity_digest=payload["repository_identity_digest"],
            lineage_id=payload["lineage_id"],
            content_digest=payload["content_digest"],
            branch_name=payload["branch_name"],
            commit_revision=payload["commit_revision"],
            pull_request_number=payload["pull_request_number"],
            pull_request_url=payload["pull_request_url"],
            preview_deployment_id=payload["preview_deployment_id"],
            preview_status=payload["preview_status"],
            preview_url=preview_url,
            actions=actions,
            replayed=replayed,
        )


class EngineeringAttemptDeliveryRecordStore:
    """Persist one bounded delivery record without advancing protected run state."""

    def __init__(self, repository: EngineeringRunRepository) -> None:
        if not isinstance(repository, EngineeringRunRepository):
            raise TypeError("repository must be EngineeringRunRepository")
        self.repository = repository

    @staticmethod
    def operation_key(lineage_id: str) -> str:
        if not isinstance(lineage_id, str) or not lineage_id.startswith("src:"):
            raise VerifiedDeliveryError("delivery record requires protected lineage identity")
        return f"source-delivery:{lineage_id}"

    @staticmethod
    def _decode(attempt: EngineeringAttempt) -> dict[str, object]:
        if attempt.stage != _DELIVERY_RECORD_STAGE or attempt.status != _DELIVERY_RECORD_STATUS:
            raise VerifiedDeliveryError("durable delivery attempt has an invalid record type")
        try:
            payload = json.loads(attempt.evidence_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise VerifiedDeliveryError("durable delivery attempt evidence is invalid") from exc
        if not isinstance(payload, dict):
            raise VerifiedDeliveryError("durable delivery attempt evidence must be an object")
        return payload

    @staticmethod
    def _canonical(payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(encoded.encode("utf-8")) > _MAX_ATTEMPT_EVIDENCE_BYTES:
            raise VerifiedDeliveryError("durable delivery evidence exceeds protected 24KB bound")
        return encoded

    def load(self, *, run_id: str, lineage_id: str) -> dict[str, object] | None:
        attempt = self.repository.find_operation(run_id, self.operation_key(lineage_id))
        if attempt is None:
            return None
        payload = self._decode(attempt)
        if payload.get("run_id") != run_id or payload.get("lineage_id") != lineage_id:
            raise VerifiedDeliveryError("durable delivery attempt identity mismatch")
        self._canonical(payload)
        return payload

    def persist(
        self,
        *,
        run: EngineeringRun,
        lineage_id: str,
        payload: dict[str, object],
    ) -> tuple[dict[str, object], bool]:
        if payload.get("project_id") != run.project_id or payload.get("run_id") != run.id:
            raise VerifiedDeliveryError("delivery record does not match canonical Engineering Run")
        if payload.get("lineage_id") != lineage_id:
            raise VerifiedDeliveryError("delivery record does not match accepted lineage")
        encoded = self._canonical(payload)
        existing = self.load(run_id=run.id, lineage_id=lineage_id)
        if existing is not None:
            if self._canonical(existing) != encoded:
                raise VerifiedDeliveryError("conflicting durable delivery record already exists")
            return existing, True

        conflicting = self.repository.session.scalar(
            select(EngineeringAttempt).where(
                EngineeringAttempt.run_id == run.id,
                EngineeringAttempt.stage == _DELIVERY_RECORD_STAGE,
            )
        )
        if conflicting is not None:
            raise VerifiedDeliveryError("Engineering Run already has a different durable delivery record")

        attempt = EngineeringAttempt(
            run_id=run.id,
            stage=_DELIVERY_RECORD_STAGE,
            attempt_number=1,
            operation_key=self.operation_key(lineage_id),
            status=_DELIVERY_RECORD_STATUS,
            program_id=_DELIVERY_RECORD_PROGRAM,
            tool_id=_DELIVERY_RECORD_TOOL,
            evidence_json=encoded,
            completed_at=utcnow(),
        )
        try:
            self.repository.session.add(attempt)
            self.repository.session.commit()
        except IntegrityError as exc:
            self.repository.session.rollback()
            replay = self.load(run_id=run.id, lineage_id=lineage_id)
            if replay is None or self._canonical(replay) != encoded:
                raise VerifiedDeliveryError("concurrent durable delivery record conflicted") from exc
            return replay, True
        return payload, False


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
        records: DeliveryRecordStore,
    ) -> None:
        self.allocator = allocator
        self.projects = projects
        self.preview_targets = preview_targets
        self.github = github
        self.vercel = vercel
        self.invocations = invocations
        self.records = records

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

    @staticmethod
    def _paired(result: object) -> ProviderActionAuditPair:
        evidence = getattr(result, "evidence", None)
        audit = getattr(result, "audit", None)
        if not isinstance(evidence, ProviderActionEvidence) or not isinstance(audit, ToolAuditRecord):
            raise VerifiedDeliveryError("provider success must retain bounded evidence and matching tool audit")
        return ProviderActionAuditPair(evidence=evidence, audit=audit)

    @staticmethod
    def _delivery_operation_key(identity: ProjectRunIdentity, lineage_id: str) -> str:
        digest = sha256(
            f"{identity.project_id}|{identity.run_id}|{lineage_id}".encode("utf-8")
        ).hexdigest()[:48]
        return f"delivery:{digest}"

    def resolve_record(
        self,
        run: EngineeringRun,
        *,
        accepted_lineage_id: str | None = None,
    ) -> VerifiedDeliveryResult | None:
        identity = self._identity(run)
        lineage_id = accepted_lineage_id or self._verified_lineage_id(run, identity)
        payload = self.records.load(run_id=identity.run_id, lineage_id=lineage_id)
        if payload is None:
            return None
        result = VerifiedDeliveryResult.from_record(payload, replayed=True)
        if result.project_id != identity.project_id or result.run_id != identity.run_id:
            raise VerifiedDeliveryError("durable delivery record belongs to a different Project/run")
        if result.lineage_id != lineage_id:
            raise VerifiedDeliveryError("durable delivery record belongs to a different lineage")
        return result

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
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise VerifiedDeliveryError("delivery operation key is required")
        identity = self._identity(run)
        accepted_lineage_id = self._verified_lineage_id(run, identity)
        try:
            current = self.allocator.current_lineage(identity)
        except Exception as exc:
            raise VerifiedDeliveryError("current durable source lineage is unavailable") from exc
        if current.lineage_id != accepted_lineage_id:
            raise VerifiedDeliveryError("current durable lineage moved after verified implementation")

        replay = self.resolve_record(run, accepted_lineage_id=accepted_lineage_id)
        if replay is not None:
            if replay.content_digest != current.content_digest:
                raise VerifiedDeliveryError("durable delivery record content no longer matches accepted lineage")
            return replay

        accepted, files = self._accepted_commit_files(identity, accepted_lineage_id)
        if accepted.content_digest != current.content_digest:
            raise VerifiedDeliveryError("accepted lineage content digest changed")
        root = self._root_lineage(identity, accepted)
        binding = self.projects.resolve(identity.project_id)
        delivery_key = self._delivery_operation_key(identity, accepted.lineage_id)

        actions: list[ProviderActionAuditPair] = []
        repository = self.github.resolve_repository(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_REPOSITORY_RESOLVE, f"{delivery_key}:resolve"),
        )
        actions.append(self._paired(repository))
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
            self._invocation(GITHUB_TOOL, ACTION_BRANCH_CREATE, f"{delivery_key}:branch"),
            branch_name=branch_name,
            base_revision=repository.value.head_revision,
        )
        actions.append(self._paired(branch))
        commit = self.github.commit_accepted_lineage(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_COMMIT_WRITE, f"{delivery_key}:commit"),
            branch_name=branch_name,
            expected_parent_revision=repository.value.head_revision,
            lineage=lineage,
            files=files,
        )
        actions.append(self._paired(commit))
        pull_request = self.github.create_pull_request(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_PULL_REQUEST_CREATE, f"{delivery_key}:pr-create"),
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
        actions.append(self._paired(pull_request))
        read_pull_request = self.github.read_pull_request(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_PULL_REQUEST_READ, f"{delivery_key}:pr-read"),
            number=pull_request.value.number,
        )
        actions.append(self._paired(read_pull_request))
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
            self._invocation(VERCEL_TOOL, ACTION_PREVIEW_CREATE, f"{delivery_key}:preview-create"),
            source_revision=commit.value.commit_revision,
            branch_name=branch_name,
            lineage=lineage,
        )
        actions.append(self._paired(preview))
        read_preview = self.vercel.read_preview(
            target,
            self._invocation(VERCEL_TOOL, ACTION_PREVIEW_READ, f"{delivery_key}:preview-read"),
            deployment_id=preview.value.deployment_id,
            expected_source_revision=commit.value.commit_revision,
        )
        actions.append(self._paired(read_preview))
        if read_preview.value.status in {VercelPreviewStatus.ERROR, VercelPreviewStatus.CANCELED}:
            raise VerifiedDeliveryError("Vercel Preview entered a terminal non-success state")

        result = VerifiedDeliveryResult(
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
            actions=tuple(actions),
            replayed=False,
        )
        persisted, record_replayed = self.records.persist(
            run=run,
            lineage_id=accepted.lineage_id,
            payload=result.to_record(),
        )
        if record_replayed:
            replayed = VerifiedDeliveryResult.from_record(persisted, replayed=True)
            if (
                replayed.project_id != result.project_id
                or replayed.run_id != result.run_id
                or replayed.lineage_id != result.lineage_id
                or replayed.commit_revision != result.commit_revision
                or replayed.pull_request_number != result.pull_request_number
                or replayed.preview_deployment_id != result.preview_deployment_id
            ):
                raise VerifiedDeliveryError("concurrent delivery replay did not match exact provider result")
            return replayed
        return result


@dataclass(frozen=True, slots=True)
class SourceDeliveryComposition:
    bootstrap: RepositoryLineageBootstrap
    delivery: VerifiedLineageDelivery

    def resolve_delivery(self, run: EngineeringRun) -> VerifiedDeliveryResult | None:
        return self.delivery.resolve_record(run)


__all__ = [
    "BootstrapResult",
    "DeliveryRecordStore",
    "DurableSourceAllocator",
    "EngineeringAttemptDeliveryRecordStore",
    "OwnerScopedProjectBindingResolver",
    "PreviewTargetResolver",
    "ProjectBindingResolver",
    "ProjectRepositoryBindingError",
    "ProviderActionAuditPair",
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
