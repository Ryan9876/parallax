from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import time
from typing import Callable, Protocol

from parallax_api.execution_environment import execution_snapshot_id
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    ImplementationGeneration,
    ImplementationGenerationCoordinator,
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
from parallax_api.intelligence.router import AttemptRecord, ModelRouter
from parallax_api.evaluation.agent_judgment import (
    CandidateBinding,
    DimensionJudgment,
    DimensionPolicy,
    DimensionVerdict,
    EvaluationEvidenceReference,
    EvaluationOutcome,
    EvaluationRequest,
    EvaluatorJudgment,
    EvaluatorPolicy,
    ProtectedValidationEvidence,
    admit_evaluation_record,
    evaluate_candidate,
)
from parallax_api.models import EngineeringRun

from .agent_protocol import (
    AgentEvidenceReference,
    AgentIdentity,
    AgentLifecycleStatus,
    AgentResult,
    AgentSourceContext,
    EvidenceKind,
    MetricAvailability,
    MetricName,
    MetricObservation,
    MetricProvenanceKind,
)
from .agent_team_orchestration import (
    AdmittedAgent,
    AdmittedRoster,
    AssignmentEvidence,
    OrchestrationDisposition,
    OrchestrationLimits,
    TeamPlan,
    WorkGraph,
    WorkUnit,
    admit_assignment_result,
    build_team_plan,
    create_agent_task_request,
    observe_admitted_result,
    schedule_team_plan,
)
from .dependency_preparation import DependencyPreparationError, preparation_network_policy, run_dependency_preparation
from .domain import WorkflowStage
from .execution import ExecutionPolicyError, ProtectedCommandPolicy
from .implementation import ImplementationError, ImplementationRequest, SafeImplementationEngine
from .implementation_runtime import ProtectedImplementationRuntime
from .optimization_controller import (
    CompetitionCandidate,
    CompetitionContext,
    CompetitionDisposition,
    CompetitionPolicy,
    CompetitionRequest,
    CompetitionSignal,
    CompetitionTriggerDisposition,
    CompletionObservation,
    CompletionState,
    DevelopmentStrategy,
    EconomicMetricPolicy,
    EvidenceState,
    RoutingContext,
    RoutingMetricEvidence,
    RoutingMetricName,
    RoutingPolicy,
    RoutingProvenance,
    RoutingRequest,
    StrategyAdmissionSnapshot,
    StrategyKind,
    StrategyOutcomeEvidence,
    decide_candidate_competition,
    route_outcomes,
    should_compete,
)
from .patching import PatchError
from .runtime_composition import DurableLineageAllocator, EngineeringRuntimeComposition
from .sandbox_execution import (
    ProtectedCommandRegistry,
    VercelSandboxUnavailable,
    _bounded_evidence,
    _sanitized_provider_error,
)
from .service import EngineeringRunService
from .validation_toolchains import select_validation_profile
from .workspace_lineage import ProjectRunIdentity


AGENTIC_RUNTIME_VERSION = "agentic-runtime-v0.19.7"
AGENTIC_PLAN_PROGRAM_ID = "agentic-plan-v0.19.7"
_AGENT_POLICY_VERSION = "1.0.0"
_SANDBOX_SOURCE_ROOT = "/vercel/sandbox"
_MAX_CANDIDATE_FILES = 2000
_MAX_CANDIDATE_BYTES = 64_000_000
_MODEL_ORDER = (
    "openai/gpt-5.6-luna",
    "openai/gpt-5.6-terra",
    "openai/gpt-5.6-sol",
)


class AgenticRuntimeError(ValueError):
    """Fail-closed Wave 6 runtime activation error."""


class CandidateValidationFailure(AgenticRuntimeError):
    """Bounded protected-candidate rejection with sanitized diagnostics only."""

    def __init__(self, message: str, *, diagnostic_evidence: dict[str, object]) -> None:
        super().__init__(message)
        self.diagnostic_evidence = diagnostic_evidence


class CandidateAdmissionFailure(AgenticRuntimeError):
    """Finite candidate-admission phase failure without arbitrary exception text."""

    def __init__(self, message: str, *, diagnostic_evidence: dict[str, object]) -> None:
        super().__init__(message)
        self.diagnostic_evidence = diagnostic_evidence


@dataclass(frozen=True, slots=True)
class CandidateValidationResult:
    content_digest: str
    file_count: int
    total_bytes: int
    validation_profile_id: str
    validation_profile_digest: str
    stage_evidence: tuple[tuple[str, dict[str, object]], ...]

    @property
    def passed(self) -> bool:
        return bool(self.stage_evidence) and all(
            evidence.get("protected_success") is True
            for _, evidence in self.stage_evidence
        )

    @property
    def duration_seconds(self) -> float:
        return sum(
            max(0, int(evidence.get("duration_ms") or 0))
            for _, evidence in self.stage_evidence
        ) / 1000.0


def _sha256_value(value: object) -> str | None:
    if (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    ):
        return value
    return None


def _candidate_validation_failure_diagnostic(
    candidate_id: str,
    validation: CandidateValidationResult,
) -> dict[str, object] | None:
    """Project only non-secret protected-stage identity for a failed candidate."""

    failed = next(
        (item for item in validation.stage_evidence if item[1].get("protected_success") is not True),
        None,
    )
    if failed is None:
        return None
    stage, evidence = failed
    if stage not in {WorkflowStage.BUILD.value, WorkflowStage.TEST.value, WorkflowStage.VERIFY.value}:
        return None

    raw_exit_code = evidence.get("exit_code")
    exit_code = (
        raw_exit_code
        if isinstance(raw_exit_code, int) and not isinstance(raw_exit_code, bool)
        else None
    )
    diagnostic: dict[str, object] = {
        "candidate_id": candidate_id,
        "failed_stage": stage,
        "protected_success": False,
        "exit_code_present": exit_code is not None,
        "exit_code": exit_code,
        "timed_out": evidence.get("timed_out") is True,
        "candidate_is_canonical_lineage": False,
        "accepts_source_lineage": False,
        "source_lineage_accepted": False,
        "production_deployed": False,
    }
    for key in ("invocation_digest", "stdout_digest", "stderr_digest"):
        digest = _sha256_value(evidence.get(key))
        if digest is not None:
            diagnostic[key] = digest
    content_digest = _sha256_value(validation.content_digest)
    if content_digest is not None:
        diagnostic["candidate_content_digest"] = content_digest
    for key, limit in (("tool_id", 80), ("execution_snapshot_id", 180), ("validation_profile_id", 80), ("validation_profile_digest", 80)):
        value = evidence.get(key)
        if (
            isinstance(value, str)
            and 0 < len(value) <= limit
            and value.strip() == value
            and all(ord(ch) >= 32 for ch in value)
        ):
            diagnostic[key] = value
    return diagnostic


_CANDIDATE_ADMISSION_PHASES = frozenset(
    {
        "PROPOSAL_ASSEMBLY",
        "DISPOSABLE_CANDIDATE_VALIDATION",
        "CANDIDATE_BINDING",
        "INDEPENDENT_EVALUATION",
        "ROUTING_CONTEXT",
        "STRATEGY_CONSTRUCTION",
        "ROUTING_OUTCOME",
    }
)


def _candidate_admission_failure_kind(exc: Exception) -> str:
    if isinstance(exc, ImplementationError):
        return "SAFE_IMPLEMENTATION_ERROR"
    if isinstance(exc, PatchError):
        return "PATCH_ERROR"
    if isinstance(exc, OSError):
        return "OS_BOUNDARY_ERROR"
    if isinstance(exc, AgenticRuntimeError):
        return "AGENTIC_CONTRACT_ERROR"
    return "VALUE_CONTRACT_ERROR"


def _candidate_admission_failure_diagnostic(
    candidate_id: str,
    phase: str,
    exc: Exception,
) -> dict[str, object]:
    if phase not in _CANDIDATE_ADMISSION_PHASES:
        raise AgenticRuntimeError("candidate admission diagnostic phase is not server-owned")
    return {
        "candidate_id": candidate_id,
        "phase": phase,
        "failure_kind": _candidate_admission_failure_kind(exc),
        "candidate_is_canonical_lineage": False,
        "accepts_source_lineage": False,
        "source_lineage_accepted": False,
        "engineering_run_transitioned": False,
        "review_completed": False,
        "production_deployed": False,
    }


@contextmanager
def _candidate_admission_phase(candidate_id: str, phase: str):
    if phase not in _CANDIDATE_ADMISSION_PHASES:
        raise AgenticRuntimeError("candidate admission phase is not server-owned")
    try:
        yield
    except CandidateAdmissionFailure:
        raise
    except (ImplementationError, PatchError, OSError, AgenticRuntimeError, ValueError) as exc:
        raise CandidateAdmissionFailure(
            f"bounded candidate admission failed during {phase}",
            diagnostic_evidence=_candidate_admission_failure_diagnostic(candidate_id, phase, exc),
        ) from exc


class CandidateValidationExecutor(Protocol):
    def validate_candidate(
        self,
        workspace_root: Path,
        *,
        operation_key: str,
    ) -> CandidateValidationResult: ...


class VercelCandidateValidationExecutor:
    """Validate a disposable candidate before canonical source mutation.

    The candidate is a copy of a server-resolved accepted workspace. It is
    transferred to the same pinned, source-free Vercel execution snapshot used
    by protected same-lineage execution. The sandbox is deny-all and receives no
    application environment. No candidate validation call can accept lineage.
    """

    def __init__(
        self,
        *,
        registry: ProtectedCommandRegistry | None = None,
        policy: ProtectedCommandPolicy | None = None,
        project_id: str | None = None,
        snapshot_id: str | None = None,
    ) -> None:
        self.registry = registry or ProtectedCommandRegistry()
        self.policy = policy or ProtectedCommandPolicy()
        self.project_id = project_id or os.getenv("VERCEL_PROJECT_ID")
        try:
            self.snapshot_id = execution_snapshot_id(snapshot_id)
        except ValueError as exc:
            raise AgenticRuntimeError("server-owned execution snapshot identity is invalid") from exc

    @staticmethod
    def _sdk():
        try:
            from vercel.api import session
            from vercel.sandbox import NetworkPolicy, SnapshotSource
            from vercel.sandbox import sync as sandbox
        except ImportError as exc:
            raise VercelSandboxUnavailable("Vercel Sandbox SDK is not installed") from exc
        return session, NetworkPolicy, SnapshotSource, sandbox

    @staticmethod
    def _sandbox_cwd(working_directory: str) -> str:
        pure = PurePosixPath(working_directory)
        if pure.is_absolute() or any(part == ".." for part in pure.parts):
            raise AgenticRuntimeError("protected candidate working directory escaped source root")
        if working_directory in {"", "."}:
            return _SANDBOX_SOURCE_ROOT
        clean = pure.as_posix().removeprefix("./")
        return _SANDBOX_SOURCE_ROOT if clean in {"", "."} else f"{_SANDBOX_SOURCE_ROOT}/{clean}"

    @staticmethod
    def _source_files(root: Path) -> tuple[tuple[str, bytes], ...]:
        if not root.is_absolute() or root.is_symlink() or not root.is_dir():
            raise AgenticRuntimeError("candidate workspace root is invalid")
        resolved_root = root.resolve(strict=True)
        values: list[tuple[str, bytes]] = []
        total = 0
        for candidate in sorted(root.rglob("*")):
            if candidate.is_symlink():
                raise AgenticRuntimeError("candidate workspace contains a symlink")
            if candidate.is_dir():
                continue
            if not candidate.is_file():
                raise AgenticRuntimeError("candidate workspace contains a special file")
            resolved = candidate.resolve(strict=True)
            if not resolved.is_relative_to(resolved_root):
                raise AgenticRuntimeError("candidate workspace escaped its server-owned root")
            relative = candidate.relative_to(root).as_posix()
            pure = PurePosixPath(relative)
            if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
                raise AgenticRuntimeError("candidate workspace contains invalid source path")
            content = candidate.read_bytes()
            total += len(content)
            if len(values) + 1 > _MAX_CANDIDATE_FILES or total > _MAX_CANDIDATE_BYTES:
                raise AgenticRuntimeError("candidate workspace exceeds protected validation bounds")
            values.append((relative, content))
        if not values:
            raise AgenticRuntimeError("candidate workspace is empty")
        return tuple(values)

    @staticmethod
    def _content_digest(files: tuple[tuple[str, bytes], ...]) -> str:
        projection = [
            {
                "path": path,
                "sha256": sha256(content).hexdigest(),
                "size": len(content),
            }
            for path, content in files
        ]
        return sha256(
            json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _transfer_source(instance: object, files: tuple[tuple[str, bytes], ...]) -> None:
        filesystem = getattr(instance, "fs", None)
        if filesystem is None:
            raise AgenticRuntimeError("sandbox filesystem API is unavailable")
        filesystem.mkdir("sandbox", cwd="/vercel", recursive=True)
        with filesystem.batch(cwd=_SANDBOX_SOURCE_ROOT) as batch:
            for path, content in files:
                batch.write_bytes(path, content)

    def validate_candidate(
        self,
        workspace_root: Path,
        *,
        operation_key: str,
    ) -> CandidateValidationResult:
        profile = select_validation_profile(workspace_root)
        files = self._source_files(workspace_root)
        content_digest = self._content_digest(files)
        total_bytes = sum(len(content) for _, content in files)
        if not self.project_id:
            raise AgenticRuntimeError("Vercel project identity is unavailable for candidate validation")

        session, NetworkPolicy, SnapshotSource, sandbox = self._sdk()
        snapshot_source = SnapshotSource(snapshot_id=self.snapshot_id)
        stage_evidence: list[tuple[str, dict[str, object]]] = []
        preparation_seconds = (
            profile.preparation.probe_timeout_seconds + profile.preparation.timeout_seconds
            if profile.preparation is not None
            else 0
        )
        max_execution_seconds = preparation_seconds + sum(
            profile.spec_for(stage, operation_key=f"{operation_key}:{stage.value.lower()}").timeout_seconds
            for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY)
        ) + 60
        with session():
            with sandbox.create_sandbox(
                project_id=self.project_id,
                source=snapshot_source,
                execution_time_limit=max_execution_seconds,
                persistent=False,
                network_policy=preparation_network_policy(NetworkPolicy, profile),
                env={},
                destroy=True,
                tags={"parallax": "agentic-candidate-validation"},
            ) as instance:
                if getattr(instance, "current_snapshot_id", None) != self.snapshot_id:
                    raise AgenticRuntimeError("candidate sandbox did not restore the pinned execution snapshot")
                self._transfer_source(instance, files)
                try:
                    preparation_evidence = run_dependency_preparation(
                        instance,
                        NetworkPolicy,
                        profile,
                        sandbox_cwd=self._sandbox_cwd,
                    )
                except DependencyPreparationError as exc:
                    failure_spec = profile.spec_for(
                        WorkflowStage.BUILD,
                        operation_key=f"{operation_key[:120]}:candidate:prepare",
                    )
                    evidence = _bounded_evidence(
                        failure_spec,
                        exit_code=None,
                        duration_ms=int(exc.evidence.get("dependency_preparation_duration_ms") or 0),
                        stdout="",
                        stderr=exc.code,
                    )
                    evidence.update(
                        {
                            **exc.evidence,
                            "candidate_content_digest": content_digest,
                            "candidate_file_count": len(files),
                            "candidate_total_bytes": total_bytes,
                            "validation_profile_id": profile.profile_id.value,
                            "validation_profile_digest": profile.digest,
                            "execution_snapshot_id": self.snapshot_id,
                            "execution_snapshot_verified": True,
                            "network_policy": "deny-all" if exc.evidence.get("validation_network_locked") is True else "prepare-bounded",
                            "candidate_is_canonical_lineage": False,
                            "accepts_source_lineage": False,
                            **preparation_evidence,
                        }
                    )
                    stage_evidence.append((WorkflowStage.BUILD.value, evidence))
                    return CandidateValidationResult(
                        content_digest=content_digest,
                        file_count=len(files),
                        total_bytes=total_bytes,
                        validation_profile_id=profile.profile_id.value,
                        validation_profile_digest=profile.digest,
                        stage_evidence=tuple(stage_evidence),
                    )
                if preparation_evidence.get("validation_network_locked") is not True:
                    raise AgenticRuntimeError("validation network lock was not proven")
                for stage in (WorkflowStage.BUILD, WorkflowStage.TEST, WorkflowStage.VERIFY):
                    spec = profile.spec_for(
                        stage,
                        operation_key=f"{operation_key[:120]}:candidate:{stage.value.lower()}",
                    )
                    self.policy.validate(spec)
                    registered = profile.spec_for(stage, operation_key=spec.operation_key)
                    if spec != registered:
                        raise ExecutionPolicyError("candidate execution spec drifted from protected validation profile")
                    command, args = profile.invocation_for(stage)
                    started = time.monotonic()
                    try:
                        result = instance.run_process(
                            command,
                            list(args),
                            cwd=self._sandbox_cwd(spec.working_directory),
                            env={},
                            kill_after=spec.timeout_seconds,
                            capture_output=True,
                        )
                        evidence = _bounded_evidence(
                            spec,
                            exit_code=result.returncode,
                            duration_ms=int((time.monotonic() - started) * 1000),
                            stdout=result.stdout or "",
                            stderr=result.stderr or "",
                        )
                    except Exception as exc:
                        evidence = _bounded_evidence(
                            spec,
                            exit_code=None,
                            duration_ms=int((time.monotonic() - started) * 1000),
                            stdout="",
                            stderr=_sanitized_provider_error(exc),
                            timed_out="timeout" in type(exc).__name__.lower(),
                        )
                    evidence.update(
                        {
                            "candidate_content_digest": content_digest,
                            "candidate_file_count": len(files),
                            "candidate_total_bytes": total_bytes,
                            "validation_profile_id": profile.profile_id.value,
                            "validation_profile_digest": profile.digest,
                            "execution_snapshot_id": self.snapshot_id,
                            "execution_snapshot_verified": True,
                            "network_policy": "deny-all",
                            "candidate_is_canonical_lineage": False,
                            "accepts_source_lineage": False,
                        }
                    )
                    stage_evidence.append((stage.value, evidence))
                    if evidence.get("protected_success") is not True:
                        break

        return CandidateValidationResult(
            content_digest=content_digest,
            file_count=len(files),
            total_bytes=total_bytes,
            validation_profile_id=profile.profile_id.value,
            validation_profile_digest=profile.digest,
            stage_evidence=tuple(stage_evidence),
        )


@dataclass(frozen=True, slots=True)
class ProducedCandidate:
    candidate_id: str
    plan: TeamPlan
    proposal: ImplementationProposal
    attempts: tuple[AttemptRecord, ...]
    model_labels: tuple[str, ...]
    result_digests: tuple[str, ...]
    task_digests: tuple[str, ...]
    validation: CandidateValidationResult
    binding: CandidateBinding
    protected_validation: ProtectedValidationEvidence
    evaluation_record: object
    strategy: DevelopmentStrategy
    routing_outcome: StrategyOutcomeEvidence

    @property
    def proposal_digest(self) -> str:
        return self.proposal.digest()


class HostedImplementationAgent:
    """Production-capable S1 adapter over the existing implementation transport."""

    def __init__(self, model: str) -> None:
        self.model = model
        model_label = model.replace("/", ".")
        suffix = model.split("/")[-1]
        self.identity = AgentIdentity(
            agent_id=f"hosted-{suffix}-implementation",
            agent_version=_AGENT_POLICY_VERSION,
            adapter_id="protected-implementation-generation",
            adapter_version=_AGENT_POLICY_VERSION,
            provider_kind="openai",
            declared_work_kinds=("implementation",),
            declared_capabilities=("bounded-source-evidence",),
            model_runtime_label=model_label,
        )
        self.coordinator = ImplementationGenerationCoordinator(
            router=ModelRouter((model,))
        )

    def describe(self) -> AgentIdentity:
        return self.identity

    def generate(
        self,
        task,
        request: ImplementationGenerationRequest,
        *,
        proposal_validator: Callable[[ImplementationProposal], bool],
    ) -> tuple[AgentResult, ImplementationGeneration]:
        started = time.monotonic()
        generation = self.coordinator.generate_sync(
            request,
            proposal_validator=proposal_validator,
        )
        proposal = generation.proposal
        result = AgentResult(
            binding=task.binding,
            agent=self.identity,
            status=AgentLifecycleStatus.COMPLETED,
            reason_code=None,
            summary="hosted implementation agent produced bounded source proposal evidence",
            claimed_acceptance_ids=task.binding.acceptance_ids,
            changed_paths=tuple(sorted(item.path for item in proposal.patches)),
            evidence_refs=(
                AgentEvidenceReference(
                    EvidenceKind.ARTIFACT,
                    f"proposal:{proposal.digest()[:32]}",
                    proposal.digest(),
                ),
            ),
            metrics=(
                MetricObservation(
                    metric=MetricName.DURATION,
                    availability=MetricAvailability.OBSERVED,
                    source="parallax-agent-adapter",
                    value=max(0.0, time.monotonic() - started),
                    unit="seconds",
                    provenance_kind=MetricProvenanceKind.PARALLAX,
                    provenance_ref=f"agent:{task.binding.attempt_id}",
                ),
                MetricObservation(
                    metric=MetricName.COST,
                    availability=MetricAvailability.UNAVAILABLE,
                    source="provider-usage-unavailable",
                ),
            ),
        )
        return result, generation


class AgenticControlPlane:
    program_id = AGENTIC_PLAN_PROGRAM_ID

    def __init__(
        self,
        service: EngineeringRunService,
        allocator: DurableLineageAllocator,
        *,
        adapters: tuple[HostedImplementationAgent, ...] | None = None,
        candidate_validator: CandidateValidationExecutor | None = None,
        implementation_engine: SafeImplementationEngine | None = None,
    ) -> None:
        self.service = service
        self.allocator = allocator
        self.adapters = adapters or tuple(HostedImplementationAgent(model) for model in _MODEL_ORDER)
        if not self.adapters:
            raise AgenticRuntimeError("agentic runtime requires at least one production adapter")
        if any(adapter.describe().provider_kind == "reference" for adapter in self.adapters):
            raise AgenticRuntimeError("reference adapters cannot be admitted into production agentic runtime")
        identities = [adapter.describe().digest for adapter in self.adapters]
        if len(set(identities)) != len(identities):
            raise AgenticRuntimeError("production agent registry contains duplicate identity")
        self.candidate_validator = candidate_validator or VercelCandidateValidationExecutor()
        self.implementation_engine = implementation_engine or SafeImplementationEngine()
        self.orchestration_limits = OrchestrationLimits(
            max_team_size=min(3, len(self.adapters)),
            max_concurrency=min(3, len(self.adapters)),
            max_reassignments_per_work_unit=2,
            max_replans=3,
            max_no_progress=3,
        )
        self.routing_policy = RoutingPolicy(
            policy_id="agentic-outcome-routing",
            policy_version=_AGENT_POLICY_VERSION,
            permitted_strategy_kinds=(StrategyKind.SINGLE_AGENT, StrategyKind.TEAM),
            metric_policies=(
                EconomicMetricPolicy(
                    RoutingMetricName.DURATION,
                    weight=0.25,
                    ceiling=900.0,
                    required=False,
                    allow_estimated=False,
                    missing_penalty=1.0,
                ),
            ),
            quality_floor=1.0,
            confidence_floor=1.0,
            quality_weight=0.75,
            max_sequence_age=10,
            minimum_comparable_metrics=1,
            human_required_on_insufficient=True,
            max_explorations=0,
        )
        self.competition_policy = CompetitionPolicy(
            policy_id="agentic-candidate-competition",
            policy_version=_AGENT_POLICY_VERSION,
            max_candidates=2,
            minimum_candidates_for_comparison=2,
            required_candidate_count=1,
            permitted_strategy_kinds=(StrategyKind.SINGLE_AGENT, StrategyKind.TEAM),
            eligibility_quality_floor=1.0,
            winner_quality_floor=1.0,
            winner_confidence_floor=1.0,
            minimum_expected_quality_gain=0.05,
            max_extra_cost=None,
            max_extra_duration=None,
            max_routing_sequence_age=10,
            economic_metric_policies=(
                EconomicMetricPolicy(
                    RoutingMetricName.DURATION,
                    weight=1.0,
                    ceiling=900.0,
                    required=False,
                ),
            ),
            max_synthesis_attempts=0,
            max_synthesis_parents=2,
            max_rounds=2,
            max_no_progress_rounds=1,
            synthesis_budget_class="bounded",
            human_required_on_ambiguity=True,
        )

    @property
    def _policy_digest(self) -> str:
        return _digest(
            {
                "version": AGENTIC_RUNTIME_VERSION,
                "team_selection": "smallest-capable-team",
                "decomposition": "clear-independent-domains-only",
                "competition": self.competition_policy.digest,
                "routing": self.routing_policy.digest,
            }
        )

    @property
    def _roster(self) -> AdmittedRoster:
        return AdmittedRoster(
            tuple(
                AdmittedAgent(
                    adapter.describe(),
                    admitted_work_kinds=("implementation",),
                    admitted_capabilities=("bounded-source-evidence",),
                )
                for adapter in self.adapters
            )
        )

    @staticmethod
    def _acceptance(run: EngineeringRun, service: EngineeringRunService) -> tuple[dict[str, str], ...]:
        raw = service.acceptance_map_for_run(run)
        result = tuple(
            {"id": str(item["id"]), "text": str(item["text"])}
            for item in raw
        )
        if not result:
            raise AgenticRuntimeError("agentic runtime requires protected acceptance criteria")
        return result

    @staticmethod
    def _domain(text: str) -> str | None:
        value = text.casefold()
        groups = (
            (
                "client",
                (
                    " ui ",
                    "user interface",
                    "screen",
                    "button",
                    "mobile",
                    "client",
                    "frontend",
                    "browser",
                    "accessibility",
                    "layout",
                    "visual",
                ),
            ),
            (
                "server",
                (
                    " api ",
                    "endpoint",
                    "route",
                    "server",
                    "backend",
                    "http ",
                    "request",
                    "response",
                    "service",
                ),
            ),
            (
                "data",
                (
                    "database",
                    "persistence",
                    "persist",
                    "migration",
                    "schema",
                    "repository",
                    "storage",
                    "durable",
                ),
            ),
        )
        padded = f" {value} "
        hits = [
            name
            for name, tokens in groups
            if any(token in padded for token in tokens)
        ]
        return hits[0] if len(hits) == 1 else None

    def _work_graph(
        self,
        acceptance: tuple[dict[str, str], ...],
        *,
        source_digest: str,
    ) -> WorkGraph:
        source_ref = AgentEvidenceReference(
            EvidenceKind.SOURCE,
            "source:accepted-base",
            source_digest,
        )
        classified = [(item, self._domain(item["text"])) for item in acceptance]
        domains = {domain for _, domain in classified if domain is not None}
        can_split = (
            len(domains) >= 2
            and all(domain is not None for _, domain in classified)
            and len(acceptance) >= 2
        )
        if not can_split:
            return WorkGraph(
                approved_acceptance_ids=tuple(item["id"] for item in acceptance),
                units=(
                    WorkUnit(
                        unit_id="implementation",
                        work_kind="implementation",
                        acceptance_ids=tuple(item["id"] for item in acceptance),
                        required_capabilities=("bounded-source-evidence",),
                        coordination_domains=("source",),
                        requires_canonical_mutation=False,
                        context_refs=(source_ref,),
                    ),
                ),
            )

        units = []
        for domain in sorted(domains):
            ids = tuple(item["id"] for item, item_domain in classified if item_domain == domain)
            units.append(
                WorkUnit(
                    unit_id=f"implementation-{domain}",
                    work_kind="implementation",
                    acceptance_ids=ids,
                    required_capabilities=("bounded-source-evidence",),
                    coordination_domains=(domain,),
                    requires_canonical_mutation=False,
                    context_refs=(source_ref,),
                )
            )
        return WorkGraph(
            approved_acceptance_ids=tuple(item["id"] for item in acceptance),
            units=tuple(units),
        )

    def _lineage(self, run: EngineeringRun):
        if not run.project_id:
            raise AgenticRuntimeError("agentic runtime requires Project-bound run")
        identity = ProjectRunIdentity(project_id=run.project_id, run_id=run.id)
        lineage = self.allocator.current_lineage(identity)
        if lineage.project_id != run.project_id or lineage.run_id != run.id:
            raise AgenticRuntimeError("accepted source lineage identity mismatch")
        return lineage

    def _team_plan(
        self,
        run: EngineeringRun,
        acceptance: tuple[dict[str, str], ...],
        *,
        source_digest: str,
        roster: AdmittedRoster | None = None,
    ) -> TeamPlan:
        graph = self._work_graph(acceptance, source_digest=source_digest)
        active_roster = roster or self._roster
        decision = build_team_plan(
            project_id=run.project_id or "",
            run_id=run.id,
            work_specification_id=run.work_specification_id or "",
            work_specification_revision=int(run.work_specification_revision or 0),
            work_specification_digest=run.work_specification_digest or "",
            graph=graph,
            roster=active_roster,
            policy_digest=self._policy_digest,
            limits=self.orchestration_limits,
        )
        if decision.disposition is not OrchestrationDisposition.READY or decision.plan is None:
            raise AgenticRuntimeError(
                f"no live compatible agent strategy can be admitted: {decision.reason_code}"
            )
        return decision.plan

    def plan(
        self,
        *,
        run: EngineeringRun,
        operation_key: str,
    ) -> dict[str, object]:
        if not operation_key:
            raise AgenticRuntimeError("agentic PLAN operation identity is required")
        acceptance = self._acceptance(run, self.service)
        lineage = self._lineage(run)
        plan = self._team_plan(
            run,
            acceptance,
            source_digest=lineage.content_digest,
        )
        graph = plan.graph
        return {
            "agentic_runtime_version": AGENTIC_RUNTIME_VERSION,
            "decision_kind": "SERVER_OWNED_AGENTIC_PLAN",
            "project_id": run.project_id,
            "run_id": run.id,
            "work_specification_id": run.work_specification_id,
            "work_specification_revision": run.work_specification_revision,
            "work_specification_digest": run.work_specification_digest,
            "acceptance_ids_covered": list(graph.approved_acceptance_ids),
            "base_source_lineage_ref": lineage.lineage_id,
            "base_source_content_digest": lineage.content_digest,
            "orchestration_policy_digest": self._policy_digest,
            "work_graph_digest": graph.digest,
            "roster_digest": plan.roster.digest,
            "orchestration_identity_digest": plan.identity.digest,
            "team_plan_id": plan.plan_id,
            "selected_agent_digests": list(plan.selected_agent_digests),
            "selected_agent_count": len(plan.selected_agent_digests),
            "work_units": [
                {
                    "unit_id": unit.unit_id,
                    "acceptance_ids": list(unit.acceptance_ids),
                    "coordination_domains": list(unit.coordination_domains),
                }
                for unit in graph.units
            ],
            "routing_policy_digest": self.routing_policy.digest,
            "competition_policy_digest": self.competition_policy.digest,
            "operator_selected_agents": False,
            "agent_outputs_accept_source_lineage": False,
            "canonical_source_writer_count": 1,
            "review_authority": False,
            "production_deployment_authority": False,
        }

    @staticmethod
    def _plan_attempt(run: EngineeringRun) -> dict[str, object]:
        for attempt in reversed(run.attempts):
            if attempt.stage == WorkflowStage.PLAN.value and attempt.status == "PASSED":
                try:
                    value = json.loads(attempt.evidence_json)
                except (TypeError, json.JSONDecodeError) as exc:
                    raise AgenticRuntimeError("persisted agentic PLAN evidence is malformed") from exc
                if value.get("agentic_runtime_version") != AGENTIC_RUNTIME_VERSION:
                    raise AgenticRuntimeError("IMPLEMENT requires persisted agentic PLAN evidence")
                return value
        raise AgenticRuntimeError("IMPLEMENT requires a successful agentic PLAN attempt")

    def _verify_plan_evidence(
        self,
        *,
        run: EngineeringRun,
        base_source_lineage_ref: str,
        source_content_digest: str,
    ) -> TeamPlan:
        acceptance = self._acceptance(run, self.service)
        plan = self._team_plan(run, acceptance, source_digest=source_content_digest)
        evidence = self._plan_attempt(run)
        expected = {
            "project_id": run.project_id,
            "run_id": run.id,
            "work_specification_id": run.work_specification_id,
            "work_specification_revision": run.work_specification_revision,
            "work_specification_digest": run.work_specification_digest,
            "base_source_lineage_ref": base_source_lineage_ref,
            "base_source_content_digest": source_content_digest,
            "orchestration_policy_digest": self._policy_digest,
            "work_graph_digest": plan.graph.digest,
            "roster_digest": plan.roster.digest,
            "orchestration_identity_digest": plan.identity.digest,
            "team_plan_id": plan.plan_id,
            "selected_agent_digests": list(plan.selected_agent_digests),
            "routing_policy_digest": self.routing_policy.digest,
            "competition_policy_digest": self.competition_policy.digest,
        }
        for key, value in expected.items():
            if evidence.get(key) != value:
                raise AgenticRuntimeError(f"persisted agentic PLAN evidence drifted at {key}")
        return plan

    @staticmethod
    def _copy_candidate_workspace(source: Path, target: Path) -> None:
        if not source.is_absolute() or source.is_symlink() or not source.is_dir():
            raise AgenticRuntimeError("protected implementation workspace is invalid")
        resolved = source.resolve(strict=True)
        for candidate in source.rglob("*"):
            if candidate.is_symlink():
                raise AgenticRuntimeError("protected source contains symlink")
            if candidate.exists() and not candidate.is_file() and not candidate.is_dir():
                raise AgenticRuntimeError("protected source contains special file")
            if candidate.is_file() and not candidate.resolve(strict=True).is_relative_to(resolved):
                raise AgenticRuntimeError("protected source escaped server-owned workspace")
        shutil.copytree(source, target, dirs_exist_ok=False)

    @staticmethod
    def _subrequest(
        request: ImplementationGenerationRequest,
        acceptance_ids: tuple[str, ...],
        *,
        alternative_round: int,
    ) -> ImplementationGenerationRequest:
        accepted = {item.id: item for item in request.acceptance}
        requirements = tuple(accepted[item] for item in acceptance_ids)
        constraints = request.constraints
        if alternative_round > 1:
            constraints = (
                *constraints,
                "Produce an independent complete alternative for this bounded candidate round; do not rely on prior candidate output.",
            )
        return ImplementationGenerationRequest(
            work_specification_id=request.work_specification_id,
            work_specification_revision=request.work_specification_revision,
            work_specification_digest=request.work_specification_digest,
            title=request.title,
            objective=request.objective,
            constraints=constraints,
            acceptance=requirements,
            source_context=request.source_context,
        )

    def _adapter(self, digest: str) -> HostedImplementationAgent:
        for adapter in self.adapters:
            if adapter.describe().digest == digest:
                return adapter
        raise AgenticRuntimeError("team plan selected an adapter outside production registry")

    def _proposal_for_plan(
        self,
        plan: TeamPlan,
        request: ImplementationGenerationRequest,
        *,
        proposal_validator: Callable[[ImplementationProposal], bool],
        alternative_round: int,
    ) -> tuple[
        ImplementationProposal,
        tuple[AttemptRecord, ...],
        tuple[str, ...],
        tuple[str, ...],
        tuple[str, ...],
    ]:
        completed: set[str] = set()
        patches = []
        covered: list[str] = []
        attempts: list[AttemptRecord] = []
        models: list[str] = []
        result_digests: list[str] = []
        task_digests: list[str] = []
        seen_paths: set[str] = set()

        while len(completed) < len(plan.graph.units):
            schedule = schedule_team_plan(plan, completed_work_units=tuple(completed))
            ready = schedule.ready
            if not ready:
                raise AgenticRuntimeError("agent team schedule made no progress")
            progress = False
            for assignment in ready:
                if assignment.work_unit_id in completed:
                    continue
                unit = plan.graph.get(assignment.work_unit_id)
                task = create_agent_task_request(
                    plan,
                    assignment,
                    source_context=AgentSourceContext(
                        lineage_id=request.source_context.content_digest,
                        revision_id=f"source:{request.source_context.content_digest[:24]}",
                    ),
                )
                subrequest = self._subrequest(
                    request,
                    unit.acceptance_ids,
                    alternative_round=alternative_round,
                )
                adapter = self._adapter(assignment.agent_identity_digest or "")
                result, generation = adapter.generate(
                    task,
                    subrequest,
                    proposal_validator=proposal_validator,
                )
                admission = admit_assignment_result(
                    plan,
                    assignment,
                    expected_task=task,
                    result=result,
                    current_generation=assignment.generation,
                )
                if not admission.admitted:
                    raise AgenticRuntimeError(
                        f"agent result admission failed: {admission.reason_code}"
                    )
                observe_admitted_result(
                    plan,
                    assignment,
                    admission=admission,
                    result=result,
                )
                if result.status is not AgentLifecycleStatus.COMPLETED:
                    raise AgenticRuntimeError(
                        f"admitted agent did not complete work: {result.reason_code}"
                    )
                if tuple(generation.proposal.acceptance_ids_covered) != unit.acceptance_ids:
                    raise AgenticRuntimeError("agent proposal acceptance ownership drifted")
                for patch in generation.proposal.patches:
                    if patch.path in seen_paths:
                        raise AgenticRuntimeError(
                            "multi-agent proposal overlap requires human coordination"
                        )
                    seen_paths.add(patch.path)
                    patches.append(patch)
                covered.extend(unit.acceptance_ids)
                attempts.extend(generation.attempts)
                models.append(generation.model)
                result_digests.append(result.digest)
                task_digests.append(task.digest)
                completed.add(unit.unit_id)
                progress = True
            if not progress:
                raise AgenticRuntimeError("agent team schedule stalled without protected progress")

        ordered_coverage = request.required_acceptance_ids
        if set(covered) != set(ordered_coverage) or len(covered) != len(ordered_coverage):
            raise AgenticRuntimeError("agent team did not cover exact protected acceptance contract")
        proposal = ImplementationProposal(
            acceptance_ids_covered=list(ordered_coverage),
            patches=patches,
        )
        if not validate_implementation_proposal(proposal, ordered_coverage):
            raise AgenticRuntimeError("combined agent proposal failed exact acceptance validation")
        return (
            proposal,
            tuple(attempts),
            tuple(models),
            tuple(result_digests),
            tuple(task_digests),
        )

    @staticmethod
    def _implementation_request(proposal: ImplementationProposal) -> ImplementationRequest:
        return ProtectedImplementationRuntime._implementation_request(proposal)

    def _candidate_validation(
        self,
        base_workspace: Path,
        proposal: ImplementationProposal,
        *,
        operation_key: str,
        candidate_id: str,
    ) -> CandidateValidationResult:
        with tempfile.TemporaryDirectory(prefix=f"parallax-{candidate_id}-") as temporary:
            target = Path(temporary) / "candidate"
            self._copy_candidate_workspace(base_workspace, target)
            try:
                self.implementation_engine.apply(
                    target,
                    self._implementation_request(proposal),
                )
            except (ImplementationError, PatchError, OSError) as exc:
                raise AgenticRuntimeError("candidate proposal failed safe disposable application") from exc
            return self.candidate_validator.validate_candidate(
                target,
                operation_key=f"{operation_key[:110]}:{candidate_id}",
            )

    @staticmethod
    def _validation_refs(
        project_id: str,
        candidate_id: str,
        validation: CandidateValidationResult,
    ) -> tuple[EvaluationEvidenceReference, ...]:
        refs = []
        for stage, evidence in validation.stage_evidence:
            refs.append(
                EvaluationEvidenceReference(
                    kind=EvidenceKind.TEST,
                    reference_id=f"candidate:{candidate_id}:{stage.lower()}",
                    digest=_digest(
                        {
                            "stage": stage,
                            "protected_success": evidence.get("protected_success") is True,
                            "tool_id": evidence.get("tool_id"),
                            "invocation_digest": evidence.get("invocation_digest"),
                            "stdout_digest": evidence.get("stdout_digest"),
                            "stderr_digest": evidence.get("stderr_digest"),
                            "exit_code": evidence.get("exit_code"),
                            "timed_out": bool(evidence.get("timed_out")),
                            "candidate_content_digest": validation.content_digest,
                        }
                    ),
                    project_id=project_id,
                )
            )
        return tuple(refs)

    def _evaluation(
        self,
        *,
        run: EngineeringRun,
        candidate_id: str,
        candidate_binding: CandidateBinding,
        validation: CandidateValidationResult,
        producer_digests: tuple[str, ...],
    ) -> tuple[ProtectedValidationEvidence, object]:
        refs = self._validation_refs(run.project_id or "", candidate_id, validation)
        stages = {stage for stage, _ in validation.stage_evidence}
        complete_stages = {
            WorkflowStage.BUILD.value,
            WorkflowStage.TEST.value,
            WorkflowStage.VERIFY.value,
        }
        passed = validation.passed and stages == complete_stages
        failures = () if passed else ("PROTECTED_CANDIDATE_VALIDATION_FAILED",)
        protected = ProtectedValidationEvidence(
            candidate=candidate_binding,
            validation_id=f"validation:{candidate_id}",
            passed=passed,
            acceptance_ids=candidate_binding.acceptance_ids,
            evidence_refs=refs,
            failure_codes=failures,
        )
        evaluator = AgentIdentity(
            agent_id="parallax-independent-evaluator",
            agent_version=_AGENT_POLICY_VERSION,
            adapter_id="protected-evidence-evaluator",
            adapter_version=_AGENT_POLICY_VERSION,
            provider_kind="parallax",
            declared_work_kinds=("evaluation",),
            declared_capabilities=("bounded-evaluation-evidence",),
            model_runtime_label="deterministic-protected-evidence",
        )
        if evaluator.digest in producer_digests:
            raise AgenticRuntimeError("producer and evaluator identities must remain distinct")
        policy = EvaluatorPolicy(
            policy_id="agentic-independent-evaluation",
            policy_version=_AGENT_POLICY_VERSION,
            acceptance_ids=candidate_binding.acceptance_ids,
            admitted_evaluator_digests=(evaluator.digest,),
            dimensions=(
                DimensionPolicy(
                    dimension="correctness",
                    required_evidence_kinds=(EvidenceKind.TEST,),
                    minimum_evidence_refs=3,
                    allow_score=True,
                    minimum_support_score=1.0,
                ),
            ),
        )
        request = EvaluationRequest(
            candidate=candidate_binding,
            evaluator=evaluator,
            policy=policy,
            protected_validation=protected,
            qualitative_evidence=(),
        )
        judgment = EvaluatorJudgment(
            candidate_digest=candidate_binding.digest,
            evaluator_identity_digest=evaluator.digest,
            policy_digest=policy.digest,
            dimensions=(
                DimensionJudgment(
                    dimension="correctness",
                    verdict=DimensionVerdict.SUPPORT if passed else DimensionVerdict.INSUFFICIENT,
                    finding=(
                        "exact disposable candidate passed protected build test and verify"
                        if passed
                        else "protected candidate validation did not establish exact build test and verify support"
                    ),
                    evidence_refs=refs,
                    confidence=1.0 if passed else 0.0,
                    score=1.0 if passed else None,
                    uncertainty=None if passed else "protected deterministic candidate evidence is incomplete",
                ),
            ),
            claimed_outcome=EvaluationOutcome.SUPPORTED if passed else EvaluationOutcome.INSUFFICIENT_EVIDENCE,
        )
        record = evaluate_candidate(request, judgment)
        admission = admit_evaluation_record(
            expected_request=request,
            record=record,
        )
        if not admission.admitted:
            raise AgenticRuntimeError(f"independent evaluation admission failed: {admission.reason.value}")
        return protected, record

    def _strategy(
        self,
        plan: TeamPlan,
        *,
        candidate_id: str,
    ) -> DevelopmentStrategy:
        kind = StrategyKind.TEAM if len(plan.selected_agent_digests) > 1 else StrategyKind.SINGLE_AGENT
        return DevelopmentStrategy(
            strategy_id=f"strategy-{candidate_id}",
            strategy_version=_AGENT_POLICY_VERSION,
            kind=kind,
            agent_identity_digests=plan.selected_agent_digests,
            work_profile="implementation",
            required_capabilities=("bounded-source-evidence",),
            team_plan_digest=plan.plan_id if kind is StrategyKind.TEAM else None,
            provider_class="openai",
            model_class="hosted",
            conservative_fallback=False,
        )

    def _routing_context(
        self,
        *,
        run: EngineeringRun,
        primary_plan: TeamPlan,
        evaluation_policy_digest: str,
    ) -> RoutingContext:
        return RoutingContext(
            project_id=run.project_id or "",
            run_id=run.id,
            work_specification_id=run.work_specification_id or "",
            work_specification_revision=int(run.work_specification_revision or 0),
            work_specification_digest=run.work_specification_digest or "",
            acceptance_ids=primary_plan.graph.approved_acceptance_ids,
            orchestration_identity_digest=primary_plan.identity.digest,
            evaluation_policy_digest=evaluation_policy_digest,
            routing_policy_id=self.routing_policy.policy_id,
            routing_policy_version=self.routing_policy.policy_version,
            routing_policy_digest=self.routing_policy.digest,
            decision_id=f"routing:{run.id}",
            decision_sequence=1,
        )

    def _routing_outcome(
        self,
        *,
        routing_context: RoutingContext,
        strategy: DevelopmentStrategy,
        candidate: CandidateBinding,
        protected_validation: ProtectedValidationEvidence,
        evaluation_record,
        validation: CandidateValidationResult,
        project_id: str,
    ) -> StrategyOutcomeEvidence:
        return StrategyOutcomeEvidence(
            context_digest=routing_context.digest,
            strategy_digest=strategy.digest,
            project_id=project_id,
            protected_validation_passed=protected_validation.passed,
            protected_validation_digest=protected_validation.digest,
            evaluation_record=evaluation_record,
            completion=CompletionObservation(
                state=CompletionState.COMPLETED if validation.passed else CompletionState.FAILED,
                source_ref=f"candidate:{candidate.candidate_revision_id}",
                source_digest=validation.content_digest,
                project_id=project_id,
            ),
            metrics=(
                RoutingMetricEvidence(
                    metric=RoutingMetricName.DURATION,
                    state=EvidenceState.OBSERVED,
                    provenance=RoutingProvenance.PARALLAX,
                    source_ref=f"metric:duration:{candidate.candidate_revision_id}",
                    source_digest=_digest(
                        {
                            "candidate": validation.content_digest,
                            "duration_seconds": validation.duration_seconds,
                        }
                    ),
                    sequence=1,
                    project_id=project_id,
                    value=validation.duration_seconds,
                    unit="seconds",
                ),
                RoutingMetricEvidence(
                    metric=RoutingMetricName.COST,
                    state=EvidenceState.UNKNOWN,
                    provenance=None,
                    source_ref=f"metric:cost:{candidate.candidate_revision_id}",
                    source_digest=_digest({"candidate": validation.content_digest, "cost": "unknown"}),
                    sequence=1,
                    project_id=project_id,
                ),
            ),
        )

    def _make_candidate(
        self,
        *,
        run: EngineeringRun,
        primary_plan: TeamPlan,
        plan: TeamPlan,
        request: ImplementationGenerationRequest,
        base_workspace: Path,
        proposal_validator: Callable[[ImplementationProposal], bool],
        operation_key: str,
        candidate_id: str,
        alternative_round: int,
        routing_context: RoutingContext | None = None,
    ) -> tuple[ProducedCandidate, RoutingContext]:
        with _candidate_admission_phase(candidate_id, "PROPOSAL_ASSEMBLY"):
            proposal, attempts, models, result_digests, task_digests = self._proposal_for_plan(
                plan,
                request,
                proposal_validator=proposal_validator,
                alternative_round=alternative_round,
            )
        with _candidate_admission_phase(candidate_id, "DISPOSABLE_CANDIDATE_VALIDATION"):
            validation = self._candidate_validation(
                base_workspace,
                proposal,
                operation_key=operation_key,
                candidate_id=candidate_id,
            )
        lead = plan.selected_agent_digests[0]
        with _candidate_admission_phase(candidate_id, "CANDIDATE_BINDING"):
            binding = CandidateBinding(
                project_id=run.project_id or "",
                run_id=run.id,
                work_specification_id=run.work_specification_id or "",
                work_specification_revision=int(run.work_specification_revision or 0),
                work_specification_digest=run.work_specification_digest or "",
                acceptance_ids=primary_plan.graph.approved_acceptance_ids,
                candidate_lineage_digest=validation.content_digest,
                candidate_revision_id=f"revision:{validation.content_digest[:24]}",
                candidate_attempt_id=f"attempt:{candidate_id}",
                producer_identity_digest=lead,
            )
        with _candidate_admission_phase(candidate_id, "INDEPENDENT_EVALUATION"):
            protected, evaluation = self._evaluation(
                run=run,
                candidate_id=candidate_id,
                candidate_binding=binding,
                validation=validation,
                producer_digests=plan.selected_agent_digests,
            )
        if routing_context is None:
            with _candidate_admission_phase(candidate_id, "ROUTING_CONTEXT"):
                context = self._routing_context(
                    run=run,
                    primary_plan=primary_plan,
                    evaluation_policy_digest=evaluation.policy_digest,
                )
        else:
            context = routing_context
        with _candidate_admission_phase(candidate_id, "ROUTING_CONTEXT"):
            if context.evaluation_policy_digest != evaluation.policy_digest:
                raise AgenticRuntimeError("candidate evaluation policy drifted from routing context")
        with _candidate_admission_phase(candidate_id, "STRATEGY_CONSTRUCTION"):
            strategy = self._strategy(plan, candidate_id=candidate_id)
        with _candidate_admission_phase(candidate_id, "ROUTING_OUTCOME"):
            outcome = self._routing_outcome(
                routing_context=context,
                strategy=strategy,
                candidate=binding,
                protected_validation=protected,
                evaluation_record=evaluation,
                validation=validation,
                project_id=run.project_id or "",
            )
        return (
            ProducedCandidate(
                candidate_id=candidate_id,
                plan=plan,
                proposal=proposal,
                attempts=attempts,
                model_labels=models,
                result_digests=result_digests,
                task_digests=task_digests,
                validation=validation,
                binding=binding,
                protected_validation=protected,
                evaluation_record=evaluation,
                strategy=strategy,
                routing_outcome=outcome,
            ),
            context,
        )

    def _challenger_plan(
        self,
        *,
        run: EngineeringRun,
        acceptance: tuple[dict[str, str], ...],
        source_digest: str,
        primary: TeamPlan,
    ) -> TeamPlan | None:
        excluded = primary.selected_agent_digests[0]
        entries = tuple(
            entry for entry in self._roster.entries
            if entry.identity_digest != excluded
        )
        if not entries:
            return None
        try:
            roster = AdmittedRoster(entries)
            return self._team_plan(
                run,
                acceptance,
                source_digest=source_digest,
                roster=roster,
            )
        except (AgenticRuntimeError, ValueError):
            return None

    @staticmethod
    def _competition_candidate(candidate: ProducedCandidate) -> CompetitionCandidate:
        return CompetitionCandidate(
            candidate_id=candidate.candidate_id,
            binding=candidate.binding,
            strategy=candidate.strategy,
            producer_identity_digests=candidate.plan.selected_agent_digests,
            protected_validation=candidate.protected_validation,
            evaluation_record=candidate.evaluation_record,
            routing_outcome=candidate.routing_outcome,
            assignment_or_team_digest=candidate.plan.plan_id,
        )

    def _competition_context(
        self,
        *,
        run: EngineeringRun,
        primary_plan: TeamPlan,
        routing_context: RoutingContext,
        evaluation_policy_digest: str,
    ) -> CompetitionContext:
        return CompetitionContext(
            project_id=run.project_id or "",
            run_id=run.id,
            work_specification_id=run.work_specification_id or "",
            work_specification_revision=int(run.work_specification_revision or 0),
            work_specification_digest=run.work_specification_digest or "",
            acceptance_ids=primary_plan.graph.approved_acceptance_ids,
            orchestration_identity_digest=primary_plan.identity.digest,
            evaluation_policy_id="agentic-independent-evaluation",
            evaluation_policy_version=_AGENT_POLICY_VERSION,
            evaluation_policy_digest=evaluation_policy_digest,
            routing_evidence_digest=routing_context.digest,
            competition_policy_id=self.competition_policy.policy_id,
            competition_policy_version=self.competition_policy.policy_version,
            competition_policy_digest=self.competition_policy.digest,
            operation_id=f"competition:{run.id}",
            operation_sequence=1,
        )

    def generate_protected(
        self,
        request: ImplementationGenerationRequest,
        *,
        workspace_root: Path,
        project_ref: str,
        run_id: str,
        base_source_lineage_ref: str,
        base_revision: str,
        proposal_validator: Callable[[ImplementationProposal], bool],
        operation_key: str,
    ) -> tuple[ImplementationGeneration, dict[str, object]]:
        run = self.service.get(run_id)
        if run.project_id != project_ref:
            raise ImplementationGenerationFailure("agentic runtime Project identity mismatch")
        lineage = self._lineage(run)
        if lineage.lineage_id != base_source_lineage_ref:
            raise ImplementationGenerationFailure("agentic runtime base lineage drifted before generation")
        try:
            primary_plan = self._verify_plan_evidence(
                run=run,
                base_source_lineage_ref=base_source_lineage_ref,
                source_content_digest=lineage.content_digest,
            )
            primary, routing_context = self._make_candidate(
                run=run,
                primary_plan=primary_plan,
                plan=primary_plan,
                request=request,
                base_workspace=workspace_root,
                proposal_validator=proposal_validator,
                operation_key=operation_key,
                candidate_id="candidate-primary",
                alternative_round=1,
            )
            candidates = [primary]

            competition_context = self._competition_context(
                run=run,
                primary_plan=primary_plan,
                routing_context=routing_context,
                evaluation_policy_digest=primary.evaluation_record.policy_digest,
            )
            signal = None
            if len(primary_plan.selected_agent_digests) > 1:
                signal = CompetitionSignal(
                    routing_evidence_digest=routing_context.digest,
                    project_id=run.project_id or "",
                    sequence=1,
                    material_quality_uncertainty=True,
                    expected_quality_gain=0.10,
                )

            preliminary = CompetitionRequest(
                context=competition_context,
                policy=self.competition_policy,
                candidates=(self._competition_candidate(primary),),
                signal=signal,
            )
            trigger, _ = should_compete(
                preliminary,
                tuple(
                    item for item in decide_candidate_competition(
                        CompetitionRequest(
                            context=competition_context,
                            policy=self.competition_policy,
                            candidates=(self._competition_candidate(primary),),
                            signal=None,
                        )
                    ).eligibility
                    if item.eligible
                ),
            )
            if trigger is CompetitionTriggerDisposition.COMPETE:
                acceptance = self._acceptance(run, self.service)
                challenger_plan = self._challenger_plan(
                    run=run,
                    acceptance=acceptance,
                    source_digest=lineage.content_digest,
                    primary=primary_plan,
                )
                if challenger_plan is not None:
                    challenger, _ = self._make_candidate(
                        run=run,
                        primary_plan=primary_plan,
                        plan=challenger_plan,
                        request=request,
                        base_workspace=workspace_root,
                        proposal_validator=proposal_validator,
                        operation_key=operation_key,
                        candidate_id="candidate-challenger",
                        alternative_round=2,
                        routing_context=routing_context,
                    )
                    if challenger.validation.content_digest != primary.validation.content_digest:
                        candidates.append(challenger)

            strategies = tuple(candidate.strategy for candidate in candidates)
            admissions = tuple(
                StrategyAdmissionSnapshot(
                    context_digest=routing_context.digest,
                    strategy_digest=candidate.strategy.digest,
                    project_id=run.project_id or "",
                    source_ref=f"candidate:{candidate.candidate_id}",
                    source_digest=candidate.validation.content_digest,
                    capability_compatible=True,
                    authority_compatible=True,
                    dependency_compatible=True,
                    admitted_capabilities=("bounded-source-evidence",),
                )
                for candidate in candidates
            )
            outcomes = tuple(candidate.routing_outcome for candidate in candidates)
            routing_request = RoutingRequest(
                context=routing_context,
                policy=self.routing_policy,
                strategies=strategies,
                admissions=admissions,
                outcomes=outcomes,
            )
            routing_record = route_outcomes(routing_request)
            if routing_record.selected_strategy_id is None:
                diagnostic = _candidate_validation_failure_diagnostic(
                    primary.candidate_id,
                    primary.validation,
                )
                if diagnostic is not None:
                    raise CandidateValidationFailure(
                        f"agentic outcome routing stopped after protected candidate validation: {routing_record.reason_code}",
                        diagnostic_evidence=diagnostic,
                    )
                raise AgenticRuntimeError(
                    f"agentic outcome routing stopped: {routing_record.reason_code}"
                )

            competition_request = CompetitionRequest(
                context=competition_context,
                policy=self.competition_policy,
                candidates=tuple(self._competition_candidate(item) for item in candidates),
                signal=signal,
            )
            competition_record = decide_candidate_competition(competition_request)
            if competition_record.disposition not in {
                CompetitionDisposition.SINGLE_CANDIDATE_SUFFICIENT,
                CompetitionDisposition.WINNER_SUPPORTED,
            } or competition_record.selected_candidate_id is None:
                raise AgenticRuntimeError(
                    f"candidate competition did not admit a selected candidate: {competition_record.reason_code}"
                )
            selected = next(
                item for item in candidates
                if item.candidate_id == competition_record.selected_candidate_id
            )
            if routing_record.selected_strategy_id != selected.strategy.strategy_id:
                raise AgenticRuntimeError("S4 routing and S5 candidate selection disagree")
            if not selected.validation.passed:
                raise AgenticRuntimeError("selected candidate lacks protected deterministic validation")
            if selected.evaluation_record.outcome is not EvaluationOutcome.SUPPORTED:
                raise AgenticRuntimeError("selected candidate lacks independent S3 support")

            execution_digest = _digest(
                {
                    "runtime": AGENTIC_RUNTIME_VERSION,
                    "team_plan_id": primary_plan.plan_id,
                    "candidate_digests": [item.validation.content_digest for item in candidates],
                    "task_digests": [digest for item in candidates for digest in item.task_digests],
                    "result_digests": [digest for item in candidates for digest in item.result_digests],
                    "routing_record_digest": routing_record.digest,
                    "competition_record_digest": competition_record.digest,
                    "selected_candidate_id": selected.candidate_id,
                    "selected_proposal_digest": selected.proposal_digest,
                }
            )
            generation = ImplementationGeneration(
                proposal=selected.proposal,
                model=(
                    selected.model_labels[0]
                    if len(selected.model_labels) == 1
                    else f"agentic-team:{_digest(selected.model_labels)[:32]}"
                ),
                attempts=selected.attempts,
                program_version=f"{AGENTIC_RUNTIME_VERSION}:{execution_digest}",
            )
            evidence = {
                "runtime_version": AGENTIC_RUNTIME_VERSION,
                "execution_digest": execution_digest,
                "team_plan_id": primary_plan.plan_id,
                "orchestration_identity_digest": primary_plan.identity.digest,
                "work_graph_digest": primary_plan.graph.digest,
                "selected_agent_digests": list(primary_plan.selected_agent_digests),
                "candidate_count": len(candidates),
                "candidates": [
                    {
                        "candidate_id": item.candidate_id,
                        "candidate_content_digest": item.validation.content_digest,
                        "validation_profile_id": item.validation.validation_profile_id,
                        "validation_profile_digest": item.validation.validation_profile_digest,
                        "proposal_digest": item.proposal_digest,
                        "producer_identity_digests": list(item.plan.selected_agent_digests),
                        "protected_validation_digest": item.protected_validation.digest,
                        "evaluation_record_digest": item.evaluation_record.digest,
                        "evaluation_outcome": item.evaluation_record.outcome.value,
                        "strategy_id": item.strategy.strategy_id,
                        "strategy_digest": item.strategy.digest,
                        "duration_seconds": item.validation.duration_seconds,
                    }
                    for item in candidates
                ],
                "routing_context_digest": routing_context.digest,
                "routing_record_digest": routing_record.digest,
                "routing_disposition": routing_record.disposition.value,
                "routing_reason_code": routing_record.reason_code,
                "competition_record_digest": competition_record.digest,
                "competition_trigger": competition_record.trigger.value,
                "competition_disposition": competition_record.disposition.value,
                "competition_reason_code": competition_record.reason_code,
                "selected_candidate_id": selected.candidate_id,
                "selected_candidate_content_digest": selected.validation.content_digest,
                "selected_validation_profile_id": selected.validation.validation_profile_id,
                "selected_validation_profile_digest": selected.validation.validation_profile_digest,
                "selected_proposal_digest": selected.proposal_digest,
                "source_lineage_accepted": False,
                "engineering_run_transitioned": False,
                "review_completed": False,
                "production_deployed": False,
            }
            return generation, evidence
        except ImplementationGenerationFailure:
            raise
        except CandidateValidationFailure as exc:
            raise ImplementationGenerationFailure(
                "agentic runtime rejected a protected implementation candidate",
                diagnostic_evidence={
                    "candidate_validation_failure": dict(exc.diagnostic_evidence),
                },
            ) from exc
        except CandidateAdmissionFailure as exc:
            raise ImplementationGenerationFailure(
                "agentic runtime failed during bounded candidate admission",
                diagnostic_evidence={
                    "candidate_admission_failure": dict(exc.diagnostic_evidence),
                },
            ) from exc
        except (AgenticRuntimeError, ValueError, ImplementationError, PatchError, OSError) as exc:
            raise ImplementationGenerationFailure(
                "agentic runtime could not admit a protected implementation candidate"
            ) from exc


def build_agentic_runtime_composition(
    service: EngineeringRunService,
    allocator: DurableLineageAllocator,
    legacy_executor,
    *,
    source_delivery=None,
    lineage_executor=None,
    candidate_validator: CandidateValidationExecutor | None = None,
    adapters: tuple[HostedImplementationAgent, ...] | None = None,
) -> EngineeringRuntimeComposition:
    """Attach Wave 6 decisions to the existing authoritative runtime composition."""

    composition = EngineeringRuntimeComposition(
        service,
        allocator,
        legacy_executor,
        lineage_executor=lineage_executor,
        source_delivery=source_delivery,
    )
    control = AgenticControlPlane(
        service,
        allocator,
        adapters=adapters,
        candidate_validator=candidate_validator,
        implementation_engine=composition.implementation_runtime.implementation_engine,
    )
    composition.implementation_runtime.generator = control
    composition.coordinator.plan_runtime = control
    return composition


def agentic_runtime_enabled() -> bool:
    return os.getenv("PARALLAX_AGENTIC_RUNTIME_ENABLED") == "1"


def _digest(value: object) -> str:
    return sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


__all__ = [
    "AGENTIC_RUNTIME_VERSION",
    "AgenticControlPlane",
    "AgenticRuntimeError",
    "CandidateValidationExecutor",
    "CandidateValidationResult",
    "HostedImplementationAgent",
    "VercelCandidateValidationExecutor",
    "agentic_runtime_enabled",
    "build_agentic_runtime_composition",
]
