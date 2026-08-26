# Parallax 2.0 Current State

Release: Wave 5 generalized application delivery is fully source-integrated on `integration/wave5-generalized-delivery`; cumulative S1-S6 code integration `14961d06d5e3b1c83f9d45c94bcc0727a2ec115a` passed exact-head Workstream Spec Validation #346 (`32916448744`), Bounded Autonomy #548 (`32916448731`), P2 CI #905 (`32916448734`) and both Vercel Preview checks. This is validated integration, not production deployment. Production remains the deployment-verified Wave 4 application/runtime recorded below until a separately evidenced `main` merge and production cutover are verified.
Date: 2026-08-25
Status: **WAVE 5 S1-S6 SOURCE-INTEGRATED / CUMULATIVE RELEASE VALIDATED / PRODUCTION PROMOTION PENDING / WAVE 4 PRODUCTION REMAINS DEPLOYMENT-VERIFIED / HUMAN REVIEW BOUNDARY PRESERVED / SINGLE-USER PRODUCTION PROMOTION STANDING AUTHORITY ACTIVE**

## Wave 5 validated integration state

Control Tower #215 has accepted and serialized all six Wave 5 workstreams through S6 #221. Expected-head merge of S6 PR #240 produced cumulative code-integration SHA `14961d06d5e3b1c83f9d45c94bcc0727a2ec115a`. Validation PR #241 then proved that exact S1-S6 integration head with Workstream Spec Validation #346, Bounded Autonomy #548, P2 CI #905, full API regression, browser/Skia acceptance, protected Code/Engineering/Reason promotion evaluation, release DSPy compilation/plan verification and successful Vercel Preview checks for both deployable projects.

The integrated Wave 5 capability set is:

- deterministic repository intelligence/compatibility evidence for unfamiliar repository shapes, with repository content remaining untrusted and non-authoritative;
- exact-digest governed skills constrained by server-owned capability snapshots;
- Project-scoped application service bindings using logical interfaces/features and opaque secret-slot identities rather than model-visible credentials;
- exact Project/run/Work Specification/repository-profile objective-to-application orchestration with fail-closed `HUMAN_REQUIRED`;
- provenance-bound validated engineering memory that defaults Project-private, requires explicit sanitized-sharing approval for cross-Project reuse and never weakens fresh validation;
- a permanent multi-shape generalization benchmark and integrated proof covering static web, Python service, workspace/monorepo, ambiguity, malicious repository instructions, memory HIT/MISS, bounded correction, exact-lineage runtime execution, governed Preview publication and duplicate-safe replay.

`ARCHITECTURE.md` v3.1 records these durable contracts. `PROJECT-CONSTITUTION.md` and `DESIGN-SYSTEM.md` remain unchanged because Wave 5 does not alter constitutional authority or the visual language.

Production has **not** been changed by this integration. No Wave 5 `main` merge, production deployment, database migration, provider/credential mutation or production configuration mutation has yet occurred. The deployment-verified Wave 4 API/client identities and rollback candidates below therefore remain the current production truth. PR #241 is the governed Wave 5 release-candidate surface; this authoritative record update is included on that candidate and must itself pass final exact-head gates before promotion.

## Current production truth

The deployment-verified production API/runtime binary is Vercel deployment `dpl_ExFCK2iMVDbJbRiBZcL4faspHaw5` from repository application head `main@ff8e2395df081ebff376d703dfd97f3c10008240` (PR #231, autonomous IMPLEMENT progression recovery). It is `READY`, mapped to `parallax-api-tan.vercel.app`, and post-cutover checks on 2026-08-25 confirmed:

- `/health` = HTTP 200 / `status=ok`;
- `/ready` = HTTP 200 / `status=ready`, `database=ok`, `providers=ok`, one registered provider target;
- unauthenticated `/v1/projects` = HTTP 401 / `Authentication required` with Bearer challenge;
- production provider, delivery-permission, projected-source, private Blob, lineage-composition, projected-bootstrap, execution-snapshot and run-event-schema preflights all passed during the exact production build;
- project-level runtime-error queries covering the deployment window returned no errors for either production project.

The deployment-verified production client is Vercel deployment `dpl_HxCGSRkEuJJ6qmHwokwPSM6XMcEn` from the same repository application head `main@ff8e2395df081ebff376d703dfd97f3c10008240`. It is `READY`, has no alias error, and owns `parallax-lew7.vercel.app`, `parallax-ashy-one-20.vercel.app`, and `parallax-git-main-lew7.vercel.app`.

The exact pre-merge candidate `2eee9399b7cd778bf1719e9ae97b95a1c4cd5038` passed Parallax P2 CI #892, Bounded Autonomy Pilot #538, Workstream Spec Validation #335, protected promotion evaluation, release DSPy compilation, full API regression, browser/Skia acceptance, and the relevant Vercel Preview checks before expected-head squash merge. Exact post-merge application head `ff8e2395df081ebff376d703dfd97f3c10008240` passed Parallax P2 CI #893 and Workstream Spec Validation #336 after deployment.

The immediately preceding known-good API production deployment `dpl_2L4R6g3em7LJc7XWdRp5rueGFRK1` from `main@62012c9017953945aa55d35550800347ed9f8007` remains the rollback reference for this runtime recovery. Routine rollback remains non-destructive and follows the existing flag-first/application-deployment policy.

The immediately preceding known-good client production deployment `dpl_vDHBaGyi4q3pAGvNpULJwi8p95RR` from `main@908c7dacbefc5286d717861e70007a9deb0fd763` remains `READY` and is the Vercel rollback candidate for this client change. The earlier Wave 4 client deployment `dpl_AHKAix8J11knSfSCRzCupM6ND7vn` remains available as an older known-good reference.

This `CURRENT-STATE.md` update is a record-only repository change. It does not change the deployment-verified application/runtime binary SHA above and must not be treated as a new production application release solely because the documentation commit advances `main`.

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
