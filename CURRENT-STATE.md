# Parallax 2.0 Current State

Release: Wave 5 generalized application delivery remains the production platform baseline, with production stabilization hotfixes #246, #244, #245, and #252 deployment-verified on top of Wave 5. Current application/runtime identity is `main@5ec7eabc046b9995c8d11d5081df15b986a558fe`; production API `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q` and production client `dpl_DwjTqyD5BZSGf6XAexZzg42enBQf` are READY on that exact merge SHA. Hotfix #246 operator functional retest passed. Work Specification capture now reports all-route provider rate limiting as an explicit retryable capacity state; this does not claim that external OpenAI API capacity itself has recovered.
Date: 2026-08-26
Status: **WAVE 5 RELEASED / HOTFIXES #246 #244 #245 #252 DEPLOYMENT-VERIFIED / API READY / CLIENT READY / #246 OPERATOR RETEST PASSED / WORK-SPEC RATE-LIMIT RECOVERY EXPLICIT / HUMAN REVIEW BOUNDARY PRESERVED / ROLLBACK AVAILABLE / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Production stabilization hotfixes #244, #245 and #252 — deployment-verified

Production acceptance testing after Wave 5 produced three bounded stabilization corrections in addition to #246. Hotfix #244 restored canonical repository-target enforcement before execution; hotfix #245 restored truthful durable IMPLEMENT-failure projection and Live Build fallback; hotfix #252 distinguishes provider rate-limit exhaustion during Work Specification capture from protected-output validation or mixed provider failure.

For #244, exact candidate `40f8bc25fcfad6c725a666cf236c6ffda2402991` passed Workstream Spec Validation #357 (`32922601423`), Bounded Autonomy #563 (`32922601392`) and P2 CI #924 (`32922601357`), then PR #250 merged as `e818bc9f44e473195a1bfd7f82b3c0cb3abf7e42`. Production API `dpl_4udtw3EkTTqZH1nPbqJuGYbcjG81` reached READY on that exact merge SHA. The selected Project repository is rechecked at Work Specification approval and Engineering Run activation; no repository auto-switching or authority broadening was introduced.

For #245, exact candidate `7aebfb65d46df57ed38031d3e213a27dc9fe6303` passed Bounded Autonomy #564 and P2 CI #926, including full API regression, client typecheck/state/export, browser/Skia sparse FAILED/IMPLEMENT fallback, protected promotion/regression evaluation and release DSPy compilation. PR #251 merged as `464aa9f106348638cfd436aa427398edbd3e1583`. Production API `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` and client `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm` reached READY on that exact merge SHA. Sanitized pre-mutation failed IMPLEMENT attempts now project append-only failure evidence, and Live Build falls back to authoritative FAILED/resume-stage state without fabricating worker/source/provider/preview/evaluation success.

For #252, the operator's correctly bound `OT Time` Project reached Work Specification capture after #246, then all configured OpenAI routes returned sanitized `LMRateLimitError`. No Work Specification or Engineering Run was fabricated. Exact candidate `a9c5a6c941c596081202b3bc4dfa8f4d8fefb4d3` passed Workstream Spec Validation #359 (`32925099941`), Bounded Autonomy #565 (`32925099955`), P2 CI #928 (`32925099930`), full API regression, client typecheck/state/export, browser/Skia acceptance, protected promotion/regression evaluation, release DSPy compilation, and both Vercel preview checks. Expected-head PR #253 merged as `5ec7eabc046b9995c8d11d5081df15b986a558fe`.

Current production API `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q` and client `dpl_DwjTqyD5BZSGf6XAexZzg42enBQf` are READY on exact merge SHA `5ec7eabc046b9995c8d11d5081df15b986a558fe`, with `aliasError=null`. API provider/delivery/projected-source/Blob/lineage/bootstrap/execution-snapshot/run-event-schema preflights passed; `/health` and `/ready` return HTTP 200; unauthenticated `/v1/projects` remains HTTP 401 with Bearer challenge; the client root returns HTTP 200; and recent API/client runtime-error scans are empty.

#252 classifies only from sanitized bounded route attempts: all-route `LMRateLimitError` exhaustion returns HTTP 429 with explicit retry semantics while preserving `SPEC · NOT CAPTURED`; validation-only and mixed/other failures remain distinct. No `Retry-After` duration is invented, no deterministic Work Specification fallback exists, and no provider/model/model-family/credential or execution/deployment authority changed. This corrects application recovery/reporting and does not assert that external OpenAI API capacity has recovered.

The immediate rollback pair is #245: API `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` and client `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm`, both READY.

## Production stabilization hotfix #246 — deployment-verified / operator retest passed

Operator acceptance testing against a newly created `OT Time` Project bound to `github:ryan9876/ot-time` exposed a production workflow defect before Work Specification capture. A fresh Code objective (`Add an about page`) unnecessarily entered the model-backed protected scope/response plane even though there was no prior approved objective to compare against; that route exhausted after bounded provider/model attempts. A subsequent `Capture Spec` attempt independently exhausted Work Specification generation and returned HTTP 503. No Work Specification or Engineering Run was fabricated.

Issue #246 / PR #247 corrected the first failure boundary without broadening authority:

- a fresh ACTIVE Code conversation with no prior durable user objective now persists its first objective exactly once and hands off deterministically to Work Specification capture instead of invoking model-backed scope/reason inference;
- Reason mode and established Code follow-ups continue to use protected scope classification;
- Work Specification generation, explicit approval, canonical Project/repository binding, Engineering Run activation, source mutation, REVIEW/HUMAN_REQUIRED, provider and deployment boundaries are unchanged;
- model-router diagnostics now record only bounded operational fields needed to distinguish provider failure from protected-output validation failure; prompts, response text, credentials, secrets and chain-of-thought remain excluded.

Exact hotfix head `7eaa290fd57a2a333976ed882f29075f9d022e3f` passed Workstream Spec Validation #352 (`32921051668`), Bounded Autonomy #554 (`32921051600`), P2 CI #913 (`32921051574`), API/contract regression, client typecheck/state/export/browser-Skia, protected Code/Engineering/Reason promotion and regression rejection, release DSPy compilation/verification, and both Vercel checks before expected-head PR #247 merged to `main` as `36548611c3806d08d6fbfcdb686fe2a025956194`.

Production deployment verification established:

- API deployment `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB` is `READY`, target `production`, exact Git SHA `36548611c3806d08d6fbfcdb686fe2a025956194`, with `aliasError=null` and production aliases including `parallax-api-tan.vercel.app`;
- the build passed registered-provider/source-tree/private-Blob, exact repository delivery-permission, projected-source, immutable Blob get/put/get, lineage composition/rollback, projected bootstrap/runtime/process-recreation/replay/no-stage-mutation/project-rollback, execution-snapshot/deny-all/offline-dependency/no-repository-source and run-event schema preflights;
- `/health` returned HTTP 200 with `status=ok`;
- `/ready` returned HTTP 200 with `status=ready`, `database=ok`, `providers=ok`, and one registered provider target;
- unauthenticated `/v1/projects` returned HTTP 401 with the Bearer challenge;
- deployment-scoped `error`/`fatal` runtime logs returned no entries after cutover.

The hotfix changes API runtime behavior only; the production client remains `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn`. Immediate rollback for the API was the prior deployment-verified Wave 5 API `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc` at the time of promotion. Issue #246 is closed after the operator repeated the original fresh `OT Time` Code-objective flow in production: conversation `085bb6e7-ba2a-4770-b08e-e25618350534` persisted `Create an about page` exactly once, returned the deterministic Work Specification handoff, and reached `SPEC · NOT CAPTURED` without `PROTECTED_SCOPE_FAILURE`. The subsequent Work Specification capture failure was separately classified and corrected under #252.

This stabilization does not change durable constitutional authority, visual language, generalized application architecture, schema, production configuration, credentials, provider scope or deployment authority. `PROJECT-CONSTITUTION.md`, `ARCHITECTURE.md` v3.1 and `DESIGN-SYSTEM.md` therefore remain unchanged.

## Wave 5 production release and deployment verification

Control Tower #215 accepted and serialized all six Wave 5 workstreams through S6 #221. Expected-head S6 integration produced cumulative code head `14961d06d5e3b1c83f9d45c94bcc0727a2ec115a`, which passed Workstream Spec Validation #346 (`32916448744`), Bounded Autonomy #548 (`32916448731`), P2 CI #905 (`32916448734`) and the applicable Vercel Preview checks. Authoritative record synchronization then produced final release candidate `2fb01805ba612228d116ca4c4d8d0980d7886007`; that exact head passed Workstream Spec Validation #350 (`32916927549`), Bounded Autonomy #552 (`32916927563`), P2 CI #909 (`32916927597`), full API regression, browser/Skia acceptance, protected Code/Engineering/Reason promotion evaluation and regression rejection, release DSPy compilation/plan verification, and both Vercel release checks.

Expected-head PR #241 merged the validated release candidate to `main` as `c39b5352be940f4052baa65c7cdd9d7c3ec773bb`. The release diff contains the Wave 5 repository-intelligence, governed-skill, service-binding, objective-orchestration, validated-memory, generalization-proof, tests/specs/benchmark, and authoritative-record changes only. It contains no database migration, production environment/configuration change, credential change, provider-authority mutation or client-runtime change.

Production deployment verification on 2026-08-25 established:

- Vercel API deployment `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc` is `READY`, target `production`, bound to exact Git SHA `c39b5352be940f4052baa65c7cdd9d7c3ec773bb`, with `aliasError=null` and aliases `parallax-api-tan.vercel.app`, `parallax-api-lew7.vercel.app`, and `parallax-api-git-main-lew7.vercel.app`.
- the production API build passed provider registration/source-tree/private-Blob verification, exact repository delivery-permission verification, projected-source validation, private immutable Blob get/put/get, lineage composition plus metadata rollback, projected bootstrap plus process recreation/replay/no-stage-mutation/project rollback, execution-snapshot deny-all/offline-dependency verification, and the Wave 4 run-event schema guard;
- `https://parallax-api-tan.vercel.app/health` returned HTTP 200 with `status=ok`;
- `https://parallax-api-tan.vercel.app/ready` returned HTTP 200 with `status=ready`, `database=ok`, `providers=ok`, and exactly one registered provider target;
- unauthenticated `https://parallax-api-tan.vercel.app/v1/projects` returned HTTP 401 with `Authentication required` and a Bearer challenge;
- the project-level runtime-error query for the post-cutover hour returned no runtime errors, and deployment-scoped `error`/`fatal` logs returned no entries.
- Wave 5 contains no client-runtime change. Vercel therefore canceled/ignored the `main@c39b5352...` client production build as non-app-affecting, while deployment `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn` remains `READY`, `aliasError=null`, retains `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, and `parallax-git-main-lew7.vercel.app`, and the production alias returned HTTP 200 after the API cutover.

The integrated Wave 5 capability set is now production-released at the source/application boundary: deterministic repository compatibility evidence; exact-digest governed skills constrained by server-owned capabilities; Project-scoped logical service bindings with opaque secret slots; exact Project/run/Work Specification/repository-profile objective orchestration with fail-closed `HUMAN_REQUIRED`; provenance-bound private-by-default validated engineering memory with explicit sanitized sharing and unchanged fresh-validation requirements; and the permanent multi-shape generalization/reference proof. `REVIEW` / `HUMAN_REQUIRED` remains the autonomous ceiling, and no Wave 5 memory/skill/repository evidence surface can grant execution, provider, deployment or approval authority.

`ARCHITECTURE.md` v3.1 remains the durable architecture record for these contracts. `PROJECT-CONSTITUTION.md` and `DESIGN-SYSTEM.md` remain unchanged because Wave 5 did not change constitutional authority or the visual language.

## Current production truth

The deployment-verified current Parallax application/runtime identity is `main@5ec7eabc046b9995c8d11d5081df15b986a558fe`, layered on the Wave 5 generalized-delivery release and stabilization hotfixes #246, #244, #245 and #252.

The current production API is `dpl_7oaehRqtRnJmNa2Y4AzVkkez8Z1Q`: READY, target production, exact Git SHA `5ec7eabc046b9995c8d11d5081df15b986a558fe`, `aliasError=null`, with the canonical API aliases. Its production preflights passed; `/health` and `/ready` are HTTP 200; unauthenticated `/v1/projects` is HTTP 401 with Bearer challenge; and recent runtime-error scans are clean.

The current production client is `dpl_DwjTqyD5BZSGf6XAexZzg42enBQf`: READY on the same exact Git SHA, `aliasError=null`, with the canonical client aliases. The production root is HTTP 200 and recent client runtime-error scans are clean.

The immediate rollback pair is #245: API `dpl_7WkoYsKjrQ2tVkbzgNQyWAeVDmhn` and client `dpl_B58TT1qEK5MnMtXdxzJCdbLnL3Gm`, both READY on merge `464aa9f106348638cfd436aa427398edbd3e1583`. Earlier known-good API references include #244 `dpl_4udtw3EkTTqZH1nPbqJuGYbcjG81`, #246 `dpl_3FdvRJbf34KZfaL9mgE8eWJ6wZGB`, and Wave 5 `dpl_9fdjDUX73b8VDcRA2ipVuXhwtgKc`.

Hotfix #246 operator functional retest passed. The subsequent Work Specification capture exposed provider rate limiting across all configured routes; #252 now reports that as explicit retryable capacity state while preserving the mandatory model-generated and operator-approved Work Specification boundary. This record does not claim external OpenAI API capacity has recovered.

Post-release administrative no-op commits `0dea6f6b3588fb1d05df29105506ea2a6dd820d4` and `020409fd81de7298aa55114382fccff831b6af87` added and then immediately removed a temporary placeholder file without changing application/runtime content. They do not redefine the deployment-verified application identity above and are not deployment evidence.

`ARCHITECTURE.md` v3.1, `PROJECT-CONSTITUTION.md` v1.4 and `DESIGN-SYSTEM.md` remain unchanged because these stabilization hotfixes restore or clarify existing contracts without changing durable architecture, constitutional authority or visual language.

## Wave 4 autonomous IMPLEMENT progression recovery

Production Engineering Run `e65305f8-63f8-47e1-ac6c-2db0cd4dab7e` exposed a chained correctness defect after SPECIFY and PLAN succeeded. The Project-bound Code conversation had told the user that `Ryan9876/parallax` was inaccessible even though the canonical Project was bound to that repository and protected runtime bootstrap subsequently materialized it. That false conversational premise was then captured in the approved Work Specification as repository/file-provision constraints. The protected implementation model chain ran, failed before any safe mutation was accepted, and the autonomous coordinator returned an `IMPLEMENTATION_FAILED` stop without recording a durable failed IMPLEMENT attempt. The client also omitted `IMPLEMENT` from its autonomous-continuation stage set, leaving the run visibly active at IMPLEMENT with no failure code.

Issue #230 / PR #231 corrects the full failure chain without broadening authority:

- Project-bound Code response context and Work Specification drafting receive bounded server-authoritative canonical Project/repository capability facts; credentials, local paths, source contents and provider payloads remain excluded;
- protected implementation generation explicitly treats non-empty server-supplied source context as satisfying prior repository/file-provision preconditions while preserving all substantive approved Work Specification constraints;
- a recoverable pre-mutation implementation runtime failure now records exactly one failed IMPLEMENT attempt, transitions the Engineering Run to `FAILED`, records `last_failure_code=AUTONOMOUS_IMPLEMENT_FAILED`, and sets `resume_stage=IMPLEMENT` without advancing source lineage;
- mutation-applied implementation failures remain fail-closed and are not rewritten as ordinary failed attempts;
- the client now treats `IMPLEMENT` as an autonomous continuation stage and exposes the existing bounded autonomous action;
- REVIEW/HUMAN_REQUIRED remains the autonomous ceiling and BUILD/TEST/VERIFY, source-lineage, provider and deployment authority are unchanged.

Permanent regression coverage includes Project-bound response-context tests, Work Specification project-context tests, protected source-context authority tests, pre-mutation durable-failure semantics, mutation-applied fail-closed semantics, production-shaped runtime credential/bootstrap tests, and browser/Skia Code-binding coverage that verifies an IMPLEMENT run still exposes autonomous continuation.

The original production run was independently rechecked after deployment and remains `IMPLEMENT`, revision 2, with `resume_stage=null`, no failure code and no completion timestamp. Deployment did not mutate, resume or fabricate progress for that historical run. It is now eligible for explicit autonomous continuation through the corrected production client/runtime path.

## Wave 4 mobile Run Observability scroll hotfix

User acceptance testing on an iPhone exposed a second narrow-layout defect in Run Observability. With an active `IMPLEMENT` run and only three durable events, the fixed observability header, governed pipeline and focused section navigation consumed the available viewport while Activity only scrolled its short inner event list. Lower dashboard/support content therefore remained clipped even though the observer itself was live.

Issue #227 / PR #228 corrected this without changing run semantics: compact Run Observability now has an intentional outer vertical scroll surface spanning its header, pipeline, focused navigation and selected section. Desktop/tablet composition, persisted-event semantics, read-only evidence boundaries, provider authority, Engineering Run authority and the production API remain unchanged.

Permanent regression coverage `mobile-observability-scroll-smoke.mjs` reproduces the production failure shape at 390x844 with run `e65305f8-63f8-47e1-ac6c-2db0cd4dab7e`, state `IMPLEMENT` and durable sequence 3. It verifies meaningful outer vertical overflow, scrolls to lower Evidence & Audit content, confirms that content is viewport-reachable, and fails on browser errors. The test is part of the standard `test:visual` browser/Skia suite.

Exact candidate `aa756c94cf49912525241bce113e5b73b9423a88` passed Parallax P2 CI #884, Bounded Autonomy #532, protected promotion evaluation, release DSPy, both Vercel Preview checks and the browser/Skia suite including the new production-shaped regression. Production deployment `dpl_vDHBaGyi4q3pAGvNpULJwi8p95RR` then reached `READY` on exact merge SHA `908c7dacbefc5286d717861e70007a9deb0fd763`; `parallax-ashy-one-20.vercel.app` resolved to it with HTTP 200, no alias error, and no deployment-scoped error/fatal logs.

The observed Engineering Run was independently rechecked after that deployment and remained `IMPLEMENT`, revision 2, durable sequence 3, with no failure code. The UI hotfix did not mutate, resume or infer progress for that run.

## Wave 4 mobile governed-context scroll hotfix

User acceptance testing on an iPhone exposed a narrow-layout defect after Wave 4 closeout: an approved Work Specification and active Engineering Run were rendered in a fixed `governedContext` above the only conversation `ScrollView`. When those governed surfaces exceeded the phone viewport, the conversation scroll area collapsed and the user could not reach the lower execution controls or conversation content.

Issue #224 / PR #225 corrected the compact composition without changing runtime semantics: on mobile, the existing Work Specification + Engineering Run governed context is now the first content inside the existing conversation scroll surface, while the composer remains outside that surface and fixed in place. Non-compact desktop/tablet composition, Projects, Observability, authentication, provider authority, execution authority and API behavior are unchanged.

Permanent regression coverage `mobile-governed-scroll-smoke.mjs` now renders a 390x844 Project-bound Code conversation with an APPROVED Work Specification and active `IMPLEMENT` Engineering Run. It verifies that the execution surface has a meaningful vertical scroll ancestor, lower execution controls are reachable after scrolling, the composer remains position-stable, and no browser errors occur. This case is part of the standard `test:visual` browser/Skia suite.

Exact candidate `51e7cfcf47b927da66624118fed11b9b8911af38` passed Parallax P2 CI #880, Bounded Autonomy #530, the browser/Skia suite including the new regression, protected promotion evaluation, release DSPy, and both Vercel Preview checks before expected-head squash merge. Production client deployment `dpl_6xVHMhcdyrbb8SwSahGSuw5DLLiY` then reached `READY` on exact merge SHA `7e10b6d492361b2a8d046672b5bcd331d44172b3`; the exact user-observed alias `parallax-ashy-one-20.vercel.app` resolved to that deployment, an authenticated deployment fetch returned HTTP 200, and the deployment-scoped `error`/`fatal` log query returned no entries.

## Wave 4 stabilization and recovery outcome

Control-tower issue #169 serialized the production recovery and visual convergence effort. The original bounded workers #170-#174 were integrated, followed by a sequence of narrow production-recovery workstreams that removed successive real bottlenecks without broadening authority: runtime credentials, projected repository bootstrap latency, durable lineage object persistence latency, bounded failure classification, canonical repository provenance/delta delivery, exact-lineage Sandbox transfer, current Vercel Preview REST contract recovery, and autonomous IMPLEMENT progression recovery.

The recovery preserved these invariants throughout:

- no PAT fallback or materially broader provider credential scope;
- no arbitrary shell, filesystem, Git, HTTP or provider proxy surface;
- no production Vercel target selection from the runtime delivery path;
- exact canonical Project/run/source-lineage identity;
- protected BUILD/TEST/VERIFY execution on the accepted lineage only;
- bounded/redacted evidence rather than unrestricted logs or hidden reasoning;
- idempotent provider publication and replay-safe source delivery;
- explicit REVIEW/HUMAN_REQUIRED as the autonomous ceiling;
- no merge or production promotion authority granted to App Builder delivery.

## Fresh production autonomous proof

The final target-affecting proof used a fresh approved Work Specification and fresh Project-bound Engineering Run against the deployed production API. The proof intentionally created one harmless client-root artifact so the *registered delivery target itself* had to build rather than allowing Vercel's ignored-build rule to cancel the required Preview.

Canonical proof identities:

- Engineering Run: `ec24bdb2-543a-44f0-9f85-713f8fc36ddc`;
- Work Specification: `7b93c74f-8fa3-41e2-8e65-be15478e87c9`;
- final run state: `REVIEW`;
- final run revision: `6`;
- final failure code: none;
- accepted lineage: `src:180aab7555a15b71c320d859b888abffe263ffd11b424255d3e92da9ba360e63`;
- accepted content digest: `8bd10931f3ecd89da34831a8c7d5d1f25f13ba954e3cbde36ddc6c35ea72f7b3`.

Persisted protected attempts all passed exactly once for `SPECIFY`, `PLAN`, `IMPLEMENT`, `BUILD`, `TEST`, and `VERIFY`. BUILD/TEST/VERIFY evidence remained Vercel-Sandbox-backed, deny-all, exact-lineage bound, non-persistent, and did not fall back to a fresh repository checkout.

Persisted run-event sequence 1-10 is ordered and contains:

1. `RUN_CREATED`;
2. successful `SPECIFY`;
3. successful `PLAN`;
4. successful `IMPLEMENT`;
5. successful `SOURCE_LINEAGE_ACCEPTED`;
6. successful `BUILD`;
7. successful `TEST`;
8. successful `VERIFY`;
9. `REVIEW_REQUIRED` with outcome `HUMAN_REQUIRED`;
10. one successful `SOURCE_DELIVERY`.

The final proof did not transition the run to COMPLETE and did not perform operator review.

## Exact source-delivery proof

The successful source-delivery record for the final run created exactly the bounded provider publication expected by the existing App Builder contract:

- GitHub branch: `parallax/b1f6984d-ec24bdb2`;
- exact accepted-lineage commit: `7190079f5fab333f2d899edf644260bd3c95ed99`;
- proof-only pull request: #214;
- registered Vercel Preview project: `prj_wLXC5JjjetJf0H97kncRlqczD3OC` (`parallax` client project);
- delivery-recorded Preview deployment: `dpl_6qRbvuJchvNs1fRPHCpkEdEY5wvZ`;
- Preview URL: `parallax-kjk5uto0v-lew7.vercel.app`;
- Preview target: null / Preview-only;
- Preview source branch: `parallax/b1f6984d-ec24bdb2`;
- Preview source SHA: `7190079f5fab333f2d899edf644260bd3c95ed99`;
- status at immediate durable delivery read-back: `QUEUED`;
- independently verified terminal Preview state: `READY`, with no alias error.

The runtime's immediate source-delivery contract remains unchanged: it creates the bounded Preview, performs one authenticated read-back, rejects terminal ERROR/CANCELED states, and persists bounded delivery evidence. Control Tower then independently verifies that same recorded deployment ID reaches READY before release readiness is restored. No polling state machine or authority expansion was introduced merely to make the release proof pass.

Proof-only App Builder PRs #214, #213 and #209 were closed without merge after their evidence was captured. Their source branches/commits and provider evidence remain available for audit, but none was promoted to `main` or production.

## Production activation state

- production run-event migration/table: **APPLIED / PRESENT**;
- production run-event RLS/direct-client protections: **VERIFIED**;
- production `PARALLAX_RUN_EVENTS_ENABLED=1`: **YES**;
- protected live-observability routes active: **YES**;
- Warm Editorial stabilization client deployed: **YES**;
- mobile governed-context scroll hotfix deployed and active-run regression gate present: **YES / DEPLOYMENT-VERIFIED**;
- mobile Run Observability outer-scroll hotfix deployed and short-event-stream regression gate present: **YES / DEPLOYMENT-VERIFIED**;
- runtime credential recovery deployed: **YES**;
- projected source bootstrap recovery deployed: **YES**;
- durable lineage bootstrap recovery deployed: **YES**;
- canonical provenance/delta source delivery deployed: **YES**;
- exact-lineage Sandbox transfer recovery deployed: **YES**;
- current Vercel Preview REST contract recovery deployed: **YES**;
- autonomous IMPLEMENT progression recovery deployed: **YES / DEPLOYMENT-VERIFIED**;
- exact production API health/readiness/auth checks: **PASS**;
- final fresh autonomous run through IMPLEMENT/BUILD/TEST/VERIFY: **PASS**;
- persisted REVIEW/HUMAN_REQUIRED boundary: **PASS**;
- persisted successful SOURCE_DELIVERY: **PASS**;
- delivery-recorded exact Vercel Preview independently READY: **PASS**;
- deployment-window production runtime-error checks: **PASS / NONE FOUND**;
- end-to-end autonomous production readiness: **RESTORED / DEPLOYMENT-VERIFIED**.

## Durable architecture, design and authority

`ARCHITECTURE.md` remains authoritative for the server-owned canonical Project/repository binding, Work Specification approval boundary, protected IMPLEMENT runtime, durable failed-run semantics, Vercel Functions runtime OIDC/Connect boundary, canonical Project/run/source-lineage/provider authority, exact-lineage protected Sandbox model and observation semantics. PR #231 restores implementation to those existing trust boundaries and does not introduce a new durable architecture contract, so no architecture-record change was required.

`DESIGN-SYSTEM.md` remains authoritative for the Warm Editorial Observatory design direction. No design-system change was required for the autonomous IMPLEMENT recovery; the client change restores the existing governed continuation action rather than introducing a new visual language or durable design rule.

`PROJECT-CONSTITUTION.md` v1.4 standing single-user production promotion authority remains active. No governance-policy change was required. Standing authority did not waive exact-head CI, protected evaluation, least privilege, rollback, deployment evidence or post-deploy verification.

Production capability claims continue to require deployment evidence plus functional evidence for the claimed path. Wave 4 retains its previously captured real production autonomous proof through operator REVIEW, while PR #231 adds deployment-verified regression coverage and production health/preflight evidence for the autonomous IMPLEMENT failure-recovery path without mutating the historical run.