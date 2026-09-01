from __future__ import annotations

import argparse
from pathlib import Path
import re


def _replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one replacement, found {count}")
    return text.replace(old, new, 1)


def apply_runtime() -> None:
    runtime_path = Path("services/api/parallax_api/code/agentic_runtime.py")
    runtime = runtime_path.read_text(encoding="utf-8")
    runtime = _replace_once(
        runtime,
        """    def _proposal_for_plan(\n        self,\n        plan: TeamPlan,\n        request: ImplementationGenerationRequest,\n        *,\n        proposal_validator: Callable[[ImplementationProposal], bool],\n        alternative_round: int,\n    ) -> tuple[\n""",
        """    @staticmethod\n    def _assert_candidate_plan_compatible(\n        candidate_plan: TeamPlan,\n        canonical_plan: TeamPlan,\n    ) -> None:\n        if not isinstance(candidate_plan, TeamPlan) or not isinstance(canonical_plan, TeamPlan):\n            raise AgenticRuntimeError(\"candidate PLAN compatibility requires canonical TeamPlan values\")\n        candidate = candidate_plan.identity\n        canonical = canonical_plan.identity\n        protected_fields = (\n            \"project_id\",\n            \"run_id\",\n            \"work_specification_id\",\n            \"work_specification_revision\",\n            \"work_specification_digest\",\n            \"acceptance_ids\",\n            \"agent_protocol_version\",\n            \"policy_digest\",\n            \"work_graph_digest\",\n        )\n        if any(getattr(candidate, field) != getattr(canonical, field) for field in protected_fields):\n            raise AgenticRuntimeError(\"candidate-local plan drifted from canonical durable PLAN\")\n        if candidate_plan.graph.digest != canonical_plan.graph.digest:\n            raise AgenticRuntimeError(\"candidate-local work graph drifted from canonical durable PLAN\")\n        if candidate_plan.limits.as_dict() != canonical_plan.limits.as_dict():\n            raise AgenticRuntimeError(\"candidate-local orchestration limits drifted from canonical durable PLAN\")\n        canonical_roster = {entry.identity_digest for entry in canonical_plan.roster.entries}\n        candidate_roster = {entry.identity_digest for entry in candidate_plan.roster.entries}\n        if not candidate_roster <= canonical_roster:\n            raise AgenticRuntimeError(\"candidate-local plan introduced an agent outside canonical PLAN admission\")\n        if not set(candidate_plan.selected_agent_digests) <= canonical_roster:\n            raise AgenticRuntimeError(\"candidate-local selected producer is outside canonical PLAN admission\")\n        for unit_plan in candidate_plan.unit_plans:\n            canonical_plan.graph.get(unit_plan.work_unit_id)\n            if not set(unit_plan.eligible_agent_digests) <= canonical_roster:\n                raise AgenticRuntimeError(\"candidate-local work-unit eligibility exceeded canonical PLAN admission\")\n\n    def _proposal_for_plan(\n        self,\n        plan: TeamPlan,\n        request: ImplementationGenerationRequest,\n        *,\n        proposal_validator: Callable[[ImplementationProposal], bool],\n        alternative_round: int,\n        canonical_plan: TeamPlan | None = None,\n    ) -> tuple[\n""",
        label="agentic_runtime proposal signature",
    )
    runtime = _replace_once(
        runtime,
        """        tuple[str, ...],\n        tuple[str, ...],\n    ]:\n        completed: set[str] = set()\n""",
        """        tuple[str, ...],\n        tuple[str, ...],\n    ]:\n        durable_plan = canonical_plan or plan\n        self._assert_candidate_plan_compatible(plan, durable_plan)\n        completed: set[str] = set()\n""",
        label="agentic_runtime proposal body",
    )
    runtime = _replace_once(
        runtime,
        """            proposal, attempts, models, result_digests, task_digests = self._proposal_for_plan(\n                plan,\n                request,\n                proposal_validator=proposal_validator,\n                alternative_round=alternative_round,\n            )\n""",
        """            proposal, attempts, models, result_digests, task_digests = self._proposal_for_plan(\n                plan,\n                request,\n                proposal_validator=proposal_validator,\n                alternative_round=alternative_round,\n                canonical_plan=primary_plan,\n            )\n""",
        label="agentic_runtime candidate proposal call",
    )
    runtime_path.write_text(runtime, encoding="utf-8")

    live_path = Path("services/api/parallax_api/code/agentic_runtime_live.py")
    live = live_path.read_text(encoding="utf-8")
    live = _replace_once(
        live,
        """    def _proposal_for_plan(\n        self,\n        plan: TeamPlan,\n        request: ImplementationGenerationRequest,\n        *,\n        proposal_validator,\n        alternative_round: int,\n    ) -> tuple[\n""",
        """    def _proposal_for_plan(\n        self,\n        plan: TeamPlan,\n        request: ImplementationGenerationRequest,\n        *,\n        proposal_validator,\n        alternative_round: int,\n        canonical_plan: TeamPlan | None = None,\n    ) -> tuple[\n""",
        label="agentic_runtime_live proposal signature",
    )
    live = _replace_once(
        live,
        """    ]:\n        run = self.service.get(plan.identity.run_id)\n        lineage = self._lineage(run)\n""",
        """    ]:\n        durable_plan = canonical_plan or plan\n        self._assert_candidate_plan_compatible(plan, durable_plan)\n        run = self.service.get(durable_plan.identity.run_id)\n        lineage = self._lineage(run)\n""",
        label="agentic_runtime_live proposal body",
    )
    start = live.index("    def _proposal_for_plan(")
    end = live.index("    def generate_protected(", start)
    region = live[start:end]
    region, count = re.subn(
        r"(self\.worker_bridge\.checkpoint\(\n\s*lease,\n\s*)plan=plan,",
        r"\1plan=durable_plan,",
        region,
    )
    if count < 3:
        raise SystemExit(f"agentic_runtime_live: expected at least 3 durable checkpoint replacements, got {count}")
    live_path.write_text(live[:start] + region + live[end:], encoding="utf-8")

    recovery_path = Path("services/api/parallax_api/code/agentic_candidate_recovery.py")
    recovery = recovery_path.read_text(encoding="utf-8")
    recovery = _replace_once(
        recovery,
        """    def _proposal_for_plan(\n        self,\n        plan: TeamPlan,\n        request: ImplementationGenerationRequest,\n        *,\n        proposal_validator: Callable[[ImplementationProposal], bool],\n        alternative_round: int,\n    ) -> tuple[\n""",
        """    def _proposal_for_plan(\n        self,\n        plan: TeamPlan,\n        request: ImplementationGenerationRequest,\n        *,\n        proposal_validator: Callable[[ImplementationProposal], bool],\n        alternative_round: int,\n        canonical_plan: TeamPlan | None = None,\n    ) -> tuple[\n""",
        label="agentic_candidate_recovery proposal signature",
    )
    recovery = _replace_once(
        recovery,
        """    ]:\n        run = self.service.get(plan.identity.run_id)\n        lineage = self._lineage(run)\n""",
        """    ]:\n        durable_plan = canonical_plan or plan\n        self._assert_candidate_plan_compatible(plan, durable_plan)\n        run = self.service.get(durable_plan.identity.run_id)\n        lineage = self._lineage(run)\n""",
        label="agentic_candidate_recovery proposal body",
    )
    start = recovery.index("    def _proposal_for_plan(")
    end = recovery.index("\n\ndef build_resilient_live_agentic_runtime_composition(", start)
    region = recovery[start:end]
    region, count = re.subn(
        r"(self\.worker_bridge\.checkpoint\(\n\s*lease,\n\s*)plan=plan,",
        r"\1plan=durable_plan,",
        region,
    )
    if count < 4:
        raise SystemExit(f"agentic_candidate_recovery: expected at least 4 durable checkpoint replacements, got {count}")
    recovery_path.write_text(recovery[:start] + region + recovery[end:], encoding="utf-8")

    Path("services/api/tests/test_candidate_plan_identity_v02333.py").write_text(
        '''from __future__ import annotations

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
''',
        encoding="utf-8",
    )


def apply_architecture() -> None:
    path = Path("ARCHITECTURE.md")
    text = path.read_text(encoding="utf-8")
    text = _replace_once(text, "Version: 3.43", "Version: 3.44", label="architecture version")
    anchor = "## Version relationship\n\n"
    paragraph = (
        "Architecture v3.44 separates the canonical durable PLAN identity from subordinate disposable candidate-local producer selection during one protected IMPLEMENT attempt. The exact `primary_plan` accepted at PLAN remains the only worker-checkpoint `plan_ref` unless the existing explicit human-authorized PLAN-refresh cycle runs. A bounded challenger or validation-repair `TeamPlan` may continue to select a different already-admitted producer and therefore retain distinct assignment, operation, request and attempt identity, but it is non-authoritative selection evidence only. Before sharing the canonical worker checkpoint, server-owned code requires exact Project, Engineering Run, Work Specification ID/revision/digest, acceptance contract, agent-protocol version, orchestration policy, work-graph and orchestration-limit compatibility, and requires every candidate-local roster/selected/eligible agent to remain within the canonical PLAN admission. Live and resilient proposal generation schedule tasks and admit results against the candidate-local plan while every durable AGENT_DISPATCH/convergence/result/proposal checkpoint remains bound to the canonical protected PLAN. Candidate count, Luna/Terra/Sol admission, 60-second hosted timeout, zero hidden provider retries, per-work-unit recovery, final validator repair, static-web repair eligibility, execution-contract authority, SafeImplementationEngine, disposable BUILD/TEST/VERIFY, source-lineage/Git/deployment/lifecycle authority and the human REVIEW ceiling are unchanged. Architecture v3.43 remains the bounded static-web validation-repair foundation.\n\n"
    )
    text = _replace_once(text, anchor, anchor + paragraph, label="architecture relationship")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("runtime", "architecture"))
    args = parser.parse_args()
    if args.mode == "runtime":
        apply_runtime()
    else:
        apply_architecture()


if __name__ == "__main__":
    main()
