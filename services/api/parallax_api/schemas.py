from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=100_000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    role: str
    content: str
    status: str
    created_at: datetime


class ConversationCreate(BaseModel):
    mode: Literal["reason", "code"] = "reason"


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    mode: str
    status: str
    spec_id: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = Field(default_factory=list)


class WorkSpecificationRead(BaseModel):
    id: str
    conversation_id: str
    revision: int
    status: Literal["DRAFT", "APPROVED", "SUPERSEDED"]
    title: str
    objective: str
    constraints: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    confidence: float
    program_version: str
    model_id: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class ResponseRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    material_scope_change: bool = False


class EngineeringRunCreate(BaseModel):
    conversation_id: str
    spec_id: str
    work_specification_id: str
    workspace_ref: str | None = Field(default=None, max_length=300)


class EngineeringRunActivate(BaseModel):
    conversation_id: str
    work_specification_id: str | None = None
    workspace_ref: str | None = Field(default=None, max_length=300)


class EngineeringOperation(BaseModel):
    operation_key: str = Field(min_length=1, max_length=160)
    expected_revision: int = Field(ge=0)


class EngineeringAdvance(EngineeringOperation):
    stage: str
    passed: bool
    evidence: dict[str, object] = Field(default_factory=dict)
    failure_code: str | None = Field(default=None, max_length=120)
    program_id: str | None = Field(default=None, max_length=160)
    model_id: str | None = Field(default=None, max_length=160)
    tool_id: str | None = Field(default=None, max_length=160)


class EngineeringAttemptRead(BaseModel):
    id: str
    stage: str
    attempt_number: int
    status: str
    failure_code: str | None
    evidence: dict[str, object]
    started_at: datetime
    completed_at: datetime


class EngineeringAcceptanceCriterionRead(BaseModel):
    id: str
    text: str


class EngineeringRunRead(BaseModel):
    id: str
    conversation_id: str
    spec_id: str
    work_specification_id: str | None
    work_specification_revision: int | None
    work_specification_digest: str | None
    binding_status: Literal["APPROVED_SPEC_BOUND", "HISTORICAL_UNBOUND"]
    acceptance_criteria: list[EngineeringAcceptanceCriterionRead] = Field(default_factory=list)
    state: str
    resume_stage: str | None
    revision: int
    workspace_ref: str | None
    last_failure_code: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    attempts: list[EngineeringAttemptRead]


class EngineeringOperationRead(BaseModel):
    run: EngineeringRunRead
    attempt_id: str
    replayed: bool


class AuthorizedUserRead(BaseModel):
    id: str
    email: str | None
    display_name: str | None
    avatar_url: str | None
    role: Literal["owner", "member"]
    status: Literal["active", "revoked"]
    auth_method: Literal["google", "bearer"] | None = None
    bound: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None


class AuthorizedUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class AuthorizedUserStatusUpdate(BaseModel):
    status: Literal["active", "revoked"]
