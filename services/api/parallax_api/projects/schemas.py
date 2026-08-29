from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")
REPOSITORY_REF_PATTERN = re.compile(
    r"^(?P<provider>[a-z][a-z0-9-]{1,31}):"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?)/"
    r"(?P<repo>[A-Za-z0-9](?:[A-Za-z0-9_.-]{0,98}[A-Za-z0-9])?)$"
)
ProjectDeliveryMode = Literal["source-only", "vercel-preview"]


def normalize_slug(value: str) -> str:
    normalized = value.strip().lower()
    if not SLUG_PATTERN.fullmatch(normalized):
        raise ValueError("slug must contain only lowercase letters, digits, and interior hyphens")
    return normalized


def slug_from_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    normalized = normalized[:80].rstrip("-")
    if not normalized or not SLUG_PATTERN.fullmatch(normalized):
        raise ValueError("project name cannot produce a valid slug; provide an explicit slug")
    return normalized


def normalize_repository_ref(value: str) -> str:
    candidate = value.strip()
    if "://" in candidate or "@" in candidate or "\\" in candidate or candidate.count("/") != 1:
        raise ValueError("repository_ref must use provider:owner/name identity form")
    match = REPOSITORY_REF_PATTERN.fullmatch(candidate)
    if not match:
        raise ValueError("repository_ref must use provider:owner/name identity form")
    owner = match.group("owner")
    repo = match.group("repo")
    if owner in {".", ".."} or repo in {".", ".."}:
        raise ValueError("repository_ref contains an invalid owner or repository segment")
    return f"{match.group('provider').lower()}:{owner}/{repo}"


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=2000)
    repository_ref: str | None = Field(default=None, max_length=240)
    delivery_mode: ProjectDeliveryMode = "source-only"

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str | None) -> str | None:
        return normalize_slug(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("repository_ref")
    @classmethod
    def validate_repository_ref(cls, value: str | None) -> str | None:
        return normalize_repository_ref(value) if value is not None else None


class ProjectDeliveryModeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    delivery_mode: ProjectDeliveryMode


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    description: str | None
    repository_ref: str | None
    workspace_ref: str
    delivery_mode: ProjectDeliveryMode
    status: str
    created_at: datetime
    updated_at: datetime
