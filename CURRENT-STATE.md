# Parallax 2.0 Current State

Version: 0.6.2
Date: 2026-08-21
Status: DEPLOYED AND DEPLOYMENT-VERIFIED
Production branch: `main`
Production application release commit: `441d69e7d619520824614a28ee0c3643ca7bdf08`
Production API release lineage: `670d1233bb36de39bb2e5d91fcb046d6dbedea6b`
Production web deployment: `dpl_7dqvxnkt35Dhyct5v3X4rBQkaCB4`
Production API deployment: `dpl_HctJQ7rWMmg5BVYh35wMYqvTwCCS`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`

## Current verified release

Parallax 2.0 v0.6.2 is live through the GitHub → Vercel production pipeline.

Release promotion occurred in two validated steps:

1. PR #6 promoted the v0.6.2 session-safe private-access release to `main` at `670d1233bb36de39bb2e5d91fcb046d6dbedea6b`.
2. Production verification exposed a web routing defect: `/p2-api/*` could fall through to the Expo SPA shell instead of reaching the API. PR #7 corrected the web proxy route and was promoted at `441d69e7d619520824614a28ee0c3643ca7bdf08`.

The corrective release did not change `services/api`, so the path-aware Vercel rule intentionally skipped a redundant API rebuild. The authoritative API deployment therefore remains the READY production deployment from the v0.6.2 promotion lineage.

## Verified production evidence

### Web

- Vercel production deployment `dpl_7dqvxnkt35Dhyct5v3X4rBQkaCB4` is `READY`.
- Deployment target is `production`.
- Production alias assignment completed without alias error.
- `https://parallax-ashy-one-20.vercel.app` serves the Parallax 2.0 Expo web application.
- `https://parallax-ashy-one-20.vercel.app/p2-api/health` returns HTTP 200 with Parallax API health JSON.
- `https://parallax-ashy-one-20.vercel.app/p2-api/ready` returns HTTP 200 with database readiness `ok`.
- `https://parallax-ashy-one-20.vercel.app/p2-api/v1/session` without credentials returns the expected HTTP 401 JSON response rather than the SPA shell, proving the same-origin proxy reaches the protected API boundary.

### API

- Vercel production deployment `dpl_HctJQ7rWMmg5BVYh35wMYqvTwCCS` is `READY`.
- Production aliases include `parallax-api-tan.vercel.app`.
- `/health` returns HTTP 200.
- `/ready` returns HTTP 200 with the database dependency ready.
- Bearer authentication remains active for protected endpoints.
- The standard Swagger/OpenAPI bearer authorization scheme was previously verified in production.
- A protected authenticated conversation creation request was previously verified with HTTP 200 on the production API lineage.

The new browser-session establishment flow was validated in automated release tests. A fresh authenticated browser-cookie round trip against production is **not separately claimed in this record**, because production secret material was not exposed to the deployment-verification tooling.

## v0.6.2 product and security changes

The release adds the production-safe browser access boundary without persisting the root API credential in browser storage:

- short-lived signed `HttpOnly` browser session derived from the existing private access secret;
- bearer compatibility retained for Swagger, automation, and non-browser clients;
- custom session marker required for cookie-authenticated protected requests;
- deployed browser API traffic routed through same-origin `/p2-api`;
- production cookie hardened as Secure + HttpOnly + host-only + SameSite=Lax;
- session establish/status/logout endpoints;
- browser credential removed from local/session storage persistence;
- existing Reason, Code, SSE, Skia, reduced-graphics, and durable conversation behavior preserved.

## Release validation

The full release-grade validation suite passed for the v0.6.2 release candidate and again for the one-file production proxy correction:

- specification validation: **PASS**;
- API compile/tests: **PASS**;
- client typecheck: **PASS**;
- response-state tests: **PASS**;
- web export: **PASS**;
- production dependency audit evidence: **PASS**;
- browser/Skia acceptance suite: **PASS**;
- protected Engineering/Reason/Code promotion evaluation: **PASS**;
- DSPy SpecCritic + SpecCompiler protected-contract validation: **PASS**;
- Vercel project status checks: **PASS**.

## Development and release validation workflow

The authoritative CI path is tiered so normal development remains fast while release integrity remains protected:

```text
Draft development commit
    |
    | spec/API tests + client typecheck/state/export
    v
Vercel Preview
    |
    | pull request marked ready / release candidate
    v
Full release validation
    ├─ browser + Skia acceptance suite
    ├─ protected Engineering/Reason/Code evaluation
    ├─ DSPy SpecCritic + SpecCompiler validation
    └─ production dependency audit evidence
    |
    v
main
    |
    v
Vercel Production
    |
    v
production verification
```

Integrity controls retained:

- API tests and specification validation run during normal development;
- client typecheck, response-state tests, and web export run during normal development;
- expensive protected evaluation, DSPy compilation, Playwright/Skia acceptance, and audit evidence run for release candidates and production promotion;
- superseded CI runs are cancelled;
- one authoritative CI workflow replaces the previous duplicate release workflow;
- Vercel READY state does not substitute for live production verification.

## Vercel build efficiency

Both authoritative Vercel projects use project-root Git change detection:

- `parallax` builds when `apps/client` changes;
- `parallax-api` builds when `services/api` changes;
- repository-only documentation, CI, or unrelated changes are skipped by unaffected projects.

This behavior was validated during the v0.6.2 release. The client-only proxy hotfix caused the API production deployment attempt to be intentionally skipped while the web project rebuilt and promoted normally.

## Deployment state vocabulary

For v0.6.2:

- Generated: **YES**
- Committed/pushed: **YES**
- Full release validation: **YES**
- Deployed to production: **YES**
- Production web deployment READY: **YES**
- Production API deployment READY: **YES**
- Production web/API proxy health verified: **YES**
- Production database readiness verified: **YES**
- Protected route reaches API/auth boundary through same-origin proxy: **YES**
- Fresh authenticated browser-cookie round trip in production: **NOT SEPARATELY CLAIMED**
- Deployment verified: **YES**, subject to the explicit authenticated-cookie caveat above.

## Governance status

- `CURRENT-STATE.md`: updated for the verified v0.6.2 production release, the production proxy correction, release evidence, and the validated efficient CI/Vercel workflow.
- `ARCHITECTURE.md`: unchanged; the session-safe same-origin proxy architecture was already established by the v0.6.2 release work and no additional durable architecture change was introduced by the corrective routing fix.
- `DESIGN-SYSTEM.md`: unchanged; no durable visual-language rule changed.
- `PROJECT-CONSTITUTION.md`: unchanged; governance principles did not materially change.

Historical v0.1–v0.6.1 implementation and deployment evidence remains preserved in repository history.