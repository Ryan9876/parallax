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
    value = os.getenv("PARALLAX_ACTIVE_SPEC_ID", "P2-V0.3.0").strip()
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


settings = Settings()
