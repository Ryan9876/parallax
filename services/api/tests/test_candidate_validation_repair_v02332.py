from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from parallax_api.code.agentic_runtime import (
    AgenticControlPlane,
    CandidateValidationFailure,
    CandidateValidationResult,
    _candidate_validation_failure_diagnostic,
    _static_web_validation_reason,
)
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.implementation_runtime import _bounded_implementation_failure_evidence
from parallax_api.code.static_web_validator import (
    STATIC_WEB_REPAIRABLE_REASON_CODES,
    STATIC_WEB_VALIDATION_REASON_CODES,
)
from parallax_api.code.validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    resolve_execution_contract,
)
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    ImplementationGenerationRequest,
)


def _validation(reason: str, *, passed: bool = False) -> CandidateValidationResult:
    evidence = {
        "protected_success": passed,
        "exit_code": 0 if passed else 1,
        "timed_out": False,
        "validation_reason_code": reason,
        "validation_profile_id": "node-v1",
        "validation_profile_digest": "a" * 64,
        "candidate_is_canonical_lineage": False,
        "accepts_source_lineage": False,
    }
    return CandidateValidationResult(
        content_digest="b" * 64,
        file_count=1,
        total_bytes=10,
        validation_profile_id="node-v1",
        validation_profile_digest="a" * 64,
        stage_evidence=((WorkflowStage.BUILD.value, evidence),),
    )


def _request() -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id="spec",
        work_specification_revision=1,
        work_specification_digest="c" * 64,
        title="Build a static page",
        objective="Build a static page",
        constraints=("Use bounded source changes.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="A page exists."),),
        source_context=SourceContextSnapshot(files=(), digest="d" * 64, total_bytes=0, excluded_secret_files=(), omitted_bounded_files=()),
    )


def _contract():
    return resolve_execution_contract(
        ExecutionContractCode.STATIC_WEB.value,
        binding_reason=ExecutionBindingReason.GREENFIELD_STATIC_WEB.value,
        target=None,
    )


def test_static_web_reason_projection_is_exact_and_closed():
    assert _static_web_validation_reason("STATIC_WEB_INDEX_REQUIRED\n") == "STATIC_WEB_INDEX_REQUIRED"
    assert _static_web_validation_reason("STATIC_WEB_INDEX_REQUIRED\nsecret") is None
    assert _static_web_validation_reason("prefix STATIC_WEB_INDEX_REQUIRED") is None
    assert _static_web_validation_reason("UNKNOWN") is None
    assert STATIC_WEB_REPAIRABLE_REASON_CODES < STATIC_WEB_VALIDATION_REASON_CODES


def test_candidate_failure_diagnostic_and_durable_sanitizer_admit_only_fixed_reason():
    diagnostic = _candidate_validation_failure_diagnostic("candidate-primary", _validation("STATIC_WEB_INDEX_REQUIRED"))
    assert diagnostic is not None
    assert diagnostic["validation_reason_code"] == "STATIC_WEB_INDEX_REQUIRED"
    normalized = _bounded_implementation_failure_evidence({"candidate_validation_failure": diagnostic})
    assert normalized["candidate_validation_failure"]["validation_reason_code"] == "STATIC_WEB_INDEX_REQUIRED"

    tampered = dict(diagnostic)
    tampered["validation_reason_code"] = "RAW STDERR secret"
    with pytest.raises(ValueError):
        _bounded_implementation_failure_evidence({"candidate_validation_failure": tampered})


def test_repair_request_contains_only_fixed_server_guidance():
    diagnostic = _candidate_validation_failure_diagnostic("candidate-primary", _validation("STATIC_WEB_INDEX_REQUIRED"))
    assert diagnostic is not None
    repaired = AgenticControlPlane._candidate_validation_repair_request(_request(), _contract(), diagnostic)
    assert repaired.source_context is _request().source_context or repaired.source_context.files == ()
    assert len(repaired.constraints) == 2
    guidance = repaired.constraints[-1]
    assert "STATIC_WEB_INDEX_REQUIRED" in guidance
    assert "static-web-v1" in guidance
    assert "stderr" not in guidance.casefold()
    assert "secret" not in guidance.casefold()


class _RepairHarness(AgenticControlPlane):
    def __init__(self, replacement):
        self.service = object()
        self.replacement = replacement
        self.calls = []

    @staticmethod
    def _acceptance(run, service):
        return ({"id": "AC-01", "text": "A page exists."},)

    def _challenger_plan(self, **kwargs):
        return SimpleNamespace(selected_agent_digests=("agent-b",), plan_id="repair-plan")

    def _make_candidate(self, **kwargs):
        self.calls.append(kwargs)
        return self.replacement, kwargs["routing_context"]


def test_repair_uses_existing_second_round_and_restarts_from_authoritative_base(tmp_path: Path):
    primary = SimpleNamespace(
        candidate_id="candidate-primary",
        validation=_validation("STATIC_WEB_INDEX_REQUIRED"),
    )
    replacement = SimpleNamespace(
        candidate_id="candidate-repair",
        validation=CandidateValidationResult(
            content_digest="e" * 64,
            file_count=1,
            total_bytes=20,
            validation_profile_id="node-v1",
            validation_profile_digest="a" * 64,
            stage_evidence=(
                (WorkflowStage.BUILD.value, {"protected_success": True}),
                (WorkflowStage.TEST.value, {"protected_success": True}),
                (WorkflowStage.VERIFY.value, {"protected_success": True}),
            ),
        ),
    )
    control = _RepairHarness(replacement)
    base = tmp_path / "base"
    base.mkdir()
    repaired, diagnostic = control._repair_failed_primary_candidate(
        run=SimpleNamespace(),
        primary=primary,
        primary_plan=SimpleNamespace(selected_agent_digests=("agent-a",)),
        execution_contract=_contract(),
        execution_request=_request(),
        base_workspace=base,
        source_digest="f" * 64,
        proposal_validator=lambda proposal: True,
        operation_key="repair-test",
        routing_context=SimpleNamespace(),
    )
    assert repaired is replacement
    assert diagnostic["validation_reason_code"] == "STATIC_WEB_INDEX_REQUIRED"
    assert len(control.calls) == 1
    call = control.calls[0]
    assert call["candidate_id"] == "candidate-repair"
    assert call["alternative_round"] == 2
    assert call["base_workspace"] == base
    assert "STATIC_WEB_INDEX_REQUIRED" in call["request"].constraints[-1]


def test_nonrepairable_reason_does_not_generate_replacement(tmp_path: Path):
    primary = SimpleNamespace(
        candidate_id="candidate-primary",
        validation=_validation("STATIC_WEB_JS_CHECK_UNAVAILABLE"),
    )
    control = _RepairHarness(SimpleNamespace())
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(CandidateValidationFailure):
        control._repair_failed_primary_candidate(
            run=SimpleNamespace(),
            primary=primary,
            primary_plan=SimpleNamespace(selected_agent_digests=("agent-a",)),
            execution_contract=_contract(),
            execution_request=_request(),
            base_workspace=base,
            source_digest="f" * 64,
            proposal_validator=lambda proposal: True,
            operation_key="repair-test",
            routing_context=SimpleNamespace(),
        )
    assert control.calls == []


def test_second_candidate_validation_rejection_is_terminal(tmp_path: Path):
    primary = SimpleNamespace(
        candidate_id="candidate-primary",
        validation=_validation("STATIC_WEB_INDEX_REQUIRED"),
    )
    replacement = SimpleNamespace(
        candidate_id="candidate-repair",
        validation=_validation("STATIC_WEB_JS_SYNTAX_INVALID"),
    )
    control = _RepairHarness(replacement)
    base = tmp_path / "base"
    base.mkdir()
    with pytest.raises(CandidateValidationFailure) as captured:
        control._repair_failed_primary_candidate(
            run=SimpleNamespace(),
            primary=primary,
            primary_plan=SimpleNamespace(selected_agent_digests=("agent-a",)),
            execution_contract=_contract(),
            execution_request=_request(),
            base_workspace=base,
            source_digest="f" * 64,
            proposal_validator=lambda proposal: True,
            operation_key="repair-test",
            routing_context=SimpleNamespace(),
        )
    assert captured.value.diagnostic_evidence["candidate_id"] == "candidate-repair"
    assert len(control.calls) == 1
