from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.agentic_runtime import (
    CandidateAdmissionFailure,
    CandidateValidationResult,
    _candidate_admission_phase,
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


PROFILE_ID = "python-v1"
PROFILE_DIGEST = "e" * 64


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
        validation_profile_id=PROFILE_ID,
        validation_profile_digest=PROFILE_DIGEST,
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
                    "validation_profile_id": PROFILE_ID,
                    "validation_profile_digest": PROFILE_DIGEST,
                },
            ),
        ),
    )

    diagnostic = _candidate_validation_failure_diagnostic("candidate-primary", result)

    assert diagnostic is not None
    assert diagnostic["failed_stage"] == "TEST"
    assert diagnostic["exit_code"] == 1
    assert diagnostic["candidate_content_digest"] == "d" * 64
    assert diagnostic["validation_profile_id"] == PROFILE_ID
    assert diagnostic["validation_profile_digest"] == PROFILE_DIGEST
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

    hostile = ImplementationRuntimeError(
        "bounded failure",
        diagnostic_evidence={
            "candidate_validation_failure": {
                **_diagnostic()["candidate_validation_failure"],
                "stdout_excerpt": "Bearer super-secret",
                "stderr_excerpt": "postgresql://secret",
                "source_bytes": "private source",
                "provider_token": "secret",
                "model_output": "raw model text",
                "arbitrary": {"nested": "payload"},
            }
        },
    )
    assert hostile.diagnostic_evidence == _diagnostic()


def test_invalid_diagnostic_digest_drops_observation_without_changing_failure() -> None:
    failure = ImplementationRuntimeError(
        "bounded failure",
        diagnostic_evidence={
            "candidate_validation_failure": {
                **_diagnostic()["candidate_validation_failure"],
                "stdout_digest": "not-a-digest",
            }
        },
    )
    assert failure.mutation_applied is False
    assert failure.diagnostic_evidence is None


def _repositories():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    return (
        session,
        EngineeringRunRepository(session),
        ConversationRepository(session),
        WorkSpecificationRepository(session),
    )


def _run_with_spec():
    session, runs, conversations, specs = _repositories()
    conversation = conversations.create("code", project_id="11111111-1111-4111-8111-111111111111")
    draft = WorkSpecificationDraft(
        title="Bounded validation diagnostics",
        objective="Prove candidate failure remains observable without source mutation.",
        constraints=("No source mutation before protected validation passes.",),
        acceptance=("AC-01: Candidate validation failure remains bounded and observable.",),
        assumptions=(),
        exclusions=(),
        risk_notes=(),
        clarification_required=False,
    )
    specification = specs.create_draft(conversation.id, draft)
    specification = specs.approve(specification.id)
    service = EngineeringRunService(runs, conversations=conversations, work_specifications=specs)
    run = service.activate(
        conversation.id,
        work_specification_id=specification.id,
    ).run
    return session, service, run


def test_autonomy_persists_bounded_candidate_failure_diagnostics() -> None:
    session, service, run = _run_with_spec()

    class Executor:
        def probe(self, *, operation_key):
            return {"protected_success": True, "tool_id": "python"}

        def execute(self, spec: ExecutionSpec):
            return {"protected_success": True, "tool_id": spec.tool_id}

    class ImplementationRuntime:
        def execute(self, *, run_id, operation_key, expected_revision):
            raise ImplementationContractError(
                "protected implementation generation failed",
                diagnostic_evidence=_diagnostic(),
            )

    coordinator = AutonomyCoordinator(
        service,
        Executor(),
        implementation_runtime=ImplementationRuntime(),
        max_steps=4,
    )
    result = coordinator.run(
        run_id=run.id,
        operation_key="candidate-diagnostic-autonomy",
        expected_revision=run.revision,
    )

    assert result.stop_reason is AutonomyStopReason.IMPLEMENTATION_FAILED
    failed = result.run
    assert failed.last_failure_code == "AUTONOMOUS_IMPLEMENT_FAILED"
    attempt = failed.attempts[-1]
    evidence = json.loads(attempt.evidence_json)
    assert evidence["diagnostic_evidence"] == _diagnostic()
    assert evidence["mutation_applied"] is False
    session.close()


def test_candidate_admission_failure_preserves_bounded_diagnostic() -> None:
    with pytest.raises(CandidateAdmissionFailure) as captured:
        _candidate_admission_phase(
            candidate_id="candidate-primary",
            validation=CandidateValidationResult(
                content_digest="d" * 64,
                file_count=1,
                total_bytes=1,
                validation_profile_id=PROFILE_ID,
                validation_profile_digest=PROFILE_DIGEST,
                stage_evidence=(("TEST", {"protected_success": False}),),
            ),
        )
    assert captured.value.diagnostic_evidence["candidate_validation_failure"]["candidate_id"] == "candidate-primary"
