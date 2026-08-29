from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Iterable, Protocol

from .governed_skills import (
    CapabilitySnapshot,
    PortableSkill,
    RegisteredSkill,
    SkillRegistry,
    SkillSelection,
    SkillSelector,
)
from .repository_intelligence import RepositoryCompatibilityProfile


INTAKE_CONTRACT_VERSION = 1
_MAX_SOURCE_REF_BYTES = 224
_MAX_NAME_BYTES = 128
_MAX_UPSTREAM_REF_BYTES = 128
_MAX_LICENSE_BYTES = 64
_MAX_INSPECTION_BYTES = 64_000
_MAX_INVENTORY_ITEMS = 64
_MAX_INVENTORY_ITEM_BYTES = 256
_MAX_HINTS = 32
_MAX_APPROVER_REF_BYTES = 128
_MAX_APPROVAL_REASON_BYTES = 96
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SOURCE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,223}$")
_HINT_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_APPROVER_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,127}$")
_CANDIDATE_ID_RE = re.compile(r"^skillcand:[0-9a-f]{64}$")
_APPROVAL_ID_RE = re.compile(r"^skillapproval:[0-9a-f]{64}$")


class CandidateKind(StrEnum):
    SKILL = "skill"
    TOOL = "tool"


class SourceTier(StrEnum):
    OFFICIAL_ECOSYSTEM = "official_ecosystem"
    VENDOR_NATIVE = "vendor_native"
    CURATED_DISCOVERY = "curated_discovery"
    UNKNOWN = "unknown"


class SourceVisibility(StrEnum):
    PUBLIC = "public"
    PROJECT_PRIVATE = "project_private"


class ProvenanceState(StrEnum):
    VERIFIED = "VERIFIED"
    RESOLVED_FROM_CURATED = "RESOLVED_FROM_CURATED"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class LicenseState(StrEnum):
    ALLOWED = "ALLOWED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PROHIBITED = "PROHIBITED"
    UNKNOWN = "UNKNOWN"


class IntakeDisposition(StrEnum):
    QUARANTINED = "QUARANTINED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    APPROVED_FOR_ADMISSION = "APPROVED_FOR_ADMISSION"
    ADMITTED = "ADMITTED"
    SUPERSEDED = "SUPERSEDED"


class CandidateReason(StrEnum):
    MISSING_AUTHORITATIVE_SOURCE = "MISSING_AUTHORITATIVE_SOURCE"
    AMBIGUOUS_AUTHORITATIVE_SOURCE = "AMBIGUOUS_AUTHORITATIVE_SOURCE"
    MISSING_UPSTREAM_REF = "MISSING_UPSTREAM_REF"
    MISSING_CONTENT_DIGEST = "MISSING_CONTENT_DIGEST"
    LICENSE_UNKNOWN = "LICENSE_UNKNOWN"
    LICENSE_REVIEW_REQUIRED = "LICENSE_REVIEW_REQUIRED"
    LICENSE_PROHIBITED = "LICENSE_PROHIBITED"
    GENERIC_EXECUTION = "GENERIC_EXECUTION"
    ARBITRARY_NETWORK = "ARBITRARY_NETWORK"
    CREDENTIAL_HANDLING = "CREDENTIAL_HANDLING"
    POLICY_BYPASS = "POLICY_BYPASS"
    UNAUTHORIZED_PRODUCTION = "UNAUTHORIZED_PRODUCTION"
    HIDDEN_INSTALL_EXECUTION = "HIDDEN_INSTALL_EXECUTION"
    DESTRUCTIVE_WITHOUT_APPROVAL = "DESTRUCTIVE_WITHOUT_APPROVAL"
    UPSTREAM_CONTENT_CONFLICT = "UPSTREAM_CONTENT_CONFLICT"


class IntakeFailureCode(StrEnum):
    INVALID_OBSERVATION = "INVALID_OBSERVATION"
    PRIVATE_SCOPE_VIOLATION = "PRIVATE_SCOPE_VIOLATION"
    CANDIDATE_NOT_FOUND = "CANDIDATE_NOT_FOUND"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    APPROVAL_MISMATCH = "APPROVAL_MISMATCH"
    TOOL_ADMISSION_FORBIDDEN = "TOOL_ADMISSION_FORBIDDEN"
    CANDIDATE_NOT_ADMISSIBLE = "CANDIDATE_NOT_ADMISSIBLE"


class SkillIntakeError(ValueError):
    def __init__(self, code: IntakeFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class CandidateSourceObservation:
    kind: CandidateKind
    source_tier: SourceTier
    source_ref: str
    upstream_name: str
    upstream_ref: str | None
    content_digest: str | None
    license_id: str | None = None
    authoritative_source_refs: tuple[str, ...] = ()
    objective_hints: tuple[str, ...] = ()
    capability_hints: tuple[str, ...] = ()
    compatibility_hints: tuple[str, ...] = ()
    declared_scripts: tuple[str, ...] = ()
    declared_dependencies: tuple[str, ...] = ()
    declared_references: tuple[str, ...] = ()
    inspection_text: str = field(default="", repr=False)
    visibility: SourceVisibility = SourceVisibility.PUBLIC
    project_ref: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", _enum_value(CandidateKind, self.kind))
        object.__setattr__(self, "source_tier", _enum_value(SourceTier, self.source_tier))
        object.__setattr__(self, "visibility", _enum_value(SourceVisibility, self.visibility))
        object.__setattr__(self, "source_ref", _source_ref(self.source_ref))
        object.__setattr__(self, "upstream_name", _plain_text(self.upstream_name, _MAX_NAME_BYTES))
        object.__setattr__(
            self,
            "upstream_ref",
            None if self.upstream_ref is None else _plain_text(self.upstream_ref, _MAX_UPSTREAM_REF_BYTES),
        )
        if self.content_digest is not None:
            object.__setattr__(self, "content_digest", _digest(self.content_digest))
        if self.license_id is not None:
            object.__setattr__(self, "license_id", _plain_text(self.license_id, _MAX_LICENSE_BYTES))

        authoritative = tuple(sorted({_source_ref(value) for value in self.authoritative_source_refs}))
        if len(authoritative) > 4:
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        object.__setattr__(self, "authoritative_source_refs", authoritative)
        object.__setattr__(self, "objective_hints", _hint_set(self.objective_hints))
        object.__setattr__(self, "capability_hints", _hint_set(self.capability_hints))
        object.__setattr__(self, "compatibility_hints", _hint_set(self.compatibility_hints))
        object.__setattr__(self, "declared_scripts", _inventory(self.declared_scripts))
        object.__setattr__(self, "declared_dependencies", _inventory(self.declared_dependencies))
        object.__setattr__(self, "declared_references", _inventory(self.declared_references))
        object.__setattr__(self, "inspection_text", _inspection_text(self.inspection_text))

        if self.visibility is SourceVisibility.PROJECT_PRIVATE:
            if self.project_ref is None:
                raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
            object.__setattr__(self, "project_ref", _approver_ref(self.project_ref))
        elif self.project_ref is not None:
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)

    @property
    def canonical_source_ref(self) -> str:
        if self.source_tier in {SourceTier.OFFICIAL_ECOSYSTEM, SourceTier.VENDOR_NATIVE}:
            return self.source_ref
        if self.source_tier is SourceTier.CURATED_DISCOVERY and len(self.authoritative_source_refs) == 1:
            return self.authoritative_source_refs[0]
        return self.source_ref

    @property
    def logical_key(self) -> tuple[str, str, str, str]:
        return (
            self.kind.value,
            self.canonical_source_ref,
            self.upstream_name.casefold(),
            self.upstream_ref or "<unknown>",
        )

    @property
    def scope_digest(self) -> str:
        scope = "public" if self.visibility is SourceVisibility.PUBLIC else f"project:{self.project_ref}"
        return sha256(scope.encode("utf-8")).hexdigest()

    @property
    def inventory_digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "scripts": list(self.declared_scripts),
                    "dependencies": list(self.declared_dependencies),
                    "references": list(self.declared_references),
                }
            )
        ).hexdigest()

    @property
    def inspection_digest(self) -> str:
        return sha256(self.inspection_text.encode("utf-8")).hexdigest()

    @property
    def observation_digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "contract_version": INTAKE_CONTRACT_VERSION,
                    "kind": self.kind.value,
                    "source_tier": self.source_tier.value,
                    "source_ref": self.source_ref,
                    "canonical_source_ref": self.canonical_source_ref,
                    "upstream_name": self.upstream_name,
                    "upstream_ref": self.upstream_ref,
                    "content_digest": self.content_digest,
                    "license_id": self.license_id,
                    "authoritative_source_refs": list(self.authoritative_source_refs),
                    "objective_hints": list(self.objective_hints),
                    "capability_hints": list(self.capability_hints),
                    "compatibility_hints": list(self.compatibility_hints),
                    "inventory_digest": self.inventory_digest,
                    "inspection_digest": self.inspection_digest,
                    "visibility": self.visibility.value,
                    "scope_digest": self.scope_digest,
                }
            )
        ).hexdigest()


@dataclass(frozen=True, slots=True)
class SkillIntakePolicy:
    version: str = "1.0.0"
    allowed_licenses: tuple[str, ...] = (
        "Apache-2.0",
        "BSD-2-Clause",
        "BSD-3-Clause",
        "ISC",
        "MIT",
    )
    review_licenses: tuple[str, ...] = (
        "AGPL-3.0-only",
        "GPL-2.0-only",
        "GPL-3.0-only",
        "LGPL-2.1-only",
        "LGPL-3.0-only",
        "MPL-2.0",
    )
    prohibited_licenses: tuple[str, ...] = ("UNLICENSED",)

    def __post_init__(self) -> None:
        object.__setattr__(self, "version", _plain_text(self.version, 32))
        allowed = _license_set(self.allowed_licenses)
        review = _license_set(self.review_licenses)
        prohibited = _license_set(self.prohibited_licenses)
        if (set(allowed) & set(review)) or (set(allowed) & set(prohibited)) or (set(review) & set(prohibited)):
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        object.__setattr__(self, "allowed_licenses", allowed)
        object.__setattr__(self, "review_licenses", review)
        object.__setattr__(self, "prohibited_licenses", prohibited)

    @property
    def digest(self) -> str:
        return sha256(
            _canonical_json(
                {
                    "contract_version": INTAKE_CONTRACT_VERSION,
                    "version": self.version,
                    "allowed_licenses": list(self.allowed_licenses),
                    "review_licenses": list(self.review_licenses),
                    "prohibited_licenses": list(self.prohibited_licenses),
                    "static_rule_version": 1,
                }
            )
        ).hexdigest()

    def license_state(self, license_id: str | None) -> LicenseState:
        if license_id is None:
            return LicenseState.UNKNOWN
        folded = license_id.casefold()
        if folded in {value.casefold() for value in self.allowed_licenses}:
            return LicenseState.ALLOWED
        if folded in {value.casefold() for value in self.review_licenses}:
            return LicenseState.REVIEW_REQUIRED
        if folded in {value.casefold() for value in self.prohibited_licenses}:
            return LicenseState.PROHIBITED
        return LicenseState.UNKNOWN


@dataclass(frozen=True, slots=True)
class SkillCandidate:
    kind: CandidateKind
    source_tier: SourceTier
    discovery_source_ref: str
    canonical_source_ref: str
    upstream_name: str
    upstream_ref: str | None
    source_content_digest: str | None
    observation_digest: str
    inventory_digest: str
    inspection_digest: str
    license_id: str | None
    license_state: LicenseState
    provenance_state: ProvenanceState
    objective_hints: tuple[str, ...]
    capability_hints: tuple[str, ...]
    compatibility_hints: tuple[str, ...]
    script_count: int
    dependency_count: int
    reference_count: int
    visibility: SourceVisibility
    scope_digest: str
    policy_digest: str
    reasons: tuple[CandidateReason, ...]
    initial_disposition: IntakeDisposition
    safe_summary: str

    @property
    def candidate_id(self) -> str:
        identity = {
            "contract_version": INTAKE_CONTRACT_VERSION,
            "kind": self.kind.value,
            "canonical_source_ref": self.canonical_source_ref,
            "upstream_name": self.upstream_name.casefold(),
            "upstream_ref": self.upstream_ref,
            "source_content_digest": self.source_content_digest,
            "visibility": self.visibility.value,
            "scope_digest": self.scope_digest,
        }
        return f"skillcand:{sha256(_canonical_json(identity)).hexdigest()}"

    @property
    def logical_key(self) -> tuple[str, str, str, str]:
        return (
            self.kind.value,
            self.canonical_source_ref,
            self.upstream_name.casefold(),
            self.upstream_ref or "<unknown>",
        )

    def safe_metadata(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "kind": self.kind.value,
            "source_tier": self.source_tier.value,
            "discovery_source_ref": self.discovery_source_ref,
            "canonical_source_ref": self.canonical_source_ref,
            "upstream_name": self.upstream_name,
            "upstream_ref": self.upstream_ref,
            "source_content_digest": self.source_content_digest,
            "observation_digest": self.observation_digest,
            "inventory_digest": self.inventory_digest,
            "inspection_digest": self.inspection_digest,
            "license_id": self.license_id,
            "license_state": self.license_state.value,
            "provenance_state": self.provenance_state.value,
            "objective_hints": list(self.objective_hints),
            "capability_hints": list(self.capability_hints),
            "compatibility_hints": list(self.compatibility_hints),
            "inventory": {
                "script_count": self.script_count,
                "dependency_count": self.dependency_count,
                "reference_count": self.reference_count,
            },
            "visibility": self.visibility.value,
            "scope_digest": self.scope_digest,
            "policy_digest": self.policy_digest,
            "reasons": [reason.value for reason in self.reasons],
            "initial_disposition": self.initial_disposition.value,
            "summary": self.safe_summary,
            "contains_raw_candidate_body": False,
            "contains_authority_handles": False,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class SkillCandidateApproval:
    candidate_id: str
    source_content_digest: str
    policy_digest: str
    portable_skill_digest: str
    approved_by: str
    approval_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_id, str) or not _CANDIDATE_ID_RE.fullmatch(self.candidate_id):
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        object.__setattr__(self, "source_content_digest", _digest(self.source_content_digest))
        object.__setattr__(self, "policy_digest", _digest(self.policy_digest))
        object.__setattr__(self, "portable_skill_digest", _digest(self.portable_skill_digest))
        object.__setattr__(self, "approved_by", _approver_ref(self.approved_by))
        if self.approval_reason is not None:
            object.__setattr__(
                self,
                "approval_reason",
                _plain_text(self.approval_reason, _MAX_APPROVAL_REASON_BYTES),
            )

    @property
    def approval_id(self) -> str:
        return f"skillapproval:{sha256(_canonical_json(self._payload())).hexdigest()}"

    def _payload(self) -> dict[str, object]:
        return {
            "contract_version": INTAKE_CONTRACT_VERSION,
            "candidate_id": self.candidate_id,
            "source_content_digest": self.source_content_digest,
            "policy_digest": self.policy_digest,
            "portable_skill_digest": self.portable_skill_digest,
            "approved_by": self.approved_by,
            "approval_reason": self.approval_reason,
        }

    def safe_metadata(self) -> dict[str, object]:
        return {
            "approval_id": self.approval_id,
            **self._payload(),
            "grants_tool_authority": False,
        }


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    candidate: SkillCandidate
    disposition: IntakeDisposition
    transition_index: int = 0
    approval_id: str | None = None
    admitted_skill_id: str | None = None
    admitted_skill_version: str | None = None
    admitted_skill_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "disposition", _enum_value(IntakeDisposition, self.disposition))
        if not isinstance(self.transition_index, int) or isinstance(self.transition_index, bool) or self.transition_index < 0:
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        if self.approval_id is not None and not _APPROVAL_ID_RE.fullmatch(self.approval_id):
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        if self.admitted_skill_digest is not None:
            object.__setattr__(self, "admitted_skill_digest", _digest(self.admitted_skill_digest))

    def safe_metadata(self) -> dict[str, object]:
        value = self.candidate.safe_metadata()
        value.update(
            {
                "disposition": self.disposition.value,
                "transition_index": self.transition_index,
                "approval_id": self.approval_id,
                "admitted_skill_id": self.admitted_skill_id,
                "admitted_skill_version": self.admitted_skill_version,
                "admitted_skill_digest": self.admitted_skill_digest,
            }
        )
        return value


class CandidateSourceAdapter(Protocol):
    def observations(self) -> Iterable[CandidateSourceObservation]: ...


class SkillCatalog:
    """In-memory W9-S2 catalog. Candidate bodies never enter the catalog."""

    def __init__(self, *, project_ref: str | None = None) -> None:
        self.project_ref = None if project_ref is None else _approver_ref(project_ref)
        self._entries: dict[str, CatalogEntry] = {}
        self._history: dict[str, list[CatalogEntry]] = {}
        self._logical_index: dict[tuple[str, str, str, str], set[str]] = {}

    @property
    def is_global(self) -> bool:
        return self.project_ref is None

    def record(self, candidate: SkillCandidate) -> CatalogEntry:
        if not isinstance(candidate, SkillCandidate):
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        if candidate.visibility is SourceVisibility.PROJECT_PRIVATE:
            expected_scope = sha256(f"project:{self.project_ref}".encode("utf-8")).hexdigest() if self.project_ref else None
            if expected_scope is None or candidate.scope_digest != expected_scope:
                raise SkillIntakeError(IntakeFailureCode.PRIVATE_SCOPE_VIOLATION)

        existing = self._entries.get(candidate.candidate_id)
        if existing is not None and existing.candidate == candidate:
            return existing

        conflicts = tuple(
            self._entries[candidate_id]
            for candidate_id in sorted(self._logical_index.get(candidate.logical_key, set()))
            if candidate_id != candidate.candidate_id
        )
        if conflicts and any(
            entry.candidate.source_content_digest != candidate.source_content_digest
            for entry in conflicts
        ):
            reasons = _reason_set((*candidate.reasons, CandidateReason.UPSTREAM_CONTENT_CONFLICT))
            disposition = (
                IntakeDisposition.BLOCKED
                if candidate.initial_disposition is IntakeDisposition.BLOCKED
                else IntakeDisposition.HUMAN_REQUIRED
            )
            candidate = replace(
                candidate,
                reasons=reasons,
                initial_disposition=disposition,
                safe_summary=_summary(disposition),
            )

        entry = CatalogEntry(candidate=candidate, disposition=candidate.initial_disposition)
        self._entries[candidate.candidate_id] = entry
        self._history.setdefault(candidate.candidate_id, []).append(entry)
        self._logical_index.setdefault(candidate.logical_key, set()).add(candidate.candidate_id)
        return entry

    def entry(self, candidate_id: str) -> CatalogEntry:
        entry = self._entries.get(candidate_id)
        if entry is None:
            raise SkillIntakeError(IntakeFailureCode.CANDIDATE_NOT_FOUND)
        return entry

    def entries(self) -> tuple[CatalogEntry, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def history(self, candidate_id: str) -> tuple[CatalogEntry, ...]:
        if candidate_id not in self._history:
            raise SkillIntakeError(IntakeFailureCode.CANDIDATE_NOT_FOUND)
        return tuple(self._history[candidate_id])

    def approve_skill(self, candidate_id: str, approval: SkillCandidateApproval) -> CatalogEntry:
        entry = self.entry(candidate_id)
        candidate = entry.candidate
        if candidate.kind is not CandidateKind.SKILL:
            raise SkillIntakeError(IntakeFailureCode.TOOL_ADMISSION_FORBIDDEN)
        if entry.disposition is not IntakeDisposition.QUARANTINED:
            raise SkillIntakeError(IntakeFailureCode.CANDIDATE_NOT_ADMISSIBLE)
        _validate_approval_candidate(candidate, approval)
        updated = replace(
            entry,
            disposition=IntakeDisposition.APPROVED_FOR_ADMISSION,
            transition_index=entry.transition_index + 1,
            approval_id=approval.approval_id,
        )
        return self._transition(updated)

    def reject(self, candidate_id: str) -> CatalogEntry:
        entry = self.entry(candidate_id)
        if entry.disposition is IntakeDisposition.ADMITTED:
            raise SkillIntakeError(IntakeFailureCode.INVALID_TRANSITION)
        if entry.disposition is IntakeDisposition.REJECTED:
            return entry
        updated = replace(
            entry,
            disposition=IntakeDisposition.REJECTED,
            transition_index=entry.transition_index + 1,
        )
        return self._transition(updated)

    def _mark_admitted(self, candidate_id: str, registered: RegisteredSkill) -> CatalogEntry:
        entry = self.entry(candidate_id)
        if entry.disposition is not IntakeDisposition.APPROVED_FOR_ADMISSION:
            raise SkillIntakeError(IntakeFailureCode.INVALID_TRANSITION)
        updated = replace(
            entry,
            disposition=IntakeDisposition.ADMITTED,
            transition_index=entry.transition_index + 1,
            admitted_skill_id=registered.contract.skill_id,
            admitted_skill_version=registered.contract.version,
            admitted_skill_digest=registered.content_digest,
        )
        return self._transition(updated)

    def _transition(self, entry: CatalogEntry) -> CatalogEntry:
        candidate_id = entry.candidate.candidate_id
        self._entries[candidate_id] = entry
        self._history.setdefault(candidate_id, []).append(entry)
        return entry

    def admitted_registered(self, registry: SkillRegistry) -> tuple[RegisteredSkill, ...]:
        admitted = {
            (
                entry.admitted_skill_id,
                entry.admitted_skill_version,
                entry.admitted_skill_digest,
            )
            for entry in self._entries.values()
            if entry.disposition is IntakeDisposition.ADMITTED
        }
        return tuple(
            skill
            for skill in registry.registered()
            if (skill.contract.skill_id, skill.contract.version, skill.content_digest) in admitted
        )

    def select_runtime_skill(
        self,
        *,
        registry: SkillRegistry,
        objective_kind: str,
        compatibility: RepositoryCompatibilityProfile,
        capabilities: CapabilitySnapshot,
    ) -> SkillSelection:
        view = _RegisteredSkillView(self.admitted_registered(registry))
        return SkillSelector(view).select(
            objective_kind=objective_kind,
            compatibility=compatibility,
            capabilities=capabilities,
        )


class _RegisteredSkillView:
    def __init__(self, skills: tuple[RegisteredSkill, ...]) -> None:
        self._skills = skills

    def registered(self) -> tuple[RegisteredSkill, ...]:
        return self._skills


def ingest_source(
    adapter: CandidateSourceAdapter,
    *,
    policy: SkillIntakePolicy,
    catalog: SkillCatalog,
) -> tuple[CatalogEntry, ...]:
    entries: list[CatalogEntry] = []
    for observation in adapter.observations():
        if not isinstance(observation, CandidateSourceObservation):
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        entries.append(catalog.record(classify_candidate(observation, policy=policy)))
    return tuple(entries)


def classify_candidate(
    observation: CandidateSourceObservation,
    *,
    policy: SkillIntakePolicy,
) -> SkillCandidate:
    if not isinstance(observation, CandidateSourceObservation) or not isinstance(policy, SkillIntakePolicy):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)

    provenance = _provenance_state(observation)
    license_state = policy.license_state(observation.license_id)
    reasons: list[CandidateReason] = []

    if provenance is ProvenanceState.UNKNOWN:
        reasons.append(CandidateReason.MISSING_AUTHORITATIVE_SOURCE)
    elif provenance is ProvenanceState.AMBIGUOUS:
        reasons.append(CandidateReason.AMBIGUOUS_AUTHORITATIVE_SOURCE)
    if observation.upstream_ref is None:
        reasons.append(CandidateReason.MISSING_UPSTREAM_REF)
    if observation.content_digest is None:
        reasons.append(CandidateReason.MISSING_CONTENT_DIGEST)

    if license_state is LicenseState.UNKNOWN:
        reasons.append(CandidateReason.LICENSE_UNKNOWN)
    elif license_state is LicenseState.REVIEW_REQUIRED:
        reasons.append(CandidateReason.LICENSE_REVIEW_REQUIRED)
    elif license_state is LicenseState.PROHIBITED:
        reasons.append(CandidateReason.LICENSE_PROHIBITED)

    reasons.extend(_static_findings(observation))
    normalized_reasons = _reason_set(reasons)
    blocked = {
        CandidateReason.LICENSE_PROHIBITED,
        CandidateReason.GENERIC_EXECUTION,
        CandidateReason.ARBITRARY_NETWORK,
        CandidateReason.POLICY_BYPASS,
        CandidateReason.UNAUTHORIZED_PRODUCTION,
        CandidateReason.HIDDEN_INSTALL_EXECUTION,
    }
    if any(reason in blocked for reason in normalized_reasons):
        disposition = IntakeDisposition.BLOCKED
    elif normalized_reasons:
        disposition = IntakeDisposition.HUMAN_REQUIRED
    else:
        disposition = IntakeDisposition.QUARANTINED

    return SkillCandidate(
        kind=observation.kind,
        source_tier=observation.source_tier,
        discovery_source_ref=observation.source_ref,
        canonical_source_ref=observation.canonical_source_ref,
        upstream_name=observation.upstream_name,
        upstream_ref=observation.upstream_ref,
        source_content_digest=observation.content_digest,
        observation_digest=observation.observation_digest,
        inventory_digest=observation.inventory_digest,
        inspection_digest=observation.inspection_digest,
        license_id=observation.license_id,
        license_state=license_state,
        provenance_state=provenance,
        objective_hints=observation.objective_hints,
        capability_hints=observation.capability_hints,
        compatibility_hints=observation.compatibility_hints,
        script_count=len(observation.declared_scripts),
        dependency_count=len(observation.declared_dependencies),
        reference_count=len(observation.declared_references),
        visibility=observation.visibility,
        scope_digest=observation.scope_digest,
        policy_digest=policy.digest,
        reasons=normalized_reasons,
        initial_disposition=disposition,
        safe_summary=_summary(disposition),
    )


def build_skill_candidate_approval(
    candidate: SkillCandidate,
    contract: PortableSkill,
    *,
    approved_by: str,
    approval_reason: str | None = None,
) -> SkillCandidateApproval:
    if candidate.kind is not CandidateKind.SKILL:
        raise SkillIntakeError(IntakeFailureCode.TOOL_ADMISSION_FORBIDDEN)
    if candidate.initial_disposition is not IntakeDisposition.QUARANTINED:
        raise SkillIntakeError(IntakeFailureCode.CANDIDATE_NOT_ADMISSIBLE)
    if candidate.source_content_digest is None:
        raise SkillIntakeError(IntakeFailureCode.CANDIDATE_NOT_ADMISSIBLE)
    if not isinstance(contract, PortableSkill):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return SkillCandidateApproval(
        candidate_id=candidate.candidate_id,
        source_content_digest=candidate.source_content_digest,
        policy_digest=candidate.policy_digest,
        portable_skill_digest=contract.digest,
        approved_by=approved_by,
        approval_reason=approval_reason,
    )


def admit_skill_candidate(
    *,
    catalog: SkillCatalog,
    candidate_id: str,
    approval: SkillCandidateApproval,
    contract: PortableSkill,
    registry: SkillRegistry,
) -> RegisteredSkill:
    entry = catalog.entry(candidate_id)
    candidate = entry.candidate
    if candidate.kind is not CandidateKind.SKILL:
        raise SkillIntakeError(IntakeFailureCode.TOOL_ADMISSION_FORBIDDEN)
    if entry.disposition is not IntakeDisposition.APPROVED_FOR_ADMISSION:
        raise SkillIntakeError(IntakeFailureCode.CANDIDATE_NOT_ADMISSIBLE)
    if entry.approval_id != approval.approval_id:
        raise SkillIntakeError(IntakeFailureCode.APPROVAL_MISMATCH)
    _validate_approval_candidate(candidate, approval)
    if not isinstance(contract, PortableSkill) or contract.digest != approval.portable_skill_digest:
        raise SkillIntakeError(IntakeFailureCode.APPROVAL_MISMATCH)

    registered = registry.admit(contract)
    catalog._mark_admitted(candidate_id, registered)
    return registered


def _validate_approval_candidate(candidate: SkillCandidate, approval: SkillCandidateApproval) -> None:
    if not isinstance(approval, SkillCandidateApproval):
        raise SkillIntakeError(IntakeFailureCode.APPROVAL_MISMATCH)
    if (
        approval.candidate_id != candidate.candidate_id
        or candidate.source_content_digest is None
        or approval.source_content_digest != candidate.source_content_digest
        or approval.policy_digest != candidate.policy_digest
    ):
        raise SkillIntakeError(IntakeFailureCode.APPROVAL_MISMATCH)


def _provenance_state(observation: CandidateSourceObservation) -> ProvenanceState:
    if observation.source_tier in {SourceTier.OFFICIAL_ECOSYSTEM, SourceTier.VENDOR_NATIVE}:
        return ProvenanceState.VERIFIED
    if observation.source_tier is SourceTier.CURATED_DISCOVERY:
        if len(observation.authoritative_source_refs) == 1:
            return ProvenanceState.RESOLVED_FROM_CURATED
        if len(observation.authoritative_source_refs) > 1:
            return ProvenanceState.AMBIGUOUS
    return ProvenanceState.UNKNOWN


_BLOCK_PATTERNS: tuple[tuple[CandidateReason, re.Pattern[str]], ...] = (
    (
        CandidateReason.GENERIC_EXECUTION,
        re.compile(
            r"\b(?:shell|subprocess|os\.system|run[_ -]?command)\b|\b(?:run|execute|spawn)\s+(?:a\s+)?(?:command|shell|subprocess)\b",
            re.IGNORECASE,
        ),
    ),
    (
        CandidateReason.ARBITRARY_NETWORK,
        re.compile(r"\b(?:curl|wget|raw[_ -]?http|arbitrary[_ -]?network|open[_ -]?network)\b", re.IGNORECASE),
    ),
    (
        CandidateReason.POLICY_BYPASS,
        re.compile(
            r"\b(?:ignore|disable|bypass|skip|turn\s+off)\b.{0,48}\b(?:policy|approval|security|review|sandbox|guardrail)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        CandidateReason.UNAUTHORIZED_PRODUCTION,
        re.compile(
            r"\b(?:deploy|promote)\s+(?:directly\s+)?(?:to\s+)?production\b|\bmerge\s+(?:to|into)\s+(?:main|master)\b",
            re.IGNORECASE,
        ),
    ),
    (
        CandidateReason.HIDDEN_INSTALL_EXECUTION,
        re.compile(
            r"\b(?:pip|npm|pnpm|yarn)\s+install\b|\bdownload\b.{0,64}\b(?:execute|run)\b|\binstall\b.{0,64}\bthen\s+(?:execute|run)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)

_CREDENTIAL_RE = re.compile(
    r"\b(?:api[_ -]?key|access[_ -]?token|password|credential|authorization[_ -]?header|session[_ -]?cookie)\b",
    re.IGNORECASE,
)
_DESTRUCTIVE_RE = re.compile(r"\b(?:delete|destroy|drop|truncate|wipe|purge)\b", re.IGNORECASE)
_APPROVAL_RE = re.compile(r"\b(?:human\s+approval|approval\s+required|requires\s+approval)\b", re.IGNORECASE)


def _static_findings(observation: CandidateSourceObservation) -> tuple[CandidateReason, ...]:
    inspection = "\n".join((observation.inspection_text, *observation.declared_scripts))
    findings: list[CandidateReason] = []
    for reason, pattern in _BLOCK_PATTERNS:
        if pattern.search(inspection):
            findings.append(reason)
    if _CREDENTIAL_RE.search(inspection):
        findings.append(CandidateReason.CREDENTIAL_HANDLING)
    if _DESTRUCTIVE_RE.search(inspection) and not _APPROVAL_RE.search(inspection):
        findings.append(CandidateReason.DESTRUCTIVE_WITHOUT_APPROVAL)
    return _reason_set(findings)


def _summary(disposition: IntakeDisposition) -> str:
    if disposition is IntakeDisposition.BLOCKED:
        return "Blocked by deterministic intake policy; this candidate cannot be used at runtime."
    if disposition is IntakeDisposition.HUMAN_REQUIRED:
        return "Needs human review before this candidate can be considered for admission."
    if disposition is IntakeDisposition.QUARANTINED:
        return "Quarantined candidate with sufficient bounded evidence for explicit approval review."
    if disposition is IntakeDisposition.REJECTED:
        return "Rejected candidate; it is not available to runtime selection."
    if disposition is IntakeDisposition.APPROVED_FOR_ADMISSION:
        return "Explicitly approved candidate awaiting the existing governed skill admission check."
    if disposition is IntakeDisposition.ADMITTED:
        return "Admitted through the governed skill registry; tool authority remains separate."
    return "Superseded candidate retained as immutable intake evidence."


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _enum_value(enum_type: type[StrEnum], value: object):
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION) from exc


def _digest(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return value


def _source_ref(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > _MAX_SOURCE_REF_BYTES
        or not _SOURCE_REF_RE.fullmatch(value)
    ):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return value


def _approver_ref(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > _MAX_APPROVER_REF_BYTES
        or not _APPROVER_REF_RE.fullmatch(value)
    ):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return value


def _plain_text(value: str, max_bytes: int) -> str:
    if not isinstance(value, str) or not value or value.strip() != value or len(value.encode("utf-8")) > max_bytes:
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return value


def _inspection_text(value: str) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > _MAX_INSPECTION_BYTES:
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    if "\x00" in value:
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return value


def _inventory(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    normalized = tuple(_plain_text(value, _MAX_INVENTORY_ITEM_BYTES) for value in values)
    if len(normalized) > _MAX_INVENTORY_ITEMS:
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return normalized


def _hint_set(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str) or not _HINT_RE.fullmatch(value):
            raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
        normalized.append(value)
    if len(normalized) > _MAX_HINTS or len(set(normalized)) != len(normalized):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    return tuple(sorted(normalized))


def _license_set(values: Iterable[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise SkillIntakeError(IntakeFailureCode.INVALID_OBSERVATION)
    normalized = tuple(sorted({_plain_text(value, _MAX_LICENSE_BYTES) for value in values}, key=str.casefold))
    return normalized


def _reason_set(values: Iterable[CandidateReason]) -> tuple[CandidateReason, ...]:
    normalized = {_enum_value(CandidateReason, value) for value in values}
    return tuple(sorted(normalized, key=lambda item: item.value))
