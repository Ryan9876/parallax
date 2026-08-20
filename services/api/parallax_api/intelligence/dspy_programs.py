from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .protected_metrics import evaluate_reasoning_output


@dataclass(frozen=True)
class ReasoningResult:
    answer: str
    confidence: float
    program_version: str


class ReasoningProgram(Protocol):
    def run(self, *, objective: str, context: str, mode: str) -> ReasoningResult: ...


def _dspy():
    try:
        import dspy  # type: ignore
    except ImportError as exc:
        raise RuntimeError("DSPy is required for the live reasoning program. Install service dependencies first.") from exc
    return dspy


class DspyReasoningProgram:
    version = "reasoning-v0.1.0"

    def __init__(self, model: str):
        dspy = _dspy()

        class Reason(dspy.Signature):
            """Answer the active objective while preserving prior context and distinguishing material uncertainty."""

            objective: str = dspy.InputField()
            context: str = dspy.InputField()
            mode: str = dspy.InputField()
            answer: str = dspy.OutputField(desc="concise but complete answer for the user")
            confidence: float = dspy.OutputField(desc="0 to 1 confidence in the answer")

        self._dspy = dspy
        self._lm = dspy.LM(model)
        self._program = dspy.ChainOfThought(Reason)

    def run(self, *, objective: str, context: str, mode: str) -> ReasoningResult:
        with self._dspy.context(lm=self._lm):
            prediction = self._program(objective=objective, context=context, mode=mode)
        result = ReasoningResult(
            answer=str(prediction.answer).strip(),
            confidence=max(0.0, min(1.0, float(prediction.confidence))),
            program_version=self.version,
        )
        metric = evaluate_reasoning_output(result.answer)
        if not metric.passed:
            raise ValueError(f"Reasoning output failed protected validation: {metric.failures}")
        return result


def build_spec_compiler(model: str):
    dspy = _dspy()

    class CompileSpec(dspy.Signature):
        """Convert an approved software specification into a dependency-ordered implementation plan without changing protected requirements."""

        specification: str = dspy.InputField()
        implementation_plan_json: str = dspy.OutputField(
            desc="JSON with architecture decisions, ordered work items, files, validations, risks, and spec acceptance IDs"
        )

    lm = dspy.LM(model)
    program = dspy.ChainOfThought(CompileSpec)
    return dspy, lm, program


def build_spec_critic(model: str):
    dspy = _dspy()

    class Critic(dspy.Signature):
        """Critique an approved software specification for contradictions, missing acceptance criteria, hidden dependencies, unsafe optimizer boundaries, and deployment risks."""

        specification: str = dspy.InputField()
        critique_json: str = dspy.OutputField(desc="JSON array of material findings only")

    lm = dspy.LM(model)
    program = dspy.ChainOfThought(Critic)
    return dspy, lm, program
