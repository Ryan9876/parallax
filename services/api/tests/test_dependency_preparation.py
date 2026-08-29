from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from parallax_api.code.dependency_preparation import (
    DependencyPreparationError,
    preparation_network_policy,
    run_dependency_preparation,
)
from parallax_api.code.validation_toolchains import select_validation_profile


class FakePolicyValue:
    def __init__(self, mode: str, allow=None):
        self.mode = mode
        self.allow = allow or {}


class FakeNetworkPolicy:
    @staticmethod
    def deny_all():
        return FakePolicyValue("deny-all")

    @staticmethod
    def custom(*, allow):
        return FakePolicyValue("custom", allow)


class FakeInstance:
    def __init__(
        self,
        *,
        probe_exit: int = 0,
        prepare_exit: int = 0,
        lock_mode: str = "deny-all",
        lock_raises: bool = False,
    ):
        self.probe_exit = probe_exit
        self.prepare_exit = prepare_exit
        self.lock_mode = lock_mode
        self.lock_raises = lock_raises
        self.calls = []
        self.policies = []

    def run_process(self, command, args, **kwargs):
        self.calls.append((command, tuple(args), kwargs))
        exit_code = self.probe_exit if len(self.calls) == 1 else self.prepare_exit
        return SimpleNamespace(returncode=exit_code, stdout="bounded output", stderr="")

    def update_network_policy(self, policy):
        self.policies.append(policy)
        if self.lock_raises:
            raise RuntimeError("lock failed")
        return SimpleNamespace(network_policy=FakePolicyValue(self.lock_mode))


def dotnet_profile(tmp_path: Path):
    (tmp_path / "OtTime.sln").write_text("fixture", encoding="utf-8")
    return select_validation_profile(tmp_path.resolve())


def test_dotnet_prepare_policy_is_exact_server_owned_nuget_allowlist(tmp_path: Path):
    profile = dotnet_profile(tmp_path)
    policy = preparation_network_policy(FakeNetworkPolicy, profile)
    assert policy.mode == "custom"
    assert set(policy.allow) == {"api.nuget.org", "globalcdn.nuget.org"}
    assert all(value == () for value in policy.allow.values())


def test_dotnet_prepare_probes_restores_then_proves_deny_all(tmp_path: Path):
    profile = dotnet_profile(tmp_path)
    instance = FakeInstance()
    evidence = run_dependency_preparation(
        instance,
        FakeNetworkPolicy,
        profile,
        sandbox_cwd=lambda value: "/vercel/sandbox" if value == "." else value,
    )
    assert instance.calls[0][0:2] == ("dotnet", ("--info",))
    assert instance.calls[1][0:2] == ("dotnet", ("restore", "OtTime.sln", "--nologo"))
    assert instance.calls[0][2]["env"] == {}
    assert instance.calls[1][2]["env"] == {}
    assert len(instance.policies) == 1
    assert instance.policies[0].mode == "deny-all"
    assert evidence["dependency_preparation_succeeded"] is True
    assert evidence["validation_network_locked"] is True
    assert "bounded output" not in repr(evidence)


def test_prepare_failure_still_locks_network_and_fails_closed(tmp_path: Path):
    profile = dotnet_profile(tmp_path)
    instance = FakeInstance(prepare_exit=1)
    with pytest.raises(DependencyPreparationError) as captured:
        run_dependency_preparation(
            instance,
            FakeNetworkPolicy,
            profile,
            sandbox_cwd=lambda _value: "/vercel/sandbox",
        )
    assert captured.value.code == "DEPENDENCY_PREPARATION_FAILED"
    assert captured.value.evidence["validation_network_locked"] is True
    assert len(instance.policies) == 1
    assert instance.policies[0].mode == "deny-all"


def test_lock_failure_overrides_prepare_success_and_blocks_validation(tmp_path: Path):
    profile = dotnet_profile(tmp_path)
    instance = FakeInstance(lock_raises=True)
    with pytest.raises(DependencyPreparationError) as captured:
        run_dependency_preparation(
            instance,
            FakeNetworkPolicy,
            profile,
            sandbox_cwd=lambda _value: "/vercel/sandbox",
        )
    assert captured.value.code == "VALIDATION_NETWORK_LOCK_FAILED"
    assert captured.value.evidence["validation_network_locked"] is False


def test_missing_dotnet_toolchain_is_typed_and_network_locked(tmp_path: Path):
    profile = dotnet_profile(tmp_path)
    instance = FakeInstance(probe_exit=127)
    with pytest.raises(DependencyPreparationError) as captured:
        run_dependency_preparation(
            instance,
            FakeNetworkPolicy,
            profile,
            sandbox_cwd=lambda _value: "/vercel/sandbox",
        )
    assert captured.value.code == "EXECUTION_PROFILE_UNAVAILABLE"
    assert len(instance.calls) == 1
    assert captured.value.evidence["validation_network_locked"] is True
