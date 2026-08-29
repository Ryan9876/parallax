from __future__ import annotations

import os


_DOTNET_SDK_VERSION = "8.0.424"
_TOOL_ROOT = f"/vercel/.parallax/toolchains/dotnet-{_DOTNET_SDK_VERSION}"
_DOTNET = f"{_TOOL_ROOT}/dotnet"
_ARCHIVE = f"/tmp/dotnet-sdk-{_DOTNET_SDK_VERSION}-linux-x64.tar.gz"
_ARCHIVE_URL = (
    "https://builds.dotnet.microsoft.com/dotnet/Sdk/"
    f"{_DOTNET_SDK_VERSION}/dotnet-sdk-{_DOTNET_SDK_VERSION}-linux-x64.tar.gz"
)


def _require_success(result: object, label: str) -> None:
    if getattr(result, "returncode", None) != 0:
        raise RuntimeError(f"{label} failed")


def main() -> None:
    project_id = os.getenv("VERCEL_PROJECT_ID")
    if not project_id:
        raise RuntimeError("Vercel project identity is required for controlled toolchain provisioning")
    if (os.getenv("VERCEL_ENV") or "unknown") == "production":
        raise RuntimeError("controlled toolchain provisioning is forbidden during production publication")
    if os.getenv("VERCEL_GIT_COMMIT_REF") != "p2/profile-specific-execution-environments":
        raise RuntimeError("controlled toolchain provisioning is restricted to the governed workstream branch")

    from vercel.api import session
    from vercel.sandbox import NetworkPolicy
    from vercel.sandbox import sync as sandbox

    policy = NetworkPolicy.custom(allow={"builds.dotnet.microsoft.com": ()})
    with session():
        with sandbox.create_sandbox(
            project_id=project_id,
            execution_time_limit=600,
            persistent=False,
            network_policy=policy,
            env={},
            destroy=False,
            tags={"parallax": "dotnet-toolchain-provisioning", "sdk": _DOTNET_SDK_VERSION},
        ) as instance:
            instance.fs.mkdir("sandbox", cwd="/vercel", recursive=True)
            instance.fs.mkdir(f".parallax/toolchains/dotnet-{_DOTNET_SDK_VERSION}", cwd="/vercel", recursive=True)

            download = instance.run_process(
                "curl",
                ["--fail", "--silent", "--show-error", "--location", _ARCHIVE_URL, "--output", _ARCHIVE],
                env={},
                kill_after=180,
                capture_output=True,
            )
            _require_success(download, "pinned .NET SDK download")

            extract = instance.run_process(
                "tar",
                ["-xzf", _ARCHIVE, "-C", _TOOL_ROOT],
                env={},
                kill_after=180,
                capture_output=True,
            )
            _require_success(extract, "pinned .NET SDK extraction")

            version = instance.run_process(
                _DOTNET,
                ["--version"],
                env={},
                kill_after=30,
                capture_output=True,
            )
            _require_success(version, "pinned .NET SDK probe")
            if (version.stdout or "").strip() != _DOTNET_SDK_VERSION:
                raise RuntimeError("pinned .NET SDK version mismatch")

            source_check = instance.run_process(
                "find",
                ["/vercel/sandbox", "-mindepth", "1", "-print", "-quit"],
                env={},
                kill_after=10,
                capture_output=True,
            )
            _require_success(source_check, "source-free toolchain check")
            if (source_check.stdout or "").strip():
                raise RuntimeError("toolchain snapshot provisioning unexpectedly contains application source")

            locked = instance.update_network_policy(NetworkPolicy.deny_all())
            if getattr(getattr(locked, "network_policy", None), "mode", None) != "deny-all":
                raise RuntimeError("toolchain snapshot network policy did not become deny-all")

            snapshot = instance.snapshot(expiration=0)
            snapshot_id = getattr(snapshot, "snapshot_id", None)
            if not isinstance(snapshot_id, str) or not snapshot_id.startswith("snap_"):
                raise RuntimeError("toolchain snapshot identity is invalid")
            print(f"PARALLAX_DOTNET_EXECUTION_SNAPSHOT_ID={snapshot_id}")
            print(f"PARALLAX_DOTNET_EXECUTABLE={_DOTNET}")
            print(f"PARALLAX_DOTNET_SDK_VERSION={_DOTNET_SDK_VERSION}")


if __name__ == "__main__":
    main()
