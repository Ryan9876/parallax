from __future__ import annotations

from hashlib import sha256

from parallax_api.code.agentic_candidate_recovery import (
    IncrementalPatchRejection,
    IncrementalProposalAccumulator,
    RETAINED_TARGET_REPEATED,
    TARGET_HIERARCHY_CONFLICT,
    convergence_guided_candidate_request,
)
from parallax_api.code.agentic_runtime import _MODEL_ORDER
from parallax_api.code.implementation import (
    DuplicateTargetError,
    ImplementationLimitError,
    TargetHierarchyConflictError,
)
from parallax_api.code.implementation_runtime import (
    PROPOSAL_PREFLIGHT_REASON_CODES,
    classify_proposal_preflight_failure,
)
from parallax_api.code.patching import (
    PatchConflictError,
    PatchFormatError,
    PatchLimitError,
    StaleBaseError,
    UnsafeTargetError,
)
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.intelligence.dspy_programs import (
    _HOSTED_MODEL_NUM_RETRIES,
    _HOSTED_MODEL_TIMEOUT_SECONDS,
)
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    GeneratedSourcePatch,
    ImplementationGenerationRequest,
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
        acceptance_ids_covered=["AC-01"],
        patches=list(patches),
    )


def _request() -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id="spec-1",
        work_specification_revision=1,
        work_specification_digest=sha256(b"spec").hexdigest(),
        title="Incremental convergence",
        objective="Converge safely",
        constraints=(),
        acceptance=(AcceptanceRequirement(id="AC-01", text="implementation converges"),),
        source_context=SourceContextSnapshot(
            files=(),
            digest=sha256(b"source").hexdigest(),
            total_bytes=0,
            excluded_secret_files=0,
            omitted_bounded_files=0,
        ),
    )


def test_preflight_failure_classifier_uses_fixed_sanitized_reason_codes():
    samples = (
        (UnsafeTargetError("secret /vercel/private/root"), "UNSAFE_TARGET"),
        (StaleBaseError("private source changed"), "STALE_BASE"),
        (PatchFormatError("raw model output"), "PATCH_FORMAT"),
        (PatchConflictError("sensitive source"), "PATCH_CONFLICT"),
        (PatchLimitError("large hidden payload"), "PATCH_LIMIT"),
        (DuplicateTargetError("duplicate secret"), "DUPLICATE_TARGET"),
        (TargetHierarchyConflictError("private tree"), "TARGET_HIERARCHY_CONFLICT"),
        (ImplementationLimitError("private size"), "IMPLEMENTATION_LIMIT"),
        (OSError("filesystem /private/root"), "OS_BOUNDARY_ERROR"),
        (RuntimeError("arbitrary provider payload"), "UNKNOWN_PRECHECK_ERROR"),
    )
    for exc, expected in samples:
        result = classify_proposal_preflight_failure(exc)
        assert result == expected
        assert result in PROPOSAL_PREFLIGHT_REASON_CODES
        assert str(exc) not in result


def test_incremental_accumulator_retains_safe_patch_and_isolates_rejected_patch():
    safe = _patch("src/safe.py", "safe")
    stale = _patch("src/stale.py", "stale")

    def reason(proposal: ImplementationProposal) -> str | None:
        paths = {patch.path for patch in proposal.patches}
        return "STALE_BASE" if "src/stale.py" in paths else None

    accumulator = IncrementalProposalAccumulator(
        acceptance_ids=("AC-01",),
        proposal_preflight_reason=reason,
    )
    result = accumulator.evaluate(_proposal(safe, stale))

    assert result.converged is False
    assert result.made_progress is True
    assert result.retained_patch_count == 1
    assert accumulator.retained_paths == ("src/safe.py",)
    assert [(item.path, item.reason_code) for item in result.rejections] == [
        ("src/stale.py", "STALE_BASE")
    ]

    repaired = _patch("src/repaired.py", "repair")
    final = accumulator.evaluate(_proposal(repaired))
    assert final.converged is True
    assert final.proposal is not None
    assert [patch.path for patch in final.proposal.patches] == [
        "src/safe.py",
        "src/repaired.py",
    ]


def test_repeated_retained_target_does_not_overwrite_original_intent():
    original = _patch("src/safe.py", "first")
    replacement = _patch("src/safe.py", "second")
    accumulator = IncrementalProposalAccumulator(
        acceptance_ids=("AC-01",),
        proposal_preflight_reason=lambda _proposal: None,
    )
    assert accumulator.evaluate(_proposal(original)).converged is True

    repeated = accumulator.evaluate(_proposal(replacement))
    assert repeated.converged is False
    assert repeated.made_progress is False
    assert accumulator.retained_paths == ("src/safe.py",)
    assert repeated.rejections == (
        IncrementalPatchRejection("src/safe.py", RETAINED_TARGET_REPEATED),
    )


def test_hierarchy_conflict_is_rejected_before_safe_engine_preflight():
    calls: list[tuple[str, ...]] = []

    def reason(proposal: ImplementationProposal) -> str | None:
        calls.append(tuple(patch.path for patch in proposal.patches))
        return None

    accumulator = IncrementalProposalAccumulator(
        acceptance_ids=("AC-01",),
        proposal_preflight_reason=reason,
    )
    conflict = accumulator.evaluate(
        _proposal(_patch("src/module.py/generated.py", "nested")),
        reserved_paths=("src/module.py",),
    )

    assert conflict.converged is False
    assert conflict.rejections == (
        IncrementalPatchRejection(
            "src/module.py/generated.py",
            TARGET_HIERARCHY_CONFLICT,
        ),
    )
    assert calls == []


def test_combined_preflight_rejection_discards_current_addition_but_keeps_prior_retained():
    first = _patch("src/first.py", "first")
    stale = _patch("src/stale.py", "stale")
    second = _patch("src/second.py", "second")
    third = _patch("src/third.py", "third")

    def reason(proposal: ImplementationProposal) -> str | None:
        paths = {patch.path for patch in proposal.patches}
        if paths == {"src/stale.py"}:
            return "STALE_BASE"
        if paths == {"src/first.py", "src/second.py"}:
            return "IMPLEMENTATION_LIMIT"
        return None

    accumulator = IncrementalProposalAccumulator(
        acceptance_ids=("AC-01",),
        proposal_preflight_reason=reason,
    )
    partial = accumulator.evaluate(_proposal(first, stale))
    assert partial.made_progress is True
    assert partial.converged is False
    assert accumulator.retained_paths == ("src/first.py",)

    combined_failure = accumulator.evaluate(_proposal(second))
    assert combined_failure.converged is False
    assert combined_failure.made_progress is False
    assert accumulator.retained_paths == ("src/first.py",)
    assert any(
        rejection.reason_code == "IMPLEMENTATION_LIMIT"
        for rejection in combined_failure.rejections
    )

    final = accumulator.evaluate(_proposal(third))
    assert final.converged is True
    assert accumulator.retained_paths == ("src/first.py", "src/third.py")


def test_convergence_guidance_contains_only_bounded_targets_and_reason_codes():
    request = _request()
    guided = convergence_guided_candidate_request(
        request,
        retained_paths=("src/safe.py",),
        rejections=(
            IncrementalPatchRejection("src/stale.py", "STALE_BASE"),
            IncrementalPatchRejection("../escape.py", "UNSAFE_TARGET"),
        ),
    )
    added = guided.constraints[-1]
    assert "src/safe.py" in added
    assert "src/stale.py" in added
    assert "STALE_BASE" in added
    assert "UNSAFE_TARGET" in added
    assert "../escape.py" not in added
    assert "unified_diff" not in added
    assert "expected_base_sha256" not in added
    assert "/vercel/" not in added


def test_governed_model_timeout_and_hidden_retry_budget_are_unchanged():
    assert _MODEL_ORDER == (
        "openai/gpt-5.6-luna",
        "openai/gpt-5.6-terra",
        "openai/gpt-5.6-sol",
    )
    assert _HOSTED_MODEL_TIMEOUT_SECONDS == 60
    assert _HOSTED_MODEL_NUM_RETRIES == 0
