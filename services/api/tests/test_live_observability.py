from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from parallax_api.auth import AccessPrincipal, access_principal
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore, InMemoryLineageMetadataStore
from parallax_api.code.live_observability import resolve_event_cursor
from parallax_api.code.workspace_allocator import ProjectWorkspaceAllocator
from parallax_api.code.workspace_lineage import ProjectRunIdentity, SourceLineageStore, SourcePackage
from parallax_api.db import Base, get_session, make_engine
from parallax_api.intelligence.work_specification import WorkSpecificationDraft
from parallax_api.models import EngineeringAttempt
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.run_events import RunEventRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.routes.conversations import router as conversations_router
from parallax_api.routes.engineering_runs import router as engineering_runs_router, runtime_lineage_allocator
from parallax_api.routes.observability import router as observability_router
from parallax_api.routes.work_specifications import router as work_specifications_router


class StaticProvider:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return SourcePackage("repository", "github:owner/repo@observability", self.files)


def api_context(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path / 'observability.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    owner = {"subject": "owner-a"}
    store = SourceLineageStore(InMemoryImmutableObjectStore(), InMemoryLineageMetadataStore())
    allocator = ProjectWorkspaceAllocator(tmp_path / "lineage", lineage_store=store)

    app = FastAPI()
    app.include_router(conversations_router)
    app.include_router(work_specifications_router)
    app.include_router(engineering_runs_router)
    app.include_router(observability_router)

    def session_override():
        with Session() as session:
            yield session

    def principal_override():
        return AccessPrincipal(subject=owner["subject"], role="owner", auth_method="test")

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[access_principal] = principal_override
    app.dependency_overrides[runtime_lineage_allocator] = lambda: allocator
    return TestClient(app), Session, owner, store, allocator


def create_project(Session, owner: str):
    with Session() as session:
        return ProjectRepository(session).create(
            owner_subject=owner,
            slug="observability",
            name="Observability",
            description=None,
            repository_ref="github:owner/repo",
        )


def approve_spec(Session, conversation_id: str):
    with Session() as session:
        repository = WorkSpecificationRepository(session)
        draft = repository.create_draft(
            conversation_id=conversation_id,
            draft=WorkSpecificationDraft(
                title="Live observability",
                objective="Observe one protected engineering run.",
                constraints=["Read only."],
                acceptance_criteria=[
                    "Durable events remain owner scoped.",
                    "Observer transport never mutates authoritative engineering state.",
                ],
                risks=["Observers must not mutate the run."],
                open_questions=[],
                confidence=0.99,
                program_version="observability-test",
            ),
            model_id="test-model",
        )
        return repository.approve(draft)


def activate_run(client: TestClient, Session):
    project = create_project(Session, "owner-a")
    conversation = client.post(
        "/v1/conversations",
        json={"mode": "code", "project_id": project.id},
    ).json()
    specification = approve_spec(Session, conversation["id"])
    response = client.post(
        "/v1/engineering-runs/activate",
        json={
            "conversation_id": conversation["id"],
            "work_specification_id": specification.id,
        },
    )
    assert response.status_code == 200
    return project, response.json()


def test_json_replay_is_ordered_resumable_and_owner_scoped(tmp_path):
    client, Session, owner, _, _ = api_context(tmp_path)
    project, run = activate_run(client, Session)

    first = client.get(f"/v1/engineering-runs/{run['id']}/events?after_sequence=0&limit=1")
    assert first.status_code == 200
    payload = first.json()
    assert len(payload["events"]) == 1
    assert payload["events"][0]["project_id"] == project.id
    assert payload["events"][0]["run_id"] == run["id"]
    assert payload["events"][0]["sequence"] == 1
    assert payload["next_after_sequence"] == 1
    assert payload["has_more"] is True

    recreated = client.get(f"/v1/engineering-runs/{run['id']}/events?after_sequence=1&limit=100")
    assert recreated.status_code == 200
    sequences = [item["sequence"] for item in recreated.json()["events"]]
    assert sequences == sorted(sequences)
    assert all(sequence > 1 for sequence in sequences)

    owner["subject"] = "owner-b"
    hidden = client.get(f"/v1/engineering-runs/{run['id']}/events")
    assert hidden.status_code == 404


def test_last_event_id_precedence_and_invalid_header_fail_closed():
    assert resolve_event_cursor(after_sequence=3, last_event_id="7") == 7
    assert resolve_event_cursor(after_sequence=3, last_event_id=None) == 3
    for invalid in ("0", "-1", "1.5", "event-7", "", "99999999999999999999"):
        try:
            resolve_event_cursor(after_sequence=3, last_event_id=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid Last-Event-ID accepted: {invalid!r}")


def test_sse_replays_durable_event_and_disconnect_does_not_mutate_run(tmp_path):
    client, Session, _, _, _ = api_context(tmp_path)
    _, run = activate_run(client, Session)
    before = client.get(f"/v1/engineering-runs/{run['id']}").json()

    with client.stream("GET", f"/v1/engineering-runs/{run['id']}/events/stream") as response:
        assert response.status_code == 200
        seen_id = None
        for line in response.iter_lines():
            if line.startswith("id:"):
                seen_id = int(line.split(":", 1)[1].strip())
            if seen_id is not None and line == "":
                break
        assert seen_id == 1

    after = client.get(f"/v1/engineering-runs/{run['id']}").json()
    assert after["state"] == before["state"]
    assert after["revision"] == before["revision"]
    assert len(after["attempts"]) == len(before["attempts"])

    invalid = client.get(
        f"/v1/engineering-runs/{run['id']}/events/stream?after_sequence=0",
        headers={"Last-Event-ID": "bad"},
    )
    assert invalid.status_code == 422


def test_exact_lineage_tree_file_diff_and_secret_path_boundaries(tmp_path):
    client, Session, _, store, allocator = api_context(tmp_path)
    project, run = activate_run(client, Session)
    identity = ProjectRunIdentity(project.id, run["id"])
    initial = store.initialize(
        identity,
        StaticProvider(
            {
                "app.py": b"print('before')\n",
                "binary.dat": b"\xff\x00\x01",
                "large.txt": b"x" * (256 * 1024 + 1),
            }
        ),
    )

    tree = client.get(f"/v1/engineering-runs/{run['id']}/source/{initial.lineage_id}/tree?limit=2")
    assert tree.status_code == 200
    assert tree.json()["project_id"] == project.id
    assert tree.json()["file_count"] == 3
    assert len(tree.json()["files"]) == 2
    assert tree.json()["has_more"] is True

    text = client.get(
        f"/v1/engineering-runs/{run['id']}/source/{initial.lineage_id}/file",
        params={"path": "app.py"},
    )
    assert text.status_code == 200
    assert text.json()["availability"] == "TEXT"
    assert text.json()["text"] == "print('before')\n"

    binary = client.get(
        f"/v1/engineering-runs/{run['id']}/source/{initial.lineage_id}/file",
        params={"path": "binary.dat"},
    )
    assert binary.status_code == 200
    assert binary.json()["availability"] == "BINARY"
    assert binary.json()["text"] is None

    large = client.get(
        f"/v1/engineering-runs/{run['id']}/source/{initial.lineage_id}/file",
        params={"path": "large.txt"},
    )
    assert large.status_code == 200
    assert large.json()["availability"] == "TOO_LARGE"
    assert large.json()["text"] is None

    assert client.get(
        f"/v1/engineering-runs/{run['id']}/source/{initial.lineage_id}/file",
        params={"path": "../app.py"},
    ).status_code == 404
    assert client.get(
        f"/v1/engineering-runs/{run['id']}/source/{initial.lineage_id}/file",
        params={"path": ".env"},
    ).status_code == 404

    workspace = allocator.reconstruct(identity, initial.lineage_id)
    try:
        (workspace.path / "app.py").write_text("print('after')\n", encoding="utf-8")
        (workspace.path / "new.py").write_text("VALUE = 1\n", encoding="utf-8")
        accepted = allocator.accept_implementation(
            workspace,
            expected_parent_lineage_id=initial.lineage_id,
        )
    finally:
        allocator.cleanup(workspace)

    diff = client.get(
        f"/v1/engineering-runs/{run['id']}/source-diff",
        params={"from_lineage": initial.lineage_id, "to_lineage": accepted.lineage_id},
    )
    assert diff.status_code == 200
    body = diff.json()
    assert body["changed_count"] == 2
    assert body["truncated"] is False
    paths = {item["path"]: item for item in body["files"]}
    assert paths["app.py"]["change_type"] == "MODIFIED"
    assert "-print('before')" in paths["app.py"]["diff_text"]
    assert "+print('after')" in paths["app.py"]["diff_text"]
    assert paths["new.py"]["change_type"] == "ADDED"


def test_foreign_lineage_is_hidden_after_owner_scoped_run_resolution(tmp_path):
    client, Session, _, store, _ = api_context(tmp_path)
    project, run = activate_run(client, Session)
    own_identity = ProjectRunIdentity(project.id, run["id"])
    store.initialize(own_identity, StaticProvider({"app.py": b"own\n"}))

    foreign_identity = ProjectRunIdentity(str(uuid4()), str(uuid4()))
    foreign = store.initialize(foreign_identity, StaticProvider({"foreign.py": b"foreign\n"}))
    response = client.get(f"/v1/engineering-runs/{run['id']}/source/{foreign.lineage_id}/tree")
    assert response.status_code == 404
    assert response.json()["detail"] == "protected observability reference not found"


def test_attempt_evidence_is_allowlisted_bounded_and_secret_safe(tmp_path):
    client, Session, _, _, _ = api_context(tmp_path)
    project, run = activate_run(client, Session)
    attempt_id = str(uuid4())
    with Session() as session:
        session.add(
            EngineeringAttempt(
                id=attempt_id,
                run_id=run["id"],
                stage="BUILD",
                attempt_number=1,
                operation_key="build:test",
                status="PASSED",
                program_id="protected-build",
                model_id="test-model",
                tool_id="build",
                evidence_json=json.dumps(
                    {
                        "source_lineage_ref": "src:" + "1" * 64,
                        "invocation_digest": "2" * 64,
                        "exit_code": 0,
                        "duration_ms": 120,
                        "stdout_excerpt": "access_token=supersecretvalue123456",
                        "stdout_digest": "3" * 64,
                        "stderr_excerpt": "",
                        "stderr_digest": "4" * 64,
                        "timed_out": False,
                        "redacted": False,
                        "protected_success": True,
                        "network_policy": "deny-all",
                        "authorization": "Bearer should-never-surface",
                        "raw_provider_payload": {"secret": "never"},
                        "environment": {"TOKEN": "never"},
                    }
                ),
                failure_code=None,
            )
        )
        session.commit()

    response = client.get(f"/v1/engineering-runs/{run['id']}/attempts/{attempt_id}/evidence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == project.id
    assert payload["evidence"]["stdout_excerpt"] == "[REDACTED]"
    assert payload["evidence"]["redacted"] is True
    serialized = json.dumps(payload).casefold()
    assert "supersecretvalue" not in serialized
    assert "authorization" not in serialized
    assert "raw_provider_payload" not in serialized
    assert "environment" not in serialized

    with Session() as session:
        attempt = session.get(EngineeringAttempt, attempt_id)
        attempt.evidence_json = "{not-json"
        session.commit()
    unavailable = client.get(f"/v1/engineering-runs/{run['id']}/attempts/{attempt_id}/evidence")
    assert unavailable.status_code == 200
    assert unavailable.json()["availability"] == "UNAVAILABLE"
    assert unavailable.json()["evidence"] == {}


def test_observability_routes_are_read_only_by_surface_contract():
    source = Path(__file__).resolve().parents[1] / "parallax_api" / "routes" / "observability.py"
    text = source.read_text(encoding="utf-8")
    assert "@router.post" not in text
    assert "@router.patch" not in text
    assert "@router.delete" not in text
    assert "pause(" not in text
    assert "cancel(" not in text
    assert "complete_stage(" not in text
    assert "execute(" not in text
