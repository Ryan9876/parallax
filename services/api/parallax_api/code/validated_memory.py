from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Iterable
from uuid import UUID

from parallax_api.code.repository_intelligence import (
    CompatibilityState,
    RepositoryCompatibilityProfile,
    RepositoryShape,
)

VALIDATED_MEMORY_CONTRACT_VERSION = 1
_MAX_ITEMS = 256
_MAX_CONTENT_ITEMS = 24
_MAX_CONTENT_LENGTH = 400
_MAX_TOKENS = 64

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_MEMORY_ID_RE = re.compile(r"^[a-z][a-z0-9._/-]{2,95}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_ACCEPTANCE_ID_RE = re.compile(r"^AC-[0-9]{2,4}$")

_URL_RE = re.compile(r"(?i)\b(?:https?|postgres(?:ql)?|mysql|redis)://")
_ENV_ASSIGNMENT_RE = re.compile(r"\b[A-Z][A-Z0-9_]{2,}\s*=")
_SECRET_ASSIGNMENT_RE = re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|credential)\s*[:=]")
_COMMAND_RE = re.compile(r"(?i)^\s*(?:curl|wget|ssh|scp|bash|sh|zsh|powershell|cmd|sudo|rm|git|npm|pnpm|yarn|pip)\b")
_HIDDEN_REASONING_RE = re.compile(r"(?i)\b(?:scratchpad|hidden reasoning|chain of thought|internal reasoning)\b")
_UUID_TEXT_RE = re.compile(r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b")
_LONG_HEX_RE = re.compile(r"(?i)\b[0-9a-f]{32,}\b")
_SOURCE_PATH_RE = re.compile(r"(?i)(?:^|[\s`'\"])(?:src|app|apps|services|packages|private|home|users)/[A-Za-z0-9_.\-/]+")
_EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


class MemoryScope(StrEnum):
    PROJECT_PRIVATE = "PROJECT_PRIVATE"
    SANITIZED_SHARED = "SANITIZED_SHARED"


class MemoryKind(StrEnum):
    COMPATIBILITY_FACT = "COMPATIBILITY_FACT"
    IMPLEMENTATION_PATTERN = "IMPLEMENTATION_PATTERN"
    VALIDATION_EVIDENCE = "VALIDATION_EVIDENCE"


class MemorySelectionStatus(StrEnum):
    HIT = "HIT"
    MISS = "MISS"


class MemoryFailureCode(StrEnum):
    INVALID_MEMORY_CONTRACT = "INVALID_MEMORY_CONTRACT"
    MEMORY_VERSION_CONFLICT = "MEMORY_VERSION_CONFLICT"
    SHARED_MEMORY_NOT_APPROVED = "SHARED_MEMORY_NOT_APPROVED"
    MEMORY_KIND_NOT_DECLARABLE = "MEMORY_KIND_NOT_DECLARABLE"
    MEMORY_SCOPE_NOT_DECLARABLE = "MEMORY_SCOPE_NOT_DECLARABLE"
    OBJECTIVE_KIND_NOT_DECLARABLE = "OBJECTIVE_KIND_NOT_DECLARABLE"
    UNSAFE_SHARED_CONTENT = "UNSAFE_SHARED_CONTENT"
    NO_MEMORY_MATCH = "NO_MEMORY_MATCH"
    PROJECT_PRIVATE_BOUNDARY = "PROJECT_PRIVATE_BOUNDARY"
    MEMORY_KIND_NOT_REQUESTED = "MEMORY_KIND_NOT_REQUESTED"
    OBJECTIVE_NOT_APPLICABLE = "OBJECTIVE_NOT_APPLICABLE"
    CURRENT_REPOSITORY_NOT_SUPPORTED = "CURRENT_REPOSITORY_NOT_SUPPORTED"
    INCOMPATIBLE_REPOSITORY_SHAPE = "INCOMPATIBLE_REPOSITORY_SHAPE"
    MISSING_REPOSITORY_SIGNAL = "MISSING_REPOSITORY_SIGNAL"
    STALE_COMPATIBILITY_EVIDENCE = "STALE_COMPATIBILITY_EVIDENCE"
    VALIDATION_POLICY_STALE = "VALIDATION_POLICY_STALE"
    WORK_SPEC_IDENTITY_MISMATCH = "WORK_SPEC_IDENTITY_MISMATCH"
    REQUEST_IDENTITY_MISMATCH = "REQUEST_IDENTITY_MISMATCH"


class ValidatedMemoryError(ValueError):
    def __init__(self, code: MemoryFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class MemorySignalRequirement:
    kind: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _token(self.kind))
        object.__setattr__(self, "value", _token(self.value))

    @property
    def key(self) -> tuple[str, str]:
        return self.kind, self.value

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True, slots=True)
class MemoryProvenance:
    source_project_id: str
    source_repository_ref_digest: str
    source_revision: str
    source_identity_digest: str
    compatibility_profile_digest: str
    source_repository_shape: RepositoryShape
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    validation_evidence_digest: str
    evaluator_policy_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_project_id", _uuid(self.source_project_id))
        for name in (
            "source_repository_ref_digest",
            "source_identity_digest",
            "compatibility_profile_digest",
            "work_specification_digest",
            "validation_evidence_digest",
            "evaluator_policy_digest",
        ):
            object.__setattr__(self, name, _sha(getattr(self, name)))
        object.__setattr__(self, "source_revision", _revision(self.source_revision))
        if not isinstance(self.source_repository_shape, RepositoryShape):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id))
        object.__setattr__(self, "work_specification_revision", _positive_revision(self.work_specification_revision))
        object.__setattr__(self, "acceptance_ids", _acceptance(self.acceptance_ids))

    @classmethod
    def from_compatibility_profile(
        cls,
        *,
        profile: RepositoryCompatibilityProfile,
        work_specification_id: str,
        work_specification_revision: int,
        work_specification_digest: str,
        acceptance_ids: tuple[str, ...],
        validation_evidence_digest: str,
        evaluator_policy_digest: str,
    ) -> "MemoryProvenance":
        if not isinstance(profile, RepositoryCompatibilityProfile):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        return cls(
            source_project_id=profile.project_id,
            source_repository_ref_digest=profile.repository_ref_digest,
            source_revision=profile.source_revision,
            source_identity_digest=profile.source_identity_digest,
            compatibility_profile_digest=profile.profile_digest,
            source_repository_shape=profile.repository_shape,
            work_specification_id=work_specification_id,
            work_specification_revision=work_specification_revision,
            work_specification_digest=work_specification_digest,
            acceptance_ids=acceptance_ids,
            validation_evidence_digest=validation_evidence_digest,
            evaluator_policy_digest=evaluator_policy_digest,
        )

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "source_project_id": self.source_project_id,
            "source_repository_ref_digest": self.source_repository_ref_digest,
            "source_revision": self.source_revision,
            "source_identity_digest": self.source_identity_digest,
            "compatibility_profile_digest": self.compatibility_profile_digest,
            "source_repository_shape": self.source_repository_shape.value,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "validation_evidence_digest": self.validation_evidence_digest,
            "evaluator_policy_digest": self.evaluator_policy_digest,
        }

    def safe_digest_metadata(self) -> dict[str, str]:
        return {
            "provenance_digest": self.digest,
            "validation_evidence_digest": self.validation_evidence_digest,
            "evaluator_policy_digest": self.evaluator_policy_digest,
        }


@dataclass(frozen=True, slots=True)
class ValidatedMemoryItem:
    memory_id: str
    version: str
    kind: MemoryKind
    scope: MemoryScope
    provenance: MemoryProvenance
    objective_kinds: tuple[str, ...]
    compatible_shapes: tuple[RepositoryShape, ...]
    required_signals: tuple[MemorySignalRequirement, ...] = ()
    content: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_id", _memory_id(self.memory_id))
        object.__setattr__(self, "version", _semver(self.version))
        if not isinstance(self.kind, MemoryKind) or not isinstance(self.scope, MemoryScope):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        if not isinstance(self.provenance, MemoryProvenance):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        object.__setattr__(self, "objective_kinds", _tokens(self.objective_kinds, require_nonempty=True))
        shapes = tuple(self.compatible_shapes)
        if not shapes or len(shapes) > 8 or any(not isinstance(item, RepositoryShape) for item in shapes):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        shapes = tuple(sorted(set(shapes), key=lambda item: item.value))
        object.__setattr__(self, "compatible_shapes", shapes)
        signals = tuple(self.required_signals)
        if len(signals) > _MAX_TOKENS or any(not isinstance(item, MemorySignalRequirement) for item in signals):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        if len({item.key for item in signals}) != len(signals):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        object.__setattr__(self, "required_signals", tuple(sorted(signals, key=lambda item: item.key)))
        object.__setattr__(self, "content", _content(self.content))
        if self.kind is MemoryKind.COMPATIBILITY_FACT and self.compatible_shapes != (
            self.provenance.source_repository_shape,
        ):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self._canonical_payload())).hexdigest()

    def _canonical_payload(self) -> dict[str, object]:
        return {
            "contract_version": VALIDATED_MEMORY_CONTRACT_VERSION,
            "memory_id": self.memory_id,
            "version": self.version,
            "kind": self.kind.value,
            "scope": self.scope.value,
            "provenance": self.provenance.as_dict(),
            "objective_kinds": list(self.objective_kinds),
            "compatible_shapes": [item.value for item in self.compatible_shapes],
            "required_signals": [item.as_dict() for item in self.required_signals],
            "content": list(self.content),
        }

    def server_metadata(self) -> dict[str, object]:
        return {
            **self._canonical_payload(),
            "content_digest": self.digest,
            "contains_raw_source": False,
            "contains_prompt": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class SharedMemoryApproval:
    memory_id: str
    version: str
    content_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "memory_id", _memory_id(self.memory_id))
        object.__setattr__(self, "version", _semver(self.version))
        object.__setattr__(self, "content_digest", _sha(self.content_digest))

    @property
    def key(self) -> tuple[str, str]:
        return self.memory_id, self.version

    def as_dict(self) -> dict[str, str]:
        return {"memory_id": self.memory_id, "version": self.version, "content_digest": self.content_digest}


@dataclass(frozen=True, slots=True)
class MemoryAdmissionPolicy:
    shared_approvals: tuple[SharedMemoryApproval, ...] = ()
    declarable_kinds: tuple[MemoryKind, ...] = tuple(MemoryKind)
    declarable_scopes: tuple[MemoryScope, ...] = tuple(MemoryScope)
    declarable_objective_kinds: tuple[str, ...] = ("implement-feature",)

    def __post_init__(self) -> None:
        approvals = tuple(self.shared_approvals)
        if len(approvals) > _MAX_ITEMS or any(not isinstance(item, SharedMemoryApproval) for item in approvals):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        if len({item.key for item in approvals}) != len(approvals):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        object.__setattr__(self, "shared_approvals", tuple(sorted(approvals, key=lambda item: item.key)))
        object.__setattr__(self, "declarable_kinds", _enum_values(self.declarable_kinds, MemoryKind))
        object.__setattr__(self, "declarable_scopes", _enum_values(self.declarable_scopes, MemoryScope))
        object.__setattr__(
            self,
            "declarable_objective_kinds",
            _tokens(self.declarable_objective_kinds, require_nonempty=True),
        )

    @property
    def digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "shared_approvals": [item.as_dict() for item in self.shared_approvals],
                    "declarable_kinds": [item.value for item in self.declarable_kinds],
                    "declarable_scopes": [item.value for item in self.declarable_scopes],
                    "declarable_objective_kinds": list(self.declarable_objective_kinds),
                }
            )
        ).hexdigest()

    def shared_digest(self, memory_id: str, version: str) -> str | None:
        for approval in self.shared_approvals:
            if approval.memory_id == memory_id and approval.version == version:
                return approval.content_digest
        return None


@dataclass(frozen=True, slots=True)
class RegisteredMemoryItem:
    item: ValidatedMemoryItem
    content_digest: str
    admission_policy_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "content_digest", _sha(self.content_digest))
        object.__setattr__(self, "admission_policy_digest", _sha(self.admission_policy_digest))
        if self.content_digest != self.item.digest:
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)

    @property
    def key(self) -> tuple[str, str]:
        return self.item.memory_id, self.item.version


class ValidatedMemoryRegistry:
    def __init__(self, policy: MemoryAdmissionPolicy) -> None:
        if not isinstance(policy, MemoryAdmissionPolicy):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        self.policy = policy
        self._items: dict[tuple[str, str], RegisteredMemoryItem] = {}

    @property
    def digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "policy_digest": self.policy.digest,
                    "items": [
                        {"memory_id": item.item.memory_id, "version": item.item.version, "content_digest": item.content_digest}
                        for item in self.registered()
                    ],
                }
            )
        ).hexdigest()

    def admit(self, item: ValidatedMemoryItem) -> RegisteredMemoryItem:
        if not isinstance(item, ValidatedMemoryItem):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        key = (item.memory_id, item.version)
        existing = self._items.get(key)
        if existing is not None:
            if existing.content_digest == item.digest:
                return existing
            raise ValidatedMemoryError(MemoryFailureCode.MEMORY_VERSION_CONFLICT)
        if item.kind not in self.policy.declarable_kinds:
            raise ValidatedMemoryError(MemoryFailureCode.MEMORY_KIND_NOT_DECLARABLE)
        if item.scope not in self.policy.declarable_scopes:
            raise ValidatedMemoryError(MemoryFailureCode.MEMORY_SCOPE_NOT_DECLARABLE)
        if not set(item.objective_kinds).issubset(self.policy.declarable_objective_kinds):
            raise ValidatedMemoryError(MemoryFailureCode.OBJECTIVE_KIND_NOT_DECLARABLE)
        if item.scope is MemoryScope.SANITIZED_SHARED:
            approved = self.policy.shared_digest(item.memory_id, item.version)
            if approved != item.digest:
                raise ValidatedMemoryError(MemoryFailureCode.SHARED_MEMORY_NOT_APPROVED)
            _validate_shared_content(item)
        registered = RegisteredMemoryItem(item, item.digest, self.policy.digest)
        self._items[key] = registered
        return registered

    def registered(self) -> tuple[RegisteredMemoryItem, ...]:
        return tuple(self._items[key] for key in sorted(self._items))


@dataclass(frozen=True, slots=True)
class MemoryReuseRequest:
    requester_project_id: str
    compatibility: RepositoryCompatibilityProfile
    objective_kind: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    evaluator_policy_digest: str
    requested_kinds: tuple[MemoryKind, ...]

    def __post_init__(self) -> None:
        project = _uuid(self.requester_project_id)
        object.__setattr__(self, "requester_project_id", project)
        if not isinstance(self.compatibility, RepositoryCompatibilityProfile):
            raise ValidatedMemoryError(MemoryFailureCode.REQUEST_IDENTITY_MISMATCH)
        if self.compatibility.project_id != project:
            raise ValidatedMemoryError(MemoryFailureCode.REQUEST_IDENTITY_MISMATCH)
        object.__setattr__(self, "objective_kind", _token(self.objective_kind))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id))
        object.__setattr__(self, "work_specification_revision", _positive_revision(self.work_specification_revision))
        object.__setattr__(self, "work_specification_digest", _sha(self.work_specification_digest))
        object.__setattr__(self, "acceptance_ids", _acceptance(self.acceptance_ids))
        object.__setattr__(self, "evaluator_policy_digest", _sha(self.evaluator_policy_digest))
        object.__setattr__(self, "requested_kinds", _enum_values(self.requested_kinds, MemoryKind))

    @property
    def digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "requester_project_id": self.requester_project_id,
                    "source_identity_digest": self.compatibility.source_identity_digest,
                    "compatibility_profile_digest": self.compatibility.profile_digest,
                    "repository_shape": self.compatibility.repository_shape.value,
                    "compatibility_state": self.compatibility.compatibility_state.value,
                    "objective_kind": self.objective_kind,
                    "work_specification_id": self.work_specification_id,
                    "work_specification_revision": self.work_specification_revision,
                    "work_specification_digest": self.work_specification_digest,
                    "acceptance_ids": list(self.acceptance_ids),
                    "evaluator_policy_digest": self.evaluator_policy_digest,
                    "requested_kinds": [item.value for item in self.requested_kinds],
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class ReusableMemoryCandidate:
    memory_id: str
    version: str
    content_digest: str
    kind: MemoryKind
    scope: MemoryScope
    content: tuple[str, ...]
    provenance_digest: str
    validation_evidence_digest: str
    evaluator_policy_digest: str
    compatible_shapes: tuple[RepositoryShape, ...]
    required_signals: tuple[MemorySignalRequirement, ...]
    fresh_validation_required: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "memory_id": self.memory_id,
            "version": self.version,
            "content_digest": self.content_digest,
            "kind": self.kind.value,
            "scope": self.scope.value,
            "content": list(self.content),
            "provenance_digest": self.provenance_digest,
            "validation_evidence_digest": self.validation_evidence_digest,
            "evaluator_policy_digest": self.evaluator_policy_digest,
            "compatible_shapes": [item.value for item in self.compatible_shapes],
            "required_signals": [item.as_dict() for item in self.required_signals],
            "fresh_validation_required": True,
            "contains_source_project_identity": False,
            "contains_repository_identity": False,
            "contains_source_revision": False,
            "contains_raw_source": False,
            "contains_prompt": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "grants_tools": False,
            "grants_service_bindings": False,
            "grants_provider_scope": False,
            "grants_approval": False,
            "performs_source_mutation": False,
            "performs_execution": False,
            "performs_deployment": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class MemoryRejectionSummary:
    code: MemoryFailureCode
    count: int

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code.value, "count": self.count}


@dataclass(frozen=True, slots=True)
class MemorySelectionResult:
    selection_id: str
    status: MemorySelectionStatus
    reason: MemoryFailureCode | None
    request_digest: str
    visible_registry_digest: str
    current_work_specification_digest: str
    current_evaluator_policy_digest: str
    visible_candidate_count: int
    eligible_hit_count: int
    selected_compatibility_fact_count: int
    selected_implementation_pattern_count: int
    selected_validation_evidence_count: int
    candidates: tuple[ReusableMemoryCandidate, ...]
    rejections: tuple[MemoryRejectionSummary, ...]
    fresh_validation_required: bool = True

    def as_dict(self) -> dict[str, object]:
        return {
            "selection_id": self.selection_id,
            "status": self.status.value,
            "reason": self.reason.value if self.reason is not None else None,
            "request_digest": self.request_digest,
            "visible_registry_digest": self.visible_registry_digest,
            "current_work_specification_digest": self.current_work_specification_digest,
            "current_evaluator_policy_digest": self.current_evaluator_policy_digest,
            "visible_candidate_count": self.visible_candidate_count,
            "eligible_hit_count": self.eligible_hit_count,
            "selected_compatibility_fact_count": self.selected_compatibility_fact_count,
            "selected_implementation_pattern_count": self.selected_implementation_pattern_count,
            "selected_validation_evidence_count": self.selected_validation_evidence_count,
            "candidates": [item.as_dict() for item in self.candidates],
            "rejections": [item.as_dict() for item in self.rejections],
            "fresh_validation_required": True,
            "contains_private_cross_project_metadata": False,
            "contains_raw_source": False,
            "contains_prompt": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "grants_tools": False,
            "grants_service_bindings": False,
            "grants_provider_scope": False,
            "grants_approval": False,
            "performs_source_mutation": False,
            "performs_execution": False,
            "performs_deployment": False,
            "grants_authority": False,
        }


class ValidatedMemorySelector:
    def __init__(self, registry: ValidatedMemoryRegistry) -> None:
        if not isinstance(registry, ValidatedMemoryRegistry):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        self.registry = registry

    def select(self, request: MemoryReuseRequest) -> MemorySelectionResult:
        if not isinstance(request, MemoryReuseRequest):
            raise ValidatedMemoryError(MemoryFailureCode.REQUEST_IDENTITY_MISMATCH)
        visible: list[RegisteredMemoryItem] = []
        candidates: list[ReusableMemoryCandidate] = []
        rejected: Counter[MemoryFailureCode] = Counter()
        for registered in self.registry.registered():
            item = registered.item
            if item.scope is MemoryScope.PROJECT_PRIVATE and item.provenance.source_project_id != request.requester_project_id:
                continue
            visible.append(registered)
            reason = _ineligibility_reason(item, request)
            if reason:
                rejected[reason] += 1
            else:
                candidates.append(_candidate(registered))
        candidate_items = tuple(sorted(candidates, key=lambda item: (item.kind.value, item.memory_id, item.version, item.content_digest)))
        rejections = tuple(
            MemoryRejectionSummary(code, count)
            for code, count in sorted(rejected.items(), key=lambda pair: pair[0].value)
        )
        counts = Counter(item.kind for item in candidate_items)
        status = MemorySelectionStatus.HIT if candidate_items else MemorySelectionStatus.MISS
        reason = None if candidate_items else MemoryFailureCode.NO_MEMORY_MATCH
        visible_digest = _visible_digest(self.registry.policy.digest, visible)
        core = {
            "request_digest": request.digest,
            "visible_registry_digest": visible_digest,
            "status": status.value,
            "reason": reason.value if reason else None,
            "visible_candidate_count": len(visible),
            "candidate_identities": [
                (item.memory_id, item.version, item.content_digest, item.provenance_digest)
                for item in candidate_items
            ],
            "rejections": [item.as_dict() for item in rejections],
            "work_specification_digest": request.work_specification_digest,
            "evaluator_policy_digest": request.evaluator_policy_digest,
            "fresh_validation_required": True,
        }
        return MemorySelectionResult(
            selection_id=f"memsel:{sha256(_canonical_json(core)).hexdigest()}",
            status=status,
            reason=reason,
            request_digest=request.digest,
            visible_registry_digest=visible_digest,
            current_work_specification_digest=request.work_specification_digest,
            current_evaluator_policy_digest=request.evaluator_policy_digest,
            visible_candidate_count=len(visible),
            eligible_hit_count=len(candidate_items),
            selected_compatibility_fact_count=counts.get(MemoryKind.COMPATIBILITY_FACT, 0),
            selected_implementation_pattern_count=counts.get(MemoryKind.IMPLEMENTATION_PATTERN, 0),
            selected_validation_evidence_count=counts.get(MemoryKind.VALIDATION_EVIDENCE, 0),
            candidates=candidate_items,
            rejections=rejections,
        )


def public_selection_field_names() -> tuple[str, ...]:
    public_types = (ReusableMemoryCandidate, MemoryRejectionSummary, MemorySelectionResult)
    return tuple(sorted({field.name for type_ in public_types for field in fields(type_)}))


def _ineligibility_reason(item: ValidatedMemoryItem, request: MemoryReuseRequest) -> MemoryFailureCode | None:
    if item.kind not in request.requested_kinds:
        return MemoryFailureCode.MEMORY_KIND_NOT_REQUESTED
    if request.objective_kind not in item.objective_kinds:
        return MemoryFailureCode.OBJECTIVE_NOT_APPLICABLE
    if request.compatibility.compatibility_state is not CompatibilityState.SUPPORTED:
        return MemoryFailureCode.CURRENT_REPOSITORY_NOT_SUPPORTED
    if request.compatibility.repository_shape not in item.compatible_shapes:
        return MemoryFailureCode.INCOMPATIBLE_REPOSITORY_SHAPE
    current_signals = {(signal.kind, signal.value) for signal in request.compatibility.signals}
    if not {signal.key for signal in item.required_signals}.issubset(current_signals):
        return MemoryFailureCode.MISSING_REPOSITORY_SIGNAL
    if item.provenance.evaluator_policy_digest != request.evaluator_policy_digest:
        return MemoryFailureCode.VALIDATION_POLICY_STALE
    if item.kind is MemoryKind.COMPATIBILITY_FACT and (
        item.provenance.source_identity_digest != request.compatibility.source_identity_digest
        or item.provenance.compatibility_profile_digest != request.compatibility.profile_digest
    ):
        return MemoryFailureCode.STALE_COMPATIBILITY_EVIDENCE
    return None


def _candidate(registered: RegisteredMemoryItem) -> ReusableMemoryCandidate:
    item = registered.item
    return ReusableMemoryCandidate(
        memory_id=item.memory_id,
        version=item.version,
        content_digest=registered.content_digest,
        kind=item.kind,
        scope=item.scope,
        content=item.content,
        provenance_digest=item.provenance.digest,
        validation_evidence_digest=item.provenance.validation_evidence_digest,
        evaluator_policy_digest=item.provenance.evaluator_policy_digest,
        compatible_shapes=item.compatible_shapes,
        required_signals=item.required_signals,
    )


def _visible_digest(policy_digest: str, items: Iterable[RegisteredMemoryItem]) -> str:
    payload = [
        (item.item.memory_id, item.item.version, item.content_digest)
        for item in sorted(items, key=lambda item: (item.item.memory_id, item.item.version, item.content_digest))
    ]
    return sha256(_canonical_json({"policy_digest": _sha(policy_digest), "visible_items": payload})).hexdigest()


def _validate_shared_content(item: ValidatedMemoryItem) -> None:
    p = item.provenance
    exact_private = (
        p.source_project_id,
        p.source_repository_ref_digest,
        p.source_revision,
        p.source_identity_digest,
        p.compatibility_profile_digest,
        p.work_specification_id,
        p.work_specification_digest,
    )
    for value in item.content:
        if any(fragment in value for fragment in exact_private):
            raise ValidatedMemoryError(MemoryFailureCode.UNSAFE_SHARED_CONTENT)
        if _UUID_TEXT_RE.search(value) or _LONG_HEX_RE.search(value) or _SOURCE_PATH_RE.search(value) or _EMAIL_RE.search(value):
            raise ValidatedMemoryError(MemoryFailureCode.UNSAFE_SHARED_CONTENT)


def _content(values: Iterable[str]) -> tuple[str, ...]:
    values = tuple(values)
    if not values or len(values) > _MAX_CONTENT_ITEMS:
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    normalized: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        value = item.strip()
        if not value or len(value) > _MAX_CONTENT_LENGTH or "\n" in value or "\r" in value:
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        if any(pattern.search(value) for pattern in (_URL_RE, _ENV_ASSIGNMENT_RE, _SECRET_ASSIGNMENT_RE, _COMMAND_RE, _HIDDEN_REASONING_RE)):
            raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
        normalized.append(value)
    if len(set(normalized)) != len(normalized):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return tuple(normalized)


def _tokens(values: Iterable[str], *, require_nonempty: bool) -> tuple[str, ...]:
    values = tuple(values)
    if len(values) > _MAX_TOKENS or (require_nonempty and not values):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    normalized = tuple(_token(value) for value in values)
    if len(set(normalized)) != len(normalized):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return tuple(sorted(normalized))


def _enum_values(values: Iterable[StrEnum], enum_type: type[StrEnum]) -> tuple:
    values = tuple(values)
    if not values or len(values) > _MAX_TOKENS or any(not isinstance(value, enum_type) for value in values):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    if len(set(values)) != len(values):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return tuple(sorted(values, key=lambda value: value.value))


def _acceptance(values: Iterable[str]) -> tuple[str, ...]:
    values = tuple(values)
    if not values or len(values) > 128 or any(not isinstance(value, str) or not _ACCEPTANCE_ID_RE.fullmatch(value) for value in values):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    if len(set(values)) != len(values):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return values


def _token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return value


def _memory_id(value: str) -> str:
    if not isinstance(value, str) or not _MEMORY_ID_RE.fullmatch(value):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return value


def _semver(value: str) -> str:
    if not isinstance(value, str) or not _SEMVER_RE.fullmatch(value):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return value


def _sha(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return value


def _revision(value: str) -> str:
    if not isinstance(value, str) or not _GIT_REVISION_RE.fullmatch(value):
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return value


def _uuid(value: str) -> str:
    try:
        canonical = str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT) from exc
    if canonical != value:
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return canonical


def _positive_revision(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 1_000_000:
        raise ValidatedMemoryError(MemoryFailureCode.INVALID_MEMORY_CONTRACT)
    return value


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


__all__ = [
    "MemoryAdmissionPolicy",
    "MemoryFailureCode",
    "MemoryKind",
    "MemoryProvenance",
    "MemoryRejectionSummary",
    "MemoryReuseRequest",
    "MemoryScope",
    "MemorySelectionResult",
    "MemorySelectionStatus",
    "MemorySignalRequirement",
    "RegisteredMemoryItem",
    "ReusableMemoryCandidate",
    "SharedMemoryApproval",
    "VALIDATED_MEMORY_CONTRACT_VERSION",
    "ValidatedMemoryError",
    "ValidatedMemoryItem",
    "ValidatedMemoryRegistry",
    "ValidatedMemorySelector",
    "public_selection_field_names",
]
