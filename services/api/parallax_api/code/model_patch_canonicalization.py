from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import re

from .patching import (
    PatchConflictError,
    PatchError,
    PatchFormatError,
    PatchLimitError,
    PreparedPatch,
    SourcePatch,
    StaleBaseError,
    TextPatchEngine,
    UnsafeTargetError,
)


logger = logging.getLogger(__name__)

_HUNK_INTENT_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")
_NO_NEWLINE_MARKER = r"\ No newline at end of file"


@dataclass(frozen=True, slots=True)
class _IntentRecord:
    prefix: str
    content: str
    no_newline: bool = False


class CanonicalizingTextPatchEngine(TextPatchEngine):
    """Recover exact model edit intent before the ordinary strict patch verifier.

    The first path is always the inherited strict parser. Canonicalization is
    attempted only for unified-diff format/position failures. It never repairs
    stale source digests, unsafe targets, secret-sensitive content, unsupported
    targets, limits, or filesystem safety. A recovered diff is submitted back
    through ``TextPatchEngine.prepare`` before it can be accepted.
    """

    def prepare(self, workspace_root: str | Path, patch: SourcePatch) -> PreparedPatch:
        try:
            return super().prepare(workspace_root, patch)
        except StaleBaseError:
            logger.warning("parallax_model_patch_prepare rejected reason=stale_base")
            raise
        except UnsafeTargetError:
            logger.warning("parallax_model_patch_prepare rejected reason=unsafe_target")
            raise
        except PatchLimitError:
            logger.warning("parallax_model_patch_prepare rejected reason=limit")
            raise
        except (PatchFormatError, PatchConflictError) as strict_error:
            try:
                canonical = self._canonicalize_unified_diff(
                    workspace_root=workspace_root,
                    path=patch.path,
                    diff=patch.unified_diff,
                )
                recovered = SourcePatch(
                    path=patch.path,
                    expected_base_sha256=patch.expected_base_sha256,
                    unified_diff=canonical,
                )
                prepared = super().prepare(workspace_root, recovered)
            except StaleBaseError:
                logger.warning("parallax_model_patch_prepare rejected reason=stale_base_after_canonicalization")
                raise
            except UnsafeTargetError:
                logger.warning("parallax_model_patch_prepare rejected reason=unsafe_target_after_canonicalization")
                raise
            except PatchLimitError:
                logger.warning("parallax_model_patch_prepare rejected reason=limit_after_canonicalization")
                raise
            except PatchConflictError:
                logger.warning("parallax_model_patch_prepare rejected reason=exact_match_conflict")
                raise
            except PatchFormatError:
                logger.warning("parallax_model_patch_prepare rejected reason=canonicalization_format")
                raise
            except PatchError:
                logger.warning("parallax_model_patch_prepare rejected reason=canonicalization_patch")
                raise
            logger.info(
                "parallax_model_patch_prepare canonicalized strict_failure=%s",
                type(strict_error).__name__,
            )
            return prepared

    def _canonicalize_unified_diff(
        self,
        *,
        workspace_root: str | Path,
        path: str,
        diff: str,
    ) -> str:
        normalized = self.normalize_path(path)
        root, target = self._safe_target(workspace_root, normalized)
        del root

        if target.exists():
            if not target.is_file() or target.is_symlink():
                raise UnsafeTargetError("existing patch target must be a regular non-symlink file")
            before_bytes = target.read_bytes()
            if len(before_bytes) > self.max_file_bytes:
                raise PatchLimitError("source file exceeds the configured file-size limit")
            before = self._decode_source(before_bytes)
            creating = False
        else:
            before = ""
            creating = True

        lines = self._strip_git_prologue(diff.splitlines(keepends=True), normalized, creating=creating)
        if len(lines) < 3:
            raise PatchFormatError("model patch intent must contain file headers and at least one hunk")

        old_header = self._intent_header_path(lines[0], prefix="--- ")
        new_header = self._intent_header_path(lines[1], prefix="+++ ")
        allowed_new = {normalized, f"b/{normalized}"}
        if creating:
            if old_header != "/dev/null" or new_header not in allowed_new:
                raise PatchFormatError("new-file model patch headers do not match the declared target")
        else:
            if old_header not in {normalized, f"a/{normalized}"} or new_header not in allowed_new:
                raise PatchFormatError("model patch headers do not match the declared target")

        source = before.splitlines(keepends=True)
        canonical: list[str] = [
            f"--- {'/dev/null' if creating else f'a/{normalized}'}\n",
            f"+++ b/{normalized}\n",
        ]
        index = 2
        source_cursor = 0
        output_length = 0
        hunk_count = 0

        while index < len(lines):
            header = lines[index].rstrip("\r\n")
            match = _HUNK_INTENT_RE.fullmatch(header)
            if match is None:
                raise PatchFormatError("unexpected model patch content outside a hunk")
            declared_old_start = int(match.group(1))
            index += 1

            records: list[_IntentRecord] = []
            while index < len(lines):
                raw = lines[index]
                if _HUNK_INTENT_RE.fullmatch(raw.rstrip("\r\n")):
                    break
                if raw.startswith("diff --git ") or raw.startswith("--- ") or raw.startswith("+++ "):
                    raise PatchFormatError("multi-file model patch intent is forbidden")
                if raw.rstrip("\r\n") == _NO_NEWLINE_MARKER:
                    if not records or records[-1].no_newline:
                        raise PatchFormatError("orphaned no-newline marker in model patch intent")
                    previous = records[-1]
                    content = previous.content
                    if content.endswith("\r\n"):
                        content = content[:-2]
                    elif content.endswith("\n"):
                        content = content[:-1]
                    records[-1] = _IntentRecord(previous.prefix, content, True)
                    index += 1
                    continue
                if not raw or raw[0] not in {" ", "+", "-"}:
                    raise PatchFormatError("unsupported model patch record")
                records.append(_IntentRecord(raw[0], raw[1:]))
                index += 1

            if not records:
                raise PatchFormatError("model patch hunk contains no records")
            hunk_count += 1
            old_records = tuple(record.content for record in records if record.prefix in {" ", "-"})
            old_seen = len(old_records)
            new_seen = sum(1 for record in records if record.prefix in {" ", "+"})
            if old_seen == 0 and new_seen == 0:
                raise PatchFormatError("model patch hunk contains no source change")

            if creating:
                if hunk_count != 1 or old_seen != 0 or any(record.prefix != "+" for record in records):
                    raise PatchFormatError("new-file recovery requires one addition-only hunk")
                match_index = 0
            elif old_seen == 0:
                # Without source-consuming records there is no exact text anchor.
                # The model-declared old position therefore remains authoritative
                # for placement, but not for hunk counts or new-file coordinates.
                match_index = declared_old_start
                if match_index < source_cursor or match_index > len(source):
                    raise PatchConflictError("pure insertion position is outside current source")
            else:
                declared_index = declared_old_start - 1
                if (
                    declared_index >= source_cursor
                    and declared_index + old_seen <= len(source)
                    and tuple(source[declared_index : declared_index + old_seen]) == old_records
                ):
                    match_index = declared_index
                else:
                    candidates = [
                        candidate
                        for candidate in range(source_cursor, len(source) - old_seen + 1)
                        if tuple(source[candidate : candidate + old_seen]) == old_records
                    ]
                    if len(candidates) != 1:
                        raise PatchConflictError("model patch source intent is missing or ambiguous")
                    match_index = candidates[0]

            if match_index < source_cursor:
                raise PatchConflictError("model patch hunks overlap")
            output_length += match_index - source_cursor
            canonical_old_start = match_index if old_seen == 0 else match_index + 1
            canonical_new_start = output_length if new_seen == 0 else output_length + 1
            canonical.append(
                f"@@ -{canonical_old_start},{old_seen} +{canonical_new_start},{new_seen} @@\n"
            )
            canonical.extend(self._render_record(record) for record in records)
            source_cursor = match_index + old_seen
            output_length += new_seen

        if hunk_count == 0:
            raise PatchFormatError("model patch intent contains no hunks")
        return "".join(canonical)

    @staticmethod
    def _intent_header_path(line: str, *, prefix: str) -> str:
        if not line.startswith(prefix):
            raise PatchFormatError("model patch file header is malformed")
        value = line[len(prefix) :].rstrip("\r\n")
        # Timestamps are common in generic unified diffs. They carry no target
        # authority, so a tab-delimited timestamp may be discarded while the
        # actual path must still match the separately declared safe target.
        if "\t" in value:
            value = value.split("\t", 1)[0]
        if not value or " " in value or "\t" in value:
            raise PatchFormatError("model patch file header path is not canonicalizable")
        return value

    @staticmethod
    def _render_record(record: _IntentRecord) -> str:
        content = record.content
        if record.no_newline or not content.endswith("\n"):
            return f"{record.prefix}{content}\n{_NO_NEWLINE_MARKER}\n"
        return f"{record.prefix}{content}"

    @classmethod
    def _strip_git_prologue(
        cls,
        lines: list[str],
        path: str,
        *,
        creating: bool,
    ) -> list[str]:
        if not lines or not lines[0].startswith("diff --git "):
            return lines
        header = lines[0].rstrip("\r\n").split(" ")
        if header != ["diff", "--git", f"a/{path}", f"b/{path}"]:
            raise PatchFormatError("git-style model patch prologue does not match the declared target")
        index = 1
        if index < len(lines) and lines[index].startswith("index "):
            index += 1
        if index < len(lines) and lines[index].startswith("new file mode "):
            if not creating or lines[index].rstrip("\r\n") != "new file mode 100644":
                raise PatchFormatError("unsupported model patch file-mode intent")
            index += 1
        if index < len(lines) and lines[index].startswith("deleted file mode "):
            raise PatchFormatError("file deletion is not canonicalizable")
        return lines[index:]


__all__ = ["CanonicalizingTextPatchEngine"]
