from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from parallax_api.code.runtime_composition import production_durable_lineage_allocator
from parallax_api.code.source_context import BoundedSourceContextSelector, SourceContextError
from parallax_api.code.workspace_lineage import ProjectRunIdentity
from parallax_api.db import make_engine


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "c5b1d060-6a2f-4500-9f0b-a137a2931296"


def request_json(token: str, path: str, *, timeout: float = 60.0) -> Any:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raise RuntimeError(f"production diagnostic GET {path} failed with HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"production diagnostic GET {path} is unreachable") from exc


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "").strip().lower() != "preview":
        raise RuntimeError("lineage diagnostic is preview-only")
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN") or "").strip()
    if len(token) < 32:
        raise RuntimeError("Parallax preview access credential is unavailable")

    run = request_json(token, f"/v1/engineering-runs/{RUN_ID}")
    if not isinstance(run, dict) or not isinstance(run.get("project_id"), str):
        raise RuntimeError("production proof run identity is unavailable")
    specification = request_json(
        token,
        f"/v1/conversations/{run['conversation_id']}/work-specifications/approved",
    )
    if not isinstance(specification, dict):
        raise RuntimeError("production proof Work Specification is unavailable")

    engine = make_engine(environment="preview")
    materialization_root = Path(tempfile.gettempdir()) / "w4-lineage-readonly-diagnostic"
    allocator = production_durable_lineage_allocator(engine, materialization_root=materialization_root)
    if allocator is None:
        raise RuntimeError("production durable lineage allocator is unavailable")

    identity = ProjectRunIdentity(project_id=run["project_id"], run_id=RUN_ID)
    workspace = None
    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "project_bound": True,
        "run_state": run.get("state"),
    }
    try:
        lineage = allocator.current_lineage(identity)
        result.update({
            "current_lineage": True,
            "lineage_id": lineage.lineage_id,
            "lineage_file_count": len(lineage.files),
            "content_digest": lineage.content_digest,
        })
        workspace = allocator.resolve(identity)
        files = [path for path in workspace.path.rglob("*") if path.is_file() and not path.is_symlink()]
        result.update({
            "resolve": "PASS",
            "workspace_exists": workspace.path.exists(),
            "materialized_file_count": len(files),
        })
        try:
            context = BoundedSourceContextSelector().select(
                workspace.path,
                objective=str(specification.get("objective") or ""),
                acceptance_texts=tuple(str(item) for item in specification.get("acceptance_criteria", [])),
            )
            result.update({
                "source_context": "PASS",
                "source_context_file_count": len(context.files),
                "source_context_total_bytes": context.total_bytes,
            })
        except SourceContextError as exc:
            result.update({
                "source_context": "FAIL",
                "source_context_error_class": type(exc).__name__,
                "source_context_error": str(exc),
            })
    except Exception as exc:
        result.update({
            "resolve": "FAIL",
            "error_class": type(exc).__name__,
            "cause_class": type(exc.__cause__).__name__ if exc.__cause__ is not None else None,
        })
    finally:
        if workspace is not None:
            try:
                allocator.cleanup(workspace)
                result["cleanup"] = "PASS"
            except Exception as exc:
                result["cleanup"] = "FAIL"
                result["cleanup_error_class"] = type(exc).__name__
        engine.dispose()

    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("resolve") != "PASS" or result.get("source_context") != "PASS":
        raise RuntimeError("read-only production lineage/materialization diagnostic failed")
    raise RuntimeError("read-only production lineage/materialization diagnostic passed; stopping intentionally")


if __name__ == "__main__":
    main()
