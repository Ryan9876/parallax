---
name: Parallel development workstream
about: Reserve a bounded Parallax implementation scope before a worker chat changes code
title: "[WS] "
labels: ""
assignees: ""
---

## Workstream

ID: `WS-`
State: `PLANNED | ACTIVE | BLOCKED`
Owner / chat role: `worker | integration`

## Objective

State one bounded outcome. Avoid combining unrelated product areas merely to reduce the number of workstreams.

## Branch and base

Branch: `ws/<workstream>-<slug>`
Base: `main@<commit-or-ref>`

## Owned paths

List the narrow files/directories this workstream is allowed to modify.

- `path/**`

## Shared / integration-sensitive paths

List cross-cutting files/contracts this workstream may need but cannot treat as exclusive ownership.

- none

## Dependencies

List workstream issues/PRs/contracts that must land first, or `none`.

- none

## Acceptance gate

List the spec and validation evidence required before the PR is handed to Integration.

- Spec: `P2-V0.0.0`
- Required checks:
  - `...`

## Collision review

- [ ] Read `AGENTS.md` and `PARALLEL-DEVELOPMENT.md`.
- [ ] Searched open `[WS]` issues.
- [ ] Reviewed relevant open PRs.
- [ ] No uncoordinated material path/contract overlap exists.

If overlap exists, explain the sequencing/interface agreement here before implementation.

## Collision policy

State what this worker will do if implementation discovers overlap or an undeclared shared contract.

Default: stop changing the overlapping path, update this issue, and coordinate with the other workstream / Integration chat before continuing.

## Completion condition

A worker workstream is ready for Integration when:

- implementation matches the approved spec;
- declared validation passes;
- a PR is open;
- final changed paths and integration risks are recorded on this issue;
- the worker has not merged/deployed unless explicitly delegated.

## Completion evidence

PR: `#`
Final changed paths:
- `...`

Validation evidence:
- `...`

Known risks / limitations:
- none

Integration notes:
- none

Authoritative-record implications:
- none
