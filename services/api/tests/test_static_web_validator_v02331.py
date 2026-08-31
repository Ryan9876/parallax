from __future__ import annotations

from pathlib import Path

import pytest

from parallax_api.code.static_web_validator import StaticWebValidationError, validate


def _valid_site(root: Path) -> None:
    (root / "index.html").write_text(
        '<!doctype html><link rel="stylesheet" href="styles.css"><script src="app.js"></script><a href="https://example.com">external</a>',
        encoding="utf-8",
    )
    (root / "styles.css").write_text("body { margin: 0; }\n", encoding="utf-8")
    (root / "app.js").write_text('const value = "ok";\n', encoding="utf-8")


def test_static_web_build_test_verify_accept_valid_local_site(tmp_path: Path):
    _valid_site(tmp_path)
    for stage in ("BUILD", "TEST", "VERIFY"):
        validate(stage, str(tmp_path.resolve()))


def test_static_web_requires_root_index(tmp_path: Path):
    (tmp_path / "app.js").write_text("const value = 1;\n", encoding="utf-8")
    with pytest.raises(StaticWebValidationError, match="STATIC_WEB_INDEX_REQUIRED"):
        validate("BUILD", str(tmp_path.resolve()))


def test_static_web_rejects_broken_local_reference(tmp_path: Path):
    (tmp_path / "index.html").write_text('<script src="missing.js"></script>', encoding="utf-8")
    with pytest.raises(StaticWebValidationError, match="STATIC_WEB_LOCAL_REFERENCE_MISSING"):
        validate("TEST", str(tmp_path.resolve()))


def test_static_web_rejects_javascript_syntax_error(tmp_path: Path):
    (tmp_path / "index.html").write_text('<script src="app.js"></script>', encoding="utf-8")
    (tmp_path / "app.js").write_text("const = ;\n", encoding="utf-8")
    with pytest.raises(StaticWebValidationError, match="STATIC_WEB_JS_SYNTAX_INVALID"):
        validate("BUILD", str(tmp_path.resolve()))


def test_static_web_rejects_reference_traversal(tmp_path: Path):
    (tmp_path / "index.html").write_text('<a href="../secret.txt">bad</a>', encoding="utf-8")
    with pytest.raises(StaticWebValidationError, match="STATIC_WEB_REFERENCE_PATH_INVALID"):
        validate("TEST", str(tmp_path.resolve()))


def test_static_web_rejects_symlink(tmp_path: Path):
    target = tmp_path / "real.js"
    target.write_text("const value = 1;\n", encoding="utf-8")
    (tmp_path / "index.html").write_text('<script src="linked.js"></script>', encoding="utf-8")
    try:
        (tmp_path / "linked.js").symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(StaticWebValidationError, match="STATIC_WEB_SYMLINK_REJECTED"):
        validate("VERIFY", str(tmp_path.resolve()))


def test_static_web_never_executes_package_scripts(tmp_path: Path):
    _valid_site(tmp_path)
    sentinel = tmp_path / "should-not-exist"
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"touch should-not-exist","test":"touch should-not-exist"}}',
        encoding="utf-8",
    )
    validate("VERIFY", str(tmp_path.resolve()))
    assert not sentinel.exists()
