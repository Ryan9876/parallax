from __future__ import annotations

from dataclasses import dataclass
import os


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
    dspy_model: str = os.getenv("DSPY_MODEL", "openai/gpt-5.6-sol")


settings = Settings()
