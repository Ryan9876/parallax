from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from uuid import uuid4

from .dspy_programs import DspyReasoningProgram, ReasoningResult
from .protected_metrics import evaluate_reasoning_output
from .router import AttemptRecord, ModelRouter


@dataclass(frozen=True)
class ResponseTrace:
    response_id: str
    conversation_id: str
    spec_id: str
    mode: str
    program_version: str
    attempted_models: tuple[str, ...]
    attempts: tuple[AttemptRecord, ...]
    validation_passed: bool
    final_state: str

    def as_public_dict(self) -> dict:
        data = asdict(self)
        data["attempts"] = [asdict(attempt) for attempt in self.attempts]
        return data


@dataclass(frozen=True)
class CoordinatedResponse:
    answer: str
    confidence: float
    trace: ResponseTrace


class ResponseCoordinator:
    def __init__(self, router: ModelRouter[ReasoningResult] | None = None):
        self.router = router or ModelRouter[ReasoningResult]()

    async def respond(
        self,
        *,
        conversation_id: str,
        spec_id: str,
        mode: str,
        objective: str,
        context: str,
    ) -> CoordinatedResponse:
        async def attempt(model: str) -> ReasoningResult:
            program = DspyReasoningProgram(model)
            return await asyncio.to_thread(
                program.run,
                objective=objective,
                context=context,
                mode=mode,
            )

        route = await self.router.route(
            attempt,
            lambda result: evaluate_reasoning_output(result.answer).passed,
        )
        result = route.value
        trace = ResponseTrace(
            response_id=str(uuid4()),
            conversation_id=conversation_id,
            spec_id=spec_id,
            mode=mode,
            program_version=result.program_version,
            attempted_models=tuple(record.model for record in route.attempts),
            attempts=route.attempts,
            validation_passed=True,
            final_state="COMPLETE",
        )
        return CoordinatedResponse(answer=result.answer, confidence=result.confidence, trace=trace)
