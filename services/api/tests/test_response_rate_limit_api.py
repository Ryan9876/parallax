from types import SimpleNamespace

from fastapi.testclient import TestClient

from parallax_api.intelligence.coordinator import ResponseCoordinationFailure
from parallax_api.main import create_app
from parallax_api.routes import conversations as conversation_routes


class FakeTrace:
    def __init__(self, protected_scope_decision: str | None):
        self.protected_scope_decision = protected_scope_decision

    def as_public_dict(self):
        return {
            "response_id": "response-rate-limit",
            "conversation_id": "conversation-rate-limit",
            "spec_id": "P2-V0.3.0",
            "protected_scope_decision": self.protected_scope_decision,
            "protected_verification_passed": False,
            "final_state": "ERROR",
            "scope_attempts": [],
            "reason_attempts": [],
        }


class FakeConversationService:
    def __init__(self):
        self.conversation = SimpleNamespace(
            id="conversation-rate-limit",
            spec_id="P2-V0.3.0",
            status="ACTIVE",
            mode="code",
            project_id=None,
            messages=[SimpleNamespace(role="user", content="Original objective")],
        )

    def get(self, conversation_id: str):
        assert conversation_id == self.conversation.id
        return self.conversation

    def append_follow_up(self, conversation_id: str, content: str, **_kwargs):
        assert conversation_id == self.conversation.id
        message = SimpleNamespace(id="saved-user-turn", role="user", content=content)
        self.conversation.messages.append(message)
        return message

    def project_for_conversation(self, conversation):
        assert conversation is self.conversation
        return None


class CapacityFailureCoordinator:
    async def respond(self, **_kwargs):
        raise ResponseCoordinationFailure(
            error_code="MODEL_CAPACITY_RATE_LIMITED",
            public_message="Model capacity is temporarily unavailable.",
            trace=FakeTrace(None),
        )


class ProviderFailureCoordinator:
    async def respond(self, **_kwargs):
        raise ResponseCoordinationFailure(
            error_code="MODEL_PROVIDER_UNAVAILABLE",
            public_message="Parallax model provider is temporarily unavailable.",
            trace=FakeTrace(None),
        )


def client_with(service: FakeConversationService, monkeypatch, coordinator_type):
    app = create_app(create_schema=False)
    app.dependency_overrides[conversation_routes.service] = lambda: service
    monkeypatch.setattr(conversation_routes, "ResponseCoordinator", coordinator_type)
    return TestClient(app)


def test_capacity_exhaustion_emits_truthful_recoverable_sse_and_keeps_saved_turn(monkeypatch):
    service = FakeConversationService()
    client = client_with(service, monkeypatch, CapacityFailureCoordinator)

    response = client.post(
        "/v1/conversations/conversation-rate-limit/responses",
        json={"content": "Create an about page"},
    )

    assert response.status_code == 200
    assert '"error": "MODEL_CAPACITY_RATE_LIMITED"' in response.text
    assert '"recoverable": true' in response.text
    assert "Model capacity is temporarily unavailable." in response.text
    assert "Your message is saved" in response.text
    assert "instead of sending it again" in response.text
    assert "protected scope" not in response.text.lower()
    assert "retry or refine" not in response.text.lower()
    assert "event: chunk" not in response.text
    assert service.conversation.status == "ACTIVE"
    assert [item.role for item in service.conversation.messages] == ["user", "user"]
    assert service.conversation.messages[-1].content == "Create an about page"


def test_generic_provider_exhaustion_does_not_claim_rate_limiting(monkeypatch):
    service = FakeConversationService()
    client = client_with(service, monkeypatch, ProviderFailureCoordinator)

    response = client.post(
        "/v1/conversations/conversation-rate-limit/responses",
        json={"content": "Continue this objective"},
    )

    assert response.status_code == 200
    assert '"error": "MODEL_PROVIDER_UNAVAILABLE"' in response.text
    assert "model provider is temporarily unavailable" in response.text.lower()
    assert "your message is saved" in response.text.lower()
    assert "rate limit" not in response.text.lower()
    assert "quota" not in response.text.lower()
    assert service.conversation.status == "ACTIVE"
    assert service.conversation.messages[-1].role == "user"
