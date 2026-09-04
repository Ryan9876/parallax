from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import sessionmaker

from parallax_api.code.work_spec_binding import work_specification_digest
from parallax_api.db import Base, make_engine
from parallax_api.intelligence.behavioral_verification_plan import (
    BehavioralActionProposal,
    BehavioralCriterionProposal,
    BehavioralPlanProposal,
    BehavioralVerificationMode,
    BehavioralVerificationPlanCoordinator,
    BehavioralVerificationPlanGeneration,
    behavioral_plan_digest,
    compile_behavioral_plan,
    validate_persisted_behavioral_plan,
)
from parallax_api.models import WorkSpecification
from parallax_api.repositories.behavioral_verification_plans import BehavioralVerificationPlanRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.services.behavioral_verification_plans import BehavioralVerificationPlanService
from parallax_api.services.conversations import ConversationService
from parallax_api.services.work_specifications import WorkSpecificationService
from parallax_api.intelligence.work_specification import WorkSpecificationDraft


def _specification(*, status: str = "APPROVED") -> WorkSpecification:
    return WorkSpecification(
        id="11111111-1111-4111-8111-111111111111",
        conversation_id="22222222-2222-4222-8222-222222222222",
        revision=3,
        status=status,
        title="Decision ledger",
        objective="Provide a responsive decision ledger with a filter and durable visible entries.",
        constraints_json=json.dumps(["Preserve keyboard accessibility."]),
        acceptance_criteria_json=json.dumps(
            [
                "The page shows the decision ledger heading and current entries.",
                "The operator can filter visible entries without losing the full list.",
            ]
        ),
        risks_json="[]",
        open_questions_json="[]",
        confidence=0.95,
        program_version="work-spec-test",
        model_id="test-model",
    )


def _proposal() -> BehavioralPlanProposal:
    return BehavioralPlanProposal(
        criteria=[
            BehavioralCriterionProposal(
                acceptance_id="AC-01",
                mode=BehavioralVerificationMode.BROWSER,
                viewport_ids=["mobile-390", "desktop-1440"],
                actions=[
                    BehavioralActionProposal(kind="NAVIGATE", path="/"),
                    BehavioralActionProposal(
                        kind="ASSERT_VISIBLE",
                        target_kind="ROLE",
                        target_value="heading:Decision ledger",
                    ),
                    BehavioralActionProposal(kind="SCREENSHOT", checkpoint="ledger"),
                ],
            ),
            BehavioralCriterionProposal(
                acceptance_id="AC-02",
                mode=BehavioralVerificationMode.HUMAN_ONLY,
            ),
        ]
    )


def test_behavioral_plan_compiles_only_existing_typed_browser_contract() -> None:
    specification = _specification()
    payload = compile_behavioral_plan(specification, _proposal(), plan_revision=2)

    assert payload["schema_version"] == 1
    first, second = payload["criteria"]
    assert first["acceptance_id"] == "AC-01"
    assert first["mode"] == "BROWSER"
    assert first["workflow"]["workflow_id"] == "behavioral-11111111-r2-ac-01"
    assert first["workflow"]["viewport_ids"] == ["mobile-390", "desktop-1440"]
    assert [item["kind"] for item in first["workflow"]["actions"]] == [
        "NAVIGATE",
        "ASSERT_VISIBLE",
        "SCREENSHOT",
    ]
    assert second["acceptance_id"] == "AC-02"
    assert second["mode"] == "HUMAN_ONLY"
    assert second["workflow"] is None

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = behavioral_plan_digest(payload)
    read_back = validate_persisted_behavioral_plan(
        specification,
        plan_revision=2,
        plan_json=encoded,
        plan_digest=digest,
    )
    assert read_back == payload


def test_behavioral_plan_rejects_missing_reordered_or_invented_acceptance_identity() -> None:
    specification = _specification()
    proposal = _proposal().model_copy(deep=True)
    proposal.criteria[0].acceptance_id = "AC-02"
    proposal.criteria[1].acceptance_id = "AC-01"
    with pytest.raises(ValueError, match="exactly cover"):
        compile_behavioral_plan(specification, proposal, plan_revision=1)

    invented = _proposal().model_copy(deep=True)
    invented.criteria[1].acceptance_id = "AC-03"
    with pytest.raises(ValueError, match="exactly cover"):
        compile_behavioral_plan(specification, invented, plan_revision=1)


def test_behavioral_plan_browser_vocabulary_rejects_arbitrary_url_and_human_workflow() -> None:
    with pytest.raises(ValidationError):
        BehavioralActionProposal(kind="NAVIGATE", path="https://example.com/steal")

    with pytest.raises(ValidationError):
        BehavioralCriterionProposal(
            acceptance_id="AC-01",
            mode="HUMAN_ONLY",
            viewport_ids=["desktop-1440"],
            actions=[BehavioralActionProposal(kind="SCREENSHOT", checkpoint="bad")],
        )


def test_behavioral_plan_digest_is_canonical() -> None:
    payload = compile_behavioral_plan(_specification(), _proposal(), plan_revision=1)
    reordered = {
        "criteria": payload["criteria"],
        "schema_version": payload["schema_version"],
    }
    assert behavioral_plan_digest(payload) == behavioral_plan_digest(reordered)


def test_coordinator_input_is_only_work_spec_acceptance_map_and_fixed_browser_vocabulary(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeProgram:
        version = "fake"

        def __init__(self, model: str):
            assert model == "test-model"

        def run(self, *, specification_json: str, acceptance_json: str, vocabulary_json: str):
            captured.update(
                specification_json=specification_json,
                acceptance_json=acceptance_json,
                vocabulary_json=vocabulary_json,
            )
            return _proposal()

    class FakeRouter:
        async def route(self, attempt, validate):
            proposal = await attempt("test-model")
            assert validate(proposal) is True
            return SimpleNamespace(value=proposal, model="test-model")

    import parallax_api.intelligence.behavioral_verification_plan as module

    monkeypatch.setattr(module, "DspyBehavioralVerificationPlanProgram", FakeProgram)
    generation = asyncio.run(
        BehavioralVerificationPlanCoordinator(router=FakeRouter()).draft(_specification())
    )
    assert generation.proposal == _proposal()
    assert set(captured) == {"specification_json", "acceptance_json", "vocabulary_json"}
    specification_payload = json.loads(captured["specification_json"])
    assert set(specification_payload) == {
        "id",
        "revision",
        "title",
        "objective",
        "constraints",
        "acceptance_criteria",
        "risks",
        "open_questions",
    }
    assert json.loads(captured["acceptance_json"]) == [
        {"id": "AC-01", "text": "The page shows the decision ledger heading and current entries."},
        {"id": "AC-02", "text": "The operator can filter visible entries without losing the full list."},
    ]
    vocabulary = json.loads(captured["vocabulary_json"])
    assert "BROWSER" in vocabulary["modes"]
    assert "HUMAN_ONLY" in vocabulary["modes"]
    assert "desktop-1440" in vocabulary["viewport_ids"]


def _draft() -> WorkSpecificationDraft:
    return WorkSpecificationDraft(
        title="Behavioral plan fixture",
        objective="Provide a visible ledger with an operator-controlled filter for existing entries.",
        constraints=["Preserve keyboard accessibility."],
        acceptance_criteria=[
            "The page shows the decision ledger heading and current entries.",
            "The operator can filter visible entries without losing the full list.",
        ],
        risks=[],
        open_questions=[],
        confidence=0.9,
        program_version="test",
    )


def test_behavioral_plan_persistence_revisions_and_approval_are_separate_from_work_spec(tmp_path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'behavioral-plan.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        conversations = ConversationRepository(session)
        conversation_service = ConversationService(conversations, active_spec_id="P2-V0.23.47")
        conversation = conversation_service.create("reason")
        conversation_service.append_message(conversation.id, "user", "Build a decision ledger.")
        specs = WorkSpecificationService(WorkSpecificationRepository(session), conversations)
        specification = specs.create_draft(
            conversation_id=conversation.id,
            draft=_draft(),
            model_id="test",
        )
        specification = specs.approve(specification.id)
        original_spec_digest = work_specification_digest(specification)
        original_spec_updated_at = specification.updated_at

        plans = BehavioralVerificationPlanRepository(session)
        service = BehavioralVerificationPlanService(
            plans,
            WorkSpecificationRepository(session),
            conversations,
            owner_subject="owner",
        )
        generation = BehavioralVerificationPlanGeneration(
            proposal=_proposal(),
            model="test",
            program_version="behavioral-test",
        )
        first = service.create_draft(specification.id, generation)
        assert first.revision == 1
        assert first.status == "DRAFT"
        first_digest = first.plan_digest

        second = service.create_draft(specification.id, generation)
        assert second.revision == 2
        assert second.status == "DRAFT"
        assert plans.get(first.id).status == "SUPERSEDED"
        assert second.plan_digest != first_digest

        approved_second = service.approve(second.id)
        assert approved_second.status == "APPROVED"
        approved_at = approved_second.approved_at
        assert approved_at is not None
        assert service.approve(second.id).approved_at == approved_at

        third = service.create_draft(specification.id, generation)
        assert third.revision == 3
        assert plans.get(second.id).status == "APPROVED"
        service.approve(third.id)
        assert plans.get(second.id).status == "SUPERSEDED"
        assert plans.get(third.id).status == "APPROVED"

        unchanged = specs.repository.get(specification.id)
        assert unchanged.status == "APPROVED"
        assert work_specification_digest(unchanged) == original_spec_digest
        assert unchanged.updated_at == original_spec_updated_at


def test_behavioral_plan_requires_approved_work_specification(tmp_path) -> None:
    engine = make_engine(f"sqlite:///{tmp_path / 'behavioral-plan-draft.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        conversations = ConversationRepository(session)
        conversation_service = ConversationService(conversations, active_spec_id="P2-V0.23.47")
        conversation = conversation_service.create("reason")
        conversation_service.append_message(conversation.id, "user", "Build a decision ledger.")
        specs = WorkSpecificationService(WorkSpecificationRepository(session), conversations)
        specification = specs.create_draft(
            conversation_id=conversation.id,
            draft=_draft(),
            model_id="test",
        )
        service = BehavioralVerificationPlanService(
            BehavioralVerificationPlanRepository(session),
            WorkSpecificationRepository(session),
            conversations,
            owner_subject="owner",
        )
        with pytest.raises(Exception) as blocked:
            service.create_draft(
                specification.id,
                BehavioralVerificationPlanGeneration(
                    proposal=_proposal(),
                    model="test",
                    program_version="test",
                ),
            )
        assert getattr(blocked.value, "status_code", None) == 422


def test_behavioral_plan_migration_is_additive_guarded_and_private() -> None:
    root = Path(__file__).resolve().parents[3]
    sql = (root / "services/api/migrations/20260903_0013_behavioral_verification_plans.sql").read_text(
        encoding="utf-8"
    ).lower()
    assert "create table if not exists behavioral_verification_plans" in sql
    assert "references work_specifications(id) on delete cascade" in sql
    assert "unique (work_specification_id, revision)" in sql
    assert "check (revision > 0)" in sql
    assert "status in ('draft', 'approved', 'superseded')" in sql
    assert "octet_length(plan_json) <= 32000" in sql
    assert "enable row level security" in sql
    assert "revoke all on table behavioral_verification_plans from anon, authenticated" in sql
