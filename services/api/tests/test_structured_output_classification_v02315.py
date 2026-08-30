from __future__ import annotations

import asyncio
from contextlib import nullcontext
from hashlib import sha256
from types import SimpleNamespace

import pytest

from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    DspyImplementationGenerationProgram,
    GeneratedSourcePatch,
    IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT,
    ImplementationGenerationCoordinator,
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
)
from parallax_api.intelligence.router import (
    ModelOutputValidationError,
    ModelRouter,
    RoutingFailure,
    RoutingFailureKind,
)


def _request() -> ImplementationGenerationRequest:
    content = "old\n"
    digest = sha256(content.encode()).hexdigest()
    source = SourceContextSnapshot(
        files=(SourceContextFile("app.py", digest, len(content), content),),
        digest=sha256(b"source-context").hexdigest(),
        total_bytes=len(content),
        excluded_secret_files=0,
        omitted_bounded_files=0,
    )
    return ImplementationGenerationRequest(
        work_specification_id="33333333-3333-3333-3333-333333333333",
        work_specification_revision=1,
        work_specification_digest=sha256(b"spec").hexdigest(),
        title="Change app",
        objective="Change old to new",
        constraints=("Preserve existing behavior outside the requested change.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="app.py contains new"),),
        source_context=source,
    )


def _proposal(request: ImplementationGenerationRequest) -> ImplementationProposal:
    source = request.source_context.files[0]
    return ImplementationProposal(
        acceptance_ids_covered=["AC-01"],
        patches=[
            GeneratedSourcePatch(
                path=source.path,
                expected_base_sha256=source.sha256,
                unified_diff="--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n",
            )
        ],
    )


class _OutputFailureProgram:
    version = "test-output-failure"

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
        del request
        raise ModelOutputValidationError("synthetic raw model output must not cross the boundary")


class _ProviderFailureProgram:
    version = "test-provider-failure"

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
        del request
        raise RuntimeError("synthetic provider payload must not cross the boundary")


class _SuccessProgram:
    version = "test-success"

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
        return _proposal(request)


class _FakeDspy:
    def context(self, **_kwargs):
        return nullcontext()


class _MalformedPredictionProgram:
    def __call__(self, **_kwargs):
        return SimpleNamespace(
            proposal_json='{"acceptance_ids_covered":"AC-01","patches":[]}'
        )


def test_dspy_program_wraps_pydantic_decode_failure_without_raw_output():
    program = DspyImplementationGenerationProgram.__new__(DspyImplementationGenerationProgram)
    program._dspy = _FakeDspy()
    program._lm = object()
    program._program = _MalformedPredictionProgram()

    with pytest.raises(ModelOutputValidationError) as captured:
        program.run(request=_request())

    assert "synthetic" not in str(captured.value)
    assert "proposal_json" not in str(captured.value)
    assert "acceptance_ids_covered" not in str(captured.value)
    assert captured.value.__cause__ is None


def test_output_validation_falls_through_to_next_hosted_model():
    def factory(model: str):
        if model == "openai/gpt-5.6-luna":
            return _OutputFailureProgram()
        return _SuccessProgram()

    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(("openai/gpt-5.6-luna", "openai/gpt-5.6-terra")),
        program_factory=factory,
    )

    result = coordinator.generate_sync(_request())

    assert result.model == "openai/gpt-5.6-terra"
    assert [attempt.status for attempt in result.attempts] == ["validation_failed", "ok"]
    assert result.attempts[0].error is None


def test_all_structured_output_failures_are_validation_exhaustion():
    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(("openai/gpt-5.6-luna", "openai/gpt-5.6-terra")),
        program_factory=lambda _model: _OutputFailureProgram(),
    )

    with pytest.raises(ImplementationGenerationFailure) as captured:
        coordinator.generate_sync(_request())

    evidence = captured.value.diagnostic_evidence
    assert evidence is not None
    routing = evidence["routing_failure"]
    assert routing["reason_code"] == RoutingFailureKind.VALIDATION_EXHAUSTED.value
    assert routing["attempt_count"] == 2
    assert routing["attempts"] == [
        {
            "status": "validation_failed",
            "provider_kind": "vercel_ai_gateway",
            "error_class": None,
        },
        {
            "status": "validation_failed",
            "provider_kind": "vercel_ai_gateway",
            "error_class": None,
        },
    ]
    assert routing["raw_model_output_persisted"] is False
    assert routing["raw_provider_payload_persisted"] is False
    assert "synthetic raw model output" not in str(evidence)


def test_generic_program_exception_remains_provider_failure():
    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(("openai/gpt-5.6-luna",)),
        program_factory=lambda _model: _ProviderFailureProgram(),
    )

    with pytest.raises(ImplementationGenerationFailure) as captured:
        coordinator.generate_sync(_request())

    evidence = captured.value.diagnostic_evidence
    assert evidence is not None
    routing = evidence["routing_failure"]
    assert routing["reason_code"] == RoutingFailureKind.PROVIDER_EXHAUSTED.value
    assert routing["attempts"] == [
        {
            "status": "provider_failed",
            "provider_kind": "vercel_ai_gateway",
            "error_class": "RuntimeError",
        }
    ]
    assert "synthetic provider payload" not in str(evidence)


def test_mixed_output_validation_and_provider_failure_stays_provider_exhausted():
    def factory(model: str):
        if model == "openai/gpt-5.6-luna":
            return _OutputFailureProgram()
        return _ProviderFailureProgram()

    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(("openai/gpt-5.6-luna", "openai/gpt-5.6-terra")),
        program_factory=factory,
    )

    with pytest.raises(ImplementationGenerationFailure) as captured:
        coordinator.generate_sync(_request())

    evidence = captured.value.diagnostic_evidence
    assert evidence is not None
    routing = evidence["routing_failure"]
    assert routing["reason_code"] == RoutingFailureKind.PROVIDER_EXHAUSTED.value
    assert [attempt["status"] for attempt in routing["attempts"]] == [
        "validation_failed",
        "provider_failed",
    ]


def test_rate_limit_chain_classification_is_unchanged():
    class LMRateLimitError(RuntimeError):
        pass

    router = ModelRouter(("openai/gpt-5.6-luna", "openai/gpt-5.6-terra"))

    async def attempt(_model: str):
        raise LMRateLimitError("synthetic rate-limit body")

    with pytest.raises(RoutingFailure) as captured:
        asyncio.run(router.route(attempt, lambda _proposal: True))

    routing_failure = captured.value
    assert routing_failure.kind == RoutingFailureKind.RATE_LIMITED
    assert all(item.status == "provider_failed" for item in routing_failure.attempts)
    assert all(item.error == "LMRateLimitError" for item in routing_failure.attempts)


def test_typed_output_validation_is_only_admitted_from_attempt_boundary():
    router = ModelRouter(("openai/gpt-5.6-luna",))

    async def attempt(_model: str):
        return object()

    def validator(_proposal):
        raise ModelOutputValidationError("validator should remain outside typed attempt authority")

    with pytest.raises(RoutingFailure) as captured:
        asyncio.run(router.route(attempt, validator))

    failure = captured.value
    assert failure.kind == RoutingFailureKind.PROVIDER_EXHAUSTED
    assert failure.attempts[0].status == "provider_failed"
    assert failure.attempts[0].error == "ModelOutputValidationError"


def test_prompt_contract_names_exact_strict_json_shape_without_parser_relaxation():
    assert "acceptance_ids_covered" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "patches" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "path" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "expected_base_sha256" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "unified_diff" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "Do not wrap" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "code fences" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
