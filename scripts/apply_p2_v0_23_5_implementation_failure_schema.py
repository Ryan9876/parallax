from __future__ import annotations

from pathlib import Path


runtime = Path("services/api/parallax_api/code/implementation_runtime.py")
text = runtime.read_text(encoding="utf-8")
old = '        "candidate_content_digest",\n        "candidate_is_canonical_lineage",\n'
new = (
    '        "candidate_content_digest",\n'
    '        "dependency_preparation_code",\n'
    '        "dependency_preparation_required",\n'
    '        "dependency_preparation_succeeded",\n'
    '        "dependency_probe_exit_code",\n'
    '        "dependency_prepare_exit_code",\n'
    '        "dependency_stdout_digest",\n'
    '        "dependency_stderr_digest",\n'
    '        "validation_network_locked",\n'
    '        "candidate_is_canonical_lineage",\n'
)
if old not in text:
    raise RuntimeError("allowed-field anchor not found")
text = text.replace(old, new, 1)

anchor = '    for key in ("invocation_digest", "stdout_digest", "stderr_digest", "candidate_content_digest"):\n'
if anchor not in text:
    raise RuntimeError("digest anchor not found")
block = '''    preparation_code = raw.get("dependency_preparation_code")
    if preparation_code is not None:
        if preparation_code not in {
            "NOT_REQUIRED",
            "READY",
            "EXECUTION_PROFILE_UNAVAILABLE",
            "DEPENDENCY_PREPARATION_FAILED",
            "VALIDATION_NETWORK_LOCK_FAILED",
        }:
            raise ValueError("candidate validation diagnostics contain an invalid dependency preparation code")
        normalized_failure["dependency_preparation_code"] = preparation_code

    for key in (
        "dependency_preparation_required",
        "dependency_preparation_succeeded",
        "validation_network_locked",
    ):
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, bool):
            raise ValueError("candidate validation diagnostics contain an invalid dependency preparation boolean")
        normalized_failure[key] = value

    for key in ("dependency_probe_exit_code", "dependency_prepare_exit_code"):
        if key not in raw:
            continue
        value = raw[key]
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise ValueError("candidate validation diagnostics contain an invalid dependency preparation exit code")
        normalized_failure[key] = value

    for key in (
        "invocation_digest",
        "stdout_digest",
        "stderr_digest",
        "candidate_content_digest",
        "dependency_stdout_digest",
        "dependency_stderr_digest",
    ):
'''
text = text.replace(anchor, block, 1)
runtime.write_text(text, encoding="utf-8")

test = Path("services/api/tests/test_implementation_failure_preparation_diagnostics.py")
test.write_text('''from __future__ import annotations

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
''', encoding="utf-8")
