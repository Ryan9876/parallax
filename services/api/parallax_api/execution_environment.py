from __future__ import annotations

import os


DEFAULT_EXECUTION_SNAPSHOT_ID = "snap_vagbatADKKndxwFGSDNbt08Ueigm"
EXECUTION_SNAPSHOT_ENV = "PARALLAX_EXECUTION_SNAPSHOT_ID"


def execution_snapshot_id(explicit: str | None = None) -> str:
    value = explicit or os.getenv(EXECUTION_SNAPSHOT_ENV) or DEFAULT_EXECUTION_SNAPSHOT_ID
    if (
        not isinstance(value, str)
        or not value.startswith("snap_")
        or len(value) > 160
        or any(ord(ch) < 33 or ord(ch) > 126 for ch in value)
    ):
        raise ValueError("server-owned execution snapshot identity is invalid")
    return value


__all__ = ["DEFAULT_EXECUTION_SNAPSHOT_ID", "EXECUTION_SNAPSHOT_ENV", "execution_snapshot_id"]
