from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from hashlib import sha256
import json
import re
from typing import Iterable
from uuid import UUID

from .governed_skills import (
    CapabilitySnapshot,
    RegisteredSkill,
    SkillRegistry,
    SkillSelection,
    SkillSelectionStatus,
    SkillSelector,
)
from .repository_intelligence import (
    CompatibilityState,
    RepositoryCompatibilityProfile,
    RepositoryShape,
)
from .service_bindings import (
    ProjectServiceBindingRegistry,
    RegisteredServiceBinding,
    ServiceBindingResolutionRecord,
    ServiceBindingResolutionStatus,
    ServiceBindingResolver,
    ServiceRequirement,
    record_service_binding_resolution,
)


ORCHESTRATION_CONTRACT_VERSION = 1
PROTECTED_APPLICATION_ROUTE = ("IMPLEMENT", "BUILD", "TEST", "VERIFY", "REVIEW")
_MAX_ACCEPTANCE_IDS = 128
_MAX_SERVICE_REQUIREMENTS = 32
_MAX_FEATURE_TOKENS = 32
_MAX_CAPABILITIES = 32
_MAX_REFERENCE_BYTES = 192

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9.-]{2,63}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_ACCEPTANCE_ID_RE = re.compile(r"^AC-[0-9]{2,3}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_REFERENCE_RE = re.compile(r"^(?:policy|evidence|lineage|delivery):[A-Za-z0-9._:-]{1,160}$")


class OrchestrationStatus(StrEnum):
    READY = "READY"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class OrchestrationFailureCode(StrEnum):
    INVALID_ORCHESTRATION_CONTRACT = "INVALID_ORCHESTRATION_CONTRACT"
    ORCHESTRATION_IDENTITY_MISMATCH = "ORCHESTRATION_IDENTITY_MISMATCH"
    ACCEPTANCE_CONTRACT_MISMATCH = "ACCEPTANCE_CONTRACT_MISMATCH"
    REPOSITORY_HUMAN_REQUIRED = "REPOSITORY_HUMAN_REQUIRED"
    SKILL_HUMAN_REQUIRED = "SKILL_HUMAN_REQUIRED"
    SERVICE_BINDING_HUMAN_REQUIRED = "SERVICE_BINDING_HUMAN_REQUIRED"
    CONFLICTING_SERVICE_REQUIREMENTS = "CONFLICTING_SERVICE_REQUIREMENTS"
    CORRECTION_POLICY_MISMATCH = "CORRECTION_POLICY_MISMATCH"
    REPLAY_EVIDENCE_MISMATCH = "REPLAY_EVIDENCE_MISMATCH"
    PROTECTED_STAGE_SEQUENCE_INVALID = "PROTECTED_STAGE_SEQUENCE_INVALID"


class ReplayDisposition(StrEnum):
    START = "START"
    CONTINUE = "CONTINUE"
    ALREADY_AT_REVIEW = "ALREADY_AT_REVIEW"


class ObjectiveOrchestrationError(ValueError):
    def __init__(self, code: OrchestrationFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class OrchestrationIdentity:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    source_revision: str
    compatibility_profile_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id))
        object.__setattr__(self, "run_id", _canonical_uuid(self.run_id))
        object.__setattr__(self, "work_specification_id", _canonical_uuid(self.work_specification_id))
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        object.__setattr__(self, "work_specification_digest", _sha256(self.work_specification_digest))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        if not isinstance(self.source_revision, str) or not _GIT_REVISION_RE.fullmatch(self.source_revision):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        object.__setattr__(self, "compatibility_profile_digest", _sha256(self.compatibility_profile_digest))

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": ORCHESTRATION_CONTRACT_VERSION,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "source_revision": self.source_revision,
            "compatibility_profile_digest": self.compatibility_profile_digest,
        }


@dataclass(frozen=True, slots=True)
class ApplicationObjective:
    objective_kind: str
    acceptance_ids: tuple[str, ...]
    service_requirements: tuple[ServiceRequirement, ...] = ()
    feature_tokens: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective_kind", _safe_token(self.objective_kind))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        requirements = tuple(self.service_requirements)
        if len(requirements) > _MAX_SERVICE_REQUIREMENTS or any(
            not isinstance(item, ServiceRequirement) for item in requirements
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        by_digest: dict[str, ServiceRequirement] = {}
        for requirement in requirements:
            by_digest.setdefault(requirement.digest, requirement)
        object.__setattr__(
            self,
            "service_requirements",
            tuple(by_digest[key] for key in sorted(by_digest)),
        )
        object.__setattr__(
            self,
            "feature_tokens",
            _bounded_tokens(self.feature_tokens, limit=_MAX_FEATURE_TOKENS),
        )

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": ORCHESTRATION_CONTRACT_VERSION,
            "objective_kind": self.objective_kind,
            "acceptance_ids": list(self.acceptance_ids),
            "service_requirement_digests": [item.digest for item in self.service_requirements],
            "feature_tokens": list(self.feature_tokens),
            "contains_raw_objective": False,
        }


@dataclass(frozen=True, slots=True)
class CorrectionPolicyReference:
    policy_digest: str
    evidence_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", _sha256(self.policy_digest))
        if self.evidence_ref is not None:
            object.__setattr__(self, "evidence_ref", _safe_reference(self.evidence_ref))

    def as_dict(self) -> dict[str, str | None]:
        return {
            "policy_digest": self.policy_digest,
            "evidence_ref": self.evidence_ref,
        }


@dataclass(frozen=True, slots=True)
class ObjectiveOrchestrationDecision:
    orchestration_id: str
    status: OrchestrationStatus
    reason: OrchestrationFailureCode | None
    dependency_reason: str | None
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    identity_digest: str
    objective_kind: str
    objective_digest: str
    acceptance_ids: tuple[str, ...]
    compatibility_profile_digest: str
    source_revision: str
    repository_shape: RepositoryShape
    capability_policy_digest: str
    skill_id: str | None
    skill_version: str | None
    skill_digest: str | None
    required_capabilities: tuple[str, ...]
    service_resolutions: tuple[ServiceBindingResolutionRecord, ...]
    correction_policy_digest: str
    correction_policy_evidence_ref: str | None
    protected_route: tuple[str, ...] = PROTECTED_APPLICATION_ROUTE

    def __post_init__(self) -> None:
        if not isinstance(self.orchestration_id, str) or not re.fullmatch(
            r"orchestration:[0-9a-f]{64}", self.orchestration_id
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        try:
            status = self.status if isinstance(self.status, OrchestrationStatus) else OrchestrationStatus(self.status)
        except (TypeError, ValueError) as exc:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT) from exc
        object.__setattr__(self, "status", status)
        if self.reason is not None and not isinstance(self.reason, OrchestrationFailureCode):
            try:
                object.__setattr__(self, "reason", OrchestrationFailureCode(self.reason))
            except (TypeError, ValueError) as exc:
                raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT) from exc
        if status is OrchestrationStatus.READY and self.reason is not None:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        if status is OrchestrationStatus.HUMAN_REQUIRED and self.reason is None:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        if self.dependency_reason is not None and not _REASON_RE.fullmatch(self.dependency_reason):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)

        identity = OrchestrationIdentity(
            project_id=self.project_id,
            run_id=self.run_id,
            work_specification_id=self.work_specification_id,
            work_specification_revision=self.work_specification_revision,
            work_specification_digest=self.work_specification_digest,
            acceptance_ids=self.acceptance_ids,
            source_revision=self.source_revision,
            compatibility_profile_digest=self.compatibility_profile_digest,
        )
        object.__setattr__(self, "project_id", identity.project_id)
        object.__setattr__(self, "run_id", identity.run_id)
        object.__setattr__(self, "work_specification_id", identity.work_specification_id)
        object.__setattr__(self, "work_specification_digest", identity.work_specification_digest)
        object.__setattr__(self, "acceptance_ids", identity.acceptance_ids)
        object.__setattr__(self, "compatibility_profile_digest", identity.compatibility_profile_digest)
        if _sha256(self.identity_digest) != identity.digest:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ORCHESTRATION_IDENTITY_MISMATCH)

        object.__setattr__(self, "objective_kind", _safe_token(self.objective_kind))
        object.__setattr__(self, "objective_digest", _sha256(self.objective_digest))
        try:
            shape = self.repository_shape if isinstance(self.repository_shape, RepositoryShape) else RepositoryShape(self.repository_shape)
        except (TypeError, ValueError) as exc:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT) from exc
        object.__setattr__(self, "repository_shape", shape)
        object.__setattr__(self, "capability_policy_digest", _sha256(self.capability_policy_digest))

        skill_fields = (self.skill_id, self.skill_version, self.skill_digest)
        if any(value is None for value in skill_fields) and any(value is not None for value in skill_fields):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        if self.skill_id is not None:
            if not _SKILL_ID_RE.fullmatch(self.skill_id) or not _SEMVER_RE.fullmatch(self.skill_version or ""):
                raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
            object.__setattr__(self, "skill_digest", _sha256(self.skill_digest or ""))
        if status is OrchestrationStatus.READY and self.skill_id is None:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        object.__setattr__(
            self,
            "required_capabilities",
            _bounded_tokens(self.required_capabilities, limit=_MAX_CAPABILITIES),
        )

        resolutions = tuple(self.service_resolutions)
        if len(resolutions) > _MAX_SERVICE_REQUIREMENTS or any(
            not isinstance(item, ServiceBindingResolutionRecord) for item in resolutions
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        if any(item.project_id != identity.project_id or item.run_id != identity.run_id for item in resolutions):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ORCHESTRATION_IDENTITY_MISMATCH)
        if status is OrchestrationStatus.READY and any(
            item.status is not ServiceBindingResolutionStatus.SELECTED for item in resolutions
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        object.__setattr__(self, "service_resolutions", resolutions)

        object.__setattr__(self, "correction_policy_digest", _sha256(self.correction_policy_digest))
        if self.correction_policy_evidence_ref is not None:
            object.__setattr__(
                self,
                "correction_policy_evidence_ref",
                _safe_reference(self.correction_policy_evidence_ref),
            )
        if tuple(self.protected_route) != PROTECTED_APPLICATION_ROUTE:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        object.__setattr__(self, "protected_route", PROTECTED_APPLICATION_ROUTE)

    @property
    def ready(self) -> bool:
        return self.status is OrchestrationStatus.READY

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": ORCHESTRATION_CONTRACT_VERSION,
            "orchestration_id": self.orchestration_id,
            "status": self.status.value,
            "reason": self.reason.value if self.reason is not None else None,
            "dependency_reason": self.dependency_reason,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "identity_digest": self.identity_digest,
            "objective_kind": self.objective_kind,
            "objective_digest": self.objective_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "compatibility_profile_digest": self.compatibility_profile_digest,
            "source_revision": self.source_revision,
            "repository_shape": self.repository_shape.value,
            "capability_policy_digest": self.capability_policy_digest,
            "skill_id": self.skill_id,
            "skill_version": self.skill_version,
            "skill_digest": self.skill_digest,
            "required_capabilities": list(self.required_capabilities),
            "service_resolutions": [item.as_dict() for item in self.service_resolutions],
            "correction_policy_digest": self.correction_policy_digest,
            "correction_policy_evidence_ref": self.correction_policy_evidence_ref,
            "protected_route": list(self.protected_route),
            "acceptance_can_be_weakened": False,
            "performs_source_mutation": False,
            "performs_validation": False,
            "performs_provider_action": False,
            "grants_authority": False,
            "requires_exact_lineage_validation": True,
            "preview_delivery_governed_externally": True,
            "review_is_autonomous_ceiling": True,
            "contains_raw_objective": False,
            "contains_raw_source": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "contains_hidden_reasoning": False,
        }


class ObjectiveToApplicationOrchestrator:
    def __init__(
        self,
        *,
        skill_registry: SkillRegistry,
        service_registry: ProjectServiceBindingRegistry,
    ) -> None:
        if not isinstance(skill_registry, SkillRegistry) or not isinstance(
            service_registry, ProjectServiceBindingRegistry
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
        self.skill_registry = skill_registry
        self.service_registry = service_registry
        self.skill_selector = SkillSelector(skill_registry)
        self.service_resolver = ServiceBindingResolver(service_registry)

    def orchestrate(
        self,
        *,
        identity: OrchestrationIdentity,
        objective: ApplicationObjective,
        compatibility: RepositoryCompatibilityProfile,
        capabilities: CapabilitySnapshot,
        correction_policy: CorrectionPolicyReference,
    ) -> ObjectiveOrchestrationDecision:
        if (
            not isinstance(identity, OrchestrationIdentity)
            or not isinstance(objective, ApplicationObjective)
            or not isinstance(compatibility, RepositoryCompatibilityProfile)
            or not isinstance(capabilities, CapabilitySnapshot)
            or not isinstance(correction_policy, CorrectionPolicyReference)
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)

        self._validate_identity(identity, compatibility)
        if objective.acceptance_ids != identity.acceptance_ids:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ACCEPTANCE_CONTRACT_MISMATCH)
        if self.service_registry.project_id != identity.project_id:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ORCHESTRATION_IDENTITY_MISMATCH)

        if (
            compatibility.compatibility_state is not CompatibilityState.SUPPORTED
            or compatibility.repository_shape in {RepositoryShape.UNSUPPORTED, RepositoryShape.AMBIGUOUS}
        ):
            return self._decision(
                identity=identity,
                objective=objective,
                compatibility=compatibility,
                capabilities=capabilities,
                correction_policy=correction_policy,
                status=OrchestrationStatus.HUMAN_REQUIRED,
                reason=OrchestrationFailureCode.REPOSITORY_HUMAN_REQUIRED,
                dependency_reason=compatibility.compatibility_state.value,
            )

        selection = self.skill_selector.select(
            objective_kind=objective.objective_kind,
            compatibility=compatibility,
            capabilities=capabilities,
        )
        if selection.status is SkillSelectionStatus.HUMAN_REQUIRED:
            return self._decision(
                identity=identity,
                objective=objective,
                compatibility=compatibility,
                capabilities=capabilities,
                correction_policy=correction_policy,
                status=OrchestrationStatus.HUMAN_REQUIRED,
                reason=OrchestrationFailureCode.SKILL_HUMAN_REQUIRED,
                dependency_reason=selection.reason.value if selection.reason is not None else None,
                required_capabilities=selection.required_capabilities,
            )

        selected_skill = self._registered_skill(selection)
        conflict = _conflicting_service_reason(objective.service_requirements)
        if conflict is not None:
            return self._decision(
                identity=identity,
                objective=objective,
                compatibility=compatibility,
                capabilities=capabilities,
                correction_policy=correction_policy,
                status=OrchestrationStatus.HUMAN_REQUIRED,
                reason=OrchestrationFailureCode.CONFLICTING_SERVICE_REQUIREMENTS,
                dependency_reason=conflict,
                selected_skill=selected_skill,
                required_capabilities=selection.required_capabilities,
            )

        resolution_records: list[ServiceBindingResolutionRecord] = []
        for requirement in objective.service_requirements:
            resolution = self.service_resolver.resolve(
                project_id=identity.project_id,
                requirement=requirement,
            )
            registered_binding = (
                self._registered_binding(
                    resolution.binding_id,
                    resolution.binding_version,
                    resolution.binding_digest,
                )
                if resolution.status is ServiceBindingResolutionStatus.SELECTED
                else None
            )
            record = record_service_binding_resolution(
                project_id=identity.project_id,
                run_id=identity.run_id,
                requirement=requirement,
                policy=self.service_registry.policy,
                resolution=resolution,
                registered_binding=registered_binding,
            )
            resolution_records.append(record)
            if resolution.status is ServiceBindingResolutionStatus.HUMAN_REQUIRED:
                return self._decision(
                    identity=identity,
                    objective=objective,
                    compatibility=compatibility,
                    capabilities=capabilities,
                    correction_policy=correction_policy,
                    status=OrchestrationStatus.HUMAN_REQUIRED,
                    reason=OrchestrationFailureCode.SERVICE_BINDING_HUMAN_REQUIRED,
                    dependency_reason=resolution.reason.value if resolution.reason is not None else None,
                    selected_skill=selected_skill,
                    required_capabilities=selection.required_capabilities,
                    service_resolutions=tuple(resolution_records),
                )

        return self._decision(
            identity=identity,
            objective=objective,
            compatibility=compatibility,
            capabilities=capabilities,
            correction_policy=correction_policy,
            status=OrchestrationStatus.READY,
            reason=None,
            dependency_reason=None,
            selected_skill=selected_skill,
            required_capabilities=selection.required_capabilities,
            service_resolutions=tuple(resolution_records),
        )

    @staticmethod
    def _validate_identity(
        identity: OrchestrationIdentity,
        compatibility: RepositoryCompatibilityProfile,
    ) -> None:
        if (
            compatibility.project_id != identity.project_id
            or compatibility.source_revision != identity.source_revision
            or compatibility.profile_digest != identity.compatibility_profile_digest
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ORCHESTRATION_IDENTITY_MISMATCH)

    def _registered_skill(self, selection: SkillSelection) -> RegisteredSkill:
        matches = tuple(
            item
            for item in self.skill_registry.registered()
            if item.contract.skill_id == selection.skill_id
            and item.contract.version == selection.version
            and item.content_digest == selection.content_digest
        )
        if len(matches) != 1:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ORCHESTRATION_IDENTITY_MISMATCH)
        return matches[0]

    def _registered_binding(
        self,
        binding_id: str | None,
        binding_version: str | None,
        binding_digest: str | None,
    ) -> RegisteredServiceBinding:
        matches = tuple(
            item
            for item in self.service_registry.registered()
            if item.contract.binding_id == binding_id
            and item.contract.version == binding_version
            and item.content_digest == binding_digest
        )
        if len(matches) != 1:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.ORCHESTRATION_IDENTITY_MISMATCH)
        return matches[0]

    @staticmethod
    def _decision(
        *,
        identity: OrchestrationIdentity,
        objective: ApplicationObjective,
        compatibility: RepositoryCompatibilityProfile,
        capabilities: CapabilitySnapshot,
        correction_policy: CorrectionPolicyReference,
        status: OrchestrationStatus,
        reason: OrchestrationFailureCode | None,
        dependency_reason: str | None,
        selected_skill: RegisteredSkill | None = None,
        required_capabilities: tuple[str, ...] = (),
        service_resolutions: tuple[ServiceBindingResolutionRecord, ...] = (),
    ) -> ObjectiveOrchestrationDecision:
        if dependency_reason is not None and not _REASON_RE.fullmatch(dependency_reason):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)

        core: dict[str, object] = {
            "contract_version": ORCHESTRATION_CONTRACT_VERSION,
            "status": status.value,
            "reason": reason.value if reason is not None else None,
            "dependency_reason": dependency_reason,
            "identity_digest": identity.digest,
            "objective_digest": objective.digest,
            "compatibility_profile_digest": compatibility.profile_digest,
            "source_revision": compatibility.source_revision,
            "repository_shape": compatibility.repository_shape.value,
            "capability_policy_digest": capabilities.policy_digest,
            "skill_id": selected_skill.contract.skill_id if selected_skill is not None else None,
            "skill_version": selected_skill.contract.version if selected_skill is not None else None,
            "skill_digest": selected_skill.content_digest if selected_skill is not None else None,
            "required_capabilities": list(required_capabilities),
            "service_resolution_ids": [item.resolution_id for item in service_resolutions],
            "correction_policy_digest": correction_policy.policy_digest,
            "correction_policy_evidence_ref": correction_policy.evidence_ref,
            "protected_route": list(PROTECTED_APPLICATION_ROUTE),
        }
        orchestration_id = f"orchestration:{sha256(_canonical_json(core)).hexdigest()}"
        return ObjectiveOrchestrationDecision(
            orchestration_id=orchestration_id,
            status=status,
            reason=reason,
            dependency_reason=dependency_reason,
            project_id=identity.project_id,
            run_id=identity.run_id,
            work_specification_id=identity.work_specification_id,
            work_specification_revision=identity.work_specification_revision,
            work_specification_digest=identity.work_specification_digest,
            identity_digest=identity.digest,
            objective_kind=objective.objective_kind,
            objective_digest=objective.digest,
            acceptance_ids=identity.acceptance_ids,
            compatibility_profile_digest=compatibility.profile_digest,
            source_revision=compatibility.source_revision,
            repository_shape=compatibility.repository_shape,
            capability_policy_digest=capabilities.policy_digest,
            skill_id=selected_skill.contract.skill_id if selected_skill is not None else None,
            skill_version=selected_skill.contract.version if selected_skill is not None else None,
            skill_digest=selected_skill.content_digest if selected_skill is not None else None,
            required_capabilities=required_capabilities,
            service_resolutions=service_resolutions,
            correction_policy_digest=correction_policy.policy_digest,
            correction_policy_evidence_ref=correction_policy.evidence_ref,
        )


@dataclass(frozen=True, slots=True)
class ProtectedStageEvidence:
    stage: str
    evidence_digest: str

    def __post_init__(self) -> None:
        if self.stage not in PROTECTED_APPLICATION_ROUTE:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.PROTECTED_STAGE_SEQUENCE_INVALID)
        object.__setattr__(self, "evidence_digest", _sha256(self.evidence_digest))

    def as_dict(self) -> dict[str, str]:
        return {"stage": self.stage, "evidence_digest": self.evidence_digest}


@dataclass(frozen=True, slots=True)
class OrchestrationProgressEvidence:
    orchestration_id: str
    project_id: str
    run_id: str
    work_specification_digest: str
    compatibility_profile_digest: str
    correction_policy_digest: str
    run_revision: int
    current_stage: str
    completed_stages: tuple[ProtectedStageEvidence, ...] = ()
    accepted_lineage_ref: str | None = None
    accepted_content_digest: str | None = None
    source_delivery_ref: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.orchestration_id, str) or not re.fullmatch(
            r"orchestration:[0-9a-f]{64}", self.orchestration_id
        ):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
        object.__setattr__(self, "project_id", _canonical_uuid(self.project_id))
        object.__setattr__(self, "run_id", _canonical_uuid(self.run_id))
        object.__setattr__(self, "work_specification_digest", _sha256(self.work_specification_digest))
        object.__setattr__(self, "compatibility_profile_digest", _sha256(self.compatibility_profile_digest))
        object.__setattr__(self, "correction_policy_digest", _sha256(self.correction_policy_digest))
        if not isinstance(self.run_revision, int) or isinstance(self.run_revision, bool) or self.run_revision < 1:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
        if self.current_stage not in PROTECTED_APPLICATION_ROUTE:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.PROTECTED_STAGE_SEQUENCE_INVALID)

        completed = tuple(self.completed_stages)
        if any(not isinstance(item, ProtectedStageEvidence) for item in completed):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
        stages = tuple(item.stage for item in completed)
        if stages != PROTECTED_APPLICATION_ROUTE[: len(stages)] or len(set(stages)) != len(stages):
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.PROTECTED_STAGE_SEQUENCE_INVALID)
        if "REVIEW" in stages:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.PROTECTED_STAGE_SEQUENCE_INVALID)
        object.__setattr__(self, "completed_stages", completed)

        implementation_complete = "IMPLEMENT" in stages
        if implementation_complete:
            if self.accepted_lineage_ref is None or self.accepted_content_digest is None:
                raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
            object.__setattr__(self, "accepted_lineage_ref", _safe_reference(self.accepted_lineage_ref))
            object.__setattr__(self, "accepted_content_digest", _sha256(self.accepted_content_digest))
        elif self.accepted_lineage_ref is not None or self.accepted_content_digest is not None:
            raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)

        if self.source_delivery_ref is not None:
            if self.current_stage != "REVIEW" or stages != PROTECTED_APPLICATION_ROUTE[:-1]:
                raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
            object.__setattr__(self, "source_delivery_ref", _safe_reference(self.source_delivery_ref))

    def as_dict(self) -> dict[str, object]:
        return {
            "orchestration_id": self.orchestration_id,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_digest": self.work_specification_digest,
            "compatibility_profile_digest": self.compatibility_profile_digest,
            "correction_policy_digest": self.correction_policy_digest,
            "run_revision": self.run_revision,
            "current_stage": self.current_stage,
            "completed_stages": [item.as_dict() for item in self.completed_stages],
            "accepted_lineage_ref": self.accepted_lineage_ref,
            "accepted_content_digest": self.accepted_content_digest,
            "source_delivery_ref": self.source_delivery_ref,
            "contains_provider_payload": False,
            "grants_execution": False,
        }


@dataclass(frozen=True, slots=True)
class OrchestrationReplayDecision:
    disposition: ReplayDisposition
    current_stage: str
    next_stage: str | None
    implementation_already_accepted: bool
    delivery_already_recorded: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "disposition": self.disposition.value,
            "current_stage": self.current_stage,
            "next_stage": self.next_stage,
            "implementation_already_accepted": self.implementation_already_accepted,
            "delivery_already_recorded": self.delivery_already_recorded,
            "grants_execution": False,
            "grants_provider_authority": False,
        }


def derive_replay_disposition(
    *,
    decision: ObjectiveOrchestrationDecision,
    progress: OrchestrationProgressEvidence,
) -> OrchestrationReplayDecision:
    if not isinstance(decision, ObjectiveOrchestrationDecision) or not decision.ready:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
    if not isinstance(progress, OrchestrationProgressEvidence):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)
    if (
        progress.orchestration_id != decision.orchestration_id
        or progress.project_id != decision.project_id
        or progress.run_id != decision.run_id
        or progress.work_specification_digest != decision.work_specification_digest
        or progress.compatibility_profile_digest != decision.compatibility_profile_digest
        or progress.correction_policy_digest != decision.correction_policy_digest
    ):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.REPLAY_EVIDENCE_MISMATCH)

    completed = tuple(item.stage for item in progress.completed_stages)
    expected_current = PROTECTED_APPLICATION_ROUTE[len(completed)]
    if progress.current_stage != expected_current:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.PROTECTED_STAGE_SEQUENCE_INVALID)

    implementation_accepted = "IMPLEMENT" in completed
    delivery_recorded = progress.source_delivery_ref is not None
    if progress.current_stage == "REVIEW":
        disposition = ReplayDisposition.ALREADY_AT_REVIEW
        next_stage = None
    elif not completed:
        disposition = ReplayDisposition.START
        next_stage = "IMPLEMENT"
    else:
        disposition = ReplayDisposition.CONTINUE
        next_stage = progress.current_stage

    return OrchestrationReplayDecision(
        disposition=disposition,
        current_stage=progress.current_stage,
        next_stage=next_stage,
        implementation_already_accepted=implementation_accepted,
        delivery_already_recorded=delivery_recorded,
    )


def public_orchestration_field_names() -> tuple[str, ...]:
    """Expose public field names for structural authority/privacy regression tests."""
    contract_types = (
        OrchestrationIdentity,
        ApplicationObjective,
        CorrectionPolicyReference,
        ObjectiveOrchestrationDecision,
        OrchestrationProgressEvidence,
    )
    return tuple(sorted({field.name for contract_type in contract_types for field in fields(contract_type)}))


def _conflicting_service_reason(requirements: tuple[ServiceRequirement, ...]) -> str | None:
    by_service: dict[str, str] = {}
    for requirement in requirements:
        existing = by_service.get(requirement.service_id)
        if existing is not None and existing != requirement.digest:
            return OrchestrationFailureCode.CONFLICTING_SERVICE_REQUIREMENTS.value
        by_service[requirement.service_id] = requirement.digest
    return None


def _acceptance_ids(values: Iterable[str]) -> tuple[str, ...]:
    items = tuple(values)
    if not items or len(items) > _MAX_ACCEPTANCE_IDS:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    if any(not isinstance(item, str) or not _ACCEPTANCE_ID_RE.fullmatch(item) for item in items):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    if len(set(items)) != len(items):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    return items


def _bounded_tokens(values: Iterable[str], *, limit: int) -> tuple[str, ...]:
    items = tuple(values)
    if len(items) > limit:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    normalized = tuple(_safe_token(item) for item in items)
    if len(set(normalized)) != len(normalized):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    return tuple(sorted(normalized))


def _safe_token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    return value


def _safe_reference(value: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > _MAX_REFERENCE_BYTES
        or not _REFERENCE_RE.fullmatch(value)
    ):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    return value


def _sha256(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    return value


def _canonical_uuid(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT) from exc
    canonical = str(parsed)
    if canonical != value:
        raise ObjectiveOrchestrationError(OrchestrationFailureCode.INVALID_ORCHESTRATION_CONTRACT)
    return canonical


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


__all__ = [
    "ApplicationObjective",
    "CorrectionPolicyReference",
    "ObjectiveOrchestrationDecision",
    "ObjectiveOrchestrationError",
    "ObjectiveToApplicationOrchestrator",
    "ORCHESTRATION_CONTRACT_VERSION",
    "OrchestrationFailureCode",
    "OrchestrationIdentity",
    "OrchestrationProgressEvidence",
    "OrchestrationReplayDecision",
    "OrchestrationStatus",
    "PROTECTED_APPLICATION_ROUTE",
    "ProtectedStageEvidence",
    "ReplayDisposition",
    "derive_replay_disposition",
    "public_orchestration_field_names",
]
