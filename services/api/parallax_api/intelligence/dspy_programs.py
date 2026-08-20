from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Protocol

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


def build_lm(model: str):
    """Build a DSPy LM without coupling programs to one provider."""

    dspy = _dspy()
    api_base = os.getenv("DSPY_API_BASE")
    api_key = os.getenv("DSPY_API_KEY")
    model_type = os.getenv("DSPY_MODEL_TYPE")

    kwargs: dict[str, object] = {}
    if api_base:
        kwargs["api_base"] = api_base
    if api_key is not None:
        kwargs["api_key"] = api_key
    if model_type:
        kwargs["model_type"] = model_type
    return dspy.LM(model, **kwargs)


def plan_from_prediction(prediction: Any) -> dict[str, list[str]]:
    """Normalize the typed DSPy compiler prediction into the protected plan shape.

    The model proposes implementation content, but metadata and the exact
    acceptance contract are injected later by deterministic protected code.
    """

    keys = ("architecture_decisions", "work_items", "validations", "risks")
    plan: dict[str, list[str]] = {}
    for key in keys:
        raw = getattr(prediction, key, None)
        if not isinstance(raw, list):
            raise TypeError(f"DSPy compiler field {key} must be a list")
        clean = [str(item).strip() for item in raw if str(item).strip()]
        if not clean:
            raise ValueError(f"DSPy compiler field {key} must not be empty")
        plan[key] = clean
    return plan


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
        self._lm = build_lm(model)
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
        architecture_decisions: list[str] = dspy.OutputField(
            desc="Concrete architecture decisions. Reference relevant AC IDs from the specification."
        )
        work_items: list[str] = dspy.OutputField(
            desc="Dependency-ordered implementation work items. Reference relevant AC IDs."
        )
        validations: list[str] = dspy.OutputField(
            desc="Executable validation and evidence checks. Reference relevant AC IDs."
        )
        risks: list[str] = dspy.OutputField(
            desc="Material risks and mitigations. Reference relevant AC IDs when applicable."
        )

    lm = build_lm(model)
    # Predict is deliberate here. Structured typed outputs are the contract;
    # extra chain-of-thought text only makes small local development LMs less
    # reliable without improving protected evaluation quality.
    program = dspy.Predict(CompileSpec)
    return dspy, lm, program


def build_spec_critic(model: str):
    dspy = _dspy()

    class Critic(dspy.Signature):
        """Critique an approved software specification for contradictions, missing acceptance criteria, hidden dependencies, unsafe optimizer boundaries, and deployment risks."""

        specification: str = dspy.InputField()
        findings: list[str] = dspy.OutputField(
            desc="Material findings only. Return an empty list when the approved specification has no material finding."
        )

    lm = build_lm(model)
    program = dspy.Predict(Critic)
    return dspy, lm, program
