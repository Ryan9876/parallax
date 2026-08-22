from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Any, Mapping


_TOOL_OR_ACTION = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_RESULT_CODE = re.compile(r"^[A-Z][A-Z0-9_.:-]{0,63}$")

_RESERVED_TOOLS = frozenset(
    {
        "shell",
        "exec",
        "command",
        "subprocess",
        "http",
        "https",
        "curl",
        "wget",
        "network",
        "raw_http",
    }
)
_RESERVED_ACTIONS = frozenset(
    {
        "shell",
        "exec",
        "execute",
        "command",
        "run_command",
        "subprocess",
        "raw_http",
        "raw_request",
        "http_request",
        "network_request",
    }
)


class ToolConsequence(str, Enum):
    READ = "read"
    MUTATE = "mutate"
    DESTRUCTIVE = "destructive"


class AuthorityDenyReason(str, Enum):
    UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"
    CAPABILITY_DISABLED = "CAPABILITY_DISABLED"
    PROJECT_MISMATCH = "PROJECT_MISMATCH"
    TOOL_MISMATCH = "TOOL_MISMATCH"
    ACTION_NOT_ALLOWED = "ACTION_NOT_ALLOWED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVAL_MISMATCH = "APPROVAL_MISMATCH"


class ToolOutcome(str, Enum):
    DENIED = "DENIED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def _require_reference(value: str, *, field: str) -> None:
    if not isinstance(value, str) or not _REFERENCE.fullmatch(value):
        raise ValueError(f"{field} must be a bounded opaque identifier")


def _require_tool_or_action(value: str, *, field: str, reserved: frozenset[str]) -> None:
    if not isinstance(value, str) or not _TOOL_OR_ACTION.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase bounded identifier")
    if value in reserved:
        raise ValueError(f"{field} is reserved for generic execution or transport")


def _canonical(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_canonical(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported canonical digest value: {type(value).__name__}")


def canonical_digest(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _canonical(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ToolActionPolicy:
    action: str
    consequence: ToolConsequence
    requires_human_approval: bool = False

    def __post_init__(self) -> None:
        _require_tool_or_action(self.action, field="action", reserved=_RESERVED_ACTIONS)
        if not isinstance(self.consequence, ToolConsequence):
            raise TypeError("consequence must be ToolConsequence")
        if not isinstance(self.requires_human_approval, bool):
            raise TypeError("requires_human_approval must be bool")
        if self.consequence is ToolConsequence.DESTRUCTIVE and not self.requires_human_approval:
            raise ValueError("destructive actions require human approval")


@dataclass(frozen=True)
class ToolCapability:
    capability_id: str
    project_ref: str
    tool: str
    actions: tuple[ToolActionPolicy, ...]
    enabled: bool = True

    def __post_init__(self) -> None:
        _require_reference(self.capability_id, field="capability_id")
        _require_reference(self.project_ref, field="project_ref")
        _require_tool_or_action(self.tool, field="tool", reserved=_RESERVED_TOOLS)
        if not isinstance(self.actions, tuple) or not self.actions:
            raise ValueError("actions must be a non-empty tuple")
        if not all(isinstance(policy, ToolActionPolicy) for policy in self.actions):
            raise TypeError("actions must contain ToolActionPolicy values")
        action_ids = tuple(policy.action for policy in self.actions)
        if len(set(action_ids)) != len(action_ids):
            raise ValueError("capability actions must be unique")
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be bool")

    def policy_for(self, action: str) -> ToolActionPolicy | None:
        return next((policy for policy in self.actions if policy.action == action), None)


@dataclass(frozen=True)
class ToolAuthorityRequest:
    request_id: str
    capability_id: str
    project_ref: str
    tool: str
    action: str
    actor_ref: str

    def __post_init__(self) -> None:
        _require_reference(self.request_id, field="request_id")
        _require_reference(self.capability_id, field="capability_id")
        _require_reference(self.project_ref, field="project_ref")
        _require_tool_or_action(self.tool, field="tool", reserved=_RESERVED_TOOLS)
        _require_tool_or_action(self.action, field="action", reserved=_RESERVED_ACTIONS)
        _require_reference(self.actor_ref, field="actor_ref")

    @property
    def digest(self) -> str:
        return canonical_digest(
            {
                "request_id": self.request_id,
                "capability_id": self.capability_id,
                "project_ref": self.project_ref,
                "tool": self.tool,
                "action": self.action,
                "actor_ref": self.actor_ref,
            }
        )


@dataclass(frozen=True)
class HumanApproval:
    approval_id: str
    request_id: str
    capability_id: str
    project_ref: str
    tool: str
    action: str
    approved_by: str

    def __post_init__(self) -> None:
        _require_reference(self.approval_id, field="approval_id")
        _require_reference(self.request_id, field="request_id")
        _require_reference(self.capability_id, field="capability_id")
        _require_reference(self.project_ref, field="project_ref")
        _require_tool_or_action(self.tool, field="tool", reserved=_RESERVED_TOOLS)
        _require_tool_or_action(self.action, field="action", reserved=_RESERVED_ACTIONS)
        _require_reference(self.approved_by, field="approved_by")

    def matches(self, request: ToolAuthorityRequest) -> bool:
        return (
            self.request_id == request.request_id
            and self.capability_id == request.capability_id
            and self.project_ref == request.project_ref
            and self.tool == request.tool
            and self.action == request.action
        )


@dataclass(frozen=True)
class AuthorityDecision:
    allowed: bool
    request_id: str
    capability_id: str | None
    project_ref: str
    tool: str
    action: str
    consequence: ToolConsequence | None
    approval_id: str | None
    deny_reason: AuthorityDenyReason | None

    def __post_init__(self) -> None:
        _require_reference(self.request_id, field="request_id")
        _require_reference(self.project_ref, field="project_ref")
        _require_tool_or_action(self.tool, field="tool", reserved=_RESERVED_TOOLS)
        _require_tool_or_action(self.action, field="action", reserved=_RESERVED_ACTIONS)
        if self.capability_id is not None:
            _require_reference(self.capability_id, field="capability_id")
        if self.approval_id is not None:
            _require_reference(self.approval_id, field="approval_id")
        if self.allowed:
            if self.capability_id is None or self.consequence is None or self.deny_reason is not None:
                raise ValueError(
                    "allowed decision must identify capability/consequence and have no deny reason"
                )
        elif self.deny_reason is None:
            raise ValueError("denied decision requires a deny reason")


@dataclass(frozen=True)
class ToolExecutionResult:
    succeeded: bool
    result_code: str
    result_identity: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.succeeded, bool):
            raise TypeError("succeeded must be bool")
        if not isinstance(self.result_code, str) or not _RESULT_CODE.fullmatch(self.result_code):
            raise ValueError("result_code must be a bounded normalized code")
        if self.result_identity is not None:
            _require_reference(self.result_identity, field="result_identity")

    @property
    def digest(self) -> str:
        return canonical_digest(
            {
                "succeeded": self.succeeded,
                "result_code": self.result_code,
                "result_identity": self.result_identity,
            }
        )


@dataclass(frozen=True)
class ToolAuditRecord:
    request_id: str
    capability_id: str | None
    project_ref: str
    tool: str
    action: str
    actor_ref: str
    consequence: ToolConsequence | None
    authority_allowed: bool
    outcome: ToolOutcome
    deny_reason: AuthorityDenyReason | None
    approval_id: str | None
    request_digest: str
    result_digest: str | None
    result_code: str | None
    result_identity: str | None

    def __post_init__(self) -> None:
        _require_reference(self.request_id, field="request_id")
        _require_reference(self.project_ref, field="project_ref")
        _require_tool_or_action(self.tool, field="tool", reserved=_RESERVED_TOOLS)
        _require_tool_or_action(self.action, field="action", reserved=_RESERVED_ACTIONS)
        _require_reference(self.actor_ref, field="actor_ref")
        if self.capability_id is not None:
            _require_reference(self.capability_id, field="capability_id")
        if self.approval_id is not None:
            _require_reference(self.approval_id, field="approval_id")
        if not re.fullmatch(r"[0-9a-f]{64}", self.request_digest):
            raise ValueError("request_digest must be sha256 hex")
        if self.result_digest is not None and not re.fullmatch(r"[0-9a-f]{64}", self.result_digest):
            raise ValueError("result_digest must be sha256 hex")
        if self.result_code is not None and not _RESULT_CODE.fullmatch(self.result_code):
            raise ValueError("result_code must be a bounded normalized code")
        if self.result_identity is not None:
            _require_reference(self.result_identity, field="result_identity")

        if self.outcome is ToolOutcome.DENIED:
            if self.authority_allowed or self.deny_reason is None:
                raise ValueError("denied audit requires denied authority and reason")
            if any(
                value is not None
                for value in (self.result_digest, self.result_code, self.result_identity)
            ):
                raise ValueError("denied audit cannot contain execution result")
        elif self.outcome in {ToolOutcome.SUCCEEDED, ToolOutcome.FAILED}:
            if not self.authority_allowed or self.deny_reason is not None:
                raise ValueError("execution audit requires allowed authority")
            if self.result_digest is None or self.result_code is None:
                raise ValueError("execution audit requires result evidence")
        else:
            raise ValueError("unknown audit outcome")
