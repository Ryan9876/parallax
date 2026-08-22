# Parallax 2.0 Current State

Version: 0.11.0
Date: 2026-08-21
Status: DEPLOYED — PRODUCTION VERIFIED
Production branch: `main`
Production application release commit: `e87a25ff0ba4cf5d8c71492294da735b13498458`
Validated release-tree commit: `2414bbe719e41be52d86cc9c5329c1feea371c0c`
Production web deployment: `dpl_9iQfhzbUMVsvo9twXeSw9oLAdi5Q`
Production API deployment: `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw` (unchanged v0.10 API; v0.11 is client-only)
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`

## Current deployed release

Parallax 2.0 v0.11.0 — **Conversation Material & Optical Etching** — is deployed through the GitHub → Vercel production pipeline.

PR #16 promoted approved specification `P2-V0.11.0`. The exact validated release tree is `2414bbe719e41be52d86cc9c5329c1feea371c0c`; the production merge commit is `e87a25ff0ba4cf5d8c71492294da735b13498458`.

Git comparison between the validated release tree and production merge reports **zero changed files**. Production therefore contains the exact validated application tree plus merge metadata.

## v0.11.0 outcome

The core conversation experience was refined in response to operator review of the production mobile UI.

The release changes the presentation rather than the product authority boundary:

- ordinary user and assistant messages no longer use hard continuous card borders;
- user messages use softly rounded, translucent neutral-grey/indigo material;
- assistant responses use wider rounded neutral-grey/navy material with faint local optical depth rather than top/bottom/left panel rules;
- assistant identity remains outside the response material and subordinate to narrative copy;
- the composer uses the same softer rounded material language with 44 pt mobile controls;
- the Skia workplane now uses a calm low-frequency lava-lamp-like field of large violet/indigo optical masses with restrained cyan energy and a deliberately darker central reading field;
- the active optical typesetter restores a more visible theme-colored inscription signature: violet/indigo etching, lavender fresh-glyph energy, and a restrained cyan focus point;
- settled assistant text cools back to normal pale selectable narrative text;
- reduced-motion freezes time-dependent optical motion while preserving meaning;
- reduced-graphics parity preserves the conversation-material hierarchy without Skia.

No API, database, OAuth, authorization, session, Work Specification, Engineering Run, or execution-authority behavior changed in v0.11.0.

## Identity and authorization state

Google/Supabase proves identity. Parallax decides authorization through the production `authorized_users` allowlist.

The initial owner record is active and the real interactive production Google sign-in path has now been verified by the operator: successful Google authentication reached the live Parallax workspace and displayed the expected owner identity/role state.

The user's email address is deliberately not recorded in this public project-state file.

The production identity boundary remains:

- Google OAuth with PKCE through the dedicated Parallax Supabase Auth project;
- server-side allowlist authorization;
- identity-bearing signed Parallax sessions;
- Secure, HttpOnly, SameSite=Lax, host-only production cookie behavior;
- owner/member roles and immediate active/revoked authorization checks;
- root bearer retained only for break-glass / explicit automation compatibility.

## Release validation evidence

GitHub Actions run `32539073857` completed successfully for exact candidate commit `2414bbe719e41be52d86cc9c5329c1feea371c0c`.

Passed gates:

- protected specification validation through `P2-V0.11.0`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser / Skia acceptance;
- Google-auth browser acceptance;
- approved Work Specification → Code binding browser acceptance;
- protected Engineering / Reason / Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation against `P2-V0.11.0`;
- protected v0.11.0 compiled-plan contract verification.

The release initially exposed a specification-contract omission (`security` section). The gate correctly rejected that candidate. `P2-V0.11.0` was amended to explicitly inherit and protect the v0.10 identity/security boundary, and the subsequent exact-head run passed all gates. This is recorded as validation evidence rather than hidden release noise.

## Production verification evidence

### Web

Vercel deployment `dpl_9iQfhzbUMVsvo9twXeSw9oLAdi5Q` is `READY`, targets production, reports Git commit `e87a25ff0ba4cf5d8c71492294da735b13498458`, and owns the active production aliases.

Verified live behavior:

- production web root: HTTP 200;
- `/p2-api/health`: HTTP 200 with Parallax API health JSON;
- `/p2-api/ready`: HTTP 200 with database readiness `ok`;
- unauthenticated `/p2-api/v1/session`: expected HTTP 401 with `WWW-Authenticate: Bearer`;
- no frontend runtime-error clusters found in the verification window.

### API

v0.11.0 does not change API code. Path-aware Vercel deployment correctly canceled the redundant API build for the v0.11 production merge.

The active API production deployment remains `dpl_AfNZbFj2dMeYKKjGr6v9s3yhMgMw`, is `READY`, and continues to serve the production aliases.

Verified live behavior through the same-origin web gateway:

- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database readiness `ok`;
- protected session boundary remains enforced;
- no API runtime-error clusters found in the verification window.

## Deployment state vocabulary

For v0.11.0:

- Specification approved: **YES**
- Implemented: **YES**
- Full exact-head release validation: **YES**
- Browser / Skia acceptance: **YES**
- Google-auth browser acceptance: **YES**
- Protected Engineering / Reason / Code evaluation: **YES**
- DSPy v0.11 release compilation: **YES**
- Validated tree equals production application tree: **YES**
- Production web deployment READY: **YES**
- Production API remains READY: **YES — unchanged service**
- Production aliases active: **YES**
- Hosted same-origin health/readiness: **YES**
- Protected unauthenticated boundary: **YES**
- Real production Google login / owner path: **YES — operator verified**
- Production runtime errors in verification window: **NONE FOUND**
- v0.11 deployment-verified: **YES**

## Current product baseline

Parallax now combines:

1. **Conversation-first Reason** with protected streaming behavior and durable state.
2. **Durable Work Specifications** with revision history and explicit operator approval.
3. **Approved-Spec Code execution binding** with immutable run/spec identity and server-owned acceptance authority.
4. **Editorial Optical conversation material** with soft translucent message surfaces rather than conventional bordered cards.
5. **Calm living optical workplane** with slow lava-field motion, dark reading-zone protection, reduced-motion behavior, and reduced-graphics parity.
6. **Theme-colored optical response inscription** that visibly etches fresh response glyphs and cools into normal selectable text.
7. **Hosted-web same-origin resilience** through `/p2-api`.
8. **Google identity + server-owned authorization** with PKCE, signed Parallax sessions, explicit owner/member roles, revocation, and root bearer retained only as break-glass / automation compatibility.

The next consequential engineering phase remains bounded execution evidence. Live unrestricted shell, autonomous Git merge, and autonomous production deployment remain intentionally outside the current execution authority boundary.

## Governance status

- `CURRENT-STATE.md`: updated for deployed and verified v0.11.0, production visual evidence, exact release commit/deployment, preserved security boundary, and successful real Google owner login.
- `DESIGN-SYSTEM.md`: updated from v1.6 to v1.7 because conversation material, ambient lava-field behavior, and optical inscription treatment are now durable visual rules.
- `ARCHITECTURE.md`: unchanged at v2.0; v0.11.0 introduces no topology, persistence, trust, identity, or execution-authority change.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
