from __future__ import annotations

from hashlib import sha256
import json
import os

from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    DspyImplementationGenerationProgram,
    ImplementationGenerationRequest,
)
from parallax_api.intelligence.router import MODEL_ORDER


def _cause_chain(exc: BaseException) -> list[str]:
    result: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(result) < 6:
        seen.add(id(current))
        result.append(type(current).__name__)
        current = current.__cause__ or current.__context__
    return result


def main() -> None:
    raw = b"value = 1\n"
    source_file = SourceContextFile(
        path="example.py",
        sha256=sha256(raw).hexdigest(),
        size=len(raw),
        content=raw.decode("utf-8"),
    )
    context = SourceContextSnapshot(
        files=(source_file,),
        digest=sha256(b"synthetic-w4-generator-diagnostic").hexdigest(),
        total_bytes=len(raw),
        excluded_secret_files=0,
        omitted_bounded_files=0,
    )
    request = ImplementationGenerationRequest(
        work_specification_id="synthetic-diagnostic",
        work_specification_revision=1,
        work_specification_digest=sha256(b"synthetic-spec").hexdigest(),
        title="Synthetic generator connectivity diagnostic",
        objective="Change the example value from 1 to 2.",
        constraints=("Modify only example.py.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="example.py contains value = 2"),),
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
        "configuration": {
            "dspy_api_key_present": bool((os.getenv("DSPY_API_KEY") or "").strip()),
            "openai_api_key_present": bool((os.getenv("OPENAI_API_KEY") or "").strip()),
            "dspy_api_base_present": bool((os.getenv("DSPY_API_BASE") or "").strip()),
            "dspy_model_type": (os.getenv("DSPY_MODEL_TYPE") or "").strip() or None,
            "local_development": os.getenv("DSPY_LOCAL_DEVELOPMENT") == "1",
        },
        "models": results,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    raise RuntimeError("synthetic generator diagnostic stops intentionally")


if __name__ == "__main__":
    main()
