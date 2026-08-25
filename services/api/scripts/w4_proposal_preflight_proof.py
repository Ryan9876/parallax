from __future__ import annotations

import json
from pathlib import Path
import tempfile

from sqlalchemy.orm import sessionmaker

from parallax_api.code.implementation_runtime import ProtectedImplementationRuntime, RunProjectBinding
from parallax_api.code.runtime_composition import AllocatorWorkspaceLineageGateway, production_durable_lineage_allocator
from parallax_api.code.service import EngineeringRunService
from parallax_api.db import make_engine
from parallax_api.intelligence.implementation_generation import AcceptanceRequirement, ImplementationGenerationRequest
from parallax_api.projects.repository import ProjectRepository
from parallax_api.repositories.conversations import ConversationRepository
from parallax_api.repositories.engineering_runs import EngineeringRunRepository
from parallax_api.repositories.work_specifications import WorkSpecificationRepository


RUN_ID = "d99ae8c6-ebc0-42bf-aaa6-da5e436eda4e"


def main() -> None:
    engine = make_engine(environment="preview")
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    gateway = None
    report: dict[str, object] = {
        "gate": "Wave 4 production-shaped implementation proposal preflight proof",
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
        allocator = production_durable_lineage_allocator(
            engine,
            materialization_root=Path(tempfile.gettempdir()) / "w4-proposal-preflight-proof",
        )
        if allocator is None:
            raise RuntimeError("durable lineage allocator unavailable")
        gateway = AllocatorWorkspaceLineageGateway(allocator)
        runtime = ProtectedImplementationRuntime(service, RunProjectBinding(), gateway)

        run = service.get(RUN_ID)
        if run.state != "IMPLEMENT":
            raise RuntimeError(f"proof run is no longer at IMPLEMENT: {run.state}")
        initial_revision = run.revision
        project_ref = runtime._project_ref(run)
        handle = runtime._workspace_handle(project_ref, run)
        specification, contract, acceptance = runtime._bound_contract(run)
        source_context = runtime.source_selector.select(
            handle.workspace_root,
            objective=str(contract["objective"]),
            acceptance_texts=tuple(item["text"] for item in acceptance),
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

        def proposal_is_safe(proposal) -> bool:
            try:
                runtime.implementation_engine.validate(
                    handle.workspace_root,
                    runtime._implementation_request(proposal),
                )
            except Exception:
                return False
            return True

        generation = runtime.generator.generate_sync(request, proposal_validator=proposal_is_safe)
        implementation_request = runtime._implementation_request(generation.proposal)
        mutation = runtime.implementation_engine.apply(handle.workspace_root, implementation_request)
        if mutation.get("applied") is not True:
            raise RuntimeError("selected proposal did not pass disposable safe mutation")

        after = service.get(RUN_ID)
        if after.state != "IMPLEMENT" or after.revision != initial_revision:
            raise RuntimeError("disposable proof unexpectedly changed durable Engineering Run state")

        report.update(
            {
                "project_binding": "PASS",
                "workspace_resolution": "PASS",
                "work_specification_contract": "PASS",
                "source_context_file_count": len(source_context.files),
                "source_context_total_bytes": source_context.total_bytes,
                "selected_model": generation.model,
                "routing_attempts": [
                    {"model": item.model, "status": item.status, "error": item.error}
                    for item in generation.attempts
                ],
                "proposal_paths": [item.path for item in generation.proposal.patches],
                "safe_preflight": "PASS",
                "disposable_safe_mutation": "PASS",
                "artifact_paths": [
                    item.get("path") for item in mutation.get("artifacts", []) if isinstance(item, dict)
                ],
                "durable_run_unchanged": True,
            }
        )
    finally:
        if gateway is not None:
            gateway.cleanup_pending()
        session.close()
        engine.dispose()

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
