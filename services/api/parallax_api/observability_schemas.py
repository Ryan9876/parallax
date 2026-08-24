from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RunEventRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    run_id: str
    sequence: int = Field(ge=1)
    event_key: str
    event_type: str
    stage: str | None = None
    outcome: str
    subsystem: str
    attempt_id: str | None = None
    worker_execution_id: str | None = None
    source_lineage_ref: str | None = None
    parent_source_lineage_ref: str | None = None
    operation_ref: str | None = None
    artifact_ref: str | None = None
    evidence_ref: str | None = None
    failure_code: str | None = None
    summary: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    occurred_at: datetime
    created_at: datetime


class RunEventPageRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[RunEventRead] = Field(default_factory=list)
    next_after_sequence: int = Field(ge=0)
    has_more: bool


class SourceTreeFileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str
    size: int = Field(ge=0)


class SourceTreeRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str
    lineage_id: str
    parent_lineage_id: str | None = None
    content_digest: str
    source_kind: str
    file_count: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    files: list[SourceTreeFileRead] = Field(default_factory=list)
    next_offset: int = Field(ge=0)
    has_more: bool


class SourceFileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str
    lineage_id: str
    path: str
    sha256: str
    size: int = Field(ge=0)
    availability: Literal["TEXT", "BINARY", "TOO_LARGE"]
    text: str | None = None


class SourceDiffFileRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    change_type: Literal["ADDED", "REMOVED", "MODIFIED"]
    from_sha256: str | None = None
    from_size: int | None = Field(default=None, ge=0)
    to_sha256: str | None = None
    to_size: int | None = Field(default=None, ge=0)
    availability: Literal["TEXT", "BINARY", "TOO_LARGE"]
    diff_text: str | None = None
    truncated: bool


class SourceDiffRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str
    from_lineage: str
    to_lineage: str
    unchanged_count: int = Field(ge=0)
    changed_count: int = Field(ge=0)
    files: list[SourceDiffFileRead] = Field(default_factory=list)
    truncated: bool


class EngineeringAttemptEvidenceRead(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str
    run_id: str
    attempt_id: str
    stage: Literal["BUILD", "TEST", "VERIFY"]
    attempt_number: int = Field(ge=1)
    status: str
    program_id: str | None = None
    model_id: str | None = None
    tool_id: str | None = None
    failure_code: str | None = None
    started_at: datetime
    completed_at: datetime
    availability: Literal["AVAILABLE", "UNAVAILABLE", "REDACTED"]
    evidence: dict[str, object] = Field(default_factory=dict)


__all__ = [
    "EngineeringAttemptEvidenceRead",
    "RunEventPageRead",
    "RunEventRead",
    "SourceDiffFileRead",
    "SourceDiffRead",
    "SourceFileRead",
    "SourceTreeFileRead",
    "SourceTreeRead",
]
