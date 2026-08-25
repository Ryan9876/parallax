# Parallax 2.0 Current State

Release: Wave 3 production app-builder runtime remains deployment-verified; Wave 4 Live Development release candidate is source-integrated and under final production promotion validation
Date: 2026-08-24
Status: **WAVE 3 PRODUCTION DEPLOYED / DEPLOYMENT-VERIFIED THROUGH P2-V0.16.5; WAVE 4 P2-V0.17.0–P2-V0.17.4 SOURCE-INTEGRATED ON MAIN; P2-V0.17.5 RELEASE PROOF ACTIVE; PRODUCTION RUN-EVENT MIGRATION UNAPPLIED / ACTIVATION OFF / WAVE 4 NOT YET DEPLOYMENT-VERIFIED; SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Current production truth

Current deployment-verified production remains the Wave 3 app-builder API release `dpl_963A6hsjRH8uma7uRSE8QAJap3vb` on application merge `e9a0d82c8ed9ea2e0ee18e8b24da5d6e70adb38a`, with `/health` and `/ready` passing, protected unauthenticated access returning 401, and prior post-cutover logs clean.

Wave 4 source through `P2-V0.17.4` is integrated on repository `main@22fa4f34b617bceafe5b6a0ad7cf520af2c7c403`, including the Warm Editorial shell and governed Live Build/Observability client. These source facts do not establish production migration, activation or deployment. `P2-V0.17.5` is the final integrated release-proof boundary.

## Wave 4 source integration and activation state

- #144 / `P2-V0.17.0`: experience/design contract integrated;
- #145 / `P2-V0.17.1`: durable append-only run-event projection integrated;
- #146 / `P2-V0.17.2`: resumable SSE and protected exact-lineage source/diff/evidence reads integrated;
- #147 / `P2-V0.17.3`: Warm Editorial application shell integrated;
- #148 / `P2-V0.17.4`: governed Live Build/Observability workspace integrated on `main` after exact-head protected gates;
- #149 / `P2-V0.17.5`: active final integrated reference proof and release boundary with authentic DSPy plan committed.

Production state remains explicit:

- `20260824_0010_run_events.sql` migration file integrated: **YES**;
- production `engineering_run_events` migration applied: **NO**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **NO**;
- run-event projection active in production: **NO**;
- live-observability routes active in production: **NO**;
- Wave 4 production deployment verified: **NO**.

The activation boundary governs both emission and observation. `PersistentRunEventSink` and the live-observability router activate only when server-owned `PARALLAX_RUN_EVENTS_ENABLED` equals exact value `1`; other values remain inactive. With activation enabled, production build/preflight must fail closed if `engineering_run_events` is absent.

The Live Build experience is a read-only projection over authoritative Project/run/attempt/worker/source-lineage/provider/evaluation facts. It includes durable replay, resumable SSE, exact immutable source reads/diffs, bounded BUILD/TEST/VERIFY evidence, and Code/Diff/Terminal/Tests/Events/Evidence views. It does not gain unrestricted filesystem, shell, provider, merge or production authority. REVIEW/HUMAN_REQUIRED remains explicit.

## P2-V0.17.5 release proof

The permanent #149 reference proof composes real database-backed run events, immutable source lineage, failed TEST evidence, bounded autonomous correction to a fresh child lineage, exact-lineage source/diff observation, resumed successful TEST/VERIFY, REVIEW/HUMAN_REQUIRED and explicit operator completion. Existing protected provider publication, process-recreation/replay, browser/visual and evaluation suites remain cumulative release gates.

The proof identified a real privacy defect in protected attempt-evidence observation: a secret-like `authorization=...` stdout excerpt could survive the prior generic scanner. The observer boundary was hardened to redact credential-like excerpts, bearer/private-key patterns and private-reasoning/scratchpad markers before transport; the failing case remains a permanent regression assertion.

## Release and production authority

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. It allows promotion of an already validated release without separate per-release approval while Parallax remains effectively single-user, but does not waive exact-head CI, protected evaluation, migration order, rollback, least privilege, deployment evidence or post-deploy verification, and does not authorize destructive schema/data changes.

## Production infrastructure and persistence

Production uses Vercel for API deployment and Sandbox execution, Vercel Connect/OIDC for short-lived project-scoped GitHub credentials, private Vercel Blob for immutable source objects, and hosted PostgreSQL/Supabase for authoritative relational state. Startup performs no implicit DDL; schema changes remain migration-driven.

## Authoritative record status

This file records validated production and source-integration state as of 2026-08-24. Durable architecture is in `ARCHITECTURE.md`; design rules are in `DESIGN-SYSTEM.md`; governance/authority is in `PROJECT-CONSTITUTION.md`.

Do not infer that source integration, a green Preview or an unapplied migration is deployed production capability. Only production evidence explicitly recorded as deployment-verified is authoritative.
