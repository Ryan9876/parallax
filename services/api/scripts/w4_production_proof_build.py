from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


BASE_URL = "https://parallax-api-tan.vercel.app"
RUN_ID = "c5b1d060-6a2f-4500-9f0b-a137a2931296"
REPO_ROOT = Path(__file__).resolve().parents[3]
MAX_SELECTED_FILES = 24
MAX_FILE_BYTES = 48_000
SKIP_DIRECTORIES = {".git", ".hg", ".svn", ".aws", ".gnupg", ".ssh", "node_modules", "__pycache__"}
TOKEN_RE = re.compile(r"[A-Za-z0-9_]{3,}")


def request_json(token: str, path: str, *, timeout: float = 60.0) -> Any:
    request = Request(
        f"{BASE_URL}{path}",
        headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed production target
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"diagnostic GET {path} failed with HTTP {exc.code}: {raw[:500]}") from exc
    except URLError as exc:
        raise RuntimeError(f"diagnostic GET {path} is unreachable: {exc.reason}") from exc


def source_ranking(objective: str, acceptance: list[str]) -> dict[str, Any]:
    terms = {
        token.casefold()
        for value in [objective, *acceptance]
        for token in TOKEN_RE.findall(value)
        if len(token) >= 3
    }
    candidates: list[tuple[int, str, int]] = []
    for current, dirs, files in os.walk(REPO_ROOT, followlinks=False):
        current_path = Path(current)
        dirs[:] = sorted(
            name
            for name in dirs
            if name.casefold() not in SKIP_DIRECTORIES and not (current_path / name).is_symlink()
        )
        for name in sorted(files):
            candidate = current_path / name
            if candidate.is_symlink() or not candidate.is_file():
                continue
            try:
                relative = candidate.relative_to(REPO_ROOT).as_posix()
                size = candidate.stat().st_size
            except OSError:
                continue
            lowered = relative.casefold()
            score = sum(4 for term in terms if term in lowered)
            base = candidate.name.casefold()
            if base in {"readme.md", "package.json", "pyproject.toml", "requirements.txt"}:
                score += 2
            if "/test" in f"/{lowered}" or base.startswith("test_") or base.endswith(".test.ts") or base.endswith(".test.tsx"):
                score += 1
            candidates.append((-score, relative, size))
    candidates.sort(key=lambda item: (item[0], item[1]))
    top = [
        {"path": path, "score": -negative_score, "size": size, "oversized": size > MAX_FILE_BYTES}
        for negative_score, path, size in candidates[:MAX_SELECTED_FILES]
    ]
    first_oversized = next((row for row in top if row["oversized"]), None)
    return {
        "top_selected_candidates": top,
        "first_oversized_selected_candidate": first_oversized,
        "would_fail_per_file_limit": first_oversized is not None,
    }


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "").strip().lower() != "preview":
        raise RuntimeError("W4 production diagnostic runner is preview-only")
    token = (os.getenv("PARALLAX_ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN") or "").strip()
    if len(token) < 32:
        raise RuntimeError("Parallax preview access credential is unavailable")

    run = request_json(token, f"/v1/engineering-runs/{RUN_ID}")
    if not isinstance(run, dict):
        raise RuntimeError("diagnostic run response is invalid")
    specification = request_json(
        token,
        f"/v1/conversations/{run['conversation_id']}/work-specifications/approved",
    )
    if not isinstance(specification, dict):
        raise RuntimeError("diagnostic Work Specification response is invalid")

    ranking = source_ranking(
        str(specification.get("objective") or ""),
        [str(item) for item in specification.get("acceptance_criteria", [])],
    )
    safe = {
        "run_id": RUN_ID,
        "state": run.get("state"),
        "revision": run.get("revision"),
        "source_context_ranking": ranking,
    }
    print(json.dumps(safe, indent=2, sort_keys=True))
    raise RuntimeError("diagnostic-only preview intentionally stops after deterministic source ranking")


if __name__ == "__main__":
    main()
