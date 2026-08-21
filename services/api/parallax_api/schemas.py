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


class ResponseRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    material_scope_change: bool = False


class EngineeringRunCreate(BaseModel):
    conversation_id: str
    spec_id: str
    workspace_ref: str | None = Field(default=None, max_length=300)


class EngineeringRunEnsure(EngineeringRunCreate):
    pass


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


class EngineeringRunRead(BaseModel):
    id: str
    conversation_id: str
    spec_id: str
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
