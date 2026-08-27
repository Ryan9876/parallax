# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / FINAL SAFE-DELETION ACCEPTANCE PENDING AUTHENTICATED POST-CUTOVER SMOKE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 + W6-R1 RUNTIME ACTIVATION ACCEPTED AND INTEGRATED / EXACT INTEGRATION HEAD 07F45319 VALIDATED / WAVE 6 NOT DEPLOYED / AUTHORITATIVE RECORDS RECONCILED / PRODUCTION PROMOTION BLOCKED PENDING SEPARATE RELEASE QUALIFICATION + GOVERNED PROMOTION**

## Current production truth

Production remains the deployment-verified Wave 5 generalized application-delivery platform plus the accepted stabilization chain through mobile #261/#262, response-stream #271/#272 and P2-V0.18.10 model transport.

Safe conversation/Project deletion originated in #290 / PR #291 and is present in production with migration `20260827173141`. The post-merge lifecycle/authorization audit gaps were corrected under `P2-V0.18.12` / PR #294. PR #294 merged to `main` as `109444dcd7e13bfe842dea71355607941258b073` after the exact corrective implementation head passed all required gates. Vercel deployed the corrective API SHA to production and the production alias is serving it. The client had no source delta, so its main deployment was intentionally canceled by the configured Ignored Build Step and the existing verified client artifact remains active.

The corrective release is **production-deployed and infrastructure-verified but not yet accepted as fully deployment-verified feature behavior** because the final authenticated post-cutover deletion smoke cannot be executed by the available connector without an application user session. No destructive smoke will be performed against real user content merely to manufacture release evidence.

Wave 6 S1-S6 plus W6-R1 runtime activation are accepted/integrated development architecture and are **not** production deployments. W6-R1 exact worker head `6244cefd8c7cc2dec923f815838e14747f47aef0` passed Workstream Spec Validation #492, Bounded Autonomy #699 and P2 CI #1103 (`781 passed, 1 skipped`; client checks also passed). PR #306 merged that exact head into `integration/wave6-agentic-control-plane` as `07f45319d166d52298b2b056cdab4c48c1accf25`. Fresh integration-head Workstream #493, Bounded Autonomy #700 and P2 CI #1104 all passed. Validation-only PR #308 was closed without merge to `main`.

Ordinary `EngineeringRuntimeComposition` can now activate the accepted agentic decision plane under the server-owned `PARALLAX_AGENTIC_RUNTIME_ENABLED` switch. Disabled mode preserves the existing runtime. Enabled mode requires durable source lineage; PLAN preserves the protected evidence contract, agent candidates remain non-authoritative until selected, selected evidence still enters the existing safe IMPLEMENT/source-lineage boundary, durable worker recovery gates dispatch/reassignment, and process recreation can replay only an exact immutable selected-candidate artifact whose protected bindings still match. Preview remains the autonomous provider ceiling and REVIEW/HUMAN_REQUIRED remain protected boundaries.

Production remains unchanged at `main@a455b223ad4707aa7fe2ccd3470a5e7640c40da2`. This record reconciles the completed W6-R1 integration state; it does not authorize or imply deployment. Wave 6 production promotion remains blocked pending a separate exact-head release-qualification decision and governed production promotion/verification.

### Safe-deletion release identity

- production source branch: `main`;
- initial feature merge: `a6d7a6fd4d556d5544ede9c43b93972a8c590011` from PR #291;
- corrective merge: `109444dcd7e13bfe842dea71355607941258b073` from PR #294;
- feature issue/workstream: #290 — safe deletion for old conversations and Projects;
- corrective specification: `P2-V0.18.12`;
- pre-implementation Workstream Spec Validation #463 — PASS on spec head `095803846b5bf1c51aa62eb79ffc66665a33134c`;
- final corrective Workstream Spec Validation #471 — PASS;
- final corrective Bounded Autonomy Pilot #680 — PASS;
- final corrective Parallax P2 CI #1078 — PASS;
- exact final corrective implementation head before merge: `3f49d1b5fa7ff41bd89303c92db897030a82247d`.

### Production database

Supabase project `kjyenifnfjqnzfgshpwg` (`Parallax 2.0`) has production migration:

- version `20260827173141`;
- name `safe_conversation_project_deletion`.

Verified schema:

- `conversations.deleted_at` exists as `timestamptz`;
- `projects.deleted_at` exists as `timestamptz`;
- `ix_conversations_deleted_at` exists;
- `ix_projects_deleted_at` exists;
- `uq_projects_owner_slug_active` enforces owner-local slug uniqueness only for active Projects;
- `uq_projects_owner_repository_active` enforces owner-local repository uniqueness only for active Projects with a repository reference.

The migration is additive/backward-compatible and does not require a corrective migration for P2-V0.18.12.

### Production client

- Vercel project: `parallax`;
- active verified deployment retained from #291: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- state: `READY`;
- target: `production`;
- artifact Git SHA: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- public production alias: `parallax-ashy-one-20.vercel.app`.

The corrective main commit `109444dcd7e13bfe842dea71355607941258b073` created client deployment `dpl_9mkVu5nKgza9YnbbFYf1N4hMdmx9`, which Vercel canceled because the configured Ignored Build Step (`git diff --quiet HEAD^ HEAD ./`) found no deployable client-root changes. This is expected for the API-only correction and intentionally preserves the existing verified client artifact rather than manufacturing a redundant client build.

### Production API — corrective P2-V0.18.12

- Vercel project: `parallax-api`;
- production deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- state: `READY`;
- target: `production`;
- exact Git SHA: `109444dcd7e13bfe842dea71355607941258b073`;
- public production alias: `parallax-api-tan.vercel.app`.

Post-cutover verification on the corrective deployment established:

- production alias is serving deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- `GET /health` → HTTP 200 with `status=ok`;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- exact corrective deployment runtime scan found no `error`/`fatal` records;
- unauthenticated `GET /v1/conversations` → HTTP 401 with `Authentication required`, confirming the protected route remains behind the authentication boundary.

The final authenticated destructive-behavior smoke is intentionally still open: the available deployment connector cannot present a Parallax application user session, and production verification must not be faked by weakening auth or deleting real user data without a deliberate test target.

## Safe deletion corrective hardening — P2-V0.18.12 / PR #294

PR #294 is **MERGED**. The corrective implementation:

1. derives conversation and Project deletion terminality from the protected Engineering Run `TERMINAL_STAGES` contract instead of a duplicated deletion lifecycle list;
2. treats `COMPLETE`, `SPEC_AMENDMENT` and `CANCELLED` as terminal while preserving `FAILED` and all other states outside the protected terminal set as deletion-blocking;
3. propagates authenticated application role into conversation deletion;
4. requires application `owner` role to delete a historical unbound conversation while preserving compatibility read visibility;
5. preserves canonical Project-bound cross-owner not-found behavior;
6. adds focused regression tests for lifecycle parity, owner-only unbound destructive authority, evidence retention and Project identity reuse.

### Remaining release acceptance item

The exact corrective implementation, merge, production API deployment, health/readiness checks, authentication boundary and error scan are verified. The only remaining #290 completion item is an authenticated post-cutover feature smoke against a deliberately disposable conversation/Project test target. Until that evidence exists, #290 remains open and the feature is not labeled fully deployment-verified.

## Durable deletion contract

- user-visible `Delete` is logical workspace deletion, not evidence purge;
- deleted conversations/Projects disappear from active workspace reads;
- protected Work Specifications, Engineering Runs, attempts, run events, source lineage and immutable evidence remain retained;
- linked GitHub repositories, pull requests and Vercel deployments are never deleted by workspace cleanup;
- any relevant Engineering Run outside authoritative protected `TERMINAL_STAGES` blocks deletion with HTTP 409;
- deleted Project slug/repository identities may be reused among active Projects, but replacement creates a new canonical `Project.id` and gains no inherited authority;
- Project-bound deletion derives ownership from canonical Project identity and fails closed across owners;
- historical unbound conversation read compatibility does not grant destructive authority; deletion requires application `owner` role;
- destructive UI actions require explicit confirmation and do not hide state until server success.

## P2-V0.18.10 model-transport stabilization retained

The model-transport correction remains the accepted production routing contract and is unaffected by safe-deletion hardening.

Runtime model escalation order remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted production model traffic binds admitted request-scoped Vercel runtime OIDC to the fixed OpenAI-compatible Vercel AI Gateway endpoint. Process-environment `VERCEL_OIDC_TOKEN` is not production model-provider authority. Explicit server-owned `DSPY_API_BASE` / `DSPY_API_KEY` remains the deliberate override. There is no silent direct-OpenAI fallback.

The prior accepted P2-V0.18.10 API deployment `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` remains an application rollback reference for failures unrelated to the already-applied deletion schema.

## Deployment-verified stabilization retained

### Mobile #261 / PR #262

The mobile release remains deployment-verified. It provides mobile primary destinations `Chat`, `Build`, and `Project`; conversation-first Chat; full-screen Work Specification review; `SPEC_AMENDMENT` recovery; guided Build lifecycle; canonical Project/conversation switching; compact authenticated access behavior; and Live Build return-to-chat semantics while preserving server-owned authority.

Historical mobile identities retained:

- exact validated worker: `56f6d2a81112e592b1128df2b96506ae2d923650`;
- application merge: `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`;
- known-good mobile client rollback: `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK`.

### Response-stream #271 / PR #272

The response-stream correction remains deployment-verified. It distinguishes provider-capacity exhaustion from protected scope/reason validation failure, preserves the durably submitted user turn, and does not change model/provider order, credentials, Project/spec/source authority, approval or REVIEW boundaries.

Historical accepted identities retained:

- exact validated worker: `f26f9a9c308d7d72ca5f2aab824d217767a4bcfa`;
- application merge: `9767b2520d74c70bd1a2ec2e951480da223b45f7`;
- historical API deployment: `dpl_7WK8xEK6FtuaqLGH4eML5mXTSj7Y`.

## Wave 5 baseline retained

Control Tower #215 completed generalized application delivery through #216-#221 / `P2-V0.18.1`-`P2-V0.18.6`. Final Wave 5 application release merge `c39b5352be940f4052baa65c7cdd9d7c3ec773bb` remains the generalized-delivery architectural baseline. Later production stabilization and workspace cleanup are cumulative and do not replace its authority model.

## Wave 6 — Agentic Development Control Plane

Control Tower: #263.
Authoritative integration branch: `integration/wave6-agentic-control-plane`.
Current accepted integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`.
Current production baseline: `main@a455b223ad4707aa7fe2ccd3470a5e7640c40da2`.
Wave 6 production deployment: **none**.

### Accepted cumulative S1-S6 foundation

1. #264 / S1 Agent Adapter & Evidence Protocol — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / S2 Dynamic Development Team Orchestration — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / S3 Independent Evaluation & Quality Judgment — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / S4 Outcome Routing & Development Economics — **COMPLETE / ACCEPTED / INTEGRATED**;
5. #281 repository source-tree capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / S5 Candidate Competition & Synthesis — **COMPLETE / ACCEPTED / INTEGRATED**;
7. #269 / S6 Agentic Development Integrated Reference Proof — **COMPLETE / ACCEPTED / INTEGRATED**.

The cumulative S1-S6 integration checkpoint before runtime activation was `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`. S6 exact worker gates Workstream #485, Bounded Autonomy #692 and P2 CI #1096 passed, followed by cumulative integration Workstream #486, Bounded Autonomy #693 and P2 CI #1097. Temporary main-targeted validation PR #302 closed without merge.

### W6-R1 runtime activation closure — #304 / P2-V0.19.7

W6-R1 is **IMPLEMENTED / VALIDATED / INTEGRATED**.

- approved specification: `P2-V0.19.7` with stable AC-01..AC-10;
- authentic DSPy SpecCritic + SpecCompiler evidence: run `33111365094`;
- exact compiled plan committed at `specs/compiled/P2-V0.19.7.plan.json`;
- pre-semantic protected `--require-dspy` gate: run `33111782426` — **PASS**;
- exact validated implementation head: `6244cefd8c7cc2dec923f815838e14747f47aef0`;
- canonical PR #306: **MERGED TO INTEGRATION ONLY**;
- resulting integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`;
- worker Workstream Spec Validation #492 — **PASS**;
- worker Bounded Autonomy Pilot #699 — **PASS**;
- worker Parallax P2 CI #1103 — **PASS** (`781 passed, 1 skipped`);
- fresh integration Workstream Spec Validation #493 — **PASS**;
- fresh integration Bounded Autonomy Pilot #700 — **PASS**;
- fresh integration Parallax P2 CI #1104 — **PASS**;
- validation-only PR #308: **CLOSED WITHOUT MERGE TO MAIN**.

### Integrated runtime behavior

The ordinary protected Engineering Run path now has a server-owned Wave 6 activation composition. `PARALLAX_AGENTIC_RUNTIME_ENABLED` is the sole runtime switch: disabled mode retains the existing composition; enabled mode requires durable lineage and fails closed rather than falling back to an alternate writer.

PLAN records a deterministic server-owned team/work-graph decision while retaining the existing required PLAN evidence. Agent results remain proposal/evidence only. Selected candidates still pass through `ProtectedImplementationRuntime`, the safe patch engine and durable source-lineage compare-and-swap before exact-lineage BUILD/TEST/VERIFY. Controller evidence is bounded and cannot claim Engineering Run transition, source acceptance, REVIEW completion or deployment authority.

S2 dispatch is bound to durable worker leases/checkpoints/recovery. Expired process ownership may reassign only through the accepted recovery state and a new lease generation; competing active ownership fails closed. Multi-agent team selection does not itself trigger extra candidate competition spend.

The selected candidate is persisted as an immutable private content-addressed artifact before worker transition to `READY_FOR_INTEGRATION`. Process recreation may restore that exact candidate only if Project/run/spec/acceptance/plan/base-lineage/base-revision/source-context bindings still match and current protected proposal validation succeeds. Replay never bypasses canonical lineage acceptance or provider idempotency.

### Release state

Wave 6 remains **not deployed**. W6-R1 closed the material runtime-activation defect found by the release audit. This authoritative record reconciliation establishes the durable project truth at the exact validated integration state. The next gate is a separate release qualification against the reconciled integration head, followed only then by an explicit governed production-promotion decision and post-cutover verification.

No W6-R1 result grants autonomous production promotion, production merge, REVIEW completion or expansion of provider/model/credential authority.

## Rollback

Rollback is component-specific and governed.

### API

Corrective production API:

- deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- source `109444dcd7e13bfe842dea71355607941258b073`.

Previous #291 API rollback candidate:

- deployment `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 accepted API reference remains `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` at `e6fc6900239df436545318e6ab7f532d0d3789bc`.

Because migration `20260827173141` is additive, application rollback does not require an emergency down-migration. Do not drop deletion tombstones or partial uniqueness indexes while deletion data may depend on them.

### Client

Active safe-deletion client artifact:

- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

Pre-#291 client reference remains `dpl_ZxJTDLWYJxShme9oA6KBSYpxxaR2` at `9767b2520d74c70bd1a2ec2e951480da223b45f7`. Historical mobile rollback reference remains `dpl_A2hN3ZYPzbewMFDhe6zpGtkbd1vK` at `2bd677c3532df9fc436cac39cd23c4ca86f6e26d`.

## Program controls

- GitHub and the four authoritative project records outrank chat recollection;
- Control record #31, roadmap #32, safe-deletion workstream #290 and Wave 6 Control Tower #263 remain active durable program records;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- workers develop on isolated branches and stop at governed integration boundaries;
- interacting production workstreams are serialized at shared lifecycle/record boundaries;
- a production-baseline sync into an undeployed future-wave integration branch must preserve accepted future-wave semantics, use current production records for production truth, and pass fresh cumulative exact-head gates before becoming the new integration checkpoint;
- standing single-user production-promotion authority never waives exact-head gates, rollback, least privilege, post-cutover evidence or Preview/REVIEW boundaries;
- path-aware ignored builds may preserve a previously verified component artifact when a release has no changes under that component root;
- deployed/infrastructure-ready is not equivalent to deployment-verified feature behavior when a required post-cutover feature smoke is still absent;
- no production-verification claim is valid without exact release identity plus appropriate post-cutover evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- logical workspace deletion cannot erase or weaken protected engineering/source/provider evidence;
- authoritative Engineering Run lifecycle state, not a duplicated deletion-specific list, decides whether a run is terminal;
- historical compatibility read visibility does not imply destructive authorization;
- deleting a Project never deletes external GitHub/Vercel resources;
- reusing a deleted Project's human-readable identity creates a new canonical Project identity and grants no inherited authority;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- production hosted-model identity and transport are server-owned and fail closed;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; constitutional authority did not change.
- `ARCHITECTURE.md` v3.7 — current production architecture plus accepted Wave 6 S1-S5 durable architecture; the synchronization/release decision introduces no new durable architecture contract.
- `DESIGN-SYSTEM.md` v3.1 — current production design system; the synchronization/release decision introduces no new design contract.
- `CURRENT-STATE.md` — updated after cumulative S1-S5 validation and non-force integration advancement to record the accepted checkpoint, exact gate evidence, unchanged production state and S6 spec-first release boundary.

Wave 6 remains not deployed. Safe deletion corrective code is serving in production; final safe-deletion feature acceptance remains deliberately open until authenticated post-cutover deletion behavior is exercised against a disposable test target. S6 may begin spec-first work, but semantic implementation remains gated by an approved `P2-V0.19.6` and authentic DSPy compiled evidence.