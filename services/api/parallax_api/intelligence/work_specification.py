from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .dspy_programs import build_lm
from .router import ModelRouter, RoutingFailure, RoutingFailureKind


class WorkSpecificationDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    title: str = Field(min_length=3, max_length=120)
    objective: str = Field(min_length=10, max_length=6_000)
    constraints: list[str] = Field(default_factory=list, max_length=6)
    acceptance_criteria: list[str] = Field(min_length=2, max_length=8)
    risks: list[str] = Field(default_factory=list, max_length=5)
    open_questions: list[str] = Field(default_factory=list, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)
    program_version: str = Field(min_length=1, max_length=100)

    @field_validator("title", "objective")
    @classmethod
    def clean_scalar(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("work specification fields may not be empty")
        return clean

    @field_validator("constraints", "acceptance_criteria", "risks", "open_questions")
    @classmethod
    def clean_items(cls, values: list[str]) -> list[str]:
        clean: list[str] = []
        seen: set[str] = set()
        for raw in values:
            item = raw.strip()
            if not item:
                raise ValueError("work specification list items may not be empty")
            if len(item) > 500:
                raise ValueError("work specification list item exceeds 500 characters")
            key = item.casefold()
            if key in seen:
                continue
            seen.add(key)
            clean.append(item)
        return clean


class WorkSpecificationProgram(Protocol):
    version: str

    def run(self, *, objective: str, context: str) -> WorkSpecificationDraft: ...


class DspyWorkSpecificationProgram:
    version = "work-spec-v0.7.1"

    def __init__(self, model: str):
        try:
            import dspy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("DSPy is required for live work-specification drafting") from exc

        class DraftSpecification(dspy.Signature):
            """Turn the user's durable conversation into a concise implementation-ready specification draft.

            Preserve the user's actual outcome and later corrections. Server-authoritative Project capability
            facts describe what the protected runtime can access and override conflicting assistant assumptions about
            repository availability; they do not override user outcome or substantive constraints. Do not invent
            approval, deployment state, secret values, hidden reasoning, or requirements unsupported by the
            conversation. Acceptance criteria must be concrete and testable. Put unresolved material gaps in
            open_questions instead of guessing.
            """

            objective: str = dspy.InputField()
            context: str = dspy.InputField()
            title: str = dspy.OutputField(desc="short descriptive title, no more than 120 characters")
            specification_objective: str = dspy.OutputField(desc="clear outcome-focused objective")
            constraints: list[str] = dspy.OutputField(desc="0 to 6 material constraints explicitly supported by context")
            acceptance_criteria: list[str] = dspy.OutputField(desc="2 to 8 concrete observable acceptance criteria")
            risks: list[str] = dspy.OutputField(desc="0 to 5 material delivery, security, reliability, or UX risks")
            open_questions: list[str] = dspy.OutputField(desc="0 to 4 unresolved questions that materially affect the objective")
            confidence: float = dspy.OutputField(desc="finite confidence from 0 to 1 in the draft's fidelity to the conversation")

        self._dspy = dspy
        self._lm = build_lm(model)
        self._program = dspy.Predict(DraftSpecification)

    def run(self, *, objective: str, context: str) -> WorkSpecificationDraft:
        with self._dspy.context(lm=self._lm):
            prediction = self._program(objective=objective, context=context)
        return WorkSpecificationDraft(
            title=str(prediction.title),
            objective=str(prediction.specification_objective),
            constraints=list(prediction.constraints),
            acceptance_criteria=list(prediction.acceptance_criteria),
            risks=list(prediction.risks),
            open_questions=list(prediction.open_questions),
            confidence=float(prediction.confidence),
            program_version=self.version,
        )


def validate_work_specification_draft(draft: WorkSpecificationDraft) -> bool:
    if len(draft.acceptance_criteria) < 2:
        return False
    if len({item.casefold() for item in draft.acceptance_criteria}) != len(draft.acceptance_criteria):
        return False
    if draft.confidence < 0.0 or draft.confidence > 1.0:
        return False
    return True


@dataclass(frozen=True, slots=True)
class WorkSpecificationGeneration:
    draft: WorkSpecificationDraft
    model: str


class WorkSpecificationGenerationFailure(RuntimeError):
    def __init__(self, message: str, *, kind: RoutingFailureKind):
        super().__init__(message)
        self.kind = kind


class WorkSpecificationCoordinator:
    def __init__(self, *, router: ModelRouter[WorkSpecificationDraft] | None = None):
        self.router = router or ModelRouter()

    @staticmethod
    def conversation_context(messages, *, project_context: str | None = None) -> tuple[str, str]:
        user_messages = [item for item in messages if item.role == "user" and item.content.strip()]
        if not user_messages:
            raise ValueError("work specification drafting requires at least one user message")
        objective = user_messages[-1].content.strip()
        selected = list(messages)[-18:]
        lines: list[str] = []
        total = 0
        for item in reversed(selected):
            line = f"{item.role.upper()}: {item.content.strip()}"
            if not line.strip():
                continue
            if total + len(line) > 14_000:
                break
            lines.append(line)
            total += len(line)
        lines.reverse()
        context = "\n\n".join(lines)
        if project_context is not None:
            protected = project_context.strip()
            if not protected or len(protected) > 1_200:
                raise ValueError("server Project context exceeds protected limits")
            context = f"SERVER_PROJECT_CONTEXT:\n[SERVER AUTHORITATIVE] {protected}\n\n{context}"
        return objective[:6_000], context

    async def draft(self, messages, *, project_context: str | None = None) -> WorkSpecificationGeneration:
        objective, context = self.conversation_context(messages, project_context=project_context)

        async def attempt(model: str) -> WorkSpecificationDraft:
            program = DspyWorkSpecificationProgram(model)
            return await asyncio.to_thread(program.run, objective=objective, context=context)

        try:
            result = await self.router.route(attempt, validate_work_specification_draft)
        except RoutingFailure as exc:
            raise WorkSpecificationGenerationFailure(
                "Parallax could not produce a valid work specification draft",
                kind=exc.kind,
            ) from exc
        return WorkSpecificationGeneration(draft=result.value, model=result.model)
