from __future__ import annotations

import argparse
import json
from pathlib import Path

import provision_wave2_vercel as helper

EXPECTED_LINK = {
    "orgId": "team_JgE8AWWz36uzRbeR6V6EWg9k",
    "projectId": "prj_4lhve1AXZntfauaGHvkuaGWC6KJX",
}


def _ensure_seeded_link(repo: Path) -> None:
    path = repo / ".vercel" / "project.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise helper.ProvisioningError("canonical Vercel project link is missing or invalid") from exc
    if payload != EXPECTED_LINK:
        raise helper.ProvisioningError("canonical Vercel project link does not match parallax-api")


def main(argv: list[str] | None = None) -> int:
    # Team-scoped bootstrap access tokens can manage the known project resources
    # but Vercel CLI `link` may still try to resolve a user identity first. The
    # workflow seeds the exact server-owned project link, so CI verifies that
    # immutable binding and skips only the redundant identity-resolution call.
    helper._ensure_link = _ensure_seeded_link
    return helper.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
