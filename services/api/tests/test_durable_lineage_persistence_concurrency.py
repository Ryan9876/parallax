from __future__ import annotations

from hashlib import sha256
from threading import Event, Lock, Thread
from uuid import uuid4

from parallax_api.code.lineage_persistence import InMemoryLineageMetadataStore, ObjectWriteError
from parallax_api.code.workspace_lineage import (
    LineageIntegrityError,
    ProjectRunIdentity,
    SourceLineageStore,
    SourcePackage,
)


class StaticProvider:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def load(self, identity: ProjectRunIdentity) -> SourcePackage:
        return SourcePackage("repository", "github:owner/repo@bounded-persistence", self.files)


class BlockingObjectStore:
    def __init__(self, *, expected_concurrency: int, fail_digest: str | None = None) -> None:
        self.expected_concurrency = expected_concurrency
        self.fail_digest = fail_digest
        self.objects: dict[str, bytes] = {}
        self.active = 0
        self.max_active = 0
        self.lock = Lock()
        self.all_started = Event()
        self.release = Event()

    def put_if_absent(self, digest: str, content: bytes) -> None:
        payload = bytes(content)
        assert sha256(payload).hexdigest() == digest
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.active >= self.expected_concurrency:
                self.all_started.set()
        try:
            if not self.release.wait(timeout=5):
                raise AssertionError("concurrent persistence test timed out waiting for release")
            if digest == self.fail_digest:
                raise ObjectWriteError("injected concurrent durable object failure")
            with self.lock:
                existing = self.objects.get(digest)
                if existing is not None and existing != payload:
                    raise AssertionError("content-addressed object changed")
                self.objects.setdefault(digest, payload)
        finally:
            with self.lock:
                self.active -= 1

    def get(self, digest: str) -> bytes:
        with self.lock:
            return bytes(self.objects[digest])


def identity() -> ProjectRunIdentity:
    return ProjectRunIdentity(str(uuid4()), str(uuid4()))


def _run_initialize(
    store: SourceLineageStore,
    run_identity: ProjectRunIdentity,
    files: dict[str, bytes],
    results: list[object],
    errors: list[BaseException],
) -> None:
    try:
        results.append(store.initialize(run_identity, StaticProvider(files)))
    except BaseException as exc:  # pragma: no cover - asserted by caller
        errors.append(exc)


def test_durable_object_persistence_overlaps_with_fixed_eight_worker_bound():
    files = {f"src/file-{index:02d}.txt": f"payload-{index}\n".encode() for index in range(12)}
    objects = BlockingObjectStore(expected_concurrency=8)
    metadata = InMemoryLineageMetadataStore()
    store = SourceLineageStore(objects, metadata)
    run_identity = identity()
    results: list[object] = []
    errors: list[BaseException] = []

    thread = Thread(
        target=_run_initialize,
        args=(store, run_identity, files, results, errors),
        daemon=True,
    )
    thread.start()

    assert objects.all_started.wait(timeout=2), "object persistence did not overlap eight operations"
    assert objects.max_active == 8
    assert metadata.get_current(run_identity.project_id, run_identity.run_id) is None
    assert metadata.manifests == {}

    objects.release.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert errors == []
    assert len(results) == 1
    lineage = results[0]
    assert metadata.get_current(run_identity.project_id, run_identity.run_id) == lineage.lineage_id
    assert len(objects.objects) == len(files)


def test_concurrent_object_failure_never_advances_manifest_or_head():
    files = {f"src/file-{index:02d}.txt": f"payload-{index}\n".encode() for index in range(4)}
    failing_path = "src/file-02.txt"
    failing_digest = sha256(files[failing_path]).hexdigest()
    objects = BlockingObjectStore(expected_concurrency=4, fail_digest=failing_digest)
    metadata = InMemoryLineageMetadataStore()
    store = SourceLineageStore(objects, metadata)
    run_identity = identity()
    results: list[object] = []
    errors: list[BaseException] = []

    thread = Thread(
        target=_run_initialize,
        args=(store, run_identity, files, results, errors),
        daemon=True,
    )
    thread.start()

    assert objects.all_started.wait(timeout=2), "object persistence did not reach the concurrent failure boundary"
    assert metadata.get_current(run_identity.project_id, run_identity.run_id) is None
    assert metadata.manifests == {}

    objects.release.set()
    thread.join(timeout=5)

    assert not thread.is_alive()
    assert results == []
    assert len(errors) == 1
    assert isinstance(errors[0], LineageIntegrityError)
    assert metadata.get_current(run_identity.project_id, run_identity.run_id) is None
    assert metadata.manifests == {}
