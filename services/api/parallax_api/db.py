from __future__ import annotations

from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Use psycopg 3 for generic Postgres URLs supplied by managed providers."""

    if url.startswith("postgres://"):
        return f"postgresql+psycopg://{url[len('postgres://') :]}"
    if url.startswith("postgresql://"):
        return f"postgresql+psycopg://{url[len('postgresql://') :]}"
    return url


def make_engine(database_url: str | None = None):
    url = normalize_database_url(database_url or settings.database_url)
    if url.startswith("sqlite"):
        return create_engine(url, future=True, connect_args={"check_same_thread": False})

    connect_args: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {"pool_pre_ping": True}

    if url.startswith("postgresql+psycopg://"):
        # Supabase/Supavisor transaction pooling is the intended serverless
        # preview path. Transaction mode does not support prepared statements.
        connect_args["prepare_threshold"] = None
        if settings.environment in {"preview", "production"}:
            # Let the provider-side pool own connection reuse across ephemeral
            # Vercel function instances instead of multiplying local pools.
            engine_kwargs["poolclass"] = NullPool

    return create_engine(url, future=True, connect_args=connect_args, **engine_kwargs)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
