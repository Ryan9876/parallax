from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Iterable
from uuid import UUID

from .repository_intelligence import (
    CompatibilityState,
    RepositoryCompatibilityProfile,
    RepositoryShape,
)


SKILL_CONTRACT_VERSION = 1
_MAX_SKILL_ID_BYTES = 64
_MAX_STEP_COUNT = 32
_MAX_STEP_BYTES = 512
_MAX_FIELDS = 32
_MAX_OBJECTIVE_KINDS = 16
_MAX_SIGNAL_REQUIREMENTS = 32
_MAX_CAPABILITIES = 32
_MAX_EVIDENCE_REQUIREMENTS = 32
_MAX_EVIDENCE_ITEMS = 32
_MAX_REFERENCE_BYTES = 192
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9.-]{2,63}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_REFERENCE_RE = re.compile(r"^(?:artifact|evidence|result):[A-Za-z0-9._-]{1,128}$")


class SkillFailureCode(StrEnum):
    SKILL_NOT_APPROVED = "SKILL_NOT_APPROVED"
    SKILL_VERSION_CONFLICT = "SKILL_VERSION_CONFLICT"
    INVALID_SKILL_CONTRACT = "INVALID_SKILL_CONTRACT"
    CAPABILITY_NOT_DECLARABLE = "CAPABILITY_NOT_DECLARABLE"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
    INCOMPATIBLE_REPOSITORY = "INCOMPATIBLE_REPOSITORY"
    NO_MATCHING_SKILL = "NO_MATCHING_SKILL"
    AMBIGUOUS_SKILL_SELECTION = "AMBIGUOUS_SKILL_SELECTION"
    INVOCATION_IDENTITY_MISMATCH = "INVOCATION_IDENTITY_MISMATCH"
    EVIDENCE_LIMIT_EXCEEDED = "EVIDENCE_LIMIT_EXCEEDED"


class SkillValueType(StrEnum):
    STRING = "string"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    DIGEST = "digest"
    REFERENCE = "reference"


class SkillSelectionStatus(StrEnum):
    SELECTED = "SELECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class SkillInvocationStatus(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class SkillEvidenceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INFO = "INFO"


class GovernedSkillError(ValueError):
    def __init__(self, code: SkillFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class SkillField:
    field_id: str
    value_type: SkillValueType
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "field_id", _safe_token(self.field_id))
        if not isinstance(self.value_type, SkillValueType):
            try:
                object.__setattr__(self, "value_type", SkillValueType(self.value_type))
            except (TypeError, ValueError) as exc:
                raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT) from exc
        if not isinstance(self.required, bool):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "field_id": self.field_id,
            "value_type": self.value_type.value,
            "required": self.required,
        }


@dataclass(frozen=True, slots=True)
class SkillSignalRequirement:
    kind: str
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _safe_token(self.kind))
        object.__setattr__(self, "value", _safe_token(self.value))

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "value": self.value}


@dataclass(frozen=True, slots=True)
class PortableSkill:
    skill_id: str
    version: str
    procedure_steps: tuple[str, ...]
    input_fields: tuple[SkillField, ...]
    output_fields: tuple[SkillField, ...]
    objective_kinds: tuple[str, ...]
    compatible_shapes: tuple[RepositoryShape, ...] = ()
    required_signals: tuple[SkillSignalRequirement, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    evidence_requirements: tuple[str, ...] = ()
    priority: int = 0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.skill_id, str)
            or len(self.skill_id.encode("utf-8")) > _MAX_SKILL_ID_BYTES
            or not _SKILL_ID_RE.fullmatch(self.skill_id)
        ):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        if not isinstance(self.version, str) or not _SEMVER_RE.fullmatch(self.version):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        if not isinstance(self.priority, int) or isinstance(self.priority, bool) or not 0 <= self.priority <= 100:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)

        steps = _bounded_steps(self.procedure_steps)
        inputs = _bounded_fields(self.input_fields)
        outputs = _bounded_fields(self.output_fields)
        objectives = _bounded_token_set(self.objective_kinds, limit=_MAX_OBJECTIVE_KINDS, require_nonempty=True)
        shapes = _bounded_shapes(self.compatible_shapes)
        signals = _bounded_signals(self.required_signals)
        capabilities = _bounded_token_set(self.required_capabilities, limit=_MAX_CAPABILITIES)
        evidence = _bounded_token_set(self.evidence_requirements, limit=_MAX_EVIDENCE_REQUIREMENTS)

        object.__setattr__(self, "procedure_steps", steps)
        object.__setattr__(self, "input_fields", inputs)
        object.__setattr__(self, "output_fields", outputs)
        object.__setattr__(self, "objective_kinds", objectives)
        object.__setattr__(self, "compatible_shapes", shapes)
        object.__setattr__(self, "required_signals", signals)
        object.__setattr__(self, "required_capabilities", capabilities)
        object.__setattr__(self, "evidence_requirements", evidence)

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self._canonical_payload())).hexdigest()

    @property
    def specificity(self) -> int:
        return (
            (1 if self.compatible_shapes else 0)
            + len(self.required_signals)
            + len(self.required_capabilities)
            + len(self.evidence_requirements)
        )

    def _canonical_payload(self) -> dict[str, object]:
        return {
            "contract_version": SKILL_CONTRACT_VERSION,
            "skill_id": self.skill_id,
            "version": self.version,
            "procedure_steps": list(self.procedure_steps),
            "input_fields": [field.as_dict() for field in self.input_fields],
            "output_fields": [field.as_dict() for field in self.output_fields],
            "objective_kinds": list(self.objective_kinds),
            "compatible_shapes": [shape.value for shape in self.compatible_shapes],
            "required_signals": [signal.as_dict() for signal in self.required_signals],
            "required_capabilities": list(self.required_capabilities),
            "evidence_requirements": list(self.evidence_requirements),
            "priority": self.priority,
        }


@dataclass(frozen=True, slots=True)
class SkillApproval:
    skill_id: str
    version: str
    content_digest: str

    def __post_init__(self) -> None:
        if not isinstance(self.skill_id, str) or not _SKILL_ID_RE.fullmatch(self.skill_id):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        if not isinstance(self.version, str) or not _SEMVER_RE.fullmatch(self.version):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        object.__setattr__(self, "content_digest", _sha256_digest(self.content_digest))

    @property
    def key(self) -> tuple[str, str]:
        return self.skill_id, self.version

    def as_dict(self) -> dict[str, str]:
        return {
            "skill_id": self.skill_id,
            "version": self.version,
            "content_digest": self.content_digest,
        }


@dataclass(frozen=True, slots=True)
class SkillAdmissionPolicy:
    approvals: tuple[SkillApproval, ...]
    declarable_capabilities: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        approvals = tuple(sorted(self.approvals, key=lambda item: item.key))
        if not approvals:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        if len({item.key for item in approvals}) != len(approvals):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        capabilities = _bounded_token_set(self.declarable_capabilities, limit=_MAX_CAPABILITIES)
        object.__setattr__(self, "approvals", approvals)
        object.__setattr__(self, "declarable_capabilities", capabilities)

    @property
    def digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "approvals": [approval.as_dict() for approval in self.approvals],
                    "declarable_capabilities": list(self.declarable_capabilities),
                }
            )
        ).hexdigest()

    def approved_digest(self, skill_id: str, version: str) -> str | None:
        for approval in self.approvals:
            if approval.skill_id == skill_id and approval.version == version:
                return approval.content_digest
        return None


@dataclass(frozen=True, slots=True)
class RegisteredSkill:
    contract: PortableSkill
    content_digest: str
    admission_policy_digest: str

    def __post_init__(self) -> None:
        content_digest = _sha256_digest(self.content_digest)
        policy_digest = _sha256_digest(self.admission_policy_digest)
        if content_digest != self.contract.digest:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        object.__setattr__(self, "content_digest", content_digest)
        object.__setattr__(self, "admission_policy_digest", policy_digest)

    @property
    def key(self) -> tuple[str, str]:
        return self.contract.skill_id, self.contract.version

    def safe_metadata(self) -> dict[str, object]:
        return {
            "skill_id": self.contract.skill_id,
            "version": self.contract.version,
            "content_digest": self.content_digest,
            "admission_policy_digest": self.admission_policy_digest,
            "objective_kinds": list(self.contract.objective_kinds),
            "compatible_shapes": [shape.value for shape in self.contract.compatible_shapes],
            "required_signals": [item.as_dict() for item in self.contract.required_signals],
            "required_capabilities": list(self.contract.required_capabilities),
            "evidence_requirements": list(self.contract.evidence_requirements),
            "priority": self.contract.priority,
            "procedure_step_count": len(self.contract.procedure_steps),
            "input_fields": [field.as_dict() for field in self.contract.input_fields],
            "output_fields": [field.as_dict() for field in self.contract.output_fields],
            "grants_authority": False,
        }


class SkillRegistry:
    def __init__(self, policy: SkillAdmissionPolicy) -> None:
        self.policy = policy
        self._skills: dict[tuple[str, str], RegisteredSkill] = {}

    def admit(self, contract: PortableSkill) -> RegisteredSkill:
        if not isinstance(contract, PortableSkill):
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        digest = contract.digest
        approved = self.policy.approved_digest(contract.skill_id, contract.version)
        if approved is None or approved != digest:
            raise GovernedSkillError(SkillFailureCode.SKILL_NOT_APPROVED)
        if not set(contract.required_capabilities).issubset(self.policy.declarable_capabilities):
            raise GovernedSkillError(SkillFailureCode.CAPABILITY_NOT_DECLARABLE)

        key = contract.skill_id, contract.version
        existing = self._skills.get(key)
        if existing is not None:
            if existing.content_digest == digest:
                return existing
            raise GovernedSkillError(SkillFailureCode.SKILL_VERSION_CONFLICT)

        registered = RegisteredSkill(
            contract=contract,
            content_digest=digest,
            admission_policy_digest=self.policy.digest,
        )
        self._skills[key] = registered
        return registered

    def registered(self) -> tuple[RegisteredSkill, ...]:
        return tuple(self._skills[key] for key in sorted(self._skills))


@dataclass(frozen=True, slots=True)
class CapabilitySnapshot:
    capability_ids: tuple[str, ...]
    policy_digest: str

    def __post_init__(self) -> None:
        capabilities = _bounded_token_set(self.capability_ids, limit=_MAX_CAPABILITIES)
        object.__setattr__(self, "capability_ids", capabilities)
        object.__setattr__(self, "policy_digest", _sha256_digest(self.policy_digest))

    def safe_metadata(self) -> dict[str, object]:
        return {
            "capability_ids": list(self.capability_ids),
            "policy_digest": self.policy_digest,
            "contains_handles": False,
        }


@dataclass(frozen=True, slots=True)
class SkillSelection:
    status: SkillSelectionStatus
    reason: SkillFailureCode | None
    skill_id: str | None
    version: str | None
    content_digest: str | None
    required_capabilities: tuple[str, ...]

    @property
    def selected(self) -> bool:
        return self.status is SkillSelectionStatus.SELECTED

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "reason": self.reason.value if self.reason is not None else None,
            "skill_id": self.skill_id,
            "version": self.version,
            "content_digest": self.content_digest,
            "required_capabilities": list(self.required_capabilities),
            "grants_authority": False,
        }


class SkillSelector:
    def __init__(self, registry: SkillRegistry) -> None:
        self.registry = registry

    def select(
        self,
        *,
        objective_kind: str,
        compatibility: RepositoryCompatibilityProfile,
        capabilities: CapabilitySnapshot,
    ) -> SkillSelection:
        objective = _safe_token(objective_kind)
        if compatibility.compatibility_state is not CompatibilityState.SUPPORTED:
            return _human_required(SkillFailureCode.INCOMPATIBLE_REPOSITORY)

        compatible: list[RegisteredSkill] = []
        available: list[RegisteredSkill] = []
        signal_pairs = {(signal.kind, signal.value) for signal in compatibility.signals}
        capability_ids = set(capabilities.capability_ids)

        for registered in self.registry.registered():
            contract = registered.contract
            if objective not in contract.objective_kinds:
                continue
            if contract.compatible_shapes and compatibility.repository_shape not in contract.compatible_shapes:
                continue
            required_signals = {(item.kind, item.value) for item in contract.required_signals}
            if not required_signals.issubset(signal_pairs):
                continue
            compatible.append(registered)
            if set(contract.required_capabilities).issubset(capability_ids):
                available.append(registered)

        if not compatible:
            return _human_required(SkillFailureCode.NO_MATCHING_SKILL)
        if not available:
            required = tuple(sorted({item for skill in compatible for item in skill.contract.required_capabilities}))
            return _human_required(SkillFailureCode.MISSING_CAPABILITY, required_capabilities=required)

        top_score = max(_selection_score(skill) for skill in available)
        top = tuple(skill for skill in available if _selection_score(skill) == top_score)
        if len(top) != 1:
            return _human_required(SkillFailureCode.AMBIGUOUS_SKILL_SELECTION)

        selected = top[0]
        return SkillSelection(
            status=SkillSelectionStatus.SELECTED,
            reason=None,
            skill_id=selected.contract.skill_id,
            version=selected.contract.version,
            content_digest=selected.content_digest,
            required_capabilities=selected.contract.required_capabilities,
        )


@dataclass(frozen=True, slots=True)
class SkillEvidenceItem:
    kind: str
    status: SkillEvidenceStatus
    content_digest: str
    reference: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _safe_token(self.kind))
        if not isinstance(self.status, SkillEvidenceStatus):
            try:
                object.__setattr__(self, "status", SkillEvidenceStatus(self.status))
            except (TypeError, ValueError) as exc:
                raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT) from exc
        object.__setattr__(self, "content_digest", _sha256_digest(self.content_digest))
        if self.reference is not None:
            if (
                not isinstance(self.reference, str)
                or len(self.reference.encode("utf-8")) > _MAX_REFERENCE_BYTES
                or not _REFERENCE_RE.fullmatch(self.reference)
            ):
                raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)

    def as_dict(self) -> dict[str, str | None]:
        return {
            "kind": self.kind,
            "status": self.status.value,
            "content_digest": self.content_digest,
            "reference": self.reference,
        }


@dataclass(frozen=True, slots=True)
class SkillInvocationRecord:
    invocation_id: str
    project_id: str
    run_id: str
    skill_id: str
    skill_version: str
    skill_digest: str
    compatibility_profile_digest: str
    source_revision: str
    capability_policy_digest: str
    required_capabilities: tuple[str, ...]
    input_digest: str
    status: SkillInvocationStatus
    evidence: tuple[SkillEvidenceItem, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "invocation_id": self.invocation_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "skill_digest": self.skill_digest,
            "compatibility_profile_digest": self.compatibility_profile_digest,
            "source_revision": self.source_revision,
            "capability_policy_digest": self.capability_policy_digest,
            "required_capabilities": list(self.required_capabilities),
            "input_digest": self.input_digest,
            "status": self.status.value,
            "evidence": [item.as_dict() for item in self.evidence],
            "contains_raw_input_or_output": False,
            "contains_authority_handles": False,
        }


def record_skill_invocation(
    *,
    project_id: str,
    run_id: str,
    registered_skill: RegisteredSkill,
    compatibility: RepositoryCompatibilityProfile,
    capabilities: CapabilitySnapshot,
    input_digest: str,
    status: SkillInvocationStatus,
    evidence: Iterable[SkillEvidenceItem],
) -> SkillInvocationRecord:
    project = _canonical_uuid(project_id)
    run = _canonical_uuid(run_id)
    if compatibility.project_id != project:
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    if compatibility.compatibility_state is not CompatibilityState.SUPPORTED:
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    if not _skill_matches_profile(registered_skill.contract, compatibility):
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    if not set(registered_skill.contract.required_capabilities).issubset(capabilities.capability_ids):
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)

    input_hash = _sha256_digest(input_digest)
    try:
        invocation_status = status if isinstance(status, SkillInvocationStatus) else SkillInvocationStatus(status)
    except (TypeError, ValueError) as exc:
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH) from exc

    evidence_items = tuple(evidence)
    if len(evidence_items) > _MAX_EVIDENCE_ITEMS:
        raise GovernedSkillError(SkillFailureCode.EVIDENCE_LIMIT_EXCEEDED)
    if any(not isinstance(item, SkillEvidenceItem) for item in evidence_items):
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    evidence_items = tuple(
        sorted(
            evidence_items,
            key=lambda item: (item.kind, item.status.value, item.content_digest, item.reference or ""),
        )
    )

    core: dict[str, object] = {
        "project_id": project,
        "run_id": run,
        "skill_id": registered_skill.contract.skill_id,
        "skill_version": registered_skill.contract.version,
        "skill_digest": registered_skill.content_digest,
        "compatibility_profile_digest": _sha256_digest(compatibility.profile_digest),
        "source_revision": compatibility.source_revision,
        "capability_policy_digest": capabilities.policy_digest,
        "required_capabilities": list(registered_skill.contract.required_capabilities),
        "input_digest": input_hash,
        "status": invocation_status.value,
        "evidence": [item.as_dict() for item in evidence_items],
    }
    invocation_id = f"skillinv:{sha256(_canonical_json(core)).hexdigest()}"
    return SkillInvocationRecord(
        invocation_id=invocation_id,
        project_id=project,
        run_id=run,
        skill_id=registered_skill.contract.skill_id,
        skill_version=registered_skill.contract.version,
        skill_digest=registered_skill.content_digest,
        compatibility_profile_digest=compatibility.profile_digest,
        source_revision=compatibility.source_revision,
        capability_policy_digest=capabilities.policy_digest,
        required_capabilities=registered_skill.contract.required_capabilities,
        input_digest=input_hash,
        status=invocation_status,
        evidence=evidence_items,
    )


def _skill_matches_profile(contract: PortableSkill, profile: RepositoryCompatibilityProfile) -> bool:
    if contract.compatible_shapes and profile.repository_shape not in contract.compatible_shapes:
        return False
    profile_signals = {(signal.kind, signal.value) for signal in profile.signals}
    return {(item.kind, item.value) for item in contract.required_signals}.issubset(profile_signals)


def _selection_score(skill: RegisteredSkill) -> tuple[int, int]:
    return skill.contract.priority, skill.contract.specificity


def _human_required(
    reason: SkillFailureCode,
    *,
    required_capabilities: tuple[str, ...] = (),
) -> SkillSelection:
    return SkillSelection(
        status=SkillSelectionStatus.HUMAN_REQUIRED,
        reason=reason,
        skill_id=None,
        version=None,
        content_digest=None,
        required_capabilities=required_capabilities,
    )


def _bounded_steps(values: Iterable[str]) -> tuple[str, ...]:
    steps = tuple(values)
    if not steps or len(steps) > _MAX_STEP_COUNT:
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    normalized: list[str] = []
    for value in steps:
        if not isinstance(value, str) or value != value.strip() or not value or "\x00" in value:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        if len(value.encode("utf-8")) > _MAX_STEP_BYTES:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        normalized.append(value)
    return tuple(normalized)


def _bounded_fields(values: Iterable[SkillField]) -> tuple[SkillField, ...]:
    fields = tuple(values)
    if len(fields) > _MAX_FIELDS or any(not isinstance(field, SkillField) for field in fields):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    if len({field.field_id for field in fields}) != len(fields):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    return fields


def _bounded_token_set(
    values: Iterable[str],
    *,
    limit: int,
    require_nonempty: bool = False,
) -> tuple[str, ...]:
    items = tuple(values)
    if len(items) > limit or (require_nonempty and not items):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    normalized = tuple(_safe_token(item) for item in items)
    if len(set(normalized)) != len(normalized):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    return tuple(sorted(normalized))


def _bounded_shapes(values: Iterable[RepositoryShape]) -> tuple[RepositoryShape, ...]:
    items = tuple(values)
    normalized: list[RepositoryShape] = []
    for item in items:
        try:
            shape = item if isinstance(item, RepositoryShape) else RepositoryShape(item)
        except (TypeError, ValueError) as exc:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT) from exc
        if shape in {RepositoryShape.UNSUPPORTED, RepositoryShape.AMBIGUOUS}:
            raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
        normalized.append(shape)
    if len(set(normalized)) != len(normalized):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    return tuple(sorted(normalized, key=lambda item: item.value))


def _bounded_signals(values: Iterable[SkillSignalRequirement]) -> tuple[SkillSignalRequirement, ...]:
    items = tuple(values)
    if len(items) > _MAX_SIGNAL_REQUIREMENTS or any(not isinstance(item, SkillSignalRequirement) for item in items):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    pairs = {(item.kind, item.value) for item in items}
    if len(pairs) != len(items):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    return tuple(sorted(items, key=lambda item: (item.kind, item.value)))


def _safe_token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise GovernedSkillError(SkillFailureCode.INVALID_SKILL_CONTRACT)
    return value


def _sha256_digest(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    return value


def _canonical_uuid(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH) from exc
    canonical = str(parsed)
    if canonical != value:
        raise GovernedSkillError(SkillFailureCode.INVOCATION_IDENTITY_MISMATCH)
    return canonical


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


__all__ = [
    "CapabilitySnapshot",
    "GovernedSkillError",
    "PortableSkill",
    "RegisteredSkill",
    "SKILL_CONTRACT_VERSION",
    "SkillAdmissionPolicy",
    "SkillApproval",
    "SkillEvidenceItem",
    "SkillEvidenceStatus",
    "SkillFailureCode",
    "SkillField",
    "SkillInvocationRecord",
    "SkillInvocationStatus",
    "SkillRegistry",
    "SkillSelection",
    "SkillSelectionStatus",
    "SkillSelector",
    "SkillSignalRequirement",
    "SkillValueType",
    "record_skill_invocation",
]
