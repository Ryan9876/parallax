# Parallax 2.0 — Safe Source Implementation and Patch Engine

Status: APPROVED FOR IMPLEMENTATION
Spec ID: P2-V0.15.44
Workstream: WS-APP-SAFE-IMPLEMENTATION / GitHub issue #44
Depends on: current protected Code/Engineering Run contracts in `main`; Project/App lifecycle #43 before project-scoped production integration
Method: additive spec-first implementation with protected negative safety tests

## 1. Objective

Create a separable, bounded source implementation engine for the protected Code lifecycle that can prepare and apply deterministic text-file changes inside an explicitly supplied isolated workspace. The engine must produce inspectable implementation evidence while refusing path escape, stale input, malformed patches, unsupported targets, excessive sizes, and partial multi-file success.

This first slice establishes the source-mutation contract only. It does not connect the engine to the autonomy coordinator or grant Git, shell, network, deployment, Work Specification approval, or production authority.

## 2. Scope

- Add a strict text patch contract containing a relative target path, expected base SHA-256 digest, and single-target unified diff.
- Resolve every target beneath an explicit workspace root and reject traversal or symlink escape.
- Support bounded modification of existing UTF-8 text source files.
- Support bounded creation of new UTF-8 text source files when the declared parent directory already exists.
- Parse and apply a strict subset of unified diff syntax without invoking a shell, Git, external patch binary, or network service.
- Require exact base-content digest agreement before preparation succeeds.
- Prepare every patch before mutating any file in a multi-file implementation request.
- Commit prepared changes atomically per file and restore earlier writes if a later commit fails.
- Emit deterministic, observable evidence including path, created state, before/after digests and sizes, patch digest/size, artifact identity, and a workspace digest derived from the completed artifact set.
- Keep implementation independent of durable Project identity so #43 can provide the accepted project binding during serialized integration.

## 3. Security

The workspace is a security boundary, not a path hint.

- User/model content never becomes executable command text.
- Absolute paths, `..` traversal, NUL-containing paths, and resolved paths outside the workspace are denied.
- Existing symlinks in the target path are denied so an in-workspace name cannot redirect writes elsewhere.
- Targets must be regular UTF-8 text files or supported new text-source paths; binary content and unsupported extensions fail closed.
- Secret-sensitive filenames and locations such as `.env`, credentials, private keys, token/secret files, SSH material, and Git internals fail closed.
- Patch and file sizes are bounded before mutation; result size is bounded after patch application.
- A caller must provide the exact SHA-256 of the expected pre-image. Existing-file mismatch and non-empty base expectation for a new file are stale-base failures.
- Unified diff headers must identify exactly the declared target; malformed, multi-file, overlapping, out-of-order, or content-mismatched hunks fail closed.
- Failure evidence must never be represented as protected success.
- No shell, arbitrary HTTP, Git commit/push/merge, Vercel promotion, provider secret, or deployment authority is added.

## 4. Non-goals

- Wiring the new engine into `autonomy.py`, `service.py`, `sandbox_execution.py`, or `state_machine.py` in this workstream.
- Creating a durable Project/App model, project identifier, repository binding, or migration; #43 owns that contract.
- Creating project-scoped external tool authority; #45 owns that contract.
- Changing protected app-builder evaluation or promotion thresholds; #46 owns that contract.
- Supporting binary patches, file deletion/rename, chmod, directory creation, symlink creation, Git metadata patches, or arbitrary patch formats.
- Executing generated code, installing dependencies, calling providers, committing source, opening GitHub pull requests from runtime code, or deploying applications.
- Claiming autonomous IMPLEMENT completion in production before serialized integration and protected validation authorize it.

## 5. Acceptance criteria

### AC-01 Workspace confinement
Every accepted target is a relative workspace path whose lexical and resolved location remains under the declared workspace root. Absolute paths, traversal, NULs, Git internals, and symlink-based escape are rejected before mutation.

### AC-02 Exact stale-base protection
Existing-file patch preparation requires the caller's expected base SHA-256 to equal the actual current file digest. New-file creation requires the SHA-256 of empty content. Any mismatch fails before mutation and preserves the original workspace.

### AC-03 Bounded UTF-8 source targets
The engine accepts only supported UTF-8 text/source targets within configured file-size and result-size limits. Binary content, unsupported target types/extensions, directories, secret-sensitive targets, and oversized inputs fail closed.

### AC-04 Strict single-target unified diff
The patch parser accepts only a bounded single-target unified diff whose old/new headers match the declared target and whose hunks are ordered, non-overlapping, count-consistent, and exact against the base content. Malformed headers, multiple file sections, mismatched context/removal lines, or invalid hunk counts fail without mutation.

### AC-05 Existing-file modification and new-file creation
A valid bounded patch can deterministically modify an existing supported text file or create a new supported text file beneath an already-existing safe parent directory. New-file patches use `/dev/null` as the old side and cannot overwrite an existing file through creation semantics.

### AC-06 Deterministic implementation evidence
Successful preparation/application yields inspectable observable evidence containing target path, created state, before/after SHA-256, before/after byte sizes, patch SHA-256, patch byte size, bounded unified diff, and artifact path/digest/size. Equivalent inputs produce equivalent evidence independent of temporary filenames.

### AC-07 Atomic multi-file implementation
A multi-file implementation request rejects duplicate target paths, prepares all patches before any mutation, commits prepared files atomically per target, and restores already-written targets if a later commit fails. No partially applied request can be returned as protected success.

### AC-08 Bounded resource behavior
The implementation has explicit maximum patch, source-file, result-file, request-file-count, and total-result limits. Limits are checked before or during preparation so attacker-controlled input cannot cause unbounded source mutation or evidence growth.

### AC-09 No authority expansion
The new modules expose no user/model-supplied shell execution, arbitrary HTTP/network access, Git history mutation, repository push/merge, provider credential handling, Work Specification self-approval, Vercel promotion, or production deployment operation.

### AC-10 Integration-ready protected contract
The successful multi-file result exposes a deterministic artifact list and workspace digest suitable for later mapping into existing protected IMPLEMENT evidence. The first slice remains independent of Project persistence and existing autonomy/service/state-machine internals, with integration deferred until #43 and interacting Wave 1 contracts stabilize.

## 6. Risks

- **Unified-diff ambiguity:** supporting too much patch syntax could create unsafe or inconsistent application. Mitigation: intentionally strict single-target parsing and fail-closed rejection of unsupported syntax.
- **Filesystem race after preparation:** another actor could alter a target between preparation and commit. Mitigation: commit re-checks the expected pre-image before replacement; later project/workspace integration should also provide exclusive workspace ownership.
- **Symlink or special-file escape:** filesystem objects can redirect or reinterpret writes. Mitigation: reject symlinks and non-regular targets and re-check path safety at commit.
- **Rollback failure:** a filesystem error during rollback could leave an uncertain workspace. Mitigation: surface a hard implementation failure with rollback-error evidence; do not return protected success. Production integration must use isolated/disposable workspace semantics.
- **Project identity drift:** implementing a project identifier here could conflict with #43. Mitigation: this slice consumes only an explicit filesystem workspace root and defers durable project binding.

## 7. Release gate

Before this worker PR is presented for integration:

- this specification and its compiled plan pass `scripts/validate_spec.py`;
- changed paths remain inside the declared issue #44 reservation;
- focused patching/implementation tests pass, including traversal, symlink escape, malformed patch, header mismatch, stale base, hunk mismatch, oversize, binary, secret-sensitive, duplicate-target, and rollback cases;
- the relevant repository API regression suite passes on the worker branch;
- no test or implementation invokes a shell, Git command, network provider, or deployment API;
- no existing autonomy/service/sandbox/state-machine file is modified;
- the worker PR records exact validation evidence and limitations;
- the worker does not merge or deploy; Integration / Control Tower revalidates against latest `main` after relevant Wave 1 dependencies land.
