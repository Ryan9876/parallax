# Parallax 2.0 Current State

Version: 0.8.0
Date: 2026-08-21
Status: DEPLOYED — INFRASTRUCTURE/BOUNDARY VERIFIED; AUTHENTICATED SPEC→CODE ROUND TRIP NOT SEPARATELY VERIFIED
Production branch: `main`
Production application release commit: `d9b501517b747b1c8432e14e0f8dc3d3609f1e3c`
Validated release-tree commit: `70a5a1fbd5efb3ccd508f5d55ce9eaddd0cae3de`
Production web deployment: `dpl_95ne1ov8Q9gR2UPxnLEez9Gw3kRb`
Production API deployment: `dpl_7gTyHaJPWvRp6SKgMrkhzqEtDHR2`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`
Applied binding migration: `20260821155808_engineering_work_spec_binding`

## Current release

Parallax 2.0 v0.8.0 is deployed through the GitHub → Vercel production pipeline.

PR #11 promoted the approved `P2-V0.8.0` Approved-Spec Execution Binding release. The exact validated release tree is `70a5a1fbd5efb3ccd508f5d55ce9eaddd0cae3de`; the resulting production merge commit is `d9b501517b747b1c8432e14e0f8dc3d3609f1e3c`.

Git comparison between the validated release tree and production merge reports **zero changed files**, so the deployed application tree is the validated tree plus merge metadata.

## v0.8.0 product change — Approved-Spec Execution Binding

Code mode now treats an explicitly operator-approved user Work Specification as the authoritative execution contract.

The release adds:

- exact `EngineeringRun` binding to `work_specification_id`, revision, and server-computed SHA-256 contract digest;
- historical compatibility for pre-v0.8 unbound runs without fabricating bindings;
- approval-gated Code activation;
- automatic protected `SPECIFY` binding evidence before a new run reaches `PLAN`;
- immutable run targeting: later drafts or approvals cannot silently retarget an active run;
- deterministic server-owned acceptance IDs (`AC-01…`) derived from the bound Work Specification;
- protected PLAN, BUILD, TEST, VERIFY, and REVIEW coverage checks against that server-owned acceptance set;
- exact acceptance-map and binding identity in engineering-run read contracts;
- Code-mode status showing the bound Work Specification revision and acceptance count;
- equivalent reduced-graphics binding/status semantics;
- additive PostgreSQL migration for binding ID/revision/digest plus foreign key and index.

The release intentionally does **not** enable unrestricted shell execution, arbitrary Git mutation, autonomous merge, or autonomous production deployment.

## Release validation evidence

GitHub Actions run `32502425778` passed on exact candidate commit `70a5a1fbd5efb3ccd508f5d55ce9eaddd0cae3de`.

Passed gates:

- protected specification validation including `P2-V0.8.0`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- dependency-audit evidence capture;
- Playwright browser/Skia acceptance;
- explicit Code binding browser lifecycle;
- reduced-graphics Code binding parity;
- protected Engineering/Reason/Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation and protected v0.8.0 contract validation.

The first release-grade browser run correctly exposed one client-fixture inefficiency: the work-specification hook performed an unnecessary approved-spec lookup when no latest specification existed, causing the mock API to return a 404. The product hook was corrected to avoid the redundant request. The full release suite then passed.

## Database release evidence

Production Supabase migration `20260821155808_engineering_work_spec_binding` was applied before production promotion.

Verified schema state:

- `engineering_runs.work_specification_id` exists and is nullable for historical compatibility;
- `engineering_runs.work_specification_revision` exists;
- `engineering_runs.work_specification_digest` exists;
- foreign key `fk_engineering_runs_work_specification` exists with restrictive deletion behavior;
- index `ix_engineering_runs_work_specification_id` exists;
- production `/ready` returns database readiness `ok` after migration.

Supabase security advisor continues to report only informational `RLS enabled / no policy` notices on the server-owned tables. This is expected for the current architecture because direct client table access is not granted; API access remains server-owned.

## Preview evidence

Final v0.8.0 web preview for exact validated candidate `70a5a1fbd5efb3ccd508f5d55ce9eaddd0cae3de`:

- deployment `dpl_3qrbjGqxQkcMNEs9vGW19p1wXakB`;
- state `READY`;
- branch `p2/v0.8.0-spec-execution-binding`.

The API implementation preview for the same application release lineage was `READY` before the final client-only correction. Path-aware Vercel ignore logic correctly skipped the redundant API rebuild for the client-only head change.

## Production verification evidence

### Web

Vercel deployment `dpl_95ne1ov8Q9gR2UPxnLEez9Gw3kRb` is `READY` with production aliases active and no alias error.

- commit: `d9b501517b747b1c8432e14e0f8dc3d3609f1e3c`;
- `/p2-api/health`: HTTP 200;
- `/p2-api/ready`: HTTP 200 with database `ok`;
- unauthenticated `/p2-api/v1/engineering-runs/activate`: expected HTTP 401 with `WWW-Authenticate: Bearer`, proving the same-origin route reaches the protected API boundary rather than the SPA shell.

### API

Vercel deployment `dpl_7gTyHaJPWvRp6SKgMrkhzqEtDHR2` is `READY` with production aliases active and no alias error.

- commit: `d9b501517b747b1c8432e14e0f8dc3d3609f1e3c`;
- target: `production`;
- database-backed readiness succeeds;
- new engineering-run activation/binding code is deployed from the exact merge tree.

No runtime error clusters were reported for either production Vercel project during the verification window.

## Verification boundary

The release is deployed and its schema migration, application tree, Vercel deployment state, health/readiness, same-origin routing, and authentication boundary are verified.

A fresh authenticated production **capture Work Specification → approve → Code activation → bound PLAN run** round trip is **not separately claimed** because the production root access secret is deliberately unavailable to deployment tooling. That lifecycle passed protected API and browser acceptance on the exact validated release tree.

This record therefore distinguishes deployment evidence from an authenticated live feature exercise instead of overstating verification.

## Deployment state vocabulary

For v0.8.0:

- Specification approved: **YES**
- Implemented: **YES**
- Production database migration applied: **YES**
- Full release validation: **YES**
- Validated preview READY: **YES**
- Promoted to `main`: **YES**
- Production web deployment READY: **YES**
- Production API deployment READY: **YES**
- Production aliases active: **YES**
- Health/readiness verified: **YES**
- Same-origin protected activation route verified: **YES**
- Production runtime errors in verification window: **NONE FOUND**
- Fresh authenticated production spec→Code activation round trip: **NOT SEPARATELY VERIFIED**

## Next development cycle

The next visual/product cycle is **Editorial Optical**, inspired by the editorial hierarchy, asymmetrical framing, negative space, and tactile graphic character reviewed from Anna's House while preserving Parallax's Deep Violet Optical identity and conversation-first architecture.

The intended balance is approximately **80% Deep Violet precision / 20% editorial personality**. Planned visual work includes stronger display hierarchy, selective organic framing, restrained warm/sage secondary accents, softer non-HUD Skia structure, slow violet ink fields, hand-drawn contour ribbons, subtle print grain, and state-linked editorial tracing strokes.

This visual cycle must remain separate from execution authority: it may change presentation and Skia behavior, but it must not weaken the v0.8.0 approved-spec execution boundary.

## Governance status

- `CURRENT-STATE.md`: updated for the v0.8.0 validated production release, migration, deployment identities, live verification, and next visual cycle decision.
- `ARCHITECTURE.md`: must advance to v1.9 because exact Work Specification → EngineeringRun binding and server-owned acceptance authority are durable architecture changes.
- `DESIGN-SYSTEM.md`: remains v1.5 until Editorial Optical is implemented and validated; the visual direction is recorded here as the next-cycle decision, not falsely as deployed design.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
