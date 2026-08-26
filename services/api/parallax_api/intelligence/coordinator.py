from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Callable
from uuid import uuid4

from .context import ReasonContext
from .protected_metrics import evaluate_reason_result, evaluate_scope_output
from .reason import DspyReasonProgram, ReasonProgram, ReasonResult
from .router import AttemptRecord, ModelRouter, RoutingFailure, RoutingFailureKind
from .scope import (
    DspyScopeProgram,
    ProtectedScopePolicy,
    ScopeDecision,
    ScopeProgram,
    ScopeProposal,
    ScopeResolution,
)


@dataclass(frozen=True)
class ResponseTrace:
    response_id: str
    conversation_id: str
    spec_id: str
    mode: str
    reason_program_version: str | None
    scope_program_version: str | None
    protected_scope_decision: str | None
    scope_override_used: bool
    scope_policy_adjustment: str | None
    context_digest: str
    included_turn_count: int
    context_truncated: bool
    attempted_models: tuple[str, ...]
    scope_attempts: tuple[AttemptRecord, ...]
    reason_attempts: tuple[AttemptRecord, ...]
    protected_verification_passed: bool
    final_state: str

    def as_public_dict(self) -> dict:
        data = asdict(self)
        data["scope_attempts"] = [asdict(attempt) for attempt in self.scope_attempts]
        data["reason_attempts"] = [asdict(attempt) for attempt in self.reason_attempts]
        return data


class ResponseCoordinationFailure(RuntimeError):
    """Sanitized runtime failure carrying observable, non-reasoning trace evidence."""

    def __init__(self, *, error_code: str, public_message: str, trace: ResponseTrace):
        super().__init__(public_message)
        self.error_code = error_code
        self.public_message = public_message
        self.trace = trace


@dataclass(frozen=True)
class CoordinatedResponse:
    answer: str | None
    confidence: float
    scope: ScopeResolution
    material_uncertainties: tuple[str, ...]
    assumptions: tuple[str, ...]
    trace: ResponseTrace


ScopeFactory = Callable[[str], ScopeProgram]
ReasonFactory = Callable[[str], ReasonProgram]


def _routing_failure_contract(kind: RoutingFailureKind, *, stage: str) -> tuple[str, str]:
    """Map sanitized routing exhaustion to a bounded operator-visible contract.

    Validation exhaustion remains a protected-output failure. Provider capacity
    and other provider exhaustion are infrastructure evidence, not proof that a
    protected scope/reason decision itself was invalid.
    """

    if kind is RoutingFailureKind.RATE_LIMITED:
        return "MODEL_CAPACITY_RATE_LIMITED", "Model capacity is temporarily unavailable."
    if kind is RoutingFailureKind.PROVIDER_EXHAUSTED:
        return "MODEL_PROVIDER_UNAVAILABLE", "Parallax model provider is temporarily unavailable."
    if stage == "scope":
        return "PROTECTED_SCOPE_FAILURE", "Parallax could not establish a protected scope decision."
    return "PROTECTED_REASON_FAILURE", "Parallax could not produce a response that passed protected verification."


class ResponseCoordinator:
    def __init__(
        self,
        *,
        scope_router: ModelRouter[ScopeProposal] | None = None,
        reason_router: ModelRouter[ReasonResult] | None = None,
        scope_factory: ScopeFactory | None = None,
        reason_factory: ReasonFactory | None = None,
        scope_policy: ProtectedScopePolicy | None = None,
    ):
        self.scope_router = scope_router or ModelRouter[ScopeProposal]()
        self.reason_router = reason_router or ModelRouter[ReasonResult]()
        self.scope_factory = scope_factory or DspyScopeProgram
        self.reason_factory = reason_factory or DspyReasonProgram
        self.scope_policy = scope_policy or ProtectedScopePolicy()

    async def _scope(
        self,
        *,
        current_user_turn: str,
        context: ReasonContext,
        explicit_test_scope_override: bool,
    ) -> tuple[ScopeResolution, tuple[AttemptRecord, ...]]:
        if explicit_test_scope_override:
            override_proposal = ScopeProposal(
                decision=ScopeDecision.CONTINUE,
                confidence=1.0,
                material_factors=["Explicit test/developer override requested."],
                program_version="scope-override-v0.3.0",
            )
            return (
                self.scope_policy.resolve(override_proposal, explicit_test_override=True),
                (),
            )

        async def attempt(model: str) -> ScopeProposal:
            program = self.scope_factory(model)
            return await asyncio.to_thread(
                program.run,
                current_user_turn=current_user_turn,
                context=context.text,
            )

        route = await self.scope_router.route(
            attempt,
            lambda result: evaluate_scope_output(result).passed,
        )
        return self.scope_policy.resolve(route.value), route.attempts

    async def respond(
        self,
        *,
        conversation_id: str,
        spec_id: str,
        mode: str,
        objective: str,
        current_user_turn: str,
        context: ReasonContext,
        explicit_test_scope_override: bool = False,
    ) -> CoordinatedResponse:
        try:
            scope, scope_attempts = await self._scope(
                current_user_turn=current_user_turn,
                context=context,
                explicit_test_scope_override=explicit_test_scope_override,
            )
        except RoutingFailure as exc:
            trace = self._trace(
                conversation_id=conversation_id,
                spec_id=spec_id,
                mode=mode,
                context=context,
                scope=None,
                scope_attempts=exc.attempts,
                reason_attempts=(),
                reason_program_version=None,
                protected_verification_passed=False,
                final_state="ERROR",
            )
            error_code, public_message = _routing_failure_contract(exc.kind, stage="scope")
            raise ResponseCoordinationFailure(
                error_code=error_code,
                public_message=public_message,
                trace=trace,
            ) from None

        if scope.decision is ScopeDecision.SPEC_AMENDMENT:
            trace = self._trace(
                conversation_id=conversation_id,
                spec_id=spec_id,
                mode=mode,
                context=context,
                scope=scope,
                scope_attempts=scope_attempts,
                reason_attempts=(),
                reason_program_version=None,
                protected_verification_passed=True,
                final_state="SPEC_AMENDMENT",
            )
            return CoordinatedResponse(
                answer=None,
                confidence=scope.confidence,
                scope=scope,
                material_uncertainties=(),
                assumptions=(),
                trace=trace,
            )

        async def reason_attempt(model: str) -> ReasonResult:
            program = self.reason_factory(model)
            return await asyncio.to_thread(
                program.run,
                objective=objective,
                context=context.text,
                mode=mode,
                spec_id=spec_id,
                scope_decision=scope.decision,
            )

        try:
            route = await self.reason_router.route(
                reason_attempt,
                lambda result: evaluate_reason_result(
                    result,
                    scope_decision=scope.decision.value,
                ).passed,
            )
        except RoutingFailure as exc:
            trace = self._trace(
                conversation_id=conversation_id,
                spec_id=spec_id,
                mode=mode,
                context=context,
                scope=scope,
                scope_attempts=scope_attempts,
                reason_attempts=exc.attempts,
                reason_program_version=None,
                protected_verification_passed=False,
                final_state="ERROR",
            )
            error_code, public_message = _routing_failure_contract(exc.kind, stage="reason")
            raise ResponseCoordinationFailure(
                error_code=error_code,
                public_message=public_message,
                trace=trace,
            ) from None

        result = route.value
        trace = self._trace(
            conversation_id=conversation_id,
            spec_id=spec_id,
            mode=mode,
            context=context,
            scope=scope,
            scope_attempts=scope_attempts,
            reason_attempts=route.attempts,
            reason_program_version=result.program_version,
            protected_verification_passed=True,
            final_state="COMPLETE",
        )
        return CoordinatedResponse(
            answer=result.answer,
            confidence=result.confidence,
            scope=scope,
            material_uncertainties=tuple(result.material_uncertainties),
            assumptions=tuple(result.assumptions),
            trace=trace,
        )

    def _trace(
        self,
        *,
        conversation_id: str,
        spec_id: str,
        mode: str,
        context: ReasonContext,
        scope: ScopeResolution | None,
        scope_attempts: tuple[AttemptRecord, ...],
        reason_attempts: tuple[AttemptRecord, ...],
        reason_program_version: str | None,
        protected_verification_passed: bool,
        final_state: str,
    ) -> ResponseTrace:
        attempted = tuple(
            attempt.model
            for attempt in (*scope_attempts, *reason_attempts)
        )
        return ResponseTrace(
            response_id=str(uuid4()),
            conversation_id=conversation_id,
            spec_id=spec_id,
            mode=mode,
            reason_program_version=reason_program_version,
            scope_program_version=scope.program_version if scope is not None else None,
            protected_scope_decision=scope.decision.value if scope is not None else None,
            scope_override_used=scope.override_used if scope is not None else False,
            scope_policy_adjustment=scope.policy_adjustment if scope is not None else None,
            context_digest=context.digest,
            included_turn_count=context.included_turn_count,
            context_truncated=context.truncated,
            attempted_models=attempted,
            scope_attempts=scope_attempts,
            reason_attempts=reason_attempts,
            protected_verification_passed=protected_verification_passed,
            final_state=final_state,
        )
