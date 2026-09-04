from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from parallax_api.code.agentic_runtime import AgenticControlPlane, CandidateValidationResult
from parallax_api.code.domain import WorkflowStage
from parallax_api.evaluation.agent_judgment import CandidateBinding, EvaluationOutcome


def _sha(char: str) -> str:
    return char * 64


def _passing_validation() -> CandidateValidationResult:
    return CandidateValidationResult(
        content_digest=_sha("a"),
        file_count=1,
        total_bytes=12,
        stage_evidence=tuple(
            (
                stage.value,
                {
                    "protected_success": True,
                    "tool_id": "python",
                    "invocation_digest": _sha("b"),
                    "stdout_digest": _sha("c"),
                    "stderr_digest": _sha("d"),
                    "exit_code": 0,
                    "timed_out": False,
                },
            )
            for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY)
        ),
    )


def test_independent_evaluation_uses_protected_stage_evidence_once() -> None:
    project_id = str(uuid4())
    run_id = str(uuid4())
    work_specification_id = str(uuid4())
    producer_digest = _sha("e")
    binding = CandidateBinding(
        project_id=project_id,
        run_id=run_id,
        work_specification_id=work_specification_id,
        work_specification_revision=1,
        work_specification_digest=_sha("f"),
        acceptance_ids=("AC-01",),
        candidate_lineage_digest=_sha("a"),
        candidate_revision_id="revision:aaaaaaaaaaaaaaaaaaaaaaaa",
        candidate_attempt_id="attempt:candidate-primary",
        producer_identity_digest=producer_digest,
    )
    control = object.__new__(AgenticControlPlane)

    protected, record = control._evaluation(
        run=SimpleNamespace(project_id=project_id),
        candidate_id="candidate-primary",
        candidate_binding=binding,
        validation=_passing_validation(),
        producer_digests=(producer_digest,),
    )

    assert protected.passed is True
    assert len(protected.evidence_refs) == 3
    assert len({item.identity for item in protected.evidence_refs}) == 3
    assert record.outcome is EvaluationOutcome.SUPPORTED
    assert record.evidence_refs == protected.evidence_refs
    assert len(record.evidence_refs) == 3
    assert record.candidate == binding
    assert record.protected_validation_digest == protected.digest
