from __future__ import annotations

import os

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .auth import require_access
from .code.production_delivery import ProductionDeliveryConfigurationError
from .code.runtime_credentials import runtime_vercel_oidc_token
from .db import Base, engine
from . import models  # noqa: F401
from .intelligence.dspy_programs import request_model_gateway_credential
from .projects.routes import router as projects_router
from .routes.access import router as access_router
from .routes.agent_run_projection import router as agent_run_projection_router
from .routes.agentic_observability import router as agentic_observability_router
from .routes.conversations import router as conversations_router
from .routes.health import router as health_router
from .routes.engineering_runs import router as engineering_runs_router
from .routes.observability import router as observability_router
from .routes.session import router as session_router
from .routes.work_specifications import router as work_specifications_router
from .session import SESSION_HEADER_NAME


_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"
_RUNTIME_OIDC_HEADER = "x-vercel-oidc-token"


def create_app(*, create_schema: bool | None = None) -> FastAPI:
    if create_schema is None:
        create_schema = settings.create_schema
    if create_schema:
        Base.metadata.create_all(engine)

    app = FastAPI(title="Parallax 2.0 API", version="0.10.0")

    @app.middleware("http")
    async def bind_request_model_gateway_credential(request: Request, call_next):
        """Bind validated Vercel request identity to all downstream model construction.

        The middleware is intentionally non-authoritative for requests that do
        not construct a model: an absent/malformed request token binds no model
        credential and ordinary health/session/read paths remain available.
        Production `build_lm` itself fails closed if a model is actually needed
        without an admitted request credential. This keeps one request-scoped
        transport contract across conversation, Work Specification and protected
        implementation-generation paths without persisting or logging the token.
        """

        credential = None
        if request.headers.get(_RUNTIME_OIDC_HEADER) is not None:
            try:
                credential = runtime_vercel_oidc_token(request.headers)
            except ProductionDeliveryConfigurationError:
                credential = None
        with request_model_gateway_credential(credential):
            return await call_next(request)

    @app.get("/")
    def root():
        return {
            "service": "Parallax 2.0 API",
            "status": "online",
            "docs": "/docs",
            "health": "/health",
            "version": "0.10.0",
        }

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", SESSION_HEADER_NAME, "Last-Event-ID"],
    )
    app.include_router(health_router)
    app.include_router(session_router)
    app.include_router(access_router)
    protected = [Depends(require_access)]
    app.include_router(conversations_router, dependencies=protected)
    app.include_router(engineering_runs_router, dependencies=protected)
    app.include_router(agent_run_projection_router, dependencies=protected)
    app.include_router(agentic_observability_router, dependencies=protected)
    if os.getenv(_RUN_EVENTS_ENABLE_ENV) == "1":
        app.include_router(observability_router, dependencies=protected)
    app.include_router(work_specifications_router, dependencies=protected)
    app.include_router(projects_router, dependencies=protected)
    return app


app = create_app()
