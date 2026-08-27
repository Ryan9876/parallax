from __future__ import annotations

import json

from sqlalchemy.orm import sessionmaker

from parallax_api.code.agentic_runtime import (
    CandidateValidationResult,
    _candidate_validation_failure_diagnostic,
)
from parallax_api.code.autonomy import AutonomyCoordinator, AutonomyStopReason
from parallax_api.code.execution import ExecutionSpec
from parallax_api.code.implementation_runtime import ImplementationContractError, ImplementationRuntimeError
from parallax_api.code.service import EngineeringRunService
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


def _diagnostic() -> dict[str, object]:
    return {
        "candidate_validation_failure": {
            "candidate_id": "candidate-primary",
            "failed_stage": "TEST",
            "protected_success": False,
            "exit_code_present": True,
            "exit_code": 1,
            "timed_out": False,
            "tool_id": "test",
            "invocation_digest": "a" * 64,
            "stdout_digest": "b" * 64,
            "stderr_digest": "c" * 64,
            "execution_snapshot_id": "snap_validation-test",
            "candidate_content_digest": "d" * 64,
            "candidate_is_canonical_lineage": False,
            "accepts_source_lineage": False,
            "source_lineage_accepted": False,
            "production_deployed": False,
        }
    }


def test_candidate_validation_failure_projection_omits_raw_output_and_authority() -> None:
    result = CandidateValidationResult(
        content_digest="d" * 64,
        file_count=10,
        total_bytes=1000,
        stage_evidence=(
            (
                "BUILD",
                {
                    "tool_id": "build",
                    "exit_code": 0,
                    "protected_success": True,
                },
            ),
            (
                "TEST",
                {
                    "tool_id": "test",
                    "invocation_digest": "a" * 64,
                    "exit_code": 1,
                    "stdout_digest": "b" * 64,
                    "stdout_excerpt": "must never persist",
                    "stderr_digest": "c" * 64,
                    "stderr_excerpt": "Bearer must-never-persist",
                    "timed_out": False,
                    "protected_success": False,
                    "execution_snapshot_id": "snap_validation-test",
                },
            ),
        ),
    )

    diagnostic = _candidate_validation_failure_diagnostic("candidate-primary", result)

    assert diagnostic is not None
    assert diagnostic["failed_stage"] == "TEST"
    assert diagnostic["exit_code"] == 1
    assert diagnostic["candidate_content_digest"] == "d" * 64
    assert diagnostic["candidate_is_canonical_lineage"] is False
    assert diagnostic["accepts_source_lineage"] is False
    assert diagnostic["source_lineage_accepted"] is False
    assert diagnostic["production_deployed"] is False
    assert "stdout_excerpt" not in diagnostic
    assert "stderr_excerpt" not in diagnostic


def test_implementation_failure_diagnostics_drop_non_admitted_sensitive_fields() -> None:
    safe = ImplementationRuntimeError(
        "bounded failure",
        diagnostic_evidence=_diagnostic(),
    )
    assert safe.diagnostic_evidence == _diagnostic()

    unsafe = _diagnostic()
    unsafe["candidate_validation_failure"]["stdout_excerpt"] = "must never persist"  # type: ignore[index]
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


class _DiagnosticImplementationRuntime:
    def execute(self, **_kwargs):
        raise ImplementationContractError(
            "protected candidate validation rejected the proposal",
            mutation_applied=False,
            diagnostic_evidence=_diagnostic(),
        )


def _service(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'candidate-diagnostics.db'}")
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
            title="Candidate validation diagnostics",
            objective="Persist only sanitized failure evidence.",
            constraints=["Do not mutate canonical source on candidate failure."],
            acceptance_criteria=[
                "Candidate failure evidence identifies the protected stage.",
                "Sensitive model or provider material is never persisted.",
            ],
            risks=["Diagnostics could accidentally become an authority or secret channel."],
            open_questions=[],
            confidence=0.99,
            program_version="w6-candidate-diagnostics-test",
        ),
        model_id="test-model",
    )
    approved = work_specs.approve(draft)
    run = service.activate_run(
        conversation_id=conversation.id,
        work_specification_id=approved.id,
    )
    return session, service, run


def test_failed_implement_persists_only_bounded_candidate_diagnostic(tmp_path) -> None:
    session, service, run = _service(tmp_path)
    try:
        planned = AutonomyCoordinator(service, _Executor()).run(
            run_id=run.id,
            operation_key="candidate-diagnostic-plan",
            expected_revision=run.revision,
        )
        assert planned.run.state == "IMPLEMENT"

        result = AutonomyCoordinator(
            service,
            _Executor(),
            implementation_runtime=_DiagnosticImplementationRuntime(),
        ).run(
            run_id=run.id,
            operation_key="candidate-diagnostic-implement",
            expected_revision=planned.run.revision,
        )

        assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED
        assert result.run.state == "FAILED"
        attempt = next(item for item in result.run.attempts if item.stage == "IMPLEMENT")
        evidence = json.loads(attempt.evidence_json)
        assert evidence["error_class"] == "ImplementationContractError"
        assert evidence["mutation_applied"] is False
        assert evidence["diagnostic_evidence"] == _diagnostic()
        encoded = json.dumps(evidence, sort_keys=True)
        assert "stdout_excerpt" not in encoded
        assert "stderr_excerpt" not in encoded
        assert "Bearer" not in encoded
        assert evidence["diagnostic_evidence"]["candidate_validation_failure"]["source_lineage_accepted"] is False
        assert evidence["diagnostic_evidence"]["candidate_validation_failure"]["production_deployed"] is False
    finally:
        session.close()
