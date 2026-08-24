# Parallax 2.0 Current State

Release: Wave 3 production app-builder runtime remains deployment-verified; Wave 4 Live Development release candidate is source-integrated and under final production promotion validation
Date: 2026-08-24
Status: **WAVE 3 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; WAVE 4 P2-V0.17.0–P2-V0.17.4 SOURCE-INTEGRATED ON MAIN; P2-V0.17.5 RELEASE PROOF ACTIVE; PRODUCTION RUN-EVENT MIGRATION UNAPPLIED / ACTIVATION OFF / WAVE 4 NOT YET DEPLOYMENT-VERIFIED; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Current production truth

The authoritative repository `main` application head for the current verified API release is:

- `e9a0d82c8ed9ea2e0ee18e8b24da5d6e70adb38a` — merge of PR #160, `[Hotfix] Verify bootstrap through EngineeringRuntimeComposition`.

The current verified production API deployment is:

- `dpl_963A6hsjRH8uma7uRSE8QAJap3vb` — **READY** on exact application merge `e9a0d82c8ed9ea2e0ee18e8b24da5d6e70adb38a`;
- production alias `parallax-api-tan.vercel.app` points to this release;
- `/health` returns 200 with `status=ok`;
- `/ready` returns 200 with `status=ready` and `database=ok`;
- unauthenticated `/v1/projects` returns 401 with the Bearer challenge;
- deployment-scoped error/fatal runtime logs are empty after cutover;
- deployment-scoped `source_bootstrap_failed` logs are empty after cutover.

The Wave 3 protected app-builder runtime remains the deployment-verified production execution architecture through `P2-V0.16.5`. Wave 4 source through `P2-V0.17.4` is integrated on repository `main@22fa4f34b617bceafe5b6a0ad7cf520af2c7c403`, including the Warm Editorial shell and governed Live Build/Observability client, but those facts do not by themselves establish production activation or deployment. `P2-V0.17.5` is the final integrated release-proof boundary.

## Wave 4 source integration and activation state

Wave 4 experience/design, durable run-event telemetry, resumable transport/protected reads, Warm Editorial shell and Live Build/Observability workspace (`P2-V0.17.0` through `P2-V0.17.4`, issues #144–#148) are **source integrated but not yet production migration/activation/deployment verified**. `P2-V0.17.5` / #149 is the active integrated reference-proof and release boundary.

Current state distinction:

- Wave 4 run-event source integrated: **YES**;
- Wave 4 live transport/protected read source integrated: **YES**;
- Warm Editorial shell source integrated: **YES**;
- Live Build/Observability workspace source integrated: **YES**, `main@22fa4f34b617bceafe5b6a0ad7cf520af2c7c403`;
- `20260824_0010_run_events.sql` migration file integrated: **YES**;
- production `engineering_run_events` migration applied: **NO**;
- `PARALLAX_RUN_EVENTS_ENABLED=1` production activation: **NO**;
- Wave 4 run-event projection active in production: **NO**;
- Wave 4 live-observability routes active in production: **NO**;
- Wave 4 production deployment verified: **NO**.

The activation boundary governs both event emission and observation. `PersistentRunEventSink` and the live-observability router activate only when the server-owned value `PARALLAX_RUN_EVENTS_ENABLED` equals exactly `1`; values such as `true`, `yes` or an absent flag remain inactive. If the flag is `1`, production build/preflight requires the `engineering_run_events` table to exist before cutover.

The source-integrated Live Build experience is a read-only projection over authoritative Project/run/attempt/worker/source-lineage/provider/evaluation facts. It includes durable event replay, resumable SSE, exact immutable source tree/file/diff reads, bounded allowlisted BUILD/TEST/VERIFY evidence, Code/Diff/Terminal/Tests/Events/Evidence views, and explicit REVIEW/HUMAN_REQUIRED presentation. It does not gain unrestricted filesystem, shell, provider, merge or production authority.

## Deployed Wave 3 capability

Production retains the complete protected app-builder route:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> deterministic browser/accessibility/console/network/layout validation -> screenshot regression -> bounded multimodal review -> bounded correction/retry with last-known-good + convergence limits -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> protected AppBuilder evaluation -> explicit operator REVIEW`

Durable worker recovery, stale-worker rejection, process-recreation safety, replay-safe mutation/publication, immutable content addressing, transactional current-lineage CAS, last-known-good preservation, deterministic browser precedence, bounded correction/convergence, protected evaluation and project-scoped tool/provider authority remain in force.

Preview remains the ordinary autonomous provider ceiling. Production deployment of Parallax itself remains governed by the release process and standing single-user authorization; Parallax-developed Projects do not inherit unrestricted production deployment authority.

## Release and production authority

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. It authorizes promotion of an already validated Parallax release/hotfix without a separate per-release approval while Parallax remains effectively single-user. It does not waive exact-head CI, protected evaluation, provider/security boundaries, rollback requirements, deployment evidence or post-deploy verification, and it does not pre-authorize destructive database changes, data loss or materially broader provider/credential authority.

## Production infrastructure and persistence

Production uses Vercel for API deployment and Sandbox execution, Vercel Connect/OIDC for short-lived project-scoped GitHub credentials, private Vercel Blob for immutable content-addressed source objects, and hosted PostgreSQL/Supabase for authoritative relational state. Production startup performs no implicit DDL; schema changes remain migration-driven. Wave 4's `engineering_run_events` table is not yet recorded here as active production schema.

## Active Wave 4 release work

Wave 4 implementation workstreams #144–#148 are integrated. Current release facts:

- #144 / `P2-V0.17.0`: experience/design contract integrated;
- #145 / `P2-V0.17.1`: durable run-event projection integrated, production activation still off;
- #146 / `P2-V0.17.2`: resumable SSE and protected source/diff/evidence reads integrated;
- #147 / `P2-V0.17.3`: Warm Editorial application shell integrated;
- #148 / `P2-V0.17.4`: governed Live Build/Observability workspace integrated on `main` after exact-head protected gates;
- #149 / `P2-V0.17.5`: active final integrated reference proof and release boundary; authentic DSPy plan is committed and the permanent reference proof exercises durable failed TEST evidence, bounded autonomous correction to a fresh immutable lineage, exact-lineage observation/diff, REVIEW/HUMAN_REQUIRED and explicit operator completion;
- the #149 reference proof identified and fixed an observability privacy gap so secret/private-reasoning-like command excerpts are redacted at the protected read boundary;
- production `engineering_run_events` migration applied: **NO**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **NO**;
- Wave 4 production deployment verified: **NO**.

The release candidate must pass the full exact-head release-mode P2 CI, browser/Skia, protected promotion evaluation, DSPy, Bounded Autonomy and migration-readiness gates before any production migration or activation occurs.

## Authoritative record status

This file records validated production and source-integration state as of 2026-08-24. Durable architecture is defined in `ARCHITECTURE.md`; design rules remain in `DESIGN-SYSTEM.md`; governance/authority remains in `PROJECT-CONSTITUTION.md`.

Do not infer that source integration, a green Preview or an unapplied migration is deployed production capability. Only production evidence explicitly recorded as deployment-verified is authoritative.
