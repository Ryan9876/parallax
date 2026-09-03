from __future__ import annotations

from hashlib import sha256
import logging

from ..models import EngineeringRun
from ..tools.providers import (
    ACTION_BRANCH_CREATE,
    ACTION_COMMIT_WRITE,
    ACTION_PREVIEW_CREATE,
    ACTION_PREVIEW_READ,
    ACTION_PULL_REQUEST_CREATE,
    ACTION_PULL_REQUEST_READ,
    GITHUB_TOOL,
    VERCEL_TOOL,
    AcceptedSourceLineage,
    ProviderActionFailed,
    ProviderInvocation,
    VercelPreviewStatus,
)
from .greenfield_github import (
    ACTION_REPOSITORY_INITIALIZE_EMPTY,
    ACTION_REPOSITORY_INSPECT,
    GreenfieldGitHubActions,
)
from .greenfield_lineage import GREENFIELD_SOURCE_KIND, greenfield_source_ref
from .production_source_projection import ProjectedRepositoryLineageBootstrap
from .source_delivery_composition import (
    BootstrapResult,
    ProviderActionAuditPair,
    VerifiedDeliveryError,
    VerifiedDeliveryResult,
    VerifiedLineageDelivery,
)
from .workspace_allocator import MaterializedWorkspace
from .workspace_lineage import LineageIdentityError, LineageNotFoundError, ProjectRunIdentity, SourceLineage


REPOSITORY_AUTHORIZATION_REQUIRED = "REPOSITORY_AUTHORIZATION_REQUIRED"
_UNCLASSIFIED_PROVIDER_FAILURE = "UNCLASSIFIED_PROVIDER_FAILURE"

logger = logging.getLogger(__name__)


class RepositoryAuthorizationRequiredError(RuntimeError):
    """Exact-repository provider permission must be granted outside runtime."""


def _provider_result_code(error: BaseException) -> str | None:
    current: BaseException | None = error
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        if isinstance(current, ProviderActionFailed):
            code = current.audit.result_code or current.evidence.result_status
            return code if isinstance(code, str) and code else None
        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, BaseException) else None
    return None


def _log_greenfield_repository_inspection_failure(error: BaseException) -> str:
    """Emit only server-owned event text plus a protected normalized result code."""

    result_code = _provider_result_code(error) or _UNCLASSIFIED_PROVIDER_FAILURE
    logger.warning(
        "greenfield_repository_inspection_failed result_code=%s",
        result_code,
    )
    return result_code


def is_repository_authorization_required(error: BaseException) -> bool:
    if isinstance(error, RepositoryAuthorizationRequiredError):
        return True
    current: BaseException | None = error
    seen: set[int] = set()
    for _ in range(8):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        if isinstance(current, RepositoryAuthorizationRequiredError):
            return True
        if _provider_result_code(current) == REPOSITORY_AUTHORIZATION_REQUIRED:
            return True
        next_error = current.__cause__ or current.__context__
        current = next_error if isinstance(next_error, BaseException) else None
    return False


def _invocation(capability_id: str, action: str, operation_key: str) -> ProviderInvocation:
    request_digest = sha256(f"{operation_key}|github|{action}".encode("utf-8")).hexdigest()[:48]
    return ProviderInvocation(
        request_id=f"request:{request_digest}",
        capability_id=capability_id,
        actor_ref="actor:parallax-runtime",
    )


class GreenfieldProjectedRepositoryLineageBootstrap(ProjectedRepositoryLineageBootstrap):
    """Preserve public-first source bootstrap and add positive empty fallback."""

    def __init__(self, *, greenfield: GreenfieldGitHubActions, github_capability_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.greenfield = greenfield
        self.github_capability_id = github_capability_id

    def ensure(self, run: EngineeringRun, *, operation_key: str) -> BootstrapResult:
        try:
            return super().ensure(run, operation_key=operation_key)
        except Exception as source_error:
            identity = self.identity_for_run(run)
            try:
                current = self.allocator.current_lineage(identity)
            except (LineageIdentityError, LineageNotFoundError):
                current = None
            except Exception:
                raise source_error
            if current is not None:
                raise source_error

            binding = self.projects.resolve(identity.project_id)
            try:
                inspected = self.greenfield.inspect_repository(
                    binding,
                    _invocation(
                        self.github_capability_id,
                        ACTION_REPOSITORY_INSPECT,
                        f"{operation_key}:greenfield-inspect",
                    ),
                ).value
            except Exception as inspection_error:
                _log_greenfield_repository_inspection_failure(inspection_error)
                if is_repository_authorization_required(inspection_error):
                    raise RepositoryAuthorizationRequiredError(
                        "Repository authorization is required before Parallax can continue."
                    ) from inspection_error
                raise source_error

            if not inspected.is_empty:
                raise source_error

            initialize_greenfield = getattr(self.allocator, "initialize_greenfield", None)
            if not callable(initialize_greenfield):
                raise RuntimeError("durable allocator does not support greenfield roots") from source_error
            workspace: MaterializedWorkspace | None = None
            try:
                workspace = initialize_greenfield(
                    identity,
                    source_ref=greenfield_source_ref(binding.repository_ref, inspected.default_branch),
                )
                lineage = workspace.lineage
                if (
                    lineage.project_id != identity.project_id
                    or lineage.run_id != identity.run_id
                    or lineage.parent_lineage_id is not None
                    or lineage.source_kind != GREENFIELD_SOURCE_KIND
                    or lineage.source_ref_digest is None
                    or lineage.file_count != 0
                    or lineage.total_bytes != 0
                    or lineage.files != ()
                ):
                    raise RuntimeError("initialized greenfield lineage violates root contract")
                return BootstrapResult(identity=identity, lineage=lineage, initialized=True)
            finally:
                if workspace is not None:
                    self.allocator.cleanup(workspace)


class GreenfieldVerifiedLineageDelivery(VerifiedLineageDelivery):
    """Add REVIEW-only empty baseline initialization without changing ordinary delivery."""

    def __init__(self, *, greenfield: GreenfieldGitHubActions, github_capability_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.greenfield = greenfield
        self.github_capability_id = github_capability_id

    def _root_lineage(self, identity: ProjectRunIdentity, accepted: SourceLineage) -> SourceLineage:
        lineage = accepted
        seen = {lineage.lineage_id}
        for _ in range(128):
            parent = lineage.parent_lineage_id
            if parent is None:
                if lineage.source_kind not in {"repository", GREENFIELD_SOURCE_KIND} or lineage.source_ref_digest is None:
                    raise VerifiedDeliveryError("accepted lineage does not descend from an admitted source root")
                return lineage
            if parent in seen:
                raise VerifiedDeliveryError("source lineage contains a parent cycle")
            seen.add(parent)
            lineage = self._reconstruct_lineage(identity, parent)
        raise VerifiedDeliveryError("source lineage ancestry exceeds protected traversal bound")

    def _delivery_base(
        self,
        *,
        binding,
        delivery_key: str,
        provenance_digest: str,
    ) -> tuple[str, str, list[ProviderActionAuditPair]]:
        inspected = self.greenfield.inspect_repository(
            binding,
            _invocation(
                self.github_capability_id,
                ACTION_REPOSITORY_INSPECT,
                f"{delivery_key}:greenfield-inspect",
            ),
        )
        actions: list[ProviderActionAuditPair] = [self._paired(inspected)]
        state = inspected.value
        if state.is_empty or state.is_canonical_baseline_candidate:
            baseline = self.greenfield.initialize_empty_baseline(
                binding,
                _invocation(
                    self.github_capability_id,
                    ACTION_REPOSITORY_INITIALIZE_EMPTY,
                    f"{delivery_key}:greenfield-baseline",
                ),
                provenance_digest=provenance_digest,
            )
            actions.append(self._paired(baseline))
            return baseline.value.default_branch, baseline.value.baseline_revision, actions
        if state.is_commit_bearing_empty:
            if state.head_revision is None:
                raise VerifiedDeliveryError("commit-bearing empty repository is missing its exact head")
            return state.default_branch, state.head_revision, actions
        raise VerifiedDeliveryError(
            "greenfield repository default branch became non-empty before accepted-source publication"
        )

    def deliver(self, run: EngineeringRun, *, operation_key: str) -> VerifiedDeliveryResult:
        if not isinstance(operation_key, str) or not operation_key.strip():
            raise VerifiedDeliveryError("delivery operation key is required")
        identity = self._identity(run)
        accepted_lineage_id = self._verified_lineage_id(run, identity)
        try:
            current = self.allocator.current_lineage(identity)
        except Exception as exc:
            raise VerifiedDeliveryError("current durable source lineage is unavailable") from exc
        if current.lineage_id != accepted_lineage_id:
            raise VerifiedDeliveryError("current durable lineage moved after verified implementation")

        replay = self.resolve_record(run, accepted_lineage_id=accepted_lineage_id)
        if replay is not None:
            if replay.content_digest != current.content_digest:
                raise VerifiedDeliveryError("durable delivery record content no longer matches accepted lineage")
            return replay

        accepted, root, files = self._accepted_commit_files(identity, accepted_lineage_id)
        if root.source_kind != GREENFIELD_SOURCE_KIND:
            return super().deliver(run, operation_key=operation_key)
        if accepted.content_digest != current.content_digest:
            raise VerifiedDeliveryError("accepted lineage content digest changed")

        binding = self.projects.resolve(identity.project_id)
        delivery_key = self._delivery_operation_key(identity, accepted.lineage_id)
        provenance_digest = sha256(
            f"{identity.project_id}|{identity.run_id}|{root.lineage_id}|{root.source_ref_digest}".encode("utf-8")
        ).hexdigest()
        base_branch, base_revision, actions = self._delivery_base(
            binding=binding,
            delivery_key=delivery_key,
            provenance_digest=provenance_digest,
        )
        expected_root_digest = sha256(
            greenfield_source_ref(binding.repository_ref, base_branch).encode("utf-8")
        ).hexdigest()
        if expected_root_digest != root.source_ref_digest:
            raise VerifiedDeliveryError("greenfield repository identity changed after durable lineage bootstrap")

        lineage = AcceptedSourceLineage(
            project_id=identity.project_id,
            run_id=identity.run_id,
            lineage_id=accepted.lineage_id,
            content_digest=accepted.content_digest,
        )
        branch_name = f"parallax/{identity.project_id[:8]}-{identity.run_id[:8]}"
        branch = self.github.create_branch(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_BRANCH_CREATE, f"{delivery_key}:branch"),
            branch_name=branch_name,
            base_revision=base_revision,
        )
        actions.append(self._paired(branch))
        commit = self.github.commit_accepted_lineage(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_COMMIT_WRITE, f"{delivery_key}:commit"),
            branch_name=branch_name,
            expected_parent_revision=base_revision,
            lineage=lineage,
            files=files,
        )
        actions.append(self._paired(commit))
        pull_request = self.github.create_pull_request(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_PULL_REQUEST_CREATE, f"{delivery_key}:pr-create"),
            head_branch=branch_name,
            expected_head_revision=commit.value.commit_revision,
            base_branch=base_branch,
            lineage=lineage,
            title="Parallax verified app-builder change",
            body=(
                f"Verified Parallax lineage `{accepted.lineage_id}` for Engineering Run `{identity.run_id}`. "
                "Operator review is required; this PR is not a production promotion."
            ),
        )
        actions.append(self._paired(pull_request))
        read_pull_request = self.github.read_pull_request(
            binding,
            self._invocation(GITHUB_TOOL, ACTION_PULL_REQUEST_READ, f"{delivery_key}:pr-read"),
            number=pull_request.value.number,
        )
        actions.append(self._paired(read_pull_request))
        if (
            read_pull_request.value.state != "OPEN"
            or read_pull_request.value.head_branch != branch_name
            or read_pull_request.value.head_revision != commit.value.commit_revision
            or read_pull_request.value.base_branch != base_branch
        ):
            raise VerifiedDeliveryError("GitHub pull request read-back did not match exact verified source")

        target = self.preview_targets.resolve(binding)
        if target.project_ref != identity.project_id or target.repository_ref != binding.repository_ref:
            raise VerifiedDeliveryError("Vercel Preview target does not match canonical Project repository")
        preview = self.vercel.create_preview(
            target,
            self._invocation(VERCEL_TOOL, ACTION_PREVIEW_CREATE, f"{delivery_key}:preview-create"),
            source_revision=commit.value.commit_revision,
            branch_name=branch_name,
            lineage=lineage,
        )
        actions.append(self._paired(preview))
        read_preview = self.vercel.read_preview(
            target,
            self._invocation(VERCEL_TOOL, ACTION_PREVIEW_READ, f"{delivery_key}:preview-read"),
            deployment_id=preview.value.deployment_id,
            expected_source_revision=commit.value.commit_revision,
        )
        actions.append(self._paired(read_preview))
        if read_preview.value.status in {VercelPreviewStatus.ERROR, VercelPreviewStatus.CANCELED}:
            raise VerifiedDeliveryError("Vercel Preview entered a terminal non-success state")

        result = VerifiedDeliveryResult(
            project_id=identity.project_id,
            run_id=identity.run_id,
            repository_identity_digest=binding.repository_identity_digest,
            lineage_id=accepted.lineage_id,
            content_digest=accepted.content_digest,
            branch_name=branch_name,
            commit_revision=commit.value.commit_revision,
            pull_request_number=read_pull_request.value.number,
            pull_request_url=read_pull_request.value.url,
            preview_deployment_id=read_preview.value.deployment_id,
            preview_status=read_preview.value.status.value,
            preview_url=read_preview.value.url,
            actions=tuple(actions),
            replayed=False,
        )
        persisted, record_replayed = self.records.persist(
            run=run,
            lineage_id=accepted.lineage_id,
            payload=result.to_record(),
        )
        if record_replayed:
            return VerifiedDeliveryResult.from_record(persisted, replayed=True)
        return result


__all__ = [
    "GreenfieldProjectedRepositoryLineageBootstrap",
    "GreenfieldVerifiedLineageDelivery",
    "REPOSITORY_AUTHORIZATION_REQUIRED",
    "RepositoryAuthorizationRequiredError",
    "is_repository_authorization_required",
]
