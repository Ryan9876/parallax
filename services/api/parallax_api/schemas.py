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
    model_config = ConfigDict(extra="forbid")
    mode: Literal["reason", "code"] = "reason"
    project_id: str | None = Field(default=None, min_length=36, max_length=36)


class ConversationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    mode: str
    status: str
    spec_id: str
    project_id: str | None = None
    project_binding_status: Literal["PROJECT_BOUND", "HISTORICAL_UNBOUND"] = "HISTORICAL_UNBOUND"
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


class BehavioralVerificationTargetRead(BaseModel):
    kind: Literal["ROLE", "LABEL", "TEST_ID", "TEXT"]
    value: str


class BehavioralVerificationActionRead(BaseModel):
    kind: Literal[
        "NAVIGATE",
        "WAIT_FOR",
        "ASSERT_VISIBLE",
        "ASSERT_ABSENT",
        "CLICK",
        "FILL",
        "SELECT",
        "ASSERT_PATH",
        "ASSERT_LAYOUT",
        "SCREENSHOT",
    ]
    path: str | None = None
    target: BehavioralVerificationTargetRead | None = None
    value: str | None = None
    checkpoint: str | None = None


class BehavioralVerificationWorkflowRead(BaseModel):
    workflow_id: str
    version: int
    viewport_ids: list[str]
    timeout_ms: int
    actions: list[BehavioralVerificationActionRead]


class BehavioralVerificationCriterionRead(BaseModel):
    acceptance_id: str
    acceptance_text: str
    mode: Literal["BROWSER", "HUMAN_ONLY"]
    workflow: BehavioralVerificationWorkflowRead | None = None


class BehavioralVerificationPlanRead(BaseModel):
    id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    revision: int
    status: Literal["DRAFT", "APPROVED", "SUPERSEDED"]
    plan_digest: str
    criteria: list[BehavioralVerificationCriterionRead]
    program_version: str
    model_id: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None


class ResponseRequest(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    material_scope_change: bool = False


class EngineeringRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str
    spec_id: str
    work_specification_id: str


class EngineeringRunActivate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    conversation_id: str
    work_specification_id: str | None = None


class EngineeringOperation(BaseModel):
    operation_key: str = Field(min_length=1, max_length=160)
    expected_revision: int = Field(ge=0)


class EngineeringReviewRework(EngineeringOperation):
    model_config = ConfigDict(extra="forbid")
    acceptance_ids: list[str] = Field(min_length=1, max_length=32)
    finding: str = Field(min_length=1, max_length=1200)


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
    project_id: str | None = None
    project_binding_status: Literal["PROJECT_BOUND", "HISTORICAL_UNBOUND"] = "HISTORICAL_UNBOUND"
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


class EngineeringAutonomyStepRead(BaseModel):
    stage: str
    outcome: str
    attempt_id: str | None = None
    replayed: bool = False
    tool_id: str | None = None


class EngineeringAutonomyRead(BaseModel):
    run: EngineeringRunRead
    stop_reason: str
    steps: list[EngineeringAutonomyStepRead] = Field(default_factory=list)


class EngineeringAutonomyProbeRead(BaseModel):
    ready: bool
    executor: str
    network_policy: str
    exit_code: int | None
    duration_ms: int
    stdout_excerpt: str
    stderr_excerpt: str
    timed_out: bool
    redacted: bool


class EngineeringWorkerHealthRead(BaseModel):
    execution_id: str
    project_id: str
    run_id: str
    state: Literal[
        "RUNNING",
        "PROGRESSING",
        "CHECKPOINTED",
        "STALLED",
        "RECOVERING",
        "REASSIGNED",
        "HUMAN_REQUIRED",
        "READY_FOR_INTEGRATION",
        "SUCCEEDED",
        "FAILED",
    ]
    lease_status: Literal["ACTIVE", "EXPIRED", "UNOWNED"]
    lease_generation: int = Field(ge=0)
    current_step: str | None
    source_lineage_ref: str | None
    last_known_good_lineage_ref: str | None
    checkpoint_revision: int = Field(ge=0)
    last_meaningful_progress_at: datetime | None
    retry_count: int = Field(ge=0)
    no_progress_count: int = Field(ge=0)
    oscillation_count: int = Field(ge=0)
    stall_classification: str | None
    blocker_code: str | None
    dependencies: list[str] = Field(default_factory=list)
    next_recovery_action: str | None
    human_required: bool


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
