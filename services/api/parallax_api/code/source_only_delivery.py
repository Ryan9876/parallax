from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from ..models import EngineeringRun
from .source_delivery_composition import (
    DeliveryRecordStore,
    DurableSourceAllocator,
    ProjectBindingResolver,
    VerifiedDeliveryError,
    VerifiedLineageDelivery,
)


_SOURCE_ONLY_RECORD_KIND = "source_only_delivery"
_SOURCE_ONLY_RECORD_VERSION = 1


@dataclass(frozen=True, slots=True)
class SourceOnlyDeliveryResult:
    project_id: str
    run_id: str
    repository_identity_digest: str
    lineage_id: str
    content_digest: str
    handoff_id: str
    delivery_mode: str = "source-only"
    replayed: bool = False

    def to_record(self) -> dict[str, object]:
        return {
            "record_kind": _SOURCE_ONLY_RECORD_KIND,
            "record_version": _SOURCE_ONLY_RECORD_VERSION,
            "delivery_mode": self.delivery_mode,
            "project_id": self.project_id,
            "run_id": self.run_id,
            "repository_identity_digest": self.repository_identity_digest,
            "lineage_id": self.lineage_id,
            "content_digest": self.content_digest,
            "handoff_id": self.handoff_id,
        }

    @classmethod
    def from_record(cls, payload: object, *, replayed: bool) -> SourceOnlyDeliveryResult:
        if not isinstance(payload, dict):
            raise VerifiedDeliveryError("durable source-only delivery record is invalid")
        if (
            payload.get("record_kind") != _SOURCE_ONLY_RECORD_KIND
            or payload.get("record_version") != _SOURCE_ONLY_RECORD_VERSION
            or payload.get("delivery_mode") != "source-only"
        ):
            raise VerifiedDeliveryError("durable source-only delivery record version is unsupported")
        values: dict[str, str] = {}
        for field in (
            "project_id",
            "run_id",
            "repository_identity_digest",
            "lineage_id",
            "content_digest",
            "handoff_id",
        ):
            value = payload.get(field)
            if not isinstance(value, str) or not value:
                raise VerifiedDeliveryError(f"durable source-only delivery record {field} is invalid")
            values[field] = value
        if not values["lineage_id"].startswith("src:"):
            raise VerifiedDeliveryError("durable source-only delivery lineage identity is invalid")
        if not values["handoff_id"].startswith("handoff:"):
            raise VerifiedDeliveryError("durable source-only handoff identity is invalid")
        return cls(**values, replayed=replayed)


class SourceOnlyLineageDelivery:
    """Record an exact accepted source handoff without invoking a hosting provider."""

    def __init__(
        self,
        *,
        allocator: DurableSourceAllocator,
        projects: ProjectBindingResolver,
        records: DeliveryRecordStore,
    ) -> None:
        self.allocator = allocator
        self.projects = projects
        self.records = records

    @staticmethod
    def _handoff_id(project_id: str, run_id: str, lineage_id: str, content_digest: str) -> str:
        digest = sha256(
            f"{project_id}|{run_id}|{lineage_id}|{content_digest}|source-only-v1".encode("utf-8")
        ).hexdigest()
        return f"handoff:{digest}"

    def resolve_record(
        self,
        run: EngineeringRun,
        *,
        accepted_lineage_id: str | None = None,
    ) -> SourceOnlyDeliveryResult | None:
        identity = VerifiedLineageDelivery._identity(run)
        lineage_id = accepted_lineage_id or VerifiedLineageDelivery._verified_lineage_id(run, identity)
        payload = self.records.load(run_id=identity.run_id, lineage_id=lineage_id)
        if payload is None:
            return None
        result = SourceOnlyDeliveryResult.from_record(payload, replayed=True)
        if result.project_id != identity.project_id or result.run_id != identity.run_id:
            raise VerifiedDeliveryError("durable source-only delivery belongs to a different Project/run")
        if result.lineage_id != lineage_id:
            raise VerifiedDeliveryError("durable source-only delivery belongs to a different lineage")
        return result

    def deliver(self, run: EngineeringRun, *, operation_key: str) -> SourceOnlyDeliveryResult:
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise VerifiedDeliveryError("source-only delivery operation key is required")
        identity = VerifiedLineageDelivery._identity(run)
        accepted_lineage_id = VerifiedLineageDelivery._verified_lineage_id(run, identity)
        try:
            current = self.allocator.current_lineage(identity)
        except Exception as exc:
            raise VerifiedDeliveryError("current durable source lineage is unavailable") from exc
        if current.lineage_id != accepted_lineage_id:
            raise VerifiedDeliveryError("current durable lineage moved after verified implementation")

        replay = self.resolve_record(run, accepted_lineage_id=accepted_lineage_id)
        if replay is not None:
            if replay.content_digest != current.content_digest:
                raise VerifiedDeliveryError("source-only handoff no longer matches accepted lineage")
            return replay

        binding = self.projects.resolve(identity.project_id)
        repository_identity_digest = sha256(binding.repository_ref.encode("utf-8")).hexdigest()
        result = SourceOnlyDeliveryResult(
            project_id=identity.project_id,
            run_id=identity.run_id,
            repository_identity_digest=repository_identity_digest,
            lineage_id=current.lineage_id,
            content_digest=current.content_digest,
            handoff_id=self._handoff_id(
                identity.project_id,
                identity.run_id,
                current.lineage_id,
                current.content_digest,
            ),
        )
        persisted, replayed = self.records.persist(
            run=run,
            lineage_id=current.lineage_id,
            payload=result.to_record(),
        )
        restored = SourceOnlyDeliveryResult.from_record(persisted, replayed=replayed)
        if restored.content_digest != current.content_digest:
            raise VerifiedDeliveryError("persisted source-only handoff content mismatch")
        return restored


__all__ = ["SourceOnlyDeliveryResult", "SourceOnlyLineageDelivery"]
