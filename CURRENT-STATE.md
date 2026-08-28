# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–6 DEPLOYMENT-VERIFIED / LOCAL-FIRST P2-V0.19.8 INTEGRATED AND PRODUCTION-DEPLOYED / PRODUCTION MOBILE PLAN-HANDOFF HOTFIX DEPLOYMENT-VERIFIED / WAVE 7 PRODUCTIZATION ACTIVE WITH S1–S5 ACCEPTED INTEGRATION AND S6 NEXT / CLIENT READY / API READY / SAFE DELETION PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED WITH FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

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

Wave 7 S1–S5 integration is development/integration work only and does not change the production API identity.

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

Current accepted Wave 7 integration SHA after S5:

`00a9e66e2f87a1f992d375b4217845b8f072e11d`

Wave 7 remains a development/integration program. No wholesale Wave 7 release to `main` or production has occurred. The production mobile reliability hotfix above remains a separately governed backport of behavior that originated in S3.

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

S3 composes the accepted S2 server-owned run contract into the Agent Run Canvas / Development Studio. It includes replay-safe approved-run continuation, run presentation/evidence interactions and mobile regression coverage without creating client-side canonical run/source/provider/REVIEW authority. Its production PLAN-handoff behavior was separately backported through PR #361; S3 integration itself is not production deployment.

### W7-S4 — Safe Browser Tool Layer v1: ACCEPTED / INTEGRATED

W7-S4 / #350 / `P2-V0.20.4` is accepted into the cumulative Wave 7 integration branch as:

`e98526bccd8e62530098a7e59991d837b515be0c`

Final accepted worker head:

`cda9e1e2c1de73ff20dbae8637fbdac63f810166`

Accepted exact-head evidence includes:

- Workstream Spec Validation #549 — PASS;
- Bounded Autonomy #789 — PASS;
- release-strength P2 CI #1220 — PASS;
- exact Preview `dpl_fpME2HH7x5jAQdL1haaPXLdhUJqK` — `READY`;
- Control Tower #347 authorized the exact reconciled head for integration;
- PR #357 merged to `integration/wave7-productization` as `e98526bccd8e62530098a7e59991d837b515be0c`.

S4 adds Project-scoped non-destructive browser evidence with server-admitted targets, bounded navigation/inspection/declarative assertion/screenshot evidence, off-origin redirect denial, sensitive-observation redaction and deterministic-validation precedence. It adds no arbitrary JavaScript/network, credential/cookie/header, destructive browser action, source acceptance, lifecycle, provider, merge/deploy or REVIEW-completion authority.

### W7-S5 — Agentic Observability, Runtime Economics & Retention: ACCEPTED / INTEGRATED

W7-S5 / #352 / `P2-V0.20.5` is accepted into the cumulative Wave 7 integration branch as:

`00a9e66e2f87a1f992d375b4217845b8f072e11d`

Final accepted worker head:

`26297f3fe3bbce4eca687c8a20b65d03b8476db9`

Accepted exact-head evidence:

- authentic DSPy Spec Optimization #182 / run `33180827909` — PASS; compiled plan committed; evidence artifact `9689671217`, digest `sha256:9f5a4087ae84ad78499ae72e4c0d006d4a9026e5b5c795ad1bb932efb459eb47`;
- Workstream Spec Validation #565 / run `33184346124` — PASS;
- Bounded Autonomy Pilot #804 / run `33182504539` — PASS;
- release-strength Parallax P2 CI #1237 / run `33184346191` — PASS, including API/contract, client/browser, protected promotion/regression and DSPy release gates;
- exact API Preview `dpl_E3iA7BbET4ZCt8TMFAjdJ1LMxrkb` — `READY`, clean errors-only build scan and clean exact-deployment runtime `error`/`fatal` scan;
- Control Tower #347 explicitly authorized only exact head `26297f3fe3bbce4eca687c8a20b65d03b8476db9` for integration;
- PR #360 merged with expected-head guard as `00a9e66e2f87a1f992d375b4217845b8f072e11d`.

S5 uses query-time derivation over existing server-owned run/attempt/event/worker/evaluation evidence; it adds no telemetry database, billing ledger or migration. Metrics retain explicit `OBSERVED`, `ESTIMATED` and `UNKNOWN` semantics; absent provider usage/cost stays unknown rather than becoming zero. Deterministic validation remains authoritative over qualitative evaluation/Preview state. Replay/event cardinality is bounded, cross-Project access fails closed, and incomplete event windows downgrade or withhold event-dependent claims rather than fabricating complete observation. Accepted retention cleanup is a deterministic no-op with no canonical deletion authority.

### Active dependency-aware lane

**W7-S6 / #353 / `P2-V0.20.6` — Integrated Product Proof** is now the remaining Wave 7 workstream. Its accepted dependency baseline is cumulative S1–S5 at `00a9e66e2f87a1f992d375b4217845b8f072e11d`. S6 must remain spec-first, prove the integrated product path and authority ceilings against this exact cumulative baseline, and stop at the governed release/integration boundary until Control Tower authorizes any `main`/production promotion.

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

Wave 7 S1–S5 have not been production-deployed, so there is no Wave 7 production rollback identity to record yet.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- Control record #31 remains the parent integration/release queue;
- Wave 7 Control Tower #347 governs `integration/wave7-productization`, exact-head integration and any separately authorized production hotfix/release boundary;
- app-builder roadmap #32 records Waves 1–6 complete and Wave 7 active;
- every semantic Wave 7 workstream remains spec-first with stable acceptance IDs and authentic DSPy SpecCritic + SpecCompiler evidence;
- interacting candidates integrate serially at the Wave 7 branch and cumulative gates rerun for each candidate against the latest accepted integration baseline;
- deployment, integration, repository-record and production identities remain separate facts;
- no production-verification claim is valid without exact release identity and appropriate post-cutover evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, competition, browser or observability judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- agentic, benchmark, projection, browser, observability and model output remains evidence, not authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- client reconnect/continuation may request existing bounded server authority but cannot redefine canonical run truth;
- hosted production model transport remains server-owned and fail-closed;
- local-first configuration remains rejected in Vercel production;
- browser-tool work may not create unrestricted JavaScript/network, credential or destructive-action authority;
- absent S5 economic evidence remains unknown, not zero;
- incomplete bounded event evidence cannot be presented as complete observation;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- no deployment is recorded as deployment-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Next governed implementation boundary

Begin W7-S6 / #353 / `P2-V0.20.6` Integrated Product Proof from accepted cumulative Wave 7 integration `00a9e66e2f87a1f992d375b4217845b8f072e11d`. S6 must exercise the integrated S1–S5 product path, validate authority ceilings and failure degradation, produce authentic DSPy/spec evidence and exact-head protected/release proof, then stop at the Control Tower release decision. It must not infer that S1–S5 integration already authorizes a `main` merge or production deployment.

The production mobile PLAN-handoff defect is deployment-verified fixed at the client release boundary, but the specific previously parked authenticated run should be considered resumed only when its durable run/event evidence advances after the user loads the new client.

Safe-deletion final authenticated destructive smoke and hosted-to-private inference from Vercel remain separate boundaries.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; S4/S5 integration uses existing governance and authority boundaries.
- `ARCHITECTURE.md` v3.11 — updated because accepted Wave 7 S1–S5 establish durable productization architecture for projection/control, Development Studio composition, safe browser evidence and query-time observability/economics/retention semantics without changing canonical authority.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; S4/S5 acceptance establishes no new durable visual-system rule.
- `CURRENT-STATE.md` — updated because W7-S4 and W7-S5 are now accepted into the cumulative Wave 7 integration branch, whose current accepted SHA is `00a9e66e2f87a1f992d375b4217845b8f072e11d`; production identities remain unchanged.