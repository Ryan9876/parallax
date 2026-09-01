from parallax_api.code.agentic_runtime import _candidate_admission_failure_diagnostic
from parallax_api.code.implementation_runtime import ImplementationRuntimeError, _bounded_implementation_failure_evidence
from parallax_api.code.validation_toolchains import ValidationProfileError, ValidationProfileReason

def test_execution_contract_diagnostic_is_closed_and_durable():
    diagnostic = _candidate_admission_failure_diagnostic(
        "candidate-primary",
        "EXECUTION_CONTRACT_VERIFICATION",
        ValidationProfileError(ValidationProfileReason.EXECUTION_CONTRACT_DRIFT),
    )
    admitted = _bounded_implementation_failure_evidence({"candidate_admission_failure": diagnostic})
    assert admitted["candidate_admission_failure"]["failure_kind"] == "VALIDATION_PROFILE_ERROR"
    assert admitted["candidate_admission_failure"]["reason_code"] == "EXECUTION_CONTRACT_DRIFT"
    assert admitted["candidate_admission_failure"]["production_deployed"] is False

def test_unknown_contract_reason_is_not_persisted():
    diagnostic = {
        "candidate_id": "candidate-primary",
        "phase": "EXECUTION_CONTRACT_VERIFICATION",
        "failure_kind": "VALIDATION_PROFILE_ERROR",
        "reason_code": "RAW_PROVIDER_DETAIL",
        "candidate_is_canonical_lineage": False,
        "accepts_source_lineage": False,
        "source_lineage_accepted": False,
        "engineering_run_transitioned": False,
        "review_completed": False,
        "production_deployed": False,
    }
    error = ImplementationRuntimeError("failure", diagnostic_evidence={"candidate_admission_failure": diagnostic})
    assert error.diagnostic_evidence is None
