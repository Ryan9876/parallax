from __future__ import annotations

import os
import re


DOTNET_SDK_VERSION = "8.0.424"
DOTNET_ARCHIVE_URL = (
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/8.0.424/"
    "dotnet-sdk-8.0.424-linux-x64.tar.gz"
)
DOTNET_ARCHIVE_SHA512 = (
    "6503fd9f464d5e3a4f43a881d2b74afc6a2c46ceda74d027f1565b7239f4b3ec"
    "884857c03c0dcd49eb52f384d5ae1fa5aaf135f0a6aabc5518103aceed643c74"
)
LIBICU_PACKAGE = "libicu78"
LIBICU_VERSION = "78.2-2ubuntu1"
LIBICU_ARCHIVE_URL = (
    "https://archive.ubuntu.com/ubuntu/pool/main/i/icu/"
    "libicu78_78.2-2ubuntu1_amd64.deb"
)
LIBICU_ARCHIVE_SHA256 = "c8b97930f9e365d6d00978144b468ac8397ef07d2fb2c453869f05fc3a98c4ca"
_PROTECTED_SOURCE_ROOT = "/vercel/sandbox"
_SNAPSHOT_ID = re.compile(r"^snap_[A-Za-z0-9_-]{8,160}$")


def _must_pass(result: object, label: str) -> str:
    return_code = getattr(result, "returncode", None)
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    if return_code != 0:
        raise RuntimeError(f"{label} failed with exit code {return_code}: {str(stderr)[:400]}")
    return str(stdout)


def _snapshot(instance: object) -> str:
    snapshot_method = getattr(instance, "snapshot", None)
    if not callable(snapshot_method):
        raise RuntimeError("Vercel Sandbox SDK does not expose snapshot publication")
    snapshot = snapshot_method(expiration=0)
    snapshot_id = getattr(snapshot, "snapshot_id", None) or getattr(snapshot, "id", None)
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise RuntimeError("snapshot publication returned invalid snapshot identity")
    expires_at = getattr(snapshot, "expires_at", None)
    if expires_at is not None:
        raise RuntimeError("released .NET execution snapshot must be non-expiring")
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
    from vercel.sandbox import NetworkPolicy
    from vercel.sandbox import sync as sandbox

    policy = NetworkPolicy.custom(
        allow={
            "builds.dotnet.microsoft.com": (),
            "archive.ubuntu.com": (),
        }
    )
    with session():
        with sandbox.create_sandbox(
            project_id=project_id,
            execution_time_limit=300,
            persistent=False,
            network_policy=policy,
            env={},
            destroy=False,
            tags={"parallax": "dotnet-snapshot-provisioning"},
        ) as instance:
            if getattr(instance, "current_snapshot_id", None) is not None:
                raise RuntimeError("fresh .NET provisioning sandbox unexpectedly restored a snapshot")

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
                "source-free fresh sandbox check",
            ).strip()
            if entries != "0":
                raise RuntimeError("fresh provisioning sandbox unexpectedly contains Project source")

            os_release = _must_pass(
                instance.run_process(
                    "sh",
                    ["-lc", ". /etc/os-release && printf '%s:%s' \"$ID\" \"$VERSION_ID\""],
                    env={},
                    kill_after=30,
                    capture_output=True,
                ),
                "sandbox operating-system probe",
            ).strip()
            if os_release != "ubuntu:26.04":
                raise RuntimeError(f"unexpected provisioning operating system: {os_release}")

            icu_download_code = (
                "import hashlib,pathlib,urllib.request;"
                f"u={LIBICU_ARCHIVE_URL!r};p=pathlib.Path('/tmp/libicu78.deb');"
                "urllib.request.urlretrieve(u,p);"
                "h=hashlib.sha256(p.read_bytes()).hexdigest();"
                f"assert h=={LIBICU_ARCHIVE_SHA256!r},h;print(h)"
            )
            icu_digest = _must_pass(
                instance.run_process(
                    "python",
                    ["-c", icu_download_code],
                    env={},
                    kill_after=120,
                    capture_output=True,
                ),
                "ICU artifact download and checksum verification",
            ).strip()
            if icu_digest != LIBICU_ARCHIVE_SHA256:
                raise RuntimeError("ICU checksum evidence drifted")
            _must_pass(
                instance.run_process(
                    "sudo",
                    ["dpkg", "-i", "/tmp/libicu78.deb"],
                    env={"DEBIAN_FRONTEND": "noninteractive"},
                    kill_after=90,
                    capture_output=True,
                ),
                "pinned ICU installation",
            )
            installed_icu = _must_pass(
                instance.run_process(
                    "dpkg-query",
                    ["-W", "-f=${Package}=${Version}", LIBICU_PACKAGE],
                    env={},
                    kill_after=30,
                    capture_output=True,
                ),
                "ICU package identity probe",
            ).strip()
            if installed_icu != f"{LIBICU_PACKAGE}={LIBICU_VERSION}":
                raise RuntimeError(f"unexpected ICU package identity: {installed_icu}")
            _must_pass(
                instance.run_process("rm", ["-f", "/tmp/libicu78.deb"], env={}, kill_after=30, capture_output=True),
                "remove ICU package artifact",
            )

            dotnet_download_code = (
                "import hashlib,pathlib,urllib.request;"
                f"u={DOTNET_ARCHIVE_URL!r};p=pathlib.Path('/tmp/dotnet-sdk.tar.gz');"
                "urllib.request.urlretrieve(u,p);"
                "h=hashlib.sha512(p.read_bytes()).hexdigest();"
                f"assert h=={DOTNET_ARCHIVE_SHA512!r},h;print(h)"
            )
            digest = _must_pass(
                instance.run_process(
                    "python",
                    ["-c", dotnet_download_code],
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

            locked_session = instance.update_network_policy(NetworkPolicy.deny_all())
            effective_policy = getattr(locked_session, "network_policy", None)
            if getattr(effective_policy, "mode", None) != "deny-all":
                raise RuntimeError("provisioning sandbox did not lock networking before snapshot publication")

            snapshot_id = _snapshot(instance)
            print(
                "PARALLAX_DOTNET_SNAPSHOT_PROVISIONED "
                f"snapshot_id={snapshot_id} sdk={DOTNET_SDK_VERSION} "
                f"icu={LIBICU_PACKAGE}={LIBICU_VERSION} "
                "base=fresh-ubuntu-26.04 source_free=true network=deny-all non_expiring=true"
            )


if __name__ == "__main__":
    main()
