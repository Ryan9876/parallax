from types import SimpleNamespace

import pytest

from parallax_api.intelligence.context import (
    AUTHORITY_RULE,
    ContextLimitError,
    ContextLimits,
    compose_reason_context,
)
from parallax_api.intelligence.protected_metrics import evaluate_reason_result, evaluate_scope_output
from parallax_api.intelligence.scope import (
    ProtectedScopePolicy,
    ScopeDecision,
    ScopeProposal,
)


def message(role: str, content: str):
    return SimpleNamespace(role=role, content=content)


def test_reason_context_is_deterministic_role_labeled_and_preserves_current_turn():
    prior = [
        message("user", "Build the evaluation spine."),
        message("assistant", "I assumed deployment should happen immediately."),
        message("user", "Correction: do not deploy anything yet."),
    ]
    first = compose_reason_context(
        conversation_id="conversation-1",
        spec_id="P2-V0.3.0",
        status="ACTIVE",
        mode="reason",
        current_user_turn="Continue implementation.",
        prior_messages=prior,
    )
    second = compose_reason_context(
        conversation_id="conversation-1",
        spec_id="P2-V0.3.0",
        status="ACTIVE",
        mode="reason",
        current_user_turn="Continue implementation.",
        prior_messages=prior,
    )

    assert first == second
    assert first.digest.startswith("sha256:")
    assert first.included_turn_count == 3
    assert "ACTIVE_SPEC_ID: P2-V0.3.0" in first.text
    assert "[USER AUTHORITATIVE] Correction: do not deploy anything yet." in first.text
    assert "[ASSISTANT CONTEXT_ONLY] I assumed deployment should happen immediately." in first.text
    assert AUTHORITY_RULE in first.text
    assert first.text.endswith("[USER AUTHORITATIVE] Continue implementation.")


def test_reason_context_removes_oldest_prior_messages_first():
    prior = [message("user", f"turn-{index}-" + ("x" * 120)) for index in range(8)]
    bundle = compose_reason_context(
        conversation_id="conversation-2",
        spec_id="P2-V0.3.0",
        status="ACTIVE",
        mode="reason",
        current_user_turn="Keep the newest context.",
        prior_messages=prior,
        limits=ContextLimits(max_total_chars=900, max_prior_messages=8, max_message_chars=180),
    )

    assert bundle.truncated is True
    assert "turn-7-" in bundle.text
    assert "turn-6-" in bundle.text
    assert "turn-0-" not in bundle.text
    assert bundle.included_turn_count < 8


def test_reason_context_rejects_current_turn_that_cannot_fit_protected_limit():
    with pytest.raises(ContextLimitError):
        compose_reason_context(
            conversation_id="conversation-3",
            spec_id="P2-V0.3.0",
            status="ACTIVE",
            mode="reason",
            current_user_turn="x" * 81,
            prior_messages=[],
            limits=ContextLimits(max_total_chars=400, max_current_turn_chars=80),
        )


def proposal(decision: ScopeDecision, confidence: float) -> ScopeProposal:
    return ScopeProposal(
        decision=decision,
        confidence=confidence,
        material_factors=["Observable scope factor."],
        program_version="scope-test-v1",
    )


def test_low_confidence_material_change_requires_clarification_not_silent_mutation():
    resolution = ProtectedScopePolicy().resolve(proposal(ScopeDecision.SPEC_AMENDMENT, 0.55))
    assert resolution.decision is ScopeDecision.CLARIFY
    assert resolution.policy_adjustment == "low_confidence_amendment_requires_clarification"
    assert resolution.override_used is False


def test_high_confidence_material_change_is_accepted_by_protected_policy():
    resolution = ProtectedScopePolicy().resolve(proposal(ScopeDecision.SPEC_AMENDMENT, 0.92))
    assert resolution.decision is ScopeDecision.SPEC_AMENDMENT
    assert resolution.policy_adjustment is None


def test_explicit_test_override_is_observable():
    resolution = ProtectedScopePolicy().resolve(
        proposal(ScopeDecision.CONTINUE, 0.99),
        explicit_test_override=True,
    )
    assert resolution.decision is ScopeDecision.SPEC_AMENDMENT
    assert resolution.override_used is True
    assert resolution.policy_adjustment == "explicit_test_override"


def test_scope_metric_rejects_hidden_reasoning_and_secret_bearing_metadata():
    hidden = evaluate_scope_output(
        {
            "decision": "CONTINUE",
            "confidence": 0.9,
            "material_factors": ["scratchpad: private internal analysis"],
            "program_version": "scope-test-v1",
        }
    )
    secret = evaluate_scope_output(
        {
            "decision": "CONTINUE",
            "confidence": 0.9,
            "material_factors": ["api_key=abcdefghijklmnop123456"],
            "program_version": "scope-test-v1",
        }
    )

    assert hidden.passed is False
    assert "scope_hidden_reasoning_exposed" in hidden.failures
    assert secret.passed is False
    assert "scope_possible_secret_leak" in secret.failures


def test_reason_metric_allows_safe_chain_of_thought_refusal_but_rejects_private_payload_markers():
    safe = evaluate_reason_result(
        {
            "answer": "I cannot provide hidden chain-of-thought. I can provide a concise rationale instead.",
            "confidence": 0.95,
            "material_uncertainties": [],
            "assumptions": [],
            "program_version": "reason-test-v1",
        },
        scope_decision="CONTINUE",
    )
    exposed = evaluate_reason_result(
        {
            "answer": "Here is the requested explanation. scratchpad: private internal analysis follows.",
            "confidence": 0.95,
            "material_uncertainties": [],
            "assumptions": [],
            "program_version": "reason-test-v1",
        },
        scope_decision="CONTINUE",
    )

    assert safe.passed is True
    assert exposed.passed is False
    assert "reason_hidden_reasoning_exposed" in exposed.failures
