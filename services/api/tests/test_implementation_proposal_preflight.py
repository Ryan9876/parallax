from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from parallax_api.code.implementation import ImplementationRequest, SafeImplementationEngine
from parallax_api.code.patching import PatchFormatError, SourcePatch
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    GeneratedSourcePatch,
    ImplementationGenerationCoordinator,
    ImplementationGenerationRequest,
    ImplementationProposal,
)
from parallax_api.intelligence.router import ModelRouter


EMPTY_SHA256 = sha256(b"").hexdigest()
TARGET = "release-proof/w4-production-runtime-proof.txt"


def _proposal(*, valid: bool) -> ImplementationProposal:
    old_header = "--- /dev/null\n"
    new_header = f"+++ b/{TARGET}\n" if valid else f"+++ {TARGET}\n"
    return ImplementationProposal(
        acceptance_ids_covered=["AC-01"],
        patches=[
            GeneratedSourcePatch(
                path=TARGET,
                expected_base_sha256=EMPTY_SHA256,
                unified_diff=(
                    old_header
                    + new_header
                    + "@@ -0,0 +1 @@\n"
                    + "+W4 production runtime proof.\n"
                ),
            )
        ],
    )


def _request() -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id="ws-release-proof",
        work_specification_revision=1,
        work_specification_digest="a" * 64,
        title="Production runtime proof",
        objective="Create one bounded release-proof artifact.",
        constraints=("Do not broaden filesystem authority.",),
        acceptance=(AcceptanceRequirement("AC-01", "The bounded proof artifact is created."),),
        source_context=SourceContextSnapshot(
            files=(),
            digest="0" * 64,
            total_bytes=0,
            excluded_secret_files=0,
            omitted_bounded_files=0,
        ),
    )


def _implementation_request(proposal: ImplementationProposal) -> ImplementationRequest:
    return ImplementationRequest(
        patches=tuple(
            SourcePatch(
                path=item.path,
                expected_base_sha256=item.expected_base_sha256,
                unified_diff=item.unified_diff,
            )
            for item in proposal.patches
        )
    )


def test_safe_engine_validate_is_side_effect_free_and_rejects_malformed_diff(tmp_path: Path):
    (tmp_path / "release-proof").mkdir()
    engine = SafeImplementationEngine()

    with pytest.raises(PatchFormatError):
        engine.validate(tmp_path, _implementation_request(_proposal(valid=False)))

    assert not (tmp_path / TARGET).exists()

    engine.validate(tmp_path, _implementation_request(_proposal(valid=True)))
    assert not (tmp_path / TARGET).exists()


def test_router_retries_when_schema_valid_candidate_fails_safe_patch_preflight(tmp_path: Path):
    (tmp_path / "release-proof").mkdir()
    engine = SafeImplementationEngine()
    seen: list[str] = []

    class Program:
        version = "preflight-regression-v1"

        def __init__(self, model: str):
            self.model = model

        def run(self, *, request):
            seen.append(self.model)
            return _proposal(valid=self.model != "luna")

    def proposal_validator(proposal: ImplementationProposal) -> bool:
        try:
            engine.validate(tmp_path, _implementation_request(proposal))
        except Exception:
            return False
        return True

    coordinator = ImplementationGenerationCoordinator(
        router=ModelRouter(models=("luna", "terra", "sol")),
        program_factory=Program,
    )
    result = coordinator.generate_sync(_request(), proposal_validator=proposal_validator)

    assert result.model == "terra"
    assert seen == ["luna", "terra"]
    assert [attempt.status for attempt in result.attempts] == ["validation_failed", "ok"]
    assert not (tmp_path / TARGET).exists()
