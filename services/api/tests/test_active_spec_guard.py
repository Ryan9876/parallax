from __future__ import annotations

import pytest

from parallax_api.config import _active_spec_id


def test_production_stale_active_spec_uses_release_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_ACTIVE_SPEC_ID", "P2-V0.5.0")

    assert _active_spec_id() == "P2-V0.13.0"


def test_production_newer_active_spec_is_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_ACTIVE_SPEC_ID", "P2-V0.14.0")

    assert _active_spec_id() == "P2-V0.14.0"


def test_test_environment_can_select_older_spec(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "test")
    monkeypatch.setenv("PARALLAX_ACTIVE_SPEC_ID", "P2-V0.5.0")

    assert _active_spec_id() == "P2-V0.5.0"


def test_invalid_active_spec_still_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PARALLAX_ENV", "production")
    monkeypatch.setenv("PARALLAX_ACTIVE_SPEC_ID", "v13")

    with pytest.raises(ValueError, match="P2-Vx.y.z"):
        _active_spec_id()
