# Parallax Parallel Development Operating Guide

Status: Durable development protocol
Authority: `PROJECT-CONSTITUTION.md` + `AGENTS.md`
Live coordination: GitHub open `[WS]` issues and pull requests

## Why this exists

Parallax is developed through multiple ChatGPT conversations. Conversation context is useful, but it is not a concurrency-control system. GitHub is the authoritative coordination layer for parallel development.

The goal is to let multiple chats implement independent slices at the same time while making collisions visible before code is written and keeping final integration controlled.

## The model

```text
                         ┌────────────────────────────┐
                         │ Integration / Control Chat │
                         └─────────────┬──────────────┘
                                       │
                 reads [WS] issues + PRs + authoritative records
                                       │
          ┌────────────────────────────┼────────────────────────────┐
          │                            │                            │
   Worker Chat A                Worker Chat B                Worker Chat C
   issue + branch               issue + branch               issue + branch
   bounded scope                bounded scope                bounded scope
          │                            │                            │
          └──────────── validated PRs ┴──────────── validated PRs ─┘
                                       │
                              serialized integration
                                       │
                                latest-main gates
                                       │
                                     main
                                       │
                           deployment + verification
```

Parallel implementation is encouraged. Parallel final integration and production promotion are not.

## Sources of truth, in order

For concurrent development state, use this precedence:

1. `PROJECT-CONSTITUTION.md`
2. `ARCHITECTURE.md`
3. `DESIGN-SYSTEM.md`
4. `CURRENT-STATE.md`
5. `AGENTS.md` and the approved specification for the active change
6. open GitHub `[WS]` issues
7. Git branches and pull requests
8. CI/evaluation/deployment evidence
9. individual chat history

A chat may remember useful context, but it does not gain file ownership or integration authority from memory.

## Roles

### Integration / Control Tower chat

Keep one Parallax project conversation as the default integration chat. Its job is to:

- review open `[WS]` issues and PRs;
- identify path, subsystem, dependency, and release-order collisions;
- keep workstreams narrow enough to run concurrently;
- decide integration order when two valid PRs interact;
- require a candidate to incorporate latest `main` before merge when relevant;
- rerun the appropriate gates after integration changes;
- merge one PR at a time;
- perform or coordinate deployment;
- verify production rather than assuming deployment success;
- update `CURRENT-STATE.md` only from evidence;
- close completed workstream issues.

The integration chat has no standing right to rewrite worker-owned files while a workstream is active. If it needs to change an owned path, it coordinates through the workstream issue first.

### Worker chat

A worker chat owns one bounded objective at a time. Its job is to:

- read the authoritative records before material work;
- inspect the active workstream ledger;
- reserve concrete scope before implementation;
- create an isolated branch from current `main` unless an explicit dependency requires another base;
- create/approve the specification before substantive implementation;
- stay within declared scope;
- validate the work;
- open a PR with integration metadata;
- update its `[WS]` issue with validation and dependency notes;
- stop before merge/deployment by default.

## Start-of-work protocol for every worker chat

Before writing code:

1. Read `AGENTS.md`, `PROJECT-CONSTITUTION.md`, `ARCHITECTURE.md`, `DESIGN-SYSTEM.md`, `CURRENT-STATE.md`, and this file from `main`.
2. Search open GitHub issues whose title begins with `[WS]`.
3. Review open PRs that may touch the same subsystem.
4. Either adopt an existing relevant workstream or create a new `[WS]` issue.
5. Declare:
   - Workstream ID
   - state (`PLANNED`, `ACTIVE`, or `BLOCKED`)
   - objective
   - branch
   - base ref/commit
   - owned paths
   - shared/integration-sensitive paths
   - dependencies
   - acceptance gate
   - collision policy
   - completion condition
6. If intended work materially overlaps an ACTIVE workstream, do not independently implement the overlap. Narrow scope, sequence after it, or coordinate explicitly.
7. Create an isolated branch.
8. Create the approved spec before substantive implementation.
9. Implement and validate.
10. Open a PR. Do not merge/deploy unless explicitly assigned the integration role.

## Scope rules

### Owned paths

Owned paths are the files or narrow directories the worker expects to modify. Ownership is temporary and exists only while the workstream is ACTIVE.

Prefer narrow claims:

Good:

```text
services/api/parallax_api/execution/**
services/api/tests/test_execution_*.py
```

Too broad unless truly necessary:

```text
services/**
apps/**
```

### Shared / integration-sensitive paths

These are paths that may be changed only with coordination because many workstreams depend on them. Typical examples:

- `.github/workflows/**`
- root `package.json`
- shared API schemas/contracts
- cross-cutting migrations
- `ARCHITECTURE.md`
- `DESIGN-SYSTEM.md`
- `PROJECT-CONSTITUTION.md`
- `CURRENT-STATE.md`

Authoritative files are not automatically locked; they are updated when their durable subject changes. Their shared status means workers must explicitly account for concurrent edits.

## Collision decision

When overlap is found, use this order:

1. **Can one worker avoid the shared path?** Do that.
2. **Can the work be sequenced without meaningful delay?** Later worker depends on earlier PR.
3. **Can a stable interface be agreed first?** Create a small interface/spec PR, then parallelize behind it.
4. **Is the overlap intrinsic?** Merge the objectives into one workstream instead of pretending they are independent.

Do not resolve architecture collisions by allowing both branches to rewrite the same contract and hoping Git merge will decide correctly.

## Integration protocol

A worker PR passing CI is necessary but not always sufficient.

Before merge, the Integration chat checks:

1. The workstream issue is current.
2. The PR stayed within its declared scope or the reservation was updated before scope expansion.
3. Dependencies are merged or intentionally pinned.
4. No higher-priority active workstream now conflicts with the candidate.
5. The candidate includes latest `main` when another relevant PR has merged since validation.
6. Appropriate CI, protected evaluations, browser tests, migrations, security checks, and release gates pass on the integrated candidate.
7. The PR accurately distinguishes generated, validated, deployed, and deployment-verified states.
8. Only then is the PR merged.

After one PR merges, the next interacting PR must reassess against the new `main` before merge. This is the key safeguard that allows implementation to be parallel while integration remains coherent.

## Production rule

Production promotion is serialized. By default, only the Integration chat merges/deploys worker output.

A successful build is not deployment evidence. A READY deployment is not full deployment verification unless the required live health, security-boundary, behavior, and runtime-error checks also pass.

## Current active collision to respect

The v0.13.0 Identity & Workspace Polish workstream is tracked in GitHub issue #30 / PR #20. Until it closes, treat its declared client visual paths and `DESIGN-SYSTEM.md` as owned/integration-sensitive. New workers should concentrate on non-overlapping backend, orchestration, app-builder, evaluation, tool, or reliability areas unless the integration chat explicitly coordinates otherwise.

## Initial parallel lanes toward app-builder readiness

These are planning lanes, not automatic ownership grants. Every implementation still needs a concrete `[WS]` reservation.

### Lane A — Agent runtime and orchestration

Outcome: Parallax can decompose an app-building objective into durable executable stages and resume safely.

Likely concerns:

- execution planning/state machine;
- tool-call contracts;
- interruption/recovery;
- human approval boundaries;
- task dependency graph;
- idempotency.

### Lane B — Project/app workspace lifecycle

Outcome: Parallax can create and operate on multiple isolated app projects rather than only itself.

Likely concerns:

- project identity and metadata;
- repository/workspace isolation;
- durable project specification;
- environment/config boundaries;
- project switching and resumability.

### Lane C — Tool and connector execution layer

Outcome: an app project can safely use GitHub, deployment, database, and other authorized tools through explicit contracts.

Likely concerns:

- tool capability registry;
- per-project authority;
- dry-run/preview paths;
- error normalization;
- secret boundaries;
- audit evidence.

### Lane D — Evaluation, reliability, and observability

Outcome: autonomous work can be trusted because Parallax measures regressions and exposes operational evidence.

Likely concerns:

- app-builder benchmark suite;
- task-level success metrics;
- trace/evidence storage without hidden reasoning;
- retry/failure classification;
- structured logs;
- release quality gates.

### Lane E — Product workspace UX

Outcome: creating and running an app project feels simple rather than like operating an IDE.

This lane should avoid active v0.13 client paths until PR #20 closes, then work behind stable runtime/project contracts established by the other lanes.

## Recommended first parallel wave

After this foundation is merged, start with three mostly separable workstreams:

1. **App-builder readiness architecture and critical path** — convert issue #32 from planning into a bounded architecture/spec workstream.
2. **Project lifecycle backend** — project identity, persistence, isolation, and project-level state APIs.
3. **Agent execution/orchestration contract** — project-scoped execution state, tool authority, and resumable task stages.

A fourth worker can build **evaluation/observability contracts** against those interfaces without modifying their implementation internals.

Do not start a large UX implementation until the project/runtime contracts stabilize; otherwise frontend work will repeatedly be invalidated by backend contract churn.

## Worker-chat bootstrap prompt

Copy this into a new Parallax project chat:

> You are a Parallax worker chat. Before changing code, read `AGENTS.md`, `PROJECT-CONSTITUTION.md`, `ARCHITECTURE.md`, `DESIGN-SYSTEM.md`, `CURRENT-STATE.md`, and `PARALLEL-DEVELOPMENT.md` from the GitHub `main` branch. Search open GitHub issues with the `[WS]` prefix and review open PRs. Create or adopt exactly one ACTIVE workstream issue and declare its branch/base, owned paths, shared paths, dependencies, acceptance gate, collision policy, and completion condition. Stop or narrow scope if the intended work materially overlaps another ACTIVE workstream. Create an isolated branch from current `main`, follow spec-first rules, implement and validate only within the reserved scope, then open a PR and update the workstream issue with evidence/integration notes. Do not merge or deploy; the Integration chat handles final integration by default.

## Integration-chat bootstrap prompt

Use this in the Parallax project conversation designated as Control Tower:

> You are the Parallax Integration / Control Tower chat. Read the authoritative records and `PARALLEL-DEVELOPMENT.md`. Review all open `[WS]` issues and pull requests. Maintain the integration queue, identify path/dependency conflicts, keep workstreams narrow, and serialize final merges. Before merging a worker PR, require relevant dependencies to be integrated, refresh/reconcile against latest `main`, and rerun the appropriate gates. Only promote/deploy validated integrated candidates. Update `CURRENT-STATE.md` only from validated/deployed evidence and close completed workstream issues.

## End-of-work protocol

A worker finishes by recording on its `[WS]` issue:

- PR number;
- final changed paths;
- validation evidence;
- known risks/limitations;
- dependency/integration notes;
- whether authoritative records need changes after integration.

The Integration chat closes the issue after the work is merged or intentionally abandoned. Deployment-related issues remain open until the required deployment state is verified.
