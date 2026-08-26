import asyncio

import pytest

from parallax_api.intelligence.context import compose_reason_context
from parallax_api.intelligence.coordinator import ResponseCoordinationFailure, ResponseCoordinator
from parallax_api.intelligence.reason import ReasonResult
from parallax_api.intelligence.router import ModelRouter
from parallax_api.intelligence.scope import ScopeDecision, ScopeProposal


class LMRateLimitError(RuntimeError):
    pass


class StaticScopeProgram:
    def run(self, **_kwargs):
        return ScopeProposal(
            decision=ScopeDecision.CONTINUE,
            confidence=0.95,
            material_factors=["Existing objective remains active."],
            program_version="scope-response-rate-limit-test-v1",
        )


class StaticReasonProgram:
    def run(self, **_kwargs):
        return ReasonResult(
            answer="The current objective can continue using the protected conversation context.",
            confidence=0.91,
            material_uncertainties=[],
            assumptions=[],
            program_version="reason-response-rate-limit-test-v1",
        )


class RateLimitedProgram:
    def run(self, **_kwargs):
        raise LMRateLimitError("raw provider quota detail must not cross the router boundary")


class RuntimeFailureProgram:
    def run(self, **_kwargs):
        raise RuntimeError("raw provider failure must not cross the router boundary")


def context():
    return compose_reason_context(
        conversation_id="conversation-rate-limit",
        spec_id="P2-V0.3.0",
        status="ACTIVE",
        mode="code",
        current_user_turn="Continue this objective.",
        prior_messages=[],
    )


def respond(coordinator: ResponseCoordinator):
    return coordinator.respond(
        conversation_id="conversation-rate-limit",
        spec_id="P2-V0.3.0",
        mode="code",
        objective="Continue this objective.",
        current_user_turn="Continue this objective.",
        context=context(),
    )


def test_scope_rate_limit_exhaustion_is_capacity_failure_not_protected_scope_failure():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-a", "scope-b")),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=lambda _model: RateLimitedProgram(),
        reason_factory=lambda _model: StaticReasonProgram(),
    )

    with pytest.raises(ResponseCoordinationFailure) as exc:
        asyncio.run(respond(coordinator))

    failure = exc.value
    assert failure.error_code == "MODEL_CAPACITY_RATE_LIMITED"
    assert failure.public_message == "Model capacity is temporarily unavailable."
    assert failure.trace.protected_scope_decision is None
    assert failure.trace.reason_attempts == ()
    assert [item.status for item in failure.trace.scope_attempts] == ["provider_failed", "provider_failed"]
    assert [item.error for item in failure.trace.scope_attempts] == ["LMRateLimitError", "LMRateLimitError"]
    serialized = str(failure.trace.as_public_dict())
    assert "quota detail" not in serialized


def test_reason_rate_limit_preserves_established_scope_decision_without_answer():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-a", "reason-b")),
        scope_factory=lambda _model: StaticScopeProgram(),
        reason_factory=lambda _model: RateLimitedProgram(),
    )

    with pytest.raises(ResponseCoordinationFailure) as exc:
        asyncio.run(respond(coordinator))

    failure = exc.value
    assert failure.error_code == "MODEL_CAPACITY_RATE_LIMITED"
    assert failure.trace.protected_scope_decision == "CONTINUE"
    assert [item.status for item in failure.trace.scope_attempts] == ["ok"]
    assert [item.error for item in failure.trace.reason_attempts] == ["LMRateLimitError", "LMRateLimitError"]
    assert failure.trace.protected_verification_passed is False


def test_mixed_scope_provider_failures_remain_generic_provider_unavailable():
    def scope_factory(model: str):
        return RateLimitedProgram() if model == "scope-a" else RuntimeFailureProgram()

    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-a", "scope-b")),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=scope_factory,
        reason_factory=lambda _model: StaticReasonProgram(),
    )

    with pytest.raises(ResponseCoordinationFailure) as exc:
        asyncio.run(respond(coordinator))

    failure = exc.value
    assert failure.error_code == "MODEL_PROVIDER_UNAVAILABLE"
    assert failure.public_message == "Parallax model provider is temporarily unavailable."
    assert failure.trace.protected_scope_decision is None
    assert [item.error for item in failure.trace.scope_attempts] == ["LMRateLimitError", "RuntimeError"]


def test_successful_response_routing_is_unchanged():
    coordinator = ResponseCoordinator(
        scope_router=ModelRouter(models=("scope-model",)),
        reason_router=ModelRouter(models=("reason-model",)),
        scope_factory=lambda _model: StaticScopeProgram(),
        reason_factory=lambda _model: StaticReasonProgram(),
    )

    response = asyncio.run(respond(coordinator))

    assert response.scope.decision is ScopeDecision.CONTINUE
    assert response.answer is not None
    assert response.trace.final_state == "COMPLETE"
    assert response.trace.protected_verification_passed is True
