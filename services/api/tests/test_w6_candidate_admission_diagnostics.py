from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from parallax_api.code.agentic_runtime import (
    CandidateAdmissionFailure,
    CandidateValidationFailure,
    _candidate_admission_phase,
)
from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason
from parallax_api.code.execution import ExecutionSpec
from parallax_api.code.implementation_runtime import (
    ImplementationContractError,
    ImplementationRuntimeError,
)
from parallax_api.code.service import EngineeringRunService
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


def _diagnostic() -> dict[str, object]:
    return {
        "candidate_admission_failure": {
            "candidate_id": "candidate-primary",
            "phase": "DISPOSABLE_VALIDATION_EXECUTION",
            "failure_kind": "CONTRACT_REJECTED",
            "candidate_is_canonical_lineage": False,
            "accepts_source_lineage": False,
            "source_lineage_accepted": False,
            "engineering_run_transitioned": False,
            "review_completed": False,
            "production_deployed": False,
        }
    }


def test_candidate_admission_phase_projects_only_finite_server_owned_codes() -> None:
    try:
        with _candidate_admission_phase(
            "candidate-primary",
            "DISPOSABLE_VALIDATION_EXECUTION",
        ):
            raise ValueError("Bearer secret-value and arbitrary exception detail must not persist")
    except CandidateAdmissionFailure as exc:
        diagnostic = exc.diagnostic_evidence
    else:
        raise AssertionError("candidate admission failure was not projected")

    assert diagnostic == _diagnostic()["candidate_admission_failure"]
    encoded = json.dumps(diagnostic, sort_keys=True)
    assert "Bearer" not in encoded
    assert "secret-value" not in encoded
    assert diagnostic["source_lineage_accepted"] is False
    assert diagnostic["engineering_run_transitioned"] is False
    assert diagnostic["review_completed"] is False
    assert diagnostic["production_deployed"] is False


def test_candidate_admission_phase_preserves_richer_stage_failure() -> None:
    richer = CandidateValidationFailure(
        "protected stage failed",
        diagnostic_evidence={"candidate_id": "candidate-primary"},
    )
    try:
        with _candidate_admission_phase("candidate-primary", "ROUTING_DECISION"):
            raise richer
    except CandidateValidationFailure as exc:
        assert exc is richer
    else:
        raise AssertionError("richer candidate validation failure was not preserved")


def test_implementation_failure_boundary_drops_arbitrary_candidate_admission_fields() -> None:
    safe = ImplementationRuntimeError(
        "bounded failure",
        diagnostic_evidence=_diagnostic(),
    )
    assert safe.diagnostic_evidence == _diagnostic()

    unsafe = _diagnostic()
    raw = unsafe["candidate_admission_failure"]
    assert isinstance(raw, dict)
    raw["prompt"] = "must never persist"
    rejected = ImplementationRuntimeError(
        "bounded failure",
        diagnostic_evidence=unsafe,
    )
    assert rejected.diagnostic_evidence is None


class _Executor:
    def probe(self, *, operation_key: str) -> dict[str, object]:
        return {
            "tool_id": "python",
            "exit_code": 0,
            "protected_success": True,
        }

    def execute(self, spec: ExecutionSpec) -> dict[str, object]:
        raise AssertionError("execution must not continue past failed IMPLEMENT")


class _AdmissionDiagnosticImplementationRuntime:
    def execute(self, **_kwargs):
        raise ImplementationContractError(
            "candidate admission rejected the proposal",
            mutation_applied=False,
            diagnostic_evidence=_diagnostic(),
        )


def _service(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'candidate-admission-diagnostics.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    conversations = ConversationRepository(session)
    runs = EngineeringRunRepository(session)
    work_specs = WorkSpecificationRepository(session)
    service = EngineeringRunService(runs, conversations, work_specs)

    conversation = conversations.create("code", spec_id="P2-V0.19.7")
    draft = work_specs.create_draft(
        conversation_id=conversation.id,
        draft=WorkSpecificationDraft(
            title="Candidate admission diagnostics",
            objective="Persist only finite server-owned failure phase evidence.",
            constraints=["Do not mutate canonical source on candidate admission failure."],
            acceptance_criteria=[
                "Candidate admission failures identify a finite server-owned phase.",
                "Sensitive exception, model, provider, or authority material is never persisted.",
            ],
            risks=["Diagnostics could accidentally become an authority or secret channel."],
            open_questions=[],
            confidence=0.99,
            program_version="w6-candidate-admission-diagnostics-test",
        ),
        model_id="test-model",
    )
    approved = work_specs.approve(draft)
    run = service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=approved.id,
    )
    return session, service, run


def test_failed_implement_persists_only_bounded_candidate_admission_phase(tmp_path) -> None:
    session, service, run = _service(tmp_path)
    try:
        planned = AutonomyCoordinator(service, _Executor()).run(
            run_id=run.id,
            operation_key="candidate-admission-plan",
            expected_revision=run.revision,
        )
        assert planned.run.state == "IMPLEMENT"

        result = AutonomyCoordinator(
            service,
            _Executor(),
            implementation_runtime=_AdmissionDiagnosticImplementationRuntime(),
        ).run(
            run_id=run.id,
            operation_key="candidate-admission-implement",
            expected_revision=planned.run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED
        attempt = next(item for item in result.run.attempts if item.stage == "IMPLEMENT")
        evidence = json.loads(attempt.evidence_json)
        assert evidence["mutation_applied"] is False
        assert evidence["diagnostic_evidence"] == _diagnostic()
        encoded = json.dumps(evidence, sort_keys=True)
        assert "prompt" not in encoded
        projected = evidence["diagnostic_evidence"]["candidate_admission_failure"]
        assert projected["source_lineage_accepted"] is False
        assert projected["engineering_run_transitioned"] is False
        assert projected["review_completed"] is False
        assert projected["production_deployed"] is False
    finally:
        session.close()
