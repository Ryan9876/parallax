from __future__ import annotations

from dataclasses import dataclass
import os


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


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
    allow_scope_override: bool = _env_bool("PARALLAX_ALLOW_SCOPE_OVERRIDE", False)


settings = Settings()
