from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol

from ..models import EngineeringRun
from ..intelligence.implementation_generation import (
    AcceptanceRequirement,
    ImplementationGenerationCoordinator,
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
from .domain import AttemptStatus, WorkflowStage
from .implementation import (
    DuplicateTargetError,
    ImplementationError,
    ImplementationLimitError,
    ImplementationRequest,
    SafeImplementationEngine,
    TargetHierarchyConflictError,
)
from .model_patch_canonicalization import CanonicalizingTextPatchEngine
from .patching import (
    PatchConflictError,
    PatchError,
    PatchFormatError,
    PatchLimitError,
    SourcePatch,
    StaleBaseError,
    UnsafeTargetError,
)
from .service import EngineeringRunService, RunOperationResult
from .source_context import BoundedSourceContextSelector, SourceContextError
from .state_machine import RevisionConflict
from .static_web_validator import STATIC_WEB_VALIDATION_REASON_CODES
from .work_spec_binding import acceptance_map, work_specification_contract, work_specification_digest


class ImplementationRuntimeError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        mutation_applied: bool = False,
        diagnostic_evidence: object | None = None,
    ) -> None:
        super().__init__(message)
        self.mutation_applied = mutation_applied
        if diagnostic_evidence is None:
            self.diagnostic_evidence = None
        else:
            try:
                self.diagnostic_evidence = _bounded_implementation_failure_evidence(diagnostic_evidence)
            except ValueError:
                # Diagnostics are observation only. Invalid or sensitive diagnostic
                # material must be dropped rather than changing fail-closed behavior.
                self.diagnostic_evidence = None


class ProjectBindingError(ImplementationRuntimeError):
    pass


class WorkspaceLineageError(ImplementationRuntimeError):
    pass


class ImplementationContractError(ImplementationRuntimeError):
    pass


class ImplementationMutationError(ImplementationRuntimeError):
    pass


PROPOSAL_PREFLIGHT_REASON_CODES = frozenset(
    {
        "UNSAFE_TARGET",
        "STALE_BASE",
        "PATCH_FORMAT",
        "PATCH_CONFLICT",
        "PATCH_LIMIT",
        "DUPLICATE_TARGET",
        "TARGET_HIERARCHY_CONFLICT",
        "IMPLEMENTATION_LIMIT",
        "SAFE_IMPLEMENTATION_ERROR",
        "UNKNOWN_PATCH_ERROR",
        "OS_BOUNDARY_ERROR",
        "UNKNOWN_PRECHECK_ERROR",
    }
)


def classify_proposal_preflight_failure(exc: Exception) -> str:
    """Map protected safe-engine failures to fixed non-sensitive reason codes."""

    if isinstance(exc, UnsafeTargetError):
        return "UNSAFE_TARGET"
    if isinstance(exc, StaleBaseError):
        return "STALE_BASE"
    if isinstance(exc, PatchFormatError):
        return "PATCH_FORMAT"
    if isinstance(exc, PatchConflictError):
        return "PATCH_CONFLICT"
    if isinstance(exc, PatchLimitError):
        return "PATCH_LIMIT"
    if isinstance(exc, DuplicateTargetError):
        return "DUPLICATE_TARGET"
    if isinstance(exc, TargetHierarchyConflictError):
        return "TARGET_HIERARCHY_CONFLICT"
    if isinstance(exc, ImplementationLimitError):
        return "IMPLEMENTATION_LIMIT"
    if isinstance(exc, PatchError):
        return "UNKNOWN_PATCH_ERROR"
    if isinstance(exc, ImplementationError):
        return "SAFE_IMPLEMENTATION_ERROR"
    if isinstance(exc, OSError):
        return "OS_BOUNDARY_ERROR"
    return "UNKNOWN_PRECHECK_ERROR"


class ProposalSafetyPreflight:
    """Callable whole-proposal gate with a sanitized read-only reason seam."""

    def __init__(self, engine: SafeImplementationEngine, workspace_root: Path) -> None:
        self.engine = engine
        self.workspace_root = workspace_root

    def reason(self, proposal: ImplementationProposal) -> str | None:
        try:
            self.engine.validate(
                self.workspace_root,
                ProtectedImplementationRuntime._implementation_request(proposal),
            )
        except (ImplementationError, PatchError, OSError, ValueError) as exc:
            return classify_proposal_preflight_failure(exc)
        return None

    def __call__(self, proposal: ImplementationProposal) -> bool:
        return self.reason(proposal) is None


class CanonicalProjectBinding(Protocol):
    def project_ref_for_run(self, run: EngineeringRun) -> str: ...


class RunProjectBinding:
    """Compatibility adapter for #59's canonical EngineeringRun.project_id seam.

    The current Wave 1 model does not expose project_id yet, so this adapter
    deliberately fails closed until #59 is serialized into main. Tests may use
    an injected binding without creating a competing persistent Project identity.
    """

    def project_ref_for_run(self, run: EngineeringRun) -> str:
        value = getattr(run, "project_id", None)
        if not isinstance(value, str) or not value.strip():
            raise ProjectBindingError("canonical Project identity is unavailable for this Engineering Run")
        return value


@dataclass(frozen=True, slots=True)
class ImplementationWorkspaceHandle:
    project_ref: str
    run_id: str
    source_lineage_ref: str
    base_revision: str
    workspace_root: Path

    def __post_init__(self) -> None:
        _bounded_identity(self.project_ref, "project_ref")
        _bounded_identity(self.run_id, "run_id")
        _bounded_identity(self.source_lineage_ref, "source_lineage_ref")
        _bounded_identity(self.base_revision, "base_revision")
        if not isinstance(self.workspace_root, Path):
            raise ValueError("workspace_root must be a protected server-owned Path")


@dataclass(frozen=True, slots=True)
class ImplementationLineageReceipt:
    project_ref: str
    run_id: str
    base_source_lineage_ref: str
    source_lineage_ref: str
    workspace_digest: str

    def __post_init__(self) -> None:
        _bounded_identity(self.project_ref, "project_ref")
        _bounded_identity(self.run_id, "run_id")
        _bounded_identity(self.base_source_lineage_ref, "base_source_lineage_ref")
        _bounded_identity(self.source_lineage_ref, "source_lineage_ref")
        if len(self.workspace_digest) != 64 or any(ch not in "0123456789abcdef" for ch in self.workspace_digest):
            raise ValueError("workspace_digest must be lowercase SHA-256")


class WorkspaceLineageGateway(Protocol):
    def resolve_for_implementation(self, *, project_ref: str, run_id: str) -> ImplementationWorkspaceHandle: ...

    def accept_implementation(
        self,
        *,
        handle: ImplementationWorkspaceHandle,
        workspace_digest: str,
        artifacts: tuple[dict[str, object], ...],
    ) -> ImplementationLineageReceipt: ...


@dataclass(frozen=True, slots=True)
class ImplementationRuntimeResult:
    operation: RunOperationResult
    source_lineage_ref: str
    model_id: str | None
    proposal_digest: str | None
    source_context_digest: str | None


class ProtectedImplementationRuntime:
    """Generate, safely apply, lineage-bind, then protect an IMPLEMENT stage.

    Generation, filesystem mutation, lineage acceptance, and durable stage
    authority remain separate boundaries. No model-visible contract contains the
    protected local workspace root.

    A composed controller may supply a pre-selected candidate through the narrow
    ``generate_protected`` seam. That seam receives the already server-resolved
    workspace only for candidate validation and cannot accept lineage or complete
    the stage. The selected proposal is still revalidated and committed below by
    the same safe implementation, lineage and EngineeringRunService boundaries.
    """

    def __init__(
        self,
        service: EngineeringRunService,
        project_binding: CanonicalProjectBinding,
        workspace_lineage: WorkspaceLineageGateway,
        *,
        generator: ImplementationGenerationCoordinator | None = None,
        source_selector: BoundedSourceContextSelector | None = None,
        implementation_engine: SafeImplementationEngine | None = None,
    ) -> None:
        self.service = service
        self.project_binding = project_binding
        self.workspace_lineage = workspace_lineage
        self.generator = generator or ImplementationGenerationCoordinator()
        self.source_selector = source_selector or BoundedSourceContextSelector()
        self.implementation_engine = implementation_engine or SafeImplementationEngine(
            patch_engine=CanonicalizingTextPatchEngine()
        )

    @staticmethod
    def _implementation_request(proposal: ImplementationProposal) -> ImplementationRequest:
        return ImplementationRequest(
            patches=tuple(
                SourcePatch(
                    path=item.path,
                    expected_base_sha256=item.expected_base_sha256,
                    unified_diff=item.unified_diff,
                )
                for item in proposal.patches
            )
        )

    def execute(
        self,
        *,
        run_id: str,
        operation_key: str,
        expected_revision: int,
    ) -> ImplementationRuntimeResult:
        if not operation_key:
            raise ImplementationContractError("IMPLEMENT operation key is required")

        existing = self.service.runs.find_operation(run_id, operation_key)
        if existing is not None:
            if existing.status != AttemptStatus.PASSED.value or existing.stage != WorkflowStage.IMPLEMENT.value:
                raise ImplementationContractError("existing IMPLEMENT operation is not a successful replay")
            evidence = json.loads(existing.evidence_json)
            lineage = str(evidence.get("source_lineage_ref") or "")
            if not lineage:
                raise ImplementationContractError("replayed IMPLEMENT operation lacks accepted source lineage")
            return ImplementationRuntimeResult(
                operation=RunOperationResult(
                    run=self.service.get(run_id),
                    attempt_id=existing.id,
                    replayed=True,
                ),
                source_lineage_ref=lineage,
                model_id=existing.model_id,
                proposal_digest=str(evidence.get("proposal_digest") or "") or None,
                source_context_digest=str(evidence.get("source_context_digest") or "") or None,
            )

        run = self.service.get(run_id)
        if run.revision != expected_revision:
            raise RevisionConflict(
                f"stale engineering run revision: expected {expected_revision}, current {run.revision}"
            )
        if WorkflowStage(run.state) is not WorkflowStage.IMPLEMENT:
            raise ImplementationContractError("protected implementation runtime requires the IMPLEMENT stage")

        project_ref = self._project_ref(run)
        handle = self._workspace_handle(project_ref, run)
        specification, contract, acceptance = self._bound_contract(run)

        try:
            source_context = self.source_selector.select(
                handle.workspace_root,
                objective=str(contract["objective"]),
                acceptance_texts=tuple(item["text"] for item in acceptance),
            )
        except SourceContextError as exc:
            raise ImplementationContractError("protected source context could not be established") from exc

        request = ImplementationGenerationRequest(
            work_specification_id=specification.id,
            work_specification_revision=specification.revision,
            work_specification_digest=run.work_specification_digest or "",
            title=str(contract["title"]),
            objective=str(contract["objective"]),
            constraints=tuple(str(item) for item in contract["constraints"]),
            acceptance=tuple(
                AcceptanceRequirement(id=item["id"], text=item["text"])
                for item in acceptance
            ),
            source_context=source_context,
        )

        proposal_is_safe = ProposalSafetyPreflight(
            self.implementation_engine,
            handle.workspace_root,
        )

        controller_evidence: dict[str, object] | None = None
        try:
            protected_generate = getattr(self.generator, "generate_protected", None)
            if callable(protected_generate):
                generated = protected_generate(
                    request,
                    workspace_root=handle.workspace_root,
                    project_ref=project_ref,
                    run_id=run.id,
                    base_source_lineage_ref=handle.source_lineage_ref,
                    base_revision=handle.base_revision,
                    proposal_validator=proposal_is_safe,
                    operation_key=operation_key,
                )
                if not isinstance(generated, tuple) or len(generated) != 2:
                    raise ImplementationGenerationFailure(
                        "protected controller returned an invalid selected-candidate result"
                    )
                generation, raw_controller_evidence = generated
                controller_evidence = _bounded_controller_evidence(raw_controller_evidence)
            elif isinstance(self.generator, ImplementationGenerationCoordinator):
                generation = self.generator.generate_sync(
                    request,
                    proposal_validator=proposal_is_safe,
                )
            else:
                # Injected coordinators remain supported for deterministic tests
                # and integrations. They receive no routing authority; their
                # selected proposal is still rejected by the safe engine below.
                generation = self.generator.generate_sync(request)
        except ImplementationGenerationFailure as exc:
            raise ImplementationContractError(
                "protected implementation generation failed",
                diagnostic_evidence=exc.diagnostic_evidence,
            ) from exc
        except (TypeError, ValueError) as exc:
            raise ImplementationContractError("protected implementation generation failed") from exc

        # Defense in depth: even a custom/injected generation coordinator cannot
        # make candidate text authoritative over the server-owned acceptance set.
        if not validate_implementation_proposal(generation.proposal, request.required_acceptance_ids):
            raise ImplementationContractError("generated proposal does not exactly cover protected acceptance IDs")

        implementation_request = self._implementation_request(generation.proposal)
        try:
            # Re-prepare immediately before commit. The routing/candidate
            # preflight is not mutation authority and cannot substitute for
            # commit-time validation on the exact server-owned workspace.
            mutation = self.implementation_engine.apply(handle.workspace_root, implementation_request)
        except (ImplementationError, PatchError, OSError) as exc:
            raise ImplementationMutationError("safe source implementation rejected the proposal") from exc

        if mutation.get("applied") is not True or mutation.get("protected_stage_authority") is not False:
            raise ImplementationMutationError("safe implementation result does not prove bounded mutation")
        workspace_digest = str(mutation.get("workspace_digest") or "")
        artifacts_raw = mutation.get("artifacts")
        if len(workspace_digest) != 64 or not isinstance(artifacts_raw, list) or not artifacts_raw:
            raise ImplementationMutationError("safe implementation result lacks required artifact identity")
        artifacts = tuple(dict(item) for item in artifacts_raw if isinstance(item, dict))
        if len(artifacts) != len(artifacts_raw):
            raise ImplementationMutationError("safe implementation returned malformed artifact evidence")

        receipt = self._accept_lineage(
            handle=handle,
            workspace_digest=workspace_digest,
            artifacts=artifacts,
        )
        self._verify_receipt(
            receipt,
            handle=handle,
            project_ref=project_ref,
            run_id=run.id,
            workspace_digest=workspace_digest,
        )

        proposal_digest = generation.proposal.digest()
        evidence: dict[str, object] = {
            "artifacts": [dict(item) for item in artifacts],
            "base_revision": handle.base_revision,
            "workspace_digest": workspace_digest,
            "project_ref": project_ref,
            "run_id": run.id,
            "base_source_lineage_ref": handle.source_lineage_ref,
            "source_lineage_ref": receipt.source_lineage_ref,
            "proposal_digest": proposal_digest,
            "source_context_digest": source_context.digest,
            "source_context_file_count": len(source_context.files),
            "source_context_total_bytes": source_context.total_bytes,
            "acceptance_ids_covered": list(request.required_acceptance_ids),
            "patch_count": len(generation.proposal.patches),
            "protected_stage_authority": False,
            "external_execution": False,
            "network_mutation": False,
            "git_mutation": False,
            "deployment_mutation": False,
        }
        if controller_evidence is not None:
            evidence["controller_evidence"] = controller_evidence
        try:
            operation = self.service.complete_stage(
                run_id=run.id,
                stage=WorkflowStage.IMPLEMENT,
                operation_key=operation_key,
                expected_revision=run.revision,
                passed=True,
                evidence=evidence,
                program_id=generation.program_version,
                model_id=generation.model,
                tool_id="safe-source-implementation-v1",
            )
        except Exception as exc:
            # Mutation and lineage acceptance already completed. Durable stage
            # authority remains with EngineeringRunService; never fabricate a
            # successful transition when its validator/policy rejects the write.
            raise ImplementationRuntimeError(
                "source mutation succeeded but durable IMPLEMENT acceptance failed",
                mutation_applied=True,
            ) from exc
        return ImplementationRuntimeResult(
            operation=operation,
            source_lineage_ref=receipt.source_lineage_ref,
            model_id=generation.model,
            proposal_digest=proposal_digest,
            source_context_digest=source_context.digest,
        )

    def _project_ref(self, run: EngineeringRun) -> str:
        try:
            value = self.project_binding.project_ref_for_run(run)
            return _bounded_identity(value, "project_ref")
        except ImplementationRuntimeError:
            raise
        except Exception as exc:
            raise ProjectBindingError("canonical Project binding failed") from exc

    def _workspace_handle(self, project_ref: str, run: EngineeringRun) -> ImplementationWorkspaceHandle:
        try:
            handle = self.workspace_lineage.resolve_for_implementation(project_ref=project_ref, run_id=run.id)
        except Exception as exc:
            raise WorkspaceLineageError("protected implementation workspace could not be resolved") from exc
        if not isinstance(handle, ImplementationWorkspaceHandle):
            raise WorkspaceLineageError("protected workspace adapter returned an invalid handle")
        if handle.project_ref != project_ref or handle.run_id != run.id:
            raise WorkspaceLineageError("protected workspace identity does not match the Project/run binding")
        if not handle.workspace_root.exists() or not handle.workspace_root.is_dir() or handle.workspace_root.is_symlink():
            raise WorkspaceLineageError("protected implementation workspace is unavailable")
        return handle

    def _bound_contract(self, run: EngineeringRun):
        try:
            if not run.work_specification_id or run.work_specification_revision is None or not run.work_specification_digest:
                raise ValueError("IMPLEMENT requires an approved Work Specification binding")
            specification = self.service.work_specifications.get(run.work_specification_id)
            if specification is None:
                raise ValueError("bound Work Specification no longer exists")
            if specification.conversation_id != run.conversation_id:
                raise ValueError("bound Work Specification conversation mismatch")
            if specification.revision != run.work_specification_revision:
                raise ValueError("bound Work Specification revision mismatch")
            if specification.status not in {"APPROVED", "SUPERSEDED"}:
                raise ValueError("bound Work Specification is not an approved execution contract")
            if work_specification_digest(specification) != run.work_specification_digest:
                raise ValueError("bound Work Specification content changed after run binding")
            return specification, work_specification_contract(specification), acceptance_map(specification)
        except Exception as exc:
            raise ImplementationContractError("bound Work Specification contract could not be proven") from exc

    def _accept_lineage(
        self,
        *,
        handle: ImplementationWorkspaceHandle,
        workspace_digest: str,
        artifacts: tuple[dict[str, object], ...],
    ) -> ImplementationLineageReceipt:
        try:
            receipt = self.workspace_lineage.accept_implementation(
                handle=handle,
                workspace_digest=workspace_digest,
                artifacts=artifacts,
            )
            if not isinstance(receipt, ImplementationLineageReceipt):
                raise TypeError("workspace-lineage adapter returned an invalid receipt")
            return receipt
        except Exception as exc:
            # Mutation already completed. Do not fabricate accepted lineage or
            # durable IMPLEMENT success; serialized integration can reconcile
            # the bounded workspace through #60's immutable snapshot contract.
            raise WorkspaceLineageError(
                "source mutation succeeded but accepted lineage could not be established",
                mutation_applied=True,
            ) from exc

    @staticmethod
    def _verify_receipt(
        receipt: ImplementationLineageReceipt,
        *,
        handle: ImplementationWorkspaceHandle,
        project_ref: str,
        run_id: str,
        workspace_digest: str,
    ) -> None:
        if (
            receipt.project_ref != project_ref
            or receipt.run_id != run_id
            or receipt.base_source_lineage_ref != handle.source_lineage_ref
            or receipt.workspace_digest != workspace_digest
            or receipt.source_lineage_ref == handle.source_lineage_ref
        ):
            raise WorkspaceLineageError(
                "accepted source-lineage receipt does not match the implementation mutation",
                mutation_applied=True,
            )


def _bounded_controller_evidence(value: object) -> dict[str, object]:
    """Admit only bounded, non-secret controller evidence into durable IMPLEMENT."""

    if not isinstance(value, dict) or not value:
        raise ValueError("protected controller evidence must be a non-empty object")

    forbidden_fragments = (
        "credential",
        "token",
        "secret",
        "prompt",
        "reasoning",
        "source_bytes",
        "provider_payload",
        "workspace_root",
    )

    def inspect(item: object) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if not isinstance(key, str):
                    raise ValueError("protected controller evidence keys must be strings")
                lowered = key.casefold()
                if any(fragment in lowered for fragment in forbidden_fragments):
                    raise ValueError("protected controller evidence contains forbidden sensitive field")
                inspect(nested)
        elif isinstance(item, list):
            for nested in item:
                inspect(nested)
        elif not isinstance(item, (str, int, float, bool, type(None))):
            raise ValueError("protected controller evidence contains non-JSON value")

    inspect(value)
    for claim in (
        "source_lineage_accepted",
        "engineering_run_transitioned",
        "review_completed",
        "production_deployed",
    ):
        if claim in value and value[claim] is not False:
            raise ValueError("protected controller evidence asserted authority it does not own")

    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > 32_768:
        raise ValueError("protected controller evidence exceeds durable evidence bound")
    normalized = json.loads(encoded)
    if not isinstance(normalized, dict):
        raise ValueError("protected controller evidence normalization failed")
    return normalized


def _bounded_implementation_failure_evidence(value: object) -> dict[str, object]:
    """Allow only sanitized protected candidate failure diagnostics into durable failure evidence."""

    if not isinstance(value, dict):
        raise ValueError("implementation failure diagnostics have an invalid envelope")
    if set(value) == {"candidate_generation_failure"}:
        return _bounded_candidate_generation_failure_evidence(
            value["candidate_generation_failure"]
        )
    if set(value) == {"candidate_admission_failure"}:
        raw_phase = value["candidate_admission_failure"]
        if not isinstance(raw_phase, dict):
            raise ValueError("candidate admission diagnostics must be an object")
        required_phase_fields = {
            "candidate_id",
            "phase",
            "failure_kind",
            "candidate_is_canonical_lineage",
            "accepts_source_lineage",
            "source_lineage_accepted",
            "engineering_run_transitioned",
            "review_completed",
            "production_deployed",
        }
        allowed_phase_fields = {*required_phase_fields, "reason_code"}
        if set(raw_phase) - allowed_phase_fields or not required_phase_fields <= set(raw_phase):
            raise ValueError("candidate admission diagnostics contain a non-admitted field")
        phases = {
            "EXECUTION_CONTRACT_VERIFICATION",
            "PROPOSAL_ASSEMBLY",
            "DISPOSABLE_CANDIDATE_VALIDATION",
            "CANDIDATE_BINDING",
            "INDEPENDENT_EVALUATION",
            "ROUTING_CONTEXT",
            "STRATEGY_CONSTRUCTION",
            "ROUTING_OUTCOME",
        }
        failure_kinds = {
            "SAFE_IMPLEMENTATION_ERROR",
            "PATCH_ERROR",
            "OS_BOUNDARY_ERROR",
            "VALIDATION_PROFILE_ERROR",
            "AGENTIC_CONTRACT_ERROR",
            "VALUE_CONTRACT_ERROR",
        }
        candidate_id = _bounded_identity(raw_phase.get("candidate_id"), "candidate_id")
        phase = raw_phase.get("phase")
        failure_kind = raw_phase.get("failure_kind")
        if phase not in phases or failure_kind not in failure_kinds:
            raise ValueError("candidate admission diagnostics contain a non-server-owned classification")
        normalized_phase: dict[str, object] = {
            "candidate_id": candidate_id,
            "phase": phase,
            "failure_kind": failure_kind,
        }
        reason_code = raw_phase.get("reason_code")
        profile_reason_codes = {
            "UNSUPPORTED_VALIDATION_ECOSYSTEM",
            "AMBIGUOUS_VALIDATION_ECOSYSTEM",
            "AMBIGUOUS_DOTNET_TARGET",
            "PYTHON_FIXED_VALIDATION_UNAVAILABLE",
            "NODE_FIXED_VALIDATION_UNAVAILABLE",
            "EXECUTION_CONTRACT_DRIFT",
            "EXECUTION_CONTRACT_UNAVAILABLE",
            "EXECUTION_SNAPSHOT_UNAVAILABLE",
            "INVALID_VALIDATION_PROFILE",
            "INVALID_VALIDATION_TARGET",
        }
        if failure_kind == "VALIDATION_PROFILE_ERROR":
            if reason_code not in profile_reason_codes:
                raise ValueError("candidate admission diagnostics contain an invalid validation reason")
            normalized_phase["reason_code"] = reason_code
        elif reason_code is not None:
            raise ValueError("candidate admission diagnostics contain an unexpected reason code")
        for claim in (
            "candidate_is_canonical_lineage",
            "accepts_source_lineage",
            "source_lineage_accepted",
            "engineering_run_transitioned",
            "review_completed",
            "production_deployed",
        ):
            if raw_phase.get(claim) is not False:
                raise ValueError("candidate admission diagnostics asserted authority they do not own")
            normalized_phase[claim] = False
        normalized = {"candidate_admission_failure": normalized_phase}
        encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        if len(encoded.encode("utf-8")) > 2_048:
            raise ValueError("candidate admission diagnostics exceed durable evidence bound")
        return normalized
    if set(value) != {"candidate_validation_failure"}:
        raise ValueError("implementation failure diagnostics have an invalid envelope")
    raw = value["candidate_validation_failure"]
    if not isinstance(raw, dict):
        raise ValueError("candidate validation diagnostics must be an object")

    allowed = {
        "candidate_id",
        "failed_stage",
        "protected_success",
        "exit_code_present",
        "exit_code",
        "timed_out",
        "tool_id",
        "invocation_digest",
        "stdout_digest",
        "stderr_digest",
        "dependency_stdout_digest",
        "dependency_stderr_digest",
        "dependency_preparation_code",
        "dependency_preparation_required",
        "dependency_preparation_succeeded",
        "validation_network_locked",
        "dependency_probe_exit_code",
        "dependency_prepare_exit_code",
        "execution_snapshot_id",
        "validation_profile_id",
        "validation_profile_digest",
        "candidate_content_digest",
        "validation_reason_code",
        "candidate_is_canonical_lineage",
        "accepts_source_lineage",
        "source_lineage_accepted",
        "production_deployed",
    }
    if set(raw) - allowed:
        raise ValueError("candidate validation diagnostics contain a non-admitted field")

    candidate_id = _bounded_identity(raw.get("candidate_id"), "candidate_id")
    stage = raw.get("failed_stage")
    if stage not in {WorkflowStage.BUILD.value, WorkflowStage.TEST.value, WorkflowStage.VERIFY.value}:
        raise ValueError("candidate validation diagnostics contain an invalid stage")
    if raw.get("protected_success") is not False:
        raise ValueError("candidate validation failure cannot claim protected success")
    if not isinstance(raw.get("exit_code_present"), bool):
        raise ValueError("candidate validation exit-code presence must be boolean")
    exit_code = raw.get("exit_code")
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
        raise ValueError("candidate validation exit code must be integer or null")
    if raw["exit_code_present"] is not (exit_code is not None):
        raise ValueError("candidate validation exit-code presence drifted")
    if not isinstance(raw.get("timed_out"), bool):
        raise ValueError("candidate validation timeout state must be boolean")

    normalized_failure: dict[str, object] = {
        "candidate_id": candidate_id,
        "failed_stage": stage,
        "protected_success": False,
        "exit_code_present": raw["exit_code_present"],
        "exit_code": exit_code,
        "timed_out": raw["timed_out"],
    }
    for key in ("candidate_is_canonical_lineage", "accepts_source_lineage", "source_lineage_accepted", "production_deployed"):
        if raw.get(key) is not False:
            raise ValueError("candidate validation diagnostics asserted authority they do not own")
        normalized_failure[key] = False

    for key in (
        "invocation_digest",
        "stdout_digest",
        "stderr_digest",
        "dependency_stdout_digest",
        "dependency_stderr_digest",
        "candidate_content_digest",
    ):
        if key not in raw:
            continue
        digest = raw[key]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise ValueError("candidate validation diagnostics contain an invalid SHA-256 digest")
        normalized_failure[key] = digest

    if "dependency_preparation_code" in raw:
        code = raw["dependency_preparation_code"]
        if code not in {
            "NOT_REQUIRED",
            "READY",
            "EXECUTION_PROFILE_UNAVAILABLE",
            "DEPENDENCY_PREPARATION_FAILED",
            "VALIDATION_NETWORK_LOCK_FAILED",
        }:
            raise ValueError("candidate validation diagnostics contain an invalid dependency preparation code")
        normalized_failure["dependency_preparation_code"] = code

    for key in (
        "dependency_preparation_required",
        "dependency_preparation_succeeded",
        "validation_network_locked",
    ):
        if key not in raw:
            continue
        value = raw[key]
        if not isinstance(value, bool):
            raise ValueError("candidate validation dependency state must be boolean")
        normalized_failure[key] = value

    for key in ("dependency_probe_exit_code", "dependency_prepare_exit_code"):
        if key not in raw:
            continue
        value = raw[key]
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise ValueError("candidate validation dependency exit code must be integer or null")
        normalized_failure[key] = value

    for key, limit in (("tool_id", 80), ("execution_snapshot_id", 180), ("validation_profile_id", 80)):
        if key not in raw:
            continue
        field = raw[key]
        if (
            not isinstance(field, str)
            or not field
            or len(field) > limit
            or field.strip() != field
            or any(ord(ch) < 32 for ch in field)
        ):
            raise ValueError("candidate validation diagnostics contain an invalid bounded identity")
        normalized_failure[key] = field

    if "validation_reason_code" in raw:
        reason_code = raw["validation_reason_code"]
        if reason_code not in STATIC_WEB_VALIDATION_REASON_CODES:
            raise ValueError("candidate validation diagnostics contain an invalid fixed validator reason")
        normalized_failure["validation_reason_code"] = reason_code

    if "validation_profile_digest" in raw:
        digest = raw["validation_profile_digest"]
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise ValueError("candidate validation diagnostics contain an invalid validation profile digest")
        normalized_failure["validation_profile_digest"] = digest

    normalized = {"candidate_validation_failure": normalized_failure}
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    if len(encoded.encode("utf-8")) > 4_096:
        raise ValueError("candidate validation diagnostics exceed durable evidence bound")
    return normalized


_CANDIDATE_GENERATION_FAILURE_KINDS = frozenset(
    {
        "RATE_LIMITED",
        "VALIDATION_EXHAUSTED",
        "PROVIDER_EXHAUSTED",
        "INCREMENTAL_PRECHECK_REJECTED",
    }
)
_CANDIDATE_GENERATION_REJECTION_CODES = frozenset(
    {*PROPOSAL_PREFLIGHT_REASON_CODES, "RETAINED_TARGET_REPEATED"}
)
_MAX_CANDIDATE_GENERATION_REJECTIONS = 16
_MAX_CANDIDATE_GENERATION_COUNT = 1_000


def _bounded_non_negative_int(
    value: object,
    name: str,
    *,
    maximum: int = _MAX_CANDIDATE_GENERATION_COUNT,
) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
        or value > maximum
    ):
        raise ValueError(f"{name} must be a bounded non-negative integer")
    return value


def _bounded_sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _bounded_candidate_rejection(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("candidate rejection diagnostics must be an object")
    required = {
        "work_unit_id",
        "agent_identity_digest",
        "generation",
        "canonical_source_mutated",
        "source_lineage_accepted",
        "git_mutation",
        "deployment_mutation",
        "review_completed",
        "validator_repair_attempt",
        "retained_patch_count",
        "rejected_patch_count",
        "rejection_reason_codes",
        "made_incremental_progress",
    }
    allowed = {*required, "failure_kind"}
    if set(value) - allowed or not required <= set(value):
        raise ValueError("candidate rejection diagnostics contain a non-admitted field")

    normalized: dict[str, object] = {
        "work_unit_id": _bounded_identity(value["work_unit_id"], "work_unit_id"),
        "agent_identity_digest": _bounded_sha256(
            value["agent_identity_digest"],
            "agent_identity_digest",
        ),
        "generation": _bounded_non_negative_int(value["generation"], "generation"),
        "retained_patch_count": _bounded_non_negative_int(
            value["retained_patch_count"],
            "retained_patch_count",
        ),
        "rejected_patch_count": _bounded_non_negative_int(
            value["rejected_patch_count"],
            "rejected_patch_count",
        ),
    }
    if normalized["generation"] < 1:
        raise ValueError("candidate rejection generation must be positive")

    failure_kind = value.get("failure_kind")
    if failure_kind is not None:
        if failure_kind not in _CANDIDATE_GENERATION_FAILURE_KINDS:
            raise ValueError(
                "candidate rejection diagnostics contain an invalid failure kind"
            )
        normalized["failure_kind"] = failure_kind

    reason_codes = value["rejection_reason_codes"]
    if (
        not isinstance(reason_codes, list)
        or len(reason_codes) > _MAX_CANDIDATE_GENERATION_REJECTIONS
    ):
        raise ValueError("candidate rejection reason codes exceed durable bound")
    if len(set(reason_codes)) != len(reason_codes):
        raise ValueError("candidate rejection reason codes must be unique")
    if any(code not in _CANDIDATE_GENERATION_REJECTION_CODES for code in reason_codes):
        raise ValueError(
            "candidate rejection diagnostics contain an invalid reason code"
        )
    normalized["rejection_reason_codes"] = list(reason_codes)

    for key in ("validator_repair_attempt", "made_incremental_progress"):
        flag = value[key]
        if not isinstance(flag, bool):
            raise ValueError("candidate rejection diagnostic state must be boolean")
        normalized[key] = flag

    for claim in (
        "canonical_source_mutated",
        "source_lineage_accepted",
        "git_mutation",
        "deployment_mutation",
        "review_completed",
    ):
        if value[claim] is not False:
            raise ValueError(
                "candidate rejection diagnostics asserted authority they do not own"
            )
        normalized[claim] = False
    return normalized


def _bounded_candidate_generation_failure_evidence(
    raw: object,
) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise ValueError("candidate generation diagnostics must be an object")
    allowed = {
        "reason_code",
        "rejection_count",
        "retained_patch_count",
        "rejected_patch_count",
        "rejection_reason_codes",
        "max_reassignments_per_work_unit",
        "validator_repair_attempted",
        "validator_repair_count",
        "validator_repair_limit",
        "rejections",
        "canonical_source_mutated",
        "source_lineage_accepted",
        "worker_process_loss",
    }
    required = {
        "reason_code",
        "rejection_count",
        "max_reassignments_per_work_unit",
        "validator_repair_attempted",
        "validator_repair_count",
        "validator_repair_limit",
        "rejections",
        "canonical_source_mutated",
        "source_lineage_accepted",
        "worker_process_loss",
    }
    if set(raw) - allowed or not required <= set(raw):
        raise ValueError(
            "candidate generation diagnostics contain a non-admitted field"
        )
    if raw["reason_code"] != "CANDIDATE_GENERATION_EXHAUSTED":
        raise ValueError("candidate generation diagnostics contain an invalid reason code")

    normalized_failure: dict[str, object] = {
        "reason_code": "CANDIDATE_GENERATION_EXHAUSTED",
        "rejection_count": _bounded_non_negative_int(
            raw["rejection_count"],
            "rejection_count",
        ),
        "max_reassignments_per_work_unit": _bounded_non_negative_int(
            raw["max_reassignments_per_work_unit"],
            "max_reassignments_per_work_unit",
            maximum=32,
        ),
        "validator_repair_count": _bounded_non_negative_int(
            raw["validator_repair_count"],
            "validator_repair_count",
            maximum=1,
        ),
        "validator_repair_limit": _bounded_non_negative_int(
            raw["validator_repair_limit"],
            "validator_repair_limit",
            maximum=1,
        ),
    }
    if normalized_failure["validator_repair_limit"] != 1:
        raise ValueError("candidate generation validator repair limit drifted")

    attempted = raw["validator_repair_attempted"]
    if (
        not isinstance(attempted, bool)
        or attempted is not (normalized_failure["validator_repair_count"] > 0)
    ):
        raise ValueError("candidate generation validator repair state drifted")
    normalized_failure["validator_repair_attempted"] = attempted

    for claim in (
        "canonical_source_mutated",
        "source_lineage_accepted",
        "worker_process_loss",
    ):
        if raw[claim] is not False:
            raise ValueError(
                "candidate generation diagnostics asserted authority they do not own"
            )
        normalized_failure[claim] = False

    for key in ("retained_patch_count", "rejected_patch_count"):
        if key in raw:
            normalized_failure[key] = _bounded_non_negative_int(raw[key], key)

    reason_codes = raw.get("rejection_reason_codes", [])
    if (
        not isinstance(reason_codes, list)
        or len(reason_codes) > _MAX_CANDIDATE_GENERATION_REJECTIONS
    ):
        raise ValueError("candidate generation reason codes exceed durable bound")
    if len(set(reason_codes)) != len(reason_codes):
        raise ValueError("candidate generation reason codes must be unique")
    if any(code not in _CANDIDATE_GENERATION_REJECTION_CODES for code in reason_codes):
        raise ValueError(
            "candidate generation diagnostics contain an invalid rejection reason code"
        )
    if "rejection_reason_codes" in raw:
        normalized_failure["rejection_reason_codes"] = list(reason_codes)

    rejections = raw["rejections"]
    if (
        not isinstance(rejections, list)
        or len(rejections) > _MAX_CANDIDATE_GENERATION_REJECTIONS
    ):
        raise ValueError("candidate generation rejections exceed durable bound")
    normalized_rejections = [_bounded_candidate_rejection(item) for item in rejections]
    if normalized_failure["rejection_count"] != len(normalized_rejections):
        raise ValueError("candidate generation rejection count drifted")
    normalized_failure["rejections"] = normalized_rejections

    normalized = {"candidate_generation_failure": normalized_failure}
    encoded = json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    if len(encoded.encode("utf-8")) > 12_288:
        raise ValueError("candidate generation diagnostics exceed durable evidence bound")
    return normalized


def _bounded_identity(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    clean = value.strip()
    if not clean or clean != value or len(clean) > 300 or any(ord(ch) < 32 for ch in clean):
        raise ValueError(f"{name} is invalid")
    return clean