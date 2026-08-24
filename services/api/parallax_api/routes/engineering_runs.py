from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import AccessPrincipal, access_principal
from ..code.autonomy import AutonomyCoordinator
from ..code.domain import WorkflowStage
from ..code.production_delivery import (
    ProductionDeliveryConfigurationError,
    production_source_delivery,
)
from ..code.run_events import (
    RunEventConflict,
    RunEventPersistenceError,
    RunEventScopeError,
)
from ..code.runtime_composition import (
    DurableLineageAllocator,
    EngineeringRuntimeComposition,
    RuntimeCompositionError,
    production_durable_lineage_allocator,
)
from ..code.sandbox_execution import VercelSandboxExecutor
from ..code.service import EngineeringRunNotFound, EngineeringRunService, RunOperationResult
from ..code.state_machine import RevisionConflict, RunTransitionError
from ..code.worker_recovery import WorkerRecoveryError
from ..code.worker_service import WorkerExecutionNotFound, WorkerRecoveryService
from ..db import get_session
from ..models import EngineeringRun
from ..projects.repository import ProjectRepository
from ..repositories.conversations import ConversationRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from ..repositories.run_events import PersistentRunEventSink, RunEventRepository
from ..repositories.worker_executions import WorkerExecutionRepository
from ..repositories.work_specifications import WorkSpecificationRepository
from ..schemas import (
    EngineeringAdvance,
    EngineeringAutonomyProbeRead,
    EngineeringAutonomyRead,
    EngineeringOperation,
    EngineeringOperationRead,
    EngineeringRunActivate,
    EngineeringRunCreate,
    EngineeringRunRead,
    EngineeringWorkerHealthRead,
)

router = APIRouter(prefix="/v1/engineering-runs", tags=["engineering-runs"])


def service(
    session: Session = Depends(get_session),
    principal: AccessPrincipal = Depends(access_principal),
) -> EngineeringRunService:
    event_sink = PersistentRunEventSink(RunEventRepository(session))
    return EngineeringRunService(
        EngineeringRunRepository(session),
        ConversationRepository(session),
        WorkSpecificationRepository(session),
        ProjectRepository(session),
        owner_subject=principal.subject,
        require_project_binding=True,
        event_sink=event_sink,
    )


def runtime_lineage_allocator(
    session: Session = Depends(get_session),
) -> DurableLineageAllocator | None:
    """Construct durable lineage from server-owned persistence config.

    Immutable contents live in private Blob and lineage/head metadata remains
    transactional. Local disk is disposable materialization only.
    """

    return production_durable_lineage_allocator(session.get_bind())


def worker_recovery_service(svc: EngineeringRunService) -> WorkerRecoveryService:
    return WorkerRecoveryService(
        WorkerExecutionRepository(svc.runs.session),
        svc.runs,
        event_sink=svc.event_sink,
    )


def present(run: EngineeringRun, svc: EngineeringRunService) -> dict:
    acceptance = svc.acceptance_map_for_run(run) if run.work_specification_id else []
    return {
        "id": run.id,
        "conversation_id": run.conversation_id,
        "spec_id": run.spec_id,
        "project_id": run.project_id,
        "project_binding_status": "PROJECT_BOUND" if run.project_id else "HISTORICAL_UNBOUND",
        "work_specification_id": run.work_specification_id,
        "work_specification_revision": run.work_specification_revision,
        "work_specification_digest": run.work_specification_digest,
        "binding_status": "APPROVED_SPEC_BOUND" if run.work_specification_id else "HISTORICAL_UNBOUND",
        "acceptance_criteria": acceptance,
        "state": run.state,
        "resume_stage": run.resume_stage,
        "revision": run.revision,
        "workspace_ref": run.workspace_ref,
        "last_failure_code": run.last_failure_code,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "completed_at": run.completed_at,
        "attempts": [{
            "id": item.id,
            "stage": item.stage,
            "attempt_number": item.attempt_number,
            "status": item.status,
            "failure_code": item.failure_code,
            "evidence": json.loads(item.evidence_json),
            "started_at": item.started_at,
            "completed_at": item.completed_at,
        } for item in run.attempts],
    }


def result_payload(result: RunOperationResult, svc: EngineeringRunService) -> dict:
    return {"run": present(result.run, svc), "attempt_id": result.attempt_id, "replayed": result.replayed}


def invoke(call):
    try:
        return call()
    except (EngineeringRunNotFound, WorkerExecutionNotFound) as exc:
        raise HTTPException(404, str(exc)) from exc
    except (RevisionConflict, RunEventConflict) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ProductionDeliveryConfigurationError, RuntimeCompositionError, RunEventPersistenceError) as exc:
        raise HTTPException(503, str(exc)) from exc
    except (RunTransitionError, WorkerRecoveryError, RunEventScopeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/activate", response_model=EngineeringRunRead)
def activate_run(payload: EngineeringRunActivate, svc: EngineeringRunService = Depends(service)):
    return present(invoke(lambda: svc.activate_run(**payload.model_dump())), svc)


@router.post("", response_model=EngineeringRunRead)
def create_run(payload: EngineeringRunCreate, svc: EngineeringRunService = Depends(service)):
    return present(invoke(lambda: svc.create_run(**payload.model_dump())), svc)


@router.post("/autonomy/probe", response_model=EngineeringAutonomyProbeRead)
def autonomy_probe():
    evidence = VercelSandboxExecutor().probe(operation_key=f"probe:{uuid4().hex}")
    return {
        "ready": evidence.get("protected_success") is True,
        "executor": str(evidence.get("executor") or "vercel-sandbox"),
        "network_policy": str(evidence.get("network_policy") or "deny-all"),
        "exit_code": evidence.get("exit_code"),
        "duration_ms": int(evidence.get("duration_ms") or 0),
        "stdout_excerpt": str(evidence.get("stdout_excerpt") or ""),
        "stderr_excerpt": str(evidence.get("stderr_excerpt") or ""),
        "timed_out": bool(evidence.get("timed_out")),
        "redacted": bool(evidence.get("redacted")),
    }


@router.get("/{run_id}", response_model=EngineeringRunRead)
def get_run(run_id: str, svc: EngineeringRunService = Depends(service)):
    return present(invoke(lambda: svc.get(run_id)), svc)


@router.get("/{run_id}/worker-health", response_model=EngineeringWorkerHealthRead)
def worker_health(run_id: str, svc: EngineeringRunService = Depends(service)):
    invoke(lambda: svc.get(run_id))
    snapshot = invoke(lambda: worker_recovery_service(svc).health(run_id=run_id))
    return {
        "execution_id": snapshot.execution_id,
        "project_id": snapshot.project_id,
        "run_id": snapshot.run_id,
        "state": snapshot.state.value,
        "lease_status": snapshot.lease_status,
        "lease_generation": snapshot.lease_generation,
        "current_step": snapshot.current_step,
        "source_lineage_ref": snapshot.source_lineage_ref,
        "last_known_good_lineage_ref": snapshot.last_known_good_lineage_ref,
        "checkpoint_revision": snapshot.checkpoint_revision,
        "last_meaningful_progress_at": snapshot.last_meaningful_progress_at,
        "retry_count": snapshot.retry_count,
        "no_progress_count": snapshot.no_progress_count,
        "oscillation_count": snapshot.oscillation_count,
        "stall_classification": snapshot.stall_classification.value if snapshot.stall_classification else None,
        "blocker_code": snapshot.blocker_code,
        "dependencies": list(snapshot.dependencies),
        "next_recovery_action": snapshot.next_recovery_action.value if snapshot.next_recovery_action else None,
        "human_required": snapshot.human_required,
    }


@router.get("/conversation/{conversation_id}/latest", response_model=EngineeringRunRead | None)
def latest_run(conversation_id: str, svc: EngineeringRunService = Depends(service)):
    run = invoke(lambda: svc.latest_for_conversation(conversation_id))
    return present(run, svc) if run else None


@router.post("/{run_id}/advance", response_model=EngineeringOperationRead)
def advance(run_id: str, payload: EngineeringAdvance, svc: EngineeringRunService = Depends(service)):
    values = payload.model_dump(exclude={"stage"})
    return result_payload(
        invoke(lambda: svc.complete_stage(run_id=run_id, stage=WorkflowStage(payload.stage), **values)),
        svc,
    )


@router.post("/{run_id}/autonomous", response_model=EngineeringAutonomyRead)
def autonomous(
    run_id: str,
    payload: EngineeringOperation,
    svc: EngineeringRunService = Depends(service),
    allocator: DurableLineageAllocator | None = Depends(runtime_lineage_allocator),
):
    legacy_executor = VercelSandboxExecutor()
    if allocator is None:
        runtime = AutonomyCoordinator(svc, legacy_executor)
    else:
        run = invoke(lambda: svc.get(run_id))
        if not run.project_id:
            raise HTTPException(422, "Wave 2 autonomous execution requires a Project-bound run")
        source_delivery = invoke(
            lambda: production_source_delivery(
                svc.runs.session,
                owner_subject=svc.owner_subject or "",
                allocator=allocator,
                project_id=run.project_id or "",
            )
        )
        runtime = EngineeringRuntimeComposition(
            svc,
            allocator,
            legacy_executor,
            source_delivery=source_delivery,
        )
    result = invoke(
        lambda: runtime.run(
            run_id=run_id,
            **payload.model_dump(),
        )
    )
    return {
        "run": present(result.run, svc),
        "stop_reason": result.stop_reason.value,
        "steps": [
            {
                "stage": item.stage,
                "outcome": item.outcome,
                "attempt_id": item.attempt_id,
                "replayed": item.replayed,
                "tool_id": item.tool_id,
            }
            for item in result.steps
        ],
    }


def control(run_id: str, payload: EngineeringOperation, method: str, svc: EngineeringRunService):
    return result_payload(
        invoke(lambda: getattr(svc, method)(run_id=run_id, **payload.model_dump())),
        svc,
    )


@router.post("/{run_id}/pause", response_model=EngineeringOperationRead)
def pause(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "pause", svc)


@router.post("/{run_id}/resume", response_model=EngineeringOperationRead)
def resume(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "resume", svc)


@router.post("/{run_id}/cancel", response_model=EngineeringOperationRead)
def cancel(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "cancel", svc)
