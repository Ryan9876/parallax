from __future__ import annotations

from pathlib import Path

from parallax_api.code.agentic_runtime import VercelCandidateValidationExecutor
from parallax_api.code.domain import WorkflowStage
from parallax_api.code.validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    resolve_execution_contract,
)


_FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "static_web_canary"
_EXPECTED_STAGES = (
    WorkflowStage.BUILD.value,
    WorkflowStage.TEST.value,
    WorkflowStage.VERIFY.value,
)


def main() -> None:
    if not _FIXTURE.is_dir() or _FIXTURE.is_symlink():
        raise RuntimeError("production candidate canary fixture is unavailable")

    contract = resolve_execution_contract(
        ExecutionContractCode.STATIC_WEB.value,
        binding_reason=ExecutionBindingReason.GREENFIELD_STATIC_WEB.value,
        target=None,
    )
    executor = VercelCandidateValidationExecutor()
    result = executor.validate_candidate(
        _FIXTURE.resolve(strict=True),
        operation_key="production-static-web-candidate-canary",
        validation_profile=contract.validation_profile,
    )

    stages = tuple(stage for stage, _ in result.stage_evidence)
    if stages != _EXPECTED_STAGES:
        raise RuntimeError("production candidate canary did not execute exact BUILD/TEST/VERIFY sequence")
    if not result.passed:
        raise RuntimeError("production candidate canary protected validation failed")
    if any(evidence.get("protected_success") is not True for _, evidence in result.stage_evidence):
        raise RuntimeError("production candidate canary lacks protected stage success")
    if any(evidence.get("candidate_is_canonical_lineage") is not False for _, evidence in result.stage_evidence):
        raise RuntimeError("production candidate canary claimed canonical lineage authority")
    if any(evidence.get("accepts_source_lineage") is not False for _, evidence in result.stage_evidence):
        raise RuntimeError("production candidate canary claimed source-lineage acceptance authority")

    print(
        "Production candidate validation canary: PASS "
        f"profile={result.validation_profile_id} stages={','.join(stages)} files={result.file_count}"
    )


if __name__ == "__main__":
    main()
