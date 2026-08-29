# Parallax 2.0 Current State

Date: 2026-08-29

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / W8 IMPLEMENTATION COMPLETE WITH W8-S2 WAITING ON EXPLICIT GREENFIELD REPOSITORY PROVIDER CONSENT / W9-S1 CONTROLLED REFERENCE OBSERVATION COMPLETE WITH #406 REMEDIATION DEPLOYED AND PROVIDER CONSENT PENDING / W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production retains the deployment-verified W9-S1 real-world benchmark-admission layer, W9-S2 governed skill-intake/capability-catalog backend, agent-runnable QA authentication, Wave 8 guided experience, and earlier Waves 1–7 runtime/productization baseline.

Agent-runnable authenticated production QA is proven through the existing bounded QA identity and normal Parallax session/tenant boundaries. The W8-S2 canonical replay reaches the protected autonomous continuation without owner impersonation or an auth bypass.

The greenfield repository-authority remediation governed by `P2-V0.23.3` is now merged and production-deployment-verified. Missing GitHub App / Vercel Connect coverage for the canonical Project repository is classified as the explicit provider-consent state `REPOSITORY_AUTHORIZATION_REQUIRED` before source mutation. The remaining W8-S2 dependency is real provider authorization for `Ryan9876/sickbeard`; Parallax may not silently broaden that provider installation.

The first W9-S1 Decision Ledger reference trial remains a valid failed reference observation rather than a passing application benchmark. No target source was edited or seeded out of band, no authentication or provider authority was bypassed, and no production-promotion authority was introduced.

## Production components

### Client

Current deployment-verified client remains the QA-fallback release:

- application source: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- production deployment: `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`.

Normal `/` remains Google-first. `/?qa=1` exposes the bounded dedicated QA password/recovery path. The dedicated QA account is enrolled and agent-runnable GitHub Actions OIDC authentication maps to that same bounded QA principal without storing or exposing the QA password.

### API

Current deployment-verified production API:

- source: `0cfe499ac787a23142067e95e80af80dedab36c5`;
- deployment: `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`.

Production build evidence passed:

- provider scope and private Blob read/write preflight;
- exact repository delivery-token permission preflight;
- projected-source preflight;
- lineage composition;
- agentic runtime round trip;
- projected bootstrap and process-recreation/replay checks;
- execution-snapshot restore;
- run-event schema guard.

`P2-V0.23.3` separates provider installation coverage from runtime token scope. An explicitly authorized installation may cover multiple repositories, but every runtime exchange remains exact-one-repository scoped and independently verified. An out-of-coverage exact repository request now returns `REPOSITORY_AUTHORIZATION_REQUIRED`; timeouts, provider outages, malformed credentials and scope mismatches retain their separate fail-closed classifications.

## Wave 9 S1 — Real-world greenfield benchmark

Control Tower: #391

Workstream: #392

Governing benchmark specification: `P2-V0.23.0`

Benchmark-admission release:

- qualified worker head: `1d053823d08d8e5050e77c624dafcd09199fe942`;
- application release merge: `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- production API deployment: `dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`;
- release state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

Greenfield repository-authority remediation:

- finding: #406;
- governing remediation specification: `P2-V0.23.3`;
- qualified implementation head: `1cad61de06ce4d1da4aaec12f4f4da97d16b63a3`;
- application release merge: `0cfe499ac787a23142067e95e80af80dedab36c5`;
- production deployment: `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`;
- remediation state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED / PROVIDER CONSENT PENDING FOR CANONICAL GREENFIELD REPOSITORY**.

### Frozen benchmark

- template: `decision-ledger@1.0.0`;
- fixture digest: `15b098df3956ffe71833778e18a301a8e77fae9f37705223256703619f684900`;
- requirement tokens: exactly `DL-01` through `DL-12`;
- expected autonomous ceiling: `REVIEW`.

The frozen objective requires a responsive browser-persistent Decision Ledger with CRUD, required decision fields, Proposed/Accepted/Superseded semantics, search/filter/order, safe JSON import/export, recovery-oriented UX, 390px/1440px usability, accessibility, automated tests, repository safety, and governed Preview/REVIEW delivery.

### Controlled reference observation — COMPLETE

QA Actions run: `33231502080` — trial harness PASS.

Independent target: `Ryan9876/sickbeard`.

The workflow verified the repository had no refs before the trial began. It was not manually initialized or seeded.

Exact canonical evidence:

- Project: `7a1dd088-3b0d-4eec-90e8-3cf435eac3a4`;
- Conversation: `8dc3dbc2-6aab-4867-a399-4dfe5f903102`;
- approved Work Specification: `12d29840-6523-4470-a89b-9eb0ea6878eb`;
- Work Specification revision: `1`;
- Work Specification digest: `2772236584bbc1a841b4b5348d9f5d28626421e9d5d8c2aaaa04295675523c19`;
- canonical acceptance IDs: `AC-01` through `AC-06`;
- BenchmarkCase digest: `4cdd1e021e69a9191b74f1d8f4551e128802b7c61d70dd388499667e5c0e8fb6`;
- Engineering Run: `a3a32343-507a-4384-a9bd-2fddaa0ce7fc`;
- final observed state: `PLAN`, revision `1`;
- observed disposition: `AUTONOMOUS_REQUEST_FAILED_HTTP_503`;
- pre-approval clarifications: `0`;
- post-approval corrections: `0`;
- out-of-band source edits: `0`;
- trial start: `2026-08-29T03:29:18Z`;
- observed product boundary: `2026-08-29T03:29:41Z`.

The generated Build plan preserved every frozen `DL-01` through `DL-12` token exactly once. The approved canonical spec successfully bound through `bind_real_world_template(...)`; benchmark admission therefore passed before the runtime failure.

The first production observation failed with generic `CREDENTIAL_UNAVAILABLE`. Subsequent diagnosis and `P2-V0.23.3` proved the missing authority is repository coverage, not missing runtime identity or repository existence. `Ryan9876/sickbeard` exists and is owner-accessible; the approved Parallax Connect installation simply does not yet cover it.

Per the Wave 9 protocol, the gap is not fixed by broadening QA identity, embedding reusable credentials, bypassing Project-scoped provider authority, directly seeding target source, or weakening source-lineage / Preview / REVIEW boundaries.

**W9-S1 disposition:** the sprint's implementation, production verification, benchmark admission, first controlled real-world reference observation, and code-side least-privilege remediation are complete. The Decision Ledger application itself has not passed. Exact provider consent for the canonical greenfield repository is still required before the implementation trial can continue.

## Wave 9 S2 — Governed skill intake and capability catalog

Control Tower: #391

Workstream: #395

Governing specification: `P2-V0.23.1`

Release:

- qualified worker head: `0965969da3224ebe62e8a33348440b5753e76d6e`;
- application release merge: `fcb6abf4f794e038bcf48daac8d3400f006a18d8`;
- production API deployment: `dpl_57xiHUKBm3qK4HAA47kYzc9mJM13`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

S2 remains non-executing capability intake. External observations are quarantined metadata until exact approval and existing registry admission succeed. The release does not grant discovered content package-install, MCP-startup, generic shell/network, provider/tool-authority, merge, deployment, or REVIEW authority.

## Wave 8 remaining state

W8-S1, W8-S3 and W8-S4 remain deployment-verified. W8-S2 remains open.

PR #409 merged as `4a295adccb9d8224813bbacdeaec56de24a6a3f8`; shared QA Actions run `33232396195` proves the bounded production QA session can read QA-owned Engineering Run `a3a32343-507a-4384-a9bd-2fddaa0ce7fc` at PLAN revision 1 through ordinary protected APIs.

After `P2-V0.23.3` reached production as `dpl_4LAkdawZteqrAX34pmGAtLMvVq9V`, the same workflow was rerun. Authentication and canonical read passed again. The protected autonomous continuation reached Vercel Connect and returned HTTP 422 with the precise production classification:

`source_bootstrap_failed stage=provider-repository error_class=ProviderActionFailed result_code=REPOSITORY_AUTHORIZATION_REQUIRED`

This is the intended fail-closed behavior. The canonical Project repository is outside the currently approved provider installation; no source mutation occurred and the run remains PLAN revision 1.

W8-S2 must not close until the repository owner explicitly authorizes `Ryan9876/sickbeard` for the Parallax GitHub App / Vercel Connect installation and the same QA-authenticated replay durably advances beyond PLAN without a source-bootstrap failure caused by static Vercel target registration or missing GitHub repository authority.

## Other open governed work

- #406 — code-side repository-authority remediation is deployment-verified; exact provider consent and successful canonical replay remain before closure;
- #377 — W8-S2 authenticated production acceptance remains open pending that same consent/replay;
- #290 — safe deletion final authenticated destructive smoke.

## Authoritative-record update

`CURRENT-STATE.md` was updated after `P2-V0.23.3` production deployment and authenticated canonical replay. It now distinguishes implementation/deployment success from the still-pending provider-consent action.

`ARCHITECTURE.md` was advanced to v3.16 because `P2-V0.23.3` establishes a durable separation between installation-level repository coverage and exact-one-repository runtime credential scope, plus a new explicit repository-authorization readiness state.

`DESIGN-SYSTEM.md` was not changed because no new provider-consent UI has been released. `PROJECT-CONSTITUTION.md` was not changed because the architecture implements existing explicit-consent and least-privilege principles rather than adding a new constitutional rule.