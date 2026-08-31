from __future__ import annotations

from pathlib import Path

import pytest

from parallax_api.code.agentic_runtime import (
    AgenticRuntimeError,
    VercelCandidateValidationExecutor,
    _candidate_admission_failure_diagnostic,
)
from parallax_api.code.execution import ExecutionPolicyError
from parallax_api.code.validation_toolchains import ValidationProfileError, select_validation_profile


def test_candidate_marker_edits_cannot_switch_authoritative_dotnet_profile(tmp_path: Path, monkeypatch):
    base = tmp_path / "base"
    candidate = tmp_path / "candidate"
    base.mkdir()
    candidate.mkdir()
    (base / "OtTime.sln").write_text("fixture", encoding="utf-8")
    (candidate / "package.json").write_text('{"scripts":{"test":"echo nope"}}', encoding="utf-8")
    profile = select_validation_profile(base.resolve())
    monkeypatch.delenv("PARALLAX_DOTNET_EXECUTION_SNAPSHOT_ID", raising=False)
    executor = VercelCandidateValidationExecutor(
        project_id="prj_test",
        snapshot_id="snap_test-common-runtime",
    )

    def unexpected_sdk_call():
        raise AssertionError("candidate profile pinning must fail before sandbox when .NET snapshot is unavailable")

    executor._sdk = unexpected_sdk_call
    result = executor.validate_candidate(
        candidate.resolve(),
        operation_key="p2330:pinned-dotnet",
        validation_profile=profile,
    )

    assert result.validation_profile_id == "dotnet-v1"
    assert result.file_count == 1
    assert result.total_bytes > 0
    assert result.passed is False
    stage, evidence = result.stage_evidence[0]
    assert stage == "BUILD"
    assert evidence["dependency_preparation_code"] == "EXECUTION_PROFILE_UNAVAILABLE"


def test_candidate_validator_requires_server_owned_profile(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    executor = VercelCandidateValidationExecutor(project_id="prj_test")
    with pytest.raises(TypeError):
        executor.validate_candidate(tmp_path.resolve(), operation_key="p2330:missing-profile")


@pytest.mark.parametrize("exc", [ValidationProfileError("profile"), ExecutionPolicyError("policy")])
def test_profile_and_policy_errors_use_fixed_sanitized_admission_classification(exc):
    diagnostic = _candidate_admission_failure_diagnostic(
        "candidate-primary",
        "DISPOSABLE_CANDIDATE_VALIDATION",
        exc,
    )
    assert diagnostic["failure_kind"] == "VALIDATION_PROFILE_ERROR"
    assert "profile" not in str(diagnostic)
    assert "policy" not in str(diagnostic)
    assert diagnostic["source_lineage_accepted"] is False
    assert diagnostic["production_deployed"] is False


def test_plain_value_error_remains_value_contract_error():
    diagnostic = _candidate_admission_failure_diagnostic(
        "candidate-primary",
        "DISPOSABLE_CANDIDATE_VALIDATION",
        ValueError("raw detail must not persist"),
    )
    assert diagnostic["failure_kind"] == "VALUE_CONTRACT_ERROR"
    assert "raw detail" not in str(diagnostic)
