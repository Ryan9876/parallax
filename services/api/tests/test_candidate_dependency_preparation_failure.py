from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import parallax_api.code.agentic_runtime as runtime
from parallax_api.code.agentic_runtime import VercelCandidateValidationExecutor
from parallax_api.code.validation_toolchains import select_validation_profile
from parallax_api.code.dependency_preparation import DependencyPreparationError


class Context:
    def __init__(self, value=None):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, exc_type, exc, tb):
        return False


class Batch:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def write_bytes(self, path, content):
        return None


class Filesystem:
    def mkdir(self, *args, **kwargs):
        return None

    def batch(self, *args, **kwargs):
        return Batch()


class Policy:
    def __init__(self, mode, allow=None):
        self.mode = mode
        self.allow = allow or {}


class FakeNetworkPolicy:
    @staticmethod
    def deny_all():
        return Policy("deny-all")

    @staticmethod
    def custom(*, allow):
        return Policy("custom", allow)


@dataclass(frozen=True)
class FakeSnapshotSource:
    snapshot_id: str


class Instance:
    current_snapshot_id = "snap_test-dotnet-runtime"
    fs = Filesystem()


class Sandbox:
    def create_sandbox(self, **kwargs):
        return Context(Instance())


def test_prepare_failure_returns_bounded_candidate_result_not_http500_path(tmp_path: Path, monkeypatch):
    (tmp_path / "OtTime.sln").write_text("fixture", encoding="utf-8")
    executor = VercelCandidateValidationExecutor(
        project_id="prj_test",
        snapshot_id="snap_test-common-runtime",
        dotnet_snapshot_id="snap_test-dotnet-runtime",
    )
    executor._sdk = lambda: (lambda: Context(), FakeNetworkPolicy, FakeSnapshotSource, Sandbox())

    def fail_prepare(*args, **kwargs):
        raise DependencyPreparationError(
            "DEPENDENCY_PREPARATION_FAILED",
            evidence={
                "dependency_preparation_required": True,
                "dependency_preparation_succeeded": False,
                "dependency_preparation_code": "DEPENDENCY_PREPARATION_FAILED",
                "dependency_preparation_duration_ms": 12,
                "dependency_probe_exit_code": 0,
                "dependency_prepare_exit_code": 1,
                "dependency_stdout_digest": "a" * 64,
                "dependency_stderr_digest": "b" * 64,
                "validation_network_locked": True,
            },
        )

    monkeypatch.setattr(runtime, "run_dependency_preparation", fail_prepare)
    profile = select_validation_profile(tmp_path.resolve())
    result = executor.validate_candidate(
        tmp_path.resolve(),
        operation_key="qa-prepare-failure",
        validation_profile=profile,
    )

    assert result.passed is False
    assert len(result.stage_evidence) == 1
    stage, evidence = result.stage_evidence[0]
    assert stage == "BUILD"
    assert evidence["protected_success"] is False
    assert evidence["dependency_preparation_code"] == "DEPENDENCY_PREPARATION_FAILED"
    assert evidence["validation_network_locked"] is True
    assert evidence["execution_snapshot_id"] == "snap_test-dotnet-runtime"
    assert evidence["candidate_is_canonical_lineage"] is False
    assert evidence["accepts_source_lineage"] is False
