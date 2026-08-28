from __future__ import annotations

import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..code.agentic_observability import (
    AgenticObservabilityError,
    AgenticObservabilityScopeError,
    AgenticObservabilityService,
)
from ..code.service import EngineeringRunService
from ..repositories.run_events import RunEventRepository
from ..repositories.worker_executions import WorkerExecutionRepository
from .engineering_runs import invoke, service


router = APIRouter(tags=["agentic-observability"])
_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"


class RuntimeMetricRead(BaseModel):
    metric: Literal[
        "run.elapsed_seconds",
        "attempt.retry_count",
        "worker.retry_count",
        "human.intervention_count",
        "provider.usage_units",
        "provider.cost_usd",
    ]
    unit: Literal["seconds", "count", "usage_units", "usd"]
    source_kind: str
    retention_class: Literal[
        "CANONICAL_REFERENCE",
        "PROTECTED_RELEASE_EVIDENCE",
        "OPERATIONAL_SUMMARY",
        "EPHEMERAL_DIAGNOSTIC",
    ]
    state: Literal["OBSERVED", "ESTIMATED", "UNKNOWN"]
    value: float | None
    provenance_ref: str | None


class CompatibleProjectionMetricRead(BaseModel):
    metric: Literal["elapsed_time", "cost_usage", "human_interventions"]
    state: Literal["OBSERVED", "ESTIMATED", "UNKNOWN"]
    value: float | None
    provenance_ref: str | None


class QualityProjectionRead(BaseModel):
    deterministic_disposition: Literal["PASSED", "FAILED", "PENDING"]
    effective_disposition: Literal["PASSED", "FAILED", "PENDING"]
    evaluation_outcome: str | None
    preview_status: str | None
    deterministic_failure_authoritative: bool


class RuntimeEvidenceCoverageRead(BaseModel):
    attempt_count: int = Field(ge=0)
    unique_event_count: int = Field(ge=0, le=200)
    event_plane_available: bool
    worker_evidence_available: bool
    known_metric_count: int = Field(ge=0)
    estimated_metric_count: int = Field(ge=0)
    unknown_metric_count: int = Field(ge=0)


class RetentionProjectionRead(BaseModel):
    mode: Literal["QUERY_TIME"]
    persisted_derived_rows: Literal[False]
    cleanup_required: Literal[False]
    cleanup_mutation_available: Literal[False]
    canonical_deletion_authority: Literal[False]
    audit_ref: Literal["s5-retention:query-time:v1"]


class AgenticRunObservabilityRead(BaseModel):
    observability_version: Literal[1]
    project_id: str
    run_id: str
    run_state: str
    run_revision: int = Field(ge=0)
    projection_fingerprint: str = Field(min_length=64, max_length=64)
    latest_event_sequence: int = Field(ge=0)
    metrics: list[RuntimeMetricRead] = Field(max_length=16)
    s2_compatible_metrics: list[CompatibleProjectionMetricRead] = Field(max_length=3)
    quality: QualityProjectionRead
    coverage: RuntimeEvidenceCoverageRead
    retention: RetentionProjectionRead
    creates_scheduler: Literal[False]
    creates_billing_ledger: Literal[False]
    creates_state_machine: Literal[False]
    grants_lifecycle_authority: Literal[False]
    grants_source_authority: Literal[False]
    grants_provider_authority: Literal[False]
    grants_tool_authority: Literal[False]
    executes_arbitrary_command: Literal[False]
    performs_arbitrary_network: Literal[False]
    performs_merge: Literal[False]
    performs_production_deployment: Literal[False]
    completes_review: Literal[False]
    contains_credentials: Literal[False]
    contains_provider_payload: Literal[False]
    contains_prompts: Literal[False]
    contains_hidden_reasoning: Literal[False]
    contains_source_bytes: Literal[False]
    contains_unrestricted_logs: Literal[False]
    fingerprint: str = Field(min_length=64, max_length=64)


class ProjectObservabilityHistoryRead(BaseModel):
    observability_version: Literal[1]
    project_id: str
    limit: int = Field(ge=1, le=25)
    run_count: int = Field(ge=0, le=25)
    runs: list[AgenticRunObservabilityRead] = Field(max_length=25)
    retention: RetentionProjectionRead
    cross_project_aggregate: Literal[False]
    contains_private_project_payload: Literal[False]
    fingerprint: str = Field(min_length=64, max_length=64)


def _facade(svc: EngineeringRunService) -> AgenticObservabilityService:
    events = None
    if os.getenv(_RUN_EVENTS_ENABLE_ENV) == "1":
        events = RunEventRepository(svc.runs.session)
    return AgenticObservabilityService(
        svc,
        WorkerExecutionRepository(svc.runs.session),
        events=events,
    )


def _invoke_observability(call):
    try:
        return call()
    except AgenticObservabilityScopeError as exc:
        raise HTTPException(404, "agentic observability scope is unavailable") from exc
    except AgenticObservabilityError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get(
    "/v1/engineering-runs/{run_id}/observability",
    response_model=AgenticRunObservabilityRead,
)
def get_agentic_run_observability(
    run_id: str,
    svc: EngineeringRunService = Depends(service),
):
    run = invoke(lambda: svc.get(run_id))
    if not run.project_id:
        raise HTTPException(404, "agentic observability scope is unavailable")
    projection = _invoke_observability(
        lambda: _facade(svc).project_run(project_id=run.project_id or "", run_id=run_id)
    )
    return projection.as_dict()


@router.get(
    "/v1/projects/{project_id}/agentic-observability",
    response_model=ProjectObservabilityHistoryRead,
)
def get_project_agentic_observability(
    project_id: str,
    limit: int = Query(default=10, ge=1, le=25),
    svc: EngineeringRunService = Depends(service),
):
    history = _invoke_observability(
        lambda: _facade(svc).project_history(project_id=project_id, limit=limit)
    )
    return history.as_dict()
