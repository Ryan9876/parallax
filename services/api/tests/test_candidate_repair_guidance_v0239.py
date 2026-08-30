from __future__ import annotations

from hashlib import sha256

import pytest

from parallax_api.code.agentic_candidate_recovery import (
    VALIDATOR_REPAIR_GUIDANCE,
    candidate_generation_failure_kind,
    validator_guided_candidate_request,
)
from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    GeneratedSourcePatch,
    ImplementationGenerationCoordinator,
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    STRICT_SAFE_PATCH_RULE,
)
from parallax_api.intelligence.router import ModelRouter, RoutingFailureKind


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


class _ProposalProgram:
    version = "test-program"

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
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


class _ProviderFailureProgram:
    version = "test-provider-failure"

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
        del request
        raise RuntimeError("synthetic provider failure payload must not cross the boundary")


def test_generation_failure_projects_validation_exhaustion_without_raw_output():
    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(("openai/gpt-5.6-sol",)),
        program_factory=lambda _model: _ProposalProgram(),
    )

    with pytest.raises(ImplementationGenerationFailure) as captured:
        coordinator.generate_sync(_request(), proposal_validator=lambda _proposal: False)

    evidence = captured.value.diagnostic_evidence
    assert evidence is not None
    routing = evidence["routing_failure"]
    assert routing["reason_code"] == RoutingFailureKind.VALIDATION_EXHAUSTED.value
    assert routing["attempt_count"] == 1
    assert routing["attempts"] == [
        {
            "status": "validation_failed",
            "provider_kind": "vercel_ai_gateway",
            "error_class": None,
        }
    ]
    assert routing["raw_model_output_persisted"] is False
    assert routing["raw_provider_payload_persisted"] is False
    assert candidate_generation_failure_kind(captured.value) == RoutingFailureKind.VALIDATION_EXHAUSTED.value
    assert "synthetic" not in str(evidence)


def test_provider_failure_does_not_masquerade_as_validator_rejection():
    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(("openai/gpt-5.6-sol",)),
        program_factory=lambda _model: _ProviderFailureProgram(),
    )

    with pytest.raises(ImplementationGenerationFailure) as captured:
        coordinator.generate_sync(_request(), proposal_validator=lambda _proposal: True)

    evidence = captured.value.diagnostic_evidence
    assert evidence is not None
    routing = evidence["routing_failure"]
    assert routing["reason_code"] == RoutingFailureKind.PROVIDER_EXHAUSTED.value
    assert routing["attempts"][0]["status"] == "provider_failed"
    assert routing["attempts"][0]["error_class"] == "RuntimeError"
    assert candidate_generation_failure_kind(captured.value) == RoutingFailureKind.PROVIDER_EXHAUSTED.value
    assert "synthetic provider failure payload" not in str(evidence)


def test_validator_guidance_is_validation_only_bounded_and_idempotent():
    request = _request()

    guided = validator_guided_candidate_request(
        request,
        RoutingFailureKind.VALIDATION_EXHAUSTED.value,
    )
    assert guided is not request
    assert guided.constraints[:-1] == request.constraints
    assert guided.constraints[-1] == VALIDATOR_REPAIR_GUIDANCE
    assert "exact path" in VALIDATOR_REPAIR_GUIDANCE
    assert "lowercase SHA-256" in VALIDATOR_REPAIR_GUIDANCE
    assert "strict single-file" in VALIDATOR_REPAIR_GUIDANCE
    assert "exact hunk coordinates and counts" in VALIDATOR_REPAIR_GUIDANCE
    assert "secret material" in VALIDATOR_REPAIR_GUIDANCE

    guided_again = validator_guided_candidate_request(
        guided,
        RoutingFailureKind.VALIDATION_EXHAUSTED.value,
    )
    assert guided_again is guided

    provider_failure = validator_guided_candidate_request(
        request,
        RoutingFailureKind.PROVIDER_EXHAUSTED.value,
    )
    assert provider_failure is request


def test_initial_source_payload_also_carries_strict_safe_patch_contract():
    payload = _request().source_prompt_payload()
    assert payload["strict_safe_patch_rule"] == STRICT_SAFE_PATCH_RULE
    assert "exact path" in STRICT_SAFE_PATCH_RULE
    assert "SHA-256" in STRICT_SAFE_PATCH_RULE
    assert "strict single-file" in STRICT_SAFE_PATCH_RULE
    assert "hunk coordinates" in STRICT_SAFE_PATCH_RULE
