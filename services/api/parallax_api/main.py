from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .auth import require_access
from .db import Base, engine
from . import models  # noqa: F401
from .routes.conversations import router as conversations_router
from .routes.health import router as health_router
from .routes.engineering_runs import router as engineering_runs_router
from .routes.session import router as session_router
from .session import SESSION_HEADER_NAME


def create_app(*, create_schema: bool | None = None) -> FastAPI:
    if create_schema is None:
        create_schema = settings.create_schema
    if create_schema:
        Base.metadata.create_all(engine)

    app = FastAPI(title="Parallax 2.0 API", version="0.1.0")

    @app.get("/")
    def root():
        return {
            "service": "Parallax 2.0 API",
            "status": "online",
            "docs": "/docs",
            "health": "/health",
            "version": "0.1.0",
        }

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", SESSION_HEADER_NAME],
    )
    app.include_router(health_router)
    app.include_router(session_router)
    protected = [Depends(require_access)]
    app.include_router(conversations_router, dependencies=protected)
    app.include_router(engineering_runs_router, dependencies=protected)
    return app


app = create_app()
