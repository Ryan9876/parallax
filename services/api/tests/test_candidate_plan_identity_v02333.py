from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from types import SimpleNamespace

import pytest

from parallax_api.code.agent_protocol import AgentIdentity
from parallax_api.code.agent_team_orchestration import (
    AdmittedAgent,
    AdmittedRoster,
    OrchestrationLimits,
    TeamPlan,
    WorkGraph,
    WorkUnit,
    build_team_plan,
    schedule_team_plan,
)
from parallax_api.code.agentic_candidate_recovery import ResilientLiveAgenticControlPlane
from parallax_api.code.agentic_runtime import AgenticControlPlane, AgenticRuntimeError
from parallax_api.code.agentic_runtime_live import LiveAgenticControlPlane
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.code.worker_recovery import WorkerLease
from parallax_api.intelligence.implementation_generation import AcceptanceRequirement, ImplementationGenerationRequest


def _digest(value: str) -> str:
    return sha256(value.encode()).hexdigest()


def _identity(name: str) -> AgentIdentity:
    return AgentIdentity(
        agent_id=name,
        agent_version="1.0.0",
        adapter_id="protected-implementation-generation",
        adapter_version="1.0.0",
        provider_kind="openai",
        declared_work_kinds=("implementation",),
        declared_capabilities=("bounded-source-evidence",),
        model_runtime_label=name,
    )


def _plans() -> tuple[TeamPlan, TeamPlan]:
    entries = tuple(
        AdmittedAgent(
            _identity(name),
            admitted_work_kinds=("implementation",),
            admitted_capabilities=("bounded-source-evidence",),
            selection_priority=priority,
        )
        for priority, name in enumerate(("model-luna", "model-terra"))
    )
    graph = WorkGraph(
        approved_acceptance_ids=("AC-01",),
        units=(WorkUnit(
            unit_id="implementation",
            work_kind="implementation",
            acceptance_ids=("AC-01",),
            required_capabilities=("bounded-source-evidence",),
            coordination_domains=("source",),
        ),),
    )
    limits = OrchestrationLimits(max_team_size=2, max_concurrency=2, max_reassignments_per_work_unit=2, max_replans=3, max_no_progress=3)

    def build(roster: AdmittedRoster) -> TeamPlan:
        decision = build_team_plan(
            project_id="11111111-1111-1111-1111-111111111111",
            run_id="22222222-2222-2222-2222-222222222222",
            work_specification_id="33333333-3333-3333-3333-333333333333",
            work_specification_revision=1,
            work_specification_digest=_digest("spec"),
            graph=graph,
            roster=roster,
            policy_digest=_digest("policy"),
            limits=limits,
        )
        assert decision.plan is not None
        return decision.plan

    canonical = build(AdmittedRoster(entries))
    challenger = build(AdmittedRoster((entries[1],)))
    assert canonical.plan_id != challenger.plan_id
    assert canonical.graph.digest == challenger.graph.digest
    return canonical, challenger


def _request() -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id="33333333-3333-3333-3333-333333333333",
        work_specification_revision=1,
        work_specification_digest=_digest("spec"),
        title="Bound candidate-local producer identity",
        objective="Keep the protected PLAN durable while selecting an alternate producer.",
        constraints=("Do not change authority.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="The bounded change is produced."),),
        source_context=SourceContextSnapshot(files=(), digest=_digest("source-context"), total_bytes=0, excluded_secret_files=0, omitted_bounded_files=0),
    )


def test_candidate_local_plan_compatibility_allows_only_subordinate_producer_selection():
    canonical, challenger = _plans()
    AgenticControlPlane._assert_candidate_plan_compatible(challenger, canonical)
    assert challenger.selected_agent_digests != canonical.selected_agent_digests
    incompatible = replace(challenger, identity=replace(challenger.identity, policy_digest=_digest("different-policy")))
    with pytest.raises(AgenticRuntimeError, match="drifted from canonical durable PLAN"):
        AgenticControlPlane._assert_candidate_plan_compatible(incompatible, canonical)


def test_candidate_local_plan_cannot_introduce_agent_outside_canonical_admission():
    canonical, _ = _plans()
    outsider = AdmittedAgent(_identity("model-outsider"), admitted_work_kinds=("implementation",), admitted_capabilities=("bounded-source-evidence",), selection_priority=0)
    decision = build_team_plan(
        project_id=canonical.identity.project_id,
        run_id=canonical.identity.run_id,
        work_specification_id=canonical.identity.work_specification_id,
        work_specification_revision=canonical.identity.work_specification_revision,
        work_specification_digest=canonical.identity.work_specification_digest,
        graph=canonical.graph,
        roster=AdmittedRoster((outsider,)),
        policy_digest=canonical.identity.policy_digest,
        limits=canonical.limits,
    )
    assert decision.plan is not None
    with pytest.raises(AgenticRuntimeError, match="outside canonical PLAN admission"):
        AgenticControlPlane._assert_candidate_plan_compatible(decision.plan, canonical)


class _DispatchReached(RuntimeError):
    pass


class _ProbeWorkerBridge:
    def __init__(self) -> None:
        self.plan_ids: list[str] = []
        self.evidence_refs: list[tuple[str, ...]] = []
        self.stopped = False

    def acquire(self, *, run_id: str) -> WorkerLease:
        return WorkerLease(execution_id="candidate-plan-probe", run_id=run_id, owner_id="worker:candidate-plan-probe", generation=1, expires_at=datetime.now(timezone.utc))

    def checkpoint(self, lease, *, plan, work_unit_id, source_lineage_ref, step, evidence_refs, state=None):
        self.plan_ids.append(plan.plan_id)
        self.evidence_refs.append(evidence_refs)
        if step == "AGENT_DISPATCH":
            raise _DispatchReached("captured canonical checkpoint")
        return lease

    def stop_bounded(self, *, run_id: str) -> None:
        self.stopped = True


class _Service:
    def __init__(self, run) -> None:
        self.run = run

    def get(self, run_id: str):
        assert run_id == self.run.id
        return self.run


class _Allocator:
    def __init__(self, run) -> None:
        self.run = run

    def current_lineage(self, identity):
        assert identity.project_id == self.run.project_id
        assert identity.run_id == self.run.id
        return SimpleNamespace(project_id=self.run.project_id, run_id=self.run.id, lineage_id="lineage-primary", content_digest=_digest("accepted-source"))


@pytest.mark.parametrize("control_type", (LiveAgenticControlPlane, ResilientLiveAgenticControlPlane))
def test_repair_dispatch_uses_candidate_identity_but_canonical_worker_plan_ref(control_type):
    canonical, challenger = _plans()
    generation = {"implementation": 1}
    primary_assignment = schedule_team_plan(canonical, generation_by_work_unit=generation).ready[0]
    repair_assignment = schedule_team_plan(challenger, generation_by_work_unit=generation).ready[0]
    assert primary_assignment.attempt_id != repair_assignment.attempt_id
    assert primary_assignment.operation_id != repair_assignment.operation_id
    assert primary_assignment.request_id != repair_assignment.request_id

    run = SimpleNamespace(id=canonical.identity.run_id, project_id=canonical.identity.project_id)
    control = object.__new__(control_type)
    control.service = _Service(run)
    control.allocator = _Allocator(run)
    probe = _ProbeWorkerBridge()
    control.worker_bridge = probe

    with pytest.raises(_DispatchReached):
        control._proposal_for_plan(challenger, _request(), proposal_validator=lambda proposal: True, alternative_round=2, canonical_plan=canonical)

    assert probe.stopped is True
    assert probe.plan_ids == [canonical.plan_id]
    assert any(f"assignment:{repair_assignment.attempt_id}" in refs for refs in probe.evidence_refs)


class _ProposalThreadStop(RuntimeError):
    pass


class _ProposalThreadProbe(AgenticControlPlane):
    def _proposal_for_plan(self, plan, request, *, proposal_validator, alternative_round, canonical_plan=None):
        self.threaded = (plan, canonical_plan, alternative_round)
        raise _ProposalThreadStop("captured")


def test_make_candidate_threads_primary_plan_as_canonical_durable_plan(tmp_path):
    canonical, challenger = _plans()
    control = object.__new__(_ProposalThreadProbe)
    control.threaded = None
    with pytest.raises(_ProposalThreadStop):
        control._make_candidate(
            run=SimpleNamespace(),
            primary_plan=canonical,
            plan=challenger,
            request=_request(),
            base_workspace=tmp_path,
            validation_profile=SimpleNamespace(),
            proposal_validator=lambda proposal: True,
            operation_key="candidate-plan-thread",
            candidate_id="candidate-repair",
            alternative_round=2,
        )
    assert control.threaded == (challenger, canonical, 2)
