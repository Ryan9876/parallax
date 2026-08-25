# Parallax 2.0 Current State

Release: Wave 4 Live Development is deployed; stabilization has integrated runtime-credential recovery, Observability fidelity, and Live Build/mobile convergence, but functional production readiness remains suspended pending final visual convergence, release gates, promotion, and real post-cutover proof
Date: 2026-08-24
Status: **WAVE 4 PRODUCTION DEPLOYED / LIVE OBSERVABILITY ACTIVE; RUNTIME CREDENTIAL FIX INTEGRATED BUT NOT DEPLOYED; END-TO-END AUTONOMOUS PRODUCTION READINESS NOT YET RE-VERIFIED; OBSERVABILITY + LIVE BUILD/MOBILE FIDELITY INTEGRATED; DESKTOP/VISUAL ACCEPTANCE STABILIZATION REMAINS ACTIVE; WAVE 3 API RELEASE RETAINED AS ROLLBACK CANDIDATE; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Current production truth

Wave 4 production API is deployment `dpl_7gHytxPynJ3yoo2A51oZsyuDj8gM` from verified repository merge `main@8b5acd5c4042682d297269af0f0a5555683dac2e`. The production build completed its provider, projected-source, private Blob, lineage-composition, process-recreation/replay, rollback and run-event schema guards before publication. The decisive schema guard passed with `Wave 4 enabled; engineering_run_events present`.

Post-cutover deployment/read-boundary verification passed:

- `/health`: **200 / OK**;
- `/ready`: **200 / database ok** under the currently deployed pre-stabilization readiness contract;
- protected run-event access without authentication: **401 / Authentication required**;
- live OpenAPI exposes protected event replay, resumable SSE, exact-lineage source tree/file/diff and attempt-evidence reads;
- the immediate post-cutover production error/fatal runtime-log check was clean.

A later real authenticated production user test exposed a production-blocking runtime defect that the earlier release gates did not exercise. Two autonomous-run requests reached the production API and returned HTTP **503** with `source_bootstrap_failed stage=provider-repository error_class=ProviderActionFailed result_code=CREDENTIAL_UNAVAILABLE`. The failure occurs while obtaining the repository-scoped GitHub credential through the Vercel Connect/OIDC provider path, before substantive autonomous execution can advance. Deployment health and protected read availability remain verified, but **end-to-end autonomous production readiness is not currently verified**.

Workstream #170 has now been independently accepted and integrated into `integration/w4-stabilization` at merge `1f5b181da733c9cb440ad005dd579799e02ab421`. The accepted correction follows Vercel's documented Functions OIDC boundary: production autonomous requests use request-scoped `x-vercel-oidc-token`, inject that identity into the existing `github/parallax-runtime` Connect provider, and production `/ready` now fail-closes unless the runtime identity can perform the real Connect exchange and prove exact registered GitHub repository scope. The worker proof uses the real Project/spec/run/source-delivery/runtime composition with bounded external transports and advances from PLAN into IMPLEMENT without provider publication or mutation. **This is validated integration evidence, not production-fix evidence.** Production remains on the earlier deployment until the stabilization release is promoted and post-cutover verification proves the real runtime exchange and autonomous bootstrap.

The governed Live Build client remains the already-deployed Wave 4 production client from `main@22fa4f34b617bceafe5b6a0ad7cf520af2c7c403`, deployment `dpl_8RTZs2BJcbQUuKxurLZpGEs8zb7i`. Later Wave 4 release/activation commits did not change `apps/client`, so the Vercel client project correctly skipped those no-op redeployments. User testing also established that the deployed client is materially below the approved Warm Editorial Observatory mockup in application-shell composition and visual fidelity. This is a release-quality defect, not a change to the authoritative design direction.

The immediately preceding API deployment `dpl_2uiLj1VjJzvzZ26cAkkLzSTNxFez` from `main@e8d277de30a14b3ff1f288bcb22f651268031158` remains the rollback candidate. Its run-event activation is off by release configuration, preserving the ordered rollback boundary.

## Active Wave 4 stabilization

Control-tower issue #169 owns production recovery and visual convergence on `integration/w4-stabilization` from baseline `main@27ef2d169dc2e8d064669cdc40e2e03fc9b815aa`.

Current bounded workstream state:

- #170 / `ws/w4-runtime-credential-recovery`: **ACCEPTED + INTEGRATED** at `1f5b181da733c9cb440ad005dd579799e02ab421`; production promotion/post-cutover proof still required;
- #171 / `ws/w4-desktop-shell-convergence`: **CHANGES REQUIRED / ACTIVE** while exact-head Project-selection/browser correction is being validated;
- #172 / `ws/w4-observability-fidelity`: **ACCEPTED + INTEGRATED** at `77fc19c013dedb0d552ab495e36bc8274fc9df90`;
- #173 / `ws/w4-livebuild-mobile-convergence`: **ACCEPTED + INTEGRATED** at `d27fad3aee0557567c6fb2a19dc7fc5f357f2d63` after reconciliation onto #172 and exact-tree P2/browser/Bounded Autonomy validation;
- #174 / `ws/w4-visual-release-gates`: **ACTIVE / NOT READY**; runtime/spec/provider gate slice is green, but its material visual gate correctly found a contextual-health card clipping defect that must remain fail-closed until resolved.

Production remains deployed during stabilization, but it must not be described as ready for autonomous functional testing until the integrated #170 correction is promoted and a real protected production run proves request-scoped Connect credential acquisition, canonical repository bootstrap and advancement beyond PLAN. Final stabilization release readiness additionally requires the desktop experience to be recognizably the same product as the approved mockup family and mobile to remain intentionally composed rather than a compressed desktop layout.

## Wave 4 release state

- #144 / `P2-V0.17.0`: experience/design contract integrated;
- #145 / `P2-V0.17.1`: durable append-only run-event projection integrated;
- #146 / `P2-V0.17.2`: resumable SSE and protected exact-lineage source/diff/evidence reads integrated;
- #147 / `P2-V0.17.3`: Warm Editorial application shell integrated;
- #148 / `P2-V0.17.4`: governed Live Build/Observability workspace integrated and client deployment completed, with visual acceptance reopened by production user review;
- #149 / `P2-V0.17.5`: integrated reference proof, release gates and production activation completed, with end-to-end production readiness subsequently reopened by the credential defect;
- #166: final Wave 4 source/reference release integrated to `main`;
- #167: exact production activation configuration validated and merged.

Production activation state is explicit:

- `20260824_0010_run_events.sql` migration file integrated: **YES**;
- production migration record `20260825002736 / engineering_run_events`: **APPLIED**;
- production `engineering_run_events` table exists: **YES**;
- production table RLS enabled: **YES**;
- direct `anon` / `authenticated` read or mutation privileges: **NO**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **YES**;
- run-event projection active in production: **YES**;
- protected live-observability routes active in production: **YES**;
- Wave 4 production deployment/health/read-boundary verified: **YES**;
- #170 runtime credential correction integrated to stabilization: **YES**;
- #170 runtime credential correction deployed to production: **NO**;
- end-to-end autonomous production readiness re-verified after the correction: **NO**;
- Observability dashboard fidelity workstream #172 integrated: **YES**;
- Live Build/mobile convergence workstream #173 integrated: **YES**;
- production visual acceptance against approved mockup quality: **REOPENED — #171/#174 REMAIN ACTIVE**.

The activation boundary continues to govern both emission and observation. `PersistentRunEventSink` and the live-observability router activate only when server-owned `PARALLAX_RUN_EVENTS_ENABLED` equals exact value `1`; any other value remains inactive. Production build/preflight fails closed if the required `engineering_run_events` schema is absent.

The Live Build experience remains a read-only projection over authoritative Project/run/attempt/worker/source-lineage/provider/evaluation facts. It includes durable replay, resumable SSE, exact immutable source reads/diffs, bounded BUILD/TEST/VERIFY evidence, and Code/Diff/Terminal/Tests/Events/Evidence views. It does not gain unrestricted filesystem, shell, provider, merge or production authority. REVIEW/HUMAN_REQUIRED remains explicit.

## P2-V0.17.5 release proof and stabilization gap

The permanent #149 reference proof composes real database-backed run events, immutable source lineage, failed TEST evidence, bounded autonomous correction to a fresh child lineage, exact-lineage source/diff observation, resumed successful TEST/VERIFY, REVIEW/HUMAN_REQUIRED and explicit operator completion. Protected provider publication, process-recreation/replay, browser/visual and evaluation suites remain cumulative release gates.

The proof identified and permanently regressed a privacy defect in protected attempt-evidence observation: credential-like and private-reasoning/scratchpad excerpts are redacted at the observer boundary before transport.

The subsequent production credential failure demonstrates that the prior release proof did not exercise the live production Vercel Functions OIDC -> Connect credential exchange strongly enough. Architecture v3.0 now distinguishes build OIDC from request-scoped Functions runtime OIDC and requires production readiness to exercise the runtime Connect exchange. Stabilization #174 must preserve this requirement in the final release proof; it must not be replaced by a static credential or build-only preflight.

## Release and production authority

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. It permits promotion of an already validated release without separate per-release approval while Parallax remains effectively single-user, but does not waive exact-head CI, protected evaluation, migration order, rollback, least privilege, deployment evidence or post-deploy verification, and does not authorize destructive schema/data changes.

## Production infrastructure and persistence

Production uses Vercel for API/client deployment and Sandbox execution, Vercel Connect/OIDC for short-lived project-scoped GitHub credentials, private Vercel Blob for immutable source objects, and hosted PostgreSQL/Supabase for authoritative relational state. Startup performs no implicit DDL; schema changes remain migration-driven.

The currently deployed production defect is in the Vercel Connect/OIDC -> GitHub credential acquisition path. The accepted stabilization correction is integrated but not deployed. The architecture remains fail-closed: no broad PAT/static-token fallback is authorized merely to restore execution.

## Authoritative record status

This file records validated production state and the current stabilization-integration decisions as of 2026-08-24. Durable architecture is in `ARCHITECTURE.md` v3.0; design rules are in `DESIGN-SYSTEM.md`; governance/authority is in `PROJECT-CONSTITUTION.md`.

Production capability claims require deployment evidence plus a real functional proof for the claimed path. Source integration, a green Preview, health endpoints or route availability alone are not sufficient to claim end-to-end autonomous readiness.
