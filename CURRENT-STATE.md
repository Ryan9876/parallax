# Parallax 2.0 Current State

Version: 0.12.0
Date: 2026-08-21
Status: DEPLOYED — PRODUCTION VERIFIED
Production branch: `main`
Production application release commit: `7d86aa3e9ae1dd096cf4712b786ccf4c2534b6a5`
Validated release-tree commit: `07610e2ba22b63f8fd9f1ab6df42dc7fcd45449b`
Production web deployment: `dpl_9RZi4PQzYZpezwGcG4vUhiC7fQib`
Production API deployment: `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw` (unchanged v0.10 API; v0.12.0 is client-only)
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`

## Current deployed release

Parallax 2.0 v0.12.0 — **Ambient Chroma Flow** — is deployed through the GitHub → Vercel production pipeline.

PR #18 promoted approved specification `P2-V0.12.0`. The exact validated release tree is `07610e2ba22b63f8fd9f1ab6df42dc7fcd45449b`; the production application merge commit is `7d86aa3e9ae1dd096cf4712b786ccf4c2534b6a5`.

Git comparison between the validated release tree and production application merge reports **zero changed files**. Production therefore contains the exact validated application tree plus merge metadata.

v0.12.0 is a reference-informed visual refinement requested by the operator. The supplied motion reference was used only to identify motion principles: broad diffused color, liquid-light blending, low-frequency drift, and occasional warm counterpoints. The reference video itself, its frames, watermark, assets, or exact color sequence are not embedded, copied, or shipped by Parallax.

## v0.12.0 outcome

The living workplane now uses **Ambient Chroma Flow** rather than discrete lava-style masses.

The production treatment:

- uses broad, heavily feathered chroma fields that overlap like light diffusing through liquid glass;
- keeps dark indigo, violet, midnight blue, and cobalt as the dominant Parallax color family;
- introduces restrained magenta and lavender atmosphere without turning the experience into a neon gradient;
- permits sparse amber/peach blooms as a small warm counterpoint rather than a dominant field;
- retains cyan as a restrained optical accent;
- uses low-frequency warped haze to blend neighboring color regions so the eye does not read separate hard-edged blobs;
- changes composition over tens of seconds rather than using short loops, bouncing movement, particles, or directional sweeps;
- keeps the central conversation reading region materially darker than the perimeter chroma;
- modestly increases chroma presence during active reasoning without materially increasing animation speed;
- retains fine low-amplitude grain to avoid a flat digital gradient;
- freezes time-dependent motion when reduced motion is enabled while retaining a coherent static field;
- preserves reduced-graphics functional parity.

The v0.11 conversation-material system, v0.11.1 mobile viewport corrections, and the theme-colored optical response etching remain unchanged. Fresh assistant glyphs still carry violet/indigo etched energy, lavender heat, and a restrained cyan inscription point before cooling into normal selectable narrative text.

No API, database, OAuth, authorization, session, Reason, Code, Work Specification semantics, Engineering Run semantics, persistence, or execution-authority behavior changed in v0.12.0.

## Identity and authorization state

Google/Supabase proves identity. Parallax decides authorization through the production `authorized_users` allowlist.

The production identity boundary remains unchanged from v0.10.0:

- Google OAuth with PKCE through the dedicated Parallax Supabase Auth project;
- server-side allowlist authorization;
- identity-bearing signed Parallax sessions;
- Secure, HttpOnly, SameSite=Lax, host-only production cookie behavior;
- owner/member roles and immediate active/revoked authorization checks;
- root bearer retained only for break-glass / explicit automation compatibility.

The real interactive production Google owner path was previously verified and remains part of the production baseline.

## Release validation evidence

GitHub Actions run `32544031923` completed successfully for exact candidate commit `07610e2ba22b63f8fd9f1ab6df42dc7fcd45449b`.

Passed gates:

- protected specification validation through `P2-V0.12.0`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser / Skia acceptance;
- approved Work Specification → Code binding browser acceptance;
- hosted Google PKCE browser acceptance;
- v0.11.1 protected mobile geometry acceptance at 390×844;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation against `P2-V0.12.0`;
- protected v0.12.0 compiled-plan contract verification.

Browser/Skia evidence confirms the full-screen Skia frame changes over time, the conversation and composer remain within viewport bounds across mobile/tablet/desktop, the optical response inscription continues to activate during streaming, and reduced-graphics parity remains functional.

The implementation was deliberately tuned after first-pass visual evidence showed the initial diffused field was too subtle. The final candidate strengthens violet/blue/magenta atmospheric presence while retaining the protected dark reading zone and restrained warm accents. The final exact-head candidate then passed the complete release gate.

## Production verification evidence

### Web

Vercel deployment `dpl_9RZi4PQzYZpezwGcG4vUhiC7fQib` is `READY`, targets production, reports Git commit `7d86aa3e9ae1dd096cf4712b786ccf4c2534b6a5`, and owns the active production aliases including `parallax-ashy-one-20.vercel.app`.

Verified live behavior:

- production web root: HTTP 200 and serves the v0.12.0 production bundle;
- `/p2-api/health`: HTTP 200 with Parallax API health JSON;
- `/p2-api/ready`: HTTP 200 with database readiness `ok`;
- unauthenticated `/p2-api/v1/session`: expected HTTP 401 with `WWW-Authenticate: Bearer`;
- no frontend runtime-error clusters found in the one-hour verification window.

### API

v0.12.0 does not change API code. Vercel correctly canceled the redundant production API deployment `dpl_A8VQQfZm63hL2F9LAtirfiYoA2WF` through the path-aware build optimization.

The active API production deployment remains `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw`, is unchanged, and continues to serve the production aliases.

Verified live behavior through the same-origin web gateway:

- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database readiness `ok`;
- protected session boundary remains enforced;
- no API runtime-error clusters found in the one-hour verification window.

## Deployment state vocabulary

For v0.12.0:

- Specification approved: **YES**
- Implemented: **YES**
- Reference used as inspiration rather than embedded asset: **YES**
- Full exact-head release validation: **YES**
- Browser / Skia acceptance: **YES**
- Google-auth browser acceptance: **YES**
- v0.11.1 mobile geometry regression protection: **YES**
- Approved Work Specification → Code binding acceptance: **YES**
- Protected Engineering / Reason / Code evaluation: **YES**
- DSPy v0.12.0 release compilation: **YES**
- Validated tree equals production application tree: **YES**
- Production web deployment READY: **YES**
- Production API remains READY: **YES — unchanged service**
- Redundant API production deployment correctly skipped: **YES**
- Production aliases active: **YES**
- Hosted same-origin health/readiness: **YES**
- Protected unauthenticated boundary: **YES**
- Production runtime errors in verification window: **NONE FOUND**
- v0.12.0 deployment-verified: **YES**

## Current product baseline

Parallax now combines:

1. **Conversation-first Reason** with protected streaming behavior and durable state.
2. **Durable Work Specifications** with revision history and explicit operator approval.
3. **Approved-Spec Code execution binding** with immutable run/spec identity and server-owned acceptance authority.
4. **Editorial Optical conversation material** with soft translucent message surfaces rather than conventional bordered cards.
5. **Ambient Chroma Flow workplane** with broad diffused liquid-light color, indigo/violet dominance, restrained warm counterpoints, central reading-zone protection, reduced-motion behavior, and reduced-graphics parity.
6. **Theme-colored optical response inscription** that visibly etches fresh response glyphs and cools into normal selectable text.
7. **Mobile governed-surface discipline** with compact Work Specification presentation, non-overlapping identity/mode controls, and viewport-safe access management.
8. **Hosted-web same-origin resilience** through `/p2-api`.
9. **Google identity + server-owned authorization** with PKCE, signed Parallax sessions, explicit owner/member roles, revocation, and root bearer retained only as break-glass / automation compatibility.

The next consequential engineering phase remains bounded execution evidence. Live unrestricted shell, autonomous Git merge, and autonomous production deployment remain intentionally outside the current execution authority boundary.

## Governance status

- `CURRENT-STATE.md`: updated for deployed and verified v0.12.0, the reference-informed Ambient Chroma Flow release, exact validated/production commits, release-gate evidence, Vercel production evidence, unchanged API boundary, protected-route checks, and runtime verification.
- `DESIGN-SYSTEM.md`: advanced to v1.8 because Ambient Chroma Flow establishes a durable replacement for the previous discrete lava-mass workplane rule.
- `ARCHITECTURE.md`: unchanged at v2.0; v0.12.0 introduces no topology, persistence, trust, identity, or execution-authority change.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
