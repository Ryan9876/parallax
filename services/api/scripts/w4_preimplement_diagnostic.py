from __future__ import annotations

import json
from pathlib import Path
import tempfile

from sqlalchemy.orm import sessionmaker

from parallax_api.code.implementation import ImplementationRequest
from parallax_api.code.implementation_runtime import ProtectedImplementationRuntime, RunProjectBinding
from parallax_api.code.patching import SourcePatch
from parallax_api.code.runtime_composition import AllocatorWorkspaceLineageGateway, production_durable_lineage_allocator
from parallax_api.code.source_context import SourceContextError
from parallax_api.db import make_engine
from parallax_api.intelligence.implementation_generation import AcceptanceRequirement, ImplementationGenerationRequest
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository
from parallax_api.code.service import EngineeringRunService


RUN_ID = "d99ae8c6-ebc0-42bf-aaa6-da5e436eda4e"


def _error_chain(exc: BaseException) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(result) < 8:
        seen.add(id(current))
        result.append({"type": type(current).__name__, "message": str(current)[:500]})
        current = current.__cause__ or current.__context__
    return result


def main() -> None:
    engine = make_engine(environment="preview")
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    materialization_root = Path(tempfile.gettempdir()) / "w4-preimplement-diagnostic"
    session = Session()
    gateway = None
    report: dict[str, object] = {
        "gate": "Wave 4 disposable pre-IMPLEMENT diagnostic",
        "run_id": RUN_ID,
        "durable_mutation": False,
        "lineage_acceptance": False,
    }
    try:
        service = EngineeringRunService(
            EngineeringRunRepository(session),
            ConversationRepository(session),
            WorkSpecificationRepository(session),
            ProjectRepository(session),
            owner_subject="break-glass",
            require_project_binding=True,
        )
        allocator = production_durable_lineage_allocator(engine, materialization_root=materialization_root)
        if allocator is None:
            raise RuntimeError("durable lineage allocator unavailable")
        gateway = AllocatorWorkspaceLineageGateway(allocator)
        runtime = ProtectedImplementationRuntime(service, RunProjectBinding(), gateway)

        run = service.get(RUN_ID)
        report.update({"state": run.state, "revision": run.revision})
        project_ref = runtime._project_ref(run)
        report["project_binding"] = "PASS"
        handle = runtime._workspace_handle(project_ref, run)
        report.update(
            {
                "workspace_resolution": "PASS",
                "base_source_lineage_ref": handle.source_lineage_ref,
            }
        )
        specification, contract, acceptance = runtime._bound_contract(run)
        report.update(
            {
                "work_specification_contract": "PASS",
                "acceptance_count": len(acceptance),
            }
        )
        try:
            source_context = runtime.source_selector.select(
                handle.workspace_root,
                objective=str(contract["objective"]),
                acceptance_texts=tuple(item["text"] for item in acceptance),
            )
        except SourceContextError:
            raise
        report.update(
            {
                "source_context": "PASS",
                "source_context_file_count": len(source_context.files),
                "source_context_total_bytes": source_context.total_bytes,
            }
        )

        request = ImplementationGenerationRequest(
            work_specification_id=specification.id,
            work_specification_revision=specification.revision,
            work_specification_digest=run.work_specification_digest or "",
            title=str(contract["title"]),
            objective=str(contract["objective"]),
            constraints=tuple(str(item) for item in contract["constraints"]),
            acceptance=tuple(AcceptanceRequirement(id=item["id"], text=item["text"]) for item in acceptance),
            source_context=source_context,
        )
        generation = runtime.generator.generate_sync(request)
        report.update(
            {
                "generation": "PASS",
                "generation_model": generation.model,
                "generation_attempt_count": len(generation.attempts),
                "proposal_patch_count": len(generation.proposal.patches),
                "proposal_paths": [item.path for item in generation.proposal.patches],
            }
        )

        implementation_request = ImplementationRequest(
            patches=tuple(
                SourcePatch(
                    path=item.path,
                    expected_base_sha256=item.expected_base_sha256,
                    unified_diff=item.unified_diff,
                )
                for item in generation.proposal.patches
            )
        )
        mutation = runtime.implementation_engine.apply(handle.workspace_root, implementation_request)
        artifacts = mutation.get("artifacts") if isinstance(mutation.get("artifacts"), list) else []
        report.update(
            {
                "safe_mutation": "PASS" if mutation.get("applied") is True else "FAIL",
                "artifact_count": len(artifacts),
                "artifact_paths": [item.get("path") for item in artifacts if isinstance(item, dict)],
            }
        )
    except Exception as exc:
        report["failure"] = _error_chain(exc)
    finally:
        if gateway is not None:
            try:
                gateway.cleanup_pending()
                report["workspace_cleanup"] = "PASS"
            except Exception as exc:
                report["workspace_cleanup"] = "FAIL"
                report["cleanup_failure"] = _error_chain(exc)
        session.close()
        engine.dispose()

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
