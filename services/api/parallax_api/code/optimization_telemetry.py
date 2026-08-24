from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .optimization_contracts import (
    MAX_DURATION_MS,
    MAX_TELEMETRY,
    DevelopmentPhase,
    OptimizationPolicyError,
    _refs,
    _safe_token,
    _utc,
)


@dataclass(frozen=True, slots=True)
class PhaseObservation:
    project_id: str
    run_id: str
    workstream_id: str
    phase: DevelopmentPhase
    started_at: datetime
    ended_at: datetime
    attempt_number: int
    outcome: str
    evidence_refs: tuple[str, ...] = ()
    critical_path_blocked: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", _safe_token(self.project_id, field="project_id"))
        object.__setattr__(self, "run_id", _safe_token(self.run_id, field="run_id"))
        object.__setattr__(self, "workstream_id", _safe_token(self.workstream_id, field="workstream_id"))
        object.__setattr__(self, "outcome", _safe_token(self.outcome, field="telemetry_outcome"))
        started = _utc(self.started_at)
        ended = _utc(self.ended_at)
        if ended < started:
            raise OptimizationPolicyError("telemetry end cannot precede start")
        object.__setattr__(self, "started_at", started)
        object.__setattr__(self, "ended_at", ended)
        if self.duration_ms > MAX_DURATION_MS:
            raise OptimizationPolicyError("telemetry observation exceeds duration bound")
        if not isinstance(self.attempt_number, int) or isinstance(self.attempt_number, bool) or self.attempt_number < 0:
            raise OptimizationPolicyError("telemetry attempt number must be nonnegative")
        object.__setattr__(self, "evidence_refs", _refs(self.evidence_refs, field="telemetry_evidence"))

    @property
    def duration_ms(self) -> int:
        return int((self.ended_at - self.started_at).total_seconds() * 1000)


@dataclass(frozen=True, slots=True)
class DevelopmentPerformanceSummary:
    validated_outcome_lead_ms: int
    critical_path_blocked_ms: int
    retry_ms: int
    stall_ms: int
    human_wait_ms: int
    integration_wait_ms: int
    phase_ms: tuple[tuple[str, int], ...]


def summarize_telemetry(observations: tuple[PhaseObservation, ...]) -> DevelopmentPerformanceSummary:
    if not observations or len(observations) > MAX_TELEMETRY:
        raise OptimizationPolicyError("telemetry summary requires bounded observations")
    project_ids = {item.project_id for item in observations}
    if len(project_ids) != 1:
        raise OptimizationPolicyError("telemetry cannot aggregate across Projects")
    run_ids = {item.run_id for item in observations}
    if len(run_ids) != 1:
        raise OptimizationPolicyError("telemetry cannot aggregate across Engineering Runs")
    start = min(item.started_at for item in observations)
    end = max(item.ended_at for item in observations)
    totals = {phase: 0 for phase in DevelopmentPhase}
    blocked = 0
    for item in observations:
        totals[item.phase] += item.duration_ms
        if item.critical_path_blocked:
            blocked += item.duration_ms
    return DevelopmentPerformanceSummary(
        validated_outcome_lead_ms=int((end - start).total_seconds() * 1000),
        critical_path_blocked_ms=blocked,
        retry_ms=totals[DevelopmentPhase.RETRY],
        stall_ms=totals[DevelopmentPhase.STALL],
        human_wait_ms=totals[DevelopmentPhase.HUMAN_WAIT],
        integration_wait_ms=totals[DevelopmentPhase.INTEGRATION],
        phase_ms=tuple((phase.value, totals[phase]) for phase in DevelopmentPhase),
    )
