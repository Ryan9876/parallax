from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from ..code.agent_run_projection import (
    AgentRunProjectionService,
    ProjectionControlRequest,
)
from ..code.service import EngineeringRunService
from ..repositories.run_events import RunEventRepository
from ..repositories.worker_executions import WorkerExecutionRepository
from ..schemas import EngineeringOperationRead
from .engineering_runs import invoke, result_payload, service


router = APIRouter(prefix="/v1/engineering-runs", tags=["engineering-run-projection"])
_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"


class ProjectionIdentityRead(BaseModel):
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: list[str]


class ProjectedTaskRead(BaseModel):
    task_id: str
    stage: str
    attempt_number: int
    status: str
    producer_ref: str | None
    failure_code: str | None
    started_at: str | None
    completed_at: str | None


class RecoveryProjectionRead(BaseModel):
    execution_id: str | None
    state: str | None
    lease_generation: int | None
    checkpoint_revision: int | None
    current_step: str | None
    source_lineage_ref: str | None
    last_known_good_lineage_ref: str | None
    retry_count: int | None
    no_progress_count: int | None
    oscillation_count: int | None
    blocker_code: str | None
    next_recovery_action: str | None


class ValidationProjectionRead(BaseModel):
    stage: str
    disposition: Literal["PASSED", "FAILED", "PENDING"]
    attempt_id: str | None
    failure_code: str | None


class EvaluationProjectionRead(BaseModel):
    evaluation_id: str | None
    outcome: str | None
    score_class: str | None
    source_lineage_ref: str | None


class RoutingProjectionRead(BaseModel):
    provider: str | None
    result_code: str | None
    outcome: str | None
    source_lineage_ref: str | None


class DeliveryProjectionRead(BaseModel):
    source_lineage_ref: str | None
    parent_source_lineage_ref: str | None
    pull_request_number: int | None
    preview_deployment_id: str | None
    preview_status: str | None
    artifact_ref: str | None


class ProjectionMetricRead(BaseModel):
    metric: Literal["elapsed_time", "cost_usage", "human_interventions"]
    state: Literal["OBSERVED", "ESTIMATED", "UNKNOWN"]
    value: float | None
    provenance_ref: str | None


class AdvertisedProjectionControlRead(BaseModel):
    kind: Literal["pause", "resume", "cancel"]
    expected_revision: int = Field(ge=0)
    expected_state: str


class AgentRunProjectionRead(BaseModel):
    projection_version: Literal[2]
    identity: ProjectionIdentityRead
    current_state: str
    run_revision: int = Field(ge=0)
    resume_stage: str | None
    last_failure_code: str | None
    latest_source_lineage_ref: str | None
    tasks: list[ProjectedTaskRead]
    recovery: RecoveryProjectionRead
    validation: list[ValidationProjectionRead]
    deterministic_disposition: Literal["PASSED", "FAILED", "PENDING"]
    evaluation: EvaluationProjectionRead
    routing: RoutingProjectionRead
    delivery: DeliveryProjectionRead
    metrics: list[ProjectionMetricRead]
    advertised_controls: list[AdvertisedProjectionControlRead] = Field(default_factory=list)
    final_handoff: Literal["HUMAN_REQUIRED"] | None
    latest_event_sequence: int = Field(ge=0)
    accepts_source_lineage: Literal[False]
    creates_lifecycle_authority: Literal[False]
    grants_provider_authority: Literal[False]
    grants_tool_authority: Literal[False]
    executes_arbitrary_command: Literal[False]
    performs_merge: Literal[False]
    performs_production_deployment: Literal[False]
    completes_review: Literal[False]
    contains_source_bytes: Literal[False]
    contains_patch: Literal[False]
    contains_credentials: Literal[False]
    contains_provider_payload: Literal[False]
    contains_prompts: Literal[False]
    contains_hidden_reasoning: Literal[False]
    contains_unrestricted_logs: Literal[False]
    fingerprint: str


class AgentRunProjectionControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=120, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/+-]*$")
    project_id: str = Field(min_length=36, max_length=36)
    expected_revision: int = Field(ge=0)
    expected_state: str = Field(min_length=1, max_length=32)
    action: Literal["pause", "resume", "cancel"]


def _projection_service(svc: EngineeringRunService) -> AgentRunProjectionService:
    events = None
    if os.getenv(_RUN_EVENTS_ENABLE_ENV) == "1":
        events = RunEventRepository(svc.runs.session)
    return AgentRunProjectionService(
        svc,
        WorkerExecutionRepository(svc.runs.session),
        events=events,
    )


@router.get("/{run_id}/projection", response_model=AgentRunProjectionRead)
def get_agent_run_projection(
    run_id: str,
    svc: EngineeringRunService = Depends(service),
):
    run = invoke(lambda: svc.get(run_id))
    if not run.project_id:
        return invoke(
            lambda: _projection_service(svc).project(project_id="historical-unbound", run_id=run_id)
        )
    projection = invoke(
        lambda: _projection_service(svc).project(project_id=run.project_id or "", run_id=run_id)
    )
    return projection.as_dict()


@router.post("/{run_id}/projection/control", response_model=EngineeringOperationRead)
def control_agent_run_projection(
    run_id: str,
    payload: AgentRunProjectionControl,
    svc: EngineeringRunService = Depends(service),
):
    facade = _projection_service(svc)
    projection = invoke(
        lambda: facade.project(project_id=payload.project_id, run_id=run_id)
    )
    request = ProjectionControlRequest(
        request_id=payload.request_id,
        project_id=payload.project_id,
        run_id=run_id,
        expected_revision=payload.expected_revision,
        expected_state=payload.expected_state,
        action=payload.action,
    )
    result = invoke(lambda: facade.control(projection, request))
    return result_payload(result, svc)
