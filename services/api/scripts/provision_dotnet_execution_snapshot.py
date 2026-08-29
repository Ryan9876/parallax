from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


BASE_SNAPSHOT_ID = "snap_vagbatADKKndxwFGSDNbt08Ueigm"
DOTNET_SDK_VERSION = "8.0.424"
DOTNET_ARCHIVE_URL = (
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.424/"
    "dotnet-sdk-8.0.424-linux-x64.tar.gz"
)
DOTNET_ARCHIVE_SHA512 = (
    "6503fd9f464d5e3a4f43a881d2b74afc6a2c46ceda74d027f1565b7239f4b3ec"
    "884857c03c0dcd49eb52f384d5ae1fa5aaf135f0a6aabc5518103aceed643c74"
)
_PROTECTED_SOURCE_ROOT = "/vercel/sandbox"
_SNAPSHOT_ID = re.compile(r"^snap_[A-Za-z0-9_-]{8,160}$")
_SANDBOX_ID = re.compile(r"^sbx_[A-Za-z0-9_-]{8,160}$")


def _must_pass(result: object, label: str) -> str:
    return_code = getattr(result, "returncode", None)
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if return_code != 0:
        raise RuntimeError(f"{label} failed with exit code {return_code}: {str(stderr)[:400]}")
    return str(stdout)


def _snapshot(instance: object) -> str:
    sandbox_id = getattr(instance, "sandbox_id", None) or getattr(instance, "id", None)
    if not isinstance(sandbox_id, str) or not _SANDBOX_ID.fullmatch(sandbox_id):
        raise RuntimeError("provisioning sandbox returned an invalid session identity")
    oidc = os.getenv("VERCEL_OIDC_TOKEN")
    if not isinstance(oidc, str) or not oidc.strip():
        raise RuntimeError("preview provisioning requires Vercel OIDC")

    query: dict[str, str] = {}
    team_id = os.getenv("VERCEL_ORG_ID")
    if isinstance(team_id, str) and team_id.startswith("team_"):
        query["teamId"] = team_id
    suffix = "?" + urlencode(query) if query else ""
    request = Request(
        f"https://api.vercel.com/v2/sandboxes/sessions/{sandbox_id}/snapshot{suffix}",
        method="POST",
        data=json.dumps({"expiration": "0"}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {oidc.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "Parallax-Dotnet-Snapshot-Provisioner/1",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", errors="replace")
        raise RuntimeError(f"snapshot publication failed: HTTP {exc.code}: {detail[:500]}") from exc
    except (TimeoutError, URLError) as exc:
        raise RuntimeError("snapshot publication failed: Vercel API unavailable") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("snapshot publication returned invalid JSON") from exc
    snapshot = payload.get("snapshot") if isinstance(payload, dict) else None
    snapshot_id = snapshot.get("id") if isinstance(snapshot, dict) else None
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise RuntimeError("snapshot publication returned invalid snapshot identity")
    return snapshot_id


def main() -> None:
    if (os.getenv("VERCEL_ENV") or "unknown") != "preview":
        raise RuntimeError(".NET snapshot provisioning is preview-only")
    if os.getenv("PARALLAX_DOTNET_SNAPSHOT_PROVISIONING") != "1":
        raise RuntimeError(".NET snapshot provisioning marker is not enabled")
    project_id = os.getenv("VERCEL_PROJECT_ID")
    if not isinstance(project_id, str) or not project_id.startswith("prj_"):
        raise RuntimeError(".NET snapshot provisioning requires the canonical Vercel Project identity")

    from vercel.api import session
    from vercel.sandbox import NetworkPolicy, SnapshotSource
    from vercel.sandbox import sync as sandbox

    policy = NetworkPolicy.custom(allow={"builds.dotnet.microsoft.com": ()})
    with session():
        with sandbox.create_sandbox(
            project_id=project_id,
            execution_time_limit=300,
            persistent=False,
            network_policy=policy,
            env={},
            source=SnapshotSource(snapshot_id=BASE_SNAPSHOT_ID),
            destroy=False,
            tags={"parallax": "dotnet-snapshot-provisioning"},
        ) as instance:
            if getattr(instance, "current_snapshot_id", None) != BASE_SNAPSHOT_ID:
                raise RuntimeError("provisioning sandbox did not restore the exact common snapshot")

            entries = _must_pass(
                instance.run_process(
                    "python",
                    [
                        "-c",
                        (
                            "from pathlib import Path; "
                            f"p=Path('{_PROTECTED_SOURCE_ROOT}'); "
                            "items=[] if not p.exists() else list(p.iterdir()); "
                            "print(len(items)); raise SystemExit(0 if not items else 9)"
                        ),
                    ],
                    env={},
                    kill_after=30,
                    capture_output=True,
                ),
                "source-free base snapshot check",
            ).strip()
            if entries != "0":
                raise RuntimeError("common snapshot unexpectedly contains Project source")

            download_code = (
                "import hashlib, pathlib, urllib.request; "
                f"u={DOTNET_ARCHIVE_URL!r}; p=pathlib.Path('/tmp/dotnet-sdk.tar.gz'); "
                "urllib.request.urlretrieve(u, p); "
                "h=hashlib.sha512(p.read_bytes()).hexdigest(); "
                f"assert h == {DOTNET_ARCHIVE_SHA512!r}, h; print(h)"
            )
            digest = _must_pass(
                instance.run_process(
                    "python",
                    ["-c", download_code],
                    env={},
                    kill_after=120,
                    capture_output=True,
                ),
                ".NET SDK download and checksum verification",
            ).strip()
            if digest != DOTNET_ARCHIVE_SHA512:
                raise RuntimeError(".NET SDK checksum evidence drifted")

            _must_pass(
                instance.run_process("sudo", ["rm", "-rf", "/opt/dotnet"], env={}, kill_after=30, capture_output=True),
                "clear .NET target",
            )
            _must_pass(
                instance.run_process("sudo", ["mkdir", "-p", "/opt/dotnet"], env={}, kill_after=30, capture_output=True),
                "create .NET target",
            )
            _must_pass(
                instance.run_process(
                    "sudo",
                    ["tar", "-xzf", "/tmp/dotnet-sdk.tar.gz", "-C", "/opt/dotnet"],
                    env={},
                    kill_after=90,
                    capture_output=True,
                ),
                "extract .NET SDK",
            )
            _must_pass(
                instance.run_process(
                    "sudo",
                    ["ln", "-sfn", "/opt/dotnet/dotnet", "/usr/local/bin/dotnet"],
                    env={},
                    kill_after=30,
                    capture_output=True,
                ),
                "publish .NET executable",
            )
            _must_pass(
                instance.run_process("rm", ["-f", "/tmp/dotnet-sdk.tar.gz"], env={}, kill_after=30, capture_output=True),
                "remove SDK archive",
            )

            version = _must_pass(
                instance.run_process("dotnet", ["--version"], env={}, kill_after=30, capture_output=True),
                ".NET version probe",
            ).strip()
            if version != DOTNET_SDK_VERSION:
                raise RuntimeError(f"unexpected .NET SDK version: {version}")
            info = _must_pass(
                instance.run_process("dotnet", ["--info"], env={}, kill_after=30, capture_output=True),
                ".NET readiness probe",
            )
            if DOTNET_SDK_VERSION not in info:
                raise RuntimeError(".NET readiness output does not prove the pinned SDK")

            instance.update_network_policy(NetworkPolicy.deny_all())
            active_policy = getattr(instance, "network_policy", None)
            if active_policy != NetworkPolicy.deny_all():
                raise RuntimeError("provisioning sandbox did not lock networking before snapshot publication")

            snapshot_id = _snapshot(instance)
            print(
                "PARALLAX_DOTNET_SNAPSHOT_PROVISIONED "
                f"snapshot_id={snapshot_id} sdk={DOTNET_SDK_VERSION} "
                f"base_snapshot={BASE_SNAPSHOT_ID} source_free=true network=deny-all"
            )


if __name__ == "__main__":
    main()
