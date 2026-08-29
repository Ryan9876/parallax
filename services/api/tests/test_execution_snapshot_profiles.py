from __future__ import annotations

from pathlib import Path

import pytest

from parallax_api.code.agentic_runtime import VercelCandidateValidationExecutor
from parallax_api.execution_environment import (
    DEFAULT_EXECUTION_SNAPSHOT_ID,
    DOTNET_EXECUTION_SNAPSHOT_ENV,
    EXECUTION_SNAPSHOT_ENV,
    execution_snapshot_id_for_profile,
)


def test_python_and_node_share_established_common_snapshot(monkeypatch):
    monkeypatch.delenv(EXECUTION_SNAPSHOT_ENV, raising=False)
    assert execution_snapshot_id_for_profile("python-v1") == DEFAULT_EXECUTION_SNAPSHOT_ID
    assert execution_snapshot_id_for_profile("node-v1") == DEFAULT_EXECUTION_SNAPSHOT_ID


def test_common_snapshot_override_remains_server_owned(monkeypatch):
    monkeypatch.setenv(EXECUTION_SNAPSHOT_ENV, "snap_test-common-override")
    assert execution_snapshot_id_for_profile("python-v1") == "snap_test-common-override"
    assert execution_snapshot_id_for_profile("node-v1") == "snap_test-common-override"


def test_dotnet_requires_dedicated_configuration(monkeypatch):
    monkeypatch.delenv(DOTNET_EXECUTION_SNAPSHOT_ENV, raising=False)
    with pytest.raises(ValueError, match="\.NET execution snapshot identity is unavailable"):
        execution_snapshot_id_for_profile("dotnet-v1")

    monkeypatch.setenv(DOTNET_EXECUTION_SNAPSHOT_ENV, "snap_test-dotnet-qualified")
    assert execution_snapshot_id_for_profile("dotnet-v1") == "snap_test-dotnet-qualified"


def test_unknown_profile_cannot_shape_snapshot_lookup(monkeypatch):
    monkeypatch.setenv("PARALLAX_EVIL_EXECUTION_SNAPSHOT_ID", "snap_should-never-be-read")
    with pytest.raises(ValueError, match="not admitted"):
        execution_snapshot_id_for_profile("evil-v1")


def test_malformed_snapshot_ids_fail_closed(monkeypatch):
    monkeypatch.setenv(DOTNET_EXECUTION_SNAPSHOT_ENV, " bad-value ")
    with pytest.raises(ValueError, match="snapshot identity is invalid"):
        execution_snapshot_id_for_profile("dotnet-v1")


def test_dotnet_candidate_missing_snapshot_fails_before_sandbox_creation(tmp_path: Path, monkeypatch):
    (tmp_path / "OtTime.sln").write_text("fixture", encoding="utf-8")
    monkeypatch.delenv(DOTNET_EXECUTION_SNAPSHOT_ENV, raising=False)
    executor = VercelCandidateValidationExecutor(
        project_id="prj_test",
        snapshot_id="snap_test-common-runtime",
    )

    def unexpected_sdk_call():
        raise AssertionError("sandbox SDK must not be reached without a qualified .NET snapshot")

    executor._sdk = unexpected_sdk_call
    result = executor.validate_candidate(tmp_path.resolve(), operation_key="qa-missing-dotnet-snapshot")

    assert result.passed is False
    assert result.validation_profile_id == "dotnet-v1"
    assert len(result.stage_evidence) == 1
    stage, evidence = result.stage_evidence[0]
    assert stage == "BUILD"
    assert evidence["protected_success"] is False
    assert evidence["dependency_preparation_code"] == "EXECUTION_PROFILE_UNAVAILABLE"
    assert evidence["execution_snapshot_verified"] is False
    assert "execution_snapshot_id" not in evidence
    assert evidence["candidate_is_canonical_lineage"] is False
    assert evidence["accepts_source_lineage"] is False
