from __future__ import annotations

from pathlib import Path


TARGET = Path("services/api/parallax_api/code/agentic_runtime.py")


def replace_exact(text: str, before: str, after: str, *, label: str) -> str:
    count = text.count(before)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one protected source match, found {count}")
    return text.replace(before, after, 1)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_exact(
        text,
        "from parallax_api.execution_environment import execution_snapshot_id\n",
        "from parallax_api.execution_environment import execution_snapshot_id_for_profile\n",
        label="execution environment import",
    )

    before_constructor = '''    def __init__(
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
'''
    after_constructor = '''    def __init__(
        self,
        *,
        registry: ProtectedCommandRegistry | None = None,
        policy: ProtectedCommandPolicy | None = None,
        project_id: str | None = None,
        snapshot_id: str | None = None,
        dotnet_snapshot_id: str | None = None,
    ) -> None:
        self.registry = registry or ProtectedCommandRegistry()
        self.policy = policy or ProtectedCommandPolicy()
        self.project_id = project_id or os.getenv("VERCEL_PROJECT_ID")
        self.common_snapshot_id = snapshot_id
        self.dotnet_snapshot_id = dotnet_snapshot_id
        try:
            if snapshot_id is not None:
                execution_snapshot_id_for_profile("python-v1", common_explicit=snapshot_id)
            if dotnet_snapshot_id is not None:
                execution_snapshot_id_for_profile("dotnet-v1", dotnet_explicit=dotnet_snapshot_id)
        except ValueError as exc:
            raise AgenticRuntimeError("server-owned execution snapshot identity is invalid") from exc
'''
    text = replace_exact(text, before_constructor, after_constructor, label="candidate executor constructor")

    before_resolution = '''        if not self.project_id:
            raise AgenticRuntimeError("Vercel project identity is unavailable for candidate validation")

        session, NetworkPolicy, SnapshotSource, sandbox = self._sdk()
        snapshot_source = SnapshotSource(snapshot_id=self.snapshot_id)
        stage_evidence: list[tuple[str, dict[str, object]]] = []
'''
    after_resolution = '''        if not self.project_id:
            raise AgenticRuntimeError("Vercel project identity is unavailable for candidate validation")

        try:
            selected_snapshot_id = execution_snapshot_id_for_profile(
                profile.profile_id.value,
                common_explicit=self.common_snapshot_id,
                dotnet_explicit=self.dotnet_snapshot_id,
            )
        except ValueError:
            failure_spec = profile.spec_for(
                WorkflowStage.BUILD,
                operation_key=f"{operation_key[:120]}:candidate:snapshot",
            )
            evidence = _bounded_evidence(
                failure_spec,
                exit_code=None,
                duration_ms=0,
                stdout="",
                stderr="EXECUTION_PROFILE_UNAVAILABLE",
            )
            evidence.update(
                {
                    "dependency_preparation_required": profile.preparation is not None,
                    "dependency_preparation_succeeded": False,
                    "dependency_preparation_code": "EXECUTION_PROFILE_UNAVAILABLE",
                    "dependency_preparation_duration_ms": 0,
                    "dependency_probe_exit_code": None,
                    "dependency_prepare_exit_code": None,
                    "validation_network_locked": False,
                    "candidate_content_digest": content_digest,
                    "candidate_file_count": len(files),
                    "candidate_total_bytes": total_bytes,
                    "validation_profile_id": profile.profile_id.value,
                    "validation_profile_digest": profile.digest,
                    "execution_snapshot_verified": False,
                    "network_policy": "not-created",
                    "candidate_is_canonical_lineage": False,
                    "accepts_source_lineage": False,
                }
            )
            return CandidateValidationResult(
                content_digest=content_digest,
                file_count=len(files),
                total_bytes=total_bytes,
                validation_profile_id=profile.profile_id.value,
                validation_profile_digest=profile.digest,
                stage_evidence=((WorkflowStage.BUILD.value, evidence),),
            )

        session, NetworkPolicy, SnapshotSource, sandbox = self._sdk()
        snapshot_source = SnapshotSource(snapshot_id=selected_snapshot_id)
        stage_evidence: list[tuple[str, dict[str, object]]] = []
'''
    text = replace_exact(text, before_resolution, after_resolution, label="candidate profile snapshot resolution")

    remaining = text.count("self.snapshot_id")
    if remaining != 3:
        raise RuntimeError(f"candidate snapshot references: expected 3 remaining matches, found {remaining}")
    text = text.replace("self.snapshot_id", "selected_snapshot_id")

    TARGET.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
