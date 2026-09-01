from __future__ import annotations

import os
from pathlib import Path
import sys


_API_ROOT = Path(__file__).resolve().parent.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from parallax_api.code.agentic_runtime import (
    CandidateValidationResult,
    VercelCandidateValidationExecutor,
)
from parallax_api.code.validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    resolve_execution_contract,
)


_FIXTURE_ROOT = _API_ROOT / "tests" / "fixtures" / "static_web_canary"
_EXPECTED_STAGES = ("BUILD", "TEST", "VERIFY")


def _require_full_success(result: CandidateValidationResult) -> None:
    stages = tuple(stage for stage, _ in result.stage_evidence)
    if stages != _EXPECTED_STAGES:
        raise RuntimeError("production candidate-validation canary did not execute all protected stages")
    if not result.passed:
        raise RuntimeError("production candidate-validation canary failed protected validation")
    if any(evidence.get("protected_success") is not True for _, evidence in result.stage_evidence):
        raise RuntimeError("production candidate-validation canary stage evidence is not fully successful")
    if any(evidence.get("candidate_is_canonical_lineage") is not False for _, evidence in result.stage_evidence):
        raise RuntimeError("production candidate-validation canary claimed canonical lineage authority")
    if any(evidence.get("accepts_source_lineage") is not False for _, evidence in result.stage_evidence):
        raise RuntimeError("production candidate-validation canary claimed source-lineage acceptance authority")


def run_canary(*, executor: VercelCandidateValidationExecutor | None = None) -> CandidateValidationResult:
    project_id = (os.getenv("VERCEL_PROJECT_ID") or "").strip()
    if not project_id:
        raise RuntimeError("production candidate-validation canary requires Vercel project identity")
    if not _FIXTURE_ROOT.is_dir() or _FIXTURE_ROOT.is_symlink():
        raise RuntimeError("production candidate-validation canary fixture is unavailable")

    contract = resolve_execution_contract(
        ExecutionContractCode.STATIC_WEB.value,
        binding_reason=ExecutionBindingReason.GREENFIELD_STATIC_WEB.value,
        target=None,
    )
    active = executor or VercelCandidateValidationExecutor(project_id=project_id)
    result = active.validate_candidate(
        _FIXTURE_ROOT.resolve(strict=True),
        operation_key="production:static-web-candidate-canary",
        validation_profile=contract.validation_profile,
    )
    if result.validation_profile_id != contract.validation_profile.profile_id.value:
        raise RuntimeError("production candidate-validation canary profile identity drifted")
    if result.validation_profile_digest != contract.validation_profile.digest:
        raise RuntimeError("production candidate-validation canary profile digest drifted")
    _require_full_success(result)
    return result


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "production":
        print("Production candidate-validation canary: SKIP (non-production)")
        return
    result = run_canary()
    print(
        "Production candidate-validation canary: PASS "
        "(contract=static-web-v1; binding=GREENFIELD_STATIC_WEB; ecosystem=static-web; "
        f"profile={result.validation_profile_id}; stages=BUILD,TEST,VERIFY; "
        f"candidate_digest={result.content_digest})"
    )


if __name__ == "__main__":
    main()
