from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from parallax_api.evaluation.runtime_evidence import PersistedProviderActionFact, PersistedVerifiedDelivery
from parallax_api.intelligence.protected_metrics import evaluate_compiled_plan, evaluate_spec_contract
from parallax_api.tools.contracts import AuthorityDenyReason, ToolAuditRecord, ToolOutcome
from parallax_api.tools.providers.common import ProviderActionEvidence, ProviderActionState, ProviderProjectBinding


def test_p2_v01510_spec_and_compiled_plan_require_authentic_protected_dspy_metadata():
    repository_root = Path(__file__).resolve().parents[3]
    spec_path = repository_root / "specs" / "P2-V0.15.10.md"
    plan_path = repository_root / "specs" / "compiled" / "P2-V0.15.10.plan.json"
    spec_text = spec_path.read_text(encoding="utf-8")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    assert evaluate_spec_contract(spec_text).passed is True
    assert evaluate_compiled_plan(spec_text, plan, require_metadata=True).passed is True
    assert plan["dspy_run"]["executed"] is True
    assert [item["id"] for item in plan["protected_acceptance_map"]] == [
        f"AC-{index:02d}" for index in range(1, 13)
    ]


def test_provider_denial_remains_distinct_bounded_audit_evidence():
    project_id = str(uuid4())
    binding = ProviderProjectBinding(project_id, "github:acme/reference-app")
    evidence = ProviderActionEvidence(
        provider="github",
        action="commit.write",
        state=ProviderActionState.DENIED,
        project_ref=project_id,
        repository_identity_digest=binding.repository_identity_digest,
        result_status=AuthorityDenyReason.APPROVAL_REQUIRED.value,
    )
    audit = ToolAuditRecord(
        request_id="request:denied-reference",
        capability_id="capability:github-reference",
        project_ref=project_id,
        tool="github",
        action="commit.write",
        actor_ref="actor:reference-runtime",
        consequence=None,
        authority_allowed=False,
        outcome=ToolOutcome.DENIED,
        deny_reason=AuthorityDenyReason.APPROVAL_REQUIRED,
        approval_id=None,
        request_digest="a" * 64,
        result_digest=None,
        result_code=None,
        result_identity=None,
    )

    fact = PersistedProviderActionFact(evidence=evidence, audit=audit)
    assert fact.evidence.state is ProviderActionState.DENIED
    assert fact.audit.outcome is ToolOutcome.DENIED
    assert fact.audit.authority_allowed is False
    assert fact.audit.deny_reason is AuthorityDenyReason.APPROVAL_REQUIRED
    assert fact.digest.startswith("sha256:") and len(fact.digest) == 71

    mismatched = ProviderActionEvidence(
        provider="github",
        action="commit.write",
        state=ProviderActionState.SUCCEEDED,
        project_ref=project_id,
        repository_identity_digest=binding.repository_identity_digest,
        result_status="COMMIT_CREATED",
    )
    with pytest.raises(ValueError, match="state does not match durable audit outcome"):
        PersistedProviderActionFact(evidence=mismatched, audit=audit)


def test_verified_delivery_requires_canonical_project_and_run_uuid_identity():
    project_id = str(uuid4())
    run_id = str(uuid4())
    with pytest.raises(ValueError):
        PersistedVerifiedDelivery(
            project_id=project_id,
            run_id=f"run:{run_id}",
            repository_ref="github:acme/reference-app",
            lineage_id="src:" + "1" * 64,
            content_digest="2" * 64,
            expected_parent_revision="3" * 40,
            published_revision="4" * 40,
            pull_request_identity="pr:80",
            preview_deployment_id="dpl_reference_80",
            preview_status="READY",
            actions=(),
            publication_replayed=True,
        )
