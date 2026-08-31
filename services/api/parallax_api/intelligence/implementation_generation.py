from __future__ import annotations

import asyncio
import difflib
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Callable, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from ..code.source_context import SourceContextSnapshot
from .dspy_programs import build_lm
from .router import AttemptRecord, ModelOutputValidationError, ModelRouter, RoutingFailure


MAX_PROPOSAL_PATCHES = 16
MAX_GENERATED_DIFF_CHARS = 120_000
MAX_GENERATED_CONTENT_CHARS = 120_000
EMPTY_SOURCE_SHA256 = sha256(b"").hexdigest()
SOURCE_CONTEXT_AUTHORITY_RULE = (
    "The current source files were supplied by the protected server-owned runtime. Any earlier statement whose "
    "only precondition is that the repository or relevant files must be provided is satisfied by this non-empty "
    "protected source context. Do not refuse solely because source was absent from conversational context. All "
    "substantive Work Specification constraints and acceptance criteria remain authoritative."
)
SERVER_CANONICAL_CONTENT_RULE = (
    "Return desired full UTF-8 file contents, not patch mechanics. For an existing file, use its exact repository-relative "
    "path from protected source context and return the complete desired content. For a new source file, choose a safe "
    "repository-relative path and return its complete desired content. The protected server owns source SHA-256 binding, "
    "new-file classification, unified-diff rendering, patch validation, and mutation. Do not emit shell commands, patch "
    "syntax, source digests, filesystem roots, unsupported/binary targets, secret material, or no-op edits."
)
IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT = (
    "Return exactly one JSON object with only two top-level keys: acceptance_ids_covered and files. "
    "acceptance_ids_covered must be the exact supplied acceptance IDs in the same order. files must contain "
    "1-16 JSON objects, each with only path and content, where content is the desired complete UTF-8 file text. "
    "The protected server binds source digests and renders canonical unified diffs after generation. Do not wrap the "
    "JSON in Markdown, prose, labels, commentary, or code fences, and do not add any other keys."
)
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


class GeneratedFileContent(BaseModel):
    """Model-visible semantic file intent; patch mechanics remain server-owned."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    content: str = Field(max_length=MAX_GENERATED_CONTENT_CHARS)

    @field_validator("path")
    @classmethod
    def clean_path(cls, value: str) -> str:
        clean = value.strip()
        if clean != value or not clean:
            raise ValueError("generated file path must be non-empty normalized text")
        return clean

    @field_validator("content")
    @classmethod
    def valid_utf8_content(cls, value: str) -> str:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("generated file content must be valid UTF-8 text") from exc
        return value


class ImplementationContentProposal(BaseModel):
    """Typed non-authoritative model output before server patch canonicalization."""

    model_config = ConfigDict(extra="forbid")

    acceptance_ids_covered: list[str] = Field(min_length=1, max_length=32)
    files: list[GeneratedFileContent] = Field(min_length=1, max_length=MAX_PROPOSAL_PATCHES)

    @field_validator("acceptance_ids_covered")
    @classmethod
    def validate_acceptance_ids(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("generated acceptance coverage contains duplicates")
        if any(_ACCEPTANCE_RE.fullmatch(value) is None for value in values):
            raise ValueError("generated acceptance coverage contains an invalid acceptance ID")
        return values

    @model_validator(mode="after")
    def unique_targets(self) -> "ImplementationContentProposal":
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("generated content proposal contains duplicate target paths")
        return self


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


def _reject_bare_carriage_returns(value: str) -> None:
    if "\r" in value.replace("\r\n", ""):
        raise ModelOutputValidationError(
            "protected implementation content uses an unsupported line-ending form"
        )


def render_content_unified_diff(
    *,
    path: str,
    before: str,
    after: str,
    creating: bool,
) -> str:
    """Render one deterministic strict unified diff from authoritative text."""

    if before == after:
        raise ModelOutputValidationError("protected implementation content edit is a no-op")
    _reject_bare_carriage_returns(before)
    _reject_bare_carriage_returns(after)

    old_header = "/dev/null" if creating else f"a/{path}"
    new_header = f"b/{path}"
    generated = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=old_header,
        tofile=new_header,
        lineterm="\n",
        n=3,
    )
    rendered: list[str] = []
    for line in generated:
        is_record = line[:1] in {" ", "+", "-"} and not line.startswith(("--- ", "+++ "))
        if is_record and not line.endswith(("\n", "\r\n")):
            rendered.append(line + "\n")
            rendered.append("\\ No newline at end of file\n")
        else:
            rendered.append(line)
    diff = "".join(rendered)
    if not diff or len(diff) > MAX_GENERATED_DIFF_CHARS:
        raise ModelOutputValidationError(
            "server-canonicalized implementation diff exceeds the protected output boundary"
        )
    return diff


def canonicalize_content_proposal(
    proposal: ImplementationContentProposal,
    source_context: SourceContextSnapshot,
) -> ImplementationProposal:
    """Bind model semantic intent to protected source and canonical patch mechanics."""

    protected_sources = {item.path: item for item in source_context.files}
    patches: list[GeneratedSourcePatch] = []
    for item in proposal.files:
        source = protected_sources.get(item.path)
        creating = source is None
        before = "" if source is None else source.content
        expected_base_sha256 = EMPTY_SOURCE_SHA256 if source is None else source.sha256
        diff = render_content_unified_diff(
            path=item.path,
            before=before,
            after=item.content,
            creating=creating,
        )
        try:
            patches.append(
                GeneratedSourcePatch(
                    path=item.path,
                    expected_base_sha256=expected_base_sha256,
                    unified_diff=diff,
                )
            )
        except ValidationError:
            raise ModelOutputValidationError(
                "server-canonicalized implementation proposal failed the protected patch schema"
            ) from None
    try:
        return ImplementationProposal(
            acceptance_ids_covered=proposal.acceptance_ids_covered,
            patches=patches,
        )
    except ValidationError:
        raise ModelOutputValidationError(
            "server-canonicalized implementation proposal failed the protected proposal schema"
        ) from None


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

    def source_prompt_payload(self) -> dict[str, object]:
        payload = self.source_context.prompt_payload()
        if self.source_context.files:
            payload["runtime_source_access"] = "SERVER_PROVIDED_PROTECTED_SOURCE"
            payload["runtime_source_authority_rule"] = SOURCE_CONTEXT_AUTHORITY_RULE
            payload["server_canonical_content_rule"] = SERVER_CANONICAL_CONTENT_RULE
        return payload

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
    version = "implementation-generation-v0.23.26"

    def __init__(self, model: str):
        try:
            import dspy  # type: ignore
        except ImportError as exc:
            raise RuntimeError("DSPy is required for live implementation generation") from exc

        class GenerateImplementation(dspy.Signature):
            """Generate bounded semantic file-content intents for an immutable approved software Work Specification.

            Return only the requested JSON proposal. Cover exactly the acceptance IDs supplied by the server. For an
            existing file, use its exact repository-relative path from protected source context and return the complete
            desired UTF-8 content. New files may use a safe repository-relative source path. The protected server owns
            source SHA-256 binding, new-file classification, unified-diff rendering, strict patch validation and source
            mutation. Do not calculate or emit patch syntax or source digests. When source context declares
            SERVER_PROVIDED_PROTECTED_SOURCE, treat an earlier repository/file-provision precondition as satisfied by
            that current context; do not relax any substantive constraint or acceptance criterion. Never output commands,
            filesystem roots, URLs, credentials, environment values, Git/deployment actions, approval claims, hidden
            reasoning, scratchpads, or extra authority.
            """

            work_specification_json: str = dspy.InputField(desc="immutable approved Work Specification contract")
            source_context_json: str = dspy.InputField(
                desc="bounded protected source files plus the server-canonical content rule"
            )
            acceptance_ids_covered: list[str] = dspy.OutputField(
                desc="exact supplied acceptance IDs in the same order"
            )
            files: list[GeneratedFileContent] = dspy.OutputField(
                desc=IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
            )

        self._dspy = dspy
        self._lm = build_lm(model)
        self._program = dspy.Predict(GenerateImplementation)

    def run(self, *, request: ImplementationGenerationRequest) -> ImplementationProposal:
        contract_json = json.dumps(
            request.contract_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        source_json = json.dumps(
            request.source_prompt_payload(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        try:
            with self._dspy.context(lm=self._lm, adapter=self._dspy.JSONAdapter()):
                prediction = self._program(
                    work_specification_json=contract_json,
                    source_context_json=source_json,
                )
        except Exception as exc:
            if type(exc).__name__ == "AdapterParseError":
                raise ModelOutputValidationError(
                    "protected implementation proposal failed structured-output validation"
                ) from None
            raise
        try:
            content_proposal = ImplementationContentProposal.model_validate(
                {
                    "acceptance_ids_covered": prediction.acceptance_ids_covered,
                    "files": prediction.files,
                }
            )
            return canonicalize_content_proposal(content_proposal, request.source_context)
        except ModelOutputValidationError:
            raise
        except (ValidationError, TypeError, ValueError):
            raise ModelOutputValidationError(
                "protected implementation proposal failed structured-output validation"
            ) from None


@dataclass(frozen=True, slots=True)
class ImplementationGeneration:
    proposal: ImplementationProposal
    model: str
    attempts: tuple[AttemptRecord, ...]
    program_version: str


class ImplementationGenerationFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        diagnostic_evidence: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic_evidence = diagnostic_evidence


def validate_implementation_proposal(
    proposal: ImplementationProposal,
    required_acceptance_ids: tuple[str, ...],
) -> bool:
    # Exact ordered equality is intentional. Acceptance ownership remains with
    # the server-bound Work Specification, not candidate text.
    return tuple(proposal.acceptance_ids_covered) == required_acceptance_ids


ProgramFactory = Callable[[str], ImplementationGenerationProgram]
ProposalValidator = Callable[[ImplementationProposal], bool]


def _bounded_routing_failure_evidence(exc: RoutingFailure) -> dict[str, object]:
    return {
        "routing_failure": {
            "reason_code": exc.kind.value,
            "attempt_count": len(exc.attempts),
            "attempts": [
                {
                    "status": item.status,
                    "provider_kind": item.provider_kind,
                    "error_class": item.error if item.status == "provider_failed" else None,
                }
                for item in exc.attempts
            ],
            "raw_model_output_persisted": False,
            "raw_provider_payload_persisted": False,
        }
    }


class ImplementationGenerationCoordinator:
    def __init__(
        self,
        *,
        router: ModelRouter[ImplementationProposal] | None = None,
        program_factory: ProgramFactory | None = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.program_factory = program_factory or DspyImplementationGenerationProgram

    async def generate(
        self,
        request: ImplementationGenerationRequest,
        *,
        proposal_validator: ProposalValidator | None = None,
    ) -> ImplementationGeneration:
        required = request.required_acceptance_ids
        versions: dict[str, str] = {}

        async def attempt(model: str) -> ImplementationProposal:
            program = self.program_factory(model)
            versions[model] = program.version
            return await asyncio.to_thread(program.run, request=request)

        def validate(proposal: ImplementationProposal) -> bool:
            if not validate_implementation_proposal(proposal, required):
                return False
            return proposal_validator(proposal) if proposal_validator is not None else True

        try:
            result = await self.router.route(attempt, validate)
        except RoutingFailure as exc:
            raise ImplementationGenerationFailure(
                "Parallax could not produce a protected implementation proposal",
                diagnostic_evidence=_bounded_routing_failure_evidence(exc),
            ) from exc
        return ImplementationGeneration(
            proposal=result.value,
            model=result.model,
            attempts=result.attempts,
            program_version=versions.get(result.model, "implementation-generation"),
        )

    def generate_sync(
        self,
        request: ImplementationGenerationRequest,
        *,
        proposal_validator: ProposalValidator | None = None,
    ) -> ImplementationGeneration:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.generate(request, proposal_validator=proposal_validator))
        raise ImplementationGenerationFailure(
            "synchronous implementation generation cannot run inside an active event loop"
        )
