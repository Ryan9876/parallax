# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–6 DEPLOYMENT-VERIFIED / LOCAL-FIRST P2-V0.19.8 PRODUCTION-DEPLOYED / MOBILE PLAN-HANDOFF HOTFIX DEPLOYMENT-VERIFIED / WAVE 7 S1–S6 ACCEPTED AND CUMULATIVELY INTEGRATED / RECONCILED WAVE 7 RELEASE CANDIDATE VALIDATED / MAIN MERGE AND PRODUCTION RELEASE NOT YET AUTHORIZED / CLIENT READY / API READY / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 7 has **not** been merged to `main` or production-deployed. Current production identities therefore remain unchanged.

### API

Current production API application source:

`35113209d9ad43585a6cc5ba167774ab8d13e03c`

Current production API deployment:

`dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`

Current production API remains `READY`, target `production`, serving `parallax-api-tan.vercel.app`.

Retained deployment-verification evidence includes:

- main Workstream Spec Validation #505 / run `33134841900` — PASS;
- main Parallax P2 CI #1159 / run `33134841915` — PASS;
- production provider/source/private-Blob/lineage/runtime-bootstrap/execution-snapshot preflights — PASS;
- `GET /health` — HTTP 200 / service `parallax-api` / status `ok`;
- `GET /ready` — HTTP 200 / database/providers ready;
- exact deployment runtime `error` / `fatal` scan — clean.

### Client

Current deployment-verified production client:

- application source: `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- production deployment: `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- state: `READY`;
- target: `production`;
- alias: `parallax-ashy-one-20.vercel.app`;
- production root fetch — HTTP 200;
- build and runtime error/fatal scans — clean.

This client includes the separately governed and deployment-verified mobile PLAN-handoff reliability fix. Eligible approved active runs may request the already-existing protected `/autonomous` continuation from fresh server-owned Engineering Run truth. The client cannot redefine canonical run state, source authority, provider authority or REVIEW completion.

The previously parked user run remains preserved. Its individual progression is not claimed unless corresponding durable run/event evidence is observed.

## Wave 7 — Productization & Measured Autonomy

Control Tower: #347

Original Wave 7 entry baseline:

`860c606c34884ba9af4a5ebc886d71147b53bc8c`

Dedicated cumulative integration branch:

`integration/wave7-productization`

Final accepted cumulative Wave 7 integration:

`eb217315992ac0e20acd978433f3e4a17cdcf565`

Wave 7 S1–S6 are now **ACCEPTED / INTEGRATED** on that branch. This is a development/integration identity, not a production identity.

### W7-S1 — ParallaxBench

`P2-V0.20.1` / #348 — accepted/integrated.

ParallaxBench is a read-only objective-evaluation layer. Benchmark/model judgment cannot override deterministic failure, mutate an Engineering Run, accept source, administer providers/tools, deploy, merge or complete REVIEW.

### W7-S2 — Agent Run Projection & Control Contract

`P2-V0.20.2` / #349 — accepted/integrated.

The Agent Run projection is a typed projection over the existing canonical Engineering Run/attempt/event/recovery/evaluation evidence. It does not create a second state machine. Control requests reuse existing protected pause/resume/cancel authority.

### W7-S3 — Agent Run Canvas / Development Studio

`P2-V0.20.3` / #351 — accepted/integrated.

The client composes fresh S2 server truth into the Development Studio. Replay-safe continuation may request existing protected autonomy for eligible approved runs but does not create client-side canonical run/source/provider/REVIEW authority.

Its PLAN-handoff reliability behavior was separately backported and deployment-verified in the current production client before wholesale Wave 7 release.

### W7-S4 — Safe Browser Tool Layer v1

`P2-V0.20.4` / #350 — accepted/integrated.

S4 provides Project-scoped non-destructive browser evidence against server-admitted HTTPS targets with bounded navigation, inspection, declarative assertions and viewport screenshots. It exposes no arbitrary JavaScript/network, credentials/cookies/headers, destructive browser action, source acceptance, lifecycle, provider, merge/deploy or REVIEW authority.

### W7-S5 — Agentic Observability, Runtime Economics & Retention

`P2-V0.20.5` / #352 — accepted/integrated.

S5 derives bounded query-time evidence from existing authoritative run/attempt/event/worker/evaluation data. It adds no telemetry database or billing ledger. Metric provenance remains explicit `OBSERVED`, `ESTIMATED` or `UNKNOWN`; missing provider usage/cost is not synthesized as zero. Incomplete event windows downgrade or withhold claims. Accepted retention cleanup is a deterministic no-op and adds no canonical deletion authority.

### W7-S6 — Integrated Product Proof

`P2-V0.20.6` / #353 — **ACCEPTED / INTEGRATED / CLOSED COMPLETED**.

Final worker head:

`e284d16972e80e40f7d5d7201f638fa72985d052`

Accepted integration merge:

`eb217315992ac0e20acd978433f3e4a17cdcf565`

S6 composes accepted S1/S3/S4/S5 evidence into a bounded integrated product proof across three immutable objective classes:

- `stateful-workflow`;
- `data-operations`;
- `public-utility`.

It verifies exact Project / Work Specification / Engineering Run / source-lineage / Preview continuity, recomputes ParallaxBench truth, preserves S5 coverage state, admits only accepted browser evidence, proves bounded recovery/replay where required, preserves deterministic/protected failure precedence, rejects portfolio regressions and stops at `HUMAN_REQUIRED`.

S6 adds no upstream source, lifecycle, provider, browser-capability, merge/deploy or REVIEW authority.

Accepted exact worker evidence:

- API suite: 906 passed, 1 skipped;
- Bounded Autonomy #807 / run `33187842726` — PASS;
- Workstream Spec Validation #568 / run `33188024999` — PASS;
- release-strength P2 CI #1241 / run `33188025079` — PASS;
- exact API Preview `dpl_B9HHdHHPYAoeSJhKs897kzTkdykR` — READY with clean build/runtime error scans;
- authentic `P2-V0.20.6` SpecCritic + SpecCompiler evidence committed.

## Wave 7 release reconciliation

Current `main` at release-candidate construction:

`a29a77fa5abe28c86b527a2a99f4023dc0c975f8`

Because the mobile PLAN-handoff fix had been separately backported to production, accepted Wave 7 integration and current main contain overlapping history even though their final client content is the same.

Content audit established:

- current main and accepted Wave 7 integration have the same complete `apps` tree;
- main changes after the original Wave 7 entry baseline were limited to current authoritative records plus the deployment-verified mobile-hotfix files;
- a blind history merge is therefore unnecessary and less reliable than controlled content reconciliation.

A two-parent release reconciliation was constructed:

- branch: `release/wave7-productization-v0206`;
- exact candidate: `e2743ee17264926adc675834ee38eee108af3111`;
- parent 1: current main at construction `a29a77fa5abe28c86b527a2a99f4023dc0c975f8`;
- parent 2: accepted Wave 7 integration `eb217315992ac0e20acd978433f3e4a17cdcf565`;
- release qualification PR: #370.

The candidate preserves the deployment-verified current-main client bytes and current authoritative records while adopting accepted Wave 7 workflow/API/test/spec trees. Its exact compare to the construction-time main contains only the intended Wave 7 workflow/API/test/spec surfaces: no client delta, no database migration, no production configuration/credential change and no authority expansion.

### Exact release-candidate validation

Exact candidate `e2743ee17264926adc675834ee38eee108af3111` has passed:

- Bounded Autonomy Pilot #808 / run `33189701035` — PASS;
- Workstream Spec Validation #571 / run `33189881795` — PASS, including protected committed-plan verification;
  - evidence artifact `9693298547`, digest `sha256:2fd401a8d9078a7d01e9530891ecde444cb3b69afe8ddc29b9ecf0caba33c8d2`;
- release-strength P2 CI #1244 / run `33189881717` — PASS, including API/contract regression, client type/state/export, complete browser/Skia acceptance, protected Code/engineering/Reason promotion and regression rejection, and independent DSPy release compilation;
  - DSPy evidence `9693367156`, digest `sha256:8ed8f89bd187d32b2ecc44dd30876fb3fcdfc65cc4d5512fdb59034390a2442a`;
  - client-build evidence `9693351932`, digest `sha256:4239ca9fbcb43b105ce54521e32c7013906e6962662cb14eb329c02a978662c9`;
  - evaluation evidence `9693323109`, digest `sha256:7f49f8198cd49d02abbc1b5589a8dfdf19b27d71c798bc4e8cec0da13680478a`;
- exact API Preview `dpl_E7yGJpknEU1thgE8UXR9v1wYgxUo` — READY, source exact `e2743ee...`, clean errors-only build scan and clean exact-deployment runtime error/fatal scan.

The Vercel client Preview for the release candidate is `CANCELED`, not READY, because there is no client content delta. Client qualification instead rests on byte-identical current-main client content plus the complete client/browser release gate in P2 #1244.

PR #370 is returned to draft after release-strength gates. **No main merge or production deployment has occurred.**

## Record reconciliation effect on the release candidate

This authoritative-record update is being prepared separately from the release code candidate. Once these records are merged to `main`, the main SHA will advance beyond `a29a77...`.

Therefore `e2743ee...` must not be merged afterward without reconciliation. The release branch must be reconciled to the new record-only main head, preserving the accepted Wave 7 code trees, and exact-head release gates/Preview evidence must be rerun for the resulting final candidate before Control Tower may authorize a main merge.

This prevents an otherwise-green candidate from silently being promoted against a stale main baseline.

## Local-first model routing — P2-V0.19.8

Local-first routing remains production-deployed and unchanged.

Vercel production is intentionally hosted-only. With no admitted local-first configuration, hosted model escalation remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted GPT-5.6 traffic uses fixed Vercel AI Gateway transport and request-scoped Vercel runtime OIDC. Process `VERCEL_OIDC_TOKEN` remains non-authoritative. Enabling local-first in Vercel production fails closed. Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

Outside Vercel production, one server-owned admitted local model route may precede hosted fallback when the Parallax instance can actually reach the operator-controlled endpoint. Local output must pass the same protected validation and dedicated local credentials remain isolated to `PARALLAX_LOCAL_MODEL_CREDENTIAL_*`.

## Wave 6 retained production baseline

Wave 6 Control Tower #263 is closed completed and deployment-verified.

Final Wave 6 application source before local-first integration:

`55066fccfcb9b4d645cdb87c8b7d061f032d6dec`

Final Wave 6 production API deployment before local-first integration:

`dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`

The production-deployed local-first release is cumulative with that Wave 6 baseline.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Logical conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project does not delete linked GitHub repositories, pull requests or Vercel deployments.

Remaining safe-deletion debt: final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

## Rollback

### API

Current production API:

- source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`.

Immediate fully deployment-verified API rollback reference:

- Wave 6 source `55066fccfcb9b4d645cdb87c8b7d061f032d6dec`;
- deployment `dpl_2uYwsPsKDFo214mEFxwwXGytxh5Uj3KSo`.

Wave 7 has not been production-deployed, so there is no Wave 7 production rollback identity yet.

### Client

Current production client:

- source `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- deployment `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`.

Immediate previous verified client rollback reference:

- source `a6d7a6fd4d556d5544ede9c43b93972a8c590011`;
- deployment `dpl_9QWFw2B8UgovHoEfhJuSPS2cev7K`.

The mobile PLAN-handoff fix adds no database/API migration.

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

1. Merge this **record-only** authoritative-record reconciliation to `main` after its own repository checks. It must not be treated as a Wave 7 application release.
2. Reconcile `release/wave7-productization-v0206` onto that new main record head while preserving the accepted Wave 7 code/spec trees and deployment-verified client bytes.
3. Rerun exact-head Bounded/Workstream/full P2 and changed-component Preview verification on the resulting final release candidate.
4. Return the exact final candidate to Control Tower #347 for an explicit `main` release decision.
5. Only after a separate exact-head authorization may Wave 7 code merge to `main`.
6. Production deployment/promotion is a further separate decision and must be followed by exact deployment identity plus health/readiness/runtime verification before Wave 7 can be recorded as deployment-verified.

Safe-deletion final authenticated destructive smoke and hosted-to-private inference from Vercel remain separate boundaries.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.4 — unchanged; Wave 7 S6/release reconciliation uses existing governance and authority boundaries.
- `ARCHITECTURE.md` v3.12 — updated because accepted S6 establishes the durable integrated-product-proof composition and because Wave 7 now has a durable dual-ancestry release-reconciliation pattern.
- `DESIGN-SYSTEM.md` v3.1 — unchanged; S6 and release reconciliation establish no new durable visual-system rule.
- `CURRENT-STATE.md` — updated to record S6 accepted/integrated, cumulative Wave 7 integration `eb217315992ac0e20acd978433f3e4a17cdcf565`, validated reconciled release candidate `e2743ee17264926adc675834ee38eee108af3111`, exact release evidence and the fact that no Wave 7 main merge or production deployment has occurred.