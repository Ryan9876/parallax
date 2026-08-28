# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–6 DEPLOYMENT-VERIFIED / LOCAL-FIRST P2-V0.19.8 INTEGRATED AND PRODUCTION-DEPLOYED / PRODUCTION MOBILE PLAN-HANDOFF HOTFIX DEPLOYMENT-VERIFIED / WAVE 7 PRODUCTIZATION ACTIVE WITH S1–S3 ACCEPTED INTEGRATION AND S4/S5 IN DEVELOPMENT / CLIENT READY / API READY / SAFE DELETION PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED WITH FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

### API

Current API application source:

`35113209d9ad43585a6cc5ba167774ab8d13e03c`

Current production API deployment:

`dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`

It remains `READY`, target `production`, exact Git SHA `35113209d9ad43585a6cc5ba167774ab8d13e03c`, and serves `parallax-api-tan.vercel.app`.

Retained API post-cutover evidence:

- main Workstream Spec Validation #505 / run `33134841900` — PASS;
- main Parallax P2 CI #1159 / run `33134841915` — PASS;
- production provider/source/private-Blob/lineage/runtime-bootstrap/execution-snapshot preflights — PASS;
- `GET /health` — HTTP 200 / service `parallax-api` / status `ok`;
- `GET /ready` — HTTP 200 / `database=ok`, `providers=ok`, `provider_targets=1`;
- exact deployment `error` / `fatal` runtime scan — clean.

The 2026-08-28 mobile PLAN-handoff release is client-only and does not change the production API identity.

### Client

Current deployment-verified production client:

- application source / main merge: `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- production deployment: `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`;
- target: `production`;
- public alias: `parallax-ashy-one-20.vercel.app`;
- production root fetch — HTTP 200;
- exact deployment build error scan — clean;
- exact deployment `error` / `fatal` runtime scan — clean.

This release fixes the production mobile dead-end in which an explicitly approved Code objective could durably complete SPECIFY and enter `PLAN`, while the mobile client never issued the separate existing protected autonomous continuation call.

Accepted hotfix behavior:

- `PLAN`, `IMPLEMENT`, `BUILD`, `TEST`, and `VERIFY` may request bounded continuation only from fresh server-owned Engineering Run truth;
- explicit Work Specification approval hands the newly activated run into the already-existing protected `/autonomous` endpoint;
- reopening/reconnecting an eligible active run performs one replay-safe continuation attempt using deterministic operation identity for the server revision;
- `SPECIFY`, `PAUSED`, `FAILED`, `REVIEW`, `SPEC_AMENDMENT`, `CANCELLED`, `COMPLETE`, and historical-unbound runs do not auto-continue;
- a failed autonomous handoff does not discard or fabricate canonical run state;
- no API/runtime authority, source acceptance, provider administration, arbitrary command, deployment authority, or REVIEW-completion authority was added.

Release evidence:

- hotfix PR #361 exact candidate head `30ca4d693b2bf39a24aab77b5e709b0724961cb1`;
- Bounded Autonomy Pilot #785 / run `33144164829` — PASS;
- release-strength Parallax P2 CI #1213 / run `33144164840` — PASS, including API regression, client type/state/export, production dependency audit, complete browser/Skia acceptance, protected promotion evaluation, and DSPy release compilation;
- focused 390×844 browser regression proves an eligible approved mobile run issues protected autonomy continuation;
- exact candidate Preview `dpl_EqKwkLmEPnrM4dNakDZcCKiXzdAJ` — `READY`, clean build and runtime error/fatal scans;
- Control Tower #347 explicitly authorized only the narrow production reliability hotfix after those gates;
- PR #361 merged with an exact-head guard as `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- exact production deployment `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h` — `READY`, aliased to `parallax-ashy-one-20.vercel.app`, HTTP 200, clean build and runtime error/fatal scans.

The already-existing user run that was parked at `PLAN` is preserved. The deployed client now has the replay-safe reconnect behavior required to continue that run when it is loaded; no claim is made that the specific authenticated user run advanced until corresponding run evidence is observed.

Repository documentation/control commits after this release do not replace the deployed application identity unless a deployable component actually changes and a new deployment is verified.

## Wave 7 — Productization & Measured Autonomy

Wave 7 Control Tower #347 is active.

Original accepted Wave 7 repository baseline:

`860c606c34884ba9af4a5ebc886d71147b53bc8c`

Dedicated cumulative integration branch:

`integration/wave7-productization`

Current accepted Wave 7 integration SHA after S3:

`bd3e510679fd156f2fce5bdf84412592a04420fb`

Wave 7 remains a development/integration program. No wholesale Wave 7 release to `main` or production has occurred. The narrow production mobile reliability hotfix above is a separately governed backport of behavior also present in S3.

### W7-S1 — ParallaxBench: ACCEPTED / INTEGRATED

W7-S1 / #348 / `P2-V0.20.1` is accepted and integrated.

Final worker head:

`3d07322a1df9a92deb3c5daae1121691597849c5`

Accepted evidence includes:

- authentic DSPy SpecCritic + SpecCompiler run #173 / `33136786353` — PASS;
- exact compiled-plan SHA-256 `621672c1aa5c0584b28b266a465444111e6ce96098744b34be0965b4a58a87a2`;
- Workstream Spec Validation #510 / run `33137992966` — PASS;
- Bounded Autonomy #745 — PASS;
- release-strength P2 CI #1170 / run `33137993003` — PASS;
- exact-head API Preview `dpl_Ek8vQEaQV9KAuG5384shP2wMQmFX` — `READY`;
- accepted integration `1a293d63cf1dfdfe78b9bb83da95130657468bfb`.

S1 is a read-only objective-evaluation layer. It adds no Engineering Run, source-lineage, provider/tool, deployment, or REVIEW authority.

### W7-S2 — Agent Run Projection & Control Contract: ACCEPTED / INTEGRATED

W7-S2 / #349 / `P2-V0.20.2` is accepted as cumulative Wave 7 integration:

`ab92b84e8f8a36870791f2154f86d838b3292f99`

Its accepted integration reuses existing server-owned Engineering Run pause/resume/cancel authority and adds the governed projection/control contract without creating a second run state machine or client-side canonical authority.

Recorded acceptance evidence includes exact-head Workstream Spec Validation #533, Bounded Autonomy #769, full release P2 CI #1194, authentic DSPy plan evidence, and READY API Preview `dpl_8KwmBQJ4ezQwd9CiqTMXFR1fTyic`.

### W7-S3 — Agent Run Canvas / Development Studio: ACCEPTED / INTEGRATED

W7-S3 / #351 / `P2-V0.20.3` is accepted into the cumulative Wave 7 integration branch as:

`bd3e510679fd156f2fce5bdf84412592a04420fb`

Final accepted worker head:

`31eb5fb2c07c58971975ea484bf796bee8112f64`

Accepted exact-head evidence:

- Workstream Spec Validation #548 / run `33144250517` — PASS;
- Bounded Autonomy #786 / run `33144250611` — PASS;
- release-strength P2 CI #1214 / run `33144250617` — PASS;
- exact Preview `dpl_3pb9Dw9EZdjJtkmwzN3T5inXct3Z` — `READY`, clean build and error/fatal runtime scans;
- Control Tower #347 authorized only this exact head for integration-branch merge;
- PR #359 merged to `integration/wave7-productization` as `bd3e510679fd156f2fce5bdf84412592a04420fb`.

S3 composes the accepted S2 server-owned run contract into the Agent Run Canvas / Development Studio. It includes the replay-safe approved-run continuation behavior, run presentation/evidence interactions, and mobile regression coverage without creating client-side canonical run/source/provider/REVIEW authority. Its production PLAN-handoff behavior was separately backported through PR #361; S3 integration itself is not production deployment.

### Active dependency-aware lanes

1. **W7-S4 / #350 / `P2-V0.20.4` — Safe Browser Tool Layer v1**
   - worker PR #357 targets `integration/wave7-productization`;
   - last validated/reconciled worker head `5be84c676f3a6cb54cdf85ec5e8e1304dffbc771` was based on accepted S2;
   - because S3 is now the accepted cumulative integration head, S4 must reconcile to `bd3e510679fd156f2fce5bdf84412592a04420fb` and rerun exact-head gates before Control Tower may integrate it;
   - scope remains Project-scoped, non-destructive browser evidence with admitted HTTPS targets, bounded declarative inspection/assertion/screenshot evidence, off-origin redirect denial, sensitive-observation redaction, deterministic-validation precedence, and no arbitrary JavaScript/network/credential/destructive-action authority;
   - candidate is not yet accepted/integrated.

2. **W7-S5 / #352 / `P2-V0.20.5` — Agentic Observability, Runtime Economics & Retention**
   - draft worker PR #360 targets `integration/wave7-productization`;
   - current head `c3f09e8541e449f5663e1854418d26b726131685` contains the spec-first contract on the earlier S2 baseline;
   - S5 consumes existing run/event/worker/evaluation evidence and may not create a scheduler, billing ledger, second state machine, or canonical-deletion authority;
   - before semantic acceptance it must reconcile to the latest accepted integration head and complete authentic DSPy evidence plus exact-head protected validation.

W7-S6 / #353 / `P2-V0.20.6` — Integrated Product Proof — remains downstream of accepted S1–S5.

### Wave 7 integration rule

All Wave 7 worker PRs target `integration/wave7-productization`, never `main`.

Workers stop `READY FOR INTEGRATION`; Control Tower integrates one accepted exact head at a time. A concurrently developed worker must reconcile to the latest accepted integration head and rerun exact-head gates before acceptance.

A production reliability hotfix may be separately backported to `main` only under an explicit Control Tower decision and must not be treated as wholesale acceptance of its originating workstream.

If a worker discovers that a shared authority/security contract must change, that work stops and returns to Control Tower rather than independently redefining the boundary.

## Local-first model routing — P2-V0.19.8

Workstream #301 is completed and released through PR #345.

Vercel production remains intentionally hosted-only. With no admitted local-first configuration, runtime order remains exactly:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted GPT-5.6 production traffic retains canonical model IDs, fixed Vercel AI Gateway transport and request-scoped Vercel runtime OIDC as automatic credential authority. Process-environment `VERCEL_OIDC_TOKEN` remains non-authoritative and there is no silent direct-OpenAI fallback.

When `VERCEL_ENV=production`, enabling local-first configuration fails closed before any local endpoint request. Hosted-to-private inference from Vercel remains a separate architecture/security/network/deployment problem.

Outside Vercel production, one server-owned admitted local route may precede the hosted chain when that Parallax instance can actually reach the configured operator-controlled inference endpoint. Local provider failure or protected-validation rejection may fall back without lowering acceptance requirements.

Local credential slots remain restricted to `PARALLAX_LOCAL_MODEL_CREDENTIAL_*`; local routing adds no Project/spec/source, filesystem/shell, unrestricted network, provider administration, GitHub/Vercel, merge, production-deployment, approval or REVIEW authority.

## Wave 6 — retained deployment-verified baseline

Wave 6 Control Tower #263 is closed completed. S1–S6 plus W6-R1 remain deployment-verified and cumulative with the local-first release.

Final Wave 6 application source before local-first integration:

`55066fccfcb9b4d645cdb87c8b7d061f032d6dec`

Final Wave 6 production API deployment before local-first integration:

`dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`

The authenticated Wave 6 production proof established Project-bound PLAN, agentic IMPLEMENT, exact-lineage BUILD/TEST/VERIFY, bounded GitHub/Vercel Preview delivery, operator REVIEW ceiling and replay/process-recreation stability without duplicate canonical mutation or publication.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Safe conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is logical workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project never deletes linked GitHub repositories, pull requests or Vercel deployments.

The remaining safe-deletion item is still the final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project target. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

## Rollback

### API

Current production API:

- source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`.

Immediate fully deployment-verified API rollback reference:

- Wave 6 source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- deployment `dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`.

The local-first release adds no database migration, so rollback to the verified Wave 6 API does not require schema rollback.

### Client

Current deployment-verified client:

- source `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- deployment `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`.

Immediate previous verified client rollback reference:

- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`.

The mobile PLAN-handoff hotfix adds no database or API migration.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- Control record #31 remains the parent integration/release queue;
- Wave 7 Control Tower #347 governs `integration/wave7-productization`, dependency-aware parallelism, and the separately authorized production hotfix boundary;
- app-builder roadmap #32 records Waves 1–6 complete and Wave 7 active;
- every semantic Wave 7 workstream remains spec-first with stable acceptance IDs and authentic DSPy SpecCritic + SpecCompiler evidence;
- at most three active Wave 7 development lanes run concurrently without a new Control Tower decision;
- interacting candidates integrate serially at the Wave 7 branch and cumulative gates rerun for each candidate against the latest accepted integration baseline;
- deployment, integration, repository-record, and production identities remain separate facts;
- no production-verification claim is valid without exact release identity and appropriate post-cutover evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, competition or browser judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- agentic, benchmark, projection and model output remains evidence, not authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- client reconnect/continuation may request existing bounded server authority but cannot redefine canonical run truth;
- hosted production model transport remains server-owned and fail-closed;
- local-first configuration remains rejected in Vercel production;
- browser-tool work may not create unrestricted JavaScript/network, credential or destructive-action authority;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- no deployment is recorded as deployment-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Next governed implementation boundary

Reconcile W7-S4 to accepted S3 integration `bd3e510679fd156f2fce5bdf84412592a04420fb`, rerun exact-head protected/release gates and integrate only if it remains clean. Continue S5 spec-first evidence work on the current three-lane budget, then reconcile it to the latest accepted integration head before semantic acceptance. W7-S6 remains blocked until S1–S5 are accepted.

The production mobile PLAN-handoff defect is deployment-verified fixed at the client release boundary, but the specific previously parked authenticated run should be considered resumed only when its durable run/event evidence advances after the user loads the new client.

Safe-deletion final authenticated destructive smoke and hosted-to-private inference from Vercel remain separate boundaries.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; the production hotfix and S3 integration use existing governance/authority boundaries.
- `ARCHITECTURE.md` v3.10 — unchanged in this record update; S3 composes the accepted server-owned run contract in the client and does not add a new backend authority/state machine. S4/S5 remain unaccepted candidates.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; S3 acceptance does not establish a new durable visual-system rule in this record update.
- `CURRENT-STATE.md` — updated because W7-S3 passed exact-head gates and was accepted into the cumulative Wave 7 integration branch as `bd3e510679fd156f2fce5bdf84412592a04420fb`.
