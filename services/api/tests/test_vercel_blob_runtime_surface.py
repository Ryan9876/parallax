from __future__ import annotations


def test_vercel_blob_sdk_exports_runtime_lineage_operations() -> None:
    from vercel.blob import BlobError, BlobNotFoundError, get, put

    assert issubclass(BlobNotFoundError, BlobError)
    assert callable(get)
    assert callable(put)
