from __future__ import annotations

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .auth import require_access
from .db import Base, engine
from . import models  # noqa: F401
from .projects.routes import router as projects_router
from .routes.access import router as access_router
from .routes.conversations import router as conversations_router
from .routes.health import router as health_router
from .routes.engineering_runs import router as engineering_runs_router
from .routes.observability import router as observability_router
from .routes.session import router as session_router
from .routes.work_specifications import router as work_specifications_router
from .session import SESSION_HEADER_NAME


_RUN_EVENTS_ENABLE_ENV = "PARALLAX_RUN_EVENTS_ENABLED"


def create_app(*, create_schema: bool | None = None) -> FastAPI:
    if create_schema is None:
        create_schema = settings.create_schema
    if create_schema:
        Base.metadata.create_all(engine)

    app = FastAPI(title="Parallax 2.0 API", version="0.10.0")

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
    if os.getenv(_RUN_EVENTS_ENABLE_ENV) == "1":
        app.include_router(observability_router, dependencies=protected)
    app.include_router(work_specifications_router, dependencies=protected)
    app.include_router(projects_router, dependencies=protected)
    return app


app = create_app()
