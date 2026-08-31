from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing replacement anchor in {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def insert_before(path: str, marker: str, content: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if marker not in text:
        raise SystemExit(f"missing insertion marker in {path}: {marker[:100]!r}")
    target.write_text(text.replace(marker, content + marker, 1), encoding="utf-8")


# Protected server-owned safe-preflight reason seam.
replace_once(
    "services/api/parallax_api/code/implementation_runtime.py",
    "from .implementation import ImplementationError, ImplementationRequest, SafeImplementationEngine\n"
    "from .model_patch_canonicalization import CanonicalizingTextPatchEngine\n"
    "from .patching import PatchError, SourcePatch\n",
    "from .implementation import (\n"
    "    DuplicateTargetError,\n"
    "    ImplementationError,\n"
    "    ImplementationLimitError,\n"
    "    ImplementationRequest,\n"
    "    SafeImplementationEngine,\n"
    "    TargetHierarchyConflictError,\n"
    ")\n"
    "from .model_patch_canonicalization import CanonicalizingTextPatchEngine\n"
    "from .patching import (\n"
    "    PatchConflictError,\n"
    "    PatchError,\n"
    "    PatchFormatError,\n"
    "    PatchLimitError,\n"
    "    SourcePatch,\n"
    "    StaleBaseError,\n"
    "    UnsafeTargetError,\n"
    ")\n",
)

insert_before(
    "services/api/parallax_api/code/implementation_runtime.py",
    "class CanonicalProjectBinding(Protocol):\n",
    '''PROPOSAL_PREFLIGHT_REASON_CODES = frozenset(
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


''',
)

replace_once(
    "services/api/parallax_api/code/implementation_runtime.py",
    '''        def proposal_is_safe(proposal: ImplementationProposal) -> bool:
            try:
                self.implementation_engine.validate(
                    handle.workspace_root,
                    self._implementation_request(proposal),
                )
            except (ImplementationError, PatchError, OSError):
                return False
            return True

        controller_evidence: dict[str, object] | None = None
''',
    '''        proposal_is_safe = ProposalSafetyPreflight(
            self.implementation_engine,
            handle.workspace_root,
        )

        controller_evidence: dict[str, object] | None = None
''',
)

# Candidate recovery imports/version.
replace_once(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    '''from ..intelligence.implementation_generation import (
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
''',
    '''from ..intelligence.implementation_generation import (
    GeneratedSourcePatch,
    ImplementationGenerationFailure,
    ImplementationGenerationRequest,
    ImplementationProposal,
    validate_implementation_proposal,
)
''',
)
replace_once(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    'CANDIDATE_RECOVERY_VERSION = "candidate-recovery-v0.23.26"\n',
    'CANDIDATE_RECOVERY_VERSION = "candidate-recovery-v0.23.27"\n',
)

replace_once(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    "_BOUNDED_ROUTING_FAILURES = frozenset(item.value for item in RoutingFailureKind)\n\n\n@dataclass(frozen=True, slots=True)\nclass CandidateRejection:\n",
    '''_BOUNDED_ROUTING_FAILURES = frozenset(item.value for item in RoutingFailureKind)
INCREMENTAL_PRECHECK_REJECTED = "INCREMENTAL_PRECHECK_REJECTED"
RETAINED_TARGET_REPEATED = "RETAINED_TARGET_REPEATED"
TARGET_HIERARCHY_CONFLICT = "TARGET_HIERARCHY_CONFLICT"
_MAX_CONVERGENCE_FEEDBACK_ITEMS = 16


@dataclass(frozen=True, slots=True)
class IncrementalPatchRejection:
    path: str | None
    reason_code: str


@dataclass(frozen=True, slots=True)
class IncrementalConvergenceResult:
    proposal: ImplementationProposal | None
    rejections: tuple[IncrementalPatchRejection, ...]
    retained_patch_count: int
    rejected_patch_count: int
    made_progress: bool
    converged: bool


def _bounded_feedback_path(path: str) -> str | None:
    if (
        not isinstance(path, str)
        or not path
        or len(path) > 240
        or path.strip() != path
        or path.startswith("/")
        or "\\\\" in path
        or any(ord(ch) < 32 for ch in path)
    ):
        return None
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        return None
    return path


def _target_hierarchy_conflict(path: str, other: str) -> bool:
    if path == other:
        return False
    left = tuple(path.split("/"))
    right = tuple(other.split("/"))
    short, long = (left, right) if len(left) < len(right) else (right, left)
    return long[: len(short)] == short


def classify_incremental_proposal(
    proposal: ImplementationProposal,
    *,
    retained_paths: tuple[str, ...],
    proposal_preflight_reason: Callable[[ImplementationProposal], str | None],
) -> tuple[tuple[GeneratedSourcePatch, ...], tuple[IncrementalPatchRejection, ...]]:
    """Split one canonical proposal into independently safe new patches and bounded rejections."""

    reserved = {path for path in retained_paths if _bounded_feedback_path(path) is not None}
    accepted: list[GeneratedSourcePatch] = []
    accepted_paths: set[str] = set()
    rejections: list[IncrementalPatchRejection] = []
    acceptance = list(proposal.acceptance_ids_covered)

    for patch in proposal.patches:
        feedback_path = _bounded_feedback_path(patch.path)
        if feedback_path is None:
            one = ImplementationProposal(acceptance_ids_covered=acceptance, patches=[patch])
            reason = proposal_preflight_reason(one) or "UNSAFE_TARGET"
            rejections.append(IncrementalPatchRejection(None, reason))
            continue
        if feedback_path in reserved:
            rejections.append(IncrementalPatchRejection(feedback_path, RETAINED_TARGET_REPEATED))
            continue
        if feedback_path in accepted_paths:
            rejections.append(IncrementalPatchRejection(feedback_path, "DUPLICATE_TARGET"))
            continue
        if any(
            _target_hierarchy_conflict(feedback_path, other)
            for other in (*reserved, *accepted_paths)
        ):
            rejections.append(IncrementalPatchRejection(feedback_path, TARGET_HIERARCHY_CONFLICT))
            continue
        one = ImplementationProposal(acceptance_ids_covered=acceptance, patches=[patch])
        reason = proposal_preflight_reason(one)
        if reason is not None:
            rejections.append(IncrementalPatchRejection(feedback_path, reason))
            continue
        accepted.append(patch)
        accepted_paths.add(feedback_path)

    return tuple(accepted), tuple(rejections)


class IncrementalProposalAccumulator:
    """Retain independently safe candidate intent without granting source authority."""

    def __init__(
        self,
        *,
        acceptance_ids: tuple[str, ...],
        proposal_preflight_reason: Callable[[ImplementationProposal], str | None],
    ) -> None:
        self.acceptance_ids = acceptance_ids
        self.proposal_preflight_reason = proposal_preflight_reason
        self._retained: dict[str, GeneratedSourcePatch] = {}

    @property
    def retained_paths(self) -> tuple[str, ...]:
        return tuple(sorted(self._retained))

    def evaluate(
        self,
        proposal: ImplementationProposal,
        *,
        reserved_paths: tuple[str, ...] = (),
    ) -> IncrementalConvergenceResult:
        accepted, rejections = classify_incremental_proposal(
            proposal,
            retained_paths=tuple(sorted({*reserved_paths, *self._retained})),
            proposal_preflight_reason=self.proposal_preflight_reason,
        )
        if not accepted:
            return IncrementalConvergenceResult(
                proposal=None,
                rejections=rejections,
                retained_patch_count=len(self._retained),
                rejected_patch_count=len(rejections),
                made_progress=False,
                converged=False,
            )

        combined = ImplementationProposal(
            acceptance_ids_covered=list(self.acceptance_ids),
            patches=[*self._retained.values(), *accepted],
        )
        combined_reason = self.proposal_preflight_reason(combined)
        if combined_reason is not None:
            combined_rejections = (*rejections, IncrementalPatchRejection(None, combined_reason))
            return IncrementalConvergenceResult(
                proposal=None,
                rejections=tuple(combined_rejections),
                retained_patch_count=len(self._retained),
                rejected_patch_count=len(combined_rejections),
                made_progress=False,
                converged=False,
            )

        for patch in accepted:
            self._retained[patch.path] = patch
        converged = not rejections
        final = (
            ImplementationProposal(
                acceptance_ids_covered=list(self.acceptance_ids),
                patches=list(self._retained.values()),
            )
            if converged
            else None
        )
        return IncrementalConvergenceResult(
            proposal=final,
            rejections=rejections,
            retained_patch_count=len(self._retained),
            rejected_patch_count=len(rejections),
            made_progress=True,
            converged=converged,
        )


def convergence_guided_candidate_request(
    request: ImplementationGenerationRequest,
    *,
    retained_paths: tuple[str, ...],
    rejections: tuple[IncrementalPatchRejection, ...],
) -> ImplementationGenerationRequest:
    """Add bounded server-owned convergence facts without copying source or generated content."""

    bounded_retained = sorted(
        {
            path
            for path in retained_paths[:_MAX_CONVERGENCE_FEEDBACK_ITEMS]
            if _bounded_feedback_path(path) is not None
        }
    )
    bounded_rejections: list[dict[str, str]] = []
    for rejection in rejections[:_MAX_CONVERGENCE_FEEDBACK_ITEMS]:
        item = {"reason_code": rejection.reason_code}
        if rejection.path is not None:
            path = _bounded_feedback_path(rejection.path)
            if path is not None:
                item["path"] = path
        bounded_rejections.append(item)
    if not bounded_retained and not bounded_rejections:
        return request

    summary = json.dumps(
        {"retained_targets": bounded_retained, "rejections": bounded_rejections},
        sort_keys=True,
        separators=(",", ":"),
    )
    constraint = (
        "Server-owned incremental IMPLEMENT convergence state: "
        f"{summary}. Do not repeat retained targets. Repair only semantic path/content intent needed to satisfy the "
        "approved acceptance criteria. Return only typed path/content intent; patch mechanics remain server-owned."
    )
    if constraint in request.constraints:
        return request
    return replace(request, constraints=(*request.constraints, constraint))


def _convergence_ref(
    *,
    retained_patch_count: int,
    rejections: tuple[IncrementalPatchRejection, ...],
    made_progress: bool,
) -> str:
    projection = {
        "retained_patch_count": retained_patch_count,
        "rejected_patch_count": len(rejections),
        "reason_codes": sorted(rejection.reason_code for rejection in rejections),
        "made_progress": made_progress,
    }
    digest = sha256(
        json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"convergence:{digest}"


@dataclass(frozen=True, slots=True)
class CandidateRejection:
''',
)

replace_once(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    '''class CandidateRejection:
    work_unit_id: str
    agent_identity_digest: str
    generation: int
    failure_kind: str | None = None
    validator_repair_attempt: bool = False

    def as_dict(self) -> dict[str, object]:
        evidence: dict[str, object] = {
            "work_unit_id": self.work_unit_id,
            "agent_identity_digest": self.agent_identity_digest,
            "generation": self.generation,
            "canonical_source_mutated": False,
            "source_lineage_accepted": False,
            "git_mutation": False,
            "deployment_mutation": False,
            "review_completed": False,
            "validator_repair_attempt": self.validator_repair_attempt,
        }
        if self.failure_kind is not None:
            evidence["failure_kind"] = self.failure_kind
        return evidence
''',
    '''class CandidateRejection:
    work_unit_id: str
    agent_identity_digest: str
    generation: int
    failure_kind: str | None = None
    validator_repair_attempt: bool = False
    retained_patch_count: int = 0
    rejected_patch_count: int = 0
    rejection_reason_codes: tuple[str, ...] = ()
    made_incremental_progress: bool = False

    def as_dict(self) -> dict[str, object]:
        evidence: dict[str, object] = {
            "work_unit_id": self.work_unit_id,
            "agent_identity_digest": self.agent_identity_digest,
            "generation": self.generation,
            "canonical_source_mutated": False,
            "source_lineage_accepted": False,
            "git_mutation": False,
            "deployment_mutation": False,
            "review_completed": False,
            "validator_repair_attempt": self.validator_repair_attempt,
            "retained_patch_count": max(0, self.retained_patch_count),
            "rejected_patch_count": max(0, self.rejected_patch_count),
            "rejection_reason_codes": list(self.rejection_reason_codes[:_MAX_CONVERGENCE_FEEDBACK_ITEMS]),
            "made_incremental_progress": self.made_incremental_progress,
        }
        if self.failure_kind is not None:
            evidence["failure_kind"] = self.failure_kind
        return evidence
''',
)

recovery_path = Path("services/api/parallax_api/code/agentic_candidate_recovery.py")
recovery_text = recovery_path.read_text(encoding="utf-8")
class_index = recovery_text.index("class ResilientLiveAgenticControlPlane(LiveAgenticControlPlane):")
method_start = recovery_text.index("    def _proposal_for_plan(\n", class_index)
method_end = recovery_text.index("\n\ndef build_resilient_live_agentic_runtime_composition(", method_start)
new_method = r'''    def _proposal_for_plan(
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
        run = self.service.get(plan.identity.run_id)
        lineage = self._lineage(run)
        lease = self.worker_bridge.acquire(run_id=run.id)
        generation_by_work_unit = {unit.unit_id: lease.generation for unit in plan.graph.units}
        completed: set[str] = set()
        patches = []
        covered: list[str] = []
        attempts: list[AttemptRecord] = []
        models: list[str] = []
        result_digests: list[str] = []
        task_digests: list[str] = []
        seen_paths: set[str] = set()
        last_unit_id = plan.graph.units[0].unit_id
        rejections: list[CandidateRejection] = []
        reasoner = getattr(proposal_validator, "reason", None)
        incremental_enabled = callable(reasoner)

        try:
            while len(completed) < len(plan.graph.units):
                schedule = schedule_team_plan(
                    plan,
                    completed_work_units=tuple(completed),
                    generation_by_work_unit=generation_by_work_unit,
                )
                ready = schedule.ready
                if not ready:
                    raise AgenticRuntimeError("agent team schedule made no progress")
                progress = False
                for scheduled_assignment in ready:
                    if scheduled_assignment.work_unit_id in completed:
                        continue
                    unit = plan.graph.get(scheduled_assignment.work_unit_id)
                    last_unit_id = unit.unit_id
                    assignment = scheduled_assignment
                    attempted_agents: list[str] = []
                    rejection_count = 0
                    validator_rejected_agent_digests: list[str] = []
                    validator_repair_count = 0
                    previous_failure_kind: str | None = None
                    last_incremental_rejections: tuple[IncrementalPatchRejection, ...] = ()
                    accumulator = (
                        IncrementalProposalAccumulator(
                            acceptance_ids=unit.acceptance_ids,
                            proposal_preflight_reason=reasoner,
                        )
                        if incremental_enabled
                        else None
                    )

                    while True:
                        agent_digest = assignment.agent_identity_digest or ""
                        attempted_agents.append(agent_digest)
                        task = create_agent_task_request(
                            plan,
                            assignment,
                            source_context=AgentSourceContext(
                                lineage_id=request.source_context.digest,
                                revision_id=f"source:{request.source_context.digest[:24]}",
                            ),
                        )
                        lease = self.worker_bridge.checkpoint(
                            lease,
                            plan=plan,
                            work_unit_id=unit.unit_id,
                            source_lineage_ref=lineage.lineage_id,
                            step="AGENT_DISPATCH",
                            evidence_refs=(f"task:{task.digest}", f"assignment:{assignment.attempt_id}"),
                            state=WorkerLifecycleState.PROGRESSING,
                        )
                        subrequest = self._subrequest(
                            request,
                            unit.acceptance_ids,
                            alternative_round=alternative_round,
                        )
                        subrequest = validator_guided_candidate_request(subrequest, previous_failure_kind)
                        if accumulator is not None:
                            subrequest = convergence_guided_candidate_request(
                                subrequest,
                                retained_paths=accumulator.retained_paths,
                                rejections=last_incremental_rejections,
                            )
                        if assignment.reason_code == CANDIDATE_VALIDATION_REPAIR:
                            subrequest, repair_context_token = final_validator_repair_request(
                                subrequest,
                                run_revision=run.revision,
                                work_unit_id=unit.unit_id,
                                generation=assignment.generation,
                            )
                            logger.info(
                                "parallax_final_validator_repair_dispatch generation=%s context=%s",
                                assignment.generation,
                                repair_context_token,
                            )
                        adapter = self._adapter(agent_digest)
                        try:
                            generation_validator = (
                                (lambda _proposal: True) if accumulator is not None else proposal_validator
                            )
                            result, generation = adapter.generate(
                                task,
                                subrequest,
                                proposal_validator=generation_validator,
                            )
                        except ImplementationGenerationFailure as exc:
                            rejection_count += 1
                            failure_kind = candidate_generation_failure_kind(exc)
                            rejections.append(
                                CandidateRejection(
                                    work_unit_id=unit.unit_id,
                                    agent_identity_digest=agent_digest,
                                    generation=assignment.generation,
                                    failure_kind=failure_kind,
                                    validator_repair_attempt=(assignment.reason_code == CANDIDATE_VALIDATION_REPAIR),
                                    retained_patch_count=(len(accumulator.retained_paths) if accumulator is not None else 0),
                                )
                            )
                            if failure_kind == RoutingFailureKind.VALIDATION_EXHAUSTED.value:
                                validator_rejected_agent_digests.append(agent_digest)
                            lease = self.worker_bridge.checkpoint(
                                lease,
                                plan=plan,
                                work_unit_id=unit.unit_id,
                                source_lineage_ref=lineage.lineage_id,
                                step="CANDIDATE_REJECTED",
                                evidence_refs=(f"candidate-rejected:{agent_digest}", f"assignment:{assignment.attempt_id}"),
                                state=WorkerLifecycleState.PROGRESSING,
                            )
                            replacement = candidate_recovery_assignment(
                                plan,
                                assignment,
                                attempted_agent_digests=tuple(attempted_agents),
                                rejection_count=rejection_count,
                            )
                            repair_selected = False
                            if replacement is None:
                                replacement = validator_repair_assignment(
                                    plan,
                                    assignment,
                                    validator_rejected_agent_digests=tuple(validator_rejected_agent_digests),
                                    repair_count=validator_repair_count,
                                )
                                if replacement is not None:
                                    validator_repair_count += 1
                                    repair_selected = True
                            if replacement is None:
                                self._mark_candidate_exhausted(run_id=run.id)
                                raise ImplementationGenerationFailure(
                                    "all bounded admitted implementation candidates were rejected",
                                    diagnostic_evidence={
                                        "candidate_generation_failure": {
                                            "reason_code": CANDIDATE_GENERATION_EXHAUSTED,
                                            "rejection_count": rejection_count,
                                            "max_reassignments_per_work_unit": plan.limits.max_reassignments_per_work_unit,
                                            "validator_repair_attempted": validator_repair_count > 0,
                                            "validator_repair_count": validator_repair_count,
                                            "validator_repair_limit": MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
                                            "rejections": [item.as_dict() for item in rejections],
                                            "canonical_source_mutated": False,
                                            "source_lineage_accepted": False,
                                            "worker_process_loss": False,
                                        }
                                    },
                                )
                            previous_failure_kind = (
                                RoutingFailureKind.VALIDATION_EXHAUSTED.value if repair_selected else failure_kind
                            )
                            assignment = replacement
                            generation_by_work_unit[unit.unit_id] = replacement.generation
                            continue

                        if accumulator is not None:
                            convergence = accumulator.evaluate(
                                generation.proposal,
                                reserved_paths=tuple(sorted(seen_paths)),
                            )
                            if not convergence.converged:
                                last_incremental_rejections = convergence.rejections
                                rejection_count += 1
                                validator_rejected_agent_digests.append(agent_digest)
                                reason_codes = tuple(sorted({item.reason_code for item in convergence.rejections}))
                                rejections.append(
                                    CandidateRejection(
                                        work_unit_id=unit.unit_id,
                                        agent_identity_digest=agent_digest,
                                        generation=assignment.generation,
                                        failure_kind=INCREMENTAL_PRECHECK_REJECTED,
                                        validator_repair_attempt=(assignment.reason_code == CANDIDATE_VALIDATION_REPAIR),
                                        retained_patch_count=convergence.retained_patch_count,
                                        rejected_patch_count=convergence.rejected_patch_count,
                                        rejection_reason_codes=reason_codes,
                                        made_incremental_progress=convergence.made_progress,
                                    )
                                )
                                if convergence.made_progress:
                                    attempts.extend(generation.attempts)
                                    models.append(generation.model)
                                    result_digests.append(result.digest)
                                    task_digests.append(task.digest)
                                lease = self.worker_bridge.checkpoint(
                                    lease,
                                    plan=plan,
                                    work_unit_id=unit.unit_id,
                                    source_lineage_ref=lineage.lineage_id,
                                    step=("CANDIDATE_PARTIAL_PROGRESS" if convergence.made_progress else "CANDIDATE_REJECTED"),
                                    evidence_refs=(
                                        f"assignment:{assignment.attempt_id}",
                                        _convergence_ref(
                                            retained_patch_count=convergence.retained_patch_count,
                                            rejections=convergence.rejections,
                                            made_progress=convergence.made_progress,
                                        ),
                                    ),
                                    state=WorkerLifecycleState.PROGRESSING,
                                )
                                replacement = candidate_recovery_assignment(
                                    plan,
                                    assignment,
                                    attempted_agent_digests=tuple(attempted_agents),
                                    rejection_count=rejection_count,
                                )
                                repair_selected = False
                                if replacement is None:
                                    replacement = validator_repair_assignment(
                                        plan,
                                        assignment,
                                        validator_rejected_agent_digests=tuple(validator_rejected_agent_digests),
                                        repair_count=validator_repair_count,
                                    )
                                    if replacement is not None:
                                        validator_repair_count += 1
                                        repair_selected = True
                                if replacement is None:
                                    self._mark_candidate_exhausted(run_id=run.id)
                                    raise ImplementationGenerationFailure(
                                        "incremental IMPLEMENT convergence exhausted the bounded candidate budget",
                                        diagnostic_evidence={
                                            "candidate_generation_failure": {
                                                "reason_code": CANDIDATE_GENERATION_EXHAUSTED,
                                                "rejection_count": rejection_count,
                                                "retained_patch_count": convergence.retained_patch_count,
                                                "rejected_patch_count": convergence.rejected_patch_count,
                                                "rejection_reason_codes": list(reason_codes),
                                                "max_reassignments_per_work_unit": plan.limits.max_reassignments_per_work_unit,
                                                "validator_repair_attempted": validator_repair_count > 0,
                                                "validator_repair_count": validator_repair_count,
                                                "validator_repair_limit": MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
                                                "rejections": [item.as_dict() for item in rejections],
                                                "canonical_source_mutated": False,
                                                "source_lineage_accepted": False,
                                                "worker_process_loss": False,
                                            }
                                        },
                                    )
                                previous_failure_kind = RoutingFailureKind.VALIDATION_EXHAUSTED.value
                                assignment = replacement
                                generation_by_work_unit[unit.unit_id] = replacement.generation
                                continue
                            if convergence.proposal is None:
                                raise AgenticRuntimeError("incremental convergence claimed success without a proposal")
                            generation = replace(generation, proposal=convergence.proposal)

                        admission = admit_assignment_result(
                            plan,
                            assignment,
                            expected_task=task,
                            result=result,
                            current_generation=assignment.generation,
                        )
                        if not admission.admitted:
                            raise AgenticRuntimeError(f"agent result admission failed: {admission.reason_code}")
                        observe_admitted_result(plan, assignment, admission=admission, result=result)
                        if result.status is not AgentLifecycleStatus.COMPLETED:
                            raise AgenticRuntimeError(f"admitted agent did not complete work: {result.reason_code}")
                        if tuple(generation.proposal.acceptance_ids_covered) != unit.acceptance_ids:
                            raise AgenticRuntimeError("agent proposal acceptance ownership drifted")
                        for patch in generation.proposal.patches:
                            if patch.path in seen_paths:
                                raise AgenticRuntimeError("multi-agent proposal overlap requires human coordination")
                            seen_paths.add(patch.path)
                            patches.append(patch)
                        covered.extend(unit.acceptance_ids)
                        attempts.extend(generation.attempts)
                        models.append(generation.model)
                        result_digests.append(result.digest)
                        task_digests.append(task.digest)
                        lease = self.worker_bridge.checkpoint(
                            lease,
                            plan=plan,
                            work_unit_id=unit.unit_id,
                            source_lineage_ref=lineage.lineage_id,
                            step="AGENT_RESULT",
                            evidence_refs=(f"task:{task.digest}", f"result:{result.digest}"),
                        )
                        completed.add(unit.unit_id)
                        progress = True
                        break

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
            if not proposal_validator(proposal):
                raise AgenticRuntimeError("combined incrementally converged proposal failed final safe preflight")
            self.worker_bridge.checkpoint(
                lease,
                plan=plan,
                work_unit_id=last_unit_id,
                source_lineage_ref=lineage.lineage_id,
                step="AGENT_PROPOSAL",
                evidence_refs=(f"proposal:{proposal.digest()}",),
            )
            return (
                proposal,
                tuple(attempts),
                tuple(models),
                tuple(result_digests),
                tuple(task_digests),
            )
        except ImplementationGenerationFailure:
            raise
        except Exception:
            self.worker_bridge.stop_bounded(run_id=run.id)
            raise
'''
recovery_path.write_text(recovery_text[:method_start] + new_method + recovery_text[method_end:], encoding="utf-8")

replace_once(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    '''    "CandidateRejection",
    "FINAL_VALIDATOR_REPAIR_GUIDANCE",
    "ResilientLiveAgenticControlPlane",
''',
    '''    "CandidateRejection",
    "IncrementalConvergenceResult",
    "IncrementalPatchRejection",
    "IncrementalProposalAccumulator",
    "FINAL_VALIDATOR_REPAIR_GUIDANCE",
    "INCREMENTAL_PRECHECK_REJECTED",
    "RETAINED_TARGET_REPEATED",
    "ResilientLiveAgenticControlPlane",
''',
)
replace_once(
    "services/api/parallax_api/code/agentic_candidate_recovery.py",
    '''    "candidate_generation_failure_kind",
    "candidate_recovery_assignment",
    "final_validator_repair_context_token",
''',
    '''    "candidate_generation_failure_kind",
    "candidate_recovery_assignment",
    "classify_incremental_proposal",
    "convergence_guided_candidate_request",
    "final_validator_repair_context_token",
''',
)

print("P2-V0.23.27 runtime patch applied")
