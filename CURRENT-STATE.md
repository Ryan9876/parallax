# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVES 1–6 DEPLOYMENT-VERIFIED / LOCAL-FIRST P2-V0.19.8 INTEGRATED AND PRODUCTION-DEPLOYED / VERCEL PRODUCTION HOSTED-ONLY COMPATIBILITY VERIFIED / WAVE 7 PRODUCTIZATION ACTIVE WITH S1 ACCEPTED INTEGRATION AND S2/S4 SEMANTIC DEVELOPMENT ACTIVE / CLIENT READY / API READY / SAFE DELETION PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED WITH FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production is cumulative through the accepted Wave 6 runtime and the `P2-V0.19.8` local-first model-routing release.

Current API application source:

`35113209d9ad43585a6cc5ba167774ab8d13e03c`

Current production API deployment:

`dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`

It is `READY`, target `production`, exact Git SHA `35113209d9ad43585a6cc5ba167774ab8d13e03c`, and serves `parallax-api-tan.vercel.app`.

Post-cutover evidence remains:

- main Workstream Spec Validation #505 / run `33134841900` — PASS;
- main Parallax P2 CI #1159 / run `33134841915` — PASS;
- production provider/source/private-Blob/lineage/runtime-bootstrap/execution-snapshot preflights — PASS;
- `GET /health` — HTTP 200 / service `parallax-api` / status `ok`;
- `GET /ready` — HTTP 200 / `database=ok`, `providers=ok`, `provider_targets=1`;
- exact deployment `error` / `fatal` runtime scan — clean.

Repository documentation/control commits and Wave 7 integration commits do not replace the deployed application identity unless a deployable component is merged to the production release branch and a new deployment is verified.

## Wave 7 — Productization & Measured Autonomy

Wave 7 Control Tower #347 is active.

Original accepted Wave 7 repository baseline:

`860c606c34884ba9af4a5ebc886d71147b53bc8c`

Dedicated cumulative integration branch:

`integration/wave7-productization`

Current accepted Wave 7 integration SHA after S1:

`1a293d63cf1dfdfe78b9bb83da95130657468bfb`

Wave 7 remains **development/integration only**. No Wave 7 application code is integrated to `main`, production-deployed or deployment-verified.

### W7-S1 — ParallaxBench: ACCEPTED / INTEGRATED

W7-S1 / #348 / `P2-V0.20.1` is accepted and integrated into the Wave 7 branch.

Final worker head:

`3d07322a1df9a92deb3c5daae1121691597849c5`

Accepted evidence:

- authentic DSPy SpecCritic + SpecCompiler development run #173 / `33136786353` — PASS;
- exact generated plan SHA-256 `621672c1aa5c0584b28b266a465444111e6ce96098744b34be0965b4a58a87a2`;
- Workstream Spec Validation #510 / run `33137992966` — PASS, including committed `--require-dspy` plan validation;
- Bounded Autonomy #745 — PASS;
- release-strength P2 CI #1170 / run `33137993003` — PASS, including API/client regression, browser/Skia acceptance, protected promotion evaluation and DSPy release compilation;
- exact-head API Preview `dpl_Ek8vQEaQV9KAuG5384shP2wMQmFX` — `READY`;
- PR #355 expected-head merged only to `integration/wave7-productization` as `1a293d63cf1dfdfe78b9bb83da95130657468bfb`.

S1 adds a read-only objective-level ParallaxBench contract with immutable case/candidate/evidence identity, explicit known-state/provenance, deterministic protected correctness as a hard floor, dimension-wise comparison, material-improvement rules, diverse bounded fixtures, replay-safe fingerprints and privacy-safe/no-authority serialization. It does not alter Engineering Run, source-lineage, provider/tool, deployment or REVIEW authority.

### Active dependency-aware lanes

1. **W7-S2 / #349 / `P2-V0.20.2` — Agent Run Projection & Control Contract**
   - semantic implementation is authorized because S1 is accepted;
   - authentic DSPy run #175 / `33137953047` — PASS, protected score `1.000`, exact plan SHA-256 `eacd73d93437541d62449f2e871e2ae647b5fa00802126faff102d070051c3ae`;
   - worker reconciled to accepted S1 integration before implementation;
   - implementation is a read-only projection over existing Engineering Run / attempt / run-event facts plus an authenticated typed projection API; no second state machine is introduced;
   - no writable controls are advertised in S2 v1 until a separately accepted existing server authority is explicitly composed;
   - candidate remains under exact-head validation and is not yet accepted/integrated.

2. **W7-S4 / #350 / `P2-V0.20.4` — Safe Browser Tool Layer v1**
   - semantic implementation is authorized because S1 is accepted;
   - authentic DSPy run #176 / `33137961535` — PASS, protected score `1.000`, exact plan SHA-256 `0522b8a668965ef7fad54e0592320e34db919a8e672964d7e69275e9b4782852`;
   - worker reconciled to accepted S1 integration before implementation;
   - implementation composes the existing Project-scoped `ToolCapabilityRegistry` with typed read-only browser-evidence capabilities, server-admitted HTTPS targets, bounded declarative assertions/inspection/screenshot evidence, off-origin redirect denial, sensitive-observation redaction, deterministic-validation precedence and ephemeral session cleanup;
   - the public S4 entrypoint exposes no arbitrary JavaScript, raw network, credential, destructive-action, source/provider/deployment or REVIEW authority;
   - candidate remains under exact-head validation and is not yet accepted/integrated.

Downstream implementation remains dependency-controlled:

- W7-S3 / #351 / `P2-V0.20.3` — Agent Run Canvas / Development Studio — implementation requires accepted S2;
- W7-S5 / #352 / `P2-V0.20.5` — Agentic Observability, Runtime Economics & Retention — S1 is satisfied; implementation still requires accepted S2;
- W7-S6 / #353 / `P2-V0.20.6` — Integrated Product Proof: Real-World App Completion — implementation requires accepted S1-S5.

### Wave 7 integration rule

All Wave 7 worker PRs target `integration/wave7-productization`, never `main`.

Workers stop `READY FOR INTEGRATION`; they do not deploy. Control Tower integrates one accepted exact head at a time and advances the accepted integration SHA only after the applicable exact-head gates pass. A concurrently developed worker must reconcile to the latest accepted integration head and rerun exact-head gates before acceptance.

The integration branch now admits worker PRs to the existing Workstream Spec Validation, Bounded Autonomy and P2 CI workflows. This validation-plumbing change does not alter application runtime behavior or production deployment identity.

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

## Production client

Current verified client production remains:

- Vercel project: `parallax`;
- deployment: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- source: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- state: `READY`;
- target: `production`;
- public alias: `parallax-ashy-one-20.vercel.app`.

No Wave 7 client deployment has occurred.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Safe conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is logical workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project never deletes linked GitHub repositories, pull requests or Vercel deployments.

The remaining safe-deletion item is still the final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project target. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

## Rollback

### API

Current production API:

- source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`.

Immediate fully deployment-verified rollback reference:

- Wave 6 source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- deployment `dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`.

The local-first release adds no database migration, so rollback to the verified Wave 6 API does not require schema rollback.

### Client

Current verified client remains `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K` at `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- Control record #31 remains the parent integration/release queue;
- Wave 7 Control Tower #347 governs `integration/wave7-productization` and dependency-aware parallelism;
- app-builder roadmap #32 records Waves 1–6 complete and Wave 7 active;
- every semantic Wave 7 workstream remains spec-first with stable acceptance IDs and authentic DSPy SpecCritic + SpecCompiler evidence;
- at most three active Wave 7 development lanes run concurrently without a new Control Tower decision;
- interacting candidates integrate serially at the Wave 7 branch and cumulative gates rerun for each candidate against the latest accepted integration baseline;
- deployment, integration, repository-record and production identities remain separate facts;
- no production-verification claim is valid without exact release identity and appropriate post-cutover evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, competition or browser judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- agentic, benchmark, projection and model output remains evidence, not authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- hosted production model transport remains server-owned and fail-closed;
- local-first configuration remains rejected in Vercel production;
- browser-tool work may not create unrestricted JavaScript/network, credential or destructive-action authority;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- no deployment is recorded as deployment-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Next governed implementation boundary

Complete exact-head release validation of W7-S2 and W7-S4. If S2 passes, Control Tower integrates it first, advances the accepted Wave 7 SHA, unlocks S3 and S5 semantic implementation, and requires concurrently developed S4 to reconcile to the new accepted integration SHA before its final acceptance. S4 must then rerun exact-head gates on that reconciled baseline before integration.

Safe-deletion final authenticated destructive smoke and hosted-to-private inference from Vercel remain separate boundaries.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; Wave 7 uses the existing governance/authority model.
- `ARCHITECTURE.md` v3.10 — unchanged in this record update; S1 is an evaluation layer that composes existing authority contracts without altering the durable runtime authority model. S2/S4 are not yet accepted integrations.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; no Wave 7 UI contract is accepted yet.
- `CURRENT-STATE.md` — updated because W7-S1 was accepted into the Wave 7 integration branch and S2/S4 semantic implementation was subsequently authorized, while production identities remain unchanged.
