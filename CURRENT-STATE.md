# Parallax 2.0 Current State

Release: App-builder Wave 3 production runtime + Project-create production hotfix
Date: 2026-08-23
Status: **WAVE 3 = PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; HOTFIX #125 = MERGED / CLIENT DEPLOYED / DEPLOYMENT-VERIFIED**

## Production truth

Wave 3 remains the verified production app-builder runtime through `P2-V0.16.5`. The operator-authorized Wave 3 application release was merged through release PR #122 as `cbe7a967e37b90e4254fe838aff831eafe33536b`, production migration `20260824002126 worker_recovery` is applied, and production API deployment `dpl_q56DQQZgB6CBoSp8Bh9R5hCPrphr` remains READY on that exact Wave 3 application SHA.

Production testing then exposed one client/API compatibility regression in Project creation. The Project form accepted the natural GitHub repository shorthand `owner/repository`, but the client forwarded that value unchanged while the protected API correctly requires canonical repository identity `provider:owner/repository`. This produced HTTP 422 on `POST /v1/projects` for `ryan9876/parallax`.

Issue #124 and PR #125 corrected the client boundary without weakening the backend contract:

- only two-segment GitHub shorthand `owner/repository` is normalized to `github:owner/repository` before Project creation;
- already canonical provider-qualified repository identities remain unchanged;
- backend Project/repository validation is unchanged;
- canonical `Project.id` remains the only Code-conversation Project binding authority;
- no Project, source-lineage, tool-authority, provider-target, Work Specification, evaluation or production-control invariant was broadened.

The exact hotfix head `2ce7a87fe072c191bc311d9c8b5d27fa0bc4d0d2` was 2 commits ahead / 0 behind `main` immediately before promotion. It passed:

- Parallax P2 CI `32677519666` — **SUCCESS**, including client type/state/export, browser/Skia acceptance, full API regression, protected promotion evaluation and DSPy release compilation;
- Bounded Autonomy Pilot `32677519686` — **SUCCESS**;
- Vercel Preview `dpl_4GXDCMaaK6MLE489jVcPbfP3hbzd` — **READY** on the exact hotfix head.

After explicit operator authorization, PR #125 was merged with expected-head protection. The resulting production hotfix merge is:

`c088c363f75e7b825fc417441649f9e5069606ff`

## Current production deployments

### Client

`parallax` production deployment:

- deployment `dpl_CKmaLXMvrcjBgxo2zum6mQthtDnj`;
- exact GitHub SHA `c088c363f75e7b825fc417441649f9e5069606ff`;
- GitHub commit verification — verified;
- target — production;
- state — **READY**;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app` and `parallax-git-main-lew7.vercel.app`;
- live production root fetch — **200**;
- production bundle identity changed from the prior client artifact, confirming the new client build is active.

The previous production client deployment `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka` remains a rollback candidate at Wave 2 source SHA `686d7934044e5018dc3cd324f0b61ee2b548c756`.

### API

The hotfix changed no API source path, so Vercel correctly canceled attempted API deployment `dpl_875ZhHHUTPuTyuAyFXo9rJgKQfp8` through the configured ignored-build behavior.

The active production API remains:

- deployment `dpl_q56DQQZgB6CBoSp8Bh9R5hCPrphr`;
- exact GitHub SHA `cbe7a967e37b90e4254fe838aff831eafe33536b`;
- target — production;
- state — **READY**;
- production alias `parallax-api-tan.vercel.app`.

Post-hotfix live probes confirm the unchanged API boundary remains healthy:

- `GET /health` — **200**, service `parallax-api`, status `ok`;
- `GET /ready` — **200**, database `ok`, status `ready`;
- unauthenticated `GET /v1/projects` — **401 Authentication required** with Bearer challenge.

No database migration or production credential change was required for hotfix #125.

## Wave 3 production capability

Production continues to provide:

1. durable worker lifecycle, renewable leases, canonical checkpoints, stall classification, bounded recovery/reassignment and stale-worker fail-closed behavior;
2. protected deterministic browser/accessibility/network/layout validation, provenance-bound screenshot regression and bounded secondary multimodal review;
3. bounded autonomous diagnose/correct/revalidate convergence with strict last-known-good preservation and finite retry/no-progress/oscillation/resource limits;
4. deterministic dependency/critical-path scheduling, integration backpressure, lease-bound work stealing, conservative impact-aware validation, provenance-safe reuse, bounded model routing, spec preflight and privacy-safe telemetry;
5. the permanent protected reference-app/recovery proof across Project/spec/run/source-lineage identity, BUILD/TEST/VERIFY, GitHub publication, Vercel Preview, evaluation and explicit operator REVIEW.

The protected runtime path remains:

`authenticated Project selection/binding -> approved Work Specification -> PLAN -> repository bootstrap/current durable lineage -> typed IMPLEMENT proposal -> confined safe mutation -> durable accepted source lineage -> exact-lineage BUILD/TEST/VERIFY -> deterministic browser/accessibility/console/network/layout validation -> screenshot regression -> bounded multimodal review -> bounded correction/retry with LKG + convergence limits -> bounded GitHub publication -> project-scoped Vercel Preview -> persisted provider/runtime evidence -> protected AppBuilder evaluation -> explicit operator REVIEW`

Vercel Preview remains the autonomous provider ceiling. Production promotion remains explicit operator/release authority.

## Production database

Production Supabase project `Parallax 2.0` / `kjyenifnfjqnzfgshpwg` remains healthy. Applied migrations relevant to the current runtime are:

- `20260823194237 project_runtime_binding`;
- `20260823194310 durable_source_lineage`;
- `20260824002126 worker_recovery`.

Server-owned lineage and worker-recovery tables retain RLS defense in depth with direct `anon` and `authenticated` table access revoked. FastAPI remains the application authorization boundary.

## Provider/runtime foundations

Production prerequisites remain unchanged by hotfix #125:

- private Blob store `parallax-source-lineage`;
- bounded durable source-lineage metadata in PostgreSQL;
- GitHub Vercel Connect connector `github/parallax-runtime`;
- project-scoped Vercel Preview target registration and credential isolation;
- canonical repository identity `github:Ryan9876/parallax` / GitHub repo ID `1340272514`;
- Vercel target project `prj_wLXC5JjjetJf0H97kncRlqczD3OC` / team `team_JgE8AWWz36uzRbeR6V6EWg9k`.

The temporary broad Vercel provisioning token used during Wave 2 remains revoked/inert.

## Rollback readiness

Immediate rollback targets remain available:

- client: `dpl_5trK5jmGEVeN6av8avNEv9DnS7ka` at `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- API: `dpl_h2JMsQJKSHUXazeCWGDSK9g1upKw` at `686d7934044e5018dc3cd324f0b61ee2b548c756`;
- current Wave 3 API deployment remains `dpl_q56DQQZgB6CBoSp8Bh9R5hCPrphr` at `cbe7a967e37b90e4254fe838aff831eafe33536b`.

Database rollback must remain forward-compatible and must not destructively remove applied migration history.

## Authoritative governance

- `PROJECT-CONSTITUTION.md` v1.3 — unchanged;
- `ARCHITECTURE.md` v2.6 — unchanged by hotfix #125 because the durable authority/runtime architecture did not change;
- `DESIGN-SYSTEM.md` v2.1 — unchanged;
- `CURRENT-STATE.md` — this deployment-verified Wave 3 + hotfix production snapshot;
- `PARALLEL-DEVELOPMENT.md` — concurrent-development protocol.

GitHub issues/PRs/workflows, Supabase migration/schema evidence and Vercel deployment/runtime evidence remain operational authority when chat recollection differs.

## Current decision

Wave 3 is **PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED** through `P2-V0.16.5` and Project-create hotfix #125 is **PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED**.

The exact production client now contains the repository-shorthand normalization that was missing during the first operator test. A final authenticated operator retest of the live Project-create flow is still useful product confirmation, but deployment evidence and protected automated regression evidence are complete.

The next planned product phase remains Wave 4 UX and operating efficiency on top of this verified runtime.