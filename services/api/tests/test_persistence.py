from sqlalchemy.orm import sessionmaker

from parallax_api.db import Base, make_engine
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.services.conversations import ConversationService


def test_conversation_persists_across_service_instances(tmp_path):
    db = tmp_path / "parallax.db"
    engine = make_engine(f"sqlite:///{db}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        service = ConversationService(ConversationRepository(session))
        conversation = service.create("reason")
        service.append_message(conversation.id, "user", "Persistent hello")
        conversation_id = conversation.id

    with Session() as session:
        service = ConversationService(ConversationRepository(session))
        loaded = service.get(conversation_id)
        assert loaded.id == conversation_id
        assert [message.content for message in loaded.messages] == ["Persistent hello"]


def test_follow_up_stays_active_unless_scope_change(tmp_path):
    db = tmp_path / "followup.db"
    engine = make_engine(f"sqlite:///{db}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        service = ConversationService(ConversationRepository(session))
        conversation = service.create("reason")
        assert conversation.status == "ACTIVE"
        service.append_follow_up(conversation.id, "Why option B?")
        assert service.get(conversation.id).status == "ACTIVE"
        service.append_follow_up(conversation.id, "Change the objective entirely", material_scope_change=True)
        assert service.get(conversation.id).status == "SPEC_AMENDMENT"
