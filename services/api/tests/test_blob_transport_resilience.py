from __future__ import annotations

from hashlib import sha256
from types import SimpleNamespace

import httpx
import pytest
import vercel.blob

from parallax_api.code.lineage_persistence import (
    ObjectStoreError,
    VercelPrivateBlobObjectStore,
)


def _connect_timeout() -> httpx.ConnectTimeout:
    return httpx.ConnectTimeout(
        "injected transient connect timeout",
        request=httpx.Request("GET", "https://blob.example.test/object"),
    )


def test_verified_private_blob_is_reused_from_request_local_cache(monkeypatch) -> None:
    content = b"cached immutable source\n"
    digest = sha256(content).hexdigest()
    expected_path = f"parallax/source-lineage/v1/sha256/{digest[:2]}/{digest}"
    calls = 0

    def fake_get(path: str, **kwargs):
        nonlocal calls
        calls += 1
        assert path == expected_path
        return SimpleNamespace(content=content)

    monkeypatch.setattr(vercel.blob, "get", fake_get)
    store = VercelPrivateBlobObjectStore(token="test-token")

    assert store.get(digest) == content
    assert store.get(digest) == content
    store.put_if_absent(digest, content)

    assert calls == 1


def test_transient_private_blob_read_retries_then_caches_verified_content(monkeypatch) -> None:
    content = b"retry immutable source\n"
    digest = sha256(content).hexdigest()
    calls = 0

    def fake_get(path: str, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _connect_timeout()
        return SimpleNamespace(content=content)

    monkeypatch.setattr(vercel.blob, "get", fake_get)
    store = VercelPrivateBlobObjectStore(token="test-token", transient_attempts=2)

    assert store.get(digest) == content
    assert store.get(digest) == content
    assert calls == 2


def test_exhausted_transient_private_blob_read_is_normalized(monkeypatch) -> None:
    content = b"unavailable immutable source\n"
    digest = sha256(content).hexdigest()
    calls = 0

    def fake_get(path: str, **kwargs):
        nonlocal calls
        calls += 1
        raise _connect_timeout()

    monkeypatch.setattr(vercel.blob, "get", fake_get)
    store = VercelPrivateBlobObjectStore(token="test-token", transient_attempts=2)

    with pytest.raises(ObjectStoreError) as failure:
        store.get(digest)

    assert calls == 2
    assert isinstance(failure.value.__cause__, httpx.ConnectTimeout)
    assert "timeout" not in str(failure.value).casefold()


def test_uncertain_transient_private_blob_write_reconciles_by_content_address(monkeypatch) -> None:
    content = b"uncertain write immutable source\n"
    digest = sha256(content).hexdigest()
    remote: dict[str, bytes] = {}
    get_calls = 0
    put_calls = 0

    def fake_get(path: str, **kwargs):
        nonlocal get_calls
        get_calls += 1
        if path not in remote:
            raise vercel.blob.BlobNotFoundError()
        return SimpleNamespace(content=remote[path])

    def fake_put(path: str, body: bytes, **kwargs):
        nonlocal put_calls
        put_calls += 1
        remote[path] = bytes(body)
        raise _connect_timeout()

    monkeypatch.setattr(vercel.blob, "get", fake_get)
    monkeypatch.setattr(vercel.blob, "put", fake_put)
    store = VercelPrivateBlobObjectStore(token="test-token", transient_attempts=2)

    store.put_if_absent(digest, content)
    assert store.get(digest) == content

    assert put_calls == 1
    assert get_calls == 2
    assert list(remote.values()) == [content]


def test_transient_attempts_are_bounded() -> None:
    with pytest.raises(ValueError):
        VercelPrivateBlobObjectStore(transient_attempts=0)
    with pytest.raises(ValueError):
        VercelPrivateBlobObjectStore(transient_attempts=5)
