from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path


class WorkspaceBoundaryError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Artifact:
    path: str
    sha256: str
    size: int

    def as_dict(self) -> dict[str, str | int]:
        return {"path": self.path, "sha256": self.sha256, "size": self.size}


class LocalWorkspace:
    def __init__(self, root: str | Path, *, max_file_bytes: int = 1_000_000):
        self.root = Path(root).resolve(strict=True)
        self.max_file_bytes = max_file_bytes

    def resolve(self, relative_path: str) -> Path:
        candidate = self.root / relative_path
        if candidate.is_symlink():
            raise WorkspaceBoundaryError("workspace symlinks are not permitted")
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise WorkspaceBoundaryError("workspace artifact does not exist") from exc
        if not resolved.is_relative_to(self.root):
            raise WorkspaceBoundaryError("path escapes the protected workspace root")
        if not resolved.is_file():
            raise WorkspaceBoundaryError("workspace artifact is not a file")
        return resolved

    def artifact(self, relative_path: str) -> Artifact:
        path = self.resolve(relative_path)
        size = path.stat().st_size
        if size > self.max_file_bytes:
            raise WorkspaceBoundaryError("workspace artifact exceeds protected size bound")
        content = path.read_bytes()
        return Artifact(relative_path, sha256(content).hexdigest(), size)

    def snapshot(self, paths: list[str]) -> dict[str, object]:
        artifacts = [self.artifact(path) for path in sorted(set(paths))]
        digest = sha256()
        for item in artifacts:
            digest.update(f"{item.path}\0{item.sha256}\0{item.size}\n".encode())
        return {
            "workspace_root_digest": sha256(str(self.root).encode()).hexdigest(),
            "workspace_digest": digest.hexdigest(),
            "artifacts": [item.as_dict() for item in artifacts],
        }
