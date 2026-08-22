# Parallax 2.0 Current State

Version: 0.11.1
Date: 2026-08-21
Status: DEPLOYED — PRODUCTION VERIFIED
Production branch: `main`
Production application release commit: `1780fd42c2ce5a42a620ae1da2e0ce8c01a45e34`
Validated release-tree commit: `19e0ea740322e2d69e5007212da934edae474515`
Production web deployment: `dpl_F9k1NMott4agcRkHtbRx54MUDErD`
Production API deployment: `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw` (unchanged v0.10 API; v0.11.1 is client-only)
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`

## Current deployed release

Parallax 2.0 v0.11.1 — **Mobile Viewport Polish** — is deployed through the GitHub → Vercel production pipeline.

PR #17 promoted approved specification `P2-V0.11.1`. The exact validated release tree is `19e0ea740322e2d69e5007212da934edae474515`; the production application merge commit is `1780fd42c2ce5a42a620ae1da2e0ce8c01a45e34`.

Git comparison between the validated release tree and production application merge reports **zero changed files**. Production therefore contains the exact validated application tree plus merge metadata.

v0.11.1 is a screenshot-driven corrective client release following operator review of the production phone layout. It preserves the v0.11.0 Editorial Optical conversation material and all existing product authority boundaries while correcting mobile governed-surface density and control overlap.

## v0.11.1 outcome

The production mobile screenshot exposed two material responsive defects: the collapsed Work Specification surface consumed too much of the phone viewport, and the signed-in account control floated across governed content.

v0.11.1 corrects those defects:

- the collapsed Work Specification surface uses compact phone margins, padding, typography, and spacing;
- the Work Specification explanatory subtitle is withheld while collapsed on phone viewports and returns when the governed surface is explicitly expanded;
- the title and actions no longer compete in the same narrow horizontal row on phones;
- specification capture, refresh, approve, and disclosure controls preserve accessible mobile interaction targets;
- the signed-in account presentation becomes a compact 44 pt launcher on phone viewports rather than the full name/role pill;
- the account launcher occupies reserved top-bar space and no longer overlaps the Work Specification surface or Reason/Code controls;
- the access-management panel is bounded to the available phone viewport with safe side margins;
- desktop/tablet Work Specification and account presentation remain materially unchanged;
- the v0.11.0 conversation material, calm Skia workplane, optical response inscription, reduced-motion behavior, and reduced-graphics parity remain intact.

No API, database, OAuth, authorization, session, Work Specification semantics, Engineering Run semantics, persistence, or execution-authority behavior changed in v0.11.1.

## Identity and authorization state

Google/Supabase proves identity. Parallax decides authorization through the production `authorized_users` allowlist.

The production identity boundary remains unchanged from v0.10.0:

- Google OAuth with PKCE through the dedicated Parallax Supabase Auth project;
- server-side allowlist authorization;
- identity-bearing signed Parallax sessions;
- Secure, HttpOnly, SameSite=Lax, host-only production cookie behavior;
- owner/member roles and immediate active/revoked authorization checks;
- root bearer retained only for break-glass / explicit automation compatibility.

The v0.11.1 account-control changes are presentation-only. Owner/member authorization and server-side enforcement are unchanged.

## Release validation evidence

GitHub Actions run `32541506003` completed successfully for exact candidate commit `19e0ea740322e2d69e5007212da934edae474515`.

Passed gates:

- protected specification validation through `P2-V0.11.1`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser / Skia acceptance;
- approved Work Specification → Code binding browser acceptance;
- hosted Google PKCE browser acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation against `P2-V0.11.1`;
- protected v0.11.1 compiled-plan contract verification.

The Google-auth browser suite now includes explicit 390×844 mobile geometry acceptance. It verifies:

- collapsed Work Specification height remains below the protected mobile ceiling;
- the account launcher does not overlap the Work Specification surface;
- the account launcher does not overlap the Reason or Code mode controls;
- the opened access-management panel remains within safe phone viewport bounds.

The new gate caught an additional small account/Reason-control overlap during implementation. That geometry was corrected before the final exact-head run was allowed to pass.

The final exact-head Vercel preview `dpl_8HVHMGKBhPxTXnoBJgZ4BfUMzScB` was `READY` before production promotion.

## Production verification evidence

### Web

Vercel deployment `dpl_F9k1NMott4agcRkHtbRx54MUDErD` is `READY`, targets production, reports Git commit `1780fd42c2ce5a42a620ae1da2e0ce8c01a45e34`, and owns the active production aliases.

Verified live behavior:

- production web root: HTTP 200 and serves the v0.11.1 production bundle;
- `/p2-api/health`: HTTP 200 with Parallax API health JSON;
- `/p2-api/ready`: HTTP 200 with database readiness `ok`;
- unauthenticated `/p2-api/v1/session`: expected HTTP 401 with `WWW-Authenticate: Bearer`;
- no frontend runtime-error clusters found in the verification window.

### API

v0.11.1 does not change API code. The active API production deployment remains `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw`, is `READY`, and continues to serve the production aliases.

Verified live behavior through the same-origin web gateway:

- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database readiness `ok`;
- protected session boundary remains enforced;
- no API runtime-error clusters found in the verification window.

## Deployment state vocabulary

For v0.11.1:

- Specification approved: **YES**
- Implemented: **YES**
- Full exact-head release validation: **YES**
- 390×844 mobile geometry acceptance: **YES**
- Browser / Skia acceptance: **YES**
- Google-auth browser acceptance: **YES**
- Approved Work Specification → Code binding acceptance: **YES**
- Protected Engineering / Reason / Code evaluation: **YES**
- DSPy v0.11.1 release compilation: **YES**
- Validated tree equals production application tree: **YES**
- Exact-head preview READY before promotion: **YES**
- Production web deployment READY: **YES**
- Production API remains READY: **YES — unchanged service**
- Production aliases active: **YES**
- Hosted same-origin health/readiness: **YES**
- Protected unauthenticated boundary: **YES**
- Production runtime errors in verification window: **NONE FOUND**
- v0.11.1 deployment-verified: **YES**

## Current product baseline

Parallax now combines:

1. **Conversation-first Reason** with protected streaming behavior and durable state.
2. **Durable Work Specifications** with revision history and explicit operator approval.
3. **Approved-Spec Code execution binding** with immutable run/spec identity and server-owned acceptance authority.
4. **Editorial Optical conversation material** with soft translucent message surfaces rather than conventional bordered cards.
5. **Calm living optical workplane** with slow lava-field motion, dark reading-zone protection, reduced-motion behavior, and reduced-graphics parity.
6. **Theme-colored optical response inscription** that visibly etches fresh response glyphs and cools into normal selectable text.
7. **Mobile governed-surface discipline** with compact Work Specification presentation, non-overlapping identity/mode controls, and viewport-safe access management.
8. **Hosted-web same-origin resilience** through `/p2-api`.
9. **Google identity + server-owned authorization** with PKCE, signed Parallax sessions, explicit owner/member roles, revocation, and root bearer retained only as break-glass / automation compatibility.

The next consequential engineering phase remains bounded execution evidence. Live unrestricted shell, autonomous Git merge, and autonomous production deployment remain intentionally outside the current execution authority boundary.

## Governance status

- `CURRENT-STATE.md`: updated for deployed and verified v0.11.1, the screenshot-driven mobile corrective release, exact validated/production commits, mobile browser geometry evidence, Vercel production evidence, protected boundary checks, and runtime verification.
- `DESIGN-SYSTEM.md`: remains authoritative at v1.7; no update required because v0.11.1 corrects responsive application of the existing Editorial Optical rules rather than establishing a new durable visual language.
- `ARCHITECTURE.md`: unchanged at v2.0; v0.11.1 introduces no topology, persistence, trust, identity, or execution-authority change.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
