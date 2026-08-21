from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from parallax_api.code.service import EngineeringRunService
from parallax_api.code.state_machine import SpecBindingError
from parallax_api.db import Base, make_engine
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository


def session_factory(tmp_path, name="activation.db"):
    engine = make_engine(f"sqlite:///{tmp_path / name}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def service_for(session):
    conversations = ConversationRepository(session)
    runs = EngineeringRunRepository(session)
    return EngineeringRunService(runs, conversations), conversations, runs


def test_code_activation_creates_one_run_and_advances_only_specify(tmp_path):
    Session = session_factory(tmp_path)
    with Session() as session:
        service, conversations, runs = service_for(session)
        conversation = conversations.create("code", spec_id="P2-V0.7.0")

        activated = service.ensure_run(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
        )

        assert activated.state == "PLAN"
        assert activated.revision == 1
        assert len(activated.attempts) == 1
        assert activated.attempts[0].stage == "SPECIFY"
        assert activated.attempts[0].status == "PASSED"
        assert runs.passing_stage_names(activated.id) == {"SPECIFY"}

        repeated = service.ensure_run(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
        )

        assert repeated.id == activated.id
        assert repeated.revision == 1
        assert len(repeated.attempts) == 1
        assert repeated.state == "PLAN"


def test_code_activation_restores_same_run_after_new_session(tmp_path):
    Session = session_factory(tmp_path, "restore.db")
    with Session() as session:
        service, conversations, _ = service_for(session)
        conversation = conversations.create("code", spec_id="P2-V0.7.0")
        first = service.ensure_run(conversation_id=conversation.id, spec_id=conversation.spec_id)
        conversation_id = conversation.id
        run_id = first.id

    with Session() as session:
        service, _, _ = service_for(session)
        restored = service.ensure_run(conversation_id=conversation_id, spec_id="P2-V0.7.0")
        assert restored.id == run_id
        assert restored.state == "PLAN"
        assert restored.revision == 1
        assert len(restored.attempts) == 1


def test_code_activation_rejects_reason_mode_mismatch_and_amendment(tmp_path):
    Session = session_factory(tmp_path, "protection.db")
    with Session() as session:
        service, conversations, _ = service_for(session)

        reason = conversations.create("reason", spec_id="P2-V0.7.0")
        with pytest.raises(SpecBindingError):
            service.ensure_run(conversation_id=reason.id, spec_id=reason.spec_id)

        code = conversations.create("code", spec_id="P2-V0.7.0")
        with pytest.raises(SpecBindingError):
            service.ensure_run(conversation_id=code.id, spec_id="P2-V9.9.9")

        conversations.set_status(code, "SPEC_AMENDMENT")
        with pytest.raises(SpecBindingError):
            service.ensure_run(conversation_id=code.id, spec_id=code.spec_id)


def test_code_activation_cannot_rebind_existing_workspace(tmp_path):
    Session = session_factory(tmp_path, "workspace.db")
    with Session() as session:
        service, conversations, _ = service_for(session)
        conversation = conversations.create("code", spec_id="P2-V0.7.0")
        activated = service.ensure_run(
            conversation_id=conversation.id,
            spec_id=conversation.spec_id,
            workspace_ref="workspace:one",
        )
        assert activated.workspace_ref == "workspace:one"

        with pytest.raises(SpecBindingError):
            service.ensure_run(
                conversation_id=conversation.id,
                spec_id=conversation.spec_id,
                workspace_ref="workspace:two",
            )
