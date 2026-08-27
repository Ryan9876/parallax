from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Iterable
from uuid import UUID

from parallax_api.code.agent_team_orchestration import TeamPlan
from parallax_api.code.optimization_controller import (
    CompetitionCandidate,
    CompetitionDecisionRecord,
    CompetitionDisposition,
    RoutingDecisionRecord,
    RoutingDisposition,
)
from parallax_api.code.source_delivery_composition import VerifiedDeliveryResult
from parallax_api.evaluation.agent_judgment import EvaluationOutcome, EvaluationRecord


WAVE6_AGENTIC_REFERENCE_VERSION = 1
_MAX_ACCEPTANCE_IDS = 128
_MAX_REF_BYTES = 192
_MAX_BASELINE_CLASS_BYTES = 64
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_AC_RE = re.compile(r"^AC-[0-9]{2,3}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,95}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,191}$")
_SENSITIVE_RE = re.compile(
    r"(?:authorization\s*:|bearer\s+|api[_ -]?key|access[_ -]?token|password\s*=|"
    r"secret\s*=|-----BEGIN [A-Z ]+PRIVATE KEY-----)",
    re.IGNORECASE,
)


class AgenticReferenceError(ValueError):
    """Fail-closed Wave 6 integrated-reference proof failure."""


class TeamClass(StrEnum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"
    EITHER = "EITHER"


class AutonomousCeiling(StrEnum):
    REVIEW = "REVIEW"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class ReferenceAdmissionReason(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CASE_MISMATCH = "CASE_MISMATCH"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    COMPETING_PROOF = "COMPETING_PROOF"


@dataclass(frozen=True, slots=True)
class AgenticReferenceCase:
    case_id: str
    version: str
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]
    orchestration_policy_digest: str
    evaluation_policy_digest: str
    routing_policy_digest: str
    competition_policy_digest: str
    expected_team_class: TeamClass
    expected_terminal: AutonomousCeiling
    require_preview: bool = True
    require_replay: bool = False
    require_recovery: bool = False
    baseline_class: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _token(self.case_id, "case_id"))
        object.__setattr__(self, "version", _version(self.version, "version"))
        for field in ("project_id", "run_id", "work_specification_id"):
            object.__setattr__(self, field, _uuid(getattr(self, field), field))
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise AgenticReferenceError("work_specification_revision must be >= 1")
        for field in (
            "work_specification_digest",
            "orchestration_policy_digest",
            "evaluation_policy_digest",
            "routing_policy_digest",
            "competition_policy_digest",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field))
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))
        try:
            team_class = self.expected_team_class if isinstance(self.expected_team_class, TeamClass) else TeamClass(self.expected_team_class)
            terminal = self.expected_terminal if isinstance(self.expected_terminal, AutonomousCeiling) else AutonomousCeiling(self.expected_terminal)
        except (TypeError, ValueError) as exc:
            raise AgenticReferenceError("invalid reference-case policy class") from exc
        object.__setattr__(self, "expected_team_class", team_class)
        object.__setattr__(self, "expected_terminal", terminal)
        for field in ("require_preview", "require_replay", "require_recovery"):
            if not isinstance(getattr(self, field), bool):
                raise AgenticReferenceError(f"{field} must be bool")
        if self.require_replay and not self.require_preview:
            raise AgenticReferenceError("replay proof requires Preview composition")
        if self.baseline_class is not None:
            baseline = _token(self.baseline_class, "baseline_class")
            if len(baseline.encode("utf-8")) > _MAX_BASELINE_CLASS_BYTES:
                raise AgenticReferenceError("baseline_class exceeds protected bound")
            object.__setattr__(self, "baseline_class", baseline)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "reference_version": WAVE6_AGENTIC_REFERENCE_VERSION,
            "case_id": self.case_id,
            "version": self.version,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
            "orchestration_policy_digest": self.orchestration_policy_digest,
            "evaluation_policy_digest": self.evaluation_policy_digest,
            "routing_policy_digest": self.routing_policy_digest,
            "competition_policy_digest": self.competition_policy_digest,
            "expected_team_class": self.expected_team_class.value,
            "expected_terminal": self.expected_terminal.value,
            "require_preview": self.require_preview,
            "require_replay": self.require_replay,
            "require_recovery": self.require_recovery,
            "baseline_class": self.baseline_class,
        }


@dataclass(frozen=True, slots=True)
class ProtectedExecutionEvidence:
    accepted_content_digest: str
    build_digest: str
    test_digest: str
    verify_digest: str

    def __post_init__(self) -> None:
        for field in ("accepted_content_digest", "build_digest", "test_digest", "verify_digest"):
            object.__setattr__(self, field, _sha(getattr(self, field), field))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "accepted_content_digest": self.accepted_content_digest,
            "build_digest": self.build_digest,
            "test_digest": self.test_digest,
            "verify_digest": self.verify_digest,
            "deterministic_validation_authoritative": True,
            "grants_authority": False,
        }


@dataclass(frozen=True, slots=True)
class PreviewEvidence:
    project_id: str
    run_id: str
    lineage_id: str
    content_digest: str
    deployment_id: str
    status: str
    safe_url: str | None
    provider_action_digest: str
    replayed: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        if not isinstance(self.lineage_id, str) or not re.fullmatch(r"src:[0-9a-f]{64}", self.lineage_id):
            raise AgenticReferenceError("lineage_id must be protected source-lineage identity")
        object.__setattr__(self, "content_digest", _sha(self.content_digest, "content_digest"))
        object.__setattr__(self, "deployment_id", _reference(self.deployment_id, "deployment_id"))
        if self.status != "READY":
            raise AgenticReferenceError("reference Preview must be READY")
        if self.safe_url is not None:
            if not isinstance(self.safe_url, str) or len(self.safe_url.encode("utf-8")) > 512:
                raise AgenticReferenceError("Preview URL exceeds safe bound")
            if _SENSITIVE_RE.search(self.safe_url):
                raise AgenticReferenceError("Preview URL contains sensitive material")
        object.__setattr__(self, "provider_action_digest", _sha(self.provider_action_digest, "provider_action_digest"))
        if not isinstance(self.replayed, bool):
            raise AgenticReferenceError("replayed must be bool")

    @classmethod
    def from_delivery(cls, delivery: VerifiedDeliveryResult) -> "PreviewEvidence":
        if not isinstance(delivery, VerifiedDeliveryResult):
            raise AgenticReferenceError("Preview evidence requires protected VerifiedDeliveryResult")
        action_records = [item.to_record() for item in delivery.actions]
        action_digest = _digest(action_records)
        return cls(
            project_id=delivery.project_id,
            run_id=delivery.run_id,
            lineage_id=delivery.lineage_id,
            content_digest=delivery.content_digest,
            deployment_id=delivery.preview_deployment_id,
            status=delivery.preview_status,
            safe_url=delivery.preview_url,
            provider_action_digest=action_digest,
            replayed=delivery.replayed,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "lineage_id": self.lineage_id,
            "content_digest": self.content_digest,
            "deployment_id": self.deployment_id,
            "status": self.status,
            "safe_url": self.safe_url,
            "provider_action_digest": self.provider_action_digest,
            "replayed": self.replayed,
            "production_deployment": False,
            "accepts_source_lineage": False,
            "completes_review": False,
        }


@dataclass(frozen=True, slots=True)
class ReplayRecoveryEvidence:
    process_recreated: bool
    recovery_or_reassignment_observed: bool
    generation_advanced: bool
    accepted_source_mutations: int
    preview_publications: int

    def __post_init__(self) -> None:
        for field in ("process_recreated", "recovery_or_reassignment_observed", "generation_advanced"):
            if not isinstance(getattr(self, field), bool):
                raise AgenticReferenceError(f"{field} must be bool")
        for field in ("accepted_source_mutations", "preview_publications"):
            value = getattr(self, field)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 1:
                raise AgenticReferenceError(f"{field} must prove zero-or-one mutation")

    def as_dict(self) -> dict[str, object]:
        return {
            "process_recreated": self.process_recreated,
            "recovery_or_reassignment_observed": self.recovery_or_reassignment_observed,
            "generation_advanced": self.generation_advanced,
            "accepted_source_mutations": self.accepted_source_mutations,
            "preview_publications": self.preview_publications,
            "duplicate_mutation": False,
            "duplicate_publication": False,
        }


@dataclass(frozen=True, slots=True)
class MeasuredDevelopmentOutcome:
    evidence_digest: str
    completion_reliability: float | None
    operator_interventions: int | None
    quality: float | None
    cost: float | None
    elapsed_ms: float | None
    correctness_preserved: bool = True
    safety_preserved: bool = True
    privacy_preserved: bool = True
    governance_preserved: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_digest", _sha(self.evidence_digest, "evidence_digest"))
        for field in ("completion_reliability", "quality"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _unit(value, field))
        if self.operator_interventions is not None:
            if (
                not isinstance(self.operator_interventions, int)
                or isinstance(self.operator_interventions, bool)
                or self.operator_interventions < 0
            ):
                raise AgenticReferenceError("operator_interventions must be non-negative or unknown")
        for field in ("cost", "elapsed_ms"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _nonnegative(value, field))
        for field in ("correctness_preserved", "safety_preserved", "privacy_preserved", "governance_preserved"):
            if not isinstance(getattr(self, field), bool):
                raise AgenticReferenceError(f"{field} must be bool")

    def as_dict(self) -> dict[str, object]:
        return {
            "evidence_digest": self.evidence_digest,
            "completion_reliability": self.completion_reliability,
            "operator_interventions": self.operator_interventions,
            "quality": self.quality,
            "cost": self.cost,
            "elapsed_ms": self.elapsed_ms,
            "correctness_preserved": self.correctness_preserved,
            "safety_preserved": self.safety_preserved,
            "privacy_preserved": self.privacy_preserved,
            "governance_preserved": self.governance_preserved,
        }


@dataclass(frozen=True, slots=True)
class BaselineComparison:
    baseline_class: str
    baseline: MeasuredDevelopmentOutcome
    challenger: MeasuredDevelopmentOutcome
    comparable_dimensions: tuple[str, ...]
    improved_dimensions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "baseline_class", _token(self.baseline_class, "baseline_class"))
        if not isinstance(self.baseline, MeasuredDevelopmentOutcome) or not isinstance(self.challenger, MeasuredDevelopmentOutcome):
            raise AgenticReferenceError("comparison requires measured outcomes")
        comparable = tuple(self.comparable_dimensions)
        improved = tuple(self.improved_dimensions)
        if not comparable or not set(improved) <= set(comparable):
            raise AgenticReferenceError("comparison dimensions are inconsistent")
        if not improved:
            raise AgenticReferenceError("Wave 6 comparison requires a measured improvement")
        protected = (
            self.challenger.correctness_preserved,
            self.challenger.safety_preserved,
            self.challenger.privacy_preserved,
            self.challenger.governance_preserved,
        )
        if not all(protected):
            raise AgenticReferenceError("measured improvement cannot regress protected outcomes")

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "baseline_class": self.baseline_class,
            "baseline": self.baseline.as_dict(),
            "challenger": self.challenger.as_dict(),
            "comparable_dimensions": list(self.comparable_dimensions),
            "improved_dimensions": list(self.improved_dimensions),
            "unknown_dimensions_remain_unknown": True,
            "protected_outcomes_non_regressed": True,
        }


def compare_measured_outcomes(
    baseline_class: str,
    baseline: MeasuredDevelopmentOutcome,
    challenger: MeasuredDevelopmentOutcome,
) -> BaselineComparison:
    if not isinstance(baseline, MeasuredDevelopmentOutcome) or not isinstance(challenger, MeasuredDevelopmentOutcome):
        raise AgenticReferenceError("comparison requires canonical measured outcomes")
    dimensions = (
        ("completion_reliability", True),
        ("operator_interventions", False),
        ("quality", True),
        ("cost", False),
        ("elapsed_ms", False),
    )
    comparable: list[str] = []
    improved: list[str] = []
    for field, higher_is_better in dimensions:
        left = getattr(baseline, field)
        right = getattr(challenger, field)
        if left is None or right is None:
            continue
        comparable.append(field)
        if (right > left) if higher_is_better else (right < left):
            improved.append(field)
    return BaselineComparison(
        baseline_class=baseline_class,
        baseline=baseline,
        challenger=challenger,
        comparable_dimensions=tuple(comparable),
        improved_dimensions=tuple(improved),
    )


@dataclass(frozen=True, slots=True)
class IntegratedAgenticReferenceProof:
    case: AgenticReferenceCase
    team_plan: TeamPlan
    candidate: CompetitionCandidate
    evaluation: EvaluationRecord
    routing: RoutingDecisionRecord
    competition: CompetitionDecisionRecord
    protected_execution: ProtectedExecutionEvidence
    terminal: AutonomousCeiling
    recovery: ReplayRecoveryEvidence
    preview: PreviewEvidence | None = None
    baseline_comparison: BaselineComparison | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.case, AgenticReferenceCase):
            raise AgenticReferenceError("proof requires canonical reference case")
        if not isinstance(self.team_plan, TeamPlan):
            raise AgenticReferenceError("proof requires accepted S2 TeamPlan")
        if not isinstance(self.candidate, CompetitionCandidate):
            raise AgenticReferenceError("proof requires accepted S5 CompetitionCandidate")
        if not isinstance(self.evaluation, EvaluationRecord):
            raise AgenticReferenceError("proof requires accepted S3 EvaluationRecord")
        if not isinstance(self.routing, RoutingDecisionRecord):
            raise AgenticReferenceError("proof requires accepted S4 RoutingDecisionRecord")
        if not isinstance(self.competition, CompetitionDecisionRecord):
            raise AgenticReferenceError("proof requires accepted S5 CompetitionDecisionRecord")
        if not isinstance(self.protected_execution, ProtectedExecutionEvidence):
            raise AgenticReferenceError("proof requires protected BUILD/TEST/VERIFY evidence")
        if not isinstance(self.recovery, ReplayRecoveryEvidence):
            raise AgenticReferenceError("proof requires replay/recovery evidence")
        try:
            terminal = self.terminal if isinstance(self.terminal, AutonomousCeiling) else AutonomousCeiling(self.terminal)
        except (TypeError, ValueError) as exc:
            raise AgenticReferenceError("invalid autonomous terminal ceiling") from exc
        object.__setattr__(self, "terminal", terminal)
        if terminal is not self.case.expected_terminal:
            raise AgenticReferenceError("reference terminal does not match expected protected ceiling")

        self._validate_orchestration()
        self._validate_candidate_and_evaluation()
        self._validate_routing_and_competition()
        self._validate_delivery_and_replay()
        self._validate_baseline()

    def _validate_orchestration(self) -> None:
        case = self.case
        identity = self.team_plan.identity
        if (
            identity.project_id,
            identity.run_id,
            identity.work_specification_id,
            identity.work_specification_revision,
            identity.work_specification_digest,
            identity.acceptance_ids,
            identity.policy_digest,
        ) != (
            case.project_id,
            case.run_id,
            case.work_specification_id,
            case.work_specification_revision,
            case.work_specification_digest,
            case.acceptance_ids,
            case.orchestration_policy_digest,
        ):
            raise AgenticReferenceError("S2 orchestration identity drift")
        team_size = len(self.team_plan.selected_agent_digests)
        if case.expected_team_class is TeamClass.SINGLE and team_size != 1:
            raise AgenticReferenceError("reference case requires smallest adequate single-agent team")
        if case.expected_team_class is TeamClass.MULTI and team_size < 2:
            raise AgenticReferenceError("reference case requires bounded multi-agent team")

    def _validate_candidate_and_evaluation(self) -> None:
        case = self.case
        binding = self.candidate.binding
        if not _binding_matches_case(binding, case):
            raise AgenticReferenceError("candidate canonical identity drift")
        if self.candidate.assignment_or_team_digest is not None and self.candidate.assignment_or_team_digest != self.team_plan.plan_id:
            raise AgenticReferenceError("candidate is bound to a different team plan")
        if self.candidate.evaluation_record.digest != self.evaluation.digest or self.evaluation.candidate != binding:
            raise AgenticReferenceError("S3 evaluation/candidate identity drift")
        if self.evaluation.policy_digest != case.evaluation_policy_digest:
            raise AgenticReferenceError("S3 evaluation policy drift")
        if self.evaluation.protected_validation_digest != self.candidate.protected_validation.digest:
            raise AgenticReferenceError("S3 protected-validation binding drift")
        if not self.candidate.protected_validation.passed:
            raise AgenticReferenceError("failed deterministic validation cannot enter integrated proof")
        if self.evaluation.evaluator_identity_digest in self.candidate.producer_identity_digests:
            raise AgenticReferenceError("producer self-evaluation cannot satisfy integrated proof")
        if self.terminal is AutonomousCeiling.REVIEW and self.evaluation.outcome is not EvaluationOutcome.SUPPORTED:
            raise AgenticReferenceError("REVIEW proof requires supported independent evaluation")
        if self.protected_execution.accepted_content_digest != binding.candidate_lineage_digest:
            raise AgenticReferenceError("protected BUILD/TEST/VERIFY evidence is not bound to candidate content")

    def _validate_routing_and_competition(self) -> None:
        case = self.case
        routing_context = self.routing.context
        if not _context_matches_case(routing_context, case):
            raise AgenticReferenceError("S4 routing canonical identity drift")
        if routing_context.orchestration_identity_digest != self.team_plan.identity.digest:
            raise AgenticReferenceError("S4 routing is bound to a different orchestration identity")
        if routing_context.evaluation_policy_digest != case.evaluation_policy_digest:
            raise AgenticReferenceError("S4 evaluation-policy identity drift")
        if self.routing.policy_digest != case.routing_policy_digest:
            raise AgenticReferenceError("S4 routing policy drift")
        candidate_eligibility = next(
            (item for item in self.routing.eligibility if item.strategy_id == self.candidate.strategy.strategy_id),
            None,
        )
        if candidate_eligibility is None:
            raise AgenticReferenceError("candidate strategy is absent from S4 routing evidence")
        if self.terminal is AutonomousCeiling.REVIEW and not candidate_eligibility.eligible:
            raise AgenticReferenceError("REVIEW proof cannot use S4-ineligible strategy")
        if self.routing.selected_strategy_id is not None and self.routing.selected_strategy_id != self.candidate.strategy.strategy_id:
            raise AgenticReferenceError("S4 selected strategy does not match integrated candidate")
        if self.terminal is AutonomousCeiling.REVIEW and self.routing.disposition not in {
            RoutingDisposition.SELECTED,
            RoutingDisposition.FALLBACK_SELECTED,
        }:
            raise AgenticReferenceError("REVIEW proof requires an S4 selected strategy")
        routing_outcome = self.candidate.routing_outcome
        if routing_outcome is None or routing_outcome.context_digest != routing_context.digest:
            raise AgenticReferenceError("S5 candidate lacks exact admitted S4 outcome evidence")

        competition_context = self.competition.context
        if not _context_matches_case(competition_context, case):
            raise AgenticReferenceError("S5 competition canonical identity drift")
        if competition_context.orchestration_identity_digest != self.team_plan.identity.digest:
            raise AgenticReferenceError("S5 competition is bound to a different orchestration identity")
        if competition_context.evaluation_policy_digest != case.evaluation_policy_digest:
            raise AgenticReferenceError("S5 evaluation-policy identity drift")
        if competition_context.routing_evidence_digest != routing_context.digest:
            raise AgenticReferenceError("S5 competition is not bound to exact S4 routing context")
        if self.competition.policy_digest != case.competition_policy_digest:
            raise AgenticReferenceError("S5 competition policy drift")
        candidate_competition = next(
            (item for item in self.competition.eligibility if item.candidate_id == self.candidate.candidate_id),
            None,
        )
        if candidate_competition is None:
            raise AgenticReferenceError("candidate is absent from S5 competition evidence")
        if self.terminal is AutonomousCeiling.REVIEW:
            if not candidate_competition.eligible:
                raise AgenticReferenceError("REVIEW proof cannot use S5-ineligible candidate")
            if self.competition.disposition not in {
                CompetitionDisposition.WINNER_SUPPORTED,
                CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT,
            }:
                raise AgenticReferenceError("REVIEW proof requires supported S5 candidate disposition")
            if self.competition.selected_candidate_id != self.candidate.candidate_id:
                raise AgenticReferenceError("S5 selected candidate does not match exact delivered candidate")

    def _validate_delivery_and_replay(self) -> None:
        case = self.case
        if case.require_preview and self.preview is None:
            raise AgenticReferenceError("reference case requires exact-lineage Preview evidence")
        if self.preview is not None:
            if not isinstance(self.preview, PreviewEvidence):
                raise AgenticReferenceError("preview must be protected PreviewEvidence")
            if (self.preview.project_id, self.preview.run_id) != (case.project_id, case.run_id):
                raise AgenticReferenceError("Preview evidence crosses Project/run boundary")
            if self.preview.content_digest != self.protected_execution.accepted_content_digest:
                raise AgenticReferenceError("Preview is not bound to exact protected candidate content")
        if case.require_replay:
            if not self.recovery.process_recreated:
                raise AgenticReferenceError("replay case must cross process recreation")
            if self.recovery.accepted_source_mutations != 1 or self.recovery.preview_publications != 1:
                raise AgenticReferenceError("replay case must prove exactly-once source mutation/publication")
            if self.preview is None or not self.preview.replayed:
                raise AgenticReferenceError("replay case must prove replay-safe Preview publication")
        if case.require_recovery:
            if not self.recovery.recovery_or_reassignment_observed or not self.recovery.generation_advanced:
                raise AgenticReferenceError("recovery case requires admitted bounded recovery/reassignment evidence")

    def _validate_baseline(self) -> None:
        if self.case.baseline_class is None:
            if self.baseline_comparison is not None:
                raise AgenticReferenceError("comparison supplied for non-comparison reference case")
            return
        if self.baseline_comparison is None:
            raise AgenticReferenceError("comparison reference case requires Wave 5 baseline evidence")
        if self.baseline_comparison.baseline_class != self.case.baseline_class:
            raise AgenticReferenceError("baseline comparison class drift")

    @property
    def fingerprint(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "reference_version": WAVE6_AGENTIC_REFERENCE_VERSION,
            "case": self.case.as_dict(),
            "case_digest": self.case.digest,
            "team_plan_id": self.team_plan.plan_id,
            "orchestration_identity_digest": self.team_plan.identity.digest,
            "candidate_id": self.candidate.candidate_id,
            "candidate_digest": self.candidate.digest,
            "candidate_lineage_digest": self.candidate.binding.candidate_lineage_digest,
            "candidate_attempt_id": self.candidate.binding.candidate_attempt_id,
            "protected_execution": self.protected_execution.as_dict(),
            "evaluation_record_digest": self.evaluation.digest,
            "evaluation_outcome": self.evaluation.outcome.value,
            "routing_record_digest": self.routing.digest,
            "routing_disposition": self.routing.disposition.value,
            "competition_record_digest": self.competition.digest,
            "competition_disposition": self.competition.disposition.value,
            "preview": self.preview.as_dict() if self.preview else None,
            "recovery": self.recovery.as_dict(),
            "terminal": self.terminal.value,
            "baseline_comparison": self.baseline_comparison.as_dict() if self.baseline_comparison else None,
            "contains_source_bytes": False,
            "contains_prompts": False,
            "contains_hidden_reasoning": False,
            "contains_credentials": False,
            "contains_provider_payload": False,
            "creates_capability": False,
            "accepts_source_lineage": False,
            "performs_merge": False,
            "performs_production_deployment": False,
            "completes_review": False,
            "resolves_human_required": False,
        }


@dataclass(frozen=True, slots=True)
class ReferenceProofAdmission:
    admitted: bool
    reason: ReferenceAdmissionReason
    proof_fingerprint: str
    duplicate: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.admitted, bool) or not isinstance(self.duplicate, bool):
            raise AgenticReferenceError("admission flags must be bool")
        try:
            reason = self.reason if isinstance(self.reason, ReferenceAdmissionReason) else ReferenceAdmissionReason(self.reason)
        except (TypeError, ValueError) as exc:
            raise AgenticReferenceError("invalid proof admission reason") from exc
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "proof_fingerprint", _sha(self.proof_fingerprint, "proof_fingerprint"))
        if self.duplicate and (self.admitted or reason is not ReferenceAdmissionReason.DUPLICATE):
            raise AgenticReferenceError("duplicate proof cannot be authoritative")

    def as_dict(self) -> dict[str, object]:
        return {
            "admitted": self.admitted,
            "reason": self.reason.value,
            "proof_fingerprint": self.proof_fingerprint,
            "duplicate": self.duplicate,
            "grants_authority": False,
        }


def admit_reference_proof(
    proof: IntegratedAgenticReferenceProof,
    *,
    expected_case: AgenticReferenceCase,
    expected_fingerprint: str | None = None,
    existing: IntegratedAgenticReferenceProof | None = None,
) -> ReferenceProofAdmission:
    if not isinstance(proof, IntegratedAgenticReferenceProof) or not isinstance(expected_case, AgenticReferenceCase):
        raise AgenticReferenceError("canonical proof and expected case are required")
    if proof.case.digest != expected_case.digest:
        return ReferenceProofAdmission(False, ReferenceAdmissionReason.CASE_MISMATCH, proof.fingerprint)
    if expected_fingerprint is not None and proof.fingerprint != _sha(expected_fingerprint, "expected_fingerprint"):
        return ReferenceProofAdmission(False, ReferenceAdmissionReason.FINGERPRINT_MISMATCH, proof.fingerprint)
    if existing is None:
        return ReferenceProofAdmission(True, ReferenceAdmissionReason.ACCEPTED, proof.fingerprint)
    if existing.case.digest != proof.case.digest:
        return ReferenceProofAdmission(False, ReferenceAdmissionReason.COMPETING_PROOF, proof.fingerprint)
    if existing.fingerprint == proof.fingerprint:
        return ReferenceProofAdmission(False, ReferenceAdmissionReason.DUPLICATE, proof.fingerprint, True)
    return ReferenceProofAdmission(False, ReferenceAdmissionReason.COMPETING_PROOF, proof.fingerprint)


def safe_agentic_reference_json(proof: IntegratedAgenticReferenceProof) -> str:
    if not isinstance(proof, IntegratedAgenticReferenceProof):
        raise AgenticReferenceError("safe serializer requires canonical integrated reference proof")
    encoded = json.dumps(proof.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if _SENSITIVE_RE.search(encoded):
        raise AgenticReferenceError("reference proof contains sensitive material")
    return encoded


def _binding_matches_case(binding: object, case: AgenticReferenceCase) -> bool:
    required = (
        "project_id",
        "run_id",
        "work_specification_id",
        "work_specification_revision",
        "work_specification_digest",
        "acceptance_ids",
    )
    if any(not hasattr(binding, field) for field in required):
        return False
    return tuple(getattr(binding, field) for field in required) == (
        case.project_id,
        case.run_id,
        case.work_specification_id,
        case.work_specification_revision,
        case.work_specification_digest,
        case.acceptance_ids,
    )


def _context_matches_case(context: object, case: AgenticReferenceCase) -> bool:
    return _binding_matches_case(context, case)


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise AgenticReferenceError(f"{field} must be canonical UUID")
    try:
        parsed = str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AgenticReferenceError(f"{field} must be canonical UUID") from exc
    if parsed != value:
        raise AgenticReferenceError(f"{field} must use canonical lowercase UUID")
    return parsed


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise AgenticReferenceError(f"{field} must be sha256")
    return value


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise AgenticReferenceError(f"{field} must be bounded token")
    return value


def _version(value: str, field: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise AgenticReferenceError(f"{field} must be bounded version")
    return value


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value.encode("utf-8")) > _MAX_REF_BYTES or not _REF_RE.fullmatch(value):
        raise AgenticReferenceError(f"{field} must be bounded safe reference")
    if _SENSITIVE_RE.search(value):
        raise AgenticReferenceError(f"{field} contains sensitive material")
    return value


def _acceptance_ids(values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(values)
    if (
        not result
        or len(result) > _MAX_ACCEPTANCE_IDS
        or len(set(result)) != len(result)
        or any(not isinstance(value, str) or not _AC_RE.fullmatch(value) for value in result)
    ):
        raise AgenticReferenceError("acceptance_ids must be bounded unique stable IDs")
    return result


def _unit(value: float | int, field: str) -> float:
    result = _nonnegative(value, field)
    if result > 1:
        raise AgenticReferenceError(f"{field} must be between 0 and 1")
    return result


def _nonnegative(value: float | int, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgenticReferenceError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise AgenticReferenceError(f"{field} must be finite and non-negative")
    return result
