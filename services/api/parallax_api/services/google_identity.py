from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..config import settings


@dataclass(frozen=True)
class VerifiedGoogleIdentity:
    auth_user_id: str
    email: str
    display_name: str | None
    avatar_url: str | None


class IdentityVerificationError(RuntimeError):
    pass


def verify_google_identity(access_token: str) -> VerifiedGoogleIdentity:
    candidate = access_token.strip()
    if not candidate:
        raise IdentityVerificationError("Google authentication token is missing")

    try:
        response = httpx.get(
            f"{settings.supabase_url.rstrip('/')}/auth/v1/user",
            headers={
                "apikey": settings.supabase_publishable_key,
                "Authorization": f"Bearer {candidate}",
            },
            timeout=6.0,
        )
    except httpx.HTTPError as exc:
        raise IdentityVerificationError("Identity provider could not be reached") from exc

    if response.status_code != 200:
        raise IdentityVerificationError("Google authentication could not be verified")

    try:
        payload = response.json()
    except ValueError as exc:
        raise IdentityVerificationError("Identity provider returned an invalid response") from exc

    auth_user_id = str(payload.get("id") or "").strip()
    email = str(payload.get("email") or "").strip().casefold()
    app_metadata = payload.get("app_metadata") or {}
    providers = app_metadata.get("providers") or []
    provider = app_metadata.get("provider")
    provider_set = {str(item).casefold() for item in providers if item}
    if provider:
        provider_set.add(str(provider).casefold())

    if not auth_user_id or not email or "@" not in email:
        raise IdentityVerificationError("Verified identity is missing required account information")
    if "google" not in provider_set:
        raise IdentityVerificationError("Parallax requires a Google-authenticated identity")

    metadata = payload.get("user_metadata") or {}
    display_name = str(
        metadata.get("full_name")
        or metadata.get("name")
        or payload.get("email")
        or ""
    ).strip() or None
    avatar_url = str(
        metadata.get("avatar_url")
        or metadata.get("picture")
        or ""
    ).strip() or None

    return VerifiedGoogleIdentity(
        auth_user_id=auth_user_id,
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
    )
