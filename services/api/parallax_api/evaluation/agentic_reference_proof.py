from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import math
import re
from typing import Iterable
from uuid import UUID

from parallax_api.code.agent_team_orchestration import ReassignmentDecision, TeamPlan, TeamSchedule
from parallax_api.code.optimization_controller import (
    CompetitionDecisionRecord,
    CompetitionDisposition,
    RoutingDecisionRecord,
    RoutingDisposition,
)
from parallax_api.code.source_delivery_composition import VerifiedDeliveryResult
from parallax_api.evaluation.agent_judgment import EvaluationOutcome, EvaluationRecord


REFERENCE_PROOF_VERSION = 1
_MAX_ACCEPTANCE_IDS = 128
_MAX_S1_EVIDENCE = 64
_MAX_RECOVERY_RECORDS = 16
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,191}$")
_AC_RE = re.compile(r"^AC-[0-9]{2,3}$")
_LINEAGE_RE = re.compile(r"^src:[0-9a-f]{64}$")


class AgenticReferenceProofError(ValueError):
    """Fail-closed error for malformed or cross-boundary reference evidence."""


class ReferenceDisposition(StrEnum):
    SUPPORTED = "SUPPORTED"
    DETERMINISTIC_BLOCKED = "DETERMINISTIC_BLOCKED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    POLICY_REJECTED = "POLICY_REJECTED"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class ReferenceCeiling(StrEnum):
    REVIEW = "REVIEW"
    HUMAN_REQUIRED = "HUMAN_REQUIRED"


class BenchmarkState(StrEnum):
    OBSERVED = "OBSERVED"
    UNKNOWN = "UNKNOWN"
    INCOMPARABLE = "INCOMPARABLE"


class BenchmarkMetric(StrEnum):
    COMPLETION_RELIABILITY = "completion_reliability"
    OPERATOR_INTERVENTIONS = "operator_interventions"
    QUALITY = "quality"
    ELAPSED_TIME = "elapsed_time"
    COST = "cost"
    RETRIES = "retries"


_METRIC_UNITS = {
    BenchmarkMetric.COMPLETION_RELIABILITY: "ratio",
    BenchmarkMetric.OPERATOR_INTERVENTIONS: "count",
    BenchmarkMetric.QUALITY: "ratio",
    BenchmarkMetric.ELAPSED_TIME: "ms",
    BenchmarkMetric.COST: "usd",
    BenchmarkMetric.RETRIES: "count",
}


@dataclass(frozen=True, slots=True)
class ReferenceIdentity:
    case_id: str
    case_version: str
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _token(self.case_id, "case_id"))
        object.__setattr__(self, "case_version", _version(self.case_version, "case_version"))
        object.__setattr__(self, "project_id", _uuid(self.project_id, "project_id"))
        object.__setattr__(self, "run_id", _uuid(self.run_id, "run_id"))
        object.__setattr__(self, "work_specification_id", _uuid(self.work_specification_id, "work_specification_id"))
        if (
            not isinstance(self.work_specification_revision, int)
            or isinstance(self.work_specification_revision, bool)
            or self.work_specification_revision < 1
        ):
            raise AgenticReferenceProofError("work_specification_revision must be >= 1")
        object.__setattr__(
            self,
            "work_specification_digest",
            _sha(self.work_specification_digest, "work_specification_digest"),
        )
        object.__setattr__(self, "acceptance_ids", _acceptance_ids(self.acceptance_ids))

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "case_version": self.case_version,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "acceptance_ids": list(self.acceptance_ids),
        }


@dataclass(frozen=True, slots=True)
class BenchmarkObservation:
    metric: BenchmarkMetric
    state: BenchmarkState
    value: float | None
    provenance_ref: str
    provenance_digest: str

    def __post_init__(self) -> None:
        try:
            metric = self.metric if isinstance(self.metric, BenchmarkMetric) else BenchmarkMetric(self.metric)
            state = self.state if isinstance(self.state, BenchmarkState) else BenchmarkState(self.state)
        except (TypeError, ValueError) as exc:
            raise AgenticReferenceProofError("invalid benchmark metric/state") from exc
        object.__setattr__(self, "metric", metric)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "provenance_ref", _reference(self.provenance_ref, "provenance_ref"))
        object.__setattr__(self, "provenance_digest", _sha(self.provenance_digest, "provenance_digest"))
        if state is BenchmarkState.OBSERVED:
            if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
                raise AgenticReferenceProofError("observed benchmark requires numeric value")
            value = float(self.value)
            if not math.isfinite(value) or value < 0:
                raise AgenticReferenceProofError("benchmark value must be finite and non-negative")
            if metric in {BenchmarkMetric.COMPLETION_RELIABILITY, BenchmarkMetric.QUALITY} and value > 1:
                raise AgenticReferenceProofError("ratio benchmark must be between 0 and 1")
            object.__setattr__(self, "value", value)
        elif self.value is not None:
            raise AgenticReferenceProofError("unknown/incomparable benchmark cannot carry a value")

    @property
    def unit(self) -> str:
        return _METRIC_UNITS[self.metric]

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "state": self.state.value,
            "value": self.value,
            "unit": self.unit,
            "provenance_ref": self.provenance_ref,
            "provenance_digest": self.provenance_digest,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkPair:
    baseline: BenchmarkObservation
    challenger: BenchmarkObservation

    def __post_init__(self) -> None:
        if not isinstance(self.baseline, BenchmarkObservation) or not isinstance(self.challenger, BenchmarkObservation):
            raise AgenticReferenceProofError("benchmark pair requires canonical observations")
        if self.baseline.metric is not self.challenger.metric:
            raise AgenticReferenceProofError("benchmark pair metric mismatch")

    @property
    def metric(self) -> BenchmarkMetric:
        return self.baseline.metric

    @property
    def comparable(self) -> bool:
        return self.baseline.state is BenchmarkState.OBSERVED and self.challenger.state is BenchmarkState.OBSERVED

    @property
    def materially_improved(self) -> bool:
        if not self.comparable:
            return False
        baseline = float(self.baseline.value)
        challenger = float(self.challenger.value)
        if self.metric in {BenchmarkMetric.COMPLETION_RELIABILITY, BenchmarkMetric.QUALITY}:
            return challenger - baseline >= 0.05
        if self.metric in {BenchmarkMetric.OPERATOR_INTERVENTIONS, BenchmarkMetric.RETRIES}:
            return baseline - challenger >= 1.0
        if baseline == 0:
            return False
        return (baseline - challenger) / baseline >= 0.10

    @property
    def regressed(self) -> bool:
        if not self.comparable:
            return False
        baseline = float(self.baseline.value)
        challenger = float(self.challenger.value)
        if self.metric in {BenchmarkMetric.COMPLETION_RELIABILITY, BenchmarkMetric.QUALITY}:
            return challenger < baseline
        return challenger > baseline

    def as_dict(self) -> dict[str, object]:
        return {
            "metric": self.metric.value,
            "baseline": self.baseline.as_dict(),
            "challenger": self.challenger.as_dict(),
            "comparable": self.comparable,
            "materially_improved": self.materially_improved,
            "regressed": self.regressed,
        }


@dataclass(frozen=True, slots=True)
class Wave5Comparison:
    pairs: tuple[BenchmarkPair, ...]
    correctness_parity: bool
    safety_parity: bool
    privacy_parity: bool
    governance_parity: bool

    def __post_init__(self) -> None:
        pairs = tuple(self.pairs)
        if any(not isinstance(item, BenchmarkPair) for item in pairs):
            raise AgenticReferenceProofError("comparison contains invalid benchmark pair")
        expected = set(BenchmarkMetric)
        actual = {item.metric for item in pairs}
        if actual != expected or len(pairs) != len(expected):
            raise AgenticReferenceProofError("comparison must report every required benchmark metric exactly once")
        object.__setattr__(self, "pairs", tuple(sorted(pairs, key=lambda item: item.metric.value)))
        for field in ("correctness_parity", "safety_parity", "privacy_parity", "governance_parity"):
            if not isinstance(getattr(self, field), bool):
                raise AgenticReferenceProofError(f"{field} must be bool")

    @property
    def guardrails_preserved(self) -> bool:
        return (
            self.correctness_parity
            and self.safety_parity
            and self.privacy_parity
            and self.governance_parity
        )

    @property
    def material_improvement(self) -> bool:
        return self.guardrails_preserved and any(item.materially_improved for item in self.pairs)

    @property
    def digest(self) -> str:
        return _digest(self.as_dict())

    def as_dict(self) -> dict[str, object]:
        return {
            "pairs": [item.as_dict() for item in self.pairs],
            "correctness_parity": self.correctness_parity,
            "safety_parity": self.safety_parity,
            "privacy_parity": self.privacy_parity,
            "governance_parity": self.governance_parity,
            "guardrails_preserved": self.guardrails_preserved,
            "material_improvement": self.material_improvement,
        }


@dataclass(frozen=True, slots=True)
class AgenticReferenceProofResult:
    identity: ReferenceIdentity
    s1_evidence_digests: tuple[str, ...]
    orchestration_identity_digest: str
    team_plan_id: str
    schedule_digest: str
    recovery_evidence_digests: tuple[str, ...]
    evaluation_digest: str
    protected_validation_digest: str
    evaluation_policy_digest: str
    evaluation_outcome: str
    evaluation_reason_code: str
    routing_digest: str
    routing_policy_digest: str
    routing_disposition: str
    routing_reason_code: str
    selected_strategy_id: str | None
    competition_digest: str | None
    competition_policy_digest: str | None
    competition_disposition: str | None
    competition_reason_code: str | None
    selected_candidate_id: str | None
    candidate_lineage_digest: str
    candidate_revision_id: str
    candidate_attempt_id: str
    delivery_digest: str | None
    preview_deployment_id: str | None
    preview_status: str | None
    benchmark_digest: str | None
    benchmark: Wave5Comparison | None
    final_ceiling: ReferenceCeiling
    disposition: ReferenceDisposition
    reason_code: str
    fingerprint: str
    team_summary: tuple[tuple[str, str, int, str | None], ...]
    recovery_summary: tuple[tuple[str, str, int | None], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.identity, ReferenceIdentity):
            raise AgenticReferenceProofError("result requires canonical reference identity")
        object.__setattr__(self, "s1_evidence_digests", _digests(self.s1_evidence_digests, "s1_evidence_digest", _MAX_S1_EVIDENCE))
        for field in (
            "orchestration_identity_digest",
            "team_plan_id",
            "schedule_digest",
            "evaluation_digest",
            "protected_validation_digest",
            "evaluation_policy_digest",
            "routing_digest",
            "routing_policy_digest",
            "candidate_lineage_digest",
            "fingerprint",
        ):
            object.__setattr__(self, field, _sha(getattr(self, field), field))
        object.__setattr__(
            self,
            "recovery_evidence_digests",
            _digests(self.recovery_evidence_digests, "recovery_evidence_digest", _MAX_RECOVERY_RECORDS),
        )
        for field in ("competition_digest", "competition_policy_digest", "delivery_digest", "benchmark_digest"):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, _sha(value, field))
        object.__setattr__(self, "evaluation_outcome", _reference(self.evaluation_outcome, "evaluation_outcome"))
        object.__setattr__(self, "evaluation_reason_code", _reason(self.evaluation_reason_code))
        object.__setattr__(self, "routing_disposition", _reference(self.routing_disposition, "routing_disposition"))
        object.__setattr__(self, "routing_reason_code", _reason(self.routing_reason_code))
        if self.selected_strategy_id is not None:
            object.__setattr__(self, "selected_strategy_id", _token(self.selected_strategy_id, "selected_strategy_id"))
        if self.competition_disposition is not None:
            object.__setattr__(self, "competition_disposition", _reference(self.competition_disposition, "competition_disposition"))
        if self.competition_reason_code is not None:
            object.__setattr__(self, "competition_reason_code", _reason(self.competition_reason_code))
        if self.selected_candidate_id is not None:
            object.__setattr__(self, "selected_candidate_id", _token(self.selected_candidate_id, "selected_candidate_id"))
        object.__setattr__(self, "candidate_revision_id", _reference(self.candidate_revision_id, "candidate_revision_id"))
        object.__setattr__(self, "candidate_attempt_id", _reference(self.candidate_attempt_id, "candidate_attempt_id"))
        if self.benchmark is not None and not isinstance(self.benchmark, Wave5Comparison):
            raise AgenticReferenceProofError("result benchmark must be canonical Wave5Comparison")
        if (self.benchmark is None) != (self.benchmark_digest is None):
            raise AgenticReferenceProofError("benchmark value and digest must be present together")
        if self.benchmark is not None and self.benchmark.digest != self.benchmark_digest:
            raise AgenticReferenceProofError("benchmark digest mismatch")
        try:
            ceiling = self.final_ceiling if isinstance(self.final_ceiling, ReferenceCeiling) else ReferenceCeiling(self.final_ceiling)
            disposition = (
                self.disposition
                if isinstance(self.disposition, ReferenceDisposition)
                else ReferenceDisposition(self.disposition)
            )
        except (TypeError, ValueError) as exc:
            raise AgenticReferenceProofError("invalid result ceiling/disposition") from exc
        object.__setattr__(self, "final_ceiling", ceiling)
        object.__setattr__(self, "disposition", disposition)
        object.__setattr__(self, "reason_code", _reason(self.reason_code))
        if self.preview_deployment_id is not None:
            object.__setattr__(self, "preview_deployment_id", _reference(self.preview_deployment_id, "preview_deployment_id"))
        if self.preview_status is not None:
            object.__setattr__(self, "preview_status", _reference(self.preview_status, "preview_status"))

    @property
    def result_digest(self) -> str:
        return _digest(self.as_dict(include_result_digest=False))

    def as_dict(self, *, include_result_digest: bool = True) -> dict[str, object]:
        data: dict[str, object] = {
            "reference_proof_version": REFERENCE_PROOF_VERSION,
            "identity": self.identity.as_dict(),
            "s1_evidence_digests": list(self.s1_evidence_digests),
            "orchestration_identity_digest": self.orchestration_identity_digest,
            "team_plan_id": self.team_plan_id,
            "schedule_digest": self.schedule_digest,
            "recovery_evidence_digests": list(self.recovery_evidence_digests),
            "evaluation_digest": self.evaluation_digest,
            "protected_validation_digest": self.protected_validation_digest,
            "evaluation_policy_digest": self.evaluation_policy_digest,
            "evaluation_outcome": self.evaluation_outcome,
            "evaluation_reason_code": self.evaluation_reason_code,
            "routing_digest": self.routing_digest,
            "routing_policy_digest": self.routing_policy_digest,
            "routing_disposition": self.routing_disposition,
            "routing_reason_code": self.routing_reason_code,
            "selected_strategy_id": self.selected_strategy_id,
            "competition_digest": self.competition_digest,
            "competition_policy_digest": self.competition_policy_digest,
            "competition_disposition": self.competition_disposition,
            "competition_reason_code": self.competition_reason_code,
            "selected_candidate_id": self.selected_candidate_id,
            "candidate_lineage_digest": self.candidate_lineage_digest,
            "candidate_revision_id": self.candidate_revision_id,
            "candidate_attempt_id": self.candidate_attempt_id,
            "delivery_digest": self.delivery_digest,
            "preview_deployment_id": self.preview_deployment_id,
            "preview_status": self.preview_status,
            "benchmark_digest": self.benchmark_digest,
            "benchmark": self.benchmark.as_dict() if self.benchmark is not None else None,
            "final_ceiling": self.final_ceiling.value,
            "disposition": self.disposition.value,
            "reason_code": self.reason_code,
            "fingerprint": self.fingerprint,
            "team_summary": [
                {
                    "work_unit_id": unit,
                    "disposition": disposition,
                    "generation": generation,
                    "agent_identity_digest": agent_digest,
                }
                for unit, disposition, generation, agent_digest in self.team_summary
            ],
            "recovery_summary": [
                {"disposition": disposition, "reason_code": reason, "generation": generation}
                for disposition, reason, generation in self.recovery_summary
            ],
            "grants_capabilities": False,
            "invokes_provider": False,
            "routes_spending": False,
            "accepts_source_lineage": False,
            "transitions_engineering_run": False,
            "performs_merge": False,
            "performs_production_deployment": False,
            "approves_release": False,
            "completes_review": False,
            "resolves_human_required": False,
            "contains_source_bytes": False,
            "contains_patch": False,
            "contains_credentials": False,
            "contains_provider_payload": False,
            "contains_prompts": False,
            "contains_hidden_reasoning": False,
            "contains_arbitrary_commands": False,
            "contains_arbitrary_urls": False,
        }
        if include_result_digest:
            data["result_digest"] = self.result_digest
        return data


def build_agentic_reference_proof(
    *,
    identity: ReferenceIdentity,
    s1_evidence_digests: tuple[str, ...],
    team_plan: TeamPlan,
    schedule: TeamSchedule,
    evaluation: EvaluationRecord,
    routing: RoutingDecisionRecord,
    competition: CompetitionDecisionRecord | None,
    delivery: VerifiedDeliveryResult | None,
    benchmark: Wave5Comparison | None,
    final_ceiling: ReferenceCeiling = ReferenceCeiling.REVIEW,
    recoveries: tuple[ReassignmentDecision, ...] = (),
) -> AgenticReferenceProofResult:
    """Compose accepted S1-S5/runtime evidence without creating new authority."""

    if not isinstance(identity, ReferenceIdentity):
        raise AgenticReferenceProofError("identity must be ReferenceIdentity")
    s1_digests = _digests(s1_evidence_digests, "s1_evidence_digest", _MAX_S1_EVIDENCE)
    if not s1_digests:
        raise AgenticReferenceProofError("reference proof requires accepted S1 evidence")
    if not isinstance(team_plan, TeamPlan) or not isinstance(schedule, TeamSchedule):
        raise AgenticReferenceProofError("reference proof requires accepted S2 plan and schedule")
    if not isinstance(evaluation, EvaluationRecord):
        raise AgenticReferenceProofError("reference proof requires accepted S3 evaluation record")
    if not isinstance(routing, RoutingDecisionRecord):
        raise AgenticReferenceProofError("reference proof requires accepted S4 routing record")
    if competition is not None and not isinstance(competition, CompetitionDecisionRecord):
        raise AgenticReferenceProofError("competition must be accepted S5 decision record")
    if delivery is not None and not isinstance(delivery, VerifiedDeliveryResult):
        raise AgenticReferenceProofError("delivery must be verified source-delivery evidence")
    if benchmark is not None and not isinstance(benchmark, Wave5Comparison):
        raise AgenticReferenceProofError("benchmark must be canonical Wave 5 comparison")
    try:
        ceiling = final_ceiling if isinstance(final_ceiling, ReferenceCeiling) else ReferenceCeiling(final_ceiling)
    except (TypeError, ValueError) as exc:
        raise AgenticReferenceProofError("final ceiling must be REVIEW or HUMAN_REQUIRED") from exc

    expected = _identity_tuple(identity)
    plan_identity = team_plan.identity
    if _plan_identity_tuple(plan_identity) != expected:
        raise AgenticReferenceProofError("S2 plan identity does not match reference identity")
    if schedule.plan_id != team_plan.plan_id:
        raise AgenticReferenceProofError("S2 schedule belongs to a different team plan")
    assignment_ids = tuple(item.work_unit_id for item in schedule.assignments)
    graph_ids = tuple(item.unit_id for item in team_plan.graph.units)
    if tuple(sorted(assignment_ids)) != tuple(sorted(graph_ids)) or len(set(assignment_ids)) != len(assignment_ids):
        raise AgenticReferenceProofError("S2 schedule does not exactly cover work graph")

    candidate = evaluation.candidate
    if _candidate_identity_tuple(candidate) != expected:
        raise AgenticReferenceProofError("S3 candidate identity does not match reference identity")
    if candidate.producer_identity_digest not in team_plan.selected_agent_digests:
        raise AgenticReferenceProofError("S3 candidate producer was not selected by S2 team plan")

    context = routing.context
    if _routing_identity_tuple(context) != expected:
        raise AgenticReferenceProofError("S4 routing context does not match reference identity")
    if context.orchestration_identity_digest != team_plan.identity.digest:
        raise AgenticReferenceProofError("S4 routing context does not bind exact S2 orchestration identity")
    if context.evaluation_policy_digest != evaluation.policy_digest:
        raise AgenticReferenceProofError("S4 routing context does not bind exact S3 evaluator policy")

    if competition is not None:
        cctx = competition.context
        if _competition_identity_tuple(cctx) != expected:
            raise AgenticReferenceProofError("S5 competition context does not match reference identity")
        if cctx.orchestration_identity_digest != team_plan.identity.digest:
            raise AgenticReferenceProofError("S5 competition context does not bind exact S2 orchestration identity")
        if cctx.evaluation_policy_digest != evaluation.policy_digest:
            raise AgenticReferenceProofError("S5 competition context does not bind exact S3 evaluator policy")
        if cctx.routing_evidence_digest != routing.digest:
            raise AgenticReferenceProofError("S5 competition context does not bind exact S4 routing evidence")
        if competition.selected_candidate_id is not None:
            selected = next(
                (item for item in competition.eligibility if item.candidate_id == competition.selected_candidate_id),
                None,
            )
            if selected is None or not selected.eligible:
                raise AgenticReferenceProofError("S5 selected candidate is not eligible in competition evidence")
            if selected.candidate_lineage_digest != candidate.candidate_lineage_digest:
                raise AgenticReferenceProofError("S5 selected candidate lineage does not match S3 evaluated candidate")

    recovery_values = tuple(recoveries)
    if len(recovery_values) > _MAX_RECOVERY_RECORDS or any(
        not isinstance(item, ReassignmentDecision) for item in recovery_values
    ):
        raise AgenticReferenceProofError("recovery evidence must be bounded accepted S2 decisions")

    delivery_digest = None
    preview_deployment_id = None
    preview_status = None
    if delivery is not None:
        if delivery.project_id != identity.project_id or delivery.run_id != identity.run_id:
            raise AgenticReferenceProofError("Preview delivery belongs to a different Project/run")
        expected_lineage = f"src:{candidate.candidate_lineage_digest}"
        if not _LINEAGE_RE.fullmatch(delivery.lineage_id) or delivery.lineage_id != expected_lineage:
            raise AgenticReferenceProofError("Preview delivery lineage does not match selected candidate")
        if not _SHA_RE.fullmatch(delivery.content_digest):
            raise AgenticReferenceProofError("Preview delivery content digest is invalid")
        delivery_digest = _digest(_safe_delivery_projection(delivery))
        preview_deployment_id = delivery.preview_deployment_id
        preview_status = delivery.preview_status

    disposition, reason = _derive_disposition(
        evaluation=evaluation,
        routing=routing,
        competition=competition,
        delivery=delivery,
        benchmark=benchmark,
        final_ceiling=ceiling,
    )

    schedule_digest = _digest(schedule.as_dict())
    recovery_digests = tuple(_digest(item.as_dict()) for item in recovery_values)
    benchmark_digest = benchmark.digest if benchmark is not None else None
    competition_digest = competition.digest if competition is not None else None
    fingerprint = _digest(
        {
            "reference_proof_version": REFERENCE_PROOF_VERSION,
            "identity_digest": identity.digest,
            "s1_evidence_digests": list(s1_digests),
            "orchestration_identity_digest": team_plan.identity.digest,
            "team_plan_id": team_plan.plan_id,
            "schedule_digest": schedule_digest,
            "recovery_evidence_digests": list(recovery_digests),
            "evaluation_digest": evaluation.digest,
            "routing_digest": routing.digest,
            "competition_digest": competition_digest,
            "candidate_lineage_digest": candidate.candidate_lineage_digest,
            "delivery_digest": delivery_digest,
            "benchmark_digest": benchmark_digest,
            "final_ceiling": ceiling.value,
        }
    )
    team_summary = tuple(
        (
            assignment.work_unit_id,
            assignment.disposition.value,
            assignment.generation,
            assignment.agent_identity_digest,
        )
        for assignment in schedule.assignments
    )
    recovery_summary = tuple(
        (
            item.disposition.value,
            item.reason_code,
            item.assignment.generation if item.assignment is not None else None,
        )
        for item in recovery_values
    )
    return AgenticReferenceProofResult(
        identity=identity,
        s1_evidence_digests=s1_digests,
        orchestration_identity_digest=team_plan.identity.digest,
        team_plan_id=team_plan.plan_id,
        schedule_digest=schedule_digest,
        recovery_evidence_digests=recovery_digests,
        evaluation_digest=evaluation.digest,
        protected_validation_digest=evaluation.protected_validation_digest,
        evaluation_policy_digest=evaluation.policy_digest,
        evaluation_outcome=evaluation.outcome.value,
        evaluation_reason_code=evaluation.reason_code,
        routing_digest=routing.digest,
        routing_policy_digest=routing.policy_digest,
        routing_disposition=routing.disposition.value,
        routing_reason_code=routing.reason_code,
        selected_strategy_id=routing.selected_strategy_id,
        competition_digest=competition_digest,
        competition_policy_digest=competition.policy_digest if competition is not None else None,
        competition_disposition=competition.disposition.value if competition is not None else None,
        competition_reason_code=competition.reason_code if competition is not None else None,
        selected_candidate_id=competition.selected_candidate_id if competition is not None else None,
        candidate_lineage_digest=candidate.candidate_lineage_digest,
        candidate_revision_id=candidate.candidate_revision_id,
        candidate_attempt_id=candidate.candidate_attempt_id,
        delivery_digest=delivery_digest,
        preview_deployment_id=preview_deployment_id,
        preview_status=preview_status,
        benchmark_digest=benchmark_digest,
        benchmark=benchmark,
        final_ceiling=ceiling,
        disposition=disposition,
        reason_code=reason,
        fingerprint=fingerprint,
        team_summary=team_summary,
        recovery_summary=recovery_summary,
    )


def safe_reference_proof_json(value: AgenticReferenceProofResult | Wave5Comparison) -> str:
    if not isinstance(value, (AgenticReferenceProofResult, Wave5Comparison)):
        raise AgenticReferenceProofError("safe serialization requires canonical reference-proof evidence")
    return json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _derive_disposition(
    *,
    evaluation: EvaluationRecord,
    routing: RoutingDecisionRecord,
    competition: CompetitionDecisionRecord | None,
    delivery: VerifiedDeliveryResult | None,
    benchmark: Wave5Comparison | None,
    final_ceiling: ReferenceCeiling,
) -> tuple[ReferenceDisposition, str]:
    if final_ceiling is ReferenceCeiling.HUMAN_REQUIRED:
        return ReferenceDisposition.HUMAN_REQUIRED, "PROTECTED_HUMAN_BOUNDARY"

    if evaluation.outcome is EvaluationOutcome.HUMAN_REQUIRED:
        return ReferenceDisposition.HUMAN_REQUIRED, "S3_HUMAN_REQUIRED"
    if evaluation.outcome is EvaluationOutcome.DETERMINISTIC_BLOCKED:
        return ReferenceDisposition.DETERMINISTIC_BLOCKED, "S3_DETERMINISTIC_BLOCKED"
    if evaluation.outcome is EvaluationOutcome.INSUFFICIENT_EVIDENCE:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "S3_INSUFFICIENT_EVIDENCE"
    if evaluation.outcome in {EvaluationOutcome.NOT_INDEPENDENT, EvaluationOutcome.POLICY_REJECTED}:
        return ReferenceDisposition.POLICY_REJECTED, "S3_POLICY_REJECTED"
    if evaluation.outcome is not EvaluationOutcome.SUPPORTED:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "S3_UNSUPPORTED"

    if routing.disposition is RoutingDisposition.HUMAN_REQUIRED:
        return ReferenceDisposition.HUMAN_REQUIRED, "S4_HUMAN_REQUIRED"
    if routing.disposition is RoutingDisposition.POLICY_REJECTED:
        return ReferenceDisposition.POLICY_REJECTED, "S4_POLICY_REJECTED"
    if routing.disposition not in {RoutingDisposition.SELECTED, RoutingDisposition.FALLBACK_SELECTED}:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "S4_NO_SUPPORTED_ROUTE"

    if competition is None:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "S5_EVIDENCE_REQUIRED"
    if competition.disposition is CompetitionDisposition.HUMAN_REQUIRED:
        return ReferenceDisposition.HUMAN_REQUIRED, "S5_HUMAN_REQUIRED"
    if competition.disposition is CompetitionDisposition.POLICY_REJECTED:
        return ReferenceDisposition.POLICY_REJECTED, "S5_POLICY_REJECTED"
    if competition.disposition not in {
        CompetitionDisposition.WINNER_SUPPORTED,
        CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT,
    }:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "S5_NO_SUPPORTED_CANDIDATE"

    if delivery is None:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "PREVIEW_EVIDENCE_REQUIRED"
    if delivery.preview_status.upper() != "READY":
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "PREVIEW_NOT_READY"
    if benchmark is None:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "WAVE5_COMPARISON_REQUIRED"
    if not benchmark.guardrails_preserved:
        return ReferenceDisposition.POLICY_REJECTED, "BENCHMARK_GUARDRAIL_REGRESSION"
    if not benchmark.material_improvement:
        return ReferenceDisposition.INSUFFICIENT_EVIDENCE, "MATERIAL_IMPROVEMENT_NOT_PROVEN"
    return ReferenceDisposition.SUPPORTED, "INTEGRATED_REFERENCE_PROOF_SUPPORTED"


def _safe_delivery_projection(delivery: VerifiedDeliveryResult) -> dict[str, object]:
    return {
        "project_id": delivery.project_id,
        "run_id": delivery.run_id,
        "repository_identity_digest": delivery.repository_identity_digest,
        "lineage_id": delivery.lineage_id,
        "content_digest": delivery.content_digest,
        "commit_revision": delivery.commit_revision,
        "pull_request_number": delivery.pull_request_number,
        "preview_deployment_id": delivery.preview_deployment_id,
        "preview_status": delivery.preview_status,
        "actions": [
            {
                "provider": item.evidence.provider,
                "action": item.evidence.action,
                "state": item.evidence.state.value,
                "request_id": item.audit.request_id,
                "request_digest": item.audit.request_digest,
                "result_digest": item.audit.result_digest,
                "result_code": item.audit.result_code,
            }
            for item in delivery.actions
        ],
    }


def _identity_tuple(identity: ReferenceIdentity) -> tuple[object, ...]:
    return (
        identity.project_id,
        identity.run_id,
        identity.work_specification_id,
        identity.work_specification_revision,
        identity.work_specification_digest,
        identity.acceptance_ids,
    )


def _plan_identity_tuple(identity: object) -> tuple[object, ...]:
    return (
        identity.project_id,
        identity.run_id,
        identity.work_specification_id,
        identity.work_specification_revision,
        identity.work_specification_digest,
        identity.acceptance_ids,
    )


def _candidate_identity_tuple(candidate: object) -> tuple[object, ...]:
    return (
        candidate.project_id,
        candidate.run_id,
        candidate.work_specification_id,
        candidate.work_specification_revision,
        candidate.work_specification_digest,
        candidate.acceptance_ids,
    )


def _routing_identity_tuple(context: object) -> tuple[object, ...]:
    return (
        context.project_id,
        context.run_id,
        context.work_specification_id,
        context.work_specification_revision,
        context.work_specification_digest,
        context.acceptance_ids,
    )


def _competition_identity_tuple(context: object) -> tuple[object, ...]:
    return (
        context.project_id,
        context.run_id,
        context.work_specification_id,
        context.work_specification_revision,
        context.work_specification_digest,
        context.acceptance_ids,
    )


def _digest(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()


def _sha(value: str, field: str) -> str:
    if not isinstance(value, str) or not _SHA_RE.fullmatch(value):
        raise AgenticReferenceProofError(f"{field} must be sha256")
    return value


def _uuid(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise AgenticReferenceProofError(f"{field} must be canonical UUID")
    try:
        canonical = str(UUID(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise AgenticReferenceProofError(f"{field} must be canonical UUID") from exc
    if canonical != value:
        raise AgenticReferenceProofError(f"{field} must use canonical UUID form")
    return value


def _token(value: str, field: str) -> str:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        raise AgenticReferenceProofError(f"{field} must be bounded token")
    return value


def _version(value: str, field: str) -> str:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise AgenticReferenceProofError(f"{field} must be bounded version")
    return value


def _reference(value: str, field: str) -> str:
    if not isinstance(value, str) or not _REF_RE.fullmatch(value) or "://" in value:
        raise AgenticReferenceProofError(f"{field} must be bounded non-URL reference")
    return value


def _reason(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"^[A-Z][A-Z0-9_]{1,79}$", value):
        raise AgenticReferenceProofError("reason_code must be normalized")
    return value


def _acceptance_ids(values: Iterable[str]) -> tuple[str, ...]:
    result = tuple(values)
    if (
        not result
        or len(result) > _MAX_ACCEPTANCE_IDS
        or len(set(result)) != len(result)
        or any(not isinstance(value, str) or not _AC_RE.fullmatch(value) for value in result)
    ):
        raise AgenticReferenceProofError("acceptance_ids must be bounded unique stable IDs")
    return result


def _digests(values: Iterable[str], field: str, maximum: int) -> tuple[str, ...]:
    result = tuple(_sha(value, field) for value in values)
    if len(result) > maximum or len(set(result)) != len(result):
        raise AgenticReferenceProofError(f"{field} values must be bounded and unique")
    return result
