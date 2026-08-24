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

## Resolved production bootstrap regression — #140 / #142

Issues #140 and #142 are closed completed.

The production regression originally manifested as 503 responses from `Run autonomously` while affected Engineering Runs remained safely at PLAN revision 1. Investigation proved the failure happened before autonomous worker execution, inside repository/provider/durable source bootstrap.

The repair was delivered incrementally without weakening canonical Project identity, source-lineage integrity, provider scope, protected evaluation, rollback, sandbox authority or production controls:

1. production provider, GitHub installation/repository/branch and private Blob preflights established the external provider boundary;
2. production projected per-file GitHub reads exercised the same lineage-safe path, UTF-8, NUL, size and digest rules as runtime;
3. Vercel Python SDK execution was moved into an isolated `uv run` environment rather than modifying the externally managed Python installation;
4. the private Blob adapter now normalizes transient HTTPX transport failures, retries within a hard bounded attempt count, reconciles uncertain immutable writes by content-address read-back and reuses only request-local bytes already verified against SHA-256;
5. bootstrap failures now record bounded stage / error-class / safe-result-code evidence without raw provider messages, source bytes, tokens or database details;
6. rollback-only production canaries prove full durable lineage composition and the exact projected `production_source_delivery()` bootstrap stack;
7. the final canary enters `EngineeringRuntimeComposition.run()` itself, recreates runtime composition and replays the existing durable root lineage while deliberately stopping at the protected executor-probe boundary before any PLAN completion, IMPLEMENT mutation, BUILD/TEST/VERIFY execution, GitHub mutation/publication, Preview publication or REVIEW delivery.

Final production build evidence on `dpl_963A6hsjRH8uma7uRSE8QAJap3vb`:

- provider/repository/private Blob preflight: **PASS** — 403 tracked source-tree entries;
- lineage-safe projected source: **PASS** — 363 files / 2,912,710 UTF-8 bytes;
- Blob SDK immutable get/put/get: **PASS**;
- full durable lineage composition: **PASS** — 363 files, metadata rollback verified;
- projected bootstrap through `EngineeringRuntimeComposition.run()`: **PASS** — 363 files with `engineering_runtime_verified`, `process_recreation_verified`, `replay_verified`, `no_stage_mutation_verified`, metadata rollback verified and synthetic Project rollback verified.

The owner Project/run was not used as a repeated manual test harness. The regression was isolated and verified through production-safe synthetic identities and rollback-only canaries.

## Wave 4 source integration and activation state

Wave 4 experience/design, durable run-event telemetry, resumable transport/protected reads, Warm Editorial shell and Live Build/Observability workspace (`P2-V0.17.0` through `P2-V0.17.4`, issues #144–#148) are **source integrated but not yet production migration/activation/deployment verified**. `P2-V0.17.5` / #149 is the active integrated reference-proof and release boundary.

Current state distinction:

- Wave 4 run-event source integrated: **YES**;
- Wave 4 live transport/protected read source integrated: **YES**, merge `ee5b55ebcf3a6da14dfb2233cb69ed9dedee774f` from validated #146 / PR #158;
- `20260824_0010_run_events.sql` migration file integrated: **YES**;
- production `engineering_run_events` migration applied: **NO**;
- `PARALLAX_RUN_EVENTS_ENABLED=1` production activation: **NO**;
- Wave 4 run-event projection active in production: **NO**;
- Wave 4 live-observability routes active in production: **NO**;
- Wave 4 client Live Build UI source integrated on `main`: **YES**; production deployment verified: **NO**.

The production activation boundary now governs both emission and observation. The Engineering Run route attaches `PersistentRunEventSink` only when the server-owned environment value `PARALLAX_RUN_EVENTS_ENABLED` equals exactly `1`, and the live-observability router is registered only under that same exact activation value. Values such as `true`, `yes` or an absent flag do not activate Wave 4.

The production build guard behaves as follows:

- if the flag is not exactly `1`, Wave 4 telemetry and live reads remain disabled and the build records that the migration is unapplied/not activated;
- if the flag is `1`, the build requires the `engineering_run_events` table to exist and blocks cutover if it is absent.

This activation boundary allows source-integrated Wave 4 code to coexist with the verified Wave 3 runtime without turning an unapplied observation schema into a runtime dependency or silently deploying Wave 4 capability.

The integrated #146 source provides, when later activated under the governed migration/flag process, owner-scoped paginated run-event replay, resumable authenticated SSE with durable sequence IDs, exact immutable source tree/file/diff reads, bounded allowlisted BUILD/TEST/VERIFY evidence reads, and client cursor/de-duplication helpers. Those capabilities are not production-active merely because their source is now present on `main`.

## Deployed Wave 3 capability

Production retains the complete protected app-builder route:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> deterministic browser/accessibility/console/network/layout validation -> screenshot regression -> bounded multimodal review -> bounded correction/retry with last-known-good + convergence limits -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> protected AppBuilder evaluation -> explicit operator REVIEW`

Durable worker recovery, stale-worker rejection, process-recreation safety, replay-safe mutation/publication, immutable content addressing, transactional current-lineage CAS, last-known-good preservation, deterministic browser precedence, bounded correction/convergence, protected evaluation and project-scoped tool/provider authority remain in force.

Preview remains the ordinary autonomous provider ceiling. Production deployment of Parallax itself remains governed by the release process and standing single-user authorization; Parallax-developed Projects do not inherit unrestricted production deployment authority.

## Release and production authority

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active.

It authorizes promotion of an already validated Parallax release/hotfix without a separate per-release approval while Parallax remains effectively single-user. It does not waive exact-head CI, protected evaluation, provider/security boundaries, rollback requirements, deployment evidence or post-deploy verification, and it does not pre-authorize destructive database changes, data loss or materially broader provider/credential authority.

PR #160 was promoted under that standing authority only after:

- exact-head Parallax P2 CI succeeded;
- exact-head Bounded Autonomy Pilot succeeded;
- browser/Skia acceptance succeeded;
- protected promotion evaluation including negative regression cases succeeded;
- DSPy release compilation succeeded;
- exact-head Vercel Preview was READY;
- `main` remained reconciled immediately before merge;
- Wave 4 was made explicitly inactive rather than applying its migration as part of the Wave 3 hotfix.

## Production infrastructure and persistence

Production uses:

- Vercel for API deployment and Vercel Sandbox execution;
- Vercel Connect / OIDC for short-lived project-scoped GitHub credentials;
- private Vercel Blob for immutable content-addressed source objects;
- hosted PostgreSQL / Supabase for conversations, Work Specifications, Engineering Runs/attempts, Projects, authorized users, durable worker execution and source-lineage metadata/current heads.

Production startup performs no implicit DDL. Schema changes remain migration-driven.

Wave 4's `engineering_run_events` table is intentionally not part of the active production schema yet.

## Active Wave 4 release work

Wave 4 implementation workstreams #144–#148 are integrated. Current release facts:

- #144 / `P2-V0.17.0`: experience/design contract integrated;
- #145 / `P2-V0.17.1`: durable run-event projection integrated, production activation still off;
- #146 / `P2-V0.17.2`: resumable SSE and protected source/diff/evidence reads integrated;
- #147 / `P2-V0.17.3`: Warm Editorial application shell integrated;
- #148 / `P2-V0.17.4`: governed Live Build/Observability workspace integrated on `main` at `22fa4f34b617bceafe5b6a0ad7cf520af2c7c403` after exact-head protected gates;
- #149 / `P2-V0.17.5`: active final integrated reference proof and release boundary; authentic DSPy plan is committed and the permanent reference proof now exercises durable failed TEST evidence, bounded autonomous correction to a fresh immutable lineage, exact-lineage observation/diff, REVIEW/HUMAN_REQUIRED and explicit operator completion;
- the #149 reference proof identified and fixed an observability privacy gap so secret/private-reasoning-like command excerpts are redacted at the protected read boundary;
- production `engineering_run_events` migration applied: **NO**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **NO**;
- Wave 4 production deployment verified: **NO**.

The final release candidate must still pass the full exact-head release-mode P2 CI, browser/Skia, protected promotion evaluation, DSPy, Bounded Autonomy and migration-readiness gates before any production migration or activation occurs.

## Closed production repair chain

The production repair chain now includes the earlier Project/repository/provider corrections plus the final bootstrap hardening releases. The important terminal facts are:

- provider identity and encoded Vercel Connect wire contract are production-verified;
- private Blob SDK and immutable source storage are production-verified;
- projected GitHub source is production-verified;
- PostgreSQL lineage metadata/CAS and rollback behavior are production-verified;
- exact `production_source_delivery()` bootstrap is production-verified;
- `EngineeringRuntimeComposition.run()` bootstrap + process recreation/replay is production-verified without user clicks;
- the current API deployment is READY and post-deploy smoke/auth/runtime checks pass.

## Authoritative record status

This file records validated production and source-integration state as of 2026-08-24.

Durable architecture is defined in `ARCHITECTURE.md`; design rules remain in `DESIGN-SYSTEM.md`; governance/authority remains in `PROJECT-CONSTITUTION.md`.

Do not infer that source integration, a green Preview or an unapplied migration is deployed production capability. Only the production evidence recorded above is deployment-verified.