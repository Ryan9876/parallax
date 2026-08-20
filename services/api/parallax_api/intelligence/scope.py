from __future__ import annotations

from enum import Enum
from math import isfinite
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .dspy_programs import build_lm
from .protected_metrics import evaluate_scope_output


class ScopeDecision(str, Enum):
    CONTINUE = "CONTINUE"
    CLARIFY = "CLARIFY"
    SPEC_AMENDMENT = "SPEC_AMENDMENT"


class ScopeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    decision: ScopeDecision
    confidence: float = Field(ge=0.0, le=1.0)
    material_factors: list[str] = Field(min_length=1, max_length=4)
    program_version: str = Field(min_length=1, max_length=100)

    @field_validator("material_factors")
    @classmethod
    def validate_factors(cls, factors: list[str]) -> list[str]:
        clean: list[str] = []
        for factor in factors:
            value = factor.strip()
            if not value:
                raise ValueError("scope material factors may not be empty")
            if len(value) > 240:
                raise ValueError("scope material factor exceeds 240 characters")
            clean.append(value)
        return clean


class ScopeResolution(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    decision: ScopeDecision
    confidence: float = Field(ge=0.0, le=1.0)
    material_factors: list[str] = Field(min_length=1, max_length=4)
    program_version: str = Field(min_length=1, max_length=100)
    policy_version: str = Field(min_length=1, max_length=100)
    override_used: bool = False
    policy_adjustment: str | None = Field(default=None, max_length=160)


class ScopeProgram(Protocol):
    version: str

    def run(self, *, current_user_turn: str, context: str) -> ScopeProposal: ...


class ProtectedScopePolicy:
    version = "scope-policy-v0.3.0"
    amendment_confidence_floor = 0.72

    def resolve(
        self,
        proposal: ScopeProposal,
        *,
        explicit_test_override: bool = False,
    ) -> ScopeResolution:
        metric = evaluate_scope_output(proposal.model_dump(mode="json"))
        if not metric.passed:
            raise ValueError(f"scope proposal failed protected validation: {metric.failures}")
        if not isfinite(proposal.confidence):
            raise ValueError("scope proposal confidence must be finite")

        if explicit_test_override:
            return ScopeResolution(
                decision=ScopeDecision.SPEC_AMENDMENT,
                confidence=1.0,
                material_factors=["Explicit test/developer scope override."],
                program_version=proposal.program_version,
                policy_version=self.version,
                override_used=True,
                policy_adjustment="explicit_test_override",
            )

        if (
            proposal.decision is ScopeDecision.SPEC_AMENDMENT
            and proposal.confidence < self.amendment_confidence_floor
        ):
            return ScopeResolution(
                decision=ScopeDecision.CLARIFY,
                confidence=proposal.confidence,
                material_factors=proposal.material_factors,
                program_version=proposal.program_version,
                policy_version=self.version,
                override_used=False,
                policy_adjustment="low_confidence_amendment_requires_clarification",
            )

        return ScopeResolution(
            decision=proposal.decision,
            confidence=proposal.confidence,
            material_factors=proposal.material_factors,
            program_version=proposal.program_version,
            policy_version=self.version,
            override_used=False,
        )


class DspyScopeProgram:
    version = "scope-v0.3.0"

    def __init__(self, model: str):
        try:
            import dspy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("DSPy is required for the live scope program") from exc

        class ScopeSignature(dspy.Signature):
            """Classify the current turn against the active approved objective.

            Return CONTINUE for ordinary follow-ups, CLARIFY only when missing
            information materially blocks a useful safe answer, and
            SPEC_AMENDMENT only for a material objective/scope change. Return
            observable factors only; never return hidden reasoning.
            """

            current_user_turn: str = dspy.InputField()
            context: str = dspy.InputField()
            decision: str = dspy.OutputField(desc="CONTINUE, CLARIFY, or SPEC_AMENDMENT")
            confidence: float = dspy.OutputField(desc="finite confidence from 0 to 1")
            material_factors: list[str] = dspy.OutputField(
                desc="1 to 4 short observable factors; no chain-of-thought or secrets"
            )

        self._dspy = dspy
        self._lm = build_lm(model)
        self._program = dspy.Predict(ScopeSignature)

    def run(self, *, current_user_turn: str, context: str) -> ScopeProposal:
        with self._dspy.context(lm=self._lm):
            prediction = self._program(current_user_turn=current_user_turn, context=context)
        return ScopeProposal(
            decision=str(prediction.decision).strip(),
            confidence=float(prediction.confidence),
            material_factors=list(prediction.material_factors),
            program_version=self.version,
        )
