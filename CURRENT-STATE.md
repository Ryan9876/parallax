# Parallax 2.0 Current State

Version: 0.6.3
Date: 2026-08-21
Status: DEPLOYED AND DEPLOYMENT-VERIFIED
Production branch: `main`
Production application release commit: `3a05416bca3bf9a14817f7f5341cb38812c7cfa5`
Validated release-tree commit: `e17ee9262d1a2d151d60c0ed370c7f938a761f0b`
Production API release lineage: `670d1233bb36de39bb2e5d91fcb046d6dbedea6b`
Production web deployment: `dpl_GSizfW61TWoVGP8CkRpa3iwLAPKw`
Production API deployment: `dpl_HctJQ7rWMmg5BVYh35wMYqvTwCCS`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`

## Current verified release

Parallax 2.0 v0.6.3 is live through the GitHub → Vercel production pipeline.

PR #8 promoted the approved `P2-V0.6.3` Deep Violet Optical visual release. The release-candidate tree at `e17ee9262d1a2d151d60c0ed370c7f938a761f0b` passed the complete release validation suite before promotion. The resulting merge commit is `3a05416bca3bf9a14817f7f5341cb38812c7cfa5`.

Git comparison between the validated release-tree commit and the production merge commit reports no changed files. The production application therefore contains the exact validated application tree plus merge metadata.

This release changes client presentation only. `services/api` was not changed, so the authoritative production API remains the verified v0.6.2 API deployment lineage.

## v0.6.3 product change — Deep Violet Optical

The prior light mineral presentation has been replaced by the approved dark Parallax direction while preserving the existing product and trust contracts.

Production visual language now uses:

- deep navy/black substrate centered on `#080B12`;
- dark raised optical surfaces (`#0B1019`, `#111525`, `#161A2B`);
- high-contrast pale violet-white narrative text (`#F4F2FF`);
- cyan optical energy (`#7DE7FF`);
- indigo precision/status structure (`#8B9CFF`);
- violet identity and selected/action treatment (`#D18BFF`, `#8F63D8`);
- dark translucent glass instead of light mineral glass;
- a retuned cyan → indigo → violet Parallax Optical Mark;
- a deep navy/violet Skia living workplane with restrained contours, grid, focus, and calibration trace;
- a retuned optical typesetter with cyan/lavender response energy;
- matching dark-violet reduced-graphics fallback and Code engineering-status presentation.

The theme intentionally concentrates saturation in identity, active focus, and response energy. Conversation copy remains the highest-contrast visual layer.

## Preserved functional contracts

v0.6.3 intentionally does not change:

- Reason behavior or protected reasoning contracts;
- Code engineering state machine or execution policy;
- session establishment or signed HttpOnly cookie behavior;
- bearer compatibility for non-browser clients and Swagger;
- same-origin `/p2-api` production proxy;
- SSE response transport;
- durable conversation persistence;
- `SPEC_AMENDMENT` semantics;
- reduced-motion behavior;
- selectable/accessibility-aware final response text.

## Verified release evidence

### Release candidate

GitHub Actions run `32452412530` passed on the exact validated release-tree commit `e17ee9262d1a2d151d60c0ed370c7f938a761f0b`:

- API + contract checks: **PASS**;
- Python compile/API tests: **PASS**;
- client typecheck: **PASS**;
- response-state tests: **PASS**;
- Expo web export: **PASS**;
- production dependency audit evidence: **PASS**;
- Playwright browser/Skia acceptance suite: **PASS**;
- protected Engineering/Reason/Code promotion evaluation: **PASS**;
- DSPy SpecCritic + SpecCompiler release compilation: **PASS**.

The client build evidence artifact was produced successfully for that exact release tree. Desktop, mobile, and reduced-graphics render evidence confirms the Deep Violet Optical material system is present and coherent while keeping copy readable and controls usable.

The Vercel preview for the exact release-tree commit was `READY` before promotion:

- deployment: `dpl_HpL3VXTHxC9m3RCGf2pFHZXdasxT`;
- branch: `p2/v0.6.3-purple-optical`;
- commit: `e17ee9262d1a2d151d60c0ed370c7f938a761f0b`.

### Production web

- deployment `dpl_GSizfW61TWoVGP8CkRpa3iwLAPKw` is `READY`;
- target is `production`;
- deployed Git commit is `3a05416bca3bf9a14817f7f5341cb38812c7cfa5`;
- production alias assignment completed without error;
- `https://parallax-ashy-one-20.vercel.app` returns HTTP 200 and serves the Parallax 2.0 Expo application;
- `https://parallax-ashy-one-20.vercel.app/p2-api/health` returns HTTP 200 with Parallax API health JSON;
- `https://parallax-ashy-one-20.vercel.app/p2-api/ready` returns HTTP 200 with database readiness `ok`;
- `https://parallax-ashy-one-20.vercel.app/p2-api/v1/session` without credentials returns the expected HTTP 401 JSON response with `WWW-Authenticate: Bearer`, proving the same-origin route still reaches the protected API boundary rather than the SPA shell.

### Production API

The visual release did not modify `services/api`. The authoritative API deployment remains:

- deployment `dpl_HctJQ7rWMmg5BVYh35wMYqvTwCCS`: `READY`;
- alias `https://parallax-api-tan.vercel.app`;
- `/health`: HTTP 200;
- `/ready`: HTTP 200 with database dependency ready;
- bearer authentication remains active for protected endpoints;
- Swagger/OpenAPI bearer authorization and an authenticated protected conversation creation request were previously verified on this production lineage.

A fresh authenticated browser-cookie round trip is **not separately claimed** for v0.6.3 because no authentication implementation changed and production secret material was not exposed to deployment-verification tooling. The browser-session contract remains covered by the protected automated tests inherited from v0.6.2.

## Delivery efficiency

The tiered CI and path-aware Vercel workflow remain in force:

```text
Development change
    |
    | fast API/contracts + client typecheck/state/export
    v
Vercel Preview
    |
    | release candidate
    v
Full release validation
    ├─ browser + Skia acceptance
    ├─ protected Engineering/Reason/Code evaluation
    ├─ DSPy compilation/contract verification
    └─ dependency audit evidence
    |
    v
main → Vercel Production → live verification
```

Unchanged API code does not require a redundant API application rebuild for this client-only release.

## Deployment state vocabulary

For v0.6.3:

- Specification approved: **YES**
- Generated: **YES**
- Committed/pushed: **YES**
- Full release validation: **YES**
- Preview deployment READY: **YES**
- Promoted to `main`: **YES**
- Production web deployment READY: **YES**
- Production alias active: **YES**
- Production web/API proxy health verified: **YES**
- Production database readiness verified: **YES**
- Protected route reaches API/auth boundary through same-origin proxy: **YES**
- Fresh authenticated browser-cookie round trip: **NOT SEPARATELY CLAIMED**
- Deployment verified: **YES**, subject to the explicit authenticated-cookie caveat above.

## Governance status

- `CURRENT-STATE.md`: updated for the verified v0.6.3 production release, deployment identities, release evidence, and live verification.
- `DESIGN-SYSTEM.md`: updated to v1.5 because Deep Violet Optical is a durable visual-language change.
- `ARCHITECTURE.md`: unchanged; runtime topology and trust boundaries did not change.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not change.

Historical v0.1–v0.6.2 implementation and deployment evidence remains preserved in repository history.
