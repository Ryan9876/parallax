# Parallax 2.0 Current State

Version: 0.9.1
Date: 2026-08-21
Status: DEPLOYED AND DEPLOYMENT-VERIFIED
Production branch: `main`
Production application release commit: `16af7a2c34a3ebdca509f0a789fa577f307d8c48`
Validated release-tree commit: `e80447d179836faf3bb3a78ecbeb4568157acee0`
Production web deployment: `dpl_2UQeJNBJTjcxUdDT92uVDu2efa7e`
Production API deployment: `dpl_7gTyHaJPWvRp6SKgMrkhzqEtDHR2`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`

## Current verified release

Parallax 2.0 v0.9.1 — **Editorial Optical Amplification** — is live through the GitHub → Vercel production pipeline.

PR #13 promoted approved spec `P2-V0.9.1`. The exact validated release tree is `e80447d179836faf3bb3a78ecbeb4568157acee0`; the production merge commit is `16af7a2c34a3ebdca509f0a789fa577f307d8c48`.

Git comparison between the validated release tree and production merge reports **zero changed files**. The deployed application tree is therefore the exact validated tree plus merge metadata.

## Why v0.9.1 was required

A production screenshot of v0.9.0 showed two material issues.

First, Editorial Optical was present but too restrained at rest. The dark-violet field, contour treatment, and editorial accents were technically deployed, but the result read too close to the earlier precision shell and did not visibly deliver the stronger authored/editorial character intended by the design direction.

Second, the screenshot exposed a functional production-web routing defect: the shell showed `VISUAL FALLBACK · API OFFLINE`, `P2-V0.3.0`, and sample fallback conversation content even though the production same-origin `/p2-api` gateway and API were healthy. The client could select the localhost fallback when `EXPO_PUBLIC_PARALLAX_API_URL` was absent at bundle time.

v0.9.1 corrects both issues rather than treating the screenshot as a subjective styling complaint alone.

## v0.9.1 visual amplification

The authoritative design direction remains Editorial Optical — approximately **80% Deep Violet precision / 20% editorial personality** — but the deployed treatment now expresses it more clearly at rest.

Changes include:

- materially stronger asymmetric violet and indigo Skia ink fields;
- more legible irregular contour ribbons while retaining low-frequency motion;
- a restrained stable dusty-peach field, muted-sage field, and warm cream paper-light pool;
- stronger cyan optical focus without full-screen neon treatment;
- subtle procedural grain retained below narrative text;
- reduced center darkening so the authored field remains perceptible behind the reading area;
- stronger material transparency and border contrast;
- a more expressive Parallax Optical Mark with cyan/indigo/violet structure, a restrained peach editorial cut, and cream center;
- stronger asymmetric Work Specification framing with larger editorial title hierarchy;
- stronger opposite-side Code execution framing with sage execution identity and larger run hierarchy;
- conversation copy remains the highest-contrast layer.

This is an amplification of the already-authoritative Editorial Optical rules, not a new design-system architecture.

## Hosted-web routing correction

Hosted HTTPS web now selects the deployed same-origin `/p2-api` gateway from the runtime origin even when the compile-time public API base is absent.

The client transport rule is now:

- hosted HTTPS web → same-origin `/p2-api`;
- web with an explicitly configured HTTPS API → same-origin `/p2-api`;
- local HTTP web development → configured/local direct API behavior;
- native → configured direct API behavior.

The correction does **not** weaken authentication. Signed HttpOnly browser sessions, `X-Parallax-Session`, bearer compatibility, and non-persistence of browser bearer credentials remain unchanged. No secret was added to a public environment variable or browser storage.

The practical effect is that a hosted production browser reaches the private authentication boundary instead of silently presenting the API-offline sample shell when the compile-time public API variable is absent.

## Preserved trust and execution boundaries

v0.9.1 does not change:

- Reason behavior or SSE response contracts;
- durable conversation persistence;
- Work Specification revision/approval policy;
- approved-spec Code activation authority;
- immutable `EngineeringRun` ↔ Work Specification ID/revision/digest binding;
- server-owned acceptance criteria across PLAN / BUILD / TEST / VERIFY / REVIEW;
- database schema;
- API route contracts;
- signed-session or bearer security semantics;
- autonomous execution authority;
- Git, merge, shell, or production-deployment authority.

No database migration was required.

## Release validation evidence

GitHub Actions run `32509348460` passed on exact candidate commit `e80447d179836faf3bb3a78ecbeb4568157acee0`.

Passed gates:

- protected specification validation through `P2-V0.9.1`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser/Skia acceptance;
- Code-binding browser acceptance;
- protected Engineering/Reason/Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation;
- protected v0.9.1 compiled-plan contract verification.

The fast draft validation run `32509200933` also passed before the PR entered the release lane.

## Preview evidence

Exact-head v0.9.1 frontend preview:

- deployment `dpl_kwrNgXeiPYtw53KWAUUbfnzxHthQ`;
- commit `e80447d179836faf3bb3a78ecbeb4568157acee0`;
- branch `p2/v0.9.1-editorial-amplification`;
- state `READY`.

The preview was protected by Vercel Authentication, so no claim is made that deployment tooling visually inspected its rendered authenticated shell. Browser/Skia visual acceptance is instead grounded in the exact-head release suite.

## Production verification evidence

### Web

Vercel deployment `dpl_2UQeJNBJTjcxUdDT92uVDu2efa7e` is `READY` and serves production commit `16af7a2c34a3ebdca509f0a789fa577f307d8c48`.

Verified production behavior:

- `https://parallax-ashy-one-20.vercel.app`: HTTP 200 and serves the v0.9.1 Expo bundle;
- `/p2-api/health`: HTTP 200 with Parallax API health JSON;
- `/p2-api/ready`: HTTP 200 with database readiness `ok`;
- unauthenticated `/p2-api/v1/session`: expected HTTP 401 with `WWW-Authenticate: Bearer`, proving hosted web reaches the protected same-origin API boundary;
- Vercel reports no frontend runtime-error clusters in the verification window.

### API

No API implementation changed in v0.9.1. Path-aware Vercel logic intentionally skipped a redundant API runtime rebuild for the production merge.

The authoritative API remains deployment `dpl_7gTyHaJPWvRp6SKgMrkhzqEtDHR2`:

- alias `https://parallax-api-tan.vercel.app`;
- database-backed readiness remains healthy through the production proxy;
- Vercel reports no API runtime-error clusters in the verification window.

GitHub combined status for production merge `16af7a2c34a3ebdca509f0a789fa577f307d8c48` reports successful Vercel status for both `parallax` and `parallax-api`; API success represents the intentional ignored build rather than a redundant runtime replacement.

## Verification boundary

The v0.9.1 application tree, production web deployment, hosted same-origin routing, API health/readiness, protected authentication boundary, and runtime-error state are deployment-verified.

A fresh authenticated production Work Specification → Code activation round trip is still **not separately claimed**, because production root credential material is deliberately unavailable to deployment-verification tooling. The protected lifecycle remains covered by the exact-head API and browser acceptance suite.

## Deployment state vocabulary

For v0.9.1:

- Specification approved: **YES**
- Implemented: **YES**
- Fast validation: **YES**
- Full release validation: **YES**
- Browser/Skia acceptance: **YES**
- Protected Engineering/Reason/Code evaluation: **YES**
- DSPy release compilation: **YES**
- Exact-head preview READY: **YES**
- Promoted to `main`: **YES**
- Validated tree equals production application tree: **YES**
- Production web deployment READY: **YES**
- Production alias active: **YES**
- Hosted same-origin health/readiness: **YES**
- Protected authentication boundary through `/p2-api`: **YES**
- Production runtime errors in verification window: **NONE FOUND**
- Production API implementation changed: **NO**
- Fresh authenticated production spec→Code exercise: **NOT SEPARATELY VERIFIED**
- Deployment verified: **YES**, within the explicit authentication-evidence boundary above.

## Current product baseline

Parallax now combines:

1. **Conversation-first Reason** with protected streaming behavior and durable state.
2. **Durable Work Specifications** with revision history and explicit operator approval.
3. **Approved-Spec Code execution binding** with immutable run/spec identity and server-owned acceptance authority.
4. **Editorial Optical presentation** with materially visible asymmetric Skia ink fields, restrained warm editorial accents, governed traces, and reduced-graphics parity.
5. **Hosted-web routing resilience** that selects the production same-origin API gateway from the HTTPS runtime rather than depending on a compile-time public API base to avoid a localhost fallback.

The next consequential product phase remains bounded execution evidence: connect approved acceptance criteria to concrete implementation, test, and verification artifacts before broadening autonomous Git or deployment authority.

## Governance status

- `CURRENT-STATE.md`: updated for the verified v0.9.1 release, screenshot-derived diagnosis, routing correction, visual amplification, exact validation evidence, and production deployment evidence.
- `DESIGN-SYSTEM.md`: remains authoritative at version 1.6; no update required because v0.9.1 increases fidelity to the existing Editorial Optical rules rather than changing those durable rules.
- `ARCHITECTURE.md`: remains version 1.9; no update required because the same-origin topology and trust boundaries are unchanged and v0.9.1 corrects client transport selection within that architecture.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
