from __future__ import annotations

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
