# Parallax 2.0 Current State

Release: App-builder Wave 1 foundation
Date: 2026-08-22
Status: DEPLOYED — PRODUCTION VERIFIED FOUNDATION; END-TO-END APP BUILDING NOT YET COMPLETE
Production branch: `main`
Production application commit: `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`
Production web alias: `https://parallax-ashy-one-20.vercel.app`
Production API alias: `https://parallax-api-tan.vercel.app`
Production web deployment: `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` (unchanged v0.13.9 client)
Production API deployment: `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB`

## Current production baseline

Parallax now has the first deployed app-builder foundation while preserving the v0.13.9 conversation/client experience.

The existing production Code path still provides durable Work Specifications, immutable approved-spec Engineering Run binding, protected Code stages, bounded autonomy, Vercel Sandbox execution for registered commands, protected evaluation, Google authorization, durable persistence, and explicit human authority boundaries.

Wave 1 adds four durable backend foundations:

1. **Canonical Project/App lifecycle — P2-V0.14.1**
   - server-generated UUID Project identity;
   - owner-scoped create/list/read persistence and API;
   - immutable opaque `workspace_ref = project:<id>` identity;
   - optional bounded repository identity metadata;
   - additive production `projects` table with RLS enabled and direct `anon` / `authenticated` access revoked.

2. **Safe source implementation and patch engine — P2-V0.14.2**
   - bounded text source mutation inside an explicit isolated filesystem root;
   - exact expected-base digest protection and commit-time pre-image recheck;
   - traversal/symlink, binary, secret-sensitive, malformed, stale, oversized, unsupported and no-op patch rejection;
   - atomic multi-file prepare/apply/rollback behavior;
   - deterministic before/after/diff/artifact evidence;
   - explicit `protected_stage_authority: false`, with no shell, Git, network or deployment authority.

3. **Project-scoped tool authority contracts — P2-V0.14.3**
   - immutable capability/action/request/approval/decision/result/audit contracts;
   - server-owned fail-closed capability and approval registries;
   - exact project/tool/action matching;
   - destructive-action human approval invariant;
   - reserved denial of generic shell/exec/command/subprocess/raw-HTTP/network escape hatches;
   - structurally distinct `DENIED`, `FAILED` and `SUCCEEDED` outcomes;
   - no concrete provider adapter or credential exposure in this foundation.

4. **App-builder evaluation and observability spine — P2-V0.14.4**
   - versioned development and promotion suites;
   - deterministic protected scoring and critical-failure semantics;
   - coverage for project isolation, specification binding, implementation evidence, BUILD/TEST/VERIFY truthfulness, tool authority, interruption/recovery and evidence hygiene;
   - fail-closed secret and hidden-reasoning rejection;
   - digest-based observable evidence rather than raw provider payloads.

## Wave 1 integration and validation

The four worker candidates were not merged directly to production. They were serialized through `integration/wave1-app-builder` and revalidated cumulatively.

Final integration candidate:

- PR `#57` — **Wave 1 app-builder integration candidate**;
- validated head `345c6bc65faa9356c6035eb50bef6734bb7a6614`;
- production merge commit `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`.

Exact final cumulative validation:

- `Parallax Workstream Spec Validation` run `32603877967` — **SUCCESS**;
- `Parallax P2 CI` run `32603877968` — **SUCCESS**;
- `Bounded Autonomy Pilot` run `32603877972` — **SUCCESS**.

The integration branch was also revalidated after #44 and after #45 before the next interacting workstream was added. This prevents isolated worker success from being treated as proof that the combined runtime is safe.

The workstream spec gate now deterministically validates each changed semantic specification against its committed DSPy-generated compiled plan and protected acceptance map. Weak stochastic local-model regeneration is no longer used as a per-PR promotion oracle; the existing release DSPy lane remains the repository-level compiler-execution proof.

## Production deployment verification

### API

Vercel production deployment `dpl_D1ozbw2vzRF8DUcKFigiap4Q5HYB` is `READY`, targets production, and carries exact main commit `357aaf9e8dd2d7560b4adb0232746b7eb81b7b8c`.

Production aliases include:

- `parallax-api-tan.vercel.app`;
- `parallax-api-lew7.vercel.app`;
- `parallax-api-git-main-lew7.vercel.app`.

Live checks after deployment:

- `GET /health` → HTTP 200, service `parallax-api`, status `ok`;
- `GET /ready` → HTTP 200, database `ok`;
- unauthenticated `GET /v1/projects` → HTTP 401 with `Authentication required`, confirming the new Project surface remains behind the existing private authentication boundary;
- Vercel runtime error clusters for the API over the verification window: none observed.

### Database

The additive Project migration was applied before code promotion. Production verification confirms the `projects` table exists, has the expected schema, RLS is enabled, and direct client-role table access remains revoked. FastAPI remains the application authorization boundary.

### Web

Wave 1 contains no client implementation change. The Vercel web build for the main merge was canceled by the repository's path-aware deployment rules as intended. The deployed web application therefore remains the previously verified v0.13.9 client at `dpl_88MB16ZRUMgvFgzsukEMXq82Skyy` rather than creating a redundant production web build.

## Canonical Project identity rules

`Project.id` is now the canonical durable application identity.

`workspace_ref` is an opaque identity seam only. It is **not** a filesystem path and must never be interpreted as one by callers, models, tools or provider adapters.

`repository_ref` is bounded repository identity metadata only. It grants no Git, network, connector or deployment authority.

Tool authority must bind to the canonical Project ID after owner-scoped Project resolution. Filesystem execution must resolve through a protected Project-to-workspace allocator rather than a caller-selected path.

## What is not yet complete

Wave 1 deliberately establishes safe primitives and contracts rather than claiming an end-to-end autonomous app builder.

The current critical path is:

1. bind conversations, Work Specifications and Engineering Runs to the canonical Project identity;
2. implement a protected Project-to-isolated-workspace allocator;
3. connect the safe patch engine to the protected IMPLEMENT stage without treating patch success as stage authority by itself;
4. preserve one implementation workspace/revision across IMPLEMENT → BUILD → TEST → VERIFY instead of creating unrelated fresh sandboxes per stage;
5. adapt tool-authority contracts to concrete narrowly scoped GitHub/Vercel actions without generic shell/HTTP authority;
6. map implementation/tool/runtime evidence into the app-builder evaluation spine and add app-builder protected promotion gates;
7. prove interruption, retry, idempotency and resume behavior across project-scoped runs;
8. add the minimal project/diff/preview/review UX only after the backend contracts stabilize.

Until these are complete, Parallax should not claim it can autonomously build arbitrary applications end to end.

## Current operator-visible client baseline

The production web/client remains v0.13.9 and preserves:

- transparent glossy 3D interlocking-knot identity;
- Ambient Chroma Flow;
- rounded translucent Work Specification material;
- stream-synchronized optical engraving treatment;
- response live-edge following with intentional scroll-away preservation;
- mobile/iOS keyboard-safe in-flow composer geometry;
- Code/Engineering Run status and bounded-autonomy controls.

The previously pending real-device live-edge composition check and first real operator Sandbox exercise remain useful operator verification items, but they do not block the verified Wave 1 backend foundation.

## Parallel ChatGPT development state

The GitHub-authoritative parallel-development model is active under `PROJECT-CONSTITUTION.md` v1.1 and `PARALLEL-DEVELOPMENT.md`.

Wave 1 demonstrated the intended model in practice:

- four worker chats operated on isolated workstreams #43–#46;
- worker ownership remained bounded;
- workers prepared validated PRs without production merge/deploy authority;
- Integration / Control Tower serialized the interacting candidates;
- the cumulative integration branch was revalidated before production promotion;
- a CI design defect discovered during parallel work was corrected through #54 / PR #55 before promotion.

Issues #43–#46 are complete. Issue #32 remains the app-builder program record and now advances to Wave 2 integration work.

## Deployment state vocabulary

- v0.13.9 client baseline: **VALIDATED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Wave 1 Project lifecycle foundation: **VALIDATED / MERGED / DEPLOYED / DEPLOYMENT-VERIFIED**
- Wave 1 safe patch engine: **VALIDATED / MERGED / DEPLOYED AS FOUNDATION**
- Wave 1 tool-authority contracts: **VALIDATED / MERGED / DEPLOYED AS FOUNDATION**
- Wave 1 app-builder evaluation spine: **VALIDATED / MERGED / DEPLOYED AS FOUNDATION**
- production Project migration: **APPLIED / VERIFIED**
- production API deployment: **READY / HEALTH 200 / READY 200 / NO ERROR CLUSTERS OBSERVED**
- new Project API authentication boundary: **FAIL-CLOSED / UNAUTH 401 VERIFIED**
- complete project-scoped IMPLEMENT runtime: **NOT YET INTEGRATED**
- concrete GitHub/Vercel app-builder provider actions: **NOT YET INTEGRATED**
- end-to-end app-building loop: **NOT YET DEMONSTRATED**

## Authoritative record status

- `CURRENT-STATE.md`: updated for the validated, merged, deployed and production-verified Wave 1 app-builder foundation.
- `ARCHITECTURE.md`: requires/receives the durable Wave 1 Project, safe implementation, tool-authority and app-builder evaluation boundaries.
- `PROJECT-CONSTITUTION.md`: unchanged at v1.1; the existing parallel-development governance remains correct.
- `DESIGN-SYSTEM.md`: unchanged; Wave 1 introduced no client visual or interaction-system change.

Historical release, CI, workstream, preview and deployment evidence remains preserved in GitHub Actions, GitHub issues/PRs and Vercel history.
