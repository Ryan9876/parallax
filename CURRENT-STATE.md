# Parallax 2.0 Current State

Date: 2026-08-29

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / W8 IMPLEMENTATION COMPLETE WITH W8-S2 REPLAY STILL OPEN / W9-S1 CONTROLLED REFERENCE OBSERVATION COMPLETE WITH PRODUCT GAP #406 / W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production retains the deployment-verified W9-S1 real-world benchmark-admission layer, W9-S2 governed skill-intake/capability-catalog backend, QA authentication fallback, Wave 8 guided experience, and earlier Waves 1–7 runtime/productization baseline.

The first W9-S1 Decision Ledger reference trial has now been executed through a normal authenticated Project, ordinary product conversation, generated Build plan, explicit approval, Engineering Run activation, and the existing ParallaxBench real-world admission contract. The trial did **not** reach implementation or Preview: production source bootstrap failed at PLAN because the Engineering Runtime could not obtain the Project-scoped GitHub repository credential. That failure is the reference observation; it is not relabeled as a passing application benchmark.

No target source was edited or seeded out of band, no authentication or provider authority was bypassed, and no production-promotion authority was introduced.

## Production components

### Client

Current deployment-verified client remains the QA-fallback release:

- application source: `4f812bd2cd6a5939c3d39ede457c091bac7b6e0f`;
- production deployment: `dpl_CbuQzRDz3iJgF8rnqEpivmfmpQaM`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`.

Normal `/` remains Google-first. `/?qa=1` exposes the bounded dedicated QA password/recovery path. The dedicated QA account is now enrolled and has authenticated successfully; passwords and recovery/access tokens are not recorded here.

### API

The current deployment-verified API runtime includes the QA Actions OIDC session path introduced by PR #401 and the earlier W9-S1/W9-S2 application capabilities. The exact production deployment that first made bounded push-triggered QA automation usable was:

- source: `01bfe37bd3c264220b2af64da11cbaad0b5168ed`;
- deployment: `dpl_5Lx1qiPw4S6QJA1FqVtaqnpRf3u3`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`.

Later W9-S1 trial-harness commits changed repository workflow/script evidence rather than Parallax API application semantics; their automatic API deployments were canceled and are not recorded as deployed application releases.

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

This is a real W9 product finding: the authenticated user can create and approve a normal Project bound to a greenfield GitHub repository, but the production Engineering Runtime cannot currently obtain the Project-scoped repository credential required to bootstrap source for that new Project.

Finding: #406 — `[W9 FINDING] Greenfield source bootstrap lacks runtime GitHub credential`.

Per the Wave 9 protocol, this defect is recorded before implementation. It must not be fixed by broadening QA identity, embedding reusable credentials, bypassing Project-scoped provider authority, directly seeding target source, or weakening source-lineage / Preview / REVIEW boundaries. Any semantic fix requires a separately approved specification.

**W9-S1 disposition:** the sprint's implementation, production verification, benchmark admission, and first controlled real-world reference observation are complete. The Decision Ledger application itself did not pass; the observed PLAN bootstrap failure is now the reference evidence and follow-on product gap #406.

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

W8-S1, W8-S3 and W8-S4 remain deployment-verified. W8-S2 production infrastructure is present, but its historical OT Time replay remains open independently of W9.

The bounded QA Actions session now authenticates successfully. Replay run `33231400984` reached the QA session successfully but the historical OT Time Engineering Run lookup returned HTTP 404 under the QA identity, so the replay did not advance. W8-S2 remains open until that ownership/identity mismatch is diagnosed and the exact replay is completed or the governing workstream records a different valid resolution.

## Other open governed work

- #406 — W9 greenfield Project source-bootstrap credential gap;
- W8-S2 — historical OT Time authenticated replay;
- #290 — safe deletion final authenticated destructive smoke.

## Authoritative-record update

`CURRENT-STATE.md` was reconciled after the first controlled W9-S1 reference trial because the prior record still said the trial had not started and that QA enrollment was blocking automation. Those statements are now obsolete.

`ARCHITECTURE.md`, `DESIGN-SYSTEM.md`, and `PROJECT-CONSTITUTION.md` were not changed by this observation: the trial exposed an implementation/runtime capability gap but did not approve or deploy a durable architecture, design-system, or constitutional change.