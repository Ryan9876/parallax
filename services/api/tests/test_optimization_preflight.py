from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from parallax_api.code.optimization_controller import (
    AcceptanceAssignment,
    DependencyGraph,
    DependencyNode,
    DevelopmentPhase,
    OptimizationNodeKind,
    OptimizationNodeState,
    OptimizationPolicyError,
    PhaseObservation,
    PreflightFindingKind,
    SpecPreflightRequest,
    SpeculativeIntegrationCandidate,
    WorkstreamSizer,
    WorkstreamSizingProposal,
    preflight_spec,
    summarize_telemetry,
)

T0 = datetime(2099, 8, 23, 20, 0, tzinfo=timezone.utc)
LINEAGE_A = "src:" + "a" * 64
LINEAGE_B = "src:" + "b" * 64


def _graph() -> DependencyGraph:
    return DependencyGraph(
        project_id="project:alpha", revision=1,
        nodes=(
            DependencyNode("contract:worker", OptimizationNodeKind.CONTRACT, OptimizationNodeState.PASSED),
            DependencyNode("ws:critical", OptimizationNodeKind.WORKSTREAM, OptimizationNodeState.READY, dependencies=("contract:worker",), acceptance_refs=("AC-01", "AC-02")),
        ),
    )


def test_spec_preflight_blocks_untestable_ambiguous_excess_and_conflicting_work() -> None:
    request = SpecPreflightRequest(
        graph=_graph(), acceptance_criteria=("AC-01", "AC-02"),
        validation_coverage=(("AC-01", "check:unit"),),
        acceptance_ownership=(("AC-01", "ws:critical"), ("AC-02", "ws:one"), ("AC-02", "ws:two")),
        requested_authorities=("source:preview", "provider:production"), allowed_authorities=("source:preview",),
        contradictory_pairs=(("require:immutable", "require:mutable"),), missing_dependencies=("protocol:upstream",),
        architecture_conflicts=("architecture:second-worker-authority",), constitution_conflicts=("constitution:production-autonomy",),
    )
    findings = preflight_spec(request)
    kinds = {item.kind for item in findings}
    assert {
        PreflightFindingKind.UNTESTABLE_ACCEPTANCE,
        PreflightFindingKind.ACCEPTANCE_OWNERSHIP,
        PreflightFindingKind.AUTHORITY_CONFLICT,
        PreflightFindingKind.CONTRADICTION,
        PreflightFindingKind.MISSING_DEPENDENCY,
        PreflightFindingKind.ARCHITECTURE_CONFLICT,
        PreflightFindingKind.CONSTITUTION_CONFLICT,
    }.issubset(kinds)
    assert any(item.subject == "provider:production" for item in findings)


def test_speculative_integration_is_non_authoritative_and_sizing_preserves_acceptance_ownership() -> None:
    candidate = SpeculativeIntegrationCandidate.build(project_id="project:one", lineage_refs=(LINEAGE_A, LINEAGE_B), validation_refs=("test:speculative",))
    assert candidate.authoritative is False and candidate.to_record()["authoritative"] is False
    assert candidate.candidate_digest == SpeculativeIntegrationCandidate.build(project_id="project:one", lineage_refs=(LINEAGE_A, LINEAGE_B), validation_refs=("test:speculative",)).candidate_digest

    valid = WorkstreamSizingProposal((AcceptanceAssignment("AC-01", "ws:a"), AcceptanceAssignment("AC-02", "ws:b")), (("ws:a", "ws:b"),))
    valid.validate(("AC-01", "AC-02"))
    oversized = WorkstreamSizingProposal((
        AcceptanceAssignment("AC-01", "ws:large"), AcceptanceAssignment("AC-02", "ws:large"), AcceptanceAssignment("AC-03", "ws:large")
    ), ())
    balanced = WorkstreamSizer().recommend(oversized, max_acceptance_per_workstream=2)
    balanced.validate(("AC-01", "AC-02", "AC-03"))
    assert {item.workstream_id for item in balanced.assignments} == {"ws:large:part-1", "ws:large:part-2"}
    assert balanced.dependency_edges == (("ws:large:part-1", "ws:large:part-2"),)

    duplicate = WorkstreamSizingProposal((AcceptanceAssignment("AC-01", "ws:a"), AcceptanceAssignment("AC-01", "ws:b")), ())
    with pytest.raises(OptimizationPolicyError, match="duplicates"):
        duplicate.validate(("AC-01",))
    with pytest.raises(OptimizationPolicyError, match="orphans"):
        valid.validate(("AC-01", "AC-02", "AC-03"))


def test_telemetry_is_bounded_project_safe_and_reports_validated_outcome_waits() -> None:
    observations = (
        PhaseObservation("project:one", "run:one", "ws:one", DevelopmentPhase.QUEUE, T0, T0 + timedelta(seconds=2), 0, "complete", critical_path_blocked=True),
        PhaseObservation("project:one", "run:one", "ws:one", DevelopmentPhase.PLANNING, T0 + timedelta(seconds=2), T0 + timedelta(seconds=5), 0, "complete"),
        PhaseObservation("project:one", "run:one", "ws:one", DevelopmentPhase.RETRY, T0 + timedelta(seconds=5), T0 + timedelta(seconds=6), 1, "complete"),
        PhaseObservation("project:one", "run:one", "ws:one", DevelopmentPhase.INTEGRATION, T0 + timedelta(seconds=6), T0 + timedelta(seconds=10), 1, "passed", critical_path_blocked=True),
        PhaseObservation("project:one", "run:one", "ws:one", DevelopmentPhase.HUMAN_WAIT, T0 + timedelta(seconds=10), T0 + timedelta(seconds=12), 1, "complete"),
    )
    summary = summarize_telemetry(observations)
    assert summary.validated_outcome_lead_ms == 12_000
    assert summary.critical_path_blocked_ms == 6_000
    assert summary.retry_ms == 1_000 and summary.integration_wait_ms == 4_000 and summary.human_wait_ms == 2_000
    with pytest.raises(OptimizationPolicyError, match="across Projects"):
        summarize_telemetry((observations[0], replace(observations[1], project_id="project:two")))
    with pytest.raises(OptimizationPolicyError):
        PhaseObservation("project:one", "run:one", "ws:one", DevelopmentPhase.TEST, T0, T0 + timedelta(seconds=1), 0, "failed", evidence_refs=("secret:abcdefgh",))
