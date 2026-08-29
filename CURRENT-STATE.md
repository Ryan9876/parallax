# Parallax 2.0 Current State

Date: 2026-08-29

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / W8 IMPLEMENTATION COMPLETE WITH W8-S2 BLOCKED BY GREENFIELD GITHUB SOURCE AUTHORITY #406 / W9-S1 CONTROLLED REFERENCE OBSERVATION COMPLETE WITH PRODUCT GAP #406 / W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production retains the deployment-verified W9-S1 real-world benchmark-admission layer, W9-S2 governed skill-intake/capability-catalog backend, agent-runnable QA authentication, Wave 8 guided experience, and earlier Waves 1–7 runtime/productization baseline.

Agent-runnable authenticated production QA is now proven through the existing bounded QA identity and normal Parallax session/tenant boundaries. The W8-S2 canonical replay reached the protected autonomous continuation without owner impersonation or an auth bypass, but did not advance beyond PLAN because greenfield GitHub source authority remains unavailable for repositories outside the statically registered Parallax connector scope.

The first W9-S1 Decision Ledger reference trial has now been executed through a normal authenticated Project, ordinary product conversation, generated Build plan, explicit approval, Engineering Run activation, and the existing ParallaxBench real-world admission contract. The trial did **not** reach implementation or Preview: production source bootstrap failed at PLAN because the Engineering Runtime could not obtain the Project-scoped GitHub repository credential. That failure is the reference observation; it is not relabeled as a passing application benchmark.

No target source was edited or seeded out of band, no authentication or provider authority was bypassed, and no production-promotion authority was introduced.

## Production components

### Client

Current deployment-verified client remains the QA-fallback release:

- application source: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- production deployment: `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`.

Normal `/` remains Google-first. `/?qa=1` exposes the bounded dedicated QA password/recovery path. The dedicated QA account is enrolled and agent-runnable GitHub Actions OIDC authentication now maps to that same bounded QA principal without storing or exposing the QA password.

### API

Current deployment-verified production API:

- source: `e9c931518d2b378952024ba0105ca638559244d2`;
- deployment: `dpl_FPWh6qSvxWhWbDd7Cmpo2XHoe9mw`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`.

This release includes the bounded QA Actions OIDC session path and runtime Vercel OIDC resolution. Production build preflights pass provider scope, delivery permission, projected source, lineage, agentic runtime, projected bootstrap, execution snapshot, and run-event schema checks for the statically registered Parallax repository target.

The runtime still cannot exchange source authority for a greenfield Project repository outside that registered connector scope. For the QA-owned `Ryan9876/sickbeard` canonical run, Vercel Connect returns HTTP 422 and Parallax records `CREDENTIAL_UNAVAILABLE`.

## Wave 9 S1 — Real-world greenfield benchmark

Control Tower: #391

Workstream: #392

Governing specification: `P2-V0.23.0`

Benchmark-admission release:

- qualified worker head: `1d053823d08d8e5050e77c624dafcd09199fe942`;
- application release merge: `ee6af25d09c495f2550f39a7d7f90f527dc7e447`;
- production API deployment: `dpl_9fWd2fZLsfXyexSC8hohvS9X5iDa`;
- release state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

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

The Engineering Run completed its SPECIFY evidence and entered PLAN. The first autonomous continuation returned HTTP 503. Production runtime evidence recorded:

`source_bootstrap_failed stage=provider-repository error_class=ProviderActionFailed result_code=CREDENTIAL_UNAVAILABLE`

Finding: #406 — `[W9 FINDING] Greenfield source bootstrap lacks runtime GitHub credential`.

Subsequent production diagnosis proved runtime Vercel OIDC is present and usable for the registered Parallax repository during production preflight. The remaining gap is repository authority: `github/parallax-runtime` is statically scoped to its registered repository while a normal greenfield Project may bind a different repository such as `Ryan9876/sickbeard`. The connector correctly rejects that out-of-scope token request.

Per the Wave 9 protocol, this defect must not be fixed by broadening QA identity, embedding reusable credentials, bypassing Project-scoped provider authority, directly seeding target source, or weakening source-lineage / Preview / REVIEW boundaries. Any semantic fix requires a separately approved specification.

**W9-S1 disposition:** the sprint's implementation, production verification, benchmark admission, and first controlled real-world reference observation are complete. The Decision Ledger application itself did not pass; the observed PLAN bootstrap failure is reference evidence and follow-on product gap #406.

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

Agent-runnable QA authentication is no longer the blocker. PR #409 merged as `4a295adccb9d8224813bbacdeaec56de24a6a3f8`; QA Actions run `33232396195` successfully established the bounded production QA session and read QA-owned Engineering Run `a3a32343-507a-4384-a9bd-2fddaa0ce7fc` at PLAN revision 1 through ordinary protected APIs.

The canonical replay then returned HTTP 503. On current production API deployment `dpl_FPWh6qSvxWhWbDd7Cmpo2XHoe9mw`, runtime evidence shows Vercel Connect `POST /v1/connect/token/github%2Fparallax-runtime` returning HTTP 422 and Parallax recording:

`source_bootstrap_failed stage=provider-repository error_class=ProviderActionFailed result_code=CREDENTIAL_UNAVAILABLE`

This is not the historical missing-static-Vercel-target failure. It is the greenfield GitHub source-authority gap tracked by #406: the canonical QA Project is bound to `github:ryan9876/sickbeard`, while the existing Connect installation is scoped to the registered Parallax repository. W8-S2 therefore remains blocked by #406 and must not be closed until a governed least-privilege repository-authority solution is deployed and the same authenticated replay durably advances beyond PLAN without `source_bootstrap_failed`.

## Other open governed work

- #406 — greenfield Project GitHub source-authority gap; blocks W8-S2 canonical acceptance and the next W9-S1 implementation trial;
- #377 — W8-S2 authenticated production acceptance remains open pending #406;
- #290 — safe deletion final authenticated destructive smoke.

## Authoritative-record update

`CURRENT-STATE.md` was reconciled after the authenticated W8-S2 canonical replay and current production runtime diagnosis. The prior record said W8-S2 was waiting on an ownership/identity replay resolution; that is obsolete. QA authentication and tenant isolation are now proven, and the remaining blocker is exact greenfield repository source authority under #406.

`ARCHITECTURE.md`, `DESIGN-SYSTEM.md`, and `PROJECT-CONSTITUTION.md` were not changed by this observation. No new durable repository-authority architecture has been approved or deployed yet; the observation narrows an implementation/runtime capability gap rather than establishing a new architecture, design-system rule, or constitutional rule.