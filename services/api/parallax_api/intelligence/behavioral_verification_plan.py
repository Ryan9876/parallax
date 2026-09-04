from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..code.work_spec_binding import acceptance_map, work_specification_contract
from ..models import WorkSpecification
from ..validation.browser import (
    BrowserAction,
    BrowserActionKind,
    BrowserValidationError,
    BrowserWorkflow,
    BrowserWorkflowRegistry,
    DEFAULT_VIEWPORTS,
    SemanticTarget,
    SemanticTargetKind,
)
from .dspy_programs import build_lm
from .router import ModelRouter, RoutingFailure, RoutingFailureKind


PLAN_SCHEMA_VERSION = 1
PLAN_PROGRAM_VERSION = "behavioral-verification-plan-v0.23.47"
MAX_PLAN_JSON_BYTES = 32_000
_ACCEPTANCE_ID_RE = re.compile(r"^AC-[0-9]{2}$")
_ASSERTION_KINDS = {
    BrowserActionKind.ASSERT_VISIBLE,
    BrowserActionKind.ASSERT_ABSENT,
    BrowserActionKind.ASSERT_PATH,
    BrowserActionKind.ASSERT_LAYOUT,
}


class BehavioralVerificationMode(StrEnum):
    BROWSER = "BROWSER"
    HUMAN_ONLY = "HUMAN_ONLY"


class BehavioralActionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: BrowserActionKind
    path: str | None = None
    target_kind: SemanticTargetKind | None = None
    target_value: str | None = Field(default=None, max_length=200)
    value: str | None = Field(default=None, max_length=200)
    checkpoint: str | None = Field(default=None, max_length=120)

    def to_browser_action(self) -> BrowserAction:
        if (self.target_kind is None) != (self.target_value is None):
            raise ValueError("browser target kind and value must be supplied together")
        target = (
            SemanticTarget(self.target_kind, self.target_value)
            if self.target_kind is not None and self.target_value is not None
            else None
        )
        try:
            return BrowserAction(
                kind=self.kind,
                path=self.path,
                target=target,
                value=self.value,
                checkpoint=self.checkpoint,
            )
        except (BrowserValidationError, TypeError, ValueError) as exc:
            raise ValueError("behavioral browser action is outside the protected browser contract") from exc

    @model_validator(mode="after")
    def validate_existing_browser_contract(self):
        self.to_browser_action()
        return self


class BehavioralCriterionProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acceptance_id: str = Field(min_length=5, max_length=5)
    mode: BehavioralVerificationMode
    viewport_ids: list[str] = Field(default_factory=list, max_length=8)
    actions: list[BehavioralActionProposal] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def validate_mode(self):
        if _ACCEPTANCE_ID_RE.fullmatch(self.acceptance_id) is None:
            raise ValueError("behavioral plan acceptance identity is invalid")
        if self.mode is BehavioralVerificationMode.HUMAN_ONLY:
            if self.viewport_ids or self.actions:
                raise ValueError("HUMAN_ONLY criteria cannot contain executable browser workflow")
            return self
        if not self.viewport_ids or not self.actions:
            raise ValueError("BROWSER criteria require a bounded workflow")
        if not any(action.kind in _ASSERTION_KINDS for action in self.actions):
            raise ValueError("BROWSER criteria require at least one deterministic assertion")
        _compile_workflow(
            acceptance_id=self.acceptance_id,
            plan_revision=1,
            work_specification_id="00000000-0000-4000-8000-000000000000",
            viewport_ids=tuple(self.viewport_ids),
            actions=tuple(action.to_browser_action() for action in self.actions),
        )
        return self


class BehavioralPlanProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criteria: list[BehavioralCriterionProposal] = Field(min_length=2, max_length=8)


@dataclass(frozen=True, slots=True)
class BehavioralVerificationPlanGeneration:
    proposal: BehavioralPlanProposal
    model: str
    program_version: str


class BehavioralVerificationPlanGenerationFailure(RuntimeError):
    def __init__(self, message: str, *, kind: RoutingFailureKind):
        super().__init__(message)
        self.kind = kind


def _compile_workflow(
    *,
    acceptance_id: str,
    plan_revision: int,
    work_specification_id: str,
    viewport_ids: tuple[str, ...],
    actions: tuple[BrowserAction, ...],
) -> BrowserWorkflow:
    if not isinstance(plan_revision, int) or isinstance(plan_revision, bool) or plan_revision < 1:
        raise ValueError("behavioral plan revision must be positive")
    workflow_id = f"behavioral-{work_specification_id[:8]}-r{plan_revision}-{acceptance_id.lower()}"
    workflow = BrowserWorkflow(
        workflow_id=workflow_id,
        version=1,
        viewport_ids=viewport_ids,
        actions=actions,
        timeout_ms=30_000,
    )
    BrowserWorkflowRegistry((workflow,), DEFAULT_VIEWPORTS)
    return workflow


def _serialize_action(action: BrowserAction) -> dict[str, object]:
    result: dict[str, object] = {"kind": action.kind.value}
    if action.path is not None:
        result["path"] = action.path
    if action.target is not None:
        result["target"] = {"kind": action.target.kind.value, "value": action.target.value}
    if action.value is not None:
        result["value"] = action.value
    if action.checkpoint is not None:
        result["checkpoint"] = action.checkpoint
    return result


def _canonical_json(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > MAX_PLAN_JSON_BYTES:
        raise ValueError("behavioral verification plan exceeds protected storage bound")
    return encoded


def behavioral_plan_digest(payload: dict[str, object]) -> str:
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def validate_proposal_against_acceptance(
    proposal: BehavioralPlanProposal,
    expected_acceptance: list[dict[str, str]],
) -> bool:
    expected_ids = tuple(item["id"] for item in expected_acceptance)
    actual_ids = tuple(item.acceptance_id for item in proposal.criteria)
    return (
        actual_ids == expected_ids
        and len(set(actual_ids)) == len(actual_ids)
        and all(_ACCEPTANCE_ID_RE.fullmatch(item) is not None for item in actual_ids)
    )


def compile_behavioral_plan(
    specification: WorkSpecification,
    proposal: BehavioralPlanProposal,
    *,
    plan_revision: int,
) -> dict[str, object]:
    if specification.status != "APPROVED":
        raise ValueError("behavioral verification plans require an approved Work Specification")
    expected = acceptance_map(specification)
    if not validate_proposal_against_acceptance(proposal, expected):
        raise ValueError("behavioral plan does not exactly cover the Work Specification acceptance map")

    criteria: list[dict[str, object]] = []
    for expected_item, proposed in zip(expected, proposal.criteria, strict=True):
        entry: dict[str, object] = {
            "acceptance_id": expected_item["id"],
            "acceptance_text": expected_item["text"],
            "mode": proposed.mode.value,
            "workflow": None,
        }
        if proposed.mode is BehavioralVerificationMode.BROWSER:
            workflow = _compile_workflow(
                acceptance_id=expected_item["id"],
                plan_revision=plan_revision,
                work_specification_id=specification.id,
                viewport_ids=tuple(proposed.viewport_ids),
                actions=tuple(action.to_browser_action() for action in proposed.actions),
            )
            entry["workflow"] = {
                "workflow_id": workflow.workflow_id,
                "version": workflow.version,
                "viewport_ids": list(workflow.viewport_ids),
                "timeout_ms": workflow.timeout_ms,
                "actions": [_serialize_action(action) for action in workflow.actions],
            }
        criteria.append(entry)

    payload: dict[str, object] = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "criteria": criteria,
    }
    behavioral_plan_digest(payload)
    return payload


def validate_persisted_behavioral_plan(
    specification: WorkSpecification,
    *,
    plan_revision: int,
    plan_json: str,
    plan_digest: str,
) -> dict[str, object]:
    try:
        payload = json.loads(plan_json)
    except json.JSONDecodeError as exc:
        raise ValueError("behavioral verification plan contains invalid JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise ValueError("behavioral verification plan schema is invalid")
    if behavioral_plan_digest(payload) != plan_digest:
        raise ValueError("behavioral verification plan digest mismatch")
    raw_criteria = payload.get("criteria")
    expected = acceptance_map(specification)
    if not isinstance(raw_criteria, list) or len(raw_criteria) != len(expected):
        raise ValueError("behavioral verification plan acceptance coverage mismatch")

    for raw, expected_item in zip(raw_criteria, expected, strict=True):
        if not isinstance(raw, dict):
            raise ValueError("behavioral verification plan criterion is invalid")
        if raw.get("acceptance_id") != expected_item["id"] or raw.get("acceptance_text") != expected_item["text"]:
            raise ValueError("behavioral verification plan acceptance binding mismatch")
        mode = raw.get("mode")
        workflow_payload = raw.get("workflow")
        if mode == BehavioralVerificationMode.HUMAN_ONLY.value:
            if workflow_payload is not None:
                raise ValueError("HUMAN_ONLY behavioral criterion contains executable workflow")
            continue
        if mode != BehavioralVerificationMode.BROWSER.value or not isinstance(workflow_payload, dict):
            raise ValueError("behavioral verification plan mode is invalid")
        actions_payload = workflow_payload.get("actions")
        viewports = workflow_payload.get("viewport_ids")
        if not isinstance(actions_payload, list) or not isinstance(viewports, list):
            raise ValueError("behavioral browser workflow is invalid")
        actions: list[BrowserAction] = []
        for action_payload in actions_payload:
            if not isinstance(action_payload, dict):
                raise ValueError("behavioral browser action is invalid")
            target_payload = action_payload.get("target")
            target_kind = target_value = None
            if target_payload is not None:
                if not isinstance(target_payload, dict):
                    raise ValueError("behavioral browser target is invalid")
                target_kind = target_payload.get("kind")
                target_value = target_payload.get("value")
            proposal_action = BehavioralActionProposal.model_validate(
                {
                    "kind": action_payload.get("kind"),
                    "path": action_payload.get("path"),
                    "target_kind": target_kind,
                    "target_value": target_value,
                    "value": action_payload.get("value"),
                    "checkpoint": action_payload.get("checkpoint"),
                }
            )
            actions.append(proposal_action.to_browser_action())
        workflow = _compile_workflow(
            acceptance_id=expected_item["id"],
            plan_revision=plan_revision,
            work_specification_id=specification.id,
            viewport_ids=tuple(viewports),
            actions=tuple(actions),
        )
        if (
            workflow_payload.get("workflow_id") != workflow.workflow_id
            or workflow_payload.get("version") != workflow.version
            or workflow_payload.get("timeout_ms") != workflow.timeout_ms
        ):
            raise ValueError("behavioral browser workflow identity mismatch")
    return payload


def _strip_json_fence(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return candidate


class DspyBehavioralVerificationPlanProgram:
    version = PLAN_PROGRAM_VERSION

    def __init__(self, model: str):
        try:
            import dspy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("DSPy is required for behavioral verification plan drafting") from exc

        class DraftBehavioralVerificationPlan(dspy.Signature):
            """Map an approved Work Specification to a bounded behavioral verification proposal.

            Use only the supplied Work Specification, exact acceptance map and fixed browser vocabulary.
            Return one criterion for every acceptance ID in the exact supplied order. Choose HUMAN_ONLY
            whenever browser proof would be weak, unsafe or outside the vocabulary. BROWSER workflows
            may use only the listed typed actions, semantic target kinds, relative paths and registered
            viewports. Never invent JavaScript, shell, selectors, external URLs, headers, cookies,
            credentials, provider operations, source edits or hidden reasoning.
            """

            work_specification: str = dspy.InputField()
            acceptance_map: str = dspy.InputField()
            browser_vocabulary: str = dspy.InputField()
            plan_json: str = dspy.OutputField(
                desc=(
                    "strict JSON object with criteria array; each item has acceptance_id, mode, "
                    "viewport_ids, actions; each action has only kind/path/target_kind/target_value/value/checkpoint"
                )
            )

        self._dspy = dspy
        self._lm = build_lm(model)
        self._program = dspy.Predict(DraftBehavioralVerificationPlan)

    def run(
        self,
        *,
        specification_json: str,
        acceptance_json: str,
        vocabulary_json: str,
    ) -> BehavioralPlanProposal:
        with self._dspy.context(lm=self._lm):
            prediction = self._program(
                work_specification=specification_json,
                acceptance_map=acceptance_json,
                browser_vocabulary=vocabulary_json,
            )
        try:
            payload = json.loads(_strip_json_fence(str(prediction.plan_json)))
        except json.JSONDecodeError as exc:
            raise ValueError("behavioral verification model returned invalid JSON") from exc
        return BehavioralPlanProposal.model_validate(payload)


class BehavioralVerificationPlanCoordinator:
    def __init__(self, *, router: ModelRouter[BehavioralPlanProposal] | None = None):
        self.router = router or ModelRouter()

    @staticmethod
    def browser_vocabulary() -> dict[str, object]:
        return {
            "modes": [item.value for item in BehavioralVerificationMode],
            "viewport_ids": [item.viewport_id for item in DEFAULT_VIEWPORTS],
            "action_kinds": [item.value for item in BrowserActionKind],
            "semantic_target_kinds": [item.value for item in SemanticTargetKind],
            "rules": [
                "paths must be bounded relative paths",
                "BROWSER requires at least one deterministic assertion and one screenshot",
                "HUMAN_ONLY has empty viewport_ids and actions",
                "no arbitrary selectors, scripts, URLs, headers, cookies, credentials, HTTP or shell",
            ],
        }

    async def draft(self, specification: WorkSpecification) -> BehavioralVerificationPlanGeneration:
        if specification.status != "APPROVED":
            raise ValueError("behavioral verification plans require an approved Work Specification")
        expected = acceptance_map(specification)
        specification_json = json.dumps(
            work_specification_contract(specification),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        acceptance_json = json.dumps(expected, ensure_ascii=False, separators=(",", ":"))
        vocabulary_json = json.dumps(
            self.browser_vocabulary(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        async def attempt(model: str) -> BehavioralPlanProposal:
            program = DspyBehavioralVerificationPlanProgram(model)
            return await asyncio.to_thread(
                program.run,
                specification_json=specification_json,
                acceptance_json=acceptance_json,
                vocabulary_json=vocabulary_json,
            )

        try:
            result = await self.router.route(
                attempt,
                lambda proposal: validate_proposal_against_acceptance(proposal, expected),
            )
        except RoutingFailure as exc:
            raise BehavioralVerificationPlanGenerationFailure(
                "Parallax could not produce a valid behavioral verification plan",
                kind=exc.kind,
            ) from exc
        return BehavioralVerificationPlanGeneration(
            proposal=result.value,
            model=result.model,
            program_version=PLAN_PROGRAM_VERSION,
        )


__all__ = [
    "BehavioralActionProposal",
    "BehavioralCriterionProposal",
    "BehavioralPlanProposal",
    "BehavioralVerificationMode",
    "BehavioralVerificationPlanCoordinator",
    "BehavioralVerificationPlanGeneration",
    "BehavioralVerificationPlanGenerationFailure",
    "PLAN_PROGRAM_VERSION",
    "behavioral_plan_digest",
    "compile_behavioral_plan",
    "validate_persisted_behavioral_plan",
    "validate_proposal_against_acceptance",
]
