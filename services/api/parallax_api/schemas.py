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
