from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

import pytest

from parallax_api.tools import (
    HumanApproval,
    ToolActionPolicy,
    ToolAuthorityRequest,
    ToolCapability,
    ToolConsequence,
)


def read_policy() -> ToolActionPolicy:
    return ToolActionPolicy(action="repository.read", consequence=ToolConsequence.READ)


def test_authority_contracts_are_frozen_and_payload_free():
    capability = ToolCapability(
        capability_id="cap-1",
        project_ref="project-123",
        tool="github",
        actions=(read_policy(),),
    )
    request = ToolAuthorityRequest(
        request_id="req-1",
        capability_id=capability.capability_id,
        project_ref=capability.project_ref,
        tool=capability.tool,
        action="repository.read",
        actor_ref="user-1",
    )

    with pytest.raises(FrozenInstanceError):
        capability.enabled = False  # type: ignore[misc]

    prohibited = {"payload", "command", "url", "headers", "body", "environment", "metadata"}
    for contract in (ToolCapability, ToolAuthorityRequest, HumanApproval):
        assert prohibited.isdisjoint({item.name for item in fields(contract)})

    assert request.digest == request.digest


@pytest.mark.parametrize("tool", ["shell", "exec", "command", "subprocess", "http", "https", "curl", "network"])
def test_generic_execution_and_transport_tools_are_rejected(tool: str):
    with pytest.raises(ValueError, match="reserved"):
        ToolCapability(
            capability_id="cap-1",
            project_ref="project-123",
            tool=tool,
            actions=(read_policy(),),
        )


@pytest.mark.parametrize("action", ["shell", "exec", "execute", "command", "run_command", "subprocess", "raw_http", "raw_request", "http_request"])
def test_generic_execution_and_transport_actions_are_rejected(action: str):
    with pytest.raises(ValueError, match="reserved"):
        ToolActionPolicy(action=action, consequence=ToolConsequence.READ)


def test_destructive_action_requires_human_approval_by_invariant():
    with pytest.raises(ValueError, match="require human approval"):
        ToolActionPolicy(
            action="deployment.promote",
            consequence=ToolConsequence.DESTRUCTIVE,
            requires_human_approval=False,
        )


def test_capability_actions_must_be_immutable_nonempty_and_unique():
    with pytest.raises(ValueError, match="non-empty tuple"):
        ToolCapability(
            capability_id="cap-1",
            project_ref="project-123",
            tool="github",
            actions=[],  # type: ignore[arg-type]
        )

    with pytest.raises(ValueError, match="unique"):
        ToolCapability(
            capability_id="cap-1",
            project_ref="project-123",
            tool="github",
            actions=(read_policy(), read_policy()),
        )
