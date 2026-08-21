# Parallax 2.0 Current State

Version: 0.7.0
Date: 2026-08-21
Status: DEPLOYED — INFRASTRUCTURE/BOUNDARY VERIFIED; AUTHENTICATED WORK-SPEC ROUND TRIP NOT SEPARATELY VERIFIED
Production branch: `main`
Production application release commit: `c17c1abb021697fc4c17cbdfa205a1c6fa9559cc`
Validated release-tree commit: `8cbf00dad88bf674e670a4fcb96aecfbf1813df6`
Production web deployment: `dpl_9oecwVsR6dBDVHsnvoi3XtEtG2Mo`
Production API deployment: `dpl_J3Q9YMhE2wu23CKtg4qY71rJiApb`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`
Applied work-spec migration: `20260821131833_work_specifications`

## Current release

Parallax 2.0 v0.7.0 is deployed through the GitHub → Vercel production pipeline.

PR #10 promoted the approved `P2-V0.7.0` Durable Work Specifications release. The exact validated release tree is `8cbf00dad88bf674e670a4fcb96aecfbf1813df6`; the resulting production merge commit is `c17c1abb021697fc4c17cbdfa205a1c6fa9559cc`.

Git comparison between the validated release tree and the production merge reports **zero changed files**, so the deployed application tree is the validated release tree plus merge metadata.

## v0.7.0 product change — Durable Work Specifications

The first user-work specification layer is now part of Parallax while preserving `Conversation.spec_id` as the separate durable product/policy specification identity.

The release adds:

- durable `WorkSpecification` entities linked to conversations;
- immutable integer revisions with `DRAFT`, `APPROVED`, and `SUPERSEDED` lifecycle states;
- typed DSPy-assisted drafting through the existing Luna → Terra → Sol model order;
- protected structural validation before persistence;
- no persistence when all drafting candidates fail or fail validation;
- explicit operator approval; model output cannot self-approve;
- approval supersession rules that preserve the prior approved revision until a newer draft is explicitly approved;
- protected latest/draft/approve API routes;
- a compact expandable work-specification surface in the primary conversation UI;
- equivalent reduced-graphics work-specification interaction;
- additive PostgreSQL schema migration with RLS and revoked direct client-role table privileges.

The release intentionally does **not** bind Code engineering runs to user work-specification IDs and does not enable a live unrestricted executor.

## Release validation evidence

GitHub Actions run `32493235669` passed on the exact validated release-tree commit `8cbf00dad88bf674e670a4fcb96aecfbf1813df6`.

Passed gates:

- protected specification validation;
- Python compilation and API test suite;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser/Skia acceptance suite;
- mobile, tablet, and desktop acceptance coverage;
- reduced-graphics functional coverage;
- work-specification capture → expand → explicit approve browser lifecycle;
- protected Engineering/Reason/Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation and protected v0.7.0 contract validation.

The initial browser gate exposed a test-fixture defect because the mock API did not implement the new work-specification routes. The mock was corrected to exercise the real new contract; the complete browser acceptance suite then passed.

## Database release evidence

The additive `work_specifications` migration was applied to the dedicated production Supabase project before promotion.

Supabase reports migration `20260821131833` named `work_specifications` in the production migration history.

Post-migration verification confirmed:

- row-level security enabled on `work_specifications`;
- direct `anon` SELECT privilege absent;
- direct `authenticated` SELECT privilege absent;
- unique conversation/revision constraint present.

Production `/ready` succeeds after the migration, proving the deployed API can reach the production database.

## Preview evidence

The final validated client release-tree commit produced a READY Vercel preview:

- web deployment: `dpl_HD1j4WqrhJujrxZPj7GpN7mE7wsm`;
- branch: `p2/v0.7.0-work-specifications`;
- commit: `8cbf00dad88bf674e670a4fcb96aecfbf1813df6`.

The implementation API preview was also READY before promotion. Later branch commits changed only protected specification/test evidence, so redundant API preview builds were path-aware skipped/cancelled while the exact API code remained covered by the passing release suite and was rebuilt from the exact merge commit for production.

## Production verification evidence

### Web

Vercel production deployment `dpl_9oecwVsR6dBDVHsnvoi3XtEtG2Mo` is `READY` with no alias error.

- target: `production`;
- Git commit: `c17c1abb021697fc4c17cbdfa205a1c6fa9559cc`;
- production alias: `https://parallax-ashy-one-20.vercel.app`;
- production root returns HTTP 200 and serves the Parallax 2.0 Expo application;
- same-origin `/p2-api/health` returns HTTP 200 with Parallax API health JSON;
- a same-origin unauthenticated work-specification request reaches the API and returns the expected sanitized HTTP 401 with `WWW-Authenticate: Bearer` rather than falling through to the SPA shell.

### API

Vercel production deployment `dpl_J3Q9YMhE2wu23CKtg4qY71rJiApb` is `READY` with no alias error.

- target: `production`;
- Git commit: `c17c1abb021697fc4c17cbdfa205a1c6fa9559cc`;
- production alias: `https://parallax-api-tan.vercel.app`;
- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database dependency `ok`;
- `/openapi.json`: HTTP 200 and exposes the protected work-specification latest, draft, and approve routes;
- OpenAPI retains the HTTP Bearer security scheme on the new routes;
- unauthenticated work-specification access returns the existing sanitized 401 contract.

No Vercel runtime error clusters were reported for either authoritative production project during the deployment verification window.

## Verification boundary

The release is **deployed** and its production infrastructure, database migration, route exposure, same-origin proxy, and authentication boundary are verified.

A fresh authenticated production work-specification **draft → approve** round trip is **not separately claimed** because the production access secret is not exposed to deployment tooling. The exact behavior passed API tests and browser acceptance on the validated release tree, but the project constitution requires evidence-based status language; therefore this record does not label v0.7.0 fully deployment-verified yet.

The next time an authorized browser session performs `CAPTURE SPEC` and `APPROVE` successfully against production, that evidence is sufficient to close this final release-verification gap if no contradictory production evidence appears.

## Deployment state vocabulary

For v0.7.0:

- Specification approved: **YES**
- Generated/implemented: **YES**
- Production database migration applied: **YES**
- Full release validation: **YES**
- Validated client preview READY: **YES**
- Promoted to `main`: **YES**
- Production web deployment READY: **YES**
- Production API deployment READY: **YES**
- Production aliases active: **YES**
- API health verified: **YES**
- Database readiness verified: **YES**
- Work-spec routes present in production OpenAPI: **YES**
- Work-spec routes protected by production auth boundary: **YES**
- Same-origin web → API route verified: **YES**
- Production runtime-error check: **NO ERRORS FOUND IN VERIFICATION WINDOW**
- Fresh authenticated production draft → approve round trip: **NOT SEPARATELY VERIFIED**
- Fully deployment-verified: **NO — one explicit authenticated feature round trip remains unclaimed**

## Governance status

- `CURRENT-STATE.md`: updated for the v0.7.0 validated production deployment, database migration, deployment identities, live evidence, and the explicit remaining verification boundary.
- `ARCHITECTURE.md`: updated to v1.8 because durable user work specifications, their revision/approval lifecycle, persistence contract, API boundary, and model/human authority split are new durable architecture.
- `DESIGN-SYSTEM.md`: unchanged; v0.7.0 adds a component within the existing Deep Violet Optical system but does not change durable visual-language rules.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical v0.1–v0.6.3 release evidence remains preserved in repository history.