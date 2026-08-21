from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from parallax_api.db import Base, make_engine
from parallax_api.intelligence.work_specification import (
    WorkSpecificationCoordinator,
    WorkSpecificationDraft,
    WorkSpecificationGeneration,
)
from parallax_api.main import create_app
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.routes import work_specifications as work_spec_routes
from parallax_api.services.conversations import ConversationService
from parallax_api.services.work_specifications import WorkSpecificationService


def draft(title: str = "Durable outcome") -> WorkSpecificationDraft:
    return WorkSpecificationDraft(
        title=title,
        objective="Deliver the requested outcome with durable evidence and explicit approval.",
        constraints=["Preserve the existing conversation experience."],
        acceptance_criteria=[
            "The specification persists across a new database session.",
            "Approval is explicit and only one revision remains approved.",
        ],
        risks=["A newer draft could accidentally overwrite approved work."],
        open_questions=[],
        confidence=0.92,
        program_version="work-spec-test",
    )


def test_work_specification_revisions_preserve_approved_work_until_new_approval(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'work-spec.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        conversations = ConversationRepository(session)
        conversation_service = ConversationService(conversations, active_spec_id="P2-V0.7.0")
        conversation = conversation_service.create("reason")
        conversation_service.append_message(conversation.id, "user", "Build the durable specification layer.")
        specs = WorkSpecificationService(WorkSpecificationRepository(session), conversations)

        first = specs.create_draft(conversation_id=conversation.id, draft=draft("First draft"), model_id="luna")
        assert first.revision == 1
        assert first.status == "DRAFT"

        approved_first = specs.approve(first.id)
        assert approved_first.status == "APPROVED"
        assert approved_first.approved_at is not None

        second = specs.create_draft(conversation_id=conversation.id, draft=draft("Second draft"), model_id="terra")
        assert second.revision == 2
        assert second.status == "DRAFT"
        assert specs.repository.get(first.id).status == "APPROVED"

        approved_second = specs.approve(second.id)
        assert approved_second.status == "APPROVED"
        assert specs.repository.get(first.id).status == "SUPERSEDED"

    with Session() as session:
        specs = WorkSpecificationRepository(session)
        latest = specs.latest(conversation.id)
        assert latest is not None
        assert latest.revision == 2
        assert latest.status == "APPROVED"
        assert "persists across" in latest.acceptance_criteria_json


def test_conversation_context_requires_user_turn_and_prefers_latest_user_objective():
    coordinator = WorkSpecificationCoordinator()
    messages = [
        SimpleNamespace(role="user", content="Initial objective"),
        SimpleNamespace(role="assistant", content="Initial response"),
        SimpleNamespace(role="user", content="Later corrected objective"),
    ]
    objective, context = coordinator.conversation_context(messages)
    assert objective == "Later corrected objective"
    assert "USER: Initial objective" in context
    assert "USER: Later corrected objective" in context


def test_work_specification_routes_use_explicit_draft_then_approval():
    now = "2026-08-21T08:00:00+00:00"
    stored = SimpleNamespace(
        id="spec-1",
        conversation_id="conversation-test",
        revision=1,
        status="DRAFT",
        title="Captured objective",
        objective="Implement a durable work specification that the operator explicitly approves.",
        constraints_json='["Keep conversation primary"]',
        acceptance_criteria_json='["Draft persists", "Approval is explicit"]',
        risks_json='[]',
        open_questions_json='[]',
        confidence=0.9,
        program_version="work-spec-test",
        model_id="test-model",
        created_at=now,
        updated_at=now,
        approved_at=None,
    )

    class FakeService:
        def conversation(self, conversation_id):
            assert conversation_id == "conversation-test"
            return SimpleNamespace(messages=[SimpleNamespace(role="user", content="Capture this objective")])

        def latest(self, conversation_id):
            assert conversation_id == "conversation-test"
            return stored

        def create_draft(self, *, conversation_id, draft, model_id):
            assert conversation_id == "conversation-test"
            assert draft.title == "Captured objective"
            assert model_id == "test-model"
            return stored

        def approve(self, specification_id):
            assert specification_id == "spec-1"
            stored.status = "APPROVED"
            stored.approved_at = now
            return stored

    class FakeCoordinator:
        async def draft(self, messages):
            assert messages[0].role == "user"
            return WorkSpecificationGeneration(
                draft=WorkSpecificationDraft(
                    title="Captured objective",
                    objective="Implement a durable work specification that the operator explicitly approves.",
                    constraints=["Keep conversation primary"],
                    acceptance_criteria=["Draft persists", "Approval is explicit"],
                    risks=[],
                    open_questions=[],
                    confidence=0.9,
                    program_version="work-spec-test",
                ),
                model="test-model",
            )

    app = create_app(create_schema=False)
    app.dependency_overrides[work_spec_routes.service] = lambda: FakeService()
    app.dependency_overrides[work_spec_routes.coordinator] = lambda: FakeCoordinator()
    client = TestClient(app)

    response = client.post("/v1/conversations/conversation-test/work-specifications/draft")
    assert response.status_code == 200
    assert response.json()["status"] == "DRAFT"
    assert response.json()["acceptance_criteria"] == ["Draft persists", "Approval is explicit"]

    approved = client.post("/v1/work-specifications/spec-1/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
