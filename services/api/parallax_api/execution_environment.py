from __future__ import annotations

import os


DEFAULT_EXECUTION_SNAPSHOT_ID = "snap_vagbatADKKndxwFGSDNbt08Ueigm"
EXECUTION_SNAPSHOT_ENV = "PARALLAX_EXECUTION_SNAPSHOT_ID"
DOTNET_EXECUTION_SNAPSHOT_ENV = "PARALLAX_DOTNET_EXECUTION_SNAPSHOT_ID"

_COMMON_PROFILES = frozenset({"python-v1", "node-v1"})
_DOTNET_PROFILE = "dotnet-v1"
_ADMITTED_PROFILES = _COMMON_PROFILES | {_DOTNET_PROFILE}


def _validated_snapshot_id(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith("snap_")
        or len(value) > 160
        or any(ord(ch) < 33 or ord(ch) > 126 for ch in value)
    ):
        raise ValueError("server-owned execution snapshot identity is invalid")
    return value


def execution_snapshot_id(explicit: str | None = None) -> str:
    """Return the established common Python/Node execution snapshot."""

    value = explicit or os.getenv(EXECUTION_SNAPSHOT_ENV) or DEFAULT_EXECUTION_SNAPSHOT_ID
    return _validated_snapshot_id(value)


def execution_snapshot_id_for_profile(
    profile_id: str,
    *,
    common_explicit: str | None = None,
    dotnet_explicit: str | None = None,
) -> str:
    """Resolve one finite server-owned snapshot from an admitted profile ID.

    Repository content, user/model text, Project metadata, and arbitrary profile
    strings cannot shape environment-variable names or snapshot identities.
    Python and Node intentionally preserve the established common snapshot.
    .NET requires its dedicated released configuration and never falls back.
    """

    if not isinstance(profile_id, str) or profile_id not in _ADMITTED_PROFILES:
        raise ValueError("validation profile is not admitted for execution snapshot selection")
    if profile_id in _COMMON_PROFILES:
        return execution_snapshot_id(common_explicit)

    value = dotnet_explicit if dotnet_explicit is not None else os.getenv(DOTNET_EXECUTION_SNAPSHOT_ENV)
    if value is None:
        raise ValueError("server-owned .NET execution snapshot identity is unavailable")
    return _validated_snapshot_id(value)


__all__ = [
    "DEFAULT_EXECUTION_SNAPSHOT_ID",
    "DOTNET_EXECUTION_SNAPSHOT_ENV",
    "EXECUTION_SNAPSHOT_ENV",
    "execution_snapshot_id",
    "execution_snapshot_id_for_profile",
]
