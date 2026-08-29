from __future__ import annotations

from io import BytesIO
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request

import pytest


SCRIPTS_ROOT = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import production_projected_source_preflight as preflight


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def _rate_limit_error() -> HTTPError:
    return HTTPError(
        "https://api.github.com/repos/Ryan9876/parallax/contents/example",
        403,
        "Forbidden",
        {"X-RateLimit-Remaining": "0", "Retry-After": "1"},
        BytesIO(b'{"message":"API rate limit exceeded"}'),
    )


def test_json_request_retries_github_rate_limit_403(monkeypatch) -> None:
    calls = 0
    sleeps: list[float] = []

    def fake_urlopen(request, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _rate_limit_error()
        return _Response(b'{"ok":true}')

    monkeypatch.setattr(preflight, "urlopen", fake_urlopen)
    monkeypatch.setattr(preflight.time, "sleep", lambda value: sleeps.append(value))

    result = preflight._json_request(Request("https://api.github.com/test"), label="GitHub source read")

    assert result == {"ok": True}
    assert calls == 2
    assert sleeps == [1.0]


def test_json_request_still_fails_closed_on_ordinary_403(monkeypatch) -> None:
    error = HTTPError(
        "https://api.github.com/test",
        403,
        "Forbidden",
        {},
        BytesIO(b'{"message":"Resource not accessible"}'),
    )
    monkeypatch.setattr(preflight, "urlopen", lambda *args, **kwargs: (_ for _ in ()).throw(error))

    with pytest.raises(RuntimeError, match="HTTP 403"):
        preflight._json_request(Request("https://api.github.com/test"), label="GitHub source read")
