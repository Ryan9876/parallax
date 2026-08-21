# Parallax 2.0 Current State

Version: 0.10.0
Date: 2026-08-21
Status: DEPLOYED — INFRASTRUCTURE / AUTHORIZATION BOUNDARY VERIFIED; FIRST INTERACTIVE GOOGLE LOGIN NOT YET VERIFIED
Production branch: `main`
Production application release commit: `e2f266daea0a2caf060a8c061274cb7a3f7ced02`
Validated release-tree commit: `3927b3137a251f5dadbae29802b1ba7071c37bd0`
Production web deployment: `dpl_9RiVciErH3hCbejrqVUQ6cVxF1Aj`
Production API deployment: `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`
Production authorized-users migration: `20260821212154_authorized_users`

## Current deployed release

Parallax 2.0 v0.10.0 — **Google Identity & Access Control** — is deployed through the GitHub → Vercel production pipeline.

PR #14 promoted approved spec `P2-V0.10.0`. The exact validated release tree is `3927b3137a251f5dadbae29802b1ba7071c37bd0`; the production application merge commit is `e2f266daea0a2caf060a8c061274cb7a3f7ced02`.

Git comparison between the validated release tree and production application merge reports **zero changed files**. The deployed application tree is therefore the exact validated tree plus merge metadata.

## v0.10.0 outcome

The normal hosted-web sign-in path no longer asks the operator for a shared Parallax production credential.

v0.10.0 adds:

- Google OAuth through the dedicated Parallax Supabase Auth project;
- explicit browser-owned PKCE initiation and callback exchange;
- one-time handoff of the transient Supabase access token to the Parallax API;
- Parallax-owned signed `HttpOnly` session establishment after server-side identity verification;
- durable server-owned `authorized_users` application authorization;
- `owner` / `member` roles and `active` / `revoked` access state;
- owner-only access-management routes and the Editorial Optical access panel;
- root bearer compatibility only for break-glass / explicit automation use;
- no normal hosted-browser persistence of the production root access secret or transient Supabase access token.

## Identity and authorization boundary

Google/Supabase proves identity. Parallax decides authorization.

The production `authorized_users` table is the authoritative application allowlist. The initial owner record has been seeded directly in production as `owner`, `active`, and intentionally remains unbound to a Google auth user ID until the first successful interactive Google sign-in.

The user's email address is deliberately not recorded in this public project-state file.

On first successful Google login, the API binds the seeded allowlist record to the verified provider auth user ID. Subsequent protected requests require the active server-owned row and matching signed-session role. Revocation therefore takes effect even against an otherwise structurally valid older session cookie.

## Database migration evidence

Repository migration: `services/api/migrations/20260821_0005_authorized_users.sql`.

Production Supabase migration history records:

- `20260820165817_initial_parallax_p2_production`;
- `20260820165849_enable_rls_and_revoke_api_roles`;
- `20260821131833_work_specifications`;
- `20260821155808_engineering_work_spec_binding`;
- `20260821212154_authorized_users`.

Verified production properties for `authorized_users`:

- RLS enabled;
- direct `anon` SELECT privilege absent;
- direct `authenticated` SELECT privilege absent;
- normalized email uniqueness enforced;
- bound auth user ID uniqueness enforced.

The Supabase security advisor reports the expected informational `rls_enabled_no_policy` notice because direct client access is intentionally disabled and FastAPI is the application data boundary. No client RLS policy is required for this architecture.

## Release validation evidence

GitHub Actions run `32527836227` completed successfully for exact candidate commit `3927b3137a251f5dadbae29802b1ba7071c37bd0`.

Passed gates:

- protected specification validation through `P2-V0.10.0`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser / Skia acceptance;
- approved Work Specification → Code binding browser acceptance;
- hosted Google PKCE browser acceptance under mocked provider boundaries;
- transient provider-token handoff and Parallax session establishment acceptance;
- owner access-panel and logout acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation;
- protected v0.10.0 compiled-plan contract verification.

The final frontend preview for exact release head was `READY` before promotion.

## Production verification evidence

### Web

Vercel deployment `dpl_9RiVciErH3hCbejrqVUQ6cVxF1Aj` is `READY`, targets production, and reports Git commit `e2f266daea0a2caf060a8c061274cb7a3f7ced02`.

Production aliases include:

- `https://parallax-ashy-one-20.vercel.app`;
- `https://parallax-lew7.vercel.app`;
- `https://parallax-git-main-lew7.vercel.app`.

Verified live behavior:

- production web root: HTTP 200 and serves the v0.10 Expo bundle;
- `/p2-api/health`: HTTP 200 with Parallax API health JSON;
- `/p2-api/ready`: HTTP 200 with database readiness `ok`;
- unauthenticated `/p2-api/v1/session`: expected HTTP 401 with `WWW-Authenticate: Bearer`;
- no frontend runtime-error clusters found in the verification window.

### API

Vercel deployment `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw` is `READY`, targets production, and reports the same production application commit.

Verified live behavior:

- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database readiness `ok`;
- `/openapi.json`: HTTP 200 and API version `0.10.0`;
- deployed OpenAPI contains `POST /v1/session/google`;
- deployed OpenAPI contains `GET /v1/access/me`;
- deployed OpenAPI contains owner access-management routes under `/v1/access/users`;
- protected existing Conversation, Work Specification, and Engineering Run routes remain present;
- no API runtime-error clusters found in the verification window.

## Verification boundary

The v0.10 application tree, production web and API deployments, schema migration, seeded owner authorization row, same-origin gateway, API health/readiness, unauthenticated protection boundary, deployed access-management route contract, and runtime-error state are verified.

A real interactive production Google OAuth round trip is **not yet separately claimed** because deployment tooling cannot impersonate or authenticate as the operator's Google account. The seeded owner row remains intentionally unbound until that first successful sign-in.

The release becomes fully identity-path deployment-verified when an authorized operator completes Google sign-in on the production web alias and reaches the Parallax workspace. That successful login will bind the owner allowlist record to the verified Google/Supabase auth identity; production evidence can then close the remaining verification gap.

## Deployment state vocabulary

For v0.10.0:

- Specification approved: **YES**
- Implemented: **YES**
- Full release validation: **YES**
- Browser / Skia acceptance: **YES**
- Google PKCE browser acceptance: **YES — mocked provider boundary**
- Protected Engineering / Reason / Code evaluation: **YES**
- DSPy release compilation: **YES**
- Production database migration applied: **YES**
- Initial owner authorization seeded: **YES**
- Validated tree equals production application tree: **YES**
- Production web deployment READY: **YES**
- Production API deployment READY: **YES**
- Production aliases active: **YES**
- Hosted same-origin health/readiness: **YES**
- Protected unauthenticated boundary: **YES**
- Deployed v0.10 identity/access API contract: **YES**
- Production runtime errors in verification window: **NONE FOUND**
- First real Google login / owner identity binding: **NOT YET VERIFIED**
- Fully identity-path deployment-verified: **NO — one operator Google login remains**

## Current product baseline

Parallax now combines:

1. **Conversation-first Reason** with protected streaming behavior and durable state.
2. **Durable Work Specifications** with revision history and explicit operator approval.
3. **Approved-Spec Code execution binding** with immutable run/spec identity and server-owned acceptance authority.
4. **Editorial Optical presentation** with asymmetric Skia fields, governed traces, strong reading hierarchy, and reduced-graphics parity.
5. **Hosted-web same-origin resilience** through `/p2-api`.
6. **Google identity + server-owned authorization** with PKCE, signed Parallax sessions, explicit owner/member roles, revocation, and root bearer retained only as break-glass / automation compatibility.

The next consequential engineering phase remains bounded execution evidence. Live unrestricted shell, autonomous Git merge, and autonomous production deployment remain intentionally outside the current execution authority boundary.

## Governance status

- `CURRENT-STATE.md`: updated for the deployed v0.10 release, exact release/production commits, migration and owner-seeding evidence, Vercel production evidence, runtime verification, and the remaining first-login verification boundary.
- `ARCHITECTURE.md`: updated from version 1.9 to 2.0 because durable identity, authorization, session-establishment, owner-role, and break-glass boundaries changed.
- `DESIGN-SYSTEM.md`: remains authoritative at version 1.6; no update required because the access gate/panel use the existing Editorial Optical visual language rather than establishing new durable visual rules.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
