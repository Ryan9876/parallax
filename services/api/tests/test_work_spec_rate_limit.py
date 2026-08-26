from types import SimpleNamespace

from fastapi.testclient import TestClient

from parallax_api.intelligence.router import RoutingFailureKind
from parallax_api.intelligence.work_specification import WorkSpecificationGenerationFailure
from parallax_api.main import create_app
from parallax_api.routes import work_specifications as work_spec_routes


class _NoCreateService:
    def __init__(self):
        self.created = False

    def conversation(self, conversation_id):
        assert conversation_id == "conversation-test"
        return SimpleNamespace(
            id=conversation_id,
            mode="code",
            project_id=None,
            messages=[SimpleNamespace(role="user", content="Create an about page")],
        )

    def create_draft(self, **_kwargs):
        self.created = True
        raise AssertionError("provider failure must not persist a Work Specification")


class _FailureCoordinator:
    def __init__(self, kind: RoutingFailureKind):
        self.kind = kind

    async def draft(self, _messages, *, project_context=None):
        assert project_context is None
        raise WorkSpecificationGenerationFailure("sanitized generation failure", kind=self.kind)


def _client(kind: RoutingFailureKind):
    service = _NoCreateService()
    app = create_app(create_schema=False)
    app.dependency_overrides[work_spec_routes.service] = lambda: service
    app.dependency_overrides[work_spec_routes.coordinator] = lambda: _FailureCoordinator(kind)
    return TestClient(app), service


def test_all_rate_limit_exhaustion_returns_retryable_429_and_persists_no_spec():
    client, service = _client(RoutingFailureKind.RATE_LIMITED)

    response = client.post("/v1/conversations/conversation-test/work-specifications/draft")

    assert response.status_code == 429
    assert response.json() == {
        "detail": "Model capacity is temporarily unavailable. Retry Capture Spec later; your objective is preserved."
    }
    assert "Retry-After" not in response.headers
    assert service.created is False


def test_validation_exhaustion_remains_distinct_from_rate_limiting():
    client, service = _client(RoutingFailureKind.VALIDATION_EXHAUSTED)

    response = client.post("/v1/conversations/conversation-test/work-specifications/draft")

    assert response.status_code == 503
    assert "could not validate a Work Specification draft" in response.json()["detail"]
    assert service.created is False


def test_mixed_provider_exhaustion_is_generic_and_does_not_claim_rate_limiting():
    client, service = _client(RoutingFailureKind.PROVIDER_EXHAUSTED)

    response = client.post("/v1/conversations/conversation-test/work-specifications/draft")

    assert response.status_code == 503
    assert "model provider is temporarily unavailable" in response.json()["detail"]
    assert "rate" not in response.json()["detail"].lower()
    assert service.created is False
