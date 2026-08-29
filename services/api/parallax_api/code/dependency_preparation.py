from __future__ import annotations

from hashlib import sha256
import time
from typing import Any, Callable

from .validation_toolchains import ValidationProfile


class DependencyPreparationError(RuntimeError):
    """Fail-closed dependency/toolchain readiness error with bounded evidence."""

    def __init__(self, code: str, *, evidence: dict[str, object]) -> None:
        super().__init__(code)
        self.code = code
        self.evidence = evidence


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8", errors="replace")).hexdigest()


def preparation_network_policy(NetworkPolicy: Any, profile: ValidationProfile) -> Any:
    preparation = profile.preparation
    if preparation is None:
        return NetworkPolicy.deny_all()
    return NetworkPolicy.custom(allow={domain: () for domain in preparation.package_domains})


def _bounded_result(
    *,
    required: bool,
    succeeded: bool,
    network_locked: bool,
    code: str,
    duration_ms: int,
    probe_exit_code: int | None = None,
    prepare_exit_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
) -> dict[str, object]:
    return {
        "dependency_preparation_required": required,
        "dependency_preparation_succeeded": succeeded,
        "dependency_preparation_code": code,
        "dependency_preparation_duration_ms": max(0, duration_ms),
        "dependency_probe_exit_code": probe_exit_code,
        "dependency_prepare_exit_code": prepare_exit_code,
        "dependency_stdout_digest": _digest(stdout),
        "dependency_stderr_digest": _digest(stderr),
        "validation_network_locked": network_locked,
    }


def run_dependency_preparation(
    instance: object,
    NetworkPolicy: Any,
    profile: ValidationProfile,
    *,
    sandbox_cwd: Callable[[str], str],
) -> dict[str, object]:
    """Run one immutable profile-owned PREPARE contract then prove deny-all.

    PREPARE receives no application environment or credentials. The caller must
    create the sandbox with ``preparation_network_policy``. This function always
    attempts to transition the active runtime session to deny-all before it
    returns or raises; validation must not execute unless the returned evidence
    says ``validation_network_locked`` is true.
    """

    preparation = profile.preparation
    if preparation is None:
        return _bounded_result(
            required=False,
            succeeded=True,
            network_locked=True,
            code="NOT_REQUIRED",
            duration_ms=0,
        )

    started = time.monotonic()
    probe_exit: int | None = None
    prepare_exit: int | None = None
    stdout = ""
    stderr = ""
    failure_code: str | None = None
    lock_error: Exception | None = None
    network_locked = False

    try:
        probe = instance.run_process(
            preparation.probe_command,
            list(preparation.probe_args),
            cwd=sandbox_cwd(preparation.working_directory),
            env={},
            kill_after=preparation.probe_timeout_seconds,
            capture_output=True,
        )
        probe_exit = probe.returncode
        stdout += probe.stdout or ""
        stderr += probe.stderr or ""
        if probe_exit != 0:
            failure_code = "EXECUTION_PROFILE_UNAVAILABLE"
        else:
            prepared = instance.run_process(
                preparation.command,
                list(preparation.args),
                cwd=sandbox_cwd(preparation.working_directory),
                env={},
                kill_after=preparation.timeout_seconds,
                capture_output=True,
            )
            prepare_exit = prepared.returncode
            stdout += prepared.stdout or ""
            stderr += prepared.stderr or ""
            if prepare_exit != 0:
                failure_code = "DEPENDENCY_PREPARATION_FAILED"
    except Exception:
        failure_code = "DEPENDENCY_PREPARATION_FAILED"
    finally:
        try:
            locked_session = instance.update_network_policy(NetworkPolicy.deny_all())
            effective_policy = getattr(locked_session, "network_policy", None)
            network_locked = getattr(effective_policy, "mode", None) == "deny-all"
            if not network_locked:
                lock_error = RuntimeError("effective network policy did not become deny-all")
        except Exception as exc:
            lock_error = exc
            network_locked = False

    duration_ms = int((time.monotonic() - started) * 1000)
    if lock_error is not None:
        evidence = _bounded_result(
            required=True,
            succeeded=False,
            network_locked=False,
            code="VALIDATION_NETWORK_LOCK_FAILED",
            duration_ms=duration_ms,
            probe_exit_code=probe_exit,
            prepare_exit_code=prepare_exit,
            stdout=stdout,
            stderr=stderr,
        )
        raise DependencyPreparationError("VALIDATION_NETWORK_LOCK_FAILED", evidence=evidence) from lock_error

    if failure_code is not None:
        evidence = _bounded_result(
            required=True,
            succeeded=False,
            network_locked=True,
            code=failure_code,
            duration_ms=duration_ms,
            probe_exit_code=probe_exit,
            prepare_exit_code=prepare_exit,
            stdout=stdout,
            stderr=stderr,
        )
        raise DependencyPreparationError(failure_code, evidence=evidence)

    return _bounded_result(
        required=True,
        succeeded=True,
        network_locked=True,
        code="READY",
        duration_ms=duration_ms,
        probe_exit_code=probe_exit,
        prepare_exit_code=prepare_exit,
        stdout=stdout,
        stderr=stderr,
    )


__all__ = [
    "DependencyPreparationError",
    "preparation_network_policy",
    "run_dependency_preparation",
]
