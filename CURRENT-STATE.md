# Parallax 2.0 Current State

Version: 0.9.0
Date: 2026-08-21
Status: DEPLOYED AND DEPLOYMENT-VERIFIED
Production branch: `main`
Production application release commit: `a909b0a456917a45abc9b5e9a18f0f05cde1654c`
Validated release-tree commit: `30657652f7a5963dcf9ddf136bad828875348179`
Production web deployment: `dpl_6PhDQCRZByqajcNNLLFB8AsgnD9T`
Production API deployment: `dpl_7gTyHaJPWvRp6SKgMrkhzqEtDHR2`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production database: dedicated Supabase `Parallax 2.0`

## Current verified release

Parallax 2.0 v0.9.0 — **Editorial Optical** — is live through the GitHub → Vercel production pipeline.

PR #12 promoted the approved `P2-V0.9.0` visual release. The exact validated release tree is `30657652f7a5963dcf9ddf136bad828875348179`; the resulting production merge commit is `a909b0a456917a45abc9b5e9a18f0f05cde1654c`.

Git comparison between the validated release-tree commit and the production merge commit reports **zero changed files**, so the deployed application tree is the validated tree plus merge metadata.

The release changes client presentation and release documentation only. It does not change the API implementation, database schema, authentication architecture, Reason behavior, Work Specification approval policy, approved-spec execution binding, or deployment authority boundary. The authoritative production API therefore remains the verified v0.8.0 API deployment lineage.

## v0.9.0 product change — Editorial Optical

Editorial Optical preserves the Deep Violet precision foundation while adding a restrained editorial layer inspired by the hierarchy, asymmetry, negative space, softly framed grouping, selective color accents, and tactile graphic character reviewed from Anna's House. The implementation interprets those principles without copying external branding, illustrations, typography, menu layout, or palette.

The production visual language now includes:

- approximately **80% Deep Violet precision / 20% editorial personality**;
- slow asymmetric violet/indigo Skia ink fields instead of the prior drafting-grid/HUD emphasis;
- irregular contour ribbons and extremely subtle procedural print grain;
- one low-energy cyan optical focus linked to response energy;
- a reusable Skia `EditorialTrace` primitive for governed specification/execution state surfaces;
- open/asymmetric Work Specification framing rather than a uniform dashboard card;
- stronger display hierarchy and greater negative space for Code run state;
- softened illuminated-ink response inscription with lower scanner/beam dominance;
- restrained warm cream, dusty-peach, and muted-sage editorial accents while violet/indigo/cyan remain the identity system;
- reduced-graphics parity that preserves hierarchy and state semantics without requiring Skia traces;
- responsive mobile, tablet, and desktop behavior retained through the release browser suite.

Conversation text remains the highest-contrast visual layer. Ambient ink, grain, tracing, and accent color are subordinate to readable content.

## Preserved v0.8 trust boundary

v0.9.0 intentionally preserves the approved-spec execution architecture introduced in v0.8.0:

- explicit operator-approved Work Specification remains the Code activation authority;
- `EngineeringRun` remains bound to the exact Work Specification ID, revision, and digest;
- server-owned acceptance IDs remain authoritative across PLAN / BUILD / TEST / VERIFY / REVIEW;
- active runs cannot silently retarget to a newer specification revision;
- Reason/SSE behavior and `SPEC_AMENDMENT` semantics are unchanged;
- signed browser sessions and bearer compatibility are unchanged;
- same-origin `/p2-api` routing is unchanged;
- durable conversation and Work Specification persistence are unchanged;
- no unrestricted shell, Git mutation, merge, or autonomous production deployment authority was added.

## Release validation evidence

GitHub Actions run `32504431056` passed on exact validated candidate commit `30657652f7a5963dcf9ddf136bad828875348179`.

Passed gates:

- protected specification validation through `P2-V0.9.0`;
- Python compilation and full API tests;
- client TypeScript typecheck;
- response-state tests;
- Expo web export;
- production dependency-audit evidence capture;
- Playwright browser/Skia acceptance suite;
- Code binding browser acceptance inherited from v0.8 and included in the client visual test command;
- protected Engineering/Reason/Code promotion evaluation;
- DSPy SpecCritic + SpecCompiler release compilation;
- protected v0.9.0 compiled-plan contract verification.

During candidate validation, the new specification initially failed the protected contract because the Scope and Security sections were not numbered in the exact form required by the existing protected spec evaluator. The specification was corrected without weakening the evaluator. The subsequent full release-grade run passed all gates.

## Preview evidence

The substantive client implementation preview at commit `31badd6552553d260aed02bc6f23c67b496aeb89` was `READY`:

- deployment `dpl_HbZ36aWq8Hrse3XeeSShSmoBJaUu`;
- branch `p2/v0.9.0-editorial-optical`.

Commits after that preview changed only release workflow/documentation/specification material. Path-aware Vercel ignore logic correctly canceled redundant application builds for those non-client changes. Full release validation nevertheless ran against the exact final release-tree commit `30657652f7a5963dcf9ddf136bad828875348179`.

## Production verification evidence

### Web

Vercel production deployment `dpl_6PhDQCRZByqajcNNLLFB8AsgnD9T` is `READY` with the production aliases active and no alias error.

- deployed Git commit: `a909b0a456917a45abc9b5e9a18f0f05cde1654c`;
- target: `production`;
- `https://parallax-ashy-one-20.vercel.app`: HTTP 200 and serves Parallax 2.0;
- `/p2-api/health`: HTTP 200 with Parallax API health JSON;
- `/p2-api/ready`: HTTP 200 with database readiness `ok`;
- unauthenticated `/p2-api/v1/session`: expected HTTP 401 with `WWW-Authenticate: Bearer`, proving the same-origin route still reaches the protected API boundary rather than the SPA shell;
- Vercel reports no runtime error clusters for the web project during the verification window.

### API

The visual release does not modify `services/api`, so path-aware Vercel deployment correctly skipped the redundant API production build for merge commit `a909b0a456917a45abc9b5e9a18f0f05cde1654c`.

The authoritative API remains verified deployment `dpl_7gTyHaJPWvRp6SKgMrkhzqEtDHR2` from the v0.8.0 application lineage:

- alias: `https://parallax-api-tan.vercel.app`;
- target: `production`;
- database-backed readiness remains healthy through the production web proxy;
- Vercel reports no runtime error clusters for the API project during the v0.9 verification window.

GitHub combined status on the production v0.9 merge commit reports successful Vercel status for both `parallax` and `parallax-api`; for the API this success represents the intentional path-aware skip rather than a redundant new runtime build.

## Verification boundary

v0.9.0 is a visual/material release. No authentication or approved-spec execution implementation changed, so a new authenticated production Work Specification → Code activation round trip is not required to establish that the v0.9 visual tree is deployed correctly.

The underlying authenticated lifecycle remains covered by the protected API and browser acceptance inherited from v0.8.0. A fresh live authenticated production feature exercise is still not separately claimed because production root secret material is deliberately unavailable to deployment-verification tooling.

## Deployment state vocabulary

For v0.9.0:

- Specification approved: **YES**
- Implemented: **YES**
- Full release validation: **YES**
- Browser/Skia acceptance: **YES**
- Protected Engineering/Reason/Code evaluation: **YES**
- DSPy release compilation: **YES**
- Promoted to `main`: **YES**
- Validated tree equals production application tree: **YES**
- Production web deployment READY: **YES**
- Production web alias active: **YES**
- Production API intentionally unchanged/skipped: **YES**
- Health/readiness through same-origin production route: **YES**
- Protected authentication boundary through same-origin route: **YES**
- Production runtime errors in verification window: **NONE FOUND**
- Deployment verified: **YES**

## Current product baseline

Parallax now combines four durable layers:

1. **Conversation-first reasoning** with protected Reason/SSE behavior and durable state.
2. **Durable Work Specifications** with revision history and explicit approval.
3. **Approved-Spec Code execution binding** with immutable run/spec identity and server-owned acceptance authority.
4. **Editorial Optical presentation** with a distinctive restrained Skia material system that preserves accessibility and reduced-graphics parity.

The next consequential product phase should build on these foundations rather than widening autonomous authority prematurely. The strongest next step is bounded execution evidence: connect approved acceptance criteria to concrete, inspectable implementation/test artifacts before adding broader autonomous Git or deployment powers.

## Governance status

- `CURRENT-STATE.md`: updated for the verified v0.9.0 production release, exact validation/deployment evidence, visual baseline, and next product direction.
- `DESIGN-SYSTEM.md`: version 1.6 is authoritative on `main`; updated because Editorial Optical is now deployed durable visual language.
- `ARCHITECTURE.md`: remains version 1.9; v0.9.0 does not alter runtime topology, trust boundaries, persistence, or execution authority.
- `PROJECT-CONSTITUTION.md`: unchanged; governing principles did not materially change.

Historical release evidence remains preserved in repository history.
