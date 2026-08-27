# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVE 5 PRODUCTION BASELINE RETAINED / MOBILE #261/#262 PRODUCTION-VERIFIED / RESPONSE-STREAM #271/#272 PRODUCTION-VERIFIED / P2-V0.18.10 MODEL-TRANSPORT STABILIZATION RETAINED / SAFE DELETION CORRECTIVE P2-V0.18.12 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / FINAL SAFE-DELETION ACCEPTANCE PENDING AUTHENTICATED POST-CUTOVER SMOKE / CLIENT READY / API READY / WAVE 6 CONTROL #263 ACTIVE / S1-S6 + W6-R1 #304 PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED / PRODUCTION AGENTIC CANARY + DURABLE REPLAY PRECHECKS PASS / FINAL WAVE 6 RELEASE ACCEPTANCE PENDING AUTHENTICATED PROJECT-BOUND ENGINEERING RUN / #312 OPEN**

## Current production truth

Production is cumulative through the Wave 6 API infrastructure activation on exact application source `main@831fef94aa1c94ff1178b1a325e8774d49fd8752`, while retaining the deployment-verified Wave 5 generalized application-delivery baseline and the accepted stabilization chain through mobile #261/#262, response-stream #271/#272, P2-V0.18.10 model transport and safe-deletion hardening. The client had no Wave 6 source delta and retains its prior verified production artifact under the existing path-aware ignored-build contract.

Safe conversation/Project deletion originated in #290 / PR #291 and is present in production with migration `20260827173141`. The post-merge lifecycle/authorization audit gaps were corrected under `P2-V0.18.12` / PR #294. PR #294 merged to `main` as `109444dcd7e13bfe842dea71355607941258b073` after the exact corrective implementation head passed all required gates. Vercel deployed that corrective API SHA and it remained the verified API rollback artifact until the Wave 6 production cutover. The client had no source delta, so its main deployment was intentionally canceled by the configured Ignored Build Step and the existing verified client artifact remains active.

The corrective release is **production-deployed and infrastructure-verified but not yet accepted as fully deployment-verified feature behavior** because the final authenticated post-cutover deletion smoke cannot be executed by the available connector without an application user session. No destructive smoke will be performed against real user content merely to manufacture release evidence.

Wave 6 S1-S6 plus runtime-activation closure W6-R1 are now **production-deployed and infrastructure-verified, but not yet release-verified**. The accepted W6-R1 worker `6244cefd8c7cc2dec923f815838e14747f47aef0` was integrated through `07f45319d166d52298b2b056cdab4c48c1accf25`, authoritative records were reconciled at `f55c07c188df7cd370d10a3f5478001a139061a0`, and the governed release sequence reached production through PR #313 plus bounded fail-closed corrections PR #315, PR #318 and PR #321. Exact production application source is `main@831fef94aa1c94ff1178b1a325e8774d49fd8752`; Vercel API deployment `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw` is READY and owns the production API aliases.

The server-owned `PARALLAX_AGENTIC_RUNTIME_ENABLED=1` activation is version-controlled with the release. Production pre-cutover proof passed provider/source, delivery-permission, projected-source, private Blob, durable lineage, exact selected-candidate artifact round-trip, projected bootstrap with engineering-runtime/process-recreation/replay/no-stage-mutation proofs, execution snapshot and run-event schema guards. `/health` and `/ready` are HTTP 200, unauthenticated protected access remains HTTP 401, and the exact deployment error/fatal scan is clean. The remaining #312 acceptance gate is deliberately not bypassed: an authenticated application principal must execute a disposable Project-bound Engineering Run through live agentic PLAN/IMPLEMENT, exact-lineage BUILD/TEST/VERIFY, Preview and REVIEW stop behavior.

### Production API — Wave 6 infrastructure activation

- Vercel project: `parallax-api`;
- production deployment: `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`;
- state: `READY`;
- target: `production`;
- exact application Git SHA: `831fef94aa1c94ff1178b1a325e8774d49fd8752`;
- public production alias: `parallax-api-tan.vercel.app`;
- activation: version-controlled `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`.

Governed release/correction evidence:

- release candidate PR #313 exact head `3d90bbedfeca16a1d0dcf4e564dde6832fa0085d`; Workstream #498, Bounded #704 and full-release P2 CI #1109 — **PASS**;
- source-tree preflight parity PR #315 exact head `2843936d5dad69c57a26b6f4c293d27deb832c9c`; Bounded #708 and full-release P2 CI #1114 — **PASS**;
- direct-script source-root correction PR #318 exact head `cb7cb6f51f1eb2a86da39c3398d6fb4a19af437e`; Bounded #709 and full-release P2 CI #1116 — **PASS**;
- service-runtime dependency correction PR #321 exact head `ce55f9c4fabd82774954007483997b9d52878e2c`; Bounded #711 and full-release P2 CI #1119 — **PASS**;
- exact-head Vercel Preview for PR #321: `dpl_63ZxgWDYb7JKsRGeUetUy3VXkZzk` — **READY**.

Exact production build proof on `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`:

- provider preflight PASS with 538 source-tree entries and private Blob read/write verification;
- delivery-permission preflight PASS for one exact repository target;
- projected-source preflight PASS with 492 lineage-eligible files / 5,013,766 UTF-8 bytes;
- durable lineage composition PASS with metadata rollback verification;
- Wave 6 selected-candidate artifact canary PASS with exact immutable round trip (`artifact=366be26db9bf…`);
- projected bootstrap PASS with engineering runtime, process recreation, replay, no-stage-mutation, metadata rollback and Project rollback verified;
- execution-snapshot preflight PASS with deny-all restore, offline dependencies and no repository source present;
- run-event schema guard PASS;
- `GET /health` → HTTP 200;
- `GET /ready` → HTTP 200 with `database=ok`, `providers=ok`, `provider_targets=1`;
- unauthenticated `GET /v1/access/me` → HTTP 401 with `Authentication required`;
- exact deployment error/fatal runtime scan: no matching logs.

Release state: **DEPLOYED / INFRASTRUCTURE-VERIFIED / AUTHENTICATED RUNTIME SMOKE PENDING**. Earlier failed production attempts were fail-closed build-time probes and did not cut over the production alias. #312 remains open until the authenticated Project-bound Engineering Run is proven.

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

### Prior production API rollback — corrective P2-V0.18.12

- Vercel project: `parallax-api`;
- rollback deployment: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- state: `READY`;
- historical target: `production`;
- exact Git SHA: `109444dcd7e13bfe842dea71355607941258b073`;
- prior public alias: `parallax-api-tan.vercel.app` (now served by the Wave 6 production deployment).

Before Wave 6 cutover, post-cutover verification on this corrective deployment established HTTP 200 health/readiness, database/provider readiness, a clean exact-deployment error/fatal scan and HTTP 401 for unauthenticated protected access. It remains the immediate verified API rollback artifact.

The final authenticated destructive safe-deletion smoke remains intentionally open: the available deployment connector cannot present a Parallax application user session, and production verification must not be faked by weakening auth or deleting real user data without a deliberate test target.

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
Accepted runtime-activated application integration head: `07f45319d166d52298b2b056cdab4c48c1accf25`.
Reconciled Wave 6 integration/record head: `f55c07c188df7cd370d10a3f5478001a139061a0`.
Current production application source: `main@831fef94aa1c94ff1178b1a325e8774d49fd8752`.
Wave 6 production API deployment: `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw` — **READY / INFRASTRUCTURE-VERIFIED**.
Production activation flag state: **enabled through version-controlled `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`**.
Final Wave 6 release verification: **PENDING AUTHENTICATED PROJECT-BOUND ENGINEERING RUN**.

### Production release #312 evidence

- release candidate PR #313 exact head: `3d90bbedfeca16a1d0dcf4e564dde6832fa0085d`;
- qualified release merge: `a5c700762bcf8ebbd5605d7e5d47756bab10fb4e`;
- source-tree parity correction #314 / PR #315 merge: `8bd124244f9bb8175c417e4c4084cc15d9bea066`;
- API source-root correction #316 / PR #318 merge: `bafda5b3d42ca3662a075cefb8c83bd9b017392e`;
- service-runtime canary correction #319 / PR #321 exact worker: `ce55f9c4fabd82774954007483997b9d52878e2c`;
- production application merge: `831fef94aa1c94ff1178b1a325e8774d49fd8752`;
- final correction Bounded Autonomy #711 — **PASS**;
- final correction Parallax P2 CI #1119 — **PASS**, including browser/Skia, protected promotion evaluation and DSPy release compilation/protected-plan verification;
- production deployment: `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw` — **READY**;
- immediate API rollback: `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex` at `109444dcd7e13bfe842dea71355607941258b073`;
- authenticated Project-bound Engineering Run smoke: **PENDING**.

### Accepted cumulative S1-S6 + W6-R1 evidence

- accepted production-synchronized S1-S5 checkpoint: `f8b5bcd9b40f13777c16e3d323030b814dc4fa86`;
- S6 exact validated worker head: `75d6a51f8d014e70772a54f032370ead64c965bb`;
- S6 integration head before runtime closure: `01dda9f0328ca3f6ce2cf31f9c236c4603cef638`;
- S6 worker Workstream #485 / Bounded #692 / P2 CI #1096 — **PASS**;
- pre-W6-R1 cumulative integration Workstream #486 / Bounded #693 / P2 CI #1097 — **PASS**;
- W6-R1 specification: `P2-V0.19.7`;
- W6-R1 exact validated worker head: `6244cefd8c7cc2dec923f815838e14747f47aef0`;
- W6-R1 canonical PR #306: **MERGED TO INTEGRATION ONLY**;
- W6-R1 integration merge: `07f45319d166d52298b2b056cdab4c48c1accf25`;
- W6-R1 worker Workstream Spec Validation #492 — **PASS**;
- W6-R1 worker Bounded Autonomy Pilot #699 — **PASS**;
- W6-R1 worker Parallax P2 CI #1103 — **PASS**;
- runtime-activated cumulative integration Workstream Spec Validation #493 — **PASS**;
- runtime-activated cumulative integration Bounded Autonomy Pilot #700 — **PASS**;
- runtime-activated cumulative integration Parallax P2 CI #1104 — **PASS**;
- W6-R1 validation-only PR #308: **CLOSED WITHOUT MERGE TO MAIN**;
- long-lived PR #275 remains **DRAFT / DO NOT MERGE** and is not a production release candidate.

Accepted/integrated semantic state:

1. #264 / S1 Agent Adapter & Evidence Protocol — **COMPLETE / ACCEPTED / INTEGRATED**;
2. #265 / S2 Dynamic Development Team Orchestration — **COMPLETE / ACCEPTED / INTEGRATED**;
3. #266 / S3 Independent Evaluation & Quality Judgment — **COMPLETE / ACCEPTED / INTEGRATED**;
4. #267 / S4 Outcome Routing & Development Economics — **COMPLETE / ACCEPTED / INTEGRATED**;
5. #281 repository source-tree capacity prerequisite — **COMPLETE / ACCEPTED / INTEGRATED**;
6. #268 / S5 Candidate Competition & Synthesis — **COMPLETE / ACCEPTED / INTEGRATED**;
7. #269 / S6 Agentic Development Integrated Reference Proof — **COMPLETE / ACCEPTED / INTEGRATED**;
8. #304 / W6-R1 Runtime Activation — **COMPLETE / VALIDATED / ACCEPTED / INTEGRATED / PRODUCTION-DEPLOYED / INFRASTRUCTURE-VERIFIED / FINAL AUTHENTICATED RELEASE SMOKE PENDING**.

### Runtime activation closure — #304 / P2-V0.19.7

W6-R1 closes the release-audit gap without adding a second execution authority. Under explicit server-owned `PARALLAX_AGENTIC_RUNTIME_ENABLED=1`, ordinary protected PLAN uses one server-owned agentic planning seam bound to exact Project/run/approved Work Specification/acceptance/source identity. The accepted S2 orchestration layer selects the smallest adequate admitted team; operator agent selection is not part of the normal build path.

Agent work remains non-authoritative candidate labor. Production-capable S1 adapters wrap the existing hosted implementation-generation transport. Durable S2 worker lease/checkpoint/recovery state governs live dispatch and process-loss reassignment. Candidate BUILD/TEST/VERIFY happens on disposable deny-all Vercel Sandbox materializations before S3 evaluation; protected deterministic failure cannot be promoted by model/evaluator judgment. S4 routing consumes provenance-bound evidence and S5 selection cannot select a failed or unvalidated candidate. Team size alone is not a runtime competition/spending signal.

Exactly one selected candidate reaches the existing `ProtectedImplementationRuntime`. That runtime still performs final safe-patch validation/application against the server-resolved workspace, durable lineage compare-and-swap acceptance and the authoritative IMPLEMENT transition. The agentic controller cannot advance the source head, complete REVIEW, merge or production-deploy.

For process recreation after selection, the exact selected proposal/controller envelope is stored as a private immutable content-addressed artifact. The durable worker checkpoint stores only the artifact digest plus bounded selection evidence. Replay must rebind the artifact to exact Project/run/spec/acceptance/plan/base-lineage/base-revision/source-context identity and revalidate the proposal against the current protected workspace before canonical mutation. Artifact storage is replay evidence, not a new source-lineage authority.

After accepted IMPLEMENT, only the accepted lineage reaches BUILD/TEST/VERIFY and existing GitHub/Vercel Preview delivery. Preview remains the ordinary autonomous publication ceiling and REVIEW remains operator-controlled.

### Final release-verification gate

Wave 6 is **production-deployed and infrastructure-verified but not yet release-verified**. Infrastructure, durable replay prechecks, health/readiness and exact-deployment logs are green. The remaining #312 gate is intentionally application-authenticated and must not be replaced by a verification-only bypass.

Before closing #312 and calling Wave 6 release-verified:

1. authenticate through an existing production application bearer or authorized user session;
2. use a deliberately disposable Project-bound conversation with an approved Work Specification and valid repository/source binding;
3. execute the ordinary `/v1/engineering-runs/{run_id}/autonomous` path and prove live agentic PLAN/IMPLEMENT followed by exact-lineage BUILD/TEST/VERIFY, Preview publication and stop at REVIEW;
4. replay the same protected operation identity and confirm no duplicate canonical source mutation or duplicate Preview publication;
5. inspect run events, attempt evidence and accepted source lineage to prove canonical state/evidence consistency;
6. rescan the exact production deployment for runtime error/fatal signals after the smoke;
7. record the authenticated smoke identity/evidence, close #312 and reconcile this record from infrastructure-verified to release-verified.

No temporary auth bypass, synthetic owner endpoint, secret disclosure or weakening of REVIEW/Preview authority is permitted to satisfy this gate.

## Rollback

Rollback is component-specific and governed.

### API

Current Wave 6 production API:

- deployment `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`;
- application source `831fef94aa1c94ff1178b1a325e8774d49fd8752`;
- activation `PARALLAX_AGENTIC_RUNTIME_ENABLED=1` is version-controlled and rolls back with the application release identity.

Immediate pre-Wave-6 verified API rollback:

- deployment `dpl_FacxfrczQSQa8PUidqUA94hLT2Ex`;
- source `109444dcd7e13bfe842dea71355607941258b073`.

Previous #291 API rollback candidate remains `dpl_DKNMQrFEWa1kR8iY1vLQ6Y4sNYXP` at `a6d7a6fd4d556d5544ede9c43b93972a8c590011`. Pre-#291 accepted API reference remains `dpl_EGoHSRe69rCTZbbZjLnmFcDcqQC9` at `e6fc6900239df436545318e6ab7f532d0d3789bc`.

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
- server-owned activation flags do not redefine generated/integrated code as deployed; enabled production state requires explicit configuration and deployment evidence;
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
- agentic planning/dispatch/candidate evidence cannot advance canonical lineage or durable Engineering Run authority directly;
- selected-candidate artifact persistence is immutable replay evidence only and must be rebound/revalidated before canonical mutation;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- production hosted-model identity and transport are server-owned and fail closed;
- Preview remains the ordinary autonomous delivery ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- no deployment is recorded as production-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; W6-R1 creates no new constitutional authority.
- `ARCHITECTURE.md` v3.9 — updated for the validated/integrated Wave 6 live agentic composition, durable worker dispatch binding and private selected-candidate replay artifact boundary.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; W6-R1 changes no durable product visual or interaction-language contract.
- `CURRENT-STATE.md` — updated after the governed Wave 6 production release, bounded fail-closed production corrections, exact `main@831fef94aa1c94ff1178b1a325e8774d49fd8752` READY deployment and infrastructure/replay verification; authenticated Project-bound runtime smoke remains explicitly open.

Wave 6 is production-deployed and infrastructure-verified at application source `831fef94aa1c94ff1178b1a325e8774d49fd8752` / API deployment `dpl_Ag7tavEunrhQRGb3q8CxBTVVaQQw`; #312 remains deliberately open until the authenticated disposable Project-bound Engineering Run proves the live REVIEW-stop and idempotency contract. Safe-deletion final feature acceptance likewise remains open until authenticated post-cutover deletion behavior is exercised against a disposable test target.
