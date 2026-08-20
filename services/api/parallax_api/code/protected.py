from __future__ import annotations

from dataclasses import dataclass
import re


class ProtectedEvidenceError(ValueError):
    pass


ACCEPTANCE_ID = re.compile(r"\bAC-\d+\b")
FORBIDDEN_KEYS = {"chain_of_thought", "scratchpad", "reasoning", "secret", "environment"}
FORBIDDEN_CLAIMS = {"merged", "deployed", "deployment-verified", "production-ready"}


def _safe_mapping(payload: dict[str, object]) -> None:
    lowered = {key.casefold() for key in payload}
    if lowered & FORBIDDEN_KEYS:
        raise ProtectedEvidenceError("protected evidence contains a forbidden field")


def validate_plan(plan: dict[str, object], required_acceptance_ids: set[str]) -> None:
    _safe_mapping(plan)
    represented = set(plan.get("acceptance_ids_covered", []))
    if represented != required_acceptance_ids:
        raise ProtectedEvidenceError("plan does not exactly cover the protected acceptance map")
    if not plan.get("work_items") or not plan.get("validation_checks"):
        raise ProtectedEvidenceError("plan lacks executable work or validation items")


def validate_implementation(evidence: dict[str, object]) -> None:
    _safe_mapping(evidence)
    artifacts = evidence.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ProtectedEvidenceError("IMPLEMENT requires code artifact evidence")
    if not evidence.get("base_revision") or not evidence.get("workspace_digest"):
        raise ProtectedEvidenceError("IMPLEMENT requires base and resulting workspace identity")


def validate_execution(evidence: dict[str, object]) -> None:
    _safe_mapping(evidence)
    if evidence.get("protected_success") is not True or evidence.get("exit_code") != 0 or evidence.get("timed_out"):
        raise ProtectedEvidenceError("execution evidence does not prove protected success")


def validate_review(evidence: dict[str, object], required_acceptance_ids: set[str], current_workspace_digest: str) -> None:
    _safe_mapping(evidence)
    if evidence.get("recommendation") != "PASS":
        raise ProtectedEvidenceError("review did not recommend PASS")
    if set(evidence.get("acceptance_ids_verified", [])) != required_acceptance_ids:
        raise ProtectedEvidenceError("review lacks complete acceptance evidence")
    if evidence.get("workspace_digest") != current_workspace_digest:
        raise ProtectedEvidenceError("review evidence is stale")
    claims = {str(value).casefold() for value in evidence.get("claims", [])}
    if claims & FORBIDDEN_CLAIMS:
        raise ProtectedEvidenceError("review makes an unsupported release claim")
