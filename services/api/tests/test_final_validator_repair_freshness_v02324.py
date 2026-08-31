from __future__ import annotations

from hashlib import sha256
import logging

import pytest

from parallax_api.code.agentic_candidate_recovery import (
    FINAL_VALIDATOR_REPAIR_GUIDANCE,
    MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
    VALIDATOR_REPAIR_GUIDANCE,
    final_validator_repair_context_token,
    final_validator_repair_request,
    validator_guided_candidate_request,
)
from parallax_api.code.agentic_runtime import AgenticRuntimeError
from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    ImplementationGenerationRequest,
)
from parallax_api.intelligence.router import RoutingFailureKind


def _request() -> ImplementationGenerationRequest:
    content = "old\n"
    digest = sha256(content.encode()).hexdigest()
    source = SourceContextSnapshot(
        files=(SourceContextFile("app.py", digest, len(content), content),),
        digest=sha256(b"source-context-p2324").hexdigest(),
        total_bytes=len(content),
        excluded_secret_files=0,
        omitted_bounded_files=0,
    )
    return ImplementationGenerationRequest(
        work_specification_id="44444444-4444-4444-4444-444444444444",
        work_specification_revision=2,
        work_specification_digest=sha256(b"spec-p2324").hexdigest(),
        title="Change app",
        objective="Sensitive objective text must never be logged.",
        constraints=("Preserve existing behavior outside the requested change.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="app.py contains new"),),
        source_context=source,
    )


def test_final_repair_request_is_cache_distinct_from_prior_guided_request(caplog) -> None:
    request = _request()
    guided = validator_guided_candidate_request(
        request,
        RoutingFailureKind.VALIDATION_EXHAUSTED.value,
    )
    final, token = final_validator_repair_request(
        guided,
        run_revision=11,
        work_unit_id="unit-implementation",
        generation=4,
    )

    assert final is not guided
    assert guided.contract_payload() != final.contract_payload()
    assert final.constraints[:-1] == guided.constraints
    assert VALIDATOR_REPAIR_GUIDANCE in guided.constraints
    assert FINAL_VALIDATOR_REPAIR_GUIDANCE in final.constraints[-1]
    assert token in final.constraints[-1]
    assert len(token) == 24
    assert all(ch in "0123456789abcdef" for ch in token)
    assert MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT == 1

    with caplog.at_level(logging.INFO, logger="parallax_api.code.agentic_candidate_recovery"):
        logging.getLogger("parallax_api.code.agentic_candidate_recovery").info(
            "parallax_final_validator_repair_dispatch generation=%s context=%s",
            4,
            token,
        )
    expected = f"parallax_final_validator_repair_dispatch generation=4 context={token}"
    messages = [record.getMessage() for record in caplog.records]
    assert messages == [expected]
    assert "unit-implementation" not in caplog.text
    assert request.objective not in caplog.text


def test_final_repair_context_is_deterministic_and_changes_with_retry_identity() -> None:
    request = _request()
    guided = validator_guided_candidate_request(
        request,
        RoutingFailureKind.VALIDATION_EXHAUSTED.value,
    )
    first, token1 = final_validator_repair_request(
        guided,
        run_revision=11,
        work_unit_id="unit-implementation",
        generation=4,
    )
    same, token_same = final_validator_repair_request(
        guided,
        run_revision=11,
        work_unit_id="unit-implementation",
        generation=4,
    )
    later_revision, token2 = final_validator_repair_request(
        guided,
        run_revision=12,
        work_unit_id="unit-implementation",
        generation=4,
    )
    later_generation, token3 = final_validator_repair_request(
        guided,
        run_revision=11,
        work_unit_id="unit-implementation",
        generation=5,
    )
    other_unit, token4 = final_validator_repair_request(
        guided,
        run_revision=11,
        work_unit_id="unit-tests",
        generation=4,
    )

    assert token1 == token_same
    assert first.contract_payload() == same.contract_payload()
    assert len({token1, token2, token3, token4}) == 4
    assert len(
        {
            str(first.contract_payload()),
            str(later_revision.contract_payload()),
            str(later_generation.contract_payload()),
            str(other_unit.contract_payload()),
        }
    ) == 4


@pytest.mark.parametrize(
    ("run_revision", "work_unit_id", "generation"),
    (
        (-1, "unit", 1),
        (1, " unit", 1),
        (1, "unit", True),
        (1, "unit\nbad", 1),
    ),
)
def test_final_repair_context_fails_closed(
    run_revision: int,
    work_unit_id: str,
    generation: int,
) -> None:
    with pytest.raises(AgenticRuntimeError):
        final_validator_repair_context_token(
            run_revision=run_revision,
            work_unit_id=work_unit_id,
            generation=generation,
        )


def test_ordinary_validator_guidance_never_receives_final_only_constraint() -> None:
    request = _request()
    initial = validator_guided_candidate_request(request, None)
    assert initial is request
    assert all(FINAL_VALIDATOR_REPAIR_GUIDANCE not in item for item in initial.constraints)

    guided = validator_guided_candidate_request(
        request,
        RoutingFailureKind.VALIDATION_EXHAUSTED.value,
    )
    assert VALIDATOR_REPAIR_GUIDANCE in guided.constraints
    assert all(FINAL_VALIDATOR_REPAIR_GUIDANCE not in item for item in guided.constraints)
