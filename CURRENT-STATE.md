# Parallax 2.0 Current State

Date: 2026-08-27

Status: **WAVES 1–6 DEPLOYMENT-VERIFIED / LOCAL-FIRST P2-V0.19.8 INTEGRATED AND PRODUCTION-DEPLOYED / VERCEL PRODUCTION HOSTED-ONLY COMPATIBILITY VERIFIED / CLIENT READY / API READY / SAFE DELETION PRODUCTION-DEPLOYED AND INFRASTRUCTURE-VERIFIED WITH FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Parallax production is cumulative through the accepted Wave 6 runtime and the `P2-V0.19.8` local-first model-routing release.

The exact application source for the current API release is:

`35113209d9ad43585a6cc5ba167774ab8d13e03c`

That application source was integrated through PR #345 from exact validated worker head `457541490aae196ee9e8cb65434f7b5570b829fc` after explicit Control Tower authorization. The corresponding Vercel production API deployment is:

`dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`

It is `READY`, target `production`, exact Git SHA `35113209d9ad43585a6cc5ba167774ab8d13e03c`, and serves the production alias `parallax-api-tan.vercel.app`.

Post-cutover production evidence:

- main Workstream Spec Validation #505 / run `33134841900` — PASS;
- main Parallax P2 CI #1159 / run `33134841915` — PASS;
- production provider/source/private-Blob/lineage/runtime-bootstrap/execution-snapshot preflights — PASS;
- `GET /health` — HTTP 200 / service `parallax-api` / status `ok`;
- `GET /ready` — HTTP 200 / `database=ok`, `providers=ok`, `provider_targets=1`;
- exact deployment build completed successfully;
- exact deployment `error` / `fatal` runtime scan — clean.

The repository may later advance through record-only documentation commits. Those commits do not replace the deployed application identity above unless a deployable component actually changes and a new deployment is verified.

## Local-first model routing — P2-V0.19.8

Workstream #301 is integrated and released through PR #345.

### Production behavior

Vercel production remains intentionally hosted-only. With no admitted local-first configuration, runtime order remains exactly:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted GPT-5.6 production traffic retains canonical model IDs, the fixed Vercel AI Gateway transport and request-scoped Vercel runtime OIDC as automatic credential authority. Process-environment `VERCEL_OIDC_TOKEN` remains non-authoritative and there is no silent direct-OpenAI fallback.

If `VERCEL_ENV=production`, enabling local-first configuration fails closed before any local endpoint request, including a remote HTTPS endpoint. Hosted-to-private inference from Vercel is therefore not part of this release and requires a separate architecture/security/network/deployment workstream.

### Local/self-hosted behavior

Outside Vercel production, one server-owned admitted local route may precede the hosted chain when that Parallax instance can actually reach the configured operator-controlled inference endpoint.

A local result must pass the existing protected validator. A local provider failure or protected-validation rejection may fall back through the unchanged hosted chain without weakening acceptance requirements.

Local transport is bound only to its exact admitted local model. It cannot redirect canonical hosted GPT-5.6 routes.

Local configuration fails closed on malformed/unsupported provider-model combinations, endpoint userinfo/query/fragment, malformed ports, non-loopback plaintext HTTP, collision with the hosted chain or invalid credential configuration.

Local credential slots may resolve only through the dedicated `PARALLAX_LOCAL_MODEL_CREDENTIAL_*` server namespace and cannot select arbitrary process environment secrets or reserved hosted/provider credentials.

Routing diagnostics remain bounded to admitted model/provider identity, status, duration and sanitized exception class. Credentials, authorization values, raw exception text/results, prompts and generated content are excluded.

Local-first routing adds no Project/spec/source, filesystem/shell, unrestricted network, tool capability, provider administration, GitHub/Vercel, merge, production-deployment, approval or REVIEW authority.

### Validation evidence

Spec/evidence identity: `P2-V0.19.8`.

Authentic DSPy generation evidence:

- DSPy Spec Optimization #169 / run `33133824569` — PASS;
- development model `ollama_chat/llama3.2:1b` with `DSPY_LOCAL_DEVELOPMENT=1`;
- protected compiled-plan score `1.000`;
- protected `--require-dspy` validation — PASS;
- generation artifact `9671309634`, digest `sha256:9c89bee799572e80fe3c71c840cd492a2314b3ffe1efad179bb7fcb74851e5fe`;
- compiled-plan blob `8235d673aae0c232b5d216c3b1c7645344833289`.

Exact worker head `457541490aae196ee9e8cb65434f7b5570b829fc` passed:

- Workstream Spec Validation #503 / run `33134376707` — PASS;
- Bounded Autonomy Pilot #739 / run `33134282067` — PASS;
- Parallax P2 CI #1157 / run `33134376711` — PASS, including API regression, browser/Skia, protected promotion and independent DSPy release compilation;
- exact API Preview `dpl_531WGFwSHFAobWZTQS5kgWxQhFLW` — READY with clean build/runtime error scan.

The local/self-hosted route is therefore exact-head test/evaluation validated. It is deliberately not exercised as a Vercel-production local route because the accepted architecture forbids local-first configuration there.

## Wave 6 — retained deployment-verified baseline

Wave 6 Control Tower #263 and S1–S6 + W6-R1 remain deployment-verified and cumulative with the local-first release.

Final Wave 6 application source before local-first integration:

`55066fccfcb9b4d645cdb87c8b7d061f032d6dec`

Final Wave 6 production API deployment before local-first integration:

`dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj`

The authenticated Wave 6 production proof established Project-bound PLAN, agentic IMPLEMENT, exact-lineage BUILD/TEST/VERIFY, bounded GitHub/Vercel Preview delivery, operator REVIEW ceiling and replay/process-recreation stability without duplicate canonical mutation or publication.

Local-first routing changes model selection/transport policy only and does not modify the accepted Wave 6 Project/run/spec/source-lineage/worker/evaluation/Preview/REVIEW authority model.

## Production client

The local-first release is API-only. Client production remains on the previously verified artifact:

- Vercel project: `parallax`;
- deployment: `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`;
- source: `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- state: `READY`;
- target: `production`;
- public alias: `parallax-ashy-one-20.vercel.app`.

No redundant client production build is required merely to mirror an API-only release SHA.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Safe conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is logical workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project never deletes linked GitHub repositories, pull requests or Vercel deployments.

The remaining safe-deletion acceptance item is still the final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project target. Authentication will not be weakened and real user content will not be deleted merely to manufacture this evidence.

## Rollback

Rollback remains component-specific and governed.

### API

Current local-first production API:

- source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`.

Immediate fully deployment-verified rollback reference:

- Wave 6 source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- deployment `dpl_2uYwsPsKDFo214mEFxwwUKwa4Hzj`.

The local-first release adds no database migration, so rollback to the verified Wave 6 API does not require schema rollback.

### Client

Current verified client remains `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K` at `a6d7a6fd4d556d5544ede9c43b93972a8c590011`.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- Control record #31 is the active integration/release queue;
- Wave 6 Control Tower #263 remains the durable Wave 6 record;
- local-first workstream #301 records `P2-V0.19.8` reconciliation and release evidence;
- historical PR #303 is closed without merge and remains evidence only;
- semantic AI/runtime work remains spec-first with stable acceptance IDs and authentic compiled DSPy evidence;
- interacting production workstreams are serialized at shared lifecycle/record boundaries;
- deployment/integration/record identities remain separate facts;
- no production-verification claim is valid without exact release identity and appropriate post-cutover evidence.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks model, agent, evaluator, routing or competition judgment;
- immutable accepted lineage and single-writer canonical source mutation remain authoritative;
- agentic and model output remains evidence, not authority;
- cross-Project privacy boundaries remain strict;
- replay/idempotency and durable worker lease/checkpoint/recovery remain authoritative;
- hosted production model transport remains server-owned and fail-closed;
- local-first configuration remains server-owned, provider/model/endpoint/credential bounded and is rejected in Vercel production;
- Preview remains the ordinary autonomous publication ceiling;
- `REVIEW` / `HUMAN_REQUIRED` remains the autonomous authority ceiling;
- logical workspace deletion cannot erase protected engineering/source/provider evidence;
- no deployment is recorded as deployment-verified without exact release identity and post-cutover evidence appropriate to the changed component.

## Next governed implementation boundary

Local-first `P2-V0.19.8` no longer blocks the queue; it is integrated and production-deployed with hosted-production compatibility verified.

Two distinct future boundaries remain:

1. safe-deletion final authenticated destructive smoke, using only a deliberately disposable production target;
2. if desired, hosted-to-private inference from Vercel, which must be a separate architecture/security/network/deployment workstream and must not weaken the current production hosted-only boundary.

The next product wave should be selected through Control Tower based on the post-Wave-6 roadmap rather than reopening historical PR #303.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; local-first routing creates no new constitutional authority.
- `ARCHITECTURE.md` v3.10 — updated for the durable local-first routing, Vercel hosted-only production boundary, dedicated local credential namespace and reconciled Wave 6 production status.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; this release changes no durable visual or interaction-language contract.
- `CURRENT-STATE.md` — reconciled to application source `35113209d9ad43585a6cc5ba167774ab8d13e03c`, production deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`, post-cutover evidence and the accepted `P2-V0.19.8` production boundary.
