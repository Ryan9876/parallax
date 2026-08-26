from __future__ import annotations

from dataclasses import dataclass
import re


_EXPLICIT_GITHUB_RE = re.compile(
    r"(?i)(?:github:|https?://github\.com/)([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9][A-Za-z0-9._-]{0,99})(?:\.git)?"
)
_SHORTHAND_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])([A-Za-z0-9][A-Za-z0-9-]{0,38})/([A-Za-z0-9][A-Za-z0-9._-]{0,99})(?![A-Za-z0-9_./-])"
)
_TARGET_CUE_RE = re.compile(
    r"(?i)(?:\b(?:repository|repo|project|target)\b|\b(?:for|against|in|on)\s+(?:the\s+)?(?:requested\s+)?)\s*[:=\-–—]?\s*$"
)
_PATH_ROOTS = {
    ".github",
    "app",
    "apps",
    "benchmarks",
    "client",
    "docs",
    "packages",
    "scripts",
    "server",
    "services",
    "src",
    "test",
    "tests",
}


def normalize_github_repository_ref(value: str | None) -> str | None:
    if value is None:
        return None
    clean = value.strip()
    if not clean:
        return None
    match = _EXPLICIT_GITHUB_RE.fullmatch(clean)
    if match is None:
        match = _SHORTHAND_RE.fullmatch(clean)
    if match is None:
        return None
    owner, repo = match.groups()
    if repo.casefold().endswith(".git"):
        repo = repo[:-4]
    return f"{owner.casefold()}/{repo.casefold()}"


def _display_ref(normalized: str) -> str:
    owner, repo = normalized.split("/", 1)
    return f"github:{owner}/{repo}"


def _target_references(text: str) -> set[str]:
    candidates: set[str] = set()
    occupied: list[tuple[int, int]] = []
    for match in _EXPLICIT_GITHUB_RE.finditer(text):
        owner, repo = match.groups()
        if repo.casefold().endswith(".git"):
            repo = repo[:-4]
        candidates.add(f"{owner.casefold()}/{repo.casefold()}")
        occupied.append(match.span())

    for match in _SHORTHAND_RE.finditer(text):
        if any(start <= match.start() < end for start, end in occupied):
            continue
        owner, repo = match.groups()
        if owner.casefold() in _PATH_ROOTS:
            continue
        if repo.casefold().endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".yml", ".yaml")):
            continue
        prefix = text[max(0, match.start() - 72):match.start()]
        if not _TARGET_CUE_RE.search(prefix):
            continue
        candidates.add(f"{owner.casefold()}/{repo.casefold()}")
    return candidates


@dataclass(frozen=True, slots=True)
class RepositoryIdentityConflict:
    canonical_repository_ref: str
    requested_repository_refs: tuple[str, ...]

    @property
    def public_message(self) -> str:
        requested = ", ".join(_display_ref(item) for item in self.requested_repository_refs)
        return (
            f"Repository target conflict: this Code objective targets {requested}, but the selected Project is bound to "
            f"{self.canonical_repository_ref}. Select or create the intended Project, then start a fresh Code objective."
        )


def find_repository_identity_conflict(
    *,
    canonical_repository_ref: str | None,
    target_texts: tuple[str, ...] | list[str],
) -> RepositoryIdentityConflict | None:
    canonical = normalize_github_repository_ref(canonical_repository_ref)
    if canonical is None:
        return None

    requested: set[str] = set()
    for text in target_texts:
        if isinstance(text, str) and text.strip():
            requested.update(_target_references(text))
    requested.discard(canonical)
    if not requested:
        return None

    return RepositoryIdentityConflict(
        canonical_repository_ref=_display_ref(canonical),
        requested_repository_refs=tuple(sorted(requested)),
    )


__all__ = [
    "RepositoryIdentityConflict",
    "find_repository_identity_conflict",
    "normalize_github_repository_ref",
]
