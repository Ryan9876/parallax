from __future__ import annotations

MAX_PROJECT_CONTEXT_FIELD = 300


def _bounded(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    clean = value.strip()
    if not clean or clean != value or len(clean) > MAX_PROJECT_CONTEXT_FIELD:
        raise ValueError(f"{name} is invalid")
    if any(ord(ch) < 32 for ch in clean):
        raise ValueError(f"{name} contains control characters")
    return clean


def compose_project_capability_context(*, project_id: str, repository_ref: str | None) -> str:
    project = _bounded(project_id, "project_id")
    lines = [f"CANONICAL_PROJECT_ID: {project}"]
    if repository_ref is None:
        lines.extend([
            "CANONICAL_REPOSITORY_REF: UNBOUND",
            "PROTECTED_SOURCE_BOOTSTRAP: NOT_REGISTERED",
        ])
        return "\n".join(lines)

    repository = _bounded(repository_ref, "repository_ref")
    lines.extend([
        f"CANONICAL_REPOSITORY_REF: {repository}",
        "PROTECTED_SOURCE_BOOTSTRAP: REGISTERED_FOR_BOUND_REPOSITORY",
        (
            "PROJECT_CAPABILITY_RULE: The protected Engineering Run runtime is authorized to attempt "
            "server-owned source bootstrap for this bound repository. Absence of source files from the "
            "conversation is not evidence that the repository is inaccessible and does not, by itself, "
            "require the user to upload repository files."
        ),
    ])
    return "\n".join(lines)
