# Parallax 2.0 Current State

Release: Wave 4 Live Development is production-deployed and deployment-verified through `P2-V0.17.5`
Date: 2026-08-24
Status: **WAVE 4 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.17.5; PRODUCTION RUN-EVENT MIGRATION APPLIED; EXACT ACTIVATION ON; PROTECTED LIVE OBSERVABILITY ACTIVE; WAVE 3 API RELEASE RETAINED AS ROLLBACK CANDIDATE; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Current production truth

Wave 4 production API is deployment `dpl_7gHytxPynJ3yoo2A51oZsyuDj8gM` from verified repository merge `main@8b5acd5c4042682d297269af0f0a5555683dac2e`. The production build completed its provider, projected-source, private Blob, lineage-composition, process-recreation/replay, rollback and run-event schema guards before publication. The decisive schema guard passed with `Wave 4 enabled; engineering_run_events present`.

Post-cutover production verification passed:

- `/health`: **200 / OK**;
- `/ready`: **200 / database ok**;
- protected run-event access without authentication: **401 / Authentication required**;
- live OpenAPI exposes protected event replay, resumable SSE, exact-lineage source tree/file/diff and attempt-evidence reads;
- production error/fatal runtime-log check after cutover: **clean**.

The governed Live Build client remains the already-verified Wave 4 production client from `main@22fa4f34b617bceafe5b6a0ad7cf520af2c7c403`, deployment `dpl_8RTZs2BJcbQUuKxurLZpGEs8zb7i`. Later Wave 4 release/activation commits did not change `apps/client`, so the Vercel client project correctly skipped those no-op redeployments.

The immediately preceding API deployment `dpl_2uiLj1VjJzvzZ26cAkkLzSTNxFez` from `main@e8d277de30a14b3ff1f288bcb22f651268031158` remains the rollback candidate. Its run-event activation is off by release configuration, preserving the ordered rollback boundary.

## Wave 4 release state

- #144 / `P2-V0.17.0`: experience/design contract integrated;
- #145 / `P2-V0.17.1`: durable append-only run-event projection integrated;
- #146 / `P2-V0.17.2`: resumable SSE and protected exact-lineage source/diff/evidence reads integrated;
- #147 / `P2-V0.17.3`: Warm Editorial application shell integrated;
- #148 / `P2-V0.17.4`: governed Live Build/Observability workspace integrated and client-deployment verified;
- #149 / `P2-V0.17.5`: integrated reference proof, release gates and production activation completed;
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
- Wave 4 production deployment verified: **YES**.

The activation boundary continues to govern both emission and observation. `PersistentRunEventSink` and the live-observability router activate only when server-owned `PARALLAX_RUN_EVENTS_ENABLED` equals exact value `1`; any other value remains inactive. Production build/preflight fails closed if the required `engineering_run_events` schema is absent.

The Live Build experience remains a read-only projection over authoritative Project/run/attempt/worker/source-lineage/provider/evaluation facts. It includes durable replay, resumable SSE, exact immutable source reads/diffs, bounded BUILD/TEST/VERIFY evidence, and Code/Diff/Terminal/Tests/Events/Evidence views. It does not gain unrestricted filesystem, shell, provider, merge or production authority. REVIEW/HUMAN_REQUIRED remains explicit.

## P2-V0.17.5 release proof

The permanent #149 reference proof composes real database-backed run events, immutable source lineage, failed TEST evidence, bounded autonomous correction to a fresh child lineage, exact-lineage source/diff observation, resumed successful TEST/VERIFY, REVIEW/HUMAN_REQUIRED and explicit operator completion. Protected provider publication, process-recreation/replay, browser/visual and evaluation suites remain cumulative release gates.

The proof identified and permanently regressed a privacy defect in protected attempt-evidence observation: credential-like and private-reasoning/scratchpad excerpts are redacted at the observer boundary before transport.

## Release and production authority

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. It permits promotion of an already validated release without separate per-release approval while Parallax remains effectively single-user, but does not waive exact-head CI, protected evaluation, migration order, rollback, least privilege, deployment evidence or post-deploy verification, and does not authorize destructive schema/data changes.

## Production infrastructure and persistence

Production uses Vercel for API/client deployment and Sandbox execution, Vercel Connect/OIDC for short-lived project-scoped GitHub credentials, private Vercel Blob for immutable source objects, and hosted PostgreSQL/Supabase for authoritative relational state. Startup performs no implicit DDL; schema changes remain migration-driven.

## Authoritative record status

This file records validated production state as of 2026-08-24. Durable architecture is in `ARCHITECTURE.md`; design rules are in `DESIGN-SYSTEM.md`; governance/authority is in `PROJECT-CONSTITUTION.md`.

Production capability claims require deployment evidence. Source integration or a green Preview alone is not sufficient.