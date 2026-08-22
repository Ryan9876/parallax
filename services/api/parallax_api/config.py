from __future__ import annotations

from dataclasses import dataclass
import os
import re


_SPEC_ID = re.compile(r"^P2-V\d+\.\d+\.\d+$")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _active_spec_id() -> str:
    value = os.getenv("PARALLAX_ACTIVE_SPEC_ID", "P2-V0.13.0").strip()
    if not _SPEC_ID.fullmatch(value):
        raise ValueError("PARALLAX_ACTIVE_SPEC_ID must use the P2-Vx.y.z format")
    return value


@dataclass(frozen=True)
class Settings:
    environment: str = os.getenv("PARALLAX_ENV", "development")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./parallax.db")
    cors_origins: tuple[str, ...] = tuple(
        value.strip()
        for value in os.getenv(
            "PARALLAX_CORS_ORIGINS",
            "http://localhost:8081,http://localhost:19006",
        ).split(",")
        if value.strip()
    )
    cors_origin_regex: str | None = os.getenv("PARALLAX_CORS_ORIGIN_REGEX") or None
    dspy_model: str = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")
    active_spec_id: str = _active_spec_id()
    allow_scope_override: bool = _env_bool("PARALLAX_ALLOW_SCOPE_OVERRIDE", False)
    # Support both the documented PARALLAX name and Vercel-friendly ACCESS_TOKEN naming.
    access_token: str = (
        os.getenv("PARALLAX_ACCESS_TOKEN")
        or os.getenv("ACCESS_TOKEN")
        or ""
    ).strip()
    supabase_url: str = (
        os.getenv("PARALLAX_SUPABASE_URL")
        or "https://kjyenifnfjqnzfgshpwg.supabase.co"
    ).strip()
    # This is a public/publishable browser-safe key, not a service-role secret.
    supabase_publishable_key: str = (
        os.getenv("PARALLAX_SUPABASE_PUBLISHABLE_KEY")
        or "sb_publishable_r2rze_hNPMXthGCGW4hRHg_ajlu6INo"
    ).strip()
    create_schema: bool = _env_bool(
        "PARALLAX_CREATE_SCHEMA",
        os.getenv("PARALLAX_ENV", "development") in {"development", "test"},
    )

    def validate_runtime(self) -> None:
        if self.environment == "production" and len(self.access_token) < 32:
            raise ValueError("PARALLAX_ACCESS_TOKEN must contain at least 32 characters in production")
        if self.environment == "production" and not self.supabase_url.startswith("https://"):
            raise ValueError("PARALLAX_SUPABASE_URL must use HTTPS in production")
        if self.environment == "production" and not self.supabase_publishable_key:
            raise ValueError("PARALLAX_SUPABASE_PUBLISHABLE_KEY is required in production")


settings = Settings()
settings.validate_runtime()
