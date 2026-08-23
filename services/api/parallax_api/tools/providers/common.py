from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Generic, TypeVar
from urllib.parse import urlparse
from uuid import UUID

from ..audit import audit_denied, audit_tool_result
from ..contracts import (
    AuthorityDecision,
    ToolAuditRecord,
    ToolAuthorityRequest,
    ToolExecutionResult,
    canonical_digest,
)
from ..registry import ToolCapabilityRegistry


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SOURCE_REVISION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
_GITHUB_REPOSITORY = re.compile(
    r"^github:(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?)/"
    r"(?P<repo>[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?)$"
)


class ProviderActionState(str, Enum):
    DENIED = "DENIED"
    FAILED = "FAILED"
    SUCCEEDED = "SUCCEEDED"


def require_project_id(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("project_ref must be canonical Project.id text")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ValueError("project_ref must be canonical Project.id UUID") from exc
    canonical = str(parsed)
    if value.lower() != canonical:
        raise ValueError("project_ref must use canonical Project.id UUID form")
    return canonical


def require_repository_ref(value: str) -> str:
    if not isinstance(value, str) or not _GITHUB_REPOSITORY.fullmatch(value):
        raise ValueError("repository_ref must use github:owner/repository identity form")
    return value


def require_opaque_ref(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _OPAQUE_REF.fullmatch(value):
        raise ValueError(f"{field} must be a bounded opaque identifier")
    return value


def require_source_revision(value: str, *, field: str = "source_revision") -> str:
    if not isinstance(value, str) or not _SOURCE_REVISION.fullmatch(value):
        raise ValueError(f"{field} must be a bounded source revision")
    if value in {".", ".."} or value.startswith("/") or "//" in value or ".." in value.split("/"):
        raise ValueError(f"{field} contains an unsafe revision path")
    return value


def require_sha256(value: str, *, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{field} must be lowercase sha256 hex")
    return value


def require_https_url(value: str, *, field: str, allowed_suffix: str) -> str:
    if not isinstance(value, str) or len(value) > 512:
        raise ValueError(f"{field} must be a bounded https URL")
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.fragment:
        raise ValueError(f"{field} must be a safe https URL")
    suffix = allowed_suffix.lower()
    if host != suffix.lstrip(".") and not host.endswith(suffix):
        raise ValueError(f"{field} host is outside the allowed provider domain")
    return value


@dataclass(frozen=True, slots=True)
class ProviderProjectBinding:
    project_ref: str
    repository_ref: str

    def __post_init__(self) -> None:
        require_project_id(self.project_ref)
        require_repository_ref(self.repository_ref)

    @property
    def repository_identity_digest(self) -> str:
        return canonical_digest(
            {"project_ref": self.project_ref, "repository_ref": self.repository_ref}
        )


@dataclass(frozen=True, slots=True)
class AcceptedSourceLineage:
    lineage_ref: str
    content_digest: str

    def __post_init__(self) -> None:
        require_opaque_ref(self.lineage_ref, field="lineage_ref")
        require_sha256(self.content_digest, field="content_digest")


@dataclass(frozen=True, slots=True)
class ProviderInvocation:
    request_id: str
    capability_id: str
    actor_ref: str
    approval_id: str | None = None

    def __post_init__(self) -> None:
        require_opaque_ref(self.request_id, field="request_id")
        require_opaque_ref(self.capability_id, field="capability_id")
        require_opaque_ref(self.actor_ref, field="actor_ref")
        if self.approval_id is not None:
            require_opaque_ref(self.approval_id, field="approval_id")


@dataclass(frozen=True, slots=True)
class ProviderActionEvidence:
    provider: str
    action: str
    state: ProviderActionState
    project_ref: str
    repository_identity_digest: str
    source_revision: str | None = None
    lineage_digest: str | None = None
    result_identity: str | None = None
    result_status: str | None = None
    safe_url: str | None = None

    def __post_init__(self) -> None:
        if self.provider not in {"github", "vercel"}:
            raise ValueError("provider evidence must identify github or vercel")
        if not isinstance(self.action, str) or not self.action or len(self.action) > 64:
            raise ValueError("action must be bounded")
        if not isinstance(self.state, ProviderActionState):
            raise TypeError("state must be ProviderActionState")
        require_project_id(self.project_ref)
        require_sha256(self.repository_identity_digest, field="repository_identity_digest")
        if self.source_revision is not None:
            require_source_revision(self.source_revision)
        if self.lineage_digest is not None:
            require_sha256(self.lineage_digest, field="lineage_digest")
        if self.result_identity is not None:
            require_opaque_ref(self.result_identity, field="result_identity")
        if self.result_status is not None:
            if not re.fullmatch(r"[A-Z][A-Z0-9_.:-]{0,63}", self.result_status):
                raise ValueError("result_status must be a bounded normalized code")
        if self.safe_url is not None:
            if self.provider == "github":
                require_https_url(self.safe_url, field="safe_url", allowed_suffix="github.com")
            else:
                require_https_url(self.safe_url, field="safe_url", allowed_suffix=".vercel.app")

    @property
    def digest(self) -> str:
        return canonical_digest(
            {
                "provider": self.provider,
                "action": self.action,
                "state": self.state.value,
                "project_ref": self.project_ref,
                "repository_identity_digest": self.repository_identity_digest,
                "source_revision": self.source_revision,
                "lineage_digest": self.lineage_digest,
                "result_identity": self.result_identity,
                "result_status": self.result_status,
                "safe_url": self.safe_url,
            }
        )


T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ProviderActionSuccess(Generic[T]):
    value: T
    evidence: ProviderActionEvidence
    audit: ToolAuditRecord

    def __post_init__(self) -> None:
        if self.evidence.state is not ProviderActionState.SUCCEEDED:
            raise ValueError("success result requires SUCCEEDED evidence")


class ProviderActionDenied(PermissionError):
    def __init__(self, *, evidence: ProviderActionEvidence, audit: ToolAuditRecord) -> None:
        super().__init__(f"provider authority denied: {audit.deny_reason.value if audit.deny_reason else 'UNKNOWN'}")
        self.evidence = evidence
        self.audit = audit


class ProviderActionFailed(RuntimeError):
    def __init__(self, *, evidence: ProviderActionEvidence, audit: ToolAuditRecord) -> None:
        super().__init__(f"provider action failed: {audit.result_code or 'PROVIDER_FAILED'}")
        self.evidence = evidence
        self.audit = audit


class ProviderClientError(RuntimeError):
    def __init__(self, result_code: str, *, result_identity: str | None = None) -> None:
        result = ToolExecutionResult(
            succeeded=False,
            result_code=result_code,
            result_identity=result_identity,
        )
        super().__init__(result.result_code)
        self.result = result


class AuthorizedProviderExecutor:
    """Bridge one fixed typed provider action through the Wave 1 authority registry."""

    def __init__(self, registry: ToolCapabilityRegistry) -> None:
        if not isinstance(registry, ToolCapabilityRegistry):
            raise TypeError("registry must be ToolCapabilityRegistry")
        self.registry = registry

    def authorize(
        self,
        *,
        binding: ProviderProjectBinding,
        invocation: ProviderInvocation,
        tool: str,
        action: str,
    ) -> tuple[ToolAuthorityRequest, AuthorityDecision]:
        request = ToolAuthorityRequest(
            request_id=invocation.request_id,
            capability_id=invocation.capability_id,
            project_ref=binding.project_ref,
            tool=tool,
            action=action,
            actor_ref=invocation.actor_ref,
        )
        decision = self.registry.authorize(request, approval_id=invocation.approval_id)
        if not decision.allowed:
            audit = audit_denied(request, decision)
            evidence = ProviderActionEvidence(
                provider=tool,
                action=action,
                state=ProviderActionState.DENIED,
                project_ref=binding.project_ref,
                repository_identity_digest=binding.repository_identity_digest,
                result_status=decision.deny_reason.value if decision.deny_reason else "DENIED",
            )
            raise ProviderActionDenied(evidence=evidence, audit=audit)
        return request, decision

    def succeed(
        self,
        *,
        request: ToolAuthorityRequest,
        decision: AuthorityDecision,
        binding: ProviderProjectBinding,
        action: str,
        value: T,
        result_code: str,
        result_identity: str | None,
        source_revision: str | None = None,
        lineage: AcceptedSourceLineage | None = None,
        safe_url: str | None = None,
    ) -> ProviderActionSuccess[T]:
        execution = ToolExecutionResult(
            succeeded=True,
            result_code=result_code,
            result_identity=result_identity,
        )
        audit = audit_tool_result(request, decision, execution)
        evidence = ProviderActionEvidence(
            provider=request.tool,
            action=action,
            state=ProviderActionState.SUCCEEDED,
            project_ref=binding.project_ref,
            repository_identity_digest=binding.repository_identity_digest,
            source_revision=source_revision,
            lineage_digest=lineage.content_digest if lineage else None,
            result_identity=result_identity,
            result_status=result_code,
            safe_url=safe_url,
        )
        return ProviderActionSuccess(value=value, evidence=evidence, audit=audit)

    def fail(
        self,
        *,
        request: ToolAuthorityRequest,
        decision: AuthorityDecision,
        binding: ProviderProjectBinding,
        action: str,
        error: ProviderClientError,
        source_revision: str | None = None,
        lineage: AcceptedSourceLineage | None = None,
    ) -> ProviderActionFailed:
        audit = audit_tool_result(request, decision, error.result)
        evidence = ProviderActionEvidence(
            provider=request.tool,
            action=action,
            state=ProviderActionState.FAILED,
            project_ref=binding.project_ref,
            repository_identity_digest=binding.repository_identity_digest,
            source_revision=source_revision,
            lineage_digest=lineage.content_digest if lineage else None,
            result_identity=error.result.result_identity,
            result_status=error.result.result_code,
        )
        return ProviderActionFailed(evidence=evidence, audit=audit)
