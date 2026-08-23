from __future__ import annotations

from dataclasses import dataclass

from .optimization_contracts import (MAX_REGISTRY_RECORDS, ModelClass, OptimizationPolicyError, _canonical_digest, _digest, _refs, _safe_token)

@dataclass(frozen=True, slots=True)
class ReusablePatternRecord:
    pattern_id: str
    version: str
    digest: str
    pattern_type: str
    compatibility: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    validated: bool
    project_id: str | None = None
    public: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "pattern_id", _safe_token(self.pattern_id, field="pattern_id"))
        object.__setattr__(self, "version", _safe_token(self.version, field="pattern_version"))
        _digest(self.digest, field="pattern_digest")
        object.__setattr__(self, "pattern_type", _safe_token(self.pattern_type, field="pattern_type"))
        object.__setattr__(self, "compatibility", _refs(self.compatibility, field="pattern_compatibility"))
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="pattern_evidence"))
        if self.project_id is not None:
            object.__setattr__(self, "project_id", _safe_token(self.project_id, field="project_id"))
        if self.public and self.project_id is not None:
            raise OptimizationPolicyError("public reusable pattern cannot retain Project-private scope")
        if self.validated and not self.evidence_refs:
            raise OptimizationPolicyError("validated reusable pattern requires evidence")


class ReusablePatternRegistry:
    def __init__(self, records: tuple[ReusablePatternRecord, ...] = ()) -> None:
        if len(records) > MAX_REGISTRY_RECORDS:
            raise OptimizationPolicyError("pattern registry exceeds bound")
        self.records = records

    def recommend(self, *, project_id: str, pattern_type: str, compatibility: tuple[str, ...]) -> tuple[ReusablePatternRecord, ...]:
        project = _safe_token(project_id, field="project_id")
        kind = _safe_token(pattern_type, field="pattern_type")
        required = set(_refs(compatibility, field="required_compatibility"))
        result = [
            record
            for record in self.records
            if record.validated
            and record.pattern_type == kind
            and required.issubset(set(record.compatibility))
            and (record.project_id == project or record.public)
        ]
        return tuple(sorted(result, key=lambda item: (item.pattern_id, item.version, item.digest)))


@dataclass(frozen=True, slots=True)
class FailureFingerprint:
    digest: str
    failure_class: str
    failure_code: str
    component_id: str
    structural_locator: str
    tool_identity: str

    @classmethod
    def build(
        cls,
        *,
        failure_class: str,
        failure_code: str,
        component_id: str,
        structural_locator: str,
        tool_identity: str,
    ) -> "FailureFingerprint":
        payload = {
            "failure_class": _safe_token(failure_class, field="failure_class"),
            "failure_code": _safe_token(failure_code, field="failure_code"),
            "component_id": _safe_token(component_id, field="component_id"),
            "structural_locator": _safe_token(structural_locator, field="structural_locator"),
            "tool_identity": _safe_token(tool_identity, field="tool_identity"),
        }
        return cls(digest=_canonical_digest(payload), **payload)


@dataclass(frozen=True, slots=True)
class RepairMemoryRecord:
    fingerprint: str
    repair_class: str
    outcome_quality: str
    compatibility: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    project_id: str | None = None
    public: bool = False

    def __post_init__(self) -> None:
        _digest(self.fingerprint, field="repair_fingerprint")
        object.__setattr__(self, "repair_class", _safe_token(self.repair_class, field="repair_class"))
        object.__setattr__(self, "outcome_quality", _safe_token(self.outcome_quality, field="outcome_quality"))
        object.__setattr__(self, "compatibility", _refs(self.compatibility, field="repair_compatibility"))
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="repair_evidence"))
        if self.project_id is not None:
            object.__setattr__(self, "project_id", _safe_token(self.project_id, field="project_id"))
        if self.public and self.project_id is not None:
            raise OptimizationPolicyError("public repair memory cannot retain Project-private scope")
        if not self.evidence_refs:
            raise OptimizationPolicyError("repair memory requires bounded outcome evidence")


class RepairMemory:
    def __init__(self, records: tuple[RepairMemoryRecord, ...] = ()) -> None:
        if len(records) > MAX_REGISTRY_RECORDS:
            raise OptimizationPolicyError("repair memory exceeds bound")
        self.records = records

    def recommend(self, *, project_id: str, fingerprint: str, compatibility: tuple[str, ...]) -> tuple[RepairMemoryRecord, ...]:
        project = _safe_token(project_id, field="project_id")
        digest = _digest(fingerprint, field="failure_fingerprint")
        required = set(_refs(compatibility, field="required_compatibility"))
        result = [
            record
            for record in self.records
            if record.fingerprint == digest
            and required.issubset(set(record.compatibility))
            and (record.project_id == project or record.public)
        ]
        return tuple(sorted(result, key=lambda item: (item.repair_class, item.outcome_quality)))


@dataclass(frozen=True, slots=True)
class ModelProfile:
    model_class: ModelClass
    capabilities: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", _refs(self.capabilities, field="model_capability"))
        if not self.capabilities:
            raise OptimizationPolicyError("model profile requires capabilities")


@dataclass(frozen=True, slots=True)
class ModelRoutingDecision:
    model_class: ModelClass | None
    blocked: bool
    reason: str


class AdaptiveModelRouter:
    def __init__(self, profiles: tuple[ModelProfile, ...], *, escalation_confidence: float = 0.65) -> None:
        if not 0.0 <= escalation_confidence <= 1.0:
            raise OptimizationPolicyError("routing confidence must be between 0 and 1")
        if len({profile.model_class for profile in profiles}) != len(profiles):
            raise OptimizationPolicyError("model profiles must have unique classes")
        self.profiles = profiles
        self.escalation_confidence = escalation_confidence

    def route(
        self,
        *,
        required_capability: str,
        evidence_confidence: float,
        approved_classes: tuple[ModelClass, ...],
        protected_work: bool = False,
    ) -> ModelRoutingDecision:
        capability = _safe_token(required_capability, field="required_capability")
        if not 0.0 <= evidence_confidence <= 1.0:
            raise OptimizationPolicyError("evidence confidence must be between 0 and 1")
        approved = set(approved_classes)
        order = (ModelClass.FAST, ModelClass.GENERAL, ModelClass.DEEP)
        candidates = [
            profile.model_class
            for profile in self.profiles
            if profile.model_class in approved and capability in profile.capabilities
        ]
        if not candidates:
            return ModelRoutingDecision(None, True, "NO_APPROVED_CAPABLE_MODEL")
        if protected_work or evidence_confidence < self.escalation_confidence:
            for model_class in reversed(order):
                if model_class in candidates:
                    return ModelRoutingDecision(model_class, False, "ESCALATED_FOR_PROTECTED_OR_LOW_CONFIDENCE_WORK")
        for model_class in order:
            if model_class in candidates:
                return ModelRoutingDecision(model_class, False, "LOWEST_APPROVED_CAPABLE_CLASS")
        return ModelRoutingDecision(None, True, "NO_APPROVED_CAPABLE_MODEL")
