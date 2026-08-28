from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..code.agent_run_projection import build_agent_run_projection
from ..code.service import EngineeringRunService
from ..repositories.run_events import RunEventRepository
from .engineering_runs import invoke, service


router = APIRouter(prefix="/v1/engineering-runs", tags=["engineering-run-projection"])
_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"


class ProjectionIdentityRead(BaseModel):
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    acceptance_ids: list[str]


class ProjectedAttemptRead(BaseModel):
    attempt_id: str
    stage: str
    attempt_number: int
    status: str
    failure_code: str | None
    program_id: str | None
    tool_id: str | None


class ProjectedEventRead(BaseModel):
    sequence: int
    event_type: str
    outcome: str
    subsystem: str
    stage: str | None
    attempt_id: str | None
    worker_execution_id: str | None
    source_lineage_ref: str | None
    evidence_ref: str | None
    failure_code: str | None
    summary: str | None
    metadata: dict[str, object] = Field(default_factory=dict)


class ProjectionMetricRead(BaseModel):
    metric: Literal["elapsed_time", "cost_usage", "human_interventions"]
    state: Literal["OBSERVED", "ESTIMATED", "UNKNOWN"]
    value: float | None
    provenance_ref: str | None


class AgentRunProjectionRead(BaseModel):
    projection_version: Literal[1]
    identity: ProjectionIdentityRead
    current_state: str
    run_revision: int
    resume_stage: str | None
    last_failure_code: str | None
    latest_source_lineage_ref: str | None
    preview_deployment_id: str | None
    preview_status: str | None
    attempts: list[ProjectedAttemptRead]
    events: list[ProjectedEventRead]
    metrics: list[ProjectionMetricRead]
    advertised_controls: list[str] = Field(default_factory=list)
    accepts_source_lineage: Literal[False]
    transitions_engineering_run: Literal[False]
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


@router.get("/{run_id}/projection", response_model=AgentRunProjectionRead)
def get_agent_run_projection(
    run_id: str,
    svc: EngineeringRunService = Depends(service),
):
    run = invoke(lambda: svc.get(run_id))
    acceptance = invoke(lambda: svc.acceptance_map_for_run(run))
    acceptance_ids = tuple(item["id"] for item in acceptance)
    events = ()
    if os.getenv(_RUN_EVENTS_ENABLE_ENV) == "1" and run.project_id:
        events = invoke(
            lambda: RunEventRepository(svc.runs.session).list_for_run(
                project_id=run.project_id or "",
                run_id=run.id,
                limit=200,
            )
        )
    projection = invoke(
        lambda: build_agent_run_projection(
            run=run,
            acceptance_ids=acceptance_ids,
            events=events,
        )
    )
    return projection.as_dict()
