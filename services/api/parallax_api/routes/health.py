from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..db import get_session

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "parallax-api", "version": "0.1.0"}


@router.get("/ready")
def ready(session: Session = Depends(get_session)):
    try:
        value = session.execute(text("select 1")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    if value != 1:
        raise HTTPException(status_code=503, detail="database readiness check failed")
    return {"status": "ready", "database": "ok", "service": "parallax-api"}
