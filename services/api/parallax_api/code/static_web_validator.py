from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
from urllib.parse import unquote, urlsplit


_JS_SUFFIXES = frozenset({".js", ".mjs", ".cjs"})
_LOCAL_ATTRIBUTES = frozenset({"href", "src"})
_IGNORED_SCHEMES = frozenset({"http", "https", "data", "mailto", "tel"})

STATIC_WEB_VALIDATION_REASON_CODES = frozenset(
    {
        "STATIC_WEB_ARGUMENTS_INVALID",
        "STATIC_WEB_ROOT_INVALID",
        "STATIC_WEB_SYMLINK_REJECTED",
        "STATIC_WEB_SPECIAL_FILE_REJECTED",
        "STATIC_WEB_PATH_ESCAPE",
        "STATIC_WEB_INDEX_REQUIRED",
        "STATIC_WEB_INDEX_ESCAPE",
        "STATIC_WEB_JS_CHECK_UNAVAILABLE",
        "STATIC_WEB_JS_SYNTAX_INVALID",
        "STATIC_WEB_REFERENCE_SCHEME_UNSUPPORTED",
        "STATIC_WEB_REFERENCE_PATH_INVALID",
        "STATIC_WEB_INDEX_NOT_UTF8",
        "STATIC_WEB_HTML_INVALID",
        "STATIC_WEB_LOCAL_REFERENCE_MISSING",
        "STATIC_WEB_REFERENCE_PATH_ESCAPE",
        "STATIC_WEB_STAGE_INVALID",
    }
)
STATIC_WEB_REPAIRABLE_REASON_CODES = frozenset(
    {
        "STATIC_WEB_INDEX_REQUIRED",
        "STATIC_WEB_JS_SYNTAX_INVALID",
        "STATIC_WEB_REFERENCE_SCHEME_UNSUPPORTED",
        "STATIC_WEB_REFERENCE_PATH_INVALID",
        "STATIC_WEB_INDEX_NOT_UTF8",
        "STATIC_WEB_HTML_INVALID",
        "STATIC_WEB_LOCAL_REFERENCE_MISSING",
    }
)


class StaticWebValidationError(ValueError):
    pass


class _ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[str] = []

    def _collect(self, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if key.casefold() in _LOCAL_ATTRIBUTES and isinstance(value, str) and value.strip():
                self.references.append(value.strip())

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._collect(attrs)


def _root(value: str) -> Path:
    root = Path(value)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise StaticWebValidationError("STATIC_WEB_ROOT_INVALID")
    return root.resolve(strict=True)


def _files(root: Path) -> tuple[Path, ...]:
    result: list[Path] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise StaticWebValidationError("STATIC_WEB_SYMLINK_REJECTED")
        if path.is_dir():
            continue
        if not path.is_file():
            raise StaticWebValidationError("STATIC_WEB_SPECIAL_FILE_REJECTED")
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise StaticWebValidationError("STATIC_WEB_PATH_ESCAPE")
        result.append(resolved)
    return tuple(result)


def _index(root: Path) -> Path:
    index = root / "index.html"
    if index.is_symlink() or not index.is_file():
        raise StaticWebValidationError("STATIC_WEB_INDEX_REQUIRED")
    resolved = index.resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise StaticWebValidationError("STATIC_WEB_INDEX_ESCAPE")
    return resolved


def _node_executable() -> str:
    node = shutil.which("node")
    if not node:
        raise StaticWebValidationError("STATIC_WEB_JS_CHECK_UNAVAILABLE")
    candidate = Path(node)
    if not candidate.is_absolute() or not candidate.exists() or not candidate.is_file():
        raise StaticWebValidationError("STATIC_WEB_JS_CHECK_UNAVAILABLE")
    return str(candidate.resolve(strict=True))


def _syntax_check_javascript(root: Path, files: tuple[Path, ...]) -> None:
    javascript = tuple(path for path in files if path.suffix.casefold() in _JS_SUFFIXES)
    if not javascript:
        return
    node = _node_executable()
    for path in javascript:
        try:
            result = subprocess.run(
                [node, "--check", str(path)],
                cwd=root,
                env={},
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise StaticWebValidationError("STATIC_WEB_JS_CHECK_UNAVAILABLE") from exc
        if result.returncode != 0:
            raise StaticWebValidationError("STATIC_WEB_JS_SYNTAX_INVALID")


def _local_reference(reference: str) -> str | None:
    if reference.startswith("#"):
        return None
    parsed = urlsplit(reference)
    if parsed.scheme.casefold() in _IGNORED_SCHEMES or parsed.netloc:
        return None
    if parsed.scheme:
        raise StaticWebValidationError("STATIC_WEB_REFERENCE_SCHEME_UNSUPPORTED")
    raw = unquote(parsed.path)
    if not raw:
        return None
    raw = raw.lstrip("/")
    if not raw:
        return "index.html"
    pure = PurePosixPath(raw)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise StaticWebValidationError("STATIC_WEB_REFERENCE_PATH_INVALID")
    return pure.as_posix()


def _validate_references(root: Path, index: Path) -> None:
    try:
        source = index.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise StaticWebValidationError("STATIC_WEB_INDEX_NOT_UTF8") from exc
    parser = _ReferenceParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as exc:
        raise StaticWebValidationError("STATIC_WEB_HTML_INVALID") from exc
    for reference in parser.references:
        relative = _local_reference(reference)
        if relative is None:
            continue
        target = root.joinpath(*PurePosixPath(relative).parts)
        if target.is_symlink() or not target.is_file():
            raise StaticWebValidationError("STATIC_WEB_LOCAL_REFERENCE_MISSING")
        resolved = target.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise StaticWebValidationError("STATIC_WEB_REFERENCE_PATH_ESCAPE")


def validate(stage: str, root_value: str) -> None:
    if stage not in {"BUILD", "TEST", "VERIFY"}:
        raise StaticWebValidationError("STATIC_WEB_STAGE_INVALID")
    root = _root(root_value)
    files = _files(root)
    index = _index(root)
    _syntax_check_javascript(root, files)
    if stage in {"TEST", "VERIFY"}:
        _validate_references(root, index)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("STATIC_WEB_ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    try:
        validate(argv[1], argv[2])
    except StaticWebValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"STATIC_WEB_{argv[1]}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
