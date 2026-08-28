# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / LOCAL-FIRST P2-V0.19.8 PRODUCTION-DEPLOYED / MOBILE PLAN-HANDOFF HOTFIX DEPLOYMENT-VERIFIED / WAVE 7 S1–S6 MAIN-INTEGRATED AND CHANGED API SURFACES PRODUCTION-VERIFIED / CLIENT READY AND UNCHANGED / API READY / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 7 S1–S6 are now accepted, cumulatively integrated, merged to `main`, and deployment-verified for the components changed by the release.

The Wave 7 application release merge is:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Repository record-only commits after this application release do not replace a deployed application identity unless they cause a real changed-component production deployment that is separately verified.

### API

Current production API application source:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Current production API deployment:

`dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`

Production properties:

- project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state: `READY`;
- exact Git source: `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- production alias: `parallax-api-tan.vercel.app`;
- alias error: none.

Post-cutover production evidence:

- production provider preflight — PASS;
- production delivery-permission preflight — PASS;
- projected-source preflight — PASS;
- private Blob SDK and lineage-composition preflights — PASS;
- production agentic-runtime preflight — PASS;
- projected-bootstrap preflight — PASS, including process recreation, replay and no-stage-mutation checks;
- execution-snapshot preflight — PASS with deny-all restore and offline dependency verification;
- run-event schema guard — PASS;
- build completed and deployment completed successfully;
- `GET /health` on `parallax-api-tan.vercel.app` — HTTP 200, service `parallax-api`, status `ok`;
- `GET /ready` — HTTP 200, status `ready`, `database=ok`, `providers=ok`, `provider_targets=1`;
- exact deployment `error` / `fatal` runtime scan — clean;
- main Workstream Spec Validation #575 / run `33193923994` on exact merge source — PASS;
- main Parallax P2 CI #1250 / run `33193923996` on exact merge source — PASS.

### Client

Wave 7 contains no client content delta relative to the already deployment-verified production client. Vercel therefore canceled the path-aware client production attempt for the Wave 7 merge rather than creating a new client deployment.

Current deployment-verified production client remains:

- application source: `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- production deployment: `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`;
- target: `production`;
- aliases include `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app` and `parallax-git-main-lew7.vercel.app`.

The Wave 7 merge-created client deployment attempt `dpl_3TNmABFB7tUimF9LEnMdVckkXHuz` is `CANCELED` because the client tree is unchanged. It is not a deployment and is not represented as a new production identity.

The retained client includes the separately governed, deployment-verified mobile PLAN-handoff reliability fix. Eligible approved active runs may request the existing protected `/autonomous` continuation from fresh server-owned Engineering Run truth. The client cannot redefine canonical run state, source authority, provider authority or REVIEW completion.

The previously parked user run remains preserved. Its individual progression is not claimed unless corresponding durable run/event evidence is observed.

## Wave 7 — Productization & Measured Autonomy

Control Tower: #347

Original Wave 7 entry baseline:

`860c606c34884ba9af4a5ebc886d71147b53bc8c`

Final cumulative integration branch identity:

`integration/wave7-productization@eb217315992ac0e20acd978433f3e4a17cdcf565`

Final reconciled release candidate:

`16aa91e727dcfc3972f392ee918b1c4a92e567be`

Final release PR:

#372

Final application release merge:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Wave 7 S1–S6 are **ACCEPTED / INTEGRATED / MAIN-MERGED / CHANGED-COMPONENT PRODUCTION-DEPLOYMENT-VERIFIED**.

### W7-S1 — ParallaxBench

`P2-V0.20.1` / #348 — accepted and released.

ParallaxBench is a read-only objective-evaluation layer. Benchmark/model judgment cannot override deterministic failure, mutate an Engineering Run, accept source, administer providers/tools, deploy, merge or complete REVIEW.

### W7-S2 — Agent Run Projection & Control Contract

`P2-V0.20.2` / #349 — accepted and released.

The Agent Run projection is a typed view over the existing canonical Engineering Run/attempt/event/recovery/evaluation evidence. It does not create a second state machine. Control requests reuse existing protected pause/resume/cancel authority.

### W7-S3 — Agent Run Canvas / Development Studio

`P2-V0.20.3` / #351 — accepted and released.

Development Studio composes fresh server-owned S2 projection truth. Replay-safe continuation may request existing protected autonomy for eligible approved runs, but the client cannot create canonical run/source/provider/REVIEW authority. Its PLAN-handoff reliability behavior had already been separately backported and deployment-verified before the Wave 7 release; the final release therefore required no new client bytes.

### W7-S4 — Safe Browser Tool Layer v1

`P2-V0.20.4` / #350 — accepted and released.

S4 provides Project-scoped non-destructive browser evidence against server-admitted HTTPS targets with bounded navigation, inspection, declarative assertions and viewport screenshots. It exposes no arbitrary JavaScript/network, credential/cookie/header, destructive browser action, source acceptance, lifecycle, provider, merge/deploy or REVIEW authority.

### W7-S5 — Agentic Observability, Runtime Economics & Retention

`P2-V0.20.5` / #352 — accepted and released.

S5 derives bounded query-time evidence from existing authoritative run/attempt/event/worker/evaluation data. It adds no telemetry database or billing ledger. Metric provenance remains explicit `OBSERVED`, `ESTIMATED` or `UNKNOWN`; absent provider usage/cost is not synthesized as zero. Incomplete event windows downgrade or withhold claims. Accepted retention cleanup is a deterministic no-op and adds no canonical deletion authority.

### W7-S6 — Integrated Product Proof

`P2-V0.20.6` / #353 — accepted, integrated, released and closed completed.

Final worker head:

`e284d16972e80e40f7d5d7201f638fa72985d052`

S6 composes accepted S1/S3/S4/S5 evidence into a bounded integrated product proof across the immutable objective classes `stateful-workflow`, `data-operations` and `public-utility`.

It verifies exact Project / Work Specification / Engineering Run / source-lineage / Preview continuity, recomputes ParallaxBench truth, preserves S5 coverage state, admits only accepted browser evidence, proves bounded recovery/replay where required, preserves deterministic/protected failure precedence, rejects portfolio regressions and stops at `HUMAN_REQUIRED`.

S6 adds no upstream source, lifecycle, provider, browser-capability, merge/deploy or REVIEW authority.

## Wave 7 release qualification and reconciliation

The production mobile PLAN-handoff behavior was separately backported during Wave 7, so the accepted cumulative integration history could not be promoted naively without overlapping that history.

The final controlled dual-ancestry release reconciliation preserved the current deployment-verified client and authoritative records while retaining the accepted Wave 7 workflow/API/test/spec content.

Final candidate `16aa91e727dcfc3972f392ee918b1c4a92e567be` was reconciled against authoritative main baseline `126bd64284bc06f83dd03912cb2346252a7a7f86` with exact merge base and behind-by-zero status. Its final PR #372 contained exactly 39 intended Wave 7 files:

- 3 governed workflow files;
- 24 API/runtime/test surfaces;
- 12 `P2-V0.20.1`–`P2-V0.20.6` specification / compiled-plan records.

There was no client delta, authoritative-record delta, database migration, production configuration/credential change, or Project/source/provider/merge/deploy/REVIEW authority expansion.

Exact final-candidate qualification:

- Bounded Autonomy Pilot #811 / run `33193373970` — PASS;
- Workstream Spec Validation #574 / run `33193374005` — PASS, including committed protected-plan verification;
  - artifact `9694725556`, digest `sha256:1bedbecdfa8b7ae89b8291a9e6d05fd7bd00068b31ae4e29d27afc1f7a97e38e`;
- release-strength Parallax P2 CI #1249 / run `33193373971` — PASS, including API/contract regression, client type/state/export, complete browser/Skia acceptance, protected Code/engineering/Reason promotion and regression rejection, and independent DSPy release compilation;
  - DSPy evidence `9694805120`, digest `sha256:44b959ce5c0af1e84c3d435c9c9082aefc965dbf4ae514c7fa34b2362741027d`;
  - client-build evidence `9694771313`, digest `sha256:1d6d58ed4bca8de8e73b2f39a1180133b6f494f3ca79bdf3d31389be3da4f6cc`;
  - evaluation evidence `9694749947`, digest `sha256:f38099e9340af624947cf9af4f4f34bfa1106bca3d19d41fdcd076a437b2cbcd`;
- exact API Preview `dpl_FAHMsLThoXANZATBfEo4DdJch1ax` — READY, exact source `16aa91e...`, clean build errors-only and exact-deployment runtime error/fatal scans.

Control Tower #347 explicitly authorized only that exact candidate for main merge and the resulting path-aware production API release. PR #372 then merged with an expected-head guard as application source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`.

## Local-first model routing — P2-V0.19.8

Local-first routing remains production-deployed and unchanged by Wave 7.

Vercel production is intentionally hosted-only. With no admitted local-first configuration, hosted model escalation remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted GPT-5.6 traffic uses fixed Vercel AI Gateway transport and request-scoped Vercel runtime OIDC. Process `VERCEL_OIDC_TOKEN` remains non-authoritative. Enabling local-first in Vercel production fails closed. Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

Outside Vercel production, one server-owned admitted local model route may precede hosted fallback when the Parallax instance can actually reach the operator-controlled endpoint. Local output must pass the same protected validation and dedicated local credentials remain isolated to `PARALLAX_LOCAL_MODEL_CREDENTIAL_*`.

## Wave 6 retained baseline

Wave 6 Control Tower #263 is closed completed and deployment-verified.

Final Wave 6 application source before local-first integration:

`55066fccfcb9b4d645cdb87c8b7d061f032d6dec`

Final Wave 6 production API deployment before local-first integration:

`dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`

Wave 7 is cumulative with the accepted Wave 6 and local-first authority boundaries; it does not replace them.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Logical conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project does not delete linked GitHub repositories, pull requests or Vercel deployments.

Remaining safe-deletion debt: final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

## Rollback

### API

Current deployment-verified Wave 7 API:

- source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`.

Immediate fully deployment-verified pre-Wave-7 rollback reference:

- source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`.

Wave 7 adds no database migration, so API rollback does not require a schema rollback.

Retained deeper Wave 6 rollback reference:

- source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- deployment `dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`.

### Client

Current deployment-verified client remains:

- source `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- deployment `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`.

Immediate previous verified client rollback reference:

- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`.

No client rollback is required for the Wave 7 release because no client bytes changed.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- parent integration/control record #31 serializes cross-wave release truth;
- app-builder roadmap #32 records the program progression;
- Wave 7 Control Tower #347 governs the accepted S1–S6 program and final release evidence;
- every semantic AI/runtime change remains spec-first with stable acceptance IDs and authentic DSPy evidence;
- deployment, integration, repository-record and production identities remain separate facts;
- no deployment-verification claim is valid without exact release identity and post-cutover evidence appropriate to the changed component.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, competition, browser, observability or integrated-proof judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- client reconnect/continuation may request existing bounded server authority but cannot redefine canonical run truth;
- hosted production model transport remains server-owned and local-first remains rejected in Vercel production;
- browser tools cannot create unrestricted JavaScript/network, credential or destructive-action authority;
- absent economic evidence remains unknown, not zero;
- incomplete event evidence cannot be presented as complete observation;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- no deployment is recorded as deployment-verified without exact release identity and appropriate post-cutover evidence.

## Next governed implementation boundary

Wave 7 release work is complete and deployment-verified. No Wave 8 or successor program is inferred by this record.

Separate remaining boundaries are:

1. complete safe deletion #290 only when a deliberately disposable authenticated production target is available; do not weaken authentication or delete real user content to manufacture evidence;
2. treat hosted-to-private inference from Vercel as a separate architecture/security/network/deployment workstream if it is later desired;
3. treat the previously parked authenticated Engineering Run as resumed only when its durable run/event evidence actually advances.

Any next application-building wave should begin through the parent Control Tower / roadmap with an explicit objective, baseline and authority boundary rather than being invented by this release record.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; Wave 7 release used existing governance and authority rules.
- `ARCHITECTURE.md` v3.12 — unchanged in this final verification phase; it already records the durable S1–S6 architecture and release-reconciliation pattern.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; Wave 7 release establishes no new durable visual-system rule.
- `CURRENT-STATE.md` — updated because Wave 7 S1–S6 are now main-integrated and the changed API surfaces are production-deployment-verified at source `703934871e4df0f63828c7fd6e33d3e6a86b60b1` / deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`; the production client remains unchanged at `f5e7618c1e4262232b5eee9dda3d5f7e724b140e` / `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`.