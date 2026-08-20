from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from . import models  # noqa: F401
from .routes.conversations import router as conversations_router
from .routes.health import router as health_router


def create_app(*, create_schema: bool = True) -> FastAPI:
    if create_schema:
        Base.metadata.create_all(engine)

    app = FastAPI(title="Parallax 2.0 API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.include_router(health_router)
    app.include_router(conversations_router)
    return app


app = create_app()
