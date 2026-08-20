from types import SimpleNamespace

from fastapi.testclient import TestClient

from parallax_api.intelligence.coordinator import ResponseCoordinationFailure
from parallax_api.intelligence.scope import ScopeDecision
from parallax_api.main import create_app
from parallax_api.routes import conversations as conversation_routes


class FakeTrace:
    def __init__(self, final_state: str, protected_scope_decision: str | None = None):
        self.final_state = final_state
        self.protected_scope_decision = protected_scope_decision

    def as_public_dict(self):
        return {
            "response_id": "response-test",
            "conversation_id": "conversation-test",
            "spec_id": "P2-V0.3.0",
            "protected_scope_decision": self.protected_scope_decision,
            "protected_verification_passed": self.final_state != "ERROR",
            "final_state": self.final_state,
        }


class FakeConversationService:
    def __init__(self):
        self.conversation = SimpleNamespace(
            id="conversation-test",
            spec_id="P2-V0.3.0",
            status="ACTIVE",
            mode="reason",
            messages=[SimpleNamespace(role="user", content="Original approved objective")],
        )

    def get(self, conversation_id: str):
        assert conversation_id == self.conversation.id
        return self.conversation

    def append_follow_up(self, conversation_id: str, content: str, **kwargs):
        del kwargs
        message = SimpleNamespace(id="user-turn", role="user", content=content)
        self.conversation.messages.append(message)
        return message

    def set_status(self, conversation_id: str, status: str):
        assert conversation_id == self.conversation.id
        self.conversation.status = status
        return self.conversation

    def append_message(self, conversation_id: str, role: str, content: str):
        assert conversation_id == self.conversation.id
        message = SimpleNamespace(id="assistant-handoff", role=role, content=content)
        self.conversation.messages.append(message)
        return message


class AmendmentCoordinator:
    async def respond(self, **kwargs):
        assert kwargs["spec_id"] == "P2-V0.3.0"
        assert "ACTIVE_SPEC_ID: P2-V0.3.0" in kwargs["context"].text
        return SimpleNamespace(
            answer=None,
            confidence=0.96,
            scope=SimpleNamespace(decision=ScopeDecision.SPEC_AMENDMENT),
            material_uncertainties=(),
            assumptions=(),
            trace=FakeTrace("SPEC_AMENDMENT", "SPEC_AMENDMENT"),
        )


class ContinueCoordinator:
    async def respond(self, **kwargs):
        return SimpleNamespace(
            answer="Continue under the active objective using the preserved prior conversation context.",
            confidence=0.93,
            scope=SimpleNamespace(decision=ScopeDecision.CONTINUE),
            material_uncertainties=("Provider-backed optimization is not part of this test.",),
            assumptions=(),
            trace=FakeTrace("COMPLETE", "CONTINUE"),
        )


class ReasonFailureCoordinator:
    async def respond(self, **kwargs):
        assert kwargs["spec_id"] == "P2-V0.3.0"
        raise ResponseCoordinationFailure(
            error_code="PROTECTED_REASON_FAILURE",
            public_message="Parallax could not produce a response that passed protected verification.",
            trace=FakeTrace("ERROR", "CONTINUE"),
        )


class ScopeFailureCoordinator:
    async def respond(self, **kwargs):
        assert kwargs["spec_id"] == "P2-V0.3.0"
        raise ResponseCoordinationFailure(
            error_code="PROTECTED_SCOPE_FAILURE",
            public_message="Parallax could not establish a protected scope decision.",
            trace=FakeTrace("ERROR", None),
        )


def client_with(service: FakeConversationService, monkeypatch, coordinator_type):
    app = create_app(create_schema=False)
    app.dependency_overrides[conversation_routes.service] = lambda: service
    monkeypatch.setattr(conversation_routes, "ResponseCoordinator", coordinator_type)
    return TestClient(app)


def test_response_api_emits_amendment_handoff_without_substantive_chunks(monkeypatch):
    service = FakeConversationService()
    client = client_with(service, monkeypatch, AmendmentCoordinator)

    response = client.post(
        "/v1/conversations/conversation-test/responses",
        json={"content": "Replace the approved objective entirely."},
    )

    assert response.status_code == 200
    assert "event: state\ndata: {\"phase\": \"THINKING\"}" in response.text
    assert "event: state\ndata: {\"phase\": \"SPEC_AMENDMENT\"}" in response.text
    assert "event: amendment" in response.text
    assert "event: chunk" not in response.text
    assert service.conversation.status == "SPEC_AMENDMENT"
    assert service.conversation.messages[-1].role == "assistant"
    assert "approved specification amendment is required" in service.conversation.messages[-1].content


def test_response_api_streams_continue_answer_and_reason_metadata(monkeypatch):
    service = FakeConversationService()
    client = client_with(service, monkeypatch, ContinueCoordinator)

    response = client.post(
        "/v1/conversations/conversation-test/responses",
        json={"content": "Why is the previous option safer?"},
    )

    assert response.status_code == 200
    assert "event: chunk" in response.text
    assert "event: complete" in response.text
    assert '"scope_decision": "CONTINUE"' in response.text
    assert '"material_uncertainties"' in response.text
    assert service.conversation.status == "ACTIVE"
    assert service.conversation.messages[-1].role == "assistant"


def test_response_api_returns_recoverable_reason_failure_with_trace(monkeypatch):
    service = FakeConversationService()
    client = client_with(service, monkeypatch, ReasonFailureCoordinator)

    response = client.post(
        "/v1/conversations/conversation-test/responses",
        json={"content": "Continue the current objective."},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert '"error": "PROTECTED_REASON_FAILURE"' in response.text
    assert '"recoverable": true' in response.text
    assert '"protected_scope_decision": "CONTINUE"' in response.text
    assert '"protected_verification_passed": false' in response.text
    assert '"final_state": "ERROR"' in response.text
    assert "event: chunk" not in response.text
    assert service.conversation.status == "ACTIVE"
    assert service.conversation.messages[-1].role == "user"


def test_response_api_returns_recoverable_scope_failure_without_fabricated_decision(monkeypatch):
    service = FakeConversationService()
    client = client_with(service, monkeypatch, ScopeFailureCoordinator)

    response = client.post(
        "/v1/conversations/conversation-test/responses",
        json={"content": "Continue the current objective."},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert '"error": "PROTECTED_SCOPE_FAILURE"' in response.text
    assert '"recoverable": true' in response.text
    assert '"protected_scope_decision": null' in response.text
    assert '"final_state": "ERROR"' in response.text
    assert "event: chunk" not in response.text
    assert service.conversation.status == "ACTIVE"
    assert service.conversation.messages[-1].role == "user"
