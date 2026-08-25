from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from parallax_api.code.implementation import ImplementationRequest, SafeImplementationEngine
from parallax_api.code.patching import SourcePatch
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


def _safe_error_message(exc: BaseException) -> str:
    text = str(exc).strip()
    return text[:240] if text else type(exc).__name__


def main() -> None:
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or "").strip()
    if not token:
        raise RuntimeError("generator diagnostic requires existing Parallax access credential")

    run = _get_json(token, f"/v1/engineering-runs/{RUN_ID}")
    if not isinstance(run, dict):
        raise RuntimeError("production run is unavailable")
    specification = _get_json(token, f"/v1/conversations/{run['conversation_id']}/work-specifications/approved")
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

    identity = ProjectRunIdentity(project_id=str(run["project_id"]), run_id=RUN_ID)
    context_workspace = None
    try:
        context_workspace = allocator.resolve(identity)
        context = BoundedSourceContextSelector().select(
            context_workspace.path,
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

        selected_paths = {item.path for item in context.files}
        results: list[dict[str, object]] = []
        for model in MODEL_ORDER:
            apply_workspace = None
            try:
                program = DspyImplementationGenerationProgram(model)
                proposal = program.run(request=request)
                targets = [item.path for item in proposal.patches]
                result: dict[str, object] = {
                    "model": model,
                    "generation": "ok",
                    "patch_count": len(proposal.patches),
                    "acceptance_count": len(proposal.acceptance_ids_covered),
                    "exact_acceptance_coverage": tuple(proposal.acceptance_ids_covered) == request.required_acceptance_ids,
                    "targets": [
                        {
                            "path": path,
                            "suffix": Path(path).suffix.casefold() or None,
                            "selected_context": path in selected_paths,
                        }
                        for path in targets
                    ],
                }
                try:
                    apply_workspace = allocator.resolve(identity)
                    mutation_request = ImplementationRequest(
                        patches=tuple(
                            SourcePatch(
                                path=item.path,
                                expected_base_sha256=item.expected_base_sha256,
                                unified_diff=item.unified_diff,
                            )
                            for item in proposal.patches
                        )
                    )
                    mutation = SafeImplementationEngine().apply(apply_workspace.path, mutation_request)
                    result.update(
                        {
                            "safe_patch": "ok" if mutation.get("applied") is True else "rejected",
                            "artifact_count": len(mutation.get("artifacts") or []),
                            "protected_stage_authority": mutation.get("protected_stage_authority"),
                        }
                    )
                except Exception as exc:
                    result.update(
                        {
                            "safe_patch": "failed",
                            "safe_patch_error_chain": _cause_chain(exc),
                            "safe_patch_error": _safe_error_message(exc),
                        }
                    )
                results.append(result)
            except Exception as exc:
                results.append({"model": model, "generation": "failed", "error_chain": _cause_chain(exc)})
            finally:
                if apply_workspace is not None:
                    allocator.cleanup(apply_workspace)

        print(
            json.dumps(
                {
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
                },
                indent=2,
                sort_keys=True,
            )
        )
    finally:
        if context_workspace is not None:
            allocator.cleanup(context_workspace)
        engine.dispose()

    raise RuntimeError("safe patch rejection diagnostic stops intentionally")


if __name__ == "__main__":
    main()
