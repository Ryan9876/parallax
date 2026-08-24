from __future__ import annotations

from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from parallax_api.main import create_app
from parallax_api.repositories.run_events import PersistentRunEventSink
from parallax_api.routes import engineering_runs


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import production_run_event_schema_guard as schema_guard


def test_run_event_sink_is_disabled_without_explicit_activation(monkeypatch) -> None:
    monkeypatch.delenv("PARALLAX_RUN_EVENTS_ENABLED", raising=False)
    session = Session(bind=create_engine("sqlite:///:memory:", future=True))
    try:
        assert engineering_runs._run_event_sink(session) is None
        monkeypatch.setenv("PARALLAX_RUN_EVENTS_ENABLED", "true")
        assert engineering_runs._run_event_sink(session) is None
    finally:
        session.close()


def test_run_event_sink_activates_only_for_exact_server_flag(monkeypatch) -> None:
    monkeypatch.setenv("PARALLAX_RUN_EVENTS_ENABLED", "1")
    session = Session(bind=create_engine("sqlite:///:memory:", future=True))
    try:
        assert isinstance(engineering_runs._run_event_sink(session), PersistentRunEventSink)
    finally:
        session.close()


def test_live_observability_routes_require_exact_server_activation(monkeypatch) -> None:
    event_path = "/v1/engineering-runs/{run_id}/events"

    monkeypatch.delenv("PARALLAX_RUN_EVENTS_ENABLED", raising=False)
    disabled_paths = {route.path for route in create_app(create_schema=False).routes}
    assert event_path not in disabled_paths

    monkeypatch.setenv("PARALLAX_RUN_EVENTS_ENABLED", "true")
    truthy_but_not_authorized_paths = {route.path for route in create_app(create_schema=False).routes}
    assert event_path not in truthy_but_not_authorized_paths

    monkeypatch.setenv("PARALLAX_RUN_EVENTS_ENABLED", "1")
    enabled_paths = {route.path for route in create_app(create_schema=False).routes}
    assert event_path in enabled_paths


def test_production_schema_guard_does_not_touch_database_while_wave4_disabled(monkeypatch, capsys) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.delenv("PARALLAX_RUN_EVENTS_ENABLED", raising=False)

    def unexpected_engine(*args, **kwargs):
        raise AssertionError("disabled Wave 4 guard must not require database schema authority")

    monkeypatch.setattr(schema_guard, "make_engine", unexpected_engine)
    schema_guard.main()

    output = capsys.readouterr().out
    assert "PASS" in output
    assert "explicitly disabled" in output
    assert "migration remains unapplied/not activated" in output


def test_production_schema_guard_blocks_activation_without_table(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("PARALLAX_RUN_EVENTS_ENABLED", "1")
    engine = create_engine(f"sqlite:///{tmp_path / 'run-events-disabled.db'}", future=True)
    monkeypatch.setattr(schema_guard, "make_engine", lambda **kwargs: engine)

    with pytest.raises(SystemExit) as exc:
        schema_guard.main()

    assert exc.value.code == 1
    assert "BLOCK" in capsys.readouterr().err
