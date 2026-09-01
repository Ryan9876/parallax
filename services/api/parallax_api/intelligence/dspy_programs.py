from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import logging
import os
from typing import Any, Iterator, Protocol

from .model_routes import local_route_for_model
from .protected_metrics import evaluate_reasoning_output


_GATEWAY_API_BASE = "https://ai-gateway.vercel.sh/v1"
_GATEWAY_CREDENTIAL_ENV = (
    "AI_GATEWAY_API_KEY",
    "VERCEL_AI_GATEWAY_API_KEY",
)
_GATEWAY_MODEL_PREFIX = "vercel_ai_gateway/"
_HOSTED_MODEL_TIMEOUT_SECONDS = 60
_HOSTED_MODEL_NUM_RETRIES = 0
_LOCAL_DEFAULT_MAX_TOKENS = 384
_LOCAL_SPEC_COMPILER_MAX_TOKENS = 640
_REQUEST_GATEWAY_CREDENTIAL: ContextVar[str | None] = ContextVar(
    "parallax_request_gateway_credential",
    default=None,
)
logger = logging.getLogger(__name__)


class ModelTransportConfigurationError(RuntimeError):
    """Sanitized failure establishing the server-owned model transport boundary."""


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


def _local_development() -> bool:
    return os.getenv("DSPY_LOCAL_DEVELOPMENT") == "1"


def _production_runtime() -> bool:
    return os.getenv("VERCEL_ENV") == "production"


def _has_explicit_dspy_override() -> bool:
    """Treat even an explicitly empty DSPY key as an intentional endpoint override."""

    return "DSPY_API_BASE" in os.environ or "DSPY_API_KEY" in os.environ


def _gateway_api_key() -> str | None:
    """Resolve bounded non-request Gateway credentials; build-time OIDC is excluded."""

    for name in _GATEWAY_CREDENTIAL_ENV:
        value = os.getenv(name)
        if value:
            return value
    return None


@contextmanager
def request_model_gateway_credential(credential: str | None) -> Iterator[None]:
    """Bind one already-validated request credential to downstream DSPy construction.

    The opaque credential is request-local only. ContextVar propagation reaches
    `asyncio.to_thread` / AnyIO worker execution while reset prevents credential
    reuse by a later request. Validation of Vercel's request OIDC shape remains
    owned by the existing `runtime_vercel_oidc_token` boundary.
    """

    if credential is not None and (not isinstance(credential, str) or not credential):
        raise ModelTransportConfigurationError("request model gateway credential is invalid")
    token = _REQUEST_GATEWAY_CREDENTIAL.set(credential)
    try:
        yield
    finally:
        _REQUEST_GATEWAY_CREDENTIAL.reset(token)


def build_lm(model: str, *, local_max_tokens: int = _LOCAL_DEFAULT_MAX_TOKENS):
    """Build a DSPy LM with canonical identity and a bounded transport boundary.

    Explicit DSPY endpoint settings remain deliberate operator/development
    authority and win first. A server-admitted local route may bind transport
    only for its exact model outside Vercel production. Production request-scoped
    OIDC is admitted only by the request boundary and is sent to Vercel's fixed
    OpenAI-compatible AI Gateway without rewriting canonical `openai/...` IDs.

    Process-environment `VERCEL_OIDC_TOKEN` is deliberately ignored: Vercel
    Functions use request-scoped OIDC and the build-time token is not runtime
    authority. Production cannot silently fall back to direct OpenAI or a local
    endpoint.
    """

    if not isinstance(local_max_tokens, int) or local_max_tokens <= 0:
        raise ValueError("local_max_tokens must be a positive integer")

    dspy = _dspy()
    api_base = os.getenv("DSPY_API_BASE")
    api_key = os.getenv("DSPY_API_KEY")
    model_type = os.getenv("DSPY_MODEL_TYPE")
    explicit_override = _has_explicit_dspy_override()

    kwargs: dict[str, object] = {}

    if explicit_override:
        if api_base:
            kwargs["api_base"] = api_base
        if api_key is not None:
            kwargs["api_key"] = api_key
    else:
        if model.startswith(_GATEWAY_MODEL_PREFIX):
            raise ModelTransportConfigurationError("canonical Parallax model identity is required")

        local_route = local_route_for_model(model)
        if local_route is not None:
            if local_route.api_base is None:
                raise ModelTransportConfigurationError("local model endpoint is unavailable")
            kwargs["api_base"] = local_route.api_base
            if local_route.api_key_env is not None:
                local_key = os.getenv(local_route.api_key_env)
                if not local_key:
                    raise ModelTransportConfigurationError("local model credential is unavailable")
                kwargs["api_key"] = local_key
            logger.info(
                "parallax_model_transport transport=%s model=%s",
                local_route.provider_kind,
                model,
            )
        else:
            request_gateway_key = _REQUEST_GATEWAY_CREDENTIAL.get()
            if _production_runtime() and model.startswith("openai/") and request_gateway_key is None:
                raise ModelTransportConfigurationError("production model gateway credential is unavailable")

            gateway_key = request_gateway_key if request_gateway_key is not None else _gateway_api_key()
            if gateway_key is not None and model.startswith("openai/"):
                kwargs["api_base"] = _GATEWAY_API_BASE
                kwargs["api_key"] = gateway_key
                if _production_runtime():
                    kwargs["timeout"] = _HOSTED_MODEL_TIMEOUT_SECONDS
                    kwargs["num_retries"] = _HOSTED_MODEL_NUM_RETRIES
                logger.info("parallax_model_transport transport=vercel_ai_gateway model=%s", model)

    if model_type:
        kwargs["model_type"] = model_type
    if _local_development():
        # The local CI LM proves that the DSPy development path executes; it is
        # not the plan-quality authority. A small non-zero temperature avoids
        # the deterministic repetition loops seen with tiny CPU-only models.
        kwargs["temperature"] = 0.15
        kwargs["max_tokens"] = local_max_tokens
        kwargs["num_retries"] = 1
    return dspy.LM(model, **kwargs)


_PLAN_LIMITS = {
    "architecture_decisions": 3,
    "work_items": 4,
    "validations": 3,
    "risks": 2,
}

_LOCAL_SCALAR_FIELDS = {
    "architecture_decisions": "architecture_decision",
    "work_items": "work_item",
    "validations": "validation",
    "risks": "risk",
}


def plan_from_prediction(prediction: Any) -> dict[str, list[str]]:
    """Normalize DSPy compiler output into the protected plan shape.

    Provider-backed compilation uses richer list fields. The credential-free
    proof model uses one bounded scalar per semantic field because a 0.5B model
    is not reliable at generating several typed arrays. Both paths still have
    DSPy propose architecture/work/validation/risk content; deterministic
    protected code later injects the exact acceptance map and coverage gaps.
    """

    plan: dict[str, list[str]] = {}
    for key, limit in _PLAN_LIMITS.items():
        raw = getattr(prediction, key, None)
        if isinstance(raw, list):
            clean = [str(item).strip() for item in raw if str(item).strip()]
        elif _local_development():
            scalar_name = _LOCAL_SCALAR_FIELDS[key]
            scalar = getattr(prediction, scalar_name, None)
            clean = [str(scalar).strip()] if scalar is not None and str(scalar).strip() else []
        else:
            raise TypeError(f"DSPy compiler field {key} must be a list")

        if not clean:
            raise ValueError(f"DSPy compiler field {key} must not be empty")
        plan[key] = clean[:limit] if _local_development() else clean
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

    if _local_development():
        class CompileSpec(dspy.Signature):
            """Propose one concise item for each implementation-plan dimension from an approved specification. Do not enumerate versions or repeat text."""

            specification: str = dspy.InputField()
            architecture_decision: str = dspy.OutputField(
                desc="One architecture decision, maximum 160 characters"
            )
            work_item: str = dspy.OutputField(
                desc="One concrete implementation work item, maximum 160 characters"
            )
            validation: str = dspy.OutputField(
                desc="One executable validation or evidence check, maximum 160 characters"
            )
            risk: str = dspy.OutputField(
                desc="One material risk and mitigation, maximum 160 characters"
            )
    else:
        class CompileSpec(dspy.Signature):
            """Convert an approved software specification into a compact dependency-ordered implementation plan without changing protected requirements. Never repeat an item."""

            specification: str = dspy.InputField()
            architecture_decisions: list[str] = dspy.OutputField(
                desc="Exactly 3 concise architecture decisions, one sentence each. Reference relevant AC IDs. Do not repeat."
            )
            work_items: list[str] = dspy.OutputField(
                desc="Exactly 4 concise dependency-ordered work items, one sentence each. Reference relevant AC IDs. Do not repeat."
            )
            validations: list[str] = dspy.OutputField(
                desc="Exactly 3 concise executable validation/evidence checks, one sentence each. Reference relevant AC IDs. Do not repeat."
            )
            risks: list[str] = dspy.OutputField(
                desc="Exactly 2 concise material risk-and-mitigation items, one sentence each. Do not repeat."
            )

    lm = build_lm(
        model,
        local_max_tokens=_LOCAL_SPEC_COMPILER_MAX_TOKENS if _local_development() else _LOCAL_DEFAULT_MAX_TOKENS,
    )
    # Predict is deliberate here. Structured outputs are the contract; extra
    # chain-of-thought text only makes small development LMs less reliable.
    program = dspy.Predict(CompileSpec)
    return dspy, lm, program


def build_spec_critic(model: str):
    dspy = _dspy()

    if _local_development():
        class Critic(dspy.Signature):
            """Identify the single most material implementation risk or omission in an approved software specification."""

            specification: str = dspy.InputField()
            finding: str = dspy.OutputField(
                desc="One concise material finding, maximum 180 characters; use 'none' if no material issue"
            )
    else:
        class Critic(dspy.Signature):
            """Critique an approved software specification for contradictions, missing acceptance criteria, hidden dependencies, unsafe optimizer boundaries, and deployment risks."""

            specification: str = dspy.InputField()
            findings: list[str] = dspy.OutputField(
                desc="At most 3 concise material findings. Return an empty list when there is no material finding. Never repeat a finding."
            )

    lm = build_lm(model)
    program = dspy.Predict(Critic)
    return dspy, lm, program
