from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import os
import re
from urllib.parse import urlsplit


HOSTED_MODEL_ORDER = (
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
    "openai/gpt-5.6-sol",
)

_LOCAL_ENABLED_ENV = "PARALLAX_LOCAL_MODEL_ENABLED"
_LOCAL_MODEL_ENV = "PARALLAX_LOCAL_MODEL"
_LOCAL_PROVIDER_ENV = "PARALLAX_LOCAL_MODEL_PROVIDER"
_LOCAL_API_BASE_ENV = "PARALLAX_LOCAL_MODEL_API_BASE"
_LOCAL_API_KEY_ENV_ENV = "PARALLAX_LOCAL_MODEL_API_KEY_ENV"
_ALLOWED_LOCAL_PROVIDERS = {"ollama", "openai_compatible"}
_MODEL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_LOCAL_CREDENTIAL_ENV_RE = re.compile(r"^PARALLAX_LOCAL_MODEL_CREDENTIAL_[A-Z0-9_]{1,96}$")
_RESERVED_CREDENTIAL_ENVS = {
    "ACCESS_TOKEN",
    "AI_GATEWAY_API_KEY",
    "DSPY_API_KEY",
    "OPENAI_API_KEY",
    "PARALLAX_ACCESS_TOKEN",
    "VERCEL_AI_GATEWAY_API_KEY",
    "VERCEL_OIDC_TOKEN",
}


class ModelRouteConfigurationError(RuntimeError):
    """Fail-closed model-route configuration error without secret content."""


@dataclass(frozen=True, slots=True)
class ModelRoute:
    model: str
    provider_kind: str
    api_base: str | None = None
    api_key_env: str | None = None


def _env_bool(name: str) -> bool:
    value = os.getenv(name)
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


def _explicit_dspy_override() -> bool:
    # Presence, including an explicitly empty key, is deliberate operator
    # authority for the whole DSPy transport and therefore disables local-first.
    return "DSPY_API_BASE" in os.environ or "DSPY_API_KEY" in os.environ


def _vercel_production() -> bool:
    return os.getenv("VERCEL_ENV") == "production"


def _is_loopback_host(hostname: str) -> bool:
    normalized = hostname.strip().lower().rstrip(".")
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def _validate_api_base(raw: str) -> str:
    value = raw.strip()
    if not value or len(value) > 500:
        raise ModelRouteConfigurationError("local model API base is invalid")

    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ModelRouteConfigurationError("local model API base must be an absolute HTTP(S) URL")
    try:
        parsed.port
    except ValueError as exc:
        raise ModelRouteConfigurationError("local model API base port is invalid") from exc
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ModelRouteConfigurationError("local model API base contains unsupported authority or URL components")

    loopback = _is_loopback_host(parsed.hostname)
    if parsed.scheme == "http" and not loopback:
        raise ModelRouteConfigurationError("non-loopback local-model endpoints must use HTTPS")
    return value.rstrip("/")


def _validate_local_model_identity(model: str, provider_kind: str) -> None:
    if not _MODEL_ID_RE.fullmatch(model):
        raise ModelRouteConfigurationError("local model identity is invalid")
    if model in HOSTED_MODEL_ORDER:
        raise ModelRouteConfigurationError("local model identity collides with the canonical hosted model chain")
    if provider_kind == "ollama" and not model.startswith(("ollama/", "ollama_chat/")):
        raise ModelRouteConfigurationError("ollama local model identity must use an ollama model namespace")
    if provider_kind == "openai_compatible" and not model.startswith("openai/"):
        raise ModelRouteConfigurationError("OpenAI-compatible local model identity must use an openai model namespace")


def _validate_local_credential_slot(api_key_env: str | None) -> None:
    if api_key_env is None:
        return
    if api_key_env in _RESERVED_CREDENTIAL_ENVS:
        raise ModelRouteConfigurationError("local model credential slot cannot reuse a reserved credential")
    if _LOCAL_CREDENTIAL_ENV_RE.fullmatch(api_key_env) is None:
        raise ModelRouteConfigurationError("local model credential slot must use the dedicated local-model namespace")
    if not os.getenv(api_key_env):
        raise ModelRouteConfigurationError("local model credential is unavailable")


def _local_route() -> ModelRoute | None:
    # Preserve the accepted compatibility contract: an explicit DSPy transport
    # override owns the whole model transport/order path and is never combined
    # with local-first routing.
    if _explicit_dspy_override() or not _env_bool(_LOCAL_ENABLED_ENV):
        return None

    # P2-V0.19.8 deliberately keeps hosted Vercel production on the accepted
    # Luna -> Terra -> Sol route. Hosted-to-private inference is a separate
    # architecture/security/deployment problem and fails before route parsing.
    if _vercel_production():
        raise ModelRouteConfigurationError("local-first model routing is unavailable in Vercel production")

    model = (os.getenv(_LOCAL_MODEL_ENV) or "").strip()
    provider_kind = (os.getenv(_LOCAL_PROVIDER_ENV) or "").strip().lower()
    if provider_kind not in _ALLOWED_LOCAL_PROVIDERS:
        raise ModelRouteConfigurationError("local model provider kind is unsupported")
    _validate_local_model_identity(model, provider_kind)

    api_base = _validate_api_base(os.getenv(_LOCAL_API_BASE_ENV) or "")
    api_key_env = (os.getenv(_LOCAL_API_KEY_ENV_ENV) or "").strip() or None
    _validate_local_credential_slot(api_key_env)

    return ModelRoute(
        model=model,
        provider_kind=provider_kind,
        api_base=api_base,
        api_key_env=api_key_env,
    )


def effective_model_routes() -> tuple[ModelRoute, ...]:
    local = _local_route()
    hosted = tuple(ModelRoute(model=model, provider_kind="vercel_ai_gateway") for model in HOSTED_MODEL_ORDER)
    return hosted if local is None else (local, *hosted)


def effective_model_order() -> tuple[str, ...]:
    return tuple(route.model for route in effective_model_routes())


def local_route_for_model(model: str) -> ModelRoute | None:
    local = _local_route()
    return local if local is not None and local.model == model else None


def provider_kind_for_model(model: str) -> str:
    if model in HOSTED_MODEL_ORDER:
        return "vercel_ai_gateway"
    local = local_route_for_model(model)
    if local is not None:
        return local.provider_kind
    return "provider"
