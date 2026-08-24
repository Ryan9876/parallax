from __future__ import annotations

import hashlib
import os
import sys


_CONTENT = b"parallax-production-blob-sdk-preflight-v1\n"
_PREFIX = "parallax/source-lineage/v1/sha256"


def main() -> None:
    environment = os.getenv("VERCEL_ENV") or "unknown"
    if environment != "production":
        print(f"Production Blob SDK preflight: SKIP (VERCEL_ENV={environment})")
        return

    from vercel.blob import BlobError, BlobNotFoundError, get, put

    digest = hashlib.sha256(_CONTENT).hexdigest()
    path = f"{_PREFIX}/{digest[:2]}/{digest}"

    existing: bytes | None
    try:
        result = get(path, access="private", use_cache=False)
        existing = bytes(result.content)
    except BlobNotFoundError:
        existing = None
    except BlobError as exc:
        raise RuntimeError(f"Vercel Blob SDK read failed: {type(exc).__name__}") from exc

    if existing is not None and existing != _CONTENT:
        raise RuntimeError("Vercel Blob SDK immutable canary content mismatch")

    if existing is None:
        try:
            put(
                path,
                _CONTENT,
                access="private",
                content_type="application/octet-stream",
                add_random_suffix=False,
                overwrite=False,
            )
        except BlobError as exc:
            # Preserve the runtime race behavior: an immutable writer may have
            # won after the read. The final read is authoritative.
            try:
                raced = get(path, access="private", use_cache=False)
            except BlobError as read_exc:
                raise RuntimeError(f"Vercel Blob SDK write failed: {type(exc).__name__}") from read_exc
            if bytes(raced.content) != _CONTENT:
                raise RuntimeError("Vercel Blob SDK write race produced different content") from exc

    try:
        verified = get(path, access="private", use_cache=False)
    except BlobError as exc:
        raise RuntimeError(f"Vercel Blob SDK write-after-read failed: {type(exc).__name__}") from exc
    if bytes(verified.content) != _CONTENT:
        raise RuntimeError("Vercel Blob SDK canary failed write-after-read verification")

    print("Production Blob SDK preflight: PASS (private immutable get/put/get verified)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Production Blob SDK preflight: FAIL — {exc}", file=sys.stderr)
        raise
