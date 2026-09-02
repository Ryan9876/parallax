from __future__ import annotations

import re


class ProtectedEvidenceError(ValueError):
    pass


ACCEPTANCE_ID = re.compile(r"\bAC-\d+\b")
FORBIDDEN_KEYS = {"chain_of_thought", "scratchpad", "reasoning", "secret", "environment"}
FORBIDDEN_CLAIMS = {"merged", "deployed", "deployment-verified", "production-ready"}
STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE = "STRUCTURAL_ONLY"


def _safe_mapping(payload: dict[str, object]) -> None:
    lowered = {key.casefold() for key in payload}
    if lowered & FORBIDDEN_KEYS:
        raise ProtectedEvidenceError("protected evidence contains a forbidden field")


def _exact_acceptance_ids(payload: dict[str, object], key: str, required: set[str]) -> None:
    raw = payload.get(key)
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ProtectedEvidenceError(f"{key} must be a list of acceptance IDs")
    if len(raw) != len(set(raw)):
        raise ProtectedEvidenceError(f"{key} contains duplicate acceptance IDs")
    if set(raw) != required:
        raise ProtectedEvidenceError(f"{key} does not exactly match the protected acceptance map")


def validate_specification_binding(
    evidence: dict[str, object],
    *,
    specification_id: str,
    specification_revision: int,
    specification_digest: str,
    required_acceptance_ids: set[str],
) -> None:
    _safe_mapping(evidence)
    if evidence.get("work_specification_id") != specification_id:
        raise ProtectedEvidenceError("SPECIFY evidence does not match the bound work specification")
    if evidence.get("work_specification_revision") != specification_revision:
        raise ProtectedEvidenceError("SPECIFY evidence does not match the bound work specification revision")
    if evidence.get("work_specification_digest") != specification_digest:
        raise ProtectedEvidenceError("SPECIFY evidence does not match the bound work specification digest")
    _exact_acceptance_ids(evidence, "acceptance_ids", required_acceptance_ids)


def validate_plan(plan: dict[str, object], required_acceptance_ids: set[str]) -> None:
    _safe_mapping(plan)
    _exact_acceptance_ids(plan, "acceptance_ids_covered", required_acceptance_ids)
    if not plan.get("work_items") or not plan.get("validation_checks"):
        raise ProtectedEvidenceError("plan lacks executable work or validation items")


def validate_implementation(evidence: dict[str, object]) -> None:
    _safe_mapping(evidence)
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ProtectedEvidenceError("IMPLEMENT requires code artifact evidence")
    if not evidence.get("base_revision") or not evidence.get("workspace_digest"):
        raise ProtectedEvidenceError("IMPLEMENT requires base and resulting workspace identity")


def _validate_execution_success(evidence: dict[str, object]) -> None:
    _safe_mapping(evidence)
    if evidence.get("protected_success") is not True or evidence.get("exit_code") != 0 or evidence.get("timed_out"):
        raise ProtectedEvidenceError("execution evidence does not prove protected success")


def validate_execution(
    evidence: dict[str, object],
    required_acceptance_ids: set[str],
    *,
    acceptance_key: str,
) -> None:
    _validate_execution_success(evidence)
    _exact_acceptance_ids(evidence, acceptance_key, required_acceptance_ids)


def validate_structural_execution(
    evidence: dict[str, object],
    required_acceptance_ids: set[str],
) -> None:
    _validate_execution_success(evidence)
    if evidence.get("acceptance_verification_scope") != STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE:
        raise ProtectedEvidenceError("structural execution evidence has an invalid verification scope")
    _exact_acceptance_ids(evidence, "acceptance_ids_targeted", required_acceptance_ids)
    _exact_acceptance_ids(evidence, "acceptance_ids_unverified", required_acceptance_ids)
    verified = evidence.get("acceptance_ids_verified")
    if not isinstance(verified, list) or not all(isinstance(item, str) for item in verified):
        raise ProtectedEvidenceError("acceptance_ids_verified must be a list of acceptance IDs")
    if len(verified) != len(set(verified)):
        raise ProtectedEvidenceError("acceptance_ids_verified contains duplicate acceptance IDs")
    if verified:
        raise ProtectedEvidenceError("structural execution cannot claim protected acceptance verification")


def validate_review(evidence: dict[str, object], required_acceptance_ids: set[str], current_workspace_digest: str) -> None:
    _safe_mapping(evidence)
    if evidence.get("recommendation") != "PASS":
        raise ProtectedEvidenceError("review did not recommend PASS")
    _exact_acceptance_ids(evidence, "acceptance_ids_verified", required_acceptance_ids)
    if evidence.get("workspace_digest") != current_workspace_digest:
        raise ProtectedEvidenceError("review evidence is stale")
    claims = {str(value).casefold() for value in evidence.get("claims", [])}
    if claims & FORBIDDEN_CLAIMS:
        raise ProtectedEvidenceError("review makes an unsupported release claim")
