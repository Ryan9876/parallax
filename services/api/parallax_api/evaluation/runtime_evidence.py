from __future__ import annotations

from dataclasses import dataclass, replace
import json
import re
from typing import Protocol

from sqlalchemy.orm import Session

from ..code.domain import AttemptStatus, WorkflowStage
from ..code.protected import STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE
from ..code.validation_toolchains import (
    ExecutionBindingReason,
    ExecutionContractCode,
    ExecutionContractIdentity,
    ValidationProfileError,
)
from ..code.work_spec_binding import required_acceptance_ids, work_specification_digest
from ..code.workspace_lineage import ProjectRunIdentity, SourceLineage, SourceLineageStore
from ..models import EngineeringAttempt, EngineeringRun, WorkSpecification
from ..projects.repository import ProjectRepository
from ..repositories.engineering_runs import EngineeringRunRepository
from ..repositories.work_specifications import WorkSpecificationRepository
from ..tools.contracts import ToolAuditRecord, ToolOutcome
from ..tools.providers.common import (
    ProviderActionEvidence,
    ProviderActionState,
    require_project_id,
    require_repository_ref,
    require_sha256,
    require_source_lineage_id,
    require_source_revision,
)
from .app_builder import (
    AppBuilderBenchmarkCase,
    AppBuilderBenchmarkSuite,
    AppBuilderCaseEvidence,
    AppBuilderEvaluationReport,
    AppBuilderRecordedEvidence,
    canonical_digest,
    evaluate_app_builder,
)
from .security import assert_safe_payload


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_EVIDENCE_KEYS = frozenset(
    {
        "authorization",
        "authorization_header",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "environment",
        "headers",
        "hidden_reasoning",
        "provider_payload",
        "provider_response",
        "raw_provider_payload",
        "raw_provider_response",
        "reasoning",
        "reasoning_trace",
        "scratchpad",
        "secret",
        "token",
        "workspace_root",
    }
)
_MAX_ACTION_FACTS = 24
_MAX_ARTIFACTS = 32


class RuntimeEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PersistedProviderActionFact:
    """Secret-safe persisted #62/#70 provider evidence plus its Wave 1 audit record."""

    evidence: ProviderActionEvidence
    audit: ToolAuditRecord

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, ProviderActionEvidence):
            raise TypeError("provider action fact requires ProviderActionEvidence")
        if not isinstance(self.audit, ToolAuditRecord):
            raise TypeError("provider action fact requires ToolAuditRecord")
        if self.audit.project_ref != self.evidence.project_ref:
            raise ValueError("provider audit Project identity mismatch")
        if self.audit.tool != self.evidence.provider or self.audit.action != self.evidence.action:
            raise ValueError("provider audit tool/action identity mismatch")

        expected = {
            ProviderActionState.DENIED: ToolOutcome.DENIED,
            ProviderActionState.FAILED: ToolOutcome.FAILED,
            ProviderActionState.SUCCEEDED: ToolOutcome.SUCCEEDED,
        }[self.evidence.state]
        if self.audit.outcome is not expected:
            raise ValueError("provider evidence state does not match durable audit outcome")
        if self.evidence.state is ProviderActionState.DENIED:
            if self.audit.authority_allowed or self.audit.deny_reason is None:
                raise ValueError("provider denial lacks denied authority evidence")
            if self.evidence.result_status != self.audit.deny_reason.value:
                raise ValueError("provider denial status does not match audit reason")
        else:
            if not self.audit.authority_allowed or self.audit.deny_reason is not None:
                raise ValueError("provider execution lacks allowed authority evidence")
            if self.evidence.result_status != self.audit.result_code:
                raise ValueError("provider result status does not match audit result code")
            if self.evidence.result_identity != self.audit.result_identity:
                raise ValueError("provider result identity does not match audit result identity")
        if not _SHA256.fullmatch(self.audit.request_digest):
            raise ValueError("provider audit request digest is invalid")
        if self.audit.result_digest is not None and not _SHA256.fullmatch(self.audit.result_digest):
            raise ValueError("provider audit result digest is invalid")

    @property
    def digest(self) -> str:
        return canonical_digest(
            {
                "provider": self.evidence.provider,
                "action": self.evidence.action,
                "state": self.evidence.state.value,
                "project_ref": self.evidence.project_ref,
                "repository_identity_digest": self.evidence.repository_identity_digest,
                "source_revision": self.evidence.source_revision,
                "lineage_id": self.evidence.lineage_id,
                "lineage_digest": self.evidence.lineage_digest,
                "result_identity": self.evidence.result_identity,
                "result_status": self.evidence.result_status,
                "request_id": self.audit.request_id,
                "capability_id": self.audit.capability_id,
                "approval_id": self.audit.approval_id,
                "authority_allowed": self.audit.authority_allowed,
                "outcome": self.audit.outcome.value,
                "request_digest": self.audit.request_digest,
                "result_digest": self.audit.result_digest,
            }
        )


@dataclass(frozen=True, slots=True)
class PersistedVerifiedDelivery:
    """Provisional read model for #79 verified-source delivery persistence.

    #80 consumes this shape only. It does not own the mutation/storage path that
    produces it. Final worker readiness requires adaptation to accepted #79.
    """

    project_id: str
    run_id: str
    repository_ref: str
    lineage_id: str
    content_digest: str
    expected_parent_revision: str
    published_revision: str
    pull_request_identity: str
    preview_deployment_id: str
    preview_status: str
    actions: tuple[PersistedProviderActionFact, ...]
    publication_replayed: bool

    def __post_init__(self) -> None:
        require_project_id(self.project_id)
        require_project_id(self.run_id)
        require_repository_ref(self.repository_ref)
        require_source_lineage_id(self.lineage_id)
        require_sha256(self.content_digest, field="content_digest")
        require_source_revision(self.expected_parent_revision, field="expected_parent_revision")
        require_source_revision(self.published_revision, field="published_revision")
        if not isinstance(self.pull_request_identity, str) or not re.fullmatch(r"pr:[1-9][0-9]{0,9}", self.pull_request_identity):
            raise ValueError("pull_request_identity must use bounded pr:<number> form")
        if not isinstance(self.preview_deployment_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}", self.preview_deployment_id
        ):
            raise ValueError("preview_deployment_id must be bounded")
        if self.preview_status not in {"QUEUED", "BUILDING", "READY", "ERROR", "CANCELED"}:
            raise ValueError("preview_status is invalid")
        if not isinstance(self.actions, tuple) or not self.actions or len(self.actions) > _MAX_ACTION_FACTS:
            raise ValueError("verified delivery requires bounded provider action facts")
        if not all(isinstance(item, PersistedProviderActionFact) for item in self.actions):
            raise TypeError("delivery actions must contain PersistedProviderActionFact values")
        if not isinstance(self.publication_replayed, bool):
            raise TypeError("publication_replayed must be bool")


class VerifiedSourceDeliveryReader(Protocol):
    """Narrow read-only #79 seam consumed by #80."""

    def get_verified_delivery(
        self,
        *,
        project_id: str,
        run_id: str,
        lineage_id: str,
    ) -> PersistedVerifiedDelivery | None: ...


@dataclass(frozen=True, slots=True)
class RuntimeEvidenceSnapshot:
    project_id: str
    workspace_ref: str
    repository_ref: str
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    run_id: str
    accepted_lineage_id: str
    accepted_content_digest: str
    accepted_parent_lineage_id: str
    implementation_workspace_digest: str
    implementation_proposal_digest: str
    implementation_source_context_digest: str
    implementation_artifact_digests: tuple[str, ...]
    build_digest: str
    test_digest: str
    verify_digest: str
    delivery: PersistedVerifiedDelivery
    recovery_resumed: bool
    implementation_duplicate: bool

    @property
    def spec_digest(self) -> str:
        return f"sha256:{self.work_specification_digest}"


class RuntimeAppBuilderEvidenceAdapter:
    """Derive #46 evidence from persisted Wave 2 runtime/provider facts only."""

    def __init__(
        self,
        session: Session,
        *,
        owner_subject: str,
        lineage_store: SourceLineageStore,
        delivery_reader: VerifiedSourceDeliveryReader,
    ) -> None:
        if not owner_subject or not owner_subject.strip():
            raise ValueError("owner_subject is required")
        self.session = session
        self.owner_subject = owner_subject.strip()
        self.runs = EngineeringRunRepository(session)
        self.projects = ProjectRepository(session)
        self.work_specs = WorkSpecificationRepository(session)
        self.lineage_store = lineage_store
        self.delivery_reader = delivery_reader

    def snapshot(self, run_id: str) -> RuntimeEvidenceSnapshot:
        run = self._run(run_id)
        project = self._project(run)
        specification = self._specification(run)
        acceptance = required_acceptance_ids(specification)
        implementation, implementation_payload = self._implementation(run)
        lineage = self._lineage(run, implementation_payload)
        acceptance_verification_scope = self._acceptance_verification_scope(
            run, implementation, implementation_payload
        )
        stages = {
            stage: self._execution_attempt(
                run,
                stage,
                lineage,
                acceptance,
                acceptance_verification_scope=acceptance_verification_scope,
            )
            for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY)
        }
        delivery = self._delivery(run, project.repository_ref or "", lineage)

        resumed = any(item.status == AttemptStatus.RESUMED.value for item in run.attempts)
        passed_implementations = [
            item
            for item in run.attempts
            if item.stage == WorkflowStage.IMPLEMENT.value and item.status == AttemptStatus.PASSED.value
        ]
        if len(passed_implementations) != 1:
            raise RuntimeEvidenceError("runtime evidence requires exactly one accepted IMPLEMENT mutation")

        artifacts = implementation_payload.get("artifacts")
        if not isinstance(artifacts, list) or not 1 <= len(artifacts) <= _MAX_ARTIFACTS:
            raise RuntimeEvidenceError("IMPLEMENT artifact evidence is missing or unbounded")
        artifact_digests: list[str] = []
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                raise RuntimeEvidenceError("IMPLEMENT artifact evidence is malformed")
            path = artifact.get("path")
            digest = artifact.get("sha256")
            size = artifact.get("size")
            if not isinstance(path, str) or not path or len(path) > 240:
                raise RuntimeEvidenceError("IMPLEMENT artifact path is invalid")
            self._raw_digest(digest, field="artifact sha256")
            if not isinstance(size, int) or isinstance(size, bool) or size < 0:
                raise RuntimeEvidenceError("IMPLEMENT artifact size is invalid")
            artifact_digests.append(canonical_digest({"path": path, "sha256": digest, "size": size}))

        workspace_digest = self._raw_digest(implementation_payload.get("workspace_digest"), field="workspace_digest")
        proposal_digest = self._raw_digest(implementation_payload.get("proposal_digest"), field="proposal_digest")
        context_digest = self._raw_digest(
            implementation_payload.get("source_context_digest"), field="source_context_digest"
        )

        return RuntimeEvidenceSnapshot(
            project_id=project.id,
            workspace_ref=project.workspace_ref,
            repository_ref=project.repository_ref or "",
            work_specification_id=specification.id,
            work_specification_revision=specification.revision,
            work_specification_digest=run.work_specification_digest or "",
            run_id=run.id,
            accepted_lineage_id=lineage.lineage_id,
            accepted_content_digest=lineage.content_digest,
            accepted_parent_lineage_id=lineage.parent_lineage_id or "",
            implementation_workspace_digest=workspace_digest,
            implementation_proposal_digest=proposal_digest,
            implementation_source_context_digest=context_digest,
            implementation_artifact_digests=tuple(artifact_digests),
            build_digest=stages[WorkflowStage.BUILD],
            test_digest=stages[WorkflowStage.TEST],
            verify_digest=stages[WorkflowStage.VERIFY],
            delivery=delivery,
            recovery_resumed=resumed,
            implementation_duplicate=False,
        )

    def bind_suite(
        self,
        suite: AppBuilderBenchmarkSuite,
        snapshot: RuntimeEvidenceSnapshot,
    ) -> AppBuilderBenchmarkSuite:
        if suite.suite_id != "parallax-app-builder-runtime-reference" or suite.spec_id != "P2-V0.15.10":
            raise RuntimeEvidenceError("runtime evidence adapter requires the P2-V0.15.10 reference suite")
        cases: list[AppBuilderBenchmarkCase] = []
        for case in suite.cases:
            cases.append(
                case.model_copy(
                    update={
                        "expected_project_ref": snapshot.project_id,
                        "expected_workspace_ref": snapshot.workspace_ref,
                        "expected_spec_ref": snapshot.work_specification_id,
                        "expected_spec_revision": snapshot.work_specification_revision,
                        "expected_spec_digest": snapshot.spec_digest,
                    }
                )
            )
        bound = suite.model_copy(update={"cases": cases})
        # Ensure dynamic binding did not alter any scoring/critical semantics.
        if (
            bound.minimum_aggregate_score != suite.minimum_aggregate_score
            or bound.category_minimums != suite.category_minimums
            or any(
                updated.minimum_score != original.minimum_score
                or updated.requirements != original.requirements
                or updated.case_weight != original.case_weight
                for updated, original in zip(bound.cases, suite.cases, strict=True)
            )
        ):
            raise RuntimeEvidenceError("reference-suite binding attempted to alter protected scoring semantics")
        return bound

    def recorded_evidence(
        self,
        suite: AppBuilderBenchmarkSuite,
        snapshot: RuntimeEvidenceSnapshot,
        *,
        candidate_version: str,
        model_id: str | None = None,
    ) -> AppBuilderRecordedEvidence:
        bound = self.bind_suite(suite, snapshot)
        project_digest = canonical_digest(
            {
                "project_id": snapshot.project_id,
                "workspace_ref": snapshot.workspace_ref,
                "repository_ref": snapshot.repository_ref,
            }
        )
        spec_digest = canonical_digest(
            {
                "work_specification_id": snapshot.work_specification_id,
                "revision": snapshot.work_specification_revision,
                "digest": snapshot.work_specification_digest,
            }
        )
        lineage_digest = canonical_digest(
            {
                "project_id": snapshot.project_id,
                "run_id": snapshot.run_id,
                "lineage_id": snapshot.accepted_lineage_id,
                "parent_lineage_id": snapshot.accepted_parent_lineage_id,
                "content_digest": snapshot.accepted_content_digest,
            }
        )
        implementation_digest = canonical_digest(
            {
                "workspace_digest": snapshot.implementation_workspace_digest,
                "proposal_digest": snapshot.implementation_proposal_digest,
                "source_context_digest": snapshot.implementation_source_context_digest,
                "artifact_digests": list(snapshot.implementation_artifact_digests),
            }
        )
        provider_digests = tuple(item.digest for item in snapshot.delivery.actions)
        delivery_digest = canonical_digest(
            {
                "project_id": snapshot.delivery.project_id,
                "run_id": snapshot.delivery.run_id,
                "repository_ref": snapshot.delivery.repository_ref,
                "lineage_id": snapshot.delivery.lineage_id,
                "content_digest": snapshot.delivery.content_digest,
                "expected_parent_revision": snapshot.delivery.expected_parent_revision,
                "published_revision": snapshot.delivery.published_revision,
                "pull_request_identity": snapshot.delivery.pull_request_identity,
                "preview_deployment_id": snapshot.delivery.preview_deployment_id,
                "preview_status": snapshot.delivery.preview_status,
                "provider_action_digests": list(provider_digests),
                "publication_replayed": snapshot.delivery.publication_replayed,
            }
        )
        recovery_digest = canonical_digest(
            {
                "run_id": snapshot.run_id,
                "lineage_id": snapshot.accepted_lineage_id,
                "recovery_resumed": snapshot.recovery_resumed,
                "implementation_duplicate": snapshot.implementation_duplicate,
                "publication_replayed": snapshot.delivery.publication_replayed,
            }
        )

        common = {
            "project_ref": snapshot.project_id,
            "workspace_ref": snapshot.workspace_ref,
            "spec_ref": snapshot.work_specification_id,
            "spec_revision": snapshot.work_specification_revision,
            "spec_digest": snapshot.spec_digest,
            "run_ref": snapshot.run_id,
        }
        observations = {
            "runtime-project-isolation-01": [
                "project.binding=verified",
                "project.repository=verified",
                "cross_project.access=denied",
            ],
            "runtime-spec-binding-01": ["spec.binding=verified", "spec.digest=verified"],
            "runtime-implementation-evidence-01": [
                "implementation.patch=bounded",
                "diff.inspectable=true",
                "implementation.lineage=accepted",
                "implementation.provider_authority=false",
            ],
            "runtime-build-test-verify-01": [
                "build.result=success",
                "test.result=success",
                "verify.result=success",
                "execution.same_lineage=true",
                "execution.fresh_source=false",
            ],
            "runtime-tool-authority-01": [
                "github.publication=succeeded",
                "vercel.preview=ready",
                "provider.audit=verified",
                "production.authority=false",
            ],
            "runtime-interruption-recovery-01": [
                "recovery.result=resumed",
                "run.identity=preserved",
                "lineage.identity=preserved",
                "implementation.duplicate=false",
                "publication.duplicate=false",
            ],
            "runtime-evidence-hygiene-01": [
                "evidence.secret=false",
                "evidence.hidden_reasoning=false",
                "evidence.provider_raw=false",
                "evidence.bounded=true",
                "evidence.observable_only=true",
            ],
        }
        digests = {
            "runtime-project-isolation-01": [project_digest, delivery_digest],
            "runtime-spec-binding-01": [project_digest, spec_digest],
            "runtime-implementation-evidence-01": [
                project_digest,
                spec_digest,
                implementation_digest,
                lineage_digest,
            ],
            "runtime-build-test-verify-01": [
                project_digest,
                lineage_digest,
                snapshot.build_digest,
                snapshot.test_digest,
                snapshot.verify_digest,
            ],
            "runtime-tool-authority-01": [
                project_digest,
                lineage_digest,
                delivery_digest,
                *provider_digests[:8],
            ],
            "runtime-interruption-recovery-01": [
                project_digest,
                lineage_digest,
                delivery_digest,
                recovery_digest,
            ],
            "runtime-evidence-hygiene-01": [project_digest, spec_digest, delivery_digest],
        }

        if not snapshot.recovery_resumed:
            raise RuntimeEvidenceError("reference runtime lacks persisted interruption/resume evidence")
        if snapshot.implementation_duplicate:
            raise RuntimeEvidenceError("reference runtime contains duplicate IMPLEMENT mutation")
        if not snapshot.delivery.publication_replayed:
            raise RuntimeEvidenceError("reference runtime lacks persisted provider retry/replay proof")

        cases: list[AppBuilderCaseEvidence] = []
        for case in bound.cases:
            case_digests = list(dict.fromkeys(digests[case.case_id]))
            if len(case_digests) > 16:
                raise RuntimeEvidenceError("runtime case evidence exceeds #46 digest bound")
            cases.append(
                AppBuilderCaseEvidence(
                    case_id=case.case_id,
                    **common,
                    observations=observations[case.case_id],
                    evidence_digests=case_digests,
                )
            )
        artifact_seed = canonical_digest(
            {
                "run_id": snapshot.run_id,
                "lineage_id": snapshot.accepted_lineage_id,
                "delivery_digest": delivery_digest,
            }
        )
        evidence = AppBuilderRecordedEvidence(
            evidence_version="1",
            artifact_id=f"runtime-evidence-{artifact_seed[7:23]}",
            suite_id=bound.suite_id,
            suite_version=bound.suite_version,
            suite_purpose=bound.purpose,
            candidate_version=candidate_version,
            model_id=model_id,
            cases=cases,
        )
        assert_safe_payload(evidence)
        return evidence

    def evaluate(
        self,
        suite: AppBuilderBenchmarkSuite,
        snapshot: RuntimeEvidenceSnapshot,
        *,
        candidate_version: str,
        model_id: str | None = None,
    ) -> AppBuilderEvaluationReport:
        bound = self.bind_suite(suite, snapshot)
        evidence = self.recorded_evidence(
            suite,
            snapshot,
            candidate_version=candidate_version,
            model_id=model_id,
        )
        return evaluate_app_builder(bound, evidence)

    def _run(self, run_id: str) -> EngineeringRun:
        run = self.runs.get(run_id)
        if run is None:
            raise RuntimeEvidenceError("engineering run does not exist")
        if not run.project_id:
            raise RuntimeEvidenceError("runtime evidence requires a Project-bound Engineering Run")
        require_project_id(run.project_id)
        return run

    def _project(self, run: EngineeringRun):
        project = self.projects.get_for_owner(run.project_id or "", self.owner_subject)
        if project is None:
            raise RuntimeEvidenceError("owner-scoped Project does not exist")
        if project.status != "active":
            raise RuntimeEvidenceError("runtime evidence requires an active Project")
        if not project.repository_ref:
            raise RuntimeEvidenceError("runtime evidence requires a canonical Project repository binding")
        require_repository_ref(project.repository_ref)
        if run.project_id != project.id:
            raise RuntimeEvidenceError("Engineering Run Project identity mismatch")
        return project

    def _specification(self, run: EngineeringRun) -> WorkSpecification:
        if not run.work_specification_id or run.work_specification_revision is None or not run.work_specification_digest:
            raise RuntimeEvidenceError("Engineering Run lacks immutable Work Specification binding")
        specification = self.work_specs.get(run.work_specification_id)
        if specification is None:
            raise RuntimeEvidenceError("bound Work Specification does not exist")
        if specification.conversation_id != run.conversation_id:
            raise RuntimeEvidenceError("Work Specification conversation mismatch")
        if specification.status not in {"APPROVED", "SUPERSEDED"}:
            raise RuntimeEvidenceError("Work Specification is not an approved execution contract")
        if specification.revision != run.work_specification_revision:
            raise RuntimeEvidenceError("Work Specification revision mismatch")
        actual = work_specification_digest(specification)
        if actual != run.work_specification_digest or not _SHA256.fullmatch(actual):
            raise RuntimeEvidenceError("Work Specification digest mismatch")
        return specification

    def _implementation(self, run: EngineeringRun) -> tuple[EngineeringAttempt, dict[str, object]]:
        passing = [
            item
            for item in run.attempts
            if item.stage == WorkflowStage.IMPLEMENT.value and item.status == AttemptStatus.PASSED.value
        ]
        if len(passing) != 1:
            raise RuntimeEvidenceError("runtime evidence requires exactly one passing IMPLEMENT attempt")
        payload = self._payload(passing[0])
        required_false = (
            "protected_stage_authority",
            "external_execution",
            "network_mutation",
            "git_mutation",
            "deployment_mutation",
        )
        if any(payload.get(key) is not False for key in required_false):
            raise RuntimeEvidenceError("IMPLEMENT evidence broadened protected/provider authority")
        if payload.get("project_ref") != run.project_id or payload.get("run_id") != run.id:
            raise RuntimeEvidenceError("IMPLEMENT Project/run identity mismatch")
        if not isinstance(payload.get("source_lineage_ref"), str) or not isinstance(
            payload.get("base_source_lineage_ref"), str
        ):
            raise RuntimeEvidenceError("IMPLEMENT lacks accepted source-lineage identity")
        return passing[0], payload

    def _lineage(self, run: EngineeringRun, implementation: dict[str, object]) -> SourceLineage:
        identity = ProjectRunIdentity(project_id=run.project_id or "", run_id=run.id)
        current = self.lineage_store.current(identity)
        if current is None:
            raise RuntimeEvidenceError("durable current lineage is unavailable")
        if current.lineage_id != implementation.get("source_lineage_ref"):
            raise RuntimeEvidenceError("durable current lineage does not match accepted IMPLEMENT lineage")
        if current.parent_lineage_id != implementation.get("base_source_lineage_ref"):
            raise RuntimeEvidenceError("durable IMPLEMENT lineage parent mismatch")
        if current.source_kind != "implementation":
            raise RuntimeEvidenceError("current lineage is not an accepted implementation result")
        return current

    def _acceptance_verification_scope(
        self,
        run: EngineeringRun,
        implementation_attempt: EngineeringAttempt,
        implementation_payload: dict[str, object],
    ) -> str | None:
        try:
            implementation_index = next(
                index for index, item in enumerate(run.attempts) if item.id == implementation_attempt.id
            )
        except StopIteration as exc:  # pragma: no cover - ORM identity invariant
            raise RuntimeEvidenceError("accepted IMPLEMENT attempt is not attached to the Engineering Run") from exc

        base_source_lineage_ref = implementation_payload.get("base_source_lineage_ref")
        if not isinstance(base_source_lineage_ref, str) or not base_source_lineage_ref:
            raise RuntimeEvidenceError("IMPLEMENT lacks base source-lineage identity")

        for attempt in reversed(run.attempts[:implementation_index]):
            if attempt.stage != WorkflowStage.PLAN.value or attempt.status != AttemptStatus.PASSED.value:
                continue
            evidence = self._payload(attempt)
            if "execution_contract_id" not in evidence:
                # Historical reference evidence predating immutable execution
                # contracts retains its exact full-verification semantics.
                return None
            expected = {
                "project_id": run.project_id,
                "run_id": run.id,
                "work_specification_id": run.work_specification_id,
                "work_specification_revision": run.work_specification_revision,
                "work_specification_digest": run.work_specification_digest,
                "base_source_lineage_ref": base_source_lineage_ref,
            }
            if any(evidence.get(key) != value for key, value in expected.items()):
                raise RuntimeEvidenceError("PLAN execution-contract identity does not match accepted run lineage")
            try:
                contract = ExecutionContractIdentity.from_evidence(evidence).resolve()
            except ValidationProfileError as exc:
                raise RuntimeEvidenceError("PLAN execution-contract identity is invalid or drifted") from exc
            if (
                contract.contract_id is ExecutionContractCode.STATIC_WEB
                and contract.binding_reason is ExecutionBindingReason.GREENFIELD_STATIC_WEB
            ):
                return STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE
            return None
        return None

    def _execution_attempt(
        self,
        run: EngineeringRun,
        stage: WorkflowStage,
        lineage: SourceLineage,
        required_acceptance: set[str],
        *,
        acceptance_verification_scope: str | None,
    ) -> str:
        attempts = [
            item
            for item in run.attempts
            if item.stage == stage.value and item.status == AttemptStatus.PASSED.value
        ]
        if len(attempts) != 1:
            raise RuntimeEvidenceError(f"runtime evidence requires exactly one passing {stage.value} attempt")
        payload = self._payload(attempts[0])
        if payload.get("protected_success") is not True or payload.get("exit_code") != 0 or payload.get("timed_out"):
            raise RuntimeEvidenceError(f"{stage.value} persisted evidence does not prove protected success")
        if payload.get("project_ref") != run.project_id:
            raise RuntimeEvidenceError(f"{stage.value} Project identity mismatch")
        if payload.get("source_lineage_ref") != lineage.lineage_id:
            raise RuntimeEvidenceError(f"{stage.value} source lineage mismatch")
        if payload.get("source_content_digest") != lineage.content_digest:
            raise RuntimeEvidenceError(f"{stage.value} source content digest mismatch")
        if payload.get("lineage_bound_execution") is not True or payload.get("lineage_source_transfer") is not True:
            raise RuntimeEvidenceError(f"{stage.value} was not proven against exact accepted lineage")
        if payload.get("fresh_repository_checkout") is not False:
            raise RuntimeEvidenceError(f"{stage.value} used unrelated/fresh repository source")

        def exact_ids(key: str) -> list[str]:
            raw = payload.get(key)
            if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
                raise RuntimeEvidenceError(f"{stage.value} acceptance coverage mismatch")
            if len(raw) != len(set(raw)) or set(raw) != required_acceptance:
                raise RuntimeEvidenceError(f"{stage.value} acceptance coverage mismatch")
            return raw

        if stage is WorkflowStage.BUILD:
            exact_ids("acceptance_ids_targeted")
            digest_scope = "TARGETED"
        elif acceptance_verification_scope == STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE:
            if payload.get("acceptance_verification_scope") != STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE:
                raise RuntimeEvidenceError(f"{stage.value} structural verification scope mismatch")
            exact_ids("acceptance_ids_targeted")
            exact_ids("acceptance_ids_unverified")
            verified = payload.get("acceptance_ids_verified")
            if not isinstance(verified, list) or verified:
                raise RuntimeEvidenceError(f"{stage.value} structural evidence claimed protected acceptance verification")
            digest_scope = STRUCTURAL_ACCEPTANCE_VERIFICATION_SCOPE
        else:
            if payload.get("acceptance_verification_scope") is not None:
                raise RuntimeEvidenceError(f"{stage.value} unexpected acceptance verification scope")
            exact_ids("acceptance_ids_verified")
            digest_scope = "FULL"

        return canonical_digest(
            {
                "stage": stage.value,
                "attempt_id": attempts[0].id,
                "operation_key": attempts[0].operation_key,
                "project_ref": run.project_id,
                "run_id": run.id,
                "source_lineage_ref": lineage.lineage_id,
                "source_content_digest": lineage.content_digest,
                "protected_success": True,
                "acceptance_verification_scope": digest_scope,
                "acceptance_ids": sorted(required_acceptance),
                "lineage_bound_execution": True,
                "lineage_source_transfer": True,
                "fresh_repository_checkout": False,
            }
        )

    def _delivery(self, run: EngineeringRun, repository_ref: str, lineage: SourceLineage) -> PersistedVerifiedDelivery:
        delivery = self.delivery_reader.get_verified_delivery(
            project_id=run.project_id or "",
            run_id=run.id,
            lineage_id=lineage.lineage_id,
        )
        if delivery is None:
            raise RuntimeEvidenceError("verified-source provider delivery record is missing")
        if (
            delivery.project_id != run.project_id
            or delivery.run_id != run.id
            or delivery.repository_ref != repository_ref
            or delivery.lineage_id != lineage.lineage_id
            or delivery.content_digest != lineage.content_digest
        ):
            raise RuntimeEvidenceError("provider delivery record does not match Project/run/lineage")

        successful = [item for item in delivery.actions if item.evidence.state is ProviderActionState.SUCCEEDED]
        if len(successful) != len(delivery.actions):
            raise RuntimeEvidenceError("provider delivery contains denial/failure and cannot prove success")
        github_commit = [
            item
            for item in successful
            if item.evidence.provider == "github" and item.evidence.action == "commit.write"
        ]
        github_pr = [
            item
            for item in successful
            if item.evidence.provider == "github" and item.evidence.action == "pull_request.create"
        ]
        preview = [
            item
            for item in successful
            if item.evidence.provider == "vercel"
            and item.evidence.action in {"preview.create", "preview.read"}
            and item.evidence.result_status in {"PREVIEW_READY", "PREVIEW_STATUS_READY"}
        ]
        if not github_commit or not github_pr or not preview or delivery.preview_status != "READY":
            raise RuntimeEvidenceError("verified-source delivery lacks GitHub publication or READY Vercel Preview")
        commit = github_commit[-1].evidence
        pr = github_pr[-1].evidence
        ready = preview[-1].evidence
        for evidence in (commit, pr):
            if evidence.lineage_id != lineage.lineage_id or evidence.lineage_digest != lineage.content_digest:
                raise RuntimeEvidenceError("GitHub publication does not bind the accepted lineage")
        if commit.source_revision != delivery.published_revision:
            raise RuntimeEvidenceError("published provider revision does not match commit evidence")
        if pr.source_revision != delivery.published_revision or pr.result_identity != delivery.pull_request_identity:
            raise RuntimeEvidenceError("pull request does not bind the published source revision")
        if ready.source_revision != delivery.published_revision or ready.result_identity != delivery.preview_deployment_id:
            raise RuntimeEvidenceError("Vercel Preview does not bind the published source revision")
        return delivery

    @staticmethod
    def _payload(attempt: EngineeringAttempt) -> dict[str, object]:
        try:
            payload = json.loads(attempt.evidence_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise RuntimeEvidenceError("persisted Engineering Attempt evidence is invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeEvidenceError("persisted Engineering Attempt evidence must be an object")
        lowered = {str(key).casefold() for key in payload}
        if lowered & _FORBIDDEN_EVIDENCE_KEYS:
            raise RuntimeEvidenceError("persisted Engineering Attempt evidence contains forbidden sensitive fields")
        assert_safe_payload(payload)
        return payload

    @staticmethod
    def _raw_digest(value: object, *, field: str) -> str:
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise RuntimeEvidenceError(f"{field} must be lowercase SHA-256")
        return value


__all__ = [
    "PersistedProviderActionFact",
    "PersistedVerifiedDelivery",
    "RuntimeAppBuilderEvidenceAdapter",
    "RuntimeEvidenceError",
    "RuntimeEvidenceSnapshot",
    "VerifiedSourceDeliveryReader",
]
