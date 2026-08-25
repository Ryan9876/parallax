from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    ImplementationGenerationRequest,
    SOURCE_CONTEXT_AUTHORITY_RULE,
)


def test_server_provided_source_satisfies_file_provision_precondition_without_relaxing_contract():
    source = SourceContextSnapshot(
        files=(SourceContextFile("apps/client/src/App.tsx", "a" * 64, 12, "export {};\n"),),
        digest="b" * 64,
        total_bytes=12,
        excluded_secret_files=0,
        omitted_bounded_files=0,
    )
    request = ImplementationGenerationRequest(
        work_specification_id="spec-1",
        work_specification_revision=1,
        work_specification_digest="c" * 64,
        title="Animate logo",
        objective="Animate the Parallax logo.",
        constraints=(
            "Repository files must be provided before implementation can proceed.",
            "Preserve the existing visual language.",
        ),
        acceptance=(AcceptanceRequirement("AC-01", "The logo animates."),),
        source_context=source,
    )

    source_payload = request.source_prompt_payload()
    assert source_payload["runtime_source_access"] == "SERVER_PROVIDED_PROTECTED_SOURCE"
    assert source_payload["runtime_source_authority_rule"] == SOURCE_CONTEXT_AUTHORITY_RULE
    assert source_payload["files"] == [
        {
            "path": "apps/client/src/App.tsx",
            "sha256": "a" * 64,
            "size": 12,
            "content": "export {};\n",
        }
    ]
    assert "constraints" not in source_payload
    assert "must be provided" in request.contract_payload()["constraints"][0]
    assert "substantive Work Specification constraints" in SOURCE_CONTEXT_AUTHORITY_RULE
