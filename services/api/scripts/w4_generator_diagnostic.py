from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from parallax_api.code.runtime_composition import production_durable_lineage_allocator
from parallax_api.code.source_context import BoundedSourceContextSelector
from parallax_api.code.workspace_lineage import ProjectRunIdentity
from parallax_api.db import make_engine
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    DspyImplementationGenerationProgram,
    ImplementationGenerationRequest,
)
from parallax_api.intelligence.router import MODEL_ORDER


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "3720afc8-3109-456e-895d-f4e81fd16a44"


def _get_json(token: str, path: str) -> Any:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=60) as response:  # noqa: S310 - fixed production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raise RuntimeError(f"production diagnostic GET {path} failed with HTTP {exc.code}") from exc


def _cause_chain(exc: BaseException) -> list[str]:
    result: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(result) < 8:
        seen.add(id(current))
        result.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    return result


def main() -> None:
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("generator diagnostic requires existing Parallax access credential")

    run = _get_json(token, f"/v1/engineering-runs/{RUN_ID}")
    if not isinstance(run, dict):
        raise RuntimeError("production run is unavailable")
    specification = _get_json(
        token,
        f"/v1/conversations/{run['conversation_id']}/work-specifications/approved",
    )
    if not isinstance(specification, dict):
        raise RuntimeError("approved Work Specification is unavailable")

    acceptance_raw = run.get("acceptance_criteria")
    if not isinstance(acceptance_raw, list) or not acceptance_raw:
        raise RuntimeError("bound acceptance map is unavailable")
    acceptance = tuple(
        AcceptanceRequirement(id=str(item["id"]), text=str(item["text"]))
        for item in acceptance_raw
        if isinstance(item, dict) and item.get("id") and item.get("text")
    )
    if len(acceptance) != len(acceptance_raw):
        raise RuntimeError("bound acceptance map is malformed")

    engine = make_engine(environment="preview")
    allocator = production_durable_lineage_allocator(
        engine,
        materialization_root=Path(tempfile.gettempdir()) / "w4-exact-generator-diagnostic",
    )
    if allocator is None:
        raise RuntimeError("durable lineage allocator is unavailable")

    workspace = None
    try:
        identity = ProjectRunIdentity(project_id=str(run["project_id"]), run_id=RUN_ID)
        workspace = allocator.resolve(identity)
        context = BoundedSourceContextSelector().select(
            workspace.path,
            objective=str(specification.get("objective") or ""),
            acceptance_texts=tuple(item.text for item in acceptance),
        )
        request = ImplementationGenerationRequest(
            work_specification_id=str(run["work_specification_id"]),
            work_specification_revision=int(run["work_specification_revision"]),
            work_specification_digest=str(run["work_specification_digest"]),
            title=str(specification.get("title") or ""),
            objective=str(specification.get("objective") or ""),
            constraints=tuple(str(item) for item in specification.get("constraints", [])),
            acceptance=acceptance,
            source_context=context,
        )

        results: list[dict[str, object]] = []
        for model in MODEL_ORDER:
            try:
                program = DspyImplementationGenerationProgram(model)
                proposal = program.run(request=request)
                results.append(
                    {
                        "model": model,
                        "status": "ok",
                        "patch_count": len(proposal.patches),
                        "acceptance_count": len(proposal.acceptance_ids_covered),
                        "exact_acceptance_coverage": tuple(proposal.acceptance_ids_covered) == request.required_acceptance_ids,
                    }
                )
            except Exception as exc:
                results.append(
                    {
                        "model": model,
                        "status": "failed",
                        "error_chain": _cause_chain(exc),
                    }
                )

        output = {
            "run_id": RUN_ID,
            "run_state": run.get("state"),
            "source_context": {
                "file_count": len(context.files),
                "total_bytes": context.total_bytes,
                "omitted_bounded_files": context.omitted_bounded_files,
                "excluded_secret_files": context.excluded_secret_files,
            },
            "acceptance_count": len(acceptance),
            "models": results,
        }
        print(json.dumps(output, indent=2, sort_keys=True))
    finally:
        if workspace is not None:
            allocator.cleanup(workspace)
        engine.dispose()

    raise RuntimeError("exact production generator diagnostic stops intentionally")


if __name__ == "__main__":
    main()
