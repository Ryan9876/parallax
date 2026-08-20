import asyncio

import pytest

from parallax_api.intelligence.context import compose_reason_context
from parallax_api.intelligence.coordinator import ResponseCoordinationFailure, ResponseCoordinator
from parallax_api.intelligence.reason import ReasonResult
from parallax_api.intelligence.router import ModelRouter
from parallax_api.intelligence.scope import ScopeDecision, ScopeProposal


class StaticScopeProgram:
    def __init__(self, proposal: ScopeProposal):
        self.proposal = proposal
        self.version = proposal.program_version

    def run(self, *, current_user_turn: str, context: str) -> ScopeProposal:
        assert current_user_turn
        assert "ACTIVE_SPEC_ID" in context
        return self.proposal


class StaticReasonProgram:
    version = "reason-test-v1"

    def __init__(self, result: ReasonResult):
        self.result = result

    def run(self, **kwargs) -> ReasonResult:
        assert kwargs["scope_decision"] in {ScopeDecision.CONTINUE, ScopeDecision.CLARIFY}
        assert kwargs["spec_id"] == "P2-V0.3.0"
        return self.result


def context():
    return compose_reason_context(
        conversation_id="conversation-1",
        spec_id="P2-V0.3.0",
        status="ACTIVE",
        mode="reason",
        current_user_turn="Continue implementation.",
        prior_messages=[],
    )


def proposal(decision: ScopeDecision, confidence: float = 0.95) -> ScopeProposal:
    return ScopeProposal(
        decision=decision,
        confidence=confidence,
        material_factors=["Observable scope factor."],
        program_version="scope-test-v1",
    )


def result(answer: str, *, confidence: float = 0.9) -> ReasonResult:
    return ReasonResult(
        answer=answer,
        confidence=confidence,
        material_uncertainties=[],
        assumptions=[],
        program_version="reason-test-v1",
    )


def test_ordinary_follow_up_continues_and_returns_typed_reason_result():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=lambda model: StaticScopeProgram(proposal(ScopeDecision.CONTINUE)),
        reason_factory=lambda model: StaticReasonProgram(
            result("Continue the existing conversation using the active objective and context.")
        ),
    )

    response = asyncio.run(
        coordinator.respond(
            conversation_id="conversation-1",
            spec_id="P2-V0.3.0",
            mode="reason",
            objective="Continue implementation.",
            current_user_turn="Continue implementation.",
            context=context(),
        )
    )

    assert response.scope.decision is ScopeDecision.CONTINUE
    assert response.answer.startswith("Continue the existing conversation")
    assert response.trace.final_state == "COMPLETE"
    assert response.trace.protected_verification_passed is True
    assert response.trace.context_digest.startswith("sha256:")
    assert response.trace.scope_attempts[0].status == "ok"
    assert response.trace.reason_attempts[0].status == "ok"


def test_material_scope_change_stops_before_reason_program_runs():
    reason_called = False

    def reason_factory(model: str):
        nonlocal reason_called
        reason_called = True
        return StaticReasonProgram(result("This should never be produced by the Reason program."))

    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=lambda model: StaticScopeProgram(proposal(ScopeDecision.SPEC_AMENDMENT)),
        reason_factory=reason_factory,
    )

    response = asyncio.run(
        coordinator.respond(
            conversation_id="conversation-1",
            spec_id="P2-V0.3.0",
            mode="reason",
            objective="Replace the approved objective entirely.",
            current_user_turn="Replace the approved objective entirely.",
            context=context(),
        )
    )

    assert response.scope.decision is ScopeDecision.SPEC_AMENDMENT
    assert response.answer is None
    assert response.trace.final_state == "SPEC_AMENDMENT"
    assert response.trace.reason_attempts == ()
    assert reason_called is False


def test_low_confidence_amendment_becomes_one_focused_clarification():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=lambda model: StaticScopeProgram(
            proposal(ScopeDecision.SPEC_AMENDMENT, confidence=0.50)
        ),
        reason_factory=lambda model: StaticReasonProgram(
            result("Should the approved objective itself change, or only this implementation detail?")
        ),
    )

    response = asyncio.run(
        coordinator.respond(
            conversation_id="conversation-1",
            spec_id="P2-V0.3.0",
            mode="reason",
            objective="Change this part.",
            current_user_turn="Change this part.",
            context=context(),
        )
    )

    assert response.scope.decision is ScopeDecision.CLARIFY
    assert response.scope.policy_adjustment == "low_confidence_amendment_requires_clarification"
    assert response.answer is not None and response.answer.count("?") == 1


def test_protected_invalid_reason_result_escalates_to_next_model():
    def reason_factory(model: str):
        if model == "reason-a":
            return StaticReasonProgram(result("too short"))
        return StaticReasonProgram(
            result("The second model produced a protected-valid answer after escalation.")
        )

    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-a", "reason-b")),
        scope_factory=lambda model: StaticScopeProgram(proposal(ScopeDecision.CONTINUE)),
        reason_factory=reason_factory,
    )

    response = asyncio.run(
        coordinator.respond(
            conversation_id="conversation-1",
            spec_id="P2-V0.3.0",
            mode="reason",
            objective="Continue implementation.",
            current_user_turn="Continue implementation.",
            context=context(),
        )
    )

    assert [attempt.status for attempt in response.trace.reason_attempts] == ["validation_failed", "ok"]
    assert response.answer is not None and "second model" in response.answer


def test_all_scope_models_failing_protected_validation_returns_unresolved_scope_trace():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-a", "scope-b")),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=lambda model: StaticScopeProgram(
            ScopeProposal(
                decision=ScopeDecision.CONTINUE,
                confidence=2.0,
                material_factors=["Invalid confidence should fail protected scope validation."],
                program_version="scope-invalid-v1",
            )
        ),
        reason_factory=lambda model: StaticReasonProgram(
            result("Reason must never run without a protected scope decision.")
        ),
    )

    with pytest.raises(ResponseCoordinationFailure) as exc:
        asyncio.run(
            coordinator.respond(
                conversation_id="conversation-1",
                spec_id="P2-V0.3.0",
                mode="reason",
                objective="Continue implementation.",
                current_user_turn="Continue implementation.",
                context=context(),
            )
        )

    failure = exc.value
    assert failure.error_code == "PROTECTED_SCOPE_FAILURE"
    assert failure.trace.final_state == "ERROR"
    assert failure.trace.protected_scope_decision is None
    assert failure.trace.scope_program_version is None
    assert failure.trace.protected_verification_passed is False
    assert failure.trace.reason_attempts == ()
    assert failure.trace.attempted_models == ("scope-a", "scope-b")
    assert [attempt.status for attempt in failure.trace.scope_attempts] == [
        "validation_failed",
        "validation_failed",
    ]


def test_all_reason_models_failing_protected_validation_returns_sanitized_trace():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-a", "reason-b")),
        scope_factory=lambda model: StaticScopeProgram(proposal(ScopeDecision.CONTINUE)),
        reason_factory=lambda model: StaticReasonProgram(result("too short")),
    )

    with pytest.raises(ResponseCoordinationFailure) as exc:
        asyncio.run(
            coordinator.respond(
                conversation_id="conversation-1",
                spec_id="P2-V0.3.0",
                mode="reason",
                objective="Continue implementation.",
                current_user_turn="Continue implementation.",
                context=context(),
            )
        )

    failure = exc.value
    assert failure.error_code == "PROTECTED_REASON_FAILURE"
    assert str(failure) == "Parallax could not produce a response that passed protected verification."
    assert failure.trace.final_state == "ERROR"
    assert failure.trace.protected_scope_decision == "CONTINUE"
    assert failure.trace.protected_verification_passed is False
    assert failure.trace.context_digest.startswith("sha256:")
    assert failure.trace.reason_program_version is None
    assert failure.trace.attempted_models == ("scope-model", "reason-a", "reason-b")
    assert [attempt.status for attempt in failure.trace.reason_attempts] == [
        "validation_failed",
        "validation_failed",
    ]
    serialized = failure.trace.as_public_dict()
    assert "too short" not in str(serialized)
    assert "chain_of_thought" not in serialized
