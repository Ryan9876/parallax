# Parallax 2.0 Current State

Version: 0.6.2 release candidate
Date: 2026-08-21
Status: DEVELOPMENT CANDIDATE — NOT YET PROMOTED TO PRODUCTION
Active development branch: `p2/v0.6.2`
Production branch: `main`
Current candidate head before this record update: `3437abd92c7a158767135609f863c70dfabca579`

## Production baseline

The deployed product remains the previously verified v0.6.1 frontend baseline, with the subsequent production API authentication/OpenAPI fixes on `main` validated separately.

Verified production API evidence already established during the v0.6.2 preparation work:

- API root responds successfully.
- `/health` returns HTTP 200.
- `/ready` returns HTTP 200 with the database dependency ready.
- Swagger/OpenAPI exposes the standard Bearer authorization scheme.
- an authenticated `POST /v1/conversations` returned HTTP 200.

These checks do not imply that the v0.6.2 browser-session release candidate has been promoted. Production promotion remains a separate release event.

## v0.6.2 candidate

The active candidate adds the production-safe browser access boundary without exposing the root API credential in persistent browser storage:

- short-lived signed `HttpOnly` browser session derived from the existing private access secret;
- bearer compatibility retained for Swagger, automation, and non-browser clients;
- custom session marker required for cookie-authenticated protected requests;
- deployed browser API traffic routed through same-origin `/p2-api`;
- production cookie hardened as Secure + HttpOnly + host-only + SameSite=Lax;
- session establish/status/logout endpoints;
- browser credential removed from local/session storage persistence;
- existing Reason, Code, SSE, Skia, reduced-graphics, and durable conversation behavior preserved.

Latest preview evidence for candidate commit `3437abd92c7a158767135609f863c70dfabca579`:

- GitHub fast API + contract checks: **PASS**.
- GitHub fast client typecheck/state/export checks: **PASS**.
- protected promotion evaluation: intentionally **SKIPPED for draft development**.
- DSPy release compilation: intentionally **SKIPPED for draft development**.
- Vercel web preview `dpl_BLgCbzb36F7pcYufzUDwrpW5xWSg`: **READY**.
- Vercel API preview `dpl_GZrVF6xRxedCUB9CUt3j1MsWdgRS`: **READY**.

The candidate is generated, committed, fast-validated, and preview-built. It is **not yet production deployed or deployment-verified**.

## Development and release validation workflow

The CI path was simplified because the previous development loop duplicated release-grade work on every small commit.

The authoritative workflow is now tiered:

```text
Draft development commit
    |
    | fast contract/API tests + client typecheck/state/export
    v
Vercel Preview
    |
    | pull request marked ready / release candidate
    v
Full release validation
    ├─ browser + Skia acceptance suite
    ├─ protected engineering/Reason/Code evaluation
    ├─ DSPy SpecCritic + SpecCompiler contract validation
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

Integrity controls were retained:

- all API tests and specification validation still run during normal development;
- client typecheck, response-state tests, and web export still run during normal development;
- expensive protected evaluation, DSPy compilation, Playwright/Skia browser acceptance, and audit evidence still run before release promotion and on `main`;
- superseded CI runs are cancelled so stale commits do not continue consuming time;
- the duplicate v0.6.2 workflow was removed, leaving one authoritative CI workflow;
- release checks remain required as a release decision and are not replaced by preview `READY` status.

## Vercel build efficiency

Both authoritative Vercel project configurations now use an ignored-build command based on project-root Git changes.

- `parallax` builds when `apps/client` changes.
- `parallax-api` builds when `services/api` changes.
- repository-only documentation, CI, or unrelated changes can therefore be skipped by unaffected Vercel projects.

This preserves the two-project production topology while eliminating unnecessary cross-project preview builds.

## Deployment state vocabulary

For the v0.6.2 candidate:

- Generated: **YES**
- Committed/pushed: **YES**
- Fast development validation: **YES**
- Vercel preview build ready: **YES**
- Full release validation at current record head: **NOT YET CLAIMED**
- Deployed to production: **NO**
- Deployment verified: **NO**

## Governance status

- `CURRENT-STATE.md`: updated because the active candidate state and validated delivery process materially changed.
- `ARCHITECTURE.md`: unchanged; the application/runtime architecture and two-project deployment topology did not change.
- `DESIGN-SYSTEM.md`: unchanged; no durable visual-language rule changed.
- `PROJECT-CONSTITUTION.md`: unchanged; governance principles did not change.

Historical v0.1–v0.6.1 implementation and deployment evidence remains preserved in repository history. This file describes the presently deployed baseline and the active release candidate without treating preview or generated work as production.