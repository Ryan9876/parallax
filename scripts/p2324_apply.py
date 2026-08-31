from pathlib import Path

source_path = Path("services/api/parallax_api/code/agentic_candidate_recovery.py")
text = source_path.read_text(encoding="utf-8")
old = 'from dataclasses import dataclass, replace\nfrom typing import Callable\n'
new = 'from dataclasses import dataclass, replace\nfrom hashlib import sha256\nimport json\nimport logging\nfrom typing import Callable\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

old = 'CANDIDATE_RECOVERY_VERSION = "candidate-recovery-v0.23.23"\nCANDIDATE_GENERATION_EXHAUSTED = "CANDIDATE_GENERATION_EXHAUSTED"\nCANDIDATE_VALIDATION_REPAIR = "CANDIDATE_VALIDATION_REPAIR"\nMAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT = 1\n_CANDIDATE_EXHAUSTED_BLOCKER = "AGENTIC_CANDIDATE_EXHAUSTED"\nVALIDATOR_REPAIR_GUIDANCE = (\n'
new = 'CANDIDATE_RECOVERY_VERSION = "candidate-recovery-v0.23.24"\nCANDIDATE_GENERATION_EXHAUSTED = "CANDIDATE_GENERATION_EXHAUSTED"\nCANDIDATE_VALIDATION_REPAIR = "CANDIDATE_VALIDATION_REPAIR"\nMAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT = 1\n_CANDIDATE_EXHAUSTED_BLOCKER = "AGENTIC_CANDIDATE_EXHAUSTED"\n_FINAL_VALIDATOR_REPAIR_CONTEXT_DOMAIN = "parallax-final-validator-repair-context-v1"\n_FINAL_VALIDATOR_REPAIR_CONTEXT_TOKEN_HEX = 24\nlogger = logging.getLogger(__name__)\nVALIDATOR_REPAIR_GUIDANCE = (\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

old = ')\n_BOUNDED_ROUTING_FAILURES = frozenset(item.value for item in RoutingFailureKind)\n'
new = ')\nFINAL_VALIDATOR_REPAIR_GUIDANCE = (\n    "This is the single final validator-repair generation for this work unit. "\n    "Re-derive a fresh proposal from the supplied protected source context instead of reusing or repeating any prior response. "\n    "Re-check every target path, base SHA-256, unified diff header, hunk coordinate and count, and every removed/context line "\n    "against the supplied source before returning the proposal."\n)\n_BOUNDED_ROUTING_FAILURES = frozenset(item.value for item in RoutingFailureKind)\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

old = 'def candidate_recovery_assignment(\n'
new = 'def final_validator_repair_context_token(\n    *,\n    run_revision: int,\n    work_unit_id: str,\n    generation: int,\n) -> str:\n    if (\n        not isinstance(run_revision, int)\n        or isinstance(run_revision, bool)\n        or run_revision < 0\n    ):\n        raise AgenticRuntimeError("final validator repair run revision must be a non-negative integer")\n    if (\n        not isinstance(generation, int)\n        or isinstance(generation, bool)\n        or generation < 0\n    ):\n        raise AgenticRuntimeError("final validator repair generation must be a non-negative integer")\n    if (\n        not isinstance(work_unit_id, str)\n        or not work_unit_id\n        or len(work_unit_id) > 180\n        or work_unit_id.strip() != work_unit_id\n        or any(ord(ch) < 32 for ch in work_unit_id)\n    ):\n        raise AgenticRuntimeError("final validator repair work-unit identity is invalid")\n\n    payload = json.dumps(\n        {\n            "domain": _FINAL_VALIDATOR_REPAIR_CONTEXT_DOMAIN,\n            "generation": generation,\n            "run_revision": run_revision,\n            "work_unit_id": work_unit_id,\n        },\n        sort_keys=True,\n        separators=(",", ":"),\n    ).encode("utf-8")\n    return sha256(payload).hexdigest()[:_FINAL_VALIDATOR_REPAIR_CONTEXT_TOKEN_HEX]\n\n\ndef final_validator_repair_request(\n    request: ImplementationGenerationRequest,\n    *,\n    run_revision: int,\n    work_unit_id: str,\n    generation: int,\n) -> tuple[ImplementationGenerationRequest, str]:\n    guided = validator_guided_candidate_request(\n        request,\n        RoutingFailureKind.VALIDATION_EXHAUSTED.value,\n    )\n    context_token = final_validator_repair_context_token(\n        run_revision=run_revision,\n        work_unit_id=work_unit_id,\n        generation=generation,\n    )\n    final_constraint = (\n        f"{FINAL_VALIDATOR_REPAIR_GUIDANCE} "\n        f"Server-owned final-repair context token: {context_token}."\n    )\n    if final_constraint in guided.constraints:\n        return guided, context_token\n    return (\n        replace(\n            guided,\n            constraints=(*guided.constraints, final_constraint),\n        ),\n        context_token,\n    )\n\n\ndef candidate_recovery_assignment(\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

old = '                        subrequest = validator_guided_candidate_request(\n                            subrequest,\n                            previous_failure_kind,\n                        )\n                        adapter = self._adapter(agent_digest)\n                        try:\n'
new = '                        subrequest = validator_guided_candidate_request(\n                            subrequest,\n                            previous_failure_kind,\n                        )\n                        if assignment.reason_code == CANDIDATE_VALIDATION_REPAIR:\n                            subrequest, repair_context_token = final_validator_repair_request(\n                                subrequest,\n                                run_revision=run.revision,\n                                work_unit_id=unit.unit_id,\n                                generation=assignment.generation,\n                            )\n                            logger.info(\n                                "parallax_final_validator_repair_dispatch generation=%s context=%s",\n                                assignment.generation,\n                                repair_context_token,\n                            )\n                        adapter = self._adapter(agent_digest)\n                        try:\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

old = '    "CandidateRejection",\n    "ResilientLiveAgenticControlPlane",\n    "VALIDATOR_REPAIR_GUIDANCE",\n'
new = '    "CandidateRejection",\n    "FINAL_VALIDATOR_REPAIR_GUIDANCE",\n    "ResilientLiveAgenticControlPlane",\n    "VALIDATOR_REPAIR_GUIDANCE",\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

old = '    "candidate_generation_failure_kind",\n    "candidate_recovery_assignment",\n    "validator_guided_candidate_request",\n    "validator_repair_assignment",\n]\n'
new = '    "candidate_generation_failure_kind",\n    "candidate_recovery_assignment",\n    "final_validator_repair_context_token",\n    "final_validator_repair_request",\n    "validator_guided_candidate_request",\n    "validator_repair_assignment",\n]\n'
assert old in text, old[:120]
text = text.replace(old, new, 1)

source_path.write_text(text, encoding="utf-8")

test_path = Path("services/api/tests/test_final_validator_repair_freshness_v02324.py")
test_path.write_text('''from __future__ import annotations

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
    content = "old\\n"
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
        (1, "unit\\nbad", 1),
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
''', encoding='utf-8')

architecture_path = Path("ARCHITECTURE.md")
architecture = architecture_path.read_text(encoding="utf-8")
assert architecture.startswith("# Parallax 2.0 Architecture\n\nVersion: 3.34\nStatus: Authoritative\n")
architecture = architecture.replace("Version: 3.34", "Version: 3.35", 1)
anchor = "## Version relationship\n\n"
assert anchor in architecture
architecture = architecture.replace(anchor, anchor + 'Architecture v3.35 makes the single P2-V0.23.23 final validator-repair opportunity a genuinely fresh generation identity. The existing eligibility, admitted-agent selection, one-repair ceiling, 60-second hosted-model timeout, zero hidden transport retries, safe patch validation/canonicalization, disposable candidate validation, source-lineage authority, delivery authority, lifecycle authority, and human REVIEW ceiling remain unchanged. A final `CANDIDATE_VALIDATION_REPAIR` assignment now receives the existing static validator guidance plus a final-repair-only server-owned constraint carrying a bounded deterministic context token derived from the authoritative run revision, work-unit identity, and assignment generation. This changes the model request/cache identity so an earlier validator-rejected prediction cannot be counted as the new repair generation. The token is evidence only, contains no source or rejected output, grants no authority, and only a fixed event name, repair generation, and bounded token may be logged. Global DSPy caching, provider/model/credential authority, and all mutation/review boundaries are unchanged. Architecture v3.34 remains the finite validator-repair eligibility foundation.\n\n', 1)
architecture_path.write_text(architecture, encoding="utf-8")
