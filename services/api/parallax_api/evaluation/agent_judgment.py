from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Any
from uuid import UUID

from parallax_api.code.agent_protocol import AgentIdentity, EvidenceKind


EVALUATION_PROTOCOL_VERSION = 1
_MAX_ACCEPTANCE_IDS = 128
_MAX_DIMENSIONS = 16
_MAX_EVIDENCE_REFS = 64
_MAX_FAILURE_CODES = 32
_MAX_FINDING_BYTES = 640
_MAX_UNCERTAINTIES = 16
_MAX_REFERENCE_BYTES = 192

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ACCEPTANCE_RE = re.compile(r"^AC-[0-9]{2,3}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_REASON_RE = re.compile(r"^[A-Z][A-Z0-9_]{1,79}$")
_SENSITIVE_TEXT_RE = re.compile(
    r"(?:authorization\s*:|bearer\s+[A-Za-z0-9._-]+|api[_ -]?key|access[_ -]?token|"
    r"password\s*=|secret\s*=|token\s*=|-----BEGIN [A-Z ]+PRIVATE KEY-----|https?://)",
    re.IGNORECASE,
)
_AUTHORITY_TEXT_RE = re.compile(
    r"(?:bypass\s+(?:review|validation|policy)|grant\s+(?:shell|network|credential|capability)|"
    r"(?:merge|deploy)\s+(?:now|this|candidate)|change\s+acceptance|ignore\s+(?:test|validator|failure)|"
    r"curl\s+|wget\s+|sudo\s+|rm\s+-rf|execute\s+command)",
    re.IGNORECASE,
)


class AgentJudgmentError(ValueError):
    pass


class EvaluationOutcome(StrEnum):
    SUPPORTED = "SUPPORTED"
    DETERMINISTIC_BLOCKED = "DETERMINISTIC_BLOCKED"
    NOT_INDEPENDENT = "NOT_INDEPENDENT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    POLICY_REJECTED = "POLICY_REJECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class DimensionVerdict(StrEnum):
    SUPPORT = "SUPPORT"
    CONCERN = "CONCERN"
    INSUFFICIENT = "INSUFFICIENT"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class EvaluationAdmissionReason(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    POLICY_MISMATCH = "POLICY_MISMATCH"
    EVALUATOR_MISMATCH = "EVALUATOR_MISMATCH"
    COMPETING_RECORD = "COMPETING_RECORD"


@dataclass(frozen=True, slots=True)
class CandidateBinding:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    candidate_lineage_digest: str
    candidate_revision_id: str
    candidate_attempt_id: str
    producer_identity_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "work_specification_id",
            _uuid(self.work_specification_id, "work_specification_id"),
        )
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise AgentJudgmentError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha(self.work_specification_digest, "work_specification_digest"),
        )
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        object.__setattr__(
            self,
            "candidate_lineage_digest",
            _sha(self.candidate_lineage_digest, "candidate_lineage_digest"),
        )
        object.__setattr__(
            self,
            "candidate_revision_id",
            _reference(self.candidate_revision_id, "candidate_revision_id"),
        )
        object.__setattr__(
            self,
            "candidate_attempt_id",
            _reference(self.candidate_attempt_id, "candidate_attempt_id"),
        )
        object.__setattr__(
            self,
            "producer_identity_digest",
            _sha(self.producer_identity_digest, "producer_identity_digest"),
        )

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "candidate_lineage_digest": self.candidate_lineage_digest,
            "candidate_revision_id": self.candidate_revision_id,
            "candidate_attempt_id": self.candidate_attempt_id,
            "producer_identity_digest": self.producer_identity_digest,
        }


@dataclass(frozen=True, slots=True)
class EvaluationEvidenceReference:
    kind: EvidenceKind
    reference_id: str
    digest: str
    project_id: str | None
    sanitized_generalized: bool = False

    def __post_init__(self) -> None:
        try:
            kind = self.kind if isinstance(self.kind, EvidenceKind) else EvidenceKind(self.kind)
        except (TypeError, ValueError) as exc:
            raise AgentJudgmentError("invalid evidence kind") from exc
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "reference_id", _reference(self.reference_id, "reference_id"))
        object.__setattr__(self, "digest", _sha(self.digest, "evidence digest"))
        if not isinstance(self.sanitized_generalized, bool):
            raise AgentJudgmentError("sanitized_generalized must be bool")
        if self.sanitized_generalized:
            if self.project_id is not None:
                raise AgentJudgmentError("sanitized generalized evidence cannot retain private Project identity")
        else:
            if self.project_id is None:
                raise AgentJudgmentError("Project-private evidence requires project_id")
            object.__setattr__(self, "project_id", _uuid(self.project_id, "evidence project_id"))

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.kind.value, self.reference_id, self.digest)

    def as_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "reference_id": self.reference_id,
            "digest": self.digest,
            "project_id": self.project_id,
            "sanitized_generalized": self.sanitized_generalized,
        }


@dataclass(frozen=True, slots=True)
class ProtectedValidationEvidence:
    candidate: CandidateBinding
    validation_id: str
    passed: bool
    acceptance_ids: tuple[str, ...]
    evidence_refs: tuple[EvaluationEvidenceReference, ...]
    failure_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, CandidateBinding):
            raise AgentJudgmentError("validation candidate must be CandidateBinding")
        object.__setattr__(self, "validation_id", _reference(self.validation_id, "validation_id"))
        if not isinstance(self.passed, bool):
            raise AgentJudgmentError("passed must be bool")
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        refs = _evidence_refs(self.evidence_refs)
        object.__setattr__(self, "evidence_refs", refs)
        failures = tuple(_reason(code) for code in self.failure_codes)
        if len(failures) > _MAX_FAILURE_CODES or len(set(failures)) != len(failures):
            raise AgentJudgmentError("failure_codes must be bounded and unique")
        if self.passed and failures:
            raise AgentJudgmentError("passing validation cannot contain failure_codes")
        if not self.passed and not failures:
            raise AgentJudgmentError("failed validation requires failure_codes")
        object.__setattr__(self, "failure_codes", failures)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_digest": self.candidate.digest,
            "validation_id": self.validation_id,
            "passed": self.passed,
            "acceptance_ids": list(self.acceptance_ids),
            "evidence_refs": [ref.as_dict() for ref in self.evidence_refs],
            "failure_codes": list(self.failure_codes),
            "authoritative_over_evaluator": True,
        }


@dataclass(frozen=True, slots=True)
class DimensionPolicy:
    dimension: str
    required_evidence_kinds: tuple[EvidenceKind, ...]
    minimum_evidence_refs: int = 1
    allow_score: bool = False
    minimum_support_score: float | None = None
    concern_requires_human: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension", _token(self.dimension, "dimension"))
        kinds: list[EvidenceKind] = []
        for item in self.required_evidence_kinds:
            try:
                kind = item if isinstance(item, EvidenceKind) else EvidenceKind(item)
            except (TypeError, ValueError) as exc:
                raise AgentJudgmentError("invalid required evidence kind") from exc
            kinds.append(kind)
        normalized = tuple(sorted(set(kinds), key=lambda item: item.value))
        if not normalized:
            raise AgentJudgmentError("dimension requires at least one evidence kind")
        object.__setattr__(self, "required_evidence_kinds", normalized)
        if (
            not isinstance(self.minimum_evidence_refs, int)
            or isinstance(self.minimum_evidence_refs, bool)
            or not 1 <= self.minimum_evidence_refs <= _MAX_EVIDENCE_REFS
        ):
            raise AgentJudgmentError("minimum_evidence_refs is out of bounds")
        if not isinstance(self.allow_score, bool) or not isinstance(self.concern_requires_human, bool):
            raise AgentJudgmentError("dimension policy flags must be bool")
        if self.minimum_support_score is not None:
            if not self.allow_score:
                raise AgentJudgmentError("minimum_support_score requires allow_score")
            _bounded_unit(self.minimum_support_score, "minimum_support_score")

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "required_evidence_kinds": [item.value for item in self.required_evidence_kinds],
            "minimum_evidence_refs": self.minimum_evidence_refs,
            "allow_score": self.allow_score,
            "minimum_support_score": self.minimum_support_score,
            "concern_requires_human": self.concern_requires_human,
        }


@dataclass(frozen=True, slots=True)
class EvaluatorPolicy:
    policy_id: str
    policy_version: str
    acceptance_ids: tuple[str, ...]
    admitted_evaluator_digests: tuple[str, ...]
    dimensions: tuple[DimensionPolicy, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_id", _token(self.policy_id, "policy_id"))
        object.__setattr__(self, "policy_version", _version(self.policy_version, "policy_version"))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        evaluators = tuple(sorted(_sha(item, "admitted_evaluator_digest") for item in self.admitted_evaluator_digests))
        if not evaluators or len(evaluators) > 32 or len(set(evaluators)) != len(evaluators):
            raise AgentJudgmentError("admitted_evaluator_digests must be bounded and unique")
        object.__setattr__(self, "admitted_evaluator_digests", evaluators)
        dimensions = tuple(self.dimensions)
        if not dimensions or len(dimensions) > _MAX_DIMENSIONS:
            raise AgentJudgmentError("policy dimensions must be bounded and non-empty")
        if any(not isinstance(item, DimensionPolicy) for item in dimensions):
            raise AgentJudgmentError("policy dimensions must be DimensionPolicy values")
        if len({item.dimension for item in dimensions}) != len(dimensions):
            raise AgentJudgmentError("policy dimensions must be unique")
        object.__setattr__(self, "dimensions", tuple(sorted(dimensions, key=lambda item: item.dimension)))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict(include_digest=False))

    def as_dict(self, *, include_digest: bool = True) -> dict[str, object]:
        value: dict[str, object] = {
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "acceptance_ids": list(self.acceptance_ids),
            "admitted_evaluator_digests": list(self.admitted_evaluator_digests),
            "dimensions": [item.as_dict() for item in self.dimensions],
            "server_owned": True,
        }
        if include_digest:
            value["policy_digest"] = self.digest
        return value


@dataclass(frozen=True, slots=True)
class DimensionJudgment:
    dimension: str
    verdict: DimensionVerdict
    finding: str
    evidence_refs: tuple[EvaluationEvidenceReference, ...]
    confidence: float
    score: float | None = None
    uncertainty: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension", _token(self.dimension, "dimension"))
        try:
            verdict = self.verdict if isinstance(self.verdict, DimensionVerdict) else DimensionVerdict(self.verdict)
        except (TypeError, ValueError) as exc:
            raise AgentJudgmentError("invalid dimension verdict") from exc
        object.__setattr__(self, "verdict", verdict)
        object.__setattr__(self, "finding", _safe_finding(self.finding))
        object.__setattr__(self, "evidence_refs", _evidence_refs(self.evidence_refs))
        _bounded_unit(self.confidence, "confidence")
        if self.score is not None:
            _bounded_unit(self.score, "score")
        if self.uncertainty is not None:
            object.__setattr__(self, "uncertainty", _safe_finding(self.uncertainty))
        if verdict is DimensionVerdict.INSUFFICIENT and not self.uncertainty:
            raise AgentJudgmentError("insufficient verdict requires uncertainty")

    def as_dict(self) -> dict[str, object]:
        return {
            "dimension": self.dimension,
            "verdict": self.verdict.value,
            "finding": self.finding,
            "evidence_refs": [ref.as_dict() for ref in self.evidence_refs],
            "confidence": self.confidence,
            "score": self.score,
            "uncertainty": self.uncertainty,
        }


@dataclass(frozen=True, slots=True)
class EvaluatorJudgment:
    candidate_digest: str
    evaluator_identity_digest: str
    policy_digest: str
    dimensions: tuple[DimensionJudgment, ...]
    claimed_outcome: EvaluationOutcome | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_digest", _sha(self.candidate_digest, "candidate_digest"))
        object.__setattr__(
            self,
            "evaluator_identity_digest",
            _sha(self.evaluator_identity_digest, "evaluator_identity_digest"),
        )
        object.__setattr__(self, "policy_digest", _sha(self.policy_digest, "policy_digest"))
        dimensions = tuple(self.dimensions)
        if not dimensions or len(dimensions) > _MAX_DIMENSIONS:
            raise AgentJudgmentError("judgment dimensions must be bounded and non-empty")
        if any(not isinstance(item, DimensionJudgment) for item in dimensions):
            raise AgentJudgmentError("judgment dimensions must be DimensionJudgment values")
        if len({item.dimension for item in dimensions}) != len(dimensions):
            raise AgentJudgmentError("judgment dimensions must be unique")
        object.__setattr__(self, "dimensions", tuple(sorted(dimensions, key=lambda item: item.dimension)))
        if self.claimed_outcome is not None:
            try:
                claimed = (
                    self.claimed_outcome
                    if isinstance(self.claimed_outcome, EvaluationOutcome)
                    else EvaluationOutcome(self.claimed_outcome)
                )
            except (TypeError, ValueError) as exc:
                raise AgentJudgmentError("invalid claimed outcome") from exc
            object.__setattr__(self, "claimed_outcome", claimed)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "candidate_digest": self.candidate_digest,
            "evaluator_identity_digest": self.evaluator_identity_digest,
            "policy_digest": self.policy_digest,
            "dimensions": [item.as_dict() for item in self.dimensions],
            "claimed_outcome": self.claimed_outcome.value if self.claimed_outcome else None,
            "claimed_outcome_is_authoritative": False,
        }


@dataclass(frozen=True, slots=True)
class EvaluationRequest:
    candidate: CandidateBinding
    evaluator: AgentIdentity
    policy: EvaluatorPolicy
    protected_validation: ProtectedValidationEvidence
    qualitative_evidence: tuple[EvaluationEvidenceReference, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, CandidateBinding):
            raise AgentJudgmentError("candidate must be CandidateBinding")
        if not isinstance(self.evaluator, AgentIdentity):
            raise AgentJudgmentError("evaluator must be AgentIdentity")
        if not isinstance(self.policy, EvaluatorPolicy):
            raise AgentJudgmentError("policy must be EvaluatorPolicy")
        if not isinstance(self.protected_validation, ProtectedValidationEvidence):
            raise AgentJudgmentError("protected_validation must be ProtectedValidationEvidence")
        object.__setattr__(self, "qualitative_evidence", _evidence_refs(self.qualitative_evidence))

    @property
    def fingerprint(self) -> str:
        return _digest(
            {
                "protocol_version": EVALUATION_PROTOCOL_VERSION,
                "candidate_digest": self.candidate.digest,
                "producer_identity_digest": self.candidate.producer_identity_digest,
                "evaluator_identity_digest": self.evaluator.digest,
                "policy_digest": self.policy.digest,
                "protected_validation_digest": self.protected_validation.digest,
                "qualitative_evidence": [ref.as_dict() for ref in self.qualitative_evidence],
            }
        )


@dataclass(frozen=True, slots=True)
class EvaluationRecord:
    candidate: CandidateBinding
    evaluator_identity_digest: str
    evaluator_id: str
    evaluator_version: str
    policy_id: str
    policy_version: str
    policy_digest: str
    protected_validation_digest: str
    fingerprint: str
    outcome: EvaluationOutcome
    reason_code: str
    dimensions: tuple[DimensionJudgment, ...]
    evidence_refs: tuple[EvaluationEvidenceReference, ...]
    uncertainties: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.candidate, CandidateBinding):
            raise AgentJudgmentError("record candidate must be CandidateBinding")
        object.__setattr__(
            self,
            "evaluator_identity_digest",
            _sha(self.evaluator_identity_digest, "evaluator_identity_digest"),
        )
        object.__setattr__(self, "evaluator_id", _token(self.evaluator_id, "evaluator_id"))
        object.__setattr__(self, "evaluator_version", _version(self.evaluator_version, "evaluator_version"))
        object.__setattr__(self, "policy_id", _token(self.policy_id, "policy_id"))
        object.__setattr__(self, "policy_version", _version(self.policy_version, "policy_version"))
        object.__setattr__(self, "policy_digest", _sha(self.policy_digest, "policy_digest"))
        object.__setattr__(
            self,
            "protected_validation_digest",
            _sha(self.protected_validation_digest, "protected_validation_digest"),
        )
        object.__setattr__(self, "fingerprint", _sha(self.fingerprint, "fingerprint"))
        try:
            outcome = self.outcome if isinstance(self.outcome, EvaluationOutcome) else EvaluationOutcome(self.outcome)
        except (TypeError, ValueError) as exc:
            raise AgentJudgmentError("invalid evaluation outcome") from exc
        object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        dimensions = tuple(self.dimensions)
        if len(dimensions) > _MAX_DIMENSIONS or any(not isinstance(item, DimensionJudgment) for item in dimensions):
            raise AgentJudgmentError("record dimensions are invalid")
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "evidence_refs", _evidence_refs(self.evidence_refs))
        uncertainties = tuple(_safe_finding(item) for item in self.uncertainties)
        if len(uncertainties) > _MAX_UNCERTAINTIES:
            raise AgentJudgmentError("too many uncertainties")
        object.__setattr__(self, "uncertainties", uncertainties)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "protocol_version": EVALUATION_PROTOCOL_VERSION,
            "candidate": self.candidate.as_dict(),
            "evaluator_identity_digest": self.evaluator_identity_digest,
            "evaluator_id": self.evaluator_id,
            "evaluator_version": self.evaluator_version,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "policy_digest": self.policy_digest,
            "protected_validation_digest": self.protected_validation_digest,
            "fingerprint": self.fingerprint,
            "outcome": self.outcome.value,
            "reason_code": self.reason_code,
            "dimensions": [item.as_dict() for item in self.dimensions],
            "evidence_refs": [ref.as_dict() for ref in self.evidence_refs],
            "uncertainties": list(self.uncertainties),
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "performs_merge": False,
            "performs_deployment": False,
            "completes_review": False,
            "grants_capabilities": False,
            "selects_provider": False,
            "routes_spending": False,
            "chooses_candidate_winner": False,
            "contains_provider_payload": False,
            "contains_credentials": False,
            "contains_hidden_reasoning": False,
        }


@dataclass(frozen=True, slots=True)
class EvaluationAdmissionDecision:
    admitted: bool
    reason: EvaluationAdmissionReason
    record_digest: str
    duplicate: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.admitted, bool) or not isinstance(self.duplicate, bool):
            raise AgentJudgmentError("admission flags must be bool")
        try:
            reason = self.reason if isinstance(self.reason, EvaluationAdmissionReason) else EvaluationAdmissionReason(self.reason)
        except (TypeError, ValueError) as exc:
            raise AgentJudgmentError("invalid admission reason") from exc
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "record_digest", _sha(self.record_digest, "record_digest"))
        if self.duplicate and (self.admitted or reason is not EvaluationAdmissionReason.DUPLICATE):
            raise AgentJudgmentError("duplicate admission cannot be authoritative")

    def as_dict(self) -> dict[str, object]:
        return {
            "admitted": self.admitted,
            "reason": self.reason.value,
            "record_digest": self.record_digest,
            "duplicate": self.duplicate,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
        }


def evaluate_candidate(request: EvaluationRequest, judgment: EvaluatorJudgment) -> EvaluationRecord:
    if not isinstance(request, EvaluationRequest) or not isinstance(judgment, EvaluatorJudgment):
        raise AgentJudgmentError("canonical EvaluationRequest and EvaluatorJudgment are required")

    candidate = request.candidate
    policy = request.policy
    validation = request.protected_validation
    evaluator = request.evaluator
    evidence = _evidence_refs((*validation.evidence_refs, *request.qualitative_evidence))

    if validation.candidate != candidate or validation.acceptance_ids != candidate.acceptance_ids:
        return _record(
            request,
            EvaluationOutcome.DETERMINISTIC_BLOCKED,
            "DETERMINISTIC_IDENTITY_MISMATCH",
            (),
            evidence,
            ("protected validation identity does not match candidate",),
        )
    if not validation.evidence_refs:
        return _record(
            request,
            EvaluationOutcome.DETERMINISTIC_BLOCKED,
            "MISSING_PROTECTED_EVIDENCE",
            (),
            evidence,
            ("required protected validation evidence is missing",),
        )
    if not _evidence_matches_project(validation.evidence_refs, candidate.project_id):
        return _record(
            request,
            EvaluationOutcome.DETERMINISTIC_BLOCKED,
            "PROTECTED_EVIDENCE_SCOPE_MISMATCH",
            (),
            evidence,
            ("protected validation evidence is outside the candidate Project",),
        )
    if not validation.passed:
        return _record(
            request,
            EvaluationOutcome.DETERMINISTIC_BLOCKED,
            "PROTECTED_VALIDATION_FAILED",
            (),
            evidence,
            tuple(validation.failure_codes),
        )

    if policy.acceptance_ids != candidate.acceptance_ids:
        return _record(
            request,
            EvaluationOutcome.POLICY_REJECTED,
            "POLICY_ACCEPTANCE_MISMATCH",
            (),
            evidence,
            ("evaluator policy acceptance contract does not match candidate",),
        )
    if evaluator.digest not in policy.admitted_evaluator_digests:
        return _record(
            request,
            EvaluationOutcome.POLICY_REJECTED,
            "EVALUATOR_NOT_ADMITTED",
            (),
            evidence,
            ("evaluator identity is not admitted by server-owned policy",),
        )
    if evaluator.digest == candidate.producer_identity_digest:
        return _record(
            request,
            EvaluationOutcome.NOT_INDEPENDENT,
            "PRODUCER_EVALUATOR_IDENTITY_MATCH",
            (),
            evidence,
            ("producer self-assessment cannot satisfy independent evaluation",),
        )

    if judgment.candidate_digest != candidate.digest:
        return _record(
            request,
            EvaluationOutcome.INSUFFICIENT_EVIDENCE,
            "JUDGMENT_CANDIDATE_MISMATCH",
            (),
            evidence,
            ("evaluator judgment is bound to another candidate",),
        )
    if judgment.evaluator_identity_digest != evaluator.digest:
        return _record(
            request,
            EvaluationOutcome.NOT_INDEPENDENT,
            "JUDGMENT_EVALUATOR_MISMATCH",
            (),
            evidence,
            ("evaluator judgment identity does not match admitted evaluator",),
        )
    if judgment.policy_digest != policy.digest:
        return _record(
            request,
            EvaluationOutcome.POLICY_REJECTED,
            "JUDGMENT_POLICY_MISMATCH",
            (),
            evidence,
            ("evaluator judgment policy does not match server-owned policy",),
        )
    if not _evidence_matches_project(request.qualitative_evidence, candidate.project_id):
        return _record(
            request,
            EvaluationOutcome.POLICY_REJECTED,
            "CROSS_PROJECT_PRIVATE_EVIDENCE",
            (),
            evidence,
            ("Project-private qualitative evidence cannot cross Project boundary",),
        )

    expected_dimensions = {item.dimension: item for item in policy.dimensions}
    actual_dimensions = {item.dimension: item for item in judgment.dimensions}
    if set(actual_dimensions) != set(expected_dimensions):
        return _record(
            request,
            EvaluationOutcome.INSUFFICIENT_EVIDENCE,
            "DIMENSION_COVERAGE_INCOMPLETE",
            judgment.dimensions,
            evidence,
            ("judgment does not exactly cover the evaluator policy dimensions",),
        )

    available = {item.identity for item in evidence}
    uncertainties: list[str] = []
    policy_rejected = False
    human_required = False
    insufficient = False

    for dimension_name, dimension_policy in expected_dimensions.items():
        dimension = actual_dimensions[dimension_name]
        refs = dimension.evidence_refs
        if not refs or any(ref.identity not in available for ref in refs):
            insufficient = True
            uncertainties.append(f"{dimension_name}: referenced evidence is unavailable")
            continue
        if not _evidence_matches_project(refs, candidate.project_id):
            policy_rejected = True
            uncertainties.append(f"{dimension_name}: evidence scope mismatch")
            continue
        observed_kinds = {ref.kind for ref in refs}
        if not set(dimension_policy.required_evidence_kinds).issubset(observed_kinds):
            insufficient = True
            uncertainties.append(f"{dimension_name}: required evidence kinds are missing")
        if len(refs) < dimension_policy.minimum_evidence_refs:
            insufficient = True
            uncertainties.append(f"{dimension_name}: insufficient evidence references")
        if not dimension_policy.allow_score and dimension.score is not None:
            policy_rejected = True
            uncertainties.append(f"{dimension_name}: policy does not permit a score")
        if dimension_policy.minimum_support_score is not None:
            if dimension.score is None:
                insufficient = True
                uncertainties.append(f"{dimension_name}: required score is missing")
            elif dimension.score < dimension_policy.minimum_support_score:
                policy_rejected = True
                uncertainties.append(f"{dimension_name}: support score is below policy floor")
        if dimension.verdict is DimensionVerdict.INSUFFICIENT:
            insufficient = True
            uncertainties.append(dimension.uncertainty or f"{dimension_name}: insufficient evidence")
        elif dimension.verdict is DimensionVerdict.HUMAN_REQUIRED:
            human_required = True
            uncertainties.append(dimension.uncertainty or f"{dimension_name}: human judgment required")
        elif dimension.verdict is DimensionVerdict.CONCERN:
            if dimension_policy.concern_requires_human:
                human_required = True
                uncertainties.append(f"{dimension_name}: concern requires human review")
            else:
                policy_rejected = True
                uncertainties.append(f"{dimension_name}: concern is not supported by policy")

    if human_required:
        outcome = EvaluationOutcome.HUMAN_REQUIRED
        reason = "QUALITATIVE_HUMAN_BOUNDARY"
    elif policy_rejected:
        outcome = EvaluationOutcome.POLICY_REJECTED
        reason = "QUALITATIVE_POLICY_REJECTED"
    elif insufficient:
        outcome = EvaluationOutcome.INSUFFICIENT_EVIDENCE
        reason = "QUALITATIVE_EVIDENCE_INSUFFICIENT"
    else:
        outcome = EvaluationOutcome.SUPPORTED
        reason = "INDEPENDENT_EVIDENCE_SUPPORTED"

    return _record(request, outcome, reason, judgment.dimensions, evidence, tuple(uncertainties))


def admit_evaluation_record(
    *,
    expected_request: EvaluationRequest,
    record: EvaluationRecord,
    accepted_record_digest: str | None = None,
) -> EvaluationAdmissionDecision:
    if not isinstance(expected_request, EvaluationRequest) or not isinstance(record, EvaluationRecord):
        raise AgentJudgmentError("expected_request and record must be canonical evaluation values")
    if record.fingerprint != expected_request.fingerprint:
        return _admission_reject(record, EvaluationAdmissionReason.FINGERPRINT_MISMATCH)
    if record.candidate != expected_request.candidate:
        return _admission_reject(record, EvaluationAdmissionReason.BINDING_MISMATCH)
    if (
        record.policy_id != expected_request.policy.policy_id
        or record.policy_version != expected_request.policy.policy_version
        or record.policy_digest != expected_request.policy.digest
    ):
        return _admission_reject(record, EvaluationAdmissionReason.POLICY_MISMATCH)
    if record.evaluator_identity_digest != expected_request.evaluator.digest:
        return _admission_reject(record, EvaluationAdmissionReason.EVALUATOR_MISMATCH)
    if accepted_record_digest is not None:
        accepted = _sha(accepted_record_digest, "accepted_record_digest")
        if accepted == record.digest:
            return EvaluationAdmissionDecision(
                admitted=False,
                reason=EvaluationAdmissionReason.DUPLICATE,
                record_digest=record.digest,
                duplicate=True,
            )
        return _admission_reject(record, EvaluationAdmissionReason.COMPETING_RECORD)
    return EvaluationAdmissionDecision(
        admitted=True,
        reason=EvaluationAdmissionReason.ACCEPTED,
        record_digest=record.digest,
    )


def safe_evaluation_json(value: EvaluationRecord | EvaluationAdmissionDecision) -> str:
    if not isinstance(value, (EvaluationRecord, EvaluationAdmissionDecision)):
        raise AgentJudgmentError("safe_evaluation_json requires canonical evaluation evidence")
    return json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _record(
    request: EvaluationRequest,
    outcome: EvaluationOutcome,
    reason_code: str,
    dimensions: tuple[DimensionJudgment, ...],
    evidence: tuple[EvaluationEvidenceReference, ...],
    uncertainties: tuple[str, ...],
) -> EvaluationRecord:
    return EvaluationRecord(
        candidate=request.candidate,
        evaluator_identity_digest=request.evaluator.digest,
        evaluator_id=request.evaluator.agent_id,
        evaluator_version=request.evaluator.agent_version,
        policy_id=request.policy.policy_id,
        policy_version=request.policy.policy_version,
        policy_digest=request.policy.digest,
        protected_validation_digest=request.protected_validation.digest,
        fingerprint=request.fingerprint,
        outcome=outcome,
        reason_code=reason_code,
        dimensions=dimensions,
        evidence_refs=evidence,
        uncertainties=uncertainties,
    )


def _evidence_matches_project(
    refs: tuple[EvaluationEvidenceReference, ...], project_id: str
) -> bool:
    return all(ref.sanitized_generalized or ref.project_id == project_id for ref in refs)


def _evidence_refs(
    values: tuple[EvaluationEvidenceReference, ...] | list[EvaluationEvidenceReference],
) -> tuple[EvaluationEvidenceReference, ...]:
    refs = tuple(values)
    if len(refs) > _MAX_EVIDENCE_REFS or any(
        not isinstance(item, EvaluationEvidenceReference) for item in refs
    ):
        raise AgentJudgmentError("evidence refs must be bounded canonical references")
    if len({item.identity for item in refs}) != len(refs):
        raise AgentJudgmentError("evidence refs must be unique")
    return tuple(sorted(refs, key=lambda item: item.identity))


def _admission_reject(
    record: EvaluationRecord, reason: EvaluationAdmissionReason
) -> EvaluationAdmissionDecision:
    return EvaluationAdmissionDecision(False, reason, record.digest)


def _acceptance_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    items = tuple(values)
    if not items or len(items) > _MAX_ACCEPTANCE_IDS:
        raise AgentJudgmentError("acceptance_ids must be bounded and non-empty")
    if any(not isinstance(item, str) or not _ACCEPTANCE_RE.fullmatch(item) for item in items):
        raise AgentJudgmentError("invalid acceptance ID")
    if len(set(items)) != len(items):
        raise AgentJudgmentError("acceptance_ids must be unique")
    return items


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise AgentJudgmentError(f"{field} must be UUID string")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise AgentJudgmentError(f"{field} must be UUID string") from exc
    return str(parsed)


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA256_RE.fullmatch(value):
        raise AgentJudgmentError(f"{field} must be sha256 hex")
    return value


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise AgentJudgmentError(f"{field} must be bounded token")
    return value


def _version(value: str, field: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise AgentJudgmentError(f"{field} must be bounded version")
    return value


def _reference(value: str, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value.encode("utf-8")) > _MAX_REFERENCE_BYTES
        or not _REFERENCE_RE.fullmatch(value)
        or _SENSITIVE_TEXT_RE.search(value)
    ):
        raise AgentJudgmentError(f"{field} must be bounded safe reference")
    return value


def _reason(value: str) -> str:
    if not isinstance(value, str) or not _REASON_RE.fullmatch(value):
        raise AgentJudgmentError("reason code must be bounded normalized code")
    return value


def _safe_finding(value: str) -> str:
    if not isinstance(value, str):
        raise AgentJudgmentError("finding must be text")
    clean = " ".join(value.strip().split())
    if not clean or len(clean.encode("utf-8")) > _MAX_FINDING_BYTES:
        raise AgentJudgmentError("finding exceeds bounded text contract")
    if _SENSITIVE_TEXT_RE.search(clean) or _AUTHORITY_TEXT_RE.search(clean):
        raise AgentJudgmentError("finding contains secret, URL, command or authority-bearing content")
    return clean


def _bounded_unit(value: float, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentJudgmentError(f"{field} must be numeric")
    if not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise AgentJudgmentError(f"{field} must be between 0 and 1")


def _digest(value: Any) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
