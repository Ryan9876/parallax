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
_ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
_RESERVED_CREDENTIAL_ENVS = {
    "ACCESS_TOKEN",
    "AI_GATEWAY_API_KEY",
    "OPENAI_API_KEY",
    "PARALLAX_ACCESS_TOKEN",
    "VERCEL_AI_GATEWAY_API_KEY",
    "VERCEL_OIDC_TOKEN",
}


class ModelRouteConfigurationError(RuntimeError):
    """Fail-closed server model-route configuration error without secret content."""


@dataclass(frozen=True, slots=True)
class ModelRoute:
    model: str
    provider_kind: str
    api_base: str | None = None
    api_key_env: str | None = None


def _env_bool(name: str) -> bool:
    value = os.getenv(name)
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


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
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ModelRouteConfigurationError("local model API base contains unsupported authority or URL components")

    loopback = _is_loopback_host(parsed.hostname)
    if parsed.scheme == "http" and not loopback:
        raise ModelRouteConfigurationError("remote local-model endpoints must use HTTPS")
    if os.getenv("VERCEL_ENV") == "production" and loopback:
        raise ModelRouteConfigurationError("Vercel production cannot use a loopback local-model endpoint")
    return value.rstrip("/")


def _local_route() -> ModelRoute | None:
    if not _env_bool(_LOCAL_ENABLED_ENV):
        return None

    model = (os.getenv(_LOCAL_MODEL_ENV) or "").strip()
    provider_kind = (os.getenv(_LOCAL_PROVIDER_ENV) or "").strip().lower()
    api_base = _validate_api_base(os.getenv(_LOCAL_API_BASE_ENV) or "")
    api_key_env = (os.getenv(_LOCAL_API_KEY_ENV_ENV) or "").strip() or None

    if not _MODEL_ID_RE.fullmatch(model):
        raise ModelRouteConfigurationError("local model identity is invalid")
    if model in HOSTED_MODEL_ORDER:
        raise ModelRouteConfigurationError("local model identity collides with the canonical hosted model chain")
    if provider_kind not in _ALLOWED_LOCAL_PROVIDERS:
        raise ModelRouteConfigurationError("local model provider kind is unsupported")
    if api_key_env is not None:
        if not _ENV_NAME_RE.fullmatch(api_key_env):
            raise ModelRouteConfigurationError("local model credential slot identity is invalid")
        if api_key_env in _RESERVED_CREDENTIAL_ENVS:
            raise ModelRouteConfigurationError("local model credential slot cannot reuse a reserved credential")

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
    local = local_route_for_model(model)
    if local is not None:
        return local.provider_kind
    if model in HOSTED_MODEL_ORDER:
        return "vercel_ai_gateway"
    return "provider"
