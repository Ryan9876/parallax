import asyncio

from parallax_api.intelligence.router import MODEL_ORDER, ModelRouter


def test_router_falls_back_luna_terra_sol():
    seen = []

    async def attempt(model: str):
        seen.append(model)
        if model != MODEL_ORDER[-1]:
            raise RuntimeError("provider down")
        return "valid result"

    result = asyncio.run(ModelRouter[str]().route(attempt, lambda value: value.startswith("valid")))
    assert seen == list(MODEL_ORDER)
    assert result.model == "openai/gpt-5.6-sol"
    assert [record.status for record in result.attempts] == ["provider_failed", "provider_failed", "ok"]
