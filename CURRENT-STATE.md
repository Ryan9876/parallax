# Parallax 2.0 Current State

Version: 0.13.1 production
Date: 2026-08-22
Status: DEPLOYED AND AUTOMATED-VALIDATED — OPERATOR AUTONOMY EXECUTION TEST PENDING
Production branch: `main`
Production application commit: `6e42c14fc1ce90144387297a3e39f3202a0e1a98`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment carrying the v0.13 autonomy UI: `dpl_3aytnFCs34WqJgjxiUz6YbZqdZ6o`
Production API deployment carrying the v0.13.1 active-spec guard: `dpl_Gg7Ps1SJc5KuqgRnm1LNymRtKCy8`

## Current production baseline

Parallax 2.0 v0.13 is now merged to `main` and deployed to the production-authenticated origin. The bounded-autonomy pilot is therefore available through the normal Parallax production URL instead of a separate preview host.

The production Code path now includes:

- persistent Work Specifications with explicit approval;
- immutable approved-spec binding for Engineering Runs;
- bounded autonomous PLAN / BUILD / TEST / VERIFY coordination;
- isolated Vercel Sandbox execution for registered protected commands;
- fail-closed execution when the isolated executor is unavailable;
- server-owned acceptance criteria, stage transitions, command registry, and stop reasons;
- a `Run autonomously` control on eligible bound Engineering Run stages;
- explicit stops at IMPLEMENT when real implementation evidence is required and at REVIEW when independent review authority is required.

The pilot still does **not** grant autonomous source editing, arbitrary shell access, Work Specification self-approval, Git commit/push/merge, or autonomous production deployment authority.

## v0.13.1 production hardening

The first production operator attempt exposed configuration drift: the deployed v0.13 API code was live, but newly created conversations still reported `P2-V0.5.0` because a stale production `PARALLAX_ACTIVE_SPEC_ID` environment override superseded the repository's `P2-V0.13.0` release baseline.

v0.13.1 adds a production-only regression guard:

- production may not resolve an active product specification older than the release baseline compiled into the application;
- a valid equal or newer production specification remains allowed;
- development and test environments can still deliberately select older specifications for regression testing;
- invalid specification identifiers continue to fail validation.

This behavior is defined by `specs/P2-V0.13.1.md` and is covered by deterministic API tests.

## Validation evidence

PR `#21` head `2388acb0c44666f85c01cc3c2c2057b087918bcf` passed:

- `Bounded Autonomy Pilot` workflow run `32560701010` — SUCCESS;
- `Parallax P2 CI` workflow run `32560701012` — SUCCESS;
- full API regression suite;
- client typecheck and web export;
- browser / Skia acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy release compilation gate.

PR `#21` was then squash-merged to `main` as `6e42c14fc1ce90144387297a3e39f3202a0e1a98`.

## Deployment evidence

The v0.13.1 API production deployment `dpl_Gg7Ps1SJc5KuqgRnm1LNymRtKCy8` is READY and was created from main commit `6e42c14fc1ce90144387297a3e39f3202a0e1a98`.

The web project correctly skipped a new production build for v0.13.1 because the patch changes API/configuration/test/spec files only. The existing production web deployment `dpl_3aytnFCs34WqJgjxiUz6YbZqdZ6o` remains the deployed v0.13 autonomy UI and is aliased to `parallax-ashy-one-20.vercel.app`.

The prior v0.13 API production deployment was `dpl_5hwaNBhsYDDbKwJB6sCk23D6YuRG`. Runtime logs confirmed authenticated production requests were reaching that deployment before the v0.13.1 hardening release.

## Remaining operator verification

The production application is deployed and automated validation is complete, but the first real user-driven isolated Sandbox execution is still pending.

Expected operator path:

1. Reload the production Parallax URL.
2. Switch to Code.
3. Start a fresh Code conversation and enter a small coding objective.
4. Capture and approve its Work Specification.
5. Confirm the Engineering Run reaches PLAN and shows `Run autonomously`.
6. Invoke `Run autonomously`.
7. Expected success path: protected PLAN evidence is created and the run advances to IMPLEMENT, then stops with `IMPLEMENTATION_REQUIRED`.
8. Expected safe-failure path: the run remains at PLAN with `EXECUTOR_UNAVAILABLE`, proving fail-closed Sandbox behavior.

Because the autonomy control is conditional on a bound Engineering Run, a fresh empty Code screen does not show the button before a coding objective, Work Specification, approval, and PLAN run exist.

## Deployment state vocabulary

- v0.13 bounded-autonomy implementation: **IMPLEMENTED**
- v0.13.1 active-spec guard: **IMPLEMENTED**
- Automated CI validation: **PASS**
- Merged to `main`: **YES**
- Production web autonomy UI: **DEPLOYED / READY**
- Production API v0.13.1: **DEPLOYED / READY**
- Production active-spec regression guard: **DEPLOYED**
- First real operator Sandbox execution: **PENDING**
- Full bounded-autonomy pilot deployment verification: **PENDING operator execution evidence**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the v0.13 production promotion, v0.13.1 hardening release, validation evidence, deployment evidence, and remaining operator test.
- `ARCHITECTURE.md`: unchanged; v0.13.1 hardens release configuration without changing the bounded-autonomy architecture or trust boundaries.
- `DESIGN-SYSTEM.md`: unchanged; no visual-language rule changed.
- `PROJECT-CONSTITUTION.md`: unchanged; the release remains consistent with existing authority, evidence, security, and human-control principles.

Historical candidate and preview evidence remains preserved in Git history.
