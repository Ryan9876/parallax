import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..code.production_delivery import ProductionDeliveryConfigurationError
from ..code.runtime_credentials import (
    runtime_vercel_oidc_token,
    verify_registered_runtime_github_credentials,
)
from ..db import get_session
from ..tools.providers import ProviderClientError

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "parallax-api", "version": "0.1.0"}


@router.get("/ready")
def ready(request: Request, session: Session = Depends(get_session)):
    try:
        value = session.execute(text("select 1")).scalar_one()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc
    if value != 1:
        raise HTTPException(status_code=503, detail="database readiness check failed")

    result: dict[str, object] = {
        "status": "ready",
        "database": "ok",
        "service": "parallax-api",
    }
    if (os.getenv("VERCEL_ENV") or "unknown") != "production":
        return result

    try:
        oidc_token = runtime_vercel_oidc_token(request.headers, environment="production")
        if oidc_token is None:
            raise ProductionDeliveryConfigurationError("production runtime Vercel OIDC credential is unavailable")
        verified_targets = verify_registered_runtime_github_credentials(oidc_token)
    except (ProductionDeliveryConfigurationError, ProviderClientError) as exc:
        raise HTTPException(status_code=503, detail="provider credential unavailable") from exc

    result["providers"] = "ok"
    result["provider_targets"] = verified_targets
    return result
