from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPL = ROOT / "services/api/parallax_api/intelligence/implementation_generation.py"
RECOVERY = ROOT / "services/api/parallax_api/code/agentic_candidate_recovery.py"
STRUCTURED_TEST = ROOT / "services/api/tests/test_structured_output_classification_v02315.py"
NEW_TEST = ROOT / "services/api/tests/test_server_canonicalized_content_generation_v02326.py"
ARCH = ROOT / "ARCHITECTURE.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


impl = IMPL.read_text()
impl = replace_once(impl, "import asyncio\n", "import asyncio\nimport difflib\n", "difflib import")

constants_start = impl.index("MAX_PROPOSAL_PATCHES = 16")
constants_end = impl.index("_ACCEPTANCE_RE = re.compile", constants_start)
constants = '''MAX_PROPOSAL_PATCHES = 16
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
'''
impl = impl[:constants_start] + constants + impl[constants_end:]

models_start = impl.index("class GeneratedSourcePatch(BaseModel):")
models_end = impl.index("@dataclass(frozen=True, slots=True)\nclass AcceptanceRequirement:", models_start)
models = '''class GeneratedSourcePatch(BaseModel):
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
    if "\\r" in value.replace("\\r\\n", ""):
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
        lineterm="\\n",
        n=3,
    )
    rendered: list[str] = []
    for line in generated:
        is_record = line[:1] in {" ", "+", "-"} and not line.startswith(("--- ", "+++ "))
        if is_record and not line.endswith(("\\n", "\\r\\n")):
            rendered.append(line + "\\n")
            rendered.append("\\\\ No newline at end of file\\n")
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
'''
impl = impl[:models_start] + models + impl[models_end + len("@dataclass(frozen=True, slots=True)\nclass AcceptanceRequirement:\n"):]

impl = replace_once(
    impl,
    '            payload["strict_safe_patch_rule"] = STRICT_SAFE_PATCH_RULE\n',
    '            payload["server_canonical_content_rule"] = SERVER_CANONICAL_CONTENT_RULE\n',
    "source payload rule",
)

program_start = impl.index("class DspyImplementationGenerationProgram:")
program_end = impl.index("@dataclass(frozen=True, slots=True)\nclass ImplementationGeneration:", program_start)
program = '''class DspyImplementationGenerationProgram:
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


'''
impl = impl[:program_start] + program + impl[program_end:]
IMPL.write_text(impl)

recovery = RECOVERY.read_text()
start = recovery.index("CANDIDATE_RECOVERY_VERSION = ")
end = recovery.index("_BOUNDED_ROUTING_FAILURES =", start)
new_recovery = '''CANDIDATE_RECOVERY_VERSION = "candidate-recovery-v0.23.26"
CANDIDATE_GENERATION_EXHAUSTED = "CANDIDATE_GENERATION_EXHAUSTED"
CANDIDATE_VALIDATION_REPAIR = "CANDIDATE_VALIDATION_REPAIR"
MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT = 1
_CANDIDATE_EXHAUSTED_BLOCKER = "AGENTIC_CANDIDATE_EXHAUSTED"
_FINAL_VALIDATOR_REPAIR_CONTEXT_DOMAIN = "parallax-final-validator-repair-context-v1"
_FINAL_VALIDATOR_REPAIR_CONTEXT_TOKEN_HEX = 24
logger = logging.getLogger(__name__)
VALIDATOR_REPAIR_GUIDANCE = (
    "The previous admitted candidate produced typed file-content intent but the server-owned safe proposal validator "
    "rejected the resulting canonical proposal. Repair the semantic intent without changing the approved objective or "
    "acceptance criteria. Use only the supplied protected source context. Re-check exact existing target paths, safe new "
    "target paths, complete desired UTF-8 file contents, acceptance coverage, and prohibited or secret-sensitive targets. "
    "The protected server owns source-digest binding and canonical patch rendering after generation; return file contents, "
    "not patch syntax or source digests. Do not emit duplicate targets, unsupported or binary-prone paths, secret material, "
    "or no-op edits."
)
FINAL_VALIDATOR_REPAIR_GUIDANCE = (
    "This is the single final validator-repair generation for this work unit. Re-derive a fresh semantic file-content "
    "proposal from the supplied protected source context instead of reusing or repeating any prior response. Re-check "
    "every target path, complete desired file content, source-context compatibility, and acceptance ID before returning "
    "the proposal. Patch mechanics remain protected server-owned behavior."
)
'''
recovery = recovery[:start] + new_recovery + recovery[end:]
RECOVERY.write_text(recovery)

structured = STRUCTURED_TEST.read_text()
structured = replace_once(
    structured,
    "    GeneratedSourcePatch,\n    IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT,\n",
    "    GeneratedFileContent,\n    GeneratedSourcePatch,\n    IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT,\n",
    "structured imports",
)
structured = replace_once(
    structured,
    '            acceptance_ids_covered="AC-01",\n            patches=[],\n',
    '            acceptance_ids_covered="AC-01",\n            files=[],\n',
    "malformed typed prediction",
)
old_typed = '''    def __call__(self, **_kwargs):
        proposal = _proposal(self.request)
        return SimpleNamespace(
            acceptance_ids_covered=proposal.acceptance_ids_covered,
            patches=[item.model_dump() for item in proposal.patches],
        )
'''
new_typed = '''    def __call__(self, **_kwargs):
        return SimpleNamespace(
            acceptance_ids_covered=["AC-01"],
            files=[GeneratedFileContent(path="app.py", content="new\\n").model_dump()],
        )
'''
structured = replace_once(structured, old_typed, new_typed, "typed prediction")
old_contract_test = '''def test_prompt_contract_names_exact_strict_json_shape_without_parser_relaxation():
    assert "acceptance_ids_covered" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "patches" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "path" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "expected_base_sha256" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "unified_diff" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "Do not wrap" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "code fences" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
'''
new_contract_test = '''def test_prompt_contract_names_exact_typed_content_shape_without_patch_mechanics():
    assert "acceptance_ids_covered" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "files" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "path" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "content" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "expected_base_sha256" not in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "unified_diff" not in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "Do not wrap" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
    assert "code fences" in IMPLEMENTATION_PROPOSAL_OUTPUT_CONTRACT
'''
structured = replace_once(structured, old_contract_test, new_contract_test, "output contract test")
STRUCTURED_TEST.write_text(structured)

NEW_TEST.write_text('''from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from parallax_api.code.agentic_candidate_recovery import (
    FINAL_VALIDATOR_REPAIR_GUIDANCE,
    MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT,
    VALIDATOR_REPAIR_GUIDANCE,
)
from parallax_api.code.patching import EMPTY_SHA256, PatchError, SourcePatch, TextPatchEngine
from parallax_api.code.source_context import SourceContextFile, SourceContextSnapshot
from parallax_api.intelligence.implementation_generation import (
    GeneratedFileContent,
    ImplementationContentProposal,
    ImplementationProposal,
    ModelOutputValidationError,
    canonicalize_content_proposal,
    render_content_unified_diff,
)


def _snapshot(path: str | None = "app.py", content: str = "old\\n") -> SourceContextSnapshot:
    files = ()
    total = 0
    if path is not None:
        encoded = content.encode("utf-8")
        files = (SourceContextFile(path, sha256(encoded).hexdigest(), len(encoded), content),)
        total = len(encoded)
    return SourceContextSnapshot(
        files=files,
        digest=sha256(b"p2326-source").hexdigest(),
        total_bytes=total,
        excluded_secret_files=0,
        omitted_bounded_files=0,
    )


def _source_patch(proposal: ImplementationProposal) -> SourcePatch:
    item = proposal.patches[0]
    return SourcePatch(
        path=item.path,
        expected_base_sha256=item.expected_base_sha256,
        unified_diff=item.unified_diff,
    )


def test_existing_file_intent_binds_protected_sha_and_round_trips(tmp_path: Path):
    source = _snapshot()
    proposal = canonicalize_content_proposal(
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[GeneratedFileContent(path="app.py", content="new\\n")],
        ),
        source,
    )

    assert proposal.patches[0].expected_base_sha256 == source.files[0].sha256
    assert proposal.patches[0].unified_diff.startswith("--- a/app.py\\n+++ b/app.py\\n")

    (tmp_path / "app.py").write_text("old\\n")
    prepared = TextPatchEngine().prepare(tmp_path, _source_patch(proposal))
    assert prepared.after == b"new\\n"


def test_new_nested_file_intent_uses_empty_base_and_existing_safe_engine(tmp_path: Path):
    proposal = canonicalize_content_proposal(
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[
                GeneratedFileContent(
                    path="prototypes/fml-data-readiness/index.html",
                    content="<main>ready</main>\\n",
                )
            ],
        ),
        _snapshot(path=None),
    )
    patch = proposal.patches[0]
    assert patch.expected_base_sha256 == EMPTY_SHA256
    assert patch.unified_diff.startswith(
        "--- /dev/null\\n+++ b/prototypes/fml-data-readiness/index.html\\n"
    )

    engine = TextPatchEngine()
    prepared = engine.prepare(tmp_path, _source_patch(proposal))
    assert not (tmp_path / "prototypes").exists()
    engine.commit(tmp_path, prepared)
    assert (tmp_path / "prototypes/fml-data-readiness/index.html").read_text() == "<main>ready</main>\\n"


def test_duplicate_and_noop_content_intents_fail_closed():
    with pytest.raises(ValidationError):
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[
                GeneratedFileContent(path="app.py", content="one\\n"),
                GeneratedFileContent(path="app.py", content="two\\n"),
            ],
        )

    with pytest.raises(ModelOutputValidationError):
        canonicalize_content_proposal(
            ImplementationContentProposal(
                acceptance_ids_covered=["AC-01"],
                files=[GeneratedFileContent(path="app.py", content="old\\n")],
            ),
            _snapshot(),
        )


def test_unselected_existing_file_collision_remains_safe_engine_rejection(tmp_path: Path):
    (tmp_path / "app.py").write_text("existing\\n")
    proposal = canonicalize_content_proposal(
        ImplementationContentProposal(
            acceptance_ids_covered=["AC-01"],
            files=[GeneratedFileContent(path="app.py", content="changed\\n")],
        ),
        _snapshot(path=None),
    )
    with pytest.raises(PatchError):
        TextPatchEngine().prepare(tmp_path, _source_patch(proposal))


def test_renderer_preserves_trailing_newline_semantics_and_is_deterministic(tmp_path: Path):
    cases = [
        ("old\\n", "new\\n"),
        ("old", "new"),
        ("old\\n", "new"),
        ("old", "new\\n"),
    ]
    for index, (before, after) in enumerate(cases):
        path = f"case{index}.txt"
        first = render_content_unified_diff(path=path, before=before, after=after, creating=False)
        second = render_content_unified_diff(path=path, before=before, after=after, creating=False)
        assert first == second
        target = tmp_path / path
        target.write_text(before, newline="")
        patch = SourcePatch(
            path=path,
            expected_base_sha256=sha256(before.encode()).hexdigest(),
            unified_diff=first,
        )
        prepared = TextPatchEngine().prepare(tmp_path, patch)
        assert prepared.after.decode("utf-8") == after


def test_model_visible_content_schema_has_no_patch_authority():
    assert set(GeneratedFileContent.model_fields) == {"path", "content"}
    assert set(ImplementationContentProposal.model_fields) == {"acceptance_ids_covered", "files"}


def test_validator_repair_guidance_is_semantic_and_retry_budget_unchanged():
    joined = f"{VALIDATOR_REPAIR_GUIDANCE} {FINAL_VALIDATOR_REPAIR_GUIDANCE}"
    assert "complete desired" in joined
    assert "server" in joined.casefold()
    assert "source-digest binding" in joined
    assert "hunk coordinates" not in joined
    assert MAX_VALIDATOR_REPAIR_RETRIES_PER_WORK_UNIT == 1
''')

arch = ARCH.read_text()
arch = replace_once(arch, "Version: 3.36\n", "Version: 3.37\n", "architecture version")
marker = "## Version relationship\n\n"
paragraph = (
    "Architecture v3.37 narrows the hosted implementation-generation boundary from model-authored unified-diff mechanics "
    "to typed semantic file-content intent. Models provide only exact acceptance coverage plus bounded repository-relative "
    "target paths and desired UTF-8 file contents. The protected server binds existing targets to the exact path/SHA/content "
    "in the bounded source snapshot, treats absent selected paths only as non-authoritative empty-base new-file intent, and "
    "deterministically renders strict single-file unified diffs before constructing the unchanged canonical "
    "ImplementationProposal. The existing CanonicalizingTextPatchEngine, SafeImplementationEngine, collision/stale-source, "
    "path/secret/symlink/extension/size/hierarchy protections, source-lineage acceptance, disposable BUILD/TEST/VERIFY, "
    "delivery authority and human REVIEW ceiling remain authoritative. An unselected path that actually exists still fails "
    "closed at the safe source boundary. Bounded Luna/Terra/Sol routing, the 60-second hosted timeout, zero hidden transport "
    "retries, the single final validator repair and its cache-distinct context token are unchanged. Architecture v3.36 "
    "remains the nested-source creation and ambiguous transport-reconciliation foundation.\n\n"
)
arch = replace_once(arch, marker, marker + paragraph, "architecture relationship")
ARCH.write_text(arch)
