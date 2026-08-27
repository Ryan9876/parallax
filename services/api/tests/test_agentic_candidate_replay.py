from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from parallax_api.code.agentic_runtime import AgenticRuntimeError
from parallax_api.code.agentic_runtime_live import (
    DurableAgentWorkerBridge,
    DurableCandidateArtifactStore,
)
from parallax_api.code.lineage_persistence import InMemoryImmutableObjectStore
from parallax_api.code.source_context import SourceContextSnapshot
from parallax_api.code.worker_recovery import WorkerLifecycleState
from parallax_api.intelligence.implementation_generation import (
    AcceptanceRequirement,
    GeneratedSourcePatch,
    ImplementationGeneration,
    ImplementationGenerationRequest,
    ImplementationProposal,
)


PROJECT_ID = "11111111-1111-1111-1111-111111111111"
RUN_ID = "22222222-2222-2222-2222-222222222222"
WORK_SPEC_ID = "33333333-3333-3333-3333-333333333333"
WORK_SPEC_DIGEST = "a" * 64
SOURCE_DIGEST = "b" * 64
LINEAGE_ID = "src:" + "c" * 64
PLAN_ID = "d" * 64


def request_for_replay(*, work_specification_digest: str = WORK_SPEC_DIGEST):
    return ImplementationGenerationRequest(
        work_specification_id=WORK_SPEC_ID,
        work_specification_revision=1,
        work_specification_digest=work_specification_digest,
        title="Durable replay",
        objective="Replay the exact selected candidate.",
        constraints=("Keep canonical source authority unchanged.",),
        acceptance=(AcceptanceRequirement(id="AC-01", text="Update app.py."),),
        source_context=SourceContextSnapshot(
            files=(),
            digest=SOURCE_DIGEST,
            total_bytes=0,
            excluded_secret_files=0,
            omitted_bounded_files=0,
        ),
    )


def selected_generation():
    proposal = ImplementationProposal(
        acceptance_ids_covered=["AC-01"],
        patches=[
            GeneratedSourcePatch(
                path="app.py",
                expected_base_sha256="e" * 64,
                unified_diff="--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n",
            )
        ],
    )
    return ImplementationGeneration(
        proposal=proposal,
        model="openai/gpt-5.6-luna",
        attempts=(),
        program_version="agentic-runtime-v0.19.7:test",
    )


def test_selected_candidate_artifact_round_trips_exactly_and_rejects_binding_drift():
    objects = InMemoryImmutableObjectStore()
    store = DurableCandidateArtifactStore(objects)
    request = request_for_replay()
    generation = selected_generation()
    controller_evidence = {
        "selected_proposal_digest": generation.proposal.digest(),
        "routing_record_digest": "1" * 64,
        "competition_record_digest": "2" * 64,
        "source_lineage_accepted": False,
        "engineering_run_transitioned": False,
        "review_completed": False,
        "production_deployed": False,
    }
    digest = store.persist(
        generation=generation,
        controller_evidence=controller_evidence,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        work_specification_id=WORK_SPEC_ID,
        work_specification_revision=1,
        work_specification_digest=WORK_SPEC_DIGEST,
        acceptance_ids=("AC-01",),
        plan_id=PLAN_ID,
        base_source_lineage_ref=LINEAGE_ID,
        base_revision=SOURCE_DIGEST,
        source_context_digest=SOURCE_DIGEST,
    )

    restored, evidence = store.restore(
        digest,
        request=request,
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        plan_id=PLAN_ID,
        base_source_lineage_ref=LINEAGE_ID,
        base_revision=SOURCE_DIGEST,
    )
    assert restored.proposal.digest() == generation.proposal.digest()
    assert restored.model == generation.model
    assert restored.program_version == generation.program_version
    assert restored.attempts == ()
    assert evidence == controller_evidence

    with pytest.raises(AgenticRuntimeError, match="work_specification_digest"):
        store.restore(
            digest,
            request=request_for_replay(work_specification_digest="f" * 64),
            project_ref=PROJECT_ID,
            run_id=RUN_ID,
            plan_id=PLAN_ID,
            base_source_lineage_ref=LINEAGE_ID,
            base_revision=SOURCE_DIGEST,
        )


def test_selected_candidate_artifact_rejects_content_or_authority_tampering():
    objects = InMemoryImmutableObjectStore()
    store = DurableCandidateArtifactStore(objects)
    generation = selected_generation()
    digest = store.persist(
        generation=generation,
        controller_evidence={
            "selected_proposal_digest": generation.proposal.digest(),
            "routing_record_digest": "1" * 64,
            "competition_record_digest": "2" * 64,
        },
        project_ref=PROJECT_ID,
        run_id=RUN_ID,
        work_specification_id=WORK_SPEC_ID,
        work_specification_revision=1,
        work_specification_digest=WORK_SPEC_DIGEST,
        acceptance_ids=("AC-01",),
        plan_id=PLAN_ID,
        base_source_lineage_ref=LINEAGE_ID,
        base_revision=SOURCE_DIGEST,
        source_context_digest=SOURCE_DIGEST,
    )
    original = objects.objects[digest]
    envelope = json.loads(original)
    envelope["accepts_source_lineage"] = True
    tampered = json.dumps(envelope, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    tampered_digest = __import__("hashlib").sha256(tampered).hexdigest()
    objects.objects[tampered_digest] = tampered

    with pytest.raises(AgenticRuntimeError, match="asserted authority"):
        store.restore(
            tampered_digest,
            request=request_for_replay(),
            project_ref=PROJECT_ID,
            run_id=RUN_ID,
            plan_id=PLAN_ID,
            base_source_lineage_ref=LINEAGE_ID,
            base_revision=SOURCE_DIGEST,
        )


class FakeRecovery:
    def __init__(self, execution):
        self.executions = SimpleNamespace(get_for_run=lambda run_id: execution)


def test_ready_worker_checkpoint_resolves_exact_artifact_and_rejects_lineage_drift():
    candidate_digest = "9" * 64
    execution = SimpleNamespace(
        state=WorkerLifecycleState.READY_FOR_INTEGRATION.value,
        checkpoint_json=json.dumps(
            {
                "plan_ref": f"agentic-plan:{PLAN_ID}",
                "current_step": "CANDIDATE_SELECTED",
                "source_lineage_ref": LINEAGE_ID,
                "evidence_refs": [
                    f"candidate:{candidate_digest}",
                    "proposal:" + "8" * 64,
                ],
            }
        ),
    )
    bridge = DurableAgentWorkerBridge(
        SimpleNamespace(),
        recovery=FakeRecovery(execution),
    )

    assert bridge.selected_candidate_artifact(
        run_id=RUN_ID,
        plan_id=PLAN_ID,
        source_lineage_ref=LINEAGE_ID,
    ) == candidate_digest
    with pytest.raises(AgenticRuntimeError, match="source lineage drifted"):
        bridge.selected_candidate_artifact(
            run_id=RUN_ID,
            plan_id=PLAN_ID,
            source_lineage_ref="src:" + "7" * 64,
        )
