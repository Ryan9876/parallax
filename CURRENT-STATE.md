# Parallax 2.0 Current State

Date: 2026-08-29

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / PRODUCTION PYTHON SOURCE-ONLY FULL EXPERIENCE ACCEPTED / W8 IMPLEMENTATION COMPLETE WITH W8-S2 .NET TOOLCHAIN ACCEPTANCE OPEN / W9-S1 CONTROLLED REFERENCE OBSERVATION COMPLETE WITH GREENFIELD PROVIDER CONSENT STILL OPEN / W9-S2 API PRODUCTION-DEPLOYMENT-VERIFIED / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production now has a verified end-to-end source-only engineering path for an ordinary source-backed Python Project. The production acceptance run established the normal QA session, selected the canonical Project, created a conversation, submitted the user objective, generated and approved the Work Specification, activated the Engineering Run, bootstrapped public GitHub source without anonymous GitHub REST quota dependency, completed PLAN, IMPLEMENT, BUILD, TEST and VERIFY, reached REVIEW with no failure, and returned a verified authenticated ZIP of the accepted source lineage.

This proof used the existing least-privilege QA identity and the deployed production API. It did not widen the GitHub Actions OIDC allowlist, publish source, create a provider deployment, bypass REVIEW, impersonate the owner, or introduce production-promotion authority.

The public-source bootstrap correction governed by Architecture v3.19 is production-deployment-verified. Normal public source reads use Git smart HTTP plus an exact commit-addressed GitHub codeload archive instead of unauthenticated `api.github.com` REST reads. The prior shared anonymous REST rate-limit failure is therefore no longer the public-source bootstrap blocker.

The successful Python acceptance does not close the separate W8-S2 .NET validation gap. The OT Time replay reaches the released repository-aware `dotnet-v1` validation path and fails closed at the server-pinned sandbox dependency PREPARE boundary because the admitted .NET toolchain is not present in that execution image. It also does not satisfy the separate W9-S1 greenfield-empty-repository provider-consent requirement, because initializing source where no public commit exists still requires explicit repository authority.

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

- source: `66fbc1e058bcbc6d7ac5422e23b20f1dabff1166`;
- deployment: `dpl_DxSnt542y3NpvfC3ce43wgazVKiW`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- state: `READY`;
- canonical production alias: `parallax-api-tan.vercel.app`.

Vercel deployment metadata binds `dpl_DxSnt542y3NpvfC3ce43wgazVKiW` to exact GitHub commit `66fbc1e058bcbc6d7ac5422e23b20f1dabff1166` with commit message `Remove anonymous GitHub REST quota from public source bootstrap`.

Production retains the deployment-verified W9-S1 benchmark-admission layer, W9-S2 governed skill-intake/capability-catalog backend, P2-V0.23.5 repository-aware protected validation policy, agent-runnable QA authentication, Wave 8 guided experience, source-only delivery policy, immutable source lineage, and earlier Waves 1–7 runtime/productization baseline.

Later `main` commits through `5490daf0ef11401348256eca4c5314e615a3b8ae` are QA-harness-only corrections for the production replay. They do not represent a newer API deployment and must not be recorded as deployed runtime source.

## Production Python source-only full experience — ACCEPTED

Acceptance target: `github:Ryan9876/Movies`.

Authorized QA workflow: `.github/workflows/qa-production-replay.yml`.

Final workflow run: `33277189927`.

Final workflow job: `99165862378` / `python-full-experience` — **SUCCESS**.

Exact production evidence:

- Project: `d00e23cb-6d84-4805-bf15-4f738d920136`;
- Engineering Run: `e9a1772f-88b3-450c-b619-8008de8c9576`;
- final state: `REVIEW`;
- final revision: `6`;
- `last_failure_code`: `null`;
- stop reason: `REVIEW_REQUIRED`;
- executor: `python` — PASSED;
- PLAN — PASSED;
- IMPLEMENT — PASSED using `safe-source-implementation-v1`;
- BUILD — PASSED;
- TEST — PASSED;
- VERIFY — PASSED;
- source ZIP: verified;
- ZIP entries: `7`;
- ZIP bytes: `1406`;
- required generated acceptance file: `PARALLAX_QA_PYTHON.md` present;
- source publication: `false`;
- application deployment: `false`.

The workflow output concluded:

`Python full-experience acceptance completed: project=d00e23cb-6d84-4805-bf15-4f738d920136; run=e9a1772f-88b3-450c-b619-8008de8c9576; state=REVIEW; source_publication=false; app_deployment=false`

This is the first clean production proof in this acceptance sequence that a small source-backed application request can traverse the complete protected engineering lifecycle and produce the authenticated source-only handoff without relying on Vercel as an application-delivery dependency.

### Acceptance-harness corrections validated during the run

The production acceptance sequence also removed several false-red test conditions without weakening product controls:

- public GitHub source bootstrap no longer consumes shared anonymous GitHub REST quota;
- the clean Python acceptance uses the purpose-built `Ryan9876/Movies` fixture instead of a legacy Project with incompatible delivery policy;
- the existing QA OIDC workflow allowlist remains unchanged; an unapproved duplicate workflow correctly received HTTP 401 and was removed rather than allowlisted;
- Project creation uses a collision-safe run-scoped slug when the target repository does not already have a QA Project;
- automatic acceptance runs only the clean Python job; W9 greenfield and OT Time diagnostics remain manual so unrelated known preconditions do not obscure the Python acceptance result;
- the harness uses the canonical source-only handoff route `/v1/projects/{project_id}/engineering-runs/{run_id}/source-download`.

The preceding run `33276894175` had already proved PLAN through VERIFY and REVIEW successfully; its only failure was the harness calling an obsolete download path. The final run `33277189927` closed that last verification gap.

## Public source bootstrap — DEPLOYMENT-VERIFIED

Architecture v3.19 separates public source authority from deployment-provider authority.

For a public GitHub repository with a commit-bearing default branch, production now:

1. resolves canonical HEAD/default-branch identity through unauthenticated Git smart HTTP;
2. pins the immutable commit;
3. reads source from the exact commit-addressed GitHub codeload archive;
4. applies bounded archive, path, file-type, size and UTF-8 validation;
5. exposes read-only repository/source capability only;
6. does not silently construct a Vercel-backed credential path if the public transport is throttled or unavailable.

The normal public path does not require `api.github.com`, Vercel Connect, a Vercel Project, or a Vercel Preview target. Private or otherwise non-public source remains fail-closed behind exact repository authority.

Release evidence:

- architecture: `ARCHITECTURE.md` v3.19;
- application release merge: `66fbc1e058bcbc6d7ac5422e23b20f1dabff1166`;
- production API deployment: `dpl_DxSnt542y3NpvfC3ce43wgazVKiW`;
- deployment state: `READY`;
- clean production Python acceptance: workflow `33277189927` — PASS.

## Wave 9 S1 — Real-world greenfield benchmark

Control Tower: #391

Workstream: #392

Governing benchmark specification: `P2-V0.23.0`.

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
- remediation state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

### Frozen benchmark

- template: `decision-ledger@1.0.0`;
- fixture digest: `15b098df3956ffe71833778e18a301a8e77fae9f37705223256703619f684900`;
- requirement tokens: exactly `DL-01` through `DL-12`;
- expected autonomous ceiling: `REVIEW`.

The frozen objective requires a responsive browser-persistent Decision Ledger with CRUD, required decision fields, Proposed/Accepted/Superseded semantics, search/filter/order, safe JSON import/export, recovery-oriented UX, 390px/1440px usability, accessibility, automated tests, repository safety, and governed Preview/REVIEW delivery.

### Controlled reference observation — COMPLETE

QA Actions run: `33231502080` — trial harness PASS.

Independent target: `Ryan9876/sickbeard`.

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
- out-of-band source edits: `0`.

The generated Build plan preserved every frozen `DL-01` through `DL-12` token exactly once and benchmark admission passed before the runtime failure.

The original empty-repository observation remains a valid failed reference observation rather than a passing application benchmark. No target source was edited or seeded out of band. Architecture v3.19 removes provider consent from ordinary public commit-bearing source reads, but it does not manufacture an initial commit in an empty greenfield repository. Explicit provider repository authority remains required for that greenfield initialization boundary.

**W9-S1 disposition:** implementation, production verification, benchmark admission, first controlled real-world reference observation and code-side least-privilege remediation are complete. The Decision Ledger application itself has not passed. Exact provider consent or another governed greenfield-initialization mechanism is still required before the canonical empty-repository implementation trial can continue.

## Wave 9 S2 — Governed skill intake and capability catalog

Control Tower: #391

Workstream: #395

Governing specification: `P2-V0.23.1`.

Release:

- qualified worker head: `0965969da3224ebe62e8a33348440b5753e76d6e`;
- application release merge: `fcb6abf4f794e038bcf48daac8d3400f006a18d8`;
- production API deployment: `dpl_57xiHUKBm3qK4HAA47kYzc9mJM13`;
- state: **IMPLEMENTED / MAIN-MERGED / API PRODUCTION-DEPLOYMENT-VERIFIED**.

S2 remains non-executing capability intake. External observations are quarantined metadata until exact approval and existing registry admission succeed. The release does not grant discovered content package-install, MCP-startup, generic shell/network, provider/tool-authority, merge, deployment, or REVIEW authority.

## P2-V0.23.5 — Repository-aware protected validation toolchains

Workstream: #421.

Release:

- governing specification: `P2-V0.23.5`;
- production API source for the original release: `302a1fcbfabf32ef0955bde31f6c657ecc9d1e46`;
- production deployment for that release: `dpl_FWHw5rCwM3Bn5faMD4zhYPJ3pCNJ`;
- current production API also contains this capability through source `66fbc1e058bcbc6d7ac5422e23b20f1dabff1166` / deployment `dpl_DxSnt542y3NpvfC3ce43wgazVKiW`;
- state: **DEPLOYMENT-VERIFIED / PYTHON PATH ACCEPTED / OT TIME .NET ACCEPTANCE OPEN**.

The authentic QA replay against public `github:Ryan9876/ot-time` now gets past public source bootstrap and reaches the released `dotnet-v1` profile. It fails closed during the profile-owned PREPARE prerequisite with `DEPENDENCY_PREPARATION_FAILED`; the server-pinned sandbox does not currently provide the admitted .NET readiness needed for protected validation.

This establishes the remaining OT Time blocker as sandbox toolchain readiness, not GitHub anonymous REST quota, Project repository authorization, delivery mode, profile selection, or ungoverned command handling.

W8-S2 must not be closed on the basis of the Python acceptance alone if its governed acceptance requires the .NET OT Time target. The required next product-side correction is a server-owned execution snapshot/toolchain path that satisfies the existing admitted .NET PREPARE contract without widening package/network/runtime authority.

## Wave 8 remaining state

W8-S1, W8-S3 and W8-S4 remain deployment-verified. W8-S2 remains open specifically for the .NET protected-validation acceptance path.

The broader source-backed user experience is no longer unproven: production workflow `33277189927` demonstrates that the normal protected flow can create and approve work, perform source-aware autonomous engineering, reach REVIEW and return the accepted source ZIP for a small Python application fixture.

The OT Time replay is now a narrower toolchain-coverage issue rather than evidence that the overall autonomous experience is broken.

## Other open governed work

- #406 — code-side greenfield repository-authority remediation is deployment-verified; canonical empty-repository initialization still requires explicit authority before W9-S1 can pass;
- #377 — W8-S2 .NET authenticated production acceptance remains open on sandbox toolchain readiness;
- #290 — safe deletion final authenticated destructive smoke.

## Authoritative-record update

`CURRENT-STATE.md` was updated after the successful production Python source-only full-experience acceptance. It now records exact workflow, Project, Engineering Run, lifecycle-stage and ZIP-handoff evidence and distinguishes the accepted Python path from the still-open .NET and greenfield-specific boundaries.

`ARCHITECTURE.md` remains authoritative at v3.19. It already records the durable public-source bootstrap, source/deployment separation, source-only Project policy and authenticated source-handoff contracts proven by this acceptance; no additional architecture revision is required.

`DESIGN-SYSTEM.md` was not changed because this work did not alter durable visual or interaction-system rules.

`PROJECT-CONSTITUTION.md` was not changed because this validation exercised existing least-privilege, explicit-authority, immutable-lineage and REVIEW-ceiling principles rather than introducing a new constitutional rule.
