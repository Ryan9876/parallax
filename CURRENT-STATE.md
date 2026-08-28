# Parallax 2.0 Current State

Date: 2026-08-28

Status: **WAVES 1–7 DEPLOYMENT-VERIFIED / WAVE 8 S1 MAIN-MERGED AND CLIENT PRODUCTION-DEPLOYMENT-VERIFIED / CLIENT READY / API READY / SAFE-DELETION FINAL AUTHENTICATED DESTRUCTIVE SMOKE OPEN**

## Current production truth

Wave 8 S1 is validated, merged to `main`, production-deployed, and deployment-verified for the changed client surface.

Wave 8 S1 application merge:

`a784af75fc3076a56f9d8e52ff529ca8302e9ce6`

Wave 8 S1 changes the client experience only. It does not change API/runtime/database/provider/security authority.

### Client

Current deployment-verified production client:

- application source: `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- production deployment: `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`;
- Vercel project: `parallax` / `prj_wLXC5JjjetJf0H97kncRlqczD3OC`;
- target: `production`;
- state: `READY`;
- exact Git source: `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- aliases: `parallax-ashy-one-20.vercel.app`, `parallax-lew7.vercel.app`, `parallax-git-main-lew7.vercel.app`;
- alias error: none.

Wave 8 S1 production evidence:

- exact worker head `2754926d65ac46f12cf9a31d31d07de37038b155` fully qualified before merge;
- exact-head Vercel Preview `dpl_EoSBPtvZq48SxA9vDbG3CKGDpJb8` — `READY`;
- PR #376 merged with expected-head protection as `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- production build completed and deployment completed successfully;
- production Vercel deployment is `READY` and attached to the expected production aliases;
- production build errors-only scan contains no build failure;
- exact production deployment error/fatal runtime scan is clean;
- project runtime-error scan after cutover is clean;
- main Parallax P2 CI #1280 / run `33212573452` on exact merge source — PASS;
- production is protected by Vercel Authentication; an unauthenticated request correctly redirects to the Vercel SSO boundary. Authentication was not weakened or bypassed to manufacture release evidence.

The release qualification retained full browser/Skia acceptance, Google authentication/session handling, mobile keyboard/composer clearance, protected Engineering Run handoff, Live Build evidence access, source/diff/test/provider/health assertions, protected promotion/regression rejection, and independent DSPy release compilation.

### API

Wave 8 S1 has no API content delta. Current deployment-verified production API remains the Wave 7 release:

- application source: `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- production deployment: `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`;
- Vercel project: `parallax-api` / `prj_4lhve1AXZntfauaGHvkuaGWC6KJX`;
- target: `production`;
- state: `READY`;
- production alias: `parallax-api-tan.vercel.app`.

The Wave 7 API release remains production-verified with health/readiness, provider, source-lineage, execution-snapshot, runtime and main-CI evidence already recorded in repository history.

## Wave 8 — Human-centered UX and plain-language product experience

Control Tower: #374

Entry baseline:

`main@392c187d16a55688861db276d7d2150767667f2f`

### W8-S1 — Mobile orientation, readable typography and plain-language UX

Workstream: #375

Release PR: #376

Final qualified worker head:

`2754926d65ac46f12cf9a31d31d07de37038b155`

Application release merge:

`a784af75fc3076a56f9d8e52ff529ca8302e9ce6`

Production deployment:

`dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`

W8-S1 is **ACCEPTED / MAIN-MERGED / CLIENT PRODUCTION-DEPLOYMENT-VERIFIED**.

The deployed client now:

- uses a stable `Chat · Progress · Project` mobile navigation model;
- presents the user journey as `Define → Plan → Create → Check → Review` instead of engineering-first internal stage language;
- keeps current project, position, current activity and next meaningful action understandable without reconstructing state across screens;
- uses larger primary mobile typography and at least 44px primary touch targets;
- treats mobile as a guided control surface rather than a compressed desktop workspace;
- defaults ordinary mobile and desktop product copy to natural, outcome-oriented language;
- keeps raw IDs, internal states, failure codes, bindings and engineering evidence behind technical-detail or intentionally technical Live Build/Activity surfaces;
- preserves server-owned Project, Work Specification, Engineering Run, source, validation, provider, deployment and REVIEW authority;
- preserves mobile keyboard/composer behavior and authenticated account-control separation at phone width.

A release-gate defect found during qualification was fixed rather than waived: the authenticated 390px account control overlapped the mobile header actions. The production implementation reserves a dedicated account-control lane on mobile web. Stale acceptance paths were also updated to the current UX without removing substantive technical evidence assertions.

## Wave 7 retained baseline

Wave 7 Control Tower: #347

Wave 7 final application release merge:

`703934871e4df0f63828c7fd6e33d3e6a86b60b1`

Wave 7 S1–S6 remain **ACCEPTED / INTEGRATED / MAIN-MERGED / CHANGED-COMPONENT PRODUCTION-DEPLOYMENT-VERIFIED**.

Wave 7 established and retains:

- ParallaxBench objective evaluation;
- Agent Run projection/control contract;
- Development Studio composition over canonical Engineering Run truth;
- bounded safe browser evidence;
- agentic observability/runtime economics/retention projection;
- integrated product proof across protected source, evaluation, browser, provider and REVIEW boundaries.

Wave 8 does not replace or weaken those runtime/authority contracts.

## Local-first model routing

`P2-V0.19.8` local-first routing remains production-deployed and unchanged.

Vercel production remains intentionally hosted-only. With no admitted local-first production configuration, hosted model escalation remains:

1. `openai/gpt-5.6-luna`;
2. `openai/gpt-5.6-terra`;
3. `openai/gpt-5.6-sol`.

Hosted-to-private inference remains a separate architecture/security/network/deployment workstream.

## Production database and safe deletion

Supabase production migration `20260827173141` (`safe_conversation_project_deletion`) remains active and additive/backward-compatible.

Logical conversation/Project deletion remains production-deployed and infrastructure-verified. User-visible deletion is workspace deletion, not protected-evidence purge. Work Specifications, Engineering Runs, attempts/events, accepted source lineage and immutable engineering/provider evidence remain retained; deleting a Project does not delete linked GitHub repositories, pull requests or Vercel deployments.

Remaining safe-deletion debt: final authenticated destructive-behavior smoke against a deliberately disposable production conversation/Project. Authentication will not be weakened and real user content will not be deleted merely to manufacture evidence.

## Rollback

### Client

Current deployment-verified Wave 8 S1 client:

- source `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`;
- deployment `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`.

Immediate deployment-verified pre-Wave-8 rollback reference:

- source `f5e7618c1e4262232b5eee9dda3d5f7e724b140e`;
- deployment `dpl_jPuX7FfDKC1rYcHsf8TH4Xb9Vx4h`.

Wave 8 S1 adds no database migration and no API change, so client rollback does not require a schema or API rollback.

### API

Current deployment-verified Wave 7 API:

- source `703934871e4df0f63828c7fd6e33d3e6a86b60b1`;
- deployment `dpl_GSkdmZDyXoh2RUdoPjC2WCeHeJVi`.

Immediate fully deployment-verified pre-Wave-7 API rollback reference:

- source `35113209d9ad43585a6cc5ba167774ab8d13e03c`;
- deployment `dpl_VUpPpHN5vjXLWwwXGytxh5Uj3KSo`.

## Program controls

- GitHub plus the four authoritative project records outrank chat recollection;
- parent integration/control record #31 serializes cross-wave release truth;
- app-builder roadmap #32 records program progression;
- Wave 7 Control Tower #347 governs the retained Wave 7 productization/runtime baseline;
- Wave 8 Control Tower #374 governs the human-centered UX/plain-language program;
- every semantic AI/runtime change remains spec-first with stable acceptance IDs and authentic DSPy evidence;
- presentation may translate technical state into plain language but may not invent or conceal canonical state;
- deployment, integration, repository-record and production identities remain separate facts;
- no deployment-verification claim is valid without exact release identity and post-cutover evidence appropriate to the changed component.

## Durable invariants

- canonical Project, Work Specification, Engineering Run, repository/source identity and accepted lineage remain server-owned;
- deterministic/protected validation outranks benchmark, model, agent, evaluator, routing, browser, observability or integrated-proof judgment;
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
- plain language may simplify presentation but may not hide failures, consequences, uncertainty, security boundaries or required human approval;
- no deployment is recorded as deployment-verified without exact release identity and appropriate post-cutover evidence.

## Next governed implementation boundary

Wave 8 S1 is complete and deployment-verified. Wave 8 remains active under Control Tower #374; additional slices must be explicitly defined rather than inferred from S1.

Separate remaining boundaries are:

1. define the next Wave 8 slice under #374 before substantive implementation;
2. complete safe deletion #290 only when a deliberately disposable authenticated production target is available;
3. treat hosted-to-private inference from Vercel as a separate architecture/security/network/deployment workstream if later desired;
4. treat any parked authenticated Engineering Run as resumed only when its durable run/event evidence actually advances.

## Authoritative records

- `PROJECT-CONSTITUTION.md` v1.5 — updated by Wave 8 S1 to make plain language the durable default product-language principle.
- `ARCHITECTURE.md` v3.12 — unchanged by Wave 8 S1 because the client redesign does not alter durable runtime or authority architecture.
- `DESIGN-SYSTEM.md` v3.2 — updated by Wave 8 S1 with the human-centered mobile interaction and content standard.
- `CURRENT-STATE.md` — updated after production verification to record Wave 8 S1 source `a784af75fc3076a56f9d8e52ff529ca8302e9ce6`, production client deployment `dpl_BmCZheuArbBqDF7K1CSDQjiKkgPJ`, exact release qualification, rollback reference, and retained Wave 7/API truth.
