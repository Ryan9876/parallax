from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import sys
from time import monotonic
from uuid import NAMESPACE_URL, uuid5


_SCRIPT_ROOT = Path(__file__).resolve().parent
_API_ROOT = _SCRIPT_ROOT.parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from parallax_api.code.agentic_runtime_live import DurableCandidateArtifactStore
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    GeneratedSourcePatch,
    ImplementationGeneration,
    ImplementationGenerationRequest,
    ImplementationProposal,
)


_ACTIVATION_ENV = "PARALLAX_AGENTIC_RUNTIME_ENABLED"
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_EMPTY_SHA256 = sha256(b"").hexdigest()


@dataclass(frozen=True, slots=True)
class AgenticArtifactCanary:
    project_id: str
    run_id: str
    work_specification_id: str
    work_specification_digest: str
    source_context_digest: str
    base_source_lineage_ref: str
    base_revision: str
    plan_id: str
    routing_digest: str
    competition_digest: str


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _deployment_sha() -> str:
    value = (os.getenv("VERCEL_GIT_COMMIT_SHA") or "").strip().lower()
    if _SHA_RE.fullmatch(value) is None:
        raise RuntimeError("production agentic preflight requires exact Vercel Git revision")
    return value


def _canary(deployment_sha: str) -> AgenticArtifactCanary:
    if _SHA_RE.fullmatch(deployment_sha) is None:
        raise ValueError("agentic canary deployment revision is invalid")
    stem = f"parallax:agentic-runtime-preflight:{deployment_sha}"
    return AgenticArtifactCanary(
        project_id=str(uuid5(NAMESPACE_URL, f"{stem}:project")),
        run_id=str(uuid5(NAMESPACE_URL, f"{stem}:run")),
        work_specification_id=str(uuid5(NAMESPACE_URL, f"{stem}:work-spec")),
        work_specification_digest=_digest(f"{stem}:work-spec-digest"),
        source_context_digest=_digest(f"{stem}:source-context"),
        base_source_lineage_ref="src:" + _digest(f"{stem}:lineage"),
        base_revision=_digest(f"{stem}:base-revision"),
        plan_id=_digest(f"{stem}:plan"),
        routing_digest=_digest(f"{stem}:routing"),
        competition_digest=_digest(f"{stem}:competition"),
    )


def _request(canary: AgenticArtifactCanary) -> ImplementationGenerationRequest:
    return ImplementationGenerationRequest(
        work_specification_id=canary.work_specification_id,
        work_specification_revision=1,
        work_specification_digest=canary.work_specification_digest,
        title="Production agentic durable replay canary",
        objective="Prove private immutable selected-candidate persistence and exact replay binding.",
        constraints=(
            "The canary must not accept source lineage, transition an Engineering Run, deploy, or complete REVIEW.",
        ),
        acceptance=(
            AcceptanceRequirement(
                id="AC-01",
                text="Persist and restore the exact bounded selected-candidate artifact.",
            ),
        ),
        source_context=SourceContextSnapshot(
            files=(),
            digest=canary.source_context_digest,
            total_bytes=0,
            excluded_secret_files=0,
            omitted_bounded_files=0,
        ),
    )


def _generation() -> ImplementationGeneration:
    proposal = ImplementationProposal(
        acceptance_ids_covered=["AC-01"],
        patches=[
            GeneratedSourcePatch(
                path="agentic-preflight-canary.txt",
                expected_base_sha256=_EMPTY_SHA256,
                unified_diff=(
                    "--- /dev/null\n"
                    "+++ b/agentic-preflight-canary.txt\n"
                    "@@ -0,0 +1 @@\n"
                    "+parallax-agentic-runtime-preflight\n"
                ),
            )
        ],
    )
    return ImplementationGeneration(
        proposal=proposal,
        model="preflight/no-provider-call",
        attempts=(),
        program_version="agentic-runtime-preflight-v1",
    )


def exercise_candidate_artifact_store(
    store: DurableCandidateArtifactStore,
    deployment_sha: str,
) -> str:
    """Persist and restore one deterministic non-authoritative candidate canary."""

    canary = _canary(deployment_sha)
    request = _request(canary)
    generation = _generation()
    controller_evidence: dict[str, object] = {
        "selected_proposal_digest": generation.proposal.digest(),
        "routing_record_digest": canary.routing_digest,
        "competition_record_digest": canary.competition_digest,
        "source_lineage_accepted": False,
        "engineering_run_transitioned": False,
        "review_completed": False,
        "production_deployed": False,
    }
    artifact_digest = store.persist(
        generation=generation,
        controller_evidence=controller_evidence,
        project_ref=canary.project_id,
        run_id=canary.run_id,
        work_specification_id=canary.work_specification_id,
        work_specification_revision=1,
        work_specification_digest=canary.work_specification_digest,
        acceptance_ids=("AC-01",),
        plan_id=canary.plan_id,
        base_source_lineage_ref=canary.base_source_lineage_ref,
        base_revision=canary.base_revision,
        source_context_digest=canary.source_context_digest,
    )
    restored, evidence = store.restore(
        artifact_digest,
        request=request,
        project_ref=canary.project_id,
        run_id=canary.run_id,
        plan_id=canary.plan_id,
        base_source_lineage_ref=canary.base_source_lineage_ref,
        base_revision=canary.base_revision,
    )
    if restored.proposal.digest() != generation.proposal.digest():
        raise RuntimeError("agentic candidate artifact proposal round-trip mismatch")
    if restored.model != generation.model or restored.program_version != generation.program_version:
        raise RuntimeError("agentic candidate artifact generation identity mismatch")
    if evidence != controller_evidence:
        raise RuntimeError("agentic candidate artifact controller evidence mismatch")
    for field in (
        "source_lineage_accepted",
        "engineering_run_transitioned",
        "review_completed",
        "production_deployed",
    ):
        if evidence.get(field) is not False:
            raise RuntimeError("agentic candidate artifact canary asserted forbidden authority")
    return artifact_digest


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(
            "Production agentic runtime preflight: SKIP "
            f"(VERCEL_ENV={environment}; production activation proof not required)"
        )
        return
    if os.getenv(_ACTIVATION_ENV) != "1":
        print(
            "Production agentic runtime preflight: FAIL "
            "(activation flag is not exact 1)",
            file=sys.stderr,
        )
        raise SystemExit(1)

    started = monotonic()
    stage = "deployment-identity"
    try:
        deployment_sha = _deployment_sha()
        stage = "candidate-artifact-round-trip"
        artifact_digest = exercise_candidate_artifact_store(
            DurableCandidateArtifactStore(),
            deployment_sha,
        )
    except Exception as exc:
        print(
            "Production agentic runtime preflight: FAIL "
            f"(stage={stage}; error={type(exc).__name__})",
            file=sys.stderr,
        )
        raise SystemExit(1) from None

    elapsed_ms = int((monotonic() - started) * 1000)
    print(
        "Production agentic runtime preflight: PASS "
        f"(artifact={artifact_digest[:12]}; elapsed_ms={elapsed_ms}; exact_round_trip_verified)"
    )


if __name__ == "__main__":
    main()
