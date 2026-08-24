from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .browser import (
    BrowserAction,
    BrowserExecutionEvidence,
    BrowserExecutionRequest,
    BrowserExecutor,
    BrowserValidationError,
    NETWORK_POLICY_EXACT_PREVIEW,
)


@dataclass(frozen=True, slots=True)
class SandboxBrowserJob:
    """Non-programmable job contract for a Node/Playwright-capable Vercel Sandbox runner.

    The runner receives only the canonical Preview origin, exact egress host,
    registered viewport geometry and already-validated typed browser actions.
    It never receives shell text, JavaScript/eval strings, headers, cookies,
    credentials, arbitrary URLs or provider mutation authority.
    """

    project_id: str
    run_id: str
    lineage_id: str
    preview_deployment_id: str
    preview_origin: str
    exact_allowed_host: str
    workflow_id: str
    workflow_version: int
    viewport_id: str
    viewport_width: int
    viewport_height: int
    timeout_ms: int
    actions: tuple[BrowserAction, ...]
    network_policy: str = NETWORK_POLICY_EXACT_PREVIEW

    def __post_init__(self) -> None:
        if self.network_policy != NETWORK_POLICY_EXACT_PREVIEW:
            raise BrowserValidationError("sandbox browser job must retain exact-host network policy")
        if not self.preview_origin.startswith("https://"):
            raise BrowserValidationError("sandbox browser job requires canonical HTTPS Preview origin")
        if not self.exact_allowed_host or self.preview_origin != f"https://{self.exact_allowed_host}":
            raise BrowserValidationError("sandbox browser job origin/host authority mismatch")
        if not self.actions:
            raise BrowserValidationError("sandbox browser job requires registered typed actions")


class SandboxBrowserRunner(Protocol):
    """Infrastructure seam implemented by the Vercel Sandbox/Node browser runtime."""

    def run(self, job: SandboxBrowserJob) -> BrowserExecutionEvidence: ...


class VercelSandboxBrowserExecutor(BrowserExecutor):
    """Protected adapter from Parallax browser requests to a sandbox browser runner.

    The adapter deliberately exposes no generic command or network interface.
    A production runner can use Vercel Sandbox with a prebuilt agent-browser or
    Playwright snapshot, but all executable behavior remains server-owned by the
    typed workflow contract carried in ``SandboxBrowserJob``.
    """

    def __init__(self, runner: SandboxBrowserRunner) -> None:
        self.runner = runner

    def execute(self, request: BrowserExecutionRequest) -> BrowserExecutionEvidence:
        if request.allowed_host != request.target.preview_host:
            raise BrowserValidationError("sandbox browser executor refused widened network authority")
        job = SandboxBrowserJob(
            project_id=request.target.project_id,
            run_id=request.target.run_id,
            lineage_id=request.target.lineage_id,
            preview_deployment_id=request.target.preview_deployment_id,
            preview_origin=request.target.preview_origin,
            exact_allowed_host=request.target.preview_host,
            workflow_id=request.workflow.workflow_id,
            workflow_version=request.workflow.version,
            viewport_id=request.viewport.viewport_id,
            viewport_width=request.viewport.width,
            viewport_height=request.viewport.height,
            timeout_ms=request.workflow.timeout_ms,
            actions=request.workflow.actions,
        )
        evidence = self.runner.run(job)
        if not isinstance(evidence, BrowserExecutionEvidence):
            raise BrowserValidationError("sandbox browser runner returned invalid evidence type")
        return evidence


__all__ = [
    "SandboxBrowserJob",
    "SandboxBrowserRunner",
    "VercelSandboxBrowserExecutor",
]
