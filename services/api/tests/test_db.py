from sqlalchemy.pool import NullPool

from parallax_api.db import make_engine, normalize_database_url


def test_normalize_managed_postgres_urls():
    expected = "postgresql+psycopg://user:pass@example.com:6543/postgres"
    assert normalize_database_url("postgres://user:pass@example.com:6543/postgres") == expected
    assert normalize_database_url("postgresql://user:pass@example.com:6543/postgres") == expected


def test_preview_postgres_uses_psycopg_and_provider_side_pooling():
    engine = make_engine(
        "postgresql://user:pass@example.com:6543/postgres",
        environment="preview",
    )
    try:
        assert engine.url.drivername == "postgresql+psycopg"
        assert engine.url.port == 6543
        assert isinstance(engine.pool, NullPool)
    finally:
        engine.dispose()
