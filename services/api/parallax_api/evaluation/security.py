from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from typing import Any

_SECRET_PATTERNS = (
    re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
)
_SENSITIVE_ENV_NAME = re.compile(r"(?i)(KEY|TOKEN|SECRET|PASSWORD)")
_FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "hidden_reasoning",
    "reasoning_trace",
    "scratchpad",
}


class SecurityViolation(ValueError):
    pass


def _walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))
    return keys


def security_findings(payload: Any, *, environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Return privacy/security findings without ever serializing environment data."""

    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    findings: list[str] = []

    for key in _walk_keys(payload):
        if key.casefold() in _FORBIDDEN_REASONING_KEYS:
            findings.append(f"forbidden_reasoning_field:{key}")

    if any(pattern.search(serialized) for pattern in _SECRET_PATTERNS):
        findings.append("possible_secret_literal")

    source = os.environ if environ is None else environ
    for name, value in source.items():
        if not _SENSITIVE_ENV_NAME.search(name) or len(value) < 12:
            continue
        if value in serialized:
            findings.append(f"configured_secret_value_exposed:{name}")

    return tuple(dict.fromkeys(findings))


def assert_safe_payload(payload: Any, *, environ: Mapping[str, str] | None = None) -> None:
    findings = security_findings(payload, environ=environ)
    if findings:
        raise SecurityViolation(";".join(findings))
