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
from .implementation import ImplementationError, ImplementationRequest, SafeImplementationEngine
from .patching import PatchError, SourcePatch
from .service import EngineeringRunService, RunOperationResult
from .source_context import BoundedSourceContextSelector, SourceContextError
from .state_machine import RevisionConflict
from .work_spec_binding import acceptance_map, work_specification_contract, work_specification_digest


class ImplementationRuntimeError(RuntimeError):
    def __init__(self, message: str, *, mutation_applied: bool = False) -> None:
        super().__init__(message)
        self.mutation_applied = mutation_applied


class ProjectBindingError(ImplementationRuntimeError):
    pass


class WorkspaceLineageError(ImplementationRuntimeError):
    pass


class ImplementationContractError(ImplementationRuntimeError):
    pass


class ImplementationMutationError(ImplementationRuntimeError):
    pass


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
        self.implementation_engine = implementation_engine or SafeImplementationEngine()

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

        def proposal_is_safe(proposal: ImplementationProposal) -> bool:
            try:
                self.implementation_engine.validate(
                    handle.workspace_root,
                    self._implementation_request(proposal),
                )
            except (ImplementationError, PatchError, OSError):
                return False
            return True

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
        except (ImplementationGenerationFailure, TypeError, ValueError) as exc:
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


def _bounded_identity(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    clean = value.strip()
    if not clean or clean != value or len(clean) > 300 or any(ord(ch) < 32 for ch in clean):
        raise ValueError(f"{name} is invalid")
    return clean
