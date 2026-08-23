from __future__ import annotations

import asyncio
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..code.source_context import SourceContextSnapshot
from .dspy_programs import build_lm
from .router import AttemptRecord, ModelRouter, RoutingFailure


MAX_PROPOSAL_PATCHES = 16
MAX_GENERATED_DIFF_CHARS = 120_000
_ACCEPTANCE_RE = re.compile(r"^AC-\d{2,}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class GeneratedSourcePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    expected_base_sha256: str = Field(min_length=64, max_length=64)
    unified_diff: str = Field(min_length=1, max_length=MAX_GENERATED_DIFF_CHARS)

    @field_validator("path")
    @classmethod
    def clean_path(cls, value: str) -> str:
        clean = value.strip()
        if clean != value or not clean:
            raise ValueError("generated patch path must be non-empty normalized text")
        return clean

    @field_validator("expected_base_sha256")
    @classmethod
    def valid_digest(cls, value: str) -> str:
        if _SHA256_RE.fullmatch(value) is None:
            raise ValueError("generated base digest must be lowercase SHA-256")
        return value


class ImplementationProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    acceptance_ids_covered: list[str] = Field(min_length=1, max_length=32)
    patches: list[GeneratedSourcePatch] = Field(min_length=1, max_length=MAX_PROPOSAL_PATCHES)

    @field_validator("acceptance_ids_covered")
    @classmethod
    def validate_acceptance_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("generated acceptance coverage contains duplicates")
        if any(_ACCEPTANCE_RE.fullmatch(value) is None for value in values):
            raise ValueError("generated acceptance coverage contains an invalid acceptance ID")
        return values

    @model_validator(mode="after")
    def unique_targets(self) -> "ImplementationProposal":
        paths = [item.path for item in self.patches]
        if len(paths) != len(set(paths)):
            raise ValueError("generated proposal contains duplicate target paths")
        return self

    def digest(self) -> str:
        encoded = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class AcceptanceRequirement:
    id: str
    text: str


@dataclass(frozen=True, slots=True)
class ImplementationGenerationRequest:
    work_specification_id: str
    work_specification_revision: int
    work_specification_digest: str
    title: str
    objective: str
    constraints: tuple[str, ...]
    acceptance: tuple[AcceptanceRequirement, ...]
    source_context: SourceContextSnapshot

    @property
    def required_acceptance_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.acceptance)

    def contract_payload(self) -> dict[str, object]:
        return {
            "work_specification_id": self.work_specification_id,
            "work_specification_revision": self.work_specification_revision,
            "work_specification_digest": self.work_specification_digest,
            "title": self.title,
            "objective": self.objective,
            "constraints": list(self.constraints),
            "acceptance": [{"id": item.id, "text": item.text} for item in self.acceptance],
        }


class ImplementationGenerationProgram(Protocol):
    version: str

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal: ...


class DspyImplementationGenerationProgram:
    version = "implementation-generation-v0.15.3"

    def __init__(self, model: str):
        try:
            import dspy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("DSPy is required for live implementation generation") from exc

        class GenerateImplementation(dspy.Signature):
            """Generate a bounded source patch proposal for an immutable approved software Work Specification.

            Return only the requested JSON proposal. Cover exactly the acceptance IDs supplied by the server.
            Patch paths and expected SHA-256 values must come from source context, except a new file may bind to
            the SHA-256 of empty content. Never output commands, filesystem roots, URLs, credentials, environment
            values, Git/deployment actions, approval claims, hidden reasoning, scratchpads, or extra authority.
            """

            work_specification_json: str = dspy.InputField(desc="immutable approved Work Specification contract")
            source_context_json: str = dspy.InputField(desc="bounded source files with path, digest, size and text")
            proposal_json: str = dspy.OutputField(
                desc=(
                    "JSON object only: acceptance_ids_covered as the exact supplied IDs in the same order, and "
                    "patches as 1-16 objects containing only path, expected_base_sha256 and unified_diff"
                )
            )

        self._dspy = dspy
        self._lm = build_lm(model)
        self._program = dspy.Predict(GenerateImplementation)

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
        contract_json = json.dumps(request.contract_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        source_json = json.dumps(request.source_context.prompt_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._dspy.context(lm=self._lm):
            prediction = self._program(
                work_specification_json=contract_json,
                source_context_json=source_json,
            )
        return ImplementationProposal.model_validate_json(str(prediction.proposal_json))


@dataclass(frozen=True, slots=True)
class ImplementationGeneration:
    proposal: ImplementationProposal
    model: str
    attempts: tuple[AttemptRecord, ...]
    program_version: str


class ImplementationGenerationFailure(RuntimeError):
    pass


def validate_implementation_proposal(
    proposal: ImplementationProposal,
    required_acceptance_ids: tuple[str, ...],
) -> bool:
    # Exact ordered equality is intentional. Acceptance ownership remains with
    # the server-bound Work Specification, not candidate text.
    return tuple(proposal.acceptance_ids_covered) == required_acceptance_ids


ProgramFactory = Callable[[str], ImplementationGenerationProgram]


class ImplementationGenerationCoordinator:
    def __init__(
        self,
        *,
        router: ModelRouter[ImplementationProposal] | None = None,
        program_factory: ProgramFactory | None = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.program_factory = program_factory or DspyImplementationGenerationProgram

    async def generate(self, request: ImplementationGenerationRequest) -> ImplementationGeneration:
        required = request.required_acceptance_ids
        versions: dict[str, str] = {}

        async def attempt(model: str) -> ImplementationProposal:
            program = self.program_factory(model)
            versions[model] = program.version
            return await asyncio.to_thread(program.run, request=request)

        try:
            result = await self.router.route(
                attempt,
                lambda proposal: validate_implementation_proposal(proposal, required),
            )
        except RoutingFailure as exc:
            raise ImplementationGenerationFailure("Parallax could not produce a protected implementation proposal") from exc
        return ImplementationGeneration(
            proposal=result.value,
            model=result.model,
            attempts=result.attempts,
            program_version=versions.get(result.model, "implementation-generation"),
        )

    def generate_sync(self, request: ImplementationGenerationRequest) -> ImplementationGeneration:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.generate(request))
        raise ImplementationGenerationFailure(
            "synchronous implementation generation cannot run inside an active event loop"
        )
