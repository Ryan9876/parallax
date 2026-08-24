from __future__ import annotations

import asyncio
import json
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..code.live_observability import (
    EngineeringObservabilityService,
    MAX_CURSOR,
    MAX_EVENT_PAGE,
    MAX_TREE_PAGE,
    ProtectedObservationNotFound,
    ProtectedObservationUnavailable,
    ProtectedObservationValidation,
    resolve_event_cursor,
)
from ..code.runtime_composition import DurableLineageAllocator
from ..code.service import EngineeringRunNotFound, EngineeringRunService
from ..code.workspace_lineage import SourceLineageStore
from ..observability_schemas import (
    EngineeringAttemptEvidenceRead,
    RunEventPageRead,
    RunEventRead,
    SourceDiffRead,
    SourceFileRead,
    SourceTreeRead,
)
from ..repositories.run_events import RunEventRepository
from .engineering_runs import runtime_lineage_allocator, service


router = APIRouter(prefix="/v1/engineering-runs", tags=["engineering-observability"])

_SSE_BATCH = 100
_SSE_POLL_SECONDS = 0.5
_SSE_KEEPALIVE_SECONDS = 10.0
_SSE_MAX_SECONDS = 30.0


def _event_observer(svc: EngineeringRunService) -> EngineeringObservabilityService:
    return EngineeringObservabilityService(
        svc,
        RunEventRepository(svc.runs.session),
    )


def _source_observer(
    svc: EngineeringRunService,
    allocator: DurableLineageAllocator | None,
) -> EngineeringObservabilityService:
    lineage_store = getattr(allocator, "lineage_store", None) if allocator is not None else None
    if not isinstance(lineage_store, SourceLineageStore):
        raise ProtectedObservationUnavailable("durable source-lineage reads are unavailable")
    return EngineeringObservabilityService(
        svc,
        RunEventRepository(svc.runs.session),
        lineage_store=lineage_store,
    )


def _invoke(call):
    try:
        return call()
    except (EngineeringRunNotFound, ProtectedObservationNotFound) as exc:
        raise HTTPException(404, "protected observability reference not found") from exc
    except ProtectedObservationValidation as exc:
        raise HTTPException(422, str(exc)) from exc
    except ProtectedObservationUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


def _sse_payload(event: dict[str, object]) -> str:
    public = RunEventRead.model_validate(event).model_dump(mode="json")
    sequence = public["sequence"]
    data = json.dumps(public, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return f"id: {sequence}\nevent: run-event\ndata: {data}\n\n"


@router.get("/{run_id}/events", response_model=RunEventPageRead)
def replay_events(
    run_id: str,
    after_sequence: int = Query(default=0, ge=0, le=MAX_CURSOR),
    limit: int = Query(default=100, ge=1, le=MAX_EVENT_PAGE),
    svc: EngineeringRunService = Depends(service),
):
    observer = _event_observer(svc)
    return _invoke(
        lambda: observer.event_page(
            run_id=run_id,
            after_sequence=after_sequence,
            limit=limit,
        )
    )


@router.get("/{run_id}/events/stream")
async def stream_events(
    run_id: str,
    request: Request,
    after_sequence: int = Query(default=0, ge=0, le=MAX_CURSOR),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    svc: EngineeringRunService = Depends(service),
):
    observer = _event_observer(svc)
    cursor = _invoke(
        lambda: resolve_event_cursor(
            after_sequence=after_sequence,
            last_event_id=last_event_id,
        )
    )
    # Resolve owner scope and durable repository availability before returning a
    # streaming response so malformed/foreign references fail as normal HTTP.
    initial = _invoke(
        lambda: observer.event_page(
            run_id=run_id,
            after_sequence=cursor,
            limit=_SSE_BATCH,
        )
    )

    async def body():
        nonlocal cursor, initial
        started = time.monotonic()
        keepalive_at = started
        page: dict[str, object] | None = initial
        while time.monotonic() - started < _SSE_MAX_SECONDS:
            if await request.is_disconnected():
                return
            if page is None:
                try:
                    page = observer.event_page(
                        run_id=run_id,
                        after_sequence=cursor,
                        limit=_SSE_BATCH,
                    )
                except Exception:
                    # Transport failure closes the observer channel only. It
                    # must never be converted into an engineering event/result.
                    return
            events = page.get("events")
            if not isinstance(events, list):
                return
            for event in events:
                if not isinstance(event, dict):
                    return
                sequence = event.get("sequence")
                if not isinstance(sequence, int) or sequence <= cursor:
                    continue
                yield _sse_payload(event)
                cursor = sequence
                keepalive_at = time.monotonic()
                if await request.is_disconnected():
                    return
            has_more = page.get("has_more") is True
            page = None
            if has_more:
                continue
            now = time.monotonic()
            if now - keepalive_at >= _SSE_KEEPALIVE_SECONDS:
                yield ": keepalive\n\n"
                keepalive_at = now
            await asyncio.sleep(_SSE_POLL_SECONDS)

    return StreamingResponse(
        body(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{run_id}/source/{lineage_id}/tree", response_model=SourceTreeRead)
def source_tree(
    run_id: str,
    lineage_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=MAX_TREE_PAGE),
    svc: EngineeringRunService = Depends(service),
    allocator: DurableLineageAllocator | None = Depends(runtime_lineage_allocator),
):
    return _invoke(
        lambda: _source_observer(svc, allocator).source_tree(
            run_id=run_id,
            lineage_id=lineage_id,
            offset=offset,
            limit=limit,
        )
    )


@router.get("/{run_id}/source/{lineage_id}/file", response_model=SourceFileRead)
def source_file(
    run_id: str,
    lineage_id: str,
    path: str = Query(min_length=1, max_length=512),
    svc: EngineeringRunService = Depends(service),
    allocator: DurableLineageAllocator | None = Depends(runtime_lineage_allocator),
):
    return _invoke(
        lambda: _source_observer(svc, allocator).source_file(
            run_id=run_id,
            lineage_id=lineage_id,
            path=path,
        )
    )


@router.get("/{run_id}/source-diff", response_model=SourceDiffRead)
def source_diff(
    run_id: str,
    from_lineage: str = Query(min_length=68, max_length=68),
    to_lineage: str = Query(min_length=68, max_length=68),
    svc: EngineeringRunService = Depends(service),
    allocator: DurableLineageAllocator | None = Depends(runtime_lineage_allocator),
):
    return _invoke(
        lambda: _source_observer(svc, allocator).source_diff(
            run_id=run_id,
            from_lineage=from_lineage,
            to_lineage=to_lineage,
        )
    )


@router.get("/{run_id}/attempts/{attempt_id}/evidence", response_model=EngineeringAttemptEvidenceRead)
def attempt_evidence(
    run_id: str,
    attempt_id: str,
    svc: EngineeringRunService = Depends(service),
):
    return _invoke(
        lambda: _event_observer(svc).attempt_evidence(
            run_id=run_id,
            attempt_id=attempt_id,
        )
    )


__all__ = ["router"]
