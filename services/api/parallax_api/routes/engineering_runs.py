from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..code.domain import WorkflowStage
from ..code.service import EngineeringRunNotFound, EngineeringRunService, RunOperationResult
from ..code.state_machine import RevisionConflict, RunTransitionError
from ..db import get_session
from ..models import EngineeringRun
from ..repositories.conversations import ConversationRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from ..schemas import EngineeringAdvance, EngineeringOperation, EngineeringOperationRead, EngineeringRunCreate, EngineeringRunRead

router = APIRouter(prefix="/v1/engineering-runs", tags=["engineering-runs"])


def service(session: Session = Depends(get_session)) -> EngineeringRunService:
    return EngineeringRunService(EngineeringRunRepository(session), ConversationRepository(session))


def present(run: EngineeringRun) -> dict:
    return {
        "id": run.id, "conversation_id": run.conversation_id, "spec_id": run.spec_id,
        "state": run.state, "resume_stage": run.resume_stage, "revision": run.revision,
        "workspace_ref": run.workspace_ref, "last_failure_code": run.last_failure_code,
        "created_at": run.created_at, "updated_at": run.updated_at, "completed_at": run.completed_at,
        "attempts": [{
            "id": item.id, "stage": item.stage, "attempt_number": item.attempt_number,
            "status": item.status, "failure_code": item.failure_code,
            "evidence": json.loads(item.evidence_json), "started_at": item.started_at,
            "completed_at": item.completed_at,
        } for item in run.attempts],
    }


def result_payload(result: RunOperationResult) -> dict:
    return {"run": present(result.run), "attempt_id": result.attempt_id, "replayed": result.replayed}


def invoke(call):
    try:
        return call()
    except EngineeringRunNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except RevisionConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except (RunTransitionError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("", response_model=EngineeringRunRead)
def create_run(payload: EngineeringRunCreate, svc: EngineeringRunService = Depends(service)):
    return present(invoke(lambda: svc.create_run(**payload.model_dump())))


@router.get("/{run_id}", response_model=EngineeringRunRead)
def get_run(run_id: str, svc: EngineeringRunService = Depends(service)):
    return present(invoke(lambda: svc.get(run_id)))


@router.get("/conversation/{conversation_id}/latest", response_model=EngineeringRunRead | None)
def latest_run(conversation_id: str, session: Session = Depends(get_session)):
    run = session.scalar(select(EngineeringRun).where(EngineeringRun.conversation_id == conversation_id).order_by(EngineeringRun.updated_at.desc()))
    return present(EngineeringRunRepository(session).get(run.id)) if run else None


@router.post("/{run_id}/advance", response_model=EngineeringOperationRead)
def advance(run_id: str, payload: EngineeringAdvance, svc: EngineeringRunService = Depends(service)):
    values = payload.model_dump(exclude={"stage"})
    return result_payload(invoke(lambda: svc.complete_stage(run_id=run_id, stage=WorkflowStage(payload.stage), **values)))


def control(run_id: str, payload: EngineeringOperation, method: str, svc: EngineeringRunService):
    return result_payload(invoke(lambda: getattr(svc, method)(run_id=run_id, **payload.model_dump())))


@router.post("/{run_id}/pause", response_model=EngineeringOperationRead)
def pause(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "pause", svc)


@router.post("/{run_id}/resume", response_model=EngineeringOperationRead)
def resume(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "resume", svc)


@router.post("/{run_id}/cancel", response_model=EngineeringOperationRead)
def cancel(run_id: str, payload: EngineeringOperation, svc: EngineeringRunService = Depends(service)):
    return control(run_id, payload, "cancel", svc)
