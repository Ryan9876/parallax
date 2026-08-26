from __future__ import annotations

import asyncio
import logging

import pytest

from parallax_api.intelligence.router import ModelRouter, RoutingFailure


class ProviderFailure(RuntimeError):
    pass


def test_model_router_logs_only_bounded_provider_failure_class(caplog):
    async def attempt(model: str):
        raise ProviderFailure(f"sensitive provider detail for {model}")

    router = ModelRouter(models=("provider/model-a",))
    with caplog.at_level(logging.WARNING, logger="parallax_api.intelligence.router"):
        with pytest.raises(RoutingFailure) as caught:
            asyncio.run(router.route(attempt, lambda _value: True))

    assert caught.value.attempts[0].status == "provider_failed"
    assert caught.value.attempts[0].error == "ProviderFailure"
    assert "provider/model-a" in caplog.text
    assert "ProviderFailure" in caplog.text
    assert "sensitive provider detail" not in caplog.text


def test_model_router_logs_validation_exhaustion_without_result_content(caplog):
    async def attempt(_model: str):
        return {"candidate": "sensitive generated output"}

    router = ModelRouter(models=("provider/model-a",))
    with caplog.at_level(logging.WARNING, logger="parallax_api.intelligence.router"):
        with pytest.raises(RoutingFailure) as caught:
            asyncio.run(router.route(attempt, lambda _value: False))

    assert caught.value.attempts[0].status == "validation_failed"
    assert caught.value.attempts[0].error is None
    assert "validation_failed" in caplog.text
    assert "provider/model-a" in caplog.text
    assert "sensitive generated output" not in caplog.text
