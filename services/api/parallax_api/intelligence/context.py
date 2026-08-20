from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable, Protocol


class MessageLike(Protocol):
    role: str
    content: str


class ContextLimitError(ValueError):
    """Raised when protected context limits cannot preserve the current turn."""


@dataclass(frozen=True)
class ContextLimits:
    max_total_chars: int = 12_000
    max_prior_messages: int = 12
    max_message_chars: int = 3_000
    max_current_turn_chars: int = 8_000


@dataclass(frozen=True)
class ReasonContext:
    text: str
    digest: str
    included_turn_count: int
    truncated: bool


AUTHORITY_RULE = (
    "AUTHORITY_RULE: Later explicit USER statements and corrections supersede "
    "conflicting earlier ASSISTANT statements or inferred assumptions."
)


def _normalize_content(value: str, *, limit: int) -> tuple[str, bool]:
    clean = value.strip()
    if len(clean) <= limit:
        return clean, False
    if limit < 32:
        return clean[:limit], True
    head = max(12, (limit - 18) // 2)
    tail = limit - head - 18
    return f"{clean[:head]}…[truncated]…{clean[-tail:]}", True


def _render_message(message: MessageLike, limits: ContextLimits) -> tuple[str, bool]:
    role = message.role.strip().lower()
    if role not in {"user", "assistant"}:
        role = "assistant"
    content, truncated = _normalize_content(message.content, limit=limits.max_message_chars)
    marker = "USER" if role == "user" else "ASSISTANT"
    authority = " AUTHORITATIVE" if role == "user" else " CONTEXT_ONLY"
    return f"[{marker}{authority}] {content}", truncated


def compose_reason_context(
    *,
    conversation_id: str,
    spec_id: str,
    status: str,
    mode: str,
    current_user_turn: str,
    prior_messages: Iterable[MessageLike],
    limits: ContextLimits | None = None,
) -> ReasonContext:
    """Build the bounded, deterministic Reason context from durable state.

    Oldest eligible prior messages are removed first. The active spec, lifecycle
    state, authority rule, and current user turn are never silently truncated.
    """

    limits = limits or ContextLimits()
    current = current_user_turn.strip()
    if not current:
        raise ContextLimitError("current user turn is empty")
    if len(current) > limits.max_current_turn_chars:
        raise ContextLimitError("current user turn exceeds protected context limit")

    header = [
        f"CONVERSATION_ID: {conversation_id}",
        f"ACTIVE_SPEC_ID: {spec_id}",
        f"LIFECYCLE_STATUS: {status}",
        f"MODE: {mode}",
        AUTHORITY_RULE,
        "PRIOR_MESSAGES:",
    ]
    current_block = f"CURRENT_USER_TURN:\n[USER AUTHORITATIVE] {current}"
    fixed = "\n".join(header + [current_block])
    if len(fixed) > limits.max_total_chars:
        raise ContextLimitError("protected context envelope cannot preserve the current user turn")

    source = list(prior_messages)
    count_truncated = len(source) > limits.max_prior_messages
    eligible = source[-limits.max_prior_messages :]

    rendered: list[str] = []
    content_truncated = False
    for message in eligible:
        line, was_truncated = _render_message(message, limits)
        rendered.append(line)
        content_truncated = content_truncated or was_truncated

    # Preserve the newest context first. Remove oldest eligible messages until
    # the protected total-character bound is satisfied.
    while rendered:
        candidate = "\n".join(header + rendered + [current_block])
        if len(candidate) <= limits.max_total_chars:
            break
        rendered.pop(0)
        count_truncated = True

    text = "\n".join(header + rendered + [current_block])
    if len(text) > limits.max_total_chars:
        raise ContextLimitError("protected context envelope exceeds hard limit")

    digest = f"sha256:{sha256(text.encode('utf-8')).hexdigest()}"
    return ReasonContext(
        text=text,
        digest=digest,
        included_turn_count=len(rendered),
        truncated=count_truncated or content_truncated,
    )
