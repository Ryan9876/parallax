from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .dspy_programs import build_lm
from .scope import ScopeDecision


class ReasonResult(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    answer: str = Field(min_length=1, max_length=40_000)
    confidence: float = Field(ge=0.0, le=1.0)
    material_uncertainties: list[str] = Field(default_factory=list, max_length=4)
    assumptions: list[str] = Field(default_factory=list, max_length=4)
    program_version: str = Field(min_length=1, max_length=100)

    @field_validator("answer")
    @classmethod
    def clean_answer(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Reason answer may not be empty")
        return clean

    @field_validator("material_uncertainties", "assumptions")
    @classmethod
    def validate_observable_metadata(cls, values: list[str]) -> list[str]:
        clean: list[str] = []
        for item in values:
            value = item.strip()
            if not value:
                raise ValueError("Reason metadata items may not be empty")
            if len(value) > 300:
                raise ValueError("Reason metadata item exceeds 300 characters")
            clean.append(value)
        return clean


class ReasonProgram(Protocol):
    version: str

    def run(
        self,
        *,
        objective: str,
        context: str,
        mode: str,
        spec_id: str,
        scope_decision: ScopeDecision,
    ) -> ReasonResult: ...


class DspyReasonProgram:
    version = "reason-v0.3.0"

    def __init__(self, model: str):
        try:
            import dspy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("DSPy is required for the live Reason program") from exc

        class ReasonSignature(dspy.Signature):
            """Answer within the active approved objective and durable context.

            Treat later USER corrections as authoritative over conflicting older
            assistant assumptions. Be direct and concise. Distinguish generated,
            validated, deployed, and deployment-verified states. State only
            material uncertainty. If scope_decision is CLARIFY, ask exactly one
            focused question and do not hide missing information behind a broad
            speculative answer. Never expose secrets, chain-of-thought, rationale,
            scratchpads, or environment values.
            """

            objective: str = dspy.InputField()
            context: str = dspy.InputField()
            mode: str = dspy.InputField()
            spec_id: str = dspy.InputField()
            scope_decision: str = dspy.InputField()
            answer: str = dspy.OutputField(desc="direct user-facing answer or one focused clarification")
            confidence: float = dspy.OutputField(desc="finite confidence from 0 to 1")
            material_uncertainties: list[str] = dspy.OutputField(
                desc="0 to 4 short observable uncertainties that materially affect the answer"
            )
            assumptions: list[str] = dspy.OutputField(
                desc="0 to 4 short observable assumptions that materially affect the answer"
            )

        self._dspy = dspy
        self._lm = build_lm(model)
        self._program = dspy.Predict(ReasonSignature)

    def run(
        self,
        *,
        objective: str,
        context: str,
        mode: str,
        spec_id: str,
        scope_decision: ScopeDecision,
    ) -> ReasonResult:
        with self._dspy.context(lm=self._lm):
            prediction = self._program(
                objective=objective,
                context=context,
                mode=mode,
                spec_id=spec_id,
                scope_decision=scope_decision.value,
            )
        return ReasonResult(
            answer=str(prediction.answer),
            confidence=float(prediction.confidence),
            material_uncertainties=list(prediction.material_uncertainties),
            assumptions=list(prediction.assumptions),
            program_version=self.version,
        )
