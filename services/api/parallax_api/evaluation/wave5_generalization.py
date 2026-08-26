from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable, Mapping
from uuid import UUID

from ..code.autonomous_correction import CorrectionSessionState, CorrectionSessionStatus
from ..code.objective_orchestration import ObjectiveOrchestrationDecision, OrchestrationStatus
from ..code.repository_intelligence import (
    CompatibilityState,
    RepositoryCompatibilityProfile,
    RepositoryShape,
)
from ..code.validated_memory import MemoryKind, MemorySelectionResult, MemorySelectionStatus
from .reference_app import ReferenceAppResult


WAVE5_GENERALIZATION_CONTRACT_VERSION = 1
_MAX_CASES = 32
_MAX_ITEMS = 32
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_CASE_ID_RE = re.compile(r"^[a-z][a-z0-9._-]{2,95}$")
_SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,191}$")


class GeneralizationFailureCode(StrEnum):
    INVALID_MANIFEST = "INVALID_MANIFEST"
    DIVERSITY_REQUIREMENT_MISSING = "DIVERSITY_REQUIREMENT_MISSING"
    CASE_IDENTITY_MISMATCH = "CASE_IDENTITY_MISMATCH"
    COMPATIBILITY_EXPECTATION_MISMATCH = "COMPATIBILITY_EXPECTATION_MISMATCH"
    ORCHESTRATION_EXPECTATION_MISMATCH = "ORCHESTRATION_EXPECTATION_MISMATCH"
    MEMORY_EXPECTATION_MISMATCH = "MEMORY_EXPECTATION_MISMATCH"
    RUNTIME_PROOF_REQUIRED = "RUNTIME_PROOF_REQUIRED"
    RUNTIME_PROOF_INVALID = "RUNTIME_PROOF_INVALID"
    CORRECTION_PROOF_REQUIRED = "CORRECTION_PROOF_REQUIRED"
    CORRECTION_PROOF_INVALID = "CORRECTION_PROOF_INVALID"
    PREVIEW_REPLAY_REQUIRED = "PREVIEW_REPLAY_REQUIRED"
    REPORT_COVERAGE_MISMATCH = "REPORT_COVERAGE_MISMATCH"
    REPORT_CONTAINS_FAILED_CASE = "REPORT_CONTAINS_FAILED_CASE"


class GeneralizationProofError(ValueError):
    def __init__(self, code: GeneralizationFailureCode) -> None:
        self.code = code
        super().__init__(code.value)


class ExpectedOutcome(StrEnum):
    READY = "READY"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


@dataclass(frozen=True, slots=True)
class BenchmarkSignal:
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
class BenchmarkServiceRequirement:
    service_id: str
    interface_version: str
    required_features: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "service_id", _token(self.service_id))
        object.__setattr__(self, "interface_version", _token(self.interface_version))
        object.__setattr__(self, "required_features", _tokens(self.required_features))

    @property
    def key(self) -> tuple[str, str, tuple[str, ...]]:
        return self.service_id, self.interface_version, self.required_features

    def as_dict(self) -> dict[str, object]:
        return {
            "service_id": self.service_id,
            "interface_version": self.interface_version,
            "required_features": list(self.required_features),
        }


@dataclass(frozen=True, slots=True)
class GeneralizationBenchmarkCase:
    case_id: str
    version: str
    expected_shape: RepositoryShape
    expected_outcome: ExpectedOutcome
    objective_kind: str
    required_signals: tuple[BenchmarkSignal, ...]
    required_capabilities: tuple[str, ...]
    service_requirements: tuple[BenchmarkServiceRequirement, ...]
    requested_memory_kinds: tuple[MemoryKind, ...]
    expected_memory_status: MemorySelectionStatus
    runtime_proof: bool
    correction_proof: bool
    preview_replay_proof: bool
    malicious_input: bool

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not _CASE_ID_RE.fullmatch(self.case_id):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if not isinstance(self.version, str) or not _SEMVER_RE.fullmatch(self.version):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if not isinstance(self.expected_shape, RepositoryShape) or not isinstance(
            self.expected_outcome, ExpectedOutcome
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        object.__setattr__(self, "objective_kind", _token(self.objective_kind))
        signals = tuple(self.required_signals)
        if len(signals) > _MAX_ITEMS or any(not isinstance(item, BenchmarkSignal) for item in signals):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if len({item.key for item in signals}) != len(signals):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        object.__setattr__(self, "required_signals", tuple(sorted(signals, key=lambda item: item.key)))
        object.__setattr__(self, "required_capabilities", _tokens(self.required_capabilities))
        services = tuple(self.service_requirements)
        if len(services) > _MAX_ITEMS or any(
            not isinstance(item, BenchmarkServiceRequirement) for item in services
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if len({item.key for item in services}) != len(services):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        object.__setattr__(self, "service_requirements", tuple(sorted(services, key=lambda item: item.key)))
        kinds = tuple(self.requested_memory_kinds)
        if not kinds or len(kinds) > len(MemoryKind) or any(not isinstance(item, MemoryKind) for item in kinds):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if len(set(kinds)) != len(kinds):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        object.__setattr__(self, "requested_memory_kinds", tuple(sorted(kinds, key=lambda item: item.value)))
        if not isinstance(self.expected_memory_status, MemorySelectionStatus):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        for value in (self.runtime_proof, self.correction_proof, self.preview_replay_proof, self.malicious_input):
            if not isinstance(value, bool):
                raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if self.preview_replay_proof and not self.runtime_proof:
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if self.expected_outcome is ExpectedOutcome.HUMAN_REQUIRED and (
            self.runtime_proof or self.correction_proof or self.preview_replay_proof
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "version": self.version,
            "expected_shape": self.expected_shape.value,
            "expected_outcome": self.expected_outcome.value,
            "objective_kind": self.objective_kind,
            "required_signals": [item.as_dict() for item in self.required_signals],
            "required_capabilities": list(self.required_capabilities),
            "service_requirements": [item.as_dict() for item in self.service_requirements],
            "requested_memory_kinds": [item.value for item in self.requested_memory_kinds],
            "expected_memory_status": self.expected_memory_status.value,
            "runtime_proof": self.runtime_proof,
            "correction_proof": self.correction_proof,
            "preview_replay_proof": self.preview_replay_proof,
            "malicious_input": self.malicious_input,
        }


@dataclass(frozen=True, slots=True)
class Wave5GeneralizationManifest:
    suite_id: str
    version: str
    cases: tuple[GeneralizationBenchmarkCase, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "suite_id", _token(self.suite_id))
        if not isinstance(self.version, str) or not _SEMVER_RE.fullmatch(self.version):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        cases = tuple(self.cases)
        if not 1 <= len(cases) <= _MAX_CASES or any(
            not isinstance(item, GeneralizationBenchmarkCase) for item in cases
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        if len({item.case_id for item in cases}) != len(cases):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        ordered = tuple(sorted(cases, key=lambda item: item.case_id))
        object.__setattr__(self, "cases", ordered)
        self._validate_coverage()

    def _validate_coverage(self) -> None:
        ready_shapes = {
            item.expected_shape for item in self.cases if item.expected_outcome is ExpectedOutcome.READY
        }
        required_shapes = {
            RepositoryShape.STATIC_WEB,
            RepositoryShape.PYTHON_SERVICE,
            RepositoryShape.WORKSPACE_MONOREPO,
        }
        required = (
            required_shapes.issubset(ready_shapes)
            and any(item.expected_outcome is ExpectedOutcome.HUMAN_REQUIRED for item in self.cases)
            and any(item.malicious_input for item in self.cases)
            and any(item.correction_proof for item in self.cases)
            and any(item.runtime_proof for item in self.cases)
            and any(item.preview_replay_proof for item in self.cases)
            and {MemorySelectionStatus.HIT, MemorySelectionStatus.MISS}.issubset(
                {item.expected_memory_status for item in self.cases}
            )
        )
        if not required:
            raise GeneralizationProofError(GeneralizationFailureCode.DIVERSITY_REQUIREMENT_MISSING)

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "contract_version": WAVE5_GENERALIZATION_CONTRACT_VERSION,
            "suite_id": self.suite_id,
            "version": self.version,
            "cases": [item.as_dict() for item in self.cases],
        }

    def case(self, case_id: str) -> GeneralizationBenchmarkCase:
        for item in self.cases:
            if item.case_id == case_id:
                return item
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)


def load_wave5_generalization_manifest(path: str | Path) -> Wave5GeneralizationManifest:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST) from exc
    if not isinstance(payload, dict) or set(payload) != {"suite_id", "version", "cases"}:
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
    cases = tuple(_parse_case(item) for item in raw_cases)
    return Wave5GeneralizationManifest(payload["suite_id"], payload["version"], cases)


@dataclass(frozen=True, slots=True)
class IntegratedRuntimeProof:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_digest: str
    accepted_lineage_id: str
    accepted_content_digest: str
    build_digest: str
    test_digest: str
    verify_digest: str
    preview_deployment_id: str
    preview_status: str
    publication_replayed: bool
    implementation_duplicate: bool
    recovery_resumed: bool
    protected_evaluation_pass: bool
    operator_review_completed: bool
    autonomous_stop: str
    provider_mutation_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id))
        object.__setattr__(self, "run_id", _uuid(self.run_id))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id))
        object.__setattr__(self, "work_specification_digest", _sha(self.work_specification_digest))
        object.__setattr__(self, "accepted_lineage_id", _lineage(self.accepted_lineage_id))
        object.__setattr__(self, "accepted_content_digest", _sha(self.accepted_content_digest))
        for name in ("build_digest", "test_digest", "verify_digest"):
            object.__setattr__(self, name, _safe_ref(getattr(self, name)))
        object.__setattr__(self, "preview_deployment_id", _safe_ref(self.preview_deployment_id))
        if self.preview_status != "READY" or self.autonomous_stop != "REVIEW":
            raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
        for value in (
            self.publication_replayed,
            self.implementation_duplicate,
            self.recovery_resumed,
            self.protected_evaluation_pass,
            self.operator_review_completed,
        ):
            if not isinstance(value, bool):
                raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
        counts = tuple(self.provider_mutation_counts)
        expected_names = ("branch", "commit", "preview", "pull_request")
        if tuple(name for name, _ in counts) != expected_names or any(count != 1 for _, count in counts):
            raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
        if self.implementation_duplicate or not self.publication_replayed or not self.recovery_resumed:
            raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
        if not self.protected_evaluation_pass or not self.operator_review_completed:
            raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_digest": self.work_specification_digest,
            "accepted_lineage_id": self.accepted_lineage_id,
            "accepted_content_digest": self.accepted_content_digest,
            "build_digest": self.build_digest,
            "test_digest": self.test_digest,
            "verify_digest": self.verify_digest,
            "preview_deployment_id": self.preview_deployment_id,
            "preview_status": self.preview_status,
            "publication_replayed": self.publication_replayed,
            "implementation_duplicate": self.implementation_duplicate,
            "recovery_resumed": self.recovery_resumed,
            "protected_evaluation_pass": self.protected_evaluation_pass,
            "operator_review_completed": self.operator_review_completed,
            "autonomous_stop": self.autonomous_stop,
            "provider_mutation_counts": {name: count for name, count in self.provider_mutation_counts},
            "grants_authority": False,
            "performs_source_mutation": False,
            "performs_provider_action": False,
            "requires_operator_review": True,
        }


def runtime_proof_from_reference_result(
    result: ReferenceAppResult,
    *,
    provider_mutation_counts: Mapping[str, int],
) -> IntegratedRuntimeProof:
    if not isinstance(result, ReferenceAppResult):
        raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
    snapshot = result.evidence_snapshot
    delivery = result.delivery
    if (
        not result.evaluation.protected_pass
        or result.review.run.state != "COMPLETE"
        or snapshot.accepted_lineage_id != result.source_lineage_ref
        or delivery.lineage_id != result.source_lineage_ref
        or delivery.content_digest != snapshot.accepted_content_digest
        or delivery.preview_status != "READY"
        or not delivery.publication_replayed
    ):
        raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
    normalized_counts = {
        "branch": provider_mutation_counts.get("branch"),
        "commit": provider_mutation_counts.get("commit"),
        "preview": provider_mutation_counts.get("preview"),
        "pull_request": provider_mutation_counts.get("pull_request", provider_mutation_counts.get("pr")),
    }
    if any(not isinstance(value, int) or isinstance(value, bool) for value in normalized_counts.values()):
        raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)
    return IntegratedRuntimeProof(
        project_id=snapshot.project_id,
        run_id=snapshot.run_id,
        work_specification_id=snapshot.work_specification_id,
        work_specification_digest=snapshot.work_specification_digest,
        accepted_lineage_id=snapshot.accepted_lineage_id,
        accepted_content_digest=snapshot.accepted_content_digest,
        build_digest=snapshot.build_digest,
        test_digest=snapshot.test_digest,
        verify_digest=snapshot.verify_digest,
        preview_deployment_id=delivery.preview_deployment_id,
        preview_status=delivery.preview_status,
        publication_replayed=delivery.publication_replayed,
        implementation_duplicate=snapshot.implementation_duplicate,
        recovery_resumed=snapshot.recovery_resumed,
        protected_evaluation_pass=result.evaluation.protected_pass,
        operator_review_completed=result.review.run.state == "COMPLETE",
        autonomous_stop="REVIEW",
        provider_mutation_counts=tuple(sorted(normalized_counts.items())),
    )


@dataclass(frozen=True, slots=True)
class IntegratedCorrectionProof:
    project_id: str
    run_id: str
    work_specification_digest: str
    session_id: str
    initial_lineage_id: str
    final_lineage_id: str
    validation_lineages: tuple[str, ...]
    mutation_count: int
    attempt_count: int
    status: str
    fresh_validation_required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id))
        object.__setattr__(self, "run_id", _uuid(self.run_id))
        object.__setattr__(self, "work_specification_digest", _sha(self.work_specification_digest))
        object.__setattr__(self, "session_id", _safe_ref(self.session_id))
        initial = _lineage(self.initial_lineage_id)
        final = _lineage(self.final_lineage_id)
        object.__setattr__(self, "initial_lineage_id", initial)
        object.__setattr__(self, "final_lineage_id", final)
        validation = tuple(_lineage(item) for item in self.validation_lineages)
        object.__setattr__(self, "validation_lineages", validation)
        if (
            initial == final
            or len(validation) < 2
            or validation[0] != initial
            or validation[-1] != final
            or self.mutation_count != 1
            or not isinstance(self.attempt_count, int)
            or self.attempt_count < 1
            or self.status != CorrectionSessionStatus.PASSED.value
            or self.fresh_validation_required is not True
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.CORRECTION_PROOF_INVALID)

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_digest": self.work_specification_digest,
            "session_id": self.session_id,
            "initial_lineage_id": self.initial_lineage_id,
            "final_lineage_id": self.final_lineage_id,
            "validation_lineages": list(self.validation_lineages),
            "mutation_count": self.mutation_count,
            "attempt_count": self.attempt_count,
            "status": self.status,
            "fresh_validation_required": True,
            "acceptance_can_be_weakened": False,
            "grants_authority": False,
            "performs_provider_action": False,
        }


def correction_proof_from_session(
    state: CorrectionSessionState,
    *,
    initial_lineage_id: str,
    validation_lineages: Iterable[str],
    mutation_count: int,
) -> IntegratedCorrectionProof:
    if (
        not isinstance(state, CorrectionSessionState)
        or state.status is not CorrectionSessionStatus.PASSED
        or not state.current_quality.passed
    ):
        raise GeneralizationProofError(GeneralizationFailureCode.CORRECTION_PROOF_INVALID)
    return IntegratedCorrectionProof(
        project_id=state.project_id,
        run_id=state.run_id,
        work_specification_digest=state.work_specification_digest,
        session_id=state.session_id,
        initial_lineage_id=initial_lineage_id,
        final_lineage_id=state.current_lineage_id,
        validation_lineages=tuple(validation_lineages),
        mutation_count=mutation_count,
        attempt_count=state.attempt_count,
        status=state.status.value,
    )


@dataclass(frozen=True, slots=True)
class GeneralizationCaseResult:
    case_id: str
    case_version: str
    manifest_digest: str
    passed: bool
    expected_outcome: ExpectedOutcome
    repository_shape: RepositoryShape
    compatibility_state: CompatibilityState
    compatibility_profile_digest: str
    orchestration_status: OrchestrationStatus
    orchestration_id: str
    orchestration_reason: str | None
    memory_status: MemorySelectionStatus
    memory_selection_id: str
    memory_hit_count: int
    fresh_validation_required: bool
    runtime_proof_digest: str | None
    correction_proof_digest: str | None
    protected_stop: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _case_id(self.case_id))
        if not _SEMVER_RE.fullmatch(self.case_version):
            raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)
        object.__setattr__(self, "manifest_digest", _sha(self.manifest_digest))
        object.__setattr__(self, "compatibility_profile_digest", _sha(self.compatibility_profile_digest))
        object.__setattr__(self, "orchestration_id", _safe_ref(self.orchestration_id))
        object.__setattr__(self, "memory_selection_id", _safe_ref(self.memory_selection_id))
        if self.runtime_proof_digest is not None:
            object.__setattr__(self, "runtime_proof_digest", _sha(self.runtime_proof_digest))
        if self.correction_proof_digest is not None:
            object.__setattr__(self, "correction_proof_digest", _sha(self.correction_proof_digest))
        if not isinstance(self.memory_hit_count, int) or self.memory_hit_count < 0:
            raise GeneralizationProofError(GeneralizationFailureCode.MEMORY_EXPECTATION_MISMATCH)
        if self.fresh_validation_required is not True:
            raise GeneralizationProofError(GeneralizationFailureCode.MEMORY_EXPECTATION_MISMATCH)
        object.__setattr__(self, "protected_stop", _safe_ref(self.protected_stop))

    @property
    def digest(self) -> str:
        return sha256(_canonical_json(self.as_dict())).hexdigest()

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "case_version": self.case_version,
            "manifest_digest": self.manifest_digest,
            "passed": self.passed,
            "expected_outcome": self.expected_outcome.value,
            "repository_shape": self.repository_shape.value,
            "compatibility_state": self.compatibility_state.value,
            "compatibility_profile_digest": self.compatibility_profile_digest,
            "orchestration_status": self.orchestration_status.value,
            "orchestration_id": self.orchestration_id,
            "orchestration_reason": self.orchestration_reason,
            "memory_status": self.memory_status.value,
            "memory_selection_id": self.memory_selection_id,
            "memory_hit_count": self.memory_hit_count,
            "fresh_validation_required": True,
            "runtime_proof_digest": self.runtime_proof_digest,
            "correction_proof_digest": self.correction_proof_digest,
            "protected_stop": self.protected_stop,
            "contains_raw_source": False,
            "contains_prompt": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "contains_private_cross_project_metadata": False,
            "grants_tools": False,
            "grants_service_bindings": False,
            "grants_provider_scope": False,
            "grants_approval": False,
            "performs_source_mutation": False,
            "performs_execution": False,
            "performs_deployment": False,
            "grants_authority": False,
        }


class Wave5GeneralizationHarness:
    def __init__(self, manifest: Wave5GeneralizationManifest) -> None:
        if not isinstance(manifest, Wave5GeneralizationManifest):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        self.manifest = manifest

    def evaluate_case(
        self,
        case_id: str,
        *,
        compatibility: RepositoryCompatibilityProfile,
        orchestration: ObjectiveOrchestrationDecision,
        memory: MemorySelectionResult,
        runtime: IntegratedRuntimeProof | None = None,
        correction: IntegratedCorrectionProof | None = None,
    ) -> GeneralizationCaseResult:
        case = self.manifest.case(case_id)
        if not isinstance(compatibility, RepositoryCompatibilityProfile):
            raise GeneralizationProofError(GeneralizationFailureCode.COMPATIBILITY_EXPECTATION_MISMATCH)
        if compatibility.repository_shape is not case.expected_shape:
            raise GeneralizationProofError(GeneralizationFailureCode.COMPATIBILITY_EXPECTATION_MISMATCH)
        expected_signals = {item.key for item in case.required_signals}
        actual_signals = {(item.kind, item.value) for item in compatibility.signals}
        if not expected_signals.issubset(actual_signals):
            raise GeneralizationProofError(GeneralizationFailureCode.COMPATIBILITY_EXPECTATION_MISMATCH)
        if orchestration.compatibility_profile_digest != compatibility.profile_digest:
            raise GeneralizationProofError(GeneralizationFailureCode.ORCHESTRATION_EXPECTATION_MISMATCH)

        if case.expected_outcome is ExpectedOutcome.READY:
            if compatibility.compatibility_state is not CompatibilityState.SUPPORTED or orchestration.status is not OrchestrationStatus.READY:
                raise GeneralizationProofError(GeneralizationFailureCode.ORCHESTRATION_EXPECTATION_MISMATCH)
            if not set(case.required_capabilities).issubset(orchestration.required_capabilities):
                raise GeneralizationProofError(GeneralizationFailureCode.ORCHESTRATION_EXPECTATION_MISMATCH)
            if len(case.service_requirements) != len(orchestration.service_resolutions):
                raise GeneralizationProofError(GeneralizationFailureCode.ORCHESTRATION_EXPECTATION_MISMATCH)
        else:
            if orchestration.status is not OrchestrationStatus.HUMAN_REQUIRED:
                raise GeneralizationProofError(GeneralizationFailureCode.ORCHESTRATION_EXPECTATION_MISMATCH)
            if runtime is not None or correction is not None:
                raise GeneralizationProofError(GeneralizationFailureCode.ORCHESTRATION_EXPECTATION_MISMATCH)

        if not isinstance(memory, MemorySelectionResult) or memory.fresh_validation_required is not True:
            raise GeneralizationProofError(GeneralizationFailureCode.MEMORY_EXPECTATION_MISMATCH)
        if memory.status is not case.expected_memory_status:
            raise GeneralizationProofError(GeneralizationFailureCode.MEMORY_EXPECTATION_MISMATCH)
        if memory.current_work_specification_digest != orchestration.work_specification_digest:
            raise GeneralizationProofError(GeneralizationFailureCode.MEMORY_EXPECTATION_MISMATCH)
        if memory.as_dict().get("grants_authority") is not False:
            raise GeneralizationProofError(GeneralizationFailureCode.MEMORY_EXPECTATION_MISMATCH)

        if case.runtime_proof:
            if runtime is None:
                raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_REQUIRED)
            self._validate_runtime(orchestration, runtime)
        elif runtime is not None:
            raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)

        if case.correction_proof:
            if correction is None:
                raise GeneralizationProofError(GeneralizationFailureCode.CORRECTION_PROOF_REQUIRED)
            self._validate_correction(orchestration, correction)
        elif correction is not None:
            raise GeneralizationProofError(GeneralizationFailureCode.CORRECTION_PROOF_INVALID)

        if case.preview_replay_proof and (runtime is None or not runtime.publication_replayed):
            raise GeneralizationProofError(GeneralizationFailureCode.PREVIEW_REPLAY_REQUIRED)

        if orchestration.status is OrchestrationStatus.HUMAN_REQUIRED:
            stop = "HUMAN_REQUIRED"
        elif runtime is not None:
            stop = runtime.autonomous_stop
        else:
            stop = "READY"

        return GeneralizationCaseResult(
            case_id=case.case_id,
            case_version=case.version,
            manifest_digest=self.manifest.digest,
            passed=True,
            expected_outcome=case.expected_outcome,
            repository_shape=compatibility.repository_shape,
            compatibility_state=compatibility.compatibility_state,
            compatibility_profile_digest=compatibility.profile_digest,
            orchestration_status=orchestration.status,
            orchestration_id=orchestration.orchestration_id,
            orchestration_reason=orchestration.reason.value if orchestration.reason is not None else None,
            memory_status=memory.status,
            memory_selection_id=memory.selection_id,
            memory_hit_count=memory.eligible_hit_count,
            fresh_validation_required=memory.fresh_validation_required,
            runtime_proof_digest=runtime.digest if runtime is not None else None,
            correction_proof_digest=correction.digest if correction is not None else None,
            protected_stop=stop,
        )

    @staticmethod
    def _validate_runtime(
        orchestration: ObjectiveOrchestrationDecision,
        runtime: IntegratedRuntimeProof,
    ) -> None:
        if (
            runtime.project_id != orchestration.project_id
            or runtime.run_id != orchestration.run_id
            or runtime.work_specification_id != orchestration.work_specification_id
            or runtime.work_specification_digest != orchestration.work_specification_digest
            or runtime.autonomous_stop != "REVIEW"
            or runtime.preview_status != "READY"
            or not runtime.publication_replayed
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.RUNTIME_PROOF_INVALID)

    @staticmethod
    def _validate_correction(
        orchestration: ObjectiveOrchestrationDecision,
        correction: IntegratedCorrectionProof,
    ) -> None:
        if (
            correction.project_id != orchestration.project_id
            or correction.run_id != orchestration.run_id
            or correction.work_specification_digest != orchestration.work_specification_digest
            or correction.status != CorrectionSessionStatus.PASSED.value
            or correction.initial_lineage_id == correction.final_lineage_id
            or correction.fresh_validation_required is not True
        ):
            raise GeneralizationProofError(GeneralizationFailureCode.CORRECTION_PROOF_INVALID)

    def build_report(self, results: Iterable[GeneralizationCaseResult]) -> "Wave5GeneralizationReport":
        items = tuple(results)
        if len(items) != len(self.manifest.cases) or len({item.case_id for item in items}) != len(items):
            raise GeneralizationProofError(GeneralizationFailureCode.REPORT_COVERAGE_MISMATCH)
        expected = {item.case_id for item in self.manifest.cases}
        if {item.case_id for item in items} != expected:
            raise GeneralizationProofError(GeneralizationFailureCode.REPORT_COVERAGE_MISMATCH)
        if any(not item.passed or item.manifest_digest != self.manifest.digest for item in items):
            raise GeneralizationProofError(GeneralizationFailureCode.REPORT_CONTAINS_FAILED_CASE)
        return Wave5GeneralizationReport(
            suite_id=self.manifest.suite_id,
            suite_version=self.manifest.version,
            manifest_digest=self.manifest.digest,
            results=tuple(sorted(items, key=lambda item: item.case_id)),
        )


@dataclass(frozen=True, slots=True)
class Wave5GeneralizationReport:
    suite_id: str
    suite_version: str
    manifest_digest: str
    results: tuple[GeneralizationCaseResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "suite_id", _token(self.suite_id))
        if not _SEMVER_RE.fullmatch(self.suite_version):
            raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
        object.__setattr__(self, "manifest_digest", _sha(self.manifest_digest))
        if not self.results or any(not isinstance(item, GeneralizationCaseResult) for item in self.results):
            raise GeneralizationProofError(GeneralizationFailureCode.REPORT_COVERAGE_MISMATCH)
        ordered = tuple(sorted(self.results, key=lambda item: item.case_id))
        if ordered != self.results:
            object.__setattr__(self, "results", ordered)

    @property
    def proof_digest(self) -> str:
        return sha256(_canonical_json(self._core())).hexdigest()

    def _core(self) -> dict[str, object]:
        return {
            "contract_version": WAVE5_GENERALIZATION_CONTRACT_VERSION,
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "manifest_digest": self.manifest_digest,
            "case_result_digests": [item.digest for item in self.results],
            "case_count": len(self.results),
            "all_passed": all(item.passed for item in self.results),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            **self._core(),
            "proof_digest": self.proof_digest,
            "results": [item.as_dict() for item in self.results],
            "contains_raw_source": False,
            "contains_prompt": False,
            "contains_secret_values": False,
            "contains_secret_handles": False,
            "contains_provider_payload": False,
            "contains_private_cross_project_metadata": False,
            "contains_hidden_reasoning": False,
            "grants_tools": False,
            "grants_service_bindings": False,
            "grants_provider_scope": False,
            "grants_approval": False,
            "performs_source_mutation": False,
            "performs_execution": False,
            "performs_deployment": False,
            "grants_authority": False,
            "review_is_autonomous_ceiling": True,
        }


def public_generalization_field_names() -> tuple[str, ...]:
    contract_types = (
        GeneralizationBenchmarkCase,
        IntegratedRuntimeProof,
        IntegratedCorrectionProof,
        GeneralizationCaseResult,
        Wave5GeneralizationReport,
    )
    return tuple(sorted({field.name for contract_type in contract_types for field in fields(contract_type)}))


def _parse_case(raw: object) -> GeneralizationBenchmarkCase:
    expected_keys = {
        "case_id",
        "version",
        "expected_shape",
        "expected_outcome",
        "objective_kind",
        "required_signals",
        "required_capabilities",
        "service_requirements",
        "requested_memory_kinds",
        "expected_memory_status",
        "runtime_proof",
        "correction_proof",
        "preview_replay_proof",
        "malicious_input",
    }
    if not isinstance(raw, dict) or set(raw) != expected_keys:
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
    try:
        raw_signals = raw["required_signals"]
        raw_services = raw["service_requirements"]
        raw_capabilities = raw["required_capabilities"]
        raw_memory = raw["requested_memory_kinds"]
        if not isinstance(raw_signals, list) or not isinstance(raw_services, list):
            raise TypeError
        if not isinstance(raw_capabilities, list) or not isinstance(raw_memory, list):
            raise TypeError
        signals = tuple(BenchmarkSignal(item["kind"], item["value"]) for item in raw_signals)
        services = tuple(
            BenchmarkServiceRequirement(
                item["service_id"],
                item["interface_version"],
                tuple(item["required_features"]),
            )
            for item in raw_services
        )
        return GeneralizationBenchmarkCase(
            case_id=raw["case_id"],
            version=raw["version"],
            expected_shape=RepositoryShape(raw["expected_shape"]),
            expected_outcome=ExpectedOutcome(raw["expected_outcome"]),
            objective_kind=raw["objective_kind"],
            required_signals=signals,
            required_capabilities=tuple(raw_capabilities),
            service_requirements=services,
            requested_memory_kinds=tuple(MemoryKind(item) for item in raw_memory),
            expected_memory_status=MemorySelectionStatus(raw["expected_memory_status"]),
            runtime_proof=raw["runtime_proof"],
            correction_proof=raw["correction_proof"],
            preview_replay_proof=raw["preview_replay_proof"],
            malicious_input=raw["malicious_input"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST) from exc


def _tokens(values: Iterable[str]) -> tuple[str, ...]:
    values = tuple(values)
    if len(values) > _MAX_ITEMS:
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
    normalized = tuple(_token(item) for item in values)
    if len(set(normalized)) != len(normalized):
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
    return tuple(sorted(normalized))


def _token(value: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise GeneralizationProofError(GeneralizationFailureCode.INVALID_MANIFEST)
    return value


def _case_id(value: str) -> str:
    if not isinstance(value, str) or not _CASE_ID_RE.fullmatch(value):
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)
    return value


def _sha(value: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)
    return value


def _lineage(value: str) -> str:
    if not isinstance(value, str) or not _LINEAGE_RE.fullmatch(value):
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)
    return value


def _uuid(value: str) -> str:
    try:
        canonical = str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH) from exc
    if canonical != value:
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)
    return canonical


def _safe_ref(value: str) -> str:
    if not isinstance(value, str) or not _SAFE_REF_RE.fullmatch(value):
        raise GeneralizationProofError(GeneralizationFailureCode.CASE_IDENTITY_MISMATCH)
    return value


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


__all__ = [
    "BenchmarkServiceRequirement",
    "BenchmarkSignal",
    "ExpectedOutcome",
    "GeneralizationBenchmarkCase",
    "GeneralizationCaseResult",
    "GeneralizationFailureCode",
    "GeneralizationProofError",
    "IntegratedCorrectionProof",
    "IntegratedRuntimeProof",
    "WAVE5_GENERALIZATION_CONTRACT_VERSION",
    "Wave5GeneralizationHarness",
    "Wave5GeneralizationManifest",
    "Wave5GeneralizationReport",
    "correction_proof_from_session",
    "load_wave5_generalization_manifest",
    "public_generalization_field_names",
    "runtime_proof_from_reference_result",
]
