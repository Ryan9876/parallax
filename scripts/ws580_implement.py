from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


root = Path(__file__).resolve().parents[1]
source_path = root / "services/api/parallax_api/code/source_delivery_composition.py"
greenfield_path = root / "services/api/parallax_api/code/greenfield_composition.py"
test_path = root / "services/api/tests/test_source_delivery_composition.py"
greenfield_test_path = root / "services/api/tests/test_greenfield_commit_bearing_delivery.py"

source = source_path.read_text(encoding="utf-8")
source = replace_once(
    source,
    "from sqlalchemy import select\n",
    "from sqlalchemy import func, select\n",
    label="sqlalchemy func import",
)
source = replace_once(
    source,
    "from .domain import AttemptStatus, WorkflowStage\n",
    "from ..tools.providers.common import require_app_branch, require_canonical_uuid, require_source_lineage_id\nfrom .domain import AttemptStatus, WorkflowStage\n",
    label="provider common imports",
)
source = replace_once(
    source,
    "class SourceDeliveryCompositionError(RuntimeError):\n",
    '''def canonical_publication_branch_name(identity: ProjectRunIdentity, lineage_id: str) -> str:\n    \"\"\"Return the server-owned exact-lineage publication branch identity.\"\"\"\n\n    if not isinstance(identity, ProjectRunIdentity):\n        raise VerifiedDeliveryError(\"publication branch requires canonical Project/run identity\")\n    try:\n        project_id = require_canonical_uuid(identity.project_id, field=\"project_id\")\n        run_id = require_canonical_uuid(identity.run_id, field=\"run_id\")\n        protected_lineage_id = require_source_lineage_id(lineage_id)\n        return require_app_branch(\n            f\"parallax/{project_id[:8]}-{run_id[:8]}-{protected_lineage_id[4:]}\"\n        )\n    except (TypeError, ValueError) as exc:\n        raise VerifiedDeliveryError(\"publication branch identity is invalid\") from exc\n\n\nclass SourceDeliveryCompositionError(RuntimeError):\n''',
    label="publication branch helper",
)
old_persist = '''        conflicting = self.repository.session.scalar(\n            select(EngineeringAttempt).where(\n                EngineeringAttempt.run_id == run.id,\n                EngineeringAttempt.stage == _DELIVERY_RECORD_STAGE,\n            )\n        )\n        if conflicting is not None:\n            raise VerifiedDeliveryError(\"Engineering Run already has a different durable delivery record\")\n\n        attempt = EngineeringAttempt(\n            run_id=run.id,\n            stage=_DELIVERY_RECORD_STAGE,\n            attempt_number=1,\n            operation_key=self.operation_key(lineage_id),\n            status=_DELIVERY_RECORD_STATUS,\n            program_id=_DELIVERY_RECORD_PROGRAM,\n            tool_id=_DELIVERY_RECORD_TOOL,\n            evidence_json=encoded,\n            completed_at=utcnow(),\n        )\n        try:\n            self.repository.session.add(attempt)\n            self.repository.session.commit()\n        except IntegrityError as exc:\n            self.repository.session.rollback()\n            replay = self.load(run_id=run.id, lineage_id=lineage_id)\n            if replay is None or self._canonical(replay) != encoded:\n                raise VerifiedDeliveryError(\"concurrent durable delivery record conflicted\") from exc\n            return replay, True\n        return payload, False\n'''
new_persist = '''        operation_key = self.operation_key(lineage_id)\n        last_integrity_error: IntegrityError | None = None\n        for insertion_index in range(2):\n            current_attempt_number = self.repository.session.scalar(\n                select(func.max(EngineeringAttempt.attempt_number)).where(\n                    EngineeringAttempt.run_id == run.id,\n                    EngineeringAttempt.stage == _DELIVERY_RECORD_STAGE,\n                )\n            )\n            attempt = EngineeringAttempt(\n                run_id=run.id,\n                stage=_DELIVERY_RECORD_STAGE,\n                attempt_number=int(current_attempt_number or 0) + 1,\n                operation_key=operation_key,\n                status=_DELIVERY_RECORD_STATUS,\n                program_id=_DELIVERY_RECORD_PROGRAM,\n                tool_id=_DELIVERY_RECORD_TOOL,\n                evidence_json=encoded,\n                completed_at=utcnow(),\n            )\n            try:\n                self.repository.session.add(attempt)\n                self.repository.session.commit()\n            except IntegrityError as exc:\n                last_integrity_error = exc\n                self.repository.session.rollback()\n                replay = self.load(run_id=run.id, lineage_id=lineage_id)\n                if replay is not None:\n                    if self._canonical(replay) != encoded:\n                        raise VerifiedDeliveryError(\"conflicting durable delivery record already exists\") from exc\n                    return replay, True\n                if insertion_index == 0:\n                    continue\n                raise VerifiedDeliveryError(\"concurrent durable delivery record conflicted\") from exc\n            return payload, False\n        raise VerifiedDeliveryError(\"concurrent durable delivery record conflicted\") from last_integrity_error\n'''
source = replace_once(source, old_persist, new_persist, label="multi-lineage delivery ledger")
source = replace_once(
    source,
    '        branch_name = f"parallax/{identity.project_id[:8]}-{identity.run_id[:8]}"\n',
    '        branch_name = canonical_publication_branch_name(identity, accepted.lineage_id)\n',
    label="ordinary lineage branch",
)
source = replace_once(
    source,
    '    "BootstrapResult",\n',
    '    "BootstrapResult",\n    "canonical_publication_branch_name",\n',
    label="helper export",
)
source_path.write_text(source, encoding="utf-8")

greenfield = greenfield_path.read_text(encoding="utf-8")
greenfield = replace_once(
    greenfield,
    "    BootstrapResult,\n",
    "    BootstrapResult,\n    canonical_publication_branch_name,\n",
    label="greenfield shared helper import",
)
greenfield = replace_once(
    greenfield,
    '        branch_name = f"parallax/{identity.project_id[:8]}-{identity.run_id[:8]}"\n',
    '        branch_name = canonical_publication_branch_name(identity, accepted.lineage_id)\n',
    label="greenfield lineage branch",
)
greenfield_path.write_text(greenfield, encoding="utf-8")

test_source = test_path.read_text(encoding="utf-8")
test_source = replace_once(
    test_source,
    "import pytest\nfrom sqlalchemy.orm import sessionmaker\n",
    "import pytest\nfrom sqlalchemy.exc import IntegrityError\nfrom sqlalchemy.orm import sessionmaker\n",
    label="test IntegrityError import",
)
test_source = replace_once(
    test_source,
    "    EngineeringAttemptDeliveryRecordStore,\n",
    "    EngineeringAttemptDeliveryRecordStore,\n    canonical_publication_branch_name,\n",
    label="test helper import",
)
test_source = replace_once(
    test_source,
    "        self.committed_files = ()\n",
    "        self.committed_files = ()\n        self.created_branch: str | None = None\n",
    label="fake created branch state",
)
test_source = replace_once(
    test_source,
    "        assert base_revision == ROOT_REVISION\n        value = GitHubBranchResult(REPOSITORY_REF, branch_name, base_revision, base_revision)\n",
    "        assert base_revision == ROOT_REVISION\n        self.created_branch = branch_name\n        value = GitHubBranchResult(REPOSITORY_REF, branch_name, base_revision, base_revision)\n",
    label="fake remember branch",
)
test_source = replace_once(
    test_source,
    '        branch = f"parallax/{binding.project_ref[:8]}-{self.run_id[:8]}"\n',
    '        assert self.created_branch is not None\n        branch = self.created_branch\n',
    label="fake PR read branch",
)
test_source = replace_once(
    test_source,
    "    assert result.lineage_id == accepted.lineage_id\n",
    "    assert result.lineage_id == accepted.lineage_id\n    assert result.branch_name == canonical_publication_branch_name(\n        ProjectRunIdentity(project_id, run_id), accepted.lineage_id\n    )\n",
    label="ordinary branch assertion",
)
append_tests = r'''


def test_canonical_publication_branch_name_binds_full_exact_lineage() -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    lineage_one = "src:" + "a" * 64
    lineage_two = "src:" + "b" * 64
    identity = ProjectRunIdentity(project_id, run_id)

    first = canonical_publication_branch_name(identity, lineage_one)
    second = canonical_publication_branch_name(identity, lineage_two)

    assert first == f"parallax/{project_id[:8]}-{run_id[:8]}-{'a' * 64}"
    assert second == f"parallax/{project_id[:8]}-{run_id[:8]}-{'b' * 64}"
    assert first != second
    with pytest.raises(VerifiedDeliveryError, match="publication branch"):
        canonical_publication_branch_name(identity, "src:abc")
    with pytest.raises(VerifiedDeliveryError, match="publication branch"):
        canonical_publication_branch_name(SimpleNamespace(project_id=project_id, run_id=run_id), lineage_one)


def test_delivery_record_store_persists_two_lineages_in_same_run_and_replays_exactly(tmp_path) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    first_lineage = "src:" + "1" * 64
    second_lineage = "src:" + "2" * 64
    engine = make_engine(f"sqlite:///{tmp_path / 'multi-delivery.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        session.add(
            EngineeringRun(
                id=run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.23.43",
                project_id=project_id,
                state="REVIEW",
                revision=12,
            )
        )
        session.commit()
        repository = EngineeringRunRepository(session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        run = repository.get(run_id)
        assert run is not None
        first_payload = {
            "project_id": project_id,
            "run_id": run_id,
            "lineage_id": first_lineage,
            "branch_name": f"parallax/{project_id[:8]}-{run_id[:8]}",
        }
        second_payload = {
            "project_id": project_id,
            "run_id": run_id,
            "lineage_id": second_lineage,
            "branch_name": canonical_publication_branch_name(ProjectRunIdentity(project_id, run_id), second_lineage),
        }

        stored_first, replayed_first = records.persist(run=run, lineage_id=first_lineage, payload=first_payload)
        stored_second, replayed_second = records.persist(run=run, lineage_id=second_lineage, payload=second_payload)
        replay_first, exact_replay = records.persist(run=run, lineage_id=first_lineage, payload=first_payload)

        assert replayed_first is False and replayed_second is False and exact_replay is True
        assert stored_first == first_payload and stored_second == second_payload and replay_first == first_payload
        attempts = [attempt for attempt in repository.get(run_id).attempts if attempt.stage == "SOURCE_DELIVERY"]
        assert [attempt.attempt_number for attempt in attempts] == [1, 2]
        assert len({attempt.operation_key for attempt in attempts}) == 2
        assert records.load(run_id=run_id, lineage_id=first_lineage) == first_payload
        assert records.load(run_id=run_id, lineage_id=second_lineage) == second_payload
        assert repository.get(run_id).revision == 12


def test_delivery_record_store_retries_database_insert_once_after_integrity_error(tmp_path, monkeypatch) -> None:
    project_id, run_id = str(uuid4()), str(uuid4())
    lineage_id = "src:" + "3" * 64
    engine = make_engine(f"sqlite:///{tmp_path / 'delivery-retry.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    with Session() as session:
        session.add(
            EngineeringRun(
                id=run_id,
                conversation_id=str(uuid4()),
                spec_id="P2-V0.23.43",
                project_id=project_id,
                state="REVIEW",
                revision=12,
            )
        )
        session.commit()
        repository = EngineeringRunRepository(session)
        records = EngineeringAttemptDeliveryRecordStore(repository)
        run = repository.get(run_id)
        assert run is not None
        payload = {"project_id": project_id, "run_id": run_id, "lineage_id": lineage_id}
        original_commit = session.commit
        commit_calls = 0

        def flaky_commit():
            nonlocal commit_calls
            commit_calls += 1
            if commit_calls == 1:
                raise IntegrityError("INSERT", {}, RuntimeError("simulated stage-attempt race"))
            return original_commit()

        monkeypatch.setattr(session, "commit", flaky_commit)
        stored, replayed = records.persist(run=run, lineage_id=lineage_id, payload=payload)
        assert stored == payload
        assert replayed is False
        assert commit_calls == 2
        attempt = repository.find_operation(run_id, records.operation_key(lineage_id))
        assert attempt is not None and attempt.attempt_number == 1
'''
if "test_canonical_publication_branch_name_binds_full_exact_lineage" in test_source:
    raise SystemExit("focused P2-V0.23.43 tests already present")
test_source += append_tests
test_path.write_text(test_source, encoding="utf-8")

greenfield_test = greenfield_test_path.read_text(encoding="utf-8")
greenfield_test = replace_once(
    greenfield_test,
    "from types import SimpleNamespace\n",
    "from types import SimpleNamespace\nimport inspect\n",
    label="greenfield inspect import",
)
greenfield_append = r'''


def test_greenfield_delivery_uses_shared_lineage_branch_helper() -> None:
    source = inspect.getsource(GreenfieldVerifiedLineageDelivery.deliver)
    assert "canonical_publication_branch_name(identity, accepted.lineage_id)" in source
    assert 'branch_name = f"parallax/' not in source
'''
if "test_greenfield_delivery_uses_shared_lineage_branch_helper" in greenfield_test:
    raise SystemExit("greenfield helper test already present")
greenfield_test += greenfield_append
greenfield_test_path.write_text(greenfield_test, encoding="utf-8")

print("P2-V0.23.43 semantic patch applied")
