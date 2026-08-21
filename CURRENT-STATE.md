# Parallax 2.0 Current State

Version: 0.6.1
Date: 2026-08-20
Status: DEPLOYED AND DEPLOYMENT-VERIFIED
Active development branch: `p2/v0.6.0`
Production branch: `main`
Release head before this record update: `74724b166c9481597b3c7b175ec8d37b6bd34336`
Production deployment: `dpl_6EuWr8yUPRM4KAhqvaCTvwS541p1`
Production alias: `https://parallax-ashy-one-20.vercel.app`

## Current verified release

Parallax 2.0 v0.6.1 is live through the GitHub → Vercel production pipeline.

Verified release evidence:

- GitHub `main` was fast-forwarded to the validated v0.6.1 release lineage.
- Vercel created a Git-sourced production deployment from commit `74724b166c9481597b3c7b175ec8d37b6bd34336`.
- Vercel reported deployment state `READY` with production target and no alias error.
- The production alias returned HTTP `200 OK` and served the Parallax 2.0 Expo web shell.
- `p2/v0.6.0` was fast-forwarded to the same release head so development and production histories remain aligned.

Deployment state vocabulary remains strict:

- Generated: **YES**
- Committed/pushed: **YES**
- Vercel build ready: **YES**
- Deployed to production: **YES**
- Deployment verified: **YES**
- Full CI/typecheck/lint re-run specifically for this visual-only release: **NOT CLAIMED**

## v0.6.1 product changes

### Optical identity

- The Parallax mark was refined away from scanner/HUD language toward a calmer proprietary optical-instrument identity.
- Motion remains slow and bounded and respects reduced-motion preferences.
- The mark is designed to remain legible at sidebar scale rather than relying on large decorative animation.

### Living surface

- The optical workplane was materially quieted so conversation content remains the dominant visual layer.
- Topographic isolines, drafting grid, optical focus, and warm calibration trace remain, but all are reduced toward the threshold of perception.
- Surface movement is slower and lower-frequency.
- A gentle center bias protects reading contrast behind the conversation stage.
- Response-state energy may influence the focus region without materially increasing full-screen contrast.

### Design system

- `DESIGN-SYSTEM.md` is now version 1.4.
- The durable visual rule is: **content wins every visual competition**.
- Parallax continues to reject generic AI-neon, generic SaaS-glass, orbital-logo, spinner, and decorative HUD conventions.
- The target remains high-end industrial design software + calm intelligence + optical instrumentation.

### Release identity

- `apps/client/package.json` now identifies the client as version `0.6.1`.
- Production deployment is now driven by GitHub `main`; development work remains on `p2/v0.6.0` and is preview-deployed until promoted by fast-forwarding the release lineage into `main`.

## Deployment workflow

The authoritative delivery path is now:

```text
p2/v0.6.0
    |
    | implementation commits
    v
Vercel Preview
    |
    | release accepted
    v
main (fast-forward only)
    |
    v
Vercel Production
    |
    v
production alias verification
```

Rules:

- Do not return to CLI-created production artifacts for normal releases.
- Do not force-update `main` for routine releases; production promotion should be a fast-forward from an accepted release lineage.
- A release is not called deployment-verified until the production deployment is `READY` and the production alias responds successfully.
- Preview success does not by itself mean production deployment.

## Architecture status

No durable architecture change was required for v0.6.1.

The established architecture remains:

- Expo + React Native + React Native Skia client.
- FastAPI + SQLAlchemy + DSPy service baseline.
- Durable server-side conversations as source of truth.
- Browser storage only for local draft/session convenience.
- Stored conversation specification identity remains durable and historical.
- Reason and Code protected-state contracts remain unchanged.
- `SPEC_AMENDMENT` remains a first-class protected hand-off state.

`ARCHITECTURE.md` therefore did not require a v0.6.1 change.

## Governance status

- `CURRENT-STATE.md`: updated for the verified v0.6.1 production release and recovered GitHub → Vercel delivery path.
- `DESIGN-SYSTEM.md`: updated because the durable visual restraint and Parallax mark rules changed.
- `ARCHITECTURE.md`: unchanged because application architecture did not materially change.
- `PROJECT-CONSTITUTION.md`: unchanged because governance principles did not materially change.

Prior v0.1–v0.5 implementation, evaluation, migration, and CI evidence remains preserved in repository history and release branches. This current-state record intentionally describes the presently deployed system rather than duplicating historical release narratives.
