from __future__ import annotations

from types import SimpleNamespace

from parallax_api.code.agentic_runtime import AgenticControlPlane, CandidateValidationResult
from parallax_api.evaluation.agent_judgment import CandidateBinding, EvaluationOutcome

PROJECT_ID = "11111111-1111-4111-8111-111111111111"
RUN_ID = "22222222-2222-4222-8222-222222222222"
WORK_SPEC_ID = "33333333-3333-4333-8333-333333333333"
PRODUCER_DIGEST = "a" * 64


def _binding() -> CandidateBinding:
    return CandidateBinding(
        project_id=PROJECT_ID,
        run_id=RUN_ID,
        work_specification_id=WORK_SPEC_ID,
        work_specification_revision=1,
        work_specification_digest="b" * 64,
        acceptance_ids=("AC-01",),
        candidate_lineage_digest="c" * 64,
        candidate_revision_id="revision:candidate-primary",
        candidate_attempt_id="attempt:candidate-primary",
        producer_identity_digest=PRODUCER_DIGEST,
    )


def _stage(name: str, passed: bool) -> tuple[str, dict[str, object]]:
    prefix = {"BUILD": "1", "TEST": "2", "VERIFY": "3"}[name]
    return name, {
        "protected_success": passed,
        "tool_id": name.lower(),
        "invocation_digest": prefix * 64,
        "stdout_digest": "4" * 64,
        "stderr_digest": "5" * 64,
        "exit_code": 0 if passed else 1,
        "timed_out": False,
    }


def _control() -> AgenticControlPlane:
    return object.__new__(AgenticControlPlane)


def test_passing_protected_refs_are_evaluated_once() -> None:
    validation = CandidateValidationResult(
        content_digest="c" * 64,
        file_count=1,
        total_bytes=1,
        validation_profile_id="python-v1",
        validation_profile_digest="e" * 64,
        stage_evidence=(
            _stage("BUILD", True),
            _stage("TEST", True),
            _stage("VERIFY", True),
        ),
    )
    protected, record = _control()._evaluation(
        run=SimpleNamespace(project_id=PROJECT_ID),
        candidate_id="candidate-primary",
        candidate_binding=_binding(),
        validation=validation,
        producer_digests=(PRODUCER_DIGEST,),
    )
    assert protected.passed is True
    assert record.outcome is EvaluationOutcome.SUPPORTED
    assert len(protected.evidence_refs) == 3
    assert len(record.evidence_refs) == 3
    assert {ref.identity for ref in record.evidence_refs} == {
        ref.identity for ref in protected.evidence_refs
    }


def test_failed_protected_validation_blocks_without_duplicate_ref_error() -> None:
    validation = CandidateValidationResult(
        content_digest="c" * 64,
        file_count=1,
        total_bytes=1,
        validation_profile_id="python-v1",
        validation_profile_digest="e" * 64,
        stage_evidence=(_stage("BUILD", False),),
    )
    protected, record = _control()._evaluation(
        run=SimpleNamespace(project_id=PROJECT_ID),
        candidate_id="candidate-primary",
        candidate_binding=_binding(),
        validation=validation,
        producer_digests=(PRODUCER_DIGEST,),
    )
    assert protected.passed is False
    assert record.outcome is EvaluationOutcome.DETERMINISTIC_BLOCKED
    assert len(record.evidence_refs) == 1
