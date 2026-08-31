from __future__ import annotations

from pathlib import Path


RECOVERY = Path("services/api/parallax_api/code/agentic_candidate_recovery.py")
RUNTIME = Path("services/api/parallax_api/code/implementation_runtime.py")
TEST = Path("services/api/tests/test_cross_work_unit_convergence_v02328.py")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"{label} seam not found")
    if text.count(old) != 1:
        raise SystemExit(f"{label} seam is not unique")
    return text.replace(old, new, 1)


def patch_recovery() -> None:
    text = RECOVERY.read_text()
    text = replace_once(
        text,
        """    def evaluate(\n        self,\n        proposal: ImplementationProposal,\n        *,\n        reserved_paths: tuple[str, ...] = (),\n    ) -> IncrementalConvergenceResult:\n""",
        """    def evaluate(\n        self,\n        proposal: ImplementationProposal,\n        *,\n        reserved_paths: tuple[str, ...] = (),\n        prefix_patches: tuple[GeneratedSourcePatch, ...] = (),\n    ) -> IncrementalConvergenceResult:\n""",
        "incremental accumulator signature",
    )
    text = replace_once(
        text,
        """        for patch in accepted:\n            self._retained[patch.path] = patch\n""",
        """        if prefix_patches:\n            plan_prefix = ImplementationProposal(\n                acceptance_ids_covered=list(self.acceptance_ids),\n                patches=[*prefix_patches, *self._retained.values(), *accepted],\n            )\n            prefix_reason = self.proposal_preflight_reason(plan_prefix)\n            if prefix_reason is not None:\n                prefix_rejections = (\n                    *rejections,\n                    IncrementalPatchRejection(None, prefix_reason),\n                )\n                return IncrementalConvergenceResult(\n                    proposal=None,\n                    rejections=tuple(prefix_rejections),\n                    retained_patch_count=len(self._retained),\n                    rejected_patch_count=len(prefix_rejections),\n                    made_progress=False,\n                    converged=False,\n                )\n\n        for patch in accepted:\n            self._retained[patch.path] = patch\n""",
        "plan-prefix preflight insertion",
    )
    text = replace_once(
        text,
        """                            convergence = accumulator.evaluate(\n                                generation.proposal,\n                                reserved_paths=tuple(sorted(seen_paths)),\n                            )\n""",
        """                            convergence = accumulator.evaluate(\n                                generation.proposal,\n                                reserved_paths=tuple(sorted(seen_paths)),\n                                prefix_patches=tuple(patches),\n                            )\n""",
        "resilient convergence call",
    )
    RECOVERY.write_text(text)


def patch_runtime() -> None:
    text = RUNTIME.read_text()
    text = replace_once(
        text,
        """    if not isinstance(value, dict):\n        raise ValueError(\"implementation failure diagnostics have an invalid envelope\")\n    if set(value) == {\"candidate_admission_failure\"}:\n""",
        """    if not isinstance(value, dict):\n        raise ValueError(\"implementation failure diagnostics have an invalid envelope\")\n    if set(value) == {\"candidate_generation_failure\"}:\n        return _bounded_candidate_generation_failure_evidence(\n            value[\"candidate_generation_failure\"]\n        )\n    if set(value) == {\"candidate_admission_failure\"}:\n""",
        "candidate generation failure envelope",
    )

    marker = "\n\ndef _bounded_identity(value: str, name: str) -> str:\n"
    helper = r'''

_CANDIDATE_GENERATION_FAILURE_KINDS = frozenset(
    {
        "RATE_LIMITED",
        "VALIDATION_EXHAUSTED",
        "PROVIDER_EXHAUSTED",
        "INCREMENTAL_PRECHECK_REJECTED",
    }
)
_CANDIDATE_GENERATION_REJECTION_CODES = frozenset(
    {*PROPOSAL_PREFLIGHT_REASON_CODES, "RETAINED_TARGET_REPEATED"}
)
_MAX_CANDIDATE_GENERATION_REJECTIONS = 16
_MAX_CANDIDATE_GENERATION_COUNT = 1_000


def _bounded_non_negative_int(
    value: object,
    name: str,
    *,
    maximum: int = _MAX_CANDIDATE_GENERATION_COUNT,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > maximum
    ):
        raise ValueError(f"{name} must be a bounded non-negative integer")
    return value


def _bounded_sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _bounded_candidate_rejection(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("candidate rejection diagnostics must be an object")
    required = {
        "work_unit_id",
        "agent_identity_digest",
        "generation",
        "canonical_source_mutated",
        "source_lineage_accepted",
        "git_mutation",
        "deployment_mutation",
        "review_completed",
        "validator_repair_attempt",
        "retained_patch_count",
        "rejected_patch_count",
        "rejection_reason_codes",
        "made_incremental_progress",
    }
    allowed = {*required, "failure_kind"}
    if set(value) - allowed or not required <= set(value):
        raise ValueError("candidate rejection diagnostics contain a non-admitted field")

    normalized: dict[str, object] = {
        "work_unit_id": _bounded_identity(value["work_unit_id"], "work_unit_id"),
        "agent_identity_digest": _bounded_sha256(
            value["agent_identity_digest"],
            "agent_identity_digest",
        ),
        "generation": _bounded_non_negative_int(value["generation"], "generation"),
        "retained_patch_count": _bounded_non_negative_int(
            value["retained_patch_count"],
            "retained_patch_count",
        ),
        "rejected_patch_count": _bounded_non_negative_int(
            value["rejected_patch_count"],
            "rejected_patch_count",
        ),
    }
    if normalized["generation"] < 1:
        raise ValueError("candidate rejection generation must be positive")

    failure_kind = value.get("failure_kind")
    if failure_kind is not None:
        if failure_kind not in _CANDIDATE_GENERATION_FAILURE_KINDS:
            raise ValueError(
                "candidate rejection diagnostics contain an invalid failure kind"
            )
        normalized["failure_kind"] = failure_kind

    reason_codes = value["rejection_reason_codes"]
    if (
        not isinstance(reason_codes, list)
        or len(reason_codes) > _MAX_CANDIDATE_GENERATION_REJECTIONS
    ):
        raise ValueError("candidate rejection reason codes exceed durable bound")
    if len(set(reason_codes)) != len(reason_codes):
        raise ValueError("candidate rejection reason codes must be unique")
    if any(code not in _CANDIDATE_GENERATION_REJECTION_CODES for code in reason_codes):
        raise ValueError(
            "candidate rejection diagnostics contain an invalid reason code"
        )
    normalized["rejection_reason_codes"] = list(reason_codes)

    for key in ("validator_repair_attempt", "made_incremental_progress"):
        flag = value[key]
        if not isinstance(flag, bool):
            raise ValueError("candidate rejection diagnostic state must be boolean")
        normalized[key] = flag

    for claim in (
        "canonical_source_mutated",
        "source_lineage_accepted",
        "git_mutation",
        "deployment_mutation",
        "review_completed",
    ):
        if value[claim] is not False:
            raise ValueError(
                "candidate rejection diagnostics asserted authority they do not own"
            )
        normalized[claim] = False
    return normalized


def _bounded_candidate_generation_failure_evidence(
    raw: object,
) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("candidate generation diagnostics must be an object")
    allowed = {
        "reason_code",
        "rejection_count",
        "retained_patch_count",
        "rejected_patch_count",
        "rejection_reason_codes",
        "max_reassignments_per_work_unit",
        "validator_repair_attempted",
        "validator_repair_count",
        "validator_repair_limit",
        "rejections",
        "canonical_source_mutated",
        "source_lineage_accepted",
        "worker_process_loss",
    }
    required = {
        "reason_code",
        "rejection_count",
        "max_reassignments_per_work_unit",
        "validator_repair_attempted",
        "validator_repair_count",
        "validator_repair_limit",
        "rejections",
        "canonical_source_mutated",
        "source_lineage_accepted",
        "worker_process_loss",
    }
    if set(raw) - allowed or not required <= set(raw):
        raise ValueError(
            "candidate generation diagnostics contain a non-admitted field"
        )
    if raw["reason_code"] != "CANDIDATE_GENERATION_EXHAUSTED":
        raise ValueError("candidate generation diagnostics contain an invalid reason code")

    normalized_failure: dict[str, object] = {
        "reason_code": "CANDIDATE_GENERATION_EXHAUSTED",
        "rejection_count": _bounded_non_negative_int(
            raw["rejection_count"],
            "rejection_count",
        ),
        "max_reassignments_per_work_unit": _bounded_non_negative_int(
            raw["max_reassignments_per_work_unit"],
            "max_reassignments_per_work_unit",
            maximum=32,
        ),
        "validator_repair_count": _bounded_non_negative_int(
            raw["validator_repair_count"],
            "validator_repair_count",
            maximum=1,
        ),
        "validator_repair_limit": _bounded_non_negative_int(
            raw["validator_repair_limit"],
            "validator_repair_limit",
            maximum=1,
        ),
    }
    if normalized_failure["validator_repair_limit"] != 1:
        raise ValueError("candidate generation validator repair limit drifted")

    attempted = raw["validator_repair_attempted"]
    if (
        not isinstance(attempted, bool)
        or attempted is not (normalized_failure["validator_repair_count"] > 0)
    ):
        raise ValueError("candidate generation validator repair state drifted")
    normalized_failure["validator_repair_attempted"] = attempted

    for claim in (
        "canonical_source_mutated",
        "source_lineage_accepted",
        "worker_process_loss",
    ):
        if raw[claim] is not False:
            raise ValueError(
                "candidate generation diagnostics asserted authority they do not own"
            )
        normalized_failure[claim] = False

    for key in ("retained_patch_count", "rejected_patch_count"):
        if key in raw:
            normalized_failure[key] = _bounded_non_negative_int(raw[key], key)

    reason_codes = raw.get("rejection_reason_codes", [])
    if (
        not isinstance(reason_codes, list)
        or len(reason_codes) > _MAX_CANDIDATE_GENERATION_REJECTIONS
    ):
        raise ValueError("candidate generation reason codes exceed durable bound")
    if len(set(reason_codes)) != len(reason_codes):
        raise ValueError("candidate generation reason codes must be unique")
    if any(code not in _CANDIDATE_GENERATION_REJECTION_CODES for code in reason_codes):
        raise ValueError(
            "candidate generation diagnostics contain an invalid rejection reason code"
        )
    if "rejection_reason_codes" in raw:
        normalized_failure["rejection_reason_codes"] = list(reason_codes)

    rejections = raw["rejections"]
    if (
        not isinstance(rejections, list)
        or len(rejections) > _MAX_CANDIDATE_GENERATION_REJECTIONS
    ):
        raise ValueError("candidate generation rejections exceed durable bound")
    normalized_rejections = [_bounded_candidate_rejection(item) for item in rejections]
    if normalized_failure["rejection_count"] != len(normalized_rejections):
        raise ValueError("candidate generation rejection count drifted")
    normalized_failure["rejections"] = normalized_rejections

    normalized = {"candidate_generation_failure": normalized_failure}
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    if len(encoded.encode("utf-8")) > 12_288:
        raise ValueError("candidate generation diagnostics exceed durable evidence bound")
    return normalized
'''
    if marker not in text:
        raise SystemExit("bounded identity insertion seam not found")
    if text.count(marker) != 1:
        raise SystemExit("bounded identity insertion seam is not unique")
    text = text.replace(marker, helper + marker, 1)
    RUNTIME.write_text(text)


def write_tests() -> None:
    TEST.write_text(
        r'''from __future__ import annotations

from hashlib import sha256

from parallax_api.code.agentic_candidate_recovery import IncrementalProposalAccumulator
from parallax_api.code.implementation_runtime import (
    ImplementationRuntimeError,
    _bounded_implementation_failure_evidence,
)
from parallax_api.intelligence.implementation_generation import (
    GeneratedSourcePatch,
    ImplementationProposal,
)


def _patch(path: str, marker: str) -> GeneratedSourcePatch:
    return GeneratedSourcePatch(
        path=path,
        expected_base_sha256=sha256(marker.encode("utf-8")).hexdigest(),
        unified_diff=(
            f"--- a/{path}\n"
            f"+++ b/{path}\n"
            "@@ -1,1 +1,1 @@\n"
            f"-{marker}\n"
            f"+{marker}-changed\n"
        ),
    )


def _proposal(*patches: GeneratedSourcePatch) -> ImplementationProposal:
    return ImplementationProposal(
        acceptance_ids_covered=["AC-02"],
        patches=list(patches),
    )


def _rejection(
    *,
    reason_codes: list[str] | None = None,
    authority: bool = False,
) -> dict[str, object]:
    return {
        "work_unit_id": "implementation-server",
        "agent_identity_digest": "a" * 64,
        "generation": 2,
        "failure_kind": "INCREMENTAL_PRECHECK_REJECTED",
        "canonical_source_mutated": authority,
        "source_lineage_accepted": False,
        "git_mutation": False,
        "deployment_mutation": False,
        "review_completed": False,
        "validator_repair_attempt": False,
        "retained_patch_count": 0,
        "rejected_patch_count": 1,
        "rejection_reason_codes": reason_codes or ["IMPLEMENTATION_LIMIT"],
        "made_incremental_progress": False,
    }


def _generation_failure() -> dict[str, object]:
    return {
        "candidate_generation_failure": {
            "reason_code": "CANDIDATE_GENERATION_EXHAUSTED",
            "rejection_count": 1,
            "retained_patch_count": 0,
            "rejected_patch_count": 1,
            "rejection_reason_codes": ["IMPLEMENTATION_LIMIT"],
            "max_reassignments_per_work_unit": 2,
            "validator_repair_attempted": False,
            "validator_repair_count": 0,
            "validator_repair_limit": 1,
            "rejections": [_rejection()],
            "canonical_source_mutated": False,
            "source_lineage_accepted": False,
            "worker_process_loss": False,
        }
    }


def test_plan_prefix_rejection_rolls_back_current_generation_and_allows_repair():
    prior = _patch("src/prior.py", "prior")
    rejected = _patch("src/current.py", "current")
    repaired = _patch("src/repaired.py", "repaired")

    def reason(proposal: ImplementationProposal) -> str | None:
        paths = {patch.path for patch in proposal.patches}
        if paths == {"src/prior.py", "src/current.py"}:
            return "IMPLEMENTATION_LIMIT"
        return None

    accumulator = IncrementalProposalAccumulator(
        acceptance_ids=("AC-02",),
        proposal_preflight_reason=reason,
    )
    first = accumulator.evaluate(
        _proposal(rejected),
        reserved_paths=("src/prior.py",),
        prefix_patches=(prior,),
    )
    assert first.converged is False
    assert first.made_progress is False
    assert first.retained_patch_count == 0
    assert accumulator.retained_paths == ()
    assert [item.reason_code for item in first.rejections] == ["IMPLEMENTATION_LIMIT"]

    second = accumulator.evaluate(
        _proposal(repaired),
        reserved_paths=("src/prior.py",),
        prefix_patches=(prior,),
    )
    assert second.converged is True
    assert second.proposal is not None
    assert accumulator.retained_paths == ("src/repaired.py",)
    assert [item.path for item in second.proposal.patches] == ["src/repaired.py"]


def test_plan_prefix_rejection_preserves_previously_retained_current_unit_intent():
    prior = _patch("src/prior.py", "prior")
    retained = _patch("src/retained.py", "retained")
    bad = _patch("src/bad.py", "bad")
    good = _patch("src/good.py", "good")

    def reason(proposal: ImplementationProposal) -> str | None:
        paths = {patch.path for patch in proposal.patches}
        if paths == {"src/prior.py", "src/retained.py", "src/bad.py"}:
            return "IMPLEMENTATION_LIMIT"
        if paths == {"src/stale.py"}:
            return "STALE_BASE"
        return None

    accumulator = IncrementalProposalAccumulator(
        acceptance_ids=("AC-02",),
        proposal_preflight_reason=reason,
    )
    partial = accumulator.evaluate(
        _proposal(retained, _patch("src/stale.py", "stale")),
        reserved_paths=("src/prior.py",),
        prefix_patches=(prior,),
    )
    assert partial.made_progress is True
    assert partial.converged is False
    assert accumulator.retained_paths == ("src/retained.py",)

    rejected = accumulator.evaluate(
        _proposal(bad),
        reserved_paths=("src/prior.py",),
        prefix_patches=(prior,),
    )
    assert rejected.made_progress is False
    assert rejected.converged is False
    assert accumulator.retained_paths == ("src/retained.py",)

    final = accumulator.evaluate(
        _proposal(good),
        reserved_paths=("src/prior.py",),
        prefix_patches=(prior,),
    )
    assert final.converged is True
    assert accumulator.retained_paths == ("src/good.py", "src/retained.py")


def test_candidate_generation_failure_evidence_survives_closed_schema_sanitizer():
    raw = _generation_failure()
    normalized = _bounded_implementation_failure_evidence(raw)
    assert normalized == raw
    error = ImplementationRuntimeError("failed", diagnostic_evidence=raw)
    assert error.diagnostic_evidence == raw


def test_candidate_generation_failure_rejects_unknown_or_sensitive_fields():
    raw = _generation_failure()
    raw["candidate_generation_failure"]["raw_model_output"] = "secret source"
    error = ImplementationRuntimeError("failed", diagnostic_evidence=raw)
    assert error.diagnostic_evidence is None


def test_candidate_generation_failure_rejects_arbitrary_reason_codes_and_authority_claims():
    arbitrary = _generation_failure()
    arbitrary["candidate_generation_failure"]["rejection_reason_codes"] = [
        "PRIVATE_EXCEPTION_TEXT"
    ]
    assert (
        ImplementationRuntimeError(
            "failed",
            diagnostic_evidence=arbitrary,
        ).diagnostic_evidence
        is None
    )

    authority = _generation_failure()
    authority["candidate_generation_failure"]["rejections"][0][
        "canonical_source_mutated"
    ] = True
    assert (
        ImplementationRuntimeError(
            "failed",
            diagnostic_evidence=authority,
        ).diagnostic_evidence
        is None
    )


def test_candidate_generation_failure_rejection_count_must_match_records():
    raw = _generation_failure()
    raw["candidate_generation_failure"]["rejection_count"] = 2
    assert (
        ImplementationRuntimeError(
            "failed",
            diagnostic_evidence=raw,
        ).diagnostic_evidence
        is None
    )
'''
    )


if __name__ == "__main__":
    patch_recovery()
    patch_runtime()
    write_tests()
