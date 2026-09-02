from pathlib import Path

import pytest

from parallax_api.code.domain import WorkflowStage
from parallax_api.code.execution import ExecutionPolicyError, ExecutionResult, ExecutionSpec, RecordedExecutor
from parallax_api.code.protected import (
    STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE,
    ProtectedEvidenceError,
    validate_implementation,
    validate_review,
    validate_structural_execution,
)
from parallax_api.code.workspace import LocalWorkspace, WorkspaceBoundaryError


def test_workspace_artifacts_are_bounded_and_stably_identified(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('ok')\n")
    snapshot = LocalWorkspace(tmp_path).snapshot(["src/app.py"])
    assert len(snapshot["workspace_digest"]) == 64
    assert snapshot["artifacts"][0]["path"] == "src/app.py"
    with pytest.raises(WorkspaceBoundaryError):
        LocalWorkspace(tmp_path).artifact("../outside")


def test_recorded_executor_rejects_unsafe_commands_and_preserves_failure_truth():
    executor = RecordedExecutor({"build-1": ExecutionResult(exit_code=1, duration_ms=8, stderr="failed")})
    evidence = executor.execute(ExecutionSpec(tool_id="build", stage=WorkflowStage.BUILD, operation_key="build-1"))
    assert evidence["protected_success"] is False
    with pytest.raises(ExecutionPolicyError):
        executor.execute(ExecutionSpec(tool_id="build", args=("ok; deploy",), stage=WorkflowStage.BUILD, operation_key="build-1"))


def test_prose_only_implementation_and_stale_review_are_rejected():
    with pytest.raises(ProtectedEvidenceError):
        validate_implementation({"summary": "implemented"})
    with pytest.raises(ProtectedEvidenceError):
        validate_review({"recommendation": "PASS", "acceptance_ids_verified": ["AC-01"], "workspace_digest": "old"}, {"AC-01"}, "new")


def test_structural_execution_requires_exact_unverified_partition():
    required = {"AC-01", "AC-02"}
    evidence = {
        "protected_success": True,
        "exit_code": 0,
        "timed_out": False,
        "acceptance_verification_scope": STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE,
        "acceptance_ids_targeted": ["AC-01", "AC-02"],
        "acceptance_ids_verified": [],
        "acceptance_ids_unverified": ["AC-01", "AC-02"],
    }
    validate_structural_execution(evidence, required)
    with pytest.raises(ProtectedEvidenceError):
        validate_structural_execution(dict(evidence, acceptance_ids_verified=["AC-01"]), required)
    with pytest.raises(ProtectedEvidenceError):
        validate_structural_execution(dict(evidence, acceptance_ids_unverified=["AC-01"]), required)
    with pytest.raises(ProtectedEvidenceError):
        validate_structural_execution(dict(evidence, acceptance_ids_targeted=["AC-01", "AC-01"]), required)
    with pytest.raises(ProtectedEvidenceError):
        validate_structural_execution(dict(evidence, acceptance_verification_scope="FULL"), required)
