from __future__ import annotations

from parallax_api.code.implementation_runtime import ImplementationContractError


def diagnostic():
    return {"candidate_validation_failure": {
        "candidate_id": "candidate-1", "failed_stage": "BUILD", "protected_success": False,
        "exit_code_present": False, "exit_code": None, "timed_out": False,
        "validation_profile_id": "dotnet-solution-v1", "validation_profile_digest": "a" * 64,
        "candidate_content_digest": "b" * 64,
        "dependency_preparation_code": "DEPENDENCY_PREPARATION_FAILED",
        "dependency_preparation_required": True, "dependency_preparation_succeeded": False,
        "dependency_probe_exit_code": 0, "dependency_prepare_exit_code": 1,
        "dependency_stdout_digest": "c" * 64, "dependency_stderr_digest": "d" * 64,
        "validation_network_locked": True, "candidate_is_canonical_lineage": False,
        "accepts_source_lineage": False, "source_lineage_accepted": False, "production_deployed": False,
    }}


def test_bounded_prepare_diagnostics_survive_contract_boundary():
    exc = ImplementationContractError("failed", diagnostic_evidence=diagnostic())
    failure = exc.diagnostic_evidence["candidate_validation_failure"]
    assert failure["dependency_preparation_code"] == "DEPENDENCY_PREPARATION_FAILED"
    assert failure["dependency_probe_exit_code"] == 0
    assert failure["dependency_prepare_exit_code"] == 1
    assert failure["validation_network_locked"] is True


def test_raw_prepare_material_is_rejected():
    value = diagnostic()
    value["candidate_validation_failure"]["dependency_raw_output"] = "Bearer must-never-persist"
    assert ImplementationContractError("failed", diagnostic_evidence=value).diagnostic_evidence is None


def test_unknown_prepare_code_is_rejected():
    value = diagnostic()
    value["candidate_validation_failure"]["dependency_preparation_code"] = "WIDEN_NETWORK_AND_RETRY"
    assert ImplementationContractError("failed", diagnostic_evidence=value).diagnostic_evidence is None
